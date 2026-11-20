"""[designed: #799/#800/#801] Navigation and save cues describe actual actions."""
import copy,tempfile,unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from goal2.tests import requires
requires.require(modules=('PySide6',))
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication,QLabel,QVBoxLayout,QWidget
from goal2.ui import theme,replays
from goal2.tests.ui_assertions import assert_fits
from goal2.ui.window import Window
from goal2.desktop import data_setup
APP=QApplication.instance() or QApplication([])


class WindowCase(unittest.TestCase):
    def setUp(self):
        theme.install(APP);self.folder=tempfile.TemporaryDirectory();self.addCleanup(self.folder.cleanup)
        self.win=Window(data_setup.paths(Path(self.folder.name)/'game'));self.addCleanup(self.cleanup)

    def cleanup(self):
        self.win.leaving=True;self.win.close();self.win.deleteLater();APP.processEvents()

    def escape_to(self,screen,parent,caption):
        binding=next(b for b in screen.bindings if Qt.Key.Key_Escape in b.keys)
        self.assertEqual(binding.text,caption)
        APP.processEvents();assert_fits(self,self.win)
        screen.handle_key(Qt.Key.Key_Escape)
        self.assertIs(self.win.current(),parent)


@requires.need(**requires.HALFTIME)
class BackCaptions(WindowCase):
    def setUp(self):
        super().setUp()
        from goal2.tests.test_assistant_pipe_t183c import model
        self.model=model();self.model.mark_saved();self.win.open_career(self.model)
        self.win.show();APP.processEvents()

    def test_team_info_tactics_escape_returns_to_team_info(self):
        from goal2.ui.s07_team_info import TeamInfoScreen
        parent=self.win.push(TeamInfoScreen(self.win,self.model))
        parent.index=next(i for i,row in enumerate(parent.order) if row[0]==self.model.state.managed_country)
        parent.tactics();self.escape_to(self.win.current(),parent,'team info')

    def test_pre_match_players_and_tactics_escape_return_to_match_menu(self):
        from goal2.ui.match_day import MatchDay
        from goal2.ui.s15_match_menu import MenuScreen
        day=MatchDay(self.win,self.model);day.fixture=self.model.state.campaign.next_fixture
        day.watch=True
        parent=self.win.push(MenuScreen(self.win,day,'before'))
        for action in (parent.players,parent.tactics):
            action(self.model.state.managed_country)
            self.escape_to(self.win.current(),parent,'match menu')

    def test_new_career_escape_returns_to_the_desk(self):
        parent=self.win.current();parent.new_career()
        self.escape_to(self.win.current(),parent,'desk')


class RecordingsCues(WindowCase):
    def test_empty_lists_offer_no_open_and_have_one_arrow_caption(self):
        for kind in ('goal','summary'):
            with self.subTest(kind=kind):
                screen=replays.open_list(self.win,None,kind)
                arrows=[(caps,text) for caps,text in screen.key_texts() if caps==('↑','↓')]
                self.assertEqual(len(arrows),1)
                self.assertEqual(screen.enter_hint_text(),'')
                screen.press_enter();self.assertIs(self.win.current(),screen)
                self.win.pop()

    def test_nonempty_list_keeps_open_hint(self):
        with patch.object(replays,'entries',return_value=[{'name':'Example recording'}]):
            screen=replays.open_list(self.win,None,'goal')
        self.assertEqual(screen.enter_hint_text(),'Open')
        self.assertEqual(len([b for b in screen.bindings if b.captions==('↑','↓')]),1)


class CoreSaveCues(unittest.TestCase):
    def test_saved_match_and_save_prompt_summaries_do_not_claim_a_future_fixture(self):
        from goal2.desktop.launch import core_summary
        desk=dict(team={'name':'Example'},manager='A Manager',year=1990,stage_word='qualifying',
                  squad=list(range(20)),sacked=False,opponent={'name':'Opponent'},fixture_kind='friendly home')
        original=copy.deepcopy(desk)
        for in_round,in_save,caption,next_action in ((True,False,'In a match','Continue this match'),
                                                    (False,True,'At the save prompt','Resume the save prompt')):
            with self.subTest(in_round=in_round,in_save=in_save):
                model=SimpleNamespace(desk=lambda:desk,in_round=in_round,in_save_name=in_save)
                answer=core_summary(model)
                self.assertEqual(answer['checkpoint'],caption);self.assertEqual(answer['next'],next_action)
        self.assertEqual(desk,original)

    def test_save_page_has_player_resume_instructions(self):
        from goal2.desktop.core_window import CoreWindow
        page=QWidget();page.content=QVBoxLayout(page);self.addCleanup(page.deleteLater)
        window=SimpleNamespace(pages=[None]*4+[page],model=SimpleNamespace(save_path=Path('game.g2core')),
                               save_core=lambda:None,cancel_save_name=lambda:None)
        CoreWindow._build_save(window)
        words=' '.join(w.text() for w in page.findChildren(QLabel))
        self.assertNotIn('python3',words);self.assertIn('Start goal2 again',words)


@requires.need(modules=('unicorn',),files=('e006-r0001-main.sav','GOAL.DAT'))
class ActualCoreSaveCue(unittest.TestCase):
    def test_live_match_save_reloads_with_a_current_match_summary(self):
        from goal2.tests.test_core_in_match_tactics_t224 import watched_live,_core
        from goal2.desktop.core_model import CoreModel
        from goal2.desktop.launch import core_summary
        watched_live()
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'live.g2core'
            model=CoreModel(_core('live'),requires.CACHE/'GOAL.DAT',path)
            self.assertEqual(model.core.wait.kind,'match-live')
            self.assertTrue(model.in_round)
            before=model.memory_sha256();model.save(path)
            loaded=CoreModel.from_save(path,requires.CACHE/'GOAL.DAT')
            self.assertEqual(loaded.memory_sha256(),before)
            self.assertTrue(loaded.in_round)
            summary=core_summary(loaded)
            self.assertEqual(summary['checkpoint'],'In a match')
            self.assertEqual(summary['next'],'Continue this match')
            self.assertEqual(loaded.memory_sha256(),before)
