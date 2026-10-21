"""[designed: #280] After an original match returns the squad reordered, an unchanged team is not
an unconfirmed draft."""
from pathlib import Path
import unittest
from unittest.mock import patch

from goal2.tests import requires

requires.require(modules=('PySide6',), **requires.HALFTIME)

from PySide6.QtCore import Qt  # noqa: E402
from PySide6.QtTest import QTest  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402
from goal2.desktop.model import DesktopModel  # noqa: E402
from goal2.desktop.window import ManagementWindow  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]


class ReorderedSquad(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.model = DesktopModel.open(ROOT / '.cache/e010-r0008-halftime.sav', ROOT / '.cache/GOAL.DAT',
                                       ROOT / '.cache/never-written.g2save', country=13)
        self.window = ManagementWindow(self.model);self.window.show();QTest.qWaitForWindowActive(self.window)
        self.addCleanup(lambda: (self.window.close(), self.window.deleteLater(), self.app.processEvents()))
        w = self.window;w.confirm_draft()
        # As watched_publication does: the image's squad order changes, the stored eleven does not.
        state = self.model.state;squad = list(state.managed_squad)
        i, j = squad.index(state.starting_eleven[2]), squad.index(state.starting_eleven[8])
        squad[i], squad[j] = squad[j], squad[i];state.managed_squad = squad
        record = bytearray(state.countries[13])
        for k, word in enumerate(squad):
            record[2 * k:2 * k + 2] = word.to_bytes(2, 'little')
        state.countries[13] = bytes(record);self.model.mark_saved()
        w.refresh()

    def test_an_unchanged_team_is_not_a_draft(self):
        w = self.window;state = self.model.state
        self.assertNotEqual(w.selected_ids(), state.starting_eleven, 'the rows are in the new squad order')
        self.assertEqual(w.draft(), (state.starting_eleven, state.captain, state.country_tactics))
        self.assertIn('Confirmed management', w.draft_state.text())
        with patch.object(w.jobs, 'start') as start, patch.object(w.timer, 'start'), patch.object(w, 'set_busy'):
            w.start_match()
        start.assert_called_once()
        self.assertNotIn('Confirm or discard', w.status.text())

    def test_confirm_keeps_the_stored_order_and_a_real_change_is_still_a_draft(self):
        w = self.window;state = self.model.state;stored = list(state.starting_eleven)
        w.confirm_draft();self.assertEqual(self.model.state.starting_eleven, stored)
        bench = next(r for r in range(20) if w.table.item(r, 0).checkState() == Qt.CheckState.Unchecked
                     and w.table.item(r, 0).flags() & Qt.ItemFlag.ItemIsUserCheckable)
        starter = next(r for r in range(20) if w.table.item(r, 0).data(Qt.ItemDataRole.UserRole) == stored[4])
        w.table.item(starter, 0).setCheckState(Qt.CheckState.Unchecked);w.table.item(bench, 0).setCheckState(Qt.CheckState.Checked)
        self.assertIn('Unconfirmed', w.draft_state.text())
        new = w.table.item(bench, 0).data(Qt.ItemDataRole.UserRole)
        self.assertEqual(w.draft()[0], [p for p in stored if p != stored[4]] + [new], 'kept players first, the new one after')


if __name__ == '__main__':
    unittest.main()
