"""The rebuild's gameplay-side code: written-here modules, not vendored.

T03 `new_game`, T04 `skills`, T06/T17 `state` were moved here from
`goal2/engine/` (T21) — that directory now holds only the three vendored
rows in `PROVENANCE.md`. Importers reach these modules through this package.

[designed: the codebase uses both import forms because each call site picks
whichever is shorter and clearer; this docstring names the actual usage
file-by-file so future readers do not have to grep to find out.

- **Runtime code** — `goal2/loop.py:14`, `goal2/main_loop.py:14`,
  `goal2/ui/country_select.py:17`, `goal2/ui/result.py:25`,
  `goal2/ui/squad.py:18`, `goal2/ui/tactics.py:18` — every one uses
  `from goal2.game.state import GameState, to_savestate, from_savestate`
  (direct form, names only). The `state` parameter in
  `main_loop.run_main_loop` (`state: GameState`) is the reason: importing
  the `state` module would shadow it.
- **Tests** — split by file:
    * `test_new_game.py`, `test_skills.py`, `test_p1_fidelity.py`,
      `measurements/T19/divergence.py` — parent form
      (`from goal2.game import new_game` / `skills`), because the test
      bodies call `module.X(...)` repeatedly.
    * `test_country_select.py`, `test_main_loop.py`, `test_squad_select.py`,
      `test_tactics.py` — direct form (`from goal2.game.state import GameState`),
      because the tests use `GameState` only for type hints.
    * `test_state.py` and `test_engine_on_adapted_state.py` — both:
      parent form on one line for `state.from_savestate(...)` /
      `state.to_savestate(...)`; direct form on another for
      `_wrap_raw` / `_countries_bytes` (the helper functions the
      round-trip test needs).

The forbidden case is `from goal2.game import new_game` alongside
`from goal2.game.new_game import make_all_players` in the *same* file
(T21 Hazards — a file imports the same module two different ways). The
coexistence of parent form and direct form *across* files is fine and
intentional; the docstring above is the only source of truth on which
file uses which.]
"""
from __future__ import annotations

from goal2.game import new_game, skills, state  # noqa: F401  re-exports for parent-form imports
