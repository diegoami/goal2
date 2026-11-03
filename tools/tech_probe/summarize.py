"""[designed: T158] The tables of docs/design/technology-2026-11/README.md, computed from measurements/T158/*.json.

    python3 tools/tech_probe/summarize.py [--dir measurements/T158]

Prints Markdown: the toolkit candidates' start and memory, what the portable ZIP becomes for each choice, the
engine's match speed and the equality of its outcomes, and the engine channels. Every figure is a median over
the runs (with the range where it matters); the load columns give the range recorded with the runs.
"""
from __future__ import annotations

import argparse
import json
import statistics
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

# [designed: T158] What each choice ships, as groups of measure.py sizes. Every choice keeps the bundled CPython
# (the UI's interpreter; the pipe or hybrid still needs one) and goal2.
BASE = ["cpython", "goal2", "launcher"]
PYSIDE_ALL = ["pyside6", "pyside6_essentials", "pyside6_addons", "pyside6_webengine", "pyside6_pdf", "shiboken6"]
CHOICES = [
    ("today (T147): every PySide6 module, pygame-ce, Unicorn, PyPy", BASE + PYSIDE_ALL + ["pygame_ce", "unicorn", "pypy"]),
    ("PySide6 widgets only (Essentials), pitch in the window, PyPy", BASE + ["pyside6", "pyside6_essentials", "shiboken6", "pypy"]),
    ("PySide6 with QtWebEngine as the web shell, PyPy", BASE + PYSIDE_ALL + ["pypy"]),
    ("web page in the player's browser (Edge), PyPy", BASE + ["pypy"]),
    ("web page in pywebview (Edge WebView2), PyPy", BASE + ["pywebview", "pypy"]),
    ("pygame-ce, PyPy", BASE + ["pygame_ce", "pypy"]),
    ("web page in the player's browser, goal2rust hybrid instead of PyPy", BASE + ["goal2rust"]),
    ("PySide6 Essentials, goal2rust hybrid instead of PyPy", BASE + ["pyside6", "pyside6_essentials", "shiboken6", "goal2rust"]),
]


def mb(n):
    return f"{n / 2**20:.1f}"


def med(values):
    values = [v for v in values if v is not None]
    return statistics.median(values) if values else None


def rng(values, fmt="{:.2f}"):
    values = [v for v in values if v is not None]
    if not values:
        return "–"
    return f"{fmt.format(med(values))} ({fmt.format(min(values))}–{fmt.format(max(values))})"


def platform(data):
    return {"Linux": "Linux", "Windows": "Windows"}.get(data["host"]["os"], data["host"]["os"])


def loads(records):
    cpu = [r["load"].get("windows_cpu_pct") for r in records if r.get("load")]
    la = [r["load"].get("loadavg", r["load"].get("wsl_loadavg", [None]))[0] for r in records if r.get("load")]
    cpu = [c for c in cpu if c is not None]
    la = [x for x in la if x is not None]
    return (f"{min(cpu):.0f}–{max(cpu):.0f}" if cpu else "–", f"{min(la):.2f}–{max(la):.2f}" if la else "–")


def files(folder, kind):
    for path in sorted(folder.glob("*.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        if data.get("kind") == kind:
            yield path, data


def ui_table(folder):
    rows = ["| Candidate | Platform | Runs | First frame, s (median, range) | Memory of the tree, MB: resident / private | Processes | Windows CPU % | WSL load (1 min) |",
            "| --- | --- | --- | --- | --- | --- | --- | --- |"]
    for path, data in files(folder, "ui-start-memory"):
        by = defaultdict(list)
        for r in data["records"]:
            by[r["candidate"]].append(r)
        for cand, recs in by.items():
            ok = [r for r in recs if "error" not in r]
            mem = [r["memory"] for r in ok if r.get("memory")]
            cpu, la = loads(recs)
            rows.append(f"| {cand} | {platform(data)} | {len(ok)}/{len(recs)} | {rng([r['ready_s'] for r in ok])} | "
                        f"{med([m['rss_mb'] for m in mem]) or '–'} / {med([m['uss_mb'] for m in mem]) or '–'} | "
                        f"{med([m['processes'] for m in mem]) or '–'} | {cpu} | {la} |")
    return "\n".join(rows)


def size_tables(folder):
    out = []
    for path, data in files(folder, "portable-sizes"):
        groups = {}
        for r in data["records"]:
            groups[r["group"]] = r
        out.append("| Part | Files | On disk, MB | In the ZIP, MB |\n| --- | --- | --- | --- |")
        for name, r in sorted(groups.items(), key=lambda kv: -kv[1]["bytes"]):
            out[-1] += f"\n| {name} | {r['files']} | {mb(r['bytes'])} | {mb(r['zip_bytes'])} |"
        today = sum(groups[g]["zip_bytes"] for g in CHOICES[0][1] if g in groups)
        rows = ["| Choice | On disk, MB | ZIP, MB | ZIP against today, MB |", "| --- | --- | --- | --- |"]
        for label, parts in CHOICES:
            missing = [g for g in parts if g not in groups]
            if missing:
                rows.append(f"| {label} | not measured ({', '.join(missing)}) | | |")
                continue
            disk = sum(groups[g]["bytes"] for g in parts)
            packed = sum(groups[g]["zip_bytes"] for g in parts)
            rows.append(f"| {label} | {mb(disk)} | {mb(packed)} | {(packed - today) / 2**20:+.1f} |")
        out.append("\n".join(rows))
    return "\n\n".join(out)


def speed_table(folder):
    rows = ["| Platform | Arm | Matches | Match CPU, s (median, range) | Against PyPy | Windows CPU % | WSL load (1 min) |",
            "| --- | --- | --- | --- | --- | --- | --- |"]
    for path, data in files(folder, "engine-speed"):
        if "equal" in path.name:
            continue
        by = defaultdict(list)
        for r in data["records"]:
            by[r["arm"]].append(r)
        base = med([r.get("match_cpu_s") for r in by.get("pypy", [])])
        for arm in ("pypy", "cpython", "hybrid"):
            recs = by.get(arm, [])
            if not recs:
                continue
            ok = [r for r in recs if "error" not in r]
            m = med([r["match_cpu_s"] for r in ok])
            cpu, la = loads(recs)
            ratio = f"{m / base:.2f}×" if m and base else "–"
            rows.append(f"| {platform(data)} | {arm} | {len(ok)}/{len(recs)} | {rng([r['match_cpu_s'] for r in ok], '{:.1f}')} | {ratio} | {cpu} | {la} |")
    return "\n".join(rows)


def equality_table(folder):
    rows = ["| File | Platform | Seeds | Arms | Seeds with equal outcome, events and result digests | Score digests |",
            "| --- | --- | --- | --- | --- | --- |"]
    for path, data in files(folder, "engine-speed"):
        by_seed = defaultdict(dict)
        for r in data["records"]:
            if "error" not in r:
                by_seed[r["seed"]].setdefault(r["arm"], set()).add(
                    (r["outcome_sha256"], r["events_sha256"], r["result_sha256"]))
        arms = sorted({a for s in by_seed.values() for a in s})
        equal = sum(1 for s in by_seed.values() if len(s) == len(arms) and len(set().union(*s.values())) == 1)
        scores = len({tuple(r.get("score") or ()) for r in data["records"] if "error" not in r})
        rows.append(f"| {path.name} | {platform(data)} | {len(by_seed)} | {', '.join(arms)} | {equal}/{len(by_seed)} | {scores} distinct scores |")
    return "\n".join(rows)


def channel_table(folder):
    rows = ["| Platform | Channel | Runs | Process start, s | First event, s (cold) | First event, s (warm) | Event to window, ms p50 / p95 | Round trip, ms p50 | Late UI tick, ms p95 / max | Windows CPU % |",
            "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |"]
    for path, data in files(folder, "engine-channel"):
        by = defaultdict(list)
        for r in data["records"]:
            mode = r["mode"] if r["mode"] != "thread" else f"thread ({r['ui'].split()[0]}, plain port)"
            by[mode].append(r)
        for mode in sorted(by, key=lambda m: ("file", "pipe", "thread-hybrid").index(m) if m in ("file", "pipe", "thread-hybrid") else 9):
            recs = by.get(mode, [])
            if not recs:
                continue
            ok = [r for r in recs if "error" not in r]
            cpu, _ = loads(recs)
            cold = [r["first_event_s"] for r in ok]
            if mode.startswith("thread"):
                cold = cold[:1]  # one process: only its first run is cold
            warm = [r.get("warm_first_event_s") for r in ok]
            lat = f"{med([r['latency_ms']['p50'] for r in ok]):.1f} / {med([r['latency_ms']['p95'] for r in ok]):.1f}"
            late = f"{med([r['ui_late_ms']['p95'] for r in ok]):.1f} / {max(r['ui_late_ms']['max'] for r in ok):.1f}"
            rows.append(f"| {platform(data)} | {mode} | {len(ok)}/{len(recs)} | {rng([r.get('start_s') for r in ok], '{:.3f}')} | "
                        f"{rng(cold)} | {rng(warm)} | {lat} | {med([r['rtt_ms']['p50'] for r in ok]):.2f} | {late} | {cpu} |")
    return "\n".join(rows)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dir", type=Path, default=ROOT / "measurements" / "T158")
    args = parser.parse_args()
    for title, table in (("Toolkit candidates: start and memory", ui_table), ("Portable sizes", size_tables),
                         ("Engine speed", speed_table), ("Engine outcome equality", equality_table),
                         ("Engine channels", channel_table)):
        print(f"### {title}\n\n{table(args.dir)}\n")


if __name__ == "__main__":
    main()
