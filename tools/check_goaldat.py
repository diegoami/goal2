#!/usr/bin/env python3
"""`tools/check_goaldat.py <path to GOAL.DAT>` — exit 0 on a well-formed file.

A thin CLI over `goal2.data.goaldat.run_checks`; the library form is what
tests use, the script form is what CI and humans run.
[designed: the script mirrors `python -m goal2.data --check`; the duplication
keeps the script callable from a fresh checkout without the package on
sys.path (the script adjusts sys.path before importing).]
"""
from __future__ import annotations

import os
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from goal2.data.goaldat import run_checks  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if len(argv) != 1:
        print(__doc__, file=sys.stderr)
        return 2
    path = Path(argv[0])
    if not path.is_file():
        print(f"error: {path}: not a file", file=sys.stderr)
        return 2
    data = path.read_bytes()
    try:
        checks = run_checks(data)
    except ValueError as e:
        print(f"error: {e}", file=sys.stderr)
        return 1
    failed = 0
    for cid, ok, text in checks:
        mark = "OK  " if ok else "FAIL"
        print(f"{cid} {mark} {text}")
        if not ok:
            failed += 1
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
