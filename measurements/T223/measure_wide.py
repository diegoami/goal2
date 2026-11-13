#!/usr/bin/env python3
"""[designed: T223] #455's pause: the wall time of the one watched step of Signori's wide shot at speed 2.

The step from wait 420 to 421 of T140's career kicked off at speed 2 (goal2/tests/test_core_delay_t223.py: "shot from
Signori", "just wide of post", "GOAL KICK", the whistle's 1,708 x 214B:1E09(1)), three ways: the loop executed (before
T223), served with no wait (a headless run), served and waited (the window's model). Each is run REPEAT times from
the same core save. Writes JSON of timings and hashes only: no guest byte.

    .cache/venv/bin/python measurements/T223/measure_wide.py --output measurements/T223/linux-wide.json
"""
import argparse
import hashlib
import json
from pathlib import Path
import platform
import subprocess
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
REPEAT = 3


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--output", type=Path, required=True)
    args = p.parse_args()
    from goal2.tests import test_core_delay_t223 as t
    from goal2.desktop.core_model import CoreModel
    blob = t.at_pose(t.WIDE - 1)
    out = dict(head=subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
               script_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
               core_sha256=hashlib.sha256(blob).hexdigest(), python=platform.python_version(),
               platform=platform.platform(), runs={})
    for name, served, paced in (("executed", False, False), ("served", True, False), ("served-waited", True, True)):
        rows = []
        for _ in range(REPEAT):
            core = t.load(blob)
            core.delays_served = served
            m = CoreModel(core, t.requires.CACHE / "GOAL.DAT", Path(tempfile.gettempdir()) / "unused-t223.g2core")
            m.pacing = paced
            start = time.perf_counter()
            m.round_step("live_step")
            rows.append(dict(wall_s=round(time.perf_counter() - start, 3), asked_ms=core.wait.delay_ms,
                             memory_sha256=core.memory_sha256()))
        out["runs"][name] = rows
        print(name, rows, flush=True)
    args.output.write_text(json.dumps(out, indent=1) + "\n")


if __name__ == "__main__":
    main()
