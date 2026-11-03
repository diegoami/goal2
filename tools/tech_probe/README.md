# tools/tech_probe: T158's throwaway prototypes and probes

[designed: T158, #527] The prototypes and measurements behind
[docs/design/technology-2026-11/README.md](../../docs/design/technology-2026-11/README.md). Nothing of goal2 imports
them. They stay here until the owner decides on #527, and are deleted after the decision (the task's hazard: a
prototype that grows into the product).

## The prototypes

Each draws the same two screens of the approved design ([docs/design/ui-2026-11](../../docs/design/ui-2026-11/README.md)):
**S06 the manager's desk** and **S16 choose your captain**, then the **kick-off** of S17 (the pitch in the window,
commentary beside it, the ball moving to show the frame rate). Palette and font are the design's. Keys: on the desk
↑↓ and Enter (*play next game* opens the captain; the other options and Space, T, F1, F3, F4, F7, F10 say they are not
in the prototype); on the captain ↑↓, Enter kicks off with the highlighted player, C with the computer's pick; Esc goes
back to the desk (a prototype convenience). The mouse: a click on an option, a player or the Enter button does what the
key does.

Run them from the repository root. On Linux with goal2's virtual environment (PySide6 and pygame-ce are goal2's
`desktop` and `match-view` extras); on Windows with the portable build's own CPython (docs/packaging.md), unpacked in
`<portable>`:

| Prototype | Linux | Windows |
| --- | --- | --- |
| PySide6 | `python tools/tech_probe/qt_probe.py` | `<portable>\python\python.exe tools\tech_probe\qt_probe.py` |
| pygame-ce | `python tools/tech_probe/pygame_probe.py` | `<portable>\python\python.exe tools\tech_probe\pygame_probe.py` |
| web page in the browser | `python tools/tech_probe/web_probe.py --shell browser` (Chrome or Chromium; `T158_CHROME` names its binary) | `<portable>\python\python.exe tools\tech_probe\web_probe.py --shell browser` (Edge) |
| web page in a desktop shell | `T158_EXTRA_PATH=<pywebview folder> python tools/tech_probe/web_probe.py --shell webview` | `set T158_EXTRA_PATH=<pywebview folder>` then `<portable>\python\python.exe tools\tech_probe\web_probe.py --shell webview` |

The web shell needs pywebview, which goal2 does not depend on: `python -m pip install --target <pywebview folder>
pywebview` (on Linux add `qtpy`: pywebview then uses goal2's PySide6 QtWebEngine). Every prototype also takes
`--quit-after S` (quit S seconds after the first frame) and prints `READY <s>` when its first frame is on screen;
`qt_probe.py` and `pygame_probe.py` take `--screenshot DIR`.

## The probes

| Script | What |
| --- | --- |
| `measure.py ui` | start time and memory of a prototype's whole process tree, `--runs` times |
| `measure.py sizes` | bytes on disk and in the ZIP of every part of an unpacked portable folder |
| `measure.py capture` | (Windows) a picture of a prototype's window |
| `engine_probe.py speed` | whole matches in fresh processes: PyPy, CPython, goal2rust's hybrid under CPython |
| `engine_probe.py channel` | today's file channel, a long-lived PyPy process over a pipe (`pipe_child.py`), the hybrid on a thread |
| `summarize.py` | the document's tables, from `measurements/T158/*.json` |

`match_child.py`, `file_child.py` and `pipe_child.py` are the probes' child processes; `common.py` holds the shared
helpers (the load at each measurement, goal2rust's installation over goal2's vendored kit); `screens.py` the
prototypes' content. The engine probes need the reference savestate in a cache folder (`--cache`, as
`tools/portable/smoke_match.py`), PyPy 3.11 (`--pypy`) and, for the hybrid, a CPython with goal2rust installed
(`--rust-python`; build it as goal2rust's `engine/README.md` says).
