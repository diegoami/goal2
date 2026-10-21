"""[designed: T91; accepted vision #266 screens 02/03/04] The Country desk, Team and Pool pages."""
from pathlib import Path
import unittest

from goal2.tests import requires

requires.require(modules=('PySide6',), **requires.HALFTIME)

from PySide6.QtCore import Qt  # noqa: E402
from PySide6.QtTest import QTest  # noqa: E402
from PySide6.QtWidgets import QApplication, QLabel, QPushButton, QWidget  # noqa: E402
from goal2.desktop.model import DesktopModel  # noqa: E402
from goal2.desktop.player_card import LINE  # noqa: E402
from goal2.desktop.window import ManagementWindow  # noqa: E402
from goal2.game import country_card, player_card  # noqa: E402
from goal2.game.session_save import encode  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]


class Pages(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.model = DesktopModel.open(ROOT / '.cache/e010-r0008-halftime.sav', ROOT / '.cache/GOAL.DAT',
                                       ROOT / '.cache/never-written.g2save', country=8)
        self.window = ManagementWindow(self.model);self.window.resize(1440, 900);self.window.show()
        self.window.activateWindow();QTest.qWaitForWindowActive(self.window)
        self.addCleanup(lambda: (self.window.close(), self.window.deleteLater(), self.app.processEvents()))

    def state(self):
        # The encoded session holds every record, the campaign and the RNG.
        return encode(self.model.state, self.model.template_bytes)

    def test_country_desk_names_both_countries_ranks_and_the_draft(self):
        w = self.window;state = self.model.state;names = self.model.goaldat.country_names
        own = country_card.card(state, 8, self.model.goaldat)
        self.assertEqual(w.desk_own.text().split('\n')[1:], [f"World    {own['world']:>3}", f"{own['continent']:<8} {own['continental']:>3}"])
        fixture = state.campaign.next_fixture
        opponent = fixture.side_b if fixture.side_a == 8 else fixture.side_a
        theirs = country_card.card(state, opponent, self.model.goaldat)
        self.assertEqual(w.desk_opponent.text().split('\n'),
                         [names[opponent].upper(), f"World    {theirs['world']:>3}", f"{theirs['continent']:<8} {theirs['continental']:>3}"])
        ready = sum(1 for p in self.model.view()['players'] if p['availability']['available'])
        self.assertEqual(w.desk_readiness.text(), f'{ready} ready / XI 11')
        captain = w.draft()[1];self.assertTrue(captain)
        self.assertIn(self.model.goaldat.player_names[captain], w.desk_captain.text())
        # Routes go to the existing pages; the card is the T89 card of the displayed country.
        before = self.state()
        for button, index in zip(w.desk_routes, (1, 2, 3)):
            button.click();self.assertEqual(w.page_stack.currentIndex(), index)
        w.navigate(0);w.desk_card.click();self.app.processEvents()
        self.assertTrue(w.country_card_view.isVisible());self.assertEqual(w.country_card_view.card, own)
        self.assertEqual(self.state(), before)

    def test_roster_lists_the_twenty_with_marks_codes_colours_and_captain(self):
        w = self.window;state = self.model.state;goaldat = self.model.goaldat
        view = self.model.view()['players']
        for roster in (w.team_roster, w.country_roster):
            self.assertEqual([r[0] for r in roster.rows], list(state.managed_squad))
            for row, p in zip(roster.rows, view):
                word, name, code, line, in_xi, captain = row
                self.assertEqual(name, goaldat.player_initials[word] + ' ' + goaldat.player_names[word])
                self.assertEqual((code, line), (p['role'], p['line']));self.assertIn(line, LINE)
                self.assertEqual(in_xi, word in state.starting_eleven);self.assertEqual(captain, word == w.draft()[1])
            self.assertIn('XI 11, bench 9', roster.accessibleName())

    def test_team_selection_shows_the_complete_card_with_the_draft_tactics(self):
        w = self.window;w.navigate(1);before = self.state()
        w.team_roster.setFocus();QTest.keyClick(w.team_roster, Qt.Key.Key_Down);QTest.keyClick(w.team_roster, Qt.Key.Key_Down)
        self.assertEqual(w.table.currentRow(), 2);self.assertEqual(w.team_roster.current, 2)
        word = self.model.state.managed_squad[2]
        self.assertEqual(w.team_card.card, player_card.card(self.model.state, word, self.model.goaldat, team_tactics=w.draft()[2]))
        # A draft tactic shows on the card at once, before any confirm.
        w.tactics[0][1].click();self.app.processEvents()
        self.assertEqual(w.team_card.card, player_card.card(self.model.state, word, self.model.goaldat, team_tactics=w.draft()[2]))
        # Selecting in the table moves the roster too.
        w.table.setCurrentCell(5, 1);self.assertEqual(w.team_roster.current, 5)
        self.assertEqual(self.state(), before)

    def test_space_toggles_the_xi_under_the_existing_rules(self):
        w = self.window;w.navigate(1);squad = self.model.state.managed_squad;eleven = self.model.state.starting_eleven
        before = self.state()
        starter = squad.index(eleven[1]);w.team_roster.set_current(starter);w.team_roster.setFocus()
        QTest.keyClick(w.team_roster, Qt.Key.Key_Space)
        self.assertNotIn(eleven[1], w.selected_ids());self.assertFalse(w.team_roster.rows[starter][4])
        QTest.keyClick(w.team_roster, Qt.Key.Key_Space);self.assertIn(eleven[1], w.selected_ids())
        self.assertEqual(self.state(), before, 'toggling only drafts')
        # An unavailable reserve cannot start.
        reserve = next(i for i, word in enumerate(squad) if word not in eleven)
        record = bytearray(self.model.state.players[squad[reserve]]);record[14] = 0;record[16] = 0x88
        self.model.state.players[squad[reserve]] = bytes(record);w.refresh();w.navigate(1)
        w.team_roster.set_current(reserve);w.team_roster.setFocus();QTest.keyClick(w.team_roster, Qt.Key.Key_Space)
        self.assertNotIn(squad[reserve], w.selected_ids());self.assertIn('Unavailable', w.status.text())

    def test_a_preview_cannot_toggle(self):
        w = self.window;w.country.setCurrentIndex(w.country.findData(13));self.app.processEvents()
        self.assertIsNotNone(w.preview);w.navigate(1)
        selected = w.selected_ids();w.team_roster.set_current(0);w.team_roster.setFocus()
        QTest.keyClick(w.team_roster, Qt.Key.Key_Space)
        self.assertEqual(w.selected_ids(), selected);self.assertIn('preview', w.status.text().lower())

    def test_country_roster_enter_opens_the_player_on_team(self):
        w = self.window;w.navigate(0);w.country_roster.set_current(4);w.country_roster.setFocus()
        selected = w.selected_ids();QTest.keyClick(w.country_roster, Qt.Key.Key_Space)
        self.assertEqual(w.selected_ids(), selected, 'the desk never changes the XI')
        QTest.keyClick(w.country_roster, Qt.Key.Key_Return)
        self.assertEqual((w.page_stack.currentIndex(), w.table.currentRow(), w.team_roster.current), (1, 4, 4))

    def test_pool_cards_follow_outgoing_and_incoming(self):
        w = self.window;w.navigate(2);before = self.state()
        self.assertIsNone(w.pool_in_card.card)
        w.table.setCurrentCell(3, 1);word = self.model.state.managed_squad[3]
        self.assertEqual(w.pool_out_card.card, player_card.card(self.model.state, word, self.model.goaldat))
        self.assertGreater(w.reserves.rowCount(), 0)
        w.reserves.setCurrentCell(0, 1);incoming = w.reserves.item(0, 0).data(Qt.ItemDataRole.UserRole)
        self.assertEqual(w.pool_in_card.card, player_card.card(self.model.state, incoming, self.model.goaldat))
        self.assertEqual(self.state(), before)

    def test_a_page_does_not_grow_after_it_is_shown(self):
        # A page laid out while hidden must have its final height when navigation returns, or the
        # row the player is on moves away (player-browsing's 'focused row clipped').
        w = self.window
        for size in ((1440, 900), (1050, 780), (900, 700)):
            w.resize(*size);QTest.qWait(50)
            for index in (0, 1, 2):
                w.navigate(0 if index else 3);QTest.qWait(20);w.navigate(index)
                height = w.pages[index].widget().height()
                self.app.processEvents();QTest.qWait(20)
                self.assertEqual(w.pages[index].widget().height(), height, (size, index))

    def test_no_attribute_total_anywhere(self):
        w = self.window
        for index in range(5):
            w.navigate(index);self.app.processEvents()
        texts = [x.text() for x in w.findChildren(QLabel) + w.findChildren(QPushButton)]
        texts += [x.accessibleName() for x in w.findChildren(QWidget)]
        import re
        self.assertFalse([t for t in texts if re.search(r'\b(ability|overall|total)\b', t, re.I)])
        for card in (w.team_card.card, w.pool_out_card.card):
            if card is not None:self.assertNotIn('ability', card)


if __name__ == '__main__':
    unittest.main()
