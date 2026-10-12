"""The `goal2.data` package: the data the rebuild reads to make a new game.

`GOAL.DAT` is the original game's data file; the rebuild never edits it
(CLAUDE.md rule 19 — no asset of the original game is committed). The loader
exposes its ten blocks as Python objects, and a CLI entry (`python -m goal2.data
--check <path>`) runs the R001–R011 block-shape checks F002 records.

[designed: the loader is this rebuild's; the block offsets and sizes are
F002's, and the field meanings (Pascal strings, the three per-country arrays,
the two per-country permutations, the squad-20 array) come from the same
finding.]
"""
from .goaldat import (
    GoalDat,
    SHA256,
    load,
    run_checks,
)


__all__ = ["GoalDat", "SHA256", "load", "run_checks"]
