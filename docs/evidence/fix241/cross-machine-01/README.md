# Player browsing cross-machine validation kit

[confirmed: ../serial-02/receipt.json, validation/premerge-7560.log] Runtime source checkpoint `7560fbc336fa0efd6ea188c3739eb66e6460df63` has all21 serial groups,18 focused tests and clean exact-head premerge passing. All3 browsing controls reject the intended disabled-preview, outer-page-clipped-row and broad-enable mutations, restoring exact saved bytes. Later commits carrying only `docs/evidence/fix241/` preserve this runtime checkpoint; compare all178 archived `goal2` and `tools/desktop-ui` files before native execution. Current task/PR state and complete author run notes belong on [issue241](https://github.com/diegoami/goal2/issues/241) and [PR245](https://github.com/diegoami/goal2/pull/245).

[confirmed: diagnostics/native-02-failed/host-receipt.json, diagnostics/native-geometry.log] Native acceptance has not passed. Windows reported `WinDisc`1024×768. Six active cases produced offscreen captures, then the preview1440×900 request clamped to1028×744; minimum564×331 did not change, and400ms settling/showNormal/move did not resolve it. This evidence supports a missing-display-capacity prerequisite, not a product correction or a waived assertion. The exact native02 receipt is `628ad7166ab6ae5fc0d451609b22b6737197b3837ca6cceeb40d8b69769cd574`; it retains `INCOMPLETE` plus failure, unchanged sources/protected files and empty callbacks. Native01 stopped before source archive/Qt execution and is recorded as `NOT_RUN`.

[designed: #241] The v3 runner, display probe, collector, proof checker and reviewer wrapper are preparation, not accepted executions. Syntax and synthetic validator checks do not establish Windows behavior. `kit/fix241-display-audit-synthetic.json` records only2 valid synthetic inputs and8 rejected synthetic mutants. `*-initial.py` snapshots preserve earlier unexecuted preparation. Older v1/v2 runners and the review template are historical references; use v3 only after the display prerequisite is satisfied. Global window position was not retained by the frozen source helper; audit output states that limit explicitly.

[designed: #241] Every tracked file is in `inventory.json`. Windows CRLF log/JSON bytes are represented losslessly by UTF-8 JSON envelopes containing the original SHA256 and text; adjacent LF files are reading derivatives, with terminal blank lines trimmed where required by strict whitespace checks. The diagnostic `inventory.json` files are exact historical private inventories: reconstruct their `.raw.txt`/CRLF JSON bytes from envelopes when comparing those historical hashes. The package inventory hashes the actual tracked derivatives/envelopes. `validation/historical-reading-normalization.json` records before/after hashes for two earlier diagnostic log reading derivatives; their exact original bytes are retained in this kit. `validation/pre-normalization-whitespace.*` preserves the strict-check failure that exposed them. No line-ending waiver is used.

## Prepare the new computer

[designed: #241] Read repository `AGENTS.md`, `CLAUDE.md`, `docs/process.md`, `docs/environment.md`, this kit and issue241 before resuming. Owner-selected Native Sol Medium and independent MiniMax M3 choices persist for this task; no new task or attributes enhancement is authorized by this kit. Preserve existing worktrees, saves, launchers and unrelated untracked files; never stash/reset/restore/force-push/remove a worktree. Main alone executes Windows, starts the paid review and accepts/merges.

[designed: #241] Fetch the task branch and prepare its isolated worktree beneath the configured worktree root, resolved by the repository helper (run from the checkout):

```bash
node --input-type=module -e 'import {loadConfig,repoPaths} from "./tools/harness/lib/common.mjs"; console.log(repoPaths(loadConfig(process.cwd())))'
python3 docs/evidence/fix241/cross-machine-01/kit/verify-kit.py
```

[designed: #241] Use WSL/Linux for these main/reviewer launch scripts and native Windows Python for the actual Windows child. Restore private verified fixtures and optional runtimes locally using `docs/environment.md` and `docs/watched-kit-acceptance.md`; original resources and saves cannot be recovered from Git. Required fixture hashes are in the proof checker (`e010-r0008-halftime.sav`, `GOAL.DAT`). `runtime-metadata/` records the exact Unicorn2.1.4 and pygame-ce2.5.8 wheel hashes and566 extracted-file hashes, not their bytes. Recreate private `.goal2-validation/.../python-libs` installs, verify every hash and native import, then put updated local directory/native-import paths in ignored `T78-private-runtime-config.json` and `T79-private-runtime-config.json` beneath the main checkout's `.cache/kept/review-receipts/`; keep the expected hashes and versions. Preserve both existing Windows launchers and all saves/data protected by the runner. Do not fabricate missing baseline files or treat a missing fixture/runtime as a passing check.

[designed: #241] Copy the kit scripts into an ignored working directory before adapting them. Keep `windows_display_probe.py`, v3 runner, collector and proof checker colocated. Set these path overrides for v3 (shown as placeholders, replace locally):

```text
GOAL2_ROOT=<main checkout>
GOAL2_TASK_WORKTREE=<isolated fix241 worktree>
GOAL2_WINDOWS_ROOT=<WSL path to existing Windows goal2-exe installation>
GOAL2_RECEIPT_ROOT=<new ignored receipt directory>
GOAL2_VALIDATION_PYTHON=<Linux validation venv python3, for reviewer wrapper>
GOAL2_NODE_BIN=<Node20+ binary directory, for reviewer wrapper>
```

[designed: #241] Export these values explicitly to detached service units; `HARNESS_CLIENT=codex` is required. Historical machine paths elsewhere (especially `stage-review.py`, the review template and runtime metadata) are snapshots/defaults, not portable discoveries: adapt ignored copies to the new main/worktree/fixture/xcb-library/Node/venv paths, using `repoPaths` for the worktree root. Stage the exact grammar dependencies with the documented `npm ci` command. The staging script's `--driver`, `--proof`, `--proof-config`, `--native-original`, `--native-evidence` and `--notes` inputs must refer to locally verified artifacts; never copy credentials or use a sibling review checkout's source. Patch the copied template's executable paths and supply the literal native receipt anchor on `--start`.

## Complete the native gate, then review

[designed: #241] Reconnect/unlock the normal Windows desktop first. Before copying any source archive, v3 requires actual available logical workarea≥1440×900 at scale1 and≥900×640 at scale2, with independent native primary/virtual/workarea pixels and DPI. Previously observed normal physical workarea was2560×1392; verify the current machine instead of assuming that value. Main owns the native launch, detached log and monitoring:

```text
python3 -B <ignored-kit>/fix241-windows-acceptance-v3.py --head 7560fbc336fa0efd6ea188c3739eb66e6460df63
```

[designed: #241] The runner requires current clean/pushed HEAD, ancestry, identical runtime trees and only task-owned evidence carry after that checkpoint. It archives the immutable checkpoint and records it via `--source-head`; never replace the checkpoint or weaken assertions to accommodate packaging commits. v3 measures both display scales before the archive and stable before/after OS/Qt metrics for each run. Keep every failed attempt; do not reuse output directories.

[designed: #241] After both native scales pass, main independently holds the original receipt SHA256 and authorizes collection from the task worktree:

```text
python3 -B <ignored-kit>/fix241-collect-native.py --receipt <original-receipt.json> --expected-receipt-sha256 <literal-main-anchor> --output docs/evidence/fix241/windows/<fresh-attempt> --runner <ignored-kit>/fix241-windows-acceptance-v3.py
```

[designed: #241] The collector binds archive/current/Git source, original and private-copy dependencies, wheels, fixtures, protected launchers/saves, wrappers, probe, raw envelopes, reports and captures. The fresh audit requires the external anchor, correct20/80 source-order IDs for both countries, all16 native cases, complete row-band oracle, state/RNG/save/draft/guard invariants, actual DPR/capture size, sufficient stable Qt/OS workarea, empty callbacks and wrapper cleanup. It accepts only task-owned evidence carry. Audit tampering must fail; no Windows re-execution is attributed to the reviewer.

[designed: #241] After collecting/committing/pushing accepted native evidence, main marks PR245 ready, stages the reviewer checkout and launches the already selected MiniMax M3 review through the harness. The prepared reviewer wrapper supports `--start --expected-receipt-sha256 <literal-main-anchor>`, `--status`, and `--run --expected-receipt-sha256 <literal-main-anchor>`. It owns a systemd unit, Xvfb2880×1800, window manager and private XDG directories with explicit xcb; serially runs the anchored native audit, all21 portable groups/controls, provenance, links, strict whitespace and exact-head premerge. Main audits the complete review, runs required accepted-head checks and alone squash-merges. No paid review or merge is established by this preparation kit.

[confirmed: kit/historical-geometry-diagnostic.py and its raw envelope, diagnostics/native-geometry.log] The retained mock-free geometry script records both countries,80ms resize and400ms settlement, unchanged minimum/hint, and showNormal/move behavior. Its absolute paths describe the failed1024×768 session; adapt an ignored copy to a locally verified immutable archive before any new diagnostic. It is historical diagnosis, not the final native acceptance runner.

[confirmed: validation/premerge-37634b8b-outcome.json] Clean exact-head premerge passed at37634b8b398f9e60e9ad7677999e40cb70a230a0. The final follow-on collection adds only task-owned evidence (this script and completed outcome/log); no long check or native/review execution is claimed for that later evidence-only head. Main still validates the exact final reviewed head before merging.
