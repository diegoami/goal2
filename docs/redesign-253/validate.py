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
            "#242": "player-card-projection", "#243": "supported-entry-speed",
            "#198": "match-renderer-presentation", "#248": "personal-instruction-edits",
            "#249": "available-fixture-group-display", "#250": "watched-support-audit-first-action",
            "#251": "available-retained-summary-display"}
ISSUES = {"B01": 259, "B02": 260, "B03": 261, "B04": 262,
          "B05": 263, "B06": 265, "B07": 264}
LAYOUTS = ["01-country-setup", "02-country-desk", "03-team-workspace",
           "04-pool-compare", "05-competition", "06-match-preparation",
           "07-live-match", "08-result-and-campaign", "09-small-window",
           "10-match-decisions"]
GAP_FIELDS = {
    "G01": {"FX03", "FX04", "FX07", "MP01", "MP02", "MP07", "MP08"} | {f"IN{i:02}" for i in range(12, 19)},
    "G02": {"FX05"},
    "G03": {f"NW{i:02}" for i in range(1, 9)},
    "G04": {"MP09", "PR01", "PR02", "PR03", "PR05", "PR07", "PR08", "SV05", "SV06", "SV07", "RS19"},
    "G05": {f"{prefix}{i:02}" for prefix, count in [("CO", 14), ("CS", 8), ("CC", 4), ("HI", 24), ("HR", 9), ("TT", 8)] for i in range(1, count + 1)} | {"HU01", "HU03", "HU05"}}
VISIBLE_SURFACES = dict(zip(LAYOUTS, [[x] for x in ("S02", "S03", "S04", "S05", "S07", "S08", "S09", "S11", "S04", "S10")]))
ROSTER_NAMES = ["Van Breukelen", "Koeman", "Van Aerle", "Van Tiggelen", "Fordham", "Rijkaard", "Gullit", "Bergkamp", "Bosz", "Van Basten", "Kieft", "Hiele", "Snelders", "De Wolf", "Blind", "Wouters", "Winter", "Witschge", "Roy", "Eijkelkamp"]
CAP_SCOPE = {"Country ranks/status/profile/strips": "G05", "Complete country records": "G05",
 "Extra-time midpoint/shoot-out order": "G01",
 "Additional watched modes, watch scheduling and mode-dependent decisions": "G01",
 "Friendly cancellation and rearrangement": "G02", "Generated news and bulletin consequences": "G03",
 "Durable goal/summary capture, export and goal replay": "G04"}

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
        for item in ("Country desk", "Broadcast career", "Modern command room", *[f"O{i:02}" for i in range(1, 13)]):
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
        self.illustration_contracts()
        bounds = self.data(reg["layout_validation_receipt"])
        need(sha((self.path / "evidence/check_layout_bounds.py").read_bytes()) == bounds["helper_sha256"], "static bounds helper hash differs")
        need({x["svg"] for x in bounds["layouts"]} == {x + ".svg" for x in LAYOUTS}, "bounds receipt omits a layout")
        for item in bounds["layouts"]:
            need(item["static_svg_and_png_valid"] is True and item["out_of_canvas_text"] == [], "invalid/clipped static layout")
            file = self.path / "layouts" / item["svg"]
            need(sha(file.read_bytes()) == item["svg_sha256"] and sha(file.with_suffix(".png").read_bytes()) == item["png_sha256"], "layout changed after bounds/visual validation")
        return "A/B/C compared; O01–O12/gate;10 static sheets;20-name XI/bench strips;explicit scenarios;0 out-of-canvas text"

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
        allowed = set(EXISTING) | set(ISSUES) | {"UNOWNED:" + g for g in GAP_FIELDS}
        for key, row in source.items():
            need(all(row.values()), "blank evidence/category/source field: " + key)
            need(row["context"] == key[:2], "source context mismatch: " + key)
            need(set(row["screen"].split(";")) <= screenshots, "source screenshot absent: " + key)
            d = dest[key]
            need(d["context"] == row["context"], "destination context mismatch: " + key)
            targets = set(re.findall(r"S\d+", d["destination"]))
            need(targets and targets <= set(surfaces), "blank/unknown destination: " + key)
            owners = set(d["owner"].split("/"))
            need(owners and owners <= allowed, "unknown delivery/gap vocabulary: " + key)
            need(d["reuse"].strip(), "missing scoped reuse: " + key)
        self.scope_contracts()
        for key in (f"TT{i:02}" for i in range(1, 9)):
            need({"S02", "S06"} <= set(re.findall(r"S\d+", dest[key]["destination"])), "team tactics/default missing setup/scout context: " + key)
        for key in ("SD05", "SD06", "SV08", "ST04"):
            need("B06" in dest[key]["owner"], "assistant/identity dependency absent: " + key)
        rendered = "\n".join(self.read("parity/" + f + ".md") for f in ("management", "campaign", "match"))
        rendered_ids = re.findall(r"^\| ([A-Z]{2}\d{2}) \|", rendered, re.M)
        need(Counter(rendered_ids) == Counter(source.keys()), "rendered matrix omitted/duplicated field")
        for key in source:
            expected_cells = " | [designed] ".join([dest[key]["destination"], dest[key]["owner"], dest[key]["reuse"]])
            need(any(line.startswith("| " + key + " |") and line.endswith("[designed] " + expected_cells + " |") for line in rendered.splitlines()), "rendered destination/owner/reuse differs: " + key)
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
        by_image = {r["image"]: r for r in ledger}
        for image in ("country-select.png", "country-select-name-entry.png", "m244-team-info-2030.png"):
            need("TT01-TT08" in by_image[image]["trace"], "country image missing team-default trace: " + image)
        for key in (f"TT{i:02}" for i in range(1, 9)):
            targets = set(re.findall(r"S\d+", dest[key]["destination"]))
            need({"S02", "S06"} <= targets, "team tactics/default missing setup/scout context: " + key)
        return "234 source=allocated=rendered fields;12 skills/5 characteristics;23 contexts/17 categories;64 pinned image-name/hash traces (63 distinct byte hashes);5 explicit unowned capability decisions;country TT traces"

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
        need(len(cap) == 24 and all(all(r.values()) for r in cap), "incomplete capability register")
        # Representative drawings need not illustrate every surface covered by journeys.
        exact = VISIBLE_SURFACES
        for key, visible in exact.items():
            need(reg["layouts"][key] == visible, "layout claims a surface not visibly drawn: " + key)
        return "15 surfaces covered by9 journeys; automatic/player/conditional edges;24 scoped capability rows;all10 visible-surface mappings"

    def scope_contracts(self):
        """[designed: R1] Issue existence cannot satisfy excluded capability delivery."""
        records = self.data("capability-gaps.json")["gaps"]
        gaps = {g["id"]: g for g in records}
        need(len(records) == 5 and set(gaps) == set(GAP_FIELDS), "missing/duplicate unowned capability decision")
        dest = {r["id"]: r for r in self.rows("parity/destinations.tsv")}
        decisions = self.read("decisions.md")
        need("## Unowned capability decisions" in decisions, "unowned decisions not presented to owner")
        for gid, fields in GAP_FIELDS.items():
            g = gaps[gid]
            decision = "O" + str(8 + int(gid[1:]) - 1).zfill(2)
            need(g["decision"] == decision and f"| {decision} / {gid} |" in decisions, "gap has no operative owner decision: " + gid)
            need(g["capability_owner"] is None and g["implementation_authorized"] is False and g["required_for_full_parity"] is True, "gap silently assigned/authorized/excepted: " + gid)
            need(set(g["fields"]) == fields and len(g["fields"]) == len(fields), "gap field inventory differs from independent scope oracle: " + gid)
            need(all(g[k] for k in ("scope", "reuse", "recommendation", "priority", "size_risk", "next_contract_acceptance")), "gap next-scope requirements absent: " + gid)
            for field in fields:
                expected_owner = {"UNOWNED:" + gid} | ({"B03"} if field.startswith("TT") else set())
                need(field in dest and set(dest[field]["owner"].split("/")) == expected_owner, "excluded capability assigned to an existing issue: " + field + " requires explicit unowned delivery; existing issues are reuse only")
                reuse = dest[field]["reuse"]
                if "#249" in reuse or "#251" in reuse:
                    need("audit/display when available" in reuse, "conditional reuse qualification absent: " + field)
        for field in (f"TT{i:02}" for i in range(1, 9)):
            need("B03" in dest[field]["owner"] and "#248" not in dest[field]["owner"], "team controls reassigned to personal-edit issue: " + field)
        capabilities = {r["capability"]: r for r in self.rows("capabilities.tsv")}
        for name, gap in CAP_SCOPE.items():
            need(name in capabilities and "UNOWNED:" + gap in capabilities[name]["owner"], "capability register silently extends existing contract: " + name)
        for key, expected in (("B02", "O12/G05"), ("B05", "O08–O12/G01–G05")):
            need(expected in self.read("backlog/" + key + ".md"), "child hides unowned capability prerequisite: " + key)
        return "five unowned delivery gaps remain gated; existing issues only bounded conditional reuse"

    def illustration_contracts(self):
        """[designed: R2–R4] Inspect drawn names/sections, scrollbars and scenarios."""
        reg = self.data("package.json")
        records = self.data("illustrations.json")["sheets"]
        sheets = {r["layout"]: r for r in records}
        need(len(records) == 10 and set(sheets) == set(LAYOUTS), "illustration context omitted")
        for name, visible in VISIBLE_SURFACES.items():
            need(reg["layouts"][name] == visible and sheets[name]["visible_surfaces"] == visible, "layout overclaims a linked destination: " + name)
            tree = ET.fromstring((self.path / "layouts" / (name + ".svg")).read_bytes())
            texts = ["".join(n.itertext()) for n in tree.iter() if n.tag.endswith("text")]
            need(any("SCENARIO " + sheets[name]["scenario"] + ":" in t for t in texts), "scenario not visibly labelled: " + name)
            if name in ("03-team-workspace", "10-match-decisions"):
                nodes = [n for n in tree.iter() if n.get("data-roster-slot")]
                names = {n.get("data-roster-slot"): n for n in nodes}
                need(len(nodes) == 20 and set(names) == {str(i) for i in range(1, 21)}, "all20 named squad rows not drawn beside full card: " + name)
                for i, player in enumerate(ROSTER_NAMES, 1):
                    node = names[str(i)]
                    need("".join(node.itertext()) == player and node.get("data-squad-section") == ("XI" if i <= 11 else "Bench"), "squad identity/membership contradiction: " + name + " " + player)
                    need(218 <= float(node.get("x")) <= 848 and 290 <= float(node.get("y")) <= 744, "squad name outside visible decision strip")
                for field in SKILLS + CHARACTERISTICS:
                    need(field in texts, "complete card missing beside squad: " + name + " " + field)
            if name == "09-small-window":
                tracks = [n for n in tree.iter() if n.get("data-scroll-track") == "squad"]
                thumbs = [n for n in tree.iter() if n.get("data-scroll-thumb") == "squad"]
                need(len(tracks) == len(thumbs) == 1 and float(tracks[0].get("height")) > float(thumbs[0].get("height")) > 0, "small-window roster scrollbar absent")
                need(any("Jump to Bench 9" in t for t in texts), "small-window Bench jump absent")
                need(not any(n.get("x") == "24" and n.get("y") == "86" and n.get("width") == "1260" for n in tree.iter()), "small window retains underlying large shell/corner fragments")
            if name == "01-country-setup":
                need(not any(n.get("x") == "34" and n.get("width") == "152" and n.get("fill") == "#006C5B" for n in tree.iter()), "active career navigation highlighted during setup")
            if name == "04-pool-compare":
                need("Squad · midfielder · Bench" in texts and not any("confirmed XI" in t for t in texts), "pool preview contradicts bench membership")
            if name == "06-match-preparation":
                need(sheets[name]["scenario"] == "B" and "Bosz · MF" in texts and "Wouters · MF" not in texts, "friendly preparation contradicts shared initial XI")
                for country, x in (("Holland", "236"), ("Belgium", "598")):
                    lineup = ["".join(n.itertext()).split(" · ")[1] for n in tree.iter() if n.tag.endswith("text") and n.get("x") == x and 375 <= float(n.get("y", "0")) <= 655]
                    need(len(lineup) == 11 and lineup.count("GK") == 1, "named preparation lineup incomplete: " + country)
                    defenders = sum(r in {"SW", "CB", "LB", "RB"} for r in lineup)
                    midfield = lineup.count("MF")
                    forwards = lineup.count("FW")
                    need(f"{country} · {defenders}–{midfield}–{forwards}" in texts, "formation contradicts named lineup roles: " + country)
            if name == "07-live-match":
                need(sheets[name]["scenario"] == "B" and any("view-only" in t for t in texts), "friendly illustration implies new active Watch management")
        return "all10 mappings honest;20 named XI/bench rows;explicit small-window relocation and independent scenarios"

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
        self.scope_contracts()
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
        for key, deps in {"B01": ["#242"], "B02": ["G05", "B06"], "B03": ["#248", "#249"], "B05": ["B06", "B07", "G01–G05", "capability"]}.items():
            for dep in deps:
                need(dep in by[key]["dependencies"], "dependency absent: " + key + " " + dep)
        for key, dep in (("B02", "B06"), ("B05", "B06"), ("B05", "B07")):
            need(dep in self.read(by[key]["contract"]), "contract/manifest dependency mismatch: " + key)
        index = (self.root / "docs/tasks/README.md").read_text()
        for n in ISSUES.values():
            need(f"/issues/{n}" in index and f"/issues/{n}" in self.read("backlog.md"), "filed scope absent from proposed order")
        return "7 filed scoped gated issues;9 existing owners preserved;dependencies and task index linked;no duplicate area ownership;5 unowned scopes tied to owner decisions"

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
        allowed = lambda x: x.startswith("docs/redesign-253/") or x in {"docs/tasks/README.md", "docs/model-trials.md"}
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
        return f"{len(changed)} changed files limited to task docs/index and explicit process lesson;JSON valid;no app/engine/dependency/original payload changes"


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
          "backlog/B03.md": lambda t: t.replace("COMPOSITION only", "COMPOSITION and available fixture/group display ownership")}),
        ("watch-flags-assigned-to249", "backlog", {dst: lambda t: set_cell(t, "FX03", "owner", "#249")}),
        ("friendly-rearrangement-assigned-to249", "backlog", {dst: lambda t: set_cell(t, "FX05", "owner", "#249")}),
        ("generated-news-assigned-to249", "backlog", {dst: lambda t: set_cell(t, "NW01", "owner", "#249")}),
        ("competitive-watch-assigned-to250", "backlog", {dst: lambda t: set_cell(t, "IN12", "owner", "#250")}),
        ("durable-replay-assigned-to251", "backlog", {dst: lambda t: set_cell(t, "SV06", "owner", "#251")}),
        ("setup-profile-assigned-to249", "backlog", {dst: lambda t: set_cell(t, "CO05", "owner", "#249")}),
        ("resolved-gap-without-owner-choice", "backlog", {"capability-gaps.json": resolve_gap}),
        ("capability-register-profile-overreach", "backlog", {"capabilities.tsv": lambda t: set_cell(t, "Country ranks/status/profile/strips", "owner", "#249", "capability")}),
        ("linked-profile-claimed-as-drawn", "journeys", {"package.json": overclaim_profile}),
        ("formation-disagrees-with-lineup", "proposal", {"layouts/06-match-preparation.svg": wrong_formation}),
        ("missing-twentieth-bench-name", "proposal", {"layouts/03-team-workspace.svg": missing_bench_name}),
        ("small-window-scrollbar-omitted", "proposal", {"layouts/09-small-window.svg": missing_scrollbar}),
        ("team-default-relocation-omitted", "parity", {dst: lambda t: set_cell(t, "TT01", "destination", "S04 Team instructions; S08 preparation"),
          "parity/management.md": lambda t: t.replace("S02/S06 read-only country tactics/defaults; S04 Team instructions; S08 preparation", "S04 Team instructions; S08 preparation", 1)}),
        ("country-screenshot-team-default-trace-omitted", "parity", {"evidence/screens-inspected.tsv": missing_country_tt})]
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


def set_cell(text, key, column, value, key_column="id"):
    rows = list(csv.DictReader(io.StringIO(text), delimiter="\t"))
    next(r for r in rows if r[key_column] == key)[column] = value
    out = io.StringIO()
    writer = csv.DictWriter(out, fieldnames=list(rows[0]), delimiter="\t", lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    return out.getvalue()


def resolve_gap(text):
    data = json.loads(text)
    next(g for g in data["gaps"] if g["id"] == "G05")["required_for_full_parity"] = False
    return json.dumps(data, indent=2) + "\n"


def overclaim_profile(text):
    data = json.loads(text)
    data["layouts"]["05-competition"].append("S06")
    return json.dumps(data, indent=2) + "\n"


def remove_svg_element(text, attribute, value):
    tree = ET.fromstring(text)
    for parent in tree.iter():
        for child in list(parent):
            if child.get(attribute) == value:
                parent.remove(child)
                return ET.tostring(tree, encoding="unicode")
    raise ValueError("control target SVG element absent")


def wrong_formation(text):
    return text.replace("Belgium · 4–4–2", "Belgium · 5–4–1")


def missing_bench_name(text):
    return remove_svg_element(text, "data-roster-slot", "20")


def missing_scrollbar(text):
    return remove_svg_element(text, "data-scroll-track", "squad")


def missing_country_tt(text):
    rows = list(csv.DictReader(io.StringIO(text), delimiter="\t"))
    row = next(r for r in rows if r["image"] == "country-select.png")
    return set_cell(text, "country-select.png", "trace", row["trace"].replace("/TT01-TT08", ""), "image")


def duplicate_campaign(text):
    items = json.loads(text)
    next(x for x in items if x["key"] == "B03")["owned_areas"].append("available-fixture-group-display")
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
