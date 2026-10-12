"""Tests for `goal2.ui.grid`.

[confirmed: plan.md, the owner's 2026-10-12 decision] Screens are tested by the
grid, not pixels.
"""
import unittest

from goal2.ui.grid import Grid, HEIGHT, WIDTH
from goal2.ui.plain_renderer import render


class TestGrid(unittest.TestCase):
    def test_draw_text_basic(self):
        """Done-when 2: draw_text + render round-trip.

        The expected string is computed from the input, not a literal.
        Deleting the draw_text call leaves a row of 80 spaces and fails.
        """
        grid = Grid()
        text = "HELLO"
        grid.draw_text(0, 0, text, fg=14, bg=1)
        result = render(grid)
        first_row = result.split("\n")[0]
        expected = text + " " * (WIDTH - len(text))
        self.assertEqual(first_row, expected)

    def test_draw_text_clip_right(self):
        """Done-when 3b: text past column 80 is clipped, no exception."""
        grid = Grid()
        long_text = "A" * 100  # longer than 80
        grid.draw_text(0, 0, long_text)  # must not raise
        result = render(grid)
        first_row = result.split("\n")[0]
        self.assertEqual(len(first_row), WIDTH)
        self.assertEqual(first_row, "A" * WIDTH)

    def test_draw_text_clip_bottom(self):
        """Done-when 3c: text past row 25 is clipped, no exception."""
        grid = Grid()
        # Write at row 24 (last valid row) and beyond
        grid.draw_text(24, 0, "X")
        grid.draw_text(25, 0, "Y")  # must not raise
        result = render(grid)
        lines = result.split("\n")
        # 25 lines total
        self.assertEqual(len(lines), HEIGHT)
        # Row 24 has the X, row 25 does not exist
        self.assertEqual(lines[24], "X" + " " * (WIDTH - 1))

    def test_cell_roundtrip(self):
        """Done-when 4: colour values stored on cells round-trip."""
        grid = Grid()
        grid.draw_text(0, 0, "X", fg=14, bg=1)
        cell = grid.cell(0, 0)
        self.assertEqual(cell, (ord("X"), 14, 1, 0))

    def test_cell_out_of_bounds(self):
        """Out-of-bounds cell access returns (0, 0, 0, 0)."""
        grid = Grid()
        self.assertEqual(grid.cell(-1, 0), (0, 0, 0, 0))
        self.assertEqual(grid.cell(0, -1), (0, 0, 0, 0))
        self.assertEqual(grid.cell(HEIGHT, 0), (0, 0, 0, 0))
        self.assertEqual(grid.cell(0, WIDTH), (0, 0, 0, 0))


if __name__ == "__main__":
    unittest.main()
