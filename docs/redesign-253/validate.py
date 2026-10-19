#!/usr/bin/env python3
"""[designed: #253] Stdlib trace checks; no application execution or UX acceptance.

A frozen copy can validate any checkout via --root. Negative controls edit saved
bytes only under this task's package and restore them in finally, checking hashes.
"""
from __future__ import annotations
import argparse
import csv
import hashlib
import io
import json
import re
import struct
import subprocess
import sys
import xml.etree.ElementTree as ET
from collections import Counter
from pathlib import Path

BASE = "3335da830d289cc869f989b73816926c54360ff1"
MANUAL = "ebdd6879d469a574f6d4b446f59b33a6be3ffd81"
GROUPS = {"ST": 6, "CO": 14, "CS": 8, "CC": 4, "HU": 9, "PI": 11,
          "SK": 12, "PC": 5, "PT": 8, "TT": 8, "SD": 9, "FX": 12,
          "TB": 7, "BR": 5, "HI": 24, "HR": 9, "NW": 8, "MP": 9,
          "LI": 11, "IN": 18, "PR": 8, "RS": 19, "SV": 10}
# Independent original-field oracle: dropping a field from BOTH TSVs must fail.
SKILLS = "Keeping Kicking Tackling Heading Marking Passing Crossing Feinting Control Dribbling Shooting Penalties".split()
CHARACTERISTICS = "Hardness Fitness Energy Morale Leadership".split()
EXISTING = {"#241": "roster-scroll-preview", "#252": "roster-diagnostics",
            "#242": "player-card-projection", "#243": "match-entry-speed",
            "#198": "match-renderer-presentation", "#248": "personal-instruction-edits",
            "#249": "campaign-context-data", "#250": "watched-intervention-support",
            "#251": "retained-result-replay-data"}
ISSUES = {"B01": 259, "B02": 260, "B03": 261, "B04": 262,
          "B05": 263, "B06": 265, "B07": 264}
LAYOUTS = ["01-country-setup", "02-country-desk", "03-team-workspace",
           "04-pool-compare", "05-competition", "06-match-preparation",
           "07-live-match", "08-result-and-campaign", "09-small-window",
           "10-match-decisions"]
CHECKS = ("proposal", "parity", "journeys", "current", "backlog", "technology", "scope")


def need(condition, message):
    if not condition:
        raise ValueError(message)


def sha(data):
    return hashlib.sha256(data).hexdigest()


class Package:
    def __init__(self, root):
        self.root = root.resolve()
        self.path = self.root / "docs/redesign-253"

    def read(self, name):
        return (self.path / name).read_text()

    def data(self, name):
        return json.loads(self.read(name))

    def rows(self, name):
        return list(csv.DictReader(io.StringIO(self.read(name)), delimiter="\t"))

    def git(self, *args):
        return subprocess.check_output(["git", "-C", str(self.root), *args], stderr=subprocess.PIPE)

    def gate(self):
        text = self.read("decisions.md")
        match = re.search(r"^## Approval gate\n(.*?)(?=^## |\Z)", text, re.M | re.S)
        need(match, "operative Approval gate section missing")
        gate = match.group(1)
        for phrase in ("Explicit owner direction approval is required", "new child issue starts",
                       "not implementation approval", "No toolkit, backend-language or architecture migration is authorized",
                       "Existing independently authorized work retains its own scope"):
            need(phrase in gate, "operative gate missing: " + phrase)
        need(self.data("package.json")["implementation_authorized"] is False, "registry authorizes implementation")

    def proposal(self):
        self.gate()
        for f in ("README.md", "assessment.md", "information-parity.md", "journeys.md",
                  "layouts.md", "decisions.md", "technology.md", "backlog.md", "validation.md"):
            need(len(self.read(f)) > 700, "proposal document absent/empty: " + f)
        index = self.read("README.md")
        need("being assembled" not in index, "transient index instead of decision package")
        need("Recommend A: Country desk" in index, "no clear recommended direction")
        options = self.read("decisions.md")
        for item in ("Country desk", "Broadcast career", "Modern command room", *[f"O{i:02}" for i in range(1, 8)]):
            need(item in options, "missing option/owner decision: " + item)
        reg = self.data("package.json")
        need(reg["base_commit"] == BASE and reg["manual_commit"] == MANUAL, "proposal pins changed")
        need(set(reg["layouts"]) == set(LAYOUTS), "representative layout inventory differs")
        for name in LAYOUTS:
            svg = self.path / "layouts" / (name + ".svg")
            tree = ET.fromstring(svg.read_bytes())
            need(tree.tag.endswith("svg"), "invalid SVG root: " + name)
            for node in tree.iter():
                need(node.tag.split("}")[-1] not in ("script", "foreignObject", "image", "animate", "set"), "non-static/external layout: " + name)
                need(not any(k.split("}")[-1].startswith("on") or k.split("}")[-1] == "href" for k in node.attrib), "active/external SVG attribute")
            w, h = png_size((self.path / "layouts" / (name + ".png")).read_bytes())
            need((w, h) == (1600, 1010), "missing/incorrect layout PNG: " + name)
        bounds = self.data("evidence/layout-bounds-01.json")
        need(sha((self.path / "evidence/check_layout_bounds.py").read_bytes()) == bounds["helper_sha256"], "static bounds helper hash differs")
        need({x["svg"] for x in bounds["layouts"]} == {x + ".svg" for x in LAYOUTS}, "bounds receipt omits a layout")
        for item in bounds["layouts"]:
            need(item["static_svg_and_png_valid"] is True and item["out_of_canvas_text"] == [], "invalid/clipped static layout")
            file = self.path / "layouts" / item["svg"]
            need(sha(file.read_bytes()) == item["svg_sha256"] and sha(file.with_suffix(".png").read_bytes()) == item["png_sha256"], "layout changed after bounds/visual validation")
        return "A/B/C compared; O01–O07 and operative gate;10 static annotated SVG/PNG pairs;0 out-of-canvas text"

    def parity(self):
        src = self.rows("parity/source-fields.tsv")
        dst = self.rows("parity/destinations.tsv")
        source = {r["id"]: r for r in src}
        dest = {r["id"]: r for r in dst}
        need(len(source) == len(src) and len(dest) == len(dst), "duplicate field ID")
        for prefix, names in (("SK", SKILLS), ("PC", CHARACTERISTICS)):
            for n, name in enumerate(names, 1):
                key = f"{prefix}{n:02}"
                need(key in source and source[key]["information"] == name, "required original field missing/renamed: " + key + " " + name)
        expected = {f"{p}{i:02}" for p, count in GROUPS.items() for i in range(1, count + 1)}
        need(set(source) == expected, "original context/field coverage differs from234-field audit")
        need(set(dest) == set(source), "source/destination field IDs differ")
        need(len({r["category"] for r in src}) == 17, "missing original category")
        contexts = self.rows("parity/contexts.tsv")
        need({r["context"] for r in contexts} == set(GROUPS) and len(contexts) == 23, "missing/duplicate decision context")
        for context in contexts:
            need(all(context.values()), "blank when/why/access/owner/limit context")
        surfaces = self.data("package.json")["surfaces"]
        screenshots = {p.name for p in (self.root / "docs/original-game/images").glob("*.png")}
        allowed = set(EXISTING) | set(ISSUES)
        for key, row in source.items():
            need(all(row.values()), "blank evidence/category/source field: " + key)
            need(row["context"] == key[:2], "source context mismatch: " + key)
            need(set(row["screen"].split(";")) <= screenshots, "source screenshot absent: " + key)
            d = dest[key]
            need(d["context"] == row["context"], "destination context mismatch: " + key)
            targets = set(re.findall(r"S\d+", d["destination"]))
            need(targets and targets <= set(surfaces), "blank/unknown destination: " + key)
            owners = set(d["owner"].split("/"))
            need(owners and owners <= allowed, "unowned/unknown field owner: " + key)
        for key in ("SD05", "SD06", "SV08", "ST04"):
            need("B06" in dest[key]["owner"], "assistant/identity dependency absent: " + key)
        rendered = "\n".join(self.read("parity/" + f + ".md") for f in ("management", "campaign", "match"))
        rendered_ids = re.findall(r"^\| ([A-Z]{2}\d{2}) \|", rendered, re.M)
        need(Counter(rendered_ids) == Counter(source.keys()), "rendered matrix omitted/duplicated field")
        for key in source:
            need(re.search(r"^\| " + key + r" \|.*?\[designed\] " + re.escape(dest[key]["destination"]) + r" \| \[designed\] " + re.escape(dest[key]["owner"]) + r" \|$", rendered, re.M), "rendered destination/owner differs: " + key)
        ledger = self.rows("evidence/screens-inspected.tsv")
        need(len(ledger) == 64 and {r["image"] for r in ledger} == screenshots and len(screenshots) == 64, "64-screen inventory/inspection omission")
        duplicate_hashes = {}
        for r in ledger:
            duplicate_hashes.setdefault(r["png_sha256"], []).append(r["image"])
        duplicates = {k: sorted(v) for k, v in duplicate_hashes.items() if len(v) > 1}
        need(len(duplicate_hashes) == 63 and duplicates == {
            "0433257b818389b39b741f0e1f21731478526200347ae14b8081d132695c0392":
            ["m244-position-club.png", "m244-squad-next.png"]},
            "original duplicate-byte set differs from accepted source; retain64 unique names")
        for r in ledger:
            need(all(r.values()), "blank screenshot visual/source/trace entry")
            path = "docs/original-game/images/" + r["image"]
            need(sha((self.root / path).read_bytes()) == r["png_sha256"], "original PNG/inspection hash differs: " + r["image"])
            need(sha(self.git("show", MANUAL + ":" + path)) == r["png_sha256"], "PNG differs from accepted manual pin")
            need("view_image native640x400" in r["inspection"], "missing native visual inspection")
            if r["image"] == "dos-shell.png":
                need(r["trace"] == "environment-only", "DOS shell misclassified")
            else:
                need(re.search(r"J0[1-9]", r["trace"]), "screen lacks journey trace")
                need(all(x in source for x in re.findall(r"[A-Z]{2}\d{2}", r["trace"])), "screen traces unknown field")
        return "234 source=allocated=rendered fields;12 skills/5 characteristics;23 contexts/17 categories;64 pinned image-name/hash traces (63 distinct byte hashes)"

    def journeys(self):
        reg = self.data("package.json")
        text = self.read("journeys.md")
        surfaces = {f"S{i:02}" for i in range(1, 16)}
        journeys = {f"J{i:02}" for i in range(1, 10)}
        need(set(reg["surfaces"]) == surfaces, "screen hierarchy incomplete")
        need(set(reg["journeys"]) == journeys, "journey registry incomplete")
        need(set(re.findall(r"^\| (S\d{2}) \|", text, re.M)) == surfaces, "screen hierarchy prose incomplete")
        need(set(re.findall(r"^## (J\d{2})", text, re.M)) == journeys, "journey prose incomplete")
        need({x for j in reg["journeys"].values() for x in j["surfaces"]} == surfaces, "journeys omit a surface")
        for j in reg["journeys"].values():
            need(j["edges"] and set(j["surfaces"]) <= surfaces, "empty/unknown journey edge")
        for phrase in ("automatic", "player", "Start second half", "Start extra time", "Resume extra time", "Undo", "timed", "No-substitutions-left", "view-only", "Not recorded", "atomic", "handoff", "B06", "B07"):
            need(phrase in text, "significant transition/capability missing: " + phrase)
        cap = self.rows("capabilities.tsv")
        for phrase in ("Local manager", "identities", "Assistant", "shoot-out", "halftime", "replay", "competitive"):
            need(any(phrase.lower() in " ".join(r.values()).lower() for r in cap), "capability dependency omitted: " + phrase)
        need(len(cap) >= 20 and all(all(r.values()) for r in cap), "incomplete capability register")
        # Representative drawings need not illustrate every surface covered by journeys.
        exact = {"01-country-setup": ["S02"], "09-small-window": ["S04"], "10-match-decisions": ["S10"]}
        for key, visible in exact.items():
            need(reg["layouts"][key] == visible, "layout claims a surface not visibly drawn: " + key)
        return "15 surfaces covered by9 journeys; automatic/player/conditional edges and20 capability dependencies"

    def current(self):
        r = self.data("evidence/runtime-06/report.json")
        b = self.data("evidence/browser-03/report.json")
        need(r["audited_commit"] == b["audited_product_commit"] == BASE, "wrong current product pin")
        need(r["resources"] == r["resources_after"] and len(r["resources"]) == 3, "private resource changed during audit")
        for report in (r, b):
            need(report["sources"] == report["sources_after"], "application source changed during audit")
            for name, digest in report["sources"].items():
                need(sha((self.root / name).read_bytes()) == digest, "current source no longer matches runtime audit: " + name)
                need(sha(self.git("show", BASE + ":" + name)) == digest, "runtime source differs from product pin: " + name)
            for name, digest in report["artifacts"].items():
                folder = "runtime-06" if report is r else "browser-03"
                data = (self.path / "evidence" / folder / name).read_bytes()
                need(sha(data) == digest, "observation artifact hash differs: " + name)
                if name.endswith(".png"):
                    png_size(data)
        need(sha((self.path / "evidence/runtime-06/audit-source.py").read_bytes()) == r["audit_sha256"], "frozen runtime helper hash does not resolve")
        d = r["desktop"]
        need(len(d["screens"]) == 10 and {s["page"] for s in d["screens"]} == {"overview", "squad", "pool", "fixtures", "save"}, "not all current pages observed")
        need(all(s["requested"] == s["actual"] for s in d["screens"]) and d["ratio"] == 1, "capture geometry/ratio claim differs")
        need(d["navigation_state_unchanged"] is True and d["ephemeral_setup_confirmation"] == "Management confirmed", "disposable draft baseline not explicit")
        w = d["watched"]
        need(w["started"] is True and w["painted_frame_sequence"] >= 3, "no painted actual watched frame")
        need(w["management_enabled"] is False and w["save_enabled"] is False and w["cancel_restored_state"] is True, "watch lock/cancel baseline evidence missing")
        need(d["save_written"] is False and r["terminal"]["save_written"] is False and r["terminal"]["frames"] == 3, "observation wrote save or lacked terminal frames")
        terminal = self.read("evidence/runtime-06/terminal.txt")
        need("Austria" in terminal and "CAPTAIN: Wohlfahrt" in terminal, "terminal inputs did not visit selected country/squad")
        need(b["non_get_requests"] == [] and b["session_unchanged"] is True and b["save_written"] is False and len(b["screens"]) == 2, "browser read-only observation invalid")
        need("5c26616917d19a77a0e548a0baa2a3997112c477" in self.read("assessment.md"), "Windows audit distinction absent")
        return "24 source hashes match3335da83;10 actual Qt captures;PTY3 states;painted SDL frame3/cancel;2 browser captures/0 writes;no saves"

    def backlog(self):
        self.gate()
        items = self.data("backlog.json")
        need(len(items) == 7 and {x["key"] for x in items} == set(ISSUES), "missing/duplicate new backlog scope")
        all_new_areas = []
        protected = set(EXISTING.values())
        reg_owners = self.data("package.json")["existing_owners"]
        need(reg_owners == {k: [v] for k, v in EXISTING.items()}, "existing ownership registry differs from audited issue contracts")
        for x in items:
            need(x["issue"] == f'https://github.com/diegoami/goal2/issues/{ISSUES[x["key"]]}', "wrong/missing filed issue")
            need(x["implementation_authorized"] is False, "new child authorizes implementation")
            need(all(x[k] for k in ("title", "priority", "size_risk", "dependencies", "owns", "owned_areas")), "incomplete issue identity/dependencies")
            need(not (set(x["owned_areas"]) & protected), "duplicate existing ownership: " + x["key"] + " " + str(set(x["owned_areas"]) & protected))
            all_new_areas += x["owned_areas"]
            body = self.read(x["contract"])
            for phrase in ("Player problem:", "Dependencies:", "Original reference:", "Intended behavior:", "Owned surfaces / exclusions:", "## Acceptance criteria", "## Validation", "not implementation approval", "Existing independently authorized work retains its own scope"):
                need(phrase in body, "child contract missing " + phrase + ": " + x["key"])
            need(len(re.findall(r"^\d\. \[designed\]", body, re.M)) >= 5, "child acceptance criteria missing")
            need("https://github.com/diegoami/goal2/blob/" + MANUAL + "/docs/original-game/" in body, "child original references not absolute/pinned")
        need(len(all_new_areas) == len(set(all_new_areas)), "duplicate new scope ownership")
        by = {x["key"]: x for x in items}
        for key, deps in {"B01": ["#242"], "B02": ["#249", "B06"], "B03": ["#248", "#249"], "B05": ["B06", "B07", "capability"]}.items():
            for dep in deps:
                need(dep in by[key]["dependencies"], "dependency absent: " + key + " " + dep)
        for key, dep in (("B02", "B06"), ("B05", "B06"), ("B05", "B07")):
            need(dep in self.read(by[key]["contract"]), "contract/manifest dependency mismatch: " + key)
        index = (self.root / "docs/tasks/README.md").read_text()
        for n in ISSUES.values():
            need(f"/issues/{n}" in index and f"/issues/{n}" in self.read("backlog.md"), "filed scope absent from proposed order")
        return "7 filed scoped gated issues;9 existing owners preserved;dependencies and task index linked;no duplicate area ownership"

    def technology(self):
        self.gate()
        t = self.read("technology.md")
        for phrase in ("Python backend", "PySide6 Widgets", "Qt Quick", "Tauri2", "Electron", "Godot", "Windows", "Linux", "atomic", "ACK", "save", "migration", "not schedules", "No experimental prototype"):
            need(phrase.lower() in t.lower(), "technology constraint/alternative absent: " + phrase)
        for host in ("doc.qt.io", "v2.tauri.app", "electronjs.org", "docs.godotengine.org"):
            need("https://" + host in t or "https://www." + host in t, "missing primary technology source: " + host)
        need("2026-10-19" in t and "No numeric" in t, "capabilities/estimates not bounded")
        return "desktop/Python constraints;5 frontend approaches;primary sources;relative cost/migration/owner decisions"

    def scope(self):
        need((self.path / "package.json").exists(), "proposal package absent")
        changed = set(self.git("diff", "--name-only", BASE).decode().splitlines())
        changed.update(self.git("ls-files", "--others", "--exclude-standard").decode().splitlines())
        need(changed, "no planning deliverable")
        allowed = lambda x: x.startswith("docs/redesign-253/") or x == "docs/tasks/README.md"
        need(all(allowed(x) for x in changed), "out-of-scope changed file: " + str([x for x in changed if not allowed(x)]))
        for path in self.path.rglob("*"):
            if not path.is_file():
                continue
            need(not path.is_symlink(), "package symlink")
            need(path.suffix.lower() not in (".sav", ".dat", ".gl", ".sum", ".hil", ".exe", ".wasm"), "original/runtime payload entered package")
            if path.suffix == ".json":
                json.loads(path.read_text())
            if path.suffix in (".md", ".py", ".mjs", ".json", ".tsv", ".svg"):
                need(len(path.read_text()) < 110000, "oversized planning file: " + path.name)
        return f"{len(changed)} changed files limited to task docs/index;JSON valid;no app/engine/dependency/original payload changes"


def png_size(data):
    need(data[:8] == b"\x89PNG\r\n\x1a\n" and data[12:16] == b"IHDR" and len(data) > 32, "invalid PNG")
    return struct.unpack(">II", data[16:24])


def run(package, checks):
    results = []
    for name in checks:
        try:
            results.append({"check": name, "pass": True, "finding": getattr(package, name)()})
        except (OSError, ValueError, KeyError, TypeError, ET.ParseError, subprocess.CalledProcessError) as e:
            results.append({"check": name, "pass": False, "finding": str(e)})
    return results


def negative_controls(package):
    """[designed: #253] Realistic omissions, not token injection; exact bytes restore."""
    initial = run(package, CHECKS)
    need(all(x["pass"] for x in initial), "positive package must pass before controls: " + str(initial))
    src = "parity/source-fields.tsv"
    dst = "parity/destinations.tsv"
    def drop(text, prefix):
        return "".join(x for x in text.splitlines(keepends=True) if not x.startswith(prefix + "\t"))
    cases = [
        ("missing-skill-allocation", "parity", {dst: lambda t: drop(t, "SK12")}),
        ("missing-skill-from-both-inventories", "parity", {src: lambda t: drop(t, "SK12"), dst: lambda t: drop(t, "SK12")}),
        ("blank-destination", "parity", {dst: lambda t: re.sub(r"^(SK12\tSK\t)[^\t\n]+", r"\1", t, flags=re.M)}),
        ("missing-original-screen", "parity", {"evidence/screens-inspected.tsv": lambda t: drop(t, "captain-select.png")}),
        ("remove-operative-gate", "proposal", {"decisions.md": lambda t: re.sub(r"^## Approval gate\n.*?(?=^## |\Z)", "", t, flags=re.M | re.S)}),
        ("realistic-duplicate-campaign-owner", "backlog", {"backlog.json": duplicate_campaign,
          "backlog/B03.md": lambda t: t.replace("COMPOSITION only", "COMPOSITION and campaign-context dataset projection/retention")})]
    receipts = []
    for name, check, edits in cases:
        saved = {f: (package.path / f).read_bytes() for f in edits}
        result = None
        try:
            for f, change in edits.items():
                altered = change(saved[f].decode())
                need(altered.encode() != saved[f], "control made no change: " + name)
                (package.path / f).write_text(altered)
            result = run(package, [check])[0]
            need(result["pass"] is False, "control unexpectedly passed: " + name)
        finally:
            for f, data in saved.items():
                (package.path / f).write_bytes(data)
            need(all((package.path / f).read_bytes() == data for f, data in saved.items()), "saved-byte restoration failed: " + name)
        receipts.append({"control": name, "rejected_by": check, "finding": result["finding"],
                         "before_sha256": {f: sha(v) for f, v in saved.items()},
                         "after_sha256": {f: sha((package.path / f).read_bytes()) for f in saved},
                         "exact_bytes_restored": True})
    need(all(x["pass"] for x in run(package, CHECKS)), "package failed after restoration")
    return {"positive_checks": initial, "negative_controls": receipts, "all_restored": True}


def duplicate_campaign(text):
    items = json.loads(text)
    next(x for x in items if x["key"] == "B03")["owned_areas"].append("campaign-context-data")
    return json.dumps(items, indent=2) + "\n"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.cwd(), help="checkout root; helper may live outside it")
    parser.add_argument("--check", choices=CHECKS)
    parser.add_argument("--all", action="store_true")
    parser.add_argument("--negative-controls", action="store_true")
    args = parser.parse_args()
    package = Package(args.root)
    if args.negative_controls:
        try:
            result = negative_controls(package)
            print(json.dumps(result, indent=2))
            return 0
        except (OSError, ValueError) as e:
            print(json.dumps({"pass": False, "finding": str(e)}))
            return 1
    results = run(package, CHECKS if args.all or not args.check else [args.check])
    print(json.dumps(results, indent=2))
    return 0 if all(x["pass"] for x in results) else 1


if __name__ == "__main__":
    sys.exit(main())
