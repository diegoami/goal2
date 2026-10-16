#!/usr/bin/env python3
"""[designed: T62] Re-run accepted upstream checks on immutable source copies."""
import argparse
from pathlib import Path
import subprocess
import sys
import time
from watched_evidence import ROOT, stage, verify_vendor


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--suite", required=True, choices=("tests", "mutations", "stamps", "saves", "entry", "example"))
    args = ap.parse_args()
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
    return result.returncode


if __name__ == "__main__":
    sys.exit(main())
