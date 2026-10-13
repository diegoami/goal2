"""The rebuild's gameplay-side code: written-here modules, not vendored.

T03 `new_game`, T04 `skills`, T06/T17 `state` were moved here from
`goal2/engine/` (T21) — that directory now holds only the three vendored
rows in `PROVENANCE.md`. Importers reach these modules through this package.

[designed: two import styles coexist, chosen by call site rather than by
module, to keep tests readable and runtime code free of parameter shadowing.

- **Parent form** — `from goal2.game import new_game, skills, state; X.Y(...)`
  brings the module into the call site's namespace so its body can use
  `module.X(...)` repeatedly. Used by every test file (call sites use
  `new_game.make_all_players(...)`, `skills.skills(...)`, `state.from_savestate(...)`)
  and by `measurements/T19/divergence.py` (it constructs the same way).
  The three modules are re-exported below so the form resolves.
- **Direct form** — `from goal2.game.state import GameState, to_savestate`
  imports the names directly, avoiding both the `state` parameter collision
  in `goal2.main_loop.run_main_loop` (where `state: GameState` would shadow
  the module) and the cost of a namespace indirection. Used by the runtime
  code under `goal2/{loop,main_loop}.py` and `goal2/ui/*.py`, and inside
  test bodies that need only one or two names (`from goal2.game.state
  import _wrap_raw, _countries_bytes` in `test_state.py:245`,
  `from goal2.game.state import GameState` in the test_*_select / test_tactics
  / test_main_loop files).

The codebase never mixes the two forms for the *same* call site: a file
either uses parent form for its main module or direct form for specific
names, not both. (T21 Hazards; the forbidden case is `from goal2.game
import new_game` alongside `from goal2.game.new_game import make_all_players`
in the same file.)
"""
from __future__ import annotations

from goal2.game import new_game, skills, state  # noqa: F401  re-exports for parent-form imports
