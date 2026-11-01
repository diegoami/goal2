"""[designed: owner, 2026-11-02, T147] One watched match through goal2's own job route, for the packaged smoke
(tools/portable/smoke.py): this interpreter is the UI's side (WatchedJobs), the worker runs under GOAL2_ENGINE_PYTHON.
The match is test_pypy_worker_t152's watched one: the reference savestate, Fixture(7, 19, 21), seed 257, delay 0,
draws recorded. It writes what the two runs are compared on (the repr digests of the outcome, its events and its
result, the score, the seeds) and where goal2 and the worker came from.

    python smoke_match.py --cache DIR --out FILE [--expect-root DIR]

With --expect-root, goal2 must be imported from DIR's `python/` and the worker must be DIR's PyPy: the packaged run
may not reach the source tree.
"""
import argparse
import hashlib
import json
import platform
import sys
import time
from pathlib import Path


class Owner:
    """What WatchedJobs needs of the active game (as goal2.tests.test_watched_publication.Owner)."""
    def __init__(self, state, template):
        self.state = state
        self.template_bytes = template

    def view(self, state):
        return state.last_match


def digest(value) -> str:
    return hashlib.sha256(repr(value).encode()).hexdigest()


def main(argv=None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cache", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--expect-root", type=Path)
    args = parser.parse_args(argv)
    import goal2
    from goal2.engine.original_match import Fixture
    from goal2.engine.original_match.assets import reference_image
    from goal2.game.state import from_savestate
    from goal2.game.watched_jobs import WatchedJobs
    from goal2.game.engine_python import engine_python
    where = Path(goal2.__file__).resolve()
    if args.expect_root is not None:
        root = args.expect_root.resolve()
        if root / "python" not in where.parents:
            raise SystemExit(f"goal2 came from {where}, not from {root / 'python'}")
        if Path(engine_python()).resolve() != root / "pypy" / "pypy.exe":
            raise SystemExit(f"the worker interpreter is {engine_python()}, not {root / 'pypy' / 'pypy.exe'}")
    raw = reference_image(args.cache)
    state = from_savestate(raw)
    state.captain = 0                                   # as test_watched_adapter's state()
    jobs = WatchedJobs(Owner(state, raw))
    try:
        started = time.monotonic()
        token = jobs.start(Fixture(7, 19, 21), reference_seed=257, delay_byte=0, record_draws=True)
        events = []
        while jobs.busy:
            if time.monotonic() - started > 1800:
                raise SystemExit("the worker did not finish in 30 minutes")
            events.extend(jobs.poll(token))
            time.sleep(.01)
        wall = time.monotonic() - started
        outcome = jobs.outcome
    finally:
        jobs.close()
    if outcome is None:
        raise SystemExit("the job ended without an outcome")
    if tuple(events) != outcome.events:
        raise SystemExit("the polled events differ from the outcome's")
    args.out.write_text(json.dumps({
        "ui_python": f"{platform.python_implementation()} {platform.python_version()}", "ui_executable": sys.executable,
        "goal2": str(where), "worker": jobs.interpreter, "match_wall_s": round(wall, 1),
        "outcome_sha256": digest(outcome), "events_sha256": digest(outcome.events), "events": len(outcome.events),
        "result_sha256": digest(outcome.result), "score": outcome.result.get("score"), "seeds": list(outcome.seeds), "engine_year": outcome.engine_year,
    }, indent=1) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
