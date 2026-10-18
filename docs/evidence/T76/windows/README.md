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
