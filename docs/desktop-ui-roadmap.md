# Desktop UI roadmap

[designed: owner #148, 2026-10-16; session choice] The primary app uses PySide6
with ordinary Qt management widgets. [designed: owner, 2026-10-17] A separate
Pygame match view consumes original engine events; keep Qt management and saves.
This amends the earlier all-Qt match-view choice and supersedes the browser direction; T34–T38 remain
historical contracts, not tasks to reopen. Reuse Python game logic, state adapters,
the evidence register and saves. The web layer is not reused. No HTTP server,
network sessions or hosting is needed. A web demo is an optional later owner choice.

## Small playable slices

[designed: T68] These are future contracts, not implemented commands or status.
GitHub labels carry status. Each task receives its own preflight and PR.

| Task | Outcome | Difficulty | Depends on |
| --- | --- | --- | --- |
| [T45](tasks/T45.md) | Portable pool membership/exchange/save and ordered condition updates, tested headlessly | Medium | T44 |
| [T69](tasks/T69.md) | Desktop country, squad, XI/captain/tactics, eligibility/morale, save/resume | Medium | T44 |
| [T70](tasks/T70.md) | Desktop quick friendly and scheduled campaign play/result/repeat through a process worker | Medium | T69 |
| [T71](tasks/T71.md) | Search/filter the 80 reserves, exchange with the 20-player squad and continue in desktop | Medium | T45, T70 |
| [T66](tasks/T66.md) | Pygame original-friendly view from Qt management, real events/results, save and repeat | Medium | T65, T70 |

[designed] T45 and T46 keep progressing independently of kit acceptance and desktop
migration. The later UI-bearing campaign tasks require T71 through T47; their
rule dependencies stay intact. T62–T64 acceptance/adapter/publication do not depend
on Qt. T65 supplies a UI-independent process bridge; T66 connects it to a separate Pygame
match window while Qt retains state/publication and management.
The engine kit acceptance sequence remains first on the original-engine track.

## Execution and state ownership

[designed: #148] Keep match computation outside the Qt UI thread. Default to a
separate process: whether Unicorn releases Python's GIL has not been established.
The engine runs locally within the worker process. IPC carries ordered events,
answers and completion/failure. Qt retains publication on its UI thread and forwards
read-only presentation packets to the separate Pygame window. Neither redraws
nor playback timing may change engine inputs, RNG or publication. Match workers receive a candidate snapshot, never shared mutable active
state. One current job token permits one publication; ignore stale completions.
Keep controls responsive and the previous committed state/save intact on failure.
Process shutdown/cancellation and application close must be bounded and tested.
T70 handles quick play; T65 adds original decisions/events and the post-match tail,
reusing transport primitives if present without coupling rule code to Qt.

[designed: stage 1] T66 uses the existing default-answer policy. The kit's
`events()`/`answer()`/`pause()` capability does not itself authorize new in-play
editing, pitch animation or mid-match application saves. T47 separately owns
halftime substitutions and the owner's unlimited-friendly/five-otherwise budget.
A `full_time` event does not authorize publication before the original tail.

## Dependencies, acceptance and distribution

[designed] Add PySide6 as an optional desktop dependency in T69, with a tested
version and actionable missing-dependency instructions; Python/headless quick
play remains usable without Qt or Unicorn. Qt interaction checks run offscreen
and include a real window smoke. Use real local verified resources for integration;
keep all original bytes out of git. Future `tools/desktop-ui/acceptance.py` commands
are contracts to establish at each task's preflight, not available tools today.
Existing browser checks cover retained browser behavior, not new desktop acceptance.

[derived: official documentation, checked 2026-10-16] PySide6 is Qt's official
Python binding and is offered under LGPLv3/GPLv3 and commercial terms
([Qt for Python](https://doc.qt.io/qtforpython-6/)). PyQt is offered under GPLv3
or commercial terms ([Riverbank](https://riverbankcomputing.com/software/pyqt/intro)).
The owner selected PySide6; this is not a finding about the original game.

[designed: #130/#148] Distribution remains small, last and unscheduled. A zip/run
script is the cheap first package; a later executable is built and verified per OS
with the engine image supplied from the private release at build time, never git.
No bundler is selected and cross-platform Unicorn/Qt packaging is not proven.
Native mobile is outside this desktop plan until a separately chosen exact port;
a phone web demo is optional, not a desktop acceptance requirement.

[designed: T69] The [desktop management guide](desktop-management.md) defines the shell launch, optional dependency and direct-Python management/save boundary. Match execution, pool controls and watched integration retain their separate task contracts.

## Gradual Pygame match view

[designed: owner, 2026-10-17] T66 first displays real minute, score, commentary
and original result boards in a separate pygame-ce window launched from Qt.
Keep the management screens and save/resume ownership in Qt. T65 supplies ordered
original events, default answers and a completed outcome; the viewer never runs a
second match or publishes state. Test both process lifecycles and stale/duplicate
messages, with optional dependencies and headless/real-window checks.

[confirmed: accepted kit at424d599, `Match.pitch()`, F013] The kit exposes 22 player
records and ball coordinates, labeling their pitch interpretation likely.
[designed] A later bounded pitch-view slice must validate the coordinate transform,
orientation and sampling cadence against original output before claiming animation
fidelity. Presentation interpolation must be labeled and cannot alter engine behavior.

[derived: official pygame-ce documentation, checked 2026-10-17]
[pygame-ce](https://pyga.me/docs/) supplies display, drawing, fonts, events and sprites
for a Python 2D viewer. The implementation preflight selects/tests its optional
version; this plan does not claim the dependency or viewer has shipped.
