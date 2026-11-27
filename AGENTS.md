# goal2: start here

This file is for every agent: Codex, OpenCode (any model) and Claude Code. It says where the work
is, how to find your next step, and how to run the checks. The rules are in [CLAUDE.md](CLAUDE.md)
and apply to every client. Claude Code's skills and agents under `.claude/` are Claude-specific;
other clients follow the same steps with their own tools. [designed: owner, 2026-11-27]

goal2 rebuilds the 1993 DOS game *goal (version 2)* as a native Windows desktop game in Python. The
redesigned window is `goal2/ui` (PySide6). The match engine is a sealed Python port of the
original, run under PyPy in its own process. Everything rests on evidence from the private
goal2-archaeology repository.

## 1. Read, in this order

1. [CLAUDE.md](CLAUDE.md): the rules. Above all: never edit `goal2/engine/`; never commit an
   original-game file; never `git stash`, force-push or rewrite `main`; tag every behaviour claim
   `[confirmed]`, `[derived]` or `[designed]`; a question is not a request to edit.
2. [docs/plan.md](docs/plan.md): the owner's current decisions and milestones.
3. [docs/process.md](docs/process.md): how one task runs, from branch to merge.
4. [docs/README.md](docs/README.md): which documents are current and which are history. **Don't take
   work from a document marked history.**
5. For any screen: [docs/design/README.md](docs/design/README.md), then the
   [UI evidence rule](CLAUDE.md#ui-evidence).

## 2. Where the work is

Two tracks run in parallel, usually in two sessions. Status lives on GitHub, never in this file.

| Track | Parent issue | What it does | Its sources |
| --- | --- | --- | --- |
| **UI redesign** | [#862](https://github.com/diegoami/goal2/issues/862), under [#666](https://github.com/diegoami/goal2/issues/666) | redraws each `goal2/ui` screen from the original, one slice at a time | [docs/design/README.md](docs/design/README.md) |
| **Native season** | [#566](https://github.com/diegoami/goal2/issues/566) (T170), toward [#509](https://github.com/diegoami/goal2/issues/509) m3 | makes the Python route play a whole season on the native engine, without Unicorn | [docs/engine-process.md](docs/engine-process.md), the T170 task files |

**Find your next step:**
1. Read the latest comments on the checkpoint issue [#471](https://github.com/diegoami/goal2/issues/471).
   Both tracks post there. Take the newest comment whose **Next:** line names your track; another
   track's next step is not yours.
2. Run `python3 tools/checkpoint.py` for the live snapshot: branches, open PRs, jobs.
3. Recheck the live PR heads, labels and checks before acting. A vanished job is rerun, never
   assumed to have passed.
4. For the UI track, the newest comment on #862 names the slice in progress and the one after it.

Don't take the other track's open PR or branch. If the owner hasn't said which track you are on, ask.

## 3. Running things locally

The owner's machine has the private game files in `.cache/` and a project virtualenv in `.cache/venv`.
A fresh checkout runs `tools/cloud_setup.sh` first ([docs/cloud.md](docs/cloud.md)).

```bash
source .cache/cloud.env      # venv on PATH, offscreen Qt, SDL dummy drivers
export GOAL2_ARCHAEOLOGY=/home/diego/projects/goal2-archaeology-engine   # the clone with the vendored pins
python -m unittest goal2.tests.test_ui_pitch_t166                       # one test module
python3 tools/jobs.py start gate -- python tools/check_premerge.py --expected-head "$(git rev-parse HEAD)" --jobs 4
python3 tools/jobs.py wait gate                                          # the pre-merge gate, as a tracked job
python -m goal2.ui                                                       # the redesigned window
```

- Run only one pre-merge gate at a time on a computer (process.md §10).
- Without `GOAL2_ARCHAEOLOGY`, the vendor and provenance tests fail. Without `cloud.env`, the
  real-window tests fail under WSLg. Neither failure is a defect in your change.
- Wait on a job with `tools/jobs.py wait`, never with `pgrep -f` (CLAUDE.md rule 11a).

## 4. Checkouts and files you must not touch

- `/home/diego/projects/goal2-archaeology-engine` is the delivery clone of goal2-archaeology.
  `/home/diego/projects/goal2-archaeology` belongs to another analysis session: don't change it.
- Never read or alter the owner's untracked `.claude/settings.local.json.clother-20261020-181204.bak`,
  `1` or `error1.txt`.
- Evidence and receipts too large or private for git are in `/home/diego/projects/goal2-keep`.
- Codex on the owner's machine: read the `worktree-cleanup` skill
  (`/home/diego/.codex/skills/worktree-cleanup/SKILL.md`) and its latest sweep receipt on resume.

## 5. Not to be restarted

No resume authorises these (CLAUDE.md, owner 2026-10-26 and 2026-10-27):
- Unicorn performance work.
- Migrating old careers.
- Surname research beyond the 33 authored country profiles (the top 32 plus Greece, 80 surnames
  each; other countries keep their original names).
- The October #253 queue.

## 6. Pitfalls found earlier

- **Native-season state.** The route-boundary state goes stale after held edits, so don't use it as a
  current card or lineup preview. The legacy assistant projection (`best_twenty_state.prepare`) is not
  a native season bootstrap.
- **Marking menu.** The original's marking-menu eligibility includes the available outfield bench
  players, not only the XI.
- **The assistant (T183).** Preserve the accepted A / Ins controls and their isolated owner data. Native
  held-season integration needs its own explicit contract.
- **Native-track history.** The detailed status this file carried until 2026-11-18 is on
  [#471](https://github.com/diegoami/goal2/issues/471#issuecomment-7213437303).
