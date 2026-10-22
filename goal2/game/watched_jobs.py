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
import threading
import time

from goal2.engine.original_match.match import Event
from goal2.game.watched_match import WatchedOutcome, BENCH_CONTEXTS
from goal2.game.watched_publication import WatchedPublication
from goal2.game.watched_pitch import (MAX_FRAME_BYTES, MAX_FRAME_PACKET, FRAME_READ_BUDGET,
                                      FRAME_POLL_BUDGET, validate)

MAX_MEMORY = 32 * 1024 * 1024
# [designed: #311] How long a caller that must end a job keeps cancelling it (cancel_and_reap).
REAP_DEADLINE = 30
MAX_PACKET = 8 * 1024 * 1024
READ_BUDGET = 65536
# [designed: T102] Pacing: the child writes pitch sample k only once the parent has acknowledged
# sample k - LEAD as shown, so it is never more than LEAD samples ahead of the player's view. 64 is
# the viewer's own bounded queue (match_view.MAX_BACKLOG): the child never runs ahead of what the
# view can hold, and an Enter in play reaches the original within 64 samples of what the player
# sees (about a second at Normal, 60 per second; 6.4 s at Slowest, 10). It is large enough for the
# parent's 30 ms polls and the viewer's acknowledgements to keep Fastest (240) fed.
LEAD = 64
# [designed: T102] The command journal's bounds: one ack per pitch sample (at most
# watched_pitch.MAX_FRAMES), a pause and an answer per decision, each packet small.
MAX_COMMAND_PACKET = 4096
MAX_COMMANDS = 2 * 1024 * 1024
MAX_PAIRS = 20


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


def _pairs(value):
    """[designed: T102] The shape of an answer: at most MAX_PAIRS (off, on) player words. Whether a
    pair is legal is the original's to decide, never this check's."""
    if (not isinstance(value, (list, tuple)) or len(value) > MAX_PAIRS
            or any(not isinstance(pair, (list, tuple)) or len(pair) != 2
                   or any(type(word) is not int or not 1 <= word <= 3060 for word in pair) for pair in value)):
        raise ValueError('invalid substitution pairs')
    return [[off, on] for off, on in value]


class CommandReader:
    """[designed: T102] The child's side of the command journal: the latest acknowledged sample,
    the Enter presses and the answers, read in bounded batches."""
    def __init__(self, path, token):
        self.stream = open(path, 'rb')
        self.token = token
        self.sequence = 0
        self.buffer = bytearray()
        self.ack = -1
        self.pauses = 0
        self.answers = []

    def read(self):
        self.buffer.extend(self.stream.read(READ_BUDGET))
        if self.stream.tell() > MAX_COMMANDS:
            raise ValueError('watched command journal exceeds limit')
        while len(self.buffer) >= 4:
            size = struct.unpack('!I', self.buffer[:4])[0]
            if size > MAX_COMMAND_PACKET:
                raise ValueError('watched command packet exceeds limit')
            if len(self.buffer) < size + 4:
                break
            packet = bytes(self.buffer[4:4 + size])
            del self.buffer[:4 + size]
            identity, number, kind, value = json.loads(packet)
            if identity != self.token or type(number) is not int or number != self.sequence:
                raise ValueError('watched command identity/order differs from the job')
            self.sequence += 1
            if kind == 'ack' and type(value) is int and value >= self.ack:
                self.ack = value
            elif kind == 'pause' and value is None:
                self.pauses += 1
            elif (kind == 'answer' and isinstance(value, dict) and set(value) == {'decision', 'substitutions'}
                    and type(value['decision']) is int):
                self.answers.append((value['decision'], _pairs(value['substitutions'])))
            else:
                raise ValueError('invalid watched command')

    def wait(self, ready, pause=0.002):
        """Read until `ready()`; the parent's cancel terminates a child waiting here (#254)."""
        while True:
            self.read()
            if ready():
                return
            time.sleep(pause)


def _event(value):
    event = Event(**value)
    if (not isinstance(event.kind, str) or type(event.minute) is not int
            or not isinstance(event.score, tuple) or len(event.score) != 2
            or any(type(score) is not int or score < 0 for score in event.score)
            or not isinstance(event.data, dict)):
        raise ValueError('invalid watched event shape')
    return event


def _report(value):
    """[designed: T102] The shape of an `answered` record (goal2.game.watched_match._report)."""
    if (set(value) != {'context', 'asked', 'made', 'requested', 'refused', 'substitutions_left'}
            or value['context'] not in BENCH_CONTEXTS or type(value['substitutions_left']) is not int
            or not isinstance(value['refused'], list)
            or any(not isinstance(r, list) or len(r) != 3 or not isinstance(r[2], str) for r in value['refused'])):
        raise ValueError('invalid watched answer report')
    for name in ('asked', 'made', 'requested'):
        _pairs(value[name])
    _pairs([r[:2] for r in value['refused']])
    return copy.deepcopy(value)


def _memory(value):
    decoder = zlib.decompressobj()
    memory = decoder.decompress(base64.b64decode(value, validate=True), MAX_MEMORY + 1)
    if len(memory) > MAX_MEMORY or not decoder.eof or decoder.unused_data:
        raise ValueError('invalid or oversized watched memory')
    return memory


def _remove_folder(folder, attempts=40, pause=0.05):
    """[designed: #309] Remove a job's private folder. Windows can refuse to delete a file for a
    moment after the process that held it ended (WinError 32, seen on the Windows runner during
    a cancel at startup), so a refusal is retried for about two seconds. One that persists is
    raised, keeping the job owned and retryable as #254 requires."""
    for attempt in range(attempts):
        try:
            folder.cleanup()
            return
        except PermissionError:
            if attempt + 1 == attempts:
                raise
            time.sleep(pause)


class _PreparingProcess:
    """[designed: #254] Own private input preparation until an owner-thread launch.

    The thread only encodes/writes the captured job, never reads the active owner
    or launches a child. Popen-compatible lifecycle methods retain ownership when
    a bounded wait expires; cancelled preparation can never launch a worker.
    """
    def __init__(self, state, template, source, command, **options):
        self.args = command
        self._options = options
        self._process = None
        self._cancelled = False
        self._error = None
        def prepare():
            try:
                source.write_bytes(encode(state, template))
            except BaseException as exc:
                self._error = exc
        self._thread = threading.Thread(target=prepare, name='goal2-watched-input')
        self._thread.start()

    @property
    def pid(self):
        return self._process.pid if self._process is not None else None

    @property
    def returncode(self):
        if self._process is not None:
            return self._process.returncode
        return 0 if self._cancelled and not self._thread.is_alive() else None

    def poll(self):
        if self._thread.is_alive():
            return None
        self._thread.join()
        if self._cancelled:
            return self._process.poll() if self._process is not None else 0
        if self._error is not None:
            raise self._error
        if self._process is None:
            self._process = subprocess.Popen(self.args, **self._options)
        return self._process.poll()

    def terminate(self):
        self._cancelled = True
        if self._process is not None:
            self._process.terminate()

    def kill(self):
        self._cancelled = True
        if self._process is not None:
            self._process.kill()

    def wait(self, timeout=None):
        started = time.monotonic()
        self._thread.join(timeout)
        if self._thread.is_alive():
            raise subprocess.TimeoutExpired(self.args, timeout)
        if self._process is None:
            if self._cancelled:
                return 0
            self.poll()
        remaining = None if timeout is None else max(0, timeout-(time.monotonic()-started))
        return self._process.wait(timeout=remaining)


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

    def start(self, fixture, *, reference_seed=None, delay_byte=None, record_draws=False, frames=False,
              bench=False):
        if type(frames) is not bool or type(bench) is not bool:
            raise ValueError('frames and bench must be boolean')
        if self.closed or self.busy:
            raise ValueError('watched bridge is closed or a match is already running')
        if frames and getattr(self.owner, 'match_pending', False):
            raise ValueError('Another match is already pending')
        self._pitch_owns_pending = False
        job = self.publication.begin(fixture)
        self.token = job.token
        self.outcome = None
        self.events = []
        self._frames_enabled = frames
        self._frame_sequence = 0
        self._frame_ack = -1
        self._frame_watermark = 0
        self._frame_buffer = bytearray()
        self._engine_done = False
        self._complete = None
        self._completion_thread = None
        self._completion_work = None
        self._sequence = 0
        self._buffer = bytearray()
        # [designed: T102] The bench: the decision waiting for the player's answer, the decisions
        # asked so far, the engine's reports and the command journal's position.
        self._bench = bench
        self.waiting = None
        self._decisions = 0
        self._pause_pending = False
        self.reports = []
        self._command_sequence = 0
        try:
            self._start(job, reference_seed, delay_byte, record_draws)
            if frames:
                self.owner.match_pending = True
                self._pitch_owns_pending = True
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
        (folder / 'request.json').write_text(json.dumps({'token':job.token, 'fixture':asdict(job.fixture),
            'frames':self._frames_enabled, 'bench':self._bench,
            'options':dict(reference_seed=reference_seed, delay_byte=delay_byte, record_draws=record_draws)}))
        self._journal = (folder / 'events').open('w+b')
        self._errors = (folder / 'errors').open('w+b')
        self._frames = (folder / 'frames').open('w+b')
        self._commands = (folder / 'commands').open('wb')
        command = [sys.executable, '-m', 'goal2.game.watched_worker'] if self.command is None else list(self.command)
        self.process = _PreparingProcess(job.state, self._template, source,
            command + [str(source), str(folder / 'events')],
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
                    if self._bench and value.kind == 'decision' and value.data.get('context') in BENCH_CONTEXTS:
                        if self.waiting is not None:
                            raise ValueError('bench decision before the previous was answered')
                        self.waiting = copy.deepcopy(value)
                        if value.data['context'] == 'pause':
                            self._pause_pending = False
                elif kind == 'answered' and self._bench and isinstance(value, dict) and len(self.reports) < self._decisions:
                    self.reports.append(_report(value))
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
                self._engine_done = True
                self._maybe_publish(token)
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

    @property
    def engine_complete(self):
        """[designed] Valid transcript/exit received; presentation may still own pending state."""
        return getattr(self, '_engine_done', False)

    def _maybe_publish(self, token):
        if not self._engine_done:
            return
        if self._frames_enabled:
            size = Path(self._frames.name).stat().st_size
            if size > MAX_FRAME_BYTES:
                raise ValueError('pitch frame total budget exceeded')
            if self._frame_buffer or self._frames.tell() != size:
                return
            if self._frame_sequence != self._complete.result['ticks'] or self._frame_sequence == 0:
                raise ValueError('pitch frame count differs from completed ticks')
            if self._frame_ack != self._frame_sequence - 1:
                return
        # [designed: #254] Full result/image/round validation can be expensive.
        # It uses only private captured data; owner view/state swap stays here.
        thread = getattr(self, '_completion_thread', None)
        if thread is None:
            work = self.publication.prepare_completion(token, self._complete)
            self._completion_work = work
            self._completion_thread = threading.Thread(target=work.run, name='goal2-watched-completion')
            try:
                self._completion_thread.start()
            except BaseException:
                self._completion_thread = None
                self._completion_work = None
                self.publication.cancel()
                raise
            return
        if thread.is_alive():
            return
        thread.join()
        self.publication.publish_prepared(token, self._completion_work)
        self.outcome = self._complete
        self._release()

    def poll_frames(self, token):
        """[designed] Read <=64KiB/decode <=32 samples; caller owns returned poses.

        Canonical poll must run first. A frame ahead of that poll's event watermark
        waits in the bounded decoder; after canonical completion it is an error.
        Returned frames require cumulative acknowledgement after actual consumption.
        """
        self._check_token(token)
        if not self._frames_enabled:
            raise ValueError('pitch frames were not enabled')
        try:
            if (self.owner.state is not self._original or self.owner.state != self._snapshot
                    or self.owner.template_bytes != self._template):
                raise ValueError('watched job is stale; active game changed')
            size = Path(self._frames.name).stat().st_size
            if size > MAX_FRAME_BYTES:
                raise ValueError('pitch frame total budget exceeded')
            ready = len(self._frame_buffer) >= 4 and len(self._frame_buffer) >= 4 + struct.unpack('!I',self._frame_buffer[:4])[0]
            if not ready:
                self._frame_buffer.extend(self._frames.read(FRAME_READ_BUDGET))
            new = []
            for _ in range(FRAME_POLL_BUDGET):
                if len(self._frame_buffer) < 4:
                    break
                length = struct.unpack('!I',self._frame_buffer[:4])[0]
                if length > MAX_FRAME_PACKET:
                    raise ValueError('pitch frame packet budget exceeded')
                if len(self._frame_buffer) < length + 4:
                    break
                identity, frame = json.loads(bytes(self._frame_buffer[4:length+4]))
                if identity != token:
                    raise ValueError('pitch frame token differs')
                validate(frame, self._frame_sequence, self._frame_watermark)
                if frame['watermark'] > len(self.events):
                    if self._engine_done:
                        raise ValueError('pitch frame watermark exceeds canonical events')
                    break
                del self._frame_buffer[:length+4]
                self._frame_sequence += 1
                self._frame_watermark = frame['watermark']
                new.append(frame)
            if (self._engine_done and self._frames.tell() == size and self._frame_buffer
                    and (len(self._frame_buffer) < 4 or len(self._frame_buffer) < 4 + struct.unpack('!I',self._frame_buffer[:4])[0])):
                raise ValueError('truncated pitch frame record')
            if self._engine_done and size == 0:
                raise ValueError('pitch frame stream is empty')
            self._maybe_publish(token)
            return new
        except Exception as exc:
            self.cancel(token)
            raise ValueError(f'Invalid watched pitch IPC: {exc}') from exc

    def ack_frames(self, token, sequence):
        """[designed] Cumulative consumed sequence; duplicate/stale/future acks cannot publish."""
        self._check_token(token)
        if (not self._frames_enabled or type(sequence) is not int
                or not self._frame_ack < sequence < self._frame_sequence):
            raise ValueError('stale or invalid pitch frame acknowledgement')
        self._frame_ack = sequence
        if self._bench:
            # [designed: T102] The pacing: the child may run LEAD samples past this one.
            self._command(token, 'ack', sequence)

    def _command(self, token, kind, value):
        """[designed: T102] One record of the command journal, written by the parent alone."""
        try:
            packet = json.dumps([token, self._command_sequence, kind, value], allow_nan=False,
                                separators=(',', ':')).encode('utf8')
            if len(packet) > MAX_COMMAND_PACKET or self._commands.tell() + len(packet) + 4 > MAX_COMMANDS:
                raise ValueError('watched command journal exceeds limit')
            self._commands.write(struct.pack('!I', len(packet)) + packet)
            self._commands.flush()
            self._command_sequence += 1
        except Exception as exc:
            self.cancel(token)
            raise ValueError(f'Invalid watched command: {exc}') from exc

    def frames_drained(self):
        """[designed: T102] Every pitch sample the child has written so far has been read."""
        return (not self._frame_buffer and
                self._frames.tell() == Path(self._frames.name).stat().st_size)

    def pause(self, token):
        """[designed: T102] The player's Enter in play: the original takes it at its next key poll
        and asks a `pause` decision. One request at a time; none while a decision waits. Returns
        whether it was sent."""
        self._check_token(token)
        if not self._bench:
            raise ValueError('the bench was not enabled')
        if self.waiting is not None or self._pause_pending or self._engine_done:
            return False
        self._command(token, 'pause', None)
        self._pause_pending = True
        return True

    def answer(self, token, substitutions=()):
        """[designed: T102] Answer the waiting bench decision with (off, on) pairs; none plays on.
        The original makes, requests or refuses each pair; `reports` says which."""
        self._check_token(token)
        if self.waiting is None:
            raise ValueError('no bench decision is waiting')
        pairs = _pairs(list(substitutions))
        self._command(token, 'answer', {'decision': self._decisions, 'substitutions': pairs})
        self._decisions += 1
        self.waiting = None
        # [designed] Publication occurs on the next canonical poll, whose returned
        # events must reach the caller rather than disappear inside acknowledgement.


    def _release(self):
        for name in ('_journal', '_errors', '_frames', '_commands'):
            stream = getattr(self, name, None)
            if stream is not None:
                stream.close()
        folder = getattr(self, '_folder', None)
        if folder is not None:
            _remove_folder(folder)
            self._folder = None
        if getattr(self, '_pitch_owns_pending', False):
            self.owner.match_pending = False
            self._pitch_owns_pending = False
        self.process = None
        self._completion_thread = None
        self._completion_work = None

    def cancel(self, token):
        self._check_token(token)
        # [designed: #254] Invalidate first; a timed-out preparer/child stays owned
        # and busy until cancellation can reap it, before any folder is released.
        self.publication.cancel()
        self.process.terminate()
        try:
            self.process.wait(timeout=0.5)
        except subprocess.TimeoutExpired:
            self.process.kill()
            self.process.wait(timeout=0.5)
        # [designed: #254] Completion starts only after engine exit, so these
        # bounded waits cannot overlap a running engine/input-preparation wait.
        thread = getattr(self, '_completion_thread', None)
        if thread is not None:
            thread.join(0.5)
            if thread.is_alive():
                thread.join(0.5)
            if thread.is_alive():
                raise subprocess.TimeoutExpired('watched completion preparation', 1.0)
        self._release()

    def cancel_and_reap(self, token, deadline=REAP_DEADLINE):
        """[designed: #311; #254] Cancel until the job is reaped. One cancel during the input
        encoding times out and keeps the job owned (#254); a caller that must end the job retries
        it until the encoding is done, as on a loaded machine, and raises only past `deadline`."""
        end = time.monotonic() + deadline
        while True:
            try:
                return self.cancel(token)
            except subprocess.TimeoutExpired:
                if time.monotonic() >= end:
                    raise
                time.sleep(0.05)

    def close(self):
        if self.busy:
            self.cancel_and_reap(self.token)
        self.closed = True
        if getattr(self.owner, '_watched_jobs', None) is self:
            del self.owner._watched_jobs
