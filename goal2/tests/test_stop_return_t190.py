"""Owner #612: real Qt returns and stop statuses; packet tests do not claim engine acceptance."""
import copy
import time
import unittest
from types import SimpleNamespace
from goal2.tests import requires

@requires.need(modules=('PySide6', 'pygame'), **requires.HALFTIME)
class StopReturn(unittest.TestCase):
    def setUp(self):
        from goal2.tests.test_ui_replay_t181 import ReplayScreens
        ReplayScreens.setUp(self)
        self.sent = []
        self.bridge.answer = lambda token, pairs, changes=None: self.sent.append((copy.deepcopy(pairs), copy.deepcopy(changes)))

    def key(self, key, repeat=False):
        from PySide6.QtCore import QEvent, Qt
        from PySide6.QtGui import QKeyEvent
        from PySide6.QtTest import QTest
        if repeat:
            self.app.sendEvent(self.window, QKeyEvent(QEvent.Type.KeyPress, key, Qt.KeyboardModifier.NoModifier, '', True, 1))
        else:
            QTest.keyClick(self.window, key)
        self.app.processEvents()

    def decision(self, context):
        words = self.model.state.managed_squad
        return SimpleNamespace(minute=45, score=[0, 0], data=dict(context=context,
            eleven=words[:11], bench=words[11:], substitutions_now=context!='pause', substitutions_left=5,
            positions=[[w, self.model.state.players[w][6]] for w in words], injured=[words[1]]))

    def stopped(self, context):
        from goal2.ui.s19_bench import BenchAnswer
        from goal2.ui.s15_match_menu import MenuScreen
        decision = self.decision(context)
        self.controller.stop = self.pitch.held = decision
        self.day.bench = BenchAnswer(self.model, decision)
        if context == 'pause':
            return self.day.open_bench(back=lambda: self.day._bench_played(self.pitch))
        self.menu = self.window.push(MenuScreen(self.window, self.day, 'half' if context=='half_time' else 'stop'))
        return self.day.open_bench()

    def test_stop_arrival_consumes_requested_status_at_pause_half_and_injury(self):
        from goal2.ui.s17_pitch import REQUESTED
        for context in ('pause', 'half_time', 'substitution'):
            with self.subTest(context=context):
                self.controller.stop = None
                self.controller.note = REQUESTED
                self.bridge.waiting = self.decision(context)
                self.controller.tick(time.monotonic())
                self.assertIs(self.controller.stop, self.bridge.waiting)
                self.assertNotEqual(self.controller.note, REQUESTED)

    def test_held_stop_cannot_request_another_stop(self):
        self.stopped('pause')
        self.assertFalse(self.controller.request_bench())
        self.assertEqual(self.bridge.pauses, 0)

    def test_failed_request_reports_failure_and_allows_a_later_request(self):
        from goal2.ui.s17_pitch import REQUESTED
        def fail(token): raise ValueError('worker unavailable')
        self.bridge.pause = fail
        self.assertFalse(self.controller.request_bench())
        self.assertIn('worker unavailable', self.controller.note)
        self.assertNotEqual(self.controller.note, REQUESTED)
        self.assertEqual(self.controller.requests, 0)
        self.bridge.pause = lambda token: True
        self.assertTrue(self.controller.request_bench())
        self.assertEqual(self.controller.requests, 1)

    def test_cancel_and_poll_failure_clear_requested_without_publication(self):
        from goal2.ui.s17_pitch import REQUESTED
        self.controller.note = REQUESTED
        def fail(token): raise ValueError('poll failed')
        self.bridge.poll = fail
        self.controller.tick(time.monotonic())
        self.assertIn('poll failed', self.controller.error)
        self.assertNotEqual(self.controller.note, REQUESTED)
        self.assertIsNone(self.controller.outcome)
        self.assertFalse(self.bridge.busy)

    def test_half_and_injury_returns_explain_play_without_advancing(self):
        from PySide6.QtCore import Qt
        for context in ('half_time', 'substitution'):
            with self.subTest(context=context):
                bench = self.stopped(context)
                self.key(Qt.Key.Key_T)
                self.key(Qt.Key.Key_Escape)
                self.assertIs(self.window.current(), bench)
                self.key(Qt.Key.Key_Escape, repeat=True)
                self.assertIs(self.window.current(), bench, 'held Esc must not traverse another screen')
                self.key(Qt.Key.Key_Escape)
                self.assertIs(self.window.current(), self.menu)
                self.menu.highlight(0)
                self.key(Qt.Key.Key_Escape)
                self.assertIs(self.menu.highlighted(), self.menu.play)
                self.assertIn('Play', self.menu.note.text())
                self.assertEqual(self.sent, [], 'Esc alone must not advance a half or discard a choice')
                self.key(Qt.Key.Key_Return)
                self.assertIs(self.window.current(), self.pitch)
                self.assertEqual(self.sent, [([], None)])
                self.sent.clear()

    def test_plain_pause_returns_once_and_repeat_cannot_request_again(self):
        from PySide6.QtCore import Qt
        bench = self.stopped('pause')
        self.key(Qt.Key.Key_T)
        self.key(Qt.Key.Key_Escape)
        self.assertIs(self.window.current(), bench)
        self.key(Qt.Key.Key_Escape)
        self.assertIs(self.window.current(), self.pitch)
        self.assertEqual(self.sent, [([], None)])
        self.key(Qt.Key.Key_Escape, repeat=True)
        self.assertEqual(self.bridge.pauses, 0)
        self.key(Qt.Key.Key_Escape)
        self.assertEqual(self.bridge.pauses, 1, 'a new discrete request is still legitimate')

    def test_mouse_back_and_play_use_the_same_explicit_return(self):
        from PySide6.QtCore import Qt
        from PySide6.QtTest import QTest
        from goal2.ui.screen import Clickable
        bench = self.stopped('half_time')
        back = next(w for w in bench.key_bar.findChildren(Clickable, 'keyItem') if Qt.Key.Key_Escape in w.binding.keys)
        QTest.mouseClick(back, Qt.MouseButton.LeftButton)
        self.app.processEvents()
        self.assertIs(self.window.current(), self.menu)
        self.assertEqual(self.sent, [])
        QTest.mouseClick(self.menu.play, Qt.MouseButton.LeftButton)
        self.app.processEvents()
        self.assertIs(self.window.current(), self.pitch)
        self.assertEqual(self.sent, [([], None)])

    def test_dropped_request_clears_status(self):
        from goal2.ui.s17_pitch import REQUESTED
        self.controller.note = REQUESTED
        self.bridge.dropped_pauses = 1
        self.controller.tick(time.monotonic())
        self.assertNotEqual(self.controller.note, REQUESTED)

    def test_pending_confirmed_and_refused_edits_keep_single_submission(self):
        from PySide6.QtCore import Qt
        from goal2.tests.test_immediate_bench_t188 import ImmediateBench
        # Existing real Qt edit packet setup/delivery, with actual key focus and repeats added.
        self.window.leave()
        ImmediateBench.setUp(self)
        ImmediateBench.pair(self)
        self.key(Qt.Key.Key_Escape)
        self.key(Qt.Key.Key_Return, repeat=True)
        self.assertIs(self.window.current(), self.bench)
        self.assertEqual(len(self.sent), 1)
        ImmediateBench.deliver(self, refused=True)
        self.assertFalse(self.bench.pending)
        self.assertIn('Not made:', self.bench.note.text())
        ImmediateBench.pair(self)
        ImmediateBench.deliver(self)
        self.assertIn('Made:', self.bench.note.text())
        self.assertIn(self.on, self.bench.answer.eleven)
        self.assertEqual(len(self.sent), 2)

@requires.need(modules=('PySide6', 'pygame', 'unicorn'), slow=True, **requires.HALFTIME)
class ActualReturn(unittest.TestCase):
    def test_natural_injury_and_halftime_returns_preserve_the_match(self):
        import tempfile
        from pathlib import Path
        from PySide6.QtCore import QEvent, Qt
        from PySide6.QtGui import QKeyEvent
        from PySide6.QtTest import QTest
        from goal2.desktop import data_setup
        from goal2.ui.window import Window
        from goal2.ui.s17_pitch import REQUESTED, engine_fixture
        from goal2.tests.test_ui_bench_t180 import (FriendlyWalk, app, career, key, PLAY_NEXT)
        from goal2.tests.match_day_policy import play_through_bridge
        from goal2.tests.test_pypy_worker_t152 import pypy
        pypy()
        application = app()
        test = self
        class ReturnWalk(FriendlyWalk):
            def playing(self, pitch):
                super().playing(pitch)
                frame = pitch.controller.display.frame
                if frame is not None and frame['minute'] >= 5 and not self.out.get('plain_requested'):
                    self.out['plain_requested'] = True
                    key(self.window, Qt.Key.Key_Escape)
            def on_bench(self, screen):
                if screen.answer.context == 'pause':
                    controller = self.out['controller']
                    test.assertNotEqual(controller.note, REQUESTED)
                    choices = len(controller.choices)
                    key(self.window, Qt.Key.Key_T)
                    key(self.window, Qt.Key.Key_Escape)
                    test.assertIs(self.window.current(), screen)
                    key(self.window, Qt.Key.Key_Escape)
                    test.assertEqual(type(self.window.current()).__name__, 'PitchScreen')
                    test.assertEqual(len(controller.choices), choices+1)
                    requests = controller.requests
                    application.sendEvent(self.window, QKeyEvent(QEvent.Type.KeyPress, Qt.Key.Key_Escape,
                        Qt.KeyboardModifier.NoModifier, '', True, 1))
                    test.assertEqual(controller.requests, requests)
                    self.out['plain_returned'] = True
                    return
                return super().on_bench(screen)
            def on_menu(self, screen):
                if screen.phase in ('half', 'stop') and screen.phase not in self.out.setdefault('returns', []):
                    self.out['returns'].append(screen.phase)
                    controller = self.out['controller']
                    choices = copy.deepcopy(controller.choices)
                    held = controller.stop
                    key(self.window, Qt.Key.Key_Space)
                    bench = self.window.current()
                    key(self.window, Qt.Key.Key_T)
                    key(self.window, Qt.Key.Key_Escape)
                    test.assertIs(self.window.current(), bench)
                    key(self.window, Qt.Key.Key_Escape)
                    test.assertIs(self.window.current(), screen)
                    screen.highlight(0)
                    QTest.keyClick(self.window, Qt.Key.Key_Escape)
                    test.assertIs(screen.highlighted(), screen.play)
                    test.assertIn('Play', screen.note.text())
                    test.assertIs(controller.stop, held)
                    test.assertEqual(controller.choices, choices)
                    test.assertNotEqual(controller.note, REQUESTED)
                return super().on_menu(screen)
        with tempfile.TemporaryDirectory() as folder:
            model = career()
            count = model.state.match_count
            fixture = model.state.campaign.next_fixture
            window = Window(data_setup.paths(Path(folder)))
            window.show()
            desk = window.open_career(model)
            walk = ReturnWalk('T190-natural-return', window, model)
            try:
                desk.highlight(PLAY_NEXT)
                key(window, Qt.Key.Key_Return)
                walk.run()
                controller = walk.out['controller']
                test.assertIsNone(controller.error)
                test.assertTrue(walk.out.get('plain_returned'))
                test.assertEqual(set(walk.out['returns']), {'half', 'stop'})
                test.assertIn('first_stop', walk.out, 'natural injury stop and substitution were exercised')
                test.assertIn('refused_screen', walk.out)
                test.assertTrue(walk.out['refused_screen']['can_continue'])
                test.assertEqual(model.state.match_count, count+1)
                test.assertTrue(all(not report['requested'] for report in controller.reports))
                other = career()
                other.state = copy.deepcopy(controller.given._snapshot)
                outcome = play_through_bridge(other, controller.choices, fixture=engine_fixture(fixture), wait=1500)
                test.assertEqual(controller.outcome.result, outcome.result)
                test.assertEqual(controller.outcome.events, outcome.events)
                test.assertEqual(controller.outcome.memory, outcome.memory)
                test.assertEqual(model.state, other.state)
            finally:
                window.close()
                window.deleteLater()
                application.processEvents()

if __name__ == '__main__': unittest.main()
