# #643 complete-match selection

[designed: owner-approved #643, T189/T194] Default fast validation excludes the 23 full-match
class/method definitions in `selection.json`. Existing test bodies, cases, original Unicorn
references, fixtures, assertions, seeds and limits are unchanged. Class-level annotations include
T97's quick formatting check because it shares `played_model()` setup with its real-match class.
The original T182 methods carry annotations, so their split discovery wrappers inherit selection.

`test_fast_match_selection_643.Selection` failed before annotation at baseline
`a93b4e3fda3edcfbc845ac0f6ed7f126e46363a6`, reporting actual full-match cases still active in fast
collection; it passes after annotation. It uses real unittest collectors and `requires` slow
selection. Optional dependency/file requirements are modelled as prepared; no TestCase setup,
match, asset byte, or original fixture is executed/read by collection. The collector test itself
requires Qt/SDL/Unicorn imports. The receipt records collection counts and focused policy results.

Reproduce the selection/body checks (no matches):

```sh
python3 -B -m unittest goal2.tests.test_fast_match_selection_643 -v
python3 -B measurements/643/verify_bodies.py
```

`verify_bodies.py` removes exactly the approved new decorator from each target and compares the
entire source AST against its pre-change baseline fingerprint. Existing bodies and all other
class/module definitions therefore remain identical. Re-run it when assessing this change;
future legitimate test-body changes naturally require fresh evidence, not a permanent source lock.

Full integrated Linux and Windows runs still use `check_premerge.py --slow`, with no
`GOAL2_CASES` cap, selecting every existing assertion and case. Changed-behavior focused PR
checks still explicitly include relevant slow tests. This change neither runs nor replaces those
milestone checks. The regular exact-head default gate and hosted checks remain required.

[derived: source inventory] `CompetitiveJobsTests.setUpClass` still generates a genuine knockout
before replay/fault/heartbeat controls. Those controls stay fast; separating their fixture is
outside #643. Partial-match pitch samples and pause/cancel scenarios also remain fast. Existing
40–50 minute hosted timings are not a prediction of elapsed savings; module timings include
concurrent load. No runtime, engine, UI, workflow, cache or task-definition change; the separately authorized heartbeat fixture correction is recorded below.

Model: inherited Codex; exact variant unavailable.

## Main-approved fixture amendment (#639/#642)

Two additional test files correct mechanical fixture blockers seen on the unchanged UI heads.
`Jobs` now kills its dedicated fake wrapper before its child for vanished scenarios. A new child-only
kill control still proves production jobs correctly records `finished`, exit `-9`.
`reproduce_old_job_race.py` forces the old opposite ordering to fail with the original20s deadline;
it touches only new temporary fake jobs. Production `tools/jobs.py` remains byte-identical.

The real competitive heartbeat observation now scopes Windows `timeBeginPeriod(1)` /
`timeEndPeriod(1)` around the original loop. This corrects sleep precision in the test fixture;
Qt's original PreciseTimer1ms,120ms observation, >10beat guard, real polling calls and all
worker/state assertions remain unchanged. Four independent controls check balanced cleanup,
failed setup, responsive poll acceptance and deliberately blocked poll rejection. They run fast,
without the real-match setup used by `CompetitiveJobsTests`.

`verify_fixtures.py` verifies all105 old assertions remain AST-identical and all old functions
remain identical except the two declared kill orders and the precision context around the
unchanged observation. `fixture-identity.json` and `fixture-receipt.json` record this separately
from the23 decorator-only definitions. Run:

```sh
python3 -B measurements/643/verify_fixtures.py
python3 -B -m unittest goal2.tests.test_checkpoints_t149 goal2.tests.test_desktop_competitive_jobs.HeartbeatClockTests -v
```

Final focused selection/policy/fixture run:76PASS in15.817s. Native bundled WindowsCPython3.13.17
and Qt:4clock controlsPASS in0.402s; actual unchanged heartbeat method gives73beats responsive,
1beat blocked. These are controlled clock inputs, not real competitive-worker acceptance.
The current native host's unscoped clock already gave72beats, so it did not reproduce the
hosted32ms sleep fault. The two failed hosted receipts remain before evidence; the native
positive control proves the scoped API and unchanged guard work on Windows. Exact-head main
gate/hosted runs still establish real-worker acceptance. All85 prior controls plus4new clock
controls remain fast. No caching, threshold, deadline, production timer, runtime, UI or engine change.
