"""[designed: T152] The match workers run under PyPy 3.11 when there is one, else under this interpreter.

The choice (goal2/game/engine_python.py) honours GOAL2_ENGINE_PYTHON as given, takes only a PyPy 3.11 it finds, and
falls back to sys.executable. A watched job and a competitive job run through their workers under PyPy give the same
outcome as the same match played under CPython (#500: in a CPython child, not in the test process)."""
import copy
import os
import sys
import time
import unittest
from pathlib import Path
from unittest.mock import patch

from goal2.engine.original_match import Fixture
from goal2.game import engine_python as ep
from goal2.tests import requires, pypy_engine

ROOT = Path(__file__).resolve().parents[2]


def fresh():
    ep.engine_python.cache_clear()


class Choice(unittest.TestCase):
    def setUp(self):
        fresh();self.addCleanup(fresh)

    def test_an_explicit_interpreter_is_used_as_given(self):
        with patch.dict(os.environ, {"GOAL2_ENGINE_PYTHON": sys.executable}):
            self.assertEqual(ep.engine_python(), sys.executable)
            self.assertEqual(ep.worker_command("goal2.game.watched_worker"),
                             [sys.executable, "-m", "goal2.game.watched_worker"])

    def test_without_pypy_the_worker_keeps_this_interpreter(self):
        env = {k: v for k, v in os.environ.items() if k != "GOAL2_ENGINE_PYTHON"}
        with patch.dict(os.environ, env, clear=True), patch.object(ep.shutil, "which", return_value=None), \
                patch.object(ep, "_uv_pythons", return_value=iter(())):
            self.assertEqual(ep.engine_python(), sys.executable)

    def test_a_found_interpreter_that_is_not_pypy_311_is_passed_over(self):
        env = {k: v for k, v in os.environ.items() if k != "GOAL2_ENGINE_PYTHON"}
        with patch.dict(os.environ, env, clear=True), patch.object(ep.shutil, "which", return_value=sys.executable), \
                patch.object(ep, "_uv_pythons", return_value=iter(())):
            self.assertEqual(ep.engine_python(), sys.executable)
            self.assertFalse(ep._is_pypy311(sys.executable))        # this process is CPython
        self.assertFalse(ep._is_pypy311(ROOT / "no-such-python"))

    def test_ci_gives_the_workers_pypy_311_and_keeps_cpython_on_path(self):
        for name in ("ci.yml", "windows.yml"):
            with self.subTest(workflow=name):
                text = (ROOT / ".github/workflows" / name).read_text()
                self.assertIn("python-version: 'pypy3.11'\n          update-environment: false", text)
                self.assertIn('GOAL2_ENGINE_PYTHON=${{ steps.pypy.outputs.python-path }}', text)
                self.assertLess(text.index("pypy3.11"), text.index("python-version: '3.12'"))

    def test_both_launch_sites_take_the_choice(self):
        from goal2.desktop import competitive
        from goal2.game import watched_jobs
        for module in (competitive, watched_jobs):
            with self.subTest(module=module.__name__):
                self.assertIn("worker_command(", Path(module.__file__).read_text())


def pypy():
    fresh()
    found = ep.engine_python()
    if not ep._is_pypy311(found):
        raise unittest.SkipTest("PyPy 3.11 absent: uv python install pypy@3.11, or set GOAL2_ENGINE_PYTHON")
    return found


class UnderPyPy(unittest.TestCase):
    """A real job's worker under PyPy, against the same match played under CPython: in a CPython child (#500: no
    match in the test process), started first so the two run side by side."""

    @classmethod
    def setUpClass(cls):
        requires.require(**requires.WATCHED)
        cls.pypy = pypy()

    def until_done(self, jobs, token, limit=1800):
        deadline, seen = time.monotonic() + limit, []
        while time.monotonic() < deadline:
            seen.extend(jobs.poll(token))
            if not jobs.busy:
                return seen
            time.sleep(.01)
        self.fail("the worker did not finish")

    @requires.need(slow=True)
    def test_a_watched_job_under_pypy_is_the_match_played_here(self):
        from goal2.game.watched_jobs import WatchedJobs
        from goal2.tests.test_watched_publication import Owner
        from goal2.game.state import from_savestate
        raw = self.raw();state = from_savestate(raw);state.captain = 0     # as test_watched_adapter's state()
        owner = Owner(state, raw);before = copy.deepcopy(owner.state)
        t = time.monotonic()
        cpython = pypy_engine.start("goal2.game.watched_match:run_watched_match", before, raw, Fixture(7, 19, 21),
                                    reference_seed=257, delay_byte=0, record_draws=True, interpreter=sys.executable)
        jobs = WatchedJobs(owner);self.addCleanup(jobs.close)
        token = jobs.start(Fixture(7, 19, 21), reference_seed=257, delay_byte=0, record_draws=True)
        self.assertEqual(jobs.interpreter, self.pypy)
        events = self.until_done(jobs, token);worker_s = time.monotonic() - t
        expected = cpython.result();here_s = time.monotonic() - t
        self.assertEqual(jobs.outcome, expected)
        self.assertEqual(tuple(events), expected.events)
        print(f"watched: worker under PyPy {worker_s:.1f} s wall, CPython child {here_s:.1f} s wall", flush=True)

    @requires.need(slow=True)
    def test_a_competitive_job_under_pypy_is_the_match_played_here(self):
        from goal2.desktop.competitive import CompetitiveJobs
        from goal2.tests.test_desktop_competitive_jobs import CompetitiveJobsTests
        from goal2.tests.test_campaign_competitive_publication import campaign
        t = time.monotonic();s, raw, fixture = campaign(42, 200)     # test_desktop_competitive_jobs.direct(200)
        cpython = pypy_engine.start("goal2.game.competitive_match:run_competitive_match", s, raw, fixture,
                                    record_draws=True, interpreter=sys.executable)
        case = CompetitiveJobsTests("test_real_kind2_and_tied_knockout_match_direct_result_events_memory_seeds")
        CompetitiveJobsTests.setUpClass();self.addCleanup(CompetitiveJobsTests.tearDownClass)
        case.setUp();self.addCleanup(case.doCleanups)
        jobs = CompetitiveJobs(case.owner);self.addCleanup(jobs.close)
        token = jobs.start(record_draws=True)
        self.assertEqual(jobs.interpreter, self.pypy)
        events = self.until_done(jobs, token);worker_s = time.monotonic() - t
        expected = cpython.result();here_s = time.monotonic() - t
        self.assertEqual(jobs.outcome, expected)
        self.assertEqual(tuple(events), expected.events)
        print(f"competitive: worker under PyPy {worker_s:.1f} s wall, CPython child {here_s:.1f} s wall", flush=True)

    def raw(self):
        from goal2.engine.original_match.assets import reference_image
        return reference_image(ROOT / ".cache")


if __name__ == "__main__":
    unittest.main()
