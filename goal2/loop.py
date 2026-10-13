"""The CLI entry point: `python -m goal2.loop <savestate> <goal.dat>`.

Mirrors `python -m goal2.play` (T01's contract). Loads GOAL.DAT via
goal2.data.goaldat.load; loads the savestate via goal2.engine.state.from_savestate;
calls run_main_loop; exits with its return code.
[designed]
"""
from __future__ import annotations

import sys
from pathlib import Path

from goal2.data.goaldat import load as load_goaldat
from goal2.engine.state import from_savestate
from goal2.main_loop import run_main_loop


def main(argv: list[str] | None = None) -> int:
    if argv is None:
        argv = sys.argv
    if len(argv) != 3:
        print("usage: python -m goal2.loop <savestate> <goal.dat>", file=sys.stderr)
        return 2
    savestate_path = argv[1]
    goaldat_path = argv[2]

    savestate_file = Path(savestate_path)
    if not savestate_file.is_file():
        print(f"error: {savestate_file}: not a file", file=sys.stderr)
        return 2

    goaldat_file = Path(goaldat_path)
    if not goaldat_file.is_file():
        print(f"error: {goaldat_file}: not a file", file=sys.stderr)
        return 2

    try:
        goaldat_data = goaldat_file.read_bytes()
        goaldat = load_goaldat(goaldat_data)
    except ValueError as e:
        print(f"error: {goaldat_file}: {e}", file=sys.stderr)
        return 2

    try:
        state_bytes = savestate_file.read_bytes()
        state = from_savestate(state_bytes)
    except Exception as e:
        print(f"error: {savestate_file}: {e}", file=sys.stderr)
        return 2

    return run_main_loop(goaldat, state, state_bytes)


if __name__ == "__main__":
    sys.exit(main())
