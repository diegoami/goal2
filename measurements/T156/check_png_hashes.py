#!/usr/bin/env python3
"""[designed: T156] Recompute the T156 run's PNG hashes from the committed files and match them.

    python3 measurements/T156/check_png_hashes.py [--root DIR]

Checks, from the repository alone (no private state, standard library only):
  1. every row of docs/original-game/image-provenance.tsv whose source is `T156-R1 step N`: the PNG's SHA-256,
     recomputed from the committed file, equals the row's png_sha256, and the log's step N names that image
     with the same PNG and savestate hashes;
  2. every step of docs/original-game/captures/t156-r1.json that names an image (the new ones and the four
     cited byte-identical older renders): the committed file hashes to the step's png_sha256;
  3. every images/t156-*.png file has a provenance row, and is embedded in a chapter (a Markdown file of
     docs/original-game links `images/<name>`);
  4. every step's action is one launch, one key (`key K`, a single keysym) or one timed wait (`wait S`), and
     every key or wait step carries its before and after screen digests (the quit's last key, after which
     DOSBox-X exited and no screen existed, carries the before digest and its note).
Prints one line per problem and exits 1, or prints the counts and exits 0.
"""
import argparse
import csv
import hashlib
import json
import re
import sys
from pathlib import Path

RUN_ID = "T156-R1"
DIGEST = re.compile(r"^[0-9a-f]{64}$")
ACTION = re.compile(r"^(launch( with .+)?|key [A-Za-z0-9_]+|wait \d+(\.\d+)?s)$")


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def check(root):
    docs = root / "docs" / "original-game"
    problems = []
    log = json.loads((docs / "captures" / "t156-r1.json").read_text(encoding="utf-8"))
    steps = log["steps"]
    if [s["step"] for s in steps] != list(range(len(steps))):
        problems.append("log steps are not numbered 0..n-1 in order")
    rows = [r for r in csv.DictReader((docs / "image-provenance.tsv").read_text(encoding="utf-8").splitlines(),
                                      delimiter="\t") if r["source"].startswith(RUN_ID + " step ")]
    chapters = "\n".join(p.read_text(encoding="utf-8") for p in docs.glob("*.md"))
    for r in rows:
        n = int(r["source"].rsplit(" ", 1)[1])
        png = docs / r["image"]
        if not png.is_file():
            problems.append(f"{r['image']}: listed in provenance, no such file")
            continue
        got = sha(png)
        if got != r["png_sha256"]:
            problems.append(f"{r['image']}: sha256 {got} != provenance {r['png_sha256']}")
        s = steps[n] if n < len(steps) else {}
        if s.get("image") != r["image"] or s.get("png_sha256") != r["png_sha256"] \
                or s.get("sav_sha256") != r["savestate_sha256"]:
            problems.append(f"{r['image']}: provenance row and log step {n} disagree")
    for s in steps:
        if "image" in s:
            png = docs / s["image"]
            if not png.is_file() or sha(png) != s["png_sha256"]:
                problems.append(f"step {s['step']}: {s['image']} does not hash to the logged png_sha256")
        if not ACTION.match(s["action"]):
            problems.append(f"step {s['step']}: action {s['action']!r} is not one launch, one key or one timed wait")
        if s["action"].startswith(("key ", "wait ")):
            if not DIGEST.match(s.get("before_digest") or ""):
                problems.append(f"step {s['step']}: no before digest")
            if not DIGEST.match(s.get("after_digest") or "") and not s.get("note"):
                problems.append(f"step {s['step']}: no after digest and no note saying why")
    listed = {r["image"] for r in rows}
    for png in sorted((docs / "images").glob("t156-*.png")):
        rel = f"images/{png.name}"
        if rel not in listed:
            problems.append(f"{rel}: no provenance row")
        if f"(images/{png.name})" not in chapters:
            problems.append(f"{rel}: not embedded in any chapter")
    return problems, len(rows), len(steps)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[2])
    a = ap.parse_args(argv)
    problems, n_rows, n_steps = check(a.root)
    for p in problems:
        print(p)
    if problems:
        print(f"FAIL: {len(problems)} problem(s)")
        return 1
    print(f"OK: {n_rows} T156 PNGs match provenance and log; {n_steps} steps, each one launch, key or timed wait")
    return 0


if __name__ == "__main__":
    sys.exit(main())
