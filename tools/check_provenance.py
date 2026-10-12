#!/usr/bin/env python3
"""Every file under `goal2/engine/` must have a PROVENANCE row whose source commit exists
in goal2-archaeology (CLAUDE.md rule 18). Exit 0 on success, non-zero on any mismatch.

The PROVENANCE.md columns are: `File`, `Source repo`, `Source commit`, `Findings`, `Vendored`.
The script parses the table, walks the vendored directory recursively (every file under it
must have a row, and vice versa: a row must point at a real file under `goal2/engine/`),
and that the source commit exists in the archaeology checkout (`$GOAL2_ARCHAEOLOGY` or a
sibling/grandparent default).

[designed: the table parser is a small hand-rolled reader, not a Markdown library, so the
script has no third-party dependency and runs the same on every host.]
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PROVENANCE = ROOT / "PROVENANCE.md"
ENGINE = ROOT / "goal2" / "engine"
DEFAULT_ARCHAEOLOGY = ROOT.parent / "goal2-archaeology"


def _archaeology() -> Path:
    """Resolve the goal2-archaeology checkout path.

    Order: `$GOAL2_ARCHAEOLOGY`, the sibling of the main checkout (when run from there),
    the grandparent of a worktree under `<repo>-work/<name>/`, or the path's parent.
    [designed: looks for the archaeology checkout by walking up from the worktree or main
    checkout. The user can override with `$GOAL2_ARCHAEOLOGY` for unusual layouts.]
    """
    env = os.environ.get("GOAL2_ARCHAEOLOGY")
    if env:
        return Path(env)
    candidates = [
        DEFAULT_ARCHAEOLOGY,                              # sibling of the main checkout
        ROOT.parent.parent / "goal2-archaeology",         # grandparent of a worktree
        ROOT.parent / "goal2-archaeology",                # last resort
    ]
    for c in candidates:
        if (c / ".git").exists():
            return c
    return DEFAULT_ARCHAEOLOGY


def _parse_table(text: str) -> list[dict]:
    """The PROVENANCE table; ignores the empty placeholder row."""
    rows: list[dict] = []
    for line in text.splitlines():
        line = line.strip()
        if not line.startswith("|") or set(line.replace("|", "").strip()) <= {"-", " "}:
            continue
        cells = [c.strip() for c in line.strip("|").split("|")]
        if len(cells) != 5:
            continue
        if cells[0] == "File":  # header
            continue
        if cells[0].startswith("_(empty"):
            continue
        rows.append({
            "file": cells[0],
            "repo": cells[1],
            "commit": cells[2],
            "findings": cells[3],
            "vendored": cells[4],
        })
    return rows


def _commit_exists(archaeology: Path, repo: str, commit: str) -> bool:
    """Does the commit exist in the archaeology checkout? (`git cat-file -e <commit>`.)"""
    if not (archaeology / ".git").is_dir():
        print(f"error: {archaeology}: not a git checkout (set $GOAL2_ARCHAEOLOGY)", file=sys.stderr)
        return False
    if not commit or not all(c in "0123456789abcdef" for c in commit):
        print(f"error: {commit!r} is not a hex sha", file=sys.stderr)
        return False
    r = subprocess.run(
        ["git", "cat-file", "-e", f"{commit}^{{commit}}"],
        cwd=str(archaeology),
        capture_output=True,
    )
    return r.returncode == 0


def _normalize(path: str) -> str:
    """A canonical POSIX-style path: each component is preserved; only a single leading
    `./` is stripped (a `lstrip("./")` would remove arbitrary leading dots and slashes,
    normalising `.goal2/engine/x` to `goal2/engine/x` and matching a real file)."""
    p = str(Path(path)).replace("\\", "/")
    if p.startswith("./"):
        p = p[2:]
    return p


def _under_engine(path: str) -> bool:
    """The path's first component is `goal2`, the second is `engine`, and the rest is
    an actual subpath of it. A row pointing outside `goal2/engine/` is rejected."""
    parts = Path(_normalize(path)).parts
    return len(parts) >= 2 and parts[0] == "goal2" and parts[1] == "engine"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.parse_args(argv)
    if not PROVENANCE.is_file():
        print(f"error: {PROVENANCE}: not a file", file=sys.stderr)
        return 2
    if not ENGINE.is_dir():
        print(f"error: {ENGINE}: not a directory", file=sys.stderr)
        return 2

    rows = _parse_table(PROVENANCE.read_text())
    failures: list[str] = []
    # The "File" column is a path. A row covers a vendored file when its canonical path
    # matches a vendored path, AND the row's path is actually under `goal2/engine/`
    # (a row pointing somewhere else cannot authorize a vendored file, even if the
    # path normalises to the same string).
    by_row_path: dict[str, dict] = {}
    for r in rows:
        norm = _normalize(r["file"])
        if not _under_engine(norm):
            failures.append(f"{r['file']}: PROVENANCE row points outside goal2/engine/")
            continue
        by_row_path[norm] = r

    # Walk the vendored directory recursively (R1: nested files must also have a row).
    # Generated Python artifacts (`__pycache__/`, `*.pyc`) are excluded — they are produced
    # by the interpreter when the engine modules are imported, never vendored, and
    # `.gitignore` already covers them. The vendored directory holds source files only.
    def _is_vendored(p: Path) -> bool:
        if not p.is_file():
            return False
        parts = set(p.relative_to(ENGINE).parts)
        return not (parts & {"__pycache__"} or p.suffix == ".pyc")

    files = sorted(p for p in ENGINE.rglob("*") if _is_vendored(p))
    if not files:
        print(f"error: {ENGINE} is empty; vendor files before checking provenance", file=sys.stderr)
        return 2
    seen: set[str] = set()
    archaeology = _archaeology()
    for path in files:
        # The repo-relative path under ROOT, normalised (R2: same-basename collisions are
        # distinguishable by path).
        rel = path.relative_to(ROOT)
        seen.add(_normalize(rel))
        row = by_row_path.get(_normalize(rel))
        if row is None:
            failures.append(f"{rel}: no PROVENANCE row")
            continue
        if not _commit_exists(archaeology, row["repo"], row["commit"]):
            failures.append(f"{rel}: source commit {row['commit']} not in {archaeology}")
    for r in rows:
        norm = _normalize(r["file"])
        if norm not in seen and not r["file"].startswith("_"):
            failures.append(f"{r['file']}: PROVENANCE row but no file under {ENGINE}")

    if failures:
        print("provenance check failed:", file=sys.stderr)
        for f in failures:
            print(f"  {f}", file=sys.stderr)
        return 1
    print(f"provenance check: {len(files)} file(s) OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
