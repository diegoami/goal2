# Full-cycle playable campaign backlog

[designed: owner #97, 2026-10-16] The [stage-1 original watched-engine backlog](watched-engine-backlog.md) takes priority before starting the next campaign task. Retain this campaign sequence; after the first playable original watched friendly, the owner decides whether to continue these Python adapters or adopt more of the original core. This supersedes the earlier execution priority, not the preserved task scopes.

[designed: owner, 2026-10-15] Turn P4/P5 of the [plan](plan.md) into a sequenced backlog following browser friendlies T35–T38. The target is one human manager who can start a fresh campaign, manage the squad, play scheduled fixtures, follow both competitions and continue into the next four-year cycle. Ordinary browser controls remain the primary interface.

[designed] The table is execution order and dependency structure, not a status report. Each task merges separately after its predecessor. GitHub labels carry status. Creating these tasks does not start implementation or select implementer/reviewer models; the earlier Luna/MiniMax batch covered T35–T38.

| Order | Task and player-facing outcome | Difficulty | Depends on |
| --- | --- | --- | --- |
| 1 | [T39](tasks/T39.md) · [#73](https://github.com/diegoami/goal2/issues/73) — Reconcile the campaign evidence register | Medium | — |
| 2 | [T40](tasks/T40.md) · [#100](https://github.com/diegoami/goal2/issues/100) — Campaign state, calendar and fresh start | Hard | T39 |
| 3a | [T41a](tasks/T41a.md) · [#125](https://github.com/diegoami/goal2/issues/125) — Build opening campaign fixture metadata | Hard | T40 |
| 3b | [T41](tasks/T41.md) · [#101](https://github.com/diegoami/goal2/issues/101) — Play scheduled friendlies in the browser | Medium | T41a |
| 4 | [T42](tasks/T42.md) · [#102](https://github.com/diegoami/goal2/issues/102) — Apply match energy and between-fixture recovery | Medium | T41 + T64; owner post-stage-1 route choice |
| 5 | [T43](tasks/T43.md) · [#103](https://github.com/diegoami/goal2/issues/103) — Update confidence and display team morale | Medium | T42 |
| 6 | [T44](tasks/T44.md) · [#104](https://github.com/diegoami/goal2/issues/104) — Enforce injuries and suspensions at selection | Medium | T43 |
| 7 | [T45](tasks/T45.md) · [#105](https://github.com/diegoami/goal2/issues/105) — Manage the national pool and twenty-player squad | Medium | T44 |
| 8 | [T46](tasks/T46.md) · [#106](https://github.com/diegoami/goal2/issues/106) — Prepare computer teams for campaign fixtures | Medium | T45 |
| 9 | [T47](tasks/T47.md) · [#107](https://github.com/diegoami/goal2/issues/107) — Allow halftime substitutions in campaign matches | Hard | T46 |
| 10 | [T48](tasks/T48.md) · [#108](https://github.com/diegoami/goal2/issues/108) — Resolve other countries’ scheduled fixtures | Medium | T47 |
| 11 | [T49](tasks/T49.md) · [#109](https://github.com/diegoami/goal2/issues/109) — Build competition tables and code-based tie-breaks | Medium | T48 |
| 12 | [T51](tasks/T51.md) · [#111](https://github.com/diegoami/goal2/issues/111) — Resolve competitive matches, extra time and penalties | Hard | T49 |
| 13 | [T50](tasks/T50.md) · [#110](https://github.com/diegoami/goal2/issues/110) — Play continental qualifying campaigns | Hard | T51 |
| 14 | [T52](tasks/T52.md) · [#112](https://github.com/diegoami/goal2/issues/112) — Play continental finals through a champion | Hard | T50 |
| 15 | [T53](tasks/T53.md) · [#113](https://github.com/diegoami/goal2/issues/113) — Play World Cup qualifying and regional playoffs | Hard | T52 |
| 16 | [T54](tasks/T54.md) · [#114](https://github.com/diegoami/goal2/issues/114) — Play World Cup finals through a champion | Hard | T53 |
| 17 | [T55](tasks/T55.md) · [#115](https://github.com/diegoami/goal2/issues/115) — Apply competition points and world rankings | Medium | T54 |
| 18 | [T56](tasks/T56.md) · [#116](https://github.com/diegoami/goal2/issues/116) — Age players at campaign stage boundaries | Medium | T55 |
| 19 | [T57](tasks/T57.md) · [#117](https://github.com/diegoami/goal2/issues/117) — Retire and replace players without breaking squads | Hard | T56 |
| 20 | [T58](tasks/T58.md) · [#118](https://github.com/diegoami/goal2/issues/118) — Finish a cycle and begin the next one | Medium | T57 |
| 21 | [T59](tasks/T59.md) · [#119](https://github.com/diegoami/goal2/issues/119) — Validate a complete playable four-year cycle | Medium | T58 |

[designed] Useful checkpoints: T41 supplies scheduled friendlies in an actual campaign; T47 adds between-match management and halftime substitutions; T52 reaches a continental champion; T54 reaches a World Cup champion; T58 enters the next cycle; T59 validates the entire path, including persistence. T55–T57 add the ranking and player lifecycle effects required for the full-cycle acceptance, even though tournament traversal can be tested earlier.

[designed] Difficulty describes integration and rule uncertainty, not elapsed time or a model choice. Medium tasks reuse existing seams with bounded state changes. Hard tasks introduce campaign state, interrupt/resume a match, or combine competition scheduling and advancement. Before dispatch, split any task likely to exceed one implementer run; task files specify the protected outcome and checks. Future test commands are acceptance contracts to be implemented and verified, not checks claimed to pass today.

[derived: issue #73 and its register handover] T39 is the evidence gate. Audit the legacy coin-based tie-break and full quick-engine CPU-result assumptions, and check Live cells against the actual vendored modules. Use the reconciled register and pinned findings before downstream implementation. Reuse [#73](https://github.com/diegoami/goal2/issues/73); do not duplicate or silently merge its branch. Proposed static readings remain distinct from executable, measured models.

[designed: owner decisions recorded in #73] Substitution limits are unlimited for friendlies and five otherwise; ties follow the code rather than a coin. T47 initially exposes substitutions at halftime, a real boundary of the current quick engine. Continuous watched-match stoppages require the separate engine/interface work. Unresolved mechanics receive explicit assumption rows and replaceable interfaces; any new product choice goes to the owner. T51 must establish actual competitive-path support before enabling competitive matches, with a narrower implementation task if a model import or rebuild is needed.

[designed] Each new campaign transition includes persistent state and a narrow browser view when useful, so campaign data is not retrofitted at the end. Reads, refreshes and repeated actions must not simulate extra fixtures or reapply recovery, rankings, ageing or retirement. Save/resume checkpoints compare complete state and RNG continuation. Legacy friendly saves retain their meaning.

[designed] Match-engine strategy and visualization stay on their separate track: [#97](https://github.com/diegoami/goal2/issues/97), the [close-enough estimate #98](https://github.com/diegoami/goal2/issues/98), and the [emulation estimate #99](https://github.com/diegoami/goal2/issues/99). This backlog does not decide those options or require watched-match visualization before campaign play. If the owner chooses a whole-game emulated core, re-scope these rule adapters before implementation rather than building competing cores. Multiple managers, nationalized pool names and existing nonblocking cleanup remain separate.

[derived: T39 source audit of F023, archaeology 0ef880e] Stage 2 interleaves competitive qualifying fixtures with friendlies. Execute T51 after T49 and before T50; T52 follows T50. This avoids running qualifying fixtures with friendly rules. T40/T41 stop at unsupported fixture kinds until competitive support is available.

[designed: preflight split, 2026-10-16] T41a supplies the source-read opening schedule before T41 browser actions. T40 intentionally supplies no generator. Each slice has a separate PR/review, retaining T41’s scheduled two-friendly browser outcome and the subsequent dependency order.

[designed: owner-approved T67, 2026-10-16] The independent T41 browser task was
a bounded authorization while the kit handoff was prepared. Defer T42 until
T64 and the post-stage-1 route choice: original match setup/half/post-match
energy effects must be carried from accepted runtime state once. Retain the
T42 tests for those boundaries and for any separately evidenced between-fixture
recovery; do not build a parallel Python match-effect pipeline. See the
[kit coverage and acceptance gates](watched-engine-backlog.md).
