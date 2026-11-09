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
import os
import re
import subprocess
import sys
import unittest
from pathlib import Path

from goal2.tests import requires

requires.require(modules=("PySide6",))

from PySide6.QtGui import QColor, QFont, QFontMetrics, QFontMetricsF  # noqa: E402
from PySide6.QtWidgets import QApplication, QLabel, QScrollBar, QWidget  # noqa: E402

from goal2.desktop import data_setup, fixed_page  # noqa: E402
from goal2.ui import theme  # noqa: E402
from goal2.tests.reflow_pending import PENDING  # noqa: E402
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

    def test_the_default_size_is_the_4_3_page_or_the_screens_available_area(self):
        """[designed: owner, 2026-11-09, #667] 1440x1080 where it fits, else the available area (a desktop clamps a window)."""
        from PySide6.QtCore import QSize
        self.assertEqual(Window.default_size(QSize(2560, 1400)), (1440, 1080))
        self.assertEqual(Window.default_size(QSize(1920, 1040)), (1440, 1040), "a taskbar's worth less: the page letterboxed")
        self.assertEqual(Window.default_size(QSize(1280, 720)), (1280, 720))
        self.assertEqual(Window.default_size(QSize(0, 0)), (1440, 1080), "no screen to ask: the page's own size")
        import tempfile
        tmp = tempfile.mkdtemp(prefix="goal2-t209-")
        self.addCleanup(__import__("shutil").rmtree, tmp, True)
        window = Window(data_setup.Paths(Path(tmp) / "goal2"))
        self.addCleanup(window.deleteLater)
        screen = self.app.primaryScreen().availableGeometry()
        self.assertEqual((window.width(), window.height()), Window.default_size(screen), "it asks for the rule's size")

    def test_a_page_of_1440_by_1080_has_no_side_bars_and_scale_1(self):
        """[designed: owner, 2026-11-09, #667] Measured on a widget that is never shown, so no desktop can clamp its size."""
        import tempfile
        tmp = tempfile.mkdtemp(prefix="goal2-t209-")
        self.addCleanup(__import__("shutil").rmtree, tmp, True)
        window = Window(data_setup.Paths(Path(tmp) / "goal2"))
        self.addCleanup(window.deleteLater)
        window.frame.resize(*theme.PICTURE)
        window.frame.fit()
        self.assertEqual(window.page.geometry().getRect(), (0, 0, 1440, 1080), "no side bars, no letterbox")
        self.assertEqual(window.frame.scale, 1.0)

    def test_a_listed_screen_is_exempt_and_every_other_must_fit(self):
        """[designed: owner, 2026-11-09, #667] `assert_fits`: only a screen not listed in `PENDING` must fit. (That a listed
        one still overflows is `PendingReflow`'s, at the canonical size.) A tag for another platform lists nothing here."""
        from unittest import mock
        from goal2.tests import reflow_pending
        window = self.window()
        overflow = mock.patch.object(fixed_page, "problems", return_value=["screen 1x1 squeezed below 2x2"])
        reflow_pending.assert_fits(self, window)   # Home fits and is not listed
        with overflow:
            with self.assertRaises(AssertionError, msg="not listed and overflowing: fails"):
                reflow_pending.assert_fits(self, window)
            with mock.patch.dict(reflow_pending.PENDING, {"HomeScreen": "test"}):
                reflow_pending.assert_fits(self, window)   # listed: exempt
            with mock.patch.dict(reflow_pending.PENDING, {"HomeScreen": "test"}), \
                    mock.patch.dict(reflow_pending.ONLY_ON, {"HomeScreen": "some-other-platform"}):
                with self.assertRaises(AssertionError, msg="listed for another platform: must fit here"):
                    reflow_pending.assert_fits(self, window)

    def test_the_font_is_one_cell_wide_and_32_high(self):
        self.assertEqual((theme.CELL_W, theme.CELL_H), (16, 32))
        self.assertEqual(theme.TEXT, 32)
        font = QFont(theme.FONT_FAMILY)
        font.setPixelSize(theme.TEXT)
        metrics = QFontMetrics(font)
        self.assertEqual((metrics.horizontalAdvance("M"), metrics.height()), (theme.CELL_W, theme.CELL_H),
                         "the vendored font at the one text size is a 16 x 32 cell")

    def test_the_body_font_is_16_by_32_stretched_1_2_at_the_pages_scale(self):
        # A desktop may clamp a top-level window to its work area (a Windows runner gave 1440x1061 for 1440x1080), so the
        # expectation is the cell at the scale the page really has, never at a scale the OS was asked for.
        window = self.window(1920, 1080)
        scale = window.frame.scale
        self.assertGreater(scale, 0.9)
        advance, height = advance_and_height(self.body(window))
        self.assertAlmostEqual(advance, theme.CELL_W * scale, delta=1, msg="a glyph is one cell wide, to a pixel of rounding")
        size = self.body(window).font().pixelSize()
        self.assertAlmostEqual(size, theme.CELL_H * theme.STRETCH * scale, delta=1, msg="the pixel size is 1.2 taller")
        self.assertGreaterEqual(height, size - 1)   # a platform's font engine may add a hinted pixel to the line (Windows: 38 -> 39)
        self.assertLessEqual(height, size + 1)
        self.assertLessEqual(abs(QFontMetrics(self.body(window).font()).horizontalAdvance("M") - theme.CELL_W * scale), 1)

    def test_the_page_is_90_by_28_cells(self):
        self.assertEqual((theme.COLS, theme.ROWS), (90, 28))
        self.assertEqual(theme.PAGE, (1440, 896))
        window = self.window()
        self.assertEqual(window.frame.logical, (1440, 896))
        advance, height = advance_and_height(self.body(window))
        columns, rows = window.page.width() / advance, window.page.height() / height
        self.assertGreaterEqual(columns, 88, "columns across the page at 1440x900")
        self.assertGreaterEqual(rows, 27, "rows down the page at 1440x900")
        # It is the original's grid doubled, not a bigger one: a larger text would have more cells (24 px gave 120 columns
        # and 37 rows). A glyph's advance is only right to a pixel (Windows hints it to a whole number: 13 for 13.3), so
        # the bound is the grid at an advance and a height one pixel short.
        scale = window.frame.scale
        self.assertLessEqual(columns, window.page.width() / (theme.CELL_W * scale - 1))
        self.assertLessEqual(rows, window.page.height() / (theme.CELL_H * theme.STRETCH * scale - 1))
        self.assertLess(columns, 100)
        self.assertLess(rows, 31)

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
                width, height = window.width(), window.height()   # what the desktop gave: it may clamp to its work area
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
        window = self.window(1200, 900)
        before = self.body(window).font().stretch()
        self.assertEqual(before, theme.stretch_percent(window.frame.scale))
        self.assertAlmostEqual(window.frame.scale, 1200 / 1440)
        window.resize(720, 540)   # a size no desktop clamps: scale 0.5
        self.settle(window)
        after = self.body(window).font().stretch()
        self.assertEqual(after, theme.stretch_percent(window.frame.scale))
        self.assertAlmostEqual(window.frame.scale, 0.5)
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
    """The whole screenshot journey (goal2/ui/__main__.py `screenshots`, the one list of the window's screens) and the squad
    tool's pictures (S08 to S10), at 1440x1080, taken once for the tests below."""

    @classmethod
    def setUpClass(cls):
        import tempfile
        from goal2.ui.__main__ import screenshots
        sys.path.insert(0, str(ROOT / "tools"))
        try:
            import ui_squad_screenshots
        finally:
            sys.path.remove(str(ROOT / "tools"))
        app = QApplication.instance() or QApplication([])
        font_before = app.font()
        cls.seen, cls.wrong, cls.overflowing = [], [], set()
        original = Window.grab

        def grab(window, *values):
            screen = window.current()
            name = type(screen).__name__
            cls.seen.append(name)
            if fixed_page.problems(window):
                cls.overflowing.add(name)
            scale = window.frame.scale
            want = round(theme.TEXT * theme.STRETCH * scale)
            stretch = theme.stretch_percent(scale)
            for widget in window.page.findChildren(QWidget):
                if not widget.isVisible() or isinstance(widget, QScrollBar):
                    continue
                font = widget.font()
                if font.pixelSize() != want or font.stretch() != stretch:
                    cls.wrong.append(f"{name} {widget.objectName() or type(widget).__name__}: "
                                     f"{font.pixelSize()} px stretch {font.stretch()}, wanted {want} px stretch {stretch}")
                if hasattr(widget, "type_at"):
                    drawn = widget.type_at(theme.TEXT)
                    if drawn.pixelSize() != round(theme.TEXT * widget.scale_y()) or drawn.stretch() != stretch:
                        cls.wrong.append(f"{name} {type(widget).__name__}.type_at: {drawn.pixelSize()} px, stretch "
                                         f"{drawn.stretch()}")
            return original(window, *values)

        Window.grab = grab
        try:
            with tempfile.TemporaryDirectory(prefix="goal2-t209-journey-") as out:
                screenshots(Path(out) / "journey")
                ui_squad_screenshots.screenshots(Path(out) / "squad")
        finally:
            Window.grab = original
            app.setFont(font_before)

    def test_every_widget_of_every_screen_has_the_one_text_size(self):
        self.assertGreater(len(set(self.seen)), 15, f"the journey reached {sorted(set(self.seen))}")
        self.assertEqual(self.wrong, [])

    @unittest.skipUnless(sys.platform.startswith("linux"), "the list was measured on Linux, Qt offscreen")
    def test_every_pending_screen_the_journey_reaches_still_overflows(self):
        """[designed: owner, 2026-11-09, #667] A screen that now fits must leave `PENDING`: checked at 1440x1080 (the journey's
        size), on the platform it was measured on. The ordinary tests exempt a listed screen."""
        reached = {key for key in PENDING if "@" not in key} & set(self.seen)
        self.assertGreater(len(reached), 10, "the journey reaches most of the pending screens")
        fits = sorted(name for name in reached if name not in self.overflowing)
        self.assertEqual(fits, [], "these screens fit now: remove them from reflow_pending.PENDING")


def target_branch():
    """The branch this run is for: the pull request's base in CI, else the pushed branch, else the checked-out one."""
    base = os.environ.get("GITHUB_BASE_REF") or os.environ.get("GITHUB_REF_NAME")
    if base:
        return base
    done = subprocess.run(["git", "branch", "--show-current"], cwd=ROOT, capture_output=True, text=True)
    return done.stdout.strip()


class PendingReflow(unittest.TestCase):
    def test_every_entry_is_a_ui_screen_with_a_reason(self):
        source = "\n".join(path.read_text(encoding="utf-8") for path in sorted((ROOT / "goal2" / "ui").glob("*.py")))
        for key, reason in PENDING.items():
            with self.subTest(key=key):
                name = key.split("@")[0]
                self.assertRegex(key, r"^[A-Za-z]+(@[A-Za-z0-9-]+)?$")
                self.assertIn(f"class {name}(", source, "a screen class of goal2/ui")
                self.assertTrue(reason.strip(), "the reason: what the screen needs")

    @requires.need(modules=("pygame",), **requires.HALFTIME)
    @unittest.skipUnless(sys.platform.startswith("linux"), "the list was measured on Linux, Qt offscreen")
    def test_every_pending_screen_the_desk_reaches_still_overflows_at_1440x1080(self):
        """[designed: owner, 2026-11-09, #667] The listed screens one career opens, with no match played, at the canonical
        1440x1080 on the platform they were measured on; the rest are `EveryScreen`'s (slow). A screen that now fits must be
        removed from `PENDING`: the ordinary tests exempt it, so this is where the list is held to shrink."""
        import tempfile
        from PySide6.QtCore import Qt
        from goal2.desktop.model import DesktopModel
        from goal2.ui.s08_squad import open_squad
        from goal2.ui.s10_team_tactics import open_team_tactics
        app = QApplication.instance() or QApplication([])
        font_before = app.font()
        theme.install(app)
        self.addCleanup(app.setFont, font_before)
        tmp = Path(tempfile.mkdtemp(prefix="goal2-t209-pending-"))
        self.addCleanup(__import__("shutil").rmtree, tmp, True)
        model = DesktopModel.open(requires.CACHE / "e010-r0008-halftime.sav", requires.CACHE / "GOAL.DAT", tmp / "career",
                                  country=20)
        window = Window(data_setup.paths(tmp / "goal2"))
        window.resize(*theme.PICTURE)
        window.show()
        self.addCleanup(lambda: (window.close(), window.deleteLater(), app.processEvents()))
        overflowing, visited = set(), []

        def look():
            for _ in range(3):
                app.processEvents()
            name = type(window.current()).__name__
            visited.append(name)
            if fixed_page.problems(window):
                overflowing.add(name)

        def key(k):
            window.current().handle_key(k)
            app.processEvents()

        desk = window.open_career(model)
        look()
        desk.reimport()
        look()
        window.pop()
        key(Qt.Key.Key_Return)   # the cursor starts on team info
        info = window.current()
        info.settle()
        look()
        info.players()
        look()
        window.pop()
        info.index = (info.index + 1) % len(info.order)   # another country: its tactics, not the manager's own
        info.tactics()
        look()
        window.pop()
        window.pop()
        for option in (2, 3):   # tournament, history (the fixtures' rows depend on the career: the journey's)
            desk = window.current()
            desk.highlight(option)
            key(Qt.Key.Key_Return)
            look()
            key(Qt.Key.Key_Escape)
        open_squad(window, model)
        look()
        key(Qt.Key.Key_T)
        look()
        key(Qt.Key.Key_Escape)
        open_team_tactics(window, model)
        key(Qt.Key.Key_Return)
        look()
        reached = {key_ for key_ in PENDING if "@" not in key_} & set(visited)
        self.assertGreaterEqual(len(reached), 10, f"visited {visited}")
        self.assertEqual(sorted(reached - overflowing), [], "these screens fit at 1440x1080 now: remove them from PENDING")

    def test_the_help_viewer_still_falls_short_at_720x450(self):
        """[designed: owner, 2026-11-09, #667] `HelpScreen@720x450` is listed because the viewer is under 70 % of the page there."""
        if sys.platform.startswith("win"):
            self.skipTest("measured on Linux, Qt offscreen")
        import tempfile
        tmp = Path(tempfile.mkdtemp(prefix="goal2-t209-help-"))
        self.addCleanup(__import__("shutil").rmtree, tmp, True)
        target = data_setup.Paths(tmp / "goal2")
        target.data.mkdir(parents=True)
        target.help.write_bytes(b"stand-in help\r\n" * 80 + b"\x1a")
        app = QApplication.instance() or QApplication([])
        window = Window(target)
        window.resize(720, 450)
        window.show()
        self.addCleanup(lambda: (window.close(), window.deleteLater(), app.processEvents()))
        window.replace_home(HomeScreen(window))
        window.open_help()
        for _ in range(3):
            app.processEvents()
        self.assertLess(window.current().viewer.height(), 0.7 * window.page.height(),
                        "it fills the page now: remove HelpScreen@720x450 from PENDING")

    def test_pending_reflow_is_empty(self):
        """THE GATE for merging the integration branch `ui/foundation-32` into main [designed: owner, 2026-11-09, #667]:
        it fails while `reflow_pending.PENDING` is not empty. On the integration branch and on the task branches that
        target it, the list is the tolerated overflow (docs/tasks/T209.md, Done-when 6) and this is skipped."""
        if target_branch() != "main":
            self.skipTest("ui/foundation-32 only: the list must be empty before this branch reaches main")
        self.assertEqual(PENDING, {}, "every screen must be reflowed to the 90 x 28 grid before this reaches main")


if __name__ == "__main__":
    unittest.main()
