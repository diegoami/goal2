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
        # Compute expected from constants, not a literal
        blank_row = " " * WIDTH
        expected = "\n".join([blank_row] * HEIGHT)
        self.assertEqual(result, expected)
        # Verify shape
        lines = result.split("\n")
        self.assertEqual(len(lines), HEIGHT)
        for i, line in enumerate(lines):
            with self.subTest(row=i):
                self.assertEqual(len(line), WIDTH)

    def test_clip_right_edge(self):
        """Done-when 3b: text written past column 80 is clipped."""
        grid = Grid()
        text = "TEXT"
        grid.draw_text(0, 0, text)
        result = render(grid)
        first_row = result.split("\n")[0]
        self.assertTrue(first_row.startswith(text))
        self.assertEqual(len(first_row), WIDTH)

    def test_clip_bottom_edge(self):
        """Done-when 3c: text written past row 25 is clipped."""
        grid = Grid()
        grid.draw_text(24, 0, "LAST")
        grid.draw_text(25, 0, "PAST")  # must not raise
        result = render(grid)
        lines = result.split("\n")
        self.assertEqual(len(lines), HEIGHT)
        self.assertEqual(lines[24], "LAST" + " " * (WIDTH - 4))
        # No line 25
        with self.assertRaises(IndexError):
            _ = lines[25]


if __name__ == "__main__":
    unittest.main()
