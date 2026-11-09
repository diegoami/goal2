"""[designed: owner, 2026-11-08, #666, #667, #668; T210] The frame (a rule with its label) and the grid check.

The claim it protects: the frame and the check exist, and a screen not on the pending list (goal2/tests/grid_pending.py) is on
the grid with no card. [designed: owner, 2026-11-08; docs/design/ui-2026-11/fidelity-review.md §3] A frame is a rule with its
lowercase label sitting on it, the rule continuing as dashes to the panel's edge, brown or red; every edge of a panel is a whole
number of 16 x 32 cells; the card and its uppercase cyan heading go.

The geometry is measured on a window that is never shown (a desktop clamps a top-level window to its work area: a measured
Windows runner gave 1440x1061 for 1440x1080), at the 4:3 page's own size, where the scale is 1 and a cell is 16 pixels across
and a row 38. A listed screen is exempt in the ordinary tests; that it still violates is `PendingGrid`'s, at the canonical size,
on the platform the list was measured on (the list only shrinks).
"""
import sys
import unittest
from pathlib import Path
from unittest import mock

from goal2.tests import requires

requires.require(modules=("PySide6",))

from PySide6.QtCore import QPoint, Qt  # noqa: E402
from PySide6.QtGui import QColor, QImage, QRegion  # noqa: E402
from PySide6.QtWidgets import QApplication, QLabel, QMainWindow, QWidget  # noqa: E402

from goal2.desktop import data_setup, fixed_page  # noqa: E402
from goal2.tests import grid_pending  # noqa: E402
from goal2.tests.test_ui_cell_t209 import target_branch  # noqa: E402
from goal2.ui import frame as frame_module, grid_check, theme  # noqa: E402
from goal2.ui.frame import Frame, FrameRule, rule_text  # noqa: E402
from goal2.ui.home import HomeScreen  # noqa: E402
from goal2.ui.window import Window  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]


def cell_ink(image, cols):
    """For each of `cols` cells across `image`, the set of colour names drawn in it (the ground left out)."""
    width = image.width() / cols
    cells = []
    for column in range(cols):
        colours = set()
        for x in range(int(column * width), int((column + 1) * width)):
            for y in range(image.height()):
                name = QColor(image.pixel(x, y)).name()
                if name != theme.GROUND:
                    colours.add(name)
        cells.append(colours)
    return cells


class Base(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])
        cls.font_before = cls.app.font()
        theme.install(cls.app)

    @classmethod
    def tearDownClass(cls):
        cls.app.setFont(cls.font_before)

    def page(self, build, size=theme.PICTURE):
        """A window with the fixed page, never shown (so no desktop clamps it), whose page is `build()`'s widget laid out at
        `size` (1440x1080: scale 1). Returns (window, page)."""
        page = QWidget()
        page.setObjectName("page")
        build(page)
        window = QMainWindow()
        window.setFont(theme.text_font())
        host = fixed_page.FixedPage(page, theme.stylesheet(), window, logical=theme.PAGE, stretch=theme.STRETCH,
                                    text=theme.TEXT, aspect=(4, 3))
        window.setCentralWidget(host)
        window.resize(*size)   # the window's own pending layout would otherwise resize the page to a default window's
        window.layout().activate()
        host.resize(*size)
        host.fit()
        self.addCleanup(window.deleteLater)
        return window, page


class FrameDrawing(Base):
    def test_a_rule_is_a_dash_the_lowercase_label_and_dashes_to_the_edge(self):
        self.assertEqual(rule_text("rankings", 20), "-rankings-----------")
        self.assertEqual(rule_text("Name", 8), "-name---", "the grammar's label is lowercase")
        self.assertEqual(rule_text("characteristics", 5), "-characteristics-", "never narrower than the label and a dash")
        self.assertEqual(len(rule_text("a", 90)), 90)
        self.assertEqual(FrameRule("Name").label, "name", "lowercase as stored, not only as drawn")
        with self.assertRaises(ValueError):
            FrameRule("x", "blue")

    def test_the_rule_draws_each_glyph_at_the_cell_in_the_palettes_colours(self):
        for kind, colour in (("brown", theme.CARD_LABEL), ("red", theme.CARD_HEADING)):
            for size in (theme.PICTURE, (720, 540)):   # scale 1 and 0.5, never clamped: the window is not shown
                with self.subTest(kind=kind, size=size):
                    def build(page):
                        rule = FrameRule("Name", kind, page)
                        rule.setObjectName("under-test")
                    window, page = self.page(build, size)
                    scale = window.centralWidget().scale
                    rule = page.findChild(FrameRule)
                    cell = theme.CELL_W * scale
                    rule.setGeometry(round(2 * cell), 0, round(20 * cell), rule.height())
                    self.assertEqual(rule.cols(), 20, "the cells across the panel")
                    self.assertEqual(rule.text(), "-name" + "-" * 15, "`-name---…` to the panel's edge")
                    cells = cell_ink(rule.grab().toImage(), 20)
                    self.assertEqual([len(c) > 0 for c in cells], [True] * 20, "a rule with no gap: every cell has ink")
                    self.assertEqual(cells[0], {theme.FRAME_DARK}, "the leading dash")
                    for index in range(1, 5):
                        self.assertEqual(cells[index], {colour}, f"label cell {index}")
                    for index in range(5, 20):
                        self.assertEqual(cells[index], {theme.FRAME_DARK}, f"dash cell {index}")

    def test_a_frame_is_the_rule_and_a_body_with_no_border_and_no_padding(self):
        def build(page):
            frame = Frame("rankings", "brown", page)
            frame.add(QLabel("body", frame))
            Frame("empty", "red", page)
        window, page = self.page(build)
        frame, empty = page.findChildren(Frame)
        frame.setGeometry(16 * 2, 38 * 3, 16 * 30, 38 * 4)
        empty.setGeometry(16 * 40, 38 * 3, 16 * 30, 38 * 4)
        frame.layout().activate()
        empty.layout().activate()
        self.assertEqual(frame.rule.geometry().getRect(), (0, 0, 16 * 30, 38), "one row, the panel's width")
        body = frame.findChild(QLabel)
        self.assertEqual(body.geometry().getRect()[:2], (0, 38), "the body starts under the rule: no padding")
        self.assertEqual(frame.rule.cols(), 30)
        self.assertEqual(len(frame.rule.text()), 30, "dashes to the panel's edge")
        self.assertEqual(frame.styleSheet(), "")
        self.assertEqual(empty.rule.geometry().getRect()[:2], (0, 0), "a panel with nothing in it keeps its rule on top")
        # The rule is drawn, not a Qt border: a frame's picture is only its rule and its body.
        body.hide()
        for panel in (frame, empty):
            image = QImage(panel.size(), QImage.Format.Format_RGB32)
            image.fill(QColor(theme.GROUND))
            panel.render(image, QPoint(), QRegion(), QWidget.RenderFlag.DrawChildren)   # no fill of its own
            below = {QColor(image.pixel(x, y)).name()
                     for x in range(0, image.width(), 3) for y in range(round(38 * image.height() / panel.height()) + 1,
                                                                         image.height())}
            self.assertEqual(below, {theme.GROUND}, "nothing is drawn under the rule: no side, no foot, no fill")

    def test_a_panel_too_narrow_for_its_label_says_so(self):
        rule = FrameRule("characteristics", "red")
        self.assertGreaterEqual(rule.minimumSizeHint().width(), (len("characteristics") + 2) * theme.CELL_W)
        self.assertEqual(rule.minimumSizeHint().height(), theme.CELL_H)

    def test_a_frame_fits_the_page_it_is_on(self):
        def build(page):
            Frame("rankings", "brown", page).setGeometry(0, 0, 16 * 30, 38 * 4)
        window, page = self.page(build)
        self.assertEqual(fixed_page.problems(window), [], "the page's own check")


class GridCheck(Base):
    def synthetic(self):
        def build(page):
            def put(name, rect, cls=QWidget):
                widget = cls(page)
                widget.setObjectName(name)
                widget.setGeometry(*rect)
            put("onGrid", (16 * 4, 38 * 2, 16 * 10, 38 * 3))
            put("offGridX", (16 * 4 + 7, 38 * 2, 16 * 10, 38))
            put("offGridSize", (16 * 4, 38 * 8, 16 * 10 + 5, 38 * 3 - 9))
            put("offGridY", (16 * 30, 38 * 5 + 13, 16 * 4, 38))
            put("foot", (0, theme.PICTURE[1] - 38, 16 * 90, 38))   # the page's last row, on the grid counted from the bottom
            put("whole", (0, 0, 16 * 90, theme.PICTURE[1]))   # a screen fills the page: 1080 is 28 rows and the 4:3 slack
            put("qt_internal", (3, 5, 7, 11))
            put("empty", (1, 1, 0, 0))
            put("box", (16 * 20, 38 * 2, 16 * 10, 38 * 3))   # on the grid, and a card
            put("boxHeading", (16 * 20, 38 * 2, 16 * 10, 38), QLabel)
        return self.page(build)

    def names(self, lines):
        return sorted(line.split(" ")[0] for line in lines)

    def test_an_off_grid_widget_is_reported_and_an_on_grid_one_is_not(self):
        window, _ = self.synthetic()
        found = grid_check.off_grid(window)
        self.assertEqual(self.names(found), ["offGridSize", "offGridX", "offGridY"], found)
        self.assertTrue(next(line for line in found if line.startswith("offGridY")).endswith("in y"))
        self.assertIn("x", next(line for line in found if line.startswith("offGridX")).split("cell in ")[1])
        size = next(line for line in found if line.startswith("offGridSize")).split("cell in ")[1]
        self.assertIn("width", size)
        self.assertIn("height", size)

    def test_a_card_is_reported(self):
        window, _ = self.synthetic()
        self.assertEqual(self.names(grid_check.cards(window)), ["card", "card"])
        self.assertEqual(sorted(line.split()[1] for line in grid_check.cards(window)), ["box", "boxHeading"])
        self.assertEqual(len(grid_check.violations(window)), 5, "three off the grid and two cards")

    def test_a_hidden_widget_and_a_qt_internal_one_are_not_the_pages(self):
        window, page = self.synthetic()
        page.findChild(QWidget, "offGridX").hide()
        page.findChild(QWidget, "offGridY").hide()
        page.findChild(QWidget, "offGridSize").setGeometry(16 * 4, 38 * 8, 16 * 10, 38 * 3)
        self.assertEqual(grid_check.off_grid(window), [])
        child = QWidget(page.findChild(QWidget, "qt_internal"))
        child.setGeometry(1, 1, 3, 3)
        self.assertEqual(grid_check.off_grid(window), [], "what is inside a qt_ part is not the page's own")

    def test_a_cell_is_a_multiple_within_a_pixel_and_a_third_of_a_cell_is_not(self):
        self.assertTrue(grid_check.on_grid(16 * 7, 16.0))
        self.assertTrue(grid_check.on_grid(16 * 7 + 1, 16.0))
        self.assertFalse(grid_check.on_grid(16 * 7 + 5, 16.0))
        self.assertTrue(grid_check.on_grid(38 * 6, 38.4), "a row is 38 pixels in a layout and 38.4 in the grid")
        self.assertTrue(grid_check.on_grid(38 * 6 + 1, 38.4))
        self.assertFalse(grid_check.on_grid(38 * 6 + 13, 38.4))
        self.assertFalse(grid_check.on_grid(3, 16.0, size=True), "a 3 px line is not a size of the grid")
        self.assertTrue(grid_check.on_grid(0, 16.0), "a position of 0")

    def test_a_frame_on_the_grid_is_a_screen_on_the_grid(self):
        """The frame and the check agree: a panel made of frames at cell positions has no violation, and the same panel
        as a card does."""
        def build(page):
            Frame("rankings", "brown", page).setGeometry(16 * 2, 38 * 1, 16 * 30, 38 * 5)
            Frame("characteristics", "red", page).setGeometry(16 * 32, 38 * 1, 16 * 40, 38 * 5)
        window, page = self.page(build)
        for frame in page.findChildren(Frame):
            frame.layout().activate()   # [designed: T211] a window that is not shown lays nothing out by itself: the rule is a row once the frame is
        self.assertEqual(grid_check.violations(window), [])


class AssertOnGrid(Base):
    def home(self):
        import shutil
        import tempfile
        tmp = tempfile.mkdtemp(prefix="goal2-t210-")
        self.addCleanup(shutil.rmtree, tmp, True)
        window = Window(data_setup.Paths(Path(tmp) / "goal2"))
        window.resize(*theme.PICTURE)
        window.replace_home(HomeScreen(window))
        self.addCleanup(lambda: (window.close(), window.deleteLater(), self.app.processEvents()))
        return window

    def test_a_listed_screen_is_exempt_and_every_other_must_be_on_the_grid(self):
        """`assert_on_grid`: only a screen not listed in `PENDING` must be on the grid with no card. (That a listed one still
        violates is `PendingGrid`'s, at the canonical size.) A tag for another platform lists nothing here."""
        window = self.home()
        violating = mock.patch.object(grid_check, "violations", return_value=["box (1, 2, 3, 4) off the cell"])
        with mock.patch.object(grid_check, "violations", return_value=[]):
            grid_pending.assert_on_grid(self, window)   # on the grid and not listed
        with violating:
            with mock.patch.dict(grid_pending.PENDING, clear=True):
                with self.assertRaises(AssertionError, msg="not listed and violating: fails"):
                    grid_pending.assert_on_grid(self, window)
            with mock.patch.dict(grid_pending.PENDING, {"HomeScreen": "test"}):
                grid_pending.assert_on_grid(self, window)   # listed: exempt
            with mock.patch.dict(grid_pending.PENDING, {"HomeScreen": "test"}), \
                    mock.patch.dict(grid_pending.ONLY_ON, {"HomeScreen": "some-other-platform"}):
                with self.assertRaises(AssertionError, msg="listed for another platform: must be on the grid here"):
                    grid_pending.assert_on_grid(self, window)
            with mock.patch.dict(grid_pending.PENDING, {"HomeScreen@1440x1080": "test"}, clear=True):
                grid_pending.assert_on_grid(self, window)   # the capture name, with the size, is looked up first

    def test_the_home_screen_still_has_its_card(self):
        """It is the first thing a layout task removes from the list: today it is a bordered card."""
        window = self.home()
        for _ in range(3):
            self.app.processEvents()
        self.assertTrue(grid_check.cards(window) or grid_check.off_grid(window))


@requires.need(slow=True, modules=("pygame",), **requires.HALFTIME)   # plays a friendly under PyPy, as the journey does
class EveryScreen(unittest.TestCase):
    """The whole screenshot journey (goal2/ui/__main__.py `screenshots`) and the squad tool's pictures (S08 to S10) at
    1440x1080, taken once: which screens violate the grid there."""

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
        cls.seen, cls.violating = [], {}
        original = Window.grab

        def grab(window, *values):
            name = type(window.current()).__name__
            cls.seen.append(name)
            found = grid_check.violations(window)
            if found:
                cls.violating.setdefault(name, found)
            return original(window, *values)

        Window.grab = grab
        try:
            with tempfile.TemporaryDirectory(prefix="goal2-t210-journey-") as out:
                screenshots(Path(out) / "journey")
                ui_squad_screenshots.screenshots(Path(out) / "squad")
        finally:
            Window.grab = original
            app.setFont(font_before)

    @unittest.skipUnless(sys.platform.startswith("linux"), "the list was measured on Linux, Qt offscreen")
    def test_every_pending_screen_the_journey_reaches_still_violates(self):
        """[designed: owner, 2026-11-09, #667] A screen that is on the grid with no card now must leave `PENDING`: checked at
        1440x1080 (the journey's size), on the platform it was measured on. The ordinary tests exempt a listed screen."""
        self.assertGreater(len(set(self.seen)), 15, f"the journey reached {sorted(set(self.seen))}")
        reached = {key for key in grid_pending.PENDING if "@" not in key} & set(self.seen)
        self.assertGreater(len(reached), 10, "the journey reaches most of the pending screens")
        clean = sorted(name for name in reached if name not in self.violating)
        self.assertEqual(clean, [], "these screens are on the grid with no card now: remove them from grid_pending.PENDING")

    def test_every_screen_the_journey_reaches_is_listed_or_on_the_grid(self):
        """The other direction: a screen that violates and is not listed would fail its own tests; say it here, once."""
        unlisted = sorted(name for name in self.violating if grid_pending.listed_name(name) is None)
        self.assertEqual(unlisted, [], "violating and not on grid_pending.PENDING")


class PendingGrid(unittest.TestCase):
    def test_every_entry_is_a_ui_screen_with_a_reason(self):
        import re
        source = "\n".join(path.read_text(encoding="utf-8") for path in sorted((ROOT / "goal2" / "ui").glob("*.py")))
        for key, reason in grid_pending.PENDING.items():
            with self.subTest(key=key):
                name = key.split("@")[0]
                self.assertRegex(key, r"^[A-Za-z]+(@[A-Za-z0-9-]+)?$")
                self.assertIn(f"class {name}(", source, "a screen class of goal2/ui")
                self.assertTrue(reason.strip(), "the reason: what the screen needs")
        for key in grid_pending.ONLY_ON:
            self.assertIn(key, grid_pending.PENDING)

    def test_the_list_names_every_screen_class_of_the_window(self):
        """[designed: T210] Every screen starts pending, so a screen added later is on the grid from its first test.
        [designed: T211] A screen laid out on the grid declares `GRID = True` (goal2/ui/screen.py) and leaves the list: it is on
        no list because it needs none, and a screen that declares it is not listed."""
        import re
        screens, on_the_grid = set(), set()
        bases = {"BoxScreen"}   # the dialogs' base class: never shown on its own
        for path in sorted((ROOT / "goal2" / "ui").glob("*.py")):
            text = path.read_text(encoding="utf-8")
            screens |= set(re.findall(r"^class (\w+Screen|SavedGoalMenu)\(", text, re.M))
            on_the_grid |= set(re.findall(r"^class (\w+)\([\w.]+\):\n(?:    #[^\n]*\n|    \"\"\"[^\n]*\n)?    GRID = True", text, re.M))
        named = {key.split("@")[0] for key in grid_pending.PENDING}
        self.assertEqual(sorted(screens - bases - named - on_the_grid), [],
                         "screens that are on no list: list them, or lay them out on the grid")
        self.assertEqual(sorted(named & on_the_grid), [], "screens that are laid out on the grid are not pending")

    @requires.need(modules=("pygame",), **requires.HALFTIME)
    @unittest.skipUnless(sys.platform.startswith("linux"), "the list was measured on Linux, Qt offscreen")
    def test_every_pending_screen_the_desk_reaches_still_violates_at_1440x1080(self):
        """[designed: owner, 2026-11-09, #667] The listed screens one career opens, with no match played (the walk of
        `test_ui_cell_t209.PendingReflow`), at the canonical 1440x1080 on the platform they were measured on; the rest are
        `EveryScreen`'s (slow). A screen that is on the grid with no card now must be removed from `PENDING`: the ordinary
        tests exempt it, so this is where the list is held to shrink."""
        import shutil
        import tempfile
        from goal2.desktop.model import DesktopModel
        from goal2.ui.s08_squad import open_squad
        from goal2.ui.s10_team_tactics import open_team_tactics
        app = QApplication.instance() or QApplication([])
        font_before = app.font()
        theme.install(app)
        self.addCleanup(app.setFont, font_before)
        tmp = Path(tempfile.mkdtemp(prefix="goal2-t210-pending-"))
        self.addCleanup(shutil.rmtree, tmp, True)
        model = DesktopModel.open(requires.CACHE / "e010-r0008-halftime.sav", requires.CACHE / "GOAL.DAT", tmp / "career",
                                  country=20)
        window = Window(data_setup.paths(tmp / "goal2"))
        window.resize(*theme.PICTURE)
        window.show()
        self.addCleanup(lambda: (window.close(), window.deleteLater(), app.processEvents()))
        violating, visited = set(), []

        def look():
            for _ in range(3):
                app.processEvents()
            name = type(window.current()).__name__
            visited.append(name)
            if grid_check.violations(window):
                violating.add(name)

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
        for option in (2, 3):   # tournament, history
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
        reached = {key_ for key_ in grid_pending.PENDING if "@" not in key_} & set(visited)
        # [designed: T211] The list shrinks as screens are reflowed, so the walk's reach is its own screens (the ten it opens),
        # not how many of them are still listed.
        self.assertGreaterEqual(len(set(visited)), 10, f"visited {visited}")
        self.assertEqual(sorted(reached - violating), [], "these screens are on the grid with no card now: remove them")

    def test_grid_pending_is_empty(self):
        """THE GATE for merging the integration branch `ui/foundation-32` into main [designed: owner, 2026-11-09, #667]:
        it fails while `grid_pending.PENDING` is not empty. On the integration branch and on the task branches that target
        it, the list is the tolerated violation and this is skipped."""
        if target_branch() != "main":
            self.skipTest("ui/foundation-32 only: the list must be empty before this branch reaches main")
        self.assertEqual(grid_pending.PENDING, {}, "every screen must be on the grid, with frames, before this reaches main")


if __name__ == "__main__":
    unittest.main()
