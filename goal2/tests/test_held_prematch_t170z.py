"""[designed: T170z/#776] Real widgets, one actual retained PyPy season pipe.

Private original reference is loaded locally, never embedded. Fixture kind below
is presentation-only; native sides/records/edits come from the retained worker.
"""
import copy
import tempfile
import time
import unittest
from pathlib import Path
from types import SimpleNamespace

from goal2.tests import requires
requires.require(modules=('PySide6',))
from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication
from goal2.data.goaldat import load
from goal2.desktop import data_setup
from goal2.desktop.model import DesktopModel
from goal2.game.prematch_controller import PrematchController
from goal2.game.season import canonical_hash
from goal2.tests.test_prematch_preview_t170s import reference_raw
from goal2.tests.test_prematch_marking_t170w import initial_state
from goal2.tests import test_season_worker_t170o as wire
from goal2.ui import theme
from goal2.ui.window import Window
from goal2.ui.screen import Screen
from goal2.ui.held_prematch import HeldPrematchFlow
from goal2.ui.s08_squad import SquadScreen
from goal2.ui.s09_player_tactics import PlayerTacticsScreen
from goal2.ui.s10_team_tactics import TeamTacticsScreen, LINES
from goal2.ui.s15_match_menu import MenuScreen
from goal2.ui.s16_choose import ChooseScreen

ROOT=Path(__file__).resolve().parents[2]


@requires.need(files=('GOAL.DAT',))
class WindowPipe(unittest.TestCase):
    make_engine=wire.Pipe.make_engine
    receive=wire.Pipe.receive

    @classmethod
    def setUpClass(cls):
        cls.app=QApplication.instance() or QApplication([])
        theme.install(cls.app)

    def setUp(self):
        raw=reference_raw();native,self.bad,_=initial_state(raw,unavailable=True)
        self.engine=self.make_engine();self.engine.season_open(native)
        self.receive('ready');self.receive('season')
        for action in ('advance','configure'):
            self.engine.season_request(action);reply=self.receive('season')
            if action=='advance':self.boundary_hash=canonical_hash(reply['state'])
        while True:
            self.engine.season_request('next',count=32);p=self.receive('season')
            if p['decision'] is not None:break
        data=next(e['data'] for e in reversed(p['events']) if e['kind']=='decision')
        self.engine.season_request('preview',decision=p['decision']);preview=self.receive('season')
        self.sent=[]
        def send(action,**values):
            self.sent.append((action,copy.deepcopy(values)));self.engine.season_request(action,**values)
        self.c=PrematchController(send,7);self.c.attach(preview,data,decision=p['decision'])
        self.tmp=tempfile.TemporaryDirectory(prefix='goal2-t170z-');self.addCleanup(self.tmp.cleanup)
        self.owner=DesktopModel(load((ROOT/'.cache/GOAL.DAT').read_bytes()),raw,Path(self.tmp.name)/'save')
        self.owner.state=self.c.view.display_state();self.before=copy.deepcopy(self.owner.state)
        self.win=Window(data_setup.paths(Path(self.tmp.name)/'data'));self.win.show()
        self.win.push(Screen(self.win));self.pid=self.engine.pid;self.calls=[];self.handoffs=[]
        def route(name,*args):
            self.calls.append(name);self.win.push(Screen(self.win))
        self.flow=HeldPrematchFlow(self.win,self.owner,self.c,
            SimpleNamespace(side_a=self.c.view.sides[0],side_b=self.c.view.sides[1],kind=1,stage=2),self.replies,
            on_handoff=lambda *v:self.handoffs.append(v),on_close=lambda f:self.calls.append('close'),
            on_tournament=lambda f:route('tournament'),on_stats=lambda f,m:route('stats'),watch=True)
        self.flow.open();self.app.processEvents()
        self.addCleanup(self.cleanup_window)

    def cleanup_window(self):
        self.flow.close();self.win.leaving=True;self.win.close();self.win.deleteLater();self.app.processEvents()

    def key(self,key,mod=Qt.KeyboardModifier.NoModifier):
        QTest.keyClick(self.win,key,mod);self.app.processEvents()

    def settle(self):
        end=time.monotonic()+120
        while self.c.pending and time.monotonic()<end:
            self.flow.poll();self.app.processEvents();QTest.qWait(2)
        self.flow.poll()
        self.assertFalse(self.c.pending);self.assertIn(self.c.status,('ready','handoff'),self.c.message)
        self.assertEqual(self.engine.pid,self.pid)

    def assert_boundary(self):
        self.engine.season_request('observe');packet=self.receive('season')
        self.assertEqual(canonical_hash(packet['state']),self.boundary_hash)
        self.assertEqual(self.owner.state.players,self.before.players)
        self.assertEqual(self.owner.state.countries,self.before.countries)
        self.assertEqual(self.owner.state.campaign,self.before.campaign)

    def squad(self):
        self.key(Qt.Key.Key_Space);self.assertIsInstance(self.win.current(),SquadScreen)
        return self.win.current()

    def pick(self,s,w,side='squad'):
        s.show_side(side);s.cursor[side]=next(i for i,r in enumerate(s.rows()) if r['id']==w);s.refresh()

    def test_squad_pool_positions_identity_and_native_sorting(self):
        s=self.squad();view=self.c.view
        a=next(w for w in view.eleven if view.can_mark(w));b=next(w for w in view.bench if view.can_mark(w))
        self.pick(s,a);self.key(Qt.Key.Key_Return);self.pick(s,b);self.key(Qt.Key.Key_Return)
        self.assertIs(self.c.view,view);sent=len(self.sent)
        self.key(Qt.Key.Key_Return);self.assertEqual(len(self.sent),sent)
        self.settle();self.assertIn(b,self.c.view.eleven);self.assertIn(a,self.c.view.bench)
        self.assertEqual(s.current(),b)
        for _ in range(2):
            off=next(w for w in self.c.view.bench if self.c.view.can_mark(w))
            on=next(w for w in self.c.view.pool if w and self.c.view.available(w) and self.c.view.record(w)[6]>=2)
            # Both pick orders use words even through a name filter.
            order=((off,'squad'),(on,'pool')) if _==0 else ((on,'pool'),(off,'squad'))
            for w,pane in order:
                s.query=self.flow.model.goaldat.player_names[on] if pane=='pool' else ''
                self.pick(s,w,pane);self.key(Qt.Key.Key_Return)
            self.settle();self.assertIn(on,self.c.view.squad);self.assertIn(off,self.c.view.pool)
        self.pick(s,on);position=self.c.view.record(on)[6]
        self.key(Qt.Key.Key_R);self.settle();self.assertEqual(self.c.view.record(on)[6],(position+1)%14)
        self.assertEqual(s.current(),on)
        self.key(Qt.Key.Key_R,Qt.KeyboardModifier.ShiftModifier);self.settle()
        self.assertEqual(self.c.view.record(on)[6],position)
        self.key(Qt.Key.Key_C);self.settle();self.assertEqual(self.c.view.record(on)[6],self.c.view.record(on)[7])
        self.key(Qt.Key.Key_F2);self.assertTrue(s.editing)
        s.card.name_line.edit.setText('Renamed');self.key(Qt.Key.Key_Return)
        self.assertEqual(self.owner.state.player_renames[on],'Renamed')
        self.key(Qt.Key.Key_F2);s.card.name_line.edit.setText('Ångström');self.key(Qt.Key.Key_Return)
        self.assertEqual(self.owner.state.player_renames[on],'Ångström')
        self.key(Qt.Key.Key_F2);s.card.name_line.edit.setText('😀');self.key(Qt.Key.Key_Return)
        self.assertTrue(s.editing);self.assertEqual(self.owner.state.player_renames[on],'Ångström')
        self.key(Qt.Key.Key_Escape)
        self.key(Qt.Key.Key_F2);s.card.name_line.edit.setText('Cancelled');self.key(Qt.Key.Key_Escape)
        self.assertEqual(self.owner.state.player_renames[on],'Ångström')
        self.key(Qt.Key.Key_A);self.assertIn('Held-match',s.message)
        self.key(Qt.Key.Key_F1);self.assertIsNot(self.win.current(),s)
        self.key(Qt.Key.Key_Escape);self.assertIs(self.win.current(),s)
        self.key(Qt.Key.Key_Escape);self.assertIsInstance(self.win.current(),MenuScreen)
        self.assertEqual(self.win.current().lineup_words[7],list(self.c.view.eleven))
        self.assertEqual(self.owner.state.players,self.before.players)
        self.assertEqual(self.owner.state.countries,self.before.countries)
        self.assertEqual((self.owner.state.rng_seed_7b62,self.owner.state.rng_seed_8336),
                         (self.before.rng_seed_7b62,self.before.rng_seed_8336))
        self.assert_boundary()

    def test_player_tactics_bench_pool_keeper_and_pure_refusal(self):
        s=self.squad();bench=next(w for w in self.c.view.bench if self.c.view.can_mark(w))
        self.pick(s,bench);self.key(Qt.Key.Key_T);p=self.win.current();self.assertIsInstance(p,PlayerTacticsScreen)
        self.assertEqual(len(p.rows),5)
        # This original reference starts this bench player's positioning at own true.
        self.assertIs(self.c.view.own_override(bench,1),True)
        for goal in (None,False,True,None):
            self.key(Qt.Key.Key_Return);self.settle();self.assertIs(self.c.view.own_override(bench,1),goal,
                (self.c.message,self.sent,p.word,p.line,self.c.view.record(bench).hex()))
        p.choose(4)
        self.assertIsNone(self.c.view.marking_goal(bench))
        self.key(Qt.Key.Key_Return);self.settle();self.assertEqual(self.c.view.marking_goal(bench),0)
        self.key(Qt.Key.Key_Return);self.settle();self.assertEqual(self.c.view.marking_goal(bench),self.c.view.marking_targets[0])
        for goal in (*self.c.view.marking_targets[1:],None):
            self.key(Qt.Key.Key_Return);self.settle();self.assertEqual(self.c.view.marking_goal(bench),goal)
        old=self.c.view;self.c.set_marking(bench,65535);self.settle()
        self.assertIs(self.c.view,old);self.assertIn('target',self.c.message)
        self.c.set_marking(bench,None);self.settle();self.assertIsNone(self.c.view.marking_goal(bench))
        self.key(Qt.Key.Key_Escape)
        keeper=next(w for w in self.c.view.squad if self.c.view.record(w)[6]<2)
        for w,side in ((keeper,'squad'),(self.bad,'squad'),(next(w for w in self.c.view.pool if w),'pool')):
            self.pick(s,w,side);self.key(Qt.Key.Key_T);p=self.win.current()
            self.assertIsInstance(p,PlayerTacticsScreen);self.assertEqual(len(p.rows),4)
            self.key(Qt.Key.Key_Escape)
        self.assert_boundary()

    def test_pool_search_position_filter_and_pool_edits(self):
        s=self.squad();self.key(Qt.Key.Key_Slash);self.assertEqual(s.side,'pool');self.assertTrue(s.searching)
        count=len(self.sent);QTest.keyClicks(self.win,'zzzz');self.app.processEvents()
        self.assertEqual(s.rows(),[]);self.key(Qt.Key.Key_Backspace);self.assertEqual(s.query,'zzz')
        self.key(Qt.Key.Key_Escape);self.assertFalse(s.searching);self.assertEqual(s.query,'')
        self.key(Qt.Key.Key_P);self.assertEqual(s.position,0)
        self.assertTrue(all(self.c.view.record(r['id'])[6]==0 for r in s.rows()))
        self.key(Qt.Key.Key_P,Qt.KeyboardModifier.ShiftModifier);self.assertIsNone(s.position)
        self.assertEqual(len(self.sent),count)
        w=next(w for w in self.c.view.pool if w and self.c.view.available(w));self.pick(s,w,'pool')
        old=self.c.view.record(w)[6];self.key(Qt.Key.Key_R);self.settle()
        self.assertEqual(self.c.view.record(w)[6],(old+1)%14)
        self.key(Qt.Key.Key_C);self.settle();self.assertEqual(self.c.view.record(w)[6],self.c.view.record(w)[7])
        self.key(Qt.Key.Key_T);p=self.win.current();self.assertFalse(p.marks)
        before=self.c.view.own_override(w,1)
        expected=False if before is None else True if before is False else None
        self.key(Qt.Key.Key_Return);self.settle();self.assertIs(self.c.view.own_override(w,1),expected)
        self.key(Qt.Key.Key_Escape);self.assertEqual(s.current(),w);self.assert_boundary()

    def test_pending_sort_while_help_and_close_before_reply(self):
        s=self.squad();w=next(w for w in self.c.view.squad if self.c.view.record(w)[6]>=2)
        self.pick(s,w);self.key(Qt.Key.Key_R);old=self.c.view;count=len(self.sent)
        self.key(Qt.Key.Key_R);self.assertEqual(len(self.sent),count);self.assertIs(self.c.view,old)
        self.key(Qt.Key.Key_F1);self.settle();self.key(Qt.Key.Key_Escape)
        self.assertIs(self.win.current(),s);self.assertEqual(s.current(),w)
        self.key(Qt.Key.Key_R);count=len(self.sent);self.flow.close();self.flow.close()
        self.app.processEvents();self.flow.poll()
        self.assertEqual(self.c.status,'detached');self.assertEqual(len(self.sent),count)
        self.assertEqual(self.calls,['close'])

    def test_team_bits_readonly_opponent_callbacks_and_replay(self):
        menu=self.win.current();self.key(Qt.Key.Key_T);t=self.win.current();self.assertIsInstance(t,TeamTacticsScreen)
        for i,(_,element) in enumerate(LINES):
            t.choose(i);old=self.c.view;before=self.flow.model.team_tactics
            QTest.mouseClick(t.rows[i],Qt.MouseButton.LeftButton)
            self.assertTrue(t.pending);self.assertIs(self.c.view,old)
            self.key(Qt.Key.Key_F1);self.key(Qt.Key.Key_Escape)
            self.settle();self.assertFalse(t.pending)
            self.assertEqual(self.flow.model.team_tactics,before^(1<<(element-1)))
        self.key(Qt.Key.Key_Escape);menu=self.win.current()
        other=next(c for c in self.c.view.sides if c!=7);count=len(self.sent)
        menu.tactics(other);self.key(Qt.Key.Key_Escape);menu.players(other);self.key(Qt.Key.Key_Escape)
        self.assertEqual(len(self.sent),count)
        menu.tournament();self.key(Qt.Key.Key_Escape);menu.stats();self.key(Qt.Key.Key_Escape)
        self.assertEqual(self.calls,['tournament','stats'])
        self.key(Qt.Key.Key_Insert);self.assertTrue(self.flow.replay_auto)
        self.assertTrue(self.flow._settings()['automatic_action_replay'])
        self.assert_boundary()

    def test_native_invalid_xi_play_refusal_returns_to_menu(self):
        s=self.squad();keeper=next(w for w in self.c.view.eleven if self.c.view.record(w)[6]==0)
        bench=next(w for w in self.c.view.bench if self.c.view.can_mark(w))
        self.pick(s,keeper);self.key(Qt.Key.Key_Return);self.pick(s,bench);self.key(Qt.Key.Key_Return);self.settle()
        self.key(Qt.Key.Key_Escape);self.key(Qt.Key.Key_Escape);self.key(Qt.Key.Key_Return)
        self.assertIsInstance(self.win.current(),ChooseScreen)
        self.key(Qt.Key.Key_C);self.settle();self.assertEqual(self.c.status,'ready')
        self.assertIsInstance(self.win.current(),MenuScreen);self.assertTrue(self.flow.message)
        self.assertIn(self.flow.message,self.win.current().note.text())
        self.assertFalse(self.handoffs);self.assert_boundary()

    def test_captain_word_computer_timeout_and_handoff_once(self):
        # Each option gets a new actual retained session via subtests in separate methods below.
        self.captain('word')

    def test_captain_computer(self):self.captain('computer')

    def test_captain_timeout_and_watch(self):
        self.flow.watch=None
        # Declared UI question-policy control; native eligibility is tested in test_match_day.
        self.flow.asks_watch=lambda *a:True
        self.win.pop();self.flow.open();menu=self.win.current()
        menu.press_play();self.assertIs(self.win.current(),menu)
        self.key(Qt.Key.Key_Y);self.assertTrue(self.flow.watch)
        self.flow.watch=None;self.win.pop();self.flow.open()
        self.key(Qt.Key.Key_N);self.assertFalse(self.flow.watch)
        self.captain('timeout')

    def captain(self,mode):
        self.key(Qt.Key.Key_Return);p=self.win.current();self.assertIsInstance(p,ChooseScreen)
        expected=p.highlighted() if mode=='word' else None
        if mode=='word':self.key(Qt.Key.Key_Return)
        elif mode=='computer':self.key(Qt.Key.Key_C)
        else:p.timer.timeout.emit()
        self.settle();self.assertEqual(self.c.status,'handoff');self.assertEqual(len(self.handoffs),1)
        self.assertEqual(self.sent[0][1]['answer'],{'captain':expected})
        self.assertTrue(self.handoffs[0][1]['events']);p.no_key();self.flow.poll()
        self.assertEqual(len(self.handoffs),1);self.assertEqual(len([a for a,_ in self.sent if a=='answer']),1)
        self.flow.close();self.assertNotIn('close',self.calls);self.assertTrue(self.engine.season_active)
        self.assertEqual(self.owner.state,self.before)

    def test_loss_and_close_detach_late_replies(self):
        s=self.squad();self.key(Qt.Key.Key_R);count=len(self.sent)
        self.replies.put(('death',{'code':1}));self.flow.poll()
        self.assertEqual(self.c.status,'lost');self.key(Qt.Key.Key_R)
        self.assertEqual(len(self.sent),count);self.assertTrue(s.message)
        self.flow.close();self.flow.close();self.flow.poll()
        self.assertEqual(self.calls,['close']);self.assertEqual(self.c.status,'detached')

    def test_team_loss_releases_pending_ui_for_return(self):
        self.key(Qt.Key.Key_T);t=self.win.current();self.key(Qt.Key.Key_Return)
        self.assertTrue(t.pending);count=len(self.sent)
        self.replies.put(('death',{'code':1}));self.flow.poll()
        self.assertFalse(t.pending);self.assertTrue(t.message)
        self.key(Qt.Key.Key_Escape);self.assertIsInstance(self.win.current(),MenuScreen)
        self.assertEqual(len(self.sent),count)

    def test_captain_loss_under_help_stops_timeout(self):
        self.key(Qt.Key.Key_Return);p=self.win.current();self.key(Qt.Key.Key_F1)
        self.replies.put(('death',{'code':1}));self.flow.poll()
        self.assertTrue(p.done);self.assertFalse(p.timer.isActive())
        p.timer.timeout.emit();self.key(Qt.Key.Key_Escape);self.key(Qt.Key.Key_C)
        self.assertEqual(self.sent,[]);self.assertEqual(self.c.status,'lost')

    def test_send_failure_without_a_reply_releases_team_pending(self):
        from unittest.mock import Mock
        self.c._send=Mock(side_effect=BrokenPipeError('closed'))
        self.key(Qt.Key.Key_T);t=self.win.current();self.key(Qt.Key.Key_Return)
        self.flow.poll();self.assertEqual(self.c.status,'lost')
        self.assertFalse(t.pending);self.assertIn('BrokenPipeError',t.message)

    def test_window_close_invokes_owner_once(self):
        self.win.leaving=True;self.win.close();self.app.processEvents()
        self.assertTrue(self.flow.closed);self.assertEqual(self.c.status,'detached')
        self.assertEqual(self.calls,['close'])


if __name__=='__main__':unittest.main()
