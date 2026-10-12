#!/usr/bin/env python3
"""Every file under `goal2/engine/` must have a PROVENANCE row whose source commit exists
in goal2-archaeology (CLAUDE.md rule 18). Exit 0 on success, non-zero on any mismatch.

The PROVENANCE.md columns are: `File`, `Source repo`, `Source commit`, `Findings`, `Vendored`.
The script parses the table, checks every file in `goal2/engine/` is listed, and that
the source commit exists in the archaeology checkout (the goal2-archaeology sibling
checkout by default, or `$GOAL2_ARCHAEOLOGY`).
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
    # The "File" column is the path the row is about; the row covers a file in `goal2/engine/`
    # when its basename matches. The full path is kept in the table for readability.
    by_basename = {Path(r["file"]).name: r for r in rows}

    failures: list[str] = []
    files = sorted(p for p in ENGINE.iterdir() if p.is_file())
    if not files:
        print(f"error: {ENGINE} is empty; vendor files before checking provenance", file=sys.stderr)
        return 2
    seen: set[str] = set()
    for path in files:
        seen.add(path.name)
        if path.name not in by_basename:
            failures.append(f"{path.name}: no PROVENANCE row")
            continue
        row = by_basename[path.name]
        archaeology = _archaeology()
        if not _commit_exists(archaeology, row["repo"], row["commit"]):
            failures.append(f"{path.name}: source commit {row['commit']} not in {archaeology}")
    for r in rows:
        if Path(r["file"]).name not in seen and not r["file"].startswith("_"):
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
