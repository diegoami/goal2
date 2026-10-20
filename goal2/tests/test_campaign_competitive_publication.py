"""[designed: T51] Atomic competitive original publication and explicit option binding."""
import copy
import hashlib
import json
import sys
import time
from dataclasses import replace
from functools import lru_cache
import unittest
from pathlib import Path
from goal2.engine.original_match import Fixture,Image
from goal2.game.campaign import CampaignState,Fixture as Scheduled
from goal2.game import watched_publication
from goal2.game.watched_match import WatchedOutcome
from goal2.tests.test_watched_publication import Owner
from goal2.tests.test_campaign_competitive_match import state,run,independent_runtime
from goal2.tests import requires


def publication(owner):
    return getattr(watched_publication,'CompetitivePublication',watched_publication.WatchedPublication)(owner)


def campaign(index=42,kind=200):
    s,raw=state();s.campaign=CampaignState(2028,1,1,2,s.rng_seed_7b62,s.rng_seed_8336,
        (Scheduled(f'original:{index}',1,1,2,kind,7,19),))
    from goal2.game.campaign_pool import validate
    s.campaign.reserve_ids=validate(s)
    return s,raw,Fixture(7,19,index,kind)


@lru_cache(maxsize=None)
def completed(index=42,kind=200):
    s,raw,f=campaign(index,kind)
    return run(s,raw,f)


class CompetitivePublicationTests(unittest.TestCase):
    def begin(self,owner,f):
        pub=publication(owner)
        try:job=pub.begin(f)
        except ValueError as exc:self.fail('competitive job blocked: '+str(exc))
        return pub,job

    def test_original_winner_and_full_tail_publish_once_without_quick_effects(self):
        s,raw,f=campaign();owner=Owner(s,raw);before=copy.deepcopy(s)
        pub,job=self.begin(owner,f);out=copy.deepcopy(completed())
        self.assertEqual(job.state,s);self.assertEqual(owner.state,before)
        try:pub.complete(job.token,out)
        except ValueError as exc:self.fail('valid original completion was rejected: '+str(exc))
        after=Image(out.memory)
        self.assertEqual(owner.state.mem,out.memory);self.assertEqual(owner.state.players,after.players())
        self.assertEqual(owner.state.countries,after.countries());self.assertEqual(owner.state.last_match['seeds'],list(out.seeds))
        self.assertEqual((owner.state.rng_seed_7b62,owner.state.rng_seed_8336),out.seeds)
        self.assertEqual(owner.state.last_match['original'],out.result)
        row=owner.state.campaign.results[0]
        self.assertEqual(row['schema'],2);self.assertEqual(row['resolution']['winner'],out.result['winner'])
        self.assertEqual(row['resolution']['penalties'],out.result['shootout']['score'])
        self.assertEqual(row['score'],[0,0]);self.assertEqual(owner.state.campaign.completed_fixture_ids,['original:42'])
        saved=copy.deepcopy(owner.state)
        with self.assertRaises(ValueError):pub.complete(job.token,out)
        self.assertEqual(owner.state,saved)

    def test_stale_options_kind_budget_incomplete_and_view_failures_are_atomic(self):
        s,raw,f=campaign()
        for damage in ('kind','budget','kit1','end','full_time','seeds','year','image','players','view','stale'):
            with self.subTest(damage=damage):
                owner=Owner(copy.deepcopy(s),raw);pub,job=self.begin(owner,f);out=completed();bad=copy.deepcopy(out)
                if damage=='kind':bad.result['kind']=201
                elif damage=='budget':bad.result['substitution_budget']=[2,2]
                elif damage=='kit1':
                    from goal2.game.watched_schema import RESULT_KEYS
                    bad.result.clear();bad.result.update({k:copy.deepcopy(v) for k,v in out.result.items() if k in RESULT_KEYS})
                    bad.result['kit']='1'
                elif damage=='end':bad=replace(bad,events=bad.events[:-1])
                elif damage=='full_time':bad=replace(bad,events=tuple(e for e in bad.events if e.kind!='full_time'))
                elif damage=='seeds':bad=replace(bad,seeds=(0,0))
                elif damage=='year':bad=replace(bad,engine_year=1)
                elif damage=='image':bad.result['image_sha256']='0'*64
                elif damage=='players':bad.result['players'][0]['confidence'][1]^=1
                elif damage=='view':owner.view=lambda candidate:(_ for _ in ()).throw(ValueError('view refused'))
                else:owner.state.country_tactics^=1
                before=copy.deepcopy(owner.state)
                with self.assertRaises(ValueError):pub.complete(job.token,bad)
                self.assertEqual(owner.state,before)
                with self.assertRaises(ValueError):pub.complete(job.token,out)

    def test_genuine_kit1_friendly_cannot_complete_same_image_competitive_job(self):
        from goal2.game import session_save
        s,raw,f=campaign(21,2);owner=Owner(s,raw);pub,job=self.begin(owner,f)
        from goal2.game.competitive_match import prepare_competitive
        root=Path(__file__).resolve().parents[2]
        requires.require(generated={'watched-legacy-v3-9fb725ac914a/standalone.g2save': 'python3 tools/export_watched_legacy.py --source 9fb725ac914afabfdaa830198fc3a514c87c243f'})
        legacy,_=session_save.decode((root/'.cache/watched-legacy-v3-9fb725ac914a/standalone.g2save').read_bytes())
        original=legacy.last_match['original']
        self.assertEqual(original['kit'],'1');self.assertEqual(original['index'],f.index)
        self.assertEqual(original['image_sha256'],prepare_competitive(job.state,raw,f).sha256())
        outcome=completed(21,2)
        replay=replace(outcome,result=copy.deepcopy(original),memory=legacy.mem,
                       seeds=tuple(legacy.last_match['seeds']),engine_year=legacy.last_match['engine_year'])
        before=copy.deepcopy(owner.state)
        with self.assertRaisesRegex(ValueError,'requires kit2'):pub.complete(job.token,replay)
        self.assertEqual(owner.state,before)

    def test_world_knockout_keeps_original_winner_separate_from_tied_normal_goals(self):
        from goal2.game.campaign_rounds import World,Scheduled as WorldFixture
        from goal2.tests.test_watched_adapter import direct_image
        from goal2.game import session_save
        s,raw,f=campaign();s.campaign.world=World(7,s.rng_seed_7b62,
            (WorldFixture('original:42',200,7,19,1),),[])
        owner=Owner(s,raw);pub,job=self.begin(owner,f)
        out=run(job.state,raw,f,record_draws=True)
        independent,probe=independent_runtime()
        original=independent.Match(independent.Image(direct_image(job.state,0).memory_component()),
            independent.Fixture(7,19,42,200),managed=7,captain=None,substitutions=(5,5),record_draws=True)
        guest=probe.Competitive(original.m);events=[]
        for event in original.events():
            events.append((event.kind,event.minute,event.score,event.data))
            if event.kind=='decision':original.answer()
        self.assertEqual(guest.expected(),probe.kit_stamps(events))
        self.assertEqual(out.result,original.result());self.assertTrue(out.memory==original.memory_component(),'complete independent Memory differs')
        self.assertEqual(out.result['score'],[0,0]);self.assertIsNotNone(out.result['shootout'])
        try:pub.complete(job.token,out)
        except ValueError as exc:self.fail('valid original knockout World completion rejected: '+str(exc))
        world=owner.state.campaign.world.results[0];history=owner.state.campaign.results[0]
        self.assertEqual(world['winner'],out.result['winner']);self.assertNotEqual(world['winner'],2)
        self.assertEqual(world['score'],out.result['score']);self.assertEqual(world['resolution'],history['resolution'])
        self.assertEqual(world['resolution']['penalties'],out.result['shootout']['score'])
        saved=session_save.encode(owner.state,raw);self.assertEqual(session_save.decode(saved)[0],owner.state)
        root=Path(__file__).resolve().parents[2];report=root/'.cache'/('T51-world-knockout-'+str(time.time_ns())+'.json')
        report.write_text(json.dumps({'source':'424d5998076da1e4efc399c2715689ddb44d3e1a',
            'kind':200,'index':42,'managed':7,'budget':[5,5],'policy':'play_on','captain_override':None,
            'engine_year':0,'base_year':2028,'stage':2,'class':0,'next_free':43,
            'image_sha256':out.result['image_sha256'],
            'result_sha256':hashlib.sha256(json.dumps(out.result,sort_keys=True).encode()).hexdigest(),
            'memory_sha256':hashlib.sha256(out.memory).hexdigest(),'seeds':list(out.seeds),
            'resolution':world['resolution'],'independent_package':str(Path(independent.__file__).relative_to(root)),
            'independent_result_memory_equal':True,'guest_stamps_order_equal':True},indent=2)+'\n')
        print('T51 WorldKO evidence '+str(report.relative_to(root)),flush=True)
        print(f'T51 declared WorldKO kind200 index42 next_free43 normal={world["score"]} PK={world["resolution"]["penalties"]} originalwinner={world["winner"]} PASS',flush=True)


if __name__=='__main__':unittest.main()
