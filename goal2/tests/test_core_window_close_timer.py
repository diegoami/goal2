"""[designed: T109] Closing the core window stops scheduling polls: the job poll timer too, not only the viewer's.

`closeEvent` stopped `viewer_timer` and waited for the running job, but left `core_timer` (1 ms in live play)
running with the finished job uncollected, so a poll after close ran `finished` on a closed window: after a pose's
step that reopens the pitch viewer, and a following step would be submitted to the pool already shut down.
"""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from goal2.tests import requires

NEEDS = dict(modules=('unicorn', 'PySide6'), files=('e006-r0001-main.sav', 'GOAL.DAT'))


@requires.need(**NEEDS)
class CloseStopsPolling(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from PySide6.QtWidgets import QApplication
        cls.app = QApplication.instance() or QApplication([])

    def test_close_during_a_job_stops_the_poll_timer(self):
        from goal2.desktop.core_model import CoreModel
        from goal2.desktop.core_window import CoreWindow
        folder = tempfile.TemporaryDirectory();self.addCleanup(folder.cleanup)
        model = CoreModel.open(requires.CACHE / 'e006-r0001-main.sav', requires.CACHE / 'GOAL.DAT',
                               Path(folder.name) / 'g.g2core')
        with patch.object(CoreWindow, 'resume_round'):
            w = CoreWindow(model)
        w.show();self.app.processEvents()
        byte = model.team_tactics()['byte']
        self.assertTrue(w.run_core('set_tactic', 1, not byte & 1))
        self.assertTrue(w.core_timer.isActive())
        status = w.status.text()
        w.close()
        self.assertFalse(w.isVisible())
        self.assertFalse(w.core_timer.isActive(), 'a poll after close would act on a closed window')
        self.app.processEvents()
        self.assertEqual(w.status.text(), status, 'the job was collected on the closed window')


if __name__ == '__main__':
    unittest.main()
