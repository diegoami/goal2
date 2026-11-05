"""[designed: owner #597] Commentary reading pauses presentation and bridge acknowledgements."""
import copy
import os
import time
import unittest

from goal2.tests import requires
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')


@requires.need(modules=('PySide6', 'pygame'), **requires.HALFTIME)
class CommentaryPause(unittest.TestCase):
    def setUp(self):
        from goal2.tests.test_ui_replay_t181 import ReplayScreens
        ReplayScreens.setUp(self)

    def space(self):
        from PySide6.QtCore import Qt
        from PySide6.QtTest import QTest
        QTest.keyClick(self.window, Qt.Key.Key_Space)
        self.app.processEvents()

    def mouse_space(self):
        from PySide6.QtCore import Qt
        from goal2.ui.screen import Clickable
        item = next(w for w in self.pitch.key_bar.findChildren(Clickable, 'keyItem')
                    if Qt.Key.Key_Space in w.binding.keys)
        item.clicked.emit()
        self.app.processEvents()

    def test_space_holds_bridge_poll_events_and_acknowledgements(self):
        self.controller.drawn = 7
        before = (self.bridge.polls, list(self.bridge.acks), self.controller.released)
        self.space()
        self.assertTrue(getattr(self.controller, 'commentary_paused', False))
        for _ in range(3):
            self.controller.tick(time.monotonic() + 100)
            self.pitch.tick()
        self.assertEqual((self.bridge.polls, self.bridge.acks, self.controller.released), before)
        self.assertIn('PAUSED', self.pitch.wait_head.text())

    def test_mouse_resume_rebases_clock_and_restores_controls(self):
        self.space()
        self.controller.display.next_frame = 0
        self.mouse_space()
        self.assertFalse(getattr(self.controller, 'commentary_paused', False))
        self.assertGreater(self.controller.display.next_frame, time.monotonic())
        self.assertEqual(self.pitch.enter_text.text(), 'Bench')
        self.assertTrue(self.pitch.wait_box.isHidden())

    def test_enter_resumes_and_live_game_actions_do_not_bypass_reading_pause(self):
        from PySide6.QtCore import Qt
        from PySide6.QtTest import QTest
        self.space()
        self.pitch.request_bench()
        self.pitch.quick_result()
        self.assertEqual(self.bridge.pauses, 0)
        self.assertFalse(self.controller.quick)
        self.assertEqual(self.pitch.enter_text.text(), 'Resume match')
        QTest.keyClick(self.window, Qt.Key.Key_Return)
        self.app.processEvents()
        self.assertFalse(getattr(self.controller, 'commentary_paused', False))

    def test_replay_pause_holds_the_sample_and_resumes_in_order(self):
        from goal2.tests.test_ui_replay_t181 import frames
        rows = frames(4)
        done = []
        self.pitch.start_replay(rows, lambda: done.append(True))
        first = copy.deepcopy(self.pitch.replay.frame)
        self.pitch.painted(first['sequence'])
        self.space()
        for offset in (10, 20, 30): self.pitch.replay_tick(time.monotonic() + offset)
        self.assertEqual(self.pitch.replay.frame, first)
        self.assertEqual(self.bridge.acks, [])
        self.space()
        drawn = [first]
        while self.pitch.replay is not None:
            self.pitch.replay_tick(time.monotonic() + len(drawn) + 1)
            if self.pitch.replay is not None:
                row = copy.deepcopy(self.pitch.replay.frame)
                drawn.append(row)
                self.pitch.painted(row['sequence'])
        self.assertEqual(drawn, rows)
        self.assertEqual(done, [True])
        self.assertEqual(self.bridge.acks, [])

    def test_space_mouse_cannot_bypass_a_goal_question(self):
        from goal2.tests.test_ui_replay_t181 import ReplayScreens
        ReplayScreens.goal(self)
        self.assertEqual(self.pitch.stop_box.kind, 'replay')
        self.mouse_space()
        self.assertFalse(getattr(self.controller, 'commentary_paused', False))
        self.assertTrue(self.pitch.stop_box.open)
        self.assertIsNotNone(self.controller.goal)

    def test_quick_result_reading_pause_also_holds_publication_polling(self):
        self.controller.quick = True
        self.space()
        polls = self.bridge.polls
        self.controller.tick(time.monotonic() + 100)
        self.assertEqual(self.bridge.polls, polls)
        self.assertFalse(self.controller.finished)
        self.space()
        self.assertTrue(self.controller.quick)


if __name__ == '__main__':
    unittest.main()
