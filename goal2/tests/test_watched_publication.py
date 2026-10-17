"""[designed: T64] Once-only publication of completed original state."""
import copy
import unittest
from unittest.mock import patch
from goal2.engine.original_match import Fixture, Image, Match
from goal2.engine.original_match.check import EXPECTED_FAMILY
from goal2.game.campaign import CampaignState, Fixture as Scheduled
from goal2.game.watched_match import run_watched_match
from goal2.game.watched_publication import WatchedPublication, ENGINE_ID
from goal2.tests import test_watched_adapter as adapter
direct = adapter.direct


class Owner:
    def __init__(self,state,template):self.state=state;self.template_bytes=template
    def view(self,state):return state.last_match


class WatchedPublicationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        adapter.WatchedAdapter.setUpClass();cls.raw=adapter.WatchedAdapter.raw

    def state(self):
        return adapter.WatchedAdapter.state(self)

    def test_all_ten_strict_cases_publish_direct_runner_memory_once(self):
        for seed,want in EXPECTED_FAMILY.items():
            with self.subTest(seed=seed):
                state=self.state();before=copy.deepcopy(state);owner=Owner(state,self.raw)
                publication=WatchedPublication(owner);job=publication.begin(Fixture(7,19,21))
                expected,memory,_=direct(job.state,job.fixture,seed=seed,delay=0)
                outcome=run_watched_match(job.state,self.raw,job.fixture,reference_seed=seed,delay_byte=0,record_draws=True)
                self.assertEqual(owner.state,before)
                publication.complete(job.token,outcome)
                current=copy.deepcopy(owner.state);image=Image(memory)
                self.assertEqual(owner.state.mem,memory)
                self.assertEqual(owner.state.players,image.players())
                self.assertEqual(owner.state.countries,image.countries())
                self.assertEqual(owner.state.managed_squad,image.squad(7))
                self.assertEqual(owner.state.rng_seed_7b62,image.rd(0x7B62))
                self.assertEqual(owner.state.rng_seed_8336,image.rd(0x8336))
                self.assertEqual([expected['score'],expected['ticks'],expected['draws'],expected['draws_digest']],want)
                self.assertEqual(owner.state.last_match['original'],expected)
                self.assertEqual(owner.state.last_match['engine'],ENGINE_ID)
                self.assertEqual(owner.state.match_count,1)
                with self.assertRaises(ValueError):publication.complete(job.token,outcome)
                self.assertEqual(owner.state,current)

    def test_full_time_is_not_completion_and_tail_failure_is_atomic(self):
        owner=Owner(self.state(),self.raw);publication=WatchedPublication(owner)
        job=publication.begin(Fixture(7,19,21));before=copy.deepcopy(owner.state)
        match=Match(Image(job.state.mem),job.fixture,managed=7,seed=0x1234,delay_byte=0)
        for event in match.events():
            if event.kind=='decision':match.answer()
            if event.kind=='full_time':
                self.assertEqual(owner.state,before)
                with self.assertRaises(RuntimeError):match.result()
                with self.assertRaises(ValueError):publication.complete(job.token,event)
                break
        self.assertEqual(owner.state,before)

    def test_stale_wrong_identity_unsupported_kind_and_view_failure_are_atomic(self):
        owner=Owner(self.state(),self.raw);publication=WatchedPublication(owner)
        before=copy.deepcopy(owner.state)
        with self.assertRaises(ValueError):publication.begin(Fixture(7,19,21,2))
        self.assertEqual(owner.state,before)
        job=publication.begin(Fixture(7,19,21))
        outcome=run_watched_match(job.state,self.raw,job.fixture)
        with patch.object(owner,'view',side_effect=ValueError('view failure')):
            with self.assertRaisesRegex(ValueError,'view failure'):publication.complete(job.token,outcome)
        self.assertEqual(owner.state,before)
        # [designed] Failed publication consumes its token; a new attempt needs a new snapshot.
        with self.assertRaises(ValueError):publication.complete(job.token,outcome)
        job=publication.begin(Fixture(7,19,21));owner.state.country_tactics^=8
        changed=copy.deepcopy(owner.state)
        with self.assertRaisesRegex(ValueError,'stale'):publication.complete(job.token,outcome)
        self.assertEqual(owner.state,changed)
        owner.state=self.state();f=Scheduled('original:21',1,1,2,1,7,19)
        owner.state.campaign=CampaignState(1992,1,1,2,123,78,(f,))
        before=copy.deepcopy(owner.state)
        for wrong in (Fixture(7,19,22),Fixture(19,7,21)):
            with self.assertRaises(ValueError):publication.begin(wrong)
        self.assertEqual(owner.state,before)

    def test_campaign_completes_and_appends_history_exactly_once(self):
        state=self.state();f=Scheduled('original:21',1,1,2,1,7,19)
        state.campaign=CampaignState(1992,1,1,2,123,78,(f,))
        owner=Owner(state,self.raw);publication=WatchedPublication(owner)
        job=publication.begin(Fixture(7,19,21));outcome=run_watched_match(job.state,self.raw,job.fixture)
        publication.complete(job.token,outcome)
        self.assertEqual(owner.state.campaign.completed_fixture_ids,['original:21'])
        self.assertEqual(len(owner.state.campaign.results),1)
        self.assertEqual(owner.state.campaign.results[0]['engine'],ENGINE_ID)
        current=copy.deepcopy(owner.state)
        with self.assertRaises(ValueError):publication.complete(job.token,outcome)
        self.assertEqual(owner.state,current)
