"""[designed: owner #636] Request acknowledgements and timed opportunity UI packets.
Actual natural-match/PyPy proof is a separate acceptance case, not simulated here.
"""
import copy
import unittest
from types import SimpleNamespace
from goal2.tests import requires

@requires.need(modules=('PySide6','pygame'), **requires.HALFTIME)
class RequestUI(unittest.TestCase):
    def setUp(self):
        from goal2.tests.test_live_team_tactics_610 import LiveTeamTactics
        LiveTeamTactics.setUp(self)
        LiveTeamTactics.prepare(self)
        self.decision.data['request_substitution'] = False
        self.controller.substitution_requested = False
        from goal2.ui.s19_bench import BenchAnswer
        self.day.bench = BenchAnswer(self.model, self.decision)
        self.screen = self.day.open_bench()
        self.app.processEvents()

    def key(self, value):
        from goal2.tests.test_live_team_tactics_610 import LiveTeamTactics
        LiveTeamTactics.key(self, value)

    def acknowledge(self, desired):
        data = copy.deepcopy(self.decision.data)
        data.update(edited=True, request_substitution=desired)
        self.decision = SimpleNamespace(data=data, minute=30, score=[0,0])
        self.bridge.waiting = self.decision
        self.pitch.tick();self.app.processEvents()

    def test_enter_requests_without_choosing_a_player_or_advancing(self):
        from PySide6.QtCore import Qt
        before = (self.screen.answer.minute, self.screen.answer.left, list(self.screen.answer.eleven))
        self.key(Qt.Key.Key_Return)
        self.assertEqual(self.sent, [([], {'request_substitution':True, 'edit_only':True})])
        self.assertTrue(self.screen.pending)
        self.assertEqual(self.screen.answer.chosen, [])
        self.key(Qt.Key.Key_Return)
        self.assertEqual(len(self.sent), 1)
        self.acknowledge(True)
        self.assertFalse(self.screen.pending)
        self.assertEqual((self.screen.answer.minute,self.screen.answer.left,self.screen.answer.eleven), before)
        self.assertIn('SUBSTITUTION REQUESTED', self.screen.mode_label.text())
        self.assertTrue(self.controller.substitution_requested)

    def test_cancel_preserves_false_and_personal_drafts_across_both_acknowledgements(self):
        from PySide6.QtCore import Qt
        answer = self.screen.answer;word = answer.eleven[2]
        answer.positions[word] = 3;answer.marking[word] = 0;answer.own[word] = 16
        saved = (dict(answer.positions),dict(answer.marking),dict(answer.own))
        self.key(Qt.Key.Key_Return);self.acknowledge(True)
        self.assertEqual((self.screen.answer.positions,self.screen.answer.marking,self.screen.answer.own),saved)
        self.key(Qt.Key.Key_Return)
        self.assertEqual(self.sent[-1], ([], {'request_substitution':False, 'edit_only':True}))
        self.acknowledge(False)
        self.assertFalse(self.controller.substitution_requested)
        self.assertEqual((self.screen.answer.positions,self.screen.answer.marking,self.screen.answer.own),saved)
        self.assertNotIn('SUBSTITUTION REQUESTED', self.screen.mode_label.text())

    def test_zero_budget_acknowledges_actual_false_without_inventing_acceptance(self):
        from PySide6.QtCore import Qt
        self.screen.answer.left = 0;self.decision.data['substitutions_left'] = 0
        self.key(Qt.Key.Key_Return);self.acknowledge(False)
        self.assertFalse(self.screen.pending)
        self.assertFalse(self.controller.substitution_requested)
        self.assertIn('no more substitutes', self.screen.line().lower())
        self.assertEqual(self.screen.answer.chosen, [])

    def test_opportunity_escape_opens_legal_bench_then_escape_leaves_a_play_menu(self):
        from PySide6.QtCore import Qt
        while self.window.current() is not self.pitch:self.window.pop()
        data = copy.deepcopy(self.decision.data)
        data.update(context='substitution_opportunity',keeper_unavailable=False,timeout_polls=400,poll_ms=10)
        decision=SimpleNamespace(data=data,minute=30,score=[0,0])
        self.controller.stop=decision;self.pitch.held=decision
        self.day.stop(self.pitch,decision)
        self.key(Qt.Key.Key_Escape)
        self.assertEqual(self.sent, [([], {'opportunity':'accept'})])
        self.assertIsNone(self.controller.stop)
        data.update(context='substitution',substitutions_now=True)
        for name in ('keeper_unavailable','timeout_polls','poll_ms'):data.pop(name,None)
        legal=SimpleNamespace(data=data,minute=30,score=[0,0])
        self.bridge.waiting=legal;self.pitch.tick();self.app.processEvents()
        self.assertEqual(type(self.window.current()).__name__,'BenchScreen')
        self.assertTrue(self.window.current().answer.takes_substitutions)
        self.key(Qt.Key.Key_Escape)
        self.assertEqual(type(self.window.current()).__name__,'MenuScreen')
        self.assertEqual(self.window.current().phase,'stop')
        self.day.play(self.window.current())
        self.assertIs(self.window.current(),self.pitch)
        self.assertIsNone(self.controller.stop)
        self.assertEqual(self.sent[-1],([],None))


@requires.need(modules=('PySide6','pygame'), **requires.HALFTIME)
class TimedOpportunity(unittest.TestCase):
    def setUp(self):
        from goal2.tests.test_ui_replay_t181 import ReplayScreens
        ReplayScreens.setUp(self)

    def show(self, keeper=False):
        data=dict(keeper_unavailable=keeper,timeout_polls=1000 if keeper else 400,poll_ms=10)
        self.responses=[]
        self.pitch.stop_box.show_opportunity(data,self.responses.append)
        self.app.processEvents()

    def test_timer_metadata_blink_colours_and_exactly_once_timeout(self):
        from PySide6.QtGui import QColor
        self.show()
        box=self.pitch.stop_box
        self.assertEqual(box.opportunity_timer.interval(),4000)
        self.assertTrue(box.open)
        self.assertIn('#aaaaaa',box.styleSheet().lower())
        self.assertEqual(box.headline.palette().color(box.headline.foregroundRole()),QColor('#000000'))
        self.assertEqual(box.key_hint.palette().color(box.key_hint.foregroundRole()),QColor('#ff55ff'))
        box._blink_opportunity()
        self.assertEqual(box.headline.palette().color(box.headline.foregroundRole()),QColor('#aaaaaa'))
        box._expire_opportunity();box._expire_opportunity()
        self.assertEqual(self.responses,[None])
        self.assertFalse(box.open)
        self.assertFalse(box.opportunity_timer.isActive())
        self.assertFalse(box.blink_timer.isActive())

    def test_keeper_uses_its_own_deadline_and_closed_notice_cannot_fire(self):
        self.show(keeper=True)
        box=self.pitch.stop_box
        self.assertEqual(box.opportunity_timer.interval(),10000)
        box.cancel()
        box._expire_opportunity()
        self.assertEqual(self.responses,[])
        self.assertFalse(box.open)
