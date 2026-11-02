"""[designed: owner, #127, 2026-10-20] The pre-merge checks of one exact, clean commit.

    python3 tools/check_premerge.py --expected-head <full sha> [--no-tests | --slow | --fast | --batch-fast] [--python PY] [--jobs N]

Checks: the checkout is clean at that commit; no original-game file is tracked (CLAUDE.md
rule 14); Markdown links and JSON parse (tools/check_links.py); every game test module under
goal2/tests, in parallel, on PY (default: this interpreter). [designed: #275] A test whose
optional dependency, original-game file or goal2-archaeology checkout is absent skips with its
reason (goal2/tests/requires.py), so the gate runs anywhere; the skips are counted in the output.
Slow tests run when it counts: [designed: owner, 2026-10-20] automatically when the commit changes
a file the slow tests guard since origin/main (SLOW_PATHS: the engine, the core, the watched and competitive
match, saves, the match view, the dependencies), always with --slow (every milestone candidate, a dispatch
of the slow workflows), never with --fast. [designed: owner, 2026-11-01, #505] Automatically, only in the test modules
those files can reach (tools/slow_reach.py: the import graph); every other module runs its fast tests. [designed: owner, 2026-10-29, T145] The cheap layout and page-reserve modules
(LAYOUT_FIRST) run first, with their slow tests unless --fast, and a failure there ends the gate
before the full batch. [designed: owner, 2026-11-01] --batch-fast keeps the layout stage's slow tests and never
runs the full batch's: CI's PR and main runs, whose 4-CPU runners took hours over the port's matches, while the
local gate plays them all. Task-specific Done-when lines stay separate.
"""
from __future__ import annotations

import argparse
from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait
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
SLOW_PATHS = re.compile(r"^(goal2/engine/|goal2/core/|goal2/game/(watched|competitive|session_save|campaign_competitive|engine_)"
                        r"|goal2/desktop/(watched|competitive|match_view|pygame_viewer|save|core_"
                        r"|squad_page|pool_page|player_card|roster|overview_page"      # [T107] the core pages' builders
                        r"|fixtures_page|bench_page|bulletin_page|bracket_page)"         # [T108/T110/T111] pages
                        r"|goal2/tests/(requires\.py$|port_parity\.py$"
                        r"|test_(watched|campaign_competitive|desktop_competitive|pygame_match_view|port_route|pypy_worker"
                        r"|core_runner_t100|core_screens_t103|core_desktop_t105|core_new_game_t106|core_team_t107"
                        r"|core_round_t108|core_watch_t109|core_bulletin_t110|core_continuation_t111|core_world_t113"
                        r"|core_lineup_t114|core_pause_t115|core_playback_t116|core_shootout_t118|core_walkoff_363|core_extra_t119|core_nice_try_371|core_takers_t120|core_save_t121|core_patches_t122|core_best_place_395|core_congratulations_409|core_cycle_t123))"
                        r"|pyproject\.toml$|tools/(watched_evidence|prove_core_cycle|verify_core_cycle)\.py$|tools/watched-kit-hashes\.json$)")
# [designed: owner, 2026-11-01, #505] Not the CI plumbing (this gate, tools/ci_changes.py, tools/slow_reach.py, the
# slow workflows): their own fast tests check them, and a full slow run of them is a dispatch.


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
    output = r.stdout + r.stderr
    # [designed: #377] Cleanup tracebacks can bury the originating test failure.
    # Keep every failed module's output in the gate/CI log; abbreviate successes only.
    return module, r.returncode, time.monotonic() - start, output if r.returncode else output[-3000:]


# [designed: #275] Modules whose mutation controls rewrite a tracked source file for a moment
# (tools/probe_watched_pitch.py, goal2/desktop/pygame_viewer.py): they run alone, after the parallel
# batch, so no other module can import a mutated file. Native focus tests also
# own shared desktop/foreground state and must not compete with other GUI modules.
SERIAL = ("test_pitch_observation", "test_pygame_pitch_view", "test_core_match_window_t138", "test_core_halftime_t139", "test_core_replay_t140")


# [designed: owner, 2026-10-29, T145] Layout and page-reserve modules that are cheap with their slow
# tests: they run first, slow tests on unless --fast, and a failure ends the gate before the full batch
# (Windows run 40785633279 reported an 8 s reserve failure after about an hour). Chosen from the
# modules that check page bounds or the 90 % reserve, by their measured slow-run time
# (measurements/T145/); the SERIAL ones stay in their own stage, and T121, whose F7 keyboard case
# lost focus among them on native Windows (#475), stays in the full batch.
LAYOUT_FIRST = ("test_core_bulletin_t110", "test_core_team_back_t141", "test_core_pool_compare_t134",
                "test_core_world_t113", "test_core_best_place_395", "test_core_extra_t119",
                "test_core_lineup_t114", "test_core_team_t107", "test_core_continuation_t111",
                "test_core_desktop_t105", "test_core_takers_t120")


def report(results: list, failed: list[str]) -> int:
    """Print each module's result, adding failures to `failed`; return the skipped-test count."""
    skipped = 0
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
    return skipped


# [designed: owner, 2026-11-01, #498] A slow run lasts hours: each module's result is printed as it finishes,
# and while none finishes, every PROGRESS_S seconds a line names the modules still running and for how long.
PROGRESS_S = 300


def run_stage(modules: list[str], workers: int, run, failed: list[str], done: list[int], total: int) -> int:
    """Run `modules` on `workers` threads, reporting each as it finishes; return the skipped-test count.
    `done` is the gate's running count of finished modules, out of `total`."""
    started: dict[str, float] = {}

    def timed(module):
        started[module] = time.monotonic()
        return run(module)
    skipped = 0
    with ThreadPoolExecutor(max_workers=workers) as pool:
        pending = {pool.submit(timed, m): m for m in modules}
        while pending:
            finished, _ = wait(pending, timeout=PROGRESS_S, return_when=FIRST_COMPLETED)
            for future in finished:
                del pending[future]
                done[0] += 1
                skipped += report([future.result()], failed)
            if not finished:
                now = time.monotonic()
                running = sorted((m for m in pending.values() if m in started), key=started.get)
                print(f"running {len(running)}: " + ", ".join(f"{m} ({(now - started[m]) / 60:.0f} min)"
                      for m in running) + f"; {done[0]}/{total} modules done", flush=True)
    return skipped


def check_tests(jobs: int, python: str, slow: bool | set[str], runner=run_module, layout_slow: bool = True) -> None:
    """`slow`: every module's slow tests (True), none (False), or only these modules' (#505)."""
    modules = sorted(p.stem for p in (ROOT / "goal2" / "tests").glob("test_*.py"))
    layout = [m for m in LAYOUT_FIRST if m in modules]
    failed: list[str] = []
    done = [0]
    skipped = run_stage(layout, jobs, lambda m: runner(m, python, layout_slow), failed, done, len(modules))
    if failed:
        raise ValidationError("layout stage failed (the full batch did not run): " + ", ".join(sorted(failed)))
    rest = [m for m in modules if m not in layout]
    batches = [([m for m in rest if m not in SERIAL], jobs)] + [([m], 1) for m in SERIAL if m in rest]
    for batch, workers in batches:
        skipped += run_stage(batch, workers, lambda m: runner(m, python, slow if isinstance(slow, bool) else m in slow),
                             failed, done, len(modules))
    scope = ("" if slow is True else " (slow tests not run)" if not slow else
             f" (slow tests in {len(set(slow) & set(rest))} modules)")
    print(f"game tests: {len(modules) - len(failed)}/{len(modules)} modules pass, {skipped} tests skipped" + scope,
          flush=True)
    if failed:
        raise ValidationError("failing test modules: " + ", ".join(sorted(failed)))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--expected-head", required=True, help="full commit SHA being merged")
    tests = parser.add_mutually_exclusive_group()
    tests.add_argument("--no-tests", dest="tests", action="store_false", help="skip the game test modules")
    tests.add_argument("--slow", action="store_true", help="always run the slow tests (milestone candidates)")
    tests.add_argument("--fast", action="store_true", help="never run the slow tests")
    tests.add_argument("--batch-fast", action="store_true",
                       help="the layout stage's slow tests only, never the full batch's (CI's PR and main runs)")
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
            if args.batch_fast:
                print("SKIP the full batch's slow tests (--batch-fast: the local gate plays them)", flush=True)
            elif not (args.slow or args.fast):
                changed = slow_changes()
                if changed is None:
                    slow, why = True, "RUN every slow test (origin/main unreadable)"
                elif not changed:
                    slow, why = False, "SKIP slow tests (no engine, watched, competitive, save or timing change since origin/main)"
                else:
                    if str(ROOT / "tools") not in sys.path:     # imported as a module (the tests), not run as a script
                        sys.path.insert(0, str(ROOT / "tools"))
                    from slow_reach import Graph
                    slow = Graph(ROOT).affected(changed)
                    why = (f"RUN slow tests in {len(slow)} modules they can reach (changed: {', '.join(changed[:5])}"
                           f"{' ...' if len(changed) > 5 else ''}): {' '.join(sorted(slow))}")
                print(why, flush=True)
            check_tests(args.jobs, args.python, slow, layout_slow=not args.fast)
        check_checkout(args.expected_head)  # a check that changed tracked files cannot certify it
    except (ValidationError, OSError, subprocess.CalledProcessError) as exc:
        print(f"FAIL pre-merge validation: {exc}", file=sys.stderr)
        return 1
    print(f"PASS pre-merge validation at {args.expected_head}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
