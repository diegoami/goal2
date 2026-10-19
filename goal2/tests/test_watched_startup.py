"""[designed: #254] Gated real save encoding proves responsive owned startup."""
import copy
from pathlib import Path
import subprocess
import threading
import time
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

from goal2.engine.original_match import Fixture
from goal2.game import watched_jobs
from goal2.game.session_save import encode, decode
from goal2.game.watched_publication import WatchedJob
from goal2.tests.test_session_save import _state


class StartupTests(unittest.TestCase):
    def setUp(self):
        self.owner = SimpleNamespace(state=_state(), template_bytes=b'private template')
        self.before = copy.deepcopy(self.owner.state)
        self.jobs = watched_jobs.WatchedJobs(self.owner, command=['owned-worker'])
        self.gate = threading.Event()
        self.entered = threading.Event()
        self.encoding_thread = None
        self.process = Mock()
        self.process.poll.return_value = None
        self.process.pid = 12345
        self.process.wait.return_value = 0
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

    def launch(self, command, **kwargs):
        self.launched_on = threading.get_ident()
        self.source = Path(command[-2])
        self.assertEqual(self.source.read_bytes(), self.encoded)
        return self.process

    def until_launch(self, token):
        deadline = time.monotonic() + 5
        while not self.jobs.process.pid:
            self.assertEqual(self.jobs.poll(token), [])
            if time.monotonic() > deadline:
                self.fail('prepared worker was never launched')
            time.sleep(.001)

    def test_encoding_and_input_write_are_private_and_start_poll_remain_responsive(self):
        with patch.object(watched_jobs, 'encode', self.encoding), patch.object(watched_jobs.subprocess, 'Popen', side_effect=self.launch) as launch:
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
            self.assertEqual(decode(self.source.read_bytes())[0], self.before)
            folder = self.source.parent
            self.jobs.cancel(token)
            self.process.terminate.assert_called_once()
            self.assertFalse(folder.exists())
            self.assertFalse(self.jobs.busy)
            self.assertFalse(self.owner.match_pending)
            self.jobs.publication.complete.assert_not_called()
            self.assertEqual(self.owner.state, self.before)

    def test_cancel_blocked_encoding_retains_ownership_and_retries_without_launch(self):
        with patch.object(watched_jobs, 'encode', self.encoding), patch.object(watched_jobs.subprocess, 'Popen') as launch:
            token = self.jobs.start(self.job.fixture, frames=True)
            self.assertTrue(self.entered.wait(1))
            folder = Path(self.jobs._folder.name)
            process = self.jobs.process
            started = time.monotonic()
            with self.assertRaises(subprocess.TimeoutExpired):
                self.jobs.cancel(token)
            self.assertLess(time.monotonic()-started, 1.5)
            self.assertTrue(self.jobs.busy)
            self.assertIs(self.jobs.process, process)
            self.assertTrue(folder.exists())
            self.assertTrue(self.owner.match_pending)
            with self.assertRaisesRegex(ValueError, 'already running'):
                self.jobs.start(self.job.fixture)
            launch.assert_not_called()
            self.gate.set()
            self.jobs.cancel(token)
            launch.assert_not_called()
            self.assertFalse(self.jobs.busy)
            self.assertFalse(folder.exists())
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
                original_write = Path.write_bytes
                def writing(path, raw):
                    if path.name == 'input' and failure == 'write':
                        raise OSError('owned write failure')
                    return original_write(path, raw)
                with patch.object(watched_jobs, 'encode', encoding), patch.object(Path, 'write_bytes', writing), patch.object(watched_jobs.subprocess, 'Popen', side_effect=OSError('owned launch failure')):
                    token = self.jobs.start(self.job.fixture)
                    folder = Path(self.jobs._folder.name)
                    deadline = time.monotonic()+5
                    with self.assertRaisesRegex(ValueError, 'owned '+failure+' failure'):
                        while time.monotonic() < deadline:
                            self.jobs.poll(token)
                            time.sleep(.001)
                    self.assertFalse(self.jobs.busy)
                    self.assertFalse(folder.exists())
                    self.assertEqual(self.owner.state, self.before)
                    self.jobs.publication.complete.assert_not_called()

    def test_stale_input_while_preparing_never_launches_or_publishes(self):
        for field in ('state', 'template'):
            with self.subTest(field=field), patch.object(watched_jobs, 'encode', self.encoding), patch.object(watched_jobs.subprocess, 'Popen') as launch:
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
        original_write = Path.write_bytes
        def writing(path, raw):
            if path.name == 'input':
                self.encoding_thread = threading.get_ident()
                self.entered.set()
                if not self.gate.wait(2):
                    raise ValueError('input write blocked the caller')
            return original_write(path, raw)
        with patch.object(Path, 'write_bytes', writing), patch.object(watched_jobs.subprocess, 'Popen') as launch:
            token = self.jobs.start(self.job.fixture, frames=True)
            self.assertTrue(self.entered.wait(1))
            self.assertNotEqual(self.encoding_thread, self.main_thread)
            self.assertEqual(self.jobs.poll(token), [])
            folder = Path(self.jobs._folder.name)
            releaser = threading.Timer(.05, self.gate.set)
            releaser.start()
            try:
                self.jobs.close()
            finally:
                releaser.join()
            launch.assert_not_called()
            self.assertFalse(folder.exists())
            self.assertFalse(self.jobs.busy)
            self.assertFalse(self.owner.match_pending)
            self.assertTrue(self.jobs.closed)
            self.assertEqual(self.owner.state, self.before)

    def test_cleanup_failure_keeps_lock_and_can_be_retried(self):
        self.gate.set()
        with patch.object(watched_jobs, 'encode', self.encoding), patch.object(watched_jobs.subprocess, 'Popen') as launch:
            token = self.jobs.start(self.job.fixture, frames=True)
            process = self.jobs.process
            folder = self.jobs._folder
            with patch.object(folder, 'cleanup', side_effect=PermissionError('owned cleanup denied')):
                with self.assertRaisesRegex(PermissionError, 'owned cleanup denied'):
                    self.jobs.cancel(token)
            self.assertTrue(self.jobs.busy)
            self.assertIs(self.jobs.process, process)
            self.assertIs(self.jobs._folder, folder)
            self.assertTrue(self.owner.match_pending)
            with self.assertRaisesRegex(ValueError, 'already running'):
                self.jobs.start(self.job.fixture)
            self.jobs.cancel(token)
            launch.assert_not_called()
            self.assertFalse(self.jobs.busy)
            self.assertFalse(self.owner.match_pending)
            self.assertFalse(Path(folder.name).exists())
            self.assertEqual(self.owner.state, self.before)
