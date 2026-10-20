"""[designed: #275] What a game test needs that a fresh checkout may lack, and the one-line skip.

A test module, class or method that needs an optional dependency (`goal2[desktop,watched,
match-view]`), an original-game file in the git-ignored `.cache/` (docs/artifacts.md), a
goal2-archaeology checkout, or a long run says so here and is skipped with the reason when it is
absent, instead of erroring:

    requires.require(modules=("pygame",))             # at import: skips the whole module
    requires.require(files=("GOAL.DAT",))             # in a test, setUpClass or helper: skips that
    @requires.need(files=("e010-r0008-halftime.sav",))  # one class or method
    @requires.need(slow=True)                         # runs only with GOAL2_SLOW=1

A skip raised at import is reported cleanly by unittest discovery, which is how the gate runs each
module (tools/check_premerge.py):
`python3 -m unittest discover -s goal2/tests -t . -p test_<name>.py`. Each file named is checked
for presence only; the tests that read it keep their own hash checks.
"""
import importlib.util
import os
from pathlib import Path
import sys
import unittest

from goal2.engine.original_match.assets import REFERENCE

ROOT = Path(__file__).resolve().parents[2]
CACHE = ROOT / ".cache"
EXTRAS = {"PySide6": "desktop", "unicorn": "watched", "pygame": "match-view"}
SLOW = os.environ.get("GOAL2_SLOW") == "1"
# The vendored watched-match engine: its emulator and the reference savestate it starts from.
WATCHED = {"modules": ("unicorn",), "files": (REFERENCE["asset"],)}
# The E010 half-time template and GOAL.DAT most campaign and desktop tests open.
HALFTIME = {"files": ("GOAL.DAT", "e010-r0008-halftime.sav")}


def archaeology() -> Path:
    """The goal2-archaeology checkout every test reads, resolved once for all of them as
    tools/check_provenance.py resolves it (`$GOAL2_ARCHAEOLOGY`, a sibling checkout, the
    `.cache/` clone of tools/cloud_setup.sh); the path may not exist."""
    sys.path.insert(0, str(ROOT / "tools"))
    try:
        from check_provenance import _archaeology
    finally:
        sys.path.remove(str(ROOT / "tools"))
    return _archaeology()


def archaeology_path() -> Path | None:
    """The goal2-archaeology checkout, or None when it is absent."""
    try:
        path = archaeology()
    except (OSError, RuntimeError, ValueError):
        return None
    return path if (path / ".git").exists() else None


def absent(modules=(), files=(), generated=None, archaeology=False, slow=False) -> str | None:
    """The one-line reason a requirement is absent, or None when all are present. `generated`
    maps a path under .cache/ to the command that makes it from the files pulled from Drive."""
    for name in modules:
        if importlib.util.find_spec(name) is None:
            return f"optional dependency {name} absent: pip install -e '.[{EXTRAS.get(name, name)}]'"
    missing = [name for name in files if not (CACHE / name).exists()]
    if missing:
        return f"original-game file .cache/{missing[0]} absent: python3 tools/artifacts.py pull"
    for name, command in (generated or {}).items():
        if not (CACHE / name).exists():
            return f"generated file .cache/{name} absent: {command}"
    if archaeology and archaeology_path() is None:
        return "goal2-archaeology checkout absent: set GOAL2_ARCHAEOLOGY, or run tools/cloud_setup.sh"
    if slow and not SLOW:
        return "slow test: set GOAL2_SLOW=1 to run it"
    return None


def require(**needs) -> None:
    """Raise the skip when a requirement is absent: at import it skips the module, in a test,
    setUp, setUpClass or a helper they call it skips that test or class."""
    reason = absent(**needs)
    if reason:
        raise unittest.SkipTest(reason)


def cases(items, keep=1):
    """[designed: owner, 2026-10-20, #275] A batch test's cases: all of them when slow tests run
    (GOAL2_SLOW=1), else the first `keep`, so the default run still plays one real case."""
    items = list(items)
    return items if SLOW else items[:keep]


def need(**needs):
    """Decorator: skip a class or method when a requirement is absent."""
    reason = absent(**needs)
    return unittest.skipIf(reason is not None, reason or "")
