# Process

[designed: owner, 2026-10-20] How a task runs. The rules are in [CLAUDE.md](../CLAUDE.md). The
earlier, much heavier process (review harness, family rule, worktrees, Jev, lessons register) is
kept on the branch `local`.

## 1. Order of work

1. **Evidence first**: every claim tagged `[confirmed]`, `[derived]` or `[designed]`.
2. **A walking skeleton before the fan-out**, then rules behind its seams, best-evidenced first.
3. **The first playable build**: the UI chain before more rules. Until it ships, only a bug that
   breaks play is scheduled (crash, stall, unwinnable game, save that will not load).
4. **Parallel tracks on more computers.** [designed: owner, 2026-11-03, #509: "we should do this more often"]
   When a plan splits into tracks that touch different repositories or different files, the main session
   offers to run one track on another computer. It writes that session's whole starting prompt into the
   repository (`docs/handover-<date>-<track>.md`: set-up, the track's steps, its reserved task numbers,
   the files each track owns, merging by rebase and `--match-head-commit`, status on the plan's issue), and
   gives the owner a one-line prompt that points at it. The first was m3's Track B
   ([handover-2026-11-03-track-b.md](handover-2026-11-03-track-b.md)).

## 2. Task files

`docs/tasks/T<nn>.md`, from [`TEMPLATE.md`](tasks/TEMPLATE.md), 150–400 words. Before writing
one, `git pull` and take the next free number.
- **Done when**: each line is one check a command can run; it fails on `main` and passes once the
  task is done.
- **Split** a task likely to outlast about an hour of implementation, or one touching more than
  three independently mergeable layers, into tasks that each merge on their own.
- The main session edits task files directly on `main`, the reason in the commit.
- **Finding gaps is the main session's job, not the owner's.** [designed: owner, 2026-11-03: "keep finding gaps,
  it is annoying having to spoonfeed you those"]
  - **Before writing a task**, the main session checks it against the original's workflow. For a screen, its
    Done-when tests every action on the design's *Actions* line, or names the action it leaves out with the
    reason and an issue. It also checks what today's window does for the same step, so nothing working is lost.
  - **Before merging**, the main session walks the player's journey through the merged screens, as the owner
    would. It checks the key bar against the design, and asks whether a player can still do what the original
    lets them do at that step. A gap that breaks play is filed and scheduled before the next task is written.
  - **At each milestone**, before handing the owner a build, it plays the build's path end to end
    (offscreen screenshots, or the capture process) and reports the gaps it found itself.
- **Check the evidence before telling the owner what the original does.** [designed: owner, 2026-11-04: "confidently
  incorrect anyone ?"; #583] A doc's tag is not proof: the main session told the owner the original draws the home
  side light red, repeating `docs/design/ui-2026-11` §3, a claim generalised from one capture (Norway at home, in
  its own red kit). The original computes each country's kit (`0791:1073`). Before answering a question about the
  original's behaviour, open what the claim cites (the finding, the capture, the port), and say how sure the
  evidence is. A claim resting on one capture is a guess about the rule until a second case or the code confirms
  it.

## 3. The loop

`ready → implement → checks → squash merge → follow-ups → report` (a review only at milestones, or when the owner asks)

1. **Check** the task is ready and its Merge-after tasks are merged; run its Done-when lines on
   `main` (they must fail).
2. **Implement** on the work branch (below), in the checkout at hand: the main session itself, or the `implementer` subagent with the brief below.
   Commit and push after each step; open the PR as a draft after the first push.
3. **No per-PR review** (owner, 2026-10-29): the PR goes on to its checks and merges. Only when the
   owner asks for a review of it does the main session write the prompt
   (`tools/review_pr.sh <pr> <cli> <model> --print`); the owner runs it and the reviewer posts one
   comment. Rework goes back to the same branch; non-blocking findings become one `T<nn> follow-up` issue.
4. **Checks** [designed: owner, 2026-11-07]:
   - **Each PR:** run its task-specific focused tests, including the actual slow/fidelity cases that
     establish the changed behavior, then `python3 tools/check_premerge.py --expected-head <sha>`
     in the clean checkout. The default is the fast regression gate: every module's fast tests and
     the cheap layout/reserve slow checks. Hosted Linux/Windows CI and native scaling checks stay required.
     `--batch-fast` is the same scope; `--fast` also disables layout slow checks.
   - **Integrated milestone:** run the complete suite once on Linux and once on Windows, with
     `python3 tools/check_premerge.py --expected-head <candidate> --slow`, all cases, before the
     milestone review/publication. The self-hosted Linux slow and Windows slow workflows are manual
     dispatches for this purpose. PR pushes and weekly-age checks never dispatch full suites.
     Do not run the same full suite again in the hosted workflow as well as the self-hosted one.
   - **After a fix:** rerun affected tests. Repeat a full suite when changed behavior, dependencies,
     fixtures, broad engine/protocol/save changes or a regression invalidate its coverage; record why.
     `--affected` explicitly enables the import-graph slow scope for a justified investigation.
     A new commit SHA or resolving an integration conflict does not itself require a full rerun.
   - **Reuse receipts:** record the original tested SHA, new SHA, platform/runtime, test scope and
     evidence that the exercised application/test code, dependencies and fixtures are unchanged.
     Documentation, measurements and commit ancestry alone do not invalidate a result. For CI/test-tool
     changes, validate that tooling with its focused regressions and retain unaffected game receipts.
     Run clean-checkout, asset-exclusion and link/JSON checks at the new head. A failure still needs a
     fix or the owner's explicit scoped exception; never turn a failed suite into a pass by relabelling it.
   - Optional dependencies/original fixtures may skip with a recorded reason. Prepared milestone runs
     must retain every available case and original reference, memory, event, RNG and publication assertion.
     No assertion, case, seed, time limit or fixture guard is weakened by this scheduling policy.
   - Matches still use the PyPy worker; original Unicorn references stay in CPython. Local Qt/SDL
     tests use `.cache/cloud.env`. The one-local-gate/per-computer rule in §10 remains in force.

   This owner decision supersedes older per-PR full-gate and automatic slow-workflow requirements,
   including active task wording. See [validation.md](validation.md) for commands and receipt scope.
5. **Merge**: locally `gh pr merge <pr> --squash --match-head-commit <reviewed-sha>`, then
   `git switch main && git pull`; in a cloud session
   `gh pr merge <pr> --merge --match-head-commit <reviewed-sha>`, then
   `git pull --ff-only origin main` (a cloud session merges through the REST API: `docs/cloud.md`, "GitHub from a cloud session"). Unblock tasks whose Merge-after are now merged. Report.

**Branches.** [designed: owner, 2026-10-20, as in malpaco cd81d225] Locally, each task has its
own branch, `task/T<nn>-<slug>` (or `fix/<issue>-<slug>`) from `origin/main`, squash-merged. A
cloud session (Claude Code on the web) starts on its own `claude/…` branch and may be able to
push only there, so that branch is the work branch for every task of the session, one PR per
task, first brought level with `git pull --ff-only origin main`. Cloud PRs merge with a merge
commit, never squash: the session branch is then contained in `main`, the next task starts from
it after a fast-forward, and no force-push is ever needed. A PR still open when a session ends is
continued by the next session (check it out and finish it, or continue from it on the new
session's branch).

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

[designed: owner, 2026-10-21; 2026-10-29, as in malpaco] Only milestones mandate a review. A PR
merges on its Done-when lines and checks; a per-PR review runs only when the owner asks for one. No
session starts a review: the main session writes the prompt and the owner runs it on the model they
choose. The milestone review ([milestone-review.md](milestone-review.md)) looks at everything merged
since the last milestone, and its issue lists the PRs merged without a review. A review proves its findings (a command, or a
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

## 9. Autonomous runs

[designed: owner, 2026-10-20] A session may work towards the first release (lane 3 of the
approved queue in `docs/redesign-253/vision-reconciliation.md`) on its own: it takes the queue's
issues in order, writes their task files, implements, checks and merges them without asking. It
stops only for a design decision the documents do not settle (CLAUDE.md rule 7), a Done-when that
would have to weaken, and each milestone: there it opens the milestone issue
([milestone-review.md](milestone-review.md)) and waits for the independent review and the owner's
playtest. Between milestones it merges on checks; a per-PR review only when the owner asks for one.

## 10. Stop and resume

[designed: owner, 2026-10-29, T149] Work can stop at any point and resume from durable state, in
another session, model or computer.
- **Where work stands** is the latest comment on the one open issue labelled `checkpoint`.
  `python3 tools/checkpoint.py --post "<next action>" [--notes FILE]` posts it: each checkout's
  branch, head and dirty count, the open PRs with heads, labels and checks, and the registered long
  jobs, with the next action and any notes. `python3 tools/checkpoint.py` alone prints the snapshot.
  List other checkouts with `--checkout DIR` or `GOAL2_CHECKOUTS`.
- **Checkpoint** before stopping, after a merge, when a long job starts or ends, and when a blocker
  is found. A checkpoint records state, not decisions: those go into the documents (CLAUDE.md rule 8).
- **One local gate at a time per computer.** [designed: main session, 2026-11-03] WSL crashed twice on the owner's
  main computer (21 GB) while two implementers each ran `check_premerge.py`. Each gate plays PyPy matches in
  parallel. With several implementers running, the main session runs their gates one after another.
- **Long jobs** (a gate, a slow study, a native probe) start with
  `python3 tools/jobs.py start <name> -- <command>`. They outlive the session; `list` says whether
  each is running, finished with its exit code, or vanished, and `wait <name>` waits by PID
  (CLAUDE.md rule 11a). Work that takes hours goes to CI instead, in batches under the six-hour job
  limit, each keeping its completed records so a rerun skips what is already verified.
- **Resume**: read the latest checkpoint comment, run `python3 tools/checkpoint.py`, recheck live
  heads and checks, and continue from the next action. A vanished job is rerun, never assumed to have
  passed.
- [designed: owner, 2026-10-29] **Every task is resumable and cut into milestones.** A milestone is a
  durable point: its outputs committed and pushed (anything private, holding original bytes, to the
  owner's Drive with `tools/artifacts.py`, never to git), and a checkpoint comment saying which
  milestone is reached and the next. A long run writes append-only records and has a resume command
  that skips what is recorded, so a crash or a stop loses at most the unit in progress; its records
  are pushed while it runs, not only at the end.

