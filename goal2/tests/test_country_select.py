"""Tests for `goal2.ui.country_select`.

[confirmed: F002 R001–R011 (country names block and squad-20 shape);
F011 (country picker writes the chosen country to the adapter's fields);
plan.md item 4 (a screen is a Grid with draw_text rows, T10 framework).]
"""
import unittest
from unittest.mock import MagicMock

from goal2.game.state import GameState
from goal2.ui.country_select import _render, run_country_select
from goal2.ui.grid import Grid, WIDTH
from goal2.ui.input import Key
from goal2.ui.plain_renderer import render


# ── Mock GoalDat ────────────────────────────────────────────────────────────

def _make_goaldat(names: list[str]) -> MagicMock:
    """Return a GoalDat-like mock whose country_names and squad_20
    have the given names (indices 1..N) and squad bytes that are
    distinctive by country index (for R3: deleting the assignment fails).

    squad_20[i] = [i * 7] * 20  — country 0 → [0,0,...], country 1 →
    [7,7,...], country 2 → [14,14,...], etc.
    """
    gd = MagicMock()
    gd.country_names = [""] + names
    squad = []
    for i in range(len(names) + 1):
        squad.append([i * 7] * 20)
    gd.squad_20 = squad
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
        self.gd3 = _make_goaldat(["ALPHA", "BRAVO", "CHARLIE"])
        self.gd128 = _make_goaldat([f"C{i}" for i in range(1, 129)])
        self.state = _make_state()

    def test_down_enter_returns_2_and_sets_state(self):
        """Done-when 2a: DOWN+ENTER from country 1 returns 2, state.managed_country==2."""
        result = run_country_select(self.gd3, _keys(Key.DOWN, Key.ENTER), initial_country=1, state=self.state)
        self.assertEqual(result, 2)
        self.assertEqual(self.state.managed_country, 2)

    def test_esc_returns_none_and_does_not_touch_state(self):
        """Done-when 2b / R4: ESC returns None and does not touch state.

        R4 fix: state is now passed to run_country_select so Esc's
        preservation guarantee is verified. State is pre-set to a known
        value and checked unchanged after the call.
        """
        state = _make_state()
        state.managed_country = 7
        state.managed_squad = [7] * 20
        result = run_country_select(self.gd3, _keys(Key.ESC), initial_country=5, state=state)
        self.assertIsNone(result)
        self.assertEqual(state.managed_country, 7)
        self.assertEqual(state.managed_squad, [7] * 20)

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

    def test_down_up_movement(self):
        """R2: Down then Up moves to 2 then back to 1; Enter returns 1.

        Mutation: if the Up handler is removed (made a no-op), Down+Up
        leaves cursor at 2 and Enter returns 2, failing the assertion.
        """
        result = run_country_select(self.gd3, _keys(Key.DOWN, Key.UP, Key.ENTER), initial_country=1)
        self.assertEqual(result, 1)

    def test_down_down_up_movement(self):
        """R2: Down×2 moves to 3, Up moves back to 2; Enter returns 2.

        Mutation: if the Up handler is removed, cursor stays at 3 and
        Enter returns 3, failing the assertion.
        """
        result = run_country_select(self.gd3, _keys(Key.DOWN, Key.DOWN, Key.UP, Key.ENTER), initial_country=1)
        self.assertEqual(result, 2)

    def test_managed_squad_is_20_runtime_player_ids(self):
        """[derived: T06/F011] Enter sets the 20 runtime player IDs."""
        state = _make_state()
        state.managed_squad = [99] * 20  # clearly different from any valid squad
        roster = list(range(41, 61))
        records = list(state.countries)
        records[2] = b"".join(p.to_bytes(2, "little") for p in roster) + bytes(0xBF - 40)
        state.countries = records
        run_country_select(self.gd3, _keys(Key.DOWN, Key.ENTER), initial_country=1, state=state)
        self.assertEqual(len(state.managed_squad), 20)
        self.assertEqual(state.managed_squad, roster)

    def test_enter_uses_runtime_player_words_instead_of_position_bytes(self):
        """[derived: T06/F011] The active squad holds player IDs from Memory.

        GOAL.DAT's twenty bytes are position patterns; duplicated values
        cannot be the engine's twenty player numbers. This fails with the
        former GOAL.DAT assignment even though it has the right length.
        """
        state = _make_state()
        roster = list(range(41, 61))
        records = list(state.countries)
        records[2] = b"".join(p.to_bytes(2, "little") for p in roster) + bytes(0xBF - 40)
        state.countries = records
        self.assertEqual(self.gd3.squad_20[2], [14] * 20)
        run_country_select(self.gd3, _keys(Key.DOWN, Key.ENTER), state=state)
        self.assertEqual(state.managed_country, 2)
        self.assertEqual(state.managed_squad, roster)


# ── Render surface tests ────────────────────────────────────────────────────

class TestRenderSurface(unittest.TestCase):
    def test_cursor_row_has_marker_and_country_name_at_index_7(self):
        """Done-when 3: cursor row starts with the marker and country 7's name.

        The expected name is derived from the input (cursor=7), not a literal.
        Deleting the cursor argument from _render leaves a different row affected.
        """
        gd128 = _make_goaldat([f"C{i}" for i in range(1, 129)])
        cursor = 7
        grid = _render(gd128, cursor=cursor, page_size=20)
        self.assertEqual(grid.cell(7, 0)[0], ord(">"))
        self.assertEqual(grid.cell(7, 1)[0], ord(" "))
        cell_char = grid.cell(7, 2)[0]
        expected_char = ord(gd128.country_names[cursor][0])
        self.assertEqual(cell_char, expected_char)

    def test_title_shows_cursor_7(self):
        """Done-when 3 / R5: title row holds cursor number derived from argument.

        R5 fix: checks cursor=7 case. The expected title is computed from
        the cursor argument, not a hardcoded literal.
        """
        cursor = 7
        gd128 = _make_goaldat([f"C{i}" for i in range(1, 129)])
        grid = _render(gd128, cursor=cursor, page_size=20)
        output = render(grid)
        lines = output.split("\n")
        # Title format: "SELECT COUNTRY  " + 3-digit cursor + "/128"
        # col 16..19 = the 3-char padded cursor number
        self.assertEqual(lines[0][16:19], f"{cursor:3d}")

    def test_title_shows_cursor_42(self):
        """R5: second cursor case (42) catches a hardcoded "7" in the title.

        Mutation: if the title used hardcoded "  7" instead of {cursor:3d},
        this test fails (42 != 7).
        """
        cursor = 42
        gd128 = _make_goaldat([f"C{i}" for i in range(1, 129)])
        grid = _render(gd128, cursor=cursor, page_size=20)
        output = render(grid)
        lines = output.split("\n")
        self.assertEqual(lines[0][16:19], f"{cursor:3d}")

    def test_cursor_row_reversed_video(self):
        """Cursor row uses fg=0, bg=7 (reversed video); other rows do not."""
        gd128 = _make_goaldat([f"C{i}" for i in range(1, 129)])
        grid = _render(gd128, cursor=5, page_size=20)
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
