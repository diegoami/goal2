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
| T30 | Understand the match result | #76 | T29 |
| T31 | Clear terminal presentation | #78 | T30 |
| T32 | Repeat friendlies with retained state | #80 | T31 |
| T33 | Save and resume a friendly session | #83 | T32 |
| T34 | Browser dashboard and squad prototype | #86 | T33 |
| T35 | Browser country selection and real squad data | #88 | T34 |
| T36 | Browser lineup, captain, tactics and preview | #89 | T35 |
| T37 | Play and repeat friendlies in the browser | #90 | T36 |
| T38 | Browser save and resume | #91 | T37 |
| [T39](T39.md) | Reconcile the campaign evidence register (medium) | [#73](https://github.com/diegoami/goal2/issues/73) | — |
| [T40](T40.md) | Campaign state, calendar and fresh start (hard) | [#100](https://github.com/diegoami/goal2/issues/100) | T39 |
| [T41a](T41a.md) | Build opening campaign fixture metadata (hard) | [#125](https://github.com/diegoami/goal2/issues/125) | T40 |
| [T41](T41.md) | Play scheduled friendlies in the browser (medium) | [#101](https://github.com/diegoami/goal2/issues/101) | T41a |
| [T42](T42.md) | Apply match energy and between-fixture recovery (medium) | [#102](https://github.com/diegoami/goal2/issues/102) | T41 |
| [T43](T43.md) | Update confidence and display team morale (medium) | [#103](https://github.com/diegoami/goal2/issues/103) | T42 |
| [T44](T44.md) | Enforce injuries and suspensions at selection (medium) | [#104](https://github.com/diegoami/goal2/issues/104) | T43 |
| [T45](T45.md) | Portable national pool and twenty-player squad (medium) | [#105](https://github.com/diegoami/goal2/issues/105) | T44 |
| [T46](T46.md) | Prepare computer teams for campaign fixtures (medium) | [#106](https://github.com/diegoami/goal2/issues/106) | T45 |
| [T47](T47.md) | Allow halftime substitutions in campaign matches (hard) | [#107](https://github.com/diegoami/goal2/issues/107) | T46, T71 |
| [T48](T48.md) | Resolve other countries’ scheduled fixtures (medium) | [#108](https://github.com/diegoami/goal2/issues/108) | T47 |
| [T49](T49.md) | Build competition tables and code-based tie-breaks (medium) | [#109](https://github.com/diegoami/goal2/issues/109) | T48 |
| [T51a](T51a.md) | Accept the competitive original-match kit (hard) | [#170](https://github.com/diegoami/goal2/issues/170) | T49 |
| [T51](T51.md) | Resolve competitive matches, extra time and penalties (hard) | [#111](https://github.com/diegoami/goal2/issues/111) | T49, T51a |
| [T50](T50.md) | Play continental qualifying campaigns (hard) | [#110](https://github.com/diegoami/goal2/issues/110) | T51 |
| [T52](T52.md) | Play continental finals through a champion (hard) | [#112](https://github.com/diegoami/goal2/issues/112) | T50 |
| [T53](T53.md) | Play World Cup qualifying and regional playoffs (hard) | [#113](https://github.com/diegoami/goal2/issues/113) | T52 |
| [T54](T54.md) | Play World Cup finals through a champion (hard) | [#114](https://github.com/diegoami/goal2/issues/114) | T53 |
| [T55](T55.md) | Apply competition points and world rankings (medium) | [#115](https://github.com/diegoami/goal2/issues/115) | T54 |
| [T56](T56.md) | Age players at campaign stage boundaries (medium) | [#116](https://github.com/diegoami/goal2/issues/116) | T55 |
| [T57](T57.md) | Retire and replace players without breaking squads (hard) | [#117](https://github.com/diegoami/goal2/issues/117) | T56 |
| [T58](T58.md) | Finish a cycle and begin the next one (medium) | [#118](https://github.com/diegoami/goal2/issues/118) | T57 |
| [T59](T59.md) | Validate a complete playable four-year cycle (medium) | [#119](https://github.com/diegoami/goal2/issues/119) | T58 |

## Original watched-engine stage 1

See the [sequenced backlog](../watched-engine-backlog.md) for review gates, difficulty and scope.

| Task | Title | Issue | Merge after |
| --- | --- | --- | --- |
| [T60](T60.md) | Accept original watched-match entry evidence (Medium) | [#248](https://github.com/diegoami/goal2-archaeology/issues/248) | Decision/estimate gate; accepted PR #251 evidence with T62 |
| [T61](T61.md) | Accept reusable original watched-match packaging (Medium) | [#249](https://github.com/diegoami/goal2-archaeology/issues/249) | T60 evidence; PR #251 approved/merged; acceptance with T62 |
| [T62](T62.md) | Vendor optional watched kit and verify handoff (Easy–Medium) | [#132](https://github.com/diegoami/goal2/issues/132) | PR #251 approved/merged; T60/T61 coverage |
| [T63](T63.md) | Adapt game state into an original watched fixture (Medium) | [#133](https://github.com/diegoami/goal2/issues/133) | T62 |
| [T64](T64.md) | Commit watched results atomically and preserve saves (Medium) | [#134](https://github.com/diegoami/goal2/issues/134) | T63 |
| [T65](T65.md) | Run watched matches in a worker with progress (Medium) | [#135](https://github.com/diegoami/goal2/issues/135) | T64 |
| [T66](T66.md) | Watch an original friendly in desktop (Medium) | [#136](https://github.com/diegoami/goal2/issues/136) | T65, T70 |

## Planning maintenance

| Task | Title | Issue | Merge after |
| --- | --- | --- | --- |
| [T67](T67.md) | Reconcile stage-1 backlog with the interactive kit | [#140](https://github.com/diegoami/goal2/issues/140) | Existing stage-1 backlog and kit handover |
| [T68](T68.md) | Reconcile desktop pivot and campaign UI contracts (Medium) | [#148](https://github.com/diegoami/goal2/issues/148) | T44; owner desktop decision |

## Desktop interface

[designed: owner #148; T68] See the [desktop roadmap](../desktop-ui-roadmap.md).
Historical browser contracts T34–T38 are preserved; these are separate implementation slices.

| Task | Title | Issue | Difficulty | Merge after |
| --- | --- | --- | --- | --- |
| [T69](T69.md) | Desktop country and management shell | [#149](https://github.com/diegoami/goal2/issues/149) | Medium | T44 |
| [T70](T70.md) | Desktop quick friendly and campaign loop | [#150](https://github.com/diegoami/goal2/issues/150) | Medium | T69 |
| [T71](T71.md) | Desktop national pool controls | [#151](https://github.com/diegoami/goal2/issues/151) | Medium | T45, T70 |

## OpenCode 2 migration

[designed: owner #168,2026-10-17] Protocol acceptance precedes the runtime cutover.

| Task | Title | Issue | Difficulty | Merge after |
| --- | --- | --- | --- | --- |
| [T72a](T72a.md) | Pin OpenCode 2 protocol fixtures and adapter contract | [#173](https://github.com/diegoami/goal2/issues/173) | Hard | Existing reviewed harness |
| [T72](T72.md) | Migrate review launch, monitoring and recovery to OpenCode 2 | [#168](https://github.com/diegoami/goal2/issues/168) | Hard | T72a |
