"""[designed: T66] Qt-polled engine/viewer ownership; viewer never receives state."""
from contextlib import ExitStack
from dataclasses import asdict
import importlib.util
import json
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
            self.frame_ack = -1
            self.frame_receipts = {}
            self.send('start', [self.model.goaldat.country_names[w] for w in (pending.side_a,pending.side_b)])
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
                with path.open('rb') as stream:
                    data = stream.read(4097)
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
            self.process = None
        # [designed: T66] Release every acquired resource, including a partial startup.
        with ExitStack() as cleanup:
            if self.folder is not None:
                cleanup.callback(self.folder.cleanup)
                self.folder = None
            for name in ('errors', 'stream'):
                handle = getattr(self, name)
                setattr(self, name, None)
                if handle is not None:
                    cleanup.callback(handle.close)
            self.directory = None

    def cancel(self):
        if self.engine.busy:
            self.engine.cancel(self.engine_token)
        if self._pending_owned:
            self.model.match_pending = False
            self._pending_owned = False
        self.close_viewer()

    def close(self):
        self.cancel()
        self.engine.close()
