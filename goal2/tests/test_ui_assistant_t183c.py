"""[designed: T183c/#762] Explicit S08 action, shared pipe, owner-only publication.

Actual keyboard/mouse cases use PyPy; gated preparation and injected refusal/
failure below are labelled host/UI controls, never original-calendar evidence.
"""
import copy
import tempfile
import threading
import time
import unittest
from pathlib import Path
from unittest.mock import patch

from goal2.tests import requires
requires.require(modules=('PySide6',))
from PySide6.QtCore import Qt,QTimer
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication
from goal2.tests.ui_assertions import assert_fits
from goal2.ui import theme
from goal2.ui.window import Window
from goal2.ui.s08_squad import open_squad
from goal2.ui.screen import Clickable
from goal2.desktop import data_setup
from goal2.game.best_twenty_jobs import close_model
from goal2.tests.test_assistant_pipe_t183c import model
from goal2.tests.pypy_engine import call


@requires.need(**requires.HALFTIME)
class AssistantUI(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app=QApplication.instance() or QApplication([])
        cls.old_font=cls.app.font();theme.install(cls.app)

    @classmethod
    def tearDownClass(cls):
        cls.app.setFont(cls.old_font)

    def setUp(self):
        self.folder=tempfile.TemporaryDirectory();self.addCleanup(self.folder.cleanup)
        self.model=model();self.win=Window(data_setup.paths(Path(self.folder.name)/'game'))
        self.win.open_career(self.model);self.win.show();self.app.processEvents()
        self.screen=open_squad(self.win,self.model);self.app.processEvents()
        self.addCleanup(self.cleanup)

    def cleanup(self):
        close_model(self.model)
        self.win.leaving=True;self.win.close();self.win.deleteLater();self.app.processEvents()

    def click_assistant(self):
        item=next(w for w in self.screen.key_bar.findChildren(Clickable,'keyItem') if w.binding.text=='assistant')
        QTest.mouseClick(item,Qt.MouseButton.LeftButton);self.app.processEvents()

    def key(self,key):
        QTest.keyClick(self.win,key);self.app.processEvents()

    def until(self,predicate,timeout=30):
        end=time.monotonic()+timeout
        while time.monotonic()<end:
            self.app.processEvents()
            if predicate():return
            QTest.qWait(10)
        self.fail('UI assistant did not reach the expected state')

    def finished(self):
        self.until(lambda:self.screen._assistant_token is None)

    def expected(self):
        from goal2.game.best_twenty_state import prepare,candidate
        p=prepare(self.model.state)
        answer=call('goal2.tests.test_best_twenty_t183a:native',p.native)
        return candidate(p,answer)

    def gated(self):
        from goal2.game import best_twenty_jobs
        entered,release=threading.Event(),threading.Event();real=best_twenty_jobs.prepare
        def held(value):
            entered.set()
            if not release.wait(10):raise RuntimeError('preparation control not released')
            return real(value)
        return entered,release,patch.object(best_twenty_jobs,'prepare',held)

    def test_actual_insert_and_mouse_equal_direct_candidate_and_keep_one_process(self):
        expected=self.expected()
        self.key(Qt.Key.Key_Insert);self.finished()
        self.assertEqual(self.model.state,expected)
        jobs=self.model.assistant_jobs();pid=jobs.shared.engine.pid
        self.assertIsNotNone(pid)
        self.assertNotIn('coming later',self.screen.note.text())
        self.assertIn('Review',self.screen.note.text())
        expected=self.expected()
        self.click_assistant();self.finished()
        self.assertEqual(self.model.state,expected)
        self.assertEqual(jobs.shared.engine.pid,pid)
        self.assertIn('No stronger players',self.screen.note.text())
        self.assertEqual(len(set(self.model.state.managed_squad+self.model.state.campaign.reserve_ids)),100)
        assert_fits(self,self.win)

    def test_heartbeat_and_cancel_before_send_never_publish(self):
        before=copy.deepcopy(self.model.state);entered,release,control=self.gated()
        beats=[];timer=QTimer();timer.setInterval(10);timer.timeout.connect(lambda:beats.append(1));timer.start()
        try:
            with control:
                self.key(Qt.Key.Key_Insert);self.assertTrue(entered.wait(5))
                self.until(lambda:len(beats)>=4)
                self.assertEqual(self.model.state,before)
                self.assertIn('Esc:',self.screen.note.text())
                assert_fits(self,self.win)
                self.key(Qt.Key.Key_Escape)
                self.assertIsNot(self.win.current(),self.screen)
                release.set()
                jobs=self.model.assistant_jobs()
                self.until(lambda:not jobs.busy or jobs.poll(jobs.token) is not None)
                self.assertEqual(self.model.state,before)
                self.assertIsNone(jobs.shared.engine.process,'cancelled preparation must not start a child')
        finally:
            release.set();timer.stop()

    def test_stale_same_value_new_identity_is_not_published(self):
        entered,release,control=self.gated()
        try:
            with control:
                self.key(Qt.Key.Key_Insert);self.assertTrue(entered.wait(5))
                self.model.state=copy.deepcopy(self.model.state)
                expected=copy.deepcopy(self.model.state);release.set();self.finished()
            self.assertEqual(self.model.state,expected)
            self.assertIn('career changed',self.screen.note.text())
        finally:release.set()

    def test_external_edit_and_candidate_validation_failure_preserve_live_data(self):
        entered,release,control=self.gated()
        try:
            with control:
                self.key(Qt.Key.Key_Insert);self.assertTrue(entered.wait(5))
                self.model.rename_manager('A Changed');expected=copy.deepcopy(self.model.state)
                release.set();self.finished()
            self.assertEqual(self.model.state,expected)
            self.assertIn('career changed',self.screen.note.text())
            before=copy.deepcopy(self.model.state)
            real_view=self.model.view
            def validate(value=None):
                if value is not None:raise ValueError('controlled candidate validation')
                return real_view()
            with patch.object(self.model,'view',side_effect=validate):
                self.click_assistant();self.finished()
            self.assertEqual(self.model.state,before)
            self.assertIn('could not finish',self.screen.note.text())
        finally:release.set()

    def test_original_refusal_ui_policy_and_failed_preparation_publish_nothing(self):
        # UI/publication control only. The actual genuine-tour pipe proof is in
        # test_assistant_pipe_t183c, not this injected completed reply.
        from goal2.game import best_twenty_jobs
        from goal2.game.engine_process import EngineProcess
        before=copy.deepcopy(self.model.state)
        with patch.object(best_twenty_jobs,'prepare',side_effect=ValueError('controlled unsupported context')):
            self.click_assistant();self.finished()
        self.assertEqual(self.model.state,before)
        self.assertIn('not available for this career',self.screen.note.text())
        def refuse(engine,value):
            from goal2.game.season import canonical_hash
            digest=canonical_hash(value)
            def send():
                engine.on_reply('assistant',{'request':123,'input_hash':digest,
                                            'result':{'allowed':False,'refusal':'tour'}})
            threading.Timer(.02,send).start()
            return 123
        with patch.object(EngineProcess,'assistant',refuse):
            self.click_assistant();self.finished()
        self.assertEqual(self.model.state,before)
        self.assertIn('whilst on tour',self.screen.note.text())

    def test_name_editor_pool_pane_and_busy_edit_guards_keep_data(self):
        self.screen.new_name();self.screen.card.name_line.edit.setText('Draft name')
        before=copy.deepcopy(self.model.state)
        self.click_assistant()
        self.assertIsNone(self.screen._assistant_token)
        self.assertEqual(self.screen.card.name_line.edit.text(),'Draft name')
        self.assertEqual(self.model.state,before)
        self.screen.close_name();self.screen.show_side('pool');self.click_assistant()
        self.assertIsNone(self.screen._assistant_token)
        self.assertIn('Left:',self.screen.note.text())
        self.screen.show_side('squad')
        entered,release,control=self.gated()
        try:
            with control:
                self.click_assistant();self.assertTrue(entered.wait(5))
                self.screen.reposition(1);self.screen.club_position();self.screen.press_move();self.screen.new_name();self.screen.his_tactics()
                self.assertEqual(self.model.state,before)
                self.assertFalse(self.screen.editing)
                self.assertIs(self.win.current(),self.screen)
                release.set();self.finished()
        finally:release.set()

    def test_close_and_career_replacement_cannot_publish_old_reply(self):
        entered,release,control=self.gated();old=self.model;before=copy.deepcopy(old.state)
        try:
            with control:
                self.click_assistant();self.assertTrue(entered.wait(5))
                replacement=model();self.win.open_career(replacement)
                self.assertEqual(old.state,before)
                release.set();QTest.qWait(100);self.app.processEvents()
                self.assertEqual(old.state,before)
                self.assertFalse(hasattr(old,'_assistant_jobs'))
                self.assertIs(self.win.career,replacement)
                close_model(replacement)
        finally:release.set()

    def test_save_cancel_on_window_close_retains_the_squad_screen(self):
        self.model.rename_manager('A Unsaved');before=copy.deepcopy(self.model.state)
        entered,release,control=self.gated()
        try:
            with control:
                self.click_assistant();self.assertTrue(entered.wait(5))
                self.win.close();self.app.processEvents()
                self.assertIn(self.screen,self.win.stack)
                self.assertIsNot(self.win.current(),self.screen)
                release.set();self.key(Qt.Key.Key_Escape)
                self.assertIs(self.win.current(),self.screen)
                self.assertEqual(self.model.state,before)
                self.assertIsNone(self.screen._assistant_token)
                self.assertIn('cancelled',self.screen.note.text())
        finally:release.set()
