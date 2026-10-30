# Handover 2026-10-30: the sealed match engine (goal2-archaeology T80)

**From**: goal2-archaeology, T80 (#291 there): T79 #624, T80a #625, T80b #626, T80c #627, T80d (its
`docs/handover/T80.md`, `experiments/E036-match-port/notes/T80.md`). Kind: a delivery of the engine
(CLAUDE.md, owner 2026-10-27: standalone engine replacement is top priority), not a finding.

## What it holds
- The plain Python port plays every admitted match equal to the original with **no Unicorn and no byte of
  GOAL.EXE at run time** beyond its constant tables: `compare.py --family ALL --no-screen` 75 of 75
  identical from records; A700 699 of 699 against T79's oracle; the kit's check (engine, interactive,
  goals, knockout, family) PASSes in a child that denies Unicorn and opening .sav/.EXE/.DAT.
- **Its input**: goal2's state = the memory goal2 holds with GOAL.EXE's load module left out, plus the
  initialised bytes the game changed (`Image.state_of`), and GOAL.EXE's tables. **Its output**:
  `Match.records_after()`, the same state after the match and its post-match update.
- **The tables** [designed: owner, 2026-10-29]: generated on the player's machine from the player's own
  GOAL.EXE by `port_tables.py extract`, which refuses any other build; never committed, never shipped.

## What the goal2 session does
1. After #624-#627 merge upstream: re-vendor `runtime/original_match/` at #627's merge commit into
   `goal2/engine/original_match/` and record it in `goal2/engine/PROVENANCE.md` (rule 13).
2. Vendor the tables generator (`tools/static/port_tables.py`'s `extract`, `tools/static/unlzexe.py`,
   `static/goal-exe/tables/manifest.json`: positions and digests only) and make goal2 build the tables
   once into the git-ignored user data from the player's GOAL.EXE (rule 14: no table in the repository or
   a release).
3. Adopt the engine (the adoption task after T78-T80): goal2's match route plays `engine="port"` from
   `Image.from_state(state, tables)` on PyPy 3.11 (#620; about 50-60 s of CPU a match), with
   `records_after()` as the next state; fresh careers only (no old-career migration).
4. Fidelity, lifecycle and the milestone review/playtest before publication, as CLAUDE.md requires.

## Not sealed (stays as it is)
The tournament continuation between matches (goal2-archaeology #427) stays the original's under Unicorn;
the port's board screen is not the original's bytes (comparisons leave it out); a fresh career's first
state still comes from a savestate goal2 holds.

## What goal2-archaeology does next
Nothing further for T80 after the merges; the T80 milestone review (owner-run, from the prompt the main
session gives) covers T79-T80d.
