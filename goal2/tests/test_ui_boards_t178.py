"""[designed: owner, 2026-11-03, #526, #527 D2; T178, #560, #563] The fixture list (S11), the tournament (S12), the
history (S13) and the desk's banner, over the Python route's state.

The claim it protects: every number these boards show is the route's own state, as the model reports it, and a stage
the route has not reached says so instead of inventing rows. Visited here, on a 2028 Holland career (the capture's):
- the model's new read-only calls against the career's world schedule and results (`fixture_list`, `tournament`,
  `history`, `competition`, `continent`), and that none of them changes the career;
- S11 lists the round's fixtures with the model's kinds and ✓ on your own; ↑↓ scroll; Enter on another country's
  match and on your own friendly says it comes later and changes nothing (the ✓ toggle is not built: the engine
  plays no computer-vs-computer match watched, #560); S07's Enter opens S11 on that country's fixtures;
- S12's managed group equals `competition_table()` row by row, every other group the route's own table
  (`continental_qualifying.tables`); ↑↓, Space, ←→, Ins; Finals and Championship read *not reached yet*;
- S13 shows a recorded result (the first round played by the route's quick friendly) and says which boxes have no
  source (#509 Track B);
- the banner reads *European Championship* for Holland, *American Championship* for an American country;
- each screen's Esc back, and the desk's three options open their screens.

The careers read GOAL.DAT and the E010 half-time template from the git-ignored `.cache/` and skip without them
(goal2/tests/requires.py); nothing of the original is in this file (CLAUDE.md rule 14).
"""
import copy
import shutil
import tempfile
import unittest
from pathlib import Path

from goal2.tests import requires

requires.require(modules=("PySide6",))

from PySide6.QtCore import Qt  # noqa: E402
from PySide6.QtTest import QTest  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from goal2.desktop import data_setup, fixed_page, worker  # noqa: E402
from goal2.desktop.model import DesktopModel  # noqa: E402
from goal2.game import continental_qualifying  # noqa: E402
from goal2.ui import saves  # noqa: E402
from goal2.ui.s06_desk import DeskScreen  # noqa: E402
from goal2.ui.s07_team_info import TeamInfoScreen  # noqa: E402
from goal2.ui.s11_fixtures import CHECK, VISIBLE, FixturesScreen  # noqa: E402
from goal2.ui.s12_tournament import TABS, TournamentScreen  # noqa: E402
from goal2.ui.s13_history import HistoryScreen  # noqa: E402
from goal2.ui.window import Window  # noqa: E402

CACHE = requires.CACHE
CAREER = requires.need(**requires.HALFTIME)
HOLLAND = 20
_BASE = {}


def career(country=HOLLAND):
    """A fresh copy of a career starting in 2028, the capture's year (opened once per country and run)."""
    if country not in _BASE:
        folder = _BASE.setdefault("folder", tempfile.mkdtemp(prefix="goal2-t178-"))
        model = DesktopModel.open(CACHE / data_setup.TEMPLATE_NAME, CACHE / data_setup.DATA_NAME,
                                  Path(folder) / "unused.g2game", country=country)
        model.new_campaign(country, 2028)
        model.rename_manager("K Ees")
        _BASE[country] = model
    return copy.deepcopy(_BASE[country])


def played_round(model):
    """The career after its first round, played by the route's own quick friendly (goal2/desktop/worker.py)."""
    fixture = model.state.campaign.next_fixture
    assert fixture.kind == 1, "the 2028 Holland career opens on a friendly"
    model.state = worker.play(model.state, model.template_bytes)
    return model


def tearDownModule():
    if "folder" in _BASE:
        shutil.rmtree(_BASE["folder"], ignore_errors=True)


@CAREER
class ModelCalls(unittest.TestCase):
    """The model's new read-only calls against the career's own state."""

    def test_the_round_is_what_play_next_game_plays(self):
        model = career()
        world = model.state.campaign.world
        listing = model.fixture_list()
        self.assertEqual(listing["round"], 1)
        rows = listing["rows"]
        managed = [i for i, f in enumerate(world.fixtures) if HOLLAND in (f.side_a, f.side_b)]
        self.assertEqual([r["fixture_id"] for r in rows], [f.fixture_id for f in world.fixtures[:managed[1]]],
                         "from the cursor up to the managed fixture after the next one")
        self.assertEqual([r["kind"] for r in rows], [f.kind for f in world.fixtures[:managed[1]]])
        self.assertEqual([r["fixture_id"] for r in rows if r["own"]], [model.state.campaign.next_fixture.fixture_id])
        self.assertEqual([r["watch"] for r in rows], [r["own"] for r in rows], "your own match, and only it, ✓")
        self.assertEqual({r["kind_name"] for r in rows}, {"friendly", "qualifying"})
        # After the round: the cursor moved, the next round starts at Holland's next match.
        played = played_round(career())
        after = played.fixture_list()
        self.assertEqual(after["round"], 2)
        cursor = len(played.state.campaign.world.results)
        self.assertEqual(after["rows"][0]["fixture_id"], world.fixtures[cursor].fixture_id)
        self.assertTrue(after["rows"][0]["own"])

    def test_a_countrys_coming_fixtures(self):
        model = career()
        eire = 8
        rows = model.fixture_list(eire)["rows"]
        world = model.state.campaign.world
        self.assertEqual([r["fixture_id"] for r in rows],
                         [f.fixture_id for f in world.fixtures if eire in (f.side_a, f.side_b)])
        self.assertIsNone(model.fixture_list(eire)["round"])
        with self.assertRaises(ValueError):
            model.fixture_list(0)

    def test_the_tournament_is_the_routes_tables(self):
        model = career()
        view = model.tournament()
        self.assertEqual(view["stage"], 2)
        self.assertEqual(len(view["groups"]), 32)
        own = [g for g in view["groups"] if g["managed"]]
        self.assertEqual(len(own), 1)
        table = model.competition_table()
        self.assertEqual(own[0]["rows"], table["rows"], "the managed group is competition_table's")
        self.assertEqual((own[0]["continent"], own[0]["group"]), (table["continent"], table["group"]))
        route = continental_qualifying.tables(model.state.campaign, model.template_bytes)
        for group, theirs in zip(view["groups"], route):
            self.assertEqual((group["continent"], group["group"]), (theirs["continent"], theirs["group"]))
            self.assertEqual([r["country"] for r in group["rows"]], [r.country for r in theirs["rows"]])
            self.assertEqual([r["points"] for r in group["rows"]], [r.points for r in theirs["rows"]])
            self.assertEqual(len(group["matches"]), 12, "a double round robin of four")
            self.assertTrue(all(m["score"] is None for m in group["matches"]), "nothing played yet")

    def test_the_history_is_this_careers_results(self):
        model = career()
        self.assertEqual(model.history(), [{"season": "2027/28", "year": 2028, "competition": "EC", "won": 0,
                                            "drawn": 0, "lost": 0, "goals_for": 0, "goals_against": 0,
                                            "results": [], "best": "qualifying"}])
        played = played_round(career())
        result = played.state.campaign.results[0]
        seasons = played.history()
        self.assertEqual(len(seasons), 1)
        shown = seasons[0]["results"]
        names = played.goaldat.country_names
        self.assertEqual(shown, [{"fixture_id": result["fixture_id"], "first_name": names[result["teams"][0]],
                                  "second_name": names[result["teams"][1]], "score": result["score"],
                                  "kind_name": "friendly"}])
        self.assertEqual((seasons[0]["won"], seasons[0]["drawn"], seasons[0]["lost"]), (0, 0, 0),
                         "the season's row counts the competition, not the friendly")

    def test_the_competitions_name(self):
        model = career()
        self.assertEqual(model.continent(), 1)
        self.assertEqual(model.competition(), {"year": 2028, "name": "European Championship", "phase": "QUALIFYING"})
        self.assertEqual(model.competition(2, "FINALS")["name"], "American Championship")
        american = next(n for n, *_ in model.countries() if model.continent(n) == 2)
        other = career(american)
        self.assertEqual(other.competition()["name"], "American Championship")

    def test_the_calls_change_nothing(self):
        model = career()
        before = copy.deepcopy(model.state)
        for call in (model.fixture_list, model.tournament, model.history, model.competition, model.continent):
            call()
        model.fixture_list(8)
        self.assertEqual(model.state, before)


class App(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])
        cls.font_before = cls.app.font()

    @classmethod
    def tearDownClass(cls):
        cls.app.setFont(cls.font_before)

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="goal2-t178-ui-"))
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.target = data_setup.Paths(self.tmp / "goal2")
        self.target.data.mkdir(parents=True, exist_ok=True)
        for name, _ in data_setup.WINDOW_MANIFEST:
            shutil.copyfile(CACHE / name, self.target.data / name)

    def desk(self, model):
        window = Window(self.target)
        window.resize(fixed_page.WIDTH, fixed_page.HEIGHT)
        window.show()
        self.app.processEvents()
        self.addCleanup(lambda: (window.close(), window.deleteLater(), self.app.processEvents()))
        return window, window.open_career(model)

    def key(self, window, key, times=1):
        for _ in range(times):
            QTest.keyClick(window, key)
            self.app.processEvents()

    def click(self, widget):
        QTest.mouseClick(widget, Qt.MouseButton.LeftButton)
        self.app.processEvents()

    def open(self, window, desk, index, kind):
        while desk.cursor != index:
            self.key(window, Qt.Key.Key_Down if desk.cursor < index else Qt.Key.Key_Up)
        self.key(window, Qt.Key.Key_Return)
        screen = window.current()
        self.assertIsInstance(screen, kind)
        self.app.processEvents()
        self.assertEqual(fixed_page.problems(window), [])
        return screen

    def back_to_desk(self, window, desk):
        self.key(window, Qt.Key.Key_Escape)
        self.assertIs(window.current(), desk)
        self.assertEqual(window.stack, [desk])

    def bar(self, screen):
        return dict((caps, text) for caps, text in screen.key_texts())


@CAREER
class Fixtures(App):
    def test_the_round_with_its_kinds_and_your_own_ticked(self):
        model = played_round(career())   # round 2 is longer than the screen
        window, desk = self.desk(model)
        screen = self.open(window, desk, 1, FixturesScreen)
        rows = model.fixture_list()["rows"]
        self.assertGreater(len(rows), VISIBLE)
        names = model.goaldat.country_names
        world = {f.fixture_id: f for f in model.state.campaign.world.fixtures}
        self.assertIn("ROUND 2", screen.heading().upper())
        shown = []
        for index in range(len(rows)):   # ↓ moves the highlight through the whole round, the list scrolling
            self.assertEqual(screen.index, index)
            highlighted = screen.rows[screen.index - screen.top]
            self.assertTrue(highlighted.on and not highlighted.isHidden())
            shown.append(tuple(highlighted.texts()))
            self.key(window, Qt.Key.Key_Down)
        self.assertEqual(screen.index, len(rows) - 1, "the last row stays highlighted")
        self.assertGreater(screen.top, 0, "the list scrolled")
        for row, data in zip(shown, rows):
            fixture = world[data["fixture_id"]]
            self.assertEqual(row[1:4], (names[fixture.side_a], "v", names[fixture.side_b]))
            self.assertEqual(row[4], {1: "friendly", 2: "qualifying"}[fixture.kind], "the model's kind")
            own = HOLLAND in (fixture.side_a, fixture.side_b)
            self.assertEqual(row[0], CHECK if own else "")
            self.assertEqual(row[5], "your match" if own else "auto result")
        self.assertEqual(sum(1 for row in shown if row[0] == CHECK), 1)
        self.assertEqual(self.bar(screen)[("↑", "↓")], "scroll")
        self.assertEqual(self.bar(screen)[("Esc",)], "desk")
        self.key(window, Qt.Key.Key_Up, 3)
        self.assertEqual(screen.index, len(rows) - 4)
        self.back_to_desk(window, desk)

    def test_enter_on_each_kind_of_row(self):
        model = career()
        window, desk = self.desk(model)
        screen = self.open(window, desk, 1, FixturesScreen)
        rows = model.fixture_list()["rows"]
        before = copy.deepcopy(model.state)
        # Another country's match: no toggle, Enter says it comes later.
        self.assertFalse(rows[0]["own"])
        self.assertEqual(screen.enter_text.text(), "Watch match: later")
        self.key(window, Qt.Key.Key_Return)
        self.assertIn("comes later", screen.note.text())
        self.assertEqual(screen.shown_rows()[0][0], "", "no ✓ appears")
        # Your own friendly: cancel or rearrange comes later.
        own = next(i for i, r in enumerate(rows) if r["own"])
        self.assertEqual(rows[own]["kind"], 1)
        self.key(window, Qt.Key.Key_Down, own)
        self.assertEqual(screen.enter_text.text(), "Cancel or rearrange: later")
        self.key(window, Qt.Key.Key_Return)
        self.assertIn("rearranging your own friendly comes later", screen.note.text())
        # A click on a row highlights it; a click on the highlighted row is Enter.
        self.click(screen.rows[0])
        self.assertEqual(screen.index, screen.top)
        self.click(screen.rows[0])
        self.assertIn("comes later", screen.note.text())
        self.assertEqual(model.state, before, "S11 changes nothing")
        self.back_to_desk(window, desk)

    def test_your_own_qualifier_is_always_watched(self):
        model = played_round(career())
        window, desk = self.desk(model)
        screen = self.open(window, desk, 1, FixturesScreen)
        self.assertIn("ROUND 2", screen.heading().upper())
        first = screen.shown_rows()[0]
        self.assertEqual((first[0], first[4], first[5]), (CHECK, "qualifying", "your match"))
        self.assertEqual(screen.enter_text.text(), "Watch match")
        self.key(window, Qt.Key.Key_Return)
        self.assertIn("always watched", screen.note.text())

    def test_team_infos_enter_opens_that_countrys_fixtures(self):
        model = career()
        window, desk = self.desk(model)
        self.key(window, Qt.Key.Key_Return)
        team = window.current()
        self.assertIsInstance(team, TeamInfoScreen)
        number, name = team.chosen()
        self.key(window, Qt.Key.Key_Return)
        screen = window.current()
        self.assertIsInstance(screen, FixturesScreen)
        self.assertEqual(fixed_page.problems(window), [])
        expected = model.fixture_list(number)["rows"]
        self.assertTrue(all(name in (row[1], row[3]) for row in screen.shown_rows()))
        self.assertEqual(len(screen.shown_rows()), min(VISIBLE, len(expected)))
        self.assertEqual(self.bar(screen)[("Esc",)], "team info")
        self.key(window, Qt.Key.Key_Escape)
        self.assertIs(window.current(), team)
        self.key(window, Qt.Key.Key_Escape)
        self.assertIs(window.current(), desk)


@CAREER
class Tournament(App):
    def test_the_managed_group_is_competition_table(self):
        model = career()
        window, desk = self.desk(model)
        screen = self.open(window, desk, 2, TournamentScreen)
        table = model.competition_table()
        self.assertEqual(screen.table(), [(r["name"], str(r["played"]), str(r["won"]), str(r["drawn"]),
                                           str(r["lost"]), str(r["goals_for"]), str(r["goals_against"]),
                                           str(r["points"])) for r in table["rows"]], "row by row")
        self.assertEqual(TABS[screen.tab][0], table["continent"])
        self.assertIn(f"GROUP {'ABCDEFGH'[table['group'] - 1]}", screen.table_heading.text())
        group = next(g for g in model.tournament()["groups"] if g["managed"])
        self.assertEqual(screen.matches(), [(m["first_name"], "v", m["second_name"]) for m in group["matches"]])
        self.assertIn("European Championship", screen.banner.text())
        self.assertIn("QUALIFYING", screen.banner.text())
        bar = self.bar(screen)
        for caps, text in ((("↑", "↓"), "group"), (("Space",), "continent"), (("←", "→"), "display"),
                           (("Ins",), "Championship results"), (("Esc",), "desk")):
            self.assertEqual(bar.get(caps), text, caps)
        self.back_to_desk(window, desk)

    def test_groups_continents_and_displays(self):
        model = career()
        window, desk = self.desk(model)
        screen = self.open(window, desk, 2, TournamentScreen)
        route = continental_qualifying.tables(model.state.campaign, model.template_bytes)
        names = model.goaldat.country_names

        def expect(continent, group):
            theirs = next(g for g in route if (g["continent"], g["group"]) == (continent, group))
            self.assertEqual([row[0] for row in screen.table()], [names[r.country] for r in theirs["rows"]])

        start = screen.group
        self.key(window, Qt.Key.Key_Up)
        self.assertEqual(screen.group, start - 1)
        expect(1, start)
        self.key(window, Qt.Key.Key_Down, 2)
        expect(1, start + 2)
        self.key(window, Qt.Key.Key_Space)   # Africa, the tab after Europe
        self.assertEqual(TABS[screen.tab][1], "Africa")
        expect(3, start + 2)
        self.assertIn("African Championship", screen.banner.text())
        self.key(window, Qt.Key.Key_Space)
        self.assertEqual(TABS[screen.tab][1], "Americas")
        expect(2, start + 2)
        self.assertIn("American Championship", screen.banner.text())
        self.click(screen.continent_tabs[0])
        self.assertEqual(TABS[screen.tab][1], "Europe")
        # Finals and Championship: not reached yet, no rows.
        before = copy.deepcopy(model.state)
        for display in ("FINALS", "CHAMPIONSHIP"):
            self.key(window, Qt.Key.Key_Right)
            self.assertIn(f"{display} · NOT REACHED YET", screen.table_heading.text())
            self.assertEqual(screen.table(), [])
            self.assertEqual(screen.matches(), [])
            self.assertIn("FINALS", screen.banner.text())
            self.assertEqual(fixed_page.problems(window), [])
        self.key(window, Qt.Key.Key_Insert)
        self.assertIn("not reach", screen.message_label.text())
        self.key(window, Qt.Key.Key_Left, 2)
        self.assertEqual(screen.display, 0)
        expect(1, start + 2)
        self.click(screen.display_tabs[1])
        self.assertEqual(screen.display, 1)
        self.assertEqual(model.state, before, "read only")
        self.back_to_desk(window, desk)


@CAREER
class History(App):
    def test_a_recorded_result_is_shown_and_the_boxes_without_a_source_say_so(self):
        model = played_round(career())
        result = model.state.campaign.results[0]
        names = model.goaldat.country_names
        window, desk = self.desk(model)
        screen = self.open(window, desk, 3, HistoryScreen)
        lines = screen.shown_texts()
        self.assertEqual(lines[0][:2], ("2027/28", "EC"))
        self.assertEqual(lines[0][-1], "qualifying")
        self.assertEqual(lines[1], ("", names[result["teams"][0]], f"{result['score'][0]} v {result['score'][1]}",
                                    names[result["teams"][1]], "friendly"), "the recorded result")
        for box in ("statistics", "successes", "scorers", "caps", "records"):
            text = screen.later[box].text()
            self.assertIn("Kept from a later version", text, box)
            self.assertIn("#509", text, box)
        self.assertIn("Holland", screen.name_label.text())
        self.assertEqual(self.bar(screen)[("Esc",)], "desk")
        self.back_to_desk(window, desk)

    def test_a_new_career_shows_its_season_and_no_result(self):
        model = career()
        window, desk = self.desk(model)
        screen = self.open(window, desk, 3, HistoryScreen)
        self.assertEqual(screen.shown_texts(), [("2027/28", "EC", "0", "0", "0", "0", "0", "qualifying")])


@CAREER
class Desk(App):
    def test_the_banner_names_the_competition(self):
        window, desk = self.desk(career())
        self.assertIn("European Championship", desk.banner.text())
        self.assertIn("2028", desk.banner.text())
        self.assertIn("QUALIFYING", desk.banner.text())
        self.assertNotIn("Continental", desk.banner.text())

    def test_the_banner_of_an_american_country(self):
        model = career()
        american = next(n for n, *_ in model.countries() if model.continent(n) == 2)
        window, desk = self.desk(career(american))
        self.assertIn("American Championship", desk.banner.text())

    def test_the_three_options_open_their_screens_from_a_loaded_save(self):
        model = played_round(career())
        saves.write(model, self.target.saves, "Holland round 2")
        window = Window(self.target)
        window.resize(fixed_page.WIDTH, fixed_page.HEIGHT)
        window.show()
        self.addCleanup(lambda: (window.close(), window.deleteLater(), self.app.processEvents()))
        window.start()
        self.key(window, Qt.Key.Key_Return)
        desk = window.current()
        self.assertIsInstance(desk, DeskScreen)
        for index, kind in ((1, FixturesScreen), (2, TournamentScreen), (3, HistoryScreen)):
            screen = self.open(window, desk, index, kind)
            self.assertNotIn("T178", desk.note.text(), "no placeholder")
            if kind is HistoryScreen:
                self.assertEqual(len(screen.shown_texts()), 2, "the loaded save's result")
            self.back_to_desk(window, desk)


if __name__ == "__main__":
    unittest.main()
