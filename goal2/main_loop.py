"""The main loop driver: country → squad → tactics → result → next fixture.

[derived: T15's `pick_computer_eleven` and `get_computer_tactics` are not on
T16's path in v1; GA-4 keys flow through the driver to each screen.]
[designed: the placeholder next-fixture line uses state.managed_country.]
[confirmed: A-WATCH-1 — the result screen is T14's stand-in; A-MATCH-2/3 —
refusals are surfaced by run_result itself.]
"""
from __future__ import annotations

from typing import Iterable

from goal2.data.goaldat import GoalDat
from goal2.engine.state import GameState, to_savestate
from goal2.ui.country_select import run_country_select
from goal2.ui.input import Key
from goal2.ui.result import run_result
from goal2.ui.squad import run_squad_select
from goal2.ui.tactics import run_tactics_select


def run_main_loop(
    goaldat: GoalDat,
    state: GameState,
    original_savestate_bytes: bytes,
    keys: Iterable[Key] | None = None,
) -> int:
    """Run the country → squad → tactics → result loop and return the exit code.

    Steps:
    1. run_country_select: on None (Esc) returns 0 without calling later screens.
    2. run_squad_select: on False (Esc) returns 0.
    3. run_tactics_select: on False (Esc) returns 0.
    4. Save user choices (country_tactics, captain, starting_eleven) back into
       the savestate bytes via `state.to_savestate`, then run_result with the
       modified bytes so the quick engine reads the updated tactics byte.
    5. Prints a one-line next-fixture placeholder using state.managed_country.

    [confirmed: A-WATCH-1 — result is T14's stand-in, running the quick engine
    on the original savestate; GA-4 — keys flow through the driver to each screen.]
    [derived: T17's state adapter writes country_tactics at country record +0x2D;
    the quick engine reads that same byte (quick_engine.py:189).]
    """
    # [designed: each screen does `iter(keys)` internally; passing a list
    # would replay it from the start for every screen.] Normalise `keys`
    # to a single iterator once. (Luna R2, 2026-10-13)
    keys = iter(keys) if keys is not None else None

    # Step 1: country select
    chosen = run_country_select(goaldat, keys, state=state)
    if chosen is None:
        return 0

    # Step 2: squad select
    ok = run_squad_select(goaldat, keys, state=state)
    if not ok:
        return 0

    # Step 3: tactics select
    ok = run_tactics_select(goaldat, keys, state=state)
    if not ok:
        return 0

    # Step 4: save user choices then run result
    saved = to_savestate(state, original=original_savestate_bytes)
    ok = run_result(saved, keys, state=state)
    if not ok:
        return 0

    # Step 5: next fixture placeholder (derived from state.managed_country)
    print(f"Next fixture: {state.managed_country}")
    return 0
