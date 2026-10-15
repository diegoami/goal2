# The plan: a playable rebuild on findings, with an assumption register

The owner's decisions of 2026-10-12 (goal2 #2):
1. **A playable loop first.** New game → country → squad → match → results → the 4-year cycle,
   on plain screens; the original's screens come after.
2. **The watched match is a stand-in** until goal2-archaeology's M2–M5 land: the quick engine's
   result, shown with commentary lines, labelled as a stand-in. Nothing about how a watched match
   plays is invented.
3. **The interface should be clear and easy to extend.** [designed: owner, 2026-10-15]
   The playable UI uses ordinary browser controls backed by Python; it does not need a custom
   text look. This supersedes the earlier text-renderer requirement for the primary UI. Existing
   terminal screens remain available. Match-engine visualization comes later; see the concrete
   [browser UI roadmap](browser-ui-roadmap.md).
4. **The main session drafts** this plan and the register.

Every rule the rebuild plays by is in [`assumptions.md`](assumptions.md), tagged by where it comes
from. Code carries CLAUDE.md's evidence tags; the register is where an `assumed` rule
names what replaces it.

## How the rebuild is built

- **Engine parts behind interfaces.** Each rule area (new game, the quick match, energy,
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
- **Browser controls call the game through a small Python server.** [designed: owner, 2026-10-15]
  HTML/CSS/JavaScript show real session data and explicit actions. Test Python state transitions
  and actual browser interactions. The existing 80×25 character grid remains the terminal UI's
  rendering/test surface; it does not constrain the browser layout.
- **Nothing of the original is committed** (CLAUDE.md: nothing of the original game is committed). `GOAL.DAT`, the source of the
  country and player data, is read at run time from `.cache/`, fetched from goal2-archaeology's
  release by hash, like every savestate.

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
| **P6 Interface coverage** | [designed: owner, 2026-10-15] browser management and match flows, using the catalogue to identify information/actions rather than requiring the original layout/keys; match visualization follows available engine evidence | [browser UI roadmap](browser-ui-roadmap.md), `docs/screens.md`, owner B6, D1 and 2026-10-15 UI decision |
| **P7 Several managers** | up to 6 human managers in one game (the pool's 80 per manager) | F011; owner B7 |

The engine's other half comes from goal2-archaeology, milestone by milestone, and replaces the
stand-ins without changing the loop:

| From goal2-archaeology | Replaces here |
| --- | --- |
| the quick engine's foul path, extra time and penalties (`FoulPathNotModelled`, `ExtraTimeNotModelled`) | A-MATCH-2, A-MATCH-3: competitive fixtures, knockouts |
| Q035/Q036, the computer's choices | A-CPU-1..3 |
| Q030–Q032, Q020: the fixtures, draws, hosts, the other results, the rankings as the code has them | A-COMP-* |
| M1–M6, the watched engine (`0791:9564`) | A-WATCH-1: the stand-in becomes the real watched match |

**The bot (G-M5)** starts once P5 plays a whole cycle unattended. It needs the loop, the computer
choice to compare against (`C`), and the determinism above. Its plan is a later issue.

## Order of work, and what waits

P0 → P1 → P2 → P3 → P4 → P5. [designed: owner, 2026-10-15] Browser tasks T35–T38 connect the
existing friendly loop before further interface visualization. P6 coverage can grow alongside
game rules. P7 comes after P5. A milestone does not wait for a finding: it ships with its `assumed` rows,
and the finding replaces them when it lands.

Design questions go to the owner one at a time. A guess about mechanics is never asked: it is
recorded as `assumed`, with why and what replaces it.

## Risks

| Risk | What we do |
| --- | --- |
| Every finding is still `proposed` (none promoted to goal2-archaeology's `spec/` as of `d6ad065`) | the register names each finding's status; a vendored model is held to its own seed-exact check (CLAUDE.md: the fidelity test is the arbiter); a finding that changes reopens its rows |
| The state adapter misplaces a field the models read | round-trip tests against the published savestates, field by field, before any model runs on goal2's state |
| The first half differs from the second in a way the model does not show (kick-off, the half's start) | A-MATCH-1 is tested against a whole recorded quick match as soon as one exists with a kick-off state |
| The help file and the code disagree (substitutions: 2/5 in the help, 5 in the owner's play; the pool: 100 in the help, 20 + 80 in the code) | the code wins when a finding says so; until then the register says which source is live and why |
