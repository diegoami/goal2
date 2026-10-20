# Running notes — `RUN-NOTES.md`

> [designed: owner, 2026-10-20] Worktrees are no longer required: read "worktree" below as the
> checkout the implementer works in (CLAUDE.md "Cloud-viable workflow").

> A per-worktree file where the implementer tracks its own progress in real time. If a
> run is interrupted (wall clock, process kill, orphan collision, owner intervention),
> the next implementer reads this file as the authoritative handoff.

## File

- **Path**: `RUN-NOTES.md` at the worktree root.
- **Git**: per-worktree ignored (`.git/info/exclude`). Never committed to any branch.
- **Created**: by the agent on its first step (Plan section filled in; Progress and
  Notes empty until the agent appends).

## Sections

```
# RUN-NOTES — <task id>

## Plan
1. <step one>
2. <step two>
3. ...

## Progress
- <timestamp> <one-line: what was done>

## Notes
- <timestamp> <one-line: anything the next session needs>

## END
- last commit: <sha>
- PR state: <open / draft / ready / merged>
- deferred: <bullet or "none">
```

Three live sections + one terminal block:

- **Plan** — what the agent intended to do. Written once at the start, from the brief's
  step list. Not edited after.
- **Progress** — what the agent actually did. Append a `## <step>` bullet after each
  commit (or after each meaningful tool-call cluster). Append-only.
- **Notes** — abandoned approaches, decisions made, surprise findings, blockers hit.
  Append-only.
- **END** — the last block the agent writes, before `git -C <worktree> checkout --detach`
  on exit. Last commit hash, current PR state, what's deferred.

## Implementer's three rules

1. **Read it first.** At the start of every run, `cat RUN-NOTES.md` at the worktree root.
   If it exists (a previous round left it), read it in full before anything else. It
   carries the design rationale and the deferred TODO.
2. **Append, don't rewrite.** After every commit (or every meaningful tool-call cluster),
   append a `## <step>` bullet to **Progress**. Never edit earlier entries. **Never
   `git add` or `git commit` `RUN-NOTES.md`** even if it ends up tracked.
3. **Final state on exit.** Before the agent exits (or before any detached `git
   checkout`), append a `## END` line to **Notes**: last commit hash, current PR state,
   what's deferred for the next round.
4. **Verify the ignore, don't write it.** On first touch, run `git check-ignore -q
   RUN-NOTES.md`. If the exit code is `1` (NOT ignored), **stop and report**: the
   main session is responsible for keeping `RUN-NOTES.md` in the shared exclude
   (`<main-checkout>/.git/info/exclude`). Do NOT attempt to write to `.git/info/exclude`
   from inside a worktree — there, `.git` is a *file* (`gitdir: <main-checkout>/.git/
   worktrees/<name>`), not a directory, and the write lands outside your worktree, where
   OpenCode will reject it. The check is what matters; the rule is what enforces it.

## Reviewer's one rule

Read the implementer's **RUN-NOTES.md content** from the **review brief**, not the
worktree. The reviewer runs in a fresh checkout of the PR head, where `RUN-NOTES.md`
is **untracked** (git-ignored) and **does not exist**. The main session pastes the
implementer's notes into the review brief before dispatch. They tell you the design
rationale and the deferred items — the review grades against the *design* (and against
the implementer's account of what was tried), not just the final diff.

## Why this concretely helps

- **Implementer interrupted by wall clock / orphan / process kill** — the next round
  reads `RUN-NOTES.md` and knows exactly what was tried, what landed, and what didn't.
- **Long implementer run** — anyone with read access can `cat RUN-NOTES.md` mid-run to
  see where it's stuck (alternative to reading the live opencode db).
- **Reviewer context loss** — the reviewer's first read is the **review-brief's
  pasted RUN-NOTES.md** (set up by the main session). The reviewer grades against the
  design rationale and the deferred items the implementer surfaced — the same reasons
  as before; the path the content travels is different (brief, not worktree).

## Main-session responsibilities (the bits the agent does NOT do)

The agent is in a worktree and cannot write to the shared exclude. Two things must be
done **by the main session** before the dispatcher calls the harness:

1. **Ensure the shared exclude has `RUN-NOTES.md`.** On the **main checkout** (not a
   worktree), run once per repo:

   ```bash
   printf 'RUN-NOTES.md\n' >> <repo>/.git/info/exclude
   ```

   Verify with `git check-ignore -q RUN-NOTES.md` from any worktree. This protects
   every worktree simultaneously, because the shared exclude applies to all worktrees
   in the repo.

2. **Paste the implementer's RUN-NOTES.md into the reviewer brief.** When dispatching
   the reviewer, the main session reads `RUN-NOTES.md` from the implementer's worktree
   and embeds its content in the reviewer brief (under a labelled heading, e.g.
   "Implementer's notes"). The reviewer reads the design rationale and the deferred
   items from there — not from a `RUN-NOTES.md` it cannot see in its fresh checkout.

   If the file is empty / absent at dispatch time, the review brief says so explicitly
   ("no notes from the implementer were recovered") so the reviewer is not misled.

## Hazards

- **Append-only.** A `Progress` entry that turned out wrong gets a new entry saying
  "the previous approach was reverted because X" — never an edit.
- **Never `git add` / `git commit`** the file, even if it ends up in `git status`. The
  `.git/info/exclude` line keeps it out; the rule keeps it from being staged by
  accident.
- **Per-worktree ignore** — the shared exclude at `<repo>/.git/info/exclude`
  applies to all worktrees in the repo. Adding it once on the main checkout (by the
  main session) protects every worktree. The agent **never** writes
  `.git/info/exclude` from inside a worktree — there, `.git` is a *file*, not a
  directory, and OpenCode would reject the write as outside the worktree. The
  agent's rule is to *verify* (with `git check-ignore -q RUN-NOTES.md`) and *stop
  and report* if the exit code is `1`.
- **Don't put the file in the PR body.** The PR carries the *result*; the notes file
  carries the *narrative of getting there*. Mixing them bloats PR bodies. The
  review brief is the right place for the notes — the main session pastes them
  in before dispatching the reviewer (see "Main-session responsibilities" above).
