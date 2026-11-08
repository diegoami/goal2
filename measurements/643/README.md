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
concurrent load. No runtime, engine, UI, workflow, cache, task-definition or heartbeat change.

Model: inherited Codex; exact variant unavailable.
