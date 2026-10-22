"""[designed: T66] Qt-polled engine/viewer ownership; viewer never receives state."""
from contextlib import ExitStack
from dataclasses import asdict
from functools import cache
import importlib.util
import errno
import json
import os
from pathlib import Path
import secrets
import subprocess
import sys
import tempfile
import time
from goal2.desktop.match_view import Display, completion, MAX_PACKET, MAX_JOURNAL, PLAYBACK_RATE, MAX_BACKLOG
from goal2.game.watched_jobs import WatchedJobs
from goal2.engine.original_match import Fixture
from goal2.engine.quick_engine import QuickEngineError


@cache
def _status_api():
    """[designed: #254] Bind pointer-sized native APIs once, only when Windows reads."""
    import ctypes
    from ctypes import wintypes
    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    create = kernel.CreateFileW
    create.argtypes = (wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD,
                      ctypes.c_void_p, wintypes.DWORD, wintypes.DWORD, wintypes.HANDLE)
    create.restype = wintypes.HANDLE
    close = kernel.CloseHandle
    close.argtypes = (wintypes.HANDLE,)
    close.restype = wintypes.BOOL
    return create, close


def _open_status(path):
    """[designed: #254] A read-only snapshot must allow the viewer's atomic replacement."""
    if os.name != 'nt':
        return path.open('rb')
    import ctypes
    import msvcrt
    create, close = _status_api()
    # [confirmed: docs/evidence/fix254/native-before-01/report.json and its Win32 reference]
    # Read-only access with read/write/delete sharing permits an atomic replacement.
    read_access = 0x80000000  # GENERIC_READ
    share_mode = 0x1 | 0x2 | 0x4  # FILE_SHARE_READ | FILE_SHARE_WRITE | FILE_SHARE_DELETE
    open_existing, normal_attributes = 3, 0x80
    handle = create(os.fspath(path), read_access, share_mode, None, open_existing, normal_attributes, None)
    if handle == ctypes.c_void_p(-1).value:
        raise ctypes.WinError(ctypes.get_last_error())
    try:
        descriptor = msvcrt.open_osfhandle(handle, os.O_RDONLY | os.O_NOINHERIT)
    except BaseException:
        close(handle)
        raise
    # [confirmed: https://docs.python.org/3/library/msvcrt.html] The descriptor owns the handle.
    try:
        msvcrt.setmode(descriptor, os.O_BINARY)
        return os.fdopen(descriptor, 'rb')
    except BaseException:
        os.close(descriptor)
        raise


def pitch_identity(model, fixture):
    """[designed: T94; confirmed: F002 R011 DS:69A8 via goal2.game.roles] The viewer's start
    packet: both countries, each squad player's one-letter role code (the managed country's
    current twenty, pool exchanges included), the managed side and the fixture's kind."""
    from goal2.game import roles
    state = model.state;codes = roles.tables(state)[0]
    def squad(country):
        if country == state.managed_country:
            return list(state.managed_squad)
        record = state.countries[country]
        return [int.from_bytes(record[2 * i:2 * i + 2], 'little') for i in range(20)]
    words = squad(fixture.side_a) + squad(fixture.side_b)
    sides = (fixture.side_a, fixture.side_b)
    return {'countries': [model.goaldat.country_names[c] for c in sides],
            'roles': {str(w): codes[state.players[w][6]] for w in words if state.players[w][6] < 14},
            'managed': sides.index(state.managed_country) if state.managed_country in sides else None,
            'kind': 'Friendly' if fixture.kind == 1 else 'Qualifier'}


# [designed: #311] How long close() keeps cancelling a job that is still preparing.
CLOSE_DEADLINE = 30


class WatchedController:
    def __init__(self, model, *, engine_command=None, viewer_command=None):
        self.model = model
        self.engine = WatchedJobs(model, command=engine_command)
        self.viewer_command = viewer_command
        self.process = None
        self.folder = None
        self.stream = self.errors = self.directory = None
        self.token = None
        self.display = None
        self.last_status = None
        self._pending_owned = False
        self._status_read_deadline = None

    @property
    def busy(self):
        return self.engine.busy

    def fixture(self):
        """[designed] Unsupported watching is explicit even with an unconfirmed draft."""
        campaign = self.model.state.campaign
        pending = campaign.next_fixture if campaign else None
        if pending is None or pending.kind != 1:
            raise ValueError('Watch supports scheduled friendlies only; pending qualifiers are unsupported')
        return pending

    def start(self, *, frames=True, playback_rate=PLAYBACK_RATE, **options):
        # [designed] No wall-clock delay; record the accepted original RNG transcript.
        options = {'delay_byte':0, 'record_draws':True, **options}
        if type(frames) is not bool:
            raise ValueError('frames must be boolean')
        if getattr(self.model, 'match_pending', False):
            raise ValueError('A match is already running')
        if importlib.util.find_spec('pygame') is None:
            raise ValueError("Watch requires pygame-ce: python3 -m pip install '.[desktop,watched,match-view]'")
        if importlib.util.find_spec('unicorn') is None:
            raise ValueError("Watch requires Unicorn: python3 -m pip install '.[watched]'")
        pending = self.fixture()
        self.close_viewer()
        try:
            self.frames_enabled = frames
            self.token = secrets.token_hex(24)
            self.display = Display(self.token)
            self.folder = tempfile.TemporaryDirectory(prefix='goal2-viewer-')
            self.directory = Path(self.folder.name)
            self.stream = (self.directory / 'display').open('wb')
            self.errors = (self.directory / 'errors').open('w+b')
            self.bytes_sent = 0
            self.digests = {0: self.display.digest()}
            self.started = time.monotonic()
            self.last_status = None
            self._status_read_deadline = None
            self.frame_ack = -1
            self.frame_receipts = {}
            # [designed: T94] Only the pitch draws codes and colours; text-only watching keeps
            # the two-country start.
            self.send('start', pitch_identity(self.model, pending) if frames else
                      [self.model.goaldat.country_names[w] for w in (pending.side_a,pending.side_b)])
            if frames:
                self.send('pitch', {'rate': playback_rate})
            command = self.viewer_command or [sys.executable, '-m', 'goal2.desktop.pygame_viewer']
            self.process = subprocess.Popen(list(command) + [str(self.directory), self.token],
                cwd=Path(__file__).resolve().parents[2], stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL, stderr=self.errors)
            self.engine_token = self.engine.start(Fixture(pending.side_a,pending.side_b,int(pending.fixture_id.split(':')[1])), frames=frames, **options)
            self.model.match_pending = True
            self._pending_owned = True
        except Exception as exc:
            self.close_viewer()
            if isinstance(exc, (OSError, ValueError, QuickEngineError)):
                raise ValueError(f'Cannot start original friendly: {exc}') from exc
            raise

    def send(self, kind, value):
        packet = [self.token, self.display.sequence, kind, value]
        # [designed] JSON copies prevent caller aliases and normalize tuple score fields.
        data = json.dumps(packet, allow_nan=False).encode() + b'\n'
        if len(data) > MAX_PACKET or self.bytes_sent + len(data) > MAX_JOURNAL:
            raise ValueError('viewer presentation exceeds bounded journal')
        self.display.accept(json.loads(data))
        self.digests[self.display.sequence] = self.display.digest()
        self.stream.write(data)
        self.stream.flush()
        self.bytes_sent += len(data)

    def poll(self):
        """[designed] Bounded parent reads; return True once on original publication."""
        if self.process is None:
            return False
        try:
            path = self.directory / 'status'
            if path.exists():
                try:
                    with _open_status(path) as stream:
                        data = stream.read(4097)
                except PermissionError as exc:
                    # [confirmed: #236 main-preflight-01] Native open may lack winerror.
                    winerror = getattr(exc, 'winerror', None)
                    if sys.platform != 'win32' or not (winerror == 5 or
                            (winerror is None and exc.errno == errno.EACCES)):
                        raise
                    # [designed: #236] Defer to Qt; consecutive denial gets <=250ms.
                    now = time.monotonic()
                    if self._status_read_deadline is None:
                        self._status_read_deadline = now + .25
                    if now >= self._status_read_deadline:
                        raise
                    return False
                self._status_read_deadline = None
                if len(data) > 4096:
                    raise ValueError('oversized viewer status')
                value = json.loads(data)
                if (not isinstance(value,dict) or value.get('token') != self.token
                        or value.get('kind') not in ('ready','closed','error')):
                    raise ValueError('malformed or stale viewer status')
                if value['kind'] == 'error':
                    raise ValueError('Pygame viewer failed: ' + str(value.get('message','unknown error')))
                keys = {'token','kind','sequence','digest'}
                # [designed] Initial startup may precede the child parsing pitch configuration.
                pitch_status = self.frames_enabled and 'frame_sequence' in value
                if pitch_status:
                    keys |= {'frame_sequence','frame_digest'}
                if (set(value) != keys or type(value['sequence']) is not int
                        or not 0 <= value['sequence'] <= self.display.sequence
                        or value['digest'] != self.digests[value['sequence']]):
                    raise ValueError('invalid viewer acknowledgement')
                if self.last_status and value['sequence'] < self.last_status['sequence']:
                    raise ValueError('stale viewer acknowledgement')
                if pitch_status:
                    consumed = value['frame_sequence']
                    if type(consumed) is not int:
                        raise ValueError('invalid rendered pitch acknowledgement')
                    receipt = self.frame_receipts.get(consumed)
                    if (consumed < self.frame_ack
                            or consumed > self.display.frame_sequence
                            or (consumed == -1 and value['frame_digest'] is not None)
                            or (consumed >= 0 and (receipt is None or value['frame_digest'] != receipt[0]
                                                  or value['sequence'] < receipt[1]))):
                        raise ValueError('invalid rendered pitch acknowledgement')
                    if consumed > self.frame_ack:
                        self.engine.ack_frames(self.engine_token, consumed)
                        self.frame_ack = consumed
                        while self.display.frames and self.display.frames[0]['sequence'] <= consumed:
                            self.display.frames.popleft()
                        # [designed] Keep one receipt for repeated status, bounded by outstanding frames.
                        self.frame_receipts = {k:v for k,v in self.frame_receipts.items() if k >= consumed}
                elif self.frames_enabled and value['sequence'] >= 2:
                    raise ValueError('missing rendered pitch acknowledgement')
                self.last_status = value
                if value['kind'] == 'closed':
                    self.cancel()
                    return False
            elif time.monotonic() - self.started > 10:
                raise ValueError('Pygame window did not start within 10 seconds; check SDL display configuration')
            if self.process.poll() is not None:
                raise ValueError('Pygame window exited; check SDL display configuration')
            if self.engine.busy and self.last_status is not None:
                for event in self.engine.poll(self.engine_token):
                    self.send('event', asdict(event))
                if self.frames_enabled and self.engine.busy and len(self.display.frames) <= MAX_BACKLOG-32:
                    from goal2.desktop.pygame_viewer import frame_digest
                    for frame in self.engine.poll_frames(self.engine_token):
                        self.send('frame', frame)
                        self.frame_receipts[frame['sequence']] = (frame_digest(frame), self.display.sequence)
                if not self.engine.busy:
                    self.model.match_pending = False
                    self._pending_owned = False
                    self.send('complete', completion(self.engine.outcome,self.model.goaldat.player_names))
                    return True
            return False
        except Exception:
            self.cancel()
            raise

    def close_viewer(self):
        if self.process is not None:
            if self.process.poll() is None:
                self.process.terminate()
                try:self.process.wait(timeout=.5)
                except subprocess.TimeoutExpired:
                    self.process.kill();self.process.wait(timeout=.5)
        # [designed: #236] Keep ownership/references until every teardown step succeeds.
        with ExitStack() as cleanup:
            for name in ('errors', 'stream'):
                handle = getattr(self, name)
                if handle is not None:
                    cleanup.callback(handle.close)
        if self.folder is not None:
            deadline = time.monotonic() + .5
            while True:
                try:
                    self.folder.cleanup()
                    break
                except PermissionError as exc:
                    remaining = deadline - time.monotonic()
                    if sys.platform != 'win32' or getattr(exc, 'winerror', None) != 32 or remaining <= 0:
                        raise
                    time.sleep(min(.02, remaining))
                    if time.monotonic() >= deadline:
                        raise
        self.process = self.folder = self.stream = self.errors = self.directory = None

    def cancel(self):
        try:
            if self.engine.busy:
                self.engine.cancel(self.engine_token)
            self.close_viewer()
        except Exception:
            # [designed: #236] Engine cancellation may release its lock before viewer deletion.
            if self._pending_owned:
                self.model.match_pending = True
            raise
        if self._pending_owned:
            self.model.match_pending = False
            self._pending_owned = False

    def close(self):
        # [designed: #311; #254] One cancel is bounded and may time out while the job still
        # encodes its input (seen on the Windows runner); close is final, so it cancels again
        # until the job is reaped, and raises only past CLOSE_DEADLINE.
        deadline = time.monotonic() + CLOSE_DEADLINE
        while True:
            try:
                self.cancel()
                break
            except subprocess.TimeoutExpired:
                if time.monotonic() >= deadline:
                    raise
        self.engine.close()
