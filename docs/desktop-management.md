# Desktop country management

[designed: owner #148, T69] The primary desktop interface uses PySide6. Install
its optional dependency in a virtual environment (tested Python3.12/PySide6 6.12.0):

```sh
python3 -m venv .venv
. .venv/bin/activate
python3 -m pip install '.[desktop]'
python3 -m goal2.desktop --template .cache/e010-r0008-halftime.sav --data .cache/GOAL.DAT --save .cache/desktop.g2save
python3 -m goal2.desktop --resume .cache/desktop.g2save --data .cache/GOAL.DAT
```

[designed] Supply verified local game resources using the existing runtime-cache
instructions. No original resources or screenshots enter git. Without Qt the
entry prints the installation instruction and exits2; headless imports and quick
play remain Qt/Unicorn-independent. Linux Qt needs its platform libraries; X11
uses libxcb-cursor0 and libxkbcommon-x11-0 in addition to existing X/GL libraries.
Offscreen acceptance does not replace the actual X11 window check.

[designed] Country selection is a draft. **New campaign** explicitly starts a
fresh1990 campaign for that country with initial seeds4660/33590, using the shared
opening campaign generator. A redraw, country selector edit or Resume does not
regenerate players. The active country's actual twenty records show original
names, position groups, ability, energy, confidence and eligibility; team morale
uses the confirmed eleven. Position groups use the runtime POS_LINE mapping,
not a new role table. The labels follow rebuild conventions, not an original Qt UI.

[designed; derived: T36/T44] Check exactly eleven available starters, choose one
as captain and toggle the eight tactics bits, then **Confirm management**. Until
confirmation, edits affect only widgets. **Discard draft** restores confirmed
choices. An unavailable selected starter can be removed; an unavailable reserve
cannot be added. Invalid drafts show a reason and preserve active state. IDs and
captain remain Python integers, including values above255. Tactics labels1..4
follow F010; labels5..8 retain the established rebuild choices.

[designed; derived: T33/T40] Save writes the confirmed state, never an unconfirmed
draft, through the existing atomic writer. Resume validates the save, embedded
template and rebuilt continuation before replacing active state. Invalid/missing
local files leave the current game and prior good save intact. DesktopModel calls
Python game/state/save interfaces directly and imports no web/Qt layer. Widget
updates stay on the Qt thread. Quick match execution uses the responsive T70 process flow below; pool
controls use the T71 flow below, watched controls belong to T66. No server/hosting
is involved in this management slice.

[derived: official Qt API documentation] The shell uses
[QApplication](https://doc.qt.io/qtforpython-6/PySide6/QtWidgets/QApplication.html)
and real widget events driven by
[QTest](https://doc.qt.io/qtforpython-6/PySide6/QtTest/QTest.html).

```sh
python3 -m unittest goal2.tests.test_desktop_model goal2.tests.test_desktop_entry -v
QT_QPA_PLATFORM=offscreen python3 tools/desktop-ui/acceptance.py --scenario management --template .cache/e010-r0008-halftime.sav --data .cache/GOAL.DAT
xvfb-run -a env QT_QPA_PLATFORM=xcb python3 tools/desktop-ui/acceptance.py --scenario management --template .cache/e010-r0008-halftime.sav --data .cache/GOAL.DAT
xvfb-run -a env QT_QPA_PLATFORM=xcb python3 tools/desktop-ui/acceptance.py --scenario launch --template .cache/e010-r0008-halftime.sav --data .cache/GOAL.DAT
python3 tools/desktop-ui/prove-management.py
```

[designed: T70] Confirm management, then choose **Play quick friendly**. Simulation
runs in a local process; the window stays responsive. Controls that change the
game are disabled until completion. **Cancel match** or closing the window stops
and reaps the process; a failed/cancelled/stale result never changes the active
game. A completed result shows named teams, score and goal scorers. The setup is
the rebuild quick simulation, not original watched commentary or visualization.

[derived: T41–T46; designed: T70] Campaign play consumes only the next supported
friendly in source A/B order, retaining condition, eligibility, RNG and history.
Save and resume use the same complete continuation. The unsupported competitive
fixture remains visible and refuses play. **New standalone friendly** explicitly
creates fresh selected-country records without a campaign ledger; confirm its
management before play. Repeat carries the prior result/player state forward.
Creating either new mode replaces the active unsaved game only on that explicit
action. Save writes confirmed state; unconfirmed management edits must be
confirmed or discarded before playing.

[designed: T70] The Qt-free worker exchanges explicit JSON session saves through
private temporary files, with one job in flight and UI-thread publication once.
A completion must match both the original state object and its complete encoded
state/template. Cancellation waits at most half a second for termination before
kill and a second bounded reap. Optional Qt remains outside headless imports.

```bash
python3 -m unittest goal2.tests.test_desktop_quick_jobs -v
QT_QPA_PLATFORM=offscreen python3 tools/desktop-ui/acceptance.py --scenario campaign-friendlies --template .cache/e010-r0008-halftime.sav --data .cache/GOAL.DAT
QT_QPA_PLATFORM=offscreen python3 tools/desktop-ui/acceptance.py --scenario worker --template .cache/e010-r0008-halftime.sav --data .cache/GOAL.DAT
python3 tools/desktop-ui/prove-friendlies.py
```

[derived: T45; designed: T71] The national pool sits beside the twenty-player
squad. It shows eighty reserve identities with original names, source position
code/group, ability, energy, confidence and availability. Search names and filter
numeric position codes to find a reserve. These controls only filter the view.
Select a row in each table, then **Exchange selected squad player and reserve**.
The exchange uses the confirmed team and discards unconfirmed widget edits.
T45 swaps full IDs, repairs a replaced starter/captain, and preserves player
records. Confirm management, save/resume or play with the exchanged team.

[assumed: T45 Q008/#254] The explanation above the reserves is authoritative:
exchanges require a pending supported managed friendly outside the provisional
tour boundary. This is the existing provisional rebuild policy, not established
original window fidelity. Invalid or unavailable incoming players are refused
without changing the game. Standalone mode has no national pool. Pool controls
are disabled while a match process is running. Redraw/filter/resume never
regenerate player identities; the existing ordered quick tail updates reserves
once per completed fixture.

```bash
python3 -m unittest goal2.tests.test_desktop_pool -v
QT_QPA_PLATFORM=offscreen python3 tools/desktop-ui/acceptance.py --scenario campaign-pool --template .cache/e010-r0008-halftime.sav --data .cache/GOAL.DAT
python3 tools/desktop-ui/prove-pool.py
```
