# T189 milestone validation policy

[designed: owner, 2026-11-07, #606] Full suites run at integrated milestones; PRs use
focused task checks and fast regression CI. The default-scope regression fails before
(default-before.log, one failure among three policy tests) and passes after. The selected
gate/workflow/layout/job regressions pass45 tests (focused-after.log). These are tooling
regressions; no game assertions, cases, seeds, fixtures or time limits were modified.

The full self-hosted workflows remain explicit --slow dispatches, unset an inherited
GOAL2_CASES cap and retain original-file upload guards. No PR/push/weekly full dispatch.

CI additionally caught two older automatic-scope assertions in test_slow_reach_505.
They now exercise the retained explicit --affected mode, keeping the same reached-module,
unrelated-module and missing-base fallback assertions. The expanded focused suite passes54 tests
(focused-reach-after.log). The earlier45-test run missed this module; the old CI failure remains
recorded rather than being described as a pass. No application or game-fidelity tests changed.
The same nine reach tests pass on native Windows (18.007s), using -X utf8 to match CI's
PYTHONUTF8=1; see windows-reach-after.log. The first standalone Windows probe lacked that CI
setting, so source parsing used CP1252 and the graph correctly took its conservative broken-source
fallback; that infrastructure result is not counted as a pass and no graph assertion was relaxed.
