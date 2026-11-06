# T189 milestone validation policy

[designed: owner, 2026-11-07, #606] Full suites run at integrated milestones; PRs use
focused task checks and fast regression CI. The default-scope regression fails before
(default-before.log, one failure among three policy tests) and passes after. The selected
gate/workflow/layout/job regressions pass45 tests (focused-after.log). These are tooling
regressions; no game assertions, cases, seeds, fixtures or time limits were modified.

The full self-hosted workflows remain explicit --slow dispatches, unset an inherited
GOAL2_CASES cap and retain original-file upload guards. No PR/push/weekly full dispatch.
