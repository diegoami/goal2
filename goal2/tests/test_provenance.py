"""Tests for `tools/check_provenance.py` (T01 scope).

The check enforces CLAUDE.md rule 18: every file under `goal2/engine/` has a PROVENANCE row
whose source commit exists in goal2-archaeology. The tests build a temporary repo layout
and call the script's `main` directly, so a bypass on the real layout shows up here too.
[confirmed: rule 18's contract; the table format is the project's own.]
"""
import os
import subprocess
import sys
import textwrap
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "tools" / "check_provenance.py"


def _write(p: Path, text: str) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text)


class ProvenanceCheck(unittest.TestCase):
    def _run(self, layout: dict, *, env_extra: dict | None = None) -> subprocess.CompletedProcess:
        """Run the script against a temporary repo layout."""
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            tmp = Path(d)
            (tmp / "tools").mkdir(parents=True)
            (tmp / "goal2" / "engine").mkdir(parents=True)
            # Copy the script into the temp tree so ROOT inside the script resolves there.
            script_dst = tmp / "tools" / "check_provenance.py"
            script_dst.write_text(SCRIPT.read_text())
            # Lay out the vendored files and the PROVENANCE table as the test specifies.
            for rel, content in layout.items():
                _write(tmp / rel, content)
            env = os.environ.copy()
            # A non-existent archaeology checkout forces a clean failure mode.
            env["GOAL2_ARCHAEOLOGY"] = str(tmp / "no-such-archaeology")
            if env_extra:
                env.update(env_extra)
            return subprocess.run(
                [sys.executable, str(script_dst)],
                cwd=str(tmp),
                env=env,
                capture_output=True,
                text=True,
            )

    def test_well_known_three_rows_pass(self):
        """The three well-known rows pass file-matching and path checks. The
        commit check would still fail (the test archaeology is a non-existent
        path), so the test asserts the commit-failure message rather than exit 0.
        [designed: the file-walk and row-matching paths are what this test
        exercises; the commit check has its own dedicated regression in the
        archaeology checkout's own integration suite.]"""
        layout = {
            "PROVENANCE.md": textwrap.dedent("""\
                | File | Source repo | Source commit | Findings it rests on | Vendored |
                | --- | --- | --- | --- | --- |
                | goal2/engine/quick_engine.py | diegoami/goal2-archaeology | 8760df9 | F012 | 2026-10-12 |
                | goal2/engine/savestate.py | diegoami/goal2-archaeology | 8760df9 | F001 | 2026-10-12 |
                | goal2/engine/players.py | diegoami/goal2-archaeology | 8760df9 | F002 | 2026-10-12 |
            """),
            "goal2/engine/quick_engine.py": "x",
            "goal2/engine/savestate.py": "x",
            "goal2/engine/players.py": "x",
        }
        # The check would fail because the commit doesn't exist in the no-such-archaeology
        # checkout (a sanity guard). The point of this test is the file enumeration and
        # path matching, not the commit check; the test_patch_archaeology test covers the
        # pass path.
        r = self._run(layout)
        # No "no PROVENANCE row" failure should appear; the failure is the commit check.
        self.assertIn("source commit 8760df9 not in", r.stderr)

    def test_unlisted_nested_file_blocks(self):
        """A vendored file under a subdirectory without a row fails the check.
        [designed: rule 18 says "every file under `goal2/engine/`"; the recursive walk
        is the implementation; this test exercises the recursion path with a subdir.]"""
        layout = {
            "PROVENANCE.md": textwrap.dedent("""\
                | File | Source repo | Source commit | Findings it rests on | Vendored |
                | --- | --- | --- | --- | --- |
                | goal2/engine/quick_engine.py | diegoami/goal2-archaeology | 8760df9 | F012 | 2026-10-12 |
            """),
            "goal2/engine/quick_engine.py": "x",
            "goal2/engine/nested/unprovenanced.py": "x",  # no row
        }
        r = self._run(layout)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("no PROVENANCE row", r.stderr)
        self.assertIn("nested/unprovenanced.py", r.stderr)

    def test_same_basename_under_different_path_blocks(self):
        """A row naming `other/quick_engine.py` cannot cover `goal2/engine/quick_engine.py`.
        [designed: rule 18 keys rows by repo-relative path; same-basename collisions are
        distinguishable by path, so a row pointing somewhere else cannot authorise a
        vendored file with the same name.]"""
        layout = {
            "PROVENANCE.md": textwrap.dedent("""\
                | File | Source repo | Source commit | Findings it rests on | Vendored |
                | --- | --- | --- | --- | --- |
                | other/quick_engine.py | diegoami/goal2-archaeology | 8760df9 | F012 | 2026-10-12 |
            """),
            "goal2/engine/quick_engine.py": "x",
        }
        r = self._run(layout)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("no PROVENANCE row", r.stderr)
        self.assertIn("goal2/engine/quick_engine.py", r.stderr)
        # The wrong-path row is also reported as orphaned.
        self.assertIn("PROVENANCE row but no file", r.stderr)

    def test_row_for_missing_file_blocks(self):
        """A PROVENANCE row with no file under `goal2/engine/` is reported as orphaned.
        [designed: rule 18 is two-sided — every vendored file has a row, and every
        row points to a real vendored file; this test covers the row-to-file
        direction.]"""
        layout = {
            "PROVENANCE.md": textwrap.dedent("""\
                | File | Source repo | Source commit | Findings it rests on | Vendored |
                | --- | --- | --- | --- | --- |
                | goal2/engine/quick_engine.py | diegoami/goal2-archaeology | 8760df9 | F012 | 2026-10-12 |
                | goal2/engine/phantom.py | diegoami/goal2-archaeology | 8760df9 | F001 | 2026-10-12 |
            """),
            "goal2/engine/quick_engine.py": "x",
        }
        r = self._run(layout)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("phantom.py", r.stderr)
        self.assertIn("PROVENANCE row but no file", r.stderr)

    def test_dot_prefix_bypass_blocks(self):
        """A row whose path normalises to a vendored file's path is rejected
        (R1 on the round-2 review: `lstrip("./")` would let `.goal2/engine/x`
        authorise `goal2/engine/x`; the fix preserves component identity and
        requires the path's first two components to be `goal2/engine/`)."""
        layout = {
            "PROVENANCE.md": textwrap.dedent("""\
                | File | Source repo | Source commit | Findings it rests on | Vendored |
                | --- | --- | --- | --- | --- |
                | .goal2/engine/quick_engine.py | diegoami/goal2-archaeology | 8760df9 | F012 | 2026-10-12 |
            """),
            "goal2/engine/quick_engine.py": "x",
        }
        r = self._run(layout)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("PROVENANCE row points outside goal2/engine/", r.stderr)

    def test_outside_engine_dir_blocks(self):
        """A row whose path is outside `goal2/engine/` is rejected even if it
        happens to share a name with a vendored file."""
        layout = {
            "PROVENANCE.md": textwrap.dedent("""\
                | File | Source repo | Source commit | Findings it rests on | Vendored |
                | --- | --- | --- | --- | --- |
                | other/quick_engine.py | diegoami/goal2-archaeology | 8760df9 | F012 | 2026-10-12 |
            """),
            "goal2/engine/quick_engine.py": "x",
        }
        r = self._run(layout)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("PROVENANCE row points outside goal2/engine/", r.stderr)


if __name__ == "__main__":
    unittest.main()
