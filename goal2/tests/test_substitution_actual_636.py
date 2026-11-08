"""[designed: owner #636] Actual fresh Window/PyPy request journeys and exact same-choice publication.
No prepared decision, direct latch write, fake bridge or pre-selected pair stands in for these cases.
"""
import copy
import hashlib
import json
import os
import unittest
from dataclasses import asdict
from pathlib import Path
from goal2.tests import requires


def run_journey(test, mode):
    import tempfile
    import subprocess
    from PySide6.QtCore import Qt
    from goal2.desktop import data_setup
    from goal2.ui.window import Window
    from goal2.ui.s17_pitch import engine_fixture
    from goal2.tests.test_ui_bench_t180 import Walk, app, career, key, enter_on, play_on, PLAY_NEXT, pump
    from goal2.tests.match_day_policy import play_through_bridge
    from goal2.tests.substitution_selectors_636 import (
        real_worker, source_capture, pause_at_lead_boundary, request_from_bench,
        accept_opportunity_with_escape, outfield_pair, swap_immediately)
    from goal2.tests.test_pypy_worker_t152 import pypy
    pypy();application=app()
    evidence=os.environ.get('GOAL2_636_EVIDENCE')
    captures=[]
    def shot(window,name):
        if evidence:
            captures.append(source_capture(window,Path(evidence)/mode,name,
                                           native=os.environ.get('GOAL2_NATIVE_PROOF')=='1'))

    class RequestWalk(Walk):
        def each(self):
            screen=self.window.current()
            if (type(screen).__name__=='PitchScreen' and screen.stop_box.open and screen.stop_box.timed
                    and screen.controller.stop is not getattr(self,'_seen_opportunity',None)):
                self._seen_opportunity=screen.controller.stop
                self.on_box(screen,screen.stop_box)
                return
            return super().each()

        def playing(self,pitch):
            super().playing(pitch)
            controller=pitch.controller
            frame=controller.display.frame
            if (not self.out.get('pause_sent') and frame is not None and frame['minute']>=(50 if mode=='zero' else 5)
                    and (mode!='zero' or self.out.get('exhausted'))
                    and controller.stop is None and not controller.held):
                boundary=pause_at_lead_boundary(self.window,pitch)
                if boundary is not None:
                    self.out['pause_sent']=True;self.out['pause_after']=boundary

        def on_menu(self,screen):
            if screen.phase=='pause' and self.out.get('pause_sent') and not self.out.get('request_done'):
                key(self.window,Qt.Key.Key_Space)
                return
            if screen.phase=='pause' and self.out.get('request_done') and mode=='accept' and not self.out.get('tactic_done'):
                controller=self.out['controller'];before=len(controller.choices)
                key(self.window,Qt.Key.Key_T)
                editor=self.window.current();test.assertEqual(type(editor).__name__,'TeamTacticsScreen')
                old=editor.answer.team_tactics
                key(self.window,Qt.Key.Key_Down);key(self.window,Qt.Key.Key_Up)
                test.assertEqual(editor.line,0)
                key(self.window,Qt.Key.Key_Return)
                pump(lambda:not editor.pending or controller.error,120,'actual team tactic was not acknowledged')
                test.assertIsNone(controller.error);test.assertEqual(editor.answer.team_tactics,old^16)
                test.assertEqual(len(controller.choices),before+1)
                self.out['tactic_done']=True
                key(self.window,Qt.Key.Key_Escape)
            play_on(self.window,screen)
            if screen.phase=='pause' and mode in ('accept','timeout') and self.out.get('request_done'):
                test.assertTrue(self.out['controller'].substitution_requested)
                test.assertTrue(self.window.current().request_badge.isVisible())
                shot(self.window,'request-on-pitch')

        def on_box(self,pitch,box):
            if not box.timed:
                return super().on_box(pitch,box)
            controller=pitch.controller
            if mode=='timeout' and self.out.get('request_done') and not self.out.get('ignored_once'):
                self.out['ignored_once']=True
                self.out['ignore_budget']=controller.stop.data['substitutions_left']
                self.out['ignore_choices']=len(controller.choices)
                shot(self.window,'opportunity-before-timeout')
                return  # Actual Qt deadline drives no-key; never an auto-accept watchdog.
            if evidence and self.out.get('request_done') and not self.out.get('blink_captured'):
                first=box._opportunity_lit;shot(self.window,'opportunity-blink-first')
                pump(lambda:not box.open or box._opportunity_lit != first,2,'real blink phase did not change')
                test.assertTrue(box.open,'opportunity expired before its visible acceptance')
                shot(self.window,'opportunity-blink-second');self.out['blink_captured']=True
            if mode=='timeout' and self.out.get('ignored_once') and not self.out.get('timeout_checked'):
                test.assertEqual(controller.stop.data['substitutions_left'],self.out['ignore_budget'])
                test.assertIn(('substitution_opportunity',{'opportunity':'timeout'}),controller.choices)
                self.out['timeout_checked']=True
            screen,data=accept_opportunity_with_escape(self.window,pitch)
            if self.out.get('request_done') and mode!='cancel' and not self.out.get('swap_done'):
                self.out['target_legal']=controller.stop
                self.out['opportunity']=data
                shot(self.window,'legal-bench-before-swap')

        def on_board(self,screen):
            if mode=='zero' and screen.phase=='half' and not self.out.get('exhausted'):
                key(self.window,Qt.Key.Key_Escape)
                return
            return super().on_board(screen)

        def on_bench(self,screen):
            controller=self.out['controller']
            if mode=='zero' and screen.answer.context=='half_time' and not self.out.get('exhausted'):
                test.assertLessEqual(screen.answer.left,5)
                while screen.answer.left:
                    used=set(self.out.get('taken_off',()))
                    off=next(w for w in screen.answer.eleven if screen.answer.position(w)!=0 and w not in screen.answer.injured)
                    on=next(w for w in screen.answer.bench if screen.answer.position(w)!=0 and w not in used and w not in screen.answer.injured)
                    before=screen.answer.left
                    enter_on(self.window,screen,off);enter_on(self.window,screen,on)
                    test.assertEqual(screen.answer.left,before-1)
                    self.out.setdefault('taken_off',[]).append(off)
                self.out['exhausted']=True
                shot(self.window,'zero-budget-before-play')
                key(self.window,Qt.Key.Key_Escape)
                return
            if screen.answer.context=='pause' and not self.out.get('request_done'):
                self.out['request_ack']=request_from_bench(self.window,screen,True,expected=False if mode=='zero' else True,capture=shot)
                if mode=='cancel':
                    self.out['cancel_ack']=request_from_bench(self.window,screen,False,capture=shot)
                self.out['request_done']=True
                key(self.window,Qt.Key.Key_Escape)
                return
            if controller.stop is self.out.get('target_legal') and not self.out.get('swap_done'):
                injured=[w for w in screen.answer.eleven if w in screen.answer.injured]
                if injured:
                    off=injured[0];used=set(self.out.get('taken_off',()))
                    on=next(w for w in screen.answer.bench if w not in used
                            and (screen.answer.position(w)==0)==(screen.answer.position(off)==0))
                    pair=(off,on)
                else:
                    pair=outfield_pair(screen.answer,taken_off=self.out.get('taken_off',()))
                self.out['pair']=list(pair);self.out['swap_answer']=swap_immediately(self.window,screen,pair)
                self.out.setdefault('taken_off',[]).append(pair[0])
                self.out['swap_done']=True;shot(self.window,'swap-confirmed-before-play')
                if mode=='accept':
                    before=screen.answer.left;choices=len(controller.choices)
                    other=next(w for w in screen.answer.eleven if w!=pair[1] and screen.answer.position(w)!=0)
                    enter_on(self.window,screen,other);enter_on(self.window,screen,pair[0])
                    test.assertEqual(screen.answer.left,before)
                    test.assertNotIn(pair[0],screen.answer.eleven)
                    test.assertEqual(len(controller.choices),choices+1)
                    test.assertTrue(controller.reports[-1]['refused'])
                    test.assertEqual(controller.reports[-1]['made'],[])
                    self.out['refusal_checked']=True
                choices=len(controller.choices)
                key(self.window,Qt.Key.Key_Escape)
                menu=self.window.current();test.assertEqual(type(menu).__name__,'MenuScreen');test.assertEqual(menu.phase,'stop')
                play_on(self.window,menu)
                test.assertEqual(type(self.window.current()).__name__,'PitchScreen')
                test.assertIsNone(controller.stop)
                test.assertEqual(len(controller.choices),choices+1)
                test.assertEqual(controller.choices[-1],('substitution',[]))
                return
            # Existing T180/T610 injury policy, using actual legal stopped data.
            injured=[w for w in screen.answer.eleven if w in screen.answer.injured]
            if screen.answer.takes_substitutions and screen.answer.left and injured:
                off=injured[0];used=set(self.out.get('taken_off',()))
                on=next(w for w in screen.answer.bench if w not in used
                        and (screen.answer.position(w)==0)==(screen.answer.position(off)==0))
                enter_on(self.window,screen,off);enter_on(self.window,screen,on)
                self.out.setdefault('taken_off',[]).append(off)
            key(self.window,Qt.Key.Key_Escape)

    with tempfile.TemporaryDirectory(prefix='goal2-636-') as folder:
        owner=career();count=owner.state.match_count
        window=Window(data_setup.paths(Path(folder)));window.resize(1440,900);window.show()
        desk=window.open_career(owner)
        if mode=='zero':
            # Reach the competitive fixture through an actual fresh friendly,
            # never by writing an allowance or constructing a waiting decision.
            class Warmup(Walk):
                def on_bench(self,screen):
                    injured=[w for w in screen.answer.eleven if w in screen.answer.injured]
                    if screen.answer.takes_substitutions and screen.answer.left and injured:
                        off=injured[0];used=set(self.out.get('taken_off',()))
                        on=next(w for w in screen.answer.bench if w not in used
                                and (screen.answer.position(w)==0)==(screen.answer.position(off)==0))
                        enter_on(self.window,screen,off);enter_on(self.window,screen,on)
                        self.out.setdefault('taken_off',[]).append(off)
                    key(self.window,Qt.Key.Key_Escape)
            warmup=Warmup('zero-budget-setup-friendly',window,owner)
            desk.highlight(PLAY_NEXT);key(window,Qt.Key.Key_Return);warmup.run()
            test.assertIsNone(warmup.out['controller'].error)
            desk=window.current();count=owner.state.match_count
        fixture=owner.state.campaign.next_fixture
        if mode=='zero':test.assertEqual(fixture.kind,2)
        walk=RequestWalk('request-'+mode,window,owner)
        try:
            desk.highlight(PLAY_NEXT);key(window,Qt.Key.Key_Return);walk.run()
            controller=walk.out['controller']
            test.assertIsNone(controller.error)
            test.assertTrue(walk.out.get('request_done'))
            test.assertEqual(owner.state.match_count,count+1)
            request_choices=[value for context,value in controller.choices if isinstance(value,dict) and 'request_substitution' in value]
            test.assertEqual([v['request_substitution'] for v in request_choices],[True,False] if mode=='cancel' else [True])
            test.assertTrue(all(not v.get('substitutions') for v in request_choices))
            if mode in ('accept','timeout'):
                test.assertTrue(walk.out.get('swap_done'))
                off,on=walk.out['pair']
                made=[e for e in controller.events if e['kind']=='substitution'
                      and e['data'].get('team')==controller.display.managed
                      and e['data'].get('off')==off and e['data'].get('on')==on]
                test.assertEqual(len(made),1)
            if mode=='zero':
                test.assertTrue(walk.out.get('exhausted'))
                test.assertIs(walk.out['request_ack']['acknowledged'],False)
            if mode=='accept':test.assertTrue(walk.out.get('tactic_done'));test.assertTrue(walk.out.get('refusal_checked'))
            if mode=='timeout':test.assertTrue(walk.out.get('timeout_checked'))
            other=career();other.state=copy.deepcopy(controller.given._snapshot)
            expected=play_through_bridge(other,controller.choices,fixture=engine_fixture(fixture),competitive=fixture.kind!=1,wait=1500,
                                         pause_after=walk.out['pause_after'])
            test.assertEqual(controller.outcome.result,expected.result)
            test.assertEqual(controller.outcome.events,expected.events)
            test.assertEqual(controller.outcome.memory,expected.memory)
            test.assertEqual(owner.state,other.state)
            test.assertEqual(controller.outcome.seeds,expected.seeds)
            root=Path(__file__).resolve().parents[2]
            files=('goal2/ui/s17_pitch.py','goal2/ui/s18_stop.py','goal2/ui/s19_bench.py','goal2/ui/s10_team_tactics.py',
                   'goal2/ui/match_day.py','goal2/ui/live_cards.py','goal2/ui/squad_card.py',
                   'goal2/game/watched_match.py','goal2/game/watched_jobs.py','goal2/game/engine_process.py',
                   'goal2/game/engine_server.py','goal2/game/watched_schema.py','goal2/desktop/competitive.py',
                   'goal2/tests/match_day_policy.py','goal2/tests/substitution_selectors_636.py',
                   'goal2/tests/test_substitution_actual_636.py','tools/watched-kit-hashes.json','PROVENANCE.md',
                   'goal2/engine/original_match/match.py','goal2/engine/original_match/screens.py')
            digest=lambda value:hashlib.sha256(json.dumps(value,sort_keys=True).encode()).hexdigest()
            source_commit=os.environ.get('GOAL2_SOURCE_COMMIT')
            if source_commit is None:
                source_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=root,text=True).strip()
            test.assertRegex(source_commit,r'^[0-9a-f]{40}$')
            report=dict(mode=mode,source_commit=source_commit,
                input_template_sha256=hashlib.sha256(bytes(owner.template_bytes)).hexdigest(),
                fixture={'id':fixture.fixture_id,'kind':fixture.kind,'sides':[fixture.side_a,fixture.side_b]},
                source_hashes={name:hashlib.sha256((root/name).read_bytes()).hexdigest() for name in files},
                flags={'live_players':True,'substitution_control':True},choices=controller.choices,
                requested=len(request_choices),published_once=True,result_sha256=digest(controller.outcome.result),
                memory_sha256=hashlib.sha256(controller.outcome.memory).hexdigest(),seeds=controller.outcome.seeds,
                result_equal=True,events_equal=True,memory_equal=True,career_equal=True,captures=captures)
            print('ACTUAL_UI_SUBSTITUTION_636 '+json.dumps(report,sort_keys=True),flush=True)
            return report
        finally:
            if window.match_day is not None:window.match_day.close()
            window.leaving=True;window.leave();application.processEvents()


@requires.need(modules=('PySide6','pygame'),slow=True, **requires.HALFTIME)
class ActualRequestJourney(unittest.TestCase):
    def test_natural_request_opportunity_escape_immediate_swap_refusal_tactics_and_play(self):
        run_journey(self,'accept')

    def test_natural_request_then_cancel_resumes_with_the_same_exact_outcome(self):
        run_journey(self,'cancel')

    def test_ignored_timed_opportunity_spends_no_allowance_then_next_guest_opportunity_can_be_accepted(self):
        run_journey(self,'timeout')

    def test_zero_budget_request_refusal_uses_actual_competitive_allowance_and_ui(self):
        run_journey(self,'zero')
