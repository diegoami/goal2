"""[designed: T170ad/#814] Real S17 controls over controlled native packets."""
import copy
import tempfile
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

from goal2.tests import requires
requires.require(modules=('PySide6',))
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication
from PySide6.QtTest import QTest
from goal2.tests.test_native_driver_t170ac import Owner, event
from goal2.tests.test_season_pitch_t170ab import frame
from goal2.ui import theme
from goal2.ui.native_pitch import NativePitchScreen
from goal2.ui.screen import Screen
from goal2.ui.window import Window
from goal2.desktop import data_setup


class WindowControls(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([]); theme.install(cls.app)

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.win = Window(data_setup.paths(Path(self.tmp.name))); self.win.resize(1440,1080)
        self.win.push(Screen(self.win)); self.win.show()
        self.owner = Owner(); self.owner.status = 'handed_off'
        state = SimpleNamespace(mem=b'current',player_renames={},manager_name='')
        self.owner.controller = SimpleNamespace(view=SimpleNamespace(display_state=lambda s:state,sides=(1,2)))
        self.owner.fixture = SimpleNamespace(side_a=1,side_b=2,kind=1,stage=0)
        self.model = SimpleNamespace(state=state,goaldat=None)
        self.decisions=[]; self.goals=[]; self.completions=[]; self.failures=[]
        identity={'countries':['ONE','TWO'],'roles':{},'managed':0,'kind':'Friendly'}
        with patch('goal2.ui.native_pitch.pitch_identity',return_value=identity), \
             patch('goal2.engine.original_match.image.Image.from_memory_component') as image:
            image.return_value.rd.return_value=0
            self.screen=NativePitchScreen(self.win,self.model,self.owner,
                on_decision=lambda s,d:self.decisions.append(d),
                on_goal=lambda s,e:self.goals.append(e),
                on_complete=lambda s:self.completions.append(s),
                on_failure=lambda s,e:self.failures.append(e),
                pause_controls=getattr(self, 'pause_controls', False),
                **({'opportunity_controls': True} if getattr(self, 'opportunity_controls', False) else {}),
                **({'substitution_controls': True} if getattr(self, 'substitution_controls', False) else {}),
                **({'choice_controls': True} if getattr(self, 'choice_controls', False) else {}))
        self.win.push(self.screen);self.screen.timer.stop()
        self.addCleanup(self.dispose)

    def dispose(self):
        self.screen.closing();self.win.leaving=True;self.win.close();self.win.deleteLater();self.app.processEvents()

    def key(self,key):
        QTest.keyClick(self.win,key);self.app.processEvents()

    def tick(self): self.screen.tick()

    def decision(self,context='set_piece',number=7):
        e=event('decision',{'context':context});e['score']=[0,0]
        self.owner.batch(events=[e],decision=number,total=4);self.tick()

    def test_real_pitch_paints_before_next_and_preserves_offset(self):
        self.tick();self.owner.batch(frames=[frame(0,3)]);self.tick()
        self.assertEqual(self.screen.controller.driver.painted_sequence,-1)
        self.app.processEvents()
        self.assertEqual(self.screen.controller.driver.painted_sequence,0)
        self.assertEqual(self.screen.display().frame['watermark'],3)
        self.assertEqual(len(self.owner.sent),1);self.tick();self.assertEqual(len(self.owner.sent),2)
        self.assertTrue(self.screen.pitch.painted)
        self.assertIsInstance(self.screen.controller.driver.events[0]['score'],tuple)
        self.assertIsInstance(self.screen.display().events[0]['score'],list)

    def test_existing_marks_speed_reading_keys_and_no_poll_while_reading(self):
        self.key(Qt.Key.Key_Right);self.assertEqual(self.screen.controller.driver.speed,4)
        marks=self.screen.pitch.marks
        self.key(Qt.Key.Key_Down);self.assertEqual(self.screen.pitch.marks,(marks+1)%5)
        self.key(Qt.Key.Key_Space);self.assertTrue(self.screen.controller.driver.held)
        self.tick();self.assertEqual(self.owner.sent,[])
        self.key(Qt.Key.Key_Return);self.tick();self.assertEqual(self.owner.sent[-1][0],'next')
        self.key(Qt.Key.Key_F9);self.assertIn('no sound',self.screen.controller.note)

    def test_quick_never_answers_decisions_and_delivers_once(self):
        self.key(Qt.Key.Key_R);self.tick();self.decision()
        self.assertEqual(len(self.decisions),1);self.tick();self.assertEqual(len(self.decisions),1)
        self.assertFalse(any(a=='answer' for a,_ in self.owner.sent))
        with self.assertRaises(ValueError):self.screen.answer_native(8,{})
        self.screen.answer_native(7,{'taker':None})
        with self.assertRaises(ValueError):self.screen.answer_native(7,{})
        self.assertEqual(self.owner.sent[-1][1]['answer'],{'taker':None})

    def test_help_cover_holds_and_preserves_stop_until_return(self):
        self.tick();self.key(Qt.Key.Key_F1);self.decision()
        self.assertEqual(self.decisions,[]);self.assertTrue(self.screen.controller.driver.held)
        self.key(Qt.Key.Key_Escape);self.tick();self.assertEqual(len(self.decisions),1)

    def test_bench_key_serializes_pause_and_close_under_cover_disposes_owner(self):
        self.key(Qt.Key.Key_Return);self.tick();self.assertEqual(self.owner.sent,[('pause',{})])
        self.key(Qt.Key.Key_Escape);self.assertEqual(self.screen.controller.driver.pause_requests,1)
        self.win.push(Screen(self.win));self.win.leaving=True;self.win.close()
        self.assertTrue(self.owner.closed);self.assertFalse(self.screen.timer.isActive())

    def test_painted_goal_holds_once_until_explicit_release(self):
        self.tick();e=event('goal',{'player':4});e['score']=[0,0]
        self.owner.batch(events=[e],total=4);self.tick()
        self.owner.batch(frames=[frame(0,4)],total=4);self.tick();self.app.processEvents();self.tick()
        self.assertEqual(len(self.goals),1);sent=copy.deepcopy(self.owner.sent)
        self.tick();self.assertEqual(self.owner.sent,sent);self.assertEqual(len(self.goals),1)
        self.screen.release_goal();self.tick();self.assertEqual(len(self.owner.sent),3)
        with self.assertRaises(ValueError):self.screen.release_goal()

    def test_completion_and_resume_are_explicit_and_delivery_once(self):
        self.tick();e=event('end');e['score']=[0,0]
        self.owner.batch(events=[e],total=4,over=True,exhausted=True);self.tick();self.tick()
        self.assertEqual(self.completions,[self.screen]);self.assertEqual(len(self.owner.sent),1)
        self.screen.resume_native();self.owner.reply('resume',state={},observation={});self.tick()
        self.assertEqual(len(self.owner.adopted),1);self.assertFalse(self.screen.timer.isActive())
        self.screen.closing();self.assertFalse(self.owner.closed)

    def test_callback_exception_and_worker_loss_fail_closed_once(self):
        self.screen.on_decision=Mock(side_effect=RuntimeError('consumer failed'))
        self.tick();self.decision();self.tick()
        self.assertTrue(self.owner.closed);self.assertEqual(len(self.failures),1)
        self.assertIn('consumer failed',self.failures[0])

    def test_loss_while_help_covered_reaches_failure_consumer(self):
        self.tick();self.key(Qt.Key.Key_F1)
        self.owner.queue.put(('death','gone'));self.tick()
        # Covered reading holds the transport too; close still disposes it.
        self.assertEqual(self.failures,[])
        self.key(Qt.Key.Key_Escape);self.tick();self.tick()
        self.assertTrue(self.owner.closed);self.assertEqual(len(self.failures),1)

    def test_callbacks_are_required_before_handoff_is_consumed(self):
        with self.assertRaises(ValueError):
            NativePitchScreen(self.win,self.model,self.owner,on_decision=None,on_goal=None,
                              on_complete=None,on_failure=None)
        self.assertEqual(self.owner.handoffs,1)

    def test_quick_score_follows_events_without_overwriting_last_painted_frame(self):
        self.tick();self.owner.batch(frames=[frame(0,3)]);self.tick();self.app.processEvents()
        self.screen.quick_result();self.tick()
        e=event('goal',{'player':4});e['minute']=12;e['score']=[1,0]
        self.owner.batch(events=[e],total=4);self.tick()
        self.assertEqual(self.screen.controller.frame_or_event(),(12,[1,0]))
        self.assertEqual(self.screen.display().frame['sequence'],0)

    def test_polling_does_not_reset_native_pacing_deadline(self):
        c=self.screen.controller
        c.tick(0);self.owner.batch(frames=[frame(0,3)]);self.assertTrue(c.tick(0))
        c.painted(0);c.tick(0);self.owner.batch(frames=[frame(1,3)])
        self.assertFalse(c.tick(.001));self.assertEqual(c.display.frame['sequence'],0)
        self.assertTrue(c.tick(.02));self.assertEqual(c.display.frame['sequence'],1)

    def test_history_cursor_is_detached_bounded_and_renderer_uses_only_suffixes(self):
        c=self.screen.controller;driver=c.driver
        values=driver.events_since(0);values[0]['data']['foreign']=True
        self.assertNotIn('foreign',driver.events_since(0)[0]['data'])
        for cursor in (True,-1,2,1.0):
            with self.assertRaises(ValueError):driver.events_since(cursor)
        self.assertEqual(driver.events_since(1),[])
        with patch.object(type(driver),'events',property(lambda s:(_ for _ in ()).throw(AssertionError('whole history read')))):
            c.tick(0);c.tick(.1);self.assertEqual(len(c.display.events),1)
            self.assertEqual(c.shown(),[])  # no sample has released that event yet
