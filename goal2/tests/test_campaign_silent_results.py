"""[designed: T48] Full schedule identity, source ordering, RNG and atomic turns."""
import copy
import json
from dataclasses import FrozenInstanceError
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from goal2.desktop.model import DesktopModel
from goal2.desktop.worker import play,complete
from goal2.engine.quick_engine import LCG,QuickMatch
from goal2.engine.savestate import Savestate
from goal2.game.state import to_savestate
from goal2.game.quick_match import begin_full_match
from goal2.game.session_save import encode,decode,SessionSaveError
from goal2.game.campaign_rounds import Scheduled,prepare,advance,validate_state
from goal2.game.silent_results import SilentResolver
from goal2.tests import requires
ROOT=Path(__file__).resolve().parents[2]

@requires.need(**requires.HALFTIME)
class SilentRoundCases(unittest.TestCase):
    def setUp(self):
        self.folder=tempfile.TemporaryDirectory();self.addCleanup(self.folder.cleanup)
        self.model=DesktopModel.open(ROOT/'.cache/e010-r0008-halftime.sav',ROOT/'.cache/GOAL.DAT',Path(self.folder.name)/'world.g2save',country=4)
        self.model.confirm(list(self.model.state.starting_eleven),61,165)
    def test_full_source_schedule_saved_not_regenerated_and_identities_are_frozen(self):
        state=self.model.state;world=state.campaign.world
        self.assertEqual(len(world.fixtures),640);self.assertEqual(world.fixtures[17].fixture_id,'original:1378')
        with self.assertRaises(FrozenInstanceError):world.fixtures[0].kind=99
        raw=encode(state,self.model.template_bytes)
        with patch('goal2.game.campaign_schedule.build_opening_campaign',side_effect=AssertionError('must not regenerate')):
            restored,template=decode(raw)
        self.assertEqual(restored,state);self.assertEqual(template,self.model.template_bytes)
        self.assertEqual(len(restored.campaign.world.fixtures),640)
    def test_first_two_turns_are_one_source_prefix_and_no_unattended_full_quick_loops(self):
        before=copy.deepcopy(self.model.state)
        with patch.object(QuickMatch,'d733',side_effect=AssertionError('CPU full-match loop')):
            try:prepared=prepare(before,self.model.template_bytes)
            except ValueError as exc:self.fail(f'Valid source prefix refused: {exc}')
        self.assertEqual(before,self.model.state);self.assertEqual(len(prepared.campaign.world.results),17)
        first=play(before,self.model.template_bytes);world=first.campaign.world
        self.assertEqual(len(world.results),110)
        self.assertEqual([r['fixture_id'] for r in world.results],[f'original:{n}' for n in range(1361,1471)])
        self.assertEqual(world.results[17]['mode'],'managed')
        # [designed] Fixed fresh-policy regression: fixture order changes these draws.
        self.assertEqual([(r['score'],r['seed_before'],r['seed_after'],r['draws']) for r in world.results[:3]],
                         [([0,1],37972,63228,72),([3,0],63228,2060,80),([1,0],2060,1922,70)])
        self.assertEqual(sum(r['mode']=='silent' for r in world.results),109)
        self.assertEqual(len(first.campaign.results),1);self.assertEqual(first.match_count,1)
        self.assertEqual(first.last_match['seed_DS7B62'],world.results[17]['seed_after'])
        self.assertNotEqual(first.rng_seed_7b62,first.last_match['seed_DS7B62'])
        validate_state(first)
        second=play(first,self.model.template_bytes)
        self.assertEqual(len(second.campaign.world.results),114)
        self.assertEqual(len({r['fixture_id'] for r in second.campaign.world.results}),114)
        self.assertEqual(second.campaign.world.results[-1]['fixture_id'],'original:1474')
        self.assertEqual(second.campaign.next_fixture.fixture_id,'original:1475')
        self.assertNotEqual(second.campaign.next_fixture.kind,1)
        snapshot=copy.deepcopy(second)
        with self.assertRaisesRegex(ValueError,'unsupported'):play(second,self.model.template_bytes)
        self.assertEqual(second,snapshot)
    def test_saved_and_split_halftime_rounds_match_uninterrupted_complete_state_and_rng(self):
        original=copy.deepcopy(self.model.state)
        saved,template=decode(encode(original,self.model.template_bytes))
        uninterrupted=play(original,template)
        pending=prepare(saved,template)
        match=begin_full_match(Savestate(to_savestate(pending,original=template)),pending)
        split=complete(pending,match.finish(retain_state=True),template=template)
        self.assertEqual(split,uninterrupted)
        resumed,template=decode(encode(split,template))
        self.assertEqual(play(resumed,template),play(uninterrupted,template))
        self.assertEqual(original,self.model.state)
    def test_failed_prefix_suffix_and_browser_result_never_publish_partial_world_or_rng(self):
        state=self.model.state;before=copy.deepcopy(state)
        class Broken:
            def __init__(self,state,template):self.delegate=SilentResolver(state,template);self.calls=0
            def __call__(self,f,seed):
                self.calls+=1
                if self.calls==3:raise ValueError('deliberate CPU failure')
                return self.delegate(f,seed)
        with self.assertRaisesRegex(ValueError,'deliberate'):prepare(state,self.model.template_bytes,resolver_factory=Broken)
        self.assertEqual(state,before)
        prepared=prepare(state,self.model.template_bytes)
        match=begin_full_match(Savestate(to_savestate(prepared,original=self.model.template_bytes)),prepared)
        result=match.finish(retain_state=True);private_before=copy.deepcopy(prepared)
        from goal2.game.campaign_rounds import complete as complete_round
        with self.assertRaisesRegex(ValueError,'deliberate'):
            complete_round(prepared,result,template=self.model.template_bytes,resolver_factory=Broken)
        self.assertEqual(prepared,private_before);self.assertEqual(state,before)
        from goal2.web.server import WebSession
        web=WebSession(copy.deepcopy(state),self.model.goaldat,Savestate(self.model.template_bytes),self.model.template_bytes)
        original=SilentResolver.__call__
        def broken(instance,f,seed):
            if f.fixture_id=='original:1380':raise ValueError('deliberate suffix failure')
            return original(instance,f,seed)
        with patch.object(SilentResolver,'__call__',broken):
            with self.assertRaisesRegex(ValueError,'suffix'):web.play({'play_token':web._play_token,'fixture_id':state.campaign.next_fixture.fixture_id})
        self.assertEqual(web.state,before)
    def test_invalid_resolver_output_is_rejected_without_mutating_the_source(self):
        before=copy.deepcopy(self.model.state)
        def invalid_factory(state,template):
            return lambda fixture,seed:{'score':[-1,0],'winner':0,'seed_after':seed,'draws':0}
        with self.assertRaisesRegex(ValueError,'world result'):
            prepare(self.model.state,self.model.template_bytes,resolver_factory=invalid_factory)
        self.assertEqual(self.model.state,before)

    def test_duplicate_order_and_rng_corruption_are_refused_by_save_decode(self):
        state=play(self.model.state,self.model.template_bytes)
        good=json.loads(encode(state,self.model.template_bytes))
        for corruption in ('duplicate','reorder','seed','draws','country','score','counter','decider'):
            doc=copy.deepcopy(good);world=doc['state']['campaign']['world'];rows=world['results']
            if corruption=='duplicate':rows[1]['fixture_id']=rows[0]['fixture_id']
            elif corruption=='reorder':rows[0],rows[1]=rows[1],rows[0]
            elif corruption=='seed':rows[0]['seed_after']^=1
            elif corruption=='draws':rows[0]['draws']+=1
            elif corruption=='country':world['managed_country']=5
            elif corruption=='score':rows[17]['score'][0]+=1
            elif corruption=='counter':doc['state']['match_count']+=1
            else:world['fixtures'][0]['kind']=4;rows[0]['score']=[0,0];rows[0]['winner']=2
            with self.assertRaises(SessionSaveError,msg=corruption):decode(json.dumps(doc).encode())
        from goal2.game.campaign_rounds import complete as complete_round
        result={**state.last_match,'managed_side':state.last_match['managed_side']}
        with self.assertRaisesRegex(ValueError,'already'):complete_round(state,result,template=self.model.template_bytes)
    def test_one_source_contest_batch_extra_round_and_coin_keep_scores_and_rng_explicit(self):
        resolver=SilentResolver(self.model.state,self.model.template_bytes)
        fixture=Scheduled('probe',1,1,2,1)
        with patch.object(resolver.qm,'roll_quick_goals',return_value=[0,0]) as roll:
            out=resolver(fixture,4660);roll.assert_called_once_with(12)
            self.assertEqual(out,{'score':[0,0],'winner':2,'seed_after':4660,'draws':0})
        fixture=Scheduled('decider',4,1,2,1)
        with patch.object(resolver.qm,'roll_quick_goals',side_effect=([0,0],[0,0])) as roll:
            out=resolver(fixture,4660)
            self.assertEqual([c.args for c in roll.call_args_list],[(12,),(4,)])
            rng=LCG(4660);winner=int(rng.rand(2)==1)
            self.assertEqual(out,{'score':[0,0],'winner':winner,'seed_after':rng.seed,'draws':1})
        with patch.object(resolver.qm,'roll_quick_goals',return_value=[2,0]) as roll:
            out=resolver(fixture,4660);self.assertEqual(roll.call_count,1);self.assertEqual(out['winner'],0)
    def test_lcg_accounting_and_stand_in_are_deterministic_and_do_not_touch_players(self):
        before=copy.deepcopy(self.model.state);resolver=SilentResolver(before,self.model.template_bytes)
        fixture=before.campaign.world.fixtures[0]
        out=resolver(fixture,4660);self.assertEqual(resolver(fixture,4660),out)
        self.assertEqual(out,{'score':[0,2],'winner':1,'seed_after':23212,'draws':88})
        self.assertEqual(before,self.model.state)
        self.assertEqual(advance(4660,out['draws']),out['seed_after'])
        self.assertGreaterEqual(out['draws'],48)
        for count in (0,1,2,31,300,65536):
            rng=LCG(4660)
            for _ in range(count):rng.rand(1)
            self.assertEqual(advance(4660,count),rng.seed)
    def test_legacy_metadata_free_save_still_has_managed_only_behavior(self):
        self.model.state.campaign.world=None
        original=copy.deepcopy(self.model.state)
        saved,template=decode(encode(original,self.model.template_bytes))
        self.assertIsNone(saved.campaign.world)
        candidate=play(saved,template)
        self.assertIsNone(candidate.campaign.world);self.assertEqual(len(candidate.campaign.results),1)

if __name__=='__main__':unittest.main()
