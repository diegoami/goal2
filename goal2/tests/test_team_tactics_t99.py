"""[designed: T99; owner, 2026-10-21; confirmed: `docs/original-game/images/m244-squad.png`]
The Team page in the original's style: the roster strip on the right of two views, 0 the card with
its routes and 1 Team tactics; no table. A tactic row's word follows its bit [confirmed: docs/original-game/images/m244-team-tactics.png;
the tactic bits of window.TACTICS]; the draft and Confirm/Discard are unchanged.
"""
from pathlib import Path
import re
import unittest

from goal2.tests import requires

requires.require(modules=('PySide6',), **requires.HALFTIME)

from PySide6.QtCore import Qt  # noqa: E402
from PySide6.QtTest import QTest  # noqa: E402
from PySide6.QtWidgets import QApplication, QCheckBox, QTableWidget, QWidget  # noqa: E402
from goal2.desktop.model import DesktopModel  # noqa: E402
from goal2.desktop.window import ManagementWindow, TACTICS  # noqa: E402
from goal2.game.session_save import encode  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
CATEGORIES = {5: 'Defence system', 6: 'Protection', 7: 'Offside', 1: 'Positioning', 2: 'Possession',
              3: 'Passing', 4: 'Tackling', 8: 'Marking'}


def word(alternatives, checked):
    value = alternatives.split(' / ')[1 if checked else 0]
    return value[:1].upper() + value[1:]


class TeamTactics(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def open(self):
        model = DesktopModel.open(ROOT / '.cache/e010-r0008-halftime.sav', ROOT / '.cache/GOAL.DAT',
                                  ROOT / '.cache/never-written.g2save', country=8)
        window = ManagementWindow(model);window.resize(1440, 900);window.show()
        window.activateWindow();QTest.qWaitForWindowActive(window)
        self.addCleanup(lambda: (window.close(), window.deleteLater(), self.app.processEvents()))
        return model, window

    def setUp(self):
        self.model, self.window = self.open()

    def state(self, model=None):
        model = model or self.model
        return encode(model.state, model.template_bytes)

    def bits(self):
        return sum(1 << (element - 1) for element, row in self.window.tactics if row.isChecked())

    def assert_rows_follow(self, bits):
        for element, row in self.window.tactics:
            checked = bool(bits & (1 << (element - 1)))
            self.assertEqual(row.isChecked(), checked, element)
            expected = f'{CATEGORIES[element]}: {word(dict(TACTICS)[element], checked)}'
            self.assertEqual(row.accessibleName(), expected)
            self.assertEqual(row.text(), expected)

    def visible_views(self):
        w = self.window
        return [i for i in range(w.team_views.count()) if w.team_views.widget(i).isVisible()]

    def test_rows_keep_the_order_and_the_alternatives(self):
        w = self.window
        self.assertEqual([element for element, _ in w.tactics], [5, 6, 7, 1, 2, 3, 4, 8])
        for element, row in w.tactics:
            self.assertEqual(row.property('alternatives'), dict(TACTICS)[element])
            self.assertTrue(row.isCheckable());self.assertNotIsInstance(row, QCheckBox)

    def test_each_word_follows_its_bit_initially_and_after_enter(self):
        w = self.window;w.navigate(1);w.team_view(1);self.app.processEvents()
        self.assert_rows_follow(self.model.state.country_tactics)
        before = self.state()
        for element, row in w.tactics:
            row.setFocus();QTest.keyClick(row, Qt.Key.Key_Return);self.app.processEvents()
            self.assertEqual(self.bits(), w.draft()[2])
            self.assert_rows_follow(w.draft()[2])
            self.assertTrue(w.draft()[2] & (1 << (element - 1)) != self.model.state.country_tactics & (1 << (element - 1)))
        self.assertEqual(w.draft()[2], self.model.state.country_tactics ^ 0xFF)
        # Space and a click switch a row too; the word follows each time.
        row = w.tactics[0][1];QTest.keyClick(row, Qt.Key.Key_Space);self.assert_rows_follow(w.draft()[2])
        QTest.mouseClick(row, Qt.MouseButton.LeftButton);self.assert_rows_follow(w.draft()[2])
        # A discard or a refresh sets the bits; the words follow them.
        w.cancel.click();self.app.processEvents();self.assert_rows_follow(self.model.state.country_tactics)
        self.assertEqual(self.state(), before, 'drafting tactics changed the encoded state')

    def test_confirm_plan_writes_what_confirm_management_writes(self):
        w = self.window;w.navigate(1);w.team_view(1)
        model2, w2 = self.open()
        before = self.state();expected = self.model.state.country_tactics ^ (1 << 4 | 1 << 0 | 1 << 7)
        for window in (w, w2):
            for element in (5, 1, 8):
                row = dict(window.tactics)[element];row.setFocus();QTest.keyClick(row, Qt.Key.Key_Return)
        self.assertEqual(self.state(), before, 'a draft was published before a confirm')
        w.confirm_plan.click();self.app.processEvents();w2.confirm.click();self.app.processEvents()
        self.assertEqual(w.status.text(), 'Management confirmed')
        self.assertEqual(self.model.state.country_tactics, model2.state.country_tactics)
        self.assertEqual(self.model.state.country_tactics, expected)
        self.assertEqual(self.state(), self.state(model2))
        self.assertNotEqual(self.state(), before)

    def test_discard_team_restores_the_confirmed_state_and_returns(self):
        w = self.window;w.navigate(1);w.team_view(1);confirmed = w.draft();before = self.state()
        for _, row in w.tactics[:3]:
            row.setFocus();QTest.keyClick(row, Qt.Key.Key_Return)
        w.captain.setCurrentIndex((w.captain.currentIndex() + 1) % w.captain.count())
        self.assertNotEqual(w.draft(), confirmed)
        w.discard_plan.click();self.app.processEvents()
        self.assertEqual(w.draft(), confirmed);self.assert_rows_follow(self.model.state.country_tactics)
        self.assertEqual(w.team_views.currentIndex(), 0);self.assertEqual(self.visible_views(), [0])
        self.assertEqual(self.state(), before)

    def test_no_view_shows_a_check_box_a_table_or_a_skill_number(self):
        w = self.window;w.navigate(1);page = w.pages[1]
        self.assertFalse(page.findChildren(QCheckBox), 'a tactic is still a check box')
        self.assertEqual(w.team_views.count(), 2, 'there is no table view')
        for view in (0, 1):
            w.team_view(view);self.app.processEvents()
            shown = [x for x in page.findChildren(QWidget) if x.isVisible()]
            self.assertFalse([x for x in shown if isinstance(x, (QCheckBox, QTableWidget))], view)
            self.assertTrue(w.team_roster.isVisible(), 'the strip shows on every view')
            self.assertTrue(w.team_views.widget(view).isVisible())
        self.assertFalse(w.table.isVisible())
        w.team_view(0)
        self.assertEqual([b.text() for b in w.team_routes], ['Pool / Compare >', 'Team tactics >', 'Rename (F2)'])
        for button in w.team_routes:self.assertTrue(button.isVisible(), button.text())
        for row in range(20):
            w.team_roster.set_current(row);w.team_card.grab()
            card = w.team_card.card;drawn = w.team_card.drawn
            self.assertTrue(drawn and card['full_name'].upper() in drawn)
            self.assertFalse([t for t in drawn if re.fullmatch(r'\s*\d+\s*', t)], 'a number beside a bar')
            # Each characteristic's word is drawn, inside its bar.
            for _, word, _, _ in card['characteristics']:self.assertIn(word, drawn)
            for name, _ in card['skills']:self.assertIn(name.capitalize(), drawn)

    def test_the_strip_lists_the_xi_a_rule_then_the_bench_and_space_moves(self):
        w = self.window;w.navigate(1);strip = w.team_roster;before = self.state()
        squad = list(self.model.state.managed_squad)

        def check():
            eleven = w.drafted_eleven();bench = [x for x in squad if x not in eleven]
            self.assertEqual([strip.rows[i][0] for i in strip.order], eleven + bench)
            self.assertEqual(strip.eleven(), len(eleven))
            last, first = strip.row_rect(strip.order[len(eleven) - 1]), strip.row_rect(strip.order[len(eleven)])
            self.assertGreater(first.top() - last.top(), last.height() + 8, 'no rule between the XI and the bench')
            return eleven, bench
        eleven, bench = check()
        self.assertEqual(eleven, list(self.model.state.starting_eleven))
        starter = eleven[3];strip.set_current(squad.index(starter));strip.setFocus()
        QTest.keyClick(strip, Qt.Key.Key_Space);self.app.processEvents()
        eleven, bench = check();self.assertIn(starter, bench);self.assertEqual(len(eleven), 10)
        QTest.keyClick(strip, Qt.Key.Key_Space);self.app.processEvents()
        eleven, bench = check();self.assertEqual(eleven, list(self.model.state.starting_eleven))
        # Up/Down follow the displayed order across the rule; a click selects the row it hits.
        strip.set_current(strip.order[10]);QTest.keyClick(strip, Qt.Key.Key_Down)
        self.assertEqual(strip.current, strip.order[11])
        target = strip.order[15];QTest.mouseClick(strip, Qt.MouseButton.LeftButton, pos=strip.row_rect(target).center())
        self.assertEqual((strip.current, w.table.currentRow()), (target, target))
        self.assertEqual(w.team_card.card['id'], squad[target])
        # A click on the current row selects it again for a table that lost its selection.
        w.table.setCurrentCell(-1, -1);self.assertEqual(strip.current, 0)
        QTest.mouseClick(strip, Qt.MouseButton.LeftButton, pos=strip.row_rect(0).center())
        self.assertEqual(w.table.currentRow(), 0)
        # While a match runs the strip cannot change the XI (the hidden table is disabled).
        selected = w.selected_ids();w.set_busy(True);strip.setFocus()
        QTest.keyClick(strip, Qt.Key.Key_Space);self.assertEqual(w.selected_ids(), selected)
        self.assertIn('Finish or cancel', w.status.text());w.set_busy(False)
        self.assertEqual(self.state(), before, 'the strip only drafts')

    def test_each_route_reaches_its_view_and_escape_returns(self):
        w = self.window;w.navigate(1);before = self.state()
        w.team_tactics_route.click();self.app.processEvents()
        self.assertEqual((w.team_views.currentIndex(), self.visible_views()), (1, [1]))
        for widget in (w.captain, w.confirm_plan, w.discard_plan, w.team_roster, *(r for _, r in w.tactics)):
            self.assertTrue(widget.isVisible(), widget.objectName())
        self.assertFalse(w.team_card.isVisible())
        # [designed: #311] The Escape shortcut fires only in the active window, and focus is read
        # from the window: another GUI test window on the Windows runner can be the active one.
        w.activateWindow();QTest.qWaitForWindowActive(w)
        QTest.keyClick(w.focusWidget(), Qt.Key.Key_Escape);self.app.processEvents()
        self.assertEqual(w.team_views.currentIndex(), 0)
        self.assertIs(w.focusWidget(), w.team_roster, 'Escape returns with the roster focused')
        # Escape from the page heading works too.
        w.team_view(1);w.pages[1].heading.setFocus();w.activateWindow();QTest.qWaitForWindowActive(w)
        QTest.keyClick(w.pages[1].heading, Qt.Key.Key_Escape)
        self.assertEqual(w.team_views.currentIndex(), 0)
        w.team_pool.click();self.assertEqual(w.page_stack.currentIndex(), 2)
        self.assertEqual(self.state(), before)

    def test_left_card_names_the_xi_formation_manager_and_captain(self):
        w = self.window;w.navigate(1);w.team_view(1)
        rows = self.model.view()['players'];eleven = [r for r in rows if r['id'] in self.model.state.starting_eleven]
        formation = '-'.join(str(sum(1 for r in eleven if r['line'] == line)) for line in ('defence', 'midfield', 'attack'))
        name = self.model.goaldat.country_names[8].upper()
        self.assertEqual(w.tactics_heading.text(), f'{name} / XI 11 / {formation}')
        self.assertEqual(w.tactics_manager.text(), 'Manager: ' + self.model.manager.split(' (')[0])
        self.assertTrue(w.tactics_heading.parentWidget().isAncestorOf(w.captain))
        # Dropping a starter changes the counted XI at once; nothing is stored.
        before = self.state();row = rows.index(eleven[-1])
        w.table.item(row, 0).setCheckState(Qt.CheckState.Unchecked);self.app.processEvents()
        self.assertIn(' / XI 10 / ', w.tactics_heading.text());self.assertEqual(self.state(), before)

    def test_preview_rows_are_read_only(self):
        w = self.window;w.country.setCurrentIndex(w.country.findData(13));self.app.processEvents()
        self.assertIsNotNone(w.preview)
        for _, row in w.tactics:self.assertFalse(row.isEnabled())
        self.assertFalse(w.confirm_plan.isEnabled())


if __name__ == '__main__':
    unittest.main()
