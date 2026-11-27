# A map of `docs/`

This page says which documents describe goal2 as it is today and which are history. A document
marked history records how a decision was reached. Do not take work, rules or a design from it unless
[plan.md](plan.md) or the UI design index sends you there. Status (what is done, what is next) is
on GitHub, not in these files (CLAUDE.md rule 9). [designed: owner, 2026-11-27]

## Start here

| Read | For |
| --- | --- |
| [../AGENTS.md](../AGENTS.md) | where the work is now, how to find the next step, how to run the checks |
| [../CLAUDE.md](../CLAUDE.md) | the rules every session follows |
| [plan.md](plan.md) | the owner's current decisions: what is built, the architecture, the milestones |
| [process.md](process.md) | how one task runs: branch, task file, checks, merge, checkpoint |
| [design/README.md](design/README.md) | every source of the UI design and which one wins |

## Current reference

**How the work runs**
- [process.md](process.md): task, branch, PR, checks and merge; stopping and resuming (§10).
- [validation.md](validation.md): which checks a PR runs and which a milestone runs.
- [runners.md](runners.md): where the checks run (hosted CI, the owner's machines).
- [milestone-review.md](milestone-review.md): the only mandated review, at a milestone.
- [cloud.md](cloud.md): preparing a fresh checkout or a cloud session.
- [artifacts.md](artifacts.md): the private original-game files in `.cache/`, and how to pull them.
- [packaging.md](packaging.md): the portable Windows ZIP.
- [tasks/README.md](tasks/README.md): the task files, `T<nn>.md`, from [tasks/TEMPLATE.md](tasks/TEMPLATE.md).

**The game and its rules**
- [assumptions.md](assumptions.md): every rule the rebuild plays by, and where it comes from.
- [engine-process.md](engine-process.md): the sealed match engine under PyPy, in its own process, over a pipe.
- [extended-squads.md](extended-squads.md): optional 22- and 24-player squads (#777).
- [pool-names.md](pool-names.md): the 33 authored country name profiles, and nothing beyond them.
- The Python route's campaign rules, used by `goal2/game` and `DesktopModel`:
  [campaign-state.md](campaign-state.md), [campaign-pool.md](campaign-pool.md),
  [campaign-computer.md](campaign-computer.md), [campaign-energy.md](campaign-energy.md),
  [campaign-confidence.md](campaign-confidence.md), [campaign-eligibility.md](campaign-eligibility.md),
  [campaign-halftime.md](campaign-halftime.md), [campaign-silent-results.md](campaign-silent-results.md),
  [campaign-standings.md](campaign-standings.md), [competitive-matches.md](competitive-matches.md),
  [continental-qualifying.md](continental-qualifying.md).

**The UI**
- [design/README.md](design/README.md): the index of the UI design. The redesign runs in the order of
  [#862](https://github.com/diegoami/goal2/issues/862).
- [ui.md](ui.md): the redesigned window, `goal2/ui`, module by module.
- [original-game/](original-game/README.md): the original's illustrated manual and uninterrupted playthrough.
  It is the default for every screen.
- [current-game/](current-game/README.md): the rebuild's illustrated manual. **It shows the older
  `goal2/desktop` window**, not `goal2/ui`.

**The older window and the core route (what v0.1 ships)**
- [core.md](core.md): the original under Unicorn, now a test oracle only (plan.md). No performance work on it.
- [desktop-management.md](desktop-management.md): the `goal2/desktop` window. It takes no new UI work.
- [watched-jobs.md](watched-jobs.md): the process bridge both windows' matches run through.
- [releases/v0.1.0.md](releases/v0.1.0.md): the v0.1 release notes.

## History

Kept for their evidence and reasoning. Each one was replaced by a later decision.

| Document | Replaced by |
| --- | --- |
| [vision-266/](vision-266/README.md), [redesign-253/](redesign-253/README.md) | the 2026-11-03 design (#526), #666 and #862 ([design/README.md](design/README.md)) |
| [desktop-ui-roadmap.md](desktop-ui-roadmap.md), [browser-ui-roadmap.md](browser-ui-roadmap.md), [prototypes/](prototypes/browser-ui/README.md) | `goal2/ui` ([ui.md](ui.md)) |
| [design/football-gui/](design/football-gui/README.md), [design/animated-pitch/](design/animated-pitch/README.md), [design/original-presentation-cues.md](design/original-presentation-cues.md) | the same, per the design index |
| [full-cycle-backlog.md](full-cycle-backlog.md), [watched-engine-backlog.md](watched-engine-backlog.md), [watched-kit-acceptance.md](watched-kit-acceptance.md), [standalone-core-integration.md](standalone-core-integration.md) | the standalone engine and the Python route (plan.md, Architecture; owner 2026-10-27 and 2026-11-03) |
| [estimates/](estimates/) | estimates of October 2026, before the engine decision |
| `handover-*.md` | deliveries from goal2-archaeology, each dated. They are evidence for the claims that cite them; the work they handed over is done or tracked on an issue |
| [tasks/](tasks/README.md) `T<nn>.md` of merged tasks | the record of each task. A merged task's file is not an instruction for new work |

Evidence folders ([evidence/](evidence/), `../measurements/`) hold receipts that tasks and PRs cite.
Read them when a claim points at them.
