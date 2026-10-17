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
                       lambda d:d['state']['last_match'].__setitem__('schema',99),
                       lambda d:d['state'].__setitem__('rng_seed_8336',1)):
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
