"""[designed: owner, 2026-11-08, #666, #667, #668; T210] The frame (a rule with its label) and the grid check.

The frame is a rule with its lowercase label; every concrete screen must use the cell grid with no cards.
[designed: T215] Checks run unconditionally on all platforms. Measurements use never-shown windows where a desktop
would clamp the requested size. The journey and career walk retain their screen coverage with no pending exemptions.
"""
from contextlib import contextmanager
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
from goal2.tests import ui_assertions  # noqa: E402
from goal2.ui import frame as frame_module, grid_check, theme  # noqa: E402
from goal2.ui.frame import Frame, FrameRule, rule_text  # noqa: E402
from goal2.ui.home import HomeScreen  # noqa: E402
from goal2.ui.window import Window  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]


@contextmanager
def canonical_page(window):
    """[designed: T215] Measure the grid on the canonical page without desktop work-area clamping.

    Fit tests separately exercise shown windows at their actual sizes. Preserve the journey's original window and
    screenshot; only its grid measurement uses this hidden 1440×1080 layout, as T210's contract requires.
    """
    from PySide6.QtWidgets import QLayout
    app = QApplication.instance()
    before, frame_before, visible = window.size(), window.centralWidget().size(), window.isVisible()

    def settle(size, frame_size=None):
        window.resize(size)
        window.layout().activate()
        window.centralWidget().resize(frame_size if frame_size is not None else size)
        window.centralWidget().fit()
        layouts = window.page.findChildren(QLayout)
        for _ in range(3):
            for layout in layouts:
                layout.invalidate()
                layout.activate()
        app.processEvents()

    window.hide()
    try:
        from PySide6.QtCore import QSize
        settle(QSize(*theme.PICTURE))
        if (window.page.width(), window.page.height()) != theme.PICTURE:
            raise AssertionError("grid measurement must use the canonical 1440×1080 page")
        yield
    finally:
        settle(before, frame_before)
        if visible:
            window.show()
        app.processEvents()


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
                    self.assertEqual(cells[0], {theme.FRAME_DARK,theme.FRAME}, "the rule joins the left edge")
                    for index in range(1, 5):
                        self.assertEqual(cells[index], {colour}, f"label cell {index}")
                    for index in range(5, 19):
                        self.assertEqual(cells[index], {theme.FRAME_DARK}, f"rule cell {index}")
                    self.assertEqual(cells[19],{theme.FRAME_DARK,theme.FRAME},"the rule joins the right edge")

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
        # [designed: owner playtest, #754] Connected panel edges are drawn without adding padding or a fill.
        body.hide()
        for panel in (frame, empty):
            image = QImage(panel.size(), QImage.Format.Format_RGB32)
            image.fill(QColor(theme.GROUND))
            panel.render(image, QPoint(), QRegion(), QWidget.RenderFlag.DrawChildren)
            for point in ((0, panel.height()-1),(panel.width()-1,panel.height()-1),
                          (0, panel.rule.height()+2),(panel.width()-1,panel.rule.height()+2)):
                self.assertEqual(image.pixelColor(*point).name(),theme.FRAME,"connected sides and bottom")
            interior={image.pixelColor(x,y).name() for x in range(2,panel.width()-2,3)
                      for y in range(panel.rule.height()+2,panel.height()-2)}
            self.assertEqual(interior,{theme.GROUND},"outline only: body stays unfilled")

    def test_fact_fields_have_dividers_without_filling_or_reducing_their_content(self):
        """[designed: owner playtest, #754] Facts share the original's visible column boundaries."""
        from goal2.ui.cell_parts import CellFacts
        def build(page):
            facts=CellFacts({'age':8,'caps':8},rows=2)
            facts.set({'age':'25','caps':'15'},theme.VALUE)
            facts.setParent(page)
        window,page=self.page(build)
        facts=page.findChild(CellFacts);facts.setGeometry(0,0,16*16,38*3);facts.layout().activate()
        image=QImage(facts.size(),QImage.Format.Format_RGB32);image.fill(QColor(theme.GROUND))
        facts.render(image,QPoint(),QRegion(),QWidget.RenderFlag.DrawChildren)
        for x in (0,8*16,16*16-1):
            self.assertEqual(image.pixelColor(x,81).name(),theme.FRAME)
        self.assertEqual(image.pixelColor(8*16+16,81).name(),theme.GROUND)
        self.assertEqual([v.text() for v in facts.values.values()],['25','15'])
        self.assertEqual(fixed_page.problems(window),[])

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

    def test_every_violation_fails_even_for_named_captures(self):
        window = self.home()
        with mock.patch.object(grid_check, "violations", return_value=[]):
            ui_assertions.assert_on_grid(self, window)
        with mock.patch.object(grid_check, "violations", return_value=["box off the cell"]):
            for capture in (None, "HomeScreen", "HomeScreen@1440x1080"):
                with self.subTest(capture=capture), self.assertRaises(AssertionError):
                    ui_assertions.assert_on_grid(self, window, capture=capture)

    def test_canonical_measurement_preserves_a_clamped_window_and_rejects_off_grid_content(self):
        window = self.home()
        window.resize(1440, 1061)   # the hosted Windows desktop's actual work area
        window.show()
        for _ in range(3):
            self.app.processEvents()
        before = window.size()
        with canonical_page(window):
            self.assertFalse(window.isVisible(), "the desktop must not clamp the measurement")
            self.assertEqual((window.page.width(), window.page.height()), theme.PICTURE)
            self.assertEqual(window.centralWidget().scale, 1)
            ui_assertions.assert_on_grid(self, window)
            bad = QWidget(window.current().body)
            bad.setObjectName("deliberatelyOffGrid")
            bad.setGeometry(7, 13, 31, 41)
            bad.show()
            with self.assertRaises(AssertionError):
                ui_assertions.assert_on_grid(self, window)
            bad.setParent(None)
            bad.deleteLater()
        self.assertTrue(window.isVisible())
        self.assertEqual(window.size(), before, "leave the visible journey at its original size")


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
            picture = original(window, *values)
            with canonical_page(window):
                found = grid_check.violations(window)
            if found:
                cls.violating.setdefault(name, found)
            return picture

        Window.grab = grab
        try:
            with tempfile.TemporaryDirectory(prefix="goal2-t210-journey-") as out:
                screenshots(Path(out) / "journey")
                ui_squad_screenshots.screenshots(Path(out) / "squad")
        finally:
            Window.grab = original
            app.setFont(font_before)

    def test_every_screen_the_journey_reaches_is_on_the_grid(self):
        self.assertGreater(len(set(self.seen)), 15, f"the journey reached {sorted(set(self.seen))}")
        self.assertEqual(self.violating, {}, "every captured screen must be on the grid without cards")


class PendingGrid(unittest.TestCase):
    def test_every_screen_class_of_the_window_declares_the_grid(self):
        """[designed: T215] Every concrete screen declares its cell layout without a pending escape."""
        import ast
        screens, on_the_grid = set(), set()
        bases = {"Screen", "BoxScreen"}   # screen/dialog bases: never shown on their own
        for path in sorted((ROOT / "goal2" / "ui").glob("*.py")):
            # [designed: T213] Parse declarations rather than assuming a class docstring is a single source line.
            for node in ast.parse(path.read_text(encoding="utf-8")).body:
                if not isinstance(node, ast.ClassDef):
                    continue
                if node.name.endswith("Screen") or node.name == "SavedGoalMenu":
                    screens.add(node.name)
                if any(isinstance(item, ast.Assign) and isinstance(item.value, ast.Constant) and item.value.value is True
                       and any(isinstance(target, ast.Name) and target.id == "GRID" for target in item.targets)
                       for item in node.body):
                    on_the_grid.add(node.name)
        self.assertEqual(sorted(screens - bases - on_the_grid), [], "every screen declares its cell layout")

    @requires.need(modules=("pygame",), **requires.HALFTIME)
    def test_every_screen_the_desk_reaches_is_on_the_grid_at_1440x1080(self):
        """[designed: T215] Retain the ten-screen career walk and require every screen to be on the grid."""
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
            with canonical_page(window):
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
        self.assertGreaterEqual(len(set(visited)), 10, f"visited {visited}")
        self.assertEqual(violating, set(), "every career screen must be on the grid without cards")

    def test_grid_pending_is_empty(self):
        """[designed: T215] The landing gate runs on every branch: no exemption modules remain."""
        ui_assertions.assert_no_exemptions(self)
        import ast
        source = (ROOT / "goal2/ui/screen.py").read_text(encoding="utf-8")
        for node in ast.walk(ast.parse(source)):
            if isinstance(node, (ast.If, ast.IfExp)):
                self.assertFalse(any(isinstance(item, ast.Attribute) and item.attr == "GRID"
                                     for item in ast.walk(node.test)), "GRID cannot select a legacy layout")



if __name__ == "__main__":
    unittest.main()
