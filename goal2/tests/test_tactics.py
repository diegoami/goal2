"""Tests for `goal2.ui.tactics`.

[confirmed: F010 (8-element Pascal set at country[+0x2D]); T11 (input layer,
screen pattern); T12 (starting_eleven and captain are set before tactics).]
[designed: T13 screen layout, display order, element labels, footer text,
country_tactics field on GameState.]
"""
import unittest
from unittest.mock import MagicMock

from goal2.engine.state import GameState
from goal2.ui.tactics import (
    _BIT_OF_ELEMENT,
    _DISPLAY_ORDER,
    _render,
    run_tactics_select,
)
from goal2.ui.grid import Grid, WIDTH
from goal2.ui.input import Key
from goal2.ui.plain_renderer import render


# ── Constants (mirrored from tactics.py for test arithmetic) ───────────────────

_DISPLAY_ORDER = (5, 6, 7, 1, 2, 3, 4, 8)
_BIT_OF_ELEMENT = {1: 0, 2: 1, 3: 2, 4: 3, 5: 4, 6: 5, 7: 6, 8: 7}


# ── Mock GoalDat ─────────────────────────────────────────────────────────────

def _make_goaldat() -> MagicMock:
    """Return a GoalDat-like mock (not directly read by the tactics screen)."""
    gd = MagicMock()
    gd.country_names = [""] + [f"C{i}" for i in range(1, 129)]
    return gd


def _make_state() -> GameState:
    """Return a GameState with placeholder fields."""
    return GameState(
        players=[b"\x00" * 20] * 3061,
        countries=[b"\x00" * 0xBF] * 129,
        managed_country=7,
        managed_squad=list(range(1, 21)),
        rng_seed_7b62=0,
        rng_seed_8336=0,
        match_state={},
        vga=b"\x00" * 4000,
        mem=bytearray(1 << 16),
    )


def _keys(*items: Key):
    """Return an iterator that yields Key values then stops cleanly."""
    return iter(items)


# ── run_tactics_select tests ─────────────────────────────────────────────────

class TestRunTacticsSelect(unittest.TestCase):
    def setUp(self):
        self.gd = _make_goaldat()
        self.state = _make_state()

    @staticmethod
    def _expected_byte(initial: int, display_row: int) -> int:
        """Compute expected byte after toggling the element at display_row."""
        element = _DISPLAY_ORDER[display_row - 1]
        bit = _BIT_OF_ELEMENT[element]
        return initial ^ (1 << bit)

    def test_space_enter_from_row1_toggles_bit4_and_writes_0x10(self):
        """Done-when 2b: SPACE+ENTER at display row 1 toggles element 5 (bit 4)
        and writes 0x10 to state.country_tactics.

        Display row 1 = element 5 = bit 4. Starting from 0x00, toggling bit 4
        gives 0x10. The expected byte is computed from cursor + toggle arithmetic
        (not a hardcoded literal) — deleting the Space handler fails this test.
        """
        result = run_tactics_select(
            self.gd, _keys(Key.SPACE, Key.ENTER),
            state=self.state, initial_tactics=0x00,
        )
        self.assertTrue(result)
        self.assertEqual(self.state.country_tactics, self._expected_byte(0x00, 1))

    def test_down_space_enter_from_row1_toggles_bit5_and_writes_0x20(self):
        """Done-when 2b: DOWN+SPACE+ENTER from display row 1 toggles element 6
        (bit 5) and writes 0x20.

        Display row 2 = element 6 = bit 5. DOWN moves cursor there; toggling
        bit 5 from 0x00 gives 0x20. The expected byte is arithmetic, not a
        literal — deleting the DOWN handler leaves cursor at row 1 (bit 4=0x10),
        failing the assertion.
        """
        result = run_tactics_select(
            self.gd, _keys(Key.DOWN, Key.SPACE, Key.ENTER),
            state=self.state, initial_tactics=0x00,
        )
        self.assertTrue(result)
        self.assertEqual(self.state.country_tactics, self._expected_byte(0x00, 2))

    def test_downx3_space_enter_toggles_bit0_and_writes_0x01(self):
        """Done-when 2b: DOWN×3+SPACE+ENTER from row 1 toggles element 1 (bit 0).

        Display order: (5,6,7,1,2,3,4,8). DOWN×3 from row 1 lands on display
        row 4 = element 1 = bit 0. Toggling bit 0 from 0x00 gives 0x01.
        Mutation: wrong display-order arithmetic fails.
        """
        result = run_tactics_select(
            self.gd, _keys(Key.DOWN, Key.DOWN, Key.DOWN, Key.SPACE, Key.ENTER),
            state=self.state, initial_tactics=0x00,
        )
        self.assertTrue(result)
        self.assertEqual(self.state.country_tactics, self._expected_byte(0x00, 4))

    def test_esc_returns_false_and_does_not_touch_state(self):
        """Done-when 2c: Esc returns False and does not touch state.country_tactics.

        State is pre-set to -1 (sentinel); Esc must leave it unchanged.
        Mutation: making Esc return True fails the boolean assertion; making
        Esc write state fails the sentinel assertion.
        """
        state = _make_state()
        state.country_tactics = -1
        result = run_tactics_select(
            self.gd, _keys(Key.ESC),
            state=state, initial_tactics=0xAA,
        )
        self.assertFalse(result)
        self.assertEqual(state.country_tactics, -1)

    def test_up_clamped_at_row1_toggles_bit4(self):
        """Done-when hazards / R6: UP at display row 1 is a no-op (clamped);
        SPACE toggles element 5 (bit 4) → 0x10.
        """
        result = run_tactics_select(
            self.gd, _keys(Key.UP, Key.UP, Key.SPACE, Key.ENTER),
            state=self.state, initial_tactics=0x00,
        )
        self.assertTrue(result)
        self.assertEqual(self.state.country_tactics, self._expected_byte(0x00, 1))

    def test_down_clamped_at_row8_toggles_bit7(self):
        """Done-when hazards / R6: DOWN×10 from row 1 clamps at display row 8;
        SPACE toggles element 8 (bit 7) → 0x80.
        """
        result = run_tactics_select(
            self.gd, _keys(*([Key.DOWN] * 10), Key.SPACE, Key.ENTER),
            state=self.state, initial_tactics=0x00,
        )
        self.assertTrue(result)
        self.assertEqual(self.state.country_tactics, self._expected_byte(0x00, 8))

    def test_enter_after_toggle_is_one_of_256_values(self):
        """Done-when 4: state.country_tactics is in [0, 255] after Enter."""
        state = _make_state()
        state.country_tactics = -1
        # DOWN to row 2, toggle, ENTER → 0x20
        run_tactics_select(
            self.gd, _keys(Key.DOWN, Key.SPACE, Key.ENTER),
            state=state, initial_tactics=0x00,
        )
        self.assertGreaterEqual(state.country_tactics, 0)
        self.assertLessEqual(state.country_tactics, 0xFF)

    def test_no_state_means_no_write(self):
        """run_tactics_select with state=None runs without error and returns True."""
        result = run_tactics_select(
            self.gd, _keys(Key.SPACE, Key.ENTER),
            state=None, initial_tactics=0x00,
        )
        self.assertTrue(result)

    def test_state_country_tactics_read_when_no_initial_tactics_given(self):
        """When initial_tactics is None, the initial byte comes from state.country_tactics."""
        state = _make_state()
        state.country_tactics = 0x55
        # No SPACE pressed, just ENTER
        result = run_tactics_select(self.gd, _keys(Key.ENTER), state=state)
        self.assertTrue(result)
        self.assertEqual(state.country_tactics, 0x55)

    def test_page_up_toggles_at_row1(self):
        """R1: PAGE_UP at row 1 toggles (non-movement key). Clamped at row 1;
        toggling bit 4 from 0x00 → 0x10.
        """
        result = run_tactics_select(
            self.gd, _keys(Key.PAGE_UP, Key.ENTER),
            state=self.state, initial_tactics=0x00,
        )
        self.assertTrue(result)
        self.assertEqual(self.state.country_tactics, self._expected_byte(0x00, 1))

    def test_page_down_toggles_at_row2(self):
        """R1: PAGE_DOWN at row 2 toggles (non-movement key).
        DOWN moves to row 2; PAGE_DOWN is also a toggle → element 6 (bit 5).
        """
        result = run_tactics_select(
            self.gd, _keys(Key.DOWN, Key.PAGE_DOWN, Key.ENTER),
            state=self.state, initial_tactics=0x00,
        )
        self.assertTrue(result)
        self.assertEqual(self.state.country_tactics, self._expected_byte(0x00, 2))


# ── Render surface tests ─────────────────────────────────────────────────────

class TestRenderSurface(unittest.TestCase):
    def setUp(self):
        self.gd = _make_goaldat()
        self.state = _make_state()

    def test_initial_0x00_renders_all_bits_clear(self):
        """Done-when 2a: initial_tactics=0x00 → all 8 rows show [ ]."""
        grid = _render(self.gd, self.state, current_byte=0x00, cursor=1)
        lines = render(grid).split("\n")
        for row in range(1, 9):
            self.assertIn(
                "[ ]",
                lines[row],
                f"row {row} should show '[ ]' for 0x00",
            )

    def test_initial_0xFF_renders_all_bits_set(self):
        """Done-when 2a: initial_tactics=0xFF → all 8 rows show [X]."""
        grid = _render(self.gd, self.state, current_byte=0xFF, cursor=1)
        lines = render(grid).split("\n")
        for row in range(1, 9):
            self.assertIn(
                "[X]",
                lines[row],
                f"row {row} should show '[X]' for 0xFF",
            )

    def test_cursor_row_marker_from_input_byte(self):
        """Done-when 3a: the cursor row's [X]/[ ] marker reflects the input byte.

        The expected marker is derived from `current_byte` and the cursor's element
        (display row → element → bit). Replacing the bit lookup with a hardcoded
        [X] fails for byte=0x00.
        """
        # cursor=1 → element 5 → bit 4. byte=0x00 → bit 4 is clear → "[ ]"
        grid = _render(self.gd, self.state, current_byte=0x00, cursor=1)
        lines = render(grid).split("\n")
        # The cursor row (1) should be "[ ]" since bit 4 of 0x00 is 0.
        self.assertIn("[ ]", lines[1])
        # cursor=2 → element 6 → bit 5. byte=0x20 → bit 5 is set → "[X]"
        grid2 = _render(self.gd, self.state, current_byte=0x20, cursor=2)
        lines2 = render(grid2).split("\n")
        self.assertIn("[X]", lines2[2])

    def test_title_shows_byte_from_input(self):
        """Done-when 3b: title row holds `f"TACTICS  0x{byte:02X}"`.

        Two distinct byte values (0x00 and 0x55) catch a hardcoded byte in the title.
        Mutation: replacing {byte:02X} with a literal fails the second test case.
        """
        for byte in [0x00, 0x55]:
            grid = _render(self.gd, self.state, current_byte=byte, cursor=1)
            lines = render(grid).split("\n")
            self.assertEqual(
                lines[0].rstrip(),
                f"TACTICS  0x{byte:02X}",
                f"title should show 0x{byte:02X}, got {lines[0].rstrip()!r}",
            )

    def test_title_byte_0x55_is_not_hardcoded(self):
        """Done-when 3b second byte: 0x55 catches a hardcoded title byte."""
        grid = _render(self.gd, self.state, current_byte=0x55, cursor=1)
        lines = render(grid).split("\n")
        self.assertEqual(lines[0].rstrip(), "TACTICS  0x55")

    def test_footer_on_row_24(self):
        """Footer text appears on row 24 (HEIGHT-1)."""
        grid = _render(self.gd, self.state, current_byte=0x00, cursor=1)
        footer_row = render(grid).split("\n")[24]
        self.assertIn("MOVE", footer_row)
        self.assertIn("TOGGLE", footer_row)
        self.assertIn("ENTER", footer_row)
        self.assertIn("ESC", footer_row)
        self.assertIn("QUIT", footer_row)

    def test_cursor_row_reversed_video(self):
        """Cursor row uses fg=0, bg=7 (reversed video); other rows do not."""
        grid = _render(self.gd, self.state, current_byte=0x00, cursor=3)
        cursor_cell = grid.cell(3, 0)
        normal_cell = grid.cell(2, 0)
        self.assertEqual(cursor_cell[1], 0)   # fg = 0 (black)
        self.assertEqual(cursor_cell[2], 7)   # bg = 7 (white)
        self.assertEqual(normal_cell[1], 7)   # fg = 7 (white, normal)
        self.assertEqual(normal_cell[2], 0)   # bg = 0 (black, normal)


if __name__ == "__main__":
    unittest.main()
