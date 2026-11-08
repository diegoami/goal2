"""[designed: owner #599] UI packets isolate input/refresh; actual engine edits are T188a's proof."""
import copy
import unittest
from types import SimpleNamespace
from goal2.tests import requires

@requires.need(modules=('PySide6','pygame'),**requires.HALFTIME)
class ImmediateBench(unittest.TestCase):
    def setUp(self):
        from goal2.tests.test_ui_replay_t181 import ReplayScreens
        from goal2.ui.s19_bench import BenchAnswer
        ReplayScreens.setUp(self)
        words=self.model.state.managed_squad
        self.off,self.on=words[1],words[12]
        self.decision=SimpleNamespace(minute=45,score=[0,0],data=dict(context='half_time',
            eleven=words[:11],bench=words[11:],substitutions_now=True,substitutions_left=5,
            injured=[self.off],positions=[[w,self.model.state.players[w][6]] for w in words]))
        self.controller.stop=self.decision
        self.pitch.held=self.decision
        self.day.bench=BenchAnswer(self.model,self.decision)
        self.sent=[]
        self.bridge.reports=[]
        self.bridge.answer=lambda token,pairs,changes=None:self.sent.append((copy.deepcopy(pairs),copy.deepcopy(changes)))
        self.bench=self.day.open_bench()
        self.app.processEvents()

    def pair(self):
        from PySide6.QtCore import Qt
        from PySide6.QtTest import QTest
        for word in (self.off,self.on):
            self.bench.row=self.bench.answer.words().index(word)
            self.bench.refresh()
            QTest.keyClick(self.window,Qt.Key.Key_Return)
            self.app.processEvents()

    def deliver(self,refused=False,reason="player cannot return"):
        data=copy.deepcopy(self.decision.data)
        data['edited']=True
        if not refused:
            data['eleven']=[self.on if w==self.off else w for w in data['eleven']]
            data['bench']=[self.off if w==self.on else w for w in data['bench']]
            data['substitutions_left']=4
            data['injured']=[]
        report=dict(context='half_time',asked=[[self.off,self.on]],made=[] if refused else [[self.off,self.on]],
            requested=[],refused=[[self.off,self.on,reason]] if refused else [],
            substitutions_left=data['substitutions_left'])
        self.bridge.reports.append(report)
        self.controller.stop=SimpleNamespace(data=data,minute=45,score=[0,0])
        self.pitch.tick()
        self.app.processEvents()

    def test_second_selection_sends_one_edit_and_repeated_input_cannot_repeat_it(self):
        from PySide6.QtCore import Qt
        from PySide6.QtTest import QTest
        self.pair()
        self.assertEqual(self.sent,[([[self.off,self.on]],{'edit_only':True})])
        self.assertTrue(self.bench.pending)
        self.assertIn(self.off,self.bench.answer.eleven,'do not guess acceptance before the engine answers')
        QTest.keyClick(self.window,Qt.Key.Key_Return)
        QTest.keyClick(self.window,Qt.Key.Key_Escape)
        self.assertIs(self.window.current(),self.bench)
        self.assertEqual(len(self.sent),1)

    def test_actual_roster_and_budget_refresh_before_play_without_a_second_command(self):
        self.pair();self.deliver()
        self.assertIs(self.window.current(),self.bench)
        self.assertFalse(self.bench.pending)
        self.assertIn(self.on,self.bench.answer.eleven)
        self.assertIn(self.off,self.bench.answer.bench)
        self.assertEqual(self.bench.answer.left,4)
        self.assertEqual(self.bench.answer.chosen,[])
        self.assertIn('Made:',self.bench.note.text())
        self.assertEqual(len(self.sent),1)
        self.day.play(SimpleNamespace(phase='half'))
        self.assertEqual(self.sent,[([[self.off,self.on]],{'edit_only':True}),([],None)])

    def test_refused_pair_stays_at_the_legal_stop_and_continuation_is_available(self):
        self.pair();self.deliver(refused=True)
        self.assertIs(self.window.current(),self.bench)
        self.assertFalse(self.bench.pending)
        self.assertIn(self.off,self.bench.answer.eleven)
        self.assertEqual(self.bench.answer.left,5)
        self.assertIsNone(self.controller.refusal,'do not deadlock the refreshed stopped decision')
        self.assertIn('Not made:',self.bench.note.text())
        self.assertIn('player cannot return',self.bench.note.text())
        self.day.play(SimpleNamespace(phase='half'))
        self.assertEqual(self.sent[-1],([],None))

    def test_ordinary_pause_cannot_queue_a_pair_but_preserves_tactical_changes(self):
        from goal2.ui.s19_bench import BenchAnswer
        decision=copy.deepcopy(self.decision)
        decision.data.update(context='pause',substitutions_now=False)
        self.day.bench=BenchAnswer(self.model,decision)
        self.window.pop();self.bench=self.day.open_bench()
        self.pair()
        self.assertEqual(self.sent,[])
        self.assertEqual(self.bench.answer.chosen,[])
        self.bench.answer.reposition(self.off)
        self.assertIn('positions',self.bench.answer.value())

    def test_injured_withdrawn_player_keeps_the_actual_match_injury_marker(self):
        self.pair();self.deliver()
        self.assertIn(self.off,self.bench.answer.injured)
        self.assertEqual(len(self.sent),1)

    def test_returning_from_a_plain_pause_clears_obsolete_bench_requested_note(self):
        from goal2.ui.s17_pitch import REQUESTED
        self.controller.note=REQUESTED
        self.controller.answer_stop([])
        self.assertNotEqual(self.controller.note,REQUESTED)

    def test_reopening_and_playing_do_not_resubmit_the_applied_pair(self):
        self.pair();self.deliver()
        self.bench.escape()
        self.bench=self.day.open_bench()
        self.assertEqual(self.bench.answer.chosen,[])
        self.assertEqual(len(self.sent),1)
        self.day.play(SimpleNamespace(phase='half'))
        self.assertEqual(self.sent[-1],([],None))

    def test_clicked_pair_uses_the_same_consumed_once_path(self):
        self.bench.row=self.bench.answer.words().index(self.off)
        self.bench.click_row(self.bench.row)
        index=self.bench.answer.words().index(self.on)
        self.bench.click_row(index)
        self.bench.click_row(index)
        self.assertEqual(self.sent,[([[self.off,self.on]],{'edit_only':True})])
        self.bench.click_row(index)
        self.assertEqual(len(self.sent),1)

    def test_confirmed_tactical_byte_is_displayed_without_resubmitting_it_on_play(self):
        self.pair()
        confirmed=self.model.state.players[self.off][15]^0x11
        self.controller.events.append(dict(kind='player_tactics',minute=45,score=[0,0],
            data=dict(player=self.off,own_set=confirmed,marking=0)))
        self.deliver()
        self.assertEqual(self.bench.answer.record(self.off)[15],confirmed)
        self.assertEqual(self.bench.answer.mark_text(self.off),'nobody')
        self.assertEqual(self.bench.answer.value(),[])
        self.day.play(SimpleNamespace(phase='half'))
        self.assertEqual(self.sent[-1],([],None))

    def test_new_accepted_tactics_override_an_earlier_confirmed_cache(self):
        self.day.bench.live_own[self.off]=11
        self.day.bench.live_marking[self.off]=123
        self.controller.events.append(dict(kind='player_tactics',minute=45,score=[0,0],
            data=dict(player=self.off,own_set=22,marking=0)))
        self.day.edited(self.pitch,self.decision,None)
        self.assertEqual(self.day.bench.record(self.off)[15],22)
        self.assertEqual(self.day.bench.mark_text(self.off),'nobody')

    def test_match_menu_uses_the_confirmed_eleven_and_live_injury_label(self):
        from goal2.ui.s15_match_menu import MenuScreen
        menu=MenuScreen(self.window,self.day,'half')
        _,rows=menu.lineups[self.model.state.managed_country]
        self.assertTrue(any('INJURED' in name for _,name in rows))
        self.pair();self.deliver()
        menu=MenuScreen(self.window,self.day,'half')
        _,rows=menu.lineups[self.model.state.managed_country]
        from goal2.ui.squad_card import full_name
        self.assertTrue(any(full_name(self.model,self.on)==name for _,name in rows))
        self.assertFalse(any(full_name(self.model,self.off) in name for _,name in rows))

    def test_a_dropped_bench_opening_clears_its_stale_requested_note(self):
        from goal2.ui.s17_pitch import REQUESTED
        import time
        self.controller.note=REQUESTED
        self.bridge.dropped_pauses=1
        self.controller.tick(time.monotonic())
        self.assertNotEqual(self.controller.note,REQUESTED)
        self.assertEqual(self.sent,[])

    def test_long_refusal_keeps_all_twenty_players_details_and_controls_visible(self):
        from goal2.desktop import fixed_page
        reason=('This player has already been substituted and cannot return; '
                'choose a different player from the bench before continuing.')
        self.pair();self.deliver(refused=True,reason=reason)
        self.assertIn(reason,self.bench.note.text())
        self.assertEqual(self.bench.answer.left,5)
        for width,height in ((1440,900),(2110,1213)):
            self.window.resize(width,height)
            for _ in range(3):self.app.processEvents()
            self.assertEqual(fixed_page.problems(self.window),[],(width,height))
            self.assertEqual(len(self.bench.strip.shown_texts()),20)


@requires.need(modules=('PySide6','pygame','unicorn'),slow=True,**requires.HALFTIME)
class ActualImmediateBench(unittest.TestCase):
    def test_injury_and_captain_swaps_are_visible_before_play_and_publish_once(self):
        import tempfile
        from pathlib import Path
        from PySide6.QtCore import Qt
        from goal2.desktop import data_setup,fixed_page
        from goal2.ui.window import Window
        from goal2.tests.test_ui_bench_t180 import (Walk,app,career,key,enter_on,play_on,PLAY_NEXT)
        from goal2.tests.match_day_policy import play_through_bridge
        from goal2.ui.s17_pitch import engine_fixture
        from goal2.tests.test_pypy_worker_t152 import pypy
        pypy();application=app();test=self
        from goal2.tests.live_card_assertions_619 import verify_bench, verify_choose, report
        card_receipts=[]
        class ActualWalk(Walk):
            def react(self,screen):
                if type(screen).__name__=='ChooseScreen' and screen.mode!='captain':
                    verify_choose(test,screen,self.model,self.out['controller'].stop.data,card_receipts)
                if type(screen).__name__=='ChooseScreen' and screen.mode=='captain':
                    self.out['initial_captain']=screen.highlighted()
                    self.out['captain_off']=False
                return super().react(screen)
            def on_menu(self,screen):
                if screen.phase=='stop' and not self.out.get('injury_done'):
                    key(self.window,Qt.Key.Key_Space)
                else:play_on(self.window,screen)
            def on_board(self,screen):
                if screen.phase=='half' and not self.out.get('half_done'):
                    key(self.window,Qt.Key.Key_Escape)
                else:super().on_board(screen)
            def on_bench(self,screen):
                verify_bench(test,screen,self.out['controller'],card_receipts,'before-stop')
                answer=screen.answer;context=answer.context
                target=None
                if context=='substitution' and not self.out.get('injury_done'):
                    target=next(w for w in answer.eleven if w in answer.injured)
                elif context=='half_time' and not self.out.get('half_done'):
                    target=(self.out['initial_captain'] if not self.out['captain_off'] else
                            next(w for w in answer.eleven if w not in answer.injured
                                 and w not in self.out.get('put_on',[])))
                if target is not None:
                    controller=self.out['controller']
                    before_left=answer.left;before_minute=answer.minute
                    before_sequence=controller.bridge._frame_sequence
                    used=set(self.out.get('taken_off',[]))
                    on=next(w for w in answer.bench if w not in used and
                            (answer.position(w)==0)==(answer.position(target)==0))
                    enter_on(self.window,screen,target);enter_on(self.window,screen,on)
                    fresh=screen.answer
                    test.assertIn(on,fresh.eleven);test.assertIn(target,fresh.bench)
                    test.assertEqual(fresh.left,before_left-1)
                    test.assertEqual(fresh.minute,before_minute)
                    test.assertEqual(controller.bridge._frame_sequence,before_sequence)
                    test.assertEqual(fresh.chosen,[])
                    test.assertTrue(controller.stop.data.get('edited'))
                    test.assertIn('Made:',screen.note.text())
                    verify_bench(test,screen,controller,card_receipts,'after-swap')
                    test.assertEqual(fixed_page.problems(self.window),[])
                    self.out.setdefault('pairs',[]).append([target,on])
                    self.out.setdefault('put_on',[]).append(on)
                    self.out.setdefault('taken_off',[]).append(target)
                    self.out['captain_off'] |= target==self.out['initial_captain']
                    self.out['injury_done' if context=='substitution' else 'half_done']=True
                key(self.window,Qt.Key.Key_Escape)
        with tempfile.TemporaryDirectory() as folder:
            owner=career();count=owner.state.match_count
            window=Window(data_setup.paths(Path(folder)))
            window.resize(1440,900);window.show()
            desk=window.open_career(owner)
            walk=ActualWalk('T188-injury-captain',window,owner)
            fixture=owner.state.campaign.next_fixture
            try:
                desk.highlight(PLAY_NEXT);key(window,Qt.Key.Key_Return)
                walk.run()
                self.assertTrue(walk.out.get('injury_done'))
                self.assertTrue(walk.out.get('half_done'))
                self.assertTrue(walk.out['captain_off'])
                controller=walk.out['controller']
                self.assertIsNone(controller.error)
                self.assertEqual(owner.state.match_count,count+1)
                self.assertEqual([p for r in controller.reports for p in r['made']],walk.out['pairs'])
                self.assertTrue(all(not r['requested'] for r in controller.reports))
                other=career();other.state=copy.deepcopy(controller.given._snapshot)
                result=play_through_bridge(other,controller.choices,fixture=engine_fixture(fixture),wait=1500)
                self.assertEqual(controller.outcome.result,result.result)
                self.assertEqual(controller.outcome.memory,result.memory)
                self.assertEqual(controller.outcome.events,result.events)
                self.assertEqual(owner.state,other.state)
                report(self,card_receipts,'injury-captain-swaps')
            finally:
                window.close();window.deleteLater();application.processEvents()

if __name__=='__main__':unittest.main()
