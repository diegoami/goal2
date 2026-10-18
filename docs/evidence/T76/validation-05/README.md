# Composed T76/T78 validation

[confirmed: progress.json; service-status-final.log] All20 serial groups pass on source commit `783bd470282957b4bd9251257ced817a432347fd`, which ordinarily merges accepted main `9c0557a770f1f4e972e0d8e93df67fadc8304eb6` with the scoped T76 caption correction. `run-validation.py` retains the exact detached driver, `service.log` its complete output, and each named log its full command output. `progress.json` records commands, exit codes, elapsed times and log hashes. Detached service startup reported nonfatal inotify-watch warnings; the driver exit is0; its initial completion status records service descendant teardown. No system settings or unrelated processes changed.

[confirmed: author-audit.log; ../source-freeze-03.json] All20 log hashes, all four squad report/capture sets, focused/unfocused QStyle caption width/height assertions, clean Qt callbacks/widgets, worker cleanup retries and unchanged source bytes were independently checked. All175 tracked product/test/tool files equal the frozen Git blobs. The three copied private T78 inputs match `results-input-inventory.json`; only their hashes/metadata enter this evidence tree.

[confirmed: squad-native/scale-2/long-900x640-detail-focused-confirm.png] The author visually inspected the native Linux200% fixed action bar: both captions and focus outlines remain clear while content scrolls. Numeric geometry and segmented reading coverage remain required; this image alone is not complete-content proof. Final actual Windows uses a separate main-owned native03 attempt at a pushed frozen checkpoint.

| Group | Exit | Seconds |
| --- | --- | --- |
| results | 0 | 34.289 |
| results-negative | 0 | 33.453 |
| competitive | 0 | 128.034 |
| units | 0 | 40.955 |
| prove-management | 0 | 11.477 |
| prove-friendlies | 0 | 12.365 |
| prove-pool | 0 | 3.534 |
| prove-halftime | 0 | 13.91 |
| management | 0 | 7.46 |
| campaign-pool | 0 | 9.005 |
| campaign-halftime | 0 | 5.998 |
| country-selection | 0 | 5.86 |
| tactics-labels | 0 | 1.086 |
| overview | 0 | 19.974 |
| overview-negative | 0 | 4.798 |
| shell | 0 | 62.778 |
| shell-negative | 0 | 35.634 |
| squad-negative | 0 | 122.187 |
| squad-offscreen | 0 | 91.509 |
| squad-native | 0 | 81.808 |
