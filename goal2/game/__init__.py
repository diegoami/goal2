"""The rebuild's gameplay-side code: written-here modules, not vendored.

T03 `new_game`, T04 `skills`, T06/T17 `state` were moved here from
`goal2/engine/` (T21) — that directory now holds only the three vendored
rows in `PROVENANCE.md`. Importers reach these modules through this package.

Two import styles are used, deliberately:

- **Parent form** — `from goal2.game import new_game, skills; new_game.X(...)`.
  Used by tests and measurement scripts whose bodies call `module.X(...)`
  repeatedly. The three modules are re-exported below.
- **Direct form** — `from goal2.game.state import GameState, to_savestate`.
  Used in runtime code where the parameter name `state` (in `main_loop.run_main_loop`)
  would shadow the module, and where only specific names are needed. Names are
  not re-exported at the package level; callers import them from the submodule.

The codebase never mixes the two forms for the *same* module
(`from goal2.game import new_game` and `from goal2.game.new_game import
make_all_players` are mutually exclusive — T21 Hazards). The split is by
module: parent form for `new_game` and `skills`; direct form for `state`.
"""
from __future__ import annotations

from goal2.game import new_game, skills, state  # noqa: F401  re-exports for parent-form imports
