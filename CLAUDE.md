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

## Working rules
1. The main session plans, triages, talks to the owner and merges. It implements itself or spawns
   a subagent (`.claude/agents/implementer.md`) on its own judgment; the owner names a model only
   when they want a specific one.
2. Work on a branch in the checkout at hand; one task at a time per checkout. No worktrees.
   Locally a task branch `task/T<nn>-<slug>`; in a cloud session the session's own `claude/…`
   branch, for every task of that session (process.md §3). Never `git stash`, never force-push,
   never rewrite `main`.
3. One task, one PR, merged by the main session once its Done-when lines and
   `python3 tools/check_premerge.py --expected-head <sha>` pass: locally
   `gh pr merge <pr> --squash --match-head-commit <sha>`; in a cloud session
   `gh pr merge <pr> --merge --match-head-commit <sha>` (never squash), then
   `git pull --ff-only origin main` on the session branch.
4. Reviews are optional. Per PR, when the risk warrants it (engine, fidelity, vendored model,
   saves, timing), run `tools/review_pr.sh <pr> <opencode|claude|codex> <model>`; any model may
   review. At each milestone, one big independent review: `tools/milestone_review.sh`
   ([docs/milestone-review.md](docs/milestone-review.md)). Relay review findings in full.
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
