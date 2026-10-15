"""[designed: T29] Confirm the selected team and opponent before kickoff.

The matchup shown here comes from the same template-to-engine-side resolver
used by the full-friendly runner. The preview never runs match simulation.
"""
from __future__ import annotations

from typing import Iterable

from goal2.engine.quick_engine import ExtraTimeNotModelled, FoulPathNotModelled
from goal2.game.quick_match import resolve_full_matchup
from goal2.game.state import GameState
from goal2.engine.savestate import Savestate
from goal2.ui.grid import Grid, HEIGHT, WIDTH
from goal2.ui.input import Key, read_key
from goal2.ui.plain_renderer import display


_FG_NORMAL = 7
_BG_NORMAL = 0
_FG_TITLE = 7
_BG_TITLE = 1


def run_match_preview(goaldat, savestate_path_or_bytes, keys: Iterable[Key] | None,
                      *, state: GameState) -> bool:
    """Show the resolved matchup and return True only after Play is confirmed.

    Scripted input is silent, matching the other screen flows. Unsupported
    setup is displayed as a refusal and cannot be confirmed with Enter.
    """
    key_iter = iter(keys) if keys is not None else None
    try:
        template = Savestate(savestate_path_or_bytes)
        teams, managed_side, opponent = resolve_full_matchup(template, state)
        _validate_lineup(state)
        refusal = None
    except (ValueError, FoulPathNotModelled, ExtraTimeNotModelled) as exc:
        teams, managed_side, opponent = None, None, None
        refusal = str(exc)

    while True:
        grid = _build_grid(goaldat, state, teams, managed_side, opponent, refusal)
        if key_iter is not None:
            try:
                key = next(key_iter)
            except StopIteration:
                return False
        else:
            display(grid)
            key = read_key()

        if key == Key.ESC:
            return False
        if key == Key.ENTER and refusal is None:
            return True


def _validate_lineup(state: GameState) -> None:
    """[designed: T29] Refuse the same invalid lineup the runner cannot use."""
    selected_squad = list(state.managed_squad)
    eleven = list(state.starting_eleven or selected_squad[:11])
    if len(selected_squad) != 20 or len(eleven) != 11 or len(set(eleven)) != 11:
        raise ValueError("friendly needs a 20-player squad and distinct eleven")
    if not set(eleven).issubset(selected_squad):
        raise ValueError("starting eleven must be in the managed squad")
    if state.captain not in eleven:
        raise ValueError("captain must be in the starting eleven")


def _build_grid(goaldat, state: GameState, teams, managed_side, opponent,
                refusal: str | None) -> Grid:
    grid = Grid()
    grid.draw_text(0, 0, "MATCH PREVIEW".ljust(WIDTH), fg=_FG_TITLE, bg=_BG_TITLE)
    if refusal is not None:
        grid.draw_text(2, 0, f"REFUSED: {refusal}"[:WIDTH].ljust(WIDTH))
        grid.draw_text(4, 0, "MATCH NOT STARTED".ljust(WIDTH))
        footer = "MATCH UNAVAILABLE  ESC QUIT"
    else:
        country_name = lambda country: _country_name(goaldat, country)
        grid.draw_text(2, 0, f"YOUR TEAM: {country_name(state.managed_country)}".ljust(WIDTH))
        grid.draw_text(3, 0, f"OPPONENT: {country_name(opponent)}".ljust(WIDTH))
        grid.draw_text(5, 0, "STARTING ELEVEN".ljust(WIDTH))
        eleven = list(state.starting_eleven or state.managed_squad[:11])
        for index, player in enumerate(eleven):
            captain = " (C)" if player == state.captain else ""
            name = _player_name(goaldat, player)
            grid.draw_text(6 + index, 0, f"{index + 1:2d}. {name}{captain}".ljust(WIDTH))
        footer = "ENTER PLAY MATCH  ESC QUIT"
    grid.draw_text(HEIGHT - 1, 0, footer.ljust(WIDTH), fg=_FG_TITLE, bg=_BG_TITLE)
    return grid


def _country_name(goaldat, country: int) -> str:
    names = getattr(goaldat, "country_names", ())
    if 0 <= country < len(names) and names[country]:
        return names[country]
    return f"Country {country}"


def _player_name(goaldat, player: int) -> str:
    names = getattr(goaldat, "player_names", ())
    if 0 <= player < len(names) and names[player]:
        return names[player]
    return f"Player {player}"


def _render(goaldat, state: GameState, teams, managed_side, opponent,
            refusal: str | None = None) -> Grid:
    """[designed: T29] Render the preview for test inspection."""
    return _build_grid(goaldat, state, teams, managed_side, opponent, refusal)
