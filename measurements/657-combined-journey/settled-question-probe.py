"""#659 complete dynamic key actions retain their readable size after questions."""
import unittest
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel
from PySide6.QtTest import QTest
from goal2.tests import requires
from goal2.tests import test_ui_replay_t181 as replay
from goal2.desktop import fixed_page


@requires.need(modules=('PySide6',),**requires.HALFTIME)
class DynamicHint(unittest.TestCase):
    def check(self, helper):
        helper.app.processEvents();QTest.qWait(20);helper.app.processEvents()
        window,pitch=helper.window,helper.pitch
        self.assertEqual(fixed_page.problems(window),[])
        self.assertGreaterEqual(pitch.enter_hint.width()+1,pitch.enter_hint.minimumSizeHint().width())
        for label in pitch.enter_hint.findChildren(QLabel):
            self.assertGreaterEqual(label.width()+1,label.minimumSizeHint().width(),label.text())

    def test_replay_save_and_commentary_hints_resize_at_each_native_fractional_size(self):
        for width,height in ((1440,900),(1800,1125),(2110,1213)):
            with self.subTest(size=(width,height)):
                helper=replay.ReplayScreens();helper.setUp()
                try:
                    helper.window.resize(width,height);helper.app.processEvents()
                    helper.goal();self.assertEqual(helper.pitch.stop_box.kind,'replay');self.check(helper)
                    helper.pitch.answer_stop_box(Qt.Key.Key_N)
                    self.assertEqual(helper.pitch.stop_box.kind,'save-goal');self.check(helper)
                    helper.pitch.answer_stop_box(Qt.Key.Key_N);self.check(helper)
                    helper.pitch.toggle_commentary();self.assertTrue(helper.controller.commentary_paused);self.check(helper)
                    helper.pitch.toggle_commentary();self.assertFalse(helper.controller.commentary_paused);self.check(helper)
                finally:helper.doCleanups()
