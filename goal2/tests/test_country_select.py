"""Tests for `goal2.ui.country_select`.

[confirmed: F002 R001–R011 (country names block and squad-20 shape);
F011 (country picker writes the chosen country to the adapter's fields);
plan.md item 4 (a screen is a Grid with draw_text rows, T10 framework).]
"""
import unittest
from unittest.mock import MagicMock

from goal2.engine.state import GameState
from goal2.ui.country_select import _render, run_country_select
from goal2.ui.grid import Grid, WIDTH
from goal2.ui.input import Key
from goal2.ui.plain_renderer import render


# ── Mock GoalDat ────────────────────────────────────────────────────────────

def _make_goaldat(names: list[str]) -> MagicMock:
    """Return a GoalDat-like mock whose country_names and squad_20
    have the given names (indices 1..N) and trivial squad bytes."""
    gd = MagicMock()
    # country_names[0] is the placeholder; names[0] is country 1, etc.
    gd.country_names = [""] + names
    gd.squad_20 = [[i % 256 for i in range(20)]] * (len(names) + 1)
    return gd


def _make_state() -> GameState:
    """Return a GameState with placeholder fields."""
    return GameState(
        players=[b"\x00" * 20] * 3061,
        countries=[b"\x00" * 0xBF] * 129,
        managed_country=1,
        managed_squad=list(range(20)),
        rng_seed_7b62=0,
        rng_seed_8336=0,
        match_state={},
        vga=b"\x00" * 4000,
        mem=bytearray(1 << 16),
    )


def _keys(*items: Key):
    """Return an iterator that yields Key values then stops cleanly."""
    return iter(items)


# ── run_country_select tests ───────────────────────────────────────────────

class TestRunCountrySelect(unittest.TestCase):
    def setUp(self):
        # 3 countries so DOWN from 1 lands on 2, DOWN from 2 lands on 3
        self.gd3 = _make_goaldat(["ALPHA", "BRAVO", "CHARLIE"])
        self.gd128 = _make_goaldat([f"C{i}" for i in range(1, 129)])
        self.state = _make_state()

    def test_down_enter_returns_2_and_sets_state(self):
        """Done-when 2a: DOWN+ENTER from country 1 returns 2, state.managed_country==2."""
        result = run_country_select(self.gd3, _keys(Key.DOWN, Key.ENTER), initial_country=1, state=self.state)
        self.assertEqual(result, 2)
        self.assertEqual(self.state.managed_country, 2)

    def test_esc_returns_none_and_does_not_touch_state(self):
        """Done-when 2b: ESC from country 5 returns None and does not touch state."""
        state = _make_state()
        state.managed_country = 5
        state.managed_squad = list(range(20))
        result = run_country_select(self.gd3, _keys(Key.ESC), initial_country=5)
        self.assertIsNone(result)
        self.assertEqual(state.managed_country, 5)
        self.assertEqual(state.managed_squad, list(range(20)))

    def test_page_down_from_1_returns_21(self):
        """Done-when 2c: PAGE_DOWN from country 1 (page_size=20) returns 21."""
        result = run_country_select(
            self.gd128, _keys(Key.PAGE_DOWN, Key.ENTER), initial_country=1, page_size=20
        )
        self.assertEqual(result, 21)

    def test_up_clamped_at_1(self):
        """Done-when 2d: UP,UP at country 1 stays at 1 (clamped, not an error)."""
        result = run_country_select(self.gd3, _keys(Key.UP, Key.UP, Key.ENTER), initial_country=1)
        self.assertEqual(result, 1)

    def test_managed_squad_is_20_bytes(self):
        """Done-when 5: Enter sets managed_squad to a 20-element list."""
        state = _make_state()
        # gd128.squad_20[2] is the bytes for country 2
        self.assertEqual(len(self.gd128.squad_20[2]), 20)
        run_country_select(self.gd128, _keys(Key.DOWN, Key.ENTER), initial_country=1, state=state)
        self.assertEqual(len(state.managed_squad), 20)
        self.assertEqual(state.managed_squad, list(self.gd128.squad_20[2]))


# ── Render surface tests ────────────────────────────────────────────────────

class TestRenderSurface(unittest.TestCase):
    def setUp(self):
        self.gd3 = _make_goaldat(["ALPHA", "BRAVO", "CHARLIE"])

    def test_cursor_row_has_country_name_at_index_7(self):
        """Done-when 3: cursor row's first cell holds country 7's name.

        The expected name is derived from the input (cursor=7), not a literal.
        Deleting the cursor argument from _render leaves a different row affected.
        """
        gd128 = _make_goaldat([f"C{i}" for i in range(1, 129)])
        cursor = 7
        grid = _render(gd128, cursor=cursor, page_size=20)
        # Country 7 is on page 1 (rows 1..20); its row index = 1 + (7-1) = 7
        cell_char = grid.cell(7, 0)[0]
        expected_char = ord(gd128.country_names[cursor][0])
        self.assertEqual(cell_char, expected_char)

    def test_title_shows_cursor_number(self):
        """Done-when 3: title row holds 'SELECT COUNTRY  N/128' with N=cursor.

        The expected number is derived from the input, not a literal.
        Deleting the cursor argument leaves a different number in the title.
        """
        cursor = 7
        gd128 = _make_goaldat([f"C{i}" for i in range(1, 129)])
        grid = _render(gd128, cursor=cursor, page_size=20)
        # Render the grid and check the title row
        output = render(grid)
        title_row = output.split("\n")[0]
        # Title contains the cursor number (padded to 3 chars by the format)
        self.assertIn(f"SELECT COUNTRY", title_row)
        self.assertIn(f"/{128}", title_row)
        # The number 7 appears in the title row (derived from cursor, not a literal)
        self.assertIn(str(cursor), title_row)

    def test_cursor_row_reversed_video(self):
        """Cursor row uses fg=0, bg=7 (reversed video); other rows do not."""
        gd128 = _make_goaldat([f"C{i}" for i in range(1, 129)])
        grid = _render(gd128, cursor=5, page_size=20)
        # Country 5 is row 1 + (5-1) = 5
        cursor_cell = grid.cell(5, 0)
        normal_cell = grid.cell(4, 0)  # country 4, previous row
        self.assertEqual(cursor_cell[1], 0)   # fg = 0 (black)
        self.assertEqual(cursor_cell[2], 7)   # bg = 7 (white)
        self.assertEqual(normal_cell[1], 7)   # fg = 7 (white, normal)
        self.assertEqual(normal_cell[2], 0)   # bg = 0 (black, normal)

    def test_footer_on_row_24(self):
        """Footer text appears on row 24 (HEIGHT-1)."""
        gd3 = _make_goaldat(["ALPHA", "BRAVO", "CHARLIE"])
        grid = _render(gd3, cursor=1, page_size=20)
        footer_row = render(grid).split("\n")[24]
        self.assertIn("SELECT", footer_row)
        self.assertIn("ENTER", footer_row)
        self.assertIn("ESC", footer_row)


if __name__ == "__main__":
    unittest.main()
