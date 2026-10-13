"""The rebuild's gameplay-side code: written-here modules, not vendored.

T03 `new_game`, T04 `skills`, T06/`T17` `state` were moved here from
`goal2/engine/` (T21) — that directory now holds only the three vendored rows
in `PROVENANCE.md`. Importers reach these modules through this package;
the parent-form style (`from goal2.game import state; state.from_savestate(...)`)
is used everywhere so the codebase never mixes `goal2.game.X` and `goal2.game.X.Y`.
"""
from __future__ import annotations
