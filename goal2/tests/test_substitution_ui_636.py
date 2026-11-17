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
        from PySide6.QtGui import QColor
        self.assertEqual(box.headline.text(),"HAS NO GOALKEEPER")
        self.assertEqual(box.headline.palette().color(box.headline.foregroundRole()),QColor("#55ffff"))
        box.cancel()
        box._expire_opportunity()
        self.assertEqual(self.responses,[])
        self.assertFalse(box.open)


@requires.need(modules=('PySide6','pygame'), **requires.HALFTIME)
class Lifecycle(unittest.TestCase):
    def setUp(self):
        from goal2.tests.test_ui_replay_t181 import ReplayScreens
        ReplayScreens.setUp(self)
        self.bridge.reports=[];self.sent=[]
        self.bridge.answer=lambda token,pairs,changes=None:self.sent.append((list(pairs),changes))

    def test_timeout_closes_only_the_notice_and_does_not_invent_request_cancellation(self):
        data=dict(context='substitution_opportunity',request_substitution=True,keeper_unavailable=False,
                  timeout_polls=400,poll_ms=10,eleven=[],bench=[],substitutions_left=5,substitutions_now=True)
        decision=SimpleNamespace(data=data,minute=5,score=[0,0])
        self.controller.stop=decision;self.controller.substitution_requested=True
        self.pitch.held=decision;self.pitch.show_opportunity(decision)
        self.pitch.stop_box._expire_opportunity()
        self.assertEqual(self.sent,[([],{'opportunity':'timeout'})])
        self.assertFalse(self.pitch.stop_box.open)
        self.assertIsNone(self.controller.stop)
        self.assertTrue(self.controller.substitution_requested)
        self.assertTrue(self.pitch.request_badge.isVisible())
        self.pitch.stop_box._expire_opportunity()
        self.assertEqual(len(self.sent),1)

    def test_old_timers_cannot_answer_the_next_notice_and_generic_detail_style_is_restored(self):
        box=self.pitch.stop_box;answers=[]
        box.show_opportunity(dict(keeper_unavailable=False,timeout_polls=400,poll_ms=10),answers.append)
        box.cancel()
        box.show_stop('test','other notice','normal detail',answers.append)
        box._expire_opportunity()
        self.assertEqual(answers,[])
        self.assertTrue(box.open)
        self.assertFalse(box.timed)
        self.assertNotIn('#000000',box.detail.styleSheet().lower())


@requires.need(modules=('PySide6','pygame'), **requires.HALFTIME)
class OpportunityScaling(unittest.TestCase):
    def test_heading_scales_with_the_page_and_the_notice_stays_inside_the_lower_pitch(self):
        from goal2.tests.test_ui_replay_t181 import ReplayScreens
        from PySide6.QtCore import QPoint
        from goal2.ui import theme
        ReplayScreens.setUp(self)
        box=self.pitch.stop_box
        for width,height in ((1440,900),(1800,1125),(2110,1213)):
            box.cancel();self.window.resize(width,height);self.app.processEvents()
            box.show_opportunity(dict(keeper_unavailable=False,timeout_polls=400,poll_ms=10),lambda key:None)
            self.app.processEvents();box.place()
            top=self.pitch.pitch.mapFromGlobal(box.mapToGlobal(QPoint(0,0)))
            self.assertGreaterEqual(top.x(),0);self.assertGreaterEqual(top.y(),0)
            self.assertLessEqual(top.x()+box.width(),self.pitch.pitch.width())
            self.assertLessEqual(top.y()+box.height(),self.pitch.pitch.height())
            self.assertGreaterEqual(box.headline.font().pixelSize(),round(theme.TEXT*theme.STRETCH*self.window.frame.scale)-1)
            self.assertFalse(box.headline.text().strip()=='')
            box.cancel()


@requires.need(modules=('PySide6','pygame'), **requires.HALFTIME)
class FullRequestCue(unittest.TestCase):
    def test_full_request_cue_fits_real_font_and_last_glyph_pixels_at_three_sizes(self):
        from goal2.tests.test_ui_replay_t181 import ReplayScreens
        from goal2.ui.s19_bench import BenchAnswer
        from goal2.ui import theme
        ReplayScreens.setUp(self)
        words=self.model.state.managed_squad
        decision=SimpleNamespace(minute=30,score=[0,0],data=dict(context='pause',eleven=words[:11],bench=words[11:],
            substitutions_now=False,substitutions_left=255,request_substitution=False,tactics=self.model.state.country_tactics,
            positions=[[w,self.model.state.players[w][6]] for w in words]))
        self.day.bench=BenchAnswer(self.model,decision,friendly=True)
        screen=self.day.open_bench()
        self.app.processEvents()
        for width,height in ((1440,900),(1800,1125),(2110,1213)):
            decision.data["request_substitution"]=False
            screen.answer=BenchAnswer(self.model,decision,friendly=True)
            self.window.resize(width,height);self.app.processEvents();screen.refresh();self.app.processEvents()
            decision.data["request_substitution"]=True
            screen._request_desired=True
            screen.applied(BenchAnswer(self.model,decision,friendly=True),None)
            # The acknowledgement must already fit before another event-loop turn.
            label=screen.mode_label;text='SUBSTITUTION REQUESTED';metrics=label.fontMetrics()
            self.assertEqual(label.text(),text)
            self.assertGreaterEqual(label.font().pixelSize(),round(theme.TEXT*theme.STRETCH*self.window.frame.scale)-1)
            self.assertLessEqual(metrics.horizontalAdvance(text),label.contentsRect().width()+1)
            image=label.grab().toImage();dpr=image.devicePixelRatio()
            start=max(0,int((label.contentsRect().left()+metrics.horizontalAdvance(text[:-1]))*dpr))
            foreground=label.palette().color(label.foregroundRole()).rgb()
            self.assertTrue(any(image.pixelColor(x,y).rgb()==foreground
                for x in range(start,image.width()) for y in range(image.height())),
                'the final D must have actual foreground pixels inside the label bounds')
