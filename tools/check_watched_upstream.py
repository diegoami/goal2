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
    ap.add_argument("--suite", required=True, choices=("tests", "mutations", "stamps", "saves", "entry", "example", "competitive-stamps", "competitive-saves"))
    ap.add_argument("--case", type=int, choices=range(8), help="one accepted scenario: saves0..6, competitive-saves0..2, competitive-stamps0..7")
    ap.add_argument("--batch", type=int, choices=(1,2,3,4,5), help="mutation batches 1=0..9, 2=10..16, 3=17..19, 4=20..27, 5=28..35")
    args = ap.parse_args()
    if args.case is not None and args.suite not in ("saves", "competitive-saves", "competitive-stamps") or args.batch is not None and args.suite != "mutations":
        ap.error("--case is for save/stamp scenarios, --batch is for mutations")
    if args.case is not None and args.case >= {"saves":7,"competitive-saves":3,"competitive-stamps":8}[args.suite]:
        ap.error("case outside accepted scenario list")
    import unicorn
    if unicorn.__version__ != "2.1.4":
        raise RuntimeError("acceptance requires tested Unicorn2.1.4; pip install unicorn==2.1.4")
    folder = stage()
    log = ROOT / ".cache" / f"watched-{args.suite}-{time.time_ns()}.jsonl"
    prefix = "experiments/E033-original-match-kit/"
    commands = {
        "competitive-stamps": ["experiments/E034-kit-competitive/stamps_competitive.py", "--log", str(log)],
        "competitive-saves": ["experiments/E034-kit-competitive/save_boundaries_competitive.py", "--log", str(log)],
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
    command = commands[args.suite]
    if args.case is not None and args.suite.startswith("competitive-"):
        command = [str(ROOT / "tools/run_watched_scenario.py"), str(folder / command[0]), str(args.case)] + command[1:]
    elif args.case is not None or args.batch is not None:
        # [designed] Select existing scenarios at runtime; the pinned upstream source remains byte-identical.
        file = folder / command[0]
        bootstrap = ("import importlib.util,sys; "
                     "spec=importlib.util.spec_from_file_location('accepted_probe',sys.argv[1]); "
                     "m=importlib.util.module_from_spec(spec); spec.loader.exec_module(m); ")
        if args.case is not None:
            bootstrap += f"m.SCENARIOS=m.SCENARIOS[{args.case}:{args.case+1}]; "
        else:
            start,end = {1:(0,10),2:(10,17),3:(17,20),4:(20,28),5:(28,36)}[args.batch]
            bootstrap += f"m.MUTATIONS=m.MUTATIONS[{start}:{end}]; "
        bootstrap += "sys.argv=sys.argv[1:]; m.main()"
        command = ["-c",bootstrap,str(file)] + command[1:]
    process = subprocess.Popen([sys.executable,"-B"]+command,cwd=folder,env=env,
                               stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True)
    output = []
    for line in process.stdout:
        output.append(line)
        print(line,end="",flush=True)
    returncode = process.wait()
    if any("killed (time limit)" in line for line in output):
        raise RuntimeError("a mutation timed out; timeout is not a proved behavioral failure")
    verify_vendor()
    if returncode == 0 and args.suite == "entry":
        validate_entry([json.loads(line) for line in log.read_text().splitlines()])
    return returncode


if __name__ == "__main__":
    sys.exit(main())
