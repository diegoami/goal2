"""[designed: owner, 2026-11-03, #526 decision 2; T166, #540] S17, the pitch in the main window, over the bridge.

The claim it protects: what S17 shows is the engine's samples and events, in order, paced by S17's own
acknowledgements, and the match the player watched is the match the engine published. Visited offscreen on a 2028
Holland career (the route's first fixture is a friendly, Romania v Holland):

- **Same match**: *play next game* on the desk goes through the match day (T167: S14, S15, S16 with C, the
  computer's captain) and plays the friendly to full time on S17; the events S17 shows equal the bridge's, in order,
  and the outcome's; the published career equals the same match played through the bridge with the same answers
  (`goal2.tests.match_day_policy.play_through_bridge`) [T167: was today's `WatchedController`, frames off, which has
  no player prompts].
- **Pacing**: with the pitch's painting stalled, the engine's samples never run past the acknowledged one + LEAD (and
  reach it), over the whole match.
- **Keys**: ←→ step through the six speeds, ↑↓ the display, Space enlarges the commentary, F9 says goal2 has no sound,
  R reaches full time with *HANG ON A TICK* shown, Enter requests a pause: the bench (S19) opens in request mode at
  the pause and its Esc answers it, no substitution [T180: was T166's default answer].
- **Close**: closing the window mid-match leaves no engine process within 5 s and publishes nothing.
- **Colours**: the home side's codes (the fixture's side B, `DesktopModel.home`, #562) are drawn light red, the
  away side's white, on the painted pitch.
- **The captain**: `best_leader` is T143's rule (goal2/core/views.py `_captain_recommendation`), over every country's
  eleven.

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

requires.require(modules=("PySide6", "pygame"))
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QEvent, Qt  # noqa: E402
from PySide6.QtGui import QColor, QKeyEvent  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from goal2.desktop import data_setup, fixed_page  # noqa: E402
from goal2.desktop.match_view import SPEEDS  # noqa: E402
from goal2.desktop.model import DesktopModel  # noqa: E402
from goal2.desktop.pygame_viewer import MARKS  # noqa: E402
from goal2.ui import theme  # noqa: E402
from goal2.ui.s06_desk import DeskScreen  # noqa: E402
from goal2.ui.s17_pitch import HANG_ON, NO_SOUND, PitchScreen, best_leader, suggested_captain  # noqa: E402
from goal2.ui.window import Window  # noqa: E402
from goal2.ui.pitch import HOME  # noqa: E402

CACHE = requires.CACHE
CAREER = requires.need(**requires.HALFTIME)
HOLLAND = 20
WAIT = 900          # seconds for a whole match under PyPy on a loaded runner
PLAY_NEXT = 5       # the desk's sixth option
_BASE = {}


def career():
    """A fresh copy of a career starting in 2028 (opened once per run)."""
    if "model" not in _BASE:
        folder = _BASE.setdefault("folder", tempfile.mkdtemp(prefix="goal2-t166-"))
        model = DesktopModel.open(CACHE / data_setup.TEMPLATE_NAME, CACHE / data_setup.DATA_NAME,
                                  Path(folder) / "unused.g2game", country=HOLLAND)
        model.new_campaign(HOLLAND, 2028)
        model.rename_manager("K Ees")
        _BASE["model"] = model
    return copy.deepcopy(_BASE["model"])


def tearDownModule():
    if "folder" in _BASE:
        shutil.rmtree(_BASE["folder"], ignore_errors=True)


def pypy():
    from goal2.tests.test_pypy_worker_t152 import pypy as found
    return found()


def app():
    application = QApplication.instance() or QApplication([])
    theme.install(application)
    return application


def key(window, k, text=""):
    window.keyPressEvent(QKeyEvent(QEvent.Type.KeyPress, k, Qt.KeyboardModifier.NoModifier, text))
    QApplication.instance().processEvents()


def pump(predicate, limit, what, each=None):
    """Run the window's event loop until `predicate()`; `each()` after every round."""
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


def open_desk(model):
    window = Window(data_setup.paths(Path(_BASE["folder"]) / "data-root"))
    window.resize(fixed_page.WIDTH, fixed_page.HEIGHT)
    window.show()
    desk = window.open_career(model)
    return window, desk


def play_next(window, desk):
    """[T167] The match day to kick-off: S14 Enter, S15 Enter (play), S16 C (the computer's captain)."""
    desk.highlight(PLAY_NEXT)
    key(window, Qt.Key.Key_Return)
    key(window, Qt.Key.Key_Return)
    key(window, Qt.Key.Key_Return)
    key(window, Qt.Key.Key_C, "c")
    screen = window.current()
    assert isinstance(screen, PitchScreen), desk.note.text()
    return screen


def to_the_desk(window, screen, limit, each=None):
    """[T167] On from S17 to the desk through the match day's stops: C on a taker card (no key: the current pick),
    Enter on the boards, the menus (play, then exit) and the round; [T180] Space on S18's notices."""
    from goal2.ui.s14_round import RoundScreen
    from goal2.ui.s16_choose import ChooseScreen

    def step():
        if each is not None:
            each()
        current = window.current()
        if current is screen and screen.stop_box.open:
            key(window, Qt.Key.Key_N if screen.stop_box.answers else Qt.Key.Key_Space)  # [T181] questions Y/N, notices any key
            return
        if current is screen or isinstance(current, DeskScreen):
            return
        if isinstance(current, ChooseScreen):
            key(window, Qt.Key.Key_C, "c")
        elif isinstance(current, RoundScreen) and current.arriving:
            return
        else:
            key(window, Qt.Key.Key_N if getattr(current, 'save_summary', False) else Qt.Key.Key_Return)
    pump(lambda: isinstance(window.current(), DeskScreen), limit, "the match did not reach the desk", step)


def as_shown(event):
    return {"kind": event.kind, "minute": event.minute, "score": list(event.score), "data": event.data}


def reference(snapshot, choices, fixture):
    """[T167] The same friendly through the bridge with the same answers, from the state the window's bridge started
    from (its captain confirmed). [was T166: today's WatchedController with frames off]"""
    from goal2.tests.match_day_policy import play_through_bridge
    from goal2.ui.s17_pitch import engine_fixture
    model = career()
    model.state = copy.deepcopy(snapshot)
    outcome = play_through_bridge(model, choices, fixture=engine_fixture(fixture), wait=WAIT)
    return model, outcome


def engine_kits(outcome):
    """[#583] The kits the engine computed for the match: DS:832E..8331 of its memory (0791:1073)."""
    from goal2.engine.original_match.image import Image
    image = Image.from_memory_component(outcome.memory)
    return (image.rd(0x832E, 1), image.rd(0x832F, 1)), (image.rd(0x8330, 1), image.rd(0x8331, 1))


@CAREER
class SameMatch(unittest.TestCase):
    """One friendly played from the desk to full time on S17, its keys pressed on the way, and the reference."""

    @classmethod
    def setUpClass(cls):
        from goal2.game.watched_jobs import LEAD
        pypy()
        cls.app = app()
        cls.lead = LEAD
        model = cls.model = career()
        window, desk = open_desk(model)
        out = cls.out = {"speeds": [], "marks": [], "worst": 0, "hang_on": False}
        try:
            screen = cls.screen = play_next(window, desk)
            controller = screen.controller
            bridge = cls.bridge = controller.bridge
            out["captain"] = model.state.captain
            out["fixture"] = model.state.campaign.next_fixture

            def watch():
                # The engine's samples, as its reader thread has received them, against the acknowledged one.
                out["worst"] = max(out["worst"], bridge._match.received_frames - 1 - bridge._frame_ack)
                if controller.quick and screen.isVisible():
                    labels = [w.text() for w in screen.key_bar.findChildren(type(screen.note), "keyLabel")]
                    out["hang_on"] = out["hang_on"] or (HANG_ON in labels and screen.note.text() == HANG_ON)

            pump(lambda: controller.drawn >= 0, 120, "no kick-off sample drawn", watch)
            out["kick_off_image"] = screen.pitch.grab().toImage()
            out["painted"] = list(screen.pitch.painted)
            out["kits"] = screen.kits
            out["countries"] = list(controller.display.countries)
            out["home_label"] = screen.home.styleSheet()
            # Painting stalled: the engine stops at the acknowledged sample + LEAD, and stays there.
            screen.pitch.setUpdatesEnabled(False)
            stalled_at = controller.drawn
            pump(lambda: bridge._match.received_frames - 1 >= bridge._frame_ack + LEAD, 120,
                 "the engine did not reach the lead", watch)
            held = time.monotonic() + 1
            pump(lambda: time.monotonic() > held, 5, "", watch)
            out["stalled"] = (stalled_at, controller.drawn, bridge._frame_ack, bridge._match.received_frames - 1)
            screen.pitch.setUpdatesEnabled(True)
            # ←→: Slowest, then each faster speed in turn.
            for _ in range(3):
                key(window, Qt.Key.Key_Left)
                out["speeds"].append(screen.speed())
            for _ in range(5):
                key(window, Qt.Key.Key_Right)
                out["speeds"].append(screen.speed())
            # ↑↓: the display styles.
            for k in (Qt.Key.Key_Down, Qt.Key.Key_Down, Qt.Key.Key_Up):
                key(window, k)
                out["marks"].append((screen.pitch.marks, screen.status.text()))
            key(window, Qt.Key.Key_Space)
            out["enlarged"] = screen.pitch.enlarged
            out["enlarged_image"] = screen.pitch.grab().toImage()
            key(window, Qt.Key.Key_Space)
            out["closed_again"] = not screen.pitch.enlarged
            key(window, Qt.Key.Key_F9)
            out["f9"] = (screen.note.text(), window.current() is screen, controller.requests)
            # R: no more pacing, to full time.
            key(window, Qt.Key.Key_R)
            to_the_desk(window, screen, WAIT, watch)
            out["desk"] = window.current()
            out["desk_note"] = out["desk"].note.text() if isinstance(out["desk"], DeskScreen) else None
            out["shown"] = controller.shown()
            out["error"] = controller.error
            out["outcome"] = controller.outcome
            out["engine_left"] = getattr(model, "_match_engine", None)
        finally:
            window.close()
            window.deleteLater()
            cls.app.processEvents()
        cls.reference_model, cls.reference_outcome = reference(controller.given._snapshot, controller.choices,
                                                               out["fixture"])

    def test_play_next_game_plays_the_friendly_to_full_time_and_publishes_it(self):
        out = self.out
        self.assertIsNone(out["error"])
        self.assertIsNotNone(out["outcome"])
        self.assertIsInstance(out["desk"], DeskScreen)
        self.assertIn("Full time:", out["desk_note"])
        result = self.model.result_text().split("\n", 1)[0]
        self.assertIn(result, out["desk_note"])
        self.assertEqual(self.model.state.match_count, _BASE["model"].state.match_count + 1)
        # [T167, D3: was T166's "closed at full time"] the match day keeps the window's engine for the next match
        self.assertIsNotNone(out["engine_left"], "the window's engine stays for the next match")

    def test_the_events_shown_are_the_bridge_s_in_order(self):
        shown = self.out["shown"]
        self.assertEqual(shown, [as_shown(e) for e in self.bridge.events])
        self.assertEqual(shown, [as_shown(e) for e in self.out["outcome"].events])
        self.assertTrue(any(e["kind"] == "decision" and e["data"]["context"] == "half_time" for e in shown))

    def test_the_published_career_equals_the_same_match_through_the_bridge(self):
        self.assertEqual([as_shown(e) for e in self.out["outcome"].events],
                         [as_shown(e) for e in self.reference_outcome.events])
        self.assertEqual(self.out["outcome"].result, self.reference_outcome.result)
        self.assertEqual(self.model.state, self.reference_model.state)

    def test_the_captain_is_the_suggested_one(self):
        self.assertIsNotNone(self.out["captain"])
        self.assertEqual(self.out["captain"], suggested_captain(_BASE["model"].state))

    def test_pacing_never_exceeds_the_acknowledged_sample_plus_lead(self):
        self.assertLessEqual(self.out["worst"], self.lead)
        stalled_at, drawn, acked, received = self.out["stalled"]
        self.assertEqual(received, acked + self.lead, "the stalled engine waits at the lead")
        self.assertEqual(drawn, acked, "only drawn samples are acknowledged")
        self.assertLessEqual(drawn, stalled_at + 1, "nothing was drawn while painting was stalled")

    def test_left_and_right_step_through_the_six_speeds(self):
        names = [name for name, _ in SPEEDS]
        self.assertEqual(self.out["speeds"], names[2::-1] + names[1:])

    def test_up_and_down_change_the_display(self):
        marks = self.out["marks"]
        self.assertEqual([m for m, _ in marks], [2, 3, 2])
        for m, status in marks:
            self.assertIn(f"marks: {MARKS[m].lower()}", status)

    def test_space_enlarges_the_commentary(self):
        self.assertTrue(self.out["enlarged"])
        self.assertTrue(self.out["closed_again"])
        image = self.out["enlarged_image"]
        heading = QColor(theme.HEADING)
        # The enlarged commentary's frame, cyan, over the right part of the pitch.
        found = any(image.pixelColor(x, image.height() // 2) == heading
                    for x in range(image.width() // 2, image.width()))
        self.assertTrue(found, "no enlarged commentary over the pitch")

    def test_f9_says_there_is_no_sound_and_does_nothing_else(self):
        note, still_there, requests = self.out["f9"]
        self.assertEqual(note, NO_SOUND)
        self.assertTrue(still_there)
        self.assertEqual(requests, 0)

    def test_r_reaches_full_time_with_hang_on_a_tick_shown(self):
        self.assertTrue(self.out["hang_on"], "HANG ON A TICK was not shown during the quick result")
        self.assertIsNotNone(self.out["outcome"])

    def test_each_side_is_drawn_in_the_engine_s_kit(self):
        """[#583; was T166's 'home light red, away white'] Each mark in its side's kit, the keepers in the second
        colour, and the kits are the engine's own for this match (DS:832E..8331, 0791:1073)."""
        from goal2.ui.pitch import KEEPERS
        kits = self.out["kits"]
        self.assertEqual((kits.shirt, kits.keeper), engine_kits(self.out["outcome"]))
        from goal2.desktop.watched import pitch_identity  # noqa: F401 - the identity S17 sends
        fixture = self.out["fixture"]
        names = self.model.goaldat.country_names
        self.assertEqual(self.out["countries"], [names[fixture.side_a], names[fixture.side_b]])
        self.assertIn(kits.colour(HOME), self.out["home_label"])
        painted = self.out["painted"]
        self.assertEqual({team for _, team, *_ in painted}, {0, 1})
        image = self.out["kick_off_image"]
        for slot, team, text, colour, box in painted:
            with self.subTest(slot=slot):
                self.assertEqual(colour, kits.colour(team, slot in KEEPERS))
                want = QColor(colour)
                pixels = (image.pixelColor(x, y) for x in range(max(0, box.left()), min(image.width(), box.right()))
                          for y in range(max(0, box.top()), min(image.height(), box.bottom())))
                self.assertTrue(any(p == want for p in pixels), f"slot {slot}'s {text!r} is not drawn in {colour}")


@CAREER
class BenchAndClose(unittest.TestCase):
    """Enter requests a pause; S19 opens in request mode and its Esc answers it with no substitution; then the window
    closes mid-match."""

    @classmethod
    def setUpClass(cls):
        pypy()
        cls.app = app()
        model = cls.model = career()
        window, desk = open_desk(model)
        out = cls.out = {}
        try:
            screen = play_next(window, desk)
            controller = screen.controller
            bridge = controller.bridge
            out["before"] = copy.deepcopy(model.state)
            pump(lambda: controller.drawn >= 0, 120, "no kick-off sample drawn")
            key(window, Qt.Key.Key_Return)
            out["requests"] = controller.requests
            out["request_note"] = screen.note.text()
            pump(lambda: type(window.current()).__name__ == "MenuScreen", 120, "the match menu did not open at the pause")
            key(window, Qt.Key.Key_Space)
            out["bench_mode"] = window.current().mode
            key(window, Qt.Key.Key_Escape)        # bench -> match menu
            key(window, Qt.Key.Key_Escape)        # original in-match menu -> play, no substitution
            pump(lambda: "pause" in controller.answered, 120, "the pause was not answered")
            out["choice"] = controller.choices[-1]
            out["waiting"] = bridge.waiting
            out["decisions"] = [e.data.get("context") for e in bridge.events if e.kind == "decision"]
            pump(lambda: any("PAUSE" in line for line in screen.lines), 60, "the pause is not in the commentary")
            out["note"] = screen.note.text()
            out["busy"] = bridge.busy
            process = bridge.shared.engine.process
        finally:
            started = time.monotonic()
            window.close()
            window.deleteLater()
            cls.app.processEvents()
        try:
            out["code"] = process.wait(timeout=5)
        except Exception as exc:  # noqa: BLE001 - asserted below
            out["code"] = repr(exc)
        out["seconds"] = time.monotonic() - started
        out["engine_left"] = getattr(model, "_match_engine", None)

    def test_enter_requests_a_pause_that_is_answered(self):
        out = self.out
        self.assertEqual(out["requests"], 1)
        self.assertIn("Bench requested", out["request_note"])
        self.assertIn("pause", out["decisions"])
        self.assertIsNone(out["waiting"])
        self.assertEqual(out["bench_mode"], "request")   # [T180: was T166's default answer, "T180" in the note]
        self.assertEqual(out["choice"], ("pause", []))
        self.assertNotIn("T180", out["note"])

    def test_closing_the_window_mid_match_leaves_no_engine_and_publishes_nothing(self):
        out = self.out
        self.assertTrue(out["busy"], "the match was still running when the window closed")
        self.assertNotIsInstance(out["code"], str, out["code"])
        self.assertLess(out["seconds"], 5)
        self.assertIsNone(out["engine_left"])
        self.assertEqual(self.model.state, out["before"])
        self.assertIsNone(self.model.state.last_match)


@CAREER
class Captain(unittest.TestCase):
    def test_best_leader_is_t143_s_rule(self):
        requires.require(modules=("unicorn",))
        from goal2.core.views import PLAYER_SIZE, _captain_recommendation
        state = career().state

        class Records:
            """The Core's reads of the player array (`views._player`) over the Python route's records."""
            mem = b"".join(state.players)

            def far(self, pointer):
                return 0
        self.assertEqual(len(state.players[1]), PLAYER_SIZE)
        compared = 0
        for country in range(1, len(state.countries)):
            record = state.countries[country]
            eleven = [int.from_bytes(record[2 * i:2 * i + 2], "little") for i in range(11)]
            if not all(eleven):
                continue
            with self.subTest(country=country):
                self.assertEqual(best_leader(state.players, eleven), _captain_recommendation(Records(), eleven)[0])
                compared += 1
        self.assertGreater(compared, 100)


if __name__ == "__main__":
    unittest.main()
