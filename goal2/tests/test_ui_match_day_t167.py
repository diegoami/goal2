"""[designed: owner, 2026-11-03, #526 decisions 1 and 3, #527 D3; T167, #541, #562] The match day in the new window.

The claim it protects: the match day the player goes through is the original's order of screens, and every answer
given on them is the answer the engine receives. Visited offscreen on a 2028 Holland career (its first fixture the
friendly Romania v Holland, its second the qualifier Eire v Holland), in one window session:

- **The friendly's match day**: *play next game* goes S14, S15, S16 (the captain), S17, S20 (half time), S15, S17,
  S20 (full time), S15 *exit*, S14 and the desk, in that order. A non-default captain is chosen (↓ Enter) and the
  first set-piece taker too (↓ Enter); the other takers are left to the original's wait (no key), and the second
  half is a quick result (R on S17). The published career equals the same match through the bridge with the same
  answers (`match_day_policy.play_through_bridge`).
- **The qualifier's match day**: the same order, published by the competitive publication (the owner's
  CompetitiveJobs, T176), N to the watch question (asked here by a stand-in: the original never asks it for a
  qualifier, F030) and C on the captain card. Its career equals T176's watched qualifier (CompetitiveJobs with the
  bench) with the same answers.
- **The captain**: the captain chosen is the one the engine played with, read from the outcome's memory (the stored
  captain `DS:9976 + 10 side + 2`, role 1, F030); C picks the computer's (T143's rule, `suggested_captain`).
- **The taker**: a set piece's taker decision reaches S16; the chosen taker's match equals `pypy_engine.drive` with
  the same answers, and a match whose takers get no key equals the same match played without the prompts.
- **Quick**: R on S17, or N to the watch question, ends on S20 with QUICK RESULT.
- **One process**: the two match days use one engine pid; it ends when the window closes.
- **Home side (#562)**: for the capture's case (Holland away to Norway in the opening friendly of a 2028 start,
  t156-013-hub.png: as the original stores it, Holland side A, F031) the model says away and Norway home; on the
  pitch the home side (here Holland, side B of Romania v Holland) is drawn light red.

The careers read GOAL.DAT and the E010 half-time template from the git-ignored `.cache/` and skip without them; the
engine runs under PyPy 3.11 and the test skips without it. Nothing of the original is in this file (CLAUDE.md rule 14).
"""
import copy
import dataclasses
import os
import shutil
import tempfile
import time
import unittest
from pathlib import Path

from goal2.tests import requires

requires.require(modules=("PySide6",))
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QEvent, Qt  # noqa: E402
from PySide6.QtGui import QKeyEvent  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from goal2.desktop import data_setup, fixed_page  # noqa: E402
from goal2.desktop.model import DesktopModel  # noqa: E402
from goal2.ui import theme  # noqa: E402

CACHE = requires.CACHE
CAREER = requires.need(**requires.HALFTIME)
HOLLAND = 20
WAIT = 900           # seconds for a whole match under PyPy on a loaded runner
PLAY_NEXT = 5        # the desk's sixth option
_BASE = {}


def career():
    """A fresh copy of a 2028 Holland career (opened once per run)."""
    if "model" not in _BASE:
        folder = _BASE.setdefault("folder", tempfile.mkdtemp(prefix="goal2-t167-"))
        model = DesktopModel.open(CACHE / data_setup.TEMPLATE_NAME, CACHE / data_setup.DATA_NAME,
                                  Path(folder) / "unused.g2game", country=HOLLAND)
        model.new_campaign(HOLLAND, 2028)
        model.rename_manager("K Ees")
        _BASE["model"] = model
    return copy.deepcopy(_BASE["model"])


def tearDownModule():
    if "folder" in _BASE:
        shutil.rmtree(_BASE["folder"], ignore_errors=True)


def app():
    application = QApplication.instance() or QApplication([])
    theme.install(application)
    return application


def key(window, k, text=""):
    window.keyPressEvent(QKeyEvent(QEvent.Type.KeyPress, k, Qt.KeyboardModifier.NoModifier, text))
    QApplication.instance().processEvents()


def pump(predicate, limit, what, each=None):
    application = QApplication.instance()
    deadline = time.monotonic() + limit
    while time.monotonic() < deadline:
        application.processEvents()
        if each is not None:
            each()
        if predicate():
            return
        time.sleep(.001)
    raise AssertionError(f"{what} within {limit} s")


def name(screen):
    """A screen as the order lists it: its class, and its phase or mode where it has one."""
    kind = type(screen).__name__
    detail = getattr(screen, "phase", None) or getattr(screen, "mode", None)
    if kind == "RoundScreen":
        detail = "after" if screen.after is not None else "before"
    return f"{kind}:{detail}" if detail else kind


def as_shown(event):
    return {"kind": event.kind, "minute": event.minute, "score": list(event.score), "data": event.data}


def stored_captain(outcome, side):
    """[confirmed: goal2-archaeology F030, 0791:CC7B's stored pick DS:9976 + 10 side + 2 role; role 1, the captain]"""
    from goal2.engine.original_match import Image
    return Image(outcome.memory).rd(0x9976 + 10 * side + 2)


# The friendly's and the qualifier's order of screens, the takers' S16 visits left out (they come where the match
# has a set piece). [designed: docs/design/ui-2026-11 §1, the thick arrows; confirmed: T156-R1 steps 36-45, 118-119,
# 191-198]
ORDER = ["RoundScreen:before", "MenuScreen:before", "ChooseScreen:captain", "PitchScreen", "BoardScreen:half",
         "MenuScreen:half", "PitchScreen", "BoardScreen:full", "MenuScreen:full", "RoundScreen:after", "DeskScreen"]


def without_takers(order):
    out = []
    for item in order:
        if item == "ChooseScreen:taker":
            continue
        if out and out[-1] == item:
            continue          # S17 again after a taker card
        out.append(item)
    return out


@CAREER
@requires.need(slow=True)
class MatchDay(unittest.TestCase):
    """Two match days in one window: the friendly, then the qualifier; the references meanwhile."""

    @classmethod
    def setUpClass(cls):
        from goal2.tests.test_pypy_worker_t152 import pypy
        pypy()
        from goal2.ui.window import Window
        cls.app = app()
        model = cls.model = career()
        window = cls.window = Window(data_setup.paths(Path(_BASE["folder"]) / "data-root"))
        window.resize(fixed_page.WIDTH, fixed_page.HEIGHT)
        window.show()
        cls.desk = window.open_career(model)
        cls.out = {}
        try:
            cls.out["friendly"] = cls.friendly()
            cls.out["qualifier"] = cls.qualifier()
            process = model._match_engine.engine.process
            window.close()
            cls.app.processEvents()
            try:
                cls.out["code"] = process.wait(timeout=5)
            except Exception as exc:  # noqa: BLE001 - asserted below
                cls.out["code"] = repr(exc)
            cls.out["engine_left"] = getattr(model, "_match_engine", None)
        finally:
            window.close()
            window.deleteLater()
            cls.app.processEvents()

    @classmethod
    def _walk(cls, out, on_pitch, on_taker):
        """From S14 to the desk: Enter on S14, S15 and the boards; `on_pitch(pitch)` once at kick-off and once at
        the second half's start; `on_taker(screen, n)` answers the n-th taker card."""
        window = cls.window
        order, takers = out.setdefault("order", []), out.setdefault("takers", [])

        def each():
            screen = window.current()
            if type(screen).__name__ == "PitchScreen" and screen.stop_box.open:
                out.setdefault("notices", []).append(screen.stop_box.kind)
                key(window, Qt.Key.Key_N if screen.stop_box.answers else Qt.Key.Key_Space)  # [T181] no replay/save; notices any key
                return
            label = name(screen)
            if not order or order[-1] != label:
                order.append(label)
                kind = type(screen).__name__
                if kind == "PitchScreen":
                    half = 2 if "BoardScreen:half" in order else 1
                    if half not in out.setdefault("halves", []):
                        out["halves"].append(half)
                        on_pitch(screen, half)
                elif kind == "ChooseScreen" and screen.mode == "taker":
                    takers.append({"current": screen.highlighted(), "eleven": list(screen.eleven),
                                   "headline": screen.wait_head.text()})
                    on_taker(screen, len(takers))
                elif kind == "BoardScreen":
                    out.setdefault("boards", {})[screen.phase] = {
                        "banner": screen.banner is not None, "rows": list(screen.stat_rows),
                        "scorers": list(screen.scorer_texts), "data": screen.data}
                    key(window, Qt.Key.Key_N if screen.save_summary else Qt.Key.Key_Return)
                elif kind == "MenuScreen":
                    out.setdefault("menus", {})[screen.phase] = {
                        "situation": screen.situation.text(), "play": screen.play.text_label.text(),
                        "lineups": dict(screen.lineups), "home": screen.home_country}
                    if screen.phase != "before":
                        key(window, Qt.Key.Key_Return)
                elif kind == "RoundScreen" and screen.after is not None:
                    pump(lambda: not screen.arriving, 120, "the round's results after the match")
                    out["after"] = screen.visible()
                    key(window, Qt.Key.Key_Return)
            elif label == "ChooseScreen:taker":
                pass          # the taker card waits for the original's wait or for on_taker's keys
        pump(lambda: name(window.current()) == "DeskScreen" and order and order[-1] == "DeskScreen", WAIT,
             "the match day did not return to the desk", each)

    @classmethod
    def _start(cls, out):
        """The desk's play next game, S14 (its rows), Enter to S15."""
        window, desk = cls.window, cls.desk
        out["order"] = []
        desk.highlight(PLAY_NEXT)
        key(window, Qt.Key.Key_Return)
        round_screen = window.current()
        out["order"].append(name(round_screen))
        pump(lambda: not round_screen.arriving, 120, "the round's results before the match")
        out["before"] = round_screen.visible()
        out["round_before"] = cls.model.round_before()
        key(window, Qt.Key.Key_Return)
        menu = window.current()
        out["order"].append(name(menu))
        out["menu_before"] = {"situation": menu.situation.text(), "play": menu.play.text_label.text(),
                              "lineups": dict(menu.lineups), "replay": menu.replay_label.text()}
        return menu

    @classmethod
    def friendly(cls):
        window, model = cls.window, cls.model
        out = {"fixture": model.state.campaign.next_fixture, "state_before": copy.deepcopy(model.state)}
        menu = cls._start(out)
        key(window, Qt.Key.Key_Insert)                 # Ins: the stored flag
        out["replay_on"] = menu.replay_label.text()
        key(window, Qt.Key.Key_Insert)
        key(window, Qt.Key.Key_Return)                 # play: the captain card
        card = window.current()
        out["order"].append(name(card))
        out["captain_card"] = {"headline": card.wait_head.text(), "highlight": card.highlighted(),
                               "computer": card.computer}
        key(window, Qt.Key.Key_Down)
        out["captain"] = card.highlighted()
        key(window, Qt.Key.Key_Return)

        def on_pitch(pitch, n):
            controller = pitch.controller
            out["controller"] = controller
            if n == 1:
                out["pid"] = window.match_day.engine_pid()
                pump(lambda: controller.drawn >= 0 and len(pitch.pitch.painted) >= 20, 120, "no kick-off drawn")
                out["painted"] = list(pitch.pitch.painted)
                out["kits"] = pitch.kits
                out["home_label"] = (pitch.home.text(), pitch.home.styleSheet())
                for _ in range(4):
                    key(window, Qt.Key.Key_Right)   # the fastest speed
            elif n == 2:
                key(window, Qt.Key.Key_R)           # the second half as a quick result
                out["hang_on"] = pitch.note.text()

        def on_taker(screen, n):
            if n == 1:
                key(window, Qt.Key.Key_Down)
                out["taker"] = screen.highlighted()
                key(window, Qt.Key.Key_Return)
            # the others: no key, the original's wait (10 s), the current pick stands
        cls._walk(out, on_pitch, on_taker)
        controller = out["controller"]
        out["outcome"] = controller.outcome
        out["choices"] = list(controller.choices)
        out["snapshot"] = controller.given._snapshot
        out["desk_note"] = cls.desk.note.text()
        out["state_after"] = copy.deepcopy(model.state)
        return out

    @classmethod
    def qualifier(cls):
        from goal2.ui.match_day import MatchDay as Day
        window, model = cls.window, cls.model
        out = {"fixture": model.state.campaign.next_fixture}
        original = Day.asks_watch
        Day.asks_watch = staticmethod(lambda model, fixture: True)   # a stand-in: the original asks for kinds 8, 200…
        try:
            menu = cls._start(out)
            out["question"] = menu.wait_head.text()
            key(window, Qt.Key.Key_Return)
            out["refused_play"] = (name(window.current()), menu.note.text())
            key(window, Qt.Key.Key_N, "n")
        finally:
            Day.asks_watch = original
        key(window, Qt.Key.Key_Return)                 # play: the captain card
        card = window.current()
        out["order"].append(name(card))
        out["computer"] = card.computer
        key(window, Qt.Key.Key_C)                      # the computer's pick

        def on_pitch(pitch, n):
            out["controller"] = pitch.controller
            if n == 1:
                out["pid"] = window.match_day.engine_pid()
                out["hang_on"] = pitch.note.text()
        cls._walk(out, on_pitch, lambda screen, n: None)
        controller = out["controller"]
        out["outcome"] = controller.outcome
        out["choices"] = list(controller.choices)
        out["snapshot"] = controller.given._snapshot
        out["kind"] = controller.given.KIND
        return out

    def reference(self, case, competitive):
        """The same match through the bridge, with the same answers, on a model in the state the window's bridge
        started from."""
        from goal2.tests.match_day_policy import play_through_bridge
        from goal2.ui.s17_pitch import engine_fixture
        out = self.out[case]
        model = career()
        model.state = copy.deepcopy(out["snapshot"])
        outcome = play_through_bridge(model, out["choices"], competitive=competitive,
                                      fixture=None if competitive else engine_fixture(out["fixture"]))
        return model, outcome

    # The friendly.
    def test_the_friendly_goes_through_the_original_s_screens_in_order(self):
        out = self.out["friendly"]
        self.assertEqual(without_takers(out["order"]), ORDER)
        self.assertIn("ChooseScreen:taker", out["order"], "a set piece's taker card")
        self.assertEqual(out["captain_card"]["headline"], "Choose your captain to kick off")
        self.assertEqual(out["menu_before"]["play"], "▶ play     next: choose your captain, then kick-off")
        self.assertIn("next: second half", out["menus"]["half"]["play"])
        self.assertEqual(out["menus"]["full"]["play"], "exit")
        self.assertIn("HALF TIME", out["menus"]["half"]["situation"])
        self.assertIn("FULL TIME", out["menus"]["full"]["situation"])
        self.assertIn("Full time:", out["desk_note"])
        self.assertEqual(self.model.state.match_count, out["state_before"].match_count + 2)

    def test_s14_lists_the_round_before_and_after_with_your_match(self):
        out = self.out["friendly"]
        rows = out["round_before"]["results"]
        self.assertEqual(out["before"][:-1], [(r["home_name"], f"{r['score'][0]} - {r['score'][1]}", r["away_name"],
                                               r["kind_name"]) for r in rows][-16:])
        self.assertEqual(out["before"][-1][1], "v")
        self.assertIn("your match is next", out["before"][-1][3])
        state = out["state_after"]
        world = state.campaign.world
        ours = next(i for i, r in enumerate(world.results) if r["fixture_id"] == out["fixture"].fixture_id)
        self.assertEqual(world.results[ours]["mode"], "watched")
        after = [r for r in world.results[ours + 1:]]
        self.assertTrue(after and all(r["mode"] == "silent" for r in after), "the round's rest, resolved after it")
        self.assertIn("your match", [row[3].split(" · ")[-1] for row in out["after"]])
        self.assertEqual(len(out["after"]), min(17, len(rows) + 1 + len(after)))

    def test_the_friendly_s_career_equals_the_same_match_through_the_bridge(self):
        out = self.out["friendly"]
        model, outcome = self.reference("friendly", competitive=False)
        self.assertEqual([as_shown(e) for e in out["outcome"].events], [as_shown(e) for e in outcome.events])
        self.assertEqual(out["outcome"].result, outcome.result)
        self.assertEqual(out["state_after"], model.state)

    def test_the_captain_chosen_is_the_one_the_engine_played_with(self):
        out = self.out["friendly"]
        from goal2.ui.s17_pitch import suggested_captain
        self.assertEqual(out["captain_card"]["highlight"], suggested_captain(out["state_before"]),
                         "the highlight starts on the computer's pick")
        self.assertNotEqual(out["captain"], out["captain_card"]["computer"])
        side = 0 if out["fixture"].side_a == HOLLAND else 1
        self.assertEqual(stored_captain(out["outcome"], side), out["captain"])

    def test_c_picks_the_computer_s_captain(self):
        out = self.out["qualifier"]
        fixture = out["fixture"]
        side = 0 if fixture.side_a == HOLLAND else 1
        self.assertIsNotNone(out["computer"])
        self.assertEqual(out["snapshot"].captain, out["computer"])
        self.assertEqual(stored_captain(out["outcome"], side), out["computer"])

    def test_the_taker_decision_reaches_s16_and_the_engine(self):
        from goal2.game.watched_publication import WatchedPublication
        from goal2.tests import pypy_engine
        from goal2.tests.match_day_policy import Scripted
        from goal2.ui.s17_pitch import engine_fixture
        out = self.out["friendly"]
        first = out["takers"][0]
        self.assertTrue(first["headline"].startswith("Choose your "), first["headline"])
        self.assertNotEqual(out["taker"], first["current"], "a non-default taker was chosen")
        contexts = [c for c, _ in out["choices"]]
        number = contexts.index("set_piece")
        self.assertEqual(out["choices"][number], ("set_piece", {"taker": out["taker"]}))
        self.assertTrue(all(v == {"taker": None} for c, v in out["choices"][number + 1:] if c == "set_piece"),
                        "the other takers got no key")
        # The same answers through drive, on the state the publication prepares.
        owner = career()
        owner.state = copy.deepcopy(out["snapshot"])
        job = WatchedPublication(owner).begin(engine_fixture(out["fixture"]))
        answers = {i: value for i, (_, value) in enumerate(out["choices"])}
        from goal2.game.watched_match import FRIENDLY_SUBSTITUTIONS   # [T180] BM-7's budget, as the engine server's
        drive, _, _ = pypy_engine.call("goal2.tests.pypy_engine:drive", copy.deepcopy(job.state),
                                       bytes(owner.template_bytes), engine_fixture(out["fixture"]), pitch=True,
                                       policy=Scripted(answers), prompts=True, delay_byte=0, record_draws=True,
                                       substitutions=FRIENDLY_SUBSTITUTIONS, live_players=True)
        self.assertEqual([as_shown(e) for e in out["outcome"].events], [as_shown(e) for e in drive.events])
        self.assertEqual(out["outcome"].result, drive.result)
        self.assertEqual(out["outcome"].memory, drive.memory)
        taken = [e for e in drive.events if e.kind == "set_piece"]
        self.assertEqual(taken[0].data["player"], out["taker"], "the engine's taker is the one chosen")

    def test_no_key_on_a_taker_leaves_the_computer_s_pick(self):
        """The qualifier's takers all got no key (a quick result shows no card): its match equals the same one
        played without the prompts, so no answer changed the original's pick."""
        from goal2.desktop.competitive import pending_fixture
        from goal2.game.watched_publication import CompetitivePublication
        from goal2.tests import pypy_engine
        out = self.out["qualifier"]
        self.assertTrue(any(c == "set_piece" for c, _ in out["choices"]), "the qualifier had a set piece")
        self.assertTrue(all(v == {"taker": None} for c, v in out["choices"] if c == "set_piece"))
        owner = career()
        owner.state = copy.deepcopy(out["snapshot"])
        fixture = pending_fixture(owner.state)
        job = CompetitivePublication(owner).begin(fixture)
        plain, _, _ = pypy_engine.call("goal2.tests.pypy_engine:drive", copy.deepcopy(job.state),
                                       bytes(owner.template_bytes), fixture, competitive=True, substitutions=(5, 5),
                                       delay_byte=0, record_draws=True, live_players=True)
        self.assertEqual(out["outcome"].memory, plain.memory)
        self.assertEqual(out["outcome"].seeds, plain.seeds)
        kept = [as_shown(e) for e in out["outcome"].events
                if e.kind != "set_piece" and not (e.kind == "decision" and e.data.get("context") == "set_piece")]
        self.assertEqual(kept, [as_shown(e) for e in plain.events])

    # The qualifier.
    def test_the_qualifier_goes_through_the_same_screens_and_the_competitive_publication(self):
        out = self.out["qualifier"]
        self.assertEqual(out["fixture"].kind, 2)
        self.assertEqual(without_takers(out["order"]), ORDER)
        self.assertEqual(out["kind"], "competitive")
        from goal2.game.watched_schema import COMPETITIVE_SCHEMA
        self.assertEqual(self.model.state.last_match.get("schema"), COMPETITIVE_SCHEMA)
        self.assertIn(out["fixture"].fixture_id, self.model.state.campaign.completed_fixture_ids)

    def test_the_qualifier_s_career_equals_t176_s_watched_qualifier(self):
        out = self.out["qualifier"]
        model, outcome = self.reference("qualifier", competitive=True)
        self.assertEqual(out["outcome"].result, outcome.result)
        self.assertEqual(self.model.state, model.state)

    # Quick, the watch question.
    def test_r_on_s17_ends_on_s20_with_quick_result(self):
        boards = self.out["friendly"]["boards"]
        self.assertFalse(boards["half"]["banner"], "the first half was watched: its board has the statistics")
        self.assertTrue(boards["full"]["banner"], "R in the second half: QUICK RESULT")
        self.assertEqual(self.out["friendly"]["hang_on"], "HANG ON A TICK")

    def test_n_to_the_watch_question_plays_a_quick_result(self):
        out = self.out["qualifier"]
        self.assertEqual(out["question"], "Do you want to watch this match? (Y/N)")
        self.assertEqual(out["refused_play"][0], "MenuScreen:before", "play waits for the answer")
        self.assertTrue(out["controller"].quick)
        self.assertEqual(out["hang_on"], "HANG ON A TICK")
        self.assertTrue(out["boards"]["half"]["banner"])
        self.assertTrue(out["boards"]["full"]["banner"])

    def test_the_half_time_board_shows_only_what_the_route_has(self):
        board = self.out["friendly"]["boards"]["half"]
        rows = dict((r[1], (r[0], r[2])) for r in board["rows"])
        self.assertEqual(rows["corners"], ("at full time", "at full time"))
        data = board["data"]
        self.assertIsNone(data["bars"])
        self.assertIsNotNone(data["half_time"])
        full = self.out["friendly"]["outcome"].result
        goals = [g for g in full["goals"] if g["minute"] <= 45]
        self.assertEqual(sum(len(s) for s in data["scorers"]), len(goals))

    def test_ins_toggles_the_stored_replay_flag(self):
        out = self.out["friendly"]
        self.assertIn("OFF", out["menu_before"]["replay"])
        self.assertIn("ON", out["replay_on"])

    # One process.
    def test_two_match_days_use_one_engine_process(self):
        self.assertIsNotNone(self.out["friendly"]["pid"])
        self.assertEqual(self.out["friendly"]["pid"], self.out["qualifier"]["pid"])
        self.assertNotIsInstance(self.out["code"], str, self.out["code"])
        self.assertIsNone(self.out["engine_left"], "the window's close ends the engine")

    # The home side.
    def test_each_side_wears_the_engine_s_kit(self):
        """[#583; was 'home is drawn light red'] The pitch, S17's names and S15's are in the kits the engine
        computed for this match (DS:832E..8331, 0791:1073); home has no colour of its own."""
        from goal2.tests.test_ui_pitch_t166 import engine_kits
        from goal2.ui.pitch import HOME, KEEPERS
        out = self.out["friendly"]
        fixture = out["fixture"]
        self.assertEqual(self.model.home(fixture), fixture.side_b)
        painted = out["painted"]
        self.assertEqual({team for _, team, *_ in painted}, {0, 1})
        kits = out["kits"]
        self.assertEqual((kits.shirt, kits.keeper), engine_kits(out["outcome"]))
        for slot, team, text, colour, box in painted:
            self.assertEqual(colour, kits.colour(team, slot in KEEPERS))
        names = self.model.goaldat.country_names
        self.assertEqual(out["home_label"][0], names[fixture.side_b])
        self.assertIn(kits.colour(HOME), out["home_label"][1])
        self.assertIn(f"location: {names[fixture.side_b]}", out["menu_before"]["situation"])


@CAREER
class HomeSide(unittest.TestCase):
    """#562: the capture's case, Holland away to Norway in the opening friendly of a 2028 start (t156-013-hub.png,
    T156-R1 step 13; t156-042: location Norway). The route's own draw differs (its seeds are fixed: Romania v
    Holland), so the case is the capture's fixture as the original stores it: Holland side A, Norway side B, because
    the hub writes "away" for side A (F031 "Venue", 000E:724A)."""

    def test_the_capture_s_case_is_away(self):
        model = career()
        names = model.goaldat.country_names
        norway = names.index("Norway")
        friendly = model.state.campaign.next_fixture
        capture = dataclasses.replace(friendly, home_country=HOLLAND, away_country=norway)   # side A, side B
        self.assertEqual(model.venue(capture), "away")
        self.assertEqual(model.home(capture), norway)
        self.assertEqual(model.venue(friendly), "home" if friendly.side_b == HOLLAND else "away")

    def test_the_desk_says_home_or_away(self):
        from unittest import mock
        from goal2.game.campaign import CampaignState
        from goal2.ui.s06_desk import next_match
        model = career()
        norway = model.goaldat.country_names.index("Norway")
        capture = dataclasses.replace(model.state.campaign.next_fixture, home_country=HOLLAND, away_country=norway)   # side A, side B
        with mock.patch.object(CampaignState, "next_fixture", new_callable=mock.PropertyMock, return_value=capture):
            self.assertEqual(next_match(model), (norway, "friendly away"))

    def test_the_watch_question_is_the_original_s_rule(self):
        """[confirmed: F030] kinds 8, 200, 201, 203 always; 101, 103 with a manager on side B's continent; never a
        friendly or a qualifier."""
        from goal2.ui.match_day import asks_watch
        model = career()
        fixture = model.state.campaign.next_fixture
        for kind, asked in ((1, False), (2, False), (5, False), (8, True), (200, True), (203, True), (4, False)):
            with self.subTest(kind=kind):
                self.assertEqual(asks_watch(model, dataclasses.replace(fixture, kind=kind)), asked)


if __name__ == "__main__":
    unittest.main()
