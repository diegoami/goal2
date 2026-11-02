"""[designed: T158] One whole watched match in a fresh process, for engine_probe.py speed.

    <python> match_child.py --cache DIR --seed N [--rust]

Plays the packaged smoke's reference match (goal2.game.watched_match.run_watched_match, the sealed port) with
the given reference seed and delay byte 0, and prints one JSON line: the interpreter, whether goal2rust's hybrid
was installed (and the machine class), the import and match times (wall and this process's CPU), the number of
events and the digests the packaged smoke compares on.
"""
import argparse
import hashlib
import json
import sys
import time
from pathlib import Path

START = time.perf_counter()
sys.path.insert(0, str(Path(__file__).resolve().parent))
import common  # noqa: E402


def digest(value):
    return hashlib.sha256(repr(value).encode()).hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--cache", required=True)
    parser.add_argument("--seed", type=int, required=True)
    parser.add_argument("--rust", action="store_true")
    args = parser.parse_args()
    machine = common.install_rust().__module__ if args.rust else None
    from goal2.game.watched_match import run_watched_match
    state, raw, fixture = common.reference(args.cache)
    imported = time.perf_counter() - START
    cpu0, wall0 = time.process_time(), time.perf_counter()
    outcome = run_watched_match(state, raw, fixture, reference_seed=args.seed, delay_byte=0)
    cpu, wall = time.process_time() - cpu0, time.perf_counter() - wall0
    native = None
    if args.rust:
        import goal2.engine.original_match.port.engine as pe
        native = pe.PortMachine.__qualname__
    print(json.dumps({"interpreter": common.interpreter(), "executable": sys.executable, "rust": args.rust,
                      "machine": machine, "machine_class": native, "seed": args.seed,
                      "import_s": round(imported, 3), "match_wall_s": round(wall, 3), "match_cpu_s": round(cpu, 3),
                      "events": len(outcome.events), "score": outcome.result.get("score"),
                      "outcome_sha256": digest(outcome), "events_sha256": digest(outcome.events),
                      "result_sha256": digest(outcome.result), "seeds": list(outcome.seeds)}))


if __name__ == "__main__":
    main()
