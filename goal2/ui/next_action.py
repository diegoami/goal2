"""[designed: T32] Ask whether to play another assumed friendly."""
from __future__ import annotations

from typing import Iterable

from goal2.ui.grid import Grid, HEIGHT, WIDTH
from goal2.ui.input import Key, read_key
from goal2.ui.plain_renderer import display


def run_next_action(keys: Iterable[Key] | None = None) -> bool:
    """Return True for another friendly; Esc, Quit, or exhaustion returns False.

    The cursor starts on Quit, so Enter and exhausted scripted input cannot
    start a match without an explicit movement to Play another friendly.
    """
    key_iter = iter(keys) if keys is not None else None
    cursor = 1
    while True:
        grid = _build_grid(cursor)
        if key_iter is None:
            display(grid)
            key = read_key()
        else:
            try:
                key = next(key_iter)
            except StopIteration:
                return False
        if key == Key.UP or key == Key.DOWN:
            cursor = 1 - cursor
        elif key == Key.ENTER:
            return cursor == 0
        elif key == Key.ESC:
            return False


def _build_grid(cursor: int) -> Grid:
    grid = Grid()
    grid.draw_text(0, 0, "FRIENDLY COMPLETE".ljust(WIDTH), fg=7, bg=1)
    grid.draw_text(2, 0, "What would you like to do?".ljust(WIDTH))
    options = ("Play another friendly", "Quit")
    for index, label in enumerate(options):
        row = 5 + index * 2
        marker = "> " if index == cursor else "  "
        grid.draw_text(row, 0, f"{marker}{label}".ljust(WIDTH),
                       fg=0 if index == cursor else 7,
                       bg=7 if index == cursor else 0)
    grid.draw_text(HEIGHT - 1, 0, "UP/DOWN MOVE  ENTER SELECT  ESC QUIT".ljust(WIDTH),
                   fg=7, bg=1)
    return grid
