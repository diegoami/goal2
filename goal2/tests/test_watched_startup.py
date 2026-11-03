"""[designed: #254] Gated real save encoding proves responsive owned startup.

[designed: T160] The game is encoded and sent to the owner's engine process (`open`) off the owner's thread; the
match request alone is sent from it, once the game is sent. A stand-in engine (test_watched_jobs.IDLE) takes them.
"""
import copy
from pathlib import Path
import subprocess
import sys
import threading
import time
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

from goal2.engine.original_match import Fixture
from goal2.game import watched_jobs
from goal2.game.engine_process import EngineProcess
from goal2.game.session_save import encode, decode
from goal2.game.watched_publication import WatchedJob
from goal2.tests.test_session_save import _state
from goal2.tests.test_watched_jobs import IDLE_COMMAND


class StartupTests(unittest.TestCase):
    def setUp(self):
        self.owner = SimpleNamespace(state=_state(), template_bytes=b'private template')
        self.before = copy.deepcopy(self.owner.state)
        self.jobs = watched_jobs.WatchedJobs(self.owner, command=IDLE_COMMAND)
        self.gate = threading.Event()
        self.entered = threading.Event()
        self.encoding_thread = None
        self.source = None
        self.encoded = None
        self.launched_on = None
        self.main_thread = threading.get_ident()
        self.job = WatchedJob('private-job', copy.deepcopy(self.before), Fixture(7,19,21))
        self.jobs.publication.begin = Mock(return_value=self.job)
        self.jobs.publication.complete = Mock()
        self.addCleanup(self.cleanup)

    def cleanup(self):
        self.gate.set()
        self.jobs.close()

    def encoding(self, state, template):
        self.encoding_thread = threading.get_ident()
        self.entered.set()
        if not self.gate.wait(2):
            raise ValueError('test release was not reached; encoding blocked the caller')
        self.encoded = encode(state, template)
        return self.encoded

    def launch(self, engine, *args, **kwargs):
        """[designed: T160] The match request: the launch of the match."""
        self.launched_on = threading.get_ident()
        return self.real_match(engine, *args, **kwargs)

    def opening(self, engine, raw):
        self.source = bytes(raw)
        return self.real_open(engine, raw)

    real_match = staticmethod(EngineProcess.match)
    real_open = staticmethod(EngineProcess.open_encoded)

    def launches(self):
        return patch.object(EngineProcess, 'match', autospec=True, side_effect=self.launch)

    def until_launch(self, token):
        deadline = time.monotonic() + 5
        while not self.jobs._sent:
            self.assertEqual(self.jobs.poll(token), [])
            if time.monotonic() > deadline:
                self.fail('prepared match was never launched')
            time.sleep(.001)

    def test_encoding_and_input_write_are_private_and_start_poll_remain_responsive(self):
        with patch.object(watched_jobs, 'encode', self.encoding), self.launches() as launch, \
                patch.object(EngineProcess, 'open_encoded', autospec=True, side_effect=self.opening):
            token = self.jobs.start(self.job.fixture, frames=True)
            self.assertTrue(self.entered.wait(1))
            self.assertNotEqual(self.encoding_thread, self.main_thread)
            self.assertFalse(self.gate.is_set())
            self.assertTrue(self.jobs.busy)
            self.assertTrue(self.owner.match_pending)
            for _ in range(50):
                self.assertEqual(self.jobs.poll(token), [])
                self.assertEqual(self.jobs.poll_frames(token), [])
            launch.assert_not_called()
            with self.assertRaisesRegex(ValueError, 'already running'):
                self.jobs.start(self.job.fixture)
            self.assertEqual(self.owner.state, self.before)
            self.gate.set()
            self.until_launch(token)
            self.assertEqual(self.launched_on, self.main_thread)
            self.assertEqual(self.encoded, encode(self.job.state, self.owner.template_bytes))
            self.assertEqual(self.source, self.encoded)
            self.assertEqual(decode(self.source)[0], self.before)
            process = self.jobs.process.popen
            self.jobs.cancel(token)
            self.assertIsNone(process.poll(), 'the engine answers the cancel and stays up for the next match')
            self.assertFalse(self.jobs.busy)
            self.assertFalse(self.owner.match_pending)
            self.jobs.publication.complete.assert_not_called()
            self.assertEqual(self.owner.state, self.before)

    def test_cancel_blocked_encoding_retains_ownership_and_retries_without_launch(self):
        with patch.object(watched_jobs, 'encode', self.encoding), self.launches() as launch:
            token = self.jobs.start(self.job.fixture, frames=True)
            self.assertTrue(self.entered.wait(1))
            process = self.jobs.process
            started = time.monotonic()
            with self.assertRaises(subprocess.TimeoutExpired):
                self.jobs.cancel(token)
            self.assertLess(time.monotonic()-started, 1.5)
            self.assertTrue(self.jobs.busy)
            self.assertIs(self.jobs.process, process)
            self.assertTrue(self.owner.match_pending)
            with self.assertRaisesRegex(ValueError, 'already running'):
                self.jobs.start(self.job.fixture)
            launch.assert_not_called()
            self.gate.set()
            self.jobs.cancel(token)
            launch.assert_not_called()
            self.assertFalse(self.jobs.busy)
            self.assertFalse(self.owner.match_pending)
            self.assertIsNone(self.jobs.publication._pending)
            self.jobs.publication.complete.assert_not_called()
            self.assertEqual(self.owner.state, self.before)

    def test_preparation_and_launch_errors_are_reported_without_publication(self):
        for failure in ('encode', 'write', 'launch'):
            with self.subTest(failure=failure):
                def encoding(state, template):
                    if failure == 'encode':
                        raise ValueError('owned encode failure')
                    return encode(state, template)
                def writing(engine, raw):
                    if failure == 'write':
                        raise OSError('owned write failure')
                    return self.real_open(engine, raw)
                with patch.object(watched_jobs, 'encode', encoding), \
                        patch.object(EngineProcess, 'open_encoded', autospec=True, side_effect=writing), \
                        patch.object(watched_jobs.subprocess, 'Popen', side_effect=OSError('owned launch failure')):
                    token = self.jobs.start(self.job.fixture)
                    deadline = time.monotonic()+5
                    with self.assertRaisesRegex(ValueError, 'owned '+failure+' failure'):
                        while time.monotonic() < deadline:
                            self.jobs.poll(token)
                            time.sleep(.001)
                    self.assertFalse(self.jobs.busy)
                    self.assertEqual(self.owner.state, self.before)
                    self.jobs.publication.complete.assert_not_called()

    def test_stale_input_while_preparing_never_launches_or_publishes(self):
        for field in ('state', 'template'):
            with self.subTest(field=field), patch.object(watched_jobs, 'encode', self.encoding), self.launches() as launch:
                self.gate.clear()
                token = self.jobs.start(self.job.fixture)
                self.assertTrue(self.entered.wait(1))
                if field == 'state':
                    self.owner.state = copy.deepcopy(self.before)
                else:
                    self.owner.template_bytes += b'changed'
                self.gate.set()
                with self.assertRaisesRegex(ValueError, 'stale'):
                    self.jobs.poll(token)
                self.assertFalse(self.jobs.busy)
                launch.assert_not_called()
                self.jobs.publication.complete.assert_not_called()

    def test_blocked_write_keeps_poll_responsive_and_close_waits_for_owned_writer(self):
        def writing(engine, raw):
            self.encoding_thread = threading.get_ident()
            self.entered.set()
            if not self.gate.wait(2):
                raise ValueError('input write blocked the caller')
            return self.real_open(engine, raw)
        with patch.object(EngineProcess, 'open_encoded', autospec=True, side_effect=writing), self.launches() as launch:
            token = self.jobs.start(self.job.fixture, frames=True)
            self.assertTrue(self.entered.wait(1))
            self.assertNotEqual(self.encoding_thread, self.main_thread)
            self.assertEqual(self.jobs.poll(token), [])
            releaser = threading.Timer(.05, self.gate.set)
            releaser.start()
            try:
                self.jobs.close()
            finally:
                releaser.join()
            launch.assert_not_called()
            self.assertFalse(self.jobs.busy)
            self.assertFalse(self.owner.match_pending)
            self.assertTrue(self.jobs.closed)
            self.assertEqual(self.owner.state, self.before)

    def test_cleanup_failure_keeps_lock_and_can_be_retried(self):
        # [designed: T160] A cancel the engine neither answers nor ends by its death keeps the job and the lock.
        self.gate.set()
        with patch.object(watched_jobs, 'encode', self.encoding):
            token = self.jobs.start(self.job.fixture, frames=True)
            self.until_launch(token)
            process = self.jobs.process
            with patch.object(EngineProcess, 'cancel', return_value=True), \
                    patch.object(watched_jobs.WatchedJobs, '_kill'), \
                    patch.object(watched_jobs, 'CANCEL_WAIT', .05), patch.object(watched_jobs, 'DEATH_WAIT', .05):
                with self.assertRaises(subprocess.TimeoutExpired):
                    self.jobs.cancel(token)
            self.assertTrue(self.jobs.busy)
            self.assertIs(self.jobs.process, process)
            self.assertTrue(self.owner.match_pending)
            with self.assertRaisesRegex(ValueError, 'already running'):
                self.jobs.start(self.job.fixture)
            self.jobs.cancel(token)
            self.assertFalse(self.jobs.busy)
            self.assertFalse(self.owner.match_pending)
            self.assertEqual(self.owner.state, self.before)

    def test_terminated_worker_can_be_reaped_by_poll_without_wait(self):
        token=self.jobs.start(self.job.fixture)
        process=self.jobs.process
        deadline=time.monotonic()+5
        while process.pid is None:
            self.jobs.poll(token)
            if time.monotonic()>deadline:self.fail('owned worker did not launch')
            time.sleep(.001)
        process.terminate()
        deadline=time.monotonic()+2
        while process.poll() is None and time.monotonic()<deadline:time.sleep(.001)
        self.assertIsNotNone(process.poll(),'terminated owned process never reaped by poll')
        self.jobs.cancel(token)
        self.assertFalse(self.jobs.busy)
        self.assertEqual(self.owner.state,self.before)
