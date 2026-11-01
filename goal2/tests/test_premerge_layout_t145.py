"""[designed: owner, 2026-10-29, T145] The pre-merge gate runs its cheap layout and page-reserve
modules first, with their slow tests, and stops before the full batch when one fails; otherwise
every other module runs once and the summary counts all of them."""
import importlib
from pathlib import Path
import re
import sys
import unittest

ROOT = Path(__file__).resolve().parents[2]
TESTS = ROOT / "goal2" / "tests"


def gate():
    sys.path.insert(0, str(ROOT / "tools"))
    try:
        return importlib.import_module("check_premerge")
    finally:
        sys.path.remove(str(ROOT / "tools"))


class LayoutFirst(unittest.TestCase):
    def setUp(self):
        self.gate = gate()
        self.modules = sorted(p.stem for p in TESTS.glob("test_*.py"))

    def fake(self, failing=()):
        calls = []

        def runner(module, python, slow):
            calls.append((module, slow))
            code = 1 if module in failing else 0
            return module, code, 0.0, f"{module} output\nRan 1 test in 0.1s\n\n" + ("FAILED (failures=1)" if code else "OK")
        return runner, calls

    def test_the_layout_modules_exist_and_check_bounds_or_the_reserve(self):
        self.assertTrue(self.gate.LAYOUT_FIRST)
        self.assertEqual(len(set(self.gate.LAYOUT_FIRST)), len(self.gate.LAYOUT_FIRST))
        for module in self.gate.LAYOUT_FIRST:
            self.assertIn(module, self.modules)
            self.assertNotIn(module, self.gate.SERIAL)
            source = (TESTS / f"{module}.py").read_text()
            self.assertTrue(re.search(r"fixed_page import problems|0\.9 ?\* ?", source), module)
        for module in ("test_core_team_t107", "test_core_team_back_t141"):
            self.assertIn(module, self.gate.LAYOUT_FIRST)

    def test_layout_runs_first_with_slow_tests_even_when_the_gate_chose_none(self):
        runner, calls = self.fake()
        self.gate.check_tests(4, sys.executable, False, runner)
        layout = len(self.gate.LAYOUT_FIRST)
        self.assertEqual(sorted(m for m, _ in calls[:layout]), sorted(self.gate.LAYOUT_FIRST))
        self.assertTrue(all(slow for _, slow in calls[:layout]))
        self.assertFalse(any(slow for _, slow in calls[layout:]))

    def test_fast_keeps_the_layout_stage_without_slow_tests(self):
        runner, calls = self.fake()
        self.gate.check_tests(4, sys.executable, False, runner, layout_slow=False)
        self.assertFalse(any(slow for _, slow in calls))

    def test_batch_fast_keeps_the_layout_slow_tests_and_drops_the_batch_ones(self):
        # [designed: owner, 2026-11-01] CI's PR and main runs: the local gate plays the matches
        from unittest.mock import patch
        seen = {}

        def check_tests(jobs, python, slow, layout_slow=True):
            seen.update(slow=slow, layout_slow=layout_slow)
        with patch.object(self.gate, "check_checkout"), patch.object(self.gate, "check_originals"), \
                patch.object(self.gate.subprocess, "run"), patch.object(self.gate, "check_tests", check_tests), \
                patch.object(self.gate, "slow_changes", return_value=["goal2/engine/x.py"]):
            self.assertEqual(self.gate.main(["--expected-head", "0" * 40, "--batch-fast"]), 0)
        self.assertEqual(seen, {"slow": False, "layout_slow": True})

    def test_a_failing_layout_module_stops_the_gate_before_the_full_batch(self):
        failing = self.gate.LAYOUT_FIRST[0]
        runner, calls = self.fake(failing={failing})
        from contextlib import redirect_stdout
        import io
        out = io.StringIO()
        with redirect_stdout(out), self.assertRaisesRegex(self.gate.ValidationError, "layout stage failed"):
            self.gate.check_tests(4, sys.executable, True, runner)
        self.assertEqual(sorted(m for m, _ in calls), sorted(self.gate.LAYOUT_FIRST))
        self.assertIn(f"FAIL goal2.tests.{failing}", out.getvalue())
        self.assertIn(f"{failing} output", out.getvalue())

    def test_with_layout_passing_every_module_runs_exactly_once_and_is_counted(self):
        runner, calls = self.fake()
        from contextlib import redirect_stdout
        import io
        out = io.StringIO()
        with redirect_stdout(out):
            self.gate.check_tests(4, sys.executable, True, runner)
        self.assertEqual(sorted(m for m, _ in calls), self.modules)
        self.assertIn(f"game tests: {len(self.modules)}/{len(self.modules)} modules pass", out.getvalue())
        serial = [m for m, _ in calls if m in self.gate.SERIAL]
        self.assertEqual([m for m, _ in calls][-len(serial):], serial)

    def test_a_failure_in_the_full_batch_still_fails_the_gate(self):
        late = next(m for m in self.modules if m not in self.gate.LAYOUT_FIRST and m not in self.gate.SERIAL)
        runner, _ = self.fake(failing={late})
        from contextlib import redirect_stdout
        import io
        with redirect_stdout(io.StringIO()), self.assertRaisesRegex(self.gate.ValidationError, late):
            self.gate.check_tests(4, sys.executable, False, runner)



class Progress(unittest.TestCase):
    """[designed: owner, 2026-11-01, #498] Each module's result is printed as it finishes, and while none
    finishes, a line names the modules still running."""

    def setUp(self):
        self.gate = gate()

    def test_a_result_is_printed_while_a_slower_module_still_runs(self):
        import io
        import threading
        import time
        from contextlib import redirect_stdout
        release, out = threading.Event(), io.StringIO()
        seen_early = []

        def run(module):
            if module == "slow_one":
                # the gate prints quick_one's result in its own thread, a moment after quick_one returns
                deadline = time.monotonic() + 5
                while "FAIL goal2.tests.quick_one" not in out.getvalue() and time.monotonic() < deadline:
                    time.sleep(0.01)
                seen_early.append(release.is_set() and "FAIL goal2.tests.quick_one" in out.getvalue())
                return module, 0, 0.0, "Ran 1 test in 0.1s\n\nOK"
            release.set()
            return module, 1, 0.0, "quick_one output\nRan 1 test in 0.1s\n\nFAILED (failures=1)"
        failed = []
        with redirect_stdout(out):
            self.gate.run_stage(["slow_one", "quick_one"], 2, run, failed, [0], 2)
        self.assertEqual(seen_early, [True])
        self.assertEqual(failed, ["quick_one"])
        self.assertIn("quick_one output", out.getvalue())

    def test_while_nothing_finishes_the_running_modules_are_named(self):
        import io
        import time
        from contextlib import redirect_stdout
        from unittest.mock import patch

        def run(module):
            time.sleep(0.5 if module == "long_one" else 0)
            return module, 0, 0.0, "Ran 1 test in 0.1s\n\nOK"
        out = io.StringIO()
        with redirect_stdout(out), patch.object(self.gate, "PROGRESS_S", 0.1):
            self.gate.run_stage(["short_one", "long_one"], 2, run, [], [0], 7)
        lines = out.getvalue().splitlines()
        progress = [line for line in lines if line.startswith("running ")]
        self.assertTrue(progress, out.getvalue())
        self.assertRegex(progress[0], r"^running 1: long_one \(0 min\); 1/7 modules done$")
        self.assertEqual(lines[-1], "PASS goal2.tests.long_one (0 s)")


if __name__ == "__main__":
    unittest.main()
