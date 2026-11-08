"""Owner #608: the actionable stopped bench blinks green without moving its contents."""
import unittest
from goal2.tests import requires


@requires.need(modules=('PySide6', 'pygame'), **requires.HALFTIME)
class BenchCue(unittest.TestCase):
    def setUp(self):
        from goal2.tests.test_immediate_bench_t188 import ImmediateBench
        ImmediateBench.setUp(self)
        self.bench.hide()
        self.bench.show()
        self.app.processEvents()

    def green_pixels(self):
        image = self.bench.mode_label.grab().toImage()
        return sum(image.pixelColor(x, y).name() == '#55ff55'
                   for y in range(image.height()) for x in range(image.width()))

    def test_real_timer_blinks_green_without_losing_text_or_moving_roster(self):
        from PySide6.QtTest import QSignalSpy
        from goal2.ui.s19_bench import MAKE_NOW
        self.assertGreater(self.green_pixels(), 0, 'the original legal-stop cue is bright green')
        before = (self.bench.mode_label.geometry(), self.bench.strip.geometry(), self.bench.note.geometry())
        spy = QSignalSpy(self.bench.cue_timer.timeout)
        self.assertTrue(spy.wait(1200), 'the visible cue must actually blink on a Qt timer')
        self.assertEqual(self.green_pixels(), 0)
        self.assertEqual(self.bench.mode_label.text(), MAKE_NOW, 'keep accessible text in the dark phase')
        self.assertEqual(before, (self.bench.mode_label.geometry(), self.bench.strip.geometry(), self.bench.note.geometry()))
        self.assertTrue(spy.wait(1200))
        self.assertGreater(self.green_pixels(), 0)

    def test_hide_close_and_non_actionable_contexts_have_no_cue_timer(self):
        self.assertTrue(self.bench.cue_timer.isActive())
        self.bench.hide()
        self.assertFalse(self.bench.cue_timer.isActive())
        self.bench.show()
        self.assertTrue(self.bench.cue_timer.isActive())
        for mode, context, now, left in [('request', 'pause', False, 5), ('view', 'extra_time', False, 5),
                                         ('now', 'half_time', True, 0)]:
            with self.subTest(mode=mode, left=left):
                self.bench.mode = mode
                self.bench.answer.context = context
                self.bench.answer.now = now
                self.bench.answer.left = left
                self.bench.refresh()
                self.assertFalse(self.bench.cue_timer.isActive())
                self.assertEqual(self.green_pixels(), 0)
        self.bench.mode = 'now'
        self.bench.answer.context = 'half_time'
        self.bench.answer.now = True
        self.bench.answer.left = 5
        self.bench.refresh()
        self.assertTrue(self.bench.cue_timer.isActive())
        self.bench.close()
        self.assertFalse(self.bench.cue_timer.isActive())

    def test_pending_swap_stops_cue_and_confirmed_reply_restores_it(self):
        from goal2.tests.test_immediate_bench_t188 import ImmediateBench
        ImmediateBench.pair(self)
        self.assertEqual(len(self.sent), 1)
        self.assertTrue(self.bench.pending)
        self.assertFalse(self.bench.cue_timer.isActive())
        self.assertEqual(self.green_pixels(), 0)
        ImmediateBench.deliver(self)
        self.assertTrue(self.bench.cue_timer.isActive())
        self.assertIn(self.on, self.bench.answer.eleven)
        self.assertIn('Made:', self.bench.note.text())
        self.assertEqual(len(self.sent), 1)
    def test_refused_swap_restores_the_cue_at_the_still_legal_stop(self):
        from goal2.tests.test_immediate_bench_t188 import ImmediateBench
        ImmediateBench.pair(self)
        self.assertTrue(self.bench.pending)
        self.assertFalse(self.bench.cue_timer.isActive())
        ImmediateBench.deliver(self, refused=True)
        self.assertFalse(self.bench.pending)
        self.assertTrue(self.bench.cue_timer.isActive())
        self.assertIn('Not made:', self.bench.note.text())


if __name__ == '__main__':
    unittest.main()
