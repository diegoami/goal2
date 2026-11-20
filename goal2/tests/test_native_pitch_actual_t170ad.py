"""[designed: T170ad/#814] Actual retained PyPy Match through real S17."""
import copy
from dataclasses import asdict
import json
from pathlib import Path
import tempfile
import time
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from goal2.tests import requires,pypy_engine
requires.require(modules=('PySide6',))
from PySide6.QtCore import Qt, QTimer
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication
from goal2.data.goaldat import load
from goal2.desktop import data_setup
from goal2.desktop.model import DesktopModel
from goal2.engine.original_match.image import Image
from goal2.game import engine_tables
from goal2.game.native_season import NativeSeasonOwner
from goal2.game.season import canonical_hash
from goal2.tests import test_native_driver_actual_t170ac as driver_proof
from goal2.tests.test_prematch_preview_t170s import reference_raw
from goal2.tests.test_season_news_wire_t170t import digest
from goal2.ui import theme
from goal2.ui.native_pitch import NativePitchScreen
from goal2.ui.screen import Screen
from goal2.ui.window import Window
from goal2.tests.ui_assertions import assert_fits

ROOT=Path(__file__).resolve().parents[2]


@requires.need(files=('GOAL.DAT',))
class NativeWindow(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app=QApplication.instance() or QApplication([]);theme.install(cls.app)

    def test_held_widgets_to_native_pitch_pause_reading_and_covered_close(self):
        from goal2.tests.test_native_season_window_t170aa import Screens
        Screens.setUpClass()
        case=Screens('test_actual_owner_enters_widgets_edits_current_xi_and_transfers_captain_once')
        self.addCleanup(case.doCleanups)
        with patch('goal2.tests.test_native_season_window_t170aa.NativeSeasonOwner',
                   side_effect=lambda owner,state:NativeSeasonOwner(owner,state,frames=True)):
            case.setUp()
        seen=[];failures=[]
        def decision(s,d):
            seen.append(d['event']['data']['context'])
            s.answer_native(d['decision'],{'taker':None} if seen[-1]=='set_piece' else {})
        screens=[];original_handoff=case.flow.on_handoff
        def handoff(flow,packet,prefs):
            original_handoff(flow,packet,prefs)
            screen=NativePitchScreen(case.win,case.owner,case.native,connection=case.handoffs[0][0],
                on_decision=decision,on_goal=lambda s,e:s.release_goal(),on_complete=lambda s:None,
                on_failure=lambda s,e:failures.append(e))
            screens.append(screen);case.win.push(screen)
        case.flow.on_handoff=handoff
        case.test_actual_owner_enters_widgets_edits_current_xi_and_transfers_captain_once()
        screen=screens[0];self.addCleanup(screen.closing)
        def responsive():
            self.app.processEvents();self.assertEqual(failures,[])
        case.until(lambda:screen.controller.driver.painted_sequence>=9,responsive)
        assert_fits(self,case.win);self.assertTrue(screen.pitch.painted)
        QTest.keyClick(case.win,Qt.Key.Key_Space);self.app.processEvents()
        count=len(screen.controller.driver.frames)
        for _ in range(20):screen.tick();self.app.processEvents()
        self.assertEqual(len(screen.controller.driver.frames),count)
        QTest.keyClick(case.win,Qt.Key.Key_Return);self.app.processEvents()
        self.assertTrue(screen.controller.request_bench())
        case.until(lambda:'pause' in seen,responsive)
        self.assertEqual(failures,[]);self.assertEqual(case.native.pid,case.pid)
        self.assertEqual(case.native.shared.engine.generation,1);self.assertEqual(case.owner.state,case.before)
        case.win.push(Screen(case.win));case.win.leaving=True;case.win.close()
        case.until(lambda:case.native.disposed,limit=15)
        self.assertEqual(case.owner.state,case.before);case.owner.confirm.assert_not_called()

    @requires.need(slow=True)
    def test_full_painted_native_ui_consumer_matches_sdk_and_explicit_resume(self):
        raw=reference_raw();expected=pypy_engine.call('goal2.tests.test_native_driver_actual_t170ac:direct',raw)
        tmp=tempfile.TemporaryDirectory(prefix='goal2-native-pitch-');self.addCleanup(tmp.cleanup)
        model=DesktopModel(load((ROOT/'.cache/GOAL.DAT').read_bytes()),raw,Path(tmp.name)/'unused')
        before=copy.deepcopy(model.state)
        helper=driver_proof.Actual('test_complete_pause_edit_paced_driver_and_resume_equal_direct_sdk')
        self.addCleanup(helper.doCleanups)
        native,driver,prefix,boundary=helper.prepare(model,Image.from_bytes(raw).state(engine_tables.load()))
        win=Window(data_setup.paths(Path(tmp.name)/'data'));win.resize(1440,1080);win.push(Screen(win));win.show()
        def close():win.leaving=True;win.close();win.deleteLater();self.app.processEvents()
        self.addCleanup(close)
        answers=driver_proof.Answers();decisions=[];failures=[];completed=[]
        def decision(s,d):
            decisions.append(d['decision']);s.answer_native(d['decision'],answers(d['event']['data']))
        def complete(s):completed.append(True);s.resume_native()
        with patch('goal2.ui.native_pitch.NativeMatchDriver',return_value=driver):
            screen=NativePitchScreen(win,model,native,on_decision=decision,
                on_goal=lambda s,e:s.release_goal(),on_complete=complete,
                on_failure=lambda s,e:failures.append(e),connection=driver.connection)
        win.push(screen);screen.timer.stop();self.addCleanup(screen.closing)
        requested=[]
        def painted(seq):
            screen.painted(seq)
            if not requested:
                self.assertTrue(screen.controller.request_bench());requested.append(True)
        screen.pitch.on_drawn=painted
        beats=[];timer=QTimer();timer.setInterval(2);timer.timeout.connect(lambda:beats.append(True));timer.start()
        self.addCleanup(timer.stop)
        now=0.;end=time.monotonic()+900
        with patch('goal2.ui.native_pitch.time',SimpleNamespace(monotonic=lambda:now)):
            while time.monotonic()<end and driver.status not in ('resumed','lost','closed'):
                now+=1.;screen.tick();self.app.processEvents();time.sleep(.0005)
                if screen.stop_box.open:screen.answer_stop_box(Qt.Key.Key_Return)
        self.assertEqual(failures,[]);self.assertEqual(driver.status,'resumed',driver.error)
        self.assertEqual(completed,[True]);self.assertEqual(len(decisions),len(set(decisions)))
        self.assertGreater(len(beats),2);self.assertEqual(driver.painted_sequence,len(driver.frames)-1)
        observations=native.take_observations()
        actual=dict(events_hash=digest(prefix+driver.events),frames_hash=digest(driver.frames),
            events=len(prefix+driver.events),frames=len(driver.frames),state_hash=canonical_hash(native.boundary_state),
            observation_hash=digest(asdict(observations[-1])),status=driver.boundary_status,
            pauses=driver.pause_requests,edited=answers.edited)
        for key,value in actual.items():self.assertEqual(value,expected[key],key)
        self.assertEqual(model.state,before);self.assertEqual(native.shared.engine.generation,1)
        self.assertFalse(screen.timer.isActive());self.assertEqual(native.take_observations(),[])
        print('T170AD_FULL '+json.dumps(actual,sort_keys=True),flush=True)
