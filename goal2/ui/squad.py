"""The squad select screen: 20 players, pick captain, write the eleven + captain.

[confirmed: F011 (squad row drawing at 1771:4E22→4D8A); T06 (state adapter's
managed_squad); SQ-5 (eleven = first 11 of squad in country-record order).
T12 Owns: this module and goal2/tests/test_squad_select.py.]

The screen renders 20 squad members with the cursor on one of them, lets the
user navigate with Up/Down, and on Enter writes starting_eleven and captain
to the GameState adapter. Esc aborts without touching state.

Rendering: title row 0, body rows 1..20, footer row 24.
[designed: the title format, the per-row format, and the footer text.]
"""
from __future__ import annotations

from typing import Iterable

from goal2.engine.state import GameState
from goal2.ui.grid import Grid, HEIGHT, WIDTH
from goal2.ui.input import Key, read_key


# Colour constants: VGA palette (matches DS:0x720 in the original).
# 0 = black, 7 = white, 1 = blue.
_FG_NORMAL = 7
_BG_NORMAL = 0
_FG_CURSOR = 0   # black on white
_BG_CURSOR = 7
_FG_TITLE  = 7
_BG_TITLE  = 1


def run_squad_select(
    goaldat,
    keys: Iterable[Key] | None,
    *,
    state: GameState | None = None,
    page_size: int = 20,
) -> bool:
    """Show the squad list and return True on Enter (captain picked), False on Esc.

    `goaldat` provides player_names and player_initials for the 20 squad members.
    `keys` is an optional iterable of Key values (for scripted tests); when
    None the screen reads from stdin.
    `state`, if given, is written with starting_eleven and captain when Enter
    is pressed; Esc leaves it untouched.
    `page_size` rows are shown (default 20); must be ≤ 23 so the footer on
    row 24 does not overlap. [designed]

    Returns True on Enter (captain was picked), False on Esc.
    """
    if page_size > 23:
        raise ValueError("page_size must be at most 23 to keep footer on row 24")

    cursor = 1  # row 1 = first squad member
    n_squad = len(state.managed_squad) if state is not None else 20

    key_iter = iter(keys) if keys is not None else None

    while True:
        grid = _build_grid(goaldat, state, cursor, page_size)

        if key_iter is not None:
            try:
                key = next(key_iter)
            except StopIteration:
                break
        else:
            key = read_key()

        if key == Key.UP:
            cursor = _clamp(cursor - 1, 1, n_squad)
        elif key == Key.DOWN:
            cursor = _clamp(cursor + 1, 1, n_squad)
        elif key == Key.ENTER:
            if state is not None:
                state.starting_eleven = list(state.managed_squad[:11])
                state.captain = state.managed_squad[cursor - 1]
            return True
        elif key == Key.ESC:
            return False


def _clamp(value: int, lo: int, hi: int) -> int:
    """Clamp `value` to the inclusive range [lo, hi]."""
    if value < lo:
        return lo
    if value > hi:
        return hi
    return value


def _build_grid(
    goaldat,
    state: GameState | None,
    cursor: int,
    page_size: int,
) -> Grid:
    """Render the squad select screen into a Grid and return it.

    Row 0:     title "SELECT CAPTAIN  N" (blue bg)
    Rows 1..page_size: player rows; cursor row in reversed video;
        the captain row (if captain is set) has " C" suffix
    Row 24:    footer "↑↓ CAPTAIN  ENTER PICK  ESC QUIT"
    """
    grid = Grid()

    # ── Title (row 0) ──────────────────────────────────────────────────────
    title = f"SELECT CAPTAIN  {cursor}"
    grid.draw_text(0, 0, title.ljust(WIDTH), fg=_FG_TITLE, bg=_BG_TITLE)

    # ── Squad rows (rows 1..page_size) ────────────────────────────────────
    if state is not None:
        squad = state.managed_squad
    else:
        squad = list(range(1, page_size + 1))

    for row in range(1, page_size + 1):
        idx = row - 1  # 0-indexed into squad
        if idx >= len(squad):
            break
        player_num = squad[idx]
        initial = goaldat.player_initials[player_num] if player_num < len(goaldat.player_initials) else ""
        name = goaldat.player_names[player_num] if player_num < len(goaldat.player_names) else ""
        # Format: " NN  I SURNAME" (padded to 12 chars) + captain marker at col 78
        row_text = f" {row:2d}  {initial} {name:<12}".ljust(78)
        if state is not None and state.captain == player_num:
            row_text = row_text + " C"   # marker at columns 78-79 (right edge)
        else:
            row_text = row_text + "  "   # no marker

        is_cursor = (row == cursor)
        if is_cursor:
            grid.draw_text(row, 0, row_text.ljust(WIDTH), fg=_FG_CURSOR, bg=_BG_CURSOR)
        else:
            grid.draw_text(row, 0, row_text.ljust(WIDTH), fg=_FG_NORMAL, bg=_BG_NORMAL)

    # ── Footer (row 24) ───────────────────────────────────────────────────
    footer = "↑↓ CAPTAIN  ENTER PICK  ESC QUIT"
    grid.draw_text(HEIGHT - 1, 0, footer.ljust(WIDTH), fg=_FG_TITLE, bg=_BG_TITLE)

    return grid


# ── Test helper (not part of the public API) ────────────────────────────────

def _render(
    goaldat,
    state: GameState,
    cursor: int,
    page_size: int,
) -> Grid:
    """Build the grid for the given cursor and page_size (test surface only)."""
    return _build_grid(goaldat, state, cursor, page_size)
