"""The `python -m goal2.data` entry point.

    python -m goal2.data --check <path to GOAL.DAT>

Runs the R001–R011 block-shape checks against the file at `<path>` and exits
0 when every check passes, non-zero otherwise. The output is one line per
check: `R001 OK  …`, `R001 FAIL …`, etc.

[designed: a thin wrapper around `goal2.data.goaldat.run_checks`.]
[confirmed: the R001–R011 checks are F002's; the one-line-per-check output
format is what `tools/static/goaldat.py` in goal2-archaeology produces.]
"""
from __future__ import annotations

import argparse
import sys

from .goaldat import run_checks


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        prog="python -m goal2.data",
        description="goal2 data utilities: check a GOAL.DAT against F002's block shape.",
    )
    ap.add_argument("--check", type=str, metavar="PATH",
                    help="Run the R001–R011 block-shape checks against the file at PATH.")
    args = ap.parse_args(argv)
    if args.check is None:
        ap.print_help()
        return 1
    with open(args.check, "rb") as f:
        data = f.read()
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
