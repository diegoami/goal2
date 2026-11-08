"""[designed: owner, 2026-11-03, #526, #527 D2] T165: S08 squad and pool, S09 player tactics, S10 team tactics.

The claim it protects: every change made on these screens is the change `DesktopModel` makes for the same request
(the same exchange, position, club position, tactics and name), read back through `DesktopModel.view` and the
whole state. Each test drives a screen over one career and makes the same request directly on a copy of it.
The new model calls (`set_position`, `club_position`, `own_tactic`, `set_team_tactic`) are visited against the
rules they cite (F029, F010).

The career comes from the `.cache/` files the desktop tests use (skipped without them); nothing of the original is in
this file (CLAUDE.md rule 14).
"""
import copy
import re
import shutil
import tempfile
import unittest
from pathlib import Path

from goal2.tests import requires

requires.require(modules=("PySide6",))

from PySide6.QtCore import Qt  # noqa: E402
from PySide6.QtTest import QTest  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from goal2.desktop import data_setup, fixed_page  # noqa: E402
from goal2.desktop.model import DesktopModel  # noqa: E402
from goal2.ui import theme  # noqa: E402
from goal2.ui.s08_squad import SquadScreen, open_squad  # noqa: E402
from goal2.ui.s09_player_tactics import PlayerTacticsScreen  # noqa: E402
from goal2.ui.s10_team_tactics import LINES as TEAM_LINES, open_team_tactics  # noqa: E402
from goal2.ui.screen import Clickable  # noqa: E402
from goal2.ui.squad_card import full_name, squad_rows  # noqa: E402
from goal2.ui.window import Window  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
COUNTRY = 4   # the pool's exchange window is open in this state (test_desktop_pool)
_BASE = {}


def career():
    """A fresh copy of one career from DesktopModel.open (opened once per run)."""
    if "model" not in _BASE:
        folder = tempfile.mkdtemp(prefix="goal2-t165-")
        _BASE["folder"] = folder
        _BASE["model"] = DesktopModel.open(ROOT / ".cache/e010-r0008-halftime.sav", ROOT / ".cache/GOAL.DAT",
                                           Path(folder) / "career.g2save", country=COUNTRY)
    return copy.deepcopy(_BASE["model"])


def tearDownModule():
    if "folder" in _BASE:
        shutil.rmtree(_BASE["folder"], ignore_errors=True)


@requires.need(**requires.HALFTIME)
class ModelCalls(unittest.TestCase):
    """The model's new calls, against the rules they cite."""

    def setUp(self):
        self.model = career()

    def record(self, word):
        return self.model.state.players[word]

    def test_set_position_steps_and_wraps_0_to_13(self):
        word = self.model.state.managed_squad[3]
        start = self.record(word)[6]
        seen = []
        for _ in range(14):
            self.model.set_position(word)
            seen.append(self.record(word)[6])
        self.assertEqual(seen, [(start + i) % 14 for i in range(1, 15)], "R: +1, wrapping 0..13 (1771:4925)")
        self.model.set_position(word, -1)
        self.assertEqual(self.record(word)[6], (start - 1) % 14, "Shift+R: one back (#423)")
        before = list(self.model.state.players)
        self.model.set_position(word)
        changed = [w for w, (a, b) in enumerate(zip(before, self.model.state.players)) if a != b]
        self.assertEqual(changed, [word])
        self.assertEqual([i for i in range(20) if before[word][i] != self.record(word)[i]], [6], "only +6 changes")

    def test_club_position_copies_plus_7_into_plus_6(self):
        word = self.model.state.managed_squad[5]
        self.model.set_position(word)
        self.assertNotEqual(self.record(word)[6], self.record(word)[7])
        self.model.club_position(word)
        self.assertEqual(self.record(word)[6], self.record(word)[7], "C: +6 = +7 (F029, 1771:4952)")

    def test_own_tactic_cycles_the_three_states_of_f010(self):
        word = self.model.state.managed_squad[6]
        for element in (1, 2, 3, 4):
            own, value = 1 << (element + 3), 1 << (element - 1)
            for team in (0, 1):
                # Start from no own setting and the team's element at `team`.
                if (self.model.state.country_tactics & value) != team * value:
                    self.model.set_team_tactic(element)
                for _ in range(3):
                    if not self.record(word)[15] & own:
                        break
                    self.model.own_tactic(word, element)
                states = []
                for _ in range(3):
                    self.model.own_tactic(word, element)
                    bits = self.record(word)[15]
                    states.append((bool(bits & own), bool(bits & value)))
                self.assertEqual(states, [(True, False), (True, True), (False, bool(team))],
                                 f"element {element}, team element {team}")

    def test_set_team_tactic_toggles_one_element(self):
        for element in range(1, 9):
            before = self.model.state.country_tactics
            self.assertEqual(self.model.set_team_tactic(element), before ^ (1 << (element - 1)))
            self.assertEqual(self.model.state.country_tactics, before ^ (1 << (element - 1)))

    def test_pool_players_change_too_and_bad_requests_change_nothing(self):
        reserve = self.model.pool_view()["reserves"][0]["id"]
        start = self.record(reserve)[6]
        self.model.set_position(reserve)
        self.assertEqual(self.record(reserve)[6], (start + 1) % 14)
        foreign = next(w for w in range(1, 2561) if self.model.state.players[w][0] != COUNTRY)
        for call in (lambda: self.model.set_position(foreign), lambda: self.model.club_position(foreign),
                     lambda: self.model.own_tactic(foreign, 1), lambda: self.model.set_position(reserve, 2),
                     lambda: self.model.own_tactic(reserve, 5), lambda: self.model.set_team_tactic(0),
                     lambda: self.model.set_team_tactic(9), lambda: self.model.set_position(True)):
            before = copy.deepcopy(self.model.state)
            with self.assertRaises(ValueError):
                call()
            self.assertEqual(self.model.state, before)


@requires.need(**requires.HALFTIME)
class Screens(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])
        cls.font_before = cls.app.font()
        theme.install(cls.app)

    @classmethod
    def tearDownClass(cls):
        cls.app.setFont(cls.font_before)

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="goal2-t165-ui-"))
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.model = career()          # the screens' career
        self.same = copy.deepcopy(self.model)   # the same career, changed directly through the model
        self.win = Window(data_setup.paths(self.tmp / "goal2"))
        self.win.resize(fixed_page.WIDTH, fixed_page.HEIGHT)
        self.win.show()
        self.app.processEvents()
        self.addCleanup(lambda: (self.win.close(), self.win.deleteLater(), self.app.processEvents()))

    # Helpers.
    def key(self, key, modifier=Qt.KeyboardModifier.NoModifier):
        QTest.keyClick(self.win, key, modifier)
        self.app.processEvents()

    def click(self, widget):
        QTest.mouseClick(widget, Qt.MouseButton.LeftButton)
        self.app.processEvents()

    def bar_key(self, screen, text):
        return next(item for item in screen.key_bar.findChildren(Clickable, "keyItem") if item.binding.text == text)

    def assertSame(self):
        self.assertEqual(self.model.view(), self.same.view())
        self.assertEqual(self.model.state, self.same.state)

    def squad(self):
        screen = open_squad(self.win, self.model)
        self.app.processEvents()
        self.assertEqual(fixed_page.problems(self.win), [])
        return screen

    def to_row(self, screen, index):
        while screen.cursor[screen.side] < index:
            self.key(Qt.Key.Key_Down)
        while screen.cursor[screen.side] > index:
            self.key(Qt.Key.Key_Up)
        return screen.current()

    # S08.
    def test_two_enter_exchange_is_the_models_exchange_with_put_here_between(self):
        screen = self.squad()
        self.assertEqual(screen.enter_text.text(), "Move player")
        self.key(Qt.Key.Key_Right)
        self.assertEqual(screen.side, "pool")
        incoming = self.to_row(screen, 3)
        self.key(Qt.Key.Key_Return)
        self.assertEqual(screen.enter_text.text(), "Put here")
        self.assertTrue(screen.wait_box.isVisible())
        self.key(Qt.Key.Key_Left)
        self.assertEqual(screen.side, "squad")
        self.assertEqual(screen.enter_text.text(), "Put here", "the hint stays between the two Enters")
        outgoing = self.to_row(screen, 7)
        self.assertEqual(screen.enter_text.text(), "Put here")
        self.assertEqual(self.model.state, self.same.state, "nothing changes before the second Enter")
        self.key(Qt.Key.Key_Return)
        self.same.exchange(outgoing, incoming)
        self.assertSame()
        self.assertIn(incoming, self.model.state.managed_squad)
        self.assertEqual(screen.enter_text.text(), "Move player")
        self.assertFalse(screen.wait_box.isVisible())
        self.assertEqual(screen.current(), incoming, "the card shows the player put here")

    def test_ins_says_coming_later_and_changes_nothing(self):
        screen = self.squad()
        item = self.bar_key(screen, "coming later")
        self.assertEqual(item.binding.captions, ("Ins",))
        self.key(Qt.Key.Key_Insert)
        self.assertIn("coming later", screen.note.text())
        self.assertSame()
        self.click(item)
        self.assertSame()

    def test_paging_the_pool_reaches_all_80(self):
        screen = self.squad()
        self.key(Qt.Key.Key_Right)
        reserves = [r["id"] for r in self.model.pool_view()["reserves"]]
        self.assertEqual(len(reserves), 80)
        seen, pages = [], set()
        for step in range(80):
            seen.append(screen.current())
            pages.add(screen.page())
            shown = screen.strip.shown_texts()
            self.assertEqual(len(shown), 20)
            on = [row for row in screen.strip.rows if row.on]
            self.assertEqual(len(on), 1)
            self.assertEqual(on[0].texts()[1], full_name(self.model, screen.current()))
            if step < 79:
                self.key(Qt.Key.Key_Down)
        self.assertEqual(seen, reserves)
        self.assertEqual(pages, {0, 1, 2, 3})
        self.key(Qt.Key.Key_Down)
        self.assertEqual(screen.current(), reserves[-1], "the last page ends the list")
        for _ in range(20):
            self.key(Qt.Key.Key_Up)
        self.assertEqual(screen.page(), 2, "↑ goes back a page")

    def test_r_shift_r_c_and_f2_are_the_models_changes(self):
        screen = self.squad()
        word = self.to_row(screen, 4)
        self.key(Qt.Key.Key_R)
        self.same.set_position(word, 1)
        self.assertSame()
        self.key(Qt.Key.Key_R)
        self.same.set_position(word, 1)
        self.assertSame()
        self.key(Qt.Key.Key_R, Qt.KeyboardModifier.ShiftModifier)
        self.same.set_position(word, -1)
        self.assertSame()
        self.assertNotEqual(self.model.state.players[word][6], self.model.state.players[word][7])
        self.key(Qt.Key.Key_C)
        self.same.club_position(word)
        self.assertSame()
        self.key(Qt.Key.Key_F2)
        self.assertEqual(screen.enter_text.text(), "Give this name")
        edit = screen.card.name_line.edit
        self.assertTrue(screen.card.name_line.isVisible())
        edit.clear()
        QTest.keyClicks(edit, "Kovalenko")
        self.app.processEvents()
        self.assertEqual(screen.card.name_line.count.text(), "9 / 12")
        self.assertEqual(self.model.state, self.same.state, "typing changes nothing before Enter")
        self.key(Qt.Key.Key_Return)
        self.same.rename_player(word, "Kovalenko")
        self.assertSame()
        self.assertFalse(screen.card.name_line.isVisible())
        self.assertTrue(screen.card.name.text().endswith("Kovalenko"))
        # Esc closes the name line and keeps the name.
        self.key(Qt.Key.Key_F2)
        QTest.keyClicks(screen.card.name_line.edit, "x")
        self.key(Qt.Key.Key_Escape)
        self.assertSame()
        self.assertIs(self.win.current(), screen)
        self.assertEqual(len(screen.card.name_line.edit.text()), 1)
        QTest.keyClicks(screen.card.name_line.edit, "y" * 20)
        self.assertLessEqual(len(screen.card.name_line.edit.text()), 12)

    def test_pool_players_take_r_and_c_too(self):
        screen = self.squad()
        self.key(Qt.Key.Key_Right)
        word = self.to_row(screen, 25)
        self.key(Qt.Key.Key_R)
        self.same.set_position(word, 1)
        self.assertSame()

    # S09.
    def test_s09_shows_four_lines_and_each_alter_is_the_models(self):
        screen = self.squad()
        own = 1 << 4 | 1 << 5 | 1 << 6 | 1 << 7
        # A player with no own tactic set, so every line gains its P on the first alter.
        index, word = next((i, r["id"]) for i, r in enumerate(squad_rows(self.model)[0])
                           if not self.model.state.players[r["id"]][15] & own)
        self.to_row(screen, index)
        self.key(Qt.Key.Key_T)
        tactics = self.win.current()
        self.assertIsInstance(tactics, PlayerTacticsScreen)
        self.assertEqual(fixed_page.problems(self.win), [])
        lines = tactics.lines()
        self.assertEqual([name for name, _ in lines], ["position", "possession", "passing", "tackling"])
        self.assertNotIn("mark", [name for name, _ in lines])
        self.assertFalse(any(value.endswith(" P") for _, value in lines))
        for line in range(4):
            while tactics.line < line:
                self.key(Qt.Key.Key_Down)
            self.assertEqual(tactics.enter_text.text(), "Alter tactic")
            self.key(Qt.Key.Key_Return)
            self.same.own_tactic(word, line + 1)
            self.assertSame()
            self.assertTrue(tactics.lines()[line][1].endswith(" P"), f"P marks line {line + 1}")
        self.key(Qt.Key.Key_Left)
        self.assertEqual(tactics.line, 2, "← is a line up too")
        self.key(Qt.Key.Key_Escape)
        self.assertIs(self.win.current(), screen, "Esc returns to the card")
        for name in ("position", "possession", "passing", "tackling"):
            self.assertTrue(screen.card.tactics.values[name].text().endswith(" P"), f"the card shows {name}'s P")

    # S10.
    def test_s10_each_of_the_eight_lines_is_the_models_change(self):
        screen = open_team_tactics(self.win, self.model)
        self.app.processEvents()
        self.assertEqual(fixed_page.problems(self.win), [])
        self.assertEqual([name for name, *_ in screen.lines()], [name for name, _ in TEAM_LINES])
        for index, (name, element) in enumerate(TEAM_LINES):
            while screen.line < index:
                self.key(Qt.Key.Key_Down)
            _, now, other = screen.lines()[index]
            self.assertNotEqual(now, other)
            self.key(Qt.Key.Key_Return)
            self.same.set_team_tactic(element)
            self.assertSame()
            self.assertEqual(screen.lines()[index][1:], (other, now), f"{name}: the other option is now")
            self.assertIn(f"Changed just now: {name} {now} → {other}", re.sub(r"<[^>]+>", "", screen.note.text()))
        from goal2.game.country_card import card
        self.assertEqual(screen.characteristics.panel,
                         card(self.model.state,self.model.state.managed_country,self.model.goaldat)['characteristics'])

    # The mouse.
    def test_a_click_on_a_row_and_on_a_bar_key_does_what_its_key_does(self):
        screen = self.squad()
        # A row: the cursor goes there, as ↓ would; on the highlighted row it is Enter.
        self.click(screen.strip.rows[2])
        self.assertEqual(screen.cursor["squad"], 2)
        self.click(screen.strip.rows[2])
        self.assertEqual(screen.picked, ("squad", screen.current()))
        self.assertEqual(screen.enter_text.text(), "Put here")
        self.click(screen.strip.rows[2])
        self.assertIsNone(screen.picked, "Enter on the picked player again drops him")
        # Squad / Pool are ← and →.
        self.click(screen.pool_button)
        self.assertEqual(screen.side, "pool")
        self.click(screen.strip.rows[1])
        incoming = screen.current()
        self.click(screen.enter_hint)
        self.assertEqual(screen.enter_text.text(), "Put here")
        self.click(screen.squad_button)
        self.assertEqual(screen.side, "squad")
        outgoing = screen.current()
        self.click(screen.strip.rows[2])
        self.same.exchange(outgoing, incoming)
        self.assertSame()
        # Bar keys.
        word = screen.current()
        self.click(self.bar_key(screen, "next position"))
        self.same.set_position(word, 1)
        self.assertSame()
        self.click(self.bar_key(screen, "club position"))
        self.same.club_position(word)
        self.assertSame()
        self.click(self.bar_key(screen, "his tactics"))
        tactics = self.win.current()
        self.assertIsInstance(tactics, PlayerTacticsScreen)
        self.click(tactics.rows[1])
        self.assertEqual(tactics.line, 1)
        self.click(tactics.rows[1])
        self.same.own_tactic(word, 2)
        self.assertSame()
        self.click(self.bar_key(tactics, "back to the card"))
        self.assertIs(self.win.current(), screen)
        teams = open_team_tactics(self.win, self.model)
        self.app.processEvents()
        self.click(teams.rows[3])
        self.click(teams.rows[3])
        self.same.set_team_tactic(TEAM_LINES[3][1])
        self.assertSame()
        self.click(self.bar_key(teams, "desk"))
        self.assertIs(self.win.current(), screen)
        self.click(self.bar_key(screen, "desk"))
        self.assertIsInstance(self.win.current(), SquadScreen, "the bottom screen stays (Esc returns to the desk)")


if __name__ == "__main__":
    unittest.main()
