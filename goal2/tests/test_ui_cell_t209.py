"""[designed: owner, 2026-11-08, #666, #667; T209] The cell, the one text size and the 4:3 page.

The claim it protects: every glyph on every screen is one size, on a 16 x 32 cell, and the page keeps 4:3 at any window
size. [designed: owner, 2026-11-08; docs/design/ui-2026-11/fidelity-review.md §3] The cell is 16 x 32 (twice the
original's 8 x 16), the page 90 x 28 cells (1440 x 896), text is `theme.TEXT` and nothing larger is drawn as type, and the
page is shown with a 1.2 vertical stretch, letterboxed and never re-flowed.

[confirmed: measured 2026-11-09, `QFont` on the vendored PxPlus IBM VGA 8x16, offscreen Qt] pixel size 32 gives advance 16
and line height 32; pixel size 38 with `QFont.setStretch(83)` gives advance 16 and height 39. A stretch is not a style sheet
property, so each widget carries it in code (goal2/desktop/fixed_page.py `set_stretch`); the screens are walked here to show
that none re-sets its own font without it.

Overflow is not asserted here: a screen that does not fit the 28 rows or 90 columns at 32 px is a finding of the task,
reported by `fixed_page.problems` (tools/ui_readability_screenshots.py), never hidden.
"""
import re
import unittest
from pathlib import Path

from goal2.tests import requires

requires.require(modules=("PySide6",))

from PySide6.QtGui import QColor, QFont, QFontMetrics, QFontMetricsF  # noqa: E402
from PySide6.QtWidgets import QApplication, QLabel, QScrollBar, QWidget  # noqa: E402

from goal2.desktop import data_setup, fixed_page  # noqa: E402
from goal2.ui import theme  # noqa: E402
from goal2.ui.home import HomeScreen  # noqa: E402
from goal2.ui.window import Window  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
SIZES = ((1440, 900), (1280, 720), (800, 600), (1920, 1080))


def advance_and_height(widget):
    """The widget's glyph advance and line height as the page draws them (fractional, so the ratio is not rounded twice)."""
    metrics = QFontMetricsF(widget.font())
    return metrics.horizontalAdvance("M" * 90) / 90, metrics.height()


class Cell(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])
        cls.font_before = cls.app.font()
        theme.install(cls.app)

    @classmethod
    def tearDownClass(cls):
        cls.app.setFont(cls.font_before)

    def window(self, width=1440, height=900):
        import tempfile
        tmp = tempfile.mkdtemp(prefix="goal2-t209-")
        self.addCleanup(__import__("shutil").rmtree, tmp, True)
        window = Window(data_setup.Paths(Path(tmp) / "goal2"))
        window.resize(width, height)
        window.show()
        window.replace_home(HomeScreen(window))
        self.addCleanup(lambda: (window.close(), window.deleteLater(), self.app.processEvents()))
        self.settle(window)
        return window

    def settle(self, window):
        for _ in range(3):
            self.app.processEvents()

    def body(self, window):
        """A label of the home screen: any text-bearing widget has the page's one font."""
        return next(w for w in window.current().findChildren(QLabel) if w.isVisible() and w.text())

    def test_the_font_is_one_cell_wide_and_32_high(self):
        self.assertEqual((theme.CELL_W, theme.CELL_H), (16, 32))
        self.assertEqual(theme.TEXT, 32)
        font = QFont(theme.FONT_FAMILY)
        font.setPixelSize(theme.TEXT)
        metrics = QFontMetrics(font)
        self.assertEqual((metrics.horizontalAdvance("M"), metrics.height()), (theme.CELL_W, theme.CELL_H),
                         "the vendored font at the one text size is a 16 x 32 cell")

    def test_the_body_font_at_a_page_of_1440_wide_is_16_by_32_stretched_1_2(self):
        window = self.window(1920, 1080)   # the 4:3 page at its own size: scale 1
        self.assertAlmostEqual(window.frame.scale, 1.0)
        advance, height = advance_and_height(self.body(window))
        self.assertAlmostEqual(advance, theme.CELL_W, delta=0.5)
        self.assertAlmostEqual(height, theme.CELL_H * theme.STRETCH, delta=1)
        self.assertEqual(QFontMetrics(self.body(window).font()).horizontalAdvance("M"), theme.CELL_W)

    def test_the_page_is_90_by_28_cells(self):
        self.assertEqual((theme.COLS, theme.ROWS), (90, 28))
        self.assertEqual(theme.PAGE, (1440, 896))
        window = self.window()
        self.assertEqual(window.frame.logical, (1440, 896))
        advance, height = advance_and_height(self.body(window))
        columns, rows = window.page.width() / advance, window.page.height() / height
        self.assertGreaterEqual(columns, 88, "columns across the page at 1440x900")
        self.assertGreaterEqual(rows, 27, "rows down the page at 1440x900")
        # It is the original's grid doubled, not a bigger one: a larger text would have fewer cells.
        self.assertLessEqual(columns, 92)
        self.assertLessEqual(rows, 29)

    def test_no_heading_size_is_defined_anywhere(self):
        names = ("HEADING" + "_SIZE", "BI" + "G", "HUG" + "E")
        pattern = re.compile(r"\b(" + "|".join(names) + r")\b")
        found = []
        for path in sorted((ROOT / "goal2").rglob("*.py")):
            if path == Path(__file__).resolve() or "engine" in path.relative_to(ROOT / "goal2").parts[:1]:
                continue
            for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
                if pattern.search(line):
                    found.append(f"{path.relative_to(ROOT)}:{number}: {line.strip()}")
        self.assertEqual(found, [])
        for sheet in (theme.stylesheet(), __import__("goal2.ui.start_look", fromlist=["x"]).stylesheet()):
            sizes = {int(s) for s in re.findall(r"font-size:\s*(\d+)px", sheet)}
            self.assertLessEqual(sizes, {theme.TEXT})

    def test_the_page_is_4_3_at_any_window_size_and_letterboxed_on_black(self):
        for width, height in SIZES:
            with self.subTest(size=(width, height)):
                window = self.window(width, height)
                page = window.page.geometry()
                self.assertLessEqual(abs(page.width() / page.height() - 4 / 3) / (4 / 3), 0.005, page.getRect())
                self.assertTrue(window.frame.rect().contains(page), "inside the window")
                self.assertLessEqual(abs(page.left() - (width - page.right() - 1)), 1, "centred across")
                self.assertLessEqual(abs(page.top() - (height - page.bottom() - 1)), 1, "centred down")
                self.assertEqual(window.frame.logical, (1440, 896), "never re-flowed: the same logical page")
                image = window.grab().toImage()
                if page.left() > 4:   # a pillar: black, not stretched content
                    self.assertEqual(QColor(image.pixel(2, height // 2)).name(), theme.GROUND)
                    self.assertEqual(QColor(image.pixel(width - 3, height // 2)).name(), theme.GROUND)

    def test_a_glyphs_advance_to_line_height_is_1_to_2_times_1_2_at_every_size(self):
        for width, height in SIZES + ((720, 540), (2110, 1213), (2880, 2160)):
            with self.subTest(size=(width, height)):
                window = self.window(width, height)
                advance, line = advance_and_height(self.body(window))
                self.assertAlmostEqual(line, advance * 2 * theme.STRETCH, delta=1)
                self.assertAlmostEqual(advance, theme.CELL_W * window.frame.scale, delta=0.5)

    def test_the_stretch_is_recomputed_when_the_window_resizes(self):
        window = self.window(1440, 900)
        before = self.body(window).font().stretch()
        self.assertEqual(before, theme.stretch_percent(1200 / 1440), "the 4:3 page at 1440x900 is 1200 wide")
        window.resize(1920, 1080)
        self.settle(window)
        after = self.body(window).font().stretch()
        self.assertEqual(after, theme.stretch_percent(1.0))
        self.assertNotEqual(before, after, "a widget keeps the stretch it was given unless it is set again")

    def test_a_style_sheet_scales_vertical_lengths_by_the_stretch_and_horizontal_ones_by_the_scale(self):
        sheet = "#a { padding: 10px 20px; min-height: 30px; min-width: 40px; border: 2px solid #fff; font-size: 32px; }"
        out = fixed_page.scale_sheet(sheet, 1.0, 1.2)
        self.assertIn("padding: 12px 20px", out)
        self.assertIn("min-height: 36px", out)
        self.assertIn("min-width: 40px", out)
        self.assertIn("border: 2px solid", out)
        self.assertIn("font-size: 38px", out)
        self.assertEqual(fixed_page.scale_sheet(sheet, 0.5, 1.0), sheet.replace("10px", "5px").replace("20px", "10px")
                         .replace("30px", "15px").replace("40px", "20px").replace("2px solid", "1px solid")
                         .replace("32px", "16px"), "a page without stretch scales every length alike, as before")


@requires.need(slow=True, modules=("pygame",), **requires.HALFTIME)   # plays a friendly under PyPy, as the journey does
class EveryScreen(unittest.TestCase):
    """The whole screenshot journey (goal2/ui/__main__.py `screenshots`, the one list of the window's screens) at 1440x900."""

    def test_every_widget_of_every_screen_has_the_one_text_size(self):
        import tempfile
        from goal2.ui.__main__ import screenshots

        app = QApplication.instance() or QApplication([])
        font_before = app.font()
        seen, wrong = [], []
        original = Window.grab

        def grab(window, *values):
            screen = window.current()
            seen.append(type(screen).__name__)
            scale = window.frame.scale
            want = round(theme.TEXT * theme.STRETCH * scale)
            stretch = theme.stretch_percent(scale)
            for widget in window.page.findChildren(QWidget):
                if not widget.isVisible() or isinstance(widget, QScrollBar):
                    continue
                font = widget.font()
                if font.pixelSize() != want or font.stretch() != stretch:
                    wrong.append(f"{seen[-1]} {widget.objectName() or type(widget).__name__}: "
                                 f"{font.pixelSize()} px stretch {font.stretch()}, wanted {want} px stretch {stretch}")
                if hasattr(widget, "type_at"):
                    drawn = widget.type_at(theme.TEXT)
                    if drawn.pixelSize() != round(theme.TEXT * widget.scale_y()) or drawn.stretch() != stretch:
                        wrong.append(f"{seen[-1]} {type(widget).__name__}.type_at: {drawn.pixelSize()} px, stretch "
                                     f"{drawn.stretch()}")
            return original(window, *values)

        Window.grab = grab
        try:
            with tempfile.TemporaryDirectory(prefix="goal2-t209-journey-") as out:
                screenshots(Path(out))
        finally:
            Window.grab = original
            app.setFont(font_before)
        self.assertGreater(len(set(seen)), 15, f"the journey reached {sorted(set(seen))}")
        self.assertEqual(wrong, [])


if __name__ == "__main__":
    unittest.main()
