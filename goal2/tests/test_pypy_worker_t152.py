"""[designed: T152] The match workers run under PyPy 3.11 when there is one, else under this interpreter.

The choice (goal2/game/engine_python.py) honours GOAL2_ENGINE_PYTHON as given, takes only a PyPy 3.11 it finds, and
without either fails with its reason, never falling back to this interpreter (owner, 2026-11-01, #496); a desktop
window still opens, and starting a match shows the reason. A watched job and a competitive job run through their workers under PyPy give the same
outcome as the same match played in this (CPython) process."""
import copy
import os
import sys
import time
import unittest
from pathlib import Path
from unittest.mock import patch

from goal2.engine.original_match import Fixture
from goal2.game import engine_python as ep
from goal2.tests import requires

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

    def test_without_pypy_a_match_fails_with_its_reason_never_on_this_interpreter(self):
        env = {k: v for k, v in os.environ.items() if k != "GOAL2_ENGINE_PYTHON"}
        with patch.dict(os.environ, env, clear=True), patch.object(ep.shutil, "which", return_value=None), \
                patch.object(ep, "_uv_pythons", return_value=iter(())):
            with self.assertRaises(ep.EngineRuntimeMissing) as caught:
                ep.worker_command("goal2.game.watched_worker")
        self.assertIn("uv python install pypy@3.11", str(caught.exception))
        self.assertIn("GOAL2_ENGINE_PYTHON", str(caught.exception))
        self.assertIsInstance(caught.exception, OSError)    # the desktop's starts show an OSError in the status line

    def test_without_pypy_the_window_still_builds_its_bridges(self):
        from types import SimpleNamespace
        from goal2.desktop.competitive import CompetitiveJobs
        from goal2.game.watched_jobs import WatchedJobs
        missing = patch.object(ep, "engine_python", side_effect=ep.EngineRuntimeMissing(ep.MISSING))
        with missing as chosen:
            for cls in (WatchedJobs, CompetitiveJobs):
                with self.subTest(bridge=cls.__name__):
                    self.assertIsNone(cls(SimpleNamespace()).command)    # the choice waits for the start
            chosen.assert_not_called()
        self.assertEqual((WatchedJobs.WORKER, CompetitiveJobs.WORKER),
                         ("goal2.game.watched_worker", "goal2.desktop.competitive_worker"))

    def test_a_found_interpreter_that_is_not_pypy_311_is_passed_over(self):
        env = {k: v for k, v in os.environ.items() if k != "GOAL2_ENGINE_PYTHON"}
        with patch.dict(os.environ, env, clear=True), patch.object(ep.shutil, "which", return_value=sys.executable), \
                patch.object(ep, "_uv_pythons", return_value=iter(())):
            with self.assertRaises(ep.EngineRuntimeMissing):
                ep.engine_python()
            self.assertFalse(ep._is_pypy311(sys.executable))        # this process is CPython
        self.assertFalse(ep._is_pypy311(ROOT / "no-such-python"))

    def test_ci_gives_the_workers_pypy_311_and_keeps_cpython_on_path(self):
        for name in ("ci.yml", "windows.yml"):
            with self.subTest(workflow=name):
                text = (ROOT / ".github/workflows" / name).read_text()
                self.assertIn("python-version: 'pypy3.11'\n          update-environment: false", text)
                self.assertIn('GOAL2_ENGINE_PYTHON=${{ steps.pypy.outputs.python-path }}', text)
                self.assertLess(text.index("pypy3.11"), text.index("python-version: '3.12'"))

    def test_a_fresh_checkout_gets_pypy_311(self):
        self.assertIn("uv python install -q pypy@3.11", (ROOT / "tools/cloud_setup.sh").read_text())

    def test_both_launch_sites_take_the_choice(self):
        from goal2.desktop import competitive
        from goal2.game import watched_jobs
        # [designed: #496] one launch site: the competitive bridge inherits WatchedJobs.start with its own WORKER
        self.assertIn("worker_command(self.WORKER)", Path(watched_jobs.__file__).read_text())
        self.assertNotIn("Popen", Path(competitive.__file__).read_text())
        self.assertIn("super().start(", Path(competitive.__file__).read_text())


def pypy():
    fresh()
    try:
        found = ep.engine_python()
    except ep.EngineRuntimeMissing:
        found = None
    if not found or not ep._is_pypy311(found):
        raise unittest.SkipTest("PyPy 3.11 absent: uv python install pypy@3.11, or set GOAL2_ENGINE_PYTHON")
    return found


class UnderPyPy(unittest.TestCase):
    """A real job's worker under PyPy, against the same match played here."""

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
        from goal2.game.watched_match import run_watched_match
        from goal2.tests.test_watched_publication import Owner
        from goal2.game.state import from_savestate
        raw = self.raw();state = from_savestate(raw);state.captain = 0     # as test_watched_adapter's state()
        owner = Owner(state, raw);before = copy.deepcopy(owner.state)
        jobs = WatchedJobs(owner);self.addCleanup(jobs.close)
        token = jobs.start(Fixture(7, 19, 21), reference_seed=257, delay_byte=0, record_draws=True)
        self.assertEqual(jobs.interpreter, self.pypy)
        t = time.monotonic();events = self.until_done(jobs, token);worker_s = time.monotonic() - t
        t = time.process_time()
        expected = run_watched_match(before, raw, Fixture(7, 19, 21), reference_seed=257, delay_byte=0, record_draws=True)
        here_s = time.process_time() - t
        self.assertEqual(jobs.outcome, expected)
        self.assertEqual(tuple(events), expected.events)
        print(f"watched: worker under PyPy {worker_s:.1f} s wall, here (CPython) {here_s:.1f} s CPU", flush=True)

    @requires.need(slow=True)
    def test_a_competitive_job_under_pypy_is_the_match_played_here(self):
        from goal2.desktop.competitive import CompetitiveJobs
        from goal2.tests.test_desktop_competitive_jobs import CompetitiveJobsTests, direct
        case = CompetitiveJobsTests("test_real_kind2_and_tied_knockout_match_direct_result_events_memory_seeds")
        CompetitiveJobsTests.setUpClass();self.addCleanup(CompetitiveJobsTests.tearDownClass)
        case.setUp();self.addCleanup(case.doCleanups)
        jobs = CompetitiveJobs(case.owner);self.addCleanup(jobs.close)
        token = jobs.start(record_draws=True)
        self.assertEqual(jobs.interpreter, self.pypy)
        t = time.monotonic();events = self.until_done(jobs, token);worker_s = time.monotonic() - t
        t = time.process_time();expected = direct(200);here_s = time.process_time() - t
        self.assertEqual(jobs.outcome, expected)
        self.assertEqual(tuple(events), expected.events)
        print(f"competitive: worker under PyPy {worker_s:.1f} s wall, here (CPython) {here_s:.1f} s CPU", flush=True)

    def raw(self):
        from goal2.engine.original_match.assets import reference_image
        return reference_image(ROOT / ".cache")


if __name__ == "__main__":
    unittest.main()
