"""[designed: owner453/T143] Original captain recommendation, detached UI selection."""
import copy
import hashlib
import os
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch
from goal2.tests import requires

NATIVE=False
CAPTURES=None
FACTOR=1
OBSERVED=[]

class Rule(unittest.TestCase):
    def recommend(self,records,eleven=None):
        from goal2.core.views import _captain_recommendation
        memory=bytearray(20*(max(records)+1))
        for word,fields in records.items():
            row=bytearray(20);row[1]=25;row[14]=32
            for offset,value in fields.items():row[offset]=value
            memory[word*20:word*20+20]=row
        mem=SimpleNamespace(mem=memory,far=lambda pointer:0)
        before=bytes(memory)
        answer=_captain_recommendation(mem,list(records) if eleven is None else eleven)
        self.assertEqual(bytes(memory),before)
        return answer

    def test_ties_follow_actual_xi_order_and_younger_players_are_halved(self):
        records={1:{3:7,1:20},2:{3:5},3:{3:5},4:{3:7}}
        self.assertEqual(self.recommend(records,[1,3,2]),(3,[1,3,2]))
        self.assertEqual(self.recommend(records,[2,3,1]),(2,[2,3,1]))

    def test_availability_uses_signed_energy_and_current_match_status(self):
        records={1:{3:7,14:128},2:{3:7,16:128},3:{3:7,16:32},4:{3:7,16:4},
                 5:{3:4,16:16},6:{3:7,14:0}}
        self.assertEqual(self.recommend(records),(5,[5]))
        self.assertEqual(self.recommend(records,[1,2,3,4,6]),(None,[]))

    def test_pascal_remainder_unsigned_halving_and_signed_best_sentinel(self):
        # Authored boundary records: remainder -1 becomes word65535. The older
        # player's negative best sentinel lets the next eligible player replace him.
        self.assertEqual(self.recommend({1:{3:0,5:1},2:{3:2}})[0],2)
        # Below21 the original unsigned division produces32767, not Python -1//2.
        self.assertEqual(self.recommend({1:{3:0,5:1,1:20},2:{3:7}})[0],1)

@requires.need(modules=('unicorn','PySide6'),files=('e039-r0005-date-call.sav','GOAL.DAT'))
class Captain(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not NATIVE:os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
        from PySide6.QtWidgets import QApplication
        from goal2.desktop.core_model import CoreNewGame
        cls.app=QApplication.instance() or QApplication([])
        model,_=CoreNewGame(requires.CACHE/'e039-r0005-date-call.sav',requires.CACHE/'GOAL.DAT',
                           Path(tempfile.gettempdir())/'unused-t143.g2core').start(2028,16,'A Test')
        model.driver.round_start(watch=True)
        cls.saved=model.core.save()

    def setUp(self):
        from goal2.core import Core
        from goal2.desktop.core_model import CoreModel
        from goal2.desktop.core_window import CoreWindow
        from PySide6.QtTest import QTest
        self.before=hashlib.sha256(self.saved).hexdigest()
        self.w=CoreWindow(CoreModel(Core.load(self.saved,goal_dat=requires.CACHE/'GOAL.DAT'),
                                   requires.CACHE/'GOAL.DAT',Path(tempfile.gettempdir())/'unused-t143.g2core'))
        self.w.resize(900,640);self.w.show();self.w.raise_();self.w.activateWindow();self.app.processEvents()
        if NATIVE:self.assertTrue(QTest.qWaitForWindowActive(self.w,5000))
        self.w.core_round.show_captain();self.app.processEvents()
        self.addCleanup(self.close)
        self.unchanged()
        if NATIVE:
            self.assertIn(self.app.platformName(),('windows','xcb'))
            base=1.0
            import sys
            if sys.platform=='win32':
                import ctypes
                from ctypes import wintypes
                dpi=ctypes.WinDLL('user32',use_last_error=True).GetDpiForWindow
                dpi.argtypes=[wintypes.HWND];dpi.restype=wintypes.UINT
                base=dpi(int(self.w.winId()))/96.0
            self.assertGreater(base,0)
            self.assertAlmostEqual(self.w.devicePixelRatioF(),FACTOR*base)
            r=self.w.core_round;roster=r.captain_roster
            for control in (roster,r.captain_note,r.kick_off,r.computer):
                self.assertTrue(control.isVisible() and control.isEnabled())
                self.assertTrue(control.visibleRegion().contains(control.rect().center()))
                self.assertTrue(self.w.screen().geometry().contains(control.mapToGlobal(control.rect().center())))
            self.assertTrue(roster.visibleRegion().contains(roster.row_rect(roster.current).center()))
            self.assertGreaterEqual(r.captain_note.height(),r.captain_note.heightForWidth(r.captain_note.width()))
            OBSERVED.append({'test':self.id(),'dpr':self.w.devicePixelRatioF(),'size':[self.w.width(),self.w.height()],
                             'recommended':self.selected(),'core_unchanged':True})
            self.assertTrue(self.w.grab().save(str(CAPTURES/(self._testMethodName+'.png'))))

    def close(self):
        self.w.close();self.app.processEvents()

    def unchanged(self):
        self.assertEqual(hashlib.sha256(self.w.model.core.save()).hexdigest(),self.before)
        self.assertFalse(self.w.core_jobs.busy)

    def selected(self):
        roster=self.w.core_round.captain_roster
        return roster.rows[roster.current][0] if roster.current>=0 else None

    def test_initial_recommendation_matches_original_c_without_preselection_mutation(self):
        from goal2.core import Core,views
        from goal2.core.driver import Driver
        choice=self.w.model.round_state()['captain']
        self.assertNotEqual(choice['captain'],choice['recommended'],'fixture must distinguish stored and recommended')
        self.assertEqual(self.selected(),choice['recommended'])
        self.assertIn('Suggested captain:',self.w.core_round.captain_note.text())
        self.unchanged()
        oracle=Driver(Core.load(self.saved,goal_dat=requires.CACHE/'GOAL.DAT'))
        oracle.kick_off(watch=True,speed=0)
        self.assertEqual(views.match_sides(oracle.wait.state)['captain'],choice['recommended'])
        self.unchanged()

    def test_keyboard_mouse_override_survives_redraw_then_confirms_by_original_keys(self):
        from PySide6.QtCore import Qt
        from PySide6.QtTest import QTest
        from goal2.core import views
        r=self.w.core_round;roster=r.captain_roster
        choice=self.w.model.round_state()['captain']
        target=next(w for w in choice['eligible'] if w!=choice['recommended'])
        index=next(i for i,row in enumerate(roster.rows) if row[0]==target)
        QTest.keyClick(roster,Qt.Key.Key_Home)
        for _ in range(index):QTest.keyClick(roster,Qt.Key.Key_Down)
        self.assertEqual(self.selected(),target)
        QTest.mouseClick(roster,Qt.MouseButton.LeftButton,pos=roster.row_rect(index).center())
        for _ in range(3):r.show_captain();self.app.processEvents();self.assertEqual(self.selected(),target)
        self.unchanged()
        if CAPTURES is not None:self.assertTrue(self.w.grab().save(str(CAPTURES/'manual-selection.png')))
        with patch.object(self.w,'run_core',return_value=False) as action:
            QTest.mouseClick(r.kick_off,Qt.MouseButton.LeftButton,pos=r.kick_off.rect().center())
            action.assert_called_once_with('kick_off',target,r.watch.isChecked())
        self.unchanged()
        # The same chosen full player ID goes through the real driver's Up/Down/Enter
        # captain selection to the first genuine live poll. No guest memory edit.
        self.w.model.driver.kick_off(target,watch=True,speed=0)
        self.assertEqual(views.match_sides(self.w.model.state)['captain'],target)

    def test_changed_xi_reselects_and_all_unavailable_does_not_guess(self):
        r=self.w.core_round;state=self.w.model.round_state();choice=state['captain']
        target=next(w for w in choice['eligible'] if w!=choice['recommended'])
        r.captain_roster.set_current(next(i for i,row in enumerate(r.captain_roster.rows) if row[0]==target))
        # Explicitly authored detached UI projection, never written into the Core.
        projection=copy.deepcopy(state);projection['captain']['eleven'].reverse()
        projection['captain']['recommended']=choice['recommended']
        with patch.object(self.w.model,'round_state',return_value=projection):r.show_captain()
        self.assertEqual(self.selected(),choice['recommended'])
        projection['captain']['recommended']=None;projection['captain']['eligible']=[]
        with patch.object(self.w.model,'round_state',return_value=projection):r.show_captain()
        self.assertIsNone(self.selected())
        with patch.object(self.w,'run_core',side_effect=AssertionError('no eligible candidate')):r.kick_off_selected()
        r.show_captain()
        r.captain_roster.set_current(next(i for i,row in enumerate(r.captain_roster.rows) if row[0]==target))
        with patch.object(self.w,'run_core',return_value=False):r.start()
        r.show_captain()
        self.assertEqual(self.selected(),choice['recommended'],'new round must not inherit the old manual pick')
        self.unchanged()


def native():
    import argparse,json,subprocess
    global NATIVE,CAPTURES,FACTOR
    parser=argparse.ArgumentParser();parser.add_argument('--native',action='store_true',required=True)
    parser.add_argument('--factor',type=int,choices=(1,2),required=True);parser.add_argument('--out',required=True)
    args=parser.parse_args();NATIVE=True;FACTOR=args.factor;CAPTURES=Path(args.out)
    CAPTURES.mkdir(parents=True,exist_ok=False);os.environ['QT_SCALE_FACTOR']=str(FACTOR)
    requires.require(modules=('unicorn','PySide6'),files=('e039-r0005-date-call.sav','GOAL.DAT'))
    result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Captain))
    head=subprocess.check_output(['git','-c','safe.directory='+requires.ROOT.as_posix(),'rev-parse','HEAD'],cwd=requires.ROOT,text=True).strip()
    report={'head':head,'factor':FACTOR,'platform':Captain.app.platformName(),'tests':result.testsRun,
            'failures':len(result.failures),'errors':len(result.errors),'skips':len(result.skipped),'observations':OBSERVED}
    (CAPTURES/'receipt.json').write_text(json.dumps(report,indent=2)+'\n')
    raise SystemExit(0 if result.wasSuccessful() and not result.skipped else 1)

if __name__=='__main__':
    import sys
    native() if '--native' in sys.argv else unittest.main()
