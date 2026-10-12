"""The CLI: run the vendored quick engine on a half-time savestate.

`python -m goal2.play <savestate>` loads the savestate, runs `quick_engine.simulate(state)`, and
prints the final score, the second half's goal minutes with their scorers, and the two seed
words after the match (T01; CLAUDE.md rule 17, rule 18, rule 19).
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

# [designed] Put the vendored engine directory on sys.path so the vendored quick_engine.py's
# `import players` finds `goal2/engine/players.py`. In goal2-archaeology the model sits at
# `runtime/model/` and the player reader at `runtime/driver/`; the vendored code's own path
# insert then looks for `goal2/driver/` (which does not exist here) at position 0, but the
# engine directory is still searched next. The layout differs, not the import.
_ENGINE_DIR = str(Path(__file__).resolve().parent / "engine")
if _ENGINE_DIR not in sys.path:
    sys.path.insert(0, _ENGINE_DIR)

# [confirmed] The model and the savestate reader are vendored from goal2-archaeology at
# 8760df9 (T01's evidence, see PROVENANCE.md).
import quick_engine  # noqa: E402
import savestate  # noqa: E402


def _print_result(result: dict) -> None:
    """Print the result in the order `check_model.py` compares. [designed]"""
    score = result["score"]
    print(f"score: {score[0]}-{score[1]}")
    goals = result["goals"]
    if goals:
        print("goals (team, minute, player):")
        for g in goals:
            print(f"  team {g['team']}, minute {g['minute']}, player {g['player']}")
    else:
        print("goals (team, minute, player): none")
    print(f"seed DS:7B62: 0x{result['seed_DS7B62']:04x}")
    print(f"seed DS:8336: 0x{result['seed_DS8336']:04x}")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        prog="python -m goal2.play",
        description=("Run the vendored quick engine on a half-time savestate. "
                     "Refuses what the model refuses (foul path, extra time, penalties)."),
    )
    ap.add_argument("savestate", type=Path,
                    help="A DOSBox-X savestate at the half-time stall of a quick result.")
    args = ap.parse_args(argv)
    if not args.savestate.is_file():
        print(f"error: {args.savestate}: not a file", file=sys.stderr)
        return 2
    try:
        state = savestate.Savestate(args.savestate)
        result = quick_engine.simulate(state)
    except (quick_engine.FoulPathNotModelled, quick_engine.ExtraTimeNotModelled) as e:
        # [confirmed] The model itself raises these; the CLI surfaces them (T01 scope).
        print(f"refused: {e}", file=sys.stderr)
        return 3
    _print_result(result)
    return 0


if __name__ == "__main__":
    sys.exit(main())
