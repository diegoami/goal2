# Startup fixture correction

[confirmed: fixture-before.log] Main identified a coverage gap in the prior
sharing-test fixture: replacing watched.sys with only platform removed executable.
The launch and engine startup subcases passed on cleanup denial after an unrelated
AttributeError, before their intended Popen/engine.start failures. New exact-error
context assertions fail on exactly these two subcases before the mock correction.
Earlier nominal-green logs remain preserved; their launch/engine startup coverage
claim is superseded by this batch. No native fixed-source gate had run at4d6adec2.

[confirmed: sharing-before.log, sharing-after-restoration.log,
baseline-restoration.json] The mock now copies real sys attributes and overrides
only platform. Each partial-startup subcase verifies the exact intended injected
OSError, ordered open attempts and allocated-handle counts, folder allocation,
Popen call/default command and engine.start reachability. All13 corrected tests
fail against accepted pre-fix product77b28447 without setup/import red, then pass
on the unchanged fix. Exact product bytes were restored in finally.

[confirmed: ../author-rework-mutations-01/receipt.json and complete logs] Three
serial broader-error mutations still fail strict propagation assertions; saved
product bytes were restored exactly before runtime validation.

[confirmed: source-carry.json] All257 product, runtime-test/helper and config
files other than this sharing-test module are exact4d6adec2 bytes. The prior53-test
Linux genuine-runtime run remains valid for those unchanged paths. Fresh focused
sharing/import-context/original Qt acceptance is recorded separately in this batch.

[confirmed: premerge-prior-freeze.log, premerge-wrong-sha-refusal.log] The prior
clean4d6adec2 freeze passed75protected hashes and exact-head offline premerge.
The earlier incorrectly copied fullSHA refusal is preserved distinctly; no checks
ran on that invalid invocation and it is not acceptance evidence.
