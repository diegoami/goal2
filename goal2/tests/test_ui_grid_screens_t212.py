"""[designed: owner, 2026-11-09, #667; T212] The selection screens: captain and taker (S16), the pitch (S17) and the bench (S19) on the 16 x 32 grid.

The claim it protects: **these screens fit and sit on the grid.** [designed: owner, 2026-11-08; docs/design/ui-2026-11/
fidelity-review.md §3] Each is laid out in cells (goal2/ui/cells.py) with frames for panels (goal2/ui/frame.py): at 1440x1080,
1440x900 and 2110x1213 (and 1440x1061, what a measured Windows runner gave a window asked for 1440x1080) `fixed_page.problems` is
empty, every widget rectangle is a multiple of the cell (T210's check, at the 4:3 page's own size) and there is no card (`#box`,
`#boxHeading`); and none of them is on `reflow_pending.PENDING` or `grid_pending.PENDING`, so the helpers enforce it everywhere
else. It is true in every state the screens have, with the longest text each shows.

[designed: T212] The pitch's own look (the drawn field, the players, the ball) is T179/#573's and is not touched: S17 is the screen
that hosts it (the score, the commentary, the stop box over it), laid out on the cells.

The geometry is measured on a window that is never shown where the grid is concerned (a desktop clamps a top-level window to its
work area); a shown window is asked for the sizes and the screen must fit the size it gets, whatever that is: no test here asserts a
size. The careers read GOAL.DAT and the E010 half-time template from the git-ignored `.cache/` and skip without them
(goal2/tests/requires.py).
"""
import unittest

from goal2.tests import requires
from goal2.tests import grid_pending, reflow_pending
from goal2.tests import test_ui_desk_t164
from goal2.tests.test_ui_desk_t164 import CAREER, holland
from goal2.tests.test_ui_grid_screens_t211 import SIZES, Base as GridBase

requires.require(modules=("PySide6",))

from PySide6.QtWidgets import QLabel  # noqa: E402

from goal2.desktop import fixed_page  # noqa: E402
from goal2.ui import cells, grid_check, theme  # noqa: E402
from goal2.ui.cell_parts import GridCard, GridStrip  # noqa: E402
from goal2.ui.cells import CellLabel  # noqa: E402
from goal2.ui.frame import Frame  # noqa: E402
from goal2.ui.s16_choose import ChooseScreen  # noqa: E402

TRINIDAD = "Trinidad/Tobago"   # fifteen characters: the longest country name


def tearDownModule():
    test_ui_desk_t164.tearDownModule()


class Base(GridBase):
    SEEN = 100   # the widgets the check must have walked (the pitch's page has fewer than the card's)

    def on_the_grid(self, window, at_least=None):
        """No widget off the cell, no card: and the check saw the page."""
        found = grid_check.violations(window)
        self.assertGreater(len(grid_check.widgets(window)), at_least or self.SEEN, "the check saw the page's widgets")
        self.assertEqual(found, [], "on the 16 x 32 grid with no card")

    def states(self):
        """(name, how to put the screen in it) for each state the screen shows."""
        return (("default", lambda screen: None),)

    def settle(self, screen):
        """What the running screen does by itself between two paints (S17's tick refreshes it every 4 ms): nothing by default."""

    def check_state(self, name, put):
        """The state on a never-shown window at the page's own size (on the grid, no card, nothing squeezed) and on a shown window at
        each size of `SIZES` (`fixed_page.problems` is empty)."""
        window, screen = self.canonical(self.make)
        put(screen)
        self.relayout(window)
        self.settle(screen)
        self.relayout(window)
        self.assertIs(window.current(), screen)
        self.assertEqual(fixed_page.problems(window), [], f"{name}, the page's own size")
        self.on_the_grid(window)
        shown = self.window()
        shown_screen = self.make(shown)
        put(shown_screen)
        for width, height in SIZES:
            shown.resize(width, height)
            shown.show()
            for _ in range(3):
                self.app.processEvents()
            self.settle(shown_screen)
            for _ in range(3):
                self.app.processEvents()
            self.assertEqual(fixed_page.problems(shown), [], f"{name} at {shown.width()}x{shown.height()}")

    def every_state_fits(self):
        for name, put in self.states():
            with self.subTest(state=name):
                self.check_state(name, put)

    def text_fits_its_cells(self, root, message=""):
        """Every label of `root` has the cells its text takes (a label is as wide as its characters: none is clipped or squeezed)."""
        cell = cells.cell_w(root)
        for label in root.findChildren(CellLabel):
            if label.isVisibleTo(root):
                self.assertLessEqual(label.cols(), round(label.width() / cell), f"{message} {label.objectName()} {label.text()!r}")

    def not_pending(self, name, kind):
        for lists in (reflow_pending.PENDING, grid_pending.PENDING):
            self.assertNotIn(name, lists)
        self.assertTrue(kind.GRID)


@CAREER
class ChooseOnTheGrid(Base):
    """S16 in each mode it has: the captain, a set-piece taker and the penalty order."""

    mode = "captain"

    def make(self, window):
        model = holland()
        window.open_career(model)
        self.model = model
        words = list(model.state.managed_squad[:11])
        screen = ChooseScreen(window, model, self.mode, words, words[0], lambda value: None, role=2, takers=5,
                              match="Holland v Norway", computer=words[1])
        screen.timer.stop()
        return window.push(screen)

    def longest(self, screen):
        """The longest text S16 shows: the eleven's names at twelve characters, the longest country in the frame."""
        data = screen.model.goaldat
        for word in screen.eleven:
            data.player_names[word] = "Abcdefghij"
            data.player_initials[word] = "X"
        screen.cards = [dict(card, full_name="X Abcdefghij") for card in screen.cards]
        data.country_names[screen.model.state.managed_country] = TRINIDAD
        screen._show()

    def states(self):
        def longest(screen):
            self.longest(screen)

        def last(screen):
            screen.move(-1)   # the highlight wraps to the eleventh

        def picks(screen):
            if screen.mode == "order":
                self.longest(screen)
                for _ in range(10):
                    screen.choose()
                    screen.move(1)

        return (("default", lambda screen: None), ("longest names", longest), ("last", last), ("picks", picks))

    def test_captain_fits_at_every_size_and_is_on_the_grid(self):
        self.mode = "captain"
        self.every_state_fits()

    def test_taker_fits_at_every_size_and_is_on_the_grid(self):
        self.mode = "taker"
        self.every_state_fits()

    def test_penalty_order_fits_at_every_size_and_is_on_the_grid(self):
        self.mode = "order"
        self.every_state_fits()

    def test_it_is_not_on_either_pending_list(self):
        """It was listed (reflow_pending, grid_pending) until T212: the helpers now hold it to fitting and to the grid."""
        self.not_pending("ChooseScreen", ChooseScreen)

    def test_its_panels_are_frames_and_the_card_is_the_squads(self):
        window, screen = self.canonical(self.make)
        self.assertIsInstance(screen.card, GridCard)
        self.assertEqual([frame.label for frame in screen.findChildren(Frame)],
                         ["name", "readiness", "skills", "tactics", "characteristics", "holland"])
        self.assertEqual(grid_check.cards(window), [])
        self.assertEqual(screen.findChildren(QLabel, "kbd"), [], "no boxed key cap on a grid screen")

    def test_the_card_the_strip_and_the_wait_are_where_the_cells_put_them(self):
        """The wait (4 rows) across the top, the card (69 x 18) and the strip (20 wide, its twelve rows) under it a cell apart."""
        window, screen = self.canonical(self.make)
        cell, row = cells.cell_w(screen), cells.row_px(screen)
        self.assertEqual(round(screen.card.width() / cell), GridCard.COLS)
        self.assertEqual(round(screen.strip.width() / cell), 20)
        self.assertEqual(round(screen.card.height() / row), GridCard.ROWS)
        self.assertEqual(round(screen.strip.height() / row), 12, "its rule and the eleven, no taller")
        gap = screen.strip.x() - (screen.card.x() + screen.card.width())
        self.assertEqual(round(gap / cell), 1, "one empty cell separates")
        self.assertEqual(screen.wait_box.height(), row * 4)
        self.assertEqual(screen.wait_box.width(), window.page.width())
        self.assertLessEqual(screen.wait_box.y() + screen.wait_box.height(), screen.card.y(), "the words are over the card")
        self.assertEqual(screen.strip.y() + screen.strip.height(), screen.card.y() + screen.card.height(),
                         "the eleven is level with the card's foot (no region of the page is left empty)")
        self.assertEqual(len(screen.strip.shown_texts()), 11)

    def test_each_mode_says_what_the_match_waits_for_in_the_rows_it_has(self):
        for mode in ("captain", "taker", "order"):
            with self.subTest(mode=mode):
                self.mode = mode
                window, screen = self.canonical(self.make)
                self.assertTrue(screen.wait_box.isVisibleTo(screen))
                self.assertLessEqual(len(screen.wait_detail.lines()), 3, screen.wait_detail.text())

    def test_the_bar_keeps_its_two_rows(self):
        for mode in ("captain", "taker", "order"):
            with self.subTest(mode=mode):
                self.mode = mode
                window, screen = self.canonical(self.make)
                self.assertEqual(screen.key_bar.height(), cells.span_px(screen, 2), "two rows, the page's own")
                self.assertEqual(screen.body.height(), window.page.height() - cells.row_px(screen) - screen.key_bar.height())

    def test_the_order_wraps_in_its_rows_whatever_the_eleven_picked(self):
        self.mode = "order"
        window, screen = self.canonical(self.make)
        self.longest(screen)
        for _ in range(10):
            screen.choose()
            screen.move(1)
        self.relayout(window)
        self.assertLessEqual(len(screen.order_label.lines()), screen.order_label.height() // cells.row_px(screen))
        self.assertIn("of 5)", screen.order_label.text())


class FakeBridge:
    """A match day's bridge that never starts an engine: S17's polls find nothing (the shape of test_ui_replay_t181's)."""
    busy = True
    closed = False
    token = "synthetic"
    reports = []

    def __init__(self):
        self.acks = []

    def start(self, *args, **kwargs):
        return self.token

    def poll(self, token):
        return []

    def poll_frames(self, token):
        return []

    def ack_frames(self, token, sequence):
        self.acks.append(sequence)

    def pause(self, token):
        return True

    def frames_drained(self):
        return True

    def cancel_and_reap(self, token):
        self.busy = False

    def close(self):
        self.busy = False
        self.closed = True

    def answer(self, token, pairs, changes=None):
        pass


PITCH = requires.need(modules=("PySide6", "pygame"), **requires.HALFTIME)


@PITCH
class PitchOnTheGrid(Base):
    """S17, the screen that hosts the pitch: the score, the pitch's cells, the commentary, what is said under the pitch, the
    stop box over it. The pitch's own drawing is not tested here (it is T179's)."""

    SEEN = 25
    names = None   # the two countries' names the match is made with (None: the fixture's)
    kind = None

    def make(self, window):
        from goal2.tests.test_ui_match_day_t167 import career
        from goal2.ui.match_day import for_window
        from goal2.ui.s17_pitch import MatchController, PitchScreen
        model = career()
        window.open_career(model)
        self.model = model
        day = for_window(window, model)
        day.fixture = model.state.campaign.next_fixture
        day.watch = True
        self.bridge = FakeBridge()
        controller = MatchController(model, day.fixture, self.bridge)
        controller.start()
        if self.names is not None:
            controller.display.countries = list(self.names)
        if self.kind is not None:
            controller.display.kind = self.kind
        day.controller = controller
        screen = window.push(PitchScreen(window, model, controller, day))
        screen.timer.stop()
        day.pitch = screen
        self.addCleanup(screen.stop_box.cancel)
        return screen

    def settle(self, screen):
        screen.refresh()   # the tick does it: the commentary is fitted to the cells it has, the badge placed

    def lines(self, screen, count=20):
        screen.lines = [f"{minute}′ A player with a long surname scored after an assist from Another Long Name." for minute in range(count)]
        screen.refresh()

    def opportunity(self, screen, keeper=False, injured=2):
        from types import SimpleNamespace
        words = screen.model.state.managed_squad
        data = dict(context="substitution_opportunity", request_substitution=True, keeper_unavailable=keeper,
                    timeout_polls=1000 if keeper else 400, poll_ms=10, eleven=list(words[:11]), bench=list(words[11:]),
                    substitutions_left=5, substitutions_now=True, injured=list(words[:injured]), requested=[[words[0], words[12]]],
                    refused="two goalkeepers are on the pitch and the other side has none, so the eleven is refused")
        decision = SimpleNamespace(data=data, minute=5, score=[0, 0])
        screen.controller.stop = decision
        screen.held = decision
        screen.show_opportunity(decision)

    def states(self):
        from goal2.ui import s17_pitch
        from goal2.ui.s18_stop import ACTION_REPLAY, NOTICE_OPPONENT, NOTICE_SHOOTOUT, SAVE_GOAL, SHOOTOUT, YES_NO
        from PySide6.QtCore import Qt

        def question(screen):
            screen.show_stop("replay", ACTION_REPLAY, "The goal's last seconds are replayed from the samples painted.", lambda key: None,
                             dict(YES_NO))

        def save_question(screen):
            screen.show_stop("save-goal", SAVE_GOAL, "", lambda key: None, dict(YES_NO))

        def opponent(screen):
            screen.show_stop(NOTICE_OPPONENT, "SUBSTITUTION Xxxxxxxxxxxx on for Yyyyyyyyyyyy " + "x" * 20,
                             f"{TRINIDAD}: {TRINIDAD} 12 - 12 {TRINIDAD}, 120′. Press any key: play on.", lambda key: None)

        def shootout(screen):
            screen.show_stop(NOTICE_SHOOTOUT, SHOOTOUT, "The match ends level: the penalty shoot-out follows.", lambda key: None)

        def requested(screen):
            screen.controller.substitution_requested = True
            screen.refresh()

        def notes(screen):
            for note in (s17_pitch.REQUESTED, s17_pitch.NO_SOUND, s17_pitch.HANG_ON,
                         "Made: " + ", ".join(f"X Xxxxxxxxxx on for Y Yyyyyyyyyy" for _ in range(3)) + "."):
                screen.controller.note = note
                screen.refresh()

        def paused(screen):
            screen.toggle_commentary()

        def result(screen):
            screen._result_text("REPLAY")

        return (("default", lambda screen: None), ("a full commentary", self.lines), ("replay question", question),
                ("save question", save_question), ("the other side's substitution", opponent), ("shoot-out notice", shootout),
                ("opportunity", self.opportunity), ("keeper opportunity", lambda screen: self.opportunity(screen, True, 3)),
                ("badge", requested), ("notes", notes), ("reading pause", paused), ("replay", result))

    def test_the_pitch_screen_fits_at_every_size_and_is_on_the_grid(self):
        self.every_state_fits()

    def test_the_longest_names_and_kind_fit_at_every_size(self):
        self.names = [TRINIDAD, "Neth. Antilles"]
        self.kind = "x" * 40
        self.check_state("the longest names", lambda screen: self.lines(screen))

    def test_it_is_not_on_either_pending_list(self):
        """It was listed (reflow_pending, grid_pending) until T212, with its saved variant: the helpers now hold both to the cells."""
        from goal2.ui.s17_pitch import PitchScreen
        self.not_pending("PitchScreen", PitchScreen)
        for lists in (reflow_pending.PENDING, grid_pending.PENDING):
            self.assertNotIn("SavedPitchScreen", lists)

    def test_the_score_the_pitch_and_the_commentary_are_where_the_cells_put_them(self):
        """The score in three rows, the pitch 64 x 18 under it, the commentary's frame at its right a cell apart and a row lower."""
        from goal2.ui.s17_pitch import COMMENTARY_COLS, HEAD_ROWS, PITCH_COLS, PITCH_ROWS
        window, screen = self.canonical(self.make)
        cell, row = cells.cell_w(screen), cells.row_px(screen)
        self.assertEqual(round(screen.pitch.width() / cell), PITCH_COLS)
        self.assertEqual(round(screen.pitch.height() / row), PITCH_ROWS)
        self.assertEqual(round(screen.score_head.height() / row), HEAD_ROWS)
        frame = next(f for f in screen.findChildren(Frame) if f.label == "commentary")
        self.assertEqual(round(frame.width() / cell), COMMENTARY_COLS)
        gap = frame.x() - (screen.pitch.x() + screen.pitch.width())
        self.assertEqual(round(gap / cell), 1, "one empty cell separates")
        self.assertEqual(frame.y() - screen.pitch.y(), row, "a row under the pitch's top")
        self.assertEqual(frame.x() + frame.width(), window.page.width())
        self.assertEqual(grid_check.cards(window), [])

    def test_the_pitch_keeps_its_drawing_size_over_the_mockups_to_the_cell(self):
        """The pitch's drawing is T179's: the widget is the cells it is given (1024 x 576 logical) and paints at the scale of its size."""
        from goal2.ui import pitch
        window, screen = self.canonical(self.make)
        self.assertEqual((pitch.WIDTH, pitch.HEIGHT), (1000, 560), "the drawing's reference size is untouched")
        self.assertAlmostEqual(screen.pitch.scale(), 1024 / 1000, places=3)

    def test_the_commentary_keeps_whole_entries_in_the_rows_it_has(self):
        window, screen = self.canonical(self.make)
        self.lines(screen, 40)
        self.relayout(window)
        self.lines(screen, 40)
        rows = screen.commentary.height() // cells.row_px(screen)
        self.assertGreater(rows, 10)
        self.assertLessEqual(len(screen.commentary.lines()), rows)
        self.assertIn(screen.lines[-1], screen.commentary.text(), "the newest entry is shown whole")

    def test_the_reading_pause_banner_takes_the_score_rows_and_the_score_comes_back(self):
        window, screen = self.canonical(self.make)
        self.assertFalse(screen.wait_box.isVisibleTo(screen))
        screen.toggle_commentary()
        self.relayout(window)
        self.assertTrue(screen.wait_box.isVisibleTo(screen))
        self.assertFalse(screen.score_head.isVisibleTo(screen))
        self.assertLessEqual(len(screen.wait_detail.lines()), 1)
        screen.toggle_commentary()
        self.relayout(window)
        self.assertTrue(screen.score_head.isVisibleTo(screen))
        self.assertFalse(screen.wait_box.isVisibleTo(screen))

    def test_the_bar_keeps_its_two_rows_whatever_the_keys_say(self):
        window, screen = self.canonical(self.make)
        rows = cells.span_px(screen, 2)
        self.assertEqual(screen.key_bar.height(), rows)
        for put in (lambda: screen._result_text("HANG ON A TICK"), lambda: screen.toggle_commentary(),
                    lambda: screen.toggle_commentary()):
            put()
            self.relayout(window)
            self.assertEqual(screen.key_bar.height(), rows)
            self.assertEqual(screen.body.height(), window.page.height() - cells.row_px(screen) - rows)

    def test_the_stop_box_is_cells_a_whole_number_of_columns_and_rows_inside_the_pitch(self):
        window, screen = self.canonical(self.make)
        cell, row = cells.cell_w(screen), cells.row_px(screen)
        for name, put in self.states():
            if name not in ("replay question", "the other side's substitution", "opportunity", "keeper opportunity"):
                continue
            with self.subTest(state=name):
                screen.stop_box.cancel()
                put(screen)
                self.relayout(window)
                box = screen.stop_box
                self.assertTrue(box.open)
                self.assertEqual(box.width(), round(box.cols * cell))
                self.assertEqual(box.height(), box.rows() * row)
                top = box.mapTo(screen, box.rect().topLeft())
                pitch = screen.pitch.mapTo(screen, screen.pitch.rect().topLeft())
                self.assertGreaterEqual(top.x(), pitch.x())
                self.assertGreaterEqual(top.y(), pitch.y())
                self.assertLessEqual(top.x() + box.width(), pitch.x() + screen.pitch.width())
                self.assertLessEqual(top.y() + box.height(), pitch.y() + screen.pitch.height())
                self.assertEqual((top.x() - pitch.x()) % round(cell), 0, "a whole number of cells from the pitch's edge")
                self.assertEqual((top.y() - pitch.y()) % row, 0)
                screen.stop_box.cancel()


@PITCH
class SavedPitchOnTheGrid(PitchOnTheGrid):
    """The saved goal's replay (SavedPitchScreen, goal2/ui/replays.py) is S17 over a recorded goal: the same cells."""

    def make(self, window):
        from goal2.tests.test_ui_match_day_t167 import career
        from goal2.tests.test_ui_replay_t181 import frames
        from goal2.ui import replays
        model = career()
        window.open_career(model)
        self.model = model
        goal = {"frames": frames(), "countries": ["Holland", "Romania"], "score": [0, 1], "minute": 3, "scorer": "A Player",
                "kits": {"shirt": [1, 2], "keeper": [3, 4]}, "kind": "FRIENDLY"}
        screen = replays.play_saved(window, model, {"kind": "goal", "data": goal})
        screen.timer.stop()
        self.addCleanup(screen.stop_box.cancel)
        return screen

    def states(self):
        return (("replay", lambda screen: None), ("a full commentary", self.lines))

    def test_it_is_a_saved_pitch_screen_on_the_cells(self):
        window, screen = self.canonical(self.make)
        self.assertEqual(type(screen).__name__, "SavedPitchScreen")
        self.assertEqual(round(screen.pitch.width() / cells.cell_w(screen)), 64)

    # the checks that need a live match (the stop box, the notes, the banner) are PitchOnTheGrid's own
    test_the_pitch_screen_fits_at_every_size_and_is_on_the_grid = PitchOnTheGrid.test_the_pitch_screen_fits_at_every_size_and_is_on_the_grid
    test_the_longest_names_and_kind_fit_at_every_size = None
    test_the_reading_pause_banner_takes_the_score_rows_and_the_score_comes_back = None
    test_the_stop_box_is_cells_a_whole_number_of_columns_and_rows_inside_the_pitch = None
    test_the_bar_keeps_its_two_rows_whatever_the_keys_say = None
    test_it_is_not_on_either_pending_list = None
    test_the_pitch_keeps_its_drawing_size_over_the_mockups_to_the_cell = None
    test_the_commentary_keeps_whole_entries_in_the_rows_it_has = None
    test_the_score_the_pitch_and_the_commentary_are_where_the_cells_put_them = None


BENCH = requires.need(modules=("PySide6", "pygame"), **requires.HALFTIME)
LONG_REASON = ("This player has already been substituted and cannot return; choose a different player from the bench before "
               "continuing.")


@BENCH
class BenchOnTheGrid(Base):
    """S19 in each mode it has (make substitutions now, request, view, refused) and each state of its words: the pair chosen, the
    engine's reports, the longest names, up to three players the match has injured (each name then takes two rows of the strip)."""

    mode = "now"
    injured = ()

    def make(self, window):
        from types import SimpleNamespace
        from goal2.tests.test_ui_match_day_t167 import career
        from goal2.ui.s19_bench import BenchAnswer, BenchScreen
        model = career()
        window.open_career(model)
        self.model = model
        words = model.state.managed_squad
        self.off, self.on = words[1], words[12]
        context = {"now": "half_time", "request": "pause", "view": "extra_time", "refused": "half_time"}[self.mode]
        data = dict(context=context, eleven=list(words[:11]), bench=list(words[11:]), substitutions_left=5,
                    injured=[words[w] for w in self.injured])
        if self.mode == "request":
            data.update(substitutions_now=False, request_substitution=False)
        decision = SimpleNamespace(minute=45, score=[0, 0], data=data)
        answer = BenchAnswer(model, decision)
        report = None
        if self.mode == "refused":
            report = dict(asked=[[self.off, self.on]], made=[], requested=[], refused=[[self.off, self.on, LONG_REASON]],
                          substitutions_left=5)
        screen = window.push(BenchScreen(window, model, answer, names=("Italy", "Poland"), report=report,
                                         request=lambda *values: None))
        screen.cue_timer.stop()
        self.addCleanup(screen.cue_timer.stop)
        return screen

    def settle(self, screen):
        screen.refresh()

    def long_names(self, screen):
        data = screen.model.goaldat
        for word in screen.answer.words():
            data.player_names[word] = "Abcdefghij"
            data.player_initials[word] = "X"
        screen.refresh()

    def pair(self, screen):
        screen.answer.enter(self.off)
        screen.answer.enter(self.on)
        screen.refresh()

    def states(self):
        def long_message(screen):
            # the longest the player is told at once: a pair made and one refused with the engine's longest reason (the T188 test's);
            # in the request mode no pair is made (no legal stop), so what is said there is the request's line, the original's
            # refusal of the eleven and the screen's own message
            if self.mode == "request":
                screen.answer.refused = "Y Yyyyyyyyyy has too many goalkeepers"   # the original's own kind of message (214B:1765)
                screen.message = "Substitution request cancelled."
            else:
                screen.feedback_report = dict(made=[[self.off, self.on]], refused=[[self.off, self.on, LONG_REASON]], requested=[])
            screen.refresh()

        def refused_eleven(screen):
            screen.answer.refused = "Y Yyyyyyyyyy has too many goalkeepers"   # the original's own kind of message (214B:1765)
            screen.refresh()

        def pending(screen):
            self.pair(screen)
            screen.pending = True
            screen.refresh()

        def marked(screen):
            screen.answer.first = self.off
            screen.refresh()

        def longest(screen):
            self.long_names(screen)
            self.pair(screen)

        def unlimited(screen):
            screen.answer.friendly = True
            screen.refresh()

        def injured(count):
            def put(screen):
                words = screen.answer.words()
                screen.answer.injured.update(words[1:1 + count])
                screen.row = 1
                screen.refresh()
            return put

        return (("default", lambda screen: None), ("a pair", self.pair), ("a mark", marked), ("long words", long_message),
                ("the original's refused eleven", refused_eleven), ("waiting for the reply", pending), ("longest names", longest),
                ("unlimited", unlimited), ("one injured", injured(1)), ("three injured", injured(3)),
                ("three injured with the longest names", lambda screen: (self.long_names(screen), injured(3)(screen))),
                ("three injured and a pair", lambda screen: (injured(3)(screen), self.pair(screen))))

    def test_make_substitutions_now_fits_at_every_size_and_is_on_the_grid(self):
        self.mode = "now"
        self.every_state_fits()

    def test_the_request_mode_with_its_button_fits_at_every_size_and_is_on_the_grid(self):
        self.mode = "request"
        self.every_state_fits()

    def test_the_view_mode_fits_at_every_size_and_is_on_the_grid(self):
        self.mode = "view"
        self.every_state_fits()

    def test_the_engines_refusal_fits_at_every_size_and_is_on_the_grid(self):
        self.mode = "refused"
        self.every_state_fits()

    def test_it_is_not_on_either_pending_list(self):
        """It was listed (reflow_pending, grid_pending) until T212: the helpers now hold it to fitting and to the grid."""
        from goal2.ui.s19_bench import BenchScreen
        self.not_pending("BenchScreen", BenchScreen)

    def test_its_panels_are_frames_and_the_card_is_the_squads(self):
        window, screen = self.canonical(self.make)
        self.assertIsInstance(screen.card, GridCard)
        self.assertEqual([frame.label for frame in screen.findChildren(Frame) if frame.isVisibleTo(screen)],
                         ["name", "readiness", "skills", "tactics", "characteristics", "substitution", "holland"])
        self.assertEqual(grid_check.cards(window), [])
        self.assertEqual(screen.findChildren(QLabel, "kbd"), [], "no boxed key cap on a grid screen")

    def test_the_header_the_card_the_feedback_and_the_twenty_are_where_the_cells_put_them(self):
        """The mode over the match's words (two rows), the card (69 x 18) under them and the substitution's words in a frame of five rows
        under the card (the budget at the right of its first row), the twenty (20 wide, down to the foot) at the right a cell apart."""
        from goal2.ui.s19_bench import FEEDBACK_ROWS, HEAD_ROWS
        window, screen = self.canonical(self.make)
        cell, row = cells.cell_w(screen), cells.row_px(screen)
        self.assertEqual(round(screen.card.width() / cell), GridCard.COLS)
        self.assertEqual(round(screen.card.height() / row), GridCard.ROWS)
        self.assertEqual(round(screen.strip.width() / cell), 20)
        self.assertEqual(round(screen.strip.height() / row), 25, "down to the foot of the body")
        self.assertEqual(round((screen.strip.x() - screen.card.x() - screen.card.width()) / cell), 1, "one empty cell separates")
        top = screen.mode_label.mapTo(screen, screen.mode_label.rect().topLeft()).y()
        self.assertEqual(screen.card.mapTo(screen, screen.card.rect().topLeft()).y(), top + HEAD_ROWS * row)
        feedback = screen.note.parentWidget().parentWidget()
        bottom = screen.card.mapTo(screen, screen.card.rect().bottomLeft()).y() + 1
        self.assertEqual(feedback.mapTo(screen, feedback.rect().topLeft()).y(), bottom)
        self.assertEqual(round(feedback.height() / row), FEEDBACK_ROWS)
        self.assertIs(screen.counter.parentWidget(), screen.note.parentWidget(), "the budget is in the substitution's frame")
        self.assertLess(screen.counter.y(), screen.note.y(), "on its first row")
        self.assertEqual(screen.counter.x() + screen.counter.width(), screen.note.x() + screen.note.width(), "at its right")
        self.assertEqual(screen.counter.text(), "substitutions: unlimited (friendly)" if screen.answer.friendly else "substitutions left 5")

    def test_the_mode_is_left_of_its_button_whatever_it_says(self):
        """T203's header test, in cells: the cue's cells end before the button's begin, the button is a row of 22 cells."""
        self.mode = "request"
        window, screen = self.canonical(self.make)
        self.assertTrue(screen.request_button.isVisibleTo(screen))
        self.assertEqual(screen.request_button.height(), cells.row_px(screen))
        self.assertLess(screen.mode_label.geometry().right(), screen.request_button.geometry().left())
        self.assertGreaterEqual(screen.mode_label.width(), 34 * round(cells.cell_w(screen)) - 1)

    def test_the_note_takes_three_rows_the_longest_refusal_included(self):
        self.mode = "refused"
        window, screen = self.canonical(self.make)
        rows = screen.note.height() // cells.row_px(screen)
        self.assertEqual(rows, 3)
        self.assertIn(LONG_REASON, screen.note.text())
        self.assertLessEqual(len(screen.note.lines()), rows)

    def test_the_card_says_a_players_live_injury_in_the_two_rows_it_has(self):
        """"INJURED — live match" is 20 characters, the readiness frame 13: two rows (S08's "ready to play" is one)."""
        window, screen = self.canonical(self.make)
        screen.answer.injured.add(self.off)
        screen.row = screen.answer.words().index(self.off)
        screen.refresh()
        self.relayout(window)
        self.assertIn("INJURED", screen.card.readiness.text())
        self.assertEqual(len(screen.card.readiness.lines()), 2)
        self.assertLessEqual(len(screen.card.readiness.lines()), screen.card.readiness.height() // cells.row_px(screen))

    def test_the_bar_keeps_its_two_rows_whatever_the_enter_hint_says(self):
        """The bar is two rows (the key bar's own height) for each hint the bench gives: take off, put on, cancel, unmark."""
        window, screen = self.canonical(self.make)
        rows = cells.span_px(screen, 2)
        for put in (lambda: None, lambda: screen.move(11), lambda: self.pair(screen), lambda: screen.move(-11)):
            put()
            self.relayout(window)
            self.assertEqual(screen.key_bar.height(), rows, screen.enter_hint_text())
            self.assertEqual(screen.body.height(), window.page.height() - cells.row_px(screen) - rows)

    def shown(self, injured):
        """The bench on a shown window at the page's own size, with `injured` (indices in the squad) said injured by the match."""
        self.injured = injured
        window = self.window()
        screen = self.make(window)
        window.resize(*theme.PICTURE)
        window.show()
        for _ in range(3):
            self.app.processEvents()
        self.settle(screen)
        for _ in range(3):
            self.app.processEvents()
        return window, screen

    def test_an_injured_players_name_takes_two_rows_and_the_rows_under_it_move_down(self):
        """[designed: T212] A live injury is said in the strip's row (" · INJURED", S19's own words, T188b): the name and the word are more
        than the 16 cells the 20-cell strip leaves its name, so the row takes a second row, the paragraph of its name wrapped at the cells,
        and the rows under it move down. The text is whole (`texts()[-1]` has INJURED), nothing is squeezed."""
        window, screen = self.shown((1,))
        self.assertEqual(fixed_page.problems(window), [])
        row = screen.strip.rows[1]
        self.assertIn("INJURED", row.texts()[-1])
        unit = cells.row_px(screen)
        self.assertEqual(row.height(), 2 * unit)
        self.assertEqual(len(row.cells[-1].lines()), 2)
        self.assertEqual(screen.strip.rows[2].y(), row.y() + 2 * unit, "the next row is under the two")
        self.assertEqual(screen.strip.rows[0].height(), unit)
        self.assertEqual(grid_check.violations(window), [])

    def test_three_injured_players_fit_and_a_fourth_is_where_the_strip_runs_out_of_rows(self):
        """The strip has three rows more than the twenty and the gap need: three names that take two rows fit. A fourth is more than the
        page has rows for, and `fixed_page.problems` says so (nothing is hidden): the limit of the layout, stated."""
        window, screen = self.shown((1, 2, 3))
        self.assertEqual(fixed_page.problems(window), [])
        self.assertEqual([row.height() // cells.row_px(screen) for row in screen.strip.rows[:5]], [1, 2, 2, 2, 1])
        window, screen = self.shown((1, 2, 3, 4))
        self.assertNotEqual(fixed_page.problems(window), [], "four names of two rows are 24 rows, the strip has 23 for the players")



if __name__ == "__main__":
    unittest.main()
