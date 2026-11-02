"""[designed: owner, 2026-11-01, #500] Every test process refuses to play the sealed port engine itself: matches run
in a child under engine_python() (goal2/tests/pypy_engine.py). The children it starts are marked and not guarded."""
import os

if os.environ.get("GOAL2_ENGINE_CHILD") != "1":
    from goal2.tests.pypy_engine import guard

    guard()
