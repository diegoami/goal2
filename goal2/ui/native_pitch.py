"""[designed: T170ad/#814] S17 over an explicitly supplied retained native Match.

The owner supplies decision, goal, completion and failure consumers. This leaf
does not manufacture current stopped cards, answers, a career or publication.
"""
from copy import deepcopy
import time
from types import SimpleNamespace

from PySide6.QtCore import Qt

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
        from goal2.desktop.model import kind_word
        identity['kind'] = kind_word(self.pending.kind, self.pending.stage)
        from goal2.engine.original_match.image import Image
        image = Image.from_memory_component(state.mem)
        self.kits = compute(lambda off: image.rd(off, 1), *view.sides)
        self.display = Display('native-pitch')
        self.display.accept(['native-pitch', 0, 'start', identity])
        self.display.accept(['native-pitch', 1, 'pitch', {'rate': SPEEDS[3][1]}])
        self.driver = NativeMatchDriver(native, connection)
        self.note = ''; self.error = None; self.finished = False
        self.goal = self.notice = None
        self._events = []; self._goal_seen = 0; self._notice_seen = 0
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
        held = self._reading or self.covered or self.goal is not None or self.notice is not None
        if self.driver.held != held: self.driver.set_held(held)

    def tick(self, now):
        self._hold()
        frame = self.driver.tick(now)
        # Canonical frame watermarks include the pre-match prefix. Keep them
        # intact; Display is a renderer, not a second causal stream validator.
        if frame is not None:
            self.display.frame = frame
        events = self.driver.events_since(len(self._events))
        self._events.extend(events)
        for event in events:
            rendered = deepcopy(event)
            rendered['score'] = list(rendered['score'])
            self.display.accept(['native-pitch', self.display.sequence, 'event', rendered])
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
        events = self._events
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

    def shown(self): return self._events[:self.driver.shown_count]

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

    GRID = True  # [designed: T215/T170ad] Explicitly retain S17's cell layout.

    def __init__(self, window, model, native, *, on_decision, on_goal,
                 on_complete, on_failure, connection=None, half_time_controls=False,
                 choice_controls=False, pause_controls=False, opportunity_controls=False,
                 substitution_controls=False):
        callbacks = (on_decision, on_goal, on_complete, on_failure)
        if not all(callable(c) for c in callbacks):
            raise ValueError('native pitch requires every owner callback')
        if type(half_time_controls) is not bool:
            raise ValueError('half_time_controls must be boolean')
        self._half_time_controls = half_time_controls
        if type(choice_controls) is not bool:
            raise ValueError('choice_controls must be boolean')
        self._choice_controls = choice_controls
        if type(pause_controls) is not bool:
            raise ValueError('pause_controls must be boolean')
        self._pause_controls = pause_controls
        if type(opportunity_controls) is not bool:
            raise ValueError('opportunity_controls must be boolean')
        self._opportunity_controls = opportunity_controls
        if type(substitution_controls) is not bool:
            raise ValueError('substitution_controls must be boolean')
        self._substitution_controls = substitution_controls
        self.on_decision, self.on_goal, self.on_complete, self.on_failure = callbacks
        self._delivered = None; self._goal_delivered = None
        self._completed = False; self._failed = False; self._closed = False
        self.review = None
        self.choice = None
        self.opportunity = None
        controller = NativePitchController(model, native, connection)
        try: super().__init__(window, model, controller)
        except Exception:
            controller.cancel(); raise
        window.destroyed.connect(self.closing)

    def _failure(self, message):
        self.controller.error = message
        if self.review is not None:
            self.review.failed(message)
        if self.choice is not None:
            self.choice.dismiss()
        self.closing()
        if self._failed: return
        self._failed = True
        self.note.setText(f'The native match stopped: {message}')
        self.on_failure(self, message)

    def tick(self):
        if self._closed: return
        c = self.controller
        c.covered = self.window_.current() is not self or self.opportunity is not None
        try:
            if self.replay is not None:
                self.replay_tick(time.monotonic()); return
            if c.tick(time.monotonic()): self.pitch.update()
            self.refresh()
            if c.error: return self._failure(c.error)
            if self.review is not None:
                if self.review.update_review():
                    self.review = None
                return
            if self.choice is not None:
                if self.choice.update():
                    self.choice = None
                return
            if self.opportunity is not None:
                if self.opportunity.update():
                    self.opportunity = None
                return
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
                    context = waiting['event']['data'].get('context')
                    if context == 'post_match':
                        from goal2.ui.native_review import NativeReviewScreen
                        self.review = NativeReviewScreen(self, waiting['decision'])
                        self.window_.push(self.review)
                    elif context == 'half_time' and self._half_time_controls:
                        from goal2.ui.native_half_time import NativeHalfTimeScreen
                        self.review = NativeHalfTimeScreen(self, waiting)
                        self.window_.push(self.review)
                    elif context in ('set_piece', 'shootout_order') and self._choice_controls:
                        from goal2.ui.native_choice import NativeChoiceFlow
                        self.choice = NativeChoiceFlow(self, waiting)
                    elif context == 'pause' and self._pause_controls:
                        from goal2.ui.native_pause import NativePauseScreen
                        self.review = NativePauseScreen(self, waiting)
                        self.window_.push(self.review)
                    elif context == 'substitution_opportunity' and self._opportunity_controls:
                        from goal2.ui.native_opportunity import NativeOpportunityFlow
                        self.opportunity = NativeOpportunityFlow(self, waiting['decision'])
                    elif context == 'substitution' and self._substitution_controls:
                        from goal2.ui.native_half_time import NativeSubstitutionScreen
                        self.review = NativeSubstitutionScreen(self, waiting)
                        self.window_.push(self.review)
                    else:
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

    def handle_key(self, key):
        opportunity = self.opportunity
        if (opportunity is not None and opportunity.phase != 'open' and key != Qt.Key.Key_F1
                and not (opportunity.phase == 'retry' and key in (Qt.Key.Key_Return, Qt.Key.Key_Enter))):
            return True
        return super().handle_key(key)

    def release_goal(self):
        if self.controller.goal is None: raise ValueError('no painted native goal is held')
        self.controller.dismiss_goal(); self._goal_delivered = None

    def resume_native(self):
        self.controller.driver.resume()

    def closing(self):
        if self._closed: return
        self._closed = True
        if self.choice is not None:
            self.choice.close()
        super().closing()
