"""[designed: owner, 2026-11-03, #526; T180, #574] The match stops and the bench in the new window: S18, S19 and
S09's mark line.

The claim it protects: every substitution the player makes on S19 is the pair the engine receives, and every refusal
the player sees is the engine's. Visited offscreen on a 2028 Austria career (its first fixture the friendly Austria v
Bulgaria, whose Austrian players are injured at 3′ and later; its second the qualifier Austria v Eire), in one window
session:

- **The substitution opportunity**: the injury stops the match on S18 (*SUBSTITUTION OPPORTUNITY*), a key opens S15,
  *players* opens S19 in *make substitutions now* mode, and the injured player is taken off (starter first).
- **A half-time substitution**: S20's Esc opens S19; the first pair is chosen bench player first, the rest starter
  first, five in all, so the friendly's sixth substitution is made (BM-7's budget: the counter reads 255, then 254,
  never the original's five). The published career equals the same match through the bridge with the same answers
  (`match_day_policy.play_through_bridge`), and the injured player who came off stays off.
- **A refusal**: at half time the player taken off at the stop is put on again; the engine refuses it, S19 shows its
  reason and waits for a key, and nothing changes: he does not come on.
- **The mark line**: T on S19 opens S09 with a fifth line, *mark*, offering the opponent's outfield players; the mark
  chosen reaches the engine (its `player_tactics` event names him); after the match S09 shows no mark line.
- **The other side's substitution** shows its notice on S18; a key plays on.
- **A request during play** (the qualifier): Esc on S17, S19 in request mode at the pause (five substitutions left);
  a pair requested; at the next stoppage S18, S15, S19 offer it again (#316's line), *play* makes it, as the engine's
  report says, and the counter reads four at half time.

The careers read GOAL.DAT and the E010 half-time template from the git-ignored `.cache/` and skip without them; the
engine runs under PyPy 3.11 and the test skips without it. Nothing of the original is in this file (CLAUDE.md rule 14).
"""
import copy
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
AUSTRIA = 2
WAIT = 1500          # seconds for a whole match day under PyPy on a loaded runner
PLAY_NEXT = 5        # the desk's sixth option
_BASE = {}


def career():
    """A fresh copy of a 2028 Austria career (opened once per run)."""
    if "model" not in _BASE:
        folder = _BASE.setdefault("folder", tempfile.mkdtemp(prefix="goal2-t180-"))
        model = DesktopModel.open(CACHE / data_setup.TEMPLATE_NAME, CACHE / data_setup.DATA_NAME,
                                  Path(folder) / "unused.g2game", country=AUSTRIA)
        model.new_campaign(AUSTRIA, 2028)
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
    kind = type(screen).__name__
    detail = getattr(screen, "phase", None) or getattr(screen, "mode", None)
    if kind == "RoundScreen":
        detail = "after" if screen.after is not None else "before"
    return f"{kind}:{detail}" if detail else kind


def as_shown(event):
    return {"kind": event.kind, "minute": event.minute, "score": list(event.score), "data": event.data}


def go_to(window, screen, word):
    """Move S19's cursor to `word`."""
    words = screen.answer.words()
    while words[screen.row] != word:
        key(window, Qt.Key.Key_Down if words.index(word) > screen.row else Qt.Key.Key_Up)


def enter_on(window, screen, word):
    go_to(window, screen, word)
    out = screen.enter_hint_text()
    key(window, Qt.Key.Key_Return)
    return out


def outfield(answer, words):
    """Outfield players only: a keeper put on for an outfield player makes the original refuse the eleven
    (test_watched_bench_t102 `choose`)."""
    return [w for w in words if answer.position(w) != 0]


def play_on(window, menu):
    """S15's *play*: ↓ to it (after *players* the cursor stays there, as in the original, T156-R1 steps 134-137), Enter."""
    for _ in range(len(menu.options)):
        if menu.highlighted() is menu.play:
            break
        key(window, Qt.Key.Key_Down)
    key(window, Qt.Key.Key_Return)


class Walk:
    """One match day from the desk to the desk: `react(screen)` answers each screen as it shows; the order of the
    screens, every S18 box and every S19 visit are recorded."""

    def __init__(self, case, window, model):
        self.case, self.window, self.model = case, window, model
        self.order, self.boxes, self.benches, self.out = [], [], [], {}
        self.halves = set()

    def label(self, screen):
        box = getattr(screen, "stop_box", None)
        text = name(screen)
        if box is not None and box.open:
            text += f"+S18:{box.kind}"
        return text

    def each(self):
        screen = self.window.current()
        text = self.label(screen)
        if self.order and self.order[-1] == text:
            if type(screen).__name__ == "PitchScreen":
                self.playing(screen)
            return
        self.order.append(text)
        self.react(screen)

    def run(self):
        pump(lambda: name(self.window.current()) == "DeskScreen" and self.order and self.order[-1] == "DeskScreen",
             WAIT, f"the {self.case} match day did not return to the desk", self.each)

    def bench_record(self, screen):
        record = {"mode": screen.mode, "label": screen.mode_label.text(), "counter": screen.counter.text(),
                  "line": screen.note.text(), "context": screen.answer.context, "left": screen.answer.left,
                  "chosen": [list(p) for p in screen.answer.chosen], "eleven": list(screen.answer.eleven),
                  "bench": list(screen.answer.bench), "injured": set(screen.answer.injured)}
        self.benches.append(record)
        return record

    def react(self, screen):
        window = self.window
        kind = type(screen).__name__
        if kind == "PitchScreen":
            box = screen.stop_box
            if box.open:
                self.boxes.append({"kind": box.kind, "texts": box.texts(), "minute": screen.controller.frame_or_event()[0]})
                self.on_box(screen, box)
                return
            self.playing(screen)
        elif kind == "ChooseScreen":
            key(window, Qt.Key.Key_Return)          # the captain or a taker: the highlighted pick
        elif kind == "BoardScreen":
            self.on_board(screen)
        elif kind == "MenuScreen":
            self.on_menu(screen)
        elif kind == "BenchScreen":
            self.on_bench(screen)
        elif kind == "PlayerTacticsScreen":
            self.on_tactics(screen)
        elif kind == "RoundScreen":
            pump(lambda: not screen.arriving, 120, "the round's results")
            key(window, Qt.Key.Key_Return)

    def playing(self, pitch):
        if "fast" not in self.out:
            self.out["fast"] = True
            self.out["controller"] = pitch.controller
            for _ in range(4):
                key(self.window, Qt.Key.Key_Right)   # the fastest speed

    def on_box(self, pitch, box):
        key(self.window, Qt.Key.Key_Space)          # any key

    def on_board(self, screen):
        key(self.window, Qt.Key.Key_Return)

    def on_menu(self, screen):
        play_on(self.window, screen)

    def on_bench(self, screen):
        self.bench_record(screen)
        key(self.window, Qt.Key.Key_Escape)

    def on_tactics(self, screen):
        key(self.window, Qt.Key.Key_Escape)


class FriendlyWalk(Walk):
    """The friendly: the injury stop, the half-time bench with the mark, the refusal, the other side's notice."""

    def on_menu(self, screen):
        if screen.phase == "stop" and "stop_bench" not in self.out:
            self.out["stop_bench"] = True
            self.out["stop_menu"] = {"situation": screen.situation.text(), "play": screen.play.text_label.text()}
            key(self.window, Qt.Key.Key_Space)      # Austria's players: the bench
            return
        play_on(self.window, screen)

    def on_board(self, screen):
        if screen.phase == "half":
            self.out["board_escape"] = screen.escape_text
            key(self.window, Qt.Key.Key_Escape)     # the bench
            return
        key(self.window, Qt.Key.Key_Return)

    def on_bench(self, screen):
        window, record = self.window, self.bench_record(screen)
        answer = screen.answer
        if screen.mode == "refused":
            self.out["refused_screen"] = record
            key(window, Qt.Key.Key_A, "a")          # any key: back to the match
            return
        if answer.context == "substitution" and "first_stop" not in self.out:
            injured = [w for w in answer.eleven if w in answer.injured]
            keeper = answer.position(injured[0]) == 0
            on = next(w for w in answer.bench if (answer.position(w) == 0) == keeper)
            hints = [enter_on(window, screen, injured[0]), enter_on(window, screen, on)]
            self.out["first_stop"] = {"pair": [injured[0], on], "hints": hints, "record": record,
                                      "chosen": [list(p) for p in answer.chosen]}
            key(window, Qt.Key.Key_Escape)          # S15, whose play sends it
            return
        if answer.context == "half_time" and "half" not in self.out:
            off_at_stop = self.out["first_stop"]["pair"][0]
            fresh = outfield(answer, [w for w in answer.bench if w != off_at_stop])
            starters = outfield(answer, [w for w in answer.eleven if w not in answer.injured])
            pairs = [[starters[0], fresh[0]]]
            hints = [enter_on(window, screen, fresh[0]), enter_on(window, screen, starters[0])]   # bench first
            for off, on in zip(starters[1:5], fresh[1:5]):
                enter_on(window, screen, off)
                enter_on(window, screen, on)
                pairs.append([off, on])
            illegal = [starters[5], off_at_stop]
            enter_on(window, screen, illegal[0])
            enter_on(window, screen, off_at_stop)
            marker = starters[6]
            go_to(window, screen, marker)
            key(window, Qt.Key.Key_T)               # S09 with the mark line
            self.out["half"] = {"pairs": pairs, "illegal": illegal, "hints": hints, "marker": marker,
                                "record": record, "chosen": [list(p) for p in answer.chosen],
                                "opponents": list(answer.opponents)}
            return
        key(window, Qt.Key.Key_Escape)

    def on_tactics(self, screen):
        window = self.window
        if screen.bench is not None and "mark" not in self.out:
            lines = screen.lines()
            for _ in range(4):
                key(window, Qt.Key.Key_Down)
            key(window, Qt.Key.Key_Return)          # nobody
            key(window, Qt.Key.Key_Return)          # their first outfield player
            self.out["mark"] = {"lines_before": lines, "lines": screen.lines(), "mark": screen.bench.marking.get(
                screen.word), "choices": screen.bench.mark_choices()}
            key(window, Qt.Key.Key_Escape)          # S19
            screen = window.current()
            self.out["half"]["after_mark"] = self.bench_record(screen)
            key(window, Qt.Key.Key_Escape)          # S15, whose play sends the answer
            return
        key(window, Qt.Key.Key_Escape)


class QualifierWalk(Walk):
    """The qualifier: Esc in play, the request at the pause, made at the next stoppage."""

    def playing(self, pitch):
        super().playing(pitch)
        controller = pitch.controller
        frame = controller.display.frame
        if (controller.requests == 0 and frame is not None and frame["minute"] >= 5
                and "requested" not in self.out):
            key(self.window, Qt.Key.Key_Escape)     # the bench, requested in play
            self.out["requests_after_esc"] = controller.requests

    def on_menu(self, screen):
        if screen.phase == "stop" and "made_stop" not in self.out and "requested" in self.out:
            self.out["made_stop"] = {"situation": screen.situation.text()}
            key(self.window, Qt.Key.Key_Space)
            return
        play_on(self.window, screen)

    def on_board(self, screen):
        if screen.phase == "half" and "half" not in self.out:
            self.out["half"] = True
            key(self.window, Qt.Key.Key_Escape)     # the bench: its counter
            return
        key(self.window, Qt.Key.Key_Return)

    def on_bench(self, screen):
        window, record = self.window, self.bench_record(screen)
        answer = screen.answer
        if screen.mode == "request" and "requested" not in self.out:
            off, on = outfield(answer, answer.eleven)[4], outfield(answer, answer.bench)[0]
            hints = [enter_on(window, screen, off), enter_on(window, screen, on)]
            self.out["requested"] = {"pair": [off, on], "record": record, "hints": hints,
                                     "after": self.bench_record(screen), "cancel_hint": None}
            go_to(window, screen, off)
            self.out["requested"]["cancel_hint"] = screen.enter_hint_text()
            key(window, Qt.Key.Key_Escape)          # back to the match: the request is sent
            return
        if screen.mode == "refused":
            key(window, Qt.Key.Key_A, "a")
            return
        key(window, Qt.Key.Key_Escape)


@CAREER
class Bench(unittest.TestCase):
    """Two match days in one window: the friendly, then the qualifier; the reference meanwhile."""

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
        try:
            cls.friendly = cls.play(FriendlyWalk)
            cls.after = cls.s09_after()
            cls.qualifier = cls.play(QualifierWalk)
        finally:
            window.close()
            window.deleteLater()
            cls.app.processEvents()

    @classmethod
    def play(cls, walk_class):
        window, model = cls.window, cls.model
        walk = walk_class(walk_class.__name__, window, model)
        walk.out["fixture"] = model.state.campaign.next_fixture
        walk.out["state_before"] = copy.deepcopy(model.state)
        cls.desk.highlight(PLAY_NEXT)
        key(window, Qt.Key.Key_Return)
        walk.run()
        controller = walk.out["controller"]
        walk.out.update(outcome=controller.outcome, choices=list(controller.choices), reports=list(controller.reports),
                        snapshot=controller.given._snapshot, state_after=copy.deepcopy(model.state))
        return walk

    @classmethod
    def s09_after(cls):
        """After the match: S08, T on a player of the eleven: S09's lines."""
        from goal2.ui.s09_player_tactics import PlayerTacticsScreen
        window = cls.window
        squad = cls.desk.select_squad()
        key(window, Qt.Key.Key_T)
        screen = window.current()
        out = {"kind": type(screen).__name__, "lines": screen.lines(),
               "is_tactics": isinstance(screen, PlayerTacticsScreen)}
        key(window, Qt.Key.Key_Escape)
        if window.current() is squad:
            key(window, Qt.Key.Key_Escape)
        return out

    # The substitution opportunity.
    def test_an_injury_stops_on_s18_then_s15_then_s19(self):
        walk = self.friendly
        first = walk.boxes[0]
        self.assertEqual(first["kind"], "substitution")
        self.assertEqual(first["texts"][0], "SUBSTITUTION OPPORTUNITY")
        self.assertIn("injured", first["texts"][1])
        self.assertEqual(first["texts"][2], "press any key")
        at = walk.order.index("PitchScreen+S18:substitution")
        self.assertEqual(walk.order[at + 1:at + 3], ["MenuScreen:stop", "BenchScreen:now"])
        self.assertIn("SUBSTITUTION OPPORTUNITY", walk.out["stop_menu"]["situation"])
        stop = walk.out["first_stop"]
        self.assertEqual(stop["record"]["label"], "MAKE SUBSTITUTIONS NOW")
        self.assertEqual(stop["hints"], ["Take off this player", "Put on this player"])
        self.assertEqual(stop["chosen"], [stop["pair"]])
        self.assertEqual(next(c for c in walk.out["choices"] if c[0] == "substitution"), ("substitution", [stop["pair"]]))
        self.assertEqual(walk.out["reports"][0]["made"], [stop["pair"]])

    # A half-time substitution.
    def test_s20_esc_opens_the_bench_in_make_substitutions_now_mode(self):
        walk = self.friendly
        self.assertEqual(walk.out["board_escape"], "bench")
        at = walk.order.index("BoardScreen:half")
        self.assertEqual(walk.order[at + 1], "BenchScreen:now")
        half = walk.out["half"]
        self.assertEqual(half["record"]["label"], "MAKE SUBSTITUTIONS NOW")
        self.assertEqual(half["hints"], ["Put on this player", "Take off this player"], "the pair in either order")
        self.assertEqual(half["chosen"], half["pairs"] + [half["illegal"]])

    def test_the_half_time_answer_is_the_pairs_the_engine_receives(self):
        walk = self.friendly
        half = walk.out["half"]
        context, value = next(c for c in walk.out["choices"] if c[0] == "half_time")
        self.assertEqual(value["substitutions"], half["pairs"] + [half["illegal"]])
        decided = [d for d in walk.out["outcome"].result["decisions"] if d["context"] == "half_time"]
        self.assertEqual([list(p) for p in decided[0]["answer"]["substitutions"]], half["pairs"] + [half["illegal"]])

    def test_the_friendly_s_career_equals_the_same_match_through_the_bridge(self):
        from goal2.tests.match_day_policy import play_through_bridge
        from goal2.ui.s17_pitch import engine_fixture
        walk = self.friendly
        model = career()
        model.state = copy.deepcopy(walk.out["snapshot"])
        outcome = play_through_bridge(model, walk.out["choices"], fixture=engine_fixture(walk.out["fixture"]),
                                      wait=WAIT)
        self.assertEqual([as_shown(e) for e in walk.out["outcome"].events], [as_shown(e) for e in outcome.events])
        self.assertEqual(walk.out["outcome"].result, outcome.result)
        self.assertEqual(walk.out["state_after"], model.state)

    def test_the_player_who_came_off_stays_off(self):
        walk = self.friendly
        side = walk.out["controller"].display.managed
        off = walk.out["first_stop"]["pair"][0]
        made = [e for e in walk.out["outcome"].events if e.kind == "substitution" and e.data["team"] == side]
        self.assertIn([off, walk.out["first_stop"]["pair"][1]], [[e.data["off"], e.data["on"]] for e in made])
        self.assertNotIn(off, [e.data["on"] for e in made], "he does not come back on")

    # A refusal.
    def test_a_refused_pair_shows_the_engine_s_reason_and_changes_nothing(self):
        walk = self.friendly
        half = walk.out["half"]
        report = next(r for r in walk.out["reports"] if r["context"] == "half_time")
        self.assertEqual(report["made"], half["pairs"])
        self.assertEqual([r[:2] for r in report["refused"]], [half["illegal"]])
        reason = report["refused"][0][2]
        self.assertTrue(reason)
        shown = walk.out["refused_screen"]
        self.assertEqual(shown["mode"], "refused")
        self.assertEqual(shown["label"], "SUBSTITUTION NOT MADE")
        self.assertIn(reason, shown["line"])
        self.assertEqual(shown["counter"], f"substitutions left {report['substitutions_left']}")
        at = walk.order.index("BenchScreen:refused")
        self.assertTrue(walk.order[at + 1].startswith("PitchScreen"), "a key goes back to the match")
        side = walk.out["controller"].display.managed
        starters_off = [e.data["off"] for e in walk.out["outcome"].events
                        if e.kind == "substitution" and e.data["team"] == side]
        self.assertNotIn(half["illegal"][0], starters_off, "the starter of the refused pair stays on")

    # The counter.
    def test_the_friendly_s_counter_is_bm7_s_and_a_sixth_substitution_is_made(self):
        from goal2.game.watched_match import FRIENDLY_SUBSTITUTIONS
        walk = self.friendly
        self.assertEqual(FRIENDLY_SUBSTITUTIONS, 255)
        self.assertEqual(walk.out["first_stop"]["record"]["counter"], "substitutions left 255")
        self.assertEqual(walk.out["half"]["record"]["counter"], "substitutions left 254")
        side = walk.out["controller"].display.managed
        made = [e for e in walk.out["outcome"].events if e.kind == "substitution" and e.data["team"] == side]
        self.assertEqual(len(made), 6, "the sixth substitution is made")
        self.assertEqual(walk.out["reports"][-1]["substitutions_left"], 255 - 6)

    def test_the_qualifier_s_counter_is_five_and_decreases(self):
        walk = self.qualifier
        self.assertEqual(walk.out["fixture"].kind, 2)
        self.assertEqual(walk.out["requested"]["record"]["counter"], "substitutions left 5")
        half = [b for b in walk.benches if b["context"] == "half_time"]
        self.assertEqual(half[0]["counter"], "substitutions left 4")

    # A request during play.
    def test_a_request_during_play_is_made_at_the_next_stoppage(self):
        from goal2.ui.s19_bench import ESC_KEEPS_REQUESTED
        walk = self.qualifier
        requested = walk.out["requested"]
        self.assertEqual(walk.out["requests_after_esc"], 1, "Esc on S17 sends the request")
        at = walk.order.index("BenchScreen:request")
        self.assertTrue(walk.order[at - 1].startswith("PitchScreen"), "S19 opens at the pause, from the pitch")
        self.assertEqual(requested["record"]["label"], "REQUEST A SUBSTITUTION")
        self.assertEqual(requested["after"]["label"], "SUBSTITUTION REQUESTED")
        self.assertEqual(requested["hints"], ["Request substitution", "Request substitution"])
        self.assertEqual(requested["cancel_hint"], "Cancel substitution request")
        pair = requested["pair"]
        choices = walk.out["choices"]
        pause = choices.index(("pause", [pair]))
        stop = next(i for i, (c, v) in enumerate(choices) if c == "substitution" and i > pause)
        self.assertEqual(choices[stop], ("substitution", [pair]))
        reports = walk.out["reports"]
        self.assertEqual(reports[0]["context"], "pause")
        self.assertEqual(reports[0]["requested"], [pair])
        self.assertEqual(reports[1]["context"], "substitution")
        self.assertEqual(reports[1]["made"], [pair], "made at that stoppage, as the engine's report says")
        offered = next(b for b in walk.benches if b["context"] == "substitution")
        self.assertEqual(offered["chosen"], [pair], "the stoppage offers the request again")
        self.assertIn(ESC_KEEPS_REQUESTED, offered["line"])
        side = walk.out["controller"].display.managed
        made = [[e.data["off"], e.data["on"]] for e in walk.out["outcome"].events
                if e.kind == "substitution" and e.data["team"] == side]
        self.assertEqual(made[0], pair)

    # The mark line.
    def test_s09_from_s19_shows_mark_with_the_opponent_s_players(self):
        walk = self.friendly
        mark = walk.out["mark"]
        opponents = walk.out["half"]["opponents"]
        self.assertEqual(len(opponents), 11)
        self.assertEqual([line[0] for line in mark["lines_before"]],
                         ["position", "possession", "passing", "tackling", "mark"])
        self.assertEqual(mark["lines_before"][4], ("mark", "—"))
        self.assertEqual(mark["choices"], [None, 0] + opponents[1:])
        self.assertEqual(mark["mark"], opponents[1])
        from goal2.ui.squad_card import full_name
        self.assertEqual(mark["lines"][4], ("mark", full_name(self.model, opponents[1])))

    def test_the_mark_reaches_the_engine(self):
        walk = self.friendly
        marker, mark = walk.out["half"]["marker"], walk.out["mark"]["mark"]
        context, value = next(c for c in walk.out["choices"] if c[0] == "half_time")
        self.assertEqual(value["marking"], {marker: mark})
        events = [e for e in walk.out["outcome"].events if e.kind == "player_tactics" and e.data["player"] == marker]
        self.assertTrue(events, "the original's player tactics screen was visited for him")
        self.assertEqual(events[-1].data["marking"], mark)

    def test_after_the_match_s09_shows_no_mark(self):
        self.assertTrue(self.after["is_tactics"], self.after["kind"])
        self.assertEqual([line[0] for line in self.after["lines"]], ["position", "possession", "passing", "tackling"])

    # The other side's substitution.
    def test_the_other_side_s_substitution_shows_its_notice_and_plays_on(self):
        walk = self.friendly
        notices = [b for b in walk.boxes if b["kind"] == "opponent"]
        self.assertTrue(notices, "the other side substituted a player")
        headline = notices[0]["texts"][0]
        self.assertTrue(headline.startswith("SUBSTITUTION ") and " on for " in headline, headline)
        side = walk.out["controller"].display.managed
        theirs = [e for e in walk.out["outcome"].events if e.kind == "substitution" and e.data["team"] == 1 - side]
        from goal2.ui.squad_card import full_name
        self.assertEqual(headline, f"SUBSTITUTION {full_name(self.model, theirs[0].data['on'])} on for "
                                   f"{full_name(self.model, theirs[0].data['off'])}")
        at = walk.order.index("PitchScreen+S18:opponent")
        self.assertEqual(walk.order[at + 1], "PitchScreen", "a key plays on")
        self.assertEqual(len(notices), len(theirs))


if __name__ == "__main__":
    unittest.main()
