# Native metadata comparison

[confirmed: initial-native.log] The initial diagnostic child imported the wrong source checkout and failed before measurement; this harness failure is preserved. The corrected child explicitly uses and verifies the archived native source directory.

[confirmed: corrected-report.json] During real first creation and replacement, holding the real writer rename handle open leaves Path.exists/stat and shared native reads successful. The actual controller also validates the packet and retains pending state without publication. All writer/read handles close and6protected hashes remain unchanged. This does not reproduce the full run’s transient missing-status result, so no metadata-cause claim or product edit follows from it.
