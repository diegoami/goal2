"""[designed: T65] Headless local process bridge; parent alone owns publication.

IPC is a private, length-prefixed JSON journal in a mode-0700 temporary folder.
Only the owned local child writes it; never open journals supplied by other users.
Each poll reads at most 64 KiB and consumes at most 32 packets, including partial
records. Completion waits for child exit, complete transcript and T64 validation.
"""
from pathlib import Path
import copy
import json
import base64
import zlib
from dataclasses import asdict
from goal2.game.session_save import encode, _json_value, _restore_json_value
import struct
import subprocess
import sys
import tempfile

from goal2.engine.original_match.match import Event
from goal2.game.watched_match import WatchedOutcome
from goal2.game.watched_publication import WatchedPublication

MAX_MEMORY = 32 * 1024 * 1024
MAX_PACKET = 8 * 1024 * 1024
READ_BUDGET = 65536


def _write(stream, token, sequence, kind, value):
    if isinstance(value, Event):
        value = asdict(value)
    elif isinstance(value, WatchedOutcome):
        value = {'result': value.result, 'memory': base64.b64encode(zlib.compress(value.memory)).decode('ascii'),
                 'events': [asdict(event) for event in value.events],
                 'seeds': value.seeds, 'engine_year': value.engine_year}
    packet = json.dumps(_json_value([token, sequence, kind, value]), allow_nan=False,
                        separators=(',', ':')).encode('utf8')
    if len(packet) > MAX_PACKET:
        raise ValueError('watched IPC packet exceeds limit')
    stream.write(struct.pack('!I', len(packet)) + packet)
    stream.flush()


def _event(value):
    event = Event(**value)
    if (not isinstance(event.kind, str) or type(event.minute) is not int
            or not isinstance(event.score, tuple) or len(event.score) != 2
            or any(type(score) is not int or score < 0 for score in event.score)
            or not isinstance(event.data, dict)):
        raise ValueError('invalid watched event shape')
    return event


def _memory(value):
    decoder = zlib.decompressobj()
    memory = decoder.decompress(base64.b64decode(value, validate=True), MAX_MEMORY + 1)
    if len(memory) > MAX_MEMORY or not decoder.eof or decoder.unused_data:
        raise ValueError('invalid or oversized watched memory')
    return memory


class WatchedJobs:
    """[designed] One active job per owner; token-scoped reads/cancellation.

    Keep this bridge for the owner's lifetime. start() returns a token; poll(token)
    returns newly observed events. Completion is available as outcome and published
    exactly once by poll. cancel/close bound termination and never publish.
    """
    def __init__(self, owner, *, command=None):
        if getattr(owner, '_watched_jobs', None) is not None:
            raise ValueError('active game already has a watched bridge')
        owner._watched_jobs = self
        self.owner = owner
        self.publication = WatchedPublication(owner)
        self.command = command
        self.process = None
        self.token = None
        self.outcome = None
        self.events = []
        self.closed = False

    @property
    def busy(self):
        return self.process is not None

    def start(self, fixture, *, reference_seed=None, delay_byte=None, record_draws=False):
        if self.closed or self.busy:
            raise ValueError('watched bridge is closed or a match is already running')
        job = self.publication.begin(fixture)
        self.token = job.token
        self.outcome = None
        self.events = []
        self._complete = None
        self._sequence = 0
        self._buffer = bytearray()
        try:
            self._start(job, reference_seed, delay_byte, record_draws)
        except Exception:
            self.publication.cancel()
            self._release()
            raise
        return self.token

    def _start(self, job, reference_seed, delay_byte, record_draws):
        self._original = self.owner.state
        self._snapshot = copy.deepcopy(self.owner.state)
        self._template = bytes(self.owner.template_bytes)
        self._folder = tempfile.TemporaryDirectory(prefix='goal2-watched-')
        folder = Path(self._folder.name)
        source = folder / 'input'
        source.write_bytes(encode(job.state, self._template))
        (folder / 'request.json').write_text(json.dumps({'token':job.token, 'fixture':asdict(job.fixture),
            'options':dict(reference_seed=reference_seed, delay_byte=delay_byte, record_draws=record_draws)}))
        self._journal = (folder / 'events').open('w+b')
        self._errors = (folder / 'errors').open('w+b')
        command = [sys.executable, '-m', 'goal2.game.watched_worker'] if self.command is None else list(self.command)
        self.process = subprocess.Popen(command + [str(source), str(folder / 'events')],
            cwd=Path(__file__).resolve().parents[2], stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL, stderr=self._errors)

    def _check_token(self, token):
        if token != self.token or not self.busy:
            raise ValueError('stale or consumed watched job token')

    def poll(self, token):
        self._check_token(token)
        new = []
        try:
            if (self.owner.state is not self._original or self.owner.state != self._snapshot
                    or self.owner.template_bytes != self._template):
                raise ValueError('watched job is stale; active game changed')
            # [designed] Drain queued complete frames before reading another bounded batch.
            ready = (len(self._buffer) >= 4 and
                     len(self._buffer) >= 4 + struct.unpack('!I', self._buffer[:4])[0])
            if not ready:
                self._buffer.extend(self._journal.read(READ_BUDGET))
            for _ in range(32):
                if len(self._buffer) < 4:
                    break
                size = struct.unpack('!I', self._buffer[:4])[0]
                if size > MAX_PACKET:
                    raise ValueError('watched IPC packet exceeds limit')
                if len(self._buffer) < size + 4:
                    break
                packet = bytes(self._buffer[4:4 + size])
                del self._buffer[:4 + size]
                identity, number, kind, value = _restore_json_value(json.loads(packet), 'watched IPC')
                if identity != token or type(number) is not int or number != self._sequence or self._complete is not None:
                    raise ValueError('watched IPC identity/order differs from active job')
                self._sequence += 1
                if kind == 'event':
                    value = _event(value)
                    self.events.append(value)
                    new.append(copy.deepcopy(value))
                elif kind == 'complete':
                    value = WatchedOutcome(value['result'], _memory(value['memory']),
                        tuple(_event(event) for event in value['events']), tuple(value['seeds']), value['engine_year'])
                    if tuple(self.events) != value.events:
                        raise ValueError('watched completion differs from live event stream')
                    self._complete = value
                elif kind == 'error' and isinstance(value, str):
                    raise ValueError('Watched worker failed: ' + value)
                else:
                    raise ValueError('invalid watched IPC record')
            code = self.process.poll()
            # [designed] Drain bounded batches after exit, before accepting the final packet.
            if code is not None and not self._buffer and self._journal.tell() == Path(self._journal.name).stat().st_size:
                if code != 0 or self._complete is None:
                    self._errors.seek(0)
                    detail = self._errors.read(1500).decode(errors='replace')
                    raise ValueError(f'Watched worker exited ({code}) without completion: {detail}')
                self.publication.complete(token, self._complete)
                self.outcome = self._complete
                self._release()
            elif code is not None and len(self._buffer) < 4 and self._journal.tell() == Path(self._journal.name).stat().st_size:
                raise ValueError('truncated watched IPC record')
            elif code is not None and len(self._buffer) >= 4:
                size = struct.unpack('!I', self._buffer[:4])[0]
                if len(self._buffer) < size + 4 and self._journal.tell() == Path(self._journal.name).stat().st_size:
                    raise ValueError('truncated watched IPC record')
            return new
        except Exception as exc:
            self.cancel(token)
            raise ValueError(f'Invalid watched worker IPC: {exc}') from exc

    def _release(self):
        self.process = None
        for name in ('_journal', '_errors'):
            stream = getattr(self, name, None)
            if stream is not None:
                stream.close()
        folder = getattr(self, '_folder', None)
        if folder is not None:
            folder.cleanup()
            self._folder = None

    def cancel(self, token):
        self._check_token(token)
        try:
            self.process.terminate()
            try:
                self.process.wait(timeout=0.5)
            except subprocess.TimeoutExpired:
                self.process.kill()
                self.process.wait(timeout=0.5)
        finally:
            self.publication.cancel()
            self._release()

    def close(self):
        if self.busy:
            self.cancel(self.token)
        self.closed = True
        if getattr(self.owner, '_watched_jobs', None) is self:
            del self.owner._watched_jobs
