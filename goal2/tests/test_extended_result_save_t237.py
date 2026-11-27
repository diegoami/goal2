"""T237: actual selected-bench results round-trip through an explicit save profile."""
import copy
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from goal2.engine.original_match import Image
from goal2.game import extended_squad
from goal2.game.extended_schema import ExtendedSelection,validate_extended_result
from goal2.game.session_save import encode,decode,save,SessionSaveError
from goal2.game.watched_match import prepare_watched,sealed,_complete_memory
from goal2.game.watched_schema import validate_saved_watched,resolution
from goal2.tests import pypy_engine
from goal2.tests.test_campaign_competitive_publication import campaign

ROOT=Path(__file__).resolve().parents[2]


def codec():
    from goal2.game import extended_save
    return extended_save


def actual_saved(state,raw,fixture,count,competitive):
    """Observe the accepted real SDK constructor; never replace execution/options."""
    import goal2.engine.original_match as package
    from goal2.tests.test_extended_schema_t236 import actual_case
    from goal2.tests.test_extended_schema_competitive_t236 import actual_competitive
    real=package.Match;observed=[]
    def observe(image,actual_fixture,**options):
        extras=tuple(options.get('extra_players',()))
        owner=extended_squad.resized(state,22)
        # Explicit owner presentation metadata; the exact SDK input is its filled order.
        owner.extra_squad=([None,extras[0]] if len(extras)==1 else
                           list(extras)+[None]*(owner.squad_capacity-20-len(extras)))
        selection=ExtendedSelection.from_prepared(owner,actual_fixture,image)
        profile=codec().to_data(selection,owner.extra_squad)
        match=real(image,actual_fixture,**options)
        observed.append((match,owner,selection,profile));return match
    with patch.object(package,'Match',new=observe):
        if competitive:
            selection,waiting,result=actual_competitive(state,raw,fixture)
        else:
            sample=actual_case(state,raw,fixture,count);result=sample['result']
    assert len(observed)==1
    match,initial,selection,profile=observed[0]
    assert isinstance(match,real) and match.result()==result
    image,_=__import__('goal2.game.extended_match',fromlist=['prepare_extended_watched']).prepare_extended_watched(
        initial,raw,fixture,competitive=competitive)
    memory=_complete_memory(match.memory_component(),image);after=Image(memory)
    checked=validate_extended_result(result,selection,competitive=competitive)
    candidate=copy.deepcopy(initial);candidate.mem=memory
    candidate.players=after.players();candidate.countries=after.countries()
    candidate.managed_squad=after.squad(initial.managed_country)
    candidate.starting_eleven=candidate.managed_squad[:11]
    for row in result['substitutions']:
        if row['team']==selection.side and candidate.captain==row['off']:candidate.captain=row['on']
    assert not candidate.captain or candidate.captain in candidate.starting_eleven
    candidate.campaign.reserve_ids=match._pool()
    remaining=iter(checked.national[20:])
    candidate.extra_squad=[None if w is None else next(remaining) for w in initial.extra_squad]
    assert next(remaining,None) is None
    candidate.country_tactics=candidate.countries[candidate.managed_country][0x2D]
    candidate.rng_seed_7b62=after.rd(0x7B62);candidate.rng_seed_8336=after.rd(0x8336)
    candidate.match_count+=1
    schema=2 if competitive else 1
    candidate.last_match=dict(engine=checked.engine,schema=schema,original=copy.deepcopy(result),
        teams=[fixture.first,fixture.second],score=list(result['score']),goals=copy.deepcopy(result['goals']),
        managed_side=selection.side,match_count=candidate.match_count,
        seeds=[candidate.rng_seed_7b62,candidate.rng_seed_8336],engine_year=image.year(),selected_bench=profile)
    candidate.match_state.update(score=tuple(result['score']),minute=90,half=2)
    compact=resolution(result) if competitive else None
    candidate.campaign.complete_fixture(f'original:{fixture.index}',resolution=compact)
    row=dict(fixture_id=f'original:{fixture.index}',teams=[fixture.first,fixture.second],
             score=list(result['score']),engine=checked.engine,schema=schema)
    if competitive:row['resolution']=compact
    candidate.campaign.results.append(row)
    return candidate,profile


class SelectedResultSaves(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.samples={}

    def sample(self,count=2,competitive=False):
        key=(count,competitive)
        if key not in self.samples:
            state,raw,fixture=campaign(index=42,kind=2 if competitive else 1)
            state.captain=state.starting_eleven[-1]
            candidate,profile=pypy_engine.call(__name__+':actual_saved',state,raw,fixture,count,competitive)
            self.samples[key]=(candidate,raw,profile)
            print('T237_NATIVE',count,competitive,len(candidate.last_match['original']['players']),flush=True)
        return copy.deepcopy(self.samples[key])

    def test_profile_codec_is_exact_detached_and_preserves_nullable_slot_positions(self):
        api=codec();state,raw,data=self.sample(1)
        selection,slots=api.from_data(data);before=copy.deepcopy(data)
        self.assertEqual(slots[0],None);self.assertIsNotNone(slots[1])
        encoded=api.to_data(selection,slots);self.assertEqual(encoded,data)
        encoded['core'].reverse();self.assertEqual(api.to_data(selection,slots),before)
        self.assertEqual(data,before);self.assertEqual(state.last_match['selected_bench'],before)
        moved=copy.deepcopy(data);moved['slots'].reverse()
        moved_selection,moved_slots=api.from_data(moved)
        self.assertEqual(api.to_data(moved_selection,moved_slots),moved)

    def test_actual_empty_partial_full_friendly_competitive_version6_roundtrip(self):
        codec()
        for count,competitive in ((0,False),(1,False),(2,False),(2,True)):
            with self.subTest(count=count,competitive=competitive):
                state,raw,_=self.sample(count,competitive);before=copy.deepcopy(state)
                saved=encode(state,raw);doc=json.loads(saved)
                self.assertEqual(doc['version'],6)
                restored,template=decode(saved)
                self.assertEqual(restored,state);self.assertEqual(template,raw);self.assertEqual(state,before)
                self.assertEqual(len(state.managed_squad),20);self.assertEqual(len(state.campaign.reserve_ids),80)
                self.assertEqual(len(set(state.managed_squad+state.campaign.reserve_ids)),100)
                self.assertEqual(state.starting_eleven,state.managed_squad[:11])

    def test_retained_profile_survives_live_shrink_growth_names_and_management_edits(self):
        codec();state,raw,_=self.sample();original=copy.deepcopy(state.last_match)
        for capacity in (20,22):
            with self.subTest(capacity=capacity):
                live=extended_squad.resized(state,capacity)
                live.manager_name='Coach';live.player_renames[live.managed_squad[0]]='Selected'
                record=bytearray(live.players[live.managed_squad[0]]);record[12]^=1
                live.players[live.managed_squad[0]]=bytes(record)
                doc=json.loads(encode(live,raw));self.assertEqual(doc['version'],6)
                self.assertEqual('extended_squad' in doc['state'],capacity!=20)
                restored,_=decode(json.dumps(doc).encode())
                self.assertEqual(restored,live);self.assertEqual(restored.last_match,original)

    def test_invalid_profile_fields_and_wrong_versions_refuse_purely(self):
        api=codec();state,raw,profile=self.sample(1);cases=[]
        def change(fn):
            data=copy.deepcopy(profile);fn(data);cases.append(data)
        change(lambda d:d.update(profile='unknown'));change(lambda d:d.update(unexpected=1))
        change(lambda d:d.update(capacity=True));change(lambda d:d.pop('before'))
        change(lambda d:d['core'].__setitem__(0,d['core'][1]))
        change(lambda d:d['before'][0].__setitem__(2,'00'))
        change(lambda d:d['before'][0].__setitem__(1,True))
        change(lambda d:d['slots'].__setitem__(0,True));change(lambda d:d.update(slots=[None,None]))
        change(lambda d:(d['extras'].__setitem__(0,1),d['slots'].__setitem__(1,1)))
        for i,data in enumerate(cases):
            before=copy.deepcopy(data)
            with self.subTest(case=i),self.assertRaises(ValueError):api.from_data(data)
            self.assertEqual(data,before)
        doc=json.loads(encode(state,raw))
        for version in (1,2,3,4,5):
            bad=copy.deepcopy(doc);bad['version']=version
            with self.subTest(version=version),self.assertRaises(SessionSaveError):decode(json.dumps(bad).encode())
        shrunk=extended_squad.resized(state,20);bad=json.loads(encode(shrunk,raw));bad['version']=3
        with self.assertRaisesRegex(SessionSaveError,'version6'):decode(json.dumps(bad).encode())
        empty,raw,_=self.sample(0);empty=extended_squad.resized(empty,20);empty.last_match.pop('selected_bench')
        bad=json.loads(encode(empty,raw));bad['version']=6
        with self.assertRaisesRegex(SessionSaveError,'version6'):decode(json.dumps(bad).encode())

    def test_returned_pool_native_records_seed_and_fixture_corruption_cannot_replace_save(self):
        codec();state,raw,_=self.sample();cases=[]
        for variant in ('pool','native','seed','fixture','record','absence'):
            bad=copy.deepcopy(state);image=Image(bad.mem)
            if variant=='pool':
                at=image.far(0xA927)+2*image.rd(0x6D1A);image.memory[at:at+2]=bad.managed_squad[0].to_bytes(2,'little')
            elif variant=='native':
                at=image.far(0xA917)+191*bad.managed_country;image.memory[at:at+2]=bytes(2)
            elif variant=='seed':image.memory[image.DS*16+0x8336]^=1
            elif variant=='fixture':image.memory[image.far(0xA92B)+8*41+4]^=1
            elif variant=='record':
                at=image.far(0xA91B)+20*bad.managed_squad[0]+12;image.memory[at]^=1
            else:
                row=next(r for r in bad.last_match['original']['players'] if r['status'][1] is None)
                row['status'][1]=0
            bad.mem=image.memory_component();cases.append((variant,bad))
        with tempfile.TemporaryDirectory() as directory:
            target=Path(directory)/'career.g2save';save(target,state,raw);original=target.read_bytes()
            for variant,bad in cases:
                before=copy.deepcopy(bad)
                with self.subTest(variant=variant),self.assertRaises(SessionSaveError):save(target,bad,raw)
                self.assertEqual(target.read_bytes(),original);self.assertEqual(bad,before)

    def test_versions_one_to_five_default_writers_remain_byte_identical(self):
        codec()
        import hashlib
        metadata=json.loads((ROOT/'measurements/T237/before-source.json').read_text())
        oldfile=ROOT/metadata['fixture']
        self.assertEqual(hashlib.sha256(oldfile.read_bytes()).hexdigest(),metadata['sha256'])
        spec=importlib.util.spec_from_file_location('t237_previous_save',oldfile);old=importlib.util.module_from_spec(spec);spec.loader.exec_module(old)
        state,raw,_=self.sample(0);normal=extended_squad.resized(state,20);normal.last_match.pop('selected_bench')
        from goal2.game.state import from_savestate
        plain=from_savestate(raw);career,_,_=campaign(index=42,kind=1)
        renamed=copy.deepcopy(normal);renamed.manager_name='Coach'
        larger=extended_squad.resized(normal,22)
        for expected,candidate in ((1,plain),(2,career),(3,normal),(4,renamed),(5,larger)):
            with self.subTest(version=expected):
                current=encode(candidate,raw);self.assertEqual(json.loads(current)['version'],expected)
                self.assertEqual(current,old.encode(candidate,raw))


if __name__=='__main__':unittest.main()
