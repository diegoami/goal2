# Bench cue #608

Owner's 2026-11-07 correction: the original stopped bench says “make substitutions now” in blinking green. Its bright green #55ff55 is visible in docs/original-game/images/t156-124-halftime-bench.png; blinking is the owner's statement. Half-second paint phases are a design choice, not an original cadence measurement.

The four new real Qt regressions all fail against parent605 e6cc1b227ca73a527104ef759d6b019e0c8605f0 (`before-v2.log`); `before.log` records the initial three-test baseline. `after-v2.log` passes all four and the existing immediate-bench input controls:18 tests,17 pass and one existing actual-engine UI test excluded as slow under default policy. The cue changes no match commands, pairing, budgets, engine outcomes or publication behavior. The parent's real-engine receipts remain relevant to those unchanged paths.

`cue-on.png` and `cue-off.png` are two actual timer phases of the same offscreen rebuilt bench, with unchanged text/geometry. The accessible label retains its text during the transparent paint phase. Visible, actionable stops blink; hidden/closed screens, ordinary pauses, extra-time view, zero budget and pending edits do not. Confirmed/refused replies restore the cue when another immediate operation is available. `receipt.json` binds sources and images.

`after-v1.log` is retained calibration: its sole failure delivered a second synthetic reply without registering a second edit; the fixture was split into independent confirmed/refused tests in v2. The cue implementation did not change between these runs.

Model: inherited Codex GPT-6 family; exact variant unavailable. No live owner game/profile was modified; this fix is stacked on605 and is not installed yet.
