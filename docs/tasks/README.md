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
| [T50](T50.md) | Play continental qualifying campaigns (hard) | [#110](https://github.com/diegoami/goal2/issues/110) | T51, T80 |
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
| [T66](T66.md) | Watch an original friendly in a Pygame match view (Medium) | [#136](https://github.com/diegoami/goal2/issues/136) | T65, T70 |

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

## Additional review transport

| Task | Title | Issue | Difficulty | Merge after |
| --- | --- | --- | --- | --- |
| [T73](T73.md) | Add direct Claude CLI and run one Sonnet review trial | [#174](https://github.com/diegoami/goal2/issues/174) | Hard | T72 |

## Modern football GUI proposal

[designed: owner #182, 2026-10-18] See the [visual study and bounded backlog](../design/football-gui/README.md).
These contracts come from planning PR188; per-slice preflight and main-session
retriage govern dispatch. Child issue identities are linked below; GitHub labels own status.

| Task | Title | Issue | Difficulty | Merge after |
| --- | --- | --- | --- | --- |
| [T74](T74.md) | Qt football shell and shared visual tokens | [#193](https://github.com/diegoami/goal2/issues/193) | Medium | #182 plan, T70, T71, T66, T80, T83 |
| [T75](T75.md) | Country identity, selection and overview | [#194](https://github.com/diegoami/goal2/issues/194) | Medium | T74, #181/PR183 |
| [T76](T76.md) | Squad/tactics draft workspace | [#195](https://github.com/diegoami/goal2/issues/195) | Hard | T75, T47, #164 |
| [T77](T77.md) | National pool exchange workspace | [#196](https://github.com/diegoami/goal2/issues/196) | Medium | T76, T71 |
| [T78](T78.md) | Fixture/result scoreboard and standings | [#197](https://github.com/diegoami/goal2/issues/197) | Medium | T75, T49, T51 |
| [T79](T79.md) | Qt/Pygame match presentation | [#198](https://github.com/diegoami/goal2/issues/198) | Hard | T74, T76, T78, T66, T83 |

## Continental qualifying desktop prerequisite

| Task | Title | Issue | Merge after |
| --- | --- | --- | --- |
| [T80](T80.md) | Play pending original competitive fixtures in the desktop (Hard) | [#189](https://github.com/diegoami/goal2/issues/189) | T51 |

## Original-engine animated pitch

[designed: owner,2026-10-18] The [pitch sequence](../design/animated-pitch/README.md)
precedes the management GUI redesign. Each slice gets independent review and
main-session preflight before implementation; status stays in issue labels.

| Task | Title | Issue | Difficulty | Merge after |
| --- | --- | --- | --- | --- |
| [T81](T81.md) | Validate original pitch coordinates and observation fidelity | [#211](https://github.com/diegoami/goal2/issues/211) | Hard | T66, T80 |
| [T82](T82.md) | Stream bounded original pitch frames independently of match events | [#212](https://github.com/diegoami/goal2/issues/212) | Hard | T81, T80 |
| [T83](T83.md) | Watch a numbered animated pitch in Pygame | [#213](https://github.com/diegoami/goal2/issues/213) | Hard | T82, #209 |

## Playtest usability and player information

[designed: owner,2026-10-19] Preserve the original information and improve access;
status remains in GitHub labels. The browsing bug is [#241](https://github.com/diegoami/goal2/issues/241).
The priority column records the manual audit's **proposed order**, not an owner-approved dispatch;
the main session still triages scope, dependencies and review for each follow-up. Issues
[#248](https://github.com/diegoami/goal2/issues/248)–[#251](https://github.com/diegoami/goal2/issues/251)
are in **goal2**, distinct from the archaeology #248/#249 rows above. [designed: issue #244 audit]

| Task | Title | Issue | Difficulty | Priority | Merge after / gate |
| --- | --- | --- | --- | --- | --- |
| [T84](T84.md) | Inspect complete original-style player attributes | [#242](https://github.com/diegoami/goal2/issues/242) | Hard | Existing backlog | T79, #241 |
| — | Illustrated original-game manual and UI/flow reference | [#244](https://github.com/diegoami/goal2/issues/244) | Documentation | High (owner) | Independent reference for #241–#243 and later UI slices |
| [T85](T85.md) | Find Play/Watch easily and choose match playback speed | [#243](https://github.com/diegoami/goal2/issues/243) | Medium | Existing backlog | T79 |
| — | Edit player roles, personal tactics and marking in desktop | [#248](https://github.com/diegoami/goal2/issues/248) | Scope/data audit first | High proposed | #241/#242 and supported-state audit; main-session triage |
| — | Browse campaign fixtures, standings, opponents and history | [#249](https://github.com/diegoami/goal2/issues/249) | Scope/data audit first | High proposed | Available campaign data audit; main-session triage |
| — | Scope and expose supported watched-match interventions | [#250](https://github.com/diegoami/goal2/issues/250) | Support matrix first | Medium proposed | Watched-kit/worker capability audit; main-session triage |
| — | Browse retained match summaries and assess saved-goal replay | [#251](https://github.com/diegoami/goal2/issues/251) | Retention audit first | Medium proposed | History-data audit; main-session triage |


## Whole-game plan #253

[designed: owner-approved queue, 2026-10-20] The [reconciled whole-game plan](../redesign-253/README.md)
holds the parity inventory, capability boundaries and open owner choices for the
accepted original-first desktop vision ([#266](https://github.com/diegoami/goal2/issues/266),
[docs/vision-266](../vision-266/README.md)). The visual direction is decided and is not
asked again; the earlier "Country desk" candidate is superseded history. The
[queue below](../redesign-253/backlog.md#approved-queue-and-first-supported-session)
is the owner-approved order, not a dispatch queue: each task keeps its own bounded preflight and
the repository's implementer and reviewer choice, and **plan acceptance is not implementation
approval**. Existing independently authorized work keeps its own contracts; this order does
not stop, cancel or redirect T79/T84/T85 or other active scopes. GitHub labels own
operational status.

| Lane | Planning scope | Issue / dependency gate |
| --- | --- | --- |
| 1 | Reconcile this plan; prepare bounded cloud slices | [#253](https://github.com/diegoami/goal2/issues/253); [#270](https://github.com/diegoami/goal2/issues/270) P0 cloud issue (referenced, not pre-split here); [#208](https://github.com/diegoami/goal2/issues/208)/[#268](https://github.com/diegoami/goal2/issues/268) keep their own tooling scope |
| 2 | Native validation, complete cards/bars, Play/Watch and speed; consuming proofs | [#198](https://github.com/diegoami/goal2/issues/198) (PR #240), [#242](https://github.com/diegoami/goal2/issues/242) and [#243](https://github.com/diegoami/goal2/issues/243); [B01/#259](https://github.com/diegoami/goal2/issues/259) split proofs |
| 3a | Launch, Resume and safe new career | [B02/#260](https://github.com/diegoami/goal2/issues/260); relevant #259 proof; G05 complete profile and #265 identity are separate |
| 3b | Original-style shell, Team and pool | [B03/#261](https://github.com/diegoami/goal2/issues/261) (split shell and Team/pool); #260 context, #198/#242/#243, #249 available information |
| 3c | Preparation, maximum-pitch play, result and Continue | [B04/#262](https://github.com/diegoami/goal2/issues/262); #261 shell, #198/#243, renderer/focus proof; #250 only supported decisions |
| 3d | First-slice acceptance oracles, started alongside 3a-3c | [B05/#263](https://github.com/diegoami/goal2/issues/263); first-slice acceptance is distinct from the 237-allocation full-parity gate |
| 3e | Available fixtures, tables and opponents; retained-history browsing | [#249](https://github.com/diegoami/goal2/issues/249) available-information slice; [#251](https://github.com/diegoami/goal2/issues/251) retained-history browsing |
| 4 | Independent career stream | [#110](https://github.com/diegoami/goal2/issues/110), [#112](https://github.com/diegoami/goal2/issues/112), [#113](https://github.com/diegoami/goal2/issues/113), [#114](https://github.com/diegoami/goal2/issues/114), [#115](https://github.com/diegoami/goal2/issues/115), [#116](https://github.com/diegoami/goal2/issues/116), [#117](https://github.com/diegoami/goal2/issues/117), [#118](https://github.com/diegoami/goal2/issues/118), [#119](https://github.com/diegoami/goal2/issues/119); [#155](https://github.com/diegoami/goal2/issues/155) |
| 5a | Supported decisions, retained records and replay | [#248](https://github.com/diegoami/goal2/issues/248), [#250](https://github.com/diegoami/goal2/issues/250), [#251](https://github.com/diegoami/goal2/issues/251) within their written bounds |
| 5b | Assistant/identity and local-manager contracts | [B06/#265](https://github.com/diegoami/goal2/issues/265), [B07/#264](https://github.com/diegoami/goal2/issues/264): contracts only; actual delivery unowned |
| 5c | Scope gaps with no delivery owner | [G01-G05, O13, O14](../redesign-253/decisions.md#unowned-capability-decisions): unowned; each full-parity claim needs a bounded contract; no task dispatch |
| 6 | Full-parity acceptance | B05/#263 full-parity gate; actual supported capabilities for B06/B07 and G01-G05, or explicit owner-named exceptions |

### Approved dependencies

[designed: owner-approved queue, 2026-10-20] Dependency order is stated **only** in the two tables below (and mirrored in `docs/redesign-253/package.json`); the lane rows above list issues without order. `validate.py --check vision` parses these rows and requires them to equal its independent list of the approved pairs: a reversed, missing or extra row fails, and so does a reverse arrow between issues or an order word that contradicts them elsewhere in this file. “#262” is the base match journey. The tables do not order #249, #263, lane 1 or lane 5, because the approved queue states no order for them. UI cosmetics are not part of the career stream’s order.

| Before | After | Source |
| --- | --- | --- |
| #198 | #242 | lane 2 |
| #198 | #243 | lane 2 |
| #260 | #261 | lane 3 |
| #261 | #262 | lane 3 |
| #262 | #251 | lane 3 |
| #110 | #112 | lane 4 |
| #112 | #113 | lane 4 |
| #113 | #114 | lane 4 |
| #114 | #115 | lane 4 |
| #115 | #116 | lane 4 |
| #116 | #117 | lane 4 |
| #117 | #118 | lane 4 |
| #118 | #119 | lane 4 |
| #155 | #117 | lane 4 |

| Not a prerequisite | Of | Source |
| --- | --- | --- |
| #259 | #198 | lane 2 |
| #259 | #242 | lane 2 |
| #259 | #243 | lane 2 |

### Lane 3 task files

[designed: autonomous run, 2026-10-21] #260 is split into two independently mergeable slices.

| Task | Title | Issue | Difficulty |
| --- | --- | --- | --- |
| [T86](T86.md) | Launch with Resume, Open another save and a reviewed new career | [#260](https://github.com/diegoami/goal2/issues/260) | Medium |
| [T87](T87.md) | Game save menu, Save as, and explicit replacement and quit decisions | [#260](https://github.com/diegoami/goal2/issues/260) | Medium |
| [T88](T88.md) | Complete original-style player cards, browsed from New career | [#288](https://github.com/diegoami/goal2/issues/288) | Hard |
| [T89](T89.md) | The original country card when choosing a country | [#288](https://github.com/diegoami/goal2/issues/288) | Medium |
| [T90](T90.md) | The management shell in the accepted original style | [#261](https://github.com/diegoami/goal2/issues/261) | Medium |
| [T91](T91.md) | The Country desk, Team and Pool pages in the accepted original style | [#261](https://github.com/diegoami/goal2/issues/261) | Medium |
| [T92](T92.md) | Rename a player and the manager | [#293](https://github.com/diegoami/goal2/issues/293) | Medium |
| [T93](T93.md) | Localized names for the national pool | [#295](https://github.com/diegoami/goal2/issues/295) | Medium |
| [T94](T94.md) | The watched pitch in the accepted original style | [#262](https://github.com/diegoami/goal2/issues/262) | Medium |
| [T95](T95.md) | Match preparation: both elevens, Quick or Watch, and the speed | [#262](https://github.com/diegoami/goal2/issues/262) | Medium |
| [T96](T96.md) | The original's pitch marks, officials and six speeds | [#262](https://github.com/diegoami/goal2/issues/262) | Medium |
| [T97](T97.md) | The result of a finished match, and Continue | [#262](https://github.com/diegoami/goal2/issues/262) | Medium |
| [T98](T98.md) | A Windows GitHub Actions workflow on every PR | [#278](https://github.com/diegoami/goal2/issues/278) | Medium |
| [T99](T99.md) | Team tactics and the attribute table in the GOAL style | [#304](https://github.com/diegoami/goal2/issues/304) | Medium |
| [T100](T100.md) | G8: the core runner | [#310](https://github.com/diegoami/goal2/issues/310) | Medium |
| [T101](T101.md) | Screens fit without scrolling: one fixed page, scaled | [#312](https://github.com/diegoami/goal2/issues/312) | Medium |
| [T102](T102.md) | The bench in a watched match: half time, and Enter mid-play | [#305](https://github.com/diegoami/goal2/issues/305) | High |
| [T103](T103.md) | G9: the screen catalogue of the core | [#315](https://github.com/diegoami/goal2/issues/315) | Medium |
| [T104](T104.md) | T102 review follow-ups, and the core tests as slow tests | [#316](https://github.com/diegoami/goal2/issues/316) | Small |
| [T105](T105.md) | G11: the desktop over the core — driver, desk, fixtures, tournament, history | [#321](https://github.com/diegoami/goal2/issues/321) | Large |
| [T106](T106.md) | G10: a new game over the core — start year, title, country choice, name | [#325](https://github.com/diegoami/goal2/issues/325) | Large |
| [T107](T107.md) | G12: the Team and Pool pages over the core | [#328](https://github.com/diegoami/goal2/issues/328) | Large |
| [T108](T108.md) | G14a: play the next game over the core — a round, captain, bench, results | [#331](https://github.com/diegoami/goal2/issues/331) | Large |
| [T109](T109.md) | G14b: watched match over the core — pitch, commentary and bench | [#333](https://github.com/diegoami/goal2/issues/333) | Large |
| [T110](T110.md) | G13a: complete three-column bulletins over the core | [#337](https://github.com/diegoami/goal2/issues/337) | Medium |
| [T111](T111.md) | G13b: continental finals and yearly continuation | [#339](https://github.com/diegoami/goal2/issues/339) | Medium |
| [T112](T112.md) | Convert original .GL and core .g2core saved games | [#341](https://github.com/diegoami/goal2/issues/341) | T100, T106 |
| [T113](T113.md) | G13c: World Cup finals and yearly continuation | [#342](https://github.com/diegoami/goal2/issues/342) | T111 |
