"""[designed: #275] A test whose requirement is absent skips with a one-line reason, never errors."""
from pathlib import Path
import subprocess
import sys
import tempfile
import textwrap
import unittest
from unittest.mock import patch

from goal2.tests import requires

ROOT = Path(__file__).resolve().parents[2]


class Reasons(unittest.TestCase):
    def test_each_absent_requirement_names_itself_and_its_remedy(self):
        with tempfile.TemporaryDirectory() as folder, patch.object(requires, "CACHE", Path(folder)):
            (Path(folder) / "present.sav").write_bytes(b"")
            self.assertIsNone(requires.absent(modules=("json",), files=("present.sav",)))
            self.assertEqual(requires.absent(modules=("PySide6_not_installed",)),
                             "optional dependency PySide6_not_installed absent: "
                             "pip install -e '.[PySide6_not_installed]'")
            with patch.dict(requires.EXTRAS, {"PySide6_not_installed": "desktop"}):
                self.assertIn("'.[desktop]'", requires.absent(modules=("PySide6_not_installed",)))
            self.assertEqual(requires.absent(files=("present.sav", "GOAL.DAT")),
                             "original-game file .cache/GOAL.DAT absent: python3 tools/artifacts.py pull")
            self.assertEqual(requires.absent(generated={"legacy/manifest.json": "python3 tools/x.py"}),
                             "generated file .cache/legacy/manifest.json absent: python3 tools/x.py")
        with patch.dict("os.environ", {"GOAL2_ARCHAEOLOGY": "/nonexistent/goal2-archaeology"}):
            self.assertEqual(requires.archaeology(), Path("/nonexistent/goal2-archaeology"))
            self.assertIsNone(requires.archaeology_path())
            self.assertEqual(requires.absent(archaeology=True), "goal2-archaeology checkout absent: "
                             "set GOAL2_ARCHAEOLOGY, or run tools/cloud_setup.sh")
        with patch.object(requires, "SLOW", False):
            self.assertEqual(requires.absent(slow=True), "slow test: set GOAL2_SLOW=1 to run it")
        with patch.object(requires, "SLOW", True):
            self.assertIsNone(requires.absent(slow=True))

    def test_batch_cases_one_by_default_all_when_slow(self):
        # [designed: #275] Fails if cases() ever drops the slow switch or the default case.
        with patch.object(requires, "SLOW", False):
            self.assertEqual(requires.cases(dict(a=1, b=2, c=3).items()), [("a", 1)])
        with patch.object(requires, "SLOW", True):
            self.assertEqual(requires.cases(dict(a=1, b=2, c=3).items()), [("a", 1), ("b", 2), ("c", 3)])

    def test_require_raises_the_skip_and_need_decorates(self):
        with self.assertRaisesRegex(unittest.SkipTest, "optional dependency no_such_module absent"):
            requires.require(modules=("no_such_module",))
        requires.require(modules=("json",))

        class Case(unittest.TestCase):
            @requires.need(modules=("no_such_module",))
            def test_skipped(self):
                raise AssertionError("must not run")

            @requires.need(modules=("json",))
            def test_runs(self):
                pass

        result = unittest.TestResult()
        unittest.defaultTestLoader.loadTestsFromTestCase(Case).run(result)
        self.assertEqual((result.testsRun, len(result.errors), len(result.failures)), (2, 0, 0))
        self.assertEqual([reason for _, reason in result.skipped],
                         ["optional dependency no_such_module absent: pip install -e '.[no_such_module]'"])


class ModuleSkip(unittest.TestCase):
    def test_discovery_reports_a_module_skipped_at_import_with_its_reason(self):
        # [designed] The gate runs each module by discovery, which turns an import-time skip into
        # a skipped test; loading the same module by name would error (unittest's loader).
        with tempfile.TemporaryDirectory() as folder:
            package = Path(folder) / "probe"
            package.mkdir()
            (package / "__init__.py").write_text("")
            (package / "test_needs.py").write_text(textwrap.dedent("""\
                import unittest
                from goal2.tests import requires
                requires.require(modules=("no_such_module",))
                class Never(unittest.TestCase):
                    def test_never(self):
                        raise AssertionError("must not run")
                """))
            run = subprocess.run([sys.executable, "-m", "unittest", "discover", "-s", "probe", "-t", ".",
                                  "-p", "test_needs.py", "-v"], cwd=folder, capture_output=True, text=True,
                                 env={"PYTHONPATH": str(ROOT), "PATH": "/usr/bin:/bin"})
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertIn("skipped \"optional dependency no_such_module absent", run.stderr)
        self.assertIn("OK (skipped=1)", run.stderr)


if __name__ == "__main__":
    unittest.main()
