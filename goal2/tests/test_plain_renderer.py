"""Tests for `goal2.ui.plain_renderer`.

[designed: the renderer is for tests and logs; colour is omitted.]
[confirmed: plan.md] A screen is tested by the grid, not pixels.
"""
import unittest

from goal2.ui.grid import Grid, HEIGHT, WIDTH
from goal2.ui.plain_renderer import render


class TestPlainRenderer(unittest.TestCase):
    def test_fresh_grid(self):
        """Done-when 3a: a fresh grid renders as 25 rows of 80 spaces each."""
        grid = Grid()
        result = render(grid)
        # [R1 fix]: trailing newline means split gives 26 elements (last is "")
        lines = result.split("\n")
        self.assertEqual(len(lines), 26)  # 25 rows + trailing empty
        rows = lines[:25]
        for i, line in enumerate(rows):
            with self.subTest(row=i):
                self.assertEqual(len(line), WIDTH)
                self.assertEqual(line, " " * WIDTH)
        # The expected shape: 25 rows of 80 spaces joined by \n, plus trailing \n
        blank_row = " " * WIDTH
        expected = ("\n".join([blank_row] * HEIGHT)) + "\n"
        self.assertEqual(result, expected)

    def test_clip_right_edge(self):
        """Done-when 3b: text written past column 80 is clipped.

        [R4 fix]: text starts at column 75, so 5 chars land at 75..79 and
        the remaining 15 are dropped. Row 1 must remain all spaces — if the
        clipping guard is removed, the dropped chars would be processed
        (and clipped at bottom), leaving a different grid state.
        """
        grid = Grid()
        # Start at col 75, write 20 chars: only 5 fit (cols 75-79)
        grid.draw_text(0, 75, "X" * 20)
        result = render(grid)
        lines = result.split("\n")[:25]
        first_row = lines[0]
        second_row = lines[1]
        # First 75 cols are spaces, cols 75-79 are X
        self.assertEqual(first_row[:75], " " * 75)
        self.assertEqual(first_row[75:], "X" * 5)
        # Row 1 must be unchanged (all spaces) — verifies no wrapping
        self.assertEqual(second_row, " " * WIDTH)

    def test_clip_bottom_edge(self):
        """Done-when 3c: text written past row 25 is clipped.

        Write 30 Y's starting at row 22, col 0. No wrapping: all 30 stay
        in row 22, cols 0-29. Rows 23, 24 remain spaces.
        """
        grid = Grid()
        grid.draw_text(22, 0, "Y" * 30)
        result = render(grid)
        lines = result.split("\n")[:25]
        self.assertEqual(len(lines), 25)
        # Row 22: 30 Y's then 50 spaces
        self.assertEqual(lines[22], "Y" * 30 + " " * 50)
        # Rows 23, 24 unchanged
        self.assertEqual(lines[23], " " * WIDTH)
        self.assertEqual(lines[24], " " * WIDTH)
        # No row 25
        self.assertEqual(len(result.split("\n")), 26)


if __name__ == "__main__":
    unittest.main()
