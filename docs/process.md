# Process

[designed: owner, 2026-10-20] How a task runs. The rules are in [CLAUDE.md](../CLAUDE.md). The
earlier, much heavier process (review harness, family rule, worktrees, Jev, lessons register) is
kept on the branch `local`.

## 1. Order of work

1. **Evidence first**: every claim tagged `[confirmed]`, `[derived]` or `[designed]`.
2. **A walking skeleton before the fan-out**, then rules behind its seams, best-evidenced first.
3. **The first playable build**: the UI chain before more rules. Until it ships, only a bug that
   breaks play is scheduled (crash, stall, unwinnable game, save that will not load).

## 2. Task files

`docs/tasks/T<nn>.md`, from [`TEMPLATE.md`](tasks/TEMPLATE.md), 150–400 words. Before writing
one, `git pull` and take the next free number.
- **Done when**: each line is one check a command can run; it fails on `main` and passes once the
  task is done.
- **Split** a task likely to outlast about an hour of implementation, or one touching more than
  three independently mergeable layers, into tasks that each merge on their own.
- The main session edits task files directly on `main`, the reason in the commit.

## 3. The loop

`ready → implement → (optional review) → checks → squash merge → follow-ups → report`

1. **Check** the task is ready and its Merge-after tasks are merged; run its Done-when lines on
   `main` (they must fail).
2. **Implement** on `task/T<nn>-<slug>` (or `fix/<issue>-<slug>`) from `origin/main`, in the
   checkout at hand: the main session itself, or the `implementer` subagent with the brief below.
   Commit and push after each step; open the PR as a draft after the first push.
3. **Review, when warranted**: `tools/review_pr.sh <pr> <cli> <model>` posts one review comment.
   Rework goes back to the same branch; non-blocking findings become one `T<nn> follow-up` issue.
4. **Checks**: every Done-when line on the PR head, and
   `python3 tools/check_premerge.py --expected-head <sha>` in a clean checkout at that head
   (`--tests` adds the game test modules; opt-in until #275 makes them skip cleanly).
5. **Merge**: `gh pr merge <pr> --squash --match-head-commit <reviewed-sha>`, then
   `git switch main && git pull`. Unblock tasks whose Merge-after are now merged. Report.

## 4. The implementer brief

The task file pasted in full, then this block (on rework, the review's URL):

```text
You implement <T<nn>>. The task file above is the contract.
- Build only what the task asks for; say why for each changed file.
- A Done-when you cannot meet: stop and report. Never weaken an assertion, skip a test or edit the task file.
- Every new test fails before your change and passes after it; say how you checked.
- Every behaviour claim carries its evidence tag; vendored engine files are never edited; nothing
  of the original game enters the tree (CLAUDE.md rules 12-14).
- Update any document your change makes wrong, in this PR. Never write status into a document.
- Commit and push after each step; after the first push open the PR as a draft.
- PR body: Closes #<issue>; Scope (files and why); each Done-when command with the tail of its
  output; Docs changed.
```

## 5. Reviews

Optional per PR (`tools/review_pr.sh`); the big independent one is at each milestone
([milestone-review.md](milestone-review.md)). A review proves its findings (a command, or a
mutation a test fails on) or labels them unverified. Blocking means a real player or implementer
would hit it through normal use; a theoretical bypass of helper tooling is a follow-up. Before
merging an approval with non-blocking findings, read them: a proven way past what the task
protects is rework.

## 6. Bugs and triage

Bugs and non-blocking findings are filed with `triage:needed`. Triage decides: **fix** (changes no
outcome outside the bug's reproduction; the issue is the contract and its reproduction the
Done-when), **correction task** (changes an outcome), **fold** into a task not yet ready, or
**close** with the reason.

## 7. Escalate to the owner

A design question; a Done-when that would have to weaken; anything destructive (force-push,
rewriting `main`, deleting an issue); a new external dependency.

## 8. Labels

`task`, `bug`, `fix`, `triage:needed`, `post-playable`, `milestone-review`, `review`,
`status:{ready,in-progress,in-review,rework,blocked,escalated,merged}`.
