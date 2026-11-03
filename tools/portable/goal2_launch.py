"""[designed: owner, 2026-11-02, T147] The portable build's launcher, run by goal2.cmd under the bundled CPython's
pythonw.exe: it gives the match workers the bundled PyPy and starts the desktop (`-m goal2.desktop`) in this process,
with every argument passed through (docs/packaging.md).
[designed: owner, 2026-11-03, T169, design README §6 item 17] goal2-new.cmd runs it with `--window new` first: the
same environment, then the new window (`-m goal2.ui`) instead. Without `--window` it is today's desktop, the default
until T170.

The folder it sits in is the build's root (`python/`, `pypy/`, `goal2.cmd`, this file), whatever the working directory.
The environment it sets is inherited by every worker:
- GOAL2_ENGINE_PYTHON: the bundled `pypy\\pypy.exe` (goal2/game/engine_python.py takes it as given).
- PYTHONSAFEPATH=1: a worker starts with `-m` in the CPython's site-packages (goal2/game/watched_jobs.py's cwd), which
  `-m` would put first on PyPy's sys.path; without it PyPy would import goal2 from the UI's site-packages instead of
  its own copy [designed: T147, hazard "PyPy picking up the UI's site-packages"]. The embeddable CPython ignores it
  (its `._pth` file fixes its path).
- PYTHONPATH, PYTHONHOME and PYTHONSTARTUP of the player's machine are dropped, and the user site is off
  (PYTHONNOUSERSITE=1), so another Python installed there cannot reach the bundled PyPy.
"""
from __future__ import annotations

import os
import runpy
import sys
from pathlib import Path

ENGINE = ("pypy", "pypy.exe")
DROPPED = ("PYTHONPATH", "PYTHONHOME", "PYTHONSTARTUP")
WINDOWS = {"desktop": "goal2.desktop", "new": "goal2.ui"}
MODULE = WINDOWS["desktop"]


def environment(root, env) -> dict:
    """`env` as the launcher leaves it for a build rooted at `root`."""
    out = {k: v for k, v in env.items() if k.upper() not in DROPPED}
    out["GOAL2_ENGINE_PYTHON"] = str(Path(root).joinpath(*ENGINE))
    out["PYTHONSAFEPATH"] = "1"
    out["PYTHONNOUSERSITE"] = "1"
    return out


def window(args) -> tuple[str, list]:
    """The module to run and its arguments: a leading `--window desktop|new` (the launcher's own, from goal2-new.cmd)
    picks the module and is taken off; without it, the desktop with every argument."""
    args = list(args)
    if args[:1] != ["--window"]:
        return MODULE, args
    if len(args) < 2 or args[1] not in WINDOWS:
        raise SystemExit(f"goal2_launch.py: --window takes one of {', '.join(WINDOWS)}")
    return WINDOWS[args[1]], args[2:]


def main(argv=None, root=None, run=runpy.run_module):
    """Set this process's environment for the build at `root` (default: this file's folder) and run the module
    `--window` picks (default: the desktop) with the rest of `argv` (default: this process's arguments)."""
    root = Path(root) if root is not None else Path(__file__).resolve().parent
    module, args = window(sys.argv[1:] if argv is None else argv)
    new = environment(root, os.environ)
    for key in [k for k in os.environ if k not in new]:
        del os.environ[key]
    os.environ.update(new)
    sys.argv = [module] + args
    return run(module, run_name="__main__", alter_sys=True)


if __name__ == "__main__":
    main()
