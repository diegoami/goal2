# The plan: current decisions

One page of what holds today. Every line is an owner decision unless tagged otherwise. Status is not
kept here (CLAUDE.md rule 9): it is on the `checkpoint` issue #471 and the issues named below. The
plan as it stood until 2026-11-13, with every superseded decision, the campaign implementation map
and the P0–P7 table, is in this file's git history (`git log -- docs/plan.md`).

## What is being built

- A faithful rebuild of *goal (version 2)* and a bot that plays a country competently for idle play
  [designed: owner, 2026-10-11].
- **The fidelity bar**: where the vendored model is seed-exact, the rebuild equals it (CLAUDE.md
  rule 15). Ported code is proven identical to the original before it replaces it [designed: owner,
  2026-11-02, #509].
- Every rule the rebuild plays by, and where it comes from, is in [assumptions.md](assumptions.md).

## Architecture

- **Match engine**: the sealed Python port from goal2-archaeology (T78–T80), vendored with its two
  constant tables, run under **PyPy 3.11** in one long-lived engine process that the window talks to
  over a pipe. No CPython fallback, no Unicorn match path [designed: owner, 2026-10-27, 2026-10-29,
  2026-10-31, 2026-11-01, 2026-11-03; [engine-process.md](engine-process.md)].
- **The game grows from the Python route** (`DesktopModel`). The original's whole game under
  Unicorn (the Core) stays only as the test oracle, and Unicorn leaves the build at m3 [designed:
  owner, 2026-11-03, #524–#527].
- **The window** is `goal2/ui`: PySide6 trimmed to Essentials, the pitch a widget inside it. It
  follows the original's screens and flow ([design](design/ui-2026-11/README.md), [guide](ui.md)).
  `goal2/desktop` stays the shipped window until T169 switches the portable build over [designed:
  owner, 2026-11-03, #526, #527].
- **The look**: the original's layout grammar at 2×. A 16 × 32 cell, one text size, rule-and-label
  frames, line-art titles, no dead regions, shown at 4:3; default window 1440 × 1080 [designed:
  owner, 2026-11-08, #666; 2026-11-09, #471].
- **Data**: no original asset is committed except the two engine tables (CLAUDE.md rule 14).
  GOAL.DAT is read from the player's own install first and replaced by goal2's own data later
  [designed: owner, 2026-11-02, #509].
- **Delivery**: a portable Windows ZIP with the PyPy runtime inside, built with Nuitka in an
  isolated environment ([packaging.md](packaging.md), #432).

## Rules of play that differ from the original, or settle an open point

- Substitutions: unlimited in friendlies, five in every other match (the original: five and two).
  Table and play-off ties follow the code, with no added coin [designed: owner, 2026-10-15, #73].
- A key wait that draws counts as answered at its first key poll; the Core oracle is driven the same
  way [designed: owner, 2026-11-03, #509].
- The route harness answers a refused first team with a legal eleven and records each choice
  [designed: owner, 2026-11-04, #509].
- Fresh careers only; old careers are not migrated [designed: owner, 2026-10-27].
- Pool names: the 33 authored country profiles only; the 128-country expansion is dropped
  [designed: owner, 2026-10-26, #415].

## Milestones, in order

| Milestone | What it is | Where |
| --- | --- | --- |
| m1 Core first playable | Reviewed at `044f7bcb`, never tagged; superseded by m2 | #415 (open: close it or tag it) |
| m2 Standalone engine | Tagged `m2-standalone-engine` at `e4991d94`, 2026-11-02 | #507 |
| **m3 GOAL.EXE out entirely** | No code path needs Unicorn or the recorded boot state | #509 |
| UI fidelity | The 32 px reflow reaches `main` only through T215: milestone review and the owner's Windows playtest | #666, branch `ui/foundation-32` |
| Autonomous showcase | A country followed through a whole cycle, published as web demos; queued, displaces nothing | #648 |

**What m3 still needs** [derived: #471, 2026-11-09]:

1. T170, the Python route plays a whole season, each round equal to the Core's (#566). In-season
   ageing, retirement and replacement come before the sealed route; year rollover stays deferred
   and the route stops at that boundary [designed: owner, 2026-11-04]. The season comparison is a
   milestone proof, not a CI gate [designed: owner, 2026-11-09].
2. T183, the assistant's recommended twenty on the squad screen: required, no heuristic substitute
   (#594) [designed: owner, 2026-11-05].
3. The Core's remaining screens and logic, then the portable ZIP on the new window (T169).

Each milestone gets a review and the owner's playtest before it is tagged
([milestone-review.md](milestone-review.md)).

## Not scheduled

- Several managers, hot seat (#551); converting original `.GL` saves (#341); sounds (#431).
- Unicorn performance work, old-career migration, extra-country surname research (CLAUDE.md).
- The Rust engine is developed in `diegoami/goal2rust`; this repository stays on the Python port
  until that one is equal [designed: owner, 2026-10-29].
- The bot starts once a whole cycle plays unattended.

## Superseded, kept in the tree

The terminal loop (`goal2.loop`), the browser UI (`goal2/web`), the quick-engine stand-in for the
watched match, the separate Pygame match window and the Unicorn match path. None takes new work.

## Open for the owner

- #415: close m1 or tag it at `044f7bcb`.
- #422: should the Core window ask before closing and before overwriting a save?
- #396: does the substitution budget apply to computer-against-computer results worldwide?
- [raised in the 2026-11-13 evaluation, undecided] Whether a release ships before m3, on the Core
  route with the player's own game files; and whether the logic between matches must be identical
  to the original or only the match engine.
