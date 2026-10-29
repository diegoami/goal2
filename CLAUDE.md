# goal2

The faithful rebuild of *goal (version 2)* (New Era Software, 1993) and the bot that plays a
country competently for idle play (the owner, 2026-10-11), built from the evidence of the private
`goal2-archaeology` repository (findings `F0nn`, task records, releases). Python. The plan is
[`docs/plan.md`](docs/plan.md); how work runs is [`docs/process.md`](docs/process.md). Tasks are
`docs/tasks/T<nn>.md`, indexed in `docs/tasks/README.md`.

[designed: owner, 2026-10-20] The project runs from any checkout, a cloud session included. The
earlier review harness (OpenCode protocol, guards, jail, model switching, worktrees, per-PR review
gates) was removed; it is kept on the branch `local`. A fresh checkout is prepared with `tools/cloud_setup.sh`
([docs/cloud.md](docs/cloud.md)). The first release is lane 3 of the approved queue, the bounded
first supported session (`docs/redesign-253/vision-reconciliation.md`; O03/O04 resolved 2026-10-20).
[designed: owner, 2026-10-22] It runs the original's whole game under Unicorn as goal2's core (stage 3,
#308); the long-term goal stays an independent executable, fed by goal2-archaeology (label `long-term`).

[designed: owner, 2026-10-27] **Standalone engine replacement is now top priority**,
superseding the earlier long-term/planning-only deferral. Stop optimizing the Unicorn
match path. Implement upstream T78–T80 and the required new-session tournament-result
contract, then adopt the accepted engine in goal2. Fresh careers suffice; old-career
migration is not required. The replacement must still pass fidelity, lifecycle and
milestone review/playtest before publication. The remaining requested UI and portable
Windows batch stays required. Build-only Nuitka4.1.1 and declared build dependencies
are approved in an isolated environment/CI (goal2#432comment6440424797).
[designed: owner, 2026-10-29] The accepted plain port runs under **PyPy 3.11** as goal2's engine runtime:
a PyPy match-engine process beside the CPython/PySide6 UI, a PyPy runtime shipped in the portable
build. Same code, same results (E034-03's drive and F40 identical, T79's 700 matches identical on
PyPy: goal2-archaeology #620, #290), about 4 times CPython's speed. A Rust engine is developed in
parallel in diegoami/goal2rust; this repository stays on the Python port until that one is equal.

## Resuming authorised work

[designed: owner handover, 2026-10-29] Continue in the owner's selected fresh Claude
session, with the same task, fidelity and merge requirements. First read
[AGENTS.md](AGENTS.md), [docs/process.md](docs/process.md) and the current
latest comment on the `checkpoint` issue #471 (the earlier handover is
[#308's](https://github.com/diegoami/goal2/issues/308#issuecomment-6442836606)), then recheck live PR
heads, labels and checks. Status and pending runs belong on
those issues/PRs; never infer completion from an old handover or a percentage estimate.

The independent delivery clone is `/home/diego/projects/goal2-archaeology-engine`;
`/home/diego/projects/goal2-archaeology` belongs to the other analysis session and
must be preserved. Cloud checkouts use their own persistent workspace paths and
[docs/cloud.md](docs/cloud.md); fetch the recorded remote branches/evidence rather
than assuming local caches/private captures are present. Record actual models used.

Never read or alter the owner's untracked `.claude/settings.local.json.clother-20261020-181204.bak`,
`1` or `error1.txt`. Preserve active/unresolved work and unique evidence. No obsolete
#253 automatic sequence, extra-country surname research, old-career migration or
Unicorn performance optimisation is authorised by a resume.

## Working rules
1. The main session plans, triages, talks to the owner and merges. It implements itself or spawns
   a subagent (`.claude/agents/implementer.md`) on its own judgment; the owner names a model only
   when they want a specific one.
2. Work on a branch in the checkout at hand; one task at a time per checkout. No worktrees.
   Locally a task branch `task/T<nn>-<slug>`; in a cloud session the session's own `claude/…`
   branch, for every task of that session (process.md §3). Never `git stash`, never force-push,
   never rewrite `main`.
3. One task, one PR, merged by the main session once its Done-when lines and
   `python3 tools/check_premerge.py --expected-head <sha>` pass (it runs the slow tests by
   itself when the change touches what they guard; process.md §3): locally
   `gh pr merge <pr> --squash --match-head-commit <sha>`; in a cloud session
   `gh pr merge <pr> --merge --match-head-commit <sha>` (never squash), then
   `git pull --ff-only origin main` on the session branch.
4. [designed: owner, 2026-10-29, as in malpaco] Only milestones mandate a review. A PR merges
   when its Done-when lines and checks pass, with no per-PR review. At each milestone the main
   session opens the milestone issue and gives the owner the review prompt
   ([docs/milestone-review.md](docs/milestone-review.md)); the owner runs it on a model of their
   choice. A per-PR review happens only when the owner asks for one, from a prompt the main
   session writes (`tools/review_pr.sh <pr> <cli> <model> --print`). No session starts a review.
   Relay review findings in full.
5. The Done-when is not negotiable by the implementer: it stops and reports, never weakens an
   assertion, skips a test or edits its task file. The main session amends a Done-when on `main`
   with the reason in the commit message.
6. A question is not a request to edit files. Answer it; propose any fix and wait.
7. Design decisions go to the owner; nothing else waits for the owner.
8. A lesson or decision of the owner goes into this file or `docs/` in a commit, never only into
   a model's memory.
9. Status lives in GitHub labels and issues, not in documents.
10. Until the first playable build, schedule only bugs that break play; the rest are `post-playable`.
11. Undo a scratch edit by writing back the file's saved contents, or commit first; never
    `git checkout`, `git restore` or `git reset` a file with uncommitted work.
11a. Start a long job with `tools/jobs.py start` and checkpoint with `tools/checkpoint.py`
    (process.md §10). Wait on a background job by its PID (`while kill -0 <pid>; do sleep 30; done`) or by the
    final line of its log, never with `pgrep -f`: it matches the waiting shell's own command line,
    so the wait never ends (L48 of the old harness; again in the first cloud session, 2026-10-20).

## Project rules
12. **Evidence tags.** Every behaviour claim in code or docs is tagged `[confirmed]` (cites the
    goal2-archaeology finding(s) and commit it rests on), `[derived]` (follows from confirmed
    claims) or `[designed]` (a choice of this rebuild). A `[designed]` choice that later
    contradicts a finding is a bug.
13. **Engine truth is vendored, never edited.** Files under `goal2/engine/` are copies pinned in
    `PROVENANCE.md`. A defect there goes upstream to goal2-archaeology and arrives here only as a
    deliberate re-vendor that records the new commit.
14. **Everything in the repository, except the original game.** The rebuild's own artifacts are
    committed (a file over ~50 MB goes to a GitHub release). No GOAL2 asset, savestate or
    executable byte enters this public repository or its releases: those live in the owner's
    private Google Drive folder, pulled into the git-ignored `.cache/` with `tools/artifacts.py`
    ([docs/artifacts.md](docs/artifacts.md)).
15. **The fidelity test is the arbiter.** When the rebuild and the vendored model disagree on a
    case the model is seed-exact for, the rebuild is wrong until proven otherwise.
16. **Tests fail before and pass after.** Every new behaviour arrives with the test that visits
    it, and the PR says how the failure was shown. A comment asserting behaviour at an edge comes
    with the test that visits that edge.
