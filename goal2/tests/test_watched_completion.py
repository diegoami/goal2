"""[designed: #254] Controlled completion work; real owner/lock/publication boundaries."""
import copy
from pathlib import Path
import subprocess
import tempfile
import threading
import time
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

from goal2.engine.original_match import Fixture
from goal2.game.watched_jobs import WatchedJobs
from goal2.game import watched_publication
from goal2.tests.test_session_save import _state


class CompletionTests(unittest.TestCase):
    def setUp(self):
        self.main_thread = threading.get_ident()
        self.views = []
        self.owner = SimpleNamespace(state=_state(), template_bytes=b'private template',
                                     match_pending=True, view=lambda state:self.views.append(threading.get_ident()))
        self.before = copy.deepcopy(self.owner.state)
        self.expected = copy.deepcopy(self.before)
        self.expected.match_count += 1
        self.jobs = WatchedJobs(self.owner)
        self.token = 'completion-token'
        self.jobs.token = self.token
        self.jobs._original = self.owner.state
        self.jobs._snapshot = copy.deepcopy(self.before)
        self.jobs._template = self.owner.template_bytes
        self.jobs._pitch_owns_pending = True
        self.jobs._engine_done = True
        self.jobs._frames_enabled = False
        self.outcome = SimpleNamespace(result={'ticks':1})
        self.jobs._complete = self.outcome
        self.jobs._buffer = bytearray()
        self.jobs._folder = tempfile.TemporaryDirectory(prefix='goal2-completion-test-')
        self.folder = Path(self.jobs._folder.name)
        for name in ('_journal','_errors','_frames'):
            setattr(self.jobs,name,(self.folder/name).open('w+b'))
        self.jobs.process = Mock()
        self.jobs.process.poll.return_value = 0
        self.jobs.process.wait.return_value = 0
        self.jobs.publication._pending = (self.token,self.owner.state,copy.deepcopy(self.before),
                                         copy.deepcopy(self.before),Fixture(7,19,21),self.owner.template_bytes)
        self.entered = threading.Event()
        self.gate = threading.Event()
        self.worker_thread = None
        self.addCleanup(self.cleanup)

    def cleanup(self):
        self.gate.set()
        self.jobs.close()

    def build(self, state, fixture, outcome, template, *, competitive=False):
        self.worker_thread = threading.get_ident()
        self.assertIsNot(state,self.owner.state)
        self.assertEqual(state,self.before)
        self.assertEqual(template,b'private template')
        self.assertIs(outcome,self.outcome)
        self.entered.set()
        if not self.gate.wait(2):
            raise ValueError('candidate preparation blocked the caller')
        return self.expected

    def finish(self):
        deadline = time.monotonic()+5
        while self.jobs.busy:
            self.jobs.poll(self.token)
            if time.monotonic()>deadline:self.fail('completion preparation did not finish')
            time.sleep(.001)

    def test_slow_candidate_keeps_poll_responsive_and_publishes_once_on_owner_thread(self):
        with patch.object(watched_publication,'completed_candidate',self.build):
            self.jobs._maybe_publish(self.token)
            self.assertTrue(self.entered.wait(1))
            self.assertNotEqual(self.worker_thread,self.main_thread)
            self.assertTrue(self.jobs.busy)
            self.assertTrue(self.owner.match_pending)
            for _ in range(50):self.assertEqual(self.jobs.poll(self.token),[])
            self.assertEqual(self.owner.state,self.before)
            self.assertEqual(self.views,[])
            self.assertIsNone(self.jobs.outcome)
            self.gate.set()
            self.finish()
            self.assertIs(self.owner.state,self.expected)
            self.assertEqual(self.views,[self.main_thread])
            self.assertIs(self.jobs.outcome,self.outcome)
            self.assertIsNone(self.jobs.publication._pending)
            self.assertFalse(self.owner.match_pending)
            self.assertFalse(self.folder.exists())
            for action in (self.jobs.poll,self.jobs.cancel):
                with self.assertRaisesRegex(ValueError,'consumed'):action(self.token)
            self.assertEqual(self.views,[self.main_thread])

    def test_completion_cannot_start_before_final_frame_ack(self):
        self.jobs._frames_enabled = True
        self.jobs._frame_buffer = bytearray()
        self.jobs._frame_sequence = 1
        self.jobs._frame_ack = -1
        with patch.object(watched_publication,'completed_candidate',self.build):
            self.jobs._engine_done = False
            self.jobs._maybe_publish(self.token)
            self.assertIsNone(getattr(self.jobs,'_completion_thread',None))
            self.jobs._engine_done = True
            self.jobs._maybe_publish(self.token)
            self.assertIsNone(getattr(self.jobs,'_completion_thread',None))
            self.assertFalse(self.entered.is_set())
            self.assertTrue(self.jobs.busy)
            self.jobs._frame_ack = 0
            self.jobs._maybe_publish(self.token)
            self.assertTrue(self.entered.wait(1))
            self.assertEqual(self.views,[])
            self.gate.set()
            self.finish()
            self.assertEqual(self.views,[self.main_thread])

    def test_cancel_timeout_retains_worker_and_lock_then_retries_without_publication(self):
        with patch.object(watched_publication,'completed_candidate',self.build):
            self.jobs._maybe_publish(self.token)
            self.assertTrue(self.entered.wait(1))
            process = self.jobs.process
            started = time.monotonic()
            with self.assertRaises(subprocess.TimeoutExpired):self.jobs.cancel(self.token)
            self.assertLess(time.monotonic()-started,1.5)
            self.assertTrue(self.jobs.busy)
            self.assertIs(self.jobs.process,process)
            self.assertTrue(self.folder.exists())
            self.assertTrue(self.owner.match_pending)
            self.assertIsNone(self.jobs.publication._pending)
            self.gate.set()
            self.jobs.cancel(self.token)
            self.assertFalse(self.jobs.busy)
            self.assertFalse(self.folder.exists())
            self.assertFalse(self.owner.match_pending)
            self.assertEqual(self.owner.state,self.before)
            self.assertEqual(self.views,[])
            self.assertIsNone(self.jobs.outcome)

    def changed_owner(self, change):
        with patch.object(watched_publication,'completed_candidate',self.build):
            self.jobs._maybe_publish(self.token)
            self.assertTrue(self.entered.wait(1))
            if change=='identity':self.owner.state=copy.deepcopy(self.before)
            elif change=='in-place':self.owner.state.captain+=1
            else:self.owner.template_bytes+=b'changed'
            changed=copy.deepcopy(self.owner.state)
            self.gate.set()
            self.jobs._completion_thread.join(5)
            with self.assertRaisesRegex(ValueError,'stale'):
                self.jobs._maybe_publish(self.token)
            self.assertEqual(self.owner.state,changed)
            self.assertEqual(self.views,[])
            self.assertIsNone(self.jobs.publication._pending)
            self.jobs.close()

    def test_changed_owner_identity_is_rechecked_after_preparation(self):
        self.changed_owner('identity')

    def test_in_place_owner_change_is_rechecked_after_preparation(self):
        self.changed_owner('in-place')

    def test_changed_template_is_rechecked_after_preparation(self):
        self.changed_owner('template')

    def test_candidate_error_releases_owned_resources_and_preserves_state(self):
        with patch.object(watched_publication,'completed_candidate',side_effect=ValueError('candidate invalid')):
            with self.assertRaisesRegex(ValueError,'candidate invalid'):self.finish()
        self.assertFalse(self.jobs.busy)
        self.assertFalse(self.folder.exists())
        self.assertFalse(self.owner.match_pending)
        self.assertEqual(self.owner.state,self.before)
        self.assertEqual(self.views,[])
        self.assertIsNone(self.jobs.outcome)
        self.assertIsNone(self.jobs.publication._pending)

    def test_unprepared_forged_duplicate_and_cancelled_candidates_cannot_publish(self):
        publication=self.jobs.publication
        with self.assertRaisesRegex(ValueError,'unknown|consumed'):
            publication.publish_prepared(self.token,None)
        work=publication.prepare_completion(self.token,self.outcome)
        with self.assertRaisesRegex(ValueError,'preparing'):
            publication.publish_prepared(self.token,work)
        with self.assertRaisesRegex(ValueError,'unknown|consumed'):
            publication.publish_prepared(self.token,SimpleNamespace(ready=True,error=None,candidate=self.expected))
        with self.assertRaisesRegex(ValueError,'preparing'):
            publication.prepare_completion(self.token,self.outcome)
        with patch.object(watched_publication,'completed_candidate',return_value=self.expected):work.run()
        publication.cancel()
        with self.assertRaisesRegex(ValueError,'unknown|consumed'):
            publication.publish_prepared(self.token,work)
        self.assertEqual(self.owner.state,self.before)
        self.assertEqual(self.views,[])

    def test_thread_start_failure_keeps_original_error_and_releases_ownership(self):
        with patch('goal2.game.watched_jobs.threading.Thread.start',side_effect=OSError('candidate thread unavailable')):
            with self.assertRaisesRegex(ValueError,'candidate thread unavailable'):
                self.jobs.poll(self.token)
        self.assertFalse(self.jobs.busy)
        self.assertFalse(self.folder.exists())
        self.assertFalse(self.owner.match_pending)
        self.assertEqual(self.owner.state,self.before)
        self.assertEqual(self.views,[])
