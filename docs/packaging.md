# The portable Windows build

[designed: owner, 2026-11-02, T147, superseding the Nuitka build of #432 comment 6440424797] goal2 ships for Windows
as a folder that bundles its Pythons instead of freezing goal2: the official embeddable CPython 3.13 runs the UI,
PyPy 3.11 runs the match workers (CLAUDE.md, owner 2026-10-29). The workers and the pitch viewer start as
`python -m ...` subprocesses (`goal2/game/engine_python.py`, `goal2/desktop/jobs.py`, `goal2/desktop/watched.py`),
which a frozen .exe cannot run; bundled interpreters run them unchanged. Nothing of the original game ships
(CLAUDE.md rule 14): the player's own data comes in through T153. No installer, signing or updates; no release is
made from this build yet.

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
| `goal2.cmd`, `goal2_launch.py` | the launcher | below |
| `portable-files.json` | every file of the folder and its source: `cpython`, `pypy`, `wheels`, `goal2`, `launcher` | the original-file checks |

pip's console-script launchers (`Scripts/`, `bin/` under each site-packages) are left out: they are bound to the
building interpreter's path, and the launcher is `goal2.cmd`.

## Pinned downloads

Every download is pinned by version and SHA-256: the two interpreters in `tools/portable/manifest.json` (python.org's
and pypy.org's published digests), the wheels in `tools/portable/requirements-win64.txt` (PyPI's), installed with
`pip --require-hashes --no-deps --only-binary :all:` for `win_amd64`, CPython 3.13. The build refuses a file whose
SHA-256 differs, also a cached one (`--downloads`, default `.cache/portable-downloads/`), and a requirement without a
version and a hash. Updating an interpreter or a wheel means changing its version and its digest together.

## The launcher

`goal2.cmd` runs `python\pythonw.exe goal2_launch.py` from its own folder (`%~dp0`) with every argument, so it works
from any working directory and from a path with spaces or non-ASCII letters, and returns the desktop's exit status.
`goal2_launch.py` sets, for itself and every worker it starts:

- `GOAL2_ENGINE_PYTHON` to the bundled `pypy\pypy.exe`, which `engine_python()` takes as given;
- `PYTHONSAFEPATH=1`: a worker starts with `-m` in the CPython's site-packages (its working directory), which would
  otherwise come first on PyPy's `sys.path` and give PyPy the UI's packages;
- no `PYTHONPATH`, `PYTHONHOME` or `PYTHONSTARTUP` of the player's machine, and `PYTHONNOUSERSITE=1`;

then runs `goal2.desktop` in its own process (`runpy`), so `sys.executable` is the bundled `pythonw.exe` for the
quick friendly worker and the pitch viewer.

## Original-game files

A file with an original-game file type (`check_premerge.FORBIDDEN`: `.exe`, `.dat`, `.sav`, ...) is accepted only from
the pinned third-party downloads (the interpreters' executables, Qt's data files), never from goal2's wheel or the
launcher, and the folder must hold exactly the files its record lists. `build_portable.py check-zip ZIP --originals
.cache` applies the same rules to the ZIP and refuses an entry whose bytes equal any original-game file in `.cache/`.

## The package workflow

`.github/workflows/package.yml` runs on the hosted Windows runner, on PRs that touch packaging, on `main` and on
dispatch. It builds the folder and the ZIP, then runs the packaged smoke (`tools/portable/smoke.py`) from the ZIP
unpacked in a folder with spaces and a non-ASCII letter, with only Windows' own folders on PATH:

1. `goal2.cmd --help` exits 0;
2. the bundled PyPy answers as PyPy 3.11, imports goal2 from its own site-packages when started where a worker is,
   and cannot import PySide6;
3. one watched match played by the bundled CPython with the launcher's environment, its worker under the bundled
   PyPy, equals the same match played from the source tree (`smoke_match.py`); it uses the original files the
   workflow pulls into `.cache/`, outside the folder that gets zipped.

It also records whether a worker started from `pythonw.exe` gets a console window. Then `check-zip` checks the ZIP
against `.cache/`, and the ZIP is uploaded as the run artifact `goal2-win64-zip`; the measurements (ZIP size, build
time, the packaged match's time) as `package-evidence`, kept in `measurements/T147/`.

## Building it yourself

On Windows, with CPython 3.13:

```text
python -m pip wheel --no-deps -w dist/wheel .
python tools/build_portable.py build --wheel dist/wheel/goal2-<version>-py3-none-any.whl
```

The folder and the ZIP land in `dist/`.
