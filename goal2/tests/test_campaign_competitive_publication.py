"""[designed: T51] Atomic competitive original publication and explicit option binding."""
import copy
from dataclasses import replace
from functools import lru_cache
import unittest
from pathlib import Path
from goal2.engine.original_match import Fixture,Image
from goal2.game.campaign import CampaignState,Fixture as Scheduled
from goal2.game import watched_publication
from goal2.game.watched_match import WatchedOutcome
from goal2.tests.test_watched_publication import Owner
from goal2.tests.test_campaign_competitive_match import state,run


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


if __name__=='__main__':unittest.main()
