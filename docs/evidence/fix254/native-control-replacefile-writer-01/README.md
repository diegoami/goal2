# Prior writer candidate fails concurrent regression

[confirmed: report.json] Replacing only the writer with its prior ReplaceFileW candidate from25096176d11f18fb0b96a32bcbb558de96246cbe passes all three held-reader cases, then fails normal actual-controller concurrent polling after633polls with the unchanged missing-status startup refusal. The owned writer is reaped. This demonstrates why held-reader success alone was insufficient; it is not UI acceptance.

[confirmed: host-receipt.json] Mutation is confined to an owned native archive. Current task source and all6protected files remain unchanged. The exact mutation launcher is retained and bound by runner_sha256.
