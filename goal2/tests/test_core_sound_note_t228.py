"""T228: the sound's note shows on a host slower than the original's pacing.

[confirmed: Windows CI runs 43452154768 (main 815c5eaa) and 43456751878 (#711)] T223's
`test_the_whistle_is_waited_and_named` failed: every sample of the step saw `sounding` None. `CoreModel.hold` named
the sound only while it waited, and on the slower runner the step's own emulation had already outlasted the
milliseconds asked, so nothing was waited and the stop showed no note: #455's look of a freeze, on a slow PC.
[designed: T228] The sound is named as soon as the core serves its delay. This test makes the step's emulation last
longer than its delays (2 s against the wide shot's 1,753 ms) so the slow host is visited on any host.
"""
import time
import unittest
from unittest.mock import patch

from goal2.tests import requires
from goal2.tests.test_core_delay_t223 import NEEDS, WHISTLE_MS, at_pose
from goal2.tests import test_core_delay_t223 as t223


@requires.need(**(NEEDS | dict(modules=("unicorn", "PySide6"))))
class SlowHost(unittest.TestCase):

    setUpClass = t223.Window.__dict__['setUpClass']
    window = t223.Window.window
    pump = t223.Window.pump

    def test_the_whistle_is_named_while_a_slow_step_runs(self):
        m, w = self.window(at_pose(t223.WIDE - 1))
        self.assertTrue(m.pacing)
        live_step = m.driver.live_step

        def slow(*args, **kwargs):
            result = live_step(*args, **kwargs)
            time.sleep(2.0)                      # the emulation outlasts the delays it served
            return result
        notes = []

        def done():
            notes.append((m.sounding, w.status.text()))
            return not w.core_jobs.busy
        with patch.object(m.driver, 'live_step', slow):
            self.assertTrue(w.run_core("live_step"))
            self.assertTrue(self.pump(w, until=done))
        self.assertIn(["whistle", WHISTLE_MS], m.waited)
        shown = [text for sound, text in notes if sound == "whistle"]
        self.assertTrue(shown and any("whistle" in text for text in shown), notes[-5:])
        self.assertIsNone(m.sounding)
        self.assertNotIn("whistle", w.status.text())

    def test_a_headless_model_names_no_sound(self):
        from goal2.desktop.core_model import CoreModel
        m = CoreModel(t223.load(at_pose(t223.WIDE - 1)), requires.CACHE / "GOAL.DAT", t223.scratch())
        self.assertFalse(m.pacing)
        seen = []
        live_step = m.driver.live_step

        def spy(*args, **kwargs):
            result = live_step(*args, **kwargs)
            seen.append(m.sounding)
            return result
        with patch.object(m.driver, 'live_step', spy):
            m.round_step('live_step')
        self.assertEqual(seen, [None]);self.assertIsNone(m.sounding)


if __name__ == '__main__':
    unittest.main()
