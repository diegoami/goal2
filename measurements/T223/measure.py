#!/usr/bin/env python3
"""[designed: T223] The wall time of the same watched stretch, before and after the delay is served, at each speed.

Before: the delay's loop executes under Unicorn (`Core.delays_served = False`) and nothing waits: the core's pace up
to T222. After: the delay is served and the model waits the milliseconds asked (`CoreModel.pacing`, what the window
turns on). The stretch is the first STEPS watched steps of T140's career (Italy, 2028, from the recorded date-call
state; goal2/tests/test_core_delay_t223.py), which hold Signori's wide shot at step 421. Also the core's own time per
delay served (its hook, `Core._on_delay`). Writes JSON of timings and hashes only: no guest byte.

    .cache/venv/bin/python measurements/T223/measure.py --output measurements/T223/linux.json
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
STEPS = 450


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--steps", type=int, default=STEPS)
    p.add_argument("--speeds", default="0,1,2,3,4,5")
    args = p.parse_args()
    from goal2.core.runner import Core
    from goal2.desktop.core_model import CoreModel, CoreNewGame
    cache = ROOT / ".cache"
    scratch = Path(tempfile.gettempdir()) / "unused-t223-measure.g2core"
    model, _ = CoreNewGame(cache / "e039-r0005-date-call.sav", cache / "GOAL.DAT", scratch).start(2028, 16, "A Test")
    menu = model.core.save()
    spent, real = [], Core._on_delay

    def timed(core, replay):
        t = time.perf_counter()
        try:
            return real(core, replay)
        finally:
            if core.delays_served:
                spent.append(time.perf_counter() - t)
    Core._on_delay = timed
    out = dict(head=subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
               script_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
               career_sha256=hashlib.sha256(menu).hexdigest(), steps=args.steps, python=platform.python_version(),
               platform=platform.platform(), speeds={})
    for speed in (int(s) for s in args.speeds.split(",")):
        row = {}
        for phase, served in (("before", False), ("after", True)):
            core = Core.load(menu, goal_dat=cache / "GOAL.DAT")
            core.delays_served = served
            m = CoreModel(core, cache / "GOAL.DAT", scratch)
            m.pacing = served
            m.round_step("round_start", True)
            m.round_step("kick_off", None, True)
            asked = 0
            # [designed: T116] the desktop kicks off at speed 0; the speed is the original's Left/Right keys
            from goal2.core import views
            from goal2.core.screens import LEFT, RIGHT
            while views.match_speed(core.wait.state) != speed:
                m.round_step("live_step", LEFT if views.match_speed(core.wait.state) < speed else RIGHT)
            n = len(spent)
            start = time.perf_counter()
            for _ in range(args.steps):
                kind = core.wait.kind
                state = m.round_step("taker_key", ord("c")) if kind == "set-piece-select" else \
                    m.round_step("replay_timeout") if kind in ("action-replay-prompt", "save-goal-prompt") else \
                    m.round_step("live_step")
                asked += core.wait.delay_ms
                if state["stop"] not in ("live", "taker", "replay", "replay-save"):
                    break
            row[phase] = dict(wall_s=round(time.perf_counter() - start, 3), memory_sha256=core.memory_sha256(),
                              at=core.wait.kind)
            if served:
                per = sorted(spent[n:])
                row["asked_ms"] = asked
                row["served_calls"] = len(per)
                if per:
                    row["served_us"] = dict(mean=round(1e6 * sum(per) / len(per), 1),
                                            p99=round(1e6 * per[len(per) * 99 // 100], 1), max=round(1e6 * per[-1], 1))
        row["same_memory"] = row["before"]["memory_sha256"] == row["after"]["memory_sha256"]
        out["speeds"][speed] = row
        print(speed, json.dumps(row), flush=True)
    args.output.write_text(json.dumps(out, indent=1) + "\n")


if __name__ == "__main__":
    main()
