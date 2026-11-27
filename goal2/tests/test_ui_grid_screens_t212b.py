"""[designed: owner, #667; T212b] Tactics and team players fit the cell grid without losing their controls or values."""
import unittest
from goal2.tests import requires, ui_assertions
from goal2.tests.test_ui_desk_t164 import CAREER, holland, tearDownModule
from goal2.tests.test_ui_grid_screens_t211b import Base
requires.require(modules=("PySide6",))
from goal2.ui.s07_team_info import CountryTacticsScreen, TeamPlayersScreen
from goal2.ui.s09_player_tactics import PlayerTacticsScreen
from goal2.ui.s10_team_tactics import TeamTacticsScreen
from goal2.ui.cells import CellPara

@CAREER
class TacticsOnTheGrid(Base):
    kind = TeamTacticsScreen
    live = False
    complete = False

    def make(self, window):
        model = holland()
        window.open_career(model)
        answer = None
        if self.live:
            from types import SimpleNamespace
            from goal2.ui.s19_bench import BenchAnswer
            words = model.state.managed_squad
            data = dict(context="half_time", eleven=list(words[:11]), bench=list(words[11:]),
                        injured=[words[1]], tactics=model.state.country_tactics, substitutions_left=5)
            if self.complete:
                data["player_records"] = [[word, model.state.players[word].hex()] for word in words]
                data["positions"] = [[word, model.state.players[word][6]] for word in words]
            answer = BenchAnswer(model, SimpleNamespace(data=data, minute=45, score=[0, 0]))
        if self.kind is CountryTacticsScreen:
            screen = self.kind(window, model, 21)
        elif self.kind is TeamPlayersScreen:
            screen = self.kind(window, model, "Trinidad/Tobago", country=21)
        elif self.kind is PlayerTacticsScreen:
            word = next(w for w in model.state.managed_squad[:11] if model.state.players[w][6] >= 2)
            screen = self.kind(window, model, word, bench=answer)
        else:
            screen = self.kind(window, model, answer=answer, apply=lambda *args: None)
        return window.push(screen)

    def test_every_tactics_screen_fits_at_every_size_and_sits_on_the_grid(self):
        for kind in (TeamTacticsScreen, CountryTacticsScreen, PlayerTacticsScreen, TeamPlayersScreen):
            with self.subTest(screen=kind.__name__):
                self.kind = kind
                self.every_state_fits()

    def test_these_screens_are_no_longer_pending(self):
        for kind in (TeamTacticsScreen, CountryTacticsScreen, PlayerTacticsScreen, TeamPlayersScreen):
            self.not_pending(kind.__name__, kind)

    def test_the_tactics_screens_use_segmented_skills_and_a_right_hand_role_column(self):
        for kind in (PlayerTacticsScreen, TeamTacticsScreen):
            self.kind = kind
            _, screen = self.canonical(self.make)
            self.assertTrue(all(bar.segmented for bar, _ in screen.skills.rows.values()))
            code, name = screen.strip.rows[0].cells
            self.assertLess(name.geometry().right(), code.x())
            if kind is PlayerTacticsScreen:
                self.assertLess(screen.skills.mapTo(screen, screen.skills.rect().topLeft()).x(),
                                screen.rows[0].mapTo(screen, screen.rows[0].rect().topLeft()).x())

    def test_all_tactic_choices_and_player_cards_keep_their_text(self):
        for kind in (TeamTacticsScreen, CountryTacticsScreen, PlayerTacticsScreen, TeamPlayersScreen):
            self.kind = kind
            window, screen = self.canonical(self.make)
            count = len(screen.cards) if kind is TeamPlayersScreen else len(screen.rows)
            for index in range(count):
                if kind is TeamPlayersScreen:
                    screen.pick(index)
                elif kind is not CountryTacticsScreen:
                    screen.choose(index)
                    if kind is PlayerTacticsScreen:
                        screen.alter()
                    else:
                        screen.change()
                self.relayout(window)
                self.text_fits_its_cells(screen, kind.__name__)
                for text in screen.findChildren(CellPara):
                    if text.isVisibleTo(screen):
                        self.assertLessEqual(len(text.lines()), self.rows_of(text), text.text())
                self.key_bar_is_two_rows(window, screen)
                self.on_the_grid(window, 20)

    def test_live_tactics_pending_and_acknowledged_and_unavailable_traits_fit(self):
        self.live = True
        for complete in (False, True):
            self.complete = complete
            for kind in (TeamTacticsScreen, PlayerTacticsScreen):
                self.kind = kind
                with self.subTest(complete=complete, kind=kind.__name__):
                    self.every_state_fits()
                    window, screen = self.canonical(self.make)
                    if kind is TeamTacticsScreen:
                        screen.change()
                        self.assertTrue(screen.pending)
                        self.relayout(window)
                        self.assertLessEqual(len(screen.note.lines()), self.rows_of(screen.note))
                        screen.applied(screen.answer, None)
                    else:
                        self.assertEqual(len(screen.rows), 5)
                        screen.choose(4)
                        screen.alter()
                        self.assertEqual(screen.rows[4].texts()[1], "nobody")
                    self.relayout(window)
                    self.text_fits_its_cells(screen)
                    self.on_the_grid(window, 20)
                    for text in screen.findChildren(CellPara):
                        if text.isVisibleTo(screen):
                            self.assertLessEqual(len(text.lines()), self.rows_of(text), text.text())

    def test_other_countries_values_are_read_only_and_the_longest_heading_fits(self):
        import copy
        from goal2.desktop import fixed_page
        self.kind = TeamPlayersScreen
        window, screen = self.canonical(self.make)
        self.assertEqual(screen.players_heading.text(), "Trinidad/Tobago · the twenty")
        self.assertEqual(fixed_page.problems(window), [])
        self.kind = CountryTacticsScreen
        window, screen = self.canonical(self.make)
        before = copy.deepcopy(window.career.state)
        for row in screen.rows:
            row.chosen.emit(0)
        self.assertEqual(window.career.state, before)


if __name__ == "__main__":
    unittest.main()
