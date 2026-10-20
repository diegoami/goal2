---
name: run-task
description: Run goal2 tasks or fixes end to end on a task branch in the checkout at hand - implement (the main session or the implementer subagent), optionally review with tools/review_pr.sh, run the checks, squash-merge and report. Main session only.
---

# /run-task [T<nn> | #<issue> ...]

Follow `docs/process.md` §3 for each id in order (none given: the first `status:ready` task in
`docs/tasks/README.md`). For `#<issue>` of a bug labelled `fix`, the issue body is the task file
and the branch is `fix/<issue>-<slug>`.

1. **Check**: Merge-after tasks are merged; each Done-when line fails on `main`. A line that cannot
   be run is amended on `main` first, the reason in the commit.
2. **Implement**: yourself, or `Agent(subagent_type: "implementer")` with the task file pasted in
   full and process §4's block (on rework, the review's URL). Label `status:in-progress`. Read the
   subagent's final report before acting.
3. **Review, when warranted** (engine, fidelity, vendored model, saves, timing, or the owner asks):
   `tools/review_pr.sh <pr> <opencode|claude|codex> <model>`, any model. Relay findings in full;
   rework on the same branch; non-blocking findings become one `T<nn> follow-up` issue
   (`triage:needed`).
4. **Checks**: re-run every Done-when line on the PR head and
   `python3 tools/check_premerge.py --expected-head <sha>` in a clean checkout at that head.
5. **Merge**: `gh pr merge <pr> --squash --match-head-commit <reviewed-sha>`, label
   `status:merged`, `git switch main && git pull`, unblock dependants, report.

Escalate (process §7) with options and a recommendation, and stop. Never weaken a Done-when,
relay part of a review, force-push or rewrite `main`.
