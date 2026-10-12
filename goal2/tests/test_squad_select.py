"""Tests for `goal2.ui.squad`.

[confirmed: F011 (squad row drawing at 1771:4E22→4D8A); T06 (state adapter's
managed_squad); SQ-5 (eleven = first 11 of squad in country-record order);
T11 (input layer, screen pattern).]
"""
import unittest
from unittest.mock import MagicMock

from goal2.engine.state import GameState
from goal2.ui.squad import _render, run_squad_select
from goal2.ui.grid import Grid, WIDTH
from goal2.ui.input import Key
from goal2.ui.plain_renderer import render


# ── Mock GoalDat ────────────────────────────────────────────────────────────

def _make_goaldat() -> MagicMock:
    """Return a GoalDat-like mock whose player_names[1..20] are "P1".."P20"
    and player_initials[1..20] are "A".."T"."""
    gd = MagicMock()
    # player_names[0] = "", player_names[1..20] = "P1".."P20"
    gd.player_names = [""] + [f"P{i}" for i in range(1, 21)]
    # player_initials[0] = "", player_initials[1..20] = "A".."T"
    gd.player_initials = [""] + [chr(ord("A") + i - 1) for i in range(1, 21)]
    return gd


def _make_state() -> GameState:
    """Return a GameState with a 20-player managed_squad."""
    return GameState(
        players=[b"\x00" * 20] * 3061,
        countries=[b"\x00" * 0xBF] * 129,
        managed_country=7,
        managed_squad=list(range(1, 21)),  # [1, 2, ..., 20]
        rng_seed_7b62=0,
        rng_seed_8336=0,
        match_state={},
        vga=b"\x00" * 4000,
        mem=bytearray(1 << 16),
    )


def _keys(*items: Key):
    """Return an iterator that yields Key values then stops cleanly."""
    return iter(items)


# ── run_squad_select tests ─────────────────────────────────────────────────

class TestRunSquadSelect(unittest.TestCase):
    def setUp(self):
        self.gd = _make_goaldat()
        self.state = _make_state()

    def test_enter_returns_true_and_sets_eleven_and_captain_at_1(self):
        """Done-when 2a: Enter at cursor=1 returns True, captain=1, eleven=[1..11]."""
        result = run_squad_select(self.gd, _keys(Key.ENTER), state=self.state)
        self.assertTrue(result)
        self.assertEqual(self.state.captain, 1)
        self.assertEqual(self.state.starting_eleven, list(range(1, 12)))

    def test_down_down_enter_returns_true_and_captain_at_3(self):
        """Done-when 2b: DOWN×2 + Enter at cursor=3 returns True, captain=3.

        Mutation: deleting the DOWN handler makes the cursor stay at 1 and
        captain=1, failing the assertion.
        """
        result = run_squad_select(self.gd, _keys(Key.DOWN, Key.DOWN, Key.ENTER), state=self.state)
        self.assertTrue(result)
        self.assertEqual(self.state.captain, 3)

    def test_esc_returns_false_and_does_not_touch_state(self):
        """Done-when 2c: Esc returns False and does not touch starting_eleven or captain.

        State is pre-set to sentinel values and checked unchanged after Esc.
        Mutation: making Esc return True fails the boolean assertion; making
        Esc write state fails the sentinel assertion.
        """
        state = _make_state()
        state.starting_eleven = [-1] * 11
        state.captain = -1
        result = run_squad_select(self.gd, _keys(Key.ESC), state=state)
        self.assertFalse(result)
        self.assertEqual(state.starting_eleven, [-1] * 11)
        self.assertEqual(state.captain, -1)

    def test_up_clamped_at_1(self):
        """Done-when 2d: UP×2 at cursor=1 stays at 1; Enter returns True with captain=1."""
        result = run_squad_select(self.gd, _keys(Key.UP, Key.UP, Key.ENTER), state=self.state, page_size=20)
        self.assertTrue(result)
        self.assertEqual(self.state.captain, 1)

    def test_down_clamped_at_20(self):
        """Done-when 2e: DOWN×30 at cursor=20 stays at 20; Enter returns True with captain=20."""
        result = run_squad_select(self.gd, _keys(*([Key.DOWN] * 30), Key.ENTER), state=self.state)
        self.assertTrue(result)
        self.assertEqual(self.state.captain, 20)

    def test_captain_is_in_managed_squad(self):
        """Done-when 4: captain is one of the 20 managed_squad entries."""
        state = _make_state()
        run_squad_select(self.gd, _keys(Key.DOWN, Key.DOWN, Key.ENTER), state=state)
        self.assertIn(state.captain, state.managed_squad)


# ── Render surface tests ────────────────────────────────────────────────────

class TestRenderSurface(unittest.TestCase):
    def setUp(self):
        self.gd = _make_goaldat()
        # Fresh state for each test (tests share self.gd but not self.state)
        self.state = _make_state()

    def test_cursor_row_starts_with_row_number(self):
        """Done-when 3a: cursor row's content starts with the row number (from input).

        Mutation: hardcoding the row number or reading from the wrong row fails.
        """
        for cursor in [1, 15, 20]:
            state = _make_state()
            grid = _render(self.gd, state, cursor=cursor, page_size=20)
            lines = render(grid).split("\n")
            self.assertTrue(
                lines[cursor].startswith(f" {cursor:2d}  "),
                f"cursor={cursor}: row {cursor!r} doesn't start with {cursor!r}",
            )

    def test_title_shows_cursor_number_from_input(self):
        """Done-when 3b: title row holds the cursor number derived from the input.

        Two distinct cursor values (1 and 15) catch a hardcoded cursor in the title.
        Mutation: replacing {cursor} with a literal fails the second test case.
        """
        for cursor in [1, 15]:
            state = _make_state()
            grid = _render(self.gd, state, cursor=cursor, page_size=20)
            lines = render(grid).split("\n")
            self.assertIn(f"SELECT CAPTAIN  {cursor}", lines[0])

    def test_captain_marker_after_enter(self):
        """Done-when 4: after Enter, the captain row in the rendered grid shows ' C'.

        The marker is fixed-column (post-Enter state), not cursor-dependent.
        Mutation: making the marker cursor-dependent (showing on every cursor row)
        fails the second assertion.
        """
        state = _make_state()
        # Enter with cursor at row 3 → captain = managed_squad[2] = 3
        run_squad_select(self.gd, _keys(Key.DOWN, Key.DOWN, Key.ENTER), state=state)
        # The captain is player number 3, which is at row 3
        captain_row = state.managed_squad.index(state.captain) + 1  # row number (1-indexed)
        grid = _render(self.gd, state, cursor=captain_row, page_size=20)
        lines = render(grid).split("\n")
        # The captain row has " C" at columns 78-79 (right edge of 80-col grid)
        self.assertEqual(
            lines[captain_row][78:80],
            " C",
            f"captain row {captain_row} cols 78-79 should be ' C': {lines[captain_row][78:80]!r}",
        )
        # A non-captain row (row 5) has spaces at cols 78-79
        non_captain_row = 5
        if non_captain_row != captain_row:
            self.assertEqual(
                lines[non_captain_row][78:80],
                "  ",
                f"non-captain row {non_captain_row} cols 78-79 should be '  ': {lines[non_captain_row][78:80]!r}",
            )

    def test_no_captain_marker_before_enter(self):
        """Before Enter, no row has ' C' at the right edge (cols 78-79)."""
        state = _make_state()
        grid = _render(self.gd, state, cursor=1, page_size=20)
        lines = render(grid).split("\n")
        for row in range(1, 21):
            self.assertNotIn(
                " C",
                lines[row][78:80],
                f"row {row} cols 78-79 should not be ' C' before Enter: {lines[row][78:80]!r}",
            )


if __name__ == "__main__":
    unittest.main()
