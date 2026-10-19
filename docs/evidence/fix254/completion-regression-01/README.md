# Completion preparation regression

[designed: owner, 2026-10-19] The [approved extension](scope-extension.md) adds private completion preparation to existing #254. Result/image/Memory/RNG/history and next-round preparation run on one owned thread after verified engine exit and final-frame consumption. Owner-thread identity/equality/template checks bind the result before and after preparation; owner view validation and the once-only active-state swap remain on the owner thread. Existing synchronous publication callers retain the same validation path and consumed-token behavior.

[confirmed: before.log] On pre-completion source16c169db, seven of eight initial cases fail: gated candidate validation blocks the polling caller; the asynchronous-boundary methods are absent. The candidate-error rollback case already passes.

[confirmed: preparation-edge-before.log] Additional edge checks expose an unprepared-None identity error and a thread-start failure whose error is masked by joining an unstarted thread. Both are corrected, with the original error and ownership cleanup checked.

[confirmed: after.log] The focused implementation passes50 startup/completion/sharing/pitch-transport cases with Python3.12.14. Controlled private candidate work verifies responsive polling, frame-ACK ordering, owner-thread once-only publication, bounded cancellation with retained ownership/retry, stale identity/in-place/template checks, errors and forged/duplicate/unprepared/cancelled candidate rejection. Real original-engine parity and native responsiveness remain separate acceptance requirements.

[designed: implementation] The saved-input preparer retains its Popen-compatible lifecycle reference; terminated children can still be reaped by poll. The completion worker owns no active owner reference. Cancellation invalidates publication before waiting; a live candidate worker retains the job lock and source ownership until bounded cleanup can be retried. No vendored engine, packet/save schema, deadline or strict assertion was relaxed.
