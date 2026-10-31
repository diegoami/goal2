"""[designed: T51] Competitive adapter parity with pinned424 guest writes and independent setup."""
import copy
from dataclasses import asdict
from functools import lru_cache
import hashlib
import json
import time
import importlib.util
from pathlib import Path
import sys
import unittest
from goal2.engine.original_match import Fixture,Image,Match
from goal2.engine.original_match.assets import reference_image
from goal2.game.state import from_savestate
from goal2.game import watched_match
from goal2.tests.test_watched_adapter import direct_image
from goal2.tests import requires

ROOT=Path(__file__).resolve().parents[2]

def api():
    # [designed] Baseline exercises the existing runnable gate rather than failing an import.
    if importlib.util.find_spec('goal2.game.competitive_match'):
        from goal2.game import competitive_match
        return competitive_match
    return watched_match


def state(managed=7):
    requires.require(**requires.WATCHED)
    raw=reference_image(ROOT/'.cache');s=from_savestate(raw)
    s.managed_country=managed;s.managed_squad=Image(s.mem).squad(managed)
    s.starting_eleven=s.managed_squad[:11];s.captain=0  # [confirmed: E034] Original captain pick, no override.
    s.country_tactics=s.countries[managed][0x2D]
    return s,raw


def run(s,raw,f,**options):
    fn=getattr(api(),'run_competitive_match',watched_match.run_watched_match)
    return fn(s,raw,f,**options)


@lru_cache(maxsize=None)
def independent_runtime():
    """[designed] Load an isolated exact export, never a global original_match alias."""
    sys.path.insert(0,str(ROOT/'tools'))
    from watched_evidence import stage,IMAGES
    requires.require(files=tuple(IMAGES),archaeology=True)
    folder=stage();package=folder/'runtime/original_match'
    name='t51_accepted_original_match'
    spec=importlib.util.spec_from_file_location(name,package/'__init__.py',submodule_search_locations=[str(package)])
    module=importlib.util.module_from_spec(spec);sys.modules[name]=module;spec.loader.exec_module(module)
    if Path(module.__file__).resolve()!=(package/'__init__.py').resolve():raise AssertionError('independent package origin differs')
    if Path(sys.modules[module.Match.__module__].__file__).resolve()!=(package/'match.py').resolve():
        raise AssertionError('independent Match is not from accepted export')
    file=folder/'experiments/E034-kit-competitive/stamps_competitive.py'
    spec=importlib.util.spec_from_file_location('t51_guest_stamps',file)
    probe=importlib.util.module_from_spec(spec);spec.loader.exec_module(probe)
    return module,probe


class CompetitiveAdapterTests(unittest.TestCase):
    def test_competitive_preparation_preserves_public_friendly_gate(self):
        s,raw=state();before=copy.deepcopy(s);f=Fixture(7,19,21,2)
        fn=getattr(api(),'prepare_competitive',watched_match.prepare_watched)
        try:image=fn(s,raw,f)
        except ValueError as exc:self.fail('existing competitive source fixture is refused: '+str(exc))
        self.assertEqual(image.year(),0);self.assertEqual(s,before)
        with self.assertRaises(ValueError):watched_match.prepare_watched(s,raw,f)
        for bad in (Fixture(7,19,21,4),Fixture(7,19,0,2),Fixture(7,19,769,2),Fixture(7,7,21,2)):
            with self.subTest(fixture=bad),self.assertRaises(ValueError):fn(s,raw,bad)
        self.assertEqual(s,before)

    @requires.need(slow=True)  # [designed: #275] about 303 s alone on 32 CPUs
    def test_owner_budget_cases_match_independent_execution_and_guest_stamps(self):
        independent,probe=independent_runtime()
        report=ROOT/'.cache'/('T51-adapter-cases-'+str(time.time_ns())+'.jsonl')
        with report.open('x'):pass
        cases=[(2,21,257,False,7,[1,0],None),(2,21,None,False,7,[1,1],None),
               (200,30,None,False,7,[3,2],None),(200,42,None,False,7,[0,0],[4,3]),
               (200,9,None,True,7,[1,1],[9,10]),(200,53,None,True,7,[2,2],[3,4]),
               (200,42,None,True,19,None,None)]
        for kind,index,seed,quick,managed,score,penalties in requires.cases(cases):  # [designed: #487]
            with self.subTest(kind=kind,index=index,managed=managed,seed=seed):
                s,raw=state(managed);before=copy.deepcopy(s);fixture=Fixture(7,19,index,kind)
                options={'reference_seed':seed,'record_draws':True}
                if quick:options['quick_at_half_time']=True
                try:outcome=run(s,raw,fixture,**options)
                except (ValueError,TypeError) as exc:self.fail('competitive execution missing: '+str(exc))
                image=direct_image(s)
                original=independent.Match(independent.Image(image.memory_component()),
                    independent.Fixture(7,19,index,kind),managed=managed,captain=s.captain or None,
                    seed=seed,delay_byte=None,substitutions=(5,5),record_draws=True)
                guest=probe.Competitive(original.m);events=[]
                for event in original.events():
                    events.append((event.kind,event.minute,event.score,event.data))
                    if event.kind=='decision':
                        original.answer(quick=True) if quick and event.data['context']=='half_time' else original.answer()
                self.assertEqual(guest.expected(),probe.kit_stamps(events))
                self.assertEqual(outcome.result,original.result());self.assertEqual(outcome.memory,original.memory_component())
                self.assertEqual([asdict(e) for e in outcome.events],
                    [dict(kind=k,minute=m,score=sc,data=d) for k,m,sc,d in events])
                after=Image(outcome.memory)
                self.assertEqual(outcome.seeds,(after.rd(0x7B62),after.rd(0x8336)))
                self.assertEqual(outcome.result['substitution_budget'],[5,5]);self.assertEqual(s,before)
                if score is not None:
                    self.assertEqual(outcome.result['score'],score)
                    self.assertEqual(outcome.result['shootout'] and outcome.result['shootout']['score'],penalties)
                if index in (9,53):self.assertGreater(len(outcome.result['shootout']['kicks']),10)
                rec={'source':'424d5998076da1e4efc399c2715689ddb44d3e1a','kind':kind,'index':index,
                    'managed':managed,'captain_override':None,'budget':[5,5],'reference_seed':seed,'delay_byte':None,
                    'quick_at_half_time':quick,'engine_year':outcome.engine_year,
                    'base_year':image.rd_far(0xA923,0x3A),'stage':image.rd_far(0xA923,0x3C,1),
                    'class':image.rd_far(0xA923,0x40,1),'next_free':image.rd_far(0xA923,0x28),
                    'template_sha256':hashlib.sha256(raw).hexdigest(),'image_sha256':outcome.result['image_sha256'],
                    'result_sha256':hashlib.sha256(json.dumps(outcome.result,sort_keys=True).encode()).hexdigest(),
                    'memory_sha256':hashlib.sha256(outcome.memory).hexdigest(),
                    'events_sha256':hashlib.sha256(json.dumps([asdict(e) for e in outcome.events],sort_keys=True).encode()).hexdigest(),
                    'seeds':list(outcome.seeds),'score':outcome.result['score'],'score_90':outcome.result['score_90'],
                    'extra_time':outcome.result['extra_time'],'winner':outcome.result['winner'],
                    'penalties':outcome.result['shootout'] and outcome.result['shootout']['score'],
                    'kicks':outcome.result['shootout'] and len(outcome.result['shootout']['kicks']),
                    'incidents':{k:len(outcome.result[k]) for k in ('goals','goals_disallowed','bookings','sendings_off','injuries','substitutions')},
                    'independent_result_memory_events_equal':True,'guest_stamps_order_equal':True,
                    'independent_module':str(Path(independent.__file__).relative_to(ROOT)),
                    'independent_match_module':str(Path(sys.modules[independent.Match.__module__].__file__).relative_to(ROOT))}
                with report.open('a') as stream:stream.write(json.dumps(rec,sort_keys=True)+'\n')
                print(f'T51 kind={kind} index={index} managed={managed} seed={seed} quick={quick} result={score} actual={outcome.result["score"]} winner={outcome.result["winner"]}',flush=True)

    def test_source_context_is_explicit_and_invalid_changes_are_atomic(self):
        from goal2.tests.test_campaign_competitive_publication import campaign
        s,raw,f=campaign(21,2);fn=getattr(api(),'prepare_competitive',watched_match.prepare_watched)
        try:image=fn(s,raw,f)
        except ValueError as exc:self.fail('valid source context rejected: '+str(exc))
        game=image.far(0xA923)
        self.assertEqual((image.year(),image.rd_far(0xA923,0x3A),image.memory[game+0x3C],image.memory[game+0x40]),(0,2028,2,0))
        for change in ('managed','index','kind','endpoints','year','stage','base_year','next_free'):
            bad=copy.deepcopy(s);fixture=f
            if change=='managed':bad.managed_country=1
            elif change=='index':fixture=Fixture(7,19,22,2)
            elif change=='kind':fixture=Fixture(7,19,21,3)
            elif change=='endpoints':fixture=Fixture(19,7,21,2)
            elif change=='year':bad.campaign.year=2
            elif change=='stage':bad.campaign.stage=5
            elif change=='base_year':bad.campaign.start_year=2027
            else:
                image_bad=Image(bad.mem);image_bad.memory[game+0x28:game+0x2A]=(21).to_bytes(2,'little');bad.mem=image_bad.memory_component()
            before=copy.deepcopy(bad)
            with self.subTest(change=change),self.assertRaises(ValueError):fn(bad,raw,fixture)
            self.assertEqual(bad,before)


if __name__=='__main__':unittest.main()
