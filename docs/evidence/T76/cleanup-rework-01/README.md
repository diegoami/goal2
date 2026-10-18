# #233 cleanup regression proof

[designed: T76/#233] Main's [contract amendment](../../../design/football-gui/T76-preflight.md)
authorizes one mechanical production change in `goal2/desktop/jobs.py`, supporting
lifecycle regressions and strict squad-scenario exception/folder checks. Worker
invocation, dependencies, model/state/save/publication and existing two-second
cancellation bounds are retained.

[designed: T76/#233] The [initial fail-before run](unit-fail-before.log) executes
four new lifecycle methods against old cleanup and fails six behavioral
assertions: transient32 was not retried, cleanup failure lost process ownership,
and a process-less pending folder could not be retried. The
[final-test proof](final-tests-old-module.json) runs the final exact test source
against the verbatim frozen cleanup module in an isolated process, without
mutating a source file. Its [full log](final-tests-old-module.log) again contains
six assertion failures and no setup/test errors. The
[reproduction script](verify-old-cleanup.py) records the source/test hashes and
frozen code identity.

[designed: T76/#233] The [real Qt fail-before report](scenario-fail-before/report.json)
and [full log](scenario-fail-before.log) run the strengthened scenario with old
cleanup. A second real pending halftime worker's owned-folder cleanup raises a
single simulated Windows sharing violation. Qt sends the exception through the
scoped `sys.excepthook`; the scenario now fails rather than accepting exit0 and
state-only cancellation. The first worker still exercises ordinary unmodified
cleanup. Every successful Cancel must leave no owned worker folder.

[designed: T76/#233] The [focused pass-after log](unit-final-pass.log) records29
passing quick-job/substitution/model/pool tests. A fake monotonic clock proves
sharing retries stop by0.5seconds and no retry starts at/after the deadline.
Transient32 succeeds; permanent32 and nonsharing errors propagate and retain
ownership; a subsequent Cancel retries cleanup, including after launch failure
without a process. Complete encoded state and saved bytes remain unchanged.
Only `PermissionError.winerror ==32` from the owned folder cleanup is retried.

[designed: T76/#233] [Linux run06](../linux/run-06/report.json) and
[2x](../linux/run-06/scale-2/report.json) pass both ordinary and injected-transient
real worker cancellation with zero callback exceptions, absent owned folders,
unchanged source/state/save, and the retained roster/detail/focus assertions.
The later process-less start guard refinement is separately covered by the final
validation batch; these earlier source hashes are retained rather than rewritten.
