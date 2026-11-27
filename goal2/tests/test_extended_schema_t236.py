"""T236: genuine SDK results, explicit selected membership and strict old guards."""
import copy
from dataclasses import FrozenInstanceError, replace
import unittest

from goal2.engine.original_match import Fixture
from goal2.game import extended_squad, campaign_pool
from goal2.game.extended_match import prepare_extended_watched
from goal2.game.watched_match import sealed
from goal2.game.watched_schema import validate_result, validate_player_records
from goal2.tests import requires, pypy_engine
from goal2.tests.test_assistant_pipe_t183c import model


def schema():
    from goal2.game import extended_schema
    return extended_schema


def actual_case(state,original,fixture,count):
    import sys
    from goal2.engine.original_match import Match
    assert sys.implementation.name=='pypy'
    before=copy.deepcopy(state)
    state=extended_squad.resized(state,22)
    pool=campaign_pool.validate(state);pairs=[]
    def available(w):
        record=state.players[w]
        return 0<record[14]<128 and not record[16]&0xA4
    for off in reversed(state.starting_eleven):
        if len(pairs)==count:break
        if state.players[off][6]==0 or not available(off):continue
        on=next((w for w in pool if available(w) and state.players[w][6]==state.players[off][6]
                 and w not in [p[1] for p in pairs]),None)
        if on is not None:pairs.append((off,on))
    assert len(pairs)==count
    state.extra_squad=[p[1] for p in pairs]+[None]*(state.squad_capacity-20-count)
    prepared,extras=prepare_extended_watched(state,original,fixture);image=sealed(prepared)
    kwargs=dict(managed=state.managed_country,captain=state.captain or None,
                engine='port',live_players=True,substitutions=255)
    if extras:kwargs['extra_players']=list(extras)
    m=Match(image,fixture,**kwargs);stream=iter(m.events());events=[]
    for event in stream:
        events.append(event)
        if event.kind=='decision':
            if event.data['context']=='half_time':break
            m.answer(quick=True)
    else:raise AssertionError('missing original halftime decision')
    waiting=copy.deepcopy(event.data)
    # [confirmed: SDK Match._flush] Completed swaps are paired in physical XI
    # order, not caller-list order. Choose that order; keep the exact assertion.
    pairs.sort(key=lambda pair:waiting['eleven'].index(pair[0]))
    m.answer(substitutions=pairs,quick=True)
    for event in stream:
        events.append(event)
        if event.kind=='decision':m.answer(quick=True)
    result=m.result()
    ours=[row for row in result['substitutions'] if row['team']==m.side]
    assert [(r['off'],r['on']) for r in ours]==pairs, ('native pairs',[(r['off'],r['on']) for r in ours],pairs)
    from goal2.engine.original_match import screens as S
    assert m.m.rd(S.SUBS_LEFT+m.side,1)==255-count
    assert all(on in m._squad(state.managed_country)[:11] for off,on in pairs)
    assert len(result['players'])==40+count, ('physical union',len(result['players']),count,result.get('national_squad_after'))
    assert events[-1].kind=='end' and state.players==before.players
    return dict(state=state,fixture=fixture,decision=waiting,result=result,pairs=pairs,
                input_hash=image.sha256())


@requires.need(**requires.HALFTIME)
class ExtendedProfiles(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.model=model();cls.samples={}

    def sample(self,count):
        if count not in self.samples:
            s=self.model.state;f=s.campaign.next_fixture
            fixture=Fixture(f.side_a,f.side_b,index=int(f.fixture_id.split(':')[1]),kind=f.kind)
            self.samples[count]=pypy_engine.call(__name__+':actual_case',s,self.model.template_bytes,fixture,count)
            print('T236_NATIVE',count,len(self.samples[count]['result']['players']),flush=True)
        return self.samples[count]

    def selection(self,sample):
        image,_=prepare_extended_watched(sample['state'],self.model.template_bytes,sample['fixture'])
        result=schema().ExtendedSelection.from_prepared(sample['state'],sample['fixture'],sealed(image))
        self.assertEqual(result.image_sha256,sample['input_hash'])
        return result

    def test_empty_larger_capacity_keeps_the_exact_default_result_profile(self):
        api=schema();sample=self.sample(0);selection=self.selection(sample)
        before=copy.deepcopy(sample['result']);legacy=validate_result(before)
        checked=api.validate_extended_result(before,selection)
        self.assertEqual(checked.engine,legacy);self.assertEqual(len(checked.consequence_words),40)
        self.assertNotIn('national_squad_after',before)
        bad=copy.deepcopy(before);bad['national_squad_after']=list(selection.core)
        self.assertRaises(ValueError,api.validate_extended_result,bad,selection)
        self.assertEqual(sample['result'],before)

    def test_all_partial_full_bench_cards_are_detached_and_old_limit_stays_strict(self):
        api=schema()
        for count in (1,2):
            with self.subTest(count=count):
                sample=self.sample(count);selection=self.selection(sample);data=copy.deepcopy(sample['decision'])
                before=copy.deepcopy(data);view=api.validate_extended_decision(data,selection)
                self.assertEqual(len(view.bench),9+count);self.assertEqual(len(view.records),20+count)
                self.assertEqual(set(view.national),set(selection.selected))
                self.assertEqual(data,before)
                self.assertRaises(ValueError,validate_player_records,data,required=True)
                data['player_records'][0][1]='00'*20
                self.assertNotEqual(view.records[0][1],bytes(20))
                self.assertRaises(FrozenInstanceError,setattr,view,'bench',())

    def test_actual_full_consequence_union_retains_truthful_absence_and_native_effects(self):
        api=schema()
        for count in (1,2):
            with self.subTest(count=count):
                sample=self.sample(count);selection=self.selection(sample);result=sample['result'];before=copy.deepcopy(result)
                checked=api.validate_extended_result(result,selection)
                self.assertEqual(len(checked.consequence_words),40+count)
                self.assertEqual(sum(r['status'][0] is None for r in result['players']),count)
                self.assertEqual(sum(r['status'][1] is None for r in result['players']),count)
                self.assertEqual(set(checked.national),set(selection.selected));self.assertEqual(len(checked.native),20)
                self.assertEqual(result,before);self.assertRaises(ValueError,validate_result,result)
                self.assertRaises(FrozenInstanceError,setattr,checked,'national',())

    def test_result_mutations_cannot_widen_membership_presence_flags_or_identity(self):
        api=schema();sample=self.sample(2);selection=self.selection(sample);original=sample['result'];cases=[]
        def changed(fn):
            r=copy.deepcopy(original);fn(r);cases.append(r)
        changed(lambda r:r.update(image_sha256='0'*64));changed(lambda r:r.update(kind=True))
        changed(lambda r:r.update(unexpected=1));changed(lambda r:r['national_squad_after'].reverse())
        changed(lambda r:r['national_squad_after'].pop());changed(lambda r:r['national_squad_after'].__setitem__(-1,1))
        changed(lambda r:r['players'].append(copy.deepcopy(r['players'][0])))
        changed(lambda r:r['players'][0].update(team=True))
        changed(lambda r:r['players'][0]['confidence'].__setitem__(0,(r['players'][0]['confidence'][0]+1)%256))
        changed(lambda r:next(row for row in r['players'] if row['status'][0] is None)['status'].__setitem__(0,0))
        changed(lambda r:next(row for row in r['players'] if row['status'][1] is None)['energy'].__setitem__(1,0))
        changed(lambda r:r['players'][0].update(injured=not r['players'][0]['injured']))
        changed(lambda r:r['players'][0]['status'].__setitem__(1,True))
        changed(lambda r:r['squads_after'][str(selection.managed)].__setitem__(0,1))
        for i,result in enumerate(cases):
            before=copy.deepcopy(result)
            with self.subTest(case=i),self.assertRaises(ValueError):api.validate_extended_result(result,selection)
            self.assertEqual(result,before)

    def test_decision_mutations_cannot_forge_card_order_side_or_selected_group(self):
        api=schema();sample=self.sample(2);selection=self.selection(sample);original=sample['decision'];cases=[]
        def changed(fn):
            r=copy.deepcopy(original);fn(r);cases.append(r)
        changed(lambda r:r['bench'].pop());changed(lambda r:r['eleven'].__setitem__(0,r['eleven'][1]))
        changed(lambda r:r['national_squad'].reverse());changed(lambda r:r['player_records'].reverse())
        changed(lambda r:r['player_records'][0].__setitem__(0,True))
        changed(lambda r:r['player_records'][0].__setitem__(1,'ff'))
        changed(lambda r:r['team_context'].update(sides=[128,127]))
        changed(lambda r:r['team_context'].update(match_set_up=True))
        changed(lambda r:r.pop('team_context'))
        changed(lambda r:r.update(substitutions_left=True))
        changed(lambda r:r['positions'][0].__setitem__(1,255))
        changed(lambda r:r.update(context='invented'))
        for i,data in enumerate(cases):
            before=copy.deepcopy(data)
            with self.subTest(case=i),self.assertRaises(ValueError):api.validate_extended_decision(data,selection)
            self.assertEqual(data,before)

    def test_selection_context_is_immutable_typed_and_bound_to_prepared_records(self):
        api=schema();sample=self.sample(2);selection=self.selection(sample)
        for fields in ({'capacity':True},{'image_sha256':'bad'},{'core':(selection.core[0],)*20},
                       {'extras':(True,)},{'before':selection.before[:-1]}):
            with self.subTest(fields=tuple(fields)),self.assertRaises(ValueError):replace(selection,**fields)
        self.assertRaises(FrozenInstanceError,setattr,selection,'core',())
        self.assertRaises(ValueError,api.validate_extended_result,sample['result'],None)
        image,_=prepare_extended_watched(sample['state'],self.model.template_bytes,sample['fixture'])
        wrong=copy.deepcopy(sample['state']);row=bytearray(wrong.players[selection.core[0]]);row[12]^=1
        wrong.players[selection.core[0]]=bytes(row)
        self.assertRaises(ValueError,api.ExtendedSelection.from_prepared,wrong,sample['fixture'],sealed(image))


if __name__=='__main__':unittest.main()
