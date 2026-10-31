"""[designed: T64] Versioned watched save continuation and atomic failures."""
import copy
import json
import unittest
from unittest.mock import patch
from goal2.game import session_save
from goal2.game.watched_publication import WatchedPublication, ENGINE_ID
from goal2.tests import test_watched_publication as publication
Owner = publication.Owner
from goal2.game.watched_match import run_watched_match
from goal2.engine.original_match import Fixture
from goal2.tests import requires


class WatchedSaveTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        publication.WatchedPublicationTests.setUpClass();cls.raw=publication.WatchedPublicationTests.raw
    def state(self):return publication.WatchedPublicationTests.state(self)
    def completed(self):
        owner=Owner(self.state(),self.raw);pub=WatchedPublication(owner)
        job=pub.begin(Fixture(7,19,21));outcome=run_watched_match(job.state,self.raw,job.fixture)
        pub.complete(job.token,outcome)
        return owner
    def test_watched_roundtrip_and_malformed_saves(self):
        owner=self.completed();raw=session_save.encode(owner.state,self.raw)
        self.assertEqual(json.loads(raw)['version'],3)
        state,template=session_save.decode(raw)
        self.assertEqual(state,owner.state);self.assertEqual(template,self.raw)
        for mutate in (lambda d:d['state']['last_match'].__setitem__('engine','unknown'),
                       lambda d:d['state']['last_match']['original'].__setitem__('seed_after',-1),
                       lambda d:d['state']['last_match']['original'].__setitem__('index',22),
                       lambda d:d['state']['last_match']['original'].__setitem__('managed',19),
                       lambda d:d['state']['last_match'].__setitem__('schema',99),
                       lambda d:d['state'].__setitem__('rng_seed_8336',1),
                       lambda d:d['state']['last_match'].pop('engine'),
                       lambda d:d.__setitem__('version',1),
                       lambda d:d['state']['last_match']['original']['board']['statistics'].__setitem__('corners',[-1,0]),
                       lambda d:d['state']['last_match']['original'].__setitem__('goals',[{'bad':'record'}])):
            doc=json.loads(raw);mutate(doc)
            with self.assertRaises(session_save.SessionSaveError):session_save.decode(json.dumps(doc).encode())
        self.assertEqual(owner.state,state)
    def test_injected_failure_before_swap_preserves_complete_state(self):
        owner=Owner(self.state(),self.raw);pub=WatchedPublication(owner)
        job=pub.begin(Fixture(7,19,21));before=copy.deepcopy(owner.state)
        outcome=run_watched_match(job.state,self.raw,job.fixture)
        with patch('goal2.game.watched_publication.validate_saved_watched',side_effect=ValueError('injected')):
            with self.assertRaisesRegex(ValueError,'injected'):pub.complete(job.token,outcome)
        self.assertEqual(owner.state,before)

    @requires.need(slow=True)  # [designed: #275] about 158 s alone on 32 CPUs
    def test_fresh_1990_1992_campaign_history_and_deterministic_next_fixture(self):
        from pathlib import Path
        from goal2.data.goaldat import load
        from goal2.game.campaign_schedule import start_opening_campaign
        from goal2.tests import test_watched_adapter as adapter
        root=Path(__file__).resolve().parents[2]
        template=(root/'.cache/e010-r0008-halftime.sav').read_bytes()
        data=load((root/'.cache/GOAL.DAT').read_bytes())
        for year in (1990,1992):
            with self.subTest(year=year):
                state,_=start_opening_campaign(data,template,managed_country=4,start_year=year,
                                              seed_7b62=4660,seed_8336=33590)
                state.captain=state.starting_eleven[4]
                state.country_tactics^=8
                owner=Owner(state,template);pub=WatchedPublication(owner)
                f=state.campaign.next_fixture
                fixture=Fixture(f.side_a,f.side_b,int(f.fixture_id.split(':')[1]))
                before=copy.deepcopy(state)
                with patch('goal2.game.campaign_rounds.silent_until_managed',side_effect=ValueError('prefix failure')):
                    with self.assertRaisesRegex(ValueError,'prefix failure'):pub.begin(fixture)
                self.assertEqual(owner.state,before)
                job=pub.begin(fixture)
                expected,memory,_=adapter.direct(job.state,fixture,year=0)
                outcome=run_watched_match(job.state,template,fixture)
                # [designed] Direct helper records draws; production need not retain their diagnostic digest.
                for key in ('draws','draws_digest'):expected.pop(key)
                # [designed: T151] goal2's route plays the sealed port; `direct` is the original (port_parity)
                from goal2.tests.port_parity import comparable_result
                self.assertIn('ports',outcome.result)
                self.assertEqual(comparable_result({k:v for k,v in outcome.result.items() if k not in ('draws','draws_digest')}),
                                 comparable_result(expected))
                with patch('goal2.game.campaign_rounds.silent_until_managed',side_effect=ValueError('suffix failure')):
                    with self.assertRaisesRegex(ValueError,'suffix failure'):pub.complete(job.token,outcome)
                self.assertEqual(owner.state,before)
                job=pub.begin(fixture)
                pub.complete(job.token,outcome)
                from goal2.tests.port_parity import comparable_memory
                self.assertEqual(owner.state.mem,outcome.memory)
                self.assertEqual(comparable_memory(owner.state.mem),comparable_memory(memory))
                self.assertEqual(owner.state.players,adapter.Image(memory).players())
                self.assertEqual(owner.state.countries,adapter.Image(memory).countries())
                self.assertEqual(owner.state.captain,state.captain)
                self.assertEqual(owner.state.starting_eleven,state.starting_eleven)
                self.assertEqual(owner.state.campaign.reserve_ids,state.campaign.reserve_ids)
                self.assertEqual(owner.state.campaign.completed_fixture_ids,[f.fixture_id])
                self.assertEqual(owner.state.last_match['seeds'],list(outcome.seeds))
                raw=session_save.encode(owner.state,template)
                resumed,raw_template=session_save.decode(raw)
                self.assertEqual(resumed,owner.state)
                self.assertEqual(raw_template,template)
                if year==1990:
                    # [designed: T64] A following quick match retains both paths' identities.
                    from goal2.desktop.worker import play
                    from goal2.game.eligibility import available_words
                    quick_states=[]
                    for prior in (owner.state,resumed):
                        selected=copy.deepcopy(prior)
                        selected.starting_eleven=available_words(selected.players,selected.managed_squad)[:11]
                        selected.captain=selected.starting_eleven[0]
                        quick_states.append(play(selected,template))
                    self.assertEqual(quick_states[0],quick_states[1])
                    self.assertNotIn('engine',quick_states[0].last_match)
                    mixed=session_save.encode(quick_states[0],template)
                    self.assertEqual(json.loads(mixed)['version'],3)
                    self.assertEqual(session_save.decode(mixed)[0],quick_states[0])
                    for damage in ('history','secondary','version'):
                        damaged=json.loads(mixed)
                        if damage=='history':damaged['state']['campaign']['results'].pop(0)
                        elif damage=='version':damaged['version']=2
                        else:
                            watched_row=next(r for r in damaged['state']['campaign']['world']['results'] if r['mode']=='watched')
                            watched_row['secondary_after']^=1
                        with self.subTest(damage=damage):
                            with self.assertRaises(session_save.SessionSaveError):session_save.decode(json.dumps(damaged).encode())
                damaged=json.loads(raw)
                damaged['state']['last_match']={'teams':[f.side_a,f.side_b],'score':[0,0],'goals':[]}
                with self.assertRaises(session_save.SessionSaveError):session_save.decode(json.dumps(damaged).encode())
                f2=resumed.campaign.next_fixture
                self.assertIsNotNone(f2)
                if year==1992:
                    # [confirmed: actual T63 opening source schedule] The next managed row
                    # is competitive kind2; save/reload must retain the same atomic refusal.
                    self.assertEqual(f2.kind,2)
                    for live in (owner,Owner(resumed,raw_template)):
                        before_refusal=copy.deepcopy(live.state)
                        with self.assertRaisesRegex(ValueError,'unsupported managed fixture'):
                            WatchedPublication(live).begin(Fixture(f2.side_a,f2.side_b,int(f2.fixture_id.split(':')[1]),f2.kind))
                        self.assertEqual(live.state,before_refusal)
                    continue
                self.assertEqual(f2.kind,1)
                next_fixture=Fixture(f2.side_a,f2.side_b,int(f2.fixture_id.split(':')[1]))
                next_jobs=[]
                for live in (owner,Owner(resumed,raw_template)):
                    continuation=WatchedPublication(live)
                    next_job=continuation.begin(next_fixture)
                    next_outcome=run_watched_match(next_job.state,template,next_fixture)
                    continuation.complete(next_job.token,next_outcome)
                    next_jobs.append(live.state)
                self.assertEqual(next_jobs[0],next_jobs[1])
                self.assertEqual(len(next_jobs[0].campaign.completed_fixture_ids),2)
                self.assertEqual(len(next_jobs[0].campaign.results),2)
                # [designed] Watched RNG metadata cannot masquerade as a quick affine ledger.
                for key,value in (('engine','unknown'),('schema',99),('setup_seed',-1),('secondary_after',65536),('index',2401)):
                    doc=json.loads(raw)
                    row=next(row for row in doc['state']['campaign']['world']['results'] if row['mode']=='watched')
                    row[key]=value
                    with self.assertRaises(session_save.SessionSaveError):session_save.decode(json.dumps(doc).encode())

    def test_legacy_friendly_and_campaign_history_retain_v1_v2_meaning(self):
        from goal2.game.campaign import CampaignState, Fixture as Scheduled
        state=self.state()
        for campaign in (None,CampaignState(1992,1,1,2,123,78,
                (Scheduled('original:21',1,1,2,1,7,19),),['original:21'],
                [{'fixture_id':'original:21','teams':[7,19],'score':[2,1]}])):
            state.campaign=campaign
            state.match_count=1
            state.last_match={'teams':(7,19),'score':(2,1),'goals':[],'draws':42}
            raw=session_save.encode(state,self.raw)
            self.assertEqual(json.loads(raw)['version'],1 if campaign is None else 2)
            resumed,template=session_save.decode(raw)
            expected=copy.deepcopy(state)
            if expected.campaign is not None:
                from goal2.game.campaign_pool import validate
                expected.campaign.reserve_ids=validate(state)
            self.assertEqual(resumed,expected);self.assertEqual(template,self.raw)
            self.assertNotIn('engine',resumed.last_match)

    def test_watched_save_write_failure_keeps_existing_file_and_active_state(self):
        import tempfile
        from pathlib import Path
        owner=self.completed();before=copy.deepcopy(owner.state)
        with tempfile.TemporaryDirectory() as directory:
            target=Path(directory)/'watched.g2save'
            target.write_bytes(b'previous complete save')
            with patch('goal2.game.session_save.os.replace',side_effect=OSError('injected write')):
                with self.assertRaisesRegex(session_save.SessionSaveError,'injected write'):
                    session_save.save(target,owner.state,self.raw)
            self.assertEqual(target.read_bytes(),b'previous complete save')
            self.assertEqual(list(Path(directory).iterdir()),[target])
        self.assertEqual(owner.state,before)
