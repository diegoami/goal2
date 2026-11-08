"""[designed: owner #636] Tactics cursor selection has no new game values to decode."""
import unittest
from types import SimpleNamespace
from unittest.mock import Mock
from PySide6.QtWidgets import QApplication
from goal2.ui.squad_card import Row


def screen_class():
    from goal2.ui.s10_team_tactics import TeamTacticsScreen
    return TeamTacticsScreen

class SelectionDoesNotDecode(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def control(self, pending=False):
        rows = [Row(i, (100,100,0)) for i in range(8)]
        for row in rows: row.set(('synthetic line', 'clear', 'set'))
        rows[0].set_on(True)
        # A cursor move has no input changes to decode. Actual full-window controls
        # will additionally spy on model.view, BenchAnswer.card and role decoders.
        return SimpleNamespace(rows=rows, pending=pending, line=0,
            refresh=Mock(side_effect=AssertionError('cursor selection redecoded game/card data')),
            _refresh_hint=Mock())

    def test_selection_only_changes_highlight_and_hint(self):
        screen = self.control()
        before = [row.texts() for row in screen.rows]
        screen_class().choose(screen, 1)
        self.assertEqual(screen.line, 1)
        self.assertEqual([row.on for row in screen.rows], [False,True,False,False,False,False,False,False])
        self.assertEqual([row.texts() for row in screen.rows], before)
        screen.refresh.assert_not_called()
        screen._refresh_hint.assert_called_once_with()

    def test_pending_selection_keeps_all_rows_and_sends_no_change(self):
        screen = self.control(pending=True)
        screen_class().choose(screen, 1)
        self.assertEqual(screen.line, 0)
        self.assertEqual([row.on for row in screen.rows], [True,False,False,False,False,False,False,False])
        screen.refresh.assert_not_called();screen._refresh_hint.assert_not_called()


if __name__ == '__main__':unittest.main(verbosity=2)
