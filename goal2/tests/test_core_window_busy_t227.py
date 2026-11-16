"""T227: the window reads no wait from a step that is still running.

[confirmed: package run 43452154714 on main 815c5eaa, the smoke's core_route] `CoreWindow.poll_core` refreshed the round's
controls while the next step already ran on the job thread; `CoreModel.in_round` read `core.wait.kind`, and the core's
wait is None while a step runs (`Core._run` clears it first, goal2/core/runner.py), so the slot raised
`AttributeError: 'NoneType' object has no attribute 'kind'`. The same head passed on its PR: it is a race.
[designed: T227] While a step runs the model answers from the wait it started from. These tests put the core in the
running step's state (its wait None, as `_run` leaves it) and refresh, so the race is visited every time.
"""
import unittest
from unittest.mock import patch

from goal2.tests import requires
from goal2.tests.test_core_in_match_tactics_t224 import NEEDS, _core, watched_live


@requires.need(**NEEDS)
class Model(unittest.TestCase):

    def model(self):
        import tempfile
        from pathlib import Path
        from goal2.desktop.core_model import CoreModel
        watched_live()
        folder = tempfile.TemporaryDirectory();self.addCleanup(folder.cleanup)
        return CoreModel(_core('live'), requires.CACHE / 'GOAL.DAT', Path(folder.name) / 'g.g2core')

    def test_in_round_and_in_save_name_answer_from_the_wait_the_step_started_from(self):
        model = self.model()
        self.assertTrue(model.in_round);self.assertFalse(model.in_save_name)
        wait, model.core.wait = model.core.wait, None        # a step runs: _run cleared the wait
        try:
            self.assertTrue(model.in_round);self.assertFalse(model.in_save_name)
        finally:
            model.core.wait = wait


@requires.need(modules=('unicorn', 'PySide6'), files=('e006-r0001-main.sav', 'GOAL.DAT'), archaeology=True)
class Window(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        from PySide6.QtWidgets import QApplication
        cls.app = QApplication.instance() or QApplication([])

    def test_refreshing_the_round_controls_while_a_step_runs_keeps_them_as_they_were(self):
        import tempfile
        from pathlib import Path
        from goal2.desktop.core_model import CoreModel
        from goal2.desktop.core_window import CoreWindow
        watched_live()
        folder = tempfile.TemporaryDirectory();self.addCleanup(folder.cleanup)
        with patch.object(CoreWindow, 'resume_round'):
            w = CoreWindow(CoreModel(_core('live'), requires.CACHE / 'GOAL.DAT', Path(folder.name) / 'g.g2core'))
        self.addCleanup(w.close)
        w.core_round.state = w.model.round_state()
        w.refresh_round_controls()
        locked = w.core_team_buttons['reposition'].isEnabled(), w.pool_move.isEnabled()
        wait, w.model.core.wait = w.model.core.wait, None
        try:
            with patch.object(type(w.core_jobs), 'busy', new=property(lambda self: True)):
                w.refresh_round_controls()             # raised AttributeError before T227
                self.assertEqual((w.core_team_buttons['reposition'].isEnabled(), w.pool_move.isEnabled()), (False, False))
        finally:
            w.model.core.wait = wait
        w.refresh_round_controls()
        self.assertEqual((w.core_team_buttons['reposition'].isEnabled(), w.pool_move.isEnabled()), locked)


if __name__ == '__main__':
    unittest.main()
