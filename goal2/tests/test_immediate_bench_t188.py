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

if __name__=='__main__':unittest.main()
