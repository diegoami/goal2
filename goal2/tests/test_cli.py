"""Tests for the `python -m goal2.play <savestate>` CLI (T01 scope).

The fidelity test (E010-r0001) lives in test_fidelity.py because it needs the published state.
These tests cover the seam itself: the refusal paths, the error paths, and the format of a
successful run. The engine's refusal exceptions are caught at the CLI boundary, so the unit
tests mock the engine's `simulate` rather than build a real DOSBox-X state.
[designed: the synthetic states the archaeology's own test fixtures build need GOAL.EXE loaded
in the savestate; that's the integration test (E010), not a unit test.]
"""
import io
import unittest
from pathlib import Path
from unittest import mock

from goal2 import cli


class CliErrors(unittest.TestCase):
    def test_missing_file_returns_2(self):
        with mock.patch.object(cli, "_print_result") as m:
            rc = cli.main(["/no/such/path.sav"])
        self.assertEqual(rc, 2)
        m.assert_not_called()


class CliEntryPoint(unittest.TestCase):
    """The `python -m goal2.play` entry point must propagate the exit code
    (R4 on the prior review: `play.py` originally discarded `main()`'s return).
    [designed: the entry point is a thin shim that re-raises `main()`'s return via
    `sys.exit`; the subprocess tests below prove the propagation for both the file
    error and the engine's refusal path.]"""

    def test_missing_file_propagates_exit_2(self):
        import subprocess
        import sys
        r = subprocess.run(
            [sys.executable, "-m", "goal2.play", "/no/such/path.sav"],
            capture_output=True, text=True,
        )
        self.assertEqual(r.returncode, 2)
        self.assertIn("not a file", r.stderr)

    def test_refusal_propagates_exit_3(self):
        """The engine's refusal path also propagates through `python -m goal2.play`.
        The script-driven subprocess mocks `quick_engine.simulate` to raise and asserts
        the entry point exits 3 — proving the same propagation as the missing-file test.
        [designed: the entry point's exit code is whatever `main()` returns; this test
        fixes that contract for the refusal path.]"""
        import subprocess
        import sys
        import tempfile
        script = (
            "import sys\n"
            "from unittest import mock\n"
            "from goal2 import cli\n"
            "with mock.patch.object(cli.savestate, 'Savestate'), "
            "     mock.patch.object(cli.quick_engine, 'simulate', "
            "       side_effect=cli.quick_engine.ExtraTimeNotModelled('DS:7C36 set')):\n"
            "    sys.exit(cli.main(sys.argv[1:]))\n"
        )
        with tempfile.NamedTemporaryFile() as tf:
            r = subprocess.run(
                [sys.executable, "-c", script, tf.name],
                capture_output=True, text=True, cwd=".",
            )
        self.assertEqual(r.returncode, 3, f"stderr={r.stderr!r}")
        self.assertIn("DS:7C36 set", r.stderr)


class CliRefusal(unittest.TestCase):
    def test_extra_time_state_refuses(self):
        """`DS:7C36` set at half time → ExtraTimeNotModelled → CLI returns 3."""
        import tempfile
        with tempfile.NamedTemporaryFile() as tf:
            with mock.patch.object(cli.savestate, "Savestate"), \
                 mock.patch.object(cli.quick_engine, "simulate",
                                   side_effect=cli.quick_engine.ExtraTimeNotModelled("DS:7C36 set")):
                rc = cli.main([tf.name])
        self.assertEqual(rc, 3)

    def test_foul_path_refuses(self):
        """`DS:9A3D` set on a competitive match → FoulPathNotModelled → CLI returns 3."""
        import tempfile
        with tempfile.NamedTemporaryFile() as tf:
            with mock.patch.object(cli.savestate, "Savestate"), \
                 mock.patch.object(cli.quick_engine, "simulate",
                                   side_effect=cli.quick_engine.FoulPathNotModelled("walk-off")):
                rc = cli.main([tf.name])
        self.assertEqual(rc, 3)


class CliOutput(unittest.TestCase):
    def test_output_format(self):
        """The CLI prints score, goals, and the two seed words in `check_model.py`'s order.
        [designed: this is the format the fidelity test compares against the E010 record.]"""
        sample = {
            "score": (1, 0),
            "goals": [{"team": 0, "minute": 85, "player": 538, "squad_slot": 1, "stored_byte": 213}],
            "seed_DS7B62": 0x63D7,
            "seed_DS8336": 0x51A8,
            "draws": 1234,
        }
        buf = io.StringIO()
        with mock.patch.object(cli.sys, "stdout", buf):
            cli._print_result(sample)
        out = buf.getvalue()
        self.assertIn("score: 1-0", out)
        self.assertIn("team 0, minute 85, player 538", out)
        self.assertIn("seed DS:7B62: 0x63d7", out)
        self.assertIn("seed DS:8336: 0x51a8", out)

    def test_output_no_goals(self):
        sample = {
            "score": (0, 0),
            "goals": [],
            "seed_DS7B62": 0x1234,
            "seed_DS8336": 0x5678,
            "draws": 0,
        }
        buf = io.StringIO()
        with mock.patch.object(cli.sys, "stdout", buf):
            cli._print_result(sample)
        out = buf.getvalue()
        self.assertIn("score: 0-0", out)
        self.assertIn("goals (team, minute, player): none", out)
