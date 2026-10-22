"""[designed: T90; accepted vision #266] The management shell in the original style."""
import copy
from pathlib import Path
import unittest

from goal2.tests import requires

requires.require(modules=('PySide6',), **requires.HALFTIME)

from PySide6.QtCore import Qt  # noqa: E402
from PySide6.QtTest import QTest  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402
from goal2.desktop.model import DesktopModel  # noqa: E402
from goal2.desktop.window import ManagementWindow  # noqa: E402
from goal2.game.session_save import encode  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]


def luminance(hex_colour):
    def channel(v):
        v /= 255
        return v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4
    r, g, b = (int(hex_colour[i:i + 2], 16) for i in (1, 3, 5))
    return 0.2126 * channel(r) + 0.7152 * channel(g) + 0.0722 * channel(b)


def contrast(a, b):
    la, lb = sorted((luminance(a), luminance(b)), reverse=True)
    return (la + 0.05) / (lb + 0.05)


class Shell(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.model = DesktopModel.open(ROOT / '.cache/e010-r0008-halftime.sav', ROOT / '.cache/GOAL.DAT',
                                       ROOT / '.cache/never-written.g2save', country=8)
        self.window = ManagementWindow(self.model);self.window.show()
        self.window.activateWindow();QTest.qWaitForWindowActive(self.window)
        # A screen smaller than the 1440x900 window clamps it below NARROW_SHELL and collapses the
        # side bar (the 1024x768 default of a hosted Windows runner, #278).
        self.assertGreaterEqual(self.window.width(), ManagementWindow.NARROW_SHELL, 'the screen is too small for these tests')
        self.addCleanup(lambda: (self.window.close(), self.window.deleteLater(), self.app.processEvents()))

    def shortcut(self, key, modifier=Qt.KeyboardModifier.NoModifier):
        """[designed: #311] A window shortcut fires only in the active window, and another GUI test
        window on the Windows runner can take activation mid-test: activate this one first."""
        self.window.activateWindow();QTest.qWaitForWindowActive(self.window)
        QTest.keyClick(self.window, key, modifier);self.app.processEvents()

    def purity(self):
        w = self.window
        return (encode(self.model.state, self.model.template_bytes), w.draft(), w.page_stack.currentIndex())

    def test_palette_is_the_accepted_one_and_readable(self):
        from goal2.desktop.style import COLORS
        self.assertEqual((COLORS['background'], COLORS['cyan'], COLORS['yellow'], COLORS['red'], COLORS['green']),
                         ('#000000', '#55ffff', '#ffff55', '#ff5555', '#55ff55'))
        for fg in ('text', 'secondary', 'cyan', 'yellow', 'red', 'green', 'magenta', 'gold', 'focus'):
            self.assertGreaterEqual(contrast(COLORS[fg], COLORS['background']), 4.5, fg)
        self.assertGreaterEqual(contrast(COLORS['ink'], COLORS['accent']), 4.5, 'selection')

    def test_top_bar_names_country_career_and_next_fixture(self):
        w = self.window;summary = self.model.summary();fixture = self.model.state.campaign.next_fixture
        names = self.model.goaldat.country_names
        self.assertEqual(w.title.text(), names[8])
        self.assertEqual(w.career_line.text(), 'Manager 1 / ' + summary['campaign'])
        self.assertEqual(w.next_line.text(), f'Next: {names[fixture.side_a]} v {names[fixture.side_b]}')
        self.assertEqual(w.next_detail.text(), 'Friendly')

    def test_destinations_keep_order_shortcuts_and_purity(self):
        w = self.window
        self.assertEqual([b.accessibleName() for b in w.navigation], ['Country', 'Team', 'Pool', 'Fixtures & match', 'Save'])
        before = encode(self.model.state, self.model.template_bytes)
        for index in range(5):
            self.shortcut(Qt.Key.Key_1 + index, Qt.KeyboardModifier.ControlModifier)
            self.assertEqual(w.page_stack.currentIndex(), index);self.assertTrue(w.navigation[index].isChecked())
        self.assertEqual(encode(self.model.state, self.model.template_bytes), before)

    def test_bars_retract_and_restore_independently_keeping_everything(self):
        w = self.window
        w.navigate(1);w.tactics[0][1].toggle();w.table.setCurrentCell(4, 1);w.pages[1].verticalScrollBar().setValue(60)
        before = self.purity();scroll = w.pages[1].verticalScrollBar().value();row = w.table.currentRow()
        w.navigation[1].setFocus()
        w.hide_side.click();self.app.processEvents()
        self.assertFalse(w.side_bar.isVisible());self.assertTrue(w.show_side.isVisible());self.assertTrue(w.top_bar.isVisible())
        self.assertFalse(w.side_bar.isAncestorOf(w.focusWidget()), 'focus left inside a hidden bar')
        w.hide_top.click();self.app.processEvents()
        self.assertFalse(w.top_bar.isVisible());self.assertTrue(w.show_top.isVisible())
        w.show_side.click();self.app.processEvents()
        self.assertTrue(w.side_bar.isVisible());self.assertIs(w.focusWidget(), w.navigation[1], 'focus returns on restore')
        self.shortcut(Qt.Key.Key_F11)
        self.assertTrue(w.top_bar.isVisible() and w.side_bar.isVisible(), 'F11 restores both when one is hidden')
        self.shortcut(Qt.Key.Key_F11)
        self.assertFalse(w.top_bar.isVisible() or w.side_bar.isVisible())
        self.shortcut(Qt.Key.Key_F11)
        self.assertEqual(self.purity(), before)
        self.assertEqual((w.table.currentRow(), w.pages[1].verticalScrollBar().value()), (row, scroll))

    def test_a_small_window_collapses_the_side_bar_to_its_handle(self):
        w = self.window
        w.resize(900, 640);self.app.processEvents()
        self.assertFalse(w.side_bar.isVisible());self.assertTrue(w.show_side.isVisible())
        self.assertEqual(w.show_side.text(), '[Menu >]')
        # The handle takes no page width or height: it sits in the top bar, or in the handle row
        # beside [v Top] when the top bar is retracted too.
        self.assertTrue(w.top_bar.isAncestorOf(w.show_side))
        w.set_bars(top=False);self.app.processEvents()
        self.assertFalse(w.top_bar.isAncestorOf(w.show_side));self.assertTrue(w.show_side.isVisible() and w.show_top.isVisible())
        w.set_bars(top=True);self.app.processEvents();self.assertTrue(w.top_bar.isAncestorOf(w.show_side))
        w.show_side.click();self.app.processEvents();self.assertTrue(w.side_bar.isVisible(), 'the player can open it')
        w.resize(1440, 900);self.app.processEvents();self.assertTrue(w.side_bar.isVisible())

    def test_country_browse_is_a_country_page_control(self):
        w = self.window
        self.assertTrue(w.pages[0].isAncestorOf(w.country))
        self.assertFalse(w.top_bar.isAncestorOf(w.country))


if __name__ == '__main__':
    unittest.main()
