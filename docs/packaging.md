# The portable Windows build

[designed: owner, 2026-11-02, T147, superseding the Nuitka build of #432 comment 6440424797] goal2 ships for Windows
as a folder that bundles its Pythons instead of freezing goal2: the official embeddable CPython 3.13 runs the UI,
PyPy 3.11 runs the match workers (CLAUDE.md, owner 2026-10-29). The workers and the pitch viewer start as
`python -m ...` subprocesses (`goal2/game/engine_python.py`, `goal2/desktop/jobs.py`, `goal2/desktop/watched.py`),
which a frozen .exe cannot run; bundled interpreters run them unchanged. Nothing of the original game ships
(CLAUDE.md rule 14): the player's own data comes in through T153. No installer, signing or updates. [designed: owner,
2026-11-13, #705] v0.1 is published as this build's ZIP, for a player with their own GOAL.EXE and GOAL.DAT
([its release notes](releases/v0.1.0.md)); the package workflow itself makes no release, tag or publication.

## The folder

`tools/build_portable.py build` lays out `goal2-<version>-win64/` (the version is `pyproject.toml`'s) and zips it:

| Path | What | Why |
|---|---|---|
| `python/` | the embeddable CPython 3.13 | the UI (PySide6) |
| `python/python313._pth` | its entries, plus `Lib\site-packages` and `import site` | the embeddable distribution reaches nothing outside its folder otherwise |
| `python/Lib/site-packages/` | the `desktop`, `watched` and `match-view` extras (`tools/portable/requirements-win64.txt`, with every dependency) and goal2 from its wheel | |
| `pypy/` | the PyPy 3.11 Windows release | the match workers, about four times CPython's speed [confirmed: goal2-archaeology #620, CLAUDE.md 2026-10-29] |
| `pypy/Lib/site-packages/goal2/` | goal2 from the same wheel, nothing else | the workers import only goal2's pure-Python modules; PyPy never sees the UI's packages |
| `pypy/vcruntime140*.dll` | copied from the CPython | [derived: T147, the pinned archive's file list and `pypy.exe`'s import table] `pypy.exe` imports `VCRUNTIME140.dll` but PyPy does not ship it; without it a machine without the Visual C++ runtime cannot start a match |
| `goal2.cmd`, `goal2_launch.py` | the launcher: today's desktop over the core route | below |
| `goal2-new.cmd` | a development build's only (`--development`): the new window's launcher | below |
| `README.txt` | the player's README (`tools/portable/README.txt`, with Windows line ends): what goal2 is, the files needed and where they come from, how to start, where saves live, v0.1's limits | [designed: T225] |
| `portable-files.json` | every file of the folder and its source (`cpython`, `pypy`, `wheels`, `goal2`, `launcher`, `readme`), and the build's kind, `release` or `development` | the original-file and launcher checks |

pip's console-script launchers (`Scripts/`, `bin/` under each site-packages) are left out: they are bound to the
building interpreter's path, and the launcher is `goal2.cmd`.

## Pinned downloads

Every download is pinned by version and SHA-256: the two interpreters in `tools/portable/manifest.json` (python.org's
and pypy.org's published digests), the wheels in `tools/portable/requirements-win64.txt` (PyPI's), installed with
`pip --require-hashes --no-deps --only-binary :all:` for `win_amd64`, CPython 3.13. The build refuses a file whose
SHA-256 differs, also a cached one (`--downloads`, default `.cache/portable-downloads/`), and a requirement without a
version and a hash. Updating an interpreter or a wheel means changing its version and its digest together.

## The launchers

| Launcher | Starts | In |
|---|---|---|
| `goal2.cmd` | today's desktop, `goal2.desktop` (docs/desktop-management.md) | every build: the one this page and the player start with |
| `goal2-new.cmd` | the new window, `goal2.ui` (docs/ui.md) | a development build only (`build --development`), for the owner's playtest |

[designed: main session, 2026-11-13, T225; the owner may overrule on #705] The release build, the default and v0.1's
ZIP, ships `goal2.cmd` only: `goal2-new.cmd`'s first start asks for the Python route's template
`e010-r0008-halftime.sav`, a recorded emulator state no player has, so it would fail for every player. `check-zip`
refuses it in a release ZIP.

[designed: owner, 2026-11-03, T169, docs/design/ui-2026-11 §6 item 17] `goal2.cmd` stays the default until the
Python route plays a whole season (T170): no build plays less than the one before it, and the new window, beside it,
is there for the playtest. The trim that goes with the switch (PySide6 Essentials only, no pygame-ce, the engine under
`pypyw.exe`) waits for it too.
`goal2-new.cmd` is `goal2.cmd` with `--window new` before the player's arguments: the same `goal2_launch.py`, so
the same environment, then `goal2.ui` instead of `goal2.desktop`. Its first start shows S01, which imports the new
window's files (GOAL.DAT and the Python route's template `e010-r0008-halftime.sav`, GOAL.HLP when the folder has
it) into the same data folder as below.

`goal2.cmd` runs `python\pythonw.exe goal2_launch.py` from its own folder (`%~dp0`) with every argument, so it works
from any working directory and from a path with spaces or non-ASCII letters, and returns the desktop's exit status.
`goal2_launch.py` sets, for itself and every worker it starts:

- `GOAL2_ENGINE_PYTHON` to the bundled `pypy\pypy.exe`, which `engine_python()` takes as given;
- `PYTHONSAFEPATH=1`: a worker starts with `-m` in the CPython's site-packages (its working directory), which would
  otherwise come first on PyPy's `sys.path` and give PyPy the UI's packages;
- no `PYTHONPATH`, `PYTHONHOME` or `PYTHONSTARTUP` of the player's machine, and `PYTHONNOUSERSITE=1`;

then runs `goal2.desktop` (or, after a leading `--window new`, `goal2.ui`; `--window desktop` is the default) in
its own process (`runpy`), so `sys.executable` is the bundled `pythonw.exe` for the
quick friendly worker and the pitch viewer.

## Original-game files

A file with an original-game file type (`check_premerge.FORBIDDEN`: `.exe`, `.dat`, `.sav`, ...) is accepted only from
the pinned third-party downloads (the interpreters' executables, Qt's data files), never from goal2's wheel or the
launcher, and the folder must hold exactly the files its record lists. `build_portable.py check-zip ZIP --originals
.cache` applies the same rules to the ZIP and refuses an entry whose bytes equal any original-game file in `.cache/`.

## The package workflow

`.github/workflows/package.yml` runs on the hosted Windows runner, on PRs that touch packaging, on `main` and on
dispatch. It builds the folder and the ZIP, then runs the packaged smoke (`tools/portable/smoke.py`) from the ZIP
unpacked in a folder with spaces and a non-ASCII letter, with only `System32` and its `Wbem` on PATH (no Python, no Git).
Before the smoke, `check-zip` checks the ZIP against `.cache/` (no original-game file, no `goal2-new.cmd` in the
release ZIP) and writes its file list, kept in the run's evidence. The smoke:

1. `goal2.cmd --help` exits 0;
2. the bundled PyPy answers as PyPy 3.11, imports goal2 from its own site-packages when started where a worker is,
   and cannot import PySide6;
3. one watched match played by the bundled CPython with the launcher's environment, its worker under the bundled
   PyPy, equals the same match played from the source tree (`smoke_match.py`); it uses the original files the
   workflow pulls into `.cache/`, outside the folder that gets zipped;
4. [designed: owner, 2026-11-13, #705; T225] the player's path (`smoke_core.py`), offscreen under the bundled CPython
   with the launcher's environment, on a fresh per-user folder: the first start's import dialog
   (`_player_defaults`, what `goal2.cmd` with no argument runs) answered with a stand-in for the player's goal install
   (GOAL.EXE and GOAL.DAT copied from `.cache/` into the work folder, outside the build); a new career on Launch, the
   original's new game booted from the imported GOAL.EXE; then *play next game*, the original's own captain and
   Watch, the match in the pitch window (the bundled pygame-ce, SDL's dummy driver) to full time, each stop answered
   by the round page's own controls, back to the manager menu. An exception in a Qt slot fails it. The match is not
   paced (`CoreModel.pacing` off; T223's wait is the window's, a whole match of wall time a smoke does not need);

and, for a development build only (it has `goal2-new.cmd`):

5. `goal2-new.cmd --help` exits 0;
6. the new window (`smoke_window.py`), offscreen under the bundled CPython with the launcher's environment, on a fresh
   per-user folder: S01 first, a stand-in data folder (GOAL.DAT and the template copied from `.cache/` into the work
   folder, outside the build) imported through S01, then S02 Start; then a new career's first friendly played on S17
   to full time, its worker the bundled PyPy.

It also records whether a worker started from `pythonw.exe` gets a console window. The ZIP is uploaded as the run
artifact `goal2-win64-zip`; the measurements (ZIP size, build time, the packaged matches' times) and the ZIP's file
list as `package-evidence`, kept in `measurements/T147/`. `python3 -m unittest goal2.tests.test_package_t147`'s
`CorePath` runs `smoke_core.py` from the source tree (`GOAL2_SLOW=1`, GOAL.EXE and GOAL.DAT in `.cache/`).

## Building it yourself

On Windows, with CPython 3.13:

```text
python -m pip wheel --no-deps -w dist/wheel .
python tools/build_portable.py build --wheel dist/wheel/goal2-<version>-py3-none-any.whl
```

The folder and the ZIP land in `dist/`. `--development` adds `goal2-new.cmd`.

## The player's data folder

[designed: owner, 2026-11-02, T153] The ZIP holds nothing of the original game; its files come in through a first-run
import (`goal2/desktop/data_setup.py`). The desktop's default start is the core route's new career (`--core-boot`,
docs/desktop-management.md). [designed: owner, 2026-11-13, #705; T222] It needs two files of the player's own copy of
goal (version 2): `GOAL.EXE`, from which the core boots the original to its DOS date call (docs/core.md, "The new
game"), and `GOAL.DAT` [confirmed: F032]. Each is checked against the released file's SHA-256. The recorded emulator
state at the date call (`e039-r0005-date-call.sav`), which the import took before T222, is no longer asked for: a
folder that holds it instead of GOAL.EXE is refused, naming GOAL.EXE.

| Path | What |
|---|---|
| `%LOCALAPPDATA%\goal2\data` (Windows), `~/.local/share/goal2/data` (elsewhere) | the imported files |
| `...\goal2\saves` beside it | the default save, `desktop.g2core` |

Started without `--data` and `--core-boot` (`goal2.cmd` with no arguments), the desktop checks the data folder. If a
file is missing or differs, a dialog asks for a folder holding the files, checks each by SHA-256 against
`data_setup.MANIFEST` (names and digests only, no byte of the files), and copies them into the data folder, each written
beside its final name, checked again and then moved over it. A refused folder is named in plain words, file by file
("GOAL.DAT is missing", "... is not the right file"), and nothing is copied from it; Quit closes goal2. The import
writes only into the data folder: never the folder offered, the saves or the working directory, so a re-import cannot
overwrite a career. [designed: owner, 2026-11-03, #526] The original's help file, `GOAL.HLP`, is taken too when the
folder has it (`data_setup.OPTIONAL`, for the redesigned UI's F1): a wrong one is refused by name like the others, and a
folder without it still imports. Then the desktop starts as with `--core-boot <data>\GOAL.EXE --data <data>\GOAL.DAT
--save <saves>\desktop.g2core`; a second start goes straight in. Every path is absolute.

Explicit arguments still win: `--data` bypasses the import (developers' `.cache/` runs and their `.cache/` default
saves are unchanged), `--save` names another save, and `--resume`, `--core` or `--template` without `--data` take
`GOAL.DAT` from the data folder. A second start opens Launch, whose Saved career panel shows the career saved at the default save
and resumes it (#519); `goal2.cmd --resume <a core save>` opens one directly.

The same import without Qt: `python\python.exe -m goal2.desktop.data_setup FOLDER` (and `--check` to name what the data
folder lacks).
