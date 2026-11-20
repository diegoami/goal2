"""[designed: T170ad/#814] S17 over an explicitly supplied retained native Match.

The owner supplies decision, goal, completion and failure consumers. This leaf
does not manufacture current stopped cards, answers, a career or publication.
"""
from copy import deepcopy
import time
from types import SimpleNamespace

from goal2.desktop.match_view import Display, SPEEDS
from goal2.desktop.watched import pitch_identity
from goal2.game.native_driver import NativeMatchDriver
from goal2.ui.kits import compute
from goal2.ui.s17_pitch import HANG_ON, REQUESTED, PitchScreen


class NativePitchController:
    """Presentation adapter; the native driver alone consumes its reply queue."""

    def __init__(self, model, native, connection=None):
        view = native.controller.view
        if view is None or native.status not in ('prematch', 'handed_off'):
            raise ValueError('native pitch needs the verified pre-match handoff')
        self.pending = native.fixture
        state = view.display_state(model.state)
        identity = pitch_identity(SimpleNamespace(state=state, goaldat=model.goaldat), self.pending)
        from goal2.engine.original_match.image import Image
        image = Image.from_memory_component(state.mem)
        self.kits = compute(lambda off: image.rd(off, 1), *view.sides)
        self.display = Display('native-pitch')
        self.display.accept(['native-pitch', 0, 'start', identity])
        self.display.accept(['native-pitch', 1, 'pitch', {'rate': SPEEDS[3][1]}])
        self.driver = NativeMatchDriver(native, connection)
        self.note = ''; self.error = None; self.finished = False
        self.goal = self.notice = None
        self._seen = 0; self._goal_seen = 0; self._notice_seen = 0
        self._reading = False; self.covered = False
        self._dropped = 0; self._bench_requested = False

    @property
    def quick(self): return self.driver.quick

    @property
    def running(self): return self.driver.status not in ('lost', 'closed', 'resumed')

    @property
    def commentary_paused(self): return self._reading

    @commentary_paused.setter
    def commentary_paused(self, value):
        self._reading = bool(value)
        self._hold()

    def _hold(self):
        self.driver.set_held(self._reading or self.covered or self.goal is not None or self.notice is not None)

    def tick(self, now):
        self._hold()
        frame = self.driver.tick(now)
        # Canonical frame watermarks include the pre-match prefix. Keep them
        # intact; Display is a renderer, not a second causal stream validator.
        if frame is not None:
            self.display.frame = frame
        for event in self.driver.events[self._seen:]:
            rendered = deepcopy(event)
            rendered['score'] = list(rendered['score'])
            self.display.accept(['native-pitch', self.display.sequence, 'event', rendered])
        self._seen = len(self.driver.events)
        shown = self.shown()
        while self._notice_seen < len(shown) and self.notice is None:
            event = shown[self._notice_seen]; self._notice_seen += 1
            if (not self.quick and event['kind'] == 'substitution'
                    and event['data'].get('team') == 1 - self.display.managed):
                self.notice = deepcopy(event)
        if self.driver.dropped_pauses > self._dropped:
            self._dropped = self.driver.dropped_pauses
            self._bench_requested = False
            self.note = self.driver.message
        if self.driver.waiting is not None:
            self._bench_requested = False
            if self.note == REQUESTED: self.note = ''
        if self.driver.message: self.note = self.driver.message
        if self.driver.status == 'lost':
            self.error = self.driver.error; self.finished = True
        self._hold()
        return frame is not None

    def painted(self, sequence):
        if not self.driver.painted(sequence): return
        frame = self.display.frame
        if self.quick or frame is None: return
        bound = frame['watermark'] - self.driver.event_base
        events = self.driver.events
        while self._goal_seen < min(bound, len(events)) and self.goal is None:
            event = events[self._goal_seen]; self._goal_seen += 1
            if event['kind'] == 'goal' and event['data'].get('player'):
                self.goal = deepcopy(event)
        self._hold()

    def dismiss_goal(self):
        self.goal = None; self._hold()

    def dismiss(self):
        self.notice = None; self._hold()

    def step_speed(self, step):
        self.driver.step_speed(step)
        self.display.pitch_rate = SPEEDS[self.driver.speed][1]

    def quick_result(self):
        if self.goal is not None or self.notice is not None or self._reading: return
        self.driver.quick_result(); self.note = HANG_ON

    def request_bench(self):
        if self._reading or self.covered or self.goal is not None or self.notice is not None: return False
        sent = self.driver.request_pause()
        if sent: self._bench_requested = True; self.note = REQUESTED
        return sent

    def shown(self): return self.driver.shown()

    def frame_or_event(self):
        frame = self.display.frame
        if frame is not None and not self.quick: return frame['minute'], frame['score']
        shown = self.shown()
        return (shown[-1]['minute'], shown[-1]['score']) if shown else (0, [0, 0])

    def cancel(self):
        self.driver.close(); self.finished = True


class NativePitchScreen(PitchScreen):
    """Existing pitch keys/layout, explicit native decision and resume ownership.

    Callbacks receive (screen, immutable-copy event/waiting) except completion
    receives only screen. The completion consumer must call resume_native()
    explicitly, then transfer/close the continuing NativeSeasonOwner itself.
    """

    def __init__(self, window, model, native, *, on_decision, on_goal,
                 on_complete, on_failure, connection=None):
        callbacks = (on_decision, on_goal, on_complete, on_failure)
        if not all(callable(c) for c in callbacks):
            raise ValueError('native pitch requires every owner callback')
        self.on_decision, self.on_goal, self.on_complete, self.on_failure = callbacks
        self._delivered = None; self._goal_delivered = None
        self._completed = False; self._failed = False; self._closed = False
        controller = NativePitchController(model, native, connection)
        try: super().__init__(window, model, controller)
        except Exception:
            controller.cancel(); raise
        window.destroyed.connect(self.closing)

    def _failure(self, message):
        self.controller.error = message
        self.closing()
        if self._failed: return
        self._failed = True
        self.note.setText(f'The native match stopped: {message}')
        self.on_failure(self, message)

    def tick(self):
        if self._closed: return
        c = self.controller
        c.covered = self.window_.current() is not self
        try:
            if self.replay is not None:
                self.replay_tick(time.monotonic()); return
            if c.tick(time.monotonic()): self.pitch.update()
            self.refresh()
            if c.error: return self._failure(c.error)
            if c.driver.status == 'resumed':
                self.timer.stop(); self.ended = True; return
            if c.covered or c.commentary_paused or self.stop_box.open: return
            if c.goal is not None:
                if self._goal_delivered != c.goal:
                    self._goal_delivered = deepcopy(c.goal)
                    self.on_goal(self, deepcopy(c.goal))
                return
            if c.notice is not None: return self.show_notice(c.notice)
            waiting = c.driver.waiting
            if waiting is not None:
                if self._delivered != waiting['decision']:
                    self._delivered = waiting['decision']
                    self.on_decision(self, waiting)
                return
            if c.driver.status == 'complete' and not self._completed:
                self._completed = True; self.on_complete(self)
        except Exception as exc:
            if self._failed: raise
            self._failure(f'{type(exc).__name__}: {exc}')

    def answer_native(self, decision, answer):
        waiting = self.controller.driver.waiting
        if waiting is None or type(decision) is not int or waiting['decision'] != decision:
            raise ValueError('native screen answer needs its current decision')
        self.controller.driver.answer(answer)

    def release_goal(self):
        if self.controller.goal is None: raise ValueError('no painted native goal is held')
        self.controller.dismiss_goal(); self._goal_delivered = None

    def resume_native(self):
        self.controller.driver.resume()

    def closing(self):
        if self._closed: return
        self._closed = True
        super().closing()
