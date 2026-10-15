"""The squad select screen: draft a starting eleven and choose its captain.

[confirmed: F011 (squad row drawing at 1771:4E22→4D8A); T06 (state adapter's
managed_squad); SQ-5 (eleven = first 11 of squad in country-record order).]
[designed: T28] The screen stages a local selection and writes it only after
Enter confirms exactly eleven players with the cursor on an included player.

The screen renders squad members with inclusion and captain-candidate markers.
Esc or exhausted scripted input discards the local draft.

Rendering: title row 0, body rows 1..20, status rows 21..23, footer row 24.
[designed: T28]
"""
from __future__ import annotations

from typing import Iterable

from goal2.game.state import GameState
from goal2.ui.grid import Grid, HEIGHT, WIDTH
from goal2.ui.input import Key, read_key
from goal2.ui.plain_renderer import display


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
    """[designed: T28] Draft a starting eleven and return on valid confirmation.

    `goaldat` provides player_names and player_initials for the 20 squad members.
    `keys` is an optional iterable of Key values (for scripted tests); when
    None the screen reads from stdin.
    `state`, if given, is written with starting_eleven and captain only after
    a valid Enter; Esc and scripted-input exhaustion leave it untouched.
    `page_size` rows are shown (default 20); must be ≤ 23 so the footer on
    row 24 does not overlap. [designed]

    Invalid Enter leaves the draft open with a visible explanation. Returns
    True after valid confirmation and False on Esc or scripted-input exhaustion.
    """
    if page_size > 23:
        raise ValueError("page_size must be at most 23 to keep footer on row 24")

    n_squad = len(state.managed_squad) if state is not None else 20
    squad = list(state.managed_squad) if state is not None else list(range(1, n_squad + 1))
    selected = _initial_selection(state, squad)
    cursor = 1  # row 1 = first squad member
    error = ""

    key_iter = iter(keys) if keys is not None else None

    while True:
        grid = _build_grid(goaldat, state, cursor, page_size, selected, error)

        if key_iter is not None:
            try:
                key = next(key_iter)
            except StopIteration:
                return False
        else:
            # [designed: T31] Display and flush the current frame before input.
            display(grid)
            key = read_key()

        if key == Key.UP:
            cursor = _clamp(cursor - 1, 1, n_squad)
            error = ""
        elif key == Key.DOWN:
            cursor = _clamp(cursor + 1, 1, n_squad)
            error = ""
        elif key == Key.SPACE:
            player = squad[cursor - 1]
            if player in selected:
                selected.remove(player)
            else:
                selected.add(player)
            error = ""
        elif key == Key.ENTER:
            if len(selected) != 11:
                error = f"ERROR: SELECT EXACTLY 11 PLAYERS ({len(selected)} selected)"
                continue
            captain = squad[cursor - 1]
            if captain not in selected:
                error = "ERROR: CAPTAIN MUST BE INCLUDED IN THE ELEVEN"
                continue
            if state is not None:
                state.starting_eleven = [player for player in squad if player in selected]
                state.captain = captain
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
    selected: set[int] | None = None,
    error: str = "",
) -> Grid:
    """[designed: T28] Render the local selection draft and return its Grid.

    Row 0 shows the selected count; rows 1..page_size show inclusion and the
    cursor's captain candidacy; rows 21..23 show captain, validation and help.
    Row 24 contains the navigation and confirmation controls.
    """
    grid = Grid()
    squad = list(state.managed_squad) if state is not None else list(range(1, page_size + 1))
    selected = _initial_selection(state, squad) if selected is None else selected

    title = f"SELECT ELEVEN  {len(selected)}/11"
    grid.draw_text(0, 0, title.ljust(WIDTH), fg=_FG_TITLE, bg=_BG_TITLE)

    for row in range(1, page_size + 1):
        idx = row - 1  # 0-indexed into squad
        if idx >= len(squad):
            break
        player_num = squad[idx]
        initial = goaldat.player_initials[player_num] if player_num < len(goaldat.player_initials) else ""
        name = goaldat.player_names[player_num] if player_num < len(goaldat.player_names) else ""
        # [designed: T27] Reserve columns 0-1 for navigation; keep the
        # captain marker fixed at columns 78-79.
        included = player_num in selected
        row_text = f"> " if row == cursor else "  "
        row_text += f"{'[x]' if included else '[ ]'} {row:2d}  {initial} {name:<12}"[:76].ljust(76)
        row_text += " C" if state is not None and state.captain == player_num else "  "

        is_cursor = (row == cursor)
        if is_cursor:
            grid.draw_text(row, 0, row_text.ljust(WIDTH), fg=_FG_CURSOR, bg=_BG_CURSOR)
        else:
            grid.draw_text(row, 0, row_text.ljust(WIDTH), fg=_FG_NORMAL, bg=_BG_NORMAL)

    cursor_player = squad[cursor - 1] if squad and cursor <= len(squad) else None
    cursor_name = ""
    if cursor_player is not None and cursor_player < len(goaldat.player_names):
        cursor_name = goaldat.player_names[cursor_player]
    captain_state = "included" if cursor_player in selected else "excluded"
    grid.draw_text(21, 0, f"CAPTAIN: {cursor_name} ({captain_state})".ljust(WIDTH))
    grid.draw_text(22, 0, error[:WIDTH].ljust(WIDTH), fg=_FG_TITLE if error else _FG_NORMAL,
                   bg=_BG_TITLE if error else _BG_NORMAL)
    grid.draw_text(23, 0, "UP/DOWN MOVE  SPACE toggles highlighted player.".ljust(WIDTH))
    footer = "UP/DOWN MOVE  SPACE TOGGLE  ENTER CONFIRM  ESC CANCEL"
    grid.draw_text(HEIGHT - 1, 0, footer.ljust(WIDTH), fg=_FG_TITLE, bg=_BG_TITLE)

    return grid


# ── Test helper (not part of the public API) ────────────────────────────────

def _render(
    goaldat,
    state: GameState,
    cursor: int,
    page_size: int,
    selected: set[int] | None = None,
    error: str = "",
) -> Grid:
    """Build the grid for the given cursor and page_size (test surface only)."""
    return _build_grid(goaldat, state, cursor, page_size, selected, error)


def _initial_selection(state: GameState | None, squad: list[int]) -> set[int]:
    """[designed: T28] Use a valid existing eleven, else the first eleven."""
    existing = list(state.starting_eleven) if state is not None else []
    if len(existing) == 11 and len(set(existing)) == 11 and set(existing).issubset(squad):
        return set(existing)
    return set(squad[:11])
