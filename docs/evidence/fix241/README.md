# Player table browsing evidence

[designed: #241] `tools/desktop-ui/player-browsing.py` owns the active and country-preview browsing regression. It dispatches wheel events to the visible table viewport, selects every row with actual keys after asserting native focus, and drives both scrollbar endpoints with keys. It compares complete encoded active and preview states, both RNG pairs, saved bytes, context-specific drafts and job ownership throughout. Preview editing and busy browsing remain refused. No original game bytes are included here; resource hashes identify private inputs.

[designed: #241] Run each scale in a fresh process, using a private native display large enough for the logical window. For Linux, explicitly select `QT_QPA_PLATFORM=xcb`, stage the two local xcb libraries, and own the Xvfb 2880×1800 display and its window manager with private XDG directories. Windows uses `QT_QPA_PLATFORM=windows`. Main owns native Windows validation; Linux results do not stand in for it.

```bash
QT_SCALE_FACTOR=1 python3 -B tools/desktop-ui/player-browsing.py --template .cache/e010-r0008-halftime.sav --data .cache/GOAL.DAT --evidence-dir <new-output>
QT_SCALE_FACTOR=2 python3 -B tools/desktop-ui/player-browsing.py --template .cache/e010-r0008-halftime.sav --data .cache/GOAL.DAT --evidence-dir <new-output>
QT_SCALE_FACTOR=1 python3 -B tools/desktop-ui/player-browsing.py --template .cache/e010-r0008-halftime.sav --data .cache/GOAL.DAT --evidence-dir <new-output> --negative-controls
```

[designed: #241] The scale1 sizes are 1440×900, 1050×780 and 900×700; scale2 uses 900×640. Reports retain the actual platform, screen, device ratio, source hashes, every row identity, wheel coverage, captures and exceptions. Outputs must be new directories. Negative controls save exact source bytes and restore them in `finally`, and must run without any concurrent source reader.

[designed: #241] Earlier runs are retained honestly. `baseline-1x` stopped at preview checkable flags. `baseline-wheel-1x` exposed a helper setup mistake: an active preliminary wheel followed by Ctrl+Home to an already-current row. `baseline-wheel-02-1x`, `baseline-wheel-03-1x`, `fixed-1x` and `fixed-02-1x` failed native activation/focus preconditions. They inherited Wayland because platform selection was omitted and the library path was wrong; these are diagnostic records, not native-display acceptance. `baseline-wheel-preview-1x` dispatched a disabled preview wheel and failed the intended scrolling assertion, also on inherited Wayland. The helper now explicitly requires X11 or Windows; accepted source controls re-prove the wheel failure on the owned display. `.cache/fixed-private-1x.log` and `.cache/qt-platform-diagnostic.log` retain pre-Qt startup failures that exposed the wrong library path; no application report was possible for those starts.
