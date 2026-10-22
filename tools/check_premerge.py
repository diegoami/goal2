"""[designed: owner, #127, 2026-10-20] The pre-merge checks of one exact, clean commit.

    python3 tools/check_premerge.py --expected-head <full sha> [--no-tests | --slow] [--python PY] [--jobs N]

Checks: the checkout is clean at that commit; no original-game file is tracked (CLAUDE.md
rule 14); Markdown links and JSON parse (tools/check_links.py); every game test module under
goal2/tests, in parallel, on PY (default: this interpreter). [designed: #275] A test whose
optional dependency, original-game file or goal2-archaeology checkout is absent skips with its
reason (goal2/tests/requires.py), so the gate runs anywhere; the skips are counted in the output.
Slow tests run when it counts: [designed: owner, 2026-10-20] automatically when the commit changes
a file the slow tests guard since origin/main (SLOW_PATHS: the engine, the core, the watched and competitive
match, saves, the match view, the dependencies), always with --slow (every milestone candidate),
never with --fast. Task-specific Done-when lines stay separate.
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


# [designed: owner, 2026-10-20] The files whose change makes the slow tests count: what they exercise
# (the vendored engine under the emulator, watched and competitive matches, saves and timing).
# [designed: #316] goal2/core/ and its two test modules: the core runs the original's whole game.
# [designed: T105] the desktop over the core (goal2/desktop/core_*) and its test module run it too.
SLOW_PATHS = re.compile(r"^(goal2/engine/|goal2/core/|goal2/game/(watched|competitive|session_save|campaign_competitive)"
                        r"|goal2/desktop/(watched|competitive|match_view|save|core_)|goal2/tests/(requires\.py$"
                        r"|test_(watched|campaign_competitive|desktop_competitive|pygame_match_view"
                        r"|core_runner_t100|core_screens_t103|core_desktop_t105|core_new_game_t106))"
                        r"|pyproject\.toml$|tools/check_premerge\.py$)")


def slow_changes(base: str = "origin/main") -> list[str] | None:
    """The changed files since the merge base with `base` that the slow tests guard, or None when
    the base cannot be read (then the slow tests run, to be safe)."""
    try:
        files = git("diff", "--name-only", f"{base}...HEAD").split()
    except subprocess.CalledProcessError:
        return None
    return [f for f in files if SLOW_PATHS.match(f)]


def run_module(module: str, python: str, slow: bool) -> tuple[str, int, float, str]:
    # Discovery, not loading by name: it reports a module skipped at import as a skip (#275).
    start = time.monotonic()
    env = {**os.environ, "GOAL2_SLOW": "1" if slow else "0"}
    r = subprocess.run([python, "-m", "unittest", "discover", "-s", "goal2/tests", "-t", ".",
                        "-p", module + ".py"], cwd=ROOT, capture_output=True, text=True, env=env)
    return module, r.returncode, time.monotonic() - start, (r.stdout + r.stderr)[-3000:]


# [designed: #275] Modules whose mutation controls rewrite a tracked source file for a moment
# (tools/probe_watched_pitch.py, goal2/desktop/pygame_viewer.py): they run alone, after the parallel
# batch, so no other module can import a mutated file.
SERIAL = ("test_pitch_observation", "test_pygame_pitch_view")


def check_tests(jobs: int, python: str, slow: bool) -> None:
    modules = sorted(p.stem for p in (ROOT / "goal2" / "tests").glob("test_*.py"))
    batches = [([m for m in modules if m not in SERIAL], jobs)] + [([m], 1) for m in SERIAL if m in modules]
    failed, skipped = [], 0
    results = []
    for batch, workers in batches:
        with ThreadPoolExecutor(max_workers=workers) as pool:
            results += pool.map(lambda m: run_module(m, python, slow), batch)
    for module, code, secs, tail in results:
        ran = re.search(r"Ran (\d+) tests?", tail)
        skips = re.search(r"skipped=(\d+)", tail.splitlines()[-1] if tail.strip() else "")
        if code == 0 and not ran:
            code = 1  # a module that ran nothing at all is broken, not skipped
        skipped += int(skips.group(1)) if skips else 0
        note = f", {skips.group(1)} skipped" if skips else ""
        print(f"{'PASS' if code == 0 else 'FAIL'} goal2.tests.{module} ({secs:.0f} s{note})", flush=True)
        if code:
            failed.append(module)
            print(tail, flush=True)
    print(f"game tests: {len(modules) - len(failed)}/{len(modules)} modules pass, {skipped} tests skipped"
          + ("" if slow else " (slow tests not run)"), flush=True)
    if failed:
        raise ValidationError("failing test modules: " + ", ".join(failed))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--expected-head", required=True, help="full commit SHA being merged")
    tests = parser.add_mutually_exclusive_group()
    tests.add_argument("--no-tests", dest="tests", action="store_false", help="skip the game test modules")
    tests.add_argument("--slow", action="store_true", help="always run the slow tests (milestone candidates)")
    tests.add_argument("--fast", action="store_true", help="never run the slow tests")
    parser.add_argument("--tests", action="store_true", help=argparse.SUPPRESS)  # the default since #275
    parser.add_argument("--python", default=sys.executable, help="interpreter for the game tests")
    parser.add_argument("--jobs", type=int, default=min(8, os.cpu_count() or 2))
    args = parser.parse_args(argv)
    try:
        check_checkout(args.expected_head)
        check_originals()
        subprocess.run([sys.executable, "tools/check_links.py"], cwd=ROOT, check=True)
        if args.tests:
            slow = args.slow
            if not (args.slow or args.fast):
                changed = slow_changes()
                slow = changed is None or bool(changed)
                why = ("origin/main unreadable" if changed is None else
                       f"changed: {', '.join(changed[:5])}{' ...' if len(changed) > 5 else ''}" if changed else
                       "no engine, watched, competitive, save or timing change since origin/main")
                print(f"{'RUN' if slow else 'SKIP'} slow tests ({why})", flush=True)
            check_tests(args.jobs, args.python, slow)
        check_checkout(args.expected_head)  # a check that changed tracked files cannot certify it
    except (ValidationError, OSError, subprocess.CalledProcessError) as exc:
        print(f"FAIL pre-merge validation: {exc}", file=sys.stderr)
        return 1
    print(f"PASS pre-merge validation at {args.expected_head}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
