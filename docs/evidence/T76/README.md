# T76 squad workspace evidence

[designed: T76] The [main preflight](preflight/README.md) and
[concrete acceptance contract](../../design/football-gui/T76-preflight.md)
separate planning mocks from implementation evidence. Original templates/data
remain in ignored local caches; reports record their SHA256 hashes. Screenshots
show rebuilt Qt controls and generated long-name fixtures, without copied game
screens or art.

[designed: T76/#233] The [Windows evidence guide](windows/README.md) labels native-01
as cleanup failure evidence despite its historical exit0/reportPASS. The
[cleanup regression proof](cleanup-rework-01/README.md) records the strict
exception/folder assertions and bounded sharing-retry correction. Earlier raw
evidence and source-freeze hashes remain unchanged.

## Preserved failures and corrections

[designed: T76] Evidence is append-only across batches. The first
[Linux report](linux/report.json) and [execution log](linux/first-run.log)
show an input error in the new scenario: Enter on the pre-existing Play button
never started its worker. The scenario now uses a genuine mouse click for Play;
focused Confirm/Discard still use Enter and must actually change/recover drafts.

[designed: T76] [Run03](linux/run-03/report.json) retained the initial scrollbar
coordinate assertion failure. The footer follows viewport resizing and excludes
scrollbar width; the assertion compares coordinates mapped into the same page.
[Run04](linux/run-04/report.json) and its
[2x report](linux/run-04/scale-2/report.json) record the corrected offscreen pass.
Historical centered reading-area captures are partial context, not evidence that
a long area fits in one viewport; later segmented captures cover the full area.

[designed: T76] The retained [management failure](validation-01/management.log)
exposed stretched checkbox centers outside their native clickable text. Restoring
left-aligned tactic widgets made the unchanged
[mouse acceptance pass](validation-01/management-after-fix.log).

[designed: T76] The retained [overview baseline failure](overview-negative-before/execution.log)
and [shell accessibility failure](shell-negative-before/execution.log) occurred
before their intended assertions because historical page fixtures lacked the new
footer interface. The overview helper now restores matching baseline squad
source. The shell helper removes the same exact unique accessibility line from
current page source; it verifies the pinned historical old/fixed pair differs by
only that line and records old/fixed/mutant hashes. The existing defect and
assertion remain unchanged.

[designed: T76] The first native xcb [1x report](linux-native/report.json) passed.
Its [2x report](linux-native/scale-2/report.json) retained a capture traversal
failure: an unnecessary final tiny segment followed a segment that already
covered the reading area's end. Traversal now stops when the area is fully
covered, retaining the40px overlap assertion between necessary segments.

## Complete offscreen coverage

[designed: T76] The [final offscreen1x report](linux/run-05/report.json)
and [2x report](linux/run-05/scale-2/report.json) pass the genuine-input squad
scenario. Each draft checkbox, tactic and captain event compares encoded active
state and saved bytes. Confirm publishes250–260/captain260/all8bits; Discard
recovers confirmed values without changing state/save. Invalid10/12-player and
outside-XI captain inputs are refused. Energy0/status0x88 fixtures demonstrate
unavailable starter removal and reserve refusal. Independent real first-half
worker/substitution/cancellation checks retain captain2561 and no re-entry
without publishing pending state.

[designed: T76] Long-name captures use native contained roster scrolling.
`roster_coverage` records the union of fully visible cells: all twenty names and
all position/raw value/availability fields at each required size. Overlapping
`reading_coverage` segments cover the entire detail/XI/bench reading height;
partial edges in one image are fully readable in its overlapping image.
Reports retain capture/source/resource hashes and prove unchanged source bytes
and complete Qt widget cleanup.

[designed: T76] [Shell1x](shell-after-geometry/interaction.json) and
[Shell2x](shell-after-geometry/scale-2/interaction.json) pass104 real navigation
transitions and retain20 screenshots. The original full bounds, visibility,
accessible-name and Tab assertions apply to every action. A footer descendant is
measured in its actual footer surface, with additional page containment and
viewport non-overlap assertions; other controls retain viewport geometry checks.
The older [failure](validation-02/shell.log) preserves Qt's invalid-parent warnings
and the resulting assertion before this compatibility adjustment. A240px minimum
roster height fits the reduced high-scaling viewport while preserving contained
row scrolling and complete-cell capture coverage.

## Regression and negative-control receipts

[designed: T76] The [serial regression receipt](validation-03/progress.json)
records commands, exit codes, timings and log hashes for the named desktop
model/pool units; existing management/friendlies/pool/halftime proof scripts;
management/pool/halftime Qt acceptance; country selection; accepted tactic
labels; T75 overview1x/2x and its controls; and retained shell controls.

[designed: T76] The [new saved-byte controls](validation-03/squad-negative/negative-controls.json)
show intended assertion failures for baseline hierarchy, captain260 truncation,
premature tactic publication, and starting-XI ID truncation above255. Every
mutated source byte is restored in `finally`, with matching before/after hashes.
The retained management acceptance fails for both captain truncation and eager
publication. Retained halftime fails for captain truncation at its subsequent
play gate; it passes under the eager-tactic mutation. This is actual measured
legacy coverage, not a claim that the legacy halftime script checks per-tactic
isolation. The new squad scenario catches the immediate publication itself.

[designed: T76] The final native Linux [1x report](linux-native-final/report.json)
and [2x report](linux-native-final/scale-2/report.json) pass with xcb in a3840×2160
Xvfb display using checksum-verified task-local libraries. They retain the same
interaction, complete roster/reading coverage, clean Qt exit and unchanged-source
checks as offscreen execution. [Source freeze01](source-freeze-01.json) verifies
both final offscreen and native reports against the exact product/scenario/
dispatcher bytes, before any evidence-only follow-up. SDL is outside this page.

[designed: T76/#233] The [rework serial receipt](validation-04/progress.json)
records17 passing focused/retained/proof/control/scenario groups. Strict
[offscreen1x](linux/run-07/report.json), [offscreen2x](linux/run-07/scale-2/report.json),
[native Linux1x](linux-native-final/run-02/report.json) and
[native Linux2x](linux-native-final/run-02/scale-2/report.json) each record zero
uncaught Qt callbacks, successful sharing retry and unchanged source bytes.
Both normal and injected-sharing Cancel paths assert absent owned folders and
the existing cancellation bound. [Source freeze02](source-freeze-02.json)
anchors all174 product/test/tool files for a separate main-owned Windows attempt.
It preserves, rather than overwrites, the first attempt and its failure evidence.

[designed: T76/#233] [Strict native Windows02](windows/README.md#native02-strict-cleanup-acceptance)
passes on immutable checkpoint `0503407a7e2466054f4b4070515d3e426ccd9942` at
actual1x/2x with61/25 captures and zero callback exceptions/raw tracebacks. The
[independent author audit](windows/native02-author-audit-01.json) verifies all174
frozen source files,95 inventory entries and all four protected hashes. The
original native-01 failure remains unchanged and is not used as clean acceptance.

[designed: T76] Native02 proves strict cleanup, while the later main native
[caption control](caption-rework-01/T76-native-caption-controls.json) exposes
focused footer caption clipping at the minimum2x size. The Windows guide records
that separate readability failure; raw native02 outputs remain historical and
unchanged. Runtime-mock success is feasibility evidence only.

[confirmed: validation-05/README.md] The [composed validation](validation-05/README.md) retains20 passing groups after accepted T78 and the scoped [caption correction](caption-rework-01/README.md). Actual focused/unfocused QStyle content bounds now accompany frame geometry at all supported sizes/scales. [Source freeze03](source-freeze-03.json) pins175 unchanged product/test/tool files for a separate final native attempt. Native02 remains cleanup-only acceptance at its older checkpoint.
