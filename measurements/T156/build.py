#!/usr/bin/env python3
"""[designed: T156] Turn the capture server's private run log into the committed record.

    python3 build.py /tmp/goal2-t156-run1

Reads RUN/steps.jsonl and RUN/png/ (written by capture/server.py, under /tmp, never committed) and writes
  docs/original-game/captures/t156-r1.json     every logged step, numbered in log order
  docs/original-game/images/t156-NNN-*.png     the renders chosen for the chapters (byte copies)
  docs/original-game/image-provenance.tsv      one row per new PNG (rows of run T156-R1 are replaced)
No savestate and no original game file is copied: only the renders, digests and hashes.

Step numbers. The server numbered its records with an in-memory counter. The quit's last key ended
DOSBox-X, so no screen could be read after it; its record (log line 241) was appended by hand from the
server's own report (`dosbox-x exited with code 0 during a savestate`, then `alive` -> rc 0). The server
did not count that line, so from the relaunch on its numbers are one lower than the line. The committed
`step` is the line index; `server_step` keeps the server's number, which names the private files.
"""
import hashlib
import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DOCS = ROOT / "docs" / "original-game"
RUN_ID = "T156-R1"
LOG = DOCS / "captures" / "t156-r1.json"
PROVENANCE = DOCS / "image-provenance.tsv"

# committed step -> image slug (the render of the read after that step)
IMAGES = {
    2: "hang-on-a-tick", 5: "country-holland", 6: "name-entry", 10: "name-typed",
    11: "bulletin-welcome", 12: "bulletin-groups", 13: "hub",
    14: "squad", 16: "pool", 17: "pool-put-here", 29: "pool-pick-done", 30: "player-tactics",
    33: "team-tactics", 34: "team-tactic-changed",
    41: "round1-results", 42: "match-menu", 43: "captain", 44: "captain-chosen", 45: "kick-off",
    46: "goal-kick-taker", 48: "menu-after-taker", 56: "corner-taker", 58: "taker-timed-out",
    66: "injury-and-booking", 67: "substitution-opportunity", 74: "bench-requested",
    80: "bench-request-cancelled", 119: "halftime-board", 124: "halftime-bench",
    132: "substitution-made", 149: "opponent-substitution", 175: "replay-prompt",
    176: "save-goal-prompt", 177: "goal-file-name", 178: "replay-playing", 192: "fulltime-board",
    193: "fulltime-menu", 198: "summary-prompt", 199: "summary-file-name", 200: "bulletin-after-match",
    201: "hub-after-round1", 202: "card-recovered", 224: "fixture-list", 227: "tournament-europe",
    228: "tournament-americas", 229: "tournament-finals", 230: "tournament-championship",
    233: "save-name-prompt", 237: "save-name-typed", 239: "quit-confirm", 240: "quit-save-prompt",
    243: "load-name", 244: "loaded-hub", 245: "load-goal-prompt", 246: "goal-replay-menu",
    247: "goal-replay", 254: "goal-replay-goal", 262: "round2-results-rolling", 263: "round2-results",
    264: "round2-match-menu", 265: "round2-captain", 267: "quick-hang-on", 270: "quick-halftime",
    274: "quick-substitution-opportunity", 279: "quick-bench", 301: "quick-substitution-made",
    310: "quick-fulltime", 316: "group-table", 317: "bulletin-round2", 318: "hub-round2",
    320: "card-recovered-round2",
}
# renders byte-identical to images already in the reference: those files are cited, not copied again
EXISTING = {0: "images/title-load-prompt.png", 1: "images/title-player-count.png",
            3: "images/country-select.png", 242: "images/title-load-prompt.png"}

# labels typed during the run that the screens later showed to be wrong (committed step numbers); the
# action, digests and hashes are unchanged
RELABEL = {
    **{s: (f"squad-down-{s - 202}", "the squad opened on Witschge already (step 202); these Downs moved past him")
       for s in range(203, 219)},
    **{s: (f"bench-down-{s - 292}", "label typed as find-winter; eight Downs from Gullit ended on W Kieft, "
                                    "not A Winter as intended (seven were needed)") for s in range(293, 301)},
    **{s: (f"eleven-down-{s - 279}", "label typed as find-gullit; the injured Gullit had moved to the end of the "
                                    "eleven, so these nine Downs ended on Van Basten") for s in range(280, 289)},
    301: ("put-on-kieft", "label typed as put-on-winter; the card and strip show W Kieft went on"),
}


def sha(b):
    return hashlib.sha256(b).hexdigest()


def main(run):
    run = Path(run)
    lines = [json.loads(x) for x in (run / "steps.jsonl").read_text(encoding="utf-8").splitlines() if x.strip()]
    steps = []
    for i, e in enumerate(lines):
        server_step = e["step"]
        expected = i if i <= 241 else i - 1
        if server_step != expected or (i == 241) != bool(e.get("observation")):
            raise SystemExit(f"line {i}: server step {server_step}, expected {expected}")
        label = e["label"]
        note = e.get("observation")
        if i in RELABEL:
            label, note = RELABEL[i]
        rec = {"step": i, "label": label, "action": e["action"], "before_digest": e["before_digest"],
               "after_digest": e["text_digest"], "changed": e["changed"], "sav_sha256": e["sav_sha256"],
               "png_sha256": e["png_sha256"], "bottom": e["bottom"], "font": e["font"], "utc": e["utc"],
               "progress": e.get("progress"), "server_step": None if e.get("observation") else server_step}
        if note:
            rec["note"] = note
        if i in IMAGES:
            rec["image"] = f"images/t156-{i:03d}-{IMAGES[i]}.png"
        if i in EXISTING:
            rec["image"] = EXISTING[i]
            rec["note"] = "render byte-identical to the existing image (same PNG SHA-256)"
        steps.append(rec)
    for i, path in EXISTING.items():
        if sha((DOCS / path).read_bytes()) != steps[i]["png_sha256"]:
            raise SystemExit(f"step {i}: {path} is not byte-identical to this run's render")
    record = {
        "run": RUN_ID, "issue": 525, "task": "T156",
        "method": {
            "driver": "goal2-archaeology experiments/E031-play-the-game/play.py PlayDriver (runtime/driver/driver.py), "
                      "imported read only from the engine clone at b519d999673c9458211279fd4da8a8325b9f56fe",
            "capture_tool": "measurements/T156/capture/server.py and client.py",
            "emulator": "DOSBox-X 2024.03.01, svga_s3, memsize 16, cycles=fixed 8000, private Xvfb display, raw XTEST keys",
            "mapper": "experiments/E031-play-the-game/mapper-nohost.map, sha256 "
                      "7b2f6f958fdb0a0b6a68e12611c3e3ab8554f0872c048ab8a8a05da2fff73a23 (savestate on Scroll Lock)",
            "release": "set goal2-67cf27d6 of the archaeology artifacts/known.json, verified by the driver before each launch",
            "workdir": "/tmp/goal2-t156-run1 (game folder recreated from the verified release copy at each launch)",
            "renderer": "goal2-archaeology tools/screens/render.py render_savestate, 640x400, the savestate's VGA plane 2 font",
            "start": "the original's own title screen, no saved game: N for a new game",
            "relaunch": "step 242 starts DOSBox-X again after the quit, with the three files the game wrote in step "
                        "177 (G-1.HIL), 199 (S-1.SUM) and 237-238 (T156.GL) copied into the recreated game folder; "
                        "their SHA-256 are in that step's action",
            "steps": "each step is one key (`key K`) or one timed wait (`wait S`), except the two launches; "
                     "before_digest is the last screen read before the action (the previous step's read), "
                     "after_digest the read the step ends with (a key: until the screen changed and two reads "
                     "agreed, or its timeout); digests are SHA-256 of the 4000 bytes of characters and attributes",
            "private": "the savestates (sav_sha256) stay in /tmp, never committed (CLAUDE.md rule 14)",
        },
        "steps": steps,
    }
    LOG.write_text(json.dumps(record, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    # The provenance file is kept byte-exact (.gitattributes: -text, mixed line endings): earlier rows are
    # never rewritten; rows of this run are dropped and appended again, tab-separated, LF-terminated.
    raw = PROVENANCE.read_bytes()
    kept = b"".join(line for line in raw.splitlines(keepends=True) if f"\t{RUN_ID} step ".encode() not in line)
    rows = []
    for i, slug in sorted(IMAGES.items()):
        rec = steps[i]
        src = run / "png" / f"{rec['server_step']:04d}.png"
        data = src.read_bytes()
        if sha(data) != rec["png_sha256"]:
            raise SystemExit(f"step {i}: {src} does not match its logged png_sha256")
        shutil.copyfile(src, DOCS / rec["image"])
        rows.append("\t".join([f"t156-{slug}", rec["image"], f"{RUN_ID} step {i}", rec["sav_sha256"],
                               rec["png_sha256"], rec["font"]]) + "\n")
    PROVENANCE.write_bytes(kept + "".join(rows).encode("utf-8"))
    print(f"{len(steps)} steps, {len(IMAGES)} new images, {len(EXISTING)} cited existing renders")


if __name__ == "__main__":
    main(sys.argv[1])
