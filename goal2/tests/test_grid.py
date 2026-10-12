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
        grid.draw_text(0, 0, text, fg=7, bg=1)
        result = render(grid)
        # [R2-round-3 fix]: assert the trailing newline, not just the
        # first row. Without the trailing "\n", a renderer that returned
        # "row0\nrow1\n...row24" (no trailing) would also split into the
        # same first row and miss the requirement.
        self.assertTrue(result.endswith("\n"))
        self.assertEqual(len(result), 25 * (WIDTH + 1))  # 25 × 81 = 2025
        first_row = result.split("\n")[0]
        expected = text + " " * (WIDTH - len(text))
        self.assertEqual(first_row, expected)

    def test_draw_text_clip_right(self):
        """Done-when 3b: text past column 80 is clipped, no exception.

        [R4 fix]: starts near right edge so dropped chars would wrap to row 1.
        """
        grid = Grid()
        # Start at col 75, write 20 chars: only 5 fit (cols 75-79)
        grid.draw_text(0, 75, "A" * 20)
        result = render(grid)
        lines = result.split("\n")[:25]
        first_row = lines[0]
        second_row = lines[1]
        self.assertEqual(len(first_row), WIDTH)
        self.assertEqual(first_row[75:], "A" * 5)
        # Row 1 must be unchanged
        self.assertEqual(second_row, " " * WIDTH)

    def test_draw_text_clip_bottom(self):
        """Done-when 3c: text past row 25 is clipped, no exception."""
        grid = Grid()
        grid.draw_text(24, 0, "X")
        grid.draw_text(25, 0, "Y")  # must not raise
        result = render(grid)
        lines = result.split("\n")[:25]
        self.assertEqual(len(lines), 25)
        self.assertEqual(lines[24], "X" + " " * (WIDTH - 1))

    def test_cell_roundtrip(self):
        """Done-when 4: colour values stored on cells round-trip."""
        grid = Grid()
        grid.draw_text(0, 0, "X", fg=7, bg=1)
        cell = grid.cell(0, 0)
        self.assertEqual(cell, (ord("X"), 7, 1, 0))

    def test_cell_out_of_bounds(self):
        """Out-of-bounds cell access returns (0, 0, 0, 0)."""
        grid = Grid()
        self.assertEqual(grid.cell(-1, 0), (0, 0, 0, 0))
        self.assertEqual(grid.cell(0, -1), (0, 0, 0, 0))
        self.assertEqual(grid.cell(HEIGHT, 0), (0, 0, 0, 0))
        self.assertEqual(grid.cell(0, WIDTH), (0, 0, 0, 0))

    def test_draw_text_non_cp437(self):
        """[R3 fix]: characters with ord > 255 are skipped silently."""
        grid = Grid()
        # "Ā" is codepoint 256, outside CP437 range
        grid.draw_text(0, 0, "AĀB")  # "A" at col 0, "Ā" skipped, "B" at col 1
        cell_a = grid.cell(0, 0)
        cell_b = grid.cell(0, 1)
        cell_256 = grid.cell(0, 2)
        self.assertEqual(cell_a, (ord("A"), 7, 0, 0))
        self.assertEqual(cell_b, (ord("B"), 7, 0, 0))
        self.assertEqual(cell_256, (0, 0, 0, 0))  # untouched


if __name__ == "__main__":
    unittest.main()
