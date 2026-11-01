"""[designed: owner, 2026-11-01, #505] A PR's gate plays only the slow tests its changes can reach.

tools/slow_reach.py computes the reach from the import graph (imports, relative imports, tools/ modules by bare
name, goal2 modules named in strings, package __init__ files); the gate's automatic mode turns slow tests on
for those modules only, --slow for all; the CI plumbing no longer counts as a change the slow tests guard."""
import importlib
import io
from contextlib import redirect_stdout
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]


def tool(name):
    sys.path.insert(0, str(ROOT / "tools"))
    try:
        return importlib.import_module(name)
    finally:
        sys.path.remove(str(ROOT / "tools"))


TREE = {
    "pyproject.toml": "",
    "goal2/__init__.py": "",
    "goal2/a/__init__.py": "",
    "goal2/a/x.py": "from . import y\n",
    "goal2/a/y.py": "",
    "goal2/a/z.py": "",
    "goal2/a/tables/t.hex": "00\n",
    "goal2/b/__init__.py": "",
    "goal2/b/w.py": "COMMAND = ['-m', 'goal2.a.z']\n",
    "goal2/c/__init__.py": "",
    "goal2/c/v.py": "",
    "goal2/tests/__init__.py": "",
    "goal2/tests/requires.py": "",
    "goal2/tests/test_one.py": "import goal2.a.x\n",
    "goal2/tests/test_two.py": "from goal2.b import w\n",
    "goal2/tests/test_three.py": "from goal2.c.v import thing\n",
    "goal2/tests/test_four.py": "from helper import load\n",
    "tools/helper.py": "PATH = 'data.json'\n",
    "tools/data.json": "{}\n",
    "docs/notes.md": "",
}


class Reach(unittest.TestCase):
    def setUp(self):
        self.reach = tool("slow_reach")
        folder = tempfile.TemporaryDirectory();self.addCleanup(folder.cleanup)
        self.root = Path(folder.name)
        for path, text in TREE.items():
            (self.root / path).parent.mkdir(parents=True, exist_ok=True)
            (self.root / path).write_text(text)

    def affected(self, *changed):
        return self.reach.Graph(self.root).affected(list(changed))

    def test_imports_relative_imports_and_named_workers_reach(self):
        self.assertEqual(self.affected("goal2/a/y.py"), {"test_one"})              # through x's `from . import y`
        self.assertEqual(self.affected("goal2/a/z.py"), {"test_two"})              # named in a string: a worker
        self.assertEqual(self.affected("goal2/c/v.py"), {"test_three"})
        self.assertEqual(self.affected("goal2/a/__init__.py"), {"test_one", "test_two"})   # the package runs too

    def test_a_test_module_reaches_itself_and_unrelated_files_reach_nothing(self):
        self.assertEqual(self.affected("goal2/tests/test_three.py"), {"test_three"})
        self.assertEqual(self.affected("docs/notes.md"), set())

    def test_data_reaches_what_reads_its_area_and_tools_data_its_readers(self):
        self.assertEqual(self.affected("goal2/a/tables/t.hex"), {"test_one", "test_two"})
        self.assertEqual(self.affected("tools/data.json"), {"test_four"})          # helper names it

    def test_dependencies_requires_and_an_unparseable_file_reach_everything(self):
        every = {"test_one", "test_two", "test_three", "test_four"}
        for path in ("pyproject.toml", "goal2/tests/requires.py", "goal2/tests/__init__.py"):
            with self.subTest(path=path):
                self.assertEqual(self.affected(path), every)
        (self.root / "goal2/c/v.py").write_text("def broken(:\n")
        self.assertEqual(self.affected("goal2/a/y.py"), every)

    def test_the_repository_graph(self):
        graph = self.reach.Graph(ROOT)
        self.assertEqual(graph.broken, set())
        jobs = graph.affected(["goal2/game/engine_python.py"])
        self.assertTrue({"test_watched_jobs", "test_desktop_competitive_jobs"} <= jobs, jobs)
        quick = graph.affected(["goal2/desktop/jobs.py"])
        self.assertIn("test_campaign_substitutions", quick)
        self.assertNotIn("test_core_team_t107", quick)


class Gate(unittest.TestCase):
    def setUp(self):
        self.gate = tool("check_premerge")

    def test_the_ci_plumbing_is_not_a_change_the_slow_tests_guard(self):
        for path in ("tools/check_premerge.py", "tools/ci_changes.py", "tools/slow_reach.py",
                     ".github/workflows/linux-slow.yml", ".github/workflows/windows-slow.yml"):
            with self.subTest(path=path):
                self.assertIsNone(self.gate.SLOW_PATHS.match(path))
        for path in ("goal2/engine/original_match/match.py", "goal2/game/engine_python.py", "pyproject.toml",
                     "tools/watched_evidence.py"):
            with self.subTest(path=path):
                self.assertIsNotNone(self.gate.SLOW_PATHS.match(path))

    def chosen(self, changed, *flags):
        seen = {}

        def check_tests(jobs, python, slow, layout_slow=True):
            seen["slow"] = slow
        out = io.StringIO()
        with patch.object(self.gate, "check_checkout"), patch.object(self.gate, "check_originals"), \
                patch.object(self.gate.subprocess, "run"), patch.object(self.gate, "check_tests", check_tests), \
                patch.object(self.gate, "slow_changes", return_value=changed), redirect_stdout(out):
            self.assertEqual(self.gate.main(["--expected-head", "0" * 40, *flags]), 0)
        return seen["slow"], out.getvalue()

    def test_automatic_plays_only_the_reached_modules(self):
        slow, out = self.chosen(["goal2/desktop/jobs.py"])
        self.assertIsInstance(slow, set)
        self.assertIn("test_campaign_substitutions", slow)
        self.assertNotIn("test_core_team_t107", slow)
        self.assertIn(f"RUN slow tests in {len(slow)} modules they can reach", out)

    def test_slow_plays_everything_and_no_guarded_change_nothing(self):
        self.assertIs(self.chosen(["goal2/desktop/jobs.py"], "--slow")[0], True)
        self.assertIs(self.chosen([])[0], False)
        self.assertIs(self.chosen(None)[0], True)                # origin/main unreadable: everything, to be safe

    def test_only_the_chosen_modules_run_their_slow_tests(self):
        calls = []

        def runner(module, python, slow):
            calls.append((module, slow))
            return module, 0, 0.0, "Ran 1 test in 0.1s\n\nOK"
        with redirect_stdout(io.StringIO()):
            self.gate.check_tests(4, sys.executable, {"test_campaign_substitutions"}, runner, layout_slow=False)
        slow = {m for m, s in calls if s}
        self.assertEqual(slow, {"test_campaign_substitutions"})
        self.assertGreater(len(calls), 100)


if __name__ == "__main__":
    unittest.main()
