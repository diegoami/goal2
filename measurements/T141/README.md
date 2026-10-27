# T141 contextual Team Info navigation

[designed: owner #452] Back to team and the existing page-local Esc restore the
Country/Team context that opened Team Info, preserving selected players and
useful focus. They send no original-game action. The modal Esc remains local to
the dialog; page bounds and the existing reserve budget are retained.

`navigation-proof-v1.json` binds four native runs to source eded2909 and the
reference input hashes: Linux XCB scale multipliers1/2 (actual DPR1/2), native
Windows multipliers1/2 (system DPI makes actual DPR1.5/3). Each runs four genuine
Core/Qt controls, no skips. The native probe requires actual active windows,
on-screen functional controls, DPR consistent with system DPI, and positive
layout measurements. Before/after default tests are4fail/4pass. No original
state or source bytes are embedded in the metadata.

The index named by the receipt preserves raw native reports/logs, rebuilt
captures and rejected setup receipts privately in goal2-keep, deduplicated and
verified by SHA256. No original game image or career save is copied there.
The first two interpreter attempts lacked declared dependencies; initial native
Linux attempts missed the cached XCB library path, then a bare X server lacked
modal focus restoration. Final runs keep all assertions and use the existing
cached XCB libraries with installed xfwm4 under isolated displays/D-Bus/XDG
configuration. Native Windows uses the same Linux source checkout via WSL UNC,
not the owner's career or Windows checkout.

Run default controls in the project environment:

```
.cache/venv/bin/python -B -m unittest goal2.tests.test_core_team_back_t141 -v
```

Native proof is a separate process, with a real platform and scale multiplier:

```
python -B -m goal2.tests.test_core_team_back_t141 --native --factor 2 --out <new-private-folder>
```

Full Linux/Windows gates and the integrated milestone review remain separate
acceptance; this navigation receipt is not engine integration or visual sign-off.
