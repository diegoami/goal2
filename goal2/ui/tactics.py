"""The tactics screen: 8 team-tactics bits, toggleable, write to state.

[designed] The screen displays 8 tactics elements (from F010's `country[+0x2D]`
Pascal set), lets the user navigate with Up/Down, toggle the bit at the cursor
with Space, and on Enter writes the resulting byte to state.country_tactics.
Esc aborts without touching state.

Display order (per F010's `DS:6BC0`): elements 5, 6, 7, 1, 2, 3, 4, 8.
Bit position = element - 1. Cursor starts at display row 1 (= element 5, bit 4).

Rendering: title row 0, body rows 1..8, footer row 24.
[designed: the title format, the per-row format, and the footer text.]
"""
from __future__ import annotations

from typing import Iterable

from goal2.game.state import GameState
from goal2.ui.grid import Grid, HEIGHT, WIDTH
from goal2.ui.input import Key, read_key
from goal2.ui.plain_renderer import display


# [derived: standard VGA text-mode palette; F010 cites DS:0x720]
# 0 = black, 7 = white, 1 = blue.
_FG_NORMAL = 7
_BG_NORMAL = 0
_FG_CURSOR = 0   # black on white
_BG_CURSOR = 7
_FG_TITLE  = 7
_BG_TITLE  = 1

# [confirmed: F010's DS:6BC0 = 5, 6, 7, 1, 2, 3, 4, 8] Display order:
# element 5 first, then 6, 7, 1, 2, 3, 4, 8.
_DISPLAY_ORDER = (5, 6, 7, 1, 2, 3, 4, 8)

# [confirmed: F010 "element k at bit k − 1"] Bit position = element - 1.
_BIT_OF_ELEMENT = {1: 0, 2: 1, 3: 2, 4: 3, 5: 4, 6: 5, 7: 6, 8: 7}

# [confirmed: F010's element labels for 1-4] [designed: F010 says
# "the screen labels of 5..7 are not read"; element 8 label not read either]
_ELEMENT_LABELS: dict[int, tuple[str, str]] = {
    # Element 5: [designed; F010 notes labels of 5..7 are not read]
    5: ("half pitch", "full pitch"),
    # Element 6: [designed; F010 notes labels of 5..7 are not read]
    6: ("short kicks", "long kicks"),
    # Element 7: [designed; F010 notes labels of 5..7 are not read]
    7: ("stay back", "push forward"),
    # Element 1: [confirmed: F010]
    1: ("stay back", "push forward"),
    # Element 2: [confirmed: F010]
    2: ("keep ball", "quick pass"),
    # Element 3: [confirmed: F010]
    3: ("short passes", "long passes"),
    # Element 4: [confirmed: F010]
    4: ("avoid injury", "go in hard"),
    # Element 8: [designed; F010 notes element 8 label not read]
    8: ("zone", "man to man"),
}


def run_tactics_select(
    goaldat,
    keys: Iterable[Key] | None,
    *,
    state: GameState | None = None,
    initial_tactics: int | None = None,
) -> bool:
    """Show the 8 tactics rows and return True on Enter, False on Esc.

    `goaldat` is required but not read by this screen (the labels are
    hardcoded per F010's evidence).
    `keys` is an optional iterable of Key values (for scripted tests); when
    None the screen reads from stdin.
    `state`, if given, is written with country_tactics when Enter is pressed;
    Esc leaves it untouched.
    `initial_tactics` sets the starting byte; if not given, the byte is read
    from state.country_tactics (if state is given), else 0.

    Returns True on Enter (tactics confirmed), False on Esc.
    """
    # Resolve the initial byte.
    if initial_tactics is not None:
        current_byte = initial_tactics & 0xFF
    elif state is not None:
        current_byte = state.country_tactics & 0xFF
    else:
        current_byte = 0

    cursor = 1  # display row 1 = element 5

    key_iter = iter(keys) if keys is not None else None

    while True:
        grid = _build_grid(current_byte, cursor)

        if key_iter is not None:
            try:
                key = next(key_iter)
            except StopIteration:
                break
        else:
            # [designed: T31] Display and flush the current frame before input.
            display(grid)
            key = read_key()

        if key == Key.UP:
            cursor = _clamp(cursor - 1, 1, 8)
        elif key == Key.DOWN:
            cursor = _clamp(cursor + 1, 1, 8)
        elif key == Key.ENTER:
            if state is not None:
                state.country_tactics = current_byte & 0xFF
            return True
        elif key == Key.ESC:
            return False
        else:
            # Any non-movement/non-confirmation key toggles the bit at the
            # cursor's element. This includes SPACE, PAGE_UP, PAGE_DOWN, etc.
            element = _DISPLAY_ORDER[cursor - 1]
            bit = _BIT_OF_ELEMENT[element]
            current_byte ^= (1 << bit)


def _clamp(value: int, lo: int, hi: int) -> int:
    """Clamp `value` to the inclusive range [lo, hi]."""
    if value < lo:
        return lo
    if value > hi:
        return hi
    return value


def _build_grid(current_byte: int, cursor: int) -> Grid:
    """Render the tactics screen into a Grid and return it.

    Row 0:     title "TACTICS  0xNN" where NN is current_byte in hex (blue bg)
    Rows 1..8: one element per row, prefixed with "> " on the cursor row
        and two spaces elsewhere; cursor row in reversed video
    Row 24:    footer "UP/DOWN MOVE  SPACE TOGGLE  ENTER CONFIRM  ESC QUIT"
    """
    grid = Grid()

    # ── Title (row 0) ──────────────────────────────────────────────────────
    title = f"TACTICS  0x{current_byte:02X}"
    grid.draw_text(0, 0, title.ljust(WIDTH), fg=_FG_TITLE, bg=_BG_TITLE)

    # ── Element rows (rows 1..8) ────────────────────────────────────────────
    for display_row in range(1, 9):
        element = _DISPLAY_ORDER[display_row - 1]
        bit = _BIT_OF_ELEMENT[element]
        is_set = bool(current_byte & (1 << bit))
        clear_label, set_label = _ELEMENT_LABELS[element]
        marker = "X" if is_set else " "
        # [designed: T27] Keep the navigation cursor distinct from [X]/[ ]
        # tactic state by reserving columns 0-1 for it.
        row_text = ("> " if display_row == cursor else "  ") + f"[{marker}]  {clear_label} / {set_label}"

        if display_row == cursor:
            grid.draw_text(display_row, 0, row_text.ljust(WIDTH), fg=_FG_CURSOR, bg=_BG_CURSOR)
        else:
            grid.draw_text(display_row, 0, row_text.ljust(WIDTH), fg=_FG_NORMAL, bg=_BG_NORMAL)

    # ── Footer (row 24) ───────────────────────────────────────────────────
    footer = "UP/DOWN MOVE  SPACE TOGGLE  ENTER CONFIRM  ESC QUIT"
    grid.draw_text(HEIGHT - 1, 0, footer.ljust(WIDTH), fg=_FG_TITLE, bg=_BG_TITLE)

    return grid


# ── Test helper (not part of the public API) ────────────────────────────────

def _render(
    goaldat,
    state: GameState,
    current_byte: int,
    cursor: int,
) -> Grid:
    """Build the grid for the given byte and cursor (test surface only)."""
    return _build_grid(current_byte, cursor)
