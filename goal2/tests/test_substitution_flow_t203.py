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

@requires.need(modules=('PySide6','pygame'),slow=True,**requires.HALFTIME)
class ActualOwnerFlow(unittest.TestCase):
    def test_exact_owner_keys_request_cancel_natural_opportunity_swap_and_half_time(self):
        from goal2.tests.test_substitution_actual_636 import run_journey
        run_journey(self,'accept',owner_flow=True)

if __name__=='__main__':unittest.main()
