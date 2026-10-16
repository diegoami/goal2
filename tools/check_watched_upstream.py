#!/usr/bin/env python3
"""[designed: T62] Re-run accepted upstream checks on immutable source copies."""
import argparse
import json
from pathlib import Path
import subprocess
import sys
import time
from watched_evidence import ROOT, stage, verify_vendor


def validate_entry(rows):
    """[designed] Historical entry probe exits0 even on false comparisons; require complete positive evidence."""
    faithful = [row for row in rows if row.get("run") == "faithful"]
    family = [row for row in rows if row.get("run") == "family"]
    reseeds = [row for row in rows if row.get("run") == "reseed"]
    # [confirmed: accepted E032 family] Seed identifiers, never original asset bytes.
    seeds = {0x0101,0x1234,0x2345,0x2B7E,0x4C1D,0x6A33,0x8E05,0xA1F0,0xC3C3,0xE719}
    if (len(faithful) != 1 or len(family) != 10 or {row["seed"] for row in family} != seeds
            or not all(row["identical"] and row["checks"] and all(row["checks"].values()) for row in faithful+family)
            or len(reseeds) != 2 or any(row["error"] is not None for row in reseeds)
            or len({row["entry_seed"] for row in reseeds}) != 2
            or any(row["first_seed_write"]["new"] != 21 for row in reseeds)
            or reseeds[0]["captain_wait"] != reseeds[1]["captain_wait"]):
        raise ValueError("original entry evidence failed: comparison, seed family or repeated boundary differs")


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--suite", required=True, choices=("tests", "mutations", "stamps", "saves", "entry", "example"))
    args = ap.parse_args()
    import unicorn
    if unicorn.__version__ != "2.1.4":
        raise RuntimeError("acceptance requires tested Unicorn2.1.4; pip install unicorn==2.1.4")
    folder = stage()
    log = ROOT / ".cache" / f"watched-{args.suite}-{time.time_ns()}.jsonl"
    prefix = "experiments/E033-original-match-kit/"
    commands = {
        "tests": ["-m", "unittest", "tests.test_original_match", "-v"],
        "mutations": ["tests/mutations_original_match.py"],
        "stamps": [prefix + "stamps.py", "--log", str(log)],
        "saves": [prefix + "save_boundaries.py", "--log", str(log)],
        "entry": [prefix + "entry_probe.py", "--log", str(log)],
        "example": ["-m", "original_match.example", "--cache", str(ROOT / ".cache")],
    }
    # [derived: byte-identical pin] Upstream tests/mutations use their original import layout.
    # The checked package copy equals the vendored bytes before AND after the run.
    import os
    env = dict(os.environ, PYTHONPATH=str(folder / "runtime"), PYTHONDONTWRITEBYTECODE="1")
    result = subprocess.run([sys.executable, "-B"] + commands[args.suite], cwd=folder, env=env)
    verify_vendor()
    if result.returncode == 0 and args.suite == "entry":
        validate_entry([json.loads(line) for line in log.read_text().splitlines()])
    return result.returncode


if __name__ == "__main__":
    sys.exit(main())
