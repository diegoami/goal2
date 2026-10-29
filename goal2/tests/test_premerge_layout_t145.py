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


if __name__ == "__main__":
    unittest.main()
