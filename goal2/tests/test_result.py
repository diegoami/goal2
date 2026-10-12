"""Tests for `goal2.ui.result`.

[confirmed: A-WATCH-1] The watched match is the quick engine's result shown
with commentary lines (goals, scorers, minutes), labelled a stand-in.

[confirmed: T01] `quick_engine.simulate(state)` returns a dict with `score`,
`goals`, and the two seed words (`seed_DS7B62`, `seed_DS8336`).

[designed: T14 screen layout] Title row 0: "RESULT  STAND-IN". Score row 2:
"FINAL SCORE  H-A". Goals rows 4..4+N-1: " MM  team T  scorer P". No goals
row: "  no goals". Seed row. Footer row 24: "ENTER CONTINUE  ESC QUIT".

[designed: T14] The screen never mutates `state`. Esc and Enter return
without writing. The `state` argument is accepted for API parity only.
"""
import subprocess
import unittest
from pathlib import Path

# [designed] Import cli first to trigger its sys.path setup for the
# vendored engine directory.
from goal2 import cli  # noqa: F401

from goal2.engine.quick_engine import FoulPathNotModelled, ExtraTimeNotModelled, simulate
from goal2.engine.savestate import Savestate
from goal2.ui.grid import Grid, HEIGHT
from goal2.ui.input import Key
from goal2.ui.plain_renderer import render
from goal2.ui.result import _render, run_result


ROOT = Path(__file__).resolve().parents[2]
CACHE = ROOT / ".cache"
ARCHAEOLOGY = Path(
    __import__("os").environ.get(
        "GOAL2_ARCHAEOLOGY", str(ROOT.parent.parent / "goal2-archaeology")
    )
)


def _fetch_e010_r0001() -> bytes:
    """Fetch E010-r0001's half-time savestate from the archaeology release.

    [confirmed: E010 release] Asset name embeds the record number:
    `*-E010-r0001-halftime.sav`.
    """
    sav_path = CACHE / "e010-r0001-halftime.sav"
    if not sav_path.is_file():
        CACHE.mkdir(parents=True, exist_ok=True)
        try:
            subprocess.run(
                [
                    "gh", "release", "download", "E010",
                    "--repo", "diegoami/goal2-archaeology",
                    "--pattern", "*.sav",
                    "--dir", str(CACHE),
                    "--skip-existing",
                ],
                check=True, capture_output=True, text=True,
            )
        except subprocess.CalledProcessError:
            raise FileNotFoundError("E010 release not fetchable")
        # Rename the downloaded file to the canonical name.
        for f in CACHE.iterdir():
            if f.name.endswith("-E010-r0001-halftime.sav"):
                if f != sav_path:
                    f.rename(sav_path)
                break
    if not sav_path.is_file():
        raise FileNotFoundError("E010-r0001 halftime savestate not in cache")
    return sav_path.read_bytes()


def _e010_or_skip() -> bytes:
    """Return E010-r0001 savestate bytes, or skip the test."""
    try:
        return _fetch_e010_r0001()
    except FileNotFoundError as e:
        raise unittest.SkipTest(f"E010-r0001 not fetchable: {e}")


def _run_engine(state_bytes: bytes) -> dict:
    """Run the vendored quick engine on the given savestate bytes and
    return the result dict."""
    sav = Savestate(state_bytes)
    return simulate(sav)


def _keys(*items: Key):
    """Return an iterator that yields Key values then stops cleanly."""
    return iter(items)


# ── Savestate fixture for the refusal path ────────────────────────────────────

def _foul_path_savestate() -> bytes:
    """Return a savestate that triggers FoulPathNotModelled.

    We build a minimal synthetic savestate by editing the E010 half-time
    savestate: set DS:9A3D != 0 (the foul-path gate at D5C1).
    """
    e010 = _e010_or_skip()
    # DS:9A3D is at offset 0x9A3D in the data segment.
    # Find the program base in the savestate to locate DS:0.
    sav = Savestate(e010)
    ds_base = sav.program().ds_base
    # The offset within the Memory component for DS:9A3D.
    addr = ds_base + 0x9A3D
    # Edit the memory: set byte at DS:9A3D to 1 (the foul-path gate value).
    from goal2.engine.savestate import with_memory
    edited = with_memory(e010, addr, bytes([1]))
    return edited


# ── run_result tests ─────────────────────────────────────────────────────────

class TestRunResult(unittest.TestCase):
    def setUp(self):
        self.state_bytes = _e010_or_skip()

    def test_enter_returns_true(self):
        """Done-when 3: run_result with ENTER returns True and the title
        row starts with 'RESULT  STAND-IN'."""
        grid = _render(self.state_bytes)
        lines = render(grid).split("\n")
        self.assertTrue(lines[0].startswith("RESULT  STAND-IN"))

        result = run_result(self.state_bytes, _keys(Key.ENTER))
        self.assertTrue(result)

    def test_enter_returns_true_with_path(self):
        """Done-when 3: run_result(savestate_path, [ENTER]) returns True.
        We write the savestate to a temp path and pass that path."""
        import tempfile
        with tempfile.NamedTemporaryFile(suffix=".sav", delete=False) as f:
            f.write(self.state_bytes)
            path = f.name
        try:
            result = run_result(path, _keys(Key.ENTER))
            self.assertTrue(result)
        finally:
            import os
            os.unlink(path)

    def test_esc_returns_false(self):
        """Done-when 4: run_result with ESC returns False."""
        result = run_result(self.state_bytes, _keys(Key.ESC))
        self.assertFalse(result)

    def test_score_row_content(self):
        """Done-when 3: the score row contains 'FINAL SCORE  ' followed by
        the score tuple elements joined by '-', computed from the engine's
        result (not hardcoded)."""
        # Run the engine to get the expected score.
        expected_result = _run_engine(self.state_bytes)
        expected_score = expected_result["score"]

        grid = _render(self.state_bytes)
        lines = render(grid).split("\n")
        # Row 2 is the score row.
        score_line = lines[2]
        expected_prefix = f"FINAL SCORE  {expected_score[0]}-{expected_score[1]}"
        self.assertIn(
            expected_prefix, score_line,
            f"score row should contain '{expected_prefix}', got {score_line!r}"
        )

    def test_title_starts_with_result_standin(self):
        """Done-when 6: title row 0 starts with 'RESULT  STAND-IN'."""
        grid = _render(self.state_bytes)
        lines = render(grid).split("\n")
        self.assertTrue(
            lines[0].startswith("RESULT  STAND-IN"),
            f"title row should start with 'RESULT  STAND-IN', got {lines[0]!r}",
        )

    def test_refusal_path_returns_false(self):
        """Done-when 5: a savestate that triggers FoulPathNotModelled
        causes run_result to return False with 'REFUSED: <substring>' on row 2."""
        try:
            foul_bytes = _foul_path_savestate()
        except unittest.SkipTest:
            self.skipTest("E010-r0001 not available for refusal fixture")

        # Run the engine on the foul-path savestate to confirm it refuses.
        sav = Savestate(foul_bytes)
        exc_type = None
        exc_msg = ""
        try:
            simulate(sav)
        except (FoulPathNotModelled, ExtraTimeNotModelled) as e:
            exc_type = type(e).__name__
            exc_msg = str(e)

        if exc_type is None:
            self.skipTest("foul-path fixture did not trigger an exception")

        # Now run the screen.
        result = run_result(foul_bytes, _keys(Key.ESC))
        self.assertFalse(result)

        # Build the grid to check row 2 content.
        grid = _render(foul_bytes)
        lines = render(grid).split("\n")
        self.assertIn("REFUSED:", lines[2])
        # The substring of the exception message should appear.
        self.assertIn(exc_msg, lines[2])

    def test_refusal_row_contains_substring(self):
        """Done-when 5: row 2 contains 'REFUSED: ' followed by a substring
        of the engine's exception message."""
        try:
            foul_bytes = _foul_path_savestate()
        except unittest.SkipTest:
            self.skipTest("E010-r0001 not available for refusal fixture")

        # Get the expected exception message.
        sav = Savestate(foul_bytes)
        expected_msg = ""
        try:
            simulate(sav)
        except (FoulPathNotModelled, ExtraTimeNotModelled) as e:
            expected_msg = str(e)

        if not expected_msg:
            self.skipTest("foul-path fixture did not trigger an exception")

        grid = _render(foul_bytes)
        lines = render(grid).split("\n")
        # The REFUSED line should contain the exception message as a substring.
        self.assertIn(
            expected_msg, lines[2],
            f"row 2 should contain exception message, got {lines[2]!r}"
        )


# ── Render surface tests ─────────────────────────────────────────────────────

class TestRenderSurface(unittest.TestCase):
    def setUp(self):
        self.state_bytes = _e010_or_skip()

    def test_title_row_0_starts_with_result_standin(self):
        """Done-when 6a: title row 0 starts with 'RESULT  STAND-IN'."""
        grid = _render(self.state_bytes)
        lines = render(grid).split("\n")
        self.assertTrue(lines[0].startswith("RESULT  STAND-IN"))

    def test_score_row_contains_score_from_engine(self):
        """Done-when 6b: row 2 contains 'FINAL SCORE  ' followed by the
        score tuple elements joined by '-', computed from the engine result
        (not hardcoded)."""
        # Run the engine to get the expected score.
        expected_result = _run_engine(self.state_bytes)
        expected_score = expected_result["score"]

        grid = _render(self.state_bytes)
        lines = render(grid).split("\n")
        expected_fragment = f"FINAL SCORE  {expected_score[0]}-{expected_score[1]}"
        self.assertIn(
            expected_fragment, lines[2],
            f"row 2 should contain '{expected_fragment}', got {lines[2]!r}",
        )

    def test_goal_rows_contain_team_and_scorer(self):
        """Done-when 6c: if result["goals"] is non-empty, rows 4..4+N-1
        each contain 'team ' and 'scorer ' (the engine's goal dict keys
        'team' and the scorer's player word, rendered as 'scorer P')."""
        expected_result = _run_engine(self.state_bytes)
        if not expected_result["goals"]:
            self.skipTest("E010-r0001 produced no goals")

        grid = _render(self.state_bytes)
        lines = render(grid).split("\n")
        n_goals = len(expected_result["goals"])
        for i, goal_line in enumerate(lines[4:4 + n_goals]):
            self.assertIn("team ", goal_line,
                          f"goal row {4+i} should contain 'team ', got {goal_line!r}")
            self.assertIn("scorer ", goal_line,
                          f"goal row {4+i} should contain 'scorer ', got {goal_line!r}")

    def test_no_goals_shows_no_goals_row(self):
        """If the engine result has 0 goals, _build_grid renders '  no goals' at row 4."""
        # Test the _build_grid helper directly with a synthetic result that has
        # no goals. This isolates the no-goals rendering path without depending
        # on a savestate that the engine produces 0 goals for.
        from goal2.ui.result import _build_grid
        synthetic_result = {
            "score": (0, 0),
            "goals": [],
            "seed_DS7B62": 0x1234,
            "seed_DS8336": 0x5678,
        }
        grid = _build_grid(synthetic_result, None)
        lines = render(grid).split("\n")
        # Row 4 should contain "no goals" (row 2 is the score row, row 3 blank).
        self.assertIn("no goals", lines[4])


if __name__ == "__main__":
    unittest.main()
