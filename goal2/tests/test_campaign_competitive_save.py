"""[designed: T51] Real opening qualifier and durable explicit competitive history."""
import copy
from functools import lru_cache
import json
from pathlib import Path
import unittest
from goal2.engine.original_match import Fixture,Image
from goal2.game import session_save
from goal2.game.campaign import Fixture as Scheduled
from goal2.game.campaign_schedule import start_opening_campaign
from goal2.game.eligibility import available_words
from goal2.game.watched_match import run_watched_match
from goal2.game.watched_publication import WatchedPublication
from goal2.tests.test_watched_publication import Owner
from goal2.tests.test_campaign_competitive_match import run
from goal2.tests.test_campaign_competitive_publication import campaign,publication,completed

ROOT=Path(__file__).resolve().parents[2]


def select(s):
    s.starting_eleven=available_words(s.players,s.managed_squad)[:11];s.captain=s.starting_eleven[0]


@lru_cache(maxsize=None)
def opening_qualifier():
    from goal2.data.goaldat import load
    raw=(ROOT/'.cache/e010-r0008-halftime.sav').read_bytes()
    data=load((ROOT/'.cache/GOAL.DAT').read_bytes())
    s,_=start_opening_campaign(data,raw,managed_country=4,start_year=1990,seed_7b62=4660,seed_8336=33590)
    owner=Owner(s,raw)
    for _ in range(2):
        select(owner.state);f=owner.state.campaign.next_fixture
        if f.kind!=1:raise AssertionError('actual1990 country4 opening fixture is not friendly')
        fixture=Fixture(f.side_a,f.side_b,int(f.fixture_id.split(':')[1]),f.kind)
        pub=WatchedPublication(owner);job=pub.begin(fixture)
        pub.complete(job.token,run_watched_match(job.state,raw,fixture))
    select(owner.state)
    before=copy.deepcopy(owner.state);f=before.campaign.next_fixture
    if f.kind==1:raise AssertionError('actual qualifier missing')
    fixture=Fixture(f.side_a,f.side_b,int(f.fixture_id.split(':')[1]),f.kind)
    pub=publication(owner);job=pub.begin(fixture);out=run(job.state,raw,fixture)
    pub.complete(job.token,out)
    return before,copy.deepcopy(owner.state),raw,fixture,job.state,out


class CompetitiveSaveTests(unittest.TestCase):
    def test_actual_country4_qualifier_after_two_original_friendlies_roundtrips_and_continues(self):
        try:before,after,raw,f,job,out=opening_qualifier()
        except ValueError as exc:self.fail('actual competitive publication unavailable: '+str(exc))
        from goal2.tests.test_watched_adapter import direct_image
        original=__import__('goal2.engine.original_match',fromlist=['Match']).Match(
            direct_image(job,0),f,managed=4,captain=job.captain,substitutions=(5,5))
        for event in original.events():
            if event.kind=='decision':original.answer()
        self.assertEqual(out.result,original.result());self.assertEqual(out.memory,original.memory_component())
        self.assertEqual(len(after.campaign.completed_fixture_ids),3)
        row=after.campaign.results[-1];self.assertEqual(row['resolution']['kind'],f.kind)
        world=next(r for r in after.campaign.world.results if r['fixture_id']==f'original:{f.index}')
        self.assertEqual(world['resolution'],row['resolution']);self.assertEqual(world['winner'],out.result['winner'])
        encoded=session_save.encode(after,raw);restored,template=session_save.decode(encoded)
        self.assertEqual(after,restored);self.assertEqual(template,raw);self.assertEqual(restored.mem,out.memory)
        self.assertEqual(restored.last_match['seeds'],list(out.seeds))
        outcomes=[]
        for prior in (after,restored):
            owner=Owner(copy.deepcopy(prior),raw);select(owner.state);nextf=owner.state.campaign.next_fixture
            fixture=Fixture(nextf.side_a,nextf.side_b,int(nextf.fixture_id.split(':')[1]),nextf.kind)
            pub=publication(owner);job=pub.begin(fixture);result=run(job.state,raw,fixture)
            pub.complete(job.token,result);outcomes.append(owner.state)
        self.assertEqual(outcomes[0],outcomes[1])
        print(f'T51 actual country4 qualifier kind={f.kind} index={f.index} score={out.result["score"]} winner={out.result["winner"]} next deterministic PASS',flush=True)

    def test_no_world_compact_resolution_survives_later_friendly_and_rejects_damage(self):
        s,raw,f=campaign();s.campaign.fixtures+=(Scheduled('original:43',1,1,2,1,7,19),)
        owner=Owner(s,raw);pub=publication(owner)
        try:job=pub.begin(f)
        except ValueError as exc:self.fail('competitive history unavailable: '+str(exc))
        pub.complete(job.token,copy.deepcopy(completed()))
        history=copy.deepcopy(owner.state.campaign.results[0]);select(owner.state)
        pub=WatchedPublication(owner);fixture=Fixture(7,19,43);job=pub.begin(fixture)
        pub.complete(job.token,run_watched_match(job.state,raw,fixture))
        self.assertEqual(owner.state.campaign.results[0],history)
        self.assertEqual(owner.state.last_match['schema'],1)
        document=session_save.encode(owner.state,raw);resumed,_=session_save.decode(document)
        self.assertEqual(resumed,owner.state)
        for damage in ('missing','winner','penalties','normal','kind','profile','extra_time','engine'):
            bad=json.loads(document);row=bad['state']['campaign']['results'][0]
            if damage=='missing':row.pop('resolution')
            elif damage=='profile':row['schema']=1
            elif damage=='engine':row['engine']='original-match:3656a2d26e0f57a410d648edeaa6cd9eb7d1f607:1'
            elif damage=='normal':row['score']=row['resolution']['penalties']
            else:row['resolution'][damage]={'winner':1,'penalties':[0,0],'kind':2,'extra_time':None}[damage]
            before=copy.deepcopy(owner.state)
            with self.subTest(damage=damage),self.assertRaises(session_save.SessionSaveError):session_save.decode(json.dumps(bad).encode())
            self.assertEqual(owner.state,before)


if __name__=='__main__':unittest.main()
