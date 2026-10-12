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
        The subprocess runs `goal2.play` as `__main__` (which executes the
        `if __name__ == "__main__": sys.exit(main())` shim) after a mock that
        raises `ExtraTimeNotModelled` from `quick_engine.simulate`. R2 on the
        round-2 review: the prior test inlined `cli.main(...)` with its own
        `sys.exit`, so a regression that removed `sys.exit` from `play.py` would
        still pass; this test runs the actual entry point under the mock.
        [designed: the entry point's exit code is whatever `play.py`'s
        `if __name__ == "__main__"` block returns; this test proves the refusal
        path propagates through it.]"""
        import os
        import runpy
        import sys
        import tempfile
        from unittest import mock
        from goal2 import cli
        # A path that exists at the moment main() runs. NamedTemporaryFile with
        # delete=False keeps it on disk; we clean it up explicitly.
        fd, path = tempfile.mkstemp(suffix=".sav")
        os.write(fd, b"not a savestate")
        os.close(fd)
        try:
            with mock.patch.object(cli.savestate, "Savestate"), \
                 mock.patch.object(cli.quick_engine, "simulate",
                                   side_effect=cli.quick_engine.ExtraTimeNotModelled("DS:7C36 set")):
                # `goal2.play` is a module whose top-level code is `if __name__ ==
                # "__main__": sys.exit(main())`. runpy with `run_name="__main__"`
                # runs that block, so play.py's shim is what raises SystemExit.
                # Patch sys.argv so argparse sees the path.
                saved_argv = sys.argv
                sys.argv = ["goal2.play", path]
                try:
                    with self.assertRaises(SystemExit) as cm:
                        runpy.run_module("goal2.play", run_name="__main__")
                finally:
                    sys.argv = saved_argv
            self.assertEqual(cm.exception.code, 3, f"got {cm.exception.code}")
        finally:
            os.unlink(path)


class CliRefusal(unittest.TestCase):
    def test_extra_time_state_refuses(self):
        """`DS:7C36` set at half time → ExtraTimeNotModelled → CLI returns 3.
        [confirmed: the vendored engine raises `ExtraTimeNotModelled` when `DS:7C36`
        is non-zero at the half-time stall (quick_engine.py:122, the
        `if self.sevenc36: raise ExtraTimeNotModelled(...)` check).]"""
        import tempfile
        with tempfile.NamedTemporaryFile() as tf:
            with mock.patch.object(cli.savestate, "Savestate"), \
                 mock.patch.object(cli.quick_engine, "simulate",
                                   side_effect=cli.quick_engine.ExtraTimeNotModelled("DS:7C36 set")):
                rc = cli.main([tf.name])
        self.assertEqual(rc, 3)

    def test_foul_path_refuses(self):
        """`DS:9A3D` set on a competitive match → FoulPathNotModelled → CLI returns 3.
        [confirmed: the vendored engine raises `FoulPathNotModelled` from `d5c1` when
        `DS:9A3D` is non-zero and the roll reaches the `7EEF` branch (quick_engine.py
        `d5c1`, the `raise FoulPathNotModelled("D5C1 reached the 278A/7EEF branch
        with 9A3D set")` line).]"""
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
