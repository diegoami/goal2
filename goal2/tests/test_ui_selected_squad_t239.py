"""Exercise the larger squad controls with temporary desktop careers."""
import copy
import tempfile
import time
import unittest
from pathlib import Path

from goal2.tests import requires
requires.require(modules=("PySide6",))
from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

from goal2.desktop import data_setup
from goal2.game import eligibility
from goal2.game.best_twenty_jobs import close_model
from goal2.game.roles import role, tables
from goal2.game.session_save import load
from goal2.tests.test_assistant_pipe_t183c import model
from goal2.tests.test_selected_bench_matches_t238 import selected_state
from goal2.tests.test_ui_grid_t210 import canonical_page
from goal2.tests.ui_assertions import assert_fits, assert_on_grid
from goal2.ui import theme
from goal2.ui.cell_parts import GridStrip
from goal2.ui.match_day import for_window
from goal2.ui.s08_squad import open_squad
from goal2.ui.s19_bench import BenchScreen
from goal2.ui.s20_board import BoardScreen
from goal2.ui.window import Window


@requires.need(**requires.HALFTIME)
class SelectedSquadUI(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])
        cls.previous_font = cls.app.font()
        theme.install(cls.app)

    @classmethod
    def tearDownClass(cls):
        cls.app.setFont(cls.previous_font)

    def setUp(self):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.path = Path(folder.name)
        self.owner = model()
        self.win = Window(data_setup.paths(self.path / "game"))
        self.win.open_career(self.owner)
        self.win.show()
        self.addCleanup(self.close)
        self.app.processEvents()

    def close(self):
        close_model(self.owner)
        self.win.leaving = True
        self.win.close()
        self.win.deleteLater()
        self.app.processEvents()

    def key(self, key, widget=None):
        QTest.keyClick(self.win if widget is None else widget, key)
        self.app.processEvents()

    def click(self, widget, point=None):
        if point is None:
            point = widget.rect().center()
        QTest.mouseClick(widget, Qt.MouseButton.LeftButton, pos=point)
        self.app.processEvents()

    def until(self, condition, timeout=120):
        deadline = time.monotonic() + timeout
        while not condition():
            self.assertLess(time.monotonic(), deadline, 'screen did not reach its expected state')
            QTest.qWait(10)

    def choose(self, screen, size):
        self.click(screen.size_button)
        self.assertTrue(screen.size_menu.isVisible())
        self.click(screen.size_menu, screen.size_menu.actionGeometry(screen.size_actions[size]).center())
        self.assertEqual(self.owner.state.squad_capacity, size)

    def test_keyboard_and_click_resize_then_fill_last_slot_from_pool(self):
        screen = open_squad(self.win, self.owner)
        self.key(Qt.Key.Key_F6)
        self.assertTrue(screen.size_menu.isVisible())
        self.key(Qt.Key.Key_Down, screen.size_menu)
        self.key(Qt.Key.Key_Return, screen.size_menu)
        self.assertEqual(self.owner.state.squad_capacity, 22)
        self.assertEqual(self.owner.state.extra_squad, [None, None])
        self.assertEqual(len(screen.strip.shown_texts()), 22)
        self.choose(screen, 24)
        self.assertEqual(self.owner.state.extra_squad, [None] * 4)
        self.assertEqual(screen.findChildren(GridStrip), [screen.strip])
        self.assertEqual(len(screen.strip.shown_texts()), 24)
        self.click(screen.strip.rows[-1])
        self.assertIsNone(screen.current())
        self.assertFalse(screen.card.isVisible())
        self.assertEqual(screen.enter_text.text(), "Fill place")
        assert_fits(self, self.win)
        with canonical_page(self.win):
            assert_on_grid(self, self.win)
        self.key(Qt.Key.Key_Return)
        self.assertEqual(screen.side, "pool")
        self.assertEqual(screen.findChildren(GridStrip), [screen.strip])
        row = next(r for r in screen.rows()[:20]
                   if not eligibility.reasons(self.owner.state.players[r["id"]]))
        index = screen.rows().index(row)
        self.click(screen.strip.rows[index])
        if screen.side == "pool":
            self.key(Qt.Key.Key_Return)
        self.assertEqual(self.owner.state.extra_squad, [None, None, None, row["id"]])
        self.assertEqual(screen.current(), row["id"])
        self.assertTrue(screen.card.isVisible())
        self.assertNotIn(row["id"], [r["id"] for r in screen.rows("pool")])
        self.key(Qt.Key.Key_F6)
        self.key(Qt.Key.Key_Escape, screen.size_menu)
        self.assertEqual(self.owner.state.extra_squad, [None, None, None, row["id"]])
        self.choose(screen, 20)
        self.assertEqual(screen.findChildren(GridStrip), [screen.strip])
        self.assertIn(row["id"], [r["id"] for r in screen.rows("pool")])
        self.assertEqual(len(screen.strip.shown_texts()), 20)

    def test_a_fills_two_and_four_outfield_slots_on_the_visible_squad(self):
        screen = open_squad(self.win, self.owner)
        original = None
        initial = copy.deepcopy(self.owner.state)
        for size in (20, 22, 24):
            if size != 20:
                self.owner.state = copy.deepcopy(initial)
                screen.refresh()
                self.choose(screen, size)
            self.key(Qt.Key.Key_A)
            self.assertIsNotNone(screen._assistant_token)
            self.until(lambda: screen._assistant_token is None)
            count = size - 20
            self.assertEqual(len(screen.strip.shown_texts()), size)
            self.assertEqual(len(self.owner.state.extra_squad), count)
            self.assertTrue(all(w is not None for w in self.owner.state.extra_squad), screen.note.text())
            state = self.owner.state
            codes = tables(state)
            lines = {role(state, state.players[w][6], cache=codes)[1] for w in state.extra_squad}
            self.assertNotIn("goalkeeper", lines)
            self.assertEqual(len(lines), min(count, 3))
            if original is None:
                original = list(state.managed_squad)
            else:
                self.assertEqual(state.managed_squad, original)
            assert_fits(self, self.win)

    @requires.need(slow=True)
    def test_actual_quick_watch_bench_selects_last_extra_and_reloads(self):
        state, template, _, pairs = selected_state(4, True)
        self.owner.state, self.owner.template_bytes = state, template
        self.owner.mark_saved()
        day = for_window(self.win, self.owner)
        day.fixture = state.campaign.next_fixture
        day.watch = False
        pitch = day.kick_off(None)
        self.assertFalse(isinstance(pitch, str), pitch)
        self.until(lambda: isinstance(self.win.current(), BoardScreen) or pitch.controller.error, timeout=720)
        self.assertIsNone(pitch.controller.error)
        self.key(Qt.Key.Key_Escape)
        bench = self.win.current()
        self.assertIsInstance(bench, BenchScreen)
        self.assertEqual(len(bench.strip.shown_texts()), 24)
        self.assertEqual(len(bench.answer.live_records), 24)
        assert_fits(self, self.win)
        with canonical_page(self.win):
            assert_on_grid(self, self.win)
        tactics = day.open_team_tactics()
        self.assertEqual(len(tactics.strip.shown_texts()), 24)
        self.assertTrue(tactics.characteristics.isVisible())
        assert_fits(self, self.win)
        self.key(Qt.Key.Key_Escape)
        self.assertIs(self.win.current(), bench)
        last = bench.answer.words()[-1]
        off = next(a for a, b in pairs if b == last)
        self.click(bench.strip.rows[bench.answer.words().index(off)])
        if bench.answer.first is None:
            self.key(Qt.Key.Key_Return)
        self.click(bench.strip.rows[-1])
        self.assertEqual(bench.current(), last)
        if not bench.pending:
            self.key(Qt.Key.Key_Return)
        self.until(lambda: not bench.pending or pitch.controller.error, timeout=120)
        self.assertIsNone(pitch.controller.error)
        self.assertIn(last, bench.answer.eleven, bench.message)
        self.key(Qt.Key.Key_Escape)
        day.play(self.win.current())
        self.until(lambda: pitch.controller.finished or pitch.controller.error, timeout=720)
        self.assertIsNone(pitch.controller.error)
        save = self.path / "expanded.g2save"
        self.owner.save(save)
        restored, _ = load(save)
        self.assertEqual(restored, self.owner.state)
        self.assertIn(last, restored.starting_eleven)
        self.assertIn("selected_bench", restored.last_match)
