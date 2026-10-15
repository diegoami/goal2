"""[designed: T32, T33] Offer another friendly, save and quit, or quit."""
from __future__ import annotations

from typing import Callable, Iterable

from goal2.ui.grid import Grid, HEIGHT, WIDTH
from goal2.ui.input import Key, read_key
from goal2.ui.plain_renderer import display


def run_next_action(
    keys: Iterable[Key] | None = None,
    *,
    on_save: Callable[[], None] | None = None,
) -> bool:
    """Return True for another friendly; save and quit or quit returns False.

    The cursor starts on Quit, so Enter and exhausted scripted input cannot
    start another match without explicit movement. A failed save remains in
    this menu and exposes its error for a retry. [designed: T33]
    """
    key_iter = iter(keys) if keys is not None else None
    cursor = 2
    error: str | None = None
    while True:
        grid = _build_grid(cursor, error)
        if key_iter is None:
            display(grid)
            key = read_key()
        else:
            try:
                key = next(key_iter)
            except StopIteration:
                return False
        if key == Key.UP or key == Key.DOWN:
            cursor = (cursor + (-1 if key == Key.UP else 1)) % 3
        elif key == Key.ENTER:
            if cursor == 0:
                return True
            if cursor == 1:
                if on_save is None:
                    error = "Save is not available."
                    continue
                try:
                    on_save()
                except Exception as exc:
                    error = f"Save failed: {exc}"
                    continue
            return False
        elif key == Key.ESC:
            return False


def _build_grid(cursor: int, error: str | None = None) -> Grid:
    grid = Grid()
    grid.draw_text(0, 0, "FRIENDLY COMPLETE".ljust(WIDTH), fg=7, bg=1)
    grid.draw_text(2, 0, "What would you like to do?".ljust(WIDTH))
    options = ("Play another friendly", "Save and quit", "Quit")
    for index, label in enumerate(options):
        row = 4 + index * 2
        marker = "> " if index == cursor else "  "
        grid.draw_text(row, 0, f"{marker}{label}".ljust(WIDTH),
                       fg=0 if index == cursor else 7,
                       bg=7 if index == cursor else 0)
    if error:
        grid.draw_text(11, 0, error[:WIDTH].ljust(WIDTH), fg=15, bg=4)
    grid.draw_text(HEIGHT - 1, 0, "UP/DOWN MOVE  ENTER SELECT  ESC QUIT".ljust(WIDTH),
                   fg=7, bg=1)
    return grid
