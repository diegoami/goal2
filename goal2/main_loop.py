"""The main loop driver: country → squad → tactics → preview → result. [designed: T33]

[derived: T15's `pick_computer_eleven` and `get_computer_tactics` are not on
T16's path in v1; GA-4 keys flow through the driver to each screen.]
[confirmed: A-WATCH-1 — the result screen is a quick-engine stand-in;
A-MATCH-2/3 — refusals are surfaced by run_result itself.]
[designed: T26, A-MATCH-1 — interactive result runs both halves on one instance.]
"""
from __future__ import annotations

from typing import Callable, Iterable

from goal2.data.goaldat import GoalDat
from goal2.game.state import GameState, to_savestate
from goal2.game.campaign import ensure_friendly_session
from goal2.ui.country_select import run_country_select
from goal2.ui.input import Key
from goal2.ui.preview import run_match_preview
from goal2.ui.result import run_result
from goal2.ui.next_action import run_next_action
from goal2.ui.squad import run_squad_select
from goal2.ui.tactics import run_tactics_select


def run_main_loop(
    goaldat: GoalDat,
    state: GameState,
    original_savestate_bytes: bytes,
    keys: Iterable[Key] | None = None,
    *,
    on_save: Callable[[], None] | None = None,
    resume: bool = False,
) -> int:
    """Run the country → squad → tactics → preview → result loop.

    Steps:
    1. run_country_select: on None (Esc) returns 0 without calling later screens.
    2. run_squad_select: on False (Esc) returns 0.
    3. run_tactics_select: on False (Esc) returns 0.
    4. Save user choices and show a matchup preview; only Play proceeds to
       run_result in full-friendly mode.
    5. After a successful friendly, offer another friendly or quit. Repeats
       retain the selected country and current squad/tactics choices.
    A resumed session opens the next-action menu first and preserves its
    managed country without revisiting country selection. [designed: T33]

    [confirmed: A-WATCH-1 — result is a stand-in, running the quick engine;
    GA-4 — keys flow through the driver to each screen.
    derived: after step 4 saves, the engine reads the modified savestate
    (user choices applied via to_savestate), not the original.]
    [derived: T17's state adapter writes country_tactics at country record +0x2D;
    the quick engine reads that same byte (quick_engine.py:189).]
    """
    ensure_friendly_session(state)
    # [designed: each screen does `iter(keys)` internally; passing a list
    # would replay it from the start for every screen.] Normalise `keys`
    # to a single iterator once. (Luna R2, 2026-10-13)
    keys = iter(keys) if keys is not None else None

    # A resumed save first asks for an explicit next action. It keeps the
    # saved managed country and never re-enters country selection. [designed: T33]
    if resume:
        if on_save is None:
            proceed = run_next_action(keys)
        else:
            proceed = run_next_action(keys, on_save=on_save)
        if not proceed:
            return 0
    else:
        chosen = run_country_select(goaldat, keys, state=state)
        if chosen is None:
            return 0

    while True:
        # Re-entering the loop keeps managed_country and all confirmed choices.
        ok = run_squad_select(goaldat, keys, state=state)
        if not ok:
            return 0

        ok = run_tactics_select(goaldat, keys, state=state)
        if not ok:
            return 0

        # [derived: T17] Serialize the current state so each simulation reads
        # the retained player records and both final seed words.
        saved = to_savestate(state, original=original_savestate_bytes)
        ok = run_match_preview(goaldat, saved, keys, state=state)
        if not ok:
            return 0

        count_before = state.match_count
        # [designed: T26, A-MATCH-1] Interactive play uses the complete
        # assumed friendly; its successful state changes are retained.
        ok = run_result(saved, keys, state=state, full_match=True, goaldat=goaldat)
        if not ok:
            return 0
        if state.match_count == count_before:
            # A refusal or other unsuccessful simulation has no next fixture.
            return 0
        next_action = (run_next_action(keys) if on_save is None
                       else run_next_action(keys, on_save=on_save))
        if not next_action:
            return 0
