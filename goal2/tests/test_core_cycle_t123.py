"""[designed: T123] Genuine bounded decisions/replay and hostile proof-receipt controls.

Synthetic receipt dictionaries below test validation only; they never establish a played cycle.
The standalone prove/verify commands supply the separate four-year acceptance.
"""
import copy
import json
from pathlib import Path
import tempfile
import unittest

from goal2.tests import requires


class ReceiptControls(unittest.TestCase):
    def example(self):
        from goal2.core.cycle_evidence import expected_sources, runtime_manifest, INPUTS, POLICY, PHASES
        fingerprint = dict(memory='1'*64, cpu='2'*64, keys='3'*64, save='4'*64,
                           key_count=10, kind='match-menu', site='214B:157C', poll=False)
        annual=[]
        for index,(season,stage,year) in enumerate(PHASES,1):
            annual.append(dict(number=index,progress=dict(season=season,stage=stage,year=year),
                replay=dict(before=f'annual-{index}.g2core',before_sha256='5'*64,
                    action='round_start',direct=copy.deepcopy(fingerprint),resumed=copy.deepcopy(fingerprint))))
        return dict(schema=1,status='complete',variant=POLICY,inputs=copy.deepcopy(INPUTS),
                    sources=expected_sources(),runtime=runtime_manifest(),start_year=2028,
                    dos_date=[2027,10,4],dos_time=[10,0,0,0],
                    initial_country=20,initial=dict(season=0,stage=2,year=2028),
                    final=dict(season=2,stage=2,year=2032),annual=annual,
                    transitions=[dict(season=0,stage=2,year=2028)]+[copy.deepcopy(a['progress']) for a in annual],
                    steps=20,rounds=5,elapsed_seconds=1.0,bounds=dict(steps=1000,rounds=300,seconds=7200),
                    trace=dict(rows=30,operations=20,consumed=10,keys_sha256='9'*64,sha256='6'*64,last_chain='7'*64),
                    final_save='final.g2core',final_sha256='8'*64,
                    history=[dict(season='2027/28'),dict(season='2029/30')],errors=[])

    def test_structural_controls_are_not_a_receipt_only_proof(self):
        from goal2.core.cycle_evidence import validate_report, verify
        report=self.example();validate_report(report)
        with tempfile.TemporaryDirectory() as folder:
            Path(folder,'report.json').write_text(json.dumps(report))
            with self.assertRaises((ValueError,FileNotFoundError)):
                verify(Path(folder))  # no original machine/trace exists; cannot pass as a cycle

    def test_empty_failed_truncated_missing_boundary_wrong_source_or_policy_cannot_pass(self):
        from goal2.core.cycle_evidence import validate_report
        good=self.example()
        variants=[{},dict(good,status='failed'),dict(good,annual=[]),dict(good,annual=good['annual'][:-1]),
                  dict(good,final=dict(season=1,stage=2,year=2032)),dict(good,errors=['unknown wait']),
                  dict(good,variant='original'),dict(good,steps=0),dict(good,trace=dict(good['trace'],rows=0)),
                  dict(good,schema=True),dict(good,initial=dict(season=False,stage=2,year=2028)),
                  dict(good,bounds=dict(good['bounds'],steps=1)),dict(good,elapsed_seconds=float('inf')),
                  dict(good,transitions=[])]
        bad=copy.deepcopy(good);bad['sources']['commit']='a'*40;variants.append(bad)
        bad=copy.deepcopy(good);bad['annual'][1]['progress']['stage']=3;variants.append(bad)
        bad=copy.deepcopy(good);bad['annual'][0]['replay']['resumed']['cpu']='b'*64;variants.append(bad)
        bad=copy.deepcopy(good);bad['annual'][0]['replay']['before']='../outside.g2core';variants.append(bad)
        for report in variants:
            with self.subTest(report=list(report)),self.assertRaises(ValueError):validate_report(report)

    @requires.need(archaeology=True)
    def test_exact_source_files_and_claims_are_read_without_importing_upstream(self):
        from goal2.core.cycle_evidence import check_sources, expected_sources
        self.assertEqual(check_sources(requires.archaeology()),expected_sources())


@requires.need(modules=('unicorn',),files=('GOAL.DAT','g13-d5ebee1ea6d80c4a-best-place-before.g2core'))
class OriginalDecisions(unittest.TestCase):
    def test_actual_achievement_step_and_saved_replay_are_exact(self):
        from goal2.tests.test_core_best_place_395 import achievement
        from goal2.core.cycle_player import Player
        from goal2.core.cycle_evidence import replay_step, fingerprint
        from goal2.core.driver import Driver
        c=achievement()
        with tempfile.TemporaryDirectory() as folder:
            proof=replay_step(c,requires.CACHE/'GOAL.DAT',Path(folder),'annual-1')
            self.assertEqual(proof['action'],'round_continue')
            self.assertEqual(proof['direct'],proof['resumed'])
            self.assertEqual(c.wait.kind,'manager-menu')
            self.assertEqual(proof['direct'],fingerprint(c))
        self.assertEqual(Player(Driver(achievement())).step(),'round_continue')

    def test_classifier_failure_keeps_the_actual_machine_and_preceding_supported_save(self):
        from unittest.mock import patch
        from goal2.tests.test_core_best_place_395 import before
        from goal2.core import Core,UnknownScreen,screens
        from goal2.core.cycle_evidence import Trace
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);c=before();trace=Trace(c,root)
            try:
                with patch.object(screens,'_best_place',return_value=None):
                    # SITES binds the original callable; patch identify only at this one poll.
                    identify=screens.identify
                    with patch.object(screens,'identify',side_effect=lambda site,frame: None if site=='000E:05EC' else identify(site,frame)):
                        with self.assertRaises(UnknownScreen):c.press(13)
            finally:trace.close()
            self.assertTrue((root/'actual.ucstate').is_file())
            self.assertTrue((root/'last-before.g2core').is_file())
            self.assertEqual(Core.load((root/'last-before.g2core').read_bytes()).wait.kind,'championship-bracket')
            rows=[json.loads(line) for line in (root/'trace.jsonl').read_text().splitlines()]
            self.assertEqual(rows[-1]['error'],'UnknownScreen')
            self.assertEqual(rows[-1]['args'],[13])


@requires.need(modules=('unicorn',),files=('GOAL.DAT','g13-cb6443bbe76d3a5a-no-keeper.g2core',
    'g13-5e303b5839883b2c-too-many-defenders.g2core'))
class Lineup(unittest.TestCase):
    def test_original_refusals_are_repaired_by_club_position_keys_without_refilling_budgets(self):
        from goal2.tests.test_core_lineup_t114 import loaded
        from goal2.core.cycle_player import Player
        from goal2.core import views
        for index in (0,1):
            with self.subTest(index=index):
                d=loaded(index);d.round_start(True);result=d.kick_off()
                self.assertIn('refused',result)
                budget=views.bench(d.wait.state)['left']
                p=Player(d);p.refused=result['refused'];action=p.step()
                self.assertEqual(action,'restore_club_position')
                self.assertEqual(views.bench(d.wait.state)['left'],budget)
                self.assertEqual(p.step(),'kick_off')
                self.assertEqual(d.wait.kind,'match-live')


@requires.need(modules=('unicorn',),files=('GOAL.DAT','3ea57029282b849f-g1-03874-shootout-start.sav'))
class Shootout(unittest.TestCase):
    def test_all_original_available_players_are_ordered_without_a_five_player_cap(self):
        from goal2.tests.test_core_shootout_t118 import started
        from goal2.core.cycle_player import Player
        from goal2.core import views
        d=started();p=Player(d);self.assertEqual(p.step(),'shootout_start')
        picked=[]
        for _ in range(11):
            if d.wait.kind!='shootout-order':break
            v=views.shootout_order(d.wait.state,d.wait.view)
            picked.append(next(r['player'] for r in v['players'] if r['available'] and r['rank'] is None))
            self.assertEqual(p.step(),'shootout_pick')
        self.assertEqual(len(picked),11)
        self.assertEqual(len(set(picked)),11)
        self.assertNotEqual(d.wait.kind,'shootout-order')


@requires.need(modules=('unicorn',),files=('GOAL.DAT','t88-bda98a358d98a82f-corner-before-space.sav',
    't89-cd047f4a697e5244-goal-kick-before-space.sav'))
class Takers(unittest.TestCase):
    def test_actual_corner_and_goal_kick_receive_the_original_computer_choice(self):
        from goal2.tests.test_core_takers_t120 import loaded
        from goal2.core.cycle_player import Player
        for index in (0,1):
            with self.subTest(index=index):
                d=loaded(index);n=len(d.core.keys)
                self.assertEqual(Player(d).step(),'taker_key')
                self.assertEqual(d.core.keys[n],ord('c'))


@requires.need(modules=('unicorn',),files=('GOAL.DAT','e039-r0005-date-call.sav'))
class BootTrace(unittest.TestCase):
    def test_observing_from_construction_records_the_actual_queued_title_key_without_changing_the_machine(self):
        from goal2.core import Core
        from goal2.core.cycle_evidence import INPUTS, Trace, fingerprint, sha
        raw=(requires.CACHE/INPUTS['boot']['name']).read_bytes()
        self.assertEqual(sha(raw),INPUTS['boot']['sha256'])
        active={}
        with tempfile.TemporaryDirectory() as folder:
            class Observed(Core):
                def __init__(self,*args,**kwargs):
                    super().__init__(*args,**kwargs);active['trace']=Trace(self,Path(folder))
            kwargs=dict(dos_time=(10,0,0,0),goal_dat=requires.CACHE/'GOAL.DAT',title_key='n')
            try:
                a=Observed.boot(raw,(2027,10,4),**kwargs).core
                b=Core.boot(raw,(2027,10,4),**kwargs).core
                self.assertEqual(fingerprint(a),fingerprint(b))
                self.assertEqual(a.wait.kind,'title-player-count')
                self.assertEqual(active['trace'].consumed,[ord('n')])
                self.assertEqual(a.keys,[], 'queued keys must be observed separately from explicit Core.press keys')
            finally:
                if 'trace' in active:active['trace'].close()
