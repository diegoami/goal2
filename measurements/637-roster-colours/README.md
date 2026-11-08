# Full roster name colours

[confirmed: original t156-014-squad.png and name-initial palette samples in
`docs/design/ui-2026-11/README.md`] Full names carry the player's line colour.
The shared strip and match-menu elevens previously coloured only role letters.
This corrects both renderers without changing palette values, records, ordering,
engine inputs or keyboard flow. Selected-row contrast and injury feedback remain.

Model: inherited Codex GPT-6 family; exact variant unavailable.

`before-main.log` exercises three real Qt pixel/contrast/menu controls on main
ac010f8ac8c9dfd829c990ad91ba56bba91268fc:16assertions fail. `after-main.log`
passes3/3 in0.090s on functional24b87f7797047b663187c58d3ca131f2cce89705.
The controls inspect full-name glyph pixels for all four lines and the unknown,
selected and injured cases; the menu control visits all11 rendered rows.

`native-final.log/json` bind the committed renderer/test bytes to bundled native
Windows CPython3.13.17:3/3 pass0.110s. Actual S08 temporary-career screenshots have
20 visible rows and zero fixed-page problems at1440x900 and1200x750. Two modified
UI modules are loaded only in this separate offscreen process; installed code,
owner game and saves remain untouched. The installed runtime is accepted d56e793.
All candidate runtime Python files match that installation except the two loaded
renderers and T202's S10 module, which these S08/lineup controls do not exercise.
This is scoped native rendering evidence, not a full installed candidate or match.

The exact producing script is retained as native-final.py with its declared IT13
UNC paths. Run it with the installed bundled python.exe and QT_QPA_PLATFORM=offscreen;
use temporary output/data copies when adapting paths. Run current source controls:

```bash
source .cache/cloud.env
.cache/venv/bin/python -B -m unittest goal2.tests.test_roster_colours_637 -v
python3 measurements/637-roster-colours/verify.py
```

Initial prototype screenshots remain private supporting diagnostics outside this
receipt: one source-loading calibration lacked explicit UTF-8 decoding and was
corrected before the exact-source native run; it is not acceptance evidence.
Default fast/platform acceptance is recorded on PR638. This colour proof does
not establish substitution requests/opportunities636, live stopped team traits,
tactics latency, full UI fidelity or season completion.
