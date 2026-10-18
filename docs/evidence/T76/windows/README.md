# T76 native Windows evidence

[designed: T76/#233] `native-01` preserves the exact main-owned implementation
attempt at frozen checkpoint `3a76a704864fadee0a92a298af3a8a4d0072b1fa`.
Its [host receipt](native-01/host-receipt.json) has SHA256
`cfb682bf444ee2a1ab920052e221df2206775f14c619da879a13e96403748182`.
The unchanged [inventory](native-01/inventory.json) records95 collected files.
Actual Windows11 build10.0.26200, Python3.13.15 and Qt6.12.0 ran at ratios1.0/2.0,
with61/25 screenshots and47.997s/56.984s elapsed. All four existing protected
launcher/save/resource hashes match before/after. These metadata and capture
hashes were independently verified against main's retained original receipt.

[designed: T76/#233] This attempt is **cleanup failure evidence**, despite its
historical exit0/reportPASS. Both full [1x log](native-01/native-1.log) and
[2x log](native-01/native-2.log) contain an uncaught Qt-slot WinError32 while Cancel
removed an owned worker folder. The earlier scenario checked state/widget
cleanup but failed to reject that callback exception. None of these raw receipt,
report, wrapper, runner, inventory or image bytes has been changed to relabel its
historical result. New acceptance requires a separate native attempt, strict Qt
exception capture and an absent owned folder after Cancel.

[designed: T76/#233] The [diagnostic collection](../cleanup-diagnostics-01/inventory.json)
contains only new pure-stdlib fixtures/process metadata. The authoritative V2
receipt records a verified venv launcher and its owned base-interpreter child.
The launcher wait returned before the child handle signaled; an immediate owned
stderr deletion failed at1.4ms and succeeded at26.7ms after child teardown.
Direct base-interpreter cancellation deleted immediately. No persistent orphan
was observed. V1's process filter had an escaping defect, so its empty snapshots
are not ownership evidence; its original scripts/results are retained honestly.
No original save or data bytes are included in the diagnostic collection.

## Native02: strict cleanup acceptance

[designed: T76/#233] Main executed a separate immutable archive at checkpoint
`0503407a7e2466054f4b4070515d3e426ccd9942`. The exact
[host receipt](native-02/host-receipt.json) SHA256 is
`7b90c2d6c56c9c65d99240f9bcc0027b3924107daf1cb74764918a0555de18b0`;
it matches main's independently retained original. The
[inventory](native-02/inventory.json) contains95 verified entries, plus the
inventory file itself. No native-01 artifact was overwritten.

| Actual native Qt process | Environment | Captures | Elapsed | Result |
| --- | --- | --- | --- | --- |
| [designed] [1x report](native-02/observations/scale-1/report.json) / [full log](native-02/native-1.log) | Windows11 build10.0.26200; Python3.13.15; Qt6.12.0; actual ratio1.0 | 61 | 141.664s | PASS |
| [designed] [2x report](native-02/observations/scale-2/report.json) / [full log](native-02/native-2.log) | Same versions; actual ratio2.0 | 25 | 103.877s | PASS |

[designed: T76/#233] Both complete logs contain exactly one PASS line and no
traceback or ignored exception. Both reports record `callback_exceptions: []`,
`cleanup_retry_calls: 2`, clean Qt widget teardown and unchanged source bytes.
Normal and injected-sharing real-worker Cancel paths assert no owned folder
remains and retain the existing two-second bound. All twenty long names and
position/raw value/availability fields are covered by complete-cell captures;
wrapped detail/XI/bench areas retain overlapping coverage and fixed actions.
The [v4 main runner](native-02/main-native-validation.py) independently rejects
raw Qt tracebacks even if a process were to exit zero.

[designed: T76/#233] The [author audit](native02-author-audit-01.json) independently
checked all174 product/test/tool bytes against the then-current evidence tree
`882835e414dc515509b77df186134e4691f3c746` and frozen Git blobs, with exact [source-freeze02](../source-freeze-02.json) parity. The main
proof checker verifies every native report/capture/wrapper/log/resource/inventory
hash and equality of all four protected launcher/save/resource hashes. The raw
native-01 receipt and its full inventory are also rechecked unchanged. These are
checkpoint-attributed results; evidence-only commits carry source bytes forward
without claiming that native Windows executed the later documentation commit.

[designed: T76; derived: main native caption control] **Native02 is cleanup
success evidence, not final caption-readability acceptance.** Main's exact
[caption control](../caption-rework-01/T76-native-caption-control.py),
[fail-before log](../caption-rework-01/T76-native-caption-before.log) and
[runtime mock](../caption-rework-01/T76-native-caption-runtime-mock.log) measure
native `SE_PushButtonContents` using each button's own style option at900×640/2x.
Focused Confirm has132px content for135px text; Discard has75px for79px text.
The raw native02 captures/logs remain unchanged. A runtime-only stable3px scoped
footer border proves feasibility. The scoped source correction and actual caption
assertions now pass offscreen1x/2x in [caption rework](../caption-rework-01/README.md).
The later accepted T78 composition and caption correction intentionally change
source bytes; final native acceptance requires their own frozen checkpoint.

## Native03: composed source and caption acceptance

[confirmed: native03-author-audit.json; native03-main-proof-author-run.log] Main
ran immutable checkpoint `b3e2c95d8c5e744782d43ece6c840a7bd0a595d9`, containing
the accepted T78 composition and scoped stable footer borders. The exact
[host receipt](native-03/host-receipt.json) SHA256 is
`f8cf9a5c13def6300f0d82075eccdee55b0ba12f270d453b9d6ca44ad3c3b751`;
its bytes match main's independently retained original. The
[inventory](native-03/inventory.json) verifies95 entries plus itself.

| Actual process | Environment | Captures | Elapsed | Result |
| --- | --- | --- | --- | --- |
| [confirmed] [1x report](native-03/observations/scale-1/report.json) / [complete log](native-03/native-1.log) | Windows11 build10.0.26200; Python3.13.15; Qt6.12.0; ratio1.0 | 61 | 81.766s | PASS |
| [confirmed] [2x report](native-03/observations/scale-2/report.json) / [complete log](native-03/native-2.log) | Same versions; ratio2.0 | 25 | 50.007s | PASS |

[confirmed: native03-author-audit.json; verify-native03.py] The independent author
audit verifies all175 sources against source-freeze03, current bytes and frozen
Git blobs; every artifact/inventory/capture/report/log hash; four protected
launcher/save/resource hashes unchanged; and native01/02 inventories unchanged.
Each full log contains exactly one PASS line. Both reports record no callback
exceptions, two cleanup calls, no owned worker folder after Cancel, clean widget
teardown and unchanged sources. All20 roster rows/fields and complete overlapping
selected-detail/XI/bench reading coverage remain required and pass.

[confirmed: native-03/observations/scale-1/report.json; native-03/observations/scale-2/report.json]
Caption checks record36 measurements at100% and12 at200%: both buttons, focused
and unfocused, at every required size and three scroll positions. All actual
QStyle content rectangles contain the caption width and height. At900×640/200%,
Confirm has136px for135px text and Discard79px for79px, unchanged by focus;
both contents are40px tall for19px text. This fresh source run establishes the
caption correction; the earlier runtime-only mock remains feasibility evidence.
Main also visually inspected the native200% focused footer and selected detail.
The evidence-only follow-up carries checkpoint source bytes forward explicitly;
it does not claim Windows executed a later documentation commit. SDL is
inapplicable to this Qt-only workspace slice.
