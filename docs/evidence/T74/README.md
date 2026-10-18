# T74 shell acceptance

[designed: T74] The shell groups the existing controls into five native Qt destinations. Navigation changes page, checked cue, scroll position and heading focus; management handlers, active-state ownership, save policy, controllers and worker/viewer bindings remain in the window and existing backend modules. The country header, status and Cancel match persist across pages.

[derived: source manifest] The production source checkpoint is `bf1846663b4e7ee995120ecbe46a131e9d42cd6e`. [The complete manifest](source-manifest-bf1846663b4e.json) includes every desktop module, all five page modules, the shell scenario and retained helper scripts including `navigation.py`. Subsequent evidence/documentation commits preserve those source bytes. `source-manifest.json` and `source-manifest-final.json` are earlier immutable observations, not the final source identity.

## Shell interaction receipts

[derived: linked interaction reports] Each final shell run uses actual mouse events and Ctrl+1…5, checks heading focus and selected cue, and compares encoded active state, dirty draft, preview/saved active draft, save bytes/path, pending ownership and starts across Quick/competitive/watched controllers. Navigation starts zero jobs. Actual country-key preview/return restores the dirty draft; Ctrl+S remains guarded during preview/pending probes. Every action has an accessible name and is reachable through Tab and content scrolling. Target captures cover all five destinations at 1440×900,1050×780,900×700 at ratio1 and900×640 at ratio2.

| Runtime | Authoritative receipt | Result |
| --- | --- | --- |
| [derived] Linux Qt offscreen | [100%](linux/run-11/interaction.json), [200%](linux/run-11/scale-2/interaction.json), [full log](linux-11.log) | Actual ratios1/2;62/42 transitions;15/5 target captures |
| [derived] Linux Qt xcb on DISPLAY=:0 | [100%](linux-xcb/run-07/interaction.json), [200%](linux-xcb/run-07/scale-2/interaction.json), [full log](linux-xcb-07.log) | Actual ratios1/2;62/42 transitions;15/5 target captures |
| [derived] Native Windows Qt | [100%](windows/final/evidence/scale-1/interaction.json), [200%](windows/final/evidence/scale-2/interaction.json), [audited receipt](windows/final/receipt.json) | Actual ratios1/2; source/resource/capture/protected-file hashes audited |

[derived: final interaction reports] Linux uses Python3.12.14/Qt6.12.0. Native Windows uses Windows-11-10.0.26200-SP0, Python3.13.15/Qt6.12.0; the native reports record actual available screen geometry and device ratio. The ratio2 Windows viewport is900×640 logical pixels. SDL is not involved in shell navigation; the retained original friendly integration below separately exercises SDL.

[derived: native surface measurements] Actual country-popup text/selection, path selection, disabled action/table, table/header and inherited competition-dialog surfaces meet4.5:1 text contrast. Selected-hover pixels retain readable accent/ink. Focus and control boundary token pairs meet3:1. The proposed divider `#507365` measured2.855:1 against the panel, so the implementation uses `#5a7c6e` at3.258:1. No original asset files or personal saves are included in this evidence.

[designed: acceptance setup] The default scenario orchestrator imports no Qt and runs separate, fully exited processes for ratios1 and2. `--single-scale` uses the caller's native scaling environment, set before Qt import. QtTest widget events do not perform the OS click-to-activate step, so navigation checks a bounded own-window activation precondition before dispatching the unchanged real event. The navigation helper never sets page/heading focus. Popup input uses a measured native focus-settle and100ms key spacing, actual Escape, and visible/hidden/native-active assertions.

```sh
# Use the prepared Python/Qt environment and a physical worktree .cache/tmp as TMPDIR.
QT_QPA_PLATFORM=offscreen python3 tools/desktop-ui/redesign.py --scenario shell --template .cache/e010-r0008-halftime.sav --data .cache/GOAL.DAT --evidence-dir docs/evidence/T74/linux
QT_QPA_PLATFORM=xcb DISPLAY=:0 python3 tools/desktop-ui/redesign.py --scenario shell --template .cache/e010-r0008-halftime.sav --data .cache/GOAL.DAT --evidence-dir docs/evidence/T74/linux-xcb
# Native Windows wrapper sets QT_SCALE_FACTOR=1/2 and QT_QPA_PLATFORM=windows inside Windows before Qt imports.
python tools/desktop-ui/redesign.py --scenario shell --template .cache/e010-r0008-halftime.sav --data .cache/GOAL.DAT --evidence-dir <unique-native-output> --single-scale
```

## Behavioral negative controls

[derived: negative06] [The receipt](negative-06/negative-controls.json) and [full output](negative-06.log) prove four intended assertion failures: accepted08e baseline lacks navigation; page-refresh navigation discards the dirty draft; saved6eaa style fails actual native surface contrast; saved154b page composition leaves table accessible names empty. Complete window/style/pages bytes are restored in finally and the before/after hashes agree. No import failure, timeout or missing executable counts as a negative.

```sh
# Exclusive: no other source readers. Choose a new evidence directory; prior outputs are never overwritten.
QT_QPA_PLATFORM=offscreen python3 tools/desktop-ui/redesign.py --scenario shell --template .cache/e010-r0008-halftime.sav --data .cache/GOAL.DAT --evidence-dir docs/evidence/T74/reproduced-negative-unique --negative-controls
```

## Retained behavior

[derived: retained logs] [27 unit cases and nine Qt scenarios](regression-01/commands.json) pass model/entry/pool/Quick/halftime plus management/launch/worker/friendlies/pool/halftime/country-preview/tactics/standings assertions. [The final two-row halftime container](halftime-final-01.log) passes the real pause/substitution/continue/save/cancel scenario. Later changes only affect surfaces, accessible names and the acceptance input setup; game/model/engine/worker modules are unchanged.

[derived: retained proofs] Existing management8/friendlies7/pool6/halftime13 mutation suites pass their original assertion oracles: [management receipt](retained-proofs-01/receipt.json), [remaining receipts](retained-proofs-02/receipt.json). The original friendlies proof fails its stale source-site lookup; pool/halftime hardcode a departed `/tmp` interpreter. The main-session-approved setup adapters replace only that interpreter path and update the one-in-flight mutation site to the accepted expanded busy/match_pending guard, still bypassing the same guard. [The reproducible adapter](run-retained-proofs.py) leaves proof and production sources unchanged after each run.

```sh
# Exclusive, with verified fixture caches; creates a new retained output directory.
python3 docs/evidence/T74/run-retained-proofs.py --evidence-dir docs/evidence/T74/reproduced-proofs-unique
python3 -m unittest goal2.tests.test_desktop_model goal2.tests.test_desktop_entry goal2.tests.test_desktop_pool goal2.tests.test_desktop_quick_jobs goal2.tests.test_campaign_substitutions -v
```

[derived: original integration] [The complete command receipt](original-regression-01/commands.json) records13 competitive unit tests, real qualifier/tied-knockout Qt play, watched Qt repeat/save/resume, and real Qt/SDL animated friendly completion with canonical result/Memory/both seeds and failure/teardown boundaries. New rebuild artifacts are copied under that directory; generated originals under the old task evidence paths are retained untracked. [Seven pitch tests](pitch-unit-controls-01.log) include [five saved-byte pixel/lifecycle controls](pitch-saved-byte-controls-01/receipt.json). These source-controlled experiments ended before surface mutations began.

```sh
python3 -m unittest goal2.tests.test_desktop_competitive_jobs -v
QT_QPA_PLATFORM=offscreen python3 tools/desktop-ui/competitive_play.py
QT_QPA_PLATFORM=offscreen SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy python3 tools/desktop-ui/watched.py
QT_QPA_PLATFORM=offscreen SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy python3 tools/desktop-ui/animated-pitch.py
QT_QPA_PLATFORM=offscreen SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy python3 -m unittest goal2.tests.test_pygame_pitch_view -v
```

## Preserved attempts

[derived: retained observations] Earlier Linux attempt directories/logs retain checkbox hit-region setup failure, the discovered table Tab trap, incomplete table-reveal geometry, native activation failures and the surface fail-before evidence. `focus-paired-04/interaction.json` records the decisive focus=null/activeWindow=null failure before adding the native activation precondition. The native assertions remain unchanged after correcting setup.

[derived: native attempt receipts] Windows `preliminary-01` is pre-surface-fix100% appPASS followed by a collector backslash-normalization failure, with no200% result. `preliminary-02` refused a tracked-doc-clean precondition before staging. `preliminary-03` failed the immediate popup-input setup before measuring contrast. The [diagnostics](windows/diagnostics/) compare immediate key/mouse input with the successful delayed real key input; they are not final DW2 acceptance. Final Windows acceptance is exclusively the audited `windows/final` pair above. Protected Windows launcher/save hashes remain unchanged; only generated temporary saves and isolated validation copies are used.

[designed: exact-head validation] Commit all intended receipts before running `python3 tools/check_premerge.py --expected-head <full-ready-head>` in the tracked-clean task worktree. The immutable check's ignored full log/hash is recorded in the PR, avoiding an evidence-only head change after the check. Main owns independent review and exact-head merge.

## Postapproval diagnostic rework

[derived: postapproval-diagnostic-01] Main's exact82def postapproval native pair passed100% but failed the final surface ownership equality at200%. The old assertion did not retain the changed field, so the original component/root cause remains unresolved. The unchanged-source runtime-only200% probe and one instrumented100%→200% pair then passed with empty12-field deltas; the1x trace observed temporary native deactivation after path selection. This observation does not establish the cause of the original failure. [The preserved failure and probes](postapproval-diagnostic-01/copy-manifest.json) retain original82def source identities, logs, reports, rebuild captures and the runtime-only loader.

[designed: diagnostic rework] Only the shell acceptance helper changes. Its original snapshot remains before all surface input, and the final full12-field equality remains. Every surface step now records named deltas, native activity, focused object and country, then rejects any ownership change immediately. Before country Alt+Down and path Ctrl+A the helper establishes and asserts actual own-window activation and target focus; before Escape the popup must own input. It never restores game/draft/preview/path values or recaptures the baseline. These are stronger setup checks and failure locators, not proof that the unreproduced original cause was fixed.

[derived: surface-input-controls-01] A deliberately wrong target focus fails the intended input precondition before dispatch. A real plain country Down key fails the step ownership assertion with draft, active_draft, preview_identity and encoded_preview deltas; save/job fields remain unchanged. Both control outputs/reports are retained. Reproduce in fresh native processes (each command must fail its named assertion):

```sh
QT_QPA_PLATFORM=xcb DISPLAY=:0 python3 tools/desktop-ui/redesign.py --scenario shell --template .cache/e010-r0008-halftime.sav --data .cache/GOAL.DAT --evidence-dir <new-output> --single-scale --surface-input-control wrong-focus
QT_QPA_PLATFORM=xcb DISPLAY=:0 python3 tools/desktop-ui/redesign.py --scenario shell --template .cache/e010-r0008-halftime.sav --data .cache/GOAL.DAT --evidence-dir <new-output> --single-scale --surface-input-control country-change
```

[derived: prior independent review] The full23-group independent approval at82def and main's postapproval failure are preserved in PR223's review history. Backend/game/worker/product Qt source bytes remain unchanged; that prior backend proof retains its actual82def identity. New helper-focused Linux/native Windows acceptance and same-reviewer reassessment are required for this rework.

[derived: input rework receipts] The new helper passes [native xcb1/2](input-xcb-01/interaction.json) and [offscreen1/2](input-offscreen-01/interaction.json), with62/42 transitions,15/5 target captures and empty per-step ownership deltas. Scale2 reports are in each `scale-2` directory. [The new inventory](source-manifest-input-rework-01.json) records the changed scenario and27 unchanged prior source files. Earlier source manifests remain immutable; their scenario hash describes the prior acceptance helper.

```sh
# Automatically requires both intended failures and verifies save/job fields unchanged.
QT_QPA_PLATFORM=offscreen python3 docs/evidence/T74/run-surface-input-controls.py --evidence-dir <new-owned-output>
```

[derived: input-negative-01 and surface-input-controls-02] All four original saved-byte controls still fail their unchanged intended oracles with exact restoration. The repeatable input-control runner passes both intended failures and exact country-change delta fields. [Serial full log](input-controls-final-01.log). New native Windows validation remains pending at this checkpoint.

[derived: Windows input-rework-final] Fresh native Windows validation at65b20f5 passes actual ratios1/2,62/42 transitions and15/5 target captures in41.564/31.036seconds. All eight per-step traces and the final12-field delta are empty. [Audited receipt](windows/input-rework-final/receipt.json), logs, wrappers and26 rebuild artifacts are collected byte-exact;157 archived source hashes match current bytes, and four protected launcher/save/resource hashes are unchanged. This pair is the authoritative Windows acceptance for the changed helper; older `windows/final` remains valid historical product-source evidence, not the reworked helper identity.

[derived: input-management-units-01.log] Fresh27 model/entry/pool/Quick/halftime tests pass after the helper rework. No product source changes require repeating the prior actual82def backend proof groups; their identities and original logs remain explicit. Final author exact-head premerge is recorded in the PR after this evidence commit.
