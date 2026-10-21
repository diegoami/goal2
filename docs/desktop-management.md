# Desktop country management

[designed: owner #148, T69] The primary desktop interface uses PySide6. Install
its optional dependency in a virtual environment (tested Python3.12/PySide6 6.12.0):

```sh
python3 -m venv .venv
. .venv/bin/activate
python3 -m pip install '.[desktop]'
python3 -m goal2.desktop --template .cache/e010-r0008-halftime.sav --data .cache/GOAL.DAT --save .cache/desktop.g2save
```

[designed: T86; accepted vision #266 screen 01] That command opens the **Launch** window. Its
**Saved career** panel summarises the save at `--save`, as the validating loader reads it:
country, manager (the one-manager default; names arrive with #265), campaign year and stage,
next and following fixture, checkpoint and confirmed team. **Resume** validates the file again
and opens management. **Open another save** takes a path. A missing, corrupt or incompatible
save names the reason and offers **Retry** and **Load another**, with nothing else changed.
**New career** lists the 128 countries with world and continent rank. A private preview shows
the first fixture and the twenty players, and names the profile categories this build does not
show yet (G05/O12). The start year is 1990 or 1992. **Review** comes before **Start career**.
Browsing, review and starting write no save; the new career is saved only when you save it.
Arrows choose, Enter accepts and Esc goes back. [designed: owner, 2026-10-21; T88] On the
country list, **Space** (or **Players**) shows that country's twenty: role codes on the left,
squad then bench, and each player's complete card on the right. The card has the name with
initial, role code, age, caps, goals, height, foot, readiness, national and club position, cards,
performance (raw; its meaning is not decoded), the twelve skill bars with their values, the five
characteristics with bar, value and the original's word, and the tactics and mark line. Every
value equals what the original's own player screen prints [confirmed: F008, E007]. No attribute
total is shown. Narrow windows stack the card and scroll it. The window keeps its text size at 900×640 and
scrolls the preview instead ([original start, load and save](original-game/startup-save-replay.md)).
`--resume <save>`, or `--country <n>` with `--template`, still opens management directly for
scripts. Check it with `python3 tools/desktop-ui/launch.py --template … --data …`, offscreen and
under `QT_QPA_PLATFORM=xcb xvfb-run -a -s "-screen 0 3200x2000x24"` with `QT_SCALE_FACTOR` 1 and 2.

```sh
python3 -m goal2.desktop --resume .cache/desktop.g2save --data .cache/GOAL.DAT
```

[designed] Supply verified local game resources using the existing runtime-cache
instructions. No original resources or screenshots enter git. Without Qt the
entry prints the installation instruction and exits2; headless imports and quick
play remain Qt/Unicorn-independent. Linux Qt needs its platform libraries; X11
uses libxcb-cursor0 and libxkbcommon-x11-0 in addition to existing X/GL libraries.
Offscreen acceptance does not replace the actual X11 window check.

[designed: T74] The persistent country header sits above five destinations:
**Overview** (Ctrl+1), **Squad & tactics** (Ctrl+2), **National pool** (Ctrl+3),
**Fixtures & results** (Ctrl+4), and **Save / resume** (Ctrl+5).

[designed: T78] Fixtures & results groups the next named fixture, last completed
score, engine provenance, goals and a read-only standings snapshot. Ordinary
goals retain source A/B order; competitive regulation, cumulative extra-time
score and penalty kicks appear separately. Qualification positions remain
provisional. A fresh country preview has its own empty result. Unavailable
Play/Watch routes show a reason and retain the existing callback refusals.
 Navigation moves
focus to the page heading and preserves unconfirmed drafts, the active game,
save files and running jobs. [designed: T77] National pool provides an outgoing
squad selector synchronized with the current squad row; it changes selection only.
Choose a visible reserve and read both full identities before exchanging.
Save/Resume and the editable save path live in Save / resume; Ctrl+S invokes the
same guarded Save. Status and Cancel match remain visible across destinations.
At small sizes, scroll the current page to reach its remaining actions; tables
retain their native row/column navigation, and Tab moves to the next control.

[designed: owner, 2026-10-21; #283, #286] Squad and pool tables and details show each player's
role as the original's one-letter code (G S C b B D Ç m M F w W ¢ $; club role in details),
coloured by line, and the pool filter lists the codes with the original's position names. No
attribute total (the overall ability byte) is shown anywhere, including the browser UI.

[designed: T75] The header shows the displayed country's full name beside an
original generic shirt and neutral decorative stripe. The art is a fallback for
every country, not a national kit. Overview shows that country's next fixture in
source A/B order and last result with its provenance, or an honest empty state.
**Return to active game** restores the active country and its unconfirmed draft;
New campaign and New standalone friendly remain explicit replacement actions.

[designed: #181] Selecting a country immediately shows a fresh campaign preview:
its name, twenty-player squad, captain, tactics, morale, next fixture and reserve
pool. Preview results belong to that fresh team; the active game's result is
shown again on return. **New campaign** or **New standalone friendly** explicitly
makes the selected country active; browsing never replaces the active game or
writes its save. Management, play, Save, exchanges and the competition table are
unavailable in a preview. [designed: #241] Both player tables remain scrollable
with the wheel, scrollbar and keyboard; selecting a row shows its full-ID detail.
Preview XI checkboxes, captain and tactics remain read-only. Return to the active
country to recover its unconfirmed
XI/captain/tactics draft, or use Resume to load a saved game. Country selection
is unavailable during a match.

[designed: #181] A successful **New campaign**, **New standalone friendly**, or
**Resume** explicitly replaces the active game and discards any unconfirmed
management draft, after the question described below (T87). A Resume that fails validation leaves the active game and draft
unchanged.

[designed: T87; original save/quit: [start, load, save and quit](original-game/startup-save-replay.md)]
The **Game** menu holds **Save** (Ctrl+S), **Save as…** and **Quit** (Ctrl+Q); the Save page
has the same Save as. Before New campaign, New standalone friendly, Resume or Quit (menu,
Ctrl+Q or the window's close button), the window asks if anything would be lost. It names
**progress confirmed since the last save** (since the game was created, resumed or saved) and
an **unconfirmed squad, captain or tactics draft**. The engine's squad reorder after an
original match (#280) is not counted as a draft. It offers **Save and continue** (only when
there is progress to save), **Continue without saving** and **Cancel** (Esc). Save never confirms a
draft. A failed save shows its reason and nothing is replaced: the window stays open and the
previous save is untouched. Saving to a different existing file asks before overwriting. While a
match runs, saving is refused, and Quit warns that the match will be cancelled. Check it with
`python3 tools/desktop-ui/save-decisions.py --template … --data …`, offscreen and under
`xvfb-run` (xcb) at `QT_SCALE_FACTOR` 1 and 2.

[designed] **New campaign** starts a fresh campaign with initial seeds 4660/33590,
using the shared opening campaign generator. [designed: owner, 2026-10-20, T50] Its **Start year**
choice is 1990 (default; World Cup qualifying first) or 1992 (continental qualifying first,
[continental qualifying](continental-qualifying.md)); previews use the chosen year. A redraw or Resume does not regenerate
players; previews generate separate records. The displayed twenty records show
original names, position groups, ability, energy, confidence and eligibility;
team morale uses the confirmed eleven. Position groups use the runtime POS_LINE
mapping, not a new role table. The labels follow rebuild conventions, not an original Qt UI.

[designed; derived: T36/T44] Check exactly eleven available starters, choose one
as captain and toggle the eight tactics bits, then **Confirm management**. Until
confirmation, edits affect only widgets. **Discard draft** restores confirmed
choices. An unavailable selected starter can be removed; an unavailable reserve
cannot be added. Invalid drafts show a reason and preserve active state. IDs and
captain remain Python integers, including values above255. [confirmed: F010] Tactics
labels for elements1..4,6,7 follow F010; [designed] labels5 and8 retain the established rebuild choices.

[designed; derived: T33/T40] Save writes the confirmed state, never an unconfirmed
draft, through the existing atomic writer. Resume validates the save, embedded
template and rebuilt continuation before replacing active state. Invalid/missing
local files leave the current game and prior good save intact. DesktopModel calls
Python game/state/save interfaces directly and imports no web/Qt layer. Widget
updates stay on the Qt thread. Quick match execution uses the responsive T70 process flow below; pool
controls use the T71 flow below; original watched friendlies use the T66 flow below. No server/hosting
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
QT_QPA_PLATFORM=offscreen python3 tools/desktop-ui/redesign.py --scenario overview --template .cache/e010-r0008-halftime.sav --data .cache/GOAL.DAT --evidence-dir docs/evidence/T75/linux
QT_QPA_PLATFORM=offscreen python3 tools/desktop-ui/country-selection.py --template .cache/e010-r0008-halftime.sav --data .cache/GOAL.DAT
```

[designed: T70] Confirm management, then choose **Play quick friendly**. Simulation
runs in a local process; the window stays responsive. Controls that change the
game are disabled until completion. **Cancel match** or closing the window stops
and reaps the process; a failed/cancelled/stale result never changes the active
game. A completed result shows named teams, score and goal scorers. The setup is
the rebuild quick simulation, not original watched commentary or visualization.

[derived: T41–T46; designed: T70] Campaign play consumes only the next supported
friendly in source A/B order, retaining condition, eligibility, RNG and history.
Save and resume use the same complete continuation. Supported original competitive
fixtures use the separate Play action described below; Quick itself remains friendly-only. **New standalone friendly** explicitly
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

[derived: T45; designed: T71/T77] The National pool destination retains the twenty-player
squad membership. It shows eighty reserve identities with original names, source position
code/group, ability, energy, confidence and availability. Search names and filter
numeric position codes to find a reserve. These controls only filter the view.
Select an outgoing player and a reserve row, then **Exchange selected squad player and reserve**.
The raw reserve detail and exchange summary retain names and full integer IDs.
Filtering clears the incoming selection and shows an explicit empty detail; select
a visible row again before exchanging.
The exchange uses the confirmed team and discards unconfirmed widget edits.
T45 swaps full IDs, repairs a replaced starter/captain, and preserves player
records. Confirm management, save/resume or play with the exchanged team.

[assumed: T45 Q008/#254] The explanation beside the exchange action is authoritative:
exchanges require a pending supported managed friendly outside the provisional
tour boundary. This is the existing provisional rebuild policy, not established
original window fidelity. Invalid or unavailable incoming players are refused
without changing the game. Standalone mode has no national pool. [designed: T77] The adjacent reason also explains preview, standalone and busy
contexts. Pool controls are disabled while a match process is running. Redraw/filter/resume never
regenerate player identities; the existing ordered quick tail updates reserves
once per completed fixture.

```bash
python3 -m unittest goal2.tests.test_desktop_pool -v
QT_QPA_PLATFORM=offscreen python3 tools/desktop-ui/acceptance.py --scenario campaign-pool --template .cache/e010-r0008-halftime.sav --data .cache/GOAL.DAT
python3 tools/desktop-ui/prove-pool.py
```

[designed: T47] Campaign matches now pause for explicit
[halftime substitutions](campaign-halftime.md). Select an outgoing starter and
available bench player, use **Substitute**, then **Continue second half**.
No re-entry; friendly substitutions are unlimited. Saving is disabled while the
match is pending; cancel keeps the previous game/save. Standalone quick play
continues uninterrupted. Substituted XI/captain choices persist for later
fixtures and through full-time save/resume.


[designed: T66] To watch the next scheduled **friendly**, install the optional
presentation and original runtime dependencies in the same environment as Qt:

```sh
python3 -m pip install '.[desktop,watched,match-view]'
python3 -m goal2.desktop --template .cache/e010-r0008-halftime.sav --data .cache/GOAL.DAT --save .cache/desktop.g2save
```

[designed] Confirm XI, captain and tactics, then choose **Watch original friendly**.
A separate Pygame window shows a numbered animated pitch, original ordered commentary, minute and score;
after the original post-match tail, scroll with the mouse wheel or arrow keys to
see the original full-time board, man of the match and **Raw rating**. Countries,
minute and score stay pinned above the scroll area. New commentary follows live
until wheel/arrow scrolling pauses it; End resumes following. Completion opens
at the original board, with raw ratings below. Escape or
the window close button closes it. Closing while the match is running cancels the
match and preserves the last committed state/save. Closing a completed viewer
keeps the published result. Save/Resume remain Qt actions; saving during a match
is unavailable. A second match requires an explicit new Play/Watch action.
Pending qualifiers, standalone watching, in-play changes, mid-match saves and
competitive watching are unsupported. Quick management/play remains available without
pygame-ce, Unicorn or watched resources; Watch reports the missing dependency.

[designed: T83] The field is a modern schematic. Team colors identify the fixture
countries; numbers 1–11 are current local pitch slots, not persistent shirt
numbers. The ball and players use discrete original completed-tick positions,
without interpolation or halftime rotation. Only the original exact hidden-position
sentinel suppresses a marker. The fixed default playback target is 60 samples per
second, independently of engine speed; slow display refresh can extend playback.
Score, minute and commentary follow the currently displayed sample's canonical
event watermark. The last tick stays on screen through full-time. Save and all
management mutations stay locked until every sample has been displayed and the
original result validated. Closing while playback is pending discards the pending
result even if the engine has finished. The bounded queue holds at most 64
unacknowledged samples; the worker's finite journal remains lossless within T82's
8192-frame/16MiB budget. `WatchedController.start(playback_rate=...)` accepts an
explicit 1–240 samples/s target; `frames=False` retains the text presentation for
compatibility checks. See [T83 evidence](evidence/T83/README.md).

[confirmed: F014/E012 §1 at424d5998076da1e4efc399c2715689ddb44d3e1a]
Raw ratings are the actual returned original player-record words at +0x12, not
confidence or a replay prediction. Blank is 0x7FFF; signed values above5000 have
the substitution encoding10000 removed. This view explicitly displays raw values,
not the original screen's 1..9 buckets. Commentary and names are decoded at runtime;
no original text resources or images are bundled here.

[designed] Tested optional dependencies are pygame-ce2.5.8 (SDL2.32.10),
Unicorn 2.1.4 and PySide6 6.12.0 on Linux/WSL. The viewer receives bounded private
JSON presentation records, never game state/Memory or engine input. Qt polls the
T65 worker and owns the single validated result publication. Viewer startup has
a10-second bound. Failed folder/stream allocation releases partial resources and
reports the original cause; the same controller can retry. Cancellation terminates
then kills/reaps only its owned engine
and viewer, each with half-second waits. Native Windows packaging is untested.

[designed: #236] The watched viewer retries Windows status replacement denial
(WinError5) for up to250ms. Qt defers status-read access denial to later polls,
without sleeping in the callback, for up to250ms of consecutive failures; a
successful read resets that budget. Native Windows reads may report errno13
without a winerror. Owned viewer-folder deletion retries WinError32 for up
to500ms after child reaping and stream closure. Permanent or unrelated errors
propagate. Failed teardown retains references for retry and keeps its pending
match lock; a completed old viewer never releases a newer job's lock.

See T66 evidence (`evidence/T66/README.md`, removed 2026-10-20; on branch `local`) for retained text-mode checks and
[T83 evidence](evidence/T83/README.md) for animated pitch display acceptance.

```sh
SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy QT_QPA_PLATFORM=offscreen python3 -m unittest goal2.tests.test_pygame_pitch_view -v
SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy QT_QPA_PLATFORM=offscreen python3 tools/desktop-ui/animated-pitch.py
SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy QT_QPA_PLATFORM=offscreen python3 -m unittest goal2.tests.test_pygame_match_view -v
SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy QT_QPA_PLATFORM=offscreen python3 tools/desktop-ui/watched.py
```

[designed] For validation, set TMPDIR to the checkout's physical `.cache/tmp` and
stage the verified fixtures described by the T66 evidence; these commands never fetch
or commits original assets. A normal desktop launch should use its native SDL/Qt
display drivers, not the headless variables above.


[designed: T80; derived: T51/E034 at424d599] For a supplied pending original
competitive fixture, the button reads **Play original competitive**. It runs the
original engine in a separate owned process with the fixture, current confirmed
XI/captain/tactics, engine year and both RNG seeds. Default decisions continue
play, with the existing five substitutions per side budget. The Qt window shows
live minute/score progress, then named regulation, extra-time, penalties and winner
labels where applicable. Only a validated full post-match continuation publishes;
Save/Resume retains its complete result, Memory and seeds. No competition draw or
new fixture progression is added. Unsupported kind4 still refuses Play.

[designed: T80] A loaded competitive automatic captain0 is displayed as the disabled
**Original captain selection** placeholder. Playing preserves that original input;
explicit **Confirm management** requires a named captain in the XI. Missing runtime
or local resources show install/resource guidance while management remains usable.
Competitive Play, friendly Quick and friendly Watch share one match lock. Save,
Resume and management edits wait until completion or cancellation. Cancel/close
reaps only the owned child and preserves the active state and previous save.
**Watch original friendly** continues to support scheduled friendlies only.

```bash
python3 -m unittest goal2.tests.test_desktop_competitive_jobs -v
python3 tools/desktop-ui/competitive_play.py
QT_QPA_PLATFORM=xcb xvfb-run -a python3 tools/desktop-ui/competitive_play.py
```

[designed: T76] **Squad & tactics** retains the twenty-player source-order roster.
Select a row to read its full ID, position group, raw ability/energy/confidence
and availability. The grouped starting XI and bench reflect the private draft,
with explicit Captain text; grouping does not assign a formation. The fixed
Confirm management / Discard draft bar stays visible while the page scrolls.
Space toggles native XI/tactics controls; Enter activates a focused draft action.
Draft edits survive navigation and country preview/return; Save writes confirmed
state, and match play still requires confirmed management.

[designed: T76/#233; derived: native launcher diagnosis] Windows quick-worker
cleanup allows up to0.5seconds for a transient sharing violation while an owned
child finishes closing stderr. Other cleanup errors propagate. Cleanup failure
retains ownership so Cancel can retry; it does not publish a candidate or change
the confirmed save. Worker interpreter and dependency context remain unchanged.

[designed: T78] The fixtures/results acceptance scenario supports verified saved
inputs and separate native scale processes:

```sh
python3 tools/desktop-ui/redesign.py --scenario results --template .cache/e010-r0008-halftime.sav --data .cache/GOAL.DAT --evidence-dir docs/evidence/T78/linux
```

[derived: evidence/T78/README.md] The retained Windows proof runs this scenario
at measured 100%/200% with Qt 6.12.0 and the declared optional Unicorn 2.1.4 runtime
in a private validation directory. Host bootstrap and missing-runtime failures
are preserved alongside the final passing proof in T78 evidence (`evidence/T78/README.md`, removed 2026-10-20; on branch `local`).
Those setup corrections leave product code and the existing Windows environment
unchanged; dependency provenance is recorded without committing package bytes.
