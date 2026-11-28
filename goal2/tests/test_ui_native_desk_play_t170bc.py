"""[designed: T170bc] The loaded Desk runs, publishes and owns the native round."""

from pathlib import Path
import shutil
from tempfile import TemporaryDirectory
import time
import unittest
from unittest.mock import patch

from goal2.desktop import data_setup
from goal2.tests import requires
from goal2.tests.season_oracle import component_of
from goal2.tests.test_native_desk_t170ba import fixture_owner, reference_raw
from goal2.tests.test_season_oracle_t170d import ARTIFACTS, CASES, GOAL_DAT, checkpoint

requires.require(modules=('PySide6',), **requires.HALFTIME)

from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

from goal2.ui import saves
from goal2.ui.native_desk import NativeDeskScreen
from goal2.ui.native_match_day import NativeMatchOpening
from goal2.ui.s02_start import StartScreen
from goal2.ui.s05_bulletin import BulletinScreen
from goal2.ui.s14_round import RoundScreen
from goal2.ui.window import Window


class Play(unittest.TestCase):
    def setUp(self):
        self.app = QApplication.instance() or QApplication([])
        folder = TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.target = data_setup.paths(Path(folder.name))
        self.target.data.mkdir()
        for name, _ in data_setup.WINDOW_MANIFEST:
            shutil.copyfile(requires.CACHE / name, self.target.data / name)
        self.window = Window(self.target)
        self.window.show()
        self.addCleanup(self.close_window)

    def close_window(self):
        self.window.leave()
        self.window.deleteLater()
        self.app.processEvents()

    def key(self, key):
        QTest.keyClick(self.window, key)
        self.app.processEvents()

    def until(self, condition, *, limit=120, step=None):
        end = time.monotonic() + limit
        while not condition():
            if time.monotonic() >= end:
                current = self.window.current()
                raise AssertionError(f'Timed out on {type(current).__name__}')
            if step is not None:
                step()
            QTest.qWait(2)

    def open_desk(self, raw):
        saves.write(fixture_owner(raw), self.target.saves, 'Native career')
        self.assertIsInstance(self.window.start_native(), StartScreen)
        self.key(Qt.Key.Key_Return)
        desk = self.window.current()
        self.assertIsInstance(desk, NativeDeskScreen)
        return desk

    def launch(self, desk, *, click=False):
        option = next(o for o in desk.options if o.enter == 'Play next game')
        if click:
            QTest.mouseClick(option, Qt.MouseButton.LeftButton)
            self.app.processEvents()
        else:
            desk.highlight(desk.options.index(option))
            self.key(Qt.Key.Key_Return)
        self.assertIsInstance(self.window.current(), NativeMatchOpening)
        self.assertIsNotNone(desk.native_round)
        self.assertIs(desk.native_round.native.owner, desk.model)
        return desk.native_round

    def acknowledge(self, desk, day, revision):
        self.until(lambda: day.phase == 'after_results')
        board = self.window.current()
        self.assertIsInstance(board, RoundScreen)
        self.assertEqual(desk.model.campaign.revision, revision)
        self.key(Qt.Key.Key_Return)
        if isinstance(self.window.current(), BulletinScreen):
            bulletin = self.window.current()
            for _ in bulletin.pages:
                self.assertEqual(desk.model.campaign.revision, revision)
                self.key(Qt.Key.Key_Return)
        self.assertEqual(self.window.stack, [desk])
        self.assertEqual(desk.model.campaign.revision, revision + 1)
        self.assertEqual(desk.model.campaign.state, day.native.boundary_state)
        self.assertEqual(desk.model.campaign.published[-1].output_hash, desk.model.desk_view().state_hash)
        self.assertTrue(desk.model.unsaved)
        self.until(lambda: day.native.disposed, limit=15)

    @requires.need(modules=('unicorn',), files=(ARTIFACTS[2]['name'],))
    def test_no_managed_match_plays_and_returns_then_guards_the_deferred_boundary(self):
        desk = self.open_desk(component_of(checkpoint(CASES[2]), GOAL_DAT))
        self.assertEqual(desk.play_kind.text(), 'No scheduled match')
        before = desk.model.desk_view()
        day = self.launch(desk, click=True)
        self.assertIsNone(desk.play_next_game())
        self.assertIs(desk.native_round, day)
        self.assertEqual(desk.model.desk_view(), before)
        self.acknowledge(desk, day, 0)
        self.assertEqual(desk.model.desk_view().status, 'complete')
        second = self.launch(desk)
        self.assertIsNot(second, day)
        self.acknowledge(desk, second, 1)
        self.assertEqual(desk.model.desk_view().status, 'deferred-rollover')
        terminal = desk.model.campaign.committed_snapshot()
        self.key(Qt.Key.Key_Return)
        self.assertIs(self.window.current(), desk)
        self.assertIn('Annual rollover', desk.note.text())
        self.assertEqual(desk.model.campaign.committed_snapshot(), terminal)

    def test_cancel_and_home_replacement_retire_workers_without_publication(self):
        desk = self.open_desk(reference_raw())
        source = desk.model.campaign.committed_snapshot()
        day = self.launch(desk)
        self.key(Qt.Key.Key_Escape)
        self.assertIs(self.window.current(), desk)
        self.until(lambda: day.native.disposed, limit=15)
        self.assertEqual(desk.model.campaign.committed_snapshot(), source)
        second = self.launch(desk)
        self.window.start_native()
        self.assertIsInstance(self.window.current(), StartScreen)
        self.until(lambda: second.native.disposed, limit=15)
        self.assertEqual(desk.model.campaign.committed_snapshot(), source)

    def test_dismissal_and_open_failure_leave_the_desk_and_campaign_intact(self):
        from goal2.core.views import Memory
        from goal2.engine.original_match.image import GAME_PTR, Image

        image = Image.from_bytes(reference_raw())
        memory = Memory(image)
        image.memory[image.far(GAME_PTR) + 0x47 + memory.game(1)] = 1
        dismissed = self.open_desk(image.header + image.memory)
        before = dismissed.model.campaign.committed_snapshot()
        with patch('goal2.ui.native_desk.NativeMatchDay', side_effect=AssertionError('dismissed round')):
            dismissed.play_next_game()
        self.assertIn('dismissed', dismissed.note.text())
        self.assertEqual(dismissed.model.campaign.committed_snapshot(), before)

        desk = self.open_desk(reference_raw())
        with patch('goal2.ui.native_desk.NativeMatchDay', side_effect=ValueError('controlled opening failure')):
            self.assertIsNone(desk.play_next_game())
        self.assertIs(self.window.current(), desk)
        self.assertIn('controlled opening failure', desk.note.text())
        self.assertEqual(desk.model.campaign.revision, 0)

    def test_close_under_help_retires_the_owned_round_without_publication(self):
        from goal2.ui.s22_help import HelpScreen

        desk = self.open_desk(reference_raw())
        source = desk.model.campaign.committed_snapshot()
        day = self.launch(desk)
        self.until(lambda: day.phase == 'before_results')
        self.key(Qt.Key.Key_F1)
        self.assertIsInstance(self.window.current(), HelpScreen)
        self.window.close()
        self.until(lambda: day.native.disposed, limit=15)
        self.assertFalse(self.window.isVisible())
        self.assertEqual(desk.model.campaign.committed_snapshot(), source)

    @requires.need(slow=True)
    def test_managed_saved_round_plays_through_review_and_returns_to_the_same_desk(self):
        from goal2.ui.native_half_time import NativeHalfTimeScreen
        from goal2.ui.native_review import NativeReviewScreen
        from goal2.ui.s15_match_menu import MenuScreen
        from goal2.ui.s16_choose import ChooseScreen

        desk = self.open_desk(reference_raw())
        day = self.launch(desk)
        self.until(lambda: day.phase == 'before_results')
        pid = day.native.pid
        self.key(Qt.Key.Key_Return)
        menu = self.window.current()
        self.assertIsInstance(menu, MenuScreen)
        menu.tournament()
        self.assertIs(self.window.current(), menu)
        menu.stats()
        self.assertIs(self.window.current(), menu)
        with self.assertRaisesRegex(ValueError, 'Player renaming is unavailable'):
            day.prematch.model.rename_player(1, 'Other')
        self.key(Qt.Key.Key_Return)
        self.assertIsInstance(self.window.current(), ChooseScreen)
        self.key(Qt.Key.Key_C)
        self.until(lambda: day.phase == 'playing')
        pitch = day.pitch
        driver = pitch.controller.driver
        self.assertEqual(day.native.pid, pid)
        self.key(Qt.Key.Key_R)
        pitch.timer.stop()
        self.assertTrue(driver.quick)

        def drive_stops():
            if not driver.pending or not driver.connection.replies.empty():
                pitch.tick()
            screen = self.window.current()
            if isinstance(screen, ChooseScreen):
                self.key(Qt.Key.Key_C)
            elif ((screen is pitch and pitch.stop_box.open)
                  or (isinstance(screen, (NativeHalfTimeScreen, NativeReviewScreen)) and screen.phase == 'ready')):
                self.key(Qt.Key.Key_Return)

        self.until(lambda: day.phase == 'complete', step=drive_stops)
        self.assertEqual(desk.model.campaign.revision, 0)
        self.key(Qt.Key.Key_Return)
        self.until(lambda: day.phase == 'after_results', step=drive_stops)
        self.assertEqual(day.native.pid, pid)
        self.acknowledge(desk, day, 0)
        self.assertEqual(desk.model.desk_view().status, 'complete')
        fixture = desk.model.desk_view().fixture
        self.assertEqual(desk.play_opponent.text(), fixture.opponent.name if fixture is not None else '')
