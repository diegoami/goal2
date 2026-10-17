"""[designed: T63] Adapter fidelity against accepted direct original execution.
[confirmed: archaeology 3656a2d26e0f57a410d648edeaa6cd9eb7d1f607, E032/E033/F025]
"""
import copy
from dataclasses import asdict
from pathlib import Path
import unittest
from unittest.mock import patch

from goal2.engine.original_match import Image, Fixture, Match
from goal2.engine.original_match.assets import reference_image
from goal2.engine.original_match.check import EXPECTED_FAMILY
from goal2.game.state import from_savestate
from goal2.game.campaign import CampaignState, Fixture as CampaignFixture
from goal2.game.watched_match import prepare_watched, run_watched_match, engine_year

ROOT = Path(__file__).resolve().parents[2]


def direct_image(state, year=None):
    """[designed] Independent field writes; deliberately does not use to_savestate/the adapter."""
    image = Image(state.mem)
    p = image.far(0xA91B)
    image.memory[p:p + 3061 * 20] = b''.join(state.players)
    p = image.far(0xA917)
    records = bytearray(b''.join(state.countries))
    squad = state.starting_eleven + [w for w in state.managed_squad if w not in state.starting_eleven]
    q = state.managed_country * 0xBF
    records[q:q + 40] = b''.join(w.to_bytes(2, 'little') for w in squad)
    records[q + 0x2D] = state.country_tactics
    image.memory[p:p + len(records)] = records
    for offset, value in ((0x7B62, state.rng_seed_7b62), (0x8336, state.rng_seed_8336)):
        p = image.DS * 16 + offset
        image.memory[p:p + 2] = value.to_bytes(2, 'little')
    if year is not None:
        p = image.far(0xA923) + 0x38
        image.memory[p:p + 2] = year.to_bytes(2, 'little')
    if state.campaign is not None:
        # [confirmed: F023/F025] Independent explicit original game-record writes.
        c=state.campaign;game=image.far(0xA923)
        image.memory[game+0x3A:game+0x3C]=c.start_year.to_bytes(2,'little')
        image.memory[game+0x3C]=c.stage
        image.memory[game+0x40]=int(c.stage>=5)
        if c.world is not None:
            next_free=max(int(f.fixture_id.split(':')[1]) for f in c.world.fixtures)+1
            image.memory[game+0x28:game+0x2A]=next_free.to_bytes(2,'little')
    return image


def direct(state, fixture, year=None, seed=None, delay=None):
    match = Match(direct_image(state, year), fixture, managed=state.managed_country,
                  captain=state.captain or None, seed=seed, record_draws=True, delay_byte=delay)
    events = []
    for ev in match.events():
        events.append(asdict(ev))
        if ev.kind == 'decision':
            match.answer()
    return match.result(), match.memory_component(), events


class WatchedAdapter(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.raw = reference_image(ROOT / '.cache')

    def state(self):
        s = from_savestate(self.raw)
        s.captain = 0  # [designed] Default original pick; +2F is an unrelated legacy placeholder.
        return s

    def compare(self, state, fixture, *, year=None, seed=None, delay=None, template=None):
        before = copy.deepcopy(state)
        expected, memory, events = direct(state, fixture, year, seed, delay)
        got = run_watched_match(state, template or self.raw, fixture, reference_seed=seed, delay_byte=delay,
                                record_draws=True)
        self.assertEqual(got.result, expected)
        self.assertEqual(got.memory, memory)
        self.assertEqual([asdict(e) for e in got.events], events)
        self.assertEqual(state, before)
        after = Image(got.memory)
        self.assertEqual(after.players(), Image(memory).players())
        self.assertEqual(after.countries(), Image(memory).countries())
        self.assertEqual(got.seeds, (after.rd(0x7B62), after.rd(0x8336)))
        self.assertEqual(got.events[-1].kind, 'end')
        self.assertTrue(any(e.kind == 'full_time' for e in got.events))
        self.assertEqual(got.engine_year, after.year())
        self.assertTrue(got.result['decisions'])
        print(f'case first={fixture.first} second={fixture.second} index={fixture.index} '
              f'year={got.engine_year} base_year={after.rd_far(0xA923,0x3A)} '
              f'stage={after.rd_far(0xA923,0x3C,1)} class={after.rd_far(0xA923,0x40,1)} '
              f'next_free={after.rd_far(0xA923,0x28)} reference_seed={seed} seeds_after={got.seeds} '
              f'decisions={[d["context"] for d in got.result["decisions"]]} PASS', flush=True)
        return got

    def test_ten_strict_t62_inputs(self):
        for seed, want in EXPECTED_FAMILY.items():
            with self.subTest(seed=hex(seed)):
                outcome = self.compare(self.state(), Fixture(7, 19, 21), seed=seed, delay=0)
                r = outcome.result
                self.assertEqual([r['score'], r['ticks'], r['draws'], r['draws_digest']], want)

    def test_year_mapping_pinned_to_f025_both_start_calendars_and_wrap(self):
        # [confirmed: F025 §2] Literal stage/word traces, independent of implementation formula.
        for start, cycle, stage, word in ((1992,1,2,0),(1992,1,3,0),(1992,1,4,0),
                (1992,1,5,1),(1992,1,6,1),(1992,1,7,1),(1992,1,8,1),(1992,2,2,2),
                (1994,1,5,0),(1994,1,6,0),(1994,1,7,0),(1994,1,8,0),
                (1994,2,2,1),(1994,2,5,2),(1992,32769,2,0)):
            c = type('Calendar', (), dict(start_year=start, cycle=cycle, stage=stage))()
            self.assertEqual(engine_year(c), word)

    def test_campaign_natural_reseed_and_source_fixture_identity(self):
        s = self.state()
        f = CampaignFixture('original:21',1,1,2,1,7,19)
        s.campaign = CampaignState(1992,1,1,2,123,78,(f,))
        a = self.compare(s,Fixture(7,19,21),year=0)
        s.rng_seed_7b62 ^= 0xFFFF
        b = self.compare(s,Fixture(7,19,21),year=0)
        self.assertEqual({k:v for k,v in a.result.items() if k not in ('image_sha256','inputs')},
                         {k:v for k,v in b.result.items() if k not in ('image_sha256','inputs')})  # [confirmed: E033] Setup replaces incoming primary RNG.
        f2 = CampaignFixture('original:22',1,3,5,1,7,19)
        s.campaign = CampaignState(1994,1,3,5,123,78,(f2,))
        c = self.compare(s,Fixture(7,19,22),year=0)
        self.assertNotEqual(a.result['kickoff_seed'], c.result['kickoff_seed'])
        schedule = tuple(CampaignFixture(f'original:{i+1}',cycle,year,stage,1,7,19)
                         for i,(cycle,year,stage) in enumerate(((1,3,5),(1,3,6),(1,4,7),(1,4,8),(2,1,2))))
        s.campaign = CampaignState(1994,2,1,2,123,78,schedule,
                                   [f.fixture_id for f in schedule[:-1]])
        self.compare(s,Fixture(7,19,5),year=1)
        s.campaign = None
        image = Image(s.mem); p = image.far(0xA923)+0x38
        image.memory[p:p+2] = (7).to_bytes(2,'little'); s.mem = image.memory_component()
        self.compare(s,Fixture(7,19,22),year=7)

    def test_real_fresh_campaigns_transfer_next_free_count_and_context(self):
        from goal2.data.goaldat import load
        from goal2.game.campaign_schedule import start_opening_campaign
        from dataclasses import replace
        template=(ROOT/'.cache/e010-r0008-halftime.sav').read_bytes()
        data=load((ROOT/'.cache/GOAL.DAT').read_bytes())
        for base_year,stage,kind_class,next_free in ((1990,5,1,2001),(1992,2,0,769)):
            state,_=start_opening_campaign(data,template,managed_country=4,start_year=base_year,
                                          seed_7b62=4660,seed_8336=33590)
            pending=state.campaign.next_fixture
            fixture=Fixture(pending.side_a,pending.side_b,int(pending.fixture_id.split(':')[1]))
            before=copy.deepcopy(state)
            prepared=prepare_watched(state,template,fixture)
            self.assertEqual(prepared.rd_far(0xA923,0x28),next_free)
            self.assertEqual(prepared.rd_far(0xA923,0x3A),base_year)
            self.assertEqual(prepared.rd_far(0xA923,0x3C,1),stage)
            self.assertEqual(prepared.rd_far(0xA923,0x40,1),kind_class)
            self.assertEqual(prepared.year(),0)
            self.compare(state,fixture,year=0,template=template)
            self.assertEqual(state,before)
            # [confirmed: F023] Aggregate rows/sentinel are not regular played fixtures.
            bad=copy.deepcopy(state);world=bad.campaign.world;rows=list(world.fixtures)
            index=next(i for i,f in enumerate(rows) if bad.managed_country not in (f.side_a,f.side_b))
            rows[index]=replace(rows[index],fixture_id='original:2401');world.fixtures=tuple(rows)
            invalid_before=copy.deepcopy(bad)
            with self.assertRaises(ValueError):prepare_watched(bad,template,fixture)
            self.assertEqual(bad,invalid_before)

    def test_changed_squad_tactics_captain_side_b_and_opaque_memory(self):
        s = self.state()
        s.starting_eleven[10] = s.managed_squad[15]
        s.captain = s.starting_eleven[4]
        s.country_tactics ^= 8
        s.match_state['clock'] = 0  # [confirmed: T62 guard] Must preserve the actual foot table.
        image = Image(s.mem); image.memory[-16:] = b'T63-opaque-tail!'; s.mem=image.memory_component()
        expected_image=direct_image(s)
        prepared=prepare_watched(s,self.raw,Fixture(19,7,21))
        self.assertEqual(prepared.memory_component(),expected_image.memory_component())
        self.assertEqual(len(set(prepared.squad(7))),20)
        got = self.compare(s,Fixture(19,7,21),seed=0x1234,delay=0)
        original = self.compare(self.state(),Fixture(19,7,21),seed=0x1234,delay=0)
        self.assertNotEqual(got.result['draws_digest'],original.result['draws_digest'])
        self.assertEqual(got.memory[-16:],b'T63-opaque-tail!')

    def test_invalid_inputs_do_not_mutate_active_state(self):
        mutations = [lambda s:setattr(s,'captain',3060), lambda s:s.managed_squad.pop(),
                     lambda s:s.managed_squad.__setitem__(1,s.managed_squad[0]),
                     lambda s:s.starting_eleven.pop(),lambda s:s.starting_eleven.__setitem__(0,3060),
                     lambda s:setattr(s,'country_tactics',256),lambda s:s.players.__setitem__(1,b'x')]
        for mutate in mutations:
            s = self.state();mutate(s); before=copy.deepcopy(s)
            with self.assertRaises(ValueError):run_watched_match(s,self.raw,Fixture(7,19,21))
            self.assertEqual(s,before)
        for f in (Fixture(7,7,21),Fixture(7,19,None),Fixture(7,19,0),Fixture(7,19,21,2),
                  Fixture(8,19,21),Fixture(True,19,21),Fixture(7,19,True),Fixture(7,19,769),Fixture(7,19,2401)):
            s=self.state();before=copy.deepcopy(s)
            with self.assertRaises(ValueError):run_watched_match(s,self.raw,f)
            self.assertEqual(s,before)
        s=self.state();f=CampaignFixture('original:21',1,1,2,1,7,19)
        s.campaign=CampaignState(1992,1,1,2,123,78,(f,))
        for fixture in (Fixture(7,19,22),Fixture(19,7,21)):
            with self.assertRaises(ValueError):prepare_watched(s,self.raw,fixture)

    def test_each_default_decision_is_explicitly_answered(self):
        from goal2.engine.original_match.match import Event
        image=Image(self.state().mem)
        class Controlled:
            def __init__(self):self.answers=0
            def events(self):
                for i,context in enumerate(('half_time','substitution','pause')):
                    yield Event('decision',45+i,(0,0),{'context':context,'injured':[121]})
                    assert self.answers==i+1, 'default answer missing'
                yield Event('full_time',90,(0,0))
                yield Event('end',90,(0,0))
            def answer(self):self.answers+=1
            def result(self):return {'complete':True}
            def memory_component(self):return image.memory_component()
        controlled=Controlled()
        with patch('goal2.game.watched_match.Match',return_value=controlled):
            got=run_watched_match(self.state(),self.raw,Fixture(7,19,21))
        self.assertEqual(controlled.answers,3)
        self.assertEqual(got.result,{'complete':True})

    def test_distinct_same_minute_notices_are_not_a_no_progress_loop(self):
        # [designed: T65 policy] Guest commentary distinguishes a later stoppage
        # even when its minute/context/selection data equal the earlier notice.
        from goal2.engine.original_match.match import Event
        image=Image(self.state().mem)
        class Notices:
            def __init__(self,progress):self.answers=0;self.progress=progress
            def events(self):
                data={'context':'substitution','injured':[121]}
                yield Event('decision',20,(0,0),data)
                if self.progress:yield Event('commentary',20,(0,0),{'text':'guest progressed'})
                yield Event('decision',20,(0,0),data)
                assert self.answers==2,'later notice was not answered'
                yield Event('full_time',90,(0,0));yield Event('end',90,(0,0))
            def answer(self):self.answers+=1
            def result(self):return {'complete':True}
            def memory_component(self):return image.memory_component()
        s=self.state();before=copy.deepcopy(s)
        with patch('goal2.game.watched_match.Match',return_value=Notices(True)):
            self.assertEqual(run_watched_match(s,self.raw,Fixture(7,19,21)).result,{'complete':True})
        with patch('goal2.game.watched_match.Match',return_value=Notices(False)):
            with self.assertRaisesRegex(RuntimeError,'no progress'):
                run_watched_match(s,self.raw,Fixture(7,19,21))
        self.assertEqual(s,before)

    def test_default_decision_policy_and_refusal_fail_closed(self):
        # [designed: T65] A controlled refused notice fails without tactics/substitution editing.
        class Refused:
            def events(self):
                from goal2.engine.original_match.match import Event
                yield Event('decision',20,(0,0),{'context':'substitution','refused':['unsupported']})
            def answer(self):raise AssertionError('must refuse')
        s=self.state();before=copy.deepcopy(s)
        with patch('goal2.game.watched_match.Match',return_value=Refused()):
            with self.assertRaisesRegex(RuntimeError,'refused'):
                run_watched_match(s,self.raw,Fixture(7,19,21))
        self.assertEqual(s,before)


if __name__ == '__main__':unittest.main()
