"""[designed: T65] Headless local process bridge; parent alone owns publication.

[designed: owner, 2026-11-03, #527 D3; T160] The match plays in the owner's one engine process
(goal2.game.engine_process, docs/engine-process.md), shared by the owner's bridges (MatchEngine). Each poll
consumes at most 32 of the match's replies. Completion waits for the engine's `complete`, a complete
transcript and T64 validation.

The file journal below (_write, CommandReader, _PreparingProcess, _remove_folder) is the old per-match
worker's (goal2.game.watched_worker, goal2.desktop.competitive_worker), unused by the window; T161 removes it.
"""
from pathlib import Path
import collections
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
from goal2.game.watched_match import WatchedOutcome, BENCH_CONTEXTS, PROMPT_CONTEXTS
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


def _choice(value):
    """[designed: T167, #541] The shape of a player prompt's answer: {'taker': a player word or None} or
    {'shootout_order': distinct player words}. Whether the player can take it is the kit's to decide."""
    words = lambda v: (isinstance(v, (list, tuple)) and len(v) <= 11 and len(set(v)) == len(v)
                       and all(type(w) is int and 1 <= w <= 3060 for w in v))
    if not isinstance(value, dict):
        raise ValueError('invalid prompt answer')
    keys = set(value) - {'op', 'decision'}
    if keys == {'taker'} and (value['taker'] is None or words([value['taker']])):
        return {'taker': value['taker']}
    if keys == {'shootout_order'} and words(value['shootout_order']):
        return {'shootout_order': list(value['shootout_order'])}
    raise ValueError('invalid prompt answer')


# [designed: T180, #574] The other changes a bench answer may carry besides the pairs, passed to the kit's
# `Match.answer` as they are (goal2/engine/original_match/match.py): positions {player: code 0..13} (R, C on S19),
# marking {player: opponent word or 0} (S09's mark line, 1771:49B8) and own_tactics {player: {element 1..4: True,
# False or None}} (S09's four lines, 1771:4B61). Whether the original takes one is its to decide.
CHANGES = ('positions', 'marking', 'own_tactics')


def _changes(value):
    """[designed: T180] The shape of a bench answer's changes (CHANGES), keys as integers; empty ones dropped."""
    word = lambda v: type(v) is int and 1 <= v <= 3060
    if not isinstance(value, dict) or set(value) - set(CHANGES):
        raise ValueError('invalid bench changes')
    out = {}
    for name, items in value.items():
        if not isinstance(items, dict) or len(items) > MAX_PAIRS:
            raise ValueError('invalid bench changes')
        items = {int(k): v for k, v in items.items()} if all(str(k).isdigit() for k in items) else None
        if items is None or not all(word(k) for k in items):
            raise ValueError('invalid bench changes')
        if name == 'positions' and not all(type(v) is int and 0 <= v <= 13 for v in items.values()):
            raise ValueError('invalid bench positions')
        if name == 'marking' and not all(v == 0 or word(v) for v in items.values()):
            raise ValueError('invalid bench marking')
        if name == 'own_tactics':
            own = {}
            for player, elements in items.items():
                if (not isinstance(elements, dict) or not all(str(e) in ('1', '2', '3', '4') for e in elements)
                        or not all(v is None or type(v) is bool for v in elements.values())):
                    raise ValueError('invalid bench own tactics')
                own[player] = {int(e): v for e, v in elements.items()}
            items = own
        if items:
            out[name] = items
    return out


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


# --- the bridge on the engine process --------------------------------------------------------------------------

# [designed: owner, 2026-11-03, #527 D3; T160] The matches play in the owner's one engine process
# (goal2.game.engine_process, docs/engine-process.md), run as this module under engine_python().
ENGINE = 'goal2.game.engine_server'
# [designed: T160] How long a cancel waits for the engine's `cancelled` before the process is killed. The engine
# reads a cancel at every event and pitch sample, milliseconds apart in play; the old worker's cancel was a
# terminate, 0.5 s, then a kill, 0.5 s (#254).
CANCEL_WAIT = 1.0
# [designed: T160] How long after that kill the reader has to report the process's end.
DEATH_WAIT = 3.0
# [designed: T160] The replies one poll consumes, as the journal's 32 records a poll.
REPLY_BUDGET = 32


class _Match:
    """[designed: T160] One match's replies as the engine's reader thread delivers them, drained by the bridge's
    polls on the owner's thread. Pitch samples wait apart from the rest, for poll_frames."""
    TERMINAL = ('complete', 'cancelled', 'error', 'death')

    def __init__(self):
        self.replies = collections.deque()
        self.frames = collections.deque()
        self.received_frames = 0
        self.ended = threading.Event()

    def put(self, kind, value):
        if kind in ('ready', 'opened'):
            return
        if kind == 'frame':
            self.frames.append(value)
            self.received_frames += 1
        else:
            self.replies.append((kind, value))
        if kind in self.TERMINAL:
            self.ended.set()


class MatchEngine:
    """[designed: owner, 2026-11-03, #527 D3; T160] The owner's one engine process, shared by its bridges
    (WatchedJobs and CompetitiveJobs, held on the owner as `_match_engine`).

    The process starts at the first match, is sent the game with `open` once, and again only when the game a match
    plays (the publication's prepared state and the template) differs from the last one sent, or the process is new.
    One match is attached at a time; the reader thread's replies go to it and to nothing else, so the replies of a
    cancelled or replaced match never reach the next one. The process is closed when the owner's last bridge closes.
    """

    def __init__(self):
        from goal2.game.engine_process import EngineProcess
        self.engine = EngineProcess(self._reply)
        self.bridges = []
        self.game = None          # (state, template) of the last `open` sent
        self.match = None         # the attached _Match
        self._lock = threading.Lock()

    @classmethod
    def join(cls, owner, bridge):
        shared = getattr(owner, '_match_engine', None)
        if shared is None:
            shared = cls()
            owner._match_engine = shared
        shared.bridges.append(bridge)
        return shared

    def leave(self, owner, bridge):
        self.bridges = [b for b in self.bridges if b is not bridge]
        if self.bridges:
            return
        if getattr(owner, '_match_engine', None) is self:
            del owner._match_engine
        self.engine.close()

    def _reply(self, kind, value):
        with self._lock:
            match = self.match
        if match is not None:
            match.put(kind, value)

    def claim(self, match):
        with self._lock:
            if self.match is not None:
                raise ValueError('Another match is already running; finish or cancel it first')
            self.match = match

    def release(self, match):
        with self._lock:
            if self.match is match:
                self.match = None

    def needs_open(self, state, template):
        process = self.engine.process
        return (process is None or process.poll() is not None or self.game is None
                or self.game[1] != template or self.game[0] != state)


class _Preparation:
    """[designed: #254; T160] Encode the game off the owner's thread and send it with `open`. It never reads the
    active owner and never sends a match; a cancelled preparation sends nothing more."""

    def __init__(self, shared, state, template):
        self.cancelled = False
        self.error = None
        self.phase = 'encode'

        def run():
            try:
                raw = encode(state, template)
                if self.cancelled:
                    return
                self.phase = 'open'
                shared.game = (state, template)
                shared.engine.open_encoded(raw)
            except BaseException as exc:
                self.error = exc
                self.engine_ran = shared.engine.process is not None
        self.engine_ran = False
        self.thread = threading.Thread(target=run, name='goal2-engine-open', daemon=True)
        self.thread.start()


class _Handle:
    """[designed: T160] The engine process that serves a job, as the job's `process` (Popen's lifecycle methods);
    before the process exists, it has no pid and is running. A job that ended before any process served it
    reports itself ended (code 0), as the old worker's cancelled preparation did (#254)."""

    def __init__(self, engine):
        self.engine = engine
        self._process = None
        self.unused = False

    @property
    def popen(self):
        if self._process is None and not self.unused:
            self._process = self.engine.process
        return self._process

    def bind(self):
        """The engine's current process serves the job (its match request goes to it)."""
        return self.popen

    @property
    def pid(self):
        return None if self.popen is None else self.popen.pid

    @property
    def returncode(self):
        if self.popen is None:
            return 0 if self.unused else None
        return self.popen.returncode

    def poll(self):
        if self.popen is None:
            return 0 if self.unused else None
        return self.popen.poll()

    def terminate(self):
        if self.popen is not None:
            self.popen.terminate()

    def kill(self):
        if self.popen is not None:
            self.popen.kill()

    def wait(self, timeout=None):
        if self.popen is None:
            return 0 if self.unused else None
        return self.popen.wait(timeout=timeout)


def _reply_failure(kind, value, completed):
    """The error a reply that ends a match without its publication raises."""
    if kind == 'error' and isinstance(value, str):
        return ValueError('Watched worker failed: ' + value)
    if kind == 'death' and isinstance(value, dict):
        detail = value.get('error') or str(value.get('stderr') or '')[-1500:]
        when = 'after its completion' if completed else 'without completion'
        return ValueError(f'Watched engine exited ({value.get("code")}) {when}: {detail}')
    if completed:
        return ValueError(f'watched engine reply {kind!r} after the completed match')
    return ValueError('invalid watched engine reply')


class WatchedJobs:
    """[designed] One active job per owner; token-scoped reads/cancellation.

    Keep this bridge for the owner's lifetime. start() returns a token; poll(token)
    returns newly observed events. Completion is available as outcome and published
    exactly once by poll. cancel/close bound termination and never publish.
    [designed: T160] The match plays in the owner's engine process (MatchEngine); `command` replaces the
    engine's command line for a process it starts.
    """
    KIND = 'watched'

    def __init__(self, owner, *, command=None):
        if getattr(owner, '_watched_jobs', None) is not None:
            raise ValueError('active game already has a watched bridge')
        owner._watched_jobs = self
        self._setup(owner, WatchedPublication(owner), command)

    def _setup(self, owner, publication, command):
        self.owner = owner
        self.publication = publication
        self.command = None if command is None else list(command)
        self.token = None
        self.outcome = None
        self.events = []
        self.closed = False
        self._active = False
        self._match = None
        self._handle = None
        self._preparing = None
        self.shared = MatchEngine.join(owner, self)

    @property
    def busy(self):
        return self._active

    @property
    def process(self):
        """The engine process serving the active job (a _Handle), or None."""
        return self._handle if self._active else None

    def start(self, fixture, *, reference_seed=None, delay_byte=None, record_draws=False, frames=False,
              bench=False, prompts=False):
        if type(frames) is not bool or type(bench) is not bool or type(prompts) is not bool:
            raise ValueError('frames, bench and prompts must be boolean')
        if prompts and not bench:
            # [designed: T167, #541] the player prompts are answered by the watching player, as the bench is
            raise ValueError('the player prompts need the bench (bench=True)')
        if bench and not frames:
            # [designed: #316] The original takes the player's Enter in play at a pitch sample
            # (_drive_match asks pause_now there), so without them a pause could never be placed.
            raise ValueError('the bench needs the pitch samples (frames=True)')
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
        self._engine_done = False
        self._complete = None
        self._completion_thread = None
        self._completion_work = None
        # [designed: T102] The bench: the decision waiting for the player's answer, the decisions
        # asked and answered so far and the engine's reports.
        self._bench = bench
        self._prompts = prompts
        self.waiting = None
        self._asked = 0
        self._decisions = 0
        self._pause_pending = False
        self.dropped_pauses = 0
        self.reports = []
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
        # [designed: T152, #496] the engine runs under PyPy 3.11 (engine_python), chosen here at the start,
        # so a missing PyPy fails this start with its reason, never the window that holds the bridge
        from goal2.game.engine_python import worker_command
        command = worker_command(ENGINE) if self.command is None else list(self.command)
        self.interpreter = command[0]
        shared = self.shared
        shared.engine.command = command
        match = _Match()
        shared.claim(match)
        self._match = match
        self._active = True
        self._sent = False
        self._handle = _Handle(shared.engine)
        self._request = dict(fixture=job.fixture, frames=self._frames_enabled, bench=self._bench,
                             prompts=getattr(self, '_prompts', False),
                             options=dict(reference_seed=reference_seed, delay_byte=delay_byte,
                                          record_draws=record_draws))
        if shared.needs_open(job.state, self._template):
            self._preparing = _Preparation(shared, job.state, self._template)
        else:
            self._send_match()

    def _send_match(self):
        """[designed: #254; T160] The match request, on the owner's thread. It never starts a process there (which
        would send it the game on this thread): an engine that ended since it took the game fails the start."""
        process = self.shared.engine.process
        if self._match.replies or process is None or process.poll() is not None:
            self._ended_before_match()
        request = self._request
        try:
            self.shared.engine.match(self.KIND, request['fixture'], options=request['options'],
                                     frames=request['frames'], bench=request['bench'],
                                     prompts=request.get('prompts', False))
        except OSError as exc:
            self._ended_before_match(exc)
        self._handle.bind()
        self._sent = True

    def _ended_before_match(self, error=None):
        """[designed: T160] The engine refused the game, or ended, before the match was asked: its reply says why."""
        if self._match.ended.wait(DEATH_WAIT) and self._match.replies:
            raise _reply_failure(*self._match.replies.popleft(), False) from error
        if error is not None:
            raise error
        raise ValueError('the engine process ended before the match was asked')

    def _launch(self):
        """[designed: #254] On the owner's thread, once the game is sent: the match request."""
        preparing = self._preparing
        if preparing is not None:
            if preparing.thread.is_alive():
                return
            preparing.thread.join()
            if preparing.error is not None:
                if preparing.engine_ran:
                    # [designed: T160] the game's write failed because the engine ended: its end says why
                    self._ended_before_match(preparing.error)
                raise preparing.error
            self._preparing = None
        self._send_match()

    def _check_token(self, token):
        if token != self.token or not self.busy:
            raise ValueError('stale or consumed watched job token')

    def _check_owner(self):
        if (self.owner.state is not self._original or self.owner.state != self._snapshot
                or self.owner.template_bytes != self._template):
            raise ValueError('watched job is stale; active game changed')

    def poll(self, token):
        self._check_token(token)
        new = []
        try:
            self._check_owner()
            if not self._sent:
                self._launch()
                return new
            replies = self._match.replies
            for _ in range(REPLY_BUDGET):
                if not replies:
                    break
                kind, value = replies.popleft()
                if self._complete is not None:
                    raise _reply_failure(kind, value, True)
                if kind == 'event' and isinstance(value, Event):
                    value = _event(asdict(value))
                    self.events.append(value)
                    new.append(copy.deepcopy(value))
                    if self._bench and value.kind == 'decision' and (
                            value.data.get('context') in BENCH_CONTEXTS
                            or (self._prompts and value.data.get('context') in PROMPT_CONTEXTS)):
                        if self.waiting is not None:
                            raise ValueError('bench decision before the previous was answered')
                        self.waiting = copy.deepcopy(value)
                        self._asked += 1
                        if value.data['context'] == 'pause':
                            self._pause_pending = False
                elif kind == 'decision' and self._bench and isinstance(value, dict):
                    # [designed: T159] The engine names the decision it waits on: the bench decision just observed.
                    if value.get('decision') != self._asked - 1 or not self.events or value.get('event') != self.events[-1]:
                        raise ValueError('bench decision reply differs from the observed decision')
                elif kind == 'answered' and self._bench and isinstance(value, dict) and len(self.reports) < self._decisions:
                    self.reports.append(_report(value))
                elif kind == 'pause_dropped' and self._bench and self._pause_pending and type(value) is int:
                    # [designed: #316] The original could not take the Enter (the match is over,
                    # or the shoot-out): the next Enter is sent again.
                    self._pause_pending = False
                    self.dropped_pauses += 1
                elif kind == 'complete' and isinstance(value, WatchedOutcome):
                    if tuple(self.events) != value.events:
                        raise ValueError('watched completion differs from live event stream')
                    self._complete = value
                else:
                    raise _reply_failure(kind, value, False)
            if self._complete is not None and not replies:
                # [designed: T160] The engine's `complete`, after every event of the match, ends it; the process
                # stays up for the next match.
                self._engine_done = True
                self._maybe_publish(token)
            return new
        except Exception as exc:
            self._fail(token)
            raise ValueError(f'Invalid watched worker IPC: {exc}') from exc

    @property
    def engine_complete(self):
        """[designed] Valid transcript received; presentation may still own pending state."""
        return getattr(self, '_engine_done', False)

    def _maybe_publish(self, token):
        if not self._engine_done:
            return
        if self._frames_enabled:
            if self._match.frames:
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
        """[designed] Decode <=32 samples; caller owns returned poses.

        Canonical poll must run first. A frame ahead of that poll's event watermark
        waits in the queue; after canonical completion it is an error.
        Returned frames require cumulative acknowledgement after actual consumption.
        """
        self._check_token(token)
        if not self._frames_enabled:
            raise ValueError('pitch frames were not enabled')
        try:
            self._check_owner()
            frames = self._match.frames
            new = []
            for _ in range(FRAME_POLL_BUDGET):
                if not frames:
                    break
                frame = frames[0]
                validate(frame, self._frame_sequence, self._frame_watermark)
                if frame['watermark'] > len(self.events):
                    if self._engine_done:
                        raise ValueError('pitch frame watermark exceeds canonical events')
                    break
                frames.popleft()
                self._frame_sequence += 1
                self._frame_watermark = frame['watermark']
                new.append(frame)
            self._maybe_publish(token)
            return new
        except Exception as exc:
            self._fail(token)
            raise ValueError(f'Invalid watched pitch IPC: {exc}') from exc

    def ack_frames(self, token, sequence):
        """[designed] Cumulative consumed sequence; duplicate/stale/future acks cannot publish."""
        self._check_token(token)
        if (not self._frames_enabled or type(sequence) is not int
                or not self._frame_ack < sequence < self._frame_sequence):
            raise ValueError('stale or invalid pitch frame acknowledgement')
        self._frame_ack = sequence
        if self._bench:
            # [designed: T102] The pacing: the engine may run LEAD samples past this one.
            self._command(token, lambda engine: engine.ack(sequence))

    def _command(self, token, send):
        """[designed: T102; T160] One request to the running match, on the engine's pipe."""
        try:
            send(self.shared.engine)
        except Exception as exc:
            self.cancel(token)
            raise ValueError(f'Invalid watched command: {exc}') from exc

    def frames_drained(self):
        """[designed: T102] Every pitch sample the engine has sent so far has been read."""
        return not self._match.frames

    def pause(self, token):
        """[designed: T102] The player's Enter in play: the original takes it at its next key poll
        and asks a `pause` decision. One request at a time; none while a decision waits. A request
        the original could not take is reported back (`dropped_pauses`) and frees the next one
        [designed: #316]. Returns whether it was sent."""
        self._check_token(token)
        if not self._bench:
            raise ValueError('the bench was not enabled')
        if self.waiting is not None or self._pause_pending or self._engine_done or not self._sent:
            return False
        self._command(token, lambda engine: engine.pause())
        self._pause_pending = True
        return True

    def answer(self, token, substitutions=(), changes=None):
        """[designed: T102] Answer the waiting bench decision with (off, on) pairs; none plays on.
        The original makes, requests or refuses each pair; `reports` says which. [designed: T180] `changes`
        also carries the bench's positions, marks and own tactics (CHANGES), in the same one answer."""
        self._check_token(token)
        if self.waiting is None:
            raise ValueError('no bench decision is waiting')
        pairs = _pairs(list(substitutions))
        changes = _changes(changes or {})
        decision = self._decisions
        if changes:
            self._command(token, lambda engine: engine.answer(decision, pairs, changes=changes))
        else:
            self._command(token, lambda engine: engine.answer(decision, pairs))
        self._decisions += 1
        self.waiting = None
        # [designed] Publication occurs on the next canonical poll, whose returned
        # events must reach the caller rather than disappear inside acknowledgement.

    def choose(self, token, choice):
        """[designed: T167, #541] Answer the waiting player prompt (`set_piece` or `shootout_order`):
        {'taker': word or None} or {'shootout_order': [words]}. Passed to the kit's `Match.answer` as it is."""
        self._check_token(token)
        if self.waiting is None or self.waiting.data.get('context') not in ('set_piece', 'shootout_order'):
            raise ValueError('no player prompt is waiting')
        choice = _choice(choice)
        if set(choice) != ({'taker'} if self.waiting.data['context'] == 'set_piece' else {'shootout_order'}):
            raise ValueError('the answer is for another prompt')
        decision = self._decisions
        self._command(token, lambda engine: engine.answer(decision, choice=choice))
        self._decisions += 1
        self.waiting = None

    def _release(self):
        if self._handle is not None and self._handle._process is None:
            self._handle.unused = True
        if self._match is not None:
            self.shared.release(self._match)
        if getattr(self, '_pitch_owns_pending', False):
            self.owner.match_pending = False
            self._pitch_owns_pending = False
        self._active = False
        self._preparing = None
        self._completion_thread = None
        self._completion_work = None

    def _kill(self):
        """End the engine process; its reader reports the end (a death) to the attached match."""
        self._handle.bind()
        process = self.shared.engine.process
        if process is not None:
            process.kill()

    def cancel(self, token):
        self._check_token(token)
        # [designed: #254] Invalidate first; a job whose game is still being encoded, or whose
        # engine has not answered, stays owned and busy until cancellation can reap it.
        self.publication.cancel()
        preparing = self._preparing
        if preparing is not None and preparing.thread.is_alive():
            preparing.cancelled = True
            preparing.thread.join(0.5)
            if preparing.thread.is_alive() and preparing.phase == 'open':
                # [designed: T160] An engine that does not take the game is ended; that ends the write.
                self._kill()
            preparing.thread.join(0.5)
            if preparing.thread.is_alive():
                raise subprocess.TimeoutExpired('watched input preparation', 1.0)
        match = self._match
        if self._sent and not match.ended.is_set():
            try:
                self.shared.engine.cancel()
            except OSError:
                pass
            if not match.ended.wait(CANCEL_WAIT):
                self._kill()
                if not match.ended.wait(DEATH_WAIT):
                    raise subprocess.TimeoutExpired('match engine cancellation', CANCEL_WAIT + DEATH_WAIT)
        # [designed: #254] Completion starts only after the engine's `complete`, so these
        # bounded waits cannot overlap a running match.
        thread = getattr(self, '_completion_thread', None)
        if thread is not None:
            thread.join(0.5)
            if thread.is_alive():
                thread.join(0.5)
            if thread.is_alive():
                raise subprocess.TimeoutExpired('watched completion preparation', 1.0)
        self._release()

    def _fail(self, token):
        """[designed: T160] End a failed match. A reply can fail it while its completion is being prepared (the
        engine's end after its `complete`); that preparation can no longer publish, and the failure waits for it
        (cancel_and_reap, #311) so that the caller sees the failure, not the wait's timeout."""
        if getattr(self, '_completion_thread', None) is not None:
            self.cancel_and_reap(token)
        else:
            self.cancel(token)

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
        self._leave()

    def _leave(self):
        """[designed: T160] The owner's engine process ends with its last bridge (#417)."""
        shared = getattr(self, 'shared', None)
        if shared is not None:
            self.shared = None
            shared.leave(self.owner, self)
