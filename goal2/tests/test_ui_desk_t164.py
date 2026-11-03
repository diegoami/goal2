"""[designed: owner, 2026-11-03, #526, #527; T164, #538, #555, #559] The manager's desk (S06) and team info (S07).

The claim it protects: from the desk the player reaches everything the original's hub offers, and chooses the eleven.
Visited here: a new career and a loaded save land on S06 with the cursor on *team info*, the six options and the
F-keys of the design; each option opens its screen or names the task that brings it; Esc returns to the desk from S07,
S08, S10, S01 and (T178) S11, S12, S13; S08's swap within the twenty is the model's (`DesktopModel.swap`), the same
eleven and bench as today's Team swap through `confirm`, and it moves an injured starter to the bench so the eleven is
playable; S07's card, next opponent, Ins, Space and T; S04's list in the ranking Ins selects (#559) and Holland's
average age, 28, as the original's capture shows it (t156-005-country-holland).

The careers read GOAL.DAT and the E010 half-time template from the git-ignored `.cache/` and skip without them
(goal2/tests/requires.py); nothing of the original is in this file (CLAUDE.md rule 14).
"""
import copy
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from goal2.tests import requires

requires.require(modules=("PySide6",))

from PySide6.QtCore import Qt  # noqa: E402
from PySide6.QtTest import QTest  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from goal2.desktop import data_setup, fixed_page  # noqa: E402
from goal2.desktop.model import DesktopModel  # noqa: E402
from goal2.game import eligibility  # noqa: E402
from goal2.game.country_card import card as country_card  # noqa: E402
from goal2.ui import s03_new_game, s04_country, saves  # noqa: E402
from goal2.ui.s01_import import ImportScreen  # noqa: E402
from goal2.ui.s02_start import StartScreen  # noqa: E402
from goal2.ui.s04_country import CountryScreen  # noqa: E402
from goal2.ui.s06_desk import DeskScreen, ReimportScreen  # noqa: E402
from goal2.ui.s07_team_info import CountryTacticsScreen, TeamInfoScreen, TeamPlayersScreen  # noqa: E402
from goal2.ui.s08_squad import SquadScreen  # noqa: E402
from goal2.ui.s10_team_tactics import TeamTacticsScreen  # noqa: E402
from goal2.ui.s11_fixtures import FixturesScreen  # noqa: E402
from goal2.ui.s12_tournament import TournamentScreen  # noqa: E402
from goal2.ui.s13_history import HistoryScreen  # noqa: E402
from goal2.ui.s22_help import HelpScreen  # noqa: E402
from goal2.ui.screen import Clickable  # noqa: E402
from goal2.ui.squad_card import full_name, squad_rows  # noqa: E402
from goal2.ui.window import Window  # noqa: E402

CACHE = requires.CACHE
CAREER = requires.need(**requires.HALFTIME)
HOLLAND = 20
SIX = ["team info", "fixture list", "tournament", "history", "select squad", "play next game"]
_BASE = {}


def holland():
    """A fresh copy of one Holland career starting in 2028, the capture's (opened once per run)."""
    if "model" not in _BASE:
        folder = tempfile.mkdtemp(prefix="goal2-t164-")
        _BASE["folder"] = folder
        model = DesktopModel.open(CACHE / data_setup.TEMPLATE_NAME, CACHE / data_setup.DATA_NAME,
                                  Path(folder) / "unused.g2game", country=HOLLAND)
        model.new_campaign(HOLLAND, 2028)
        model.rename_manager("K Ees")
        _BASE["model"] = model
    return copy.deepcopy(_BASE["model"])


def tearDownModule():
    if "folder" in _BASE:
        shutil.rmtree(_BASE["folder"], ignore_errors=True)


def todays_team_swap(model, out, incoming):
    """Today's Team swap on the Python route (goal2/desktop/squad_page.py `toggle`, window.py `drafted_eleven` and
    `confirm_draft`): the XI checks lose `out` and gain `incoming`, the drafted eleven keeps the stored order and
    appends the new player, and `DesktopModel.confirm` publishes it with the captain the draft's list offers (the
    stored one if he is still in the eleven, else the first of it) and the tactics."""
    state = model.state
    selected = [w for w in state.starting_eleven if w != out] + [incoming]
    stored = state.starting_eleven
    eleven = [w for w in stored if w in selected] + [w for w in selected if w not in stored]
    captain = state.captain if state.captain in eleven else eleven[0]
    model.confirm(eleven, captain, state.country_tactics)


def injure(model, word):
    """Make `word` injured, as the energy adapter leaves him: energy +14 at 0 [derived: eligibility.reasons]."""
    record = bytearray(model.state.players[word])
    record[14] = 0
    model.state.players = list(model.state.players)
    model.state.players[word] = bytes(record)


@CAREER
class Swap(unittest.TestCase):
    """The model's new call, `swap`, against the original's order and today's Team swap."""

    def setUp(self):
        self.model = holland()

    def test_a_starter_and_a_bench_player_swap_in_place(self):
        state = self.model.state
        out, incoming = state.starting_eleven[3], next(w for w in state.managed_squad if w not in state.starting_eleven)
        before = list(state.starting_eleven)
        today = copy.deepcopy(self.model)
        self.assertEqual(self.model.swap(out, incoming), before[:3] + [incoming] + before[4:],
                         "the incoming player takes the starter's place in the eleven (m244-squad)")
        todays_team_swap(today, out, incoming)
        self.assertEqual(set(self.model.state.starting_eleven), set(today.state.starting_eleven))
        self.assertEqual(squad_rows(self.model)[0][11:], squad_rows(today)[0][11:], "the same bench")
        self.assertEqual(self.model.view(), today.view())

    def test_two_starters_change_places_and_the_captain_follows_the_incoming_player(self):
        state = self.model.state
        a, b = state.starting_eleven[1], state.starting_eleven[9]
        self.model.swap(a, b)
        eleven = self.model.state.starting_eleven
        self.assertEqual((eleven[1], eleven[9]), (b, a))
        self.model.confirm(list(eleven), eleven[2], state.country_tactics)
        captain = eleven[2]
        incoming = next(w for w in state.managed_squad if w not in eleven)
        self.model.swap(incoming, captain)
        self.assertEqual(self.model.state.captain, incoming, "a captain who leaves is replaced by the incoming player")
        self.assertEqual(self.model.state.starting_eleven[2], incoming)

    def test_bad_requests_change_nothing(self):
        state = self.model.state
        bench = [w for w in state.managed_squad if w not in state.starting_eleven]
        foreign = next(w for w in range(1, 2561) if w not in state.managed_squad)
        for first, second in ((bench[0], bench[1]), (state.starting_eleven[0], state.starting_eleven[0]),
                              (state.starting_eleven[0], foreign), (True, bench[0])):
            before = copy.deepcopy(self.model.state)
            with self.assertRaises(ValueError):
                self.model.swap(first, second)
            self.assertEqual(self.model.state, before)

    def test_injured_starters_go_to_the_bench_one_swap_at_a_time(self):
        state = self.model.state
        hurt = state.starting_eleven[4], state.starting_eleven[7]
        for word in hurt:
            injure(self.model, word)
        with self.assertRaises(ValueError):
            eligibility.require_available(self.model.state.players, self.model.state.starting_eleven)
        bench = [w for w in state.managed_squad if w not in state.starting_eleven]
        self.model.swap(hurt[0], bench[0])
        with self.assertRaises(ValueError, msg="one injured starter is still in"):
            eligibility.require_available(self.model.state.players, self.model.state.starting_eleven)
        self.model.swap(bench[1], hurt[1])
        eligibility.require_available(self.model.state.players, self.model.state.starting_eleven)


class App(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])
        cls.font_before = cls.app.font()

    @classmethod
    def tearDownClass(cls):
        cls.app.setFont(cls.font_before)

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="goal2-t164-ui-"))
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.target = data_setup.Paths(self.tmp / "goal2")
        clock = mock.patch.object(s03_new_game, "clock_year", return_value=2026)   # 2028, the capture's start
        clock.start()
        self.addCleanup(clock.stop)
        self.target.data.mkdir(parents=True, exist_ok=True)
        for name, _ in data_setup.WINDOW_MANIFEST:
            shutil.copyfile(CACHE / name, self.target.data / name)

    def window(self):
        window = Window(self.target, choose=lambda: getattr(self, "offered", None))
        window.resize(fixed_page.WIDTH, fixed_page.HEIGHT)
        window.show()
        self.app.processEvents()
        self.addCleanup(lambda: (window.close(), window.deleteLater(), self.app.processEvents()))
        return window

    def key(self, window, key, times=1):
        for _ in range(times):
            QTest.keyClick(window, key)
            self.app.processEvents()

    def click(self, widget):
        QTest.mouseClick(widget, Qt.MouseButton.LeftButton)
        self.app.processEvents()

    def fits(self, window):
        self.app.processEvents()
        self.assertEqual(fixed_page.problems(window), [])

    def to_country_screen(self, window):
        window.start()
        self.key(window, Qt.Key.Key_N)
        self.key(window, Qt.Key.Key_Return)
        screen = window.current()
        self.assertIsInstance(screen, CountryScreen)
        return screen

    def new_career(self, window):
        """S02 → S03 → S04 on Holland (two Downs, as T156-R1 steps 3–5) → a name → the desk."""
        screen = self.to_country_screen(window)
        self.key(window, Qt.Key.Key_Down, 2)
        screen.settle()
        self.assertEqual(screen.chosen(), (HOLLAND, "Holland"))
        self.key(window, Qt.Key.Key_Return)
        QTest.keyClicks(window, "K Ees")
        self.key(window, Qt.Key.Key_Return)
        return window.current()

    def desk(self, model=None):
        window = self.window()
        return window, window.open_career(model or holland())

    def assertDesk(self, window, desk):
        self.assertIsInstance(desk, DeskScreen)
        self.assertIs(window.current(), desk)
        self.assertEqual(window.stack, [desk], "the desk is the home: nothing under it")

    def bar(self, screen):
        return dict((caps, text) for caps, text in screen.key_texts())


@CAREER
class Landing(App):
    def check_landing(self, window, desk, model):
        self.assertDesk(window, desk)
        self.assertIs(desk.model, model)
        self.assertEqual(desk.cursor, 0)
        self.assertEqual(desk.highlighted().text_label.text(), "team info", "the cursor starts on team info")
        self.assertEqual(desk.enter_text.text(), "Team info")
        self.assertEqual([o.text_label.text() for o in desk.options][:6], SIX, "the six options, in order")
        bar = self.bar(desk)
        for caps, text in ((("F1",), "help"), (("F3",), "load goal"), (("F4",), "load summary"), (("F7",), "save"),
                           (("F10",), "quit"), (("T",), "team tactics"), (("↑", "↓"), "choose")):
            self.assertEqual(bar.get(caps), text, caps)
        self.assertNotIn(("Esc",), bar, "the desk is the home")
        self.assertEqual(desk.options[4].key, Qt.Key.Key_Space, "Space is on select squad")
        state = model.state
        self.assertEqual(desk.team_name.text(), "Holland")
        self.assertEqual((desk.team_ranks["world"].text(), desk.team_ranks["continent"].text()), ("14", "3"),
                         "Holland's world 14 and Europe 3, as t156-013-hub")
        self.assertEqual(desk.team_ranks["continent"].caption.text(), "Europe")
        self.assertEqual(desk.manager["name"].text(), "K Ees")
        self.assertEqual(desk.manager["rating"].text(), "unknown")
        fixture = state.campaign.next_fixture
        opponent = fixture.side_b if fixture.side_a == HOLLAND else fixture.side_a
        card = country_card(state, opponent, model.goaldat)
        self.assertEqual(desk.opponent_name.text(), card["name"])
        self.assertEqual(desk.opponent_ranks["world"].text(), str(card["world"]))
        self.assertEqual(desk.opponent_ranks["continent"].text(), str(card["continental"]))
        self.assertEqual(desk.opponent_ranks["match"].text(), "friendly")
        self.assertIn("1 · K Ees", desk.managers.text())
        rows, eleven = squad_rows(model)
        self.assertEqual(eleven, 11)
        self.assertEqual([t[0] for t in desk.strip.shown_texts()], [r["role"] for r in rows],
                         "the twenty's role codes, the eleven above the bench")
        self.assertTrue(desk.strip.gap.isVisibleTo(desk.strip))
        # [T178, #563] the competition's name, as the original's hub: European Championship, QUALIFYING.
        self.assertIn("European Championship", desk.banner.text())
        self.assertIn("QUALIFYING", desk.banner.text())
        self.fits(window)

    def test_a_new_career_lands_on_the_desk(self):
        window = self.window()
        desk = self.new_career(window)
        self.check_landing(window, desk, window.career)

    def test_a_loaded_save_lands_on_the_desk(self):
        model = holland()
        saves.write(model, self.target.saves, "Holland 2028")
        window = self.window()
        window.start()
        self.assertIsInstance(window.current(), StartScreen)
        self.key(window, Qt.Key.Key_Return)
        self.check_landing(window, window.current(), window.career)
        self.assertEqual(window.career.state, model.state)


@CAREER
class Options(App):
    def test_each_option_opens_its_screen_or_names_its_task(self):
        window, desk = self.desk()
        # [T166, the interim route] play next game: a qualifier says it comes with T176 and T167 and changes nothing;
        # the next friendly starts on S17 (under PyPy 3.11; without it the desk says why it cannot start).
        # [T178: fixture list, tournament and history are screens now, visited below]
        import dataclasses
        from goal2.game.campaign import CampaignState
        from goal2.ui.s17_pitch import PitchScreen
        while desk.cursor < 5:
            self.key(window, Qt.Key.Key_Down)
        self.assertEqual(desk.highlighted().text_label.text(), SIX[5])
        friendly = desk.model.state.campaign.next_fixture
        self.assertEqual(friendly.kind, 1, "the 2028 Holland career opens on a friendly")
        before = copy.deepcopy(desk.model.state)
        qualifier = dataclasses.replace(friendly, kind=2)
        with mock.patch.object(CampaignState, "next_fixture", new_callable=mock.PropertyMock, return_value=qualifier):
            self.key(window, Qt.Key.Key_Return)
        self.assertIs(window.current(), desk)
        self.assertIn("T176", desk.note.text())
        self.assertIn("T167", desk.note.text())
        self.assertEqual(desk.model.state, before)
        try:
            from goal2.tests.test_pypy_worker_t152 import pypy
            pypy()
            engine = True
        except unittest.SkipTest:
            engine = False
        self.key(window, Qt.Key.Key_Return)
        if engine:
            screen = window.current()
            self.assertIsInstance(screen, PitchScreen)
            self.assertEqual(screen.controller.pending, friendly)
            screen.closing()
            window.pop()
            self.assertIsNone(desk.model.state.last_match, "a cancelled match publishes nothing")
        else:
            self.assertIs(window.current(), desk)
            self.assertIn("cannot start", desk.note.text())
        self.assertIs(window.current(), desk)
        for key, task in ((Qt.Key.Key_F3, "T167"), (Qt.Key.Key_F4, "T181")):
            self.key(window, key)
            self.assertIs(window.current(), desk)
            self.assertIn(task, desk.note.text())
        # [T168] F7 opens S21's name box and F10 its quit question; Esc and N return to the desk.
        from goal2.ui.s21_save import QuestionScreen, SaveScreen
        self.key(window, Qt.Key.Key_F7)
        self.assertIsInstance(window.current(), SaveScreen)
        self.key(window, Qt.Key.Key_Escape)
        self.assertIs(window.current(), desk)
        self.key(window, Qt.Key.Key_F10)
        self.assertIsInstance(window.current(), QuestionScreen)
        self.key(window, Qt.Key.Key_N)
        self.assertIs(window.current(), desk)
        self.assertTrue(window.isVisible(), "F10, N stays")
        # The screens, each by its key, and Esc back to the desk.
        self.key(window, Qt.Key.Key_Up, 5)
        self.assertEqual(desk.cursor, 0)
        for key, kind in ((Qt.Key.Key_Return, TeamInfoScreen), (Qt.Key.Key_Space, SquadScreen),
                          (Qt.Key.Key_T, TeamTacticsScreen), (Qt.Key.Key_F1, HelpScreen)):
            self.key(window, key)
            self.assertIsInstance(window.current(), kind)
            self.fits(window)
            self.key(window, Qt.Key.Key_Escape)
            self.assertDesk(window, desk)
        # [T178] fixture list, tournament and history open S11, S12 and S13; Esc returns to the desk.
        for index, kind in ((1, FixturesScreen), (2, TournamentScreen), (3, HistoryScreen)):
            while desk.cursor != index:
                self.key(window, Qt.Key.Key_Down if desk.cursor < index else Qt.Key.Key_Up)
            self.key(window, Qt.Key.Key_Return)
            self.assertIsInstance(window.current(), kind)
            self.fits(window)
            self.key(window, Qt.Key.Key_Escape)
            self.assertDesk(window, desk)
        self.key(window, Qt.Key.Key_Up, 5)
        # Enter on select squad is Space.
        while desk.cursor != 4:
            self.key(window, Qt.Key.Key_Down if desk.cursor < 4 else Qt.Key.Key_Up)
        self.key(window, Qt.Key.Key_Return)
        self.assertIsInstance(window.current(), SquadScreen)
        self.key(window, Qt.Key.Key_Escape)
        self.assertDesk(window, desk)

    def test_the_mouse_does_what_the_keys_do(self):
        window, desk = self.desk()
        self.click(desk.options[2])
        self.assertEqual(desk.cursor, 2)
        self.assertIsInstance(window.current(), TournamentScreen, "T178: the tournament, S12")
        self.key(window, Qt.Key.Key_Escape)
        self.click(desk.options[0])
        self.assertIsInstance(window.current(), TeamInfoScreen)
        self.key(window, Qt.Key.Key_Escape)
        item = next(i for i in desk.key_bar.findChildren(Clickable, "keyItem") if i.binding.text == "team tactics")
        self.click(item)
        self.assertIsInstance(window.current(), TeamTacticsScreen)
        self.key(window, Qt.Key.Key_Escape)
        self.click(desk.options[4])
        self.assertIsInstance(window.current(), SquadScreen)
        self.key(window, Qt.Key.Key_Escape)
        self.assertDesk(window, desk)

    def test_reimport_opens_s01_over_the_data_folder_and_esc_returns(self):
        window, desk = self.desk()
        reimport = desk.options[-1]
        self.assertEqual(reimport.text_label.text(), "re-import data")
        self.click(reimport)
        screen = window.current()
        self.assertIsInstance(screen, ImportScreen)
        self.assertIsInstance(screen, ReimportScreen)
        self.assertEqual(screen.folder, self.target.data, "S01 over the data folder")
        self.assertIn("found, verified", screen.check_text(data_setup.DATA_NAME))
        self.assertEqual(self.bar(screen).get(("Esc",)), "desk")
        self.fits(window)
        self.key(window, Qt.Key.Key_Escape)
        self.assertDesk(window, desk)
        self.assertTrue(window.isVisible(), "Esc on the re-import returns, it does not quit")
        # Choosing a folder imports it by data_setup's rules and returns to the desk.
        self.offered = str(self.target.data)
        window.push(ReimportScreen(window, self.target, window.choose))
        self.key(window, Qt.Key.Key_Return)
        self.assertDesk(window, desk)


@CAREER
class SquadSwap(App):
    def squad(self, model):
        window, desk = self.desk(model)
        self.key(window, Qt.Key.Key_Space)
        screen = window.current()
        self.assertIsInstance(screen, SquadScreen)
        return window, desk, screen

    def to_row(self, window, screen, index):
        while screen.cursor["squad"] < index:
            self.key(window, Qt.Key.Key_Down)
        while screen.cursor["squad"] > index:
            self.key(window, Qt.Key.Key_Up)
        return screen.current()

    def test_enter_enter_on_a_starter_and_a_bench_player_is_todays_team_swap(self):
        model = holland()
        today = copy.deepcopy(model)
        window, desk, screen = self.squad(model)
        out = self.to_row(window, screen, 3)
        self.key(window, Qt.Key.Key_Return)
        self.assertEqual(screen.enter_text.text(), "Put here")
        incoming = self.to_row(window, screen, 14)
        self.assertNotIn(incoming, model.state.starting_eleven)
        self.key(window, Qt.Key.Key_Return)
        self.assertIsNone(screen.picked)
        todays_team_swap(today, out, incoming)
        self.assertEqual(set(model.state.starting_eleven), set(today.state.starting_eleven), "the same eleven")
        self.assertEqual(squad_rows(model)[0][11:], squad_rows(today)[0][11:], "the same bench")
        self.assertEqual(model.view(), today.view())
        self.assertEqual(model.state.starting_eleven.index(incoming), 3, "in the starter's place (m244-squad)")
        self.assertEqual(screen.strip.shown_texts(), [list(r) for r in strip_rows(model)])
        self.assertEqual(strip_rows(model)[3][1], full_name(model, incoming))
        self.key(window, Qt.Key.Key_Escape)
        self.assertDesk(window, desk)
        self.assertEqual(desk.strip.shown_texts(), [list(r) for r in strip_rows(model)], "the desk shows the new eleven")

    def test_an_injured_starter_goes_to_the_bench_and_the_eleven_is_playable(self):
        model = holland()
        hurt = model.state.starting_eleven[6]
        injure(model, hurt)
        with self.assertRaises(ValueError):
            eligibility.require_available(model.state.players, model.state.starting_eleven)
        window, desk, screen = self.squad(model)
        self.assertEqual(self.to_row(window, screen, 6), hurt)
        self.key(window, Qt.Key.Key_Return)
        self.to_row(window, screen, 12)
        self.key(window, Qt.Key.Key_Return)
        self.assertNotIn(hurt, model.state.starting_eleven)
        eligibility.require_available(model.state.players, model.state.starting_eleven)

    def test_two_bench_players_say_why_and_a_click_swaps_as_enter_does(self):
        model = holland()
        window, desk, screen = self.squad(model)
        before = copy.deepcopy(model.state)
        self.to_row(window, screen, 12)
        self.key(window, Qt.Key.Key_Return)
        self.to_row(window, screen, 15)
        self.key(window, Qt.Key.Key_Return)
        self.assertEqual(model.state, before)
        self.assertIn("bench players", screen.note.text())
        a, b = model.state.starting_eleven[0], model.state.starting_eleven[1]
        self.click(screen.strip.rows[0])
        self.click(screen.strip.rows[0])
        self.click(screen.strip.rows[1])
        self.click(screen.strip.rows[1])
        self.assertEqual(model.state.starting_eleven[:2], [b, a], "two starters change places")


def strip_rows(model):
    """The strip's rows as the original's order makes them: the eleven, then the bench."""
    rows, _ = squad_rows(model)
    return [(r["role"], full_name(model, r["id"])) for r in rows]


@CAREER
class TeamInfo(App):
    def test_a_country_card_the_next_opponent_ins_space_and_t(self):
        model = holland()
        window, desk = self.desk(model)
        self.key(window, Qt.Key.Key_Return)
        screen = window.current()
        self.assertIsInstance(screen, TeamInfoScreen)
        fixture = model.state.campaign.next_fixture
        opponent = fixture.side_b if fixture.side_a == HOLLAND else fixture.side_a
        name = model.goaldat.country_names[opponent]
        self.assertEqual(screen.chosen(), (opponent, name), "it opens on the next opponent, as the mockup")
        self.assertEqual(screen.card_view.name.text(), name)
        start = screen.index // 16 * 16
        self.assertEqual(screen.marks()[screen.index - start], "next opponent")
        self.assertEqual(sum(1 for m in screen.marks() if m), 1)
        self.assertEqual(screen.enter_text.text(), f"Fixtures of {name}")
        card = country_card(model.state, opponent, model.goaldat)
        self.assertEqual(screen.card_view.ranks["world"].text(), str(card["world"]))
        self.assertEqual(screen.card_view.tactics["defence system"].text(), card["team_tactics"][0][1])
        world = s04_country.ordered(model.countries(), False)
        self.assertEqual(screen.visible_names(), [c[1] for c in world[start:start + 16]], "world order, as m244")
        self.fits(window)
        # Ins: the continental order; the highlight stays on the same country.
        self.key(window, Qt.Key.Key_Insert)
        self.assertEqual(screen.chosen(), (opponent, name))
        continental = s04_country.ordered(model.countries(), True)
        start = screen.index // 16 * 16
        self.assertEqual(screen.visible_names(), [c[1] for c in continental[start:start + 16]])
        # Arrows choose another country, and its card follows.
        self.key(window, Qt.Key.Key_Down)
        screen.settle()
        other = screen.chosen()
        self.assertNotEqual(other[0], opponent)
        self.assertEqual(screen.card_view.name.text(), other[1])
        group = screen.index // 16
        self.key(window, Qt.Key.Key_Right)
        self.assertEqual(screen.index // 16, group + 1, "→ the next group of 16")
        self.key(window, Qt.Key.Key_Left)
        # Space: its twenty, read only.
        self.key(window, Qt.Key.Key_Space)
        players = window.current()
        self.assertIsInstance(players, TeamPlayersScreen)
        words = country_card(model.state, other[0], model.goaldat)["players"]
        self.assertEqual([c["id"] for c in players.cards], words)
        self.fits(window)
        self.key(window, Qt.Key.Key_Escape)
        self.assertIs(window.current(), screen)
        # T: another country's tactics, read only; your own, S10.
        before = copy.deepcopy(model.state)
        self.key(window, Qt.Key.Key_T)
        tactics = window.current()
        self.assertIsInstance(tactics, CountryTacticsScreen)
        self.assertEqual(len(tactics.lines()), 8)
        self.assertEqual(tactics.lines()[0], ("defence system", country_card(model.state, other[0],
                                                                             model.goaldat)["team_tactics"][0][1]))
        self.key(window, Qt.Key.Key_Return)
        self.assertEqual(model.state, before, "read only")
        self.fits(window)
        self.key(window, Qt.Key.Key_Escape)
        self.assertIs(window.current(), screen)
        while screen.chosen()[0] != HOLLAND:
            self.key(window, Qt.Key.Key_Up)
        self.key(window, Qt.Key.Key_T)
        self.assertIsInstance(window.current(), TeamTacticsScreen, "your own tactics: S10")
        self.key(window, Qt.Key.Key_Escape)
        self.assertIs(window.current(), screen)
        # Enter: the country's fixtures, S11 (T178); Esc back here. A click on a country highlights it.
        self.key(window, Qt.Key.Key_Return)
        self.assertIsInstance(window.current(), FixturesScreen)
        self.assertEqual(window.current().country, HOLLAND)
        self.key(window, Qt.Key.Key_Escape)
        self.assertIs(window.current(), screen)
        self.click(screen.rows[0])
        self.assertEqual(screen.index % 16, 0)
        self.key(window, Qt.Key.Key_Escape)
        self.assertDesk(window, desk)


@CAREER
class CountryOrder(App):
    def test_continental_then_world_as_the_capture(self):
        window = self.window()
        screen = self.to_country_screen(window)
        self.assertIn("CONTINENTAL RANK", screen.list_heading.text(), "the browser opens on continental (step 3)")
        self.assertEqual(screen.visible_names()[:3], ["Denmark", "Germany", "Holland"], "t156-005")
        self.assertEqual(screen.visible_ranks(), [str(n) for n in range(1, 17)])
        self.assertEqual(screen.chosen()[1], "Denmark", "it opens on Denmark (T156-R1 step 3)")
        self.key(window, Qt.Key.Key_Down, 2)
        self.assertEqual(screen.chosen(), (HOLLAND, "Holland"))
        self.key(window, Qt.Key.Key_Insert)
        self.assertIn("WORLD RANK", screen.list_heading.text())
        self.assertEqual(screen.chosen(), (HOLLAND, "Holland"), "Ins keeps the country")
        countries = screen.browser.countries()
        ranks = sorted(c[2] for c in countries)
        start = screen.index // 16 * 16
        self.assertEqual(screen.visible_ranks(), [str(r) for r in ranks[start:start + 16]], "world ranks, in order")
        self.key(window, Qt.Key.Key_Left)
        self.assertEqual(screen.visible_names()[:5], [c[1] for c in sorted(countries, key=lambda c: c[2])][:5])

    def test_hollands_average_age_is_28_in_the_captures_start_year(self):
        window = self.window()
        screen = self.to_country_screen(window)
        self.assertEqual(screen.start_year, 2028, "t156-005 starts in 2028")
        self.key(window, Qt.Key.Key_Down, 2)
        screen.settle()
        self.assertEqual(screen.chosen()[1], "Holland")
        self.assertEqual(screen.averages.text(), "average caps 0 · age 28", "as t156-005-country-holland")
        from goal2.game.player_card import card
        cards = [card(screen.browser.state, w, screen.browser.goaldat) for w in screen.browser.state.managed_squad]
        self.assertEqual(sum(c["age"] for c in cards) // 20, 28, "the cards' ages, cut to a whole number")
