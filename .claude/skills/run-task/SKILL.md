---
name: run-task
description: Run goal2 tasks or fixes end to end on the work branch in the checkout at hand - implement (the main session or the implementer subagent), run the checks, merge (squash locally, merge commit in a cloud session) and report. Main session only.
---

# /run-task [T<nn> | #<issue> ...]

Follow `docs/process.md` §3 for each id in order (none given: the first `status:ready` task in
`docs/tasks/README.md`). For `#<issue>` of a bug labelled `fix`, the issue body is the task file
and the branch is `fix/<issue>-<slug>`.

1. **Check**: Merge-after tasks are merged; each Done-when line fails on `main`. A line that cannot
   be run is amended on `main` first, the reason in the commit.
2. **Implement** on the work branch (process §3: locally `task/T<nn>-<slug>` from `origin/main`;
   in a cloud session the session's own branch, after `git pull --ff-only origin main`):
   yourself, or `Agent(subagent_type: "implementer")` with the task file pasted in
   full and process §4's block (on rework, the review's URL). Label `status:in-progress`. Read the
   subagent's final report before acting.
3. **No per-PR review** (owner, 2026-10-29): go on to the checks. Only when the owner asks for a
   review of this PR, give the prompt (`tools/review_pr.sh <pr> <cli> <model> --print`), never start
   one, and wait for the owner to say it is posted. Relay findings in full;
   rework on the same branch; non-blocking findings become one `T<nn> follow-up` issue
   (`triage:needed`).
4. **Checks**: re-run every Done-when line on the PR head and
   `python3 tools/check_premerge.py --expected-head <sha>` in a clean checkout at that head.
5. **Merge**: locally `gh pr merge <pr> --squash --match-head-commit <reviewed-sha>` and
   `git switch main && git pull`; in a cloud session `gh pr merge <pr> --merge
   --match-head-commit <reviewed-sha>` (never squash, never delete the session branch) and
   `git pull --ff-only origin main`. Label `status:merged`, unblock dependants, report.

Escalate (process §7) with options and a recommendation, and stop. Never weaken a Done-when,
relay part of a review, force-push or rewrite `main`.
