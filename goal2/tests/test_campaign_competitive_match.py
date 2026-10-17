"""[designed: T51] Competitive adapter parity with pinned424 guest writes and independent setup."""
import copy
from dataclasses import asdict
import importlib.util
from pathlib import Path
import sys
import unittest
from goal2.engine.original_match import Fixture,Image,Match
from goal2.engine.original_match.assets import reference_image
from goal2.game.state import from_savestate
from goal2.game import watched_match
from goal2.tests.test_watched_adapter import direct_image

ROOT=Path(__file__).resolve().parents[2]

def api():
    # [designed] Baseline exercises the existing runnable gate rather than failing an import.
    if importlib.util.find_spec('goal2.game.competitive_match'):
        from goal2.game import competitive_match
        return competitive_match
    return watched_match


def state(managed=7):
    raw=reference_image(ROOT/'.cache');s=from_savestate(raw)
    s.managed_country=managed;s.managed_squad=Image(s.mem).squad(managed)
    s.starting_eleven=s.managed_squad[:11];s.captain=0  # [confirmed: E034] Original captain pick, no override.
    s.country_tactics=s.countries[managed][0x2D]
    return s,raw


def run(s,raw,f,**options):
    fn=getattr(api(),'run_competitive_match',watched_match.run_watched_match)
    return fn(s,raw,f,**options)


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

    def test_owner_budget_cases_match_independent_execution_and_guest_stamps(self):
        sys.path.insert(0,str(ROOT/'tools'))
        from watched_evidence import stage
        folder=stage();file=folder/'experiments/E034-kit-competitive/stamps_competitive.py'
        spec=importlib.util.spec_from_file_location('t51_guest_stamps',file)
        probe=importlib.util.module_from_spec(spec);spec.loader.exec_module(probe)
        import original_match as independent
        cases=[(2,21,257,False,7,[1,0],None),(2,21,None,False,7,[1,1],None),
               (200,30,None,False,7,[3,2],None),(200,42,None,False,7,[0,0],[4,3]),
               (200,9,None,True,7,[1,1],[9,10]),(200,53,None,True,7,[2,2],[3,4]),
               (200,42,None,True,19,None,None)]
        for kind,index,seed,quick,managed,score,penalties in cases:
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
                print(f'T51 kind={kind} index={index} managed={managed} seed={seed} quick={quick} result={score} actual={outcome.result["score"]} winner={outcome.result["winner"]}',flush=True)


if __name__=='__main__':unittest.main()
