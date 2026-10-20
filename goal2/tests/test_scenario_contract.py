"""[designed: T86] Shared protocol contract cases: the fake and, when configured, the real backend.

Each case is written once in a mixin and runs against both backends. Fault
children (goal2.scenario.worker --fault) read only argv/request.json, so the
same fault runs against either backend. An unconfigured real backend prints
`real backend: not configured (<missing items>)` per case and is reported as
skipped, never as passed. Nothing is downloaded.
"""
import copy
import sys
import tempfile
import time
import unittest
from pathlib import Path

from goal2.desktop.jobs import QuickJobs
from goal2.game.watched_jobs import WatchedJobs
from goal2.scenario import real
from goal2.scenario.model import ScenarioModel
from goal2.scenario.runtime import RUNTIME
from goal2.scenario.worker import command

ROOT = Path(__file__).resolve().parents[2]


def finish(test, step, limit=60):
    deadline = time.monotonic() + limit
    while time.monotonic() < deadline:
        value = step()
        if value:
            return value
        time.sleep(.01)
    test.fail('child exceeded its deadline')


class Fake:
    name = 'fake'

    @staticmethod
    def quick_model(test):
        return ScenarioModel()

    @staticmethod
    def quick(model, fault=None):
        return QuickJobs(model, command=command('quick', fault=fault), runtime=RUNTIME)

    @staticmethod
    def watched_owner(test):
        from goal2.engine.original_match import Fixture
        return ScenarioModel(), Fixture(1, 2, 1)

    @staticmethod
    def watched(owner, fault=None):
        return WatchedJobs(owner, command=command('watched', fault=fault), runtime=RUNTIME)


class Real:
    name = 'real'

    @staticmethod
    def quick_model(test):
        from goal2.desktop.model import DesktopModel
        folder = tempfile.TemporaryDirectory();test.addCleanup(folder.cleanup)
        return DesktopModel.open(ROOT / '.cache/e010-r0008-halftime.sav', ROOT / '.cache/GOAL.DAT',
                                 Path(folder.name) / 'game.g2save', country=4)

    @staticmethod
    def quick(model, fault=None):
        return QuickJobs(model, command=None if fault is None else command('quick', fault=fault))

    @staticmethod
    def watched_owner(test):
        # [derived: T86 from test_watched_jobs] The established reference owner and fixture.
        from goal2.engine.original_match import Fixture
        from goal2.game.state import from_savestate
        from goal2.tests.test_watched_publication import Owner
        raw = (ROOT / real.NEEDS['watched'][0]).read_bytes()
        state = from_savestate(raw);state.captain = 0
        return Owner(state, raw), Fixture(7, 19, 21)

    @staticmethod
    def watched(owner, fault=None):
        return WatchedJobs(owner, command=None if fault is None else command('watched', fault=fault))


class _Lane:
    backend = None
    lane = None

    def setUp(self):
        if self.backend is Real:
            line = real.not_configured(self.lane)
            if line is not None:
                print(f'{self.id()}: {line}', file=sys.stderr)
                self.skipTest(line)


class QuickContract(_Lane):
    lane = 'quick'

    def setUp(self):
        super().setUp()
        self.model = self.backend.quick_model(self)

    def job(self, fault=None):
        job = self.backend.quick(self.model, fault);self.addCleanup(job.cancel)
        return job

    def test_success_publishes_once_and_one_job_at_a_time(self):
        before = self.model.state
        job = self.job();job.start()
        with self.assertRaisesRegex(ValueError, 'already running'):
            job.start()
        self.assertIs(self.model.state, before)
        self.assertTrue(finish(self, job.poll))
        self.assertEqual(self.model.state.match_count, before.match_count + 1)
        self.assertIsNone(job.poll())
        self.assertFalse(self.model.match_pending)

    def test_failure_leaves_the_active_game(self):
        before = copy.deepcopy(self.model.state)
        job = self.job('fail');job.start()
        with self.assertRaisesRegex(ValueError, r'Friendly worker failed \(7\): deliberate fictional failure'):
            finish(self, job.poll)
        self.assertFalse(job.busy)
        self.assertEqual(self.model.state, before)

    def test_unreadable_output_is_refused(self):
        before = copy.deepcopy(self.model.state)
        job = self.job('garbage');job.start()
        with self.assertRaises(ValueError):
            finish(self, job.poll)
        self.assertEqual(self.model.state, before)
        self.assertFalse(self.model.match_pending)

    def test_early_output_is_not_read_before_exit(self):
        held = self.model.state
        job = self.job('early-garbage');job.start()
        finish(self, lambda: job.output.exists())
        for _ in range(20):
            self.assertIsNone(job.poll())
            time.sleep(.005)
        self.assertTrue(job.busy)
        (job.directory / 'release').write_text('go')
        with self.assertRaises(ValueError):
            finish(self, job.poll)
        self.assertIs(self.model.state, held)

    def test_stale_completion_is_refused(self):
        job = self.job();job.start()
        self.model.state.country_tactics ^= 1
        before = copy.deepcopy(self.model.state)
        with self.assertRaisesRegex(ValueError, 'Friendly completion is stale'):
            finish(self, job.poll)
        self.assertEqual(self.model.state, before)

    def test_cancel_never_publishes(self):
        before = copy.deepcopy(self.model.state)
        job = self.job('hang');job.start()
        time.sleep(.1)
        job.cancel()
        self.assertFalse(job.busy)
        self.assertFalse(self.model.match_pending)
        self.assertIsNone(job.poll())
        self.assertEqual(self.model.state, before)


class WatchedContract(_Lane):
    lane = 'watched'

    def setUp(self):
        super().setUp()
        self.owner, self.fixture = self.backend.watched_owner(self)
        self.jobs = None

    def tearDown(self):
        if self.jobs is not None:
            self.jobs.close()

    def bridge(self, fault=None):
        if self.jobs is not None:
            self.jobs.close()
        self.jobs = self.backend.watched(self.owner, fault)
        return self.jobs.start(self.fixture)

    def drain(self, token, limit=60):
        deadline = time.monotonic() + limit
        while self.jobs.busy:
            if time.monotonic() > deadline:
                self.fail('watched child exceeded its deadline')
            self.jobs.poll(token);time.sleep(.005)

    def refused(self, fault, message):
        held, before = self.owner.state, copy.deepcopy(self.owner.state)
        token = self.bridge(fault)
        with self.assertRaisesRegex(ValueError, message):
            self.drain(token)
        self.assertFalse(self.jobs.busy)
        self.assertIs(self.owner.state, held)
        self.assertEqual(self.owner.state, before)

    def test_wrong_token_packet_is_refused(self):
        self.refused('wrong-token', 'watched IPC identity/order differs from active job')

    def test_out_of_order_packet_is_refused(self):
        self.refused('gap', 'watched IPC identity/order differs from active job')

    def test_repeated_packet_is_refused(self):
        self.refused('repeat', 'watched IPC identity/order differs from active job')

    def test_error_packet_fails_the_job(self):
        self.refused('error', 'Watched worker failed: RuntimeError: deliberate fictional failure')

    def test_exit_without_completion_fails_the_job(self):
        self.refused('crash', r'Watched worker exited \(4\) without completion')

    def test_truncated_record_fails_the_job(self):
        self.refused('truncated', 'truncated watched IPC record')

    def test_stale_owner_is_refused(self):
        token = self.bridge('hang')
        finish(self, lambda: self.jobs.poll(token))
        self.owner.state.country_tactics ^= 1
        with self.assertRaisesRegex(ValueError, 'watched job is stale; active game changed'):
            self.jobs.poll(token)
        self.assertFalse(self.jobs.busy)

    def test_cancel_never_publishes_and_releases_the_token(self):
        held = self.owner.state
        token = self.bridge('hang')
        finish(self, lambda: self.jobs.poll(token))
        self.jobs.cancel(token)
        self.assertFalse(self.jobs.busy)
        with self.assertRaisesRegex(ValueError, 'stale or consumed watched job token'):
            self.jobs.poll(token)
        again = self.jobs.start(self.fixture)
        self.assertNotEqual(again, token)
        self.jobs.cancel(again)
        self.assertIs(self.owner.state, held)

    def test_success_publishes_once(self):
        held = self.owner.state
        token = self.bridge()
        self.drain(token, limit=600)
        self.assertIsNot(self.owner.state, held)
        self.assertIsNotNone(self.jobs.outcome)
        with self.assertRaisesRegex(ValueError, 'stale or consumed watched job token'):
            self.jobs.poll(token)


class FakeQuickContract(QuickContract, unittest.TestCase):
    backend = Fake


class RealQuickContract(QuickContract, unittest.TestCase):
    backend = Real


class FakeWatchedContract(WatchedContract, unittest.TestCase):
    backend = Fake


class RealWatchedContract(WatchedContract, unittest.TestCase):
    backend = Real


if __name__ == '__main__':
    unittest.main()
