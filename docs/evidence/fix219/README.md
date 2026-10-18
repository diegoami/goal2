# Fix #219 evidence

This test-only fix gives the descendant fixture 800 ms to publish its readiness files while the
capture retains a finite 1200 ms deadline. The deterministic delayed case waits 200 ms before
starting the descendant. Both normal and delayed cases check a real descendant PID, an exited
leader, termination after the capture deadline, bounded settlement, and survival of an unrelated
sentinel. The existing deletion-control mutation still has to fail with the exact
`owned descendant must terminate` assertion.

`failed-before-enoent.log` records the old 100 ms deadline expiring before the delayed fixture
could publish its PID; reading the absent PID file produces the original `ENOENT` failure class.
The main-session planning receipt independently recorded the same 200 ms startup against the old
100 ms deadline. `focused-controls.log` records both the fixed fixture check and the unchanged
substantive deletion controls passing. `full-workflow.log` records all 30 workflow tests passing.
The first full run exceeded the interactive command window and its partial output is retained in
`full-workflow-tool-window-incomplete-01.log`.

`receipt.json` records command outcomes and SHA-256 hashes for the tested source and evidence.
This directory contains text and hashes only; generated process fixtures and scratch data stayed
under the ignored `.cache` directory.
