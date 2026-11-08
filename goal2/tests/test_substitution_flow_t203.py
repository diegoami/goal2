"""[designed: owner #662/T203] Exact player-list request and opportunity flow."""
import copy
import unittest
from types import SimpleNamespace
from goal2.tests import requires

@requires.need(modules=('PySide6','pygame'),**requires.HALFTIME)
class Flow(unittest.TestCase):
    def setUp(self):
        from goal2.tests.test_substitution_ui_636 import RequestUI
        RequestUI.setUp(self)
    def key(self,value):
        from goal2.tests.test_substitution_ui_636 import RequestUI
        RequestUI.key(self,value)
    def acknowledge(self,desired):
        from goal2.tests.test_substitution_ui_636 import RequestUI
        RequestUI.acknowledge(self,desired)
    def test_ordinary_pause_opens_own_bench_without_inventing_request_or_permission(self):
        while self.window.current() is not self.pitch:self.window.pop()
        self.day.stop(self.pitch,self.decision)
        self.assertEqual(type(self.window.current()).__name__,'BenchScreen')
        self.assertFalse(self.controller.substitution_requested)
        self.assertFalse(self.window.current().answer.takes_substitutions)
        self.assertEqual(self.sent,[])
    def test_explicit_button_and_player_enter_share_true_false_true_with_no_pairs(self):
        from PySide6.QtCore import Qt
        for desired,use_button in ((True,False),(False,True),(True,True)):
            if use_button:self.screen.request_button.click()
            else:self.key(Qt.Key.Key_Return)
            self.assertEqual(self.sent[-1],([] ,{'request_substitution':desired,'edit_only':True}))
            self.assertTrue(self.screen.pending)
            self.assertEqual(self.screen.answer.chosen,[])
            self.acknowledge(desired)
            self.assertEqual(self.screen.answer.substitution_requested,desired)
            self.assertFalse(self.screen.pending)

    def test_both_opportunity_accept_keys_open_a_legal_bench(self):
        from PySide6.QtCore import Qt
        for accepting in (Qt.Key.Key_Escape,Qt.Key.Key_Return):
            while self.window.current() is not self.pitch:self.window.pop()
            data=copy.deepcopy(self.decision.data)
            data.update(context='substitution_opportunity',substitutions_now=True,keeper_unavailable=False,timeout_polls=400,poll_ms=10)
            decision=SimpleNamespace(data=data,minute=30,score=[0,0])
            self.bridge.waiting=None;self.controller.stop=decision;self.pitch.held=decision
            self.day.stop(self.pitch,decision);self.key(accepting)
            self.assertEqual(self.sent[-1],([] ,{'opportunity':'accept'}))
            data.update(context='substitution')
            for field in ('keeper_unavailable','timeout_polls','poll_ms'):data.pop(field,None)
            self.bridge.waiting=SimpleNamespace(data=data,minute=30,score=[0,0])
            self.pitch.tick();self.app.processEvents()
            self.assertEqual(type(self.window.current()).__name__,'BenchScreen')
            self.assertTrue(self.window.current().answer.takes_substitutions)
    def test_request_button_and_full_cue_fit_three_sizes(self):
        for width,height in ((1440,900),(1800,1125),(2110,1213)):
            self.window.resize(width,height);self.app.processEvents();self.screen.refresh()
            button=self.screen.request_button
            self.assertTrue(button.isVisible())
            self.assertGreaterEqual(button.width(),button.fontMetrics().horizontalAdvance(button.text())+12)
            cue=self.screen.mode_label
            self.assertLessEqual(cue.fontMetrics().horizontalAdvance(cue.text()),cue.contentsRect().width()+1)

@requires.need(modules=('PySide6','pygame'),**requires.HALFTIME)
class Acknowledgement(unittest.TestCase):
    def setUp(self):
        from goal2.tests.test_immediate_bench_t188 import ImmediateBench
        from goal2.ui.s15_match_menu import MenuScreen
        from goal2.ui.s19_bench import BenchAnswer
        ImmediateBench.setUp(self)
        self.window.pop()
        self.decision.data.update(context='substitution',request_substitution=True)
        self.day.bench=BenchAnswer(self.model,self.decision)
        self.menu=self.window.push(MenuScreen(self.window,self.day,'stop'))
        self.bench=self.day.open_bench()
    def pair(self):
        from goal2.tests.test_immediate_bench_t188 import ImmediateBench
        ImmediateBench.pair(self)
    def deliver(self,refused=False):
        data=copy.deepcopy(self.decision.data);data['edited']=True
        if not refused:
            data['eleven']=[self.on if w==self.off else w for w in data['eleven']]
            data['bench']=[self.off if w==self.on else w for w in data['bench']]
            data['substitutions_left']-=1
        report=dict(context='substitution',asked=[[self.off,self.on]],made=[] if refused else [[self.off,self.on]],
                    requested=[],refused=[[self.off,self.on,'refused']] if refused else [],substitutions_left=data['substitutions_left'])
        self.bridge.reports.append(report)
        self.controller.stop=SimpleNamespace(data=data,minute=45,score=[0,0]);self.pitch.tick();self.app.processEvents()
    def test_confirmed_swap_clears_opportunity_but_keeps_guest_permission_and_refreshes_menu(self):
        from PySide6.QtCore import Qt
        from goal2.tests.test_ui_bench_t180 import key
        before=copy.deepcopy(self.menu.lineups[self.model.state.managed_country])
        self.pair();self.deliver()
        self.assertTrue(self.bench.answer.takes_substitutions)
        self.assertNotIn('MAKE SUBSTITUTIONS NOW',self.bench.mode_label.text())
        self.assertFalse(self.bench.cue_timer.isActive())
        key(self.window,Qt.Key.Key_Escape)
        self.assertIs(self.window.current(),self.menu)
        self.assertNotEqual(self.menu.lineups[self.model.state.managed_country],before)
        self.assertNotIn('SUBSTITUTION OPPORTUNITY',self.menu.situation.text())
    def test_returned_menu_shows_the_acknowledged_current_xi(self):
        before=copy.deepcopy(self.menu.lineups[self.model.state.managed_country])
        self.pair();self.deliver();self.window.pop();self.app.processEvents()
        self.assertNotEqual(self.menu.lineups[self.model.state.managed_country],before)

    def test_refusal_or_pending_edit_does_not_clear_an_offered_opportunity(self):
        self.pair()
        self.assertTrue(self.bench.answer.opportunity_visible)
        self.deliver(refused=True)
        self.assertTrue(self.bench.answer.opportunity_visible)
        self.assertTrue(self.bench.answer.takes_substitutions)

@requires.need(modules=('PySide6','pygame'),slow=True,**requires.HALFTIME)
class ActualOwnerFlow(unittest.TestCase):
    def test_exact_owner_keys_request_cancel_natural_opportunity_swap_and_half_time(self):
        from goal2.tests.test_substitution_actual_636 import run_journey
        run_journey(self,'accept',owner_flow=True)

if __name__=='__main__':unittest.main()
