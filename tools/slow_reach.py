"""[designed: owner, 2026-11-01, #505] Which test modules' slow tests a change can affect.

    python3 tools/slow_reach.py FILE...        # the test modules each changed file reaches

The map is computed, never kept by hand: the static import graph of goal2/ and tools/. An edge is an `import`
or `from ... import` (relative ones resolved; `from package import name` also reaches the submodule `name`), a
tools/ module imported by its bare name (the tests put tools/ on sys.path), and a string constant naming a goal2
module (`-m goal2.desktop.worker`, worker_command('goal2.game.watched_worker')): a worker started by name runs
that code too. Importing a module also runs its packages' __init__.py. A test module reaches the files of its
transitive closure; a changed file affects the test modules whose closure holds it. A changed non-Python file
(a table, a JSON) is read by code that need not sit beside it (goal2/engine/tables/ by goal2/game/engine_tables.py
and the port), so it affects every test module that reaches its top-level package (goal2/engine/, goal2/core/, ...),
or, for a file under tools/, the tools/ modules that name it (any tools/ module when none does). pyproject.toml, goal2/tests/requires.py and goal2/tests/__init__.py reach
every test module, and so does a file that cannot be parsed (the graph is then unknown).
[designed: #505] goal2/tests/__init__.py runs in every test process, but what it imports (the #500 guard, which
refuses the port in the test process) is not code a test exercises: its imports are no edges, or every test
would reach the engine and its interpreter choice. A change to the file itself still reaches every module.
"""
from __future__ import annotations

import ast
from functools import lru_cache
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
GUARD = "goal2/tests/__init__.py"
EVERYTHING = {"pyproject.toml", "goal2/tests/requires.py", GUARD}
NAMED = re.compile(r"\bgoal2(?:\.\w+)+")


class Graph:
    def __init__(self, root: Path = ROOT):
        self.root = root
        self.files = {p.relative_to(root).as_posix() for d in ("goal2", "tools") for p in (root / d).rglob("*.py")}
        self.modules = {self._module(f): f for f in self.files if f.startswith("goal2/")}
        self.tools = {Path(f).stem: f for f in self.files if f.startswith("tools/") and f.count("/") == 1}
        self.broken: set[str] = set()
        self.edges = {f: (set() if f == GUARD else self._edges(f)) for f in self.files}

    @staticmethod
    def _module(path: str) -> str:
        parts = path[:-3].split("/")
        return ".".join(parts[:-1] if parts[-1] == "__init__" else parts)

    def _file(self, module: str) -> str | None:
        """The file of `module`, or of its nearest enclosing module (goal2.a.b.attr -> goal2/a/b.py)."""
        parts = module.split(".")
        while parts:
            found = self.modules.get(".".join(parts))
            if found:
                return found
            parts.pop()
        return None

    def _with_packages(self, path: str) -> set[str]:
        out, parts = {path}, path.split("/")[:-1]
        for i in range(1, len(parts) + 1):
            init = "/".join(parts[:i]) + "/__init__.py"
            if init in self.files:
                out.add(init)
        return out

    def _edges(self, path: str) -> set[str]:
        try:
            tree = ast.parse((self.root / path).read_text(), path)
        except (SyntaxError, ValueError, UnicodeDecodeError):
            self.broken.add(path)
            return set()
        here = self._module(path) if path.startswith("goal2/") else None
        package = here if path.endswith("__init__.py") else (here.rsplit(".", 1)[0] if here else None)
        names: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                names.update(a.name for a in node.names)
            elif isinstance(node, ast.ImportFrom):
                base = node.module or ""
                if node.level and package:
                    up = package.split(".")[:len(package.split(".")) - node.level + 1]
                    base = ".".join(up + ([base] if base else []))
                if base:
                    names.add(base)
                    names.update(f"{base}.{a.name}" for a in node.names)
            elif isinstance(node, ast.Constant) and isinstance(node.value, str):
                names.update(NAMED.findall(node.value))
        out: set[str] = set()
        for name in names:
            if name.startswith("goal2"):
                found = self._file(name)
                if found:
                    out |= self._with_packages(found)
            elif name.split(".")[0] in self.tools:
                out.add(self.tools[name.split(".")[0]])
        out.discard(path)
        return out

    @lru_cache(maxsize=None)
    def closure(self, path: str) -> frozenset[str]:
        seen, todo = set(), [path]
        while todo:
            f = todo.pop()
            if f not in seen:
                seen.add(f)
                todo.extend(self.edges.get(f, ()))
        return frozenset(seen)

    def tests(self) -> list[str]:
        return sorted(f for f in self.files if re.fullmatch(r"goal2/tests/test_\w+\.py", f))

    def affected(self, changed: list[str]) -> set[str]:
        """The test module names (test_x) whose slow tests the changed files can affect."""
        tests = self.tests()
        everything = {Path(t).stem for t in tests}
        if self.broken or any(f in EVERYTHING for f in changed):
            return everything
        hit: set[str] = set()
        for f in changed:
            if f.endswith(".py"):
                hit |= {Path(t).stem for t in tests if f in self.closure(t)}
            elif f.startswith(("goal2/", "tools/")):
                parts = f.split("/")
                if parts[0] == "tools":
                    readers = {g for g in self.tools.values() if parts[-1] in (self.root / g).read_text()}
                    near = readers or set(self.tools.values())
                    hit |= {Path(t).stem for t in tests if near & self.closure(t)}
                else:
                    area = "/".join(parts[:2]) + "/" if len(parts) > 2 else "goal2/"
                    hit |= {Path(t).stem for t in tests if any(g.startswith(area) for g in self.closure(t))}
        return hit


def main(argv: list[str] | None = None) -> int:
    changed = sys.argv[1:] if argv is None else argv
    graph = Graph()
    for f in changed:
        print(f"{f}: {' '.join(sorted(graph.affected([f]))) or '-'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
