# The plan: a playable rebuild on findings, with an assumption register

The owner's decisions, starting 2026-10-12 (goal2 #2):
1. **A playable loop first.** New game → country → squad → match → results → the 4-year cycle,
   on plain screens; the original's screens come after.
2. **The watched match is a stand-in** until goal2-archaeology's M2–M5 land: the quick engine's
   result, shown with commentary lines, labelled as a stand-in. Nothing about how a watched match
   plays is invented.
3. **The primary interface is a Python desktop application.** [designed: owner #148,
   2026-10-16; session binding choice] Use PySide6 and ordinary Qt widgets, calling Python
   game/state/save interfaces directly. This supersedes the browser UI decision of 2026-10-15.
   The completed browser and terminal interfaces remain historical/secondary work; new primary
   UI work follows the [desktop roadmap](desktop-ui-roadmap.md). No server or hosting is required.
   [designed: owner, 2026-10-17] Keep Qt management and use a Pygame match view,
   delivered gradually through the UI-independent worker and an original-event viewer first;
   pitch animation follows separately validated coordinate mapping.
4. **The watched-match engine is the original's own, plugged in** [designed: owner, 2026-10-16, goal2 #97]. Stage 1 of
   [the estimate for issue 99](estimates/99-original-engine-plugged-in.md) now: the original's watched match
   (`run_match`, `0791:F1F6`) runs under Unicorn on goal2's own state in a local worker process, with the original's
   score, scorers, cards, injuries, ratings, commentary lines and board statistics. The owner accepts the `unicorn` dependency
   (goal2's first external one) and the original's game files at run time, loaded locally or fetched by full verified hash, never
   committed (the owner: the game is abandonware, the registered version included). The exact port (goal2-archaeology PR 243)
   and the close-enough engine (estimates/98-close-enough-engine.md) stay open options, chosen after the first playable exists;
   stage 3 (the whole game as a headless core) is **the first version** [designed: owner, 2026-10-22, #308]:
   the original's whole game runs under Unicorn as goal2's core, and goal2 is the desktop interface and the bot over it.
   The long-term goal stays an **independent executable** (no original files at run time), fed by goal2-archaeology's
   findings and engine port; the Python rule tasks T52-T59 (#112-#119) move to that track (label `long-term`). Stage 4 is small, last and unscheduled: the package will deliver the engine image from the private release at build time (#130/#148). This supersedes decision 2
   (the quick engine as the watched match's stand-in) once stage 1 lands; until then the stand-in stays.
5. **The main session drafts** this plan and the register.

Every rule the rebuild plays by is in [`assumptions.md`](assumptions.md), tagged by where it comes
from. Code carries CLAUDE.md's evidence tags; the register is where an `assumed` rule
names what replaces it.

## How the rebuild is built

- **Designed architecture: engine parts behind interfaces.** Each rule area (new game, the quick match, energy,
  confidence, ageing, retirement, competitions, the computer's choices) is a small interface with
  one implementation. A part is an `assumed` stand-in, or a vendored goal2-archaeology model
  (`goal2/engine/`, `PROVENANCE.md`). When a finding lands, its model replaces the stand-in behind
  the same interface. This is M0's substitution idea from goal2-archaeology T38, applied here. The
  register row says which implementation is live.
- **One game state, owned by goal2.** Countries, players (the 20-byte record's fields, F007),
  managers, fixtures and the RNG (F004's LCG). Vendored models read the original's memory layout,
  so a **state adapter** lays goal2's state out as that memory image. It is tested by
  round-tripping the archaeology's published savestates: load a state, write it back, compare
  bytes field by field.
- **Determinism.** One LCG stream, seeded as F004 says. No wall clock and no unseeded randomness
  in any rule. A whole campaign replays from its seed and its inputs. The bot (G-M5) needs this.
- **Desktop controls call Python directly.** [designed: owner #148; PySide6 session choice; Pygame match-view choice2026-10-17]
  Qt owns management, active state and saves; a separate Pygame process/window presents matches.
  A separate process runs costly match work and sends ordered
  events/results over local IPC. The kit runs in that process, with no HTTP layer. The UI owns
  active state and publishes a validated completed candidate once. Reuse the game logic, state
  adapter, register and save format; build desktop controls rather than reusing the web layer.
  Test actual Qt interactions and Python transitions; see the [desktop roadmap](desktop-ui-roadmap.md).
- **Nothing of the original is committed** (CLAUDE.md: nothing of the original game is committed). `GOAL.DAT`, the source of the
  country and player data, is read at run time from `.cache/`, fetched from goal2-archaeology's
  release by hash, like every savestate.

## Original watched-engine stage 1

[designed: owner #97/#130 and approved T67 planning, 2026-10-16] Follow the
[original watched-engine backlog](watched-engine-backlog.md): accept the kit
proposed in archaeology #250/PR #251 against T60/T61, then T62 optional vendoring,
T63 state/fixture adapter, T64 atomic publication/saves, T65 process worker and T66 desktop watched controls (also requiring T70).
Do not duplicate upstream entry/packaging work. The decision/estimate PRs
#122/#123/#126 define the original authorization; consuming the kit additionally
requires independent upstream approval/merge, exact accepted pins and all handoff
checks. The proposed candidate is planning evidence only. Preserve the stand-in
until the original path is proven. [designed: owner correction, 2026-10-16]
Campaign work continues in parallel: T42 follows T41 without a T64/route-choice
scheduling gate. Keep quick Python effects separate from original watched-result
publication so neither path applies match effects twice.

## Milestones

Each milestone ends playable or testable on its own. [designed: owner, 2026-10-15]
The sequenced [full-cycle backlog](full-cycle-backlog.md) expands P4/P5 into T39–T59,
with per-task dependencies, difficulty and acceptance contracts. Later contracts are checked
and refined against completed predecessors before dispatch; their existence does not start work.

| Milestone | What works at the end | Rests on |
| --- | --- | --- |
| **P0 The skeleton** (T01, written) | `python -m goal2.play <half-time state>` reproduces E010's second halves seed-exactly | F012, F004, F006 |
| **P1 A new game** | the 128 countries, 3,060 names, managers and squads from `GOAL.DAT`; players made as the original makes them (ages, peaks, abilities, positions, profiles); the 12 skills derived as the player screen shows them; checked against the archaeology's new-game savestates | F002, F007, F008, F010, F011 |
| **P2 One match, kick-off to whistle** | the state adapter; both halves of a quick match from goal2's own state (the first half assumed to run as the second, A-MATCH-1); a friendly reproduced exactly against an archaeology savestate where one exists | F012, F005, F021 |
| **P3 The loop** | country select → squad (20 + the 80-player pool) → pick an eleven and tactics → match → result screen with the stand-in commentary → the next fixture; the computer's eleven and its tactics as stand-ins (A-CPU-1, A-CPU-2) | F010, F011, F014 (ratings), the help file |
| **P4 Between matches** | energy spent and restored, confidence after results and events, team morale (display only), injuries keeping a player out, substitutions | F018, F019, F020, F021; owner C2/C3; the help file |
| **P5 The 4-year cycle** | friendlies, continental qualifying and finals, World Cup qualifying and finals, play-offs, groups and their tie-breaks, rankings, ageing at its stages, retirements and new players, the next cycle | the help file (formats); F016, F017; Q020/Q030–Q032 open |
| **P6 Interface coverage** | [designed: owner #148, 2026-10-16] desktop management and match flows, using the catalogue to identify information/actions rather than requiring the original layout/keys; match visualization follows available engine evidence | [desktop UI roadmap](desktop-ui-roadmap.md), [pinned original screen catalogue](design/football-gui/audit.md#original-goal-reference-board--private-sources-no-copied-assets), owner #148 |
| **P7 Several managers** | up to 6 human managers in one game (the pool's 80 per manager) | F011; owner B7 |

Original-engine evidence and reusable model code come from goal2-archaeology, milestone by
milestone. Each source must be adapted or deliberately vendored and tested before it replaces a
stand-in; a finding or a static reading alone is not executable support:

| From goal2-archaeology | Replaces here |
| --- | --- |
| the quick engine's foul path, extra time and penalties (`FoulPathNotModelled`, `ExtraTimeNotModelled`) | A-MATCH-2, A-MATCH-3: competitive fixtures, knockouts |
| Q035/Q036, the computer's choices | A-CPU-1..3 |
| Q030–Q032, Q020: the fixtures, draws, hosts, the other results, the rankings as the code has them | A-COMP-*; F023/F024 findings are proposed evidence, not a complete Python competition model |
| M1–M6, the watched engine (`0791:9564`) | A-WATCH-1: the stand-in becomes the real watched match |

## Campaign implementation map

[derived: T39 audit of the goal2 tree at `fccff58` and goal2-archaeology `origin/main` at
`0ef880e1f6ec9bc12b3f12c3aaecb4d747d9d5cb`] The upstream findings F022–F029 are still proposed.
T40 adds campaign state, a caller-supplied ordered fixture seam, fresh-start reconstruction and
version-2 campaign persistence; its interface and migration policy are in [campaign-state.md](campaign-state.md).
F023's competition builders and F024's silent-result path are static readings; no campaign
fixture builder, standings model, competitive resolver, energy/recovery adapter, or player
lifecycle adapter is vendored or implemented here. The only vendored executable engine module is
`goal2/engine/quick_engine.py`; `savestate.py` and `players.py` support state/data work, not a full
campaign model. [designed: T51; confirmed: PR255/E034] That historical snapshot
predates the accepted original-match kit and its [competitive adapter](competitive-matches.md).
Keep static source readings, supplied-fixture execution and original new-game replay separate.

| Area | Existing seam and available evidence | Implementation order and boundary |
| --- | --- | --- |
| Calendar and fresh start | `goal2/game/state.py`, `new_game.py`, `session_save.py`; F023 statically reads stages, fixture kinds/counts, groups and ordering. No calendar builder exists. | T40 owns campaign state, seed/year opening-stage selection, ordered fixtures and persistence. F023 §9 reads stage 2 when the start year is divisible by 4 (1992/1996/2000) and stage 5 when it is 2 mod 4 (1990/1994/1998/2002). Stage 2 interleaves kind-2 qualifiers with kind-1 friendlies. T41 may resolve kind 1 only; it must stop clearly at kind 2 until the competitive path exists. T50 cannot depend on friendly simulation of qualifiers. |
| Condition and availability | Quick engine reads energy/form; F018–F020 and F027 read expenditure, recovery, confidence, morale, injury and ban paths. Upstream `runtime/model/energy.py`, `confidence.py`, `morale.py` and `condition.py` contain reusable entry points, but they are not vendored here and require campaign callers, ordered draws and event sequencing. | T42–T44 adapt those upstream models behind explicit energy/recovery, result-update and selection seams. Keep the unresolved friendly-kind mapping (BM-4), ban timing and fixture-kind injury mapping visible; do not state isolated probes prove fixture-end behavior. |
| Competitions | F023 statically reads stage builders and 2/1/0 tables; F024 reads D47E and synthetic-fixture behavior. Neither is an importable Python model in goal2. | T48 models computer fixtures at the D47E seam, not through the quick engine. T49 applies the code's no-coin table keys. T50–T54 add qualifying, deciders and finals only once an actual competitive result path is reachable. [designed: T51; confirmed: PR255/E034] The explicit original competitive adapter resolves supplied fixtures and persists original winners/stage scores; the owner-selected code behavior governs knockout and table ties. New builders and live controls remain separate. |
| Player lifecycle | F016/F017 are evidence for ageing, retirement, ranking input and recreation. Upstream `runtime/model/ageing.py` and `recreate.py` contain reusable record-level models, but they are not vendored here and need campaign tables, country state and RNG continuity. | T55–T57 adapt those models for rankings, stage-boundary ageing, retirement/recreation and managed-pool handling. F017 reports placement bonuses 800/600/400/200 and +200 per `5E3A` call; F023 §§4/7 confirms kind-3/7 group fixtures call it and receive +200 each, so the findings show no numeric conflict. Keep the source's “knockout fixture” label distinct from the broader call-site coverage and verify the full update chain. T58 owns year/cycle continuation and the no-end behavior; sacking remains a distinct rule to implement from GA-5/6 only after its confidence seam is reconciled. |

[designed: owner decisions recorded in issue #73, 2026-10-15] Keep the rebuild substitution budget
unlimited for friendlies and five for every other match, despite the original's five/two budget.
Follow code for table and playoff ties, with no added coin. These choices do not establish the
original model's behavior or make its unported evidence executable.

### Open rules and replacement seams

[derived: pinned F022–F029 and register rows] Resolve each item at its named seam before claiming
that the campaign implements it:

- Q030/Q031/Q032: opening stage, actual fixture lists and draws; exact table ordering under equal
  keys; silent-result behavior against a recorded fixture. Replacement seams: T40 calendar, T49
  standings, T48 other-country result.
- Q020: verify the full ranking update chain and its effect on ratings. F017 reports 800/600/400/200
  placement bonuses and +200 per `5E3A` call; F023 §§4/7 confirms the same +200 for kind-3/7 group
  calls, so no numeric disagreement is identified. Replacement seam: T55 ranking adapter.
- F023's initial order arrays and RNG uniformity, host flag's match effect, and the home-side
  interpretation of stage-6 aggregate ties; replacement seams: T40/T50 scheduling and T51 result
  resolution.
- BM-4 confidence fixture-kind mapping; BM-6/BM-8 ban service at fixture end and load/new-game
  behavior; BM-9 injury duration by actual competition kind; replacement seams: T42–T44.
- F027's event during added time, extra-time clock and managed stoppage timing; replacement seam:
  T51 for competitive matches and a later watched-engine task for continuous play.
- GA-5's threshold edge and group exemption, GA-6's relation to BM-3 confidence, and end-of-cycle
  sacking behavior; replacement seam: T58 lifecycle transition after the confidence model is
  reconciled.
- F026's positional signs/marking overrides, F024 formation choice and F024's heuristic absence of
  squad-transfer routines; replacement seam: T46/T45 with focused evidence.

**The bot (G-M5)** starts once P5 plays a whole cycle unattended. It needs the loop, the computer
choice to compare against (`C`), and the determinism above. Its plan is a later issue.

## Order of work, and what waits

P0 → P1 → P2 → P3 → P4 → P5. [designed: owner #148, 2026-10-16] T69 and T70 bring the existing friendly loop to desktop; T71 supplies pool controls after portable T45. T45/T46 can proceed without those UI tasks or the engine kit. P6 coverage grows alongside game rules. P7 comes after P5. A milestone does not wait for a finding: it ships with its `assumed` rows,
and the finding replaces them when it lands.

Design questions go to the owner one at a time. A guess about mechanics is never asked: it is
recorded as `assumed`, with why and what replaces it.

## Risks

| Risk | What we do |
| --- | --- |
| Campaign findings F022–F029 remain `proposed` at the T39 source pin | the register distinguishes static readings, measured samples and owner choices; an adapted or vendored model is held to its own relevant check (CLAUDE.md: the fidelity test is the arbiter); a finding that changes reopens its rows |
| The state adapter misplaces a field the models read | round-trip tests against the published savestates, field by field, before any model runs on goal2's state |
| The first half differs from the second in a way the model does not show (kick-off, the half's start) | A-MATCH-1 is tested against a whole recorded quick match as soon as one exists with a kick-off state |
| The help file and the original code disagree on pool wording (100 vs 20 + 80); the rebuild deliberately changes the original substitution budget (5/2) to unlimited friendlies / five otherwise | the register marks evidence and rebuild policy separately; the designed substitution decision is recorded in issue #73 |
