# Tasks

One file per task, `T<nn>.md`, from [`TEMPLATE.md`](TEMPLATE.md). The issue's `status:*` label is the
status; this index carries none.

| Task | Title | Issue | Merge after |
| --- | --- | --- | --- |
| T01 | The walking skeleton: the package, the quick-engine seam, one fixture end to end | — | — |
| T10 | The screen framework: the character grid (80×25) and a plain-text renderer | #24 | T09 |
| T11 | The country select screen: 128 countries, cursor + keys, write the choice to the state adapter | #26 | T10 |
| T12 | The squad select screen: 20 players, pick captain, write the eleven + captain to the state adapter | #28 | T11 |
| T13 | The tactics screen: 8 team tactics bits, toggleable, write to state | #30 | T12 |
| T14 | The result screen: run the vendored engine, display score + goals, label as stand-in | #32 | T13 |
| T15 | The computer's eleven + tactics: A-CPU-1 + A-CPU-2 stand-ins | #34 | T14 |
| T16 | The main loop driver | #36 | T15 |
| T17 | State adapter writes starting_eleven / captain / country_tactics | #38 | T16 |
| T18 | Main loop saves user state before run_result | #40 | T17 |
| T19 | Diagnose the LCG draw-order divergence against E006 byte-exact | #11 | T18 |
| T20 | Reconcile the LCG draw order and base-table indexing against E006 byte-exact | #11 | T19 |
| T21 | Move new_game/skills/state out of goal2/engine/ | #43 | T20 |
| T22 | Pin the vendored engine's change-tactics-when-behind behaviour (A-CPU-2 change side) | #51 | T21 |
| T23 | Display interactive grids before reading input | #53 | T22 |
| T24 | Support Codex alongside the existing Claude workflow | #56 | T23 |
| T25 | Make terminal keys immediate and restore input settings | #59 | T24 |
| T26 | Run a complete friendly through both halves | #62 | T25 |
| T27 | Make navigation visible in plain terminal output | #67 | T26, fix #65 |
| T28 | Choose the starting eleven | #70 | T27 |
| T29 | Match preview before kickoff | #72 | T28 |
