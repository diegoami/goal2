"""[designed: T109] One acknowledged core pose at a time in the existing pygame pitch window.

The viewer receives presentation records only. Closing or losing it leaves the core at its last wait; the manager
may resume watching or save there. The owned process is reaped before its journal is removed.
"""
import importlib.util
import json
from pathlib import Path
import secrets
import subprocess
import sys
import tempfile
import time

from goal2.desktop.match_view import Display
from goal2.desktop.pygame_viewer import frame_digest
from goal2.desktop.watched import WatchedController, _open_status


class CoreViewer:
    send = WatchedController.send
    close = WatchedController.close_viewer

    def __init__(self, identity, command=None):
        if importlib.util.find_spec('pygame') is None:
            raise ValueError("Watch requires pygame-ce: pip install '.[match-view]'")
        self.process = self.folder = self.stream = self.errors = self.directory = None
        self.token = secrets.token_hex(24)
        self.display = Display(self.token)
        self.bytes_sent = 0
        self.digests = {0: self.display.digest()}
        self.started = time.monotonic()
        self.frame_ack = -1
        self.requests = 0
        self.deadline = None
        self.last_status = None
        self.closed = False
        self.bench_requested = False
        try:
            self.folder = tempfile.TemporaryDirectory(prefix='goal2-core-pitch-')
            self.directory = Path(self.folder.name)
            self.stream = (self.directory / 'display').open('wb')
            self.errors = (self.directory / 'errors').open('w+b')
            self.send('start', identity)
            self.send('pitch', {'rate': 60})
            self.process = subprocess.Popen(list(command or [sys.executable, '-m', 'goal2.desktop.pygame_viewer'])
                + [str(self.directory), self.token], cwd=Path(__file__).resolve().parents[2],
                stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=self.errors)
        except Exception:
            self.close()
            raise

    @property
    def drained(self):
        return self.last_status is not None and self.frame_ack == self.display.frame_sequence

    def pose(self, frame, lines):
        if not self.drained and self.display.frame_sequence >= 0:
            raise ValueError('The previous core pose has not been displayed')
        for line in lines:
            self.send('event', dict(kind='commentary', minute=frame['minute'], score=frame['score'], data=line))
        frame = dict(frame, sequence=self.display.frame_sequence + 1, watermark=len(self.display.events))
        self.send('frame', frame)
        self.deadline = time.monotonic() + 10

    def decision(self, state):
        frame = self.display.frame
        self.send('event', dict(kind='decision', minute=frame['minute'] if frame else 0,
                  score=frame['score'] if frame else [0, 0], data={'context': state}))

    def poll(self):
        """Return an Enter request once, after the displayed pose is acknowledged. None while pending; closed
        and failed viewers never advance the core. Transient Windows replacement denial defers to the next timer."""
        path = self.directory / 'status'
        try:
            with _open_status(path) as stream:
                raw = stream.read(4097)
        except FileNotFoundError:
            raw = None
        except PermissionError:
            if sys.platform != 'win32':
                raise
            raw = None
        if raw is not None:
            if len(raw) > 4096:
                raise ValueError('Oversized core viewer status')
            value = json.loads(raw)
            if not isinstance(value, dict) or value.get('token') != self.token:
                raise ValueError('Stale core viewer status')
            if value.get('kind') == 'error':
                raise ValueError('Pitch viewer failed: ' + str(value.get('message')))
            if value.get('kind') not in ('ready', 'closed'):
                raise ValueError('Invalid core viewer status')
            seq, ack = value.get('sequence'), value.get('frame_sequence', -1)
            if (type(seq) is not int or seq not in self.digests or value.get('digest') != self.digests[seq]
                    or type(ack) is not int or not self.frame_ack <= ack <= self.display.frame_sequence):
                raise ValueError('Invalid core viewer acknowledgement')
            if ack >= 0:
                frame = next((f for f in self.display.frames if f['sequence'] == ack), self.display.frame)
                if frame is None or ack != frame['sequence'] or value.get('frame_digest') != frame_digest(frame):
                    raise ValueError('Invalid core pose digest')
                self.display.frame = frame
                while self.display.frames and self.display.frames[0]['sequence'] <= ack:
                    self.display.frames.popleft()
            requests = value.get('requests', 0)
            if type(requests) is not int or requests < self.requests:
                raise ValueError('Invalid core bench request')
            self.bench_requested |= requests > self.requests
            self.requests = requests
            self.frame_ack = ack
            self.last_status = value
            if value['kind'] == 'closed':
                self.closed = True
                return None
            if self.drained:
                self.deadline = None
                if self.bench_requested:
                    self.bench_requested = False
                    return 'bench'
        if self.process.poll() is not None:
            self.closed = True
        if self.last_status is None and time.monotonic() - self.started > 10:
            raise ValueError('Pitch viewer did not start within 10 seconds')
        if self.deadline is not None and time.monotonic() > self.deadline:
            raise ValueError('Pitch viewer did not display the core pose within 10 seconds')
        return None
