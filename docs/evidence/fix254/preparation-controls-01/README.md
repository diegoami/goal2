# Preparation and ownership mutation controls

[confirmed: saved-byte execution reports and intended rejection logs] All13controls reject: four startup mutations, six completion/lifecycle mutations and the existing three native-handle ownership deletions. Every source byte is restored before the next control. These are controlled Linux tests, not native Windows execution or independent review.

[confirmed: startup/report.json] Synchronous encoding, discarded live input preparation, allowing a cancelled preparer to launch, and premature release before cleanup each fail the targeted startup assertion.

[confirmed: completion/report.json] Synchronous candidate validation, missing owner recheck, discarded live candidate preparation, a forged candidate, a terminated child that cannot be reaped by poll, and bypassing final-frame ACK each fail their specific regression.

[confirmed: ownership/report.json] Dropping raw-handle, descriptor or rename-handle cleanup fails the existing acquired-handle ownership assertions. The original sharing/error/deadline/packet behavior remains separately tested.
