"""CLI for legacy savestates and rebuild-owned resumable sessions. [designed: T33]"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from goal2.data.goaldat import load as load_goaldat
from goal2.game.state import from_savestate, to_savestate
from goal2.game.session_save import SessionSaveError, load as load_session, save as save_session
from goal2.main_loop import run_main_loop
from goal2.ui.input import terminal_input


def main(argv: list[str] | None = None) -> int:
    if argv is None:
        argv = sys.argv
    parser = argparse.ArgumentParser(prog="python -m goal2.loop")
    parser.add_argument("--resume", metavar="PATH", help="resume a rebuild session save")
    parser.add_argument("--save", metavar="PATH", default=".cache/session.g2save",
                        help="save path (default: .cache/session.g2save)")
    parser.add_argument("paths", nargs="*", metavar="PATH",
                        help="legacy <savestate> <goal.dat>, or GOAL.DAT after --resume")
    try:
        args = parser.parse_args(argv[1:])
    except SystemExit as exc:
        return int(exc.code)
    if (args.resume and len(args.paths) != 1) or (not args.resume and len(args.paths) != 2):
        parser.print_usage(sys.stderr)
        return 2
    if args.resume:
        savestate_file = Path(args.resume)
        goaldat_file = Path(args.paths[0])
    else:
        savestate_file = Path(args.paths[0])
        goaldat_file = Path(args.paths[1])
    if not goaldat_file.is_file():
        print(f"error: {goaldat_file}: not a file", file=sys.stderr)
        return 2
    if not args.resume and not savestate_file.is_file():
        print(f"error: {savestate_file}: not a file", file=sys.stderr)
        return 2

    try:
        goaldat_data = goaldat_file.read_bytes()
        goaldat = load_goaldat(goaldat_data)
    except (OSError, ValueError) as e:
        print(f"error: {goaldat_file}: {e}", file=sys.stderr)
        return 2

    if args.resume:
        try:
            state, state_bytes = load_session(savestate_file)
            # Validate both the original template and the loaded state through
            # the adapter before the user can enter play. Keep loaded metadata
            # authoritative; the parsed objects are validation-only. [designed: T33]
            from_savestate(state_bytes)
            continuation = to_savestate(state, original=state_bytes)
            from_savestate(continuation)
        except Exception as e:
            print(f"error: {savestate_file}: {e}", file=sys.stderr)
            return 2
    else:
        try:
            state_bytes = savestate_file.read_bytes()
            state = from_savestate(state_bytes)
        except Exception as e:
            print(f"error: {savestate_file}: {e}", file=sys.stderr)
            return 2

    # [designed: T25] Keep immediate key input scoped to the interactive chain
    # and restore terminal attributes when that chain returns or raises.
    def save_current_session() -> None:
        save_session(args.save, state, state_bytes)

    with terminal_input():
        if args.resume:
            return run_main_loop(goaldat, state, state_bytes,
                                 on_save=save_current_session, resume=True)
        return run_main_loop(goaldat, state, state_bytes, on_save=save_current_session)


if __name__ == "__main__":
    sys.exit(main())
