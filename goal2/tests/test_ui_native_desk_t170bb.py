"""[designed: T170bb] The explicit native save opens the shared manager's Desk."""

from pathlib import Path
import shutil
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from goal2.core.views import Memory
from goal2.desktop import data_setup
from goal2.desktop.native_save_owner import NativeSaveOwner
from goal2.engine.original_match.image import GAME_PTR, Image
from goal2.game import engine_tables
from goal2.game.season import SeasonSession
from goal2.game.season_publication import SeasonCampaign, SeasonPublication
from goal2.tests import requires
from goal2.tests.test_native_desk_t170ba import fixture_owner, reference_raw
from goal2.tests.test_season_publication_t170c2 import step
from goal2.ui import saves

requires.require(modules=('PySide6',), **requires.HALFTIME)

from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

from goal2.ui.native_desk import NativeDeskScreen
from goal2.ui.s02_start import StartScreen
from goal2.ui.s03_new_game import NewGameScreen
from goal2.ui.s06_desk import ReimportScreen
from goal2.ui.s21_save import QuestionScreen, SaveScreen
from goal2.ui.s22_help import HelpScreen
from goal2.ui.window import Window


class Journey(unittest.TestCase):
    def setUp(self):
        self.app = QApplication.instance() or QApplication([])
        folder = TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.target = data_setup.paths(Path(folder.name))
        self.target.data.mkdir()
        for name, _ in data_setup.WINDOW_MANIFEST:
            shutil.copyfile(requires.CACHE / name, self.target.data / name)
        self.owner = fixture_owner(reference_raw())
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

    def click(self, widget):
        QTest.mouseClick(widget, Qt.MouseButton.LeftButton)
        self.app.processEvents()

    def test_continue_lands_on_shared_desk_with_original_fields_and_real_save(self):
        path = saves.write(self.owner, self.target.saves, 'Sweden next')
        start = self.window.start()
        self.assertEqual(start.entries, [])
        self.assertIsInstance(self.window.start_native(), StartScreen)
        with patch('goal2.game.engine_process.EngineProcess.season_open',
                   side_effect=AssertionError('the Desk must not start a worker')):
            self.key(Qt.Key.Key_Return)
            desk = self.window.current()
            self.assertIsInstance(desk, NativeDeskScreen)
            self.assertEqual(len(self.window.stack), 1)
            self.assertIs(self.window.career, desk.model)
            self.assertIsNot(desk.model, self.owner)
            view = desk.model.desk_view()
            self.assertEqual(view, self.owner.desk_view())
            self.assertIn('2028', desk.banner.text())
            self.assertIn('European Championship', desk.banner.text())
            self.assertIn(view.stage_word, desk.banner.text())
            self.assertEqual(desk.manager['name'].text(), view.manager.name.strip())
            self.assertEqual(desk.manager['rating'].text(), view.rating)
            self.assertEqual(desk.team_name.text(), 'Denmark')
            self.assertEqual(desk.team_ranks['world'].text(), str(view.team.world_rank))
            self.assertEqual(desk.team_ranks['continent'].text(), str(view.team.continent_rank))
            self.assertEqual(desk.play_opponent.text(), 'Sweden')
            self.assertEqual(desk.play_kind.text(), 'friendly home')
            self.assertEqual(desk.opponent_ranks['world'].text(), str(view.fixture.opponent.world_rank))
            self.assertEqual(desk.opponent_ranks['continent'].text(), str(view.fixture.opponent.continent_rank))
            self.assertEqual([tuple(row) for row in desk.strip.shown_texts()],
                             [(r.code, r.name) for r in view.squad])
            self.assertTrue(desk.strip.gap.isVisible())
            self.key(Qt.Key.Key_F1)
            self.assertIsInstance(self.window.current(), HelpScreen)
            self.key(Qt.Key.Key_Escape)
            self.assertIs(self.window.current(), desk)
            self.key(Qt.Key.Key_F7)
            self.assertIsInstance(self.window.current(), SaveScreen)
            self.assertEqual(self.window.current().field.text, 'Sweden next')
            self.key(Qt.Key.Key_Return)
            self.assertIs(self.window.current(), desk)
            self.assertEqual(desk.model.save_path, path)
            self.assertEqual(saves.load(path, self.target.goal_dat, native=True).desk_view(), view)

    def test_unbound_actions_refuse_from_keyboard_and_click_and_existing_actions_still_open(self):
        saves.write(self.owner, self.target.saves, 'Sweden next')
        start = self.window.start_native()
        self.key(Qt.Key.Key_Y)
        desk = self.window.current()
        self.assertIsInstance(desk, NativeDeskScreen)
        self.assertIsNot(start, desk)
        original = desk.model.campaign.committed_snapshot()
        with patch('goal2.ui.match_day.play_next_game', side_effect=AssertionError('legacy round')):
            for key in (Qt.Key.Key_Return, Qt.Key.Key_T, Qt.Key.Key_F3, Qt.Key.Key_F4):
                self.key(key)
                self.assertIs(self.window.current(), desk)
                self.assertIn('unavailable', desk.note.text())
            for option in desk.options[:4] + [desk.options[6]]:
                self.click(option)
                self.assertIs(self.window.current(), desk)
                self.assertIn('unavailable', desk.note.text())
        self.assertEqual(desk.model.campaign.committed_snapshot(), original)
        self.click(desk.options[-1])
        self.assertIsInstance(self.window.current(), ReimportScreen)
        self.key(Qt.Key.Key_Escape)
        self.assertIs(self.window.current(), desk)
        self.click(desk.options[-2])
        self.assertIsInstance(self.window.current(), NewGameScreen)
        self.key(Qt.Key.Key_Escape)
        self.assertIs(self.window.current(), desk)
        self.key(Qt.Key.Key_F10)
        self.assertIsInstance(self.window.current(), QuestionScreen)
        self.key(Qt.Key.Key_N)
        self.assertIs(self.window.current(), desk)

    def test_select_squad_browses_saved_native_cards_and_pool_without_starting_a_worker(self):
        from goal2.core.views import player_card, pool, squad
        from goal2.ui.s08_squad import SquadScreen

        saves.write(self.owner, self.target.saves, 'Browse native players')
        self.window.start_native()
        self.key(Qt.Key.Key_Return)
        desk = self.window.current()
        committed = desk.model.campaign.committed_snapshot()
        image = Image.from_state(committed[0], engine_tables.load())
        roster = squad(Memory(image), desk.model.desk_view().team.country)
        native_pool = [row for row in pool(image)['rows'] if row['player']]
        with patch('goal2.game.engine_process.EngineProcess.__init__',
                   side_effect=AssertionError('browsing must not create a worker')):
            self.key(Qt.Key.Key_Space)
            page = self.window.current()
            self.assertIsInstance(page, SquadScreen)
            self.assertEqual([row['id'] for row in page.rows()], [row['player'] for row in roster])
            self.assertEqual(page.current(), roster[0]['player'])
            card = player_card(image, page.current())
            self.assertEqual(page.card.card['full_name'], card['name'])
            self.assertEqual(page.card.card['role'], card['code'])
            self.assertEqual(page.card.card['skills'], card['skills'])
            self.key(Qt.Key.Key_Down)
            self.assertEqual(page.current(), roster[1]['player'])
            self.key(Qt.Key.Key_Right)
            self.assertEqual([row['id'] for row in page.rows()], [row['player'] for row in native_pool])
            self.assertEqual(page.card.card['full_name'], native_pool[0]['name'])
            self.click(page.strip.rows[1])
            self.assertEqual(page.current(), native_pool[1]['player'])
            self.key(Qt.Key.Key_P)
            self.assertEqual([row['id'] for row in page.rows()],
                             [row['player'] for row in native_pool if row['position'] == 0])
            self.key(Qt.Key.Key_Slash)
            QTest.keyClicks(self.window, 'zzzxzzzx')
            self.key(Qt.Key.Key_Return)
            self.assertEqual(page.rows(), [])
            self.assertFalse(page.card.isVisible())
            self.assertIsNone(page.current())
            self.key(Qt.Key.Key_Left)
            self.assertEqual(page.current(), roster[1]['player'])
            for key in (Qt.Key.Key_Return, Qt.Key.Key_A, Qt.Key.Key_Insert, Qt.Key.Key_R,
                        Qt.Key.Key_C, Qt.Key.Key_T, Qt.Key.Key_F2):
                self.key(key)
                self.assertIs(self.window.current(), page)
                self.assertIn('Edits are unavailable', page.note.text())
                self.assertIsNone(page.picked)
            self.key(Qt.Key.Key_Escape)
            self.assertIs(self.window.current(), desk)
            self.click(next(option for option in desk.options if option.enter == 'Select squad'))
            self.assertIsInstance(self.window.current(), SquadScreen)
            self.key(Qt.Key.Key_Escape)
            self.assertIs(self.window.current(), desk)
        self.assertEqual(desk.model.campaign.committed_snapshot(), committed)

    def test_committed_refresh_clears_previous_opponent_and_quit_can_save_the_new_revision(self):
        saves.write(self.owner, self.target.saves, 'Sweden next')
        desk = self.window.open_career(self.owner)
        self.assertEqual(desk.play_opponent.text(), 'Sweden')

        image = Image.from_bytes(reference_raw())
        memory = Memory(image)
        image.memory[image.far(GAME_PTR) + 0x47 + memory.game(1)] = 1
        output = image.state(engine_tables.load())
        session = SeasonSession(self.owner.campaign.state)
        with patch('goal2.game.season.route.play_round', return_value=step('complete', output)):
            observation = session.advance()
        publication = SeasonPublication(self.owner.campaign)
        token = publication.begin(observation).token
        prepared = publication.prepare_completion(token, session)
        prepared.run()
        desk.shown()
        self.assertEqual(desk.play_opponent.text(), 'Sweden')
        publication.publish_prepared(token, prepared)
        desk.shown()
        self.assertEqual(desk.play_opponent.text(), '')
        self.assertEqual(desk.opponent_name.text(), '—')
        self.assertEqual(desk.opponent_ranks['continent'].text(), '—')
        self.assertEqual(desk.opponent_ranks['continent'].caption.text(), 'continent')
        self.assertEqual(desk.play_kind.text(), 'No scheduled match')
        self.assertIn('dismissed', desk.note.text())
        self.assertTrue(self.owner.unsaved)

        self.key(Qt.Key.Key_F10)
        self.key(Qt.Key.Key_Y)
        self.assertIsInstance(self.window.current(), QuestionScreen)
        self.key(Qt.Key.Key_Y)
        self.assertIsInstance(self.window.current(), SaveScreen)
        self.key(Qt.Key.Key_Return)
        self.assertFalse(self.window.isVisible())
        restored = saves.load(self.owner.save_path, self.target.goal_dat, native=True)
        self.assertEqual(restored.desk_view(), self.owner.desk_view())
        self.assertEqual(restored.campaign.revision, 1)

    def test_invalid_replacement_keeps_current_desk_and_career(self):
        desk = self.window.open_career(self.owner)
        replacement = NativeSaveOwner(SeasonCampaign(self.owner.campaign.state))
        with patch.object(replacement, 'desk_view', side_effect=ValueError('damaged boundary')):
            with self.assertRaisesRegex(ValueError, 'damaged boundary'):
                self.window.open_career(replacement)
        self.assertIs(self.window.current(), desk)
        self.assertEqual(self.window.stack, [desk])
        self.assertIs(self.window.career, self.owner)
