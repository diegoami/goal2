"""[designed: T170aa/#783] Actual shared owner → held widgets → retained handoff."""
import copy
from pathlib import Path
import tempfile
import time
import unittest
from unittest.mock import Mock

from goal2.tests import requires
requires.require(modules=('PySide6',))
from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication
from goal2.data.goaldat import load
from goal2.desktop import data_setup,fixed_page
from goal2.desktop.model import DesktopModel
from goal2.game.native_season import NativeSeasonOwner
from goal2.game.season import canonical_hash
from goal2.game import roles
from goal2.tests.test_prematch_preview_t170s import reference_raw
from goal2.tests.test_prematch_marking_t170w import initial_state
from goal2.ui import theme
from goal2.ui.held_prematch import HeldPrematchFlow
from goal2.ui.s08_squad import SquadScreen
from goal2.ui.s16_choose import ChooseScreen
from goal2.ui.screen import Screen
from goal2.ui.window import Window
from goal2.tests.ui_assertions import assert_fits

ROOT=Path(__file__).resolve().parents[2]


@requires.need(files=('GOAL.DAT',))
class Screens(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app=QApplication.instance() or QApplication([]);theme.install(cls.app)

    def setUp(self):
        raw=reference_raw();state,_,_=initial_state(raw)
        self.tmp=tempfile.TemporaryDirectory(prefix='goal2-native-owner-ui-');self.addCleanup(self.tmp.cleanup)
        self.owner=DesktopModel(load((ROOT/'.cache/GOAL.DAT').read_bytes()),raw,Path(self.tmp.name)/'save')
        self.native=NativeSeasonOwner(self.owner,state)
        self.addCleanup(self.dispose)
        self.until(lambda:self.native.status in ('boundary','lost'),self.native.poll)
        self.assertEqual(self.native.status,'boundary',self.native.message)
        self.native.advance();self.until(lambda:self.native.status in ('prematch','lost'),self.native.poll)
        self.assertEqual(self.native.status,'prematch',self.native.message)
        self.c=self.native.controller;self.pid=self.native.pid
        # Identity host only. Native input was supplied before this display state existed.
        self.owner.state=self.c.view.display_state();self.before=copy.deepcopy(self.owner.state)
        self.owner.confirm=Mock(side_effect=AssertionError('legacy confirmation is outside the native entry'))
        self.win=Window(data_setup.paths(Path(self.tmp.name)/'data'));self.win.resize(1440,1080)
        self.win.push(Screen(self.win));self.win.show();self.handoffs=[];self.closed=[]
        def handoff(flow,packet,prefs):
            connection=self.native.handoff();self.assertEqual(connection.packet,packet)
            self.handoffs.append((connection,prefs))
        def close(flow):self.closed.append(True);self.native.close()
        self.flow=HeldPrematchFlow(self.win,self.owner,self.c,self.native.fixture,self.native.replies,
            on_handoff=handoff,on_close=close,on_tournament=lambda f:self.win.push(Screen(self.win)),
            on_stats=lambda f,m:self.win.push(Screen(self.win)),watch=True)
        self.flow.open();self.app.processEvents();assert_fits(self,self.win)

    def until(self,condition,step=None,limit=120):
        end=time.monotonic()+limit
        while time.monotonic()<end:
            if step:step()
            if condition():return
            time.sleep(.002)
        self.fail('actual native screen entry did not settle')

    def dispose(self):
        if hasattr(self,'flow'):self.flow.close()
        self.native.close();self.until(lambda:self.native.disposed,limit=15)
        if hasattr(self,'win'):
            self.win.leaving=True;self.win.close();self.win.deleteLater();self.app.processEvents()

    def key(self,key):QTest.keyClick(self.win,key);self.app.processEvents()

    def settled(self):
        self.until(lambda:not self.c.pending,self.flow.poll);self.flow.poll()
        self.assertIn(self.c.status,('ready','handoff'),self.c.message);self.assertEqual(self.native.pid,self.pid)

    def pick(self,s,word):
        s.cursor['squad']=next(i for i,r in enumerate(s.rows()) if r['id']==word);s.refresh()

    def test_actual_owner_enters_widgets_edits_current_xi_and_transfers_captain_once(self):
        from goal2.game.best_twenty_jobs import AssistantJobs
        from goal2.game.watched_jobs import WatchedJobs
        from goal2.engine.original_match import Fixture
        assistant=AssistantJobs(self.owner);watched=WatchedJobs(self.owner)
        try:
            with self.assertRaisesRegex(ValueError,'already running'):assistant.start()
            f=self.native.fixture
            with self.assertRaisesRegex(ValueError,'already running'):
                watched.start(Fixture(first=f.side_a,second=f.side_b,index=f.index,kind=f.kind))
            self.assertEqual(self.native.shared.engine.generation,1)
            self.assertIs(self.native.shared.match,self.native)
        finally:assistant.close();watched.close()
        before=canonical_hash(self.native.boundary_state);self.key(Qt.Key.Key_Space)
        s=self.win.current();self.assertIsInstance(s,SquadScreen);assert_fits(self,self.win)
        old_xi=self.c.view.eleven
        off=next(w for w in old_xi if self.c.view.can_mark(w))
        on=next(w for w in self.c.view.bench if self.c.view.can_mark(w) and self.c.view.record(w)[6]<13)
        self.pick(s,off);self.key(Qt.Key.Key_Return);self.pick(s,on);self.key(Qt.Key.Key_Return);self.settled()
        self.assertIn(on,self.c.view.eleven);self.assertNotIn(on,old_xi)
        self.pick(s,on);self.key(Qt.Key.Key_R);self.settled()
        position=self.c.view.record(on)[6]
        self.assertEqual(s.card.card['role'],roles.role(self.flow.model.state,position)[0])
        self.key(Qt.Key.Key_Escape);self.key(Qt.Key.Key_Escape);self.key(Qt.Key.Key_Return)
        captain=self.win.current();self.assertIsInstance(captain,ChooseScreen)
        self.assertEqual(tuple(captain.eleven),self.c.view.eleven);assert_fits(self,self.win)
        for _ in range(11):
            if captain.highlighted()==on:break
            self.key(Qt.Key.Key_Down)
        self.assertEqual(captain.highlighted(),on)
        self.assertEqual(captain.cards[captain.index]['role'],roles.role(self.flow.model.state,position)[0])
        self.key(Qt.Key.Key_Return);self.settled();self.assertEqual(self.native.status,'handed_off')
        self.assertEqual(len(self.handoffs),1);connection,prefs=self.handoffs[0]
        self.assertIs(connection.replies,self.native.replies);self.assertTrue(connection.packet['events'])
        self.assertIs(self.native.shared.match,self.native);self.flow.close()
        self.assertEqual(self.closed,[]);self.assertFalse(self.native.disposed)
        self.assertEqual(canonical_hash(self.native.boundary_state),before)
        self.assertEqual(self.owner.state,self.before);self.owner.confirm.assert_not_called()
        with self.assertRaises(ValueError):self.native.handoff()

    def test_window_close_while_edit_pending_retires_without_a_surviving_event_loop(self):
        self.key(Qt.Key.Key_Space);self.flow.timer.stop();self.key(Qt.Key.Key_R)
        self.assertTrue(self.c.pending);self.win.leaving=True;self.win.close()
        self.assertEqual(self.closed,[True]);self.assertEqual(self.native.status,'closing')
        # Intentionally no QApplication.processEvents or flow/native poll here.
        self.until(lambda:self.native.disposed,limit=15)
        self.assertEqual(self.native.status,'closed');self.assertIsNone(self.native.shared.match)
        self.assertFalse(self.native.shared.engine.season_active)
        self.assertEqual(self.owner.state,self.before)


if __name__=='__main__':unittest.main()
