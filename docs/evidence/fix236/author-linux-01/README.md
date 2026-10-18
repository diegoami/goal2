# Linux real Qt/SDL acceptance

[confirmed: runtime.log, display-receipt.json] The complete required four-module
unittest command passed53tests in214.067s with no skips. A private Xvfb display
and owned xfwm window manager provided focus for Qt xcb and SDL x11. The helper
and owned window manager exited0. Startup dbus inotify warnings and normal display
shutdown messages remain in the complete log; no Qt callback exception occurred.

[confirmed: runtime.log] The unchanged original Qt main completed fixture1378
2–3/events1171 and1471 2–0/events1392, comparing complete state/Memory/bothRNG/history
with independent direct original continuations, then Save/Resume/repeat and
ownership/cancellation controls. Qt heartbeats1005/1262 ran. Existing original
pitch controls also verified seeds257/4660 with4279/4146 frames and1079/1178 events.
These are Linux acceptance results, not native Windows acceptance.

[confirmed: fixtures-unchanged.json] All27 staged fixture/kit files retain the
main-provided SHA256 values after the suite. Only names/hashes are recorded;
original resources remain ignored. Product source and the pygame acceptance
module were unchanged during the full runtime suite; subsequent sharing-test
strengthening did not alter runtime code or existing assertions.
