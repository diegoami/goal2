# T65 evidence scope

[designed: T65] The product source is pinned by
[resources-and-source.json](resources-and-source.json), including accepted main,
accepted kit source, all supplied resource SHA-256 values, diagnostic inputs and
implementation file hashes. Only hashes/metadata are tracked; original bytes stay
in ignored local caches. Validation ran on Linux under WSL2, not native Windows.

[designed] [acceptance-final-b8232e1.log](acceptance-final-b8232e1.log) records the
13-test focused suite at fixed product commit
`b8232e159bc58e04b0ad951a253ef0539fa27982`: PASS13/97.897s. Normal seed257 and
known-injury seed70 match the full synchronous result, every event, complete
Memory and both seeds. Reported timings are poll-to-publication elapsed after
start returns, measured with another regression run active; no hardware deadline
is asserted. The separate 600-second real-run guard detects hangs only.

[designed] [controls-v2/controls.json](controls-v2/controls.json) and its logs are
the accepted nine intended assertion-failure controls. They require `FAIL:` and
reject `ERROR:`, module absence and timeout. The later
[burst-buffer control](control-burst-buffer-v1.log) adds a direct buffer-limit
assertion failure when queued-frame drainage is removed; its positive test is
[burst-01.log](burst-01.log). The control script saves each source file's complete
bytes and restores them in `finally`. It creates a new output directory and will
not overwrite an existing receipt:

```bash
python3 docs/evidence/T65/negative_controls.py .cache/T65-controls-new-run
```

[designed] Root [controls.json](controls.json) and root `control-*.log` are
historical diagnostic receipts, not the accepted assertion-control report. In
particular, the root bounded-read receipt ended in an `ERROR` caused by its exited
fixture child, so its old `behavioral_failure: true` field is not accepted proof
of the read-bound assertion. The v2 fixture mocks only process liveness and fails
`1 != 0` directly when the read bound is removed. The v2 stream mutation changes
a non-tail event, allowing wrong transcript publication if comparison is removed.
The historical launch-cleanup log omits an original-state repr, records its raw
SHA-256 and retains the full raw bytes only in the ignored local cache. The test
now prints a safe assertion message; the runner rejects oversized repr output.

[designed] `attempt-01-json.log` and `attempt-02-compressed.log` preserve failed
implementation attempts; `acceptance-03.log` is the earlier PASS11 result. These
are not substituted for the final 13-test result. `lifecycle-extra.log` separately
records the SIGTERM-ignoring child and no-UI/optional-runtime import checks.

[designed] [premerge-b8232e1.log](premerge-b8232e1.log) certifies its named clean
pushed implementation SHA before the evidence-only commit. Final-head premerge
is recorded on the PR to avoid changing the SHA it certifies. Links/provenance
outputs are [links-01.log](links-01.log) and [provenance-01.log](provenance-01.log).

[designed] [regressions-started-37aa2d1.log](regressions-started-37aa2d1.log)
records PASS60/1585.808s for the nine-module retained command. It started with
`37aa2d1` source loaded by the parent; the narrow queued-frame read guard was added
and controlled during that run. This is earlier-source regression evidence, not a
fresh exact-final-head full-suite run. The final focused suite tests the fixed
bridge guard separately; independent review runs all nine modules freshly.

[designed] After every validation reader exited, a test-only addition visits the
32 MiB decoder boundary, oversized output, truncated compression and trailing
payload. The final test count is fourteen. The earlier thirteen-test receipt and
its source/test-file hashes remain immutable; a new final receipt records the
updated test hash. Product files remain byte-identical to `b8232e1`.

[designed] [acceptance-final-a0b4e55.log](acceptance-final-a0b4e55.log) is the final
fourteen-test focused result: PASS14/113.578s, zero skips. It supersedes the earlier
thirteen-test receipt as final focused evidence. Then, with no other validation
readers, [controls-final/controls.json](controls-final/controls.json) records all
eleven intended assertion failures, including the buffer-drain and Memory-limit
controls. The updated test/source hashes, exact commands and source scopes are in
[final-source-and-validation.json](final-source-and-validation.json). Every saved
product file was restored and verified byte-identical to the original source
receipt after the controls. Final-head premerge is posted to PR185 after the
last evidence-only commit.
