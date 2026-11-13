# goal2

A faithful rebuild of *goal (version 2)* (New Era Software, 1993), and a bot that plays a country
competently for idle play. It is built from the evidence of the private
[goal2-archaeology](https://github.com/diegoami/goal2-archaeology) repository: its findings
(`F0nn`), task records and releases. No release is published yet.

- **The plan**, one page of current decisions: [docs/plan.md](docs/plan.md).
- **Where the work stands**: the latest comment on the `checkpoint` issue
  [#471](https://github.com/diegoami/goal2/issues/471).
- **How work runs**: [CLAUDE.md](CLAUDE.md) (its rules apply to every agent; Codex starts at
  [AGENTS.md](AGENTS.md)) and [docs/process.md](docs/process.md). Tasks are `docs/tasks/T<nn>.md`,
  indexed in [docs/tasks/README.md](docs/tasks/README.md).
- **Every rule the rebuild plays by**, and where it comes from: [docs/assumptions.md](docs/assumptions.md).

## What is in the tree

| Path | What |
| --- | --- |
| `goal2/engine/` | The vendored match engine and models, pinned in [PROVENANCE.md](PROVENANCE.md). Never edited here (CLAUDE.md rule 13). |
| `goal2/game/` | goal2's own state, campaign, saves and the PyPy engine process ([docs/engine-process.md](docs/engine-process.md)). |
| `goal2/ui/` | The new window, following the original's screens ([guide](docs/ui.md), [design](docs/design/ui-2026-11/README.md)). |
| `goal2/desktop/` | Today's shipped window, with the Python route and the Core route ([guide](docs/desktop-management.md), [docs/core.md](docs/core.md)). |
| `goal2/core/` | The original's whole game under Unicorn, kept as the test oracle. |
| `goal2/web/`, `goal2/loop.py` | The browser and terminal interfaces. Superseded; they take no new work. |
| `docs/current-game/` | A manual of the build as it runs, with its own screenshots. |
| `docs/original-game/` | The original, screen by screen. |

## Setting up

The game needs the original's data files, which are never committed (CLAUDE.md rule 14). They are
pulled from the owner's private Drive folder into the git-ignored `.cache/`
([docs/artifacts.md](docs/artifacts.md)). The match engine runs under PyPy 3.11 and does not fall
back to CPython.

```bash
tools/cloud_setup.sh
```

```bash
source .cache/cloud.env
```

That prepares a virtualenv in `.cache/venv` with the `desktop`, `watched` and `match-view` extras
and pulls the files ([docs/cloud.md](docs/cloud.md)). PyPy 3.11 is installed separately:

```bash
uv python install pypy@3.11
```

## Running

The new window:

```bash
python -m goal2.ui
```

Today's window, on the Python route:

```bash
python -m goal2.desktop --template .cache/e010-r0008-halftime.sav --data .cache/GOAL.DAT --save .cache/desktop.g2save
```

The Windows portable build is described in [docs/packaging.md](docs/packaging.md).

## Checks

```bash
python tools/check_premerge.py --expected-head "$(git rev-parse HEAD)"
```

This is the gate a PR passes before it merges (process.md §3). A test whose dependency or
original-game file is absent skips with its reason; the tests that need PyPy fail without it.
