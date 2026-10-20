"""[designed: owner, #127, 2026-10-20] The pre-merge checks of one exact, clean commit.

    python3 tools/check_premerge.py --expected-head <full sha> [--tests [--python PY] [--jobs N]]

Checks: the checkout is clean at that commit; no original-game file is tracked (CLAUDE.md
rule 14); Markdown links and JSON parse (tools/check_links.py). With --tests, every game test
module under goal2/tests too, in parallel, on PY (default: this interpreter). The game tests are
opt-in until they skip cleanly without the optional dependencies and the original-game files in
.cache/ (goal2 #275). Task-specific Done-when lines stay separate.
"""
from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor
import os
from pathlib import Path
import re
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
# The original game's file types, and rebuild saves that embed its bytes (rule 14).
FORBIDDEN = {".exe", ".dat", ".hlp", ".hil", ".pif", ".bat", ".sav", ".gl", ".g2save"}


class ValidationError(ValueError):
    """A mandatory check failed."""


def git(*args: str) -> str:
    return subprocess.run(["git", *args], cwd=ROOT, check=True, capture_output=True, text=True).stdout


def check_checkout(expected_head: str) -> None:
    if not re.fullmatch(r"[0-9a-f]{40}", expected_head):
        raise ValidationError("--expected-head must be a full lowercase 40-character commit SHA")
    actual = git("rev-parse", "HEAD").strip()
    if actual != expected_head:
        raise ValidationError(f"HEAD mismatch: expected {expected_head}, got {actual}")
    if git("status", "--porcelain", "--untracked-files=no").strip():
        raise ValidationError("tracked checkout is dirty; commit changes before validating")


def check_originals() -> None:
    bad = [n for n in git("ls-files", "-z").split("\0") if Path(n).suffix.lower() in FORBIDDEN]
    if bad:
        raise ValidationError("tracked original-game files: " + ", ".join(bad))
    print("PASS original-asset exclusion", flush=True)


def run_module(module: str, python: str) -> tuple[str, int, float, str]:
    start = time.monotonic()
    r = subprocess.run([python, "-m", "unittest", "-q", module], cwd=ROOT,
                       capture_output=True, text=True)
    return module, r.returncode, time.monotonic() - start, (r.stdout + r.stderr)[-3000:]


def check_tests(jobs: int, python: str) -> None:
    modules = sorted(f"goal2.tests.{p.stem}" for p in (ROOT / "goal2" / "tests").glob("test_*.py"))
    failed = []
    with ThreadPoolExecutor(max_workers=jobs) as pool:
        for module, code, secs, tail in pool.map(lambda m: run_module(m, python), modules):
            print(f"{'PASS' if code == 0 else 'FAIL'} {module} ({secs:.0f} s)", flush=True)
            if code:
                failed.append(module)
                print(tail, flush=True)
    if failed:
        raise ValidationError("failing test modules: " + ", ".join(failed))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--expected-head", required=True, help="full commit SHA being merged")
    parser.add_argument("--tests", action="store_true", help="also run the game test modules")
    parser.add_argument("--python", default=sys.executable, help="interpreter for the game tests")
    parser.add_argument("--jobs", type=int, default=min(8, os.cpu_count() or 2))
    args = parser.parse_args(argv)
    try:
        check_checkout(args.expected_head)
        check_originals()
        subprocess.run([sys.executable, "tools/check_links.py"], cwd=ROOT, check=True)
        if args.tests:
            check_tests(args.jobs, args.python)
        check_checkout(args.expected_head)  # a check that changed tracked files cannot certify it
    except (ValidationError, OSError, subprocess.CalledProcessError) as exc:
        print(f"FAIL pre-merge validation: {exc}", file=sys.stderr)
        return 1
    print(f"PASS pre-merge validation at {args.expected_head}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
