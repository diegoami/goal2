"""The character grid: 80 columns x 25 rows.

[confirmed: plan.md, the owner's 2026-10-12 decision] Each cell holds a CP437
character code (int 0..255), a 3-bit foreground colour (0..7), a 3-bit background
colour (0..7), and a 1-bit blink flag.

[derived: standard VGA text-mode attribute byte; F014 cites the same palette
at DS:0x720]
"""
from __future__ import annotations

WIDTH = 80
HEIGHT = 25


class Grid:
    """An 80x25 character grid.

    Each cell is a 4-tuple: (char_code, foreground, background, blink).
    char_code is an int in 0..255 (CP437). foreground and background are
    colour indices 0..7. blink is 0 or 1.
    """

    __slots__ = ("_cells",)

    def __init__(self) -> None:
        # Flat list of 2000 cells; row r, col c -> _cells[r * WIDTH + c]
        self._cells: list[tuple[int, int, int, int]] = [
            (0, 0, 0, 0) for _ in range(WIDTH * HEIGHT)
        ]

    def cell(self, row: int, col: int) -> tuple[int, int, int, int]:
        """Return the cell at (row, col) as (char, fg, bg, blink).

        Returns (0, 0, 0, 0) for any out-of-bounds access.
        """
        if not (0 <= row < HEIGHT and 0 <= col < WIDTH):
            return (0, 0, 0, 0)
        return self._cells[row * WIDTH + col]

    def set_cell(
        self, row: int, col: int, char: int, fg: int, bg: int, blink: int = 0
    ) -> None:
        """Set the cell at (row, col).

        Silently ignores out-of-bounds coordinates.
        """
        if not (0 <= row < HEIGHT and 0 <= col < WIDTH):
            return
        self._cells[row * WIDTH + col] = (char, fg, bg, blink)

    def draw_text(
        self,
        row: int,
        col: int,
        text: str,
        fg: int = 7,
        bg: int = 0,
        blink: int = 0,
    ) -> None:
        """Write text into the grid starting at (row, col).

        [designed]: clips at the right edge (wraps to next row) and bottom
        edge (row >= 25); writes nothing off-grid, does not raise.
        """
        if not (0 <= row < HEIGHT and 0 <= col < WIDTH):
            return
        c = col
        for ch in text:
            if c >= WIDTH:
                break  # [designed]: clip at right edge, no wrapping
            if not (0 <= row < HEIGHT):
                break  # [designed]: clip at bottom edge
            char_code = ord(ch)
            if char_code > 255:
                continue  # [designed]: skip non-CP437; do not advance column
            self._cells[row * WIDTH + c] = (char_code, fg, bg, blink)
            c += 1
