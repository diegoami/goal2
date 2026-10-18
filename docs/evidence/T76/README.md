# T76 squad workspace evidence

[designed: T76] The [main preflight](preflight/README.md) and
[concrete acceptance contract](../../design/football-gui/T76-preflight.md)
separate planning mocks from implementation evidence. Original templates/data
remain in ignored local caches; reports record their SHA256 hashes. Screenshots
show rebuilt Qt controls and generated long-name fixtures, without copied game
screens or art.

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
