"""[designed: owner, 2026-10-29, CLAUDE.md; T152] The interpreter that runs the match engine's worker processes.

The sealed port is plain Python; under PyPy 3.11 it plays the same matches about four times faster than under
CPython [confirmed: goal2-archaeology #620: E034-03's drive, F40 and T79's 700 matches identical on PyPy]. The UI
(PySide6) stays on CPython; only the watched and competitive match workers start under PyPy. The choice:
GOAL2_ENGINE_PYTHON when set, as given (it can name CPython too); else the first that answers as PyPy 3.11 of
`pypy3.11` on PATH and uv's managed PyPy 3.11; else this interpreter (sys.executable), as before T152.
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
from functools import lru_cache
from pathlib import Path

PROBE = "import platform,sys;print(platform.python_implementation(),*sys.version_info[:2])"
WANT = "PyPy 3 11"


def _is_pypy311(path) -> bool:
    try:
        r = subprocess.run([str(path), "-c", PROBE], capture_output=True, text=True, timeout=30,
                           stdin=subprocess.DEVNULL)
    except (OSError, subprocess.SubprocessError):
        return False
    return r.returncode == 0 and r.stdout.strip() == WANT


def _uv_pythons():
    """uv's managed PyPy 3.11 installations (`uv python install pypy@3.11`)."""
    roots = [Path(os.environ["UV_PYTHON_INSTALL_DIR"])] if os.environ.get("UV_PYTHON_INSTALL_DIR") else []
    roots += [Path.home() / ".local/share/uv/python",
              Path(os.environ.get("APPDATA", Path.home() / "AppData/Roaming")) / "uv/python"]
    for root in roots:
        for folder in sorted(root.glob("pypy-3.11*"), reverse=True):
            for name in ("bin/pypy3.11", "pypy3.11.exe", "pypy.exe", "python.exe"):
                if (folder / name).is_file():
                    yield folder / name


@lru_cache(maxsize=None)
def engine_python() -> str:
    """The worker's interpreter (see the module's docstring)."""
    configured = os.environ.get("GOAL2_ENGINE_PYTHON")
    if configured:
        return configured
    for candidate in [shutil.which("pypy3.11")] + list(_uv_pythons()):
        if candidate and _is_pypy311(candidate):
            return str(candidate)
    return sys.executable


def worker_command(module: str) -> list[str]:
    return [engine_python(), "-m", module]
