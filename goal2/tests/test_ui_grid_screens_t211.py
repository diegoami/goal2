"""[designed: owner, 2026-11-09, #667; T211] The desk (S06) and the squad (S08) on the 16 x 32 grid.

The claim it protects: **these screens fit and sit on the grid.** [designed: owner, 2026-11-08; docs/design/ui-2026-11/
fidelity-review.md §3] Each is laid out in cells (goal2/ui/cells.py) with frames for panels (goal2/ui/frame.py): at 1440x1080,
1440x900 and 2110x1213 `fixed_page.problems` is empty, every widget rectangle is a multiple of the cell (T210's check, at the 4:3
page's own size) and there is no card (`#box`, `#boxHeading`); and neither screen is on `reflow_pending.PENDING` or
`grid_pending.PENDING`, so the helpers enforce it everywhere else.

The geometry is measured on a window that is never shown where the grid is concerned (a desktop clamps a top-level window to its
work area: a measured Windows runner gave 1440x1061 for 1440x1080), and the sizes a shown window is asked for are bounded by the
primary screen's available area; a window that is clamped is letterboxed, and the screen must still fit it. The careers read GOAL.DAT
and the E010 half-time template from the git-ignored `.cache/` and skip without them (goal2/tests/requires.py).
"""
import shutil
import tempfile
import unittest
from pathlib import Path

from goal2.tests import requires
from goal2.tests import grid_pending, reflow_pending
from goal2.tests.test_ui_desk_t164 import CAREER, holland, tearDownModule  # noqa: F401  (the module's career cache is theirs)

requires.require(modules=("PySide6",))

from PySide6.QtCore import Qt  # noqa: E402
from PySide6.QtWidgets import QApplication, QLabel, QLayout  # noqa: E402

from goal2.desktop import data_setup, fixed_page  # noqa: E402
from goal2.ui import cells, grid_check, theme  # noqa: E402
from goal2.ui.frame import Frame  # noqa: E402
from goal2.ui.s06_desk import DeskScreen  # noqa: E402
from goal2.ui.screen import Clickable  # noqa: E402
from goal2.ui.window import Window  # noqa: E402

SIZES = ((1440, 1080), (1440, 900), (2110, 1213))


class Base(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])
        cls.font_before = cls.app.font()
        theme.install(cls.app)

    @classmethod
    def tearDownClass(cls):
        cls.app.setFont(cls.font_before)

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="goal2-t211-"))
        self.addCleanup(shutil.rmtree, self.tmp, True)

    def window(self):
        window = Window(data_setup.Paths(self.tmp / "goal2"))
        self.addCleanup(lambda: (window.close(), window.deleteLater(), self.app.processEvents()))
        return window

    def canonical(self, make):
        """A window that is never shown, at the 4:3 page's own size (1440x1080, scale 1), laid out: (window, screen)."""
        window = self.window()
        window.resize(*theme.PICTURE)
        screen = make(window)
        window.centralWidget().resize(*theme.PICTURE)
        window.centralWidget().fit()
        window.layout().activate()
        for layout in window.page.findChildren(QLayout):
            layout.activate()
        self.assertEqual((window.page.width(), window.page.height()), theme.PICTURE)
        return window, screen

    def fitting(self, make, check=None):
        """The screen at each size of `SIZES` (a window is asked for no more than the screen has): `fixed_page.problems` is empty."""
        from PySide6.QtGui import QGuiApplication
        window = self.window()
        screen = make(window)
        available = QGuiApplication.primaryScreen().availableGeometry()
        for width, height in SIZES:
            with self.subTest(size=(width, height)):
                window.resize(min(width, available.width()), min(height, available.height()))
                window.show()
                for _ in range(3):
                    self.app.processEvents()
                self.assertEqual(fixed_page.problems(window), [], f"at {window.width()}x{window.height()}")
                if check is not None:
                    check(window, screen)
        return window, screen

    def on_the_grid(self, window):
        found = grid_check.violations(window)
        self.assertGreater(len(grid_check.widgets(window)), 100, "the check saw the page's widgets")
        self.assertEqual(found, [], "on the 16 x 32 grid with no card")


@CAREER
class DeskOnTheGrid(Base):
    def make(self, window):
        return window.open_career(holland())

    def test_the_desk_fits_at_every_size(self):
        self.fitting(self.make)

    def test_the_desk_is_on_the_grid_with_no_card(self):
        window, desk = self.canonical(self.make)
        self.assertIsInstance(desk, DeskScreen)
        self.on_the_grid(window)

    def test_the_desk_is_not_on_either_pending_list(self):
        """It was listed (reflow_pending, grid_pending) until T211: the helpers now hold it to fitting and to the grid."""
        for lists in (reflow_pending.PENDING, grid_pending.PENDING):
            self.assertNotIn("DeskScreen", lists)
        self.assertTrue(DeskScreen.GRID)

    def test_its_panels_are_frames_a_rule_with_its_lowercase_label(self):
        window, desk = self.canonical(self.make)
        labels = [frame.label for frame in desk.findChildren(Frame)]
        self.assertEqual(labels, ["manager", "team", "next opponents", "managers", "holland"])
        for frame in desk.findChildren(Frame):
            self.assertEqual(frame.rule.text()[0], "-")
            self.assertEqual(len(frame.rule.text()), frame.rule.cols(), "dashes to the panel's edge")
        self.assertEqual(grid_check.cards(window), [])

    def test_a_key_is_its_caption_and_its_word_joined_in_cells_with_no_box(self):
        """[designed: T211] `F1help`: no key cap box, so the bar is rows of cells on the grid."""
        window, desk = self.canonical(self.make)
        self.assertEqual(desk.findChildren(QLabel, "kbd"), [], "no boxed key cap on a grid screen")
        items = desk.key_bar.findChildren(Clickable, "keyItem")
        caps = [item.findChildren(QLabel, "keyCap")[0].text() for item in items]
        self.assertEqual(caps[:3], ["F1", "F3", "F4"])
        words = [item.findChildren(QLabel, "keyLabel")[0].text() for item in items]
        self.assertEqual(words[:3], ["help", "load goal", "load summary"])
        self.assertEqual([label.text() for label in desk.enter_hint.findChildren(QLabel, "keyCap")], ["Enter"])

    def test_the_bar_keeps_its_rows_when_the_enter_hint_changes(self):
        """The page does not move: the bar is two rows whatever the highlighted option says Enter does ("New manager's name" is
        the longest), and the body above it keeps its height."""
        window, desk = self.canonical(self.make)
        before = (desk.key_bar.height(), desk.body.height())
        for index in range(len(desk.options)):
            desk.highlight(index)
            window.layout().activate()
            self.app.processEvents()
            self.assertEqual((desk.key_bar.height(), desk.body.height()), before, desk.enter_hint_text())
        self.assertEqual(before[0], cells.span_px(desk, 2), "two rows, the page's own (77 pixels at scale 1)")

    def test_the_messages_the_desk_says_fit_the_cells_they_have(self):
        """The hint and the note are paragraphs in cells: each message the desk says takes no more rows than it has."""
        window, desk = self.canonical(self.make)
        note_rows = desk.note.height() // cells.row_px(desk.note)
        for message in ("New manager: 14 characters maximum. Enter confirms; Esc cancels.",
                        "Type the manager's name first: 14 characters at most. Esc keeps the old one.",
                        "There is no match to play: the stage is complete.",
                        "The round cannot start: " + "x" * 40):
            desk.say(message)
            self.assertLessEqual(len(desk.note.lines()), note_rows, message)
        hint_rows = next(w for w in desk.findChildren(cells.CellPara) if w is not desk.note).height() // cells.row_px(desk)
        self.assertLessEqual(len(next(w for w in desk.findChildren(cells.CellPara) if w is not desk.note).lines()), hint_rows)


if __name__ == "__main__":
    unittest.main()
