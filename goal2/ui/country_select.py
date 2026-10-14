"""The country select screen: 128 countries, cursor, pagination.

[designed] The screen renders a paginated country list and writes the
chosen country to the GameState adapter (managed_country + managed_squad).
It builds on the T10 screen framework: a Grid plus the plain renderer for
tests and interactive stdout frames.

The screen takes an optional `keys` iterable for scripted tests; when None it
reads from stdin in a loop. [designed: scripted keys for tests, stdin for
real use]
"""
from __future__ import annotations

from typing import Iterable

from goal2.data import GoalDat
from goal2.game.state import GameState
from goal2.ui.grid import Grid, HEIGHT, WIDTH
from goal2.ui.input import Key, read_key
from goal2.ui.plain_renderer import render


# Colour constants: VGA palette (matches DS:0x720 in the original).
# 0 = black, 7 = white, 1 = blue.
_FG_NORMAL = 7
_BG_NORMAL = 0
_FG_CURSOR = 0   # black on white
_BG_CURSOR = 7
_FG_TITLE  = 7
_BG_TITLE  = 1


def run_country_select(
    goaldat: GoalDat,
    keys: Iterable[Key] | None,
    *,
    initial_country: int = 1,
    page_size: int = 20,
    state: GameState | None = None,
) -> int | None:
    """Show the country list and return the chosen country number (1..128).

    `goaldat` provides the 128 country names and the squad-20 array.
    `keys` is an optional iterable of Key values (for scripted tests); when
    None the screen reads from stdin.
    `initial_country` is the starting cursor position (1..128); out-of-range
    values are clamped to [1, 128].
    `page_size` rows are shown per page (default 20); must be ≤ 23 so the
    footer on row 24 does not overlap. [designed]
    `state`, if given, is written with `managed_country` and `managed_squad`
    when Enter is pressed; Esc leaves it untouched.

    Returns the chosen country number (1..128) on Enter, or None on Esc.
    [confirmed: F011 writes the choice to the country's record; the rebuild
    writes to the adapter's managed_country / managed_squad fields.]

    Pagination: 128 countries ÷ page_size rows = ceil(128/page_size) pages.
    The last page holds 128 % page_size countries (or page_size if evenly
    divisible). Page p (0-indexed) shows countries
    p*page_size+1 .. min((p+1)*page_size, 128).
    """
    if page_size > 23:
        raise ValueError("page_size must be at most 23 to keep footer on row 24")

    cursor = _clamp(initial_country, 1, 128)
    total = 128

    key_iter = iter(keys) if keys is not None else None

    while True:
        grid = _build_grid(goaldat, cursor, page_size)

        if key_iter is not None:
            try:
                key = next(key_iter)
            except StopIteration:
                # Generator exhausted — bail out (tests never reach here with
                # a correctly-shaped generator that yields Enter)
                break
        else:
            # [designed: T23] Display and flush the current frame before input.
            print(render(grid), end="", flush=True)
            key = read_key()

        if key == Key.UP:
            cursor = _clamp(cursor - 1, 1, 128)
        elif key == Key.DOWN:
            cursor = _clamp(cursor + 1, 1, 128)
        elif key == Key.PAGE_UP:
            cursor = _clamp(cursor - page_size, 1, 128)
        elif key == Key.PAGE_DOWN:
            cursor = _clamp(cursor + page_size, 1, 128)
        elif key == Key.ENTER:
            if state is not None:
                state.managed_country = cursor
                # [derived: T06/F011] The runtime country record begins with
                # twenty little-endian player numbers. GOAL.DAT's squad_20
                # bytes encode a position pattern, so the engine must use
                # the adapted country record for its active player IDs.
                record = state.countries[cursor]
                state.managed_squad = [
                    int.from_bytes(record[2 * i:2 * i + 2], "little")
                    for i in range(20)
                ]
            return cursor
        elif key == Key.ESC:
            return None


def _clamp(value: int, lo: int, hi: int) -> int:
    """Clamp `value` to the inclusive range [lo, hi]."""
    if value < lo:
        return lo
    if value > hi:
        return hi
    return value


def _build_grid(
    goaldat: GoalDat,
    cursor: int,
    page_size: int,
) -> Grid:
    """Render the country select screen into a Grid and return it.

    Row 0:     title "SELECT COUNTRY  NNN/128" (blue bg)
    Rows 1..page_size: country names; cursor row in reversed video
    Row 24:    footer "↑↓ SELECT  PgUp/PgDn PAGE  ENTER PICK  ESC QUIT"
    """
    grid = Grid()
    total = 128

    # ── Title (row 0) ──────────────────────────────────────────────────────
    # "SELECT COUNTRY" + 2 spaces + number padded to 3 chars + "/128"
    title = f"SELECT COUNTRY  {cursor:3d}/{total}"
    grid.draw_text(0, 0, title.ljust(WIDTH), fg=_FG_TITLE, bg=_BG_TITLE)

    # ── Country list (rows 1..page_size) ──────────────────────────────────
    page = (cursor - 1) // page_size
    start = page * page_size + 1          # first country on this page (1-indexed)
    end   = min(start + page_size - 1, 128, len(goaldat.country_names) - 1)

    row = 1
    for country_num in range(start, end + 1):
        name = goaldat.country_names[country_num]
        is_cursor = (country_num == cursor)
        if is_cursor:
            grid.draw_text(row, 0, name.ljust(WIDTH), fg=_FG_CURSOR, bg=_BG_CURSOR)
        else:
            grid.draw_text(row, 0, name.ljust(WIDTH), fg=_FG_NORMAL, bg=_BG_NORMAL)
        row += 1

    # ── Footer (row 24) ───────────────────────────────────────────────────
    footer = "↑↓ SELECT  PgUp/PgDn PAGE  ENTER PICK  ESC QUIT"
    grid.draw_text(HEIGHT - 1, 0, footer.ljust(WIDTH), fg=_FG_TITLE, bg=_BG_TITLE)

    return grid


# ── Test helper (not part of the public API) ────────────────────────────────

def _render(
    goaldat: GoalDat,
    cursor: int,
    page_size: int,
) -> Grid:
    """Build the grid for the given cursor and page_size (test surface only)."""
    return _build_grid(goaldat, cursor, page_size)
