# Handover, 2026-11-03: m3 Track B on a second computer

[designed: owner, 2026-11-03, #509] m3 runs as two tracks. **Track A** builds the engine pipe and the new window
(T159–T169, #533–#543). It runs in the first session, on the owner's main computer. **Track B** builds the
native game that takes GOAL.EXE out of run time. It runs in a separate Claude Code session on a second computer,
from the prompt below.

Start the session from an empty folder on the second computer and paste the prompt.

---

```text
You run m3's Track B for goal2 (diegoami/goal2) and its upstream, goal2-archaeology
(diegoami/goal2-archaeology). Another session on another computer runs Track A at the same time. Read this whole
prompt before you act.

## 0. Set up this computer (once)

1. Check GitHub: `gh auth status` must show diegoami with repo access. If not, stop and ask the owner to run
   `gh auth login`.
2. Check the Drive remote for the original's private files: `rclone listremotes` must show `goal2drive:`. If not,
   stop and ask the owner to copy the `[goal2drive]` section of their rclone.conf, or to export
   GOAL2_RCLONE_TOKEN (see goal2's docs/cloud.md, "Secrets").
3. Check PyPy: `uv python install pypy@3.11` (goal2's match tests need it).
4. Clone both repositories side by side:
     git clone https://github.com/diegoami/goal2-archaeology.git
     git clone https://github.com/diegoami/goal2.git
   In goal2-archaeology, run `tools/cloud_setup.sh` (its docs/cloud.md: DOSBox-X headless, the artifacts).
   In goal2, run `tools/cloud_setup.sh`, then `source .cache/cloud.env` before every test or gate run, and
   `export GOAL2_ARCHAEOLOGY=<path to your goal2-archaeology clone>`.
5. Read, in this order:
   - goal2: CLAUDE.md, AGENTS.md, docs/process.md, docs/plan.md (the m3 section and "The rebuilt UI"), and #509
     with all its comments. The task list there is the plan.
   - goal2: docs/design/technology-2026-11/README.md §2 (why route (b), and what it needs upstream).
   - goal2-archaeology: CLAUDE.md, AGENTS.md, its docs/process.md, and issue #427 with its comments.

## 1. What Track B is

The owner chose **route (b)** (2026-11-03, goal2 #527). goal2 grows its **Python route** (goal2/game/: own state,
new game, campaign through qualifying, every match on the sealed port) into the whole game. The original under
Unicorn, the "Core", stays only as the **test oracle** that each native part is proven against (goal2
CLAUDE.md rule 15).

Today the Python route stops at the first stage it has no builder for (`UnsupportedCampaignTransition`,
goal2/game/campaign.py). Its `--template` savestate and its tournament step still hold GOAL.EXE's memory
(goal2/game/watched_match.py `_complete_memory`).

The steps, in order (#509, "m3 task list, revised"). U = goal2-archaeology, T = goal2:

- **U1 (upstream):** goal2-archaeology #427, the **write-set part only**:
  - which memory writes and RNG words a match owns;
  - the manager-confidence terms and the post-match news (`000E:4E0E`) between `F1F6` and `B7FA`, as rules to
    port.
  NOT the live-Core entry frame, ABI or return boundary: route (b) never re-enters the original's caller.
  Answer #427 with this scope and say so on the issue.
- **U2 (upstream):** port and prove route_fixture, simulate_fixture and post-match news (segment `000E`).
- **T170 (goal2):** the native tournament continuation and world turn, so the Python route plays a whole season
  (it replaces T52–T55, #112–#115).
- **U3 (upstream):** port new game, the title and date code, and the management rules.
- **T171 (goal2):** a native new career, with no `--template` savestate.
- **U4 (upstream), then T172 (goal2):** the year change, ageing, retirement, sacking and rollover (T56–T58).
- **T173 (goal2):** a native save format, with no machine memory.
- **T174 (goal2):** full-cycle equivalence against the Core oracle (T59, T132, T133).
- **T175 (goal2):** Unicorn, the boot state and the template removed from run time. Only GOAL.DAT and GOAL.HLP
  stay imported.

Each upstream port is proven identical to the original, as the match engine was (T78–T80): the same seeds, the
same writes, the same results, under the original in Unicorn or DOSBox-X. It arrives in goal2 only as a
deliberate re-vendor that records the upstream commit in goal2's PROVENANCE.md (goal2 CLAUDE.md rule 13).

## 2. Rules for working beside Track A

- **Task numbers.** goal2 tasks are T170–T175 only. T159–T169 are Track A's. Upstream tasks take
  goal2-archaeology's own next free numbers.
- **Files.** Track A owns goal2/ui/, goal2/game/engine_process.py, goal2/game/engine_server.py, the match
  workers, goal2/desktop/ and packaging. Track B works in goal2/game/ (campaign*, new modules), goal2/engine/
  (re-vendors only) and its tests. If a T task must touch a Track A file, say so on #509 first and keep the
  change minimal.
- **Merging to main.** Before every merge: `git fetch` and rebase the branch on origin/main, re-run the gate
  (`python3 tools/check_premerge.py --expected-head <sha>`), then
  `gh pr merge <n> --squash --match-head-commit <sha>`. Never force-push main, never rewrite main, never git
  stash. No worktrees: one task at a time per clone.
- **The Windows runner (goal2-pc) is shared** with Track A. Slow runs queue; don't cancel runs you did not start.
- **Status lives on GitHub.** On goal2 #509, post a short comment when each U or T step starts, opens a PR or
  merges. On upstream issues, status goes in labels and comments. Read #509 before each new step to see what
  Track A has merged.
- **Reviews.** Only milestones mandate one, and no session starts a review. The m3 review comes after T175;
  the owner runs it.
- **Design questions go to the owner** (goal2 CLAUDE.md rule 7), on #509 or the task's issue, then wait.
  Nothing else waits for the owner.
- **The original's bytes.** None enter either public repository or its releases. The only exception is goal2's
  two vendored table files (goal2 CLAUDE.md rule 14). Never upload to the owner's Drive. Never print or commit
  credentials.
- **Models.** Record the model actually used on each PR. Never use DeepSeek or Alibaba models.
- **Background jobs.** Wait by PID (`while kill -0 <pid>; do sleep 30; done`), never with `pgrep -f`.
- **Owner's lessons.** A lesson or decision of the owner goes into CLAUDE.md or docs/ in a commit.

## 3. First action

Do the set-up of §0 and report what is missing, if anything. Then post on goal2 #509: "Track B started on the
second computer". Then start U1: read #427 and its comments, write the upstream task file for the write-set scope
following goal2-archaeology's process, and begin.
```
