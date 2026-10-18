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
from goal2.desktop.match_view import Display, completion, MAX_PACKET, MAX_JOURNAL
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

    def start(self, **options):
        # [designed] No wall-clock delay; record the accepted original RNG transcript.
        options = {'delay_byte':0, 'record_draws':True, **options}
        if getattr(self.model, 'match_pending', False):
            raise ValueError('A match is already running')
        if importlib.util.find_spec('pygame') is None:
            raise ValueError("Watch requires pygame-ce: python3 -m pip install '.[desktop,watched,match-view]'")
        if importlib.util.find_spec('unicorn') is None:
            raise ValueError("Watch requires Unicorn: python3 -m pip install '.[watched]'")
        pending = self.fixture()
        self.close_viewer()
        try:
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
            self.send('start', [self.model.goaldat.country_names[w] for w in (pending.side_a,pending.side_b)])
            command = self.viewer_command or [sys.executable, '-m', 'goal2.desktop.pygame_viewer']
            self.process = subprocess.Popen(list(command) + [str(self.directory), self.token],
                cwd=Path(__file__).resolve().parents[2], stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL, stderr=self.errors)
            self.engine_token = self.engine.start(Fixture(pending.side_a,pending.side_b,int(pending.fixture_id.split(':')[1])), **options)
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
                if (set(value) != {'token','kind','sequence','digest'} or type(value['sequence']) is not int
                        or not 0 <= value['sequence'] <= self.display.sequence
                        or value['digest'] != self.digests[value['sequence']]):
                    raise ValueError('invalid viewer acknowledgement')
                if self.last_status and value['sequence'] < self.last_status['sequence']:
                    raise ValueError('stale viewer acknowledgement')
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
