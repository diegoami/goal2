"""[designed: T51a] Pure profile/ledger controls; real pre-upgrade save evidence is checked separately."""
import copy
from types import SimpleNamespace
import unittest
from unittest.mock import patch
from goal2.game import watched_schema as schema
from goal2.game import watched_publication as publication
from goal2.game.campaign_rounds import World, Scheduled
from goal2.game.watched_match import WatchedOutcome
from goal2.engine.original_match import Fixture

LEGACY_ID='original-match:3656a2d26e0f57a410d648edeaa6cd9eb7d1f607:1'
CURRENT_ID='original-match:424d5998076da1e4efc399c2715689ddb44d3e1a:2'


def result(kit='2'):
    value=dict(first=1,second=2,managed=1,index=1,score=[0,0],half_time_score=[0,0],goals=[],
        goals_disallowed=[],goal_counts=[0,0],bookings=[],sendings_off=[],injuries=[],substitutions=[],
        man_of_the_match=1,man_of_the_match_name='Player',commentary=[],decisions=[],inputs=[],
        ticks=0,kickoff_seed=1,seed_after=1,image_sha256='a'*64,kit=kit,draws=0,draws_digest=None,
        squads_after={'1':list(range(1,21)),'2':list(range(21,41))})
    value['board']=dict(statistics={key:[0,0] for key in ('corners','free_kicks','penalties','shots',
        'on_target','saves','fouls','bookings','red_cards','injuries')},bars=[[0,0],[0,0]],
        man_of_the_match=1,final_score=[0,0],screen_sha256='b'*64,ticks=0,seed=1)
    if kit=='2':
        value.update(kind=1,winner=2,score_90=None,extra_time=False,substitution_budget=[5,5],shootout=None,
            players=[dict(player=w,team=int(w>20),confidence=[0,0],energy=[100,100],status=[0,0],
                          suspended=False,carried_booking=False,injured=False) for w in range(1,41)])
    return value


class FakeImage:
    def year(self):return 0
    def sha256(self):return 'a'*64
    def players(self):return [b'p']*41
    def countries(self):return [bytes(191)]*3
    def squad(self,country):return list(range(1,21)) if country==1 else list(range(21,41))
    def rd(self,offset):return {0x7B62:1,0x8336:2}[offset]
    def rd_far(self,pointer,offset):return {4:1,6:2}[offset]
    def fixture_index(self):return 1


class KitIdentityTests(unittest.TestCase):
    def test_exact_profiles_keep_actual_engine_identity(self):
        for kit,engine in (('1',LEGACY_ID),('2',CURRENT_ID)):
            raw=result(kit);before=copy.deepcopy(raw)
            self.assertEqual(schema.validate_result(raw),engine)
            self.assertEqual(raw,before)
            for change in ('unknown','wrong_kit','missing'):
                damaged=copy.deepcopy(raw)
                if change=='unknown':damaged['unknown']=True
                elif change=='wrong_kit':damaged['kit']='9'
                else:damaged.pop('board')
                with self.assertRaises(ValueError):schema.validate_result(damaged)
        forged=result('2');forged['kit']='1'
        with self.assertRaises(ValueError):schema.validate_result(forged)
        forged=result('1');forged['kit']='2'
        with self.assertRaises(ValueError):schema.validate_result(forged)

    def test_kit2_remains_friendly_with_exact_default_resolution_and_players(self):
        self.assertEqual(schema.validate_result(result()),CURRENT_ID)
        for key,value in (('kind',2),('kind',True),('winner',0),('winner',True),('extra_time',True),
                          ('score_90',[0,0]),('shootout',{}),('substitution_budget',[5,2]),
                          ('substitution_budget',[5.0,5]),('players',[])):
            damaged=result();damaged[key]=value
            with self.subTest(key=key,value=value),self.assertRaises(ValueError):schema.validate_result(damaged)
        for mutate in (lambda p:p[0].__setitem__('suspended',True),lambda p:p[0].__setitem__('team',1),
                       lambda p:p[0].__setitem__('energy',[100,-1]),lambda p:p[0].__setitem__('injured',True),
                       lambda p:p[1].__setitem__('player',1),lambda p:p[0].__setitem__('extra',0)):
            damaged=result();mutate(damaged['players'])
            with self.assertRaises(ValueError):schema.validate_result(damaged)

    def test_publication_uses_actual_result_profile_and_save_rejects_relabeling(self):
        for kit,engine in (('1',LEGACY_ID),('2',CURRENT_ID)):
            raw=result(kit);image=FakeImage()
            state=SimpleNamespace(managed_country=1,match_count=0,campaign=None,match_state={})
            outcome=WatchedOutcome(raw,b'memory',(SimpleNamespace(kind='full_time'),SimpleNamespace(kind='end')),(1,2),0)
            with patch.object(publication,'prepare_watched',return_value=image), \
                 patch.object(publication.Image,'from_memory_component',return_value=image), \
                 patch.object(schema,'_returned_image',return_value=image):
                candidate=publication.completed_candidate(state,Fixture(1,2,1),outcome,b'template')
                self.assertEqual(candidate.last_match['engine'],engine)
                self.assertEqual(candidate.last_match['original'],raw)
                before=copy.deepcopy(candidate)
                schema.validate_saved_watched(candidate)
                self.assertEqual(candidate,before)
                history=dict(fixture_id='original:1',teams=[1,2],score=[0,0],engine=engine,schema=1)
                candidate.campaign=SimpleNamespace(world=None,results=[history])
                schema.validate_saved_watched(candidate)
                other=CURRENT_ID if kit=='1' else LEGACY_ID
                history['engine']=other
                with self.assertRaisesRegex(ValueError,'history'):schema.validate_saved_watched(candidate)
                history['engine']=engine
                row=dict(history,mode='watched',seed_after=1,secondary_after=2,engine_year=0,index=1)
                candidate.campaign.world=SimpleNamespace(results=[row])
                schema.validate_saved_watched(candidate)
                row['engine']=other
                with self.assertRaisesRegex(ValueError,'continuation'):schema.validate_saved_watched(candidate)
                candidate.campaign=None
                candidate.last_match['engine']=CURRENT_ID if kit=='1' else LEGACY_ID
                with self.assertRaisesRegex(ValueError,'profile'):schema.validate_saved_watched(candidate)

    def test_mixed_history_world_preserves_identity_and_strict_quick_rng(self):
        fixtures=tuple(Scheduled(f'original:{n}',1,1,2,n) for n in (1,2))
        history=[];rows=[]
        for n,engine in enumerate((LEGACY_ID,CURRENT_ID),1):
            history.append(dict(fixture_id=f'original:{n}',teams=[1,2],score=[0,0],engine=engine,schema=1))
            rows.append(dict(fixture_id=f'original:{n}',teams=[1,2],score=[0,0],winner=2,mode='watched',engine=engine,
                schema=1,seed_before=n-1,seed_after=n,secondary_after=2,engine_year=0,index=n,setup_seed=n))
        campaign=SimpleNamespace(start_year=1992,fixtures=[SimpleNamespace(**vars(f),cycle=1,stage=2) for f in fixtures],
            completed_fixture_ids=['original:1','original:2'],results=history)
        world=World(1,0,fixtures,rows)
        self.assertEqual(world.validate(campaign),2)
        before=copy.deepcopy(rows)
        rows[0]['engine']=CURRENT_ID
        with self.assertRaisesRegex(ValueError,'score differs'):world.validate(campaign)
        rows[:]=before
        rows[0]['engine']='unknown'
        with self.assertRaises(ValueError):world.validate(campaign)
        rows[:]=copy.deepcopy(before)
        rows[0]={key:rows[0][key] for key in ('fixture_id','teams','score','winner','mode','seed_before','seed_after')}
        rows[0].update(mode='managed',draws=1)
        history[0]={key:history[0][key] for key in ('fixture_id','teams','score')}
        with self.assertRaisesRegex(ValueError,'RNG chain'):world.validate(campaign)


if __name__=='__main__':unittest.main()
