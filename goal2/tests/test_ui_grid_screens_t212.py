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
    def on_the_grid(self, window, at_least=100):
        """No widget off the cell, no card: and the check saw the page."""
        found = grid_check.violations(window)
        self.assertGreater(len(grid_check.widgets(window)), at_least, "the check saw the page's widgets")
        self.assertEqual(found, [], "on the 16 x 32 grid with no card")

    def states(self):
        """(name, how to put the screen in it) for each state the screen shows."""
        return (("default", lambda screen: None),)

    def check_state(self, name, put):
        """The state on a never-shown window at the page's own size (on the grid, no card, nothing squeezed) and on a shown window at
        each size of `SIZES` (`fixed_page.problems` is empty)."""
        window, screen = self.canonical(self.make)
        put(screen)
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
        """The wait across the top (4 rows), the card (69 x 18) and the strip (20 wide, its twelve rows) a cell apart."""
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


if __name__ == "__main__":
    unittest.main()
