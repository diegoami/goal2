"""[designed: T51] Real opening qualifier and durable explicit competitive history."""
import copy
from functools import lru_cache
import json
import hashlib
import time
import subprocess
import sys
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
from goal2.tests.test_campaign_competitive_match import run,independent_runtime
from goal2.tests.test_campaign_competitive_publication import campaign,publication,completed
from goal2.tests import requires

ROOT=Path(__file__).resolve().parents[2]


def select(s):
    # [designed] A declared manager selection: one available keeper and ten outfield players.
    image=Image(s.mem);lines=image.memory[image.DS*16+0xD4E:image.DS*16+0xD4E+16]
    eligible=available_words(s.players,s.managed_squad)
    keepers=[w for w in eligible if lines[s.players[w][6]]==0]
    outfield=[w for w in eligible if lines[s.players[w][6]]!=0]
    if not keepers or len(outfield)<10:raise AssertionError('declared squad lacks an eligible original eleven')
    s.starting_eleven=keepers[:1]+outfield[:10];s.captain=s.starting_eleven[0]


@lru_cache(maxsize=None)
def opening_qualifier():
    from goal2.data.goaldat import load
    requires.require(**requires.HALFTIME)
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
    @requires.need(slow=True)  # [designed: #275] about 155 s alone on 32 CPUs
    def test_actual_country4_qualifier_after_two_original_friendlies_roundtrips_and_continues(self):
        try:before,after,raw,f,job,out=opening_qualifier()
        except ValueError as exc:self.fail('actual competitive publication unavailable: '+str(exc))
        declared_input=job
        from goal2.tests.test_watched_adapter import direct_image
        independent,probe=independent_runtime()
        original=independent.Match(independent.Image(direct_image(job,0).memory_component()),
            independent.Fixture(f.first,f.second,f.index,f.kind),managed=4,captain=job.captain,substitutions=(5,5))
        guest=probe.Competitive(original.m);events=[]
        for event in original.events():
            events.append((event.kind,event.minute,event.score,event.data))
            if event.kind=='decision':original.answer()
        self.assertEqual(guest.expected(),probe.kit_stamps(events))
        # [designed: T151] goal2's route plays the sealed port; `original` is the accepted export (port_parity)
        from goal2.tests.port_parity import assert_same_match
        assert_same_match(self,out.result,out.memory,out.events,original.result(),original.memory_component(),
            [dict(kind=k,minute=m,score=sc,data=d) for k,m,sc,d in events])
        self.assertEqual(len(after.campaign.completed_fixture_ids),3)
        row=after.campaign.results[-1];self.assertEqual(row['resolution']['kind'],f.kind)
        world=next(r for r in after.campaign.world.results if r['fixture_id']==f'original:{f.index}')
        self.assertEqual(world['resolution'],row['resolution']);self.assertEqual(world['winner'],out.result['winner'])
        encoded=session_save.encode(after,raw);restored,template=session_save.decode(encoded)
        self.assertEqual(after,restored);self.assertEqual(template,raw);self.assertEqual(restored.mem,out.memory)
        self.assertEqual(restored.last_match['seeds'],list(out.seeds))
        for damage in ('world_resolution','world_winner','history_resolution','raw_kind','raw_players'):
            bad=json.loads(encoded)
            history=bad['state']['campaign']['results'][-1]
            world=next(r for r in bad['state']['campaign']['world']['results'] if r['fixture_id']==f'original:{f.index}')
            if damage=='world_resolution':world['resolution']['kind']=200
            elif damage=='world_winner':world['winner']=(world['winner']+1)%3
            elif damage=='history_resolution':history.pop('resolution')
            elif damage=='raw_kind':bad['state']['last_match']['original']['kind']=200
            else:bad['state']['last_match']['original']['players'][0]['energy'][1]^=1
            with self.subTest(damage=damage),self.assertRaises(session_save.SessionSaveError):session_save.decode(json.dumps(bad).encode())
        outcomes=[]
        for prior in (after,restored):
            owner=Owner(copy.deepcopy(prior),raw);select(owner.state);nextf=owner.state.campaign.next_fixture
            fixture=Fixture(nextf.side_a,nextf.side_b,int(nextf.fixture_id.split(':')[1]),nextf.kind)
            pub=WatchedPublication(owner) if fixture.kind==1 else publication(owner)
            job=pub.begin(fixture)
            result=run_watched_match(job.state,raw,fixture) if fixture.kind==1 else run(job.state,raw,fixture)
            pub.complete(job.token,result);outcomes.append(owner.state)
        self.assertEqual(outcomes[0],outcomes[1])
        # [designed] The actual next row is friendly: explicit quick continuation keeps competitive history.
        self.assertEqual(after.campaign.next_fixture.kind,1)
        from goal2.desktop.worker import play
        quick=[]
        for prior in (after,restored):
            candidate=copy.deepcopy(prior);select(candidate)
            try:quick.append(play(candidate,raw))
            except ValueError as exc:self.fail('next actual friendly cannot run after original competitive completion: '+str(exc))
        self.assertEqual(quick[0],quick[1]);self.assertNotIn('engine',quick[0].last_match)
        quick_saved=session_save.encode(quick[0],raw)
        self.assertEqual(session_save.decode(quick_saved)[0],quick[0])
        self.assertEqual(quick[0].campaign.results[2]['resolution'],row['resolution'])
        self.assertEqual(quick[0].mem,out.memory)
        report=ROOT/'.cache'/('T51-actual-qualifier-'+str(time.time_ns())+'.json')
        report.write_text(json.dumps({'source':'424d5998076da1e4efc399c2715689ddb44d3e1a',
            'fixture':{'first':f.first,'second':f.second,'index':f.index,'kind':f.kind},
            'managed':4,'budget':[5,5],'captain':declared_input.captain,'eleven':declared_input.starting_eleven,
            'policy':'play_on','reference_seed':None,'delay_byte':None,
            'engine_year':0,'base_year':1990,'stage':5,'class':1,'next_free':2001,
            'template_sha256':hashlib.sha256(raw).hexdigest(),'image_sha256':out.result['image_sha256'],
            'result_sha256':hashlib.sha256(json.dumps(out.result,sort_keys=True).encode()).hexdigest(),
            'memory_sha256':hashlib.sha256(out.memory).hexdigest(),'seeds':list(out.seeds),
            'resolution':row['resolution'],'independent_package':str(Path(independent.__file__).relative_to(ROOT)),
            'full_result_memory_equal':True,'guest_stamps_order_equal':True,
            'next_original_and_quick_deterministic':True},indent=2)+'\n')
        print('T51 actual qualifier evidence '+str(report.relative_to(ROOT)),flush=True)
        print(f'T51 actual country4 qualifier kind={f.kind} index={f.index} score={out.result["score"]} winner={out.result["winner"]} next deterministic PASS',flush=True)

    @requires.need(slow=True)  # [designed: #275] about 50 s alone on 32 CPUs
    def test_no_world_compact_resolution_survives_later_friendly_and_rejects_damage(self):
        s,raw,f=campaign();s.campaign.fixtures+=(Scheduled('original:43',1,1,2,1,7,19),Scheduled('original:44',1,1,2,1,7,19))
        owner=Owner(s,raw);pub=publication(owner)
        try:job=pub.begin(f)
        except ValueError as exc:self.fail('competitive history unavailable: '+str(exc))
        pub.complete(job.token,copy.deepcopy(completed()))
        history=copy.deepcopy(owner.state.campaign.results[0])
        from goal2.desktop.worker import play
        quick=copy.deepcopy(owner.state);retained_memory=quick.mem
        for _ in range(2):
            select(quick);quick=play(quick,raw)
            self.assertEqual(quick.mem,retained_memory)
            self.assertEqual(quick.campaign.results[0],history)
            self.assertEqual(session_save.decode(session_save.encode(quick,raw))[0],quick)
        select(owner.state)
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

    def test_quick_setup_is_private_and_preserves_strict_template_refusals(self):
        from goal2.engine.savestate import Savestate
        from goal2.engine.quick_engine import ExtraTimeNotModelled
        from goal2.game.state import to_savestate
        from goal2.game.quick_match import resolve_full_matchup
        from goal2.game import quick_match
        _friendly_input=getattr(quick_match,'_friendly_input',lambda template,state:template)
        s,raw,f=campaign();s.campaign.fixtures+=(Scheduled('original:43',1,1,2,1,7,19),Scheduled('original:44',1,1,2,1,7,19))
        owner=Owner(s,raw);pub=publication(owner)
        try:job=pub.begin(f)
        except ValueError as exc:self.fail('competitive preparation unavailable: '+str(exc))
        pub.complete(job.token,copy.deepcopy(completed()));select(owner.state)
        adapted=Savestate(to_savestate(owner.state,original=raw));before=copy.deepcopy(owner.state)
        original_memory=bytes(adapted.mem)
        try:teams,side,opponent=resolve_full_matchup(adapted,owner.state)
        except (ValueError,ExtraTimeNotModelled) as exc:self.fail('validated next friendly setup unavailable: '+str(exc))
        self.assertEqual(teams,(7,19));self.assertEqual(side,0);self.assertEqual(opponent,19)
        private=_friendly_input(adapted,owner.state)
        self.assertIsNot(private,adapted);self.assertEqual(adapted.mem,original_memory);self.assertEqual(owner.state,before)
        self.assertEqual(tuple(private.ds_bytes(o,1)[0] for o in (0x9A3D,0x8319,0x7C36)),(0,45,0))
        self.assertEqual(private.ds_bytes(0x831A,1),adapted.ds_bytes(0x831A,1))
        differences=[i for i,(a,b) in enumerate(zip(adapted.mem,private.mem)) if a!=b]
        self.assertEqual(differences,[adapted.program().ds_base+0x78+o for o in sorted((0x7C36,0x8319,0x9A3D))])
        # [designed] Ordinary quick campaigns must still run without importing optional Unicorn.
        child_code="""
import builtins,sys
from pathlib import Path
original_import=builtins.__import__
def guarded(name,*args,**kwargs):
    if name=='unicorn' or name.startswith('unicorn.'):raise ImportError('optional runtime intentionally unavailable')
    return original_import(name,*args,**kwargs)
builtins.__import__=guarded
from goal2.data.goaldat import load
from goal2.game.campaign_schedule import start_opening_campaign
from goal2.desktop.worker import play
root=Path.cwd();raw=(root/'.cache/e010-r0008-halftime.sav').read_bytes()
s,_=start_opening_campaign(load((root/'.cache/GOAL.DAT').read_bytes()),raw,managed_country=4,start_year=1990,seed_7b62=4660,seed_8336=33590)
after=play(s,raw)
assert after.match_count==1
assert 'goal2.engine.original_match' not in sys.modules
print('PASS ordinary quick campaign with optional runtime unavailable')
"""
        child=subprocess.run([sys.executable,'-B','-c',child_code],cwd=ROOT,capture_output=True,text=True,timeout=30)
        self.assertEqual(child.returncode,0,child.stdout+child.stderr)

        for damage in ('identity','resolution','unrelated_template','kickoff','unsupported_next','standalone','retained_modes'):
            state_bad=copy.deepcopy(owner.state);input_bad=copy.copy(adapted)
            if damage=='identity':state_bad.last_match['engine']='unknown'
            elif damage=='resolution':state_bad.campaign.results[0].pop('resolution')
            elif damage in ('unrelated_template','kickoff'):
                memory=bytearray(input_bad.mem);off=0x831A if damage=='kickoff' else 0x7B62
                memory[input_bad.program().ds_base+0x78+off]^=0x7F;input_bad.mem=bytes(memory)
            elif damage=='retained_modes':
                image=Image(state_bad.mem);image.memory[image.DS*16+0x9A3D]=77;state_bad.mem=image.memory_component()
                input_bad=Savestate(to_savestate(state_bad,original=raw))
            elif damage=='unsupported_next':
                state_bad.campaign.fixtures=(state_bad.campaign.fixtures[0],Scheduled('original:43',1,1,2,200,7,19))
            else:state_bad.campaign=None;state_bad.last_match=None
            with self.subTest(damage=damage),self.assertRaises((ValueError,ExtraTimeNotModelled)):
                resolve_full_matchup(input_bad,state_bad)
            self.assertEqual(owner.state,before)


if __name__=='__main__':unittest.main()
