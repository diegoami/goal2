"""[designed: T95; accepted vision #266 screen 05; #243 folded] Match preparation."""
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
from goal2.game import roles  # noqa: E402
from goal2.game.session_save import encode  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]


class Preparation(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.model = DesktopModel.open(ROOT / '.cache/e010-r0008-halftime.sav', ROOT / '.cache/GOAL.DAT',
                                       ROOT / '.cache/never-written.g2save', country=13)
        self.window = ManagementWindow(self.model);self.window.resize(1440, 900);self.window.show()
        QTest.qWaitForWindowActive(self.window)
        self.addCleanup(lambda: (self.window.close(), self.window.deleteLater(), self.app.processEvents()))

    def formation(self, words):
        state = self.model.state;_, lines = roles.tables(state)
        return '-'.join(str(sum(1 for w in words if lines[state.players[w][6]] == line)) for line in (1, 2, 3))

    def test_both_elevens_with_formations_and_the_fixture(self):
        w = self.window;state = self.model.state;names = self.model.goaldat.country_names
        fixture = state.campaign.next_fixture;before = encode(state, self.model.template_bytes)
        self.assertEqual(w.prep_title.text(), f'{names[fixture.side_a].upper()} v {names[fixture.side_b].upper()} / FRIENDLY')
        selected = w.selected_ids()
        self.assertEqual([r[0] for r in w.lineup_own.rows], selected)
        self.assertEqual(w.lineup_own.caption, f'GREECE / {self.formation(selected)}')
        other = fixture.side_b if fixture.side_a == 13 else fixture.side_a
        record = state.countries[other];stored = [int.from_bytes(record[2 * i:2 * i + 2], 'little') for i in range(11)]
        self.assertEqual([r[0] for r in w.lineup_other.rows], stored, "the opponent's stored eleven")
        self.assertEqual(w.lineup_other.caption, f'{names[other].upper()} / {self.formation(stored)}')
        codes = roles.tables(state)[0]
        self.assertEqual([r[2] for r in w.lineup_other.rows], [codes[state.players[x][6]] for x in stored])
        # A draft change shows at once and is named as unconfirmed.
        row = state.managed_squad.index(selected[3]);w.table.item(row, 0).setCheckState(Qt.CheckState.Unchecked)
        self.assertEqual(len(w.lineup_own.rows), 10);self.assertIn('Unconfirmed', w.prep_note.text())
        self.assertEqual(encode(self.model.state, self.model.template_bytes), before, 'preparation never changes the game')

    def test_the_chosen_speed_reaches_the_watched_controller(self):
        w = self.window;w.confirm_draft()
        self.assertEqual(w.speed_group.checkedId(), 60, 'Normal keeps the default 60')
        for name, rate in (('Slow', 15), ('Fast', 120), ('Normal', 60)):
            next(b for b in w.speed_buttons if b.text() == name).click()
            w.navigate(0);w.refresh();w.navigate(3)
            self.assertEqual(w.speed_group.checkedId(), rate, 'the choice survives navigation and refresh')
            with patch.object(w.watched, 'start') as start, patch.object(w.watch_timer, 'start'), patch.object(w, 'set_busy'):
                w.start_watched()
            start.assert_called_once_with(playback_rate=rate)
        w.set_busy(True)
        self.assertFalse(any(b.isEnabled() for b in w.speed_buttons), 'the speed is locked while a match runs')
        w.set_busy(False);self.assertTrue(all(b.isEnabled() for b in w.speed_buttons))

    def test_the_country_desk_leads_to_preparation(self):
        w = self.window;w.navigate(0)
        prepare = next(b for b in w.desk_routes if b.text() == 'Prepare match')
        self.assertIs(w.desk_routes[0], prepare);prepare.click()
        self.assertEqual(w.page_stack.currentIndex(), 3)
        self.assertTrue(w.pages[3].isAncestorOf(w.play) and w.pages[3].isAncestorOf(w.watch))


if __name__ == '__main__':
    unittest.main()
