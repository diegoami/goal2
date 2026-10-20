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
# [designed: #253 reconciliation] Merge commit of accepted vision #266 / PR #267; its screens are pinned by bytes.
VISION = "9683a47647f21bd2a3274ea5dc56bb8c14e6c5a9"
# Reviewed234-field source inventory at32d6c51c; destination partition must not edit it.
SOURCE_INVENTORY_SHA256 = "d69ee5bff1afde58e0de4d0235b8bc63cb7d73d8be6761b687fa78523cf34282"
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
    "G01": {"FX03", "FX04", "FX07", "MP01-G", "MP02", "MP07-G", "MP08", "LI08"} | {f"IN{i:02}" for i in range(12, 19)},
    "G02": {"FX05"},
    "G03": {f"NW{i:02}" for i in range(1, 9)},
    "G04": {"MP09", "PR01", "PR02", "PR03", "PR05", "PR07", "PR08", "SV05", "SV06", "SV07", "RS19"},
    "G05": {f"{prefix}{i:02}" for prefix, count in [("CO", 14), ("CS", 8), ("CC", 4), ("HI", 24), ("HR", 9), ("TT", 8)] for i in range(1, count + 1)} | {"HU01-G", "HU03", "HU05"}}
GAP_FIELDS["G05"].remove("CO01")
VISIBLE_SURFACES = dict(zip(LAYOUTS, [[x] for x in ("S02", "S03", "S04", "S05", "S07", "S08", "S09", "S11", "S04", "S10")]))
ROSTER_NAMES = ["Van Breukelen", "Koeman", "Van Aerle", "Van Tiggelen", "Fordham", "Rijkaard", "Gullit", "Bergkamp", "Bosz", "Van Basten", "Kieft", "Hiele", "Snelders", "De Wolf", "Blind", "Wouters", "Winter", "Witschge", "Roy", "Eijkelkamp"]
CAP_SCOPE = {"Country ranks/status/profile/strips": "G05", "Complete country records": "G05",
 "Extra-time midpoint/shoot-out order": "G01",
 "Additional watched modes, watch scheduling and mode-dependent decisions": "G01",
 "Quick continuation during watched play": "G01",
 "Friendly cancellation and rearrangement": "G02", "Generated news and bulletin consequences": "G03",
 "Durable goal/summary capture, export and goal replay": "G04"}

# Independent source-to-allocation partition: source IDs/categories never change.
SPLIT_FIELDS = {
    "HU01": {"S": ("Active managed country and existing manager name", "B03"),
             "G": ("Manager rating and complete manager-profile projection", "UNOWNED:G05")},
    "MP01": {"S": ("Supported friendly Quick/Watch, competitive Quick and managed side", "#243/B04"),
             "G": ("Competitive/other-country Watch and unsupported mode-dependent delivery", "UNOWNED:G01")},
    "MP07": {"S": ("Captain selection in Team and confirmed captain before supported friendly Watch", "B03/#250"),
             "G": ("Explicit watched captain prompt beyond audited supported first choice", "UNOWNED:G01")}}
CARD_SKILLS = {"2610": [20, 23, 5, 8, 11, 14, 17, 20, 23, 5, 8, 11],
               "2628": [4, 11, 18, 4, 11, 18, 4, 11, 18, 4, 11, 18]}
CARD_CHARACTERISTICS = {"2610": [6, 24, 27, 17, 4], "2628": [6, 24, 28, 20, 4]}

# [designed: #253 reconciliation] Independent oracles for the accepted-vision mapping: a registry that
# drops a screen, claims an undrawn surface or re-recommends a superseded layout cannot satisfy itself.
VISION_SCREENS = ["01-start-resume", "02-country-desk", "03-team", "04-pool", "05-preparation", "06-watched",
                  "07-half-time", "08-result", "09-continue", "10-career", "11-small-window", "12-unavailable-errors",
                  "13-conditional", "14-team-focus", "15-watched-drawers", "16-team-tactics", "17-small-roster",
                  "18-later-squad", "19-campaign"]
SURFACE_COVERAGE = {"S01": "drawn", "S02": "partial", "S03": "drawn", "S04": "drawn", "S05": "drawn", "S06": "undrawn",
                    "S07": "partial", "S08": "drawn", "S09": "drawn", "S10": "drawn", "S11": "drawn", "S12": "partial",
                    "S13": "partial", "S14": "partial", "S15": "undrawn"}
LAYOUT_SUCCESSOR = {"01-country-setup": {"01"}, "02-country-desk": {"02"}, "03-team-workspace": {"03", "14", "16"},
                    "04-pool-compare": {"04"}, "05-competition": {"09", "19"}, "06-match-preparation": {"05"},
                    "07-live-match": {"06", "15"}, "08-result-and-campaign": {"08", "09"},
                    "09-small-window": {"11", "17"}, "10-match-decisions": {"07", "13"}}
QUEUE_LANES = {1: [253, 270], 2: [198, 242, 243, 259], 3: [260, 261, 262, 249, 263],
               4: [110, 112, 113, 114, 115, 116, 117, 118, 119], 5: [248, 250, 251, 265, 264]}
QUEUE_EXTRA = {155, 208, 268}   # #155 before #117; #208/#268 keep their own tooling scope
# [designed: #253 rework R3] Every approved dependency as an explicit directed pair (before, after, source), held here and
# nowhere else as an oracle. The registry and the canonical tables in three documents must equal it exactly. Prose is not
# interpreted: order words and arrows are forbidden in lane rows, reverse arrows everywhere, and a clause that names two issues
# around an order word may not contradict a pair.
DEPENDENCIES = [(198, 242, "lane 2"), (198, 243, "lane 2"), (260, 261, "lane 3"), (261, 262, "lane 3"), (262, 251, "lane 3"),
                (110, 112, "lane 4"), (112, 113, "lane 4"), (113, 114, "lane 4"), (114, 115, "lane 4"), (115, 116, "lane 4"),
                (116, 117, "lane 4"), (117, 118, "lane 4"), (118, 119, "lane 4"), (155, 117, "lane 4")]
NOT_PREREQUISITE = [(259, 198, "lane 2"), (259, 242, "lane 2"), (259, 243, "lane 2")]
FOLLOW_ON = {3: [251]}   # #251 follows the base match journey (#262); the lane's follow_on list must say so
DEPENDENCY_HEADER = ["Before", "After", "Source"]
NOT_PREREQUISITE_HEADER = ["Not a prerequisite", "Of", "Source"]
# [designed: #253 rework R1] Independent screen/journey oracles, derived from the accepted storyboard (not from the registry).
SURFACE_NAMES = {"S01": "Launch", "S02": "New career", "S03": "Country desk", "S04": "Team", "S05": "Pool comparison",
                 "S06": "Country profile", "S07": "Competition", "S08": "Preparation", "S09": "Live", "S10": "Decision",
                 "S11": "Result", "S12": "Archive", "S13": "Game save/load", "S14": "Bulletin", "S15": "Local-manager handoff"}
SURFACE_SCREEN_ORACLE = {"S01": ["01"], "S02": ["01"], "S03": ["02", "09"], "S04": ["03", "11", "14", "16", "17", "18"], "S05": ["04"],
                         "S06": [], "S07": ["09", "19"], "S08": ["05"], "S09": ["06", "15"], "S10": ["07", "13"], "S11": ["08"],
                         "S12": ["10", "18", "19"], "S13": ["01", "09", "12"], "S14": ["19"], "S15": []}
SURFACE_ROUTE_ORACLE = {"S06": ["02", "05"], "S15": []}
SURFACE_OWNER_ORACLE = {"S02": {"#260"}, "S06": {"#261", "G05"}, "S07": {"#249", "#261"}, "S12": {"#251", "G04"},
                        "S13": {"#260"}, "S14": {"G03", "#249"}, "S15": {"#264"}}
JOURNEY_SCREEN_ORACLE = {"J01": ["01", "12"], "J02": ["02", "09"], "J03": ["03", "04", "11", "14", "16", "17"], "J04": ["02", "05", "19"],
                         "J05": ["05", "12"], "J06": ["06", "07", "15"], "J07": ["07", "13"], "J08": ["08", "09", "10", "18", "19"],
                         "J09": ["01", "09", "12"]}
JOURNEY_ORACLE = {"J01": (["S01", "S02", "S13"], ["new", "load", "invalid-save", "replacement", "identity-capability"]),
                  "J02": (["S03", "S14"], ["next-fixture", "calendar-boundary", "news"]),
                  "J03": (["S04", "S05"], ["compare", "draft-confirm", "draft-discard", "pool-policy", "assistant-identity-capability"]),
                  "J04": (["S06", "S07", "S08"], ["opponent-read-only", "group-fixtures", "history-source"]),
                  "J05": (["S08", "S09"], ["quick", "watch", "speed", "unsupported-route"]),
                  "J06": (["S09", "S10"], ["live-clock", "commentary", "supported-boundary", "off-on", "cancel"]),
                  "J07": (["S10", "S11"], ["halftime", "quick-injury-repeat", "extra-time", "extra-midpoint", "shoot-order", "undo", "timed-default", "no-subs-unknown"]),
                  "J08": (["S11", "S12", "S03", "S07", "S14"], ["statistics", "not-recorded", "round", "continue", "archive", "replay-dependency"]),
                  "J09": (["S13", "S15", "S01"], ["save", "resume", "quit", "handoff", "multimanager-capability"])}
# [designed: #253 rework sweep] Evidence that two mutable files used to vouch for each other is now also pinned by hash,
# so a coordinated edit of a file and its receipt fails. The live amended bodies are the external truth for #259-#265.
PINNED_EVIDENCE = {"evidence/layout-bounds-05.json": "9094c46eafeb22c601a0aabafd243220321c83b9fcd3f973bf84928f1db6b67a",
                   "evidence/runtime-06/report.json": "9a53a126f3502706682b6342445bb53f4b47cae3d1c5021f2df2115f35972209",
                   "evidence/browser-03/report.json": "eda0e1a332026c2ac6f8368150366755a695df7a99d84853f02f08d6edd05ace"}
LIVE_BODY_SHA256 = {"B01": "f18f0c4f902a316ddeae545535bdd1101b6cd5909c0852c3ede6b330233f893c", "B02": "1af09b32a1f0962e75b88eee4ac226d219a01da87b8101c07b817bf2ffb7250a",
                    "B03": "151385323d058ebd9502c084ed53d39df6e6dc84349e7eb61b920164af8821b9", "B04": "0851fd69ce9520325c1e6e8759c82b822aa955dec5efc9f994da5a1d7598f7b1",
                    "B05": "736df4ca4240d6a8e61ee5ba61d2907f121b135b43e1527c03b7b62ae4f02233", "B06": "ff9d081b13e905c8f0a99f2f4130b18efbeb303bcbb7ecc0a480f7fd1df88a75",
                    "B07": "aed16d4fcb28d8bbfe8883a91f2e1cb953081987b73ffa088431e4b75d9e8656"}
CHILD_LANE = {"B01": 2, "B02": 3, "B03": 3, "B04": 3, "B05": 3, "B06": 5, "B07": 5}
CHILD_PRIORITY = {"B01": "P1", "B02": "P1", "B03": "P1", "B04": "P1", "B05": "P1", "B06": "P2", "B07": "P2"}
# Scope obligations that stay under #253: each must say plainly that it has no delivery owner.
OBLIGATIONS = {"O08 / G01": "bounded contract", "O09 / G02": "bounded contract", "O10 / G03": "bounded contract",
               "O11 / G04": "bounded contract", "O12 / G05": "bounded contract", "O13": "bounded original-evidence contract",
               "O14": "bounded implementation contract"}
OPEN_CHOICES = ("O02", "O03", "O04", "O05", "O06", "O07")
OBSOLETE_PHRASES = ("Recommend A", "Recommend **A", "(recommended)", "Select A/B/C", "select **A Country desk**",
                    "Direction A", "recommended_direction")
CHECKS = ("proposal", "parity", "journeys", "current", "backlog", "technology", "scope", "vision")


def need(condition, message):
    if not condition:
        raise ValueError(message)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def table_blocks(lines):
    """[designed: #253 rework R4] A table is the whole contiguous block of pipe-led lines: (index of its first line, its lines)."""
    blocks, current = [], None
    for i, line in enumerate(lines):
        if line.lstrip().startswith("|"):
            if current is None:
                current = (i, [])
                blocks.append(current)
            current[1].append(line)
        else:
            current = None
    return blocks


def table_cells(line, where):
    """Cells of one pipe row, whitespace-insensitive; a pipe row must also end with a pipe."""
    s = line.strip()
    need(len(s) > 1 and s.startswith("|") and s.endswith("|"), f"malformed table row in {where}: {s[:70]}")
    return [c.strip() for c in s[1:-1].split("|")]


def parse_block(block, where):
    """(header cells, [(line index, line, cells)]); the separator is verified and every row must have the header's cell count."""
    start, lines = block
    header = table_cells(lines[0], where)
    need(len(lines) >= 2, f"table without a separator row in {where}")
    separator = table_cells(lines[1], where)
    need(len(separator) == len(header) and all(re.fullmatch(r":?-{3,}:?", c) for c in separator), f"table without a separator row in {where}: {lines[0].strip()[:50]}")
    rows = []
    for offset, line in enumerate(lines[2:], 2):
        cells = table_cells(line, where)
        need(len(cells) == len(header), f"table row with {len(cells)} cells under a {len(header)}-cell header in {where}: {line.strip()[:70]}")
        rows.append((start + offset, line, cells))
    return header, rows


def keyed_rows(text, first_header, key_pattern, where, headers=None):
    """Parse whole every table headed by `headers` (default first_header): each row's first cell must match key_pattern, once. {key: cells}."""
    found, tables = {}, 0
    for block in table_blocks(text.splitlines()):
        header, rows = parse_block(block, where)
        if header[0] not in (headers or (first_header,)):
            continue
        tables += 1
        for _, line, cells in rows:
            m = re.fullmatch(key_pattern, cells[0])
            need(m, f"unparsed row in the {header[0]} table of {where}: {line.strip()[:70]}")
            key = m.group(1)
            need(key not in found, f"duplicate {key} row in the {header[0]} table of {where}")
            found[key] = cells
    need(tables, f"no {first_header} table in {where}")
    return found


class Package:
    def __init__(self, root, base=None):
        self.root = root.resolve()
        self.path = self.root / "docs/redesign-253"
        self.base = base

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
        for phrase in ("Explicit owner direction approval is no longer outstanding", "no new child issue starts from it automatically",
                       "Plan acceptance is not implementation approval", "No toolkit, backend-language or architecture migration is authorized",
                       "Existing independently authorized work retains its own scope"):
            need(phrase in gate, "operative gate missing: " + phrase)
        need(self.data("package.json")["implementation_authorized"] is False, "registry authorizes implementation")

    def proposal(self):
        self.gate()
        for f in ("README.md", "assessment.md", "information-parity.md", "journeys.md", "layouts.md", "decisions.md",
                  "technology.md", "backlog.md", "validation.md", "vision-reconciliation.md"):
            need(len(self.read(f)) > 700, "proposal document absent/empty: " + f)
        index = self.read("README.md")
        need("being assembled" not in index, "transient index instead of decision package")
        need("The direction is chosen" in index and "docs/vision-266" in index.replace("../vision-266", "docs/vision-266"),
             "README does not state the accepted #266 direction")
        for f in ("README.md", "decisions.md", "technology.md", "backlog.md", "journeys.md", "assessment.md", "layouts.md",
                  "information-parity.md", "vision-reconciliation.md", "backlog.json", "package.json", "capability-gaps.json"):
            for phrase in OBSOLETE_PHRASES:
                need(phrase not in self.read(f), "obsolete direction recommendation or selection question in " + f + ": " + phrase)
        options = self.read("decisions.md")
        history = re.search(r"^## Historical candidate directions \(superseded\)\n(.*?)(?=^## |\Z)", options, re.M | re.S)
        need(history, "historical candidate directions not marked superseded")
        for item in ("Country desk", "Broadcast career", "Modern command room"):
            need(item in history.group(1), "historical candidate direction missing: " + item)
        outside = options.replace(history.group(0), "")
        for term in ("paper", "emerald"):
            need(term not in outside, "obsolete visual selection outside the historical section: " + term)
        for i in range(1, 15):
            need(f"O{i:02}" in options, "missing owner decision: " + f"O{i:02}")
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
        self.illustration_quality()
        self.departure_contracts()
        need(sha((self.path / reg["layout_validation_receipt"]).read_bytes()) == PINNED_EVIDENCE[reg["layout_validation_receipt"]],
             "layout bounds receipt differs from the pinned reviewed receipt")
        bounds = self.data(reg["layout_validation_receipt"])
        need(sha((self.path / "evidence/check_layout_bounds.py").read_bytes()) == bounds["helper_sha256"], "static bounds helper hash differs")
        need({x["svg"] for x in bounds["layouts"]} == {x + ".svg" for x in LAYOUTS}, "bounds receipt omits a layout")
        for item in bounds["layouts"]:
            need(item["static_svg_and_png_valid"] is True and item["out_of_canvas_text"] == [], "invalid/clipped static layout")
            file = self.path / "layouts" / item["svg"]
            need(sha(file.read_bytes()) == item["svg_sha256"] and sha(file.with_suffix(".png").read_bytes()) == item["png_sha256"], "layout changed after bounds/visual validation")
        return "accepted #266 direction stated; no obsolete recommendation/selection question; A/B/C historical only; O01–O14/gate;10 historical sheets intact;20-name XI/bench strips;explicit scenarios;0 out-of-canvas text"

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
        self.allocation_contracts()
        need(len({r["category"] for r in src}) == 17, "missing original category")
        contexts = self.rows("parity/contexts.tsv")
        need({r["context"] for r in contexts} == set(GROUPS) and len(contexts) == 23, "missing/duplicate decision context")
        for context in contexts:
            need(all(context.values()), "blank when/why/access/owner/limit context")
        surfaces = self.data("package.json")["surfaces"]
        screenshots = {p.name for p in (self.root / "docs/original-game/images").glob("*.png")}
        allowed = set(EXISTING) | set(ISSUES) | {"UNOWNED:" + g for g in GAP_FIELDS}
        for key, d in dest.items():
            row = source[d["source_id"]]
            need(all(row.values()), "blank evidence/category/source field: " + key)
            need(row["context"] == key[:2], "source context mismatch: " + key)
            need(set(row["screen"].split(";")) <= screenshots, "source screenshot absent: " + key)
            need(d["context"] == row["context"], "destination context mismatch: " + key)
            targets = set(re.findall(r"S\d+", d["destination"]))
            need(targets and targets <= set(surfaces), "blank/unknown destination: " + key)
            owners = set(d["owner"].split("/"))
            need(owners and owners <= allowed, "unknown delivery/gap vocabulary: " + key)
            need(d["reuse"].strip(), "missing scoped reuse: " + key)
        self.scope_contracts()
        self.quick_continuation_contracts()
        self.reuse_contracts()
        for key in (f"TT{i:02}" for i in range(1, 9)):
            need({"S02", "S06"} <= set(re.findall(r"S\d+", dest[key]["destination"])), "team tactics/default missing setup/scout context: " + key)
        for key in ("SD05", "SD06", "SV08", "ST04"):
            need("B06" in dest[key]["owner"], "assistant/identity dependency absent: " + key)
        rendered = "\n".join(self.read("parity/" + f + ".md") for f in ("management", "campaign", "match"))
        # [designed: #253 rework R4] whole-table parse: a row that is not an allocation row fails instead of being skipped
        rendered_ids = []
        for f in ("management", "campaign", "match"):
            for block in table_blocks(self.read("parity/" + f + ".md").splitlines()):
                header, rows = parse_block(block, "parity/" + f + ".md")
                need(header[0] == "Allocation ID", f"parity/{f}.md has a table that is not an allocation matrix: {header[0]}")
                for _, line, cells in rows:
                    need(re.fullmatch(r"[A-Z]{2}\d{2}(?:-[SG])?", cells[0]), f"unparsed allocation row in parity/{f}.md: {line.strip()[:70]}")
                    rendered_ids.append(cells[0])
        need(Counter(rendered_ids) == Counter(dest.keys()), "rendered matrix omitted/duplicated allocation")
        for key in dest:
            expected_cells = " | [designed] ".join([dest[key]["destination"], dest[key]["owner"], dest[key]["reuse"]])
            sid = dest[key]["source_id"]
            information = source[sid]["information"]
            if sid != key:
                information = sid + " — " + information + "; [designed allocation] " + dest[key]["information"]
            expected_line = "| " + key + " | " + information + " | [designed] " + expected_cells + " |"
            need(expected_line in rendered.splitlines(), "rendered source/allocation/destination/owner/reuse differs: " + key)
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
        return "234 unchanged source fields=237 complete allocations=rendered;12 skills/5 characteristics;23 contexts/17 categories;64 pinned image-name/hash traces (63 distinct byte hashes);5 explicit unowned capability decisions;country TT traces"

    def journeys(self):
        reg = self.data("package.json")
        text = self.read("journeys.md")
        surfaces = {f"S{i:02}" for i in range(1, 16)}
        journeys = {f"J{i:02}" for i in range(1, 10)}
        need(set(reg["surfaces"]) == surfaces, "screen hierarchy incomplete")
        need(set(reg["journeys"]) == journeys, "journey registry incomplete")
        need(set(keyed_rows(text, "Key", r"(S\d{2})", "journeys.md")) == surfaces, "screen hierarchy prose incomplete")
        need(set(re.findall(r"^## (J\d{2})", text, re.M)) == journeys, "journey prose incomplete")
        need({x for j in reg["journeys"].values() for x in j["surfaces"]} == surfaces, "journeys omit a surface")
        need(reg["surfaces"] == SURFACE_NAMES, "surface names differ from the independent oracle")
        for key, j in reg["journeys"].items():
            need(j["edges"] and set(j["surfaces"]) <= surfaces, "empty/unknown journey edge")
            need((j["surfaces"], j["edges"]) == JOURNEY_ORACLE[key], "journey surfaces or edges differ from the independent oracle: " + key)
        for phrase in ("automatic", "player", "Start second half", "Start extra time", "Resume extra time", "Undo", "timed", "No-substitutions-left", "view-only", "Not recorded", "atomic", "handoff", "B06", "B07"):
            need(phrase in text, "significant transition/capability missing: " + phrase)
        cap = self.rows("capabilities.tsv")
        for phrase in ("Local manager", "identities", "Assistant", "shoot-out", "halftime", "replay", "competitive"):
            need(any(phrase.lower() in " ".join(r.values()).lower() for r in cap), "capability dependency omitted: " + phrase)
        self.quick_continuation_contracts()
        need(len(cap) == 25 and all(all(r.values()) for r in cap), "incomplete capability register")
        # Representative drawings need not illustrate every surface covered by journeys.
        exact = VISIBLE_SURFACES
        for key, visible in exact.items():
            need(reg["layouts"][key] == visible, "layout claims a surface not visibly drawn: " + key)
        return "15 surfaces covered by9 journeys; automatic/player/conditional edges;25 scoped capability rows;all10 visible-surface mappings"

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
        for key, expected in (("B02", "G05"), ("B05", "G01-G05")):
            need(expected in self.read("backlog/" + key + ".md"), "child hides unowned capability prerequisite: " + key)
        self.allocation_contracts()
        return "five unowned delivery gaps remain gated; existing issues only bounded conditional reuse"

    def allocation_contracts(self):
        """[designed: R2] Preserve all original categories, partition mixed delivery."""
        src = self.rows("parity/source-fields.tsv")
        source = {r["id"]: r for r in src}
        original = {f"{p}{i:02}" for p, count in GROUPS.items() for i in range(1, count + 1)}
        need(len(src) == 234 and set(source) == original, "independent234-source inventory differs")
        need(sha((self.path / "parity/source-fields.tsv").read_bytes()) == SOURCE_INVENTORY_SHA256, "reviewed original field meanings/categories changed during allocation split")
        need(len({r["category"] for r in src}) == 17 and {r["context"] for r in src} == set(GROUPS), "original categories/contexts lost")
        rows = self.rows("parity/destinations.tsv")
        dest = {r["id"]: r for r in rows}
        expected = (original - set(SPLIT_FIELDS)) | {key + "-" + part for key, parts in SPLIT_FIELDS.items() for part in parts}
        need(len(rows) == 237 and set(dest) == expected, "mixed source fields need237 independent supported/residual allocations")
        for key, row in dest.items():
            sid = key.split("-")[0]
            need(row["source_id"] == sid and row["context"] == source[sid]["context"], "allocation loses original source/context: " + key)
            if sid in SPLIT_FIELDS:
                information, owner = SPLIT_FIELDS[sid][key[-1]]
                need(row["information"] == information and row["owner"] == owner, "supported/residual scope collapsed or misowned: " + key)
            else:
                need(row["information"] == source[sid]["information"], "unsplit original information changed: " + key)
        need(dest["CO01"]["owner"] == "B02/B03", "supported country identity/list/selection incorrectly unowned")
        for context, count in GROUPS.items():
            need({r["source_id"] for r in rows if r["context"] == context} == {f"{context}{i:02}" for i in range(1, count + 1)}, "allocation drops original category context: " + context)
        return "234 original sources/17 categories/23 contexts retained;237 exact allocations;four supported areas separated from residual gaps"

    def quick_continuation_contracts(self):
        """[designed: R2 R1] Existing supported entry cannot imply an in-flight mode switch."""
        dest = {r["id"]: r for r in self.rows("parity/destinations.tsv")}
        need(dest["LI08"]["owner"] == "UNOWNED:G01" and "#250 audit only" in dest["LI08"]["reuse"], "quick continuation has no delivery contract;LI08 must beG01/#250 audit only")
        gaps = {g["id"]: g for g in self.data("capability-gaps.json")["gaps"]}
        need("LI08" in gaps["G01"]["fields"], "G01 omits original R-result capability")
        caps = {r["capability"]: r for r in self.rows("capabilities.tsv")}
        row = caps.get("Quick continuation during watched play", {})
        need(row.get("owner") == "UNOWNED:G01" and "unavailable" in row.get("dependency_or_limit", "").lower(), "quick continuation missing scoped unavailable capability row")
        journey = self.read("journeys.md")
        need("Quick continuation is unavailable" in journey and "no supported in-flight mode switch" in journey, "J06 implies available fast-finish")
        tree = ET.fromstring((self.path / "layouts/07-live-match.svg").read_bytes())
        labels = ["".join(n.itertext()) for n in tree.iter() if n.tag.endswith("text")]
        need("Finish quickly · unavailable" in labels and "No supported in-flight mode switch · G01" in labels, "07 lacks visible quick-continuation refusal/reason")
        boxes = [n for n in tree.iter() if n.get("data-action") == "quick-continuation"]
        need(len(boxes) == 1 and boxes[0].get("data-state") == "unavailable" and boxes[0].get("fill") == "#DFE7E3", "07 quick-continuation drawn as enabled")
        return "LI08/G01;explicit absent in-flight capability;07/J06 unavailable with reason"

    def departure_contracts(self):
        text = self.read("decisions.md")
        departures = text.split("## Deliberate departures from the original", 1)[1].split("## Decisions for the owner", 1)[0]
        need("↔-speed" in departures and "T85" in departures and "freezes" in departures and "separately approved" in departures, "original live-speed departure/acceptedT85 boundary unrecorded")
        return "original live speed versus accepted frozenT85 recorded as proposed departure;no new engine authority"

    def reuse_contracts(self):
        rows = {r["id"]: r for r in self.rows("parity/destinations.tsv")}
        for i in range(1, 9):
            text = rows[f"TT{i:02}"]["reuse"]
            need("existing Squad page" in text and "T84 read-only display" not in text and "#248 owns personal edits only" in text, "TT reuse incorrectly assigned to player-cardT84")
        return "team-bit display remains existing Squad/B03 composition;personal/player scope separate"

    def illustration_quality(self):
        """[designed: R2 R3/R4] Validate visible values/state, beyond receipt hashes."""
        trees = {name: ET.fromstring((self.path / "layouts" / (name + ".svg")).read_bytes()) for name in LAYOUTS}
        texts = {name: [n for n in tree.iter() if n.tag.endswith("text")] for name, tree in trees.items()}
        for name, nodes in texts.items():
            strings = ["".join(n.itertext()) for n in nodes]
            expected_tier = "FULL-PARITY TARGET" if name in {"01-country-setup", "02-country-desk", "05-competition", "08-result-and-campaign", "10-match-decisions"} else "FIRST SLICE"
            need(any(s.startswith(expected_tier + " · ") for s in strings), "illustration delivery tier unlabelled/misleading: " + name)
            record = next(s for s in self.data("illustrations.json")["sheets"] if s["layout"] == name)
            need(record["delivery_tier"] == ("full-parity target" if expected_tier.startswith("FULL") else "first slice"), "illustration tier registry disagrees: " + name)
            for s in strings:
                need(not re.search(r"·(?=\d)|remaining:(?=\d)|retains(?=\d)|tied(?=\d)", s), "visible spacing typo: " + name + " " + s)
        hero = ["".join(n.itertext()) for n in texts["02-country-desk"]]
        need("Holland · world 14 · Europe 3" in hero and "Belgium · world 8 · Europe 9" in hero, "hero ranks have ambiguous own/opponent notation")
        need(any("G03 bulletin / G05 ranks" in s and "unowned" in s for s in hero), "hero target hides unowned bulletin/ranks")
        for name, pid, xmin, xmax in (("04-pool-compare", "2610", 541, 895), ("10-match-decisions", "2610", 842, 1264), ("03-team-workspace", "2628", 864, 1264), ("09-small-window", "2628", 360, 908)):
            nodes = [n for n in texts[name] if xmin <= float(n.get("x", "0")) <= xmax]
            for field, value in zip(SKILLS + CHARACTERISTICS, CARD_SKILLS[pid] + CARD_CHARACTERISTICS[pid]):
                labels = [n for n in nodes if (n.text or "") == field or (n.text or "").startswith(field + " ")]
                need(len(labels) == 1, "card field absent/ambiguous: " + name + " " + field)
                label = labels[0]
                combined = re.fullmatch(re.escape(field) + r" (\d+)", label.text or "")
                if combined:
                    actual = int(combined[1])
                else:
                    values = [n for n in nodes if n.get("y") == label.get("y") and float(n.get("x", "0")) > float(label.get("x", "0")) and (n.text or "").isdigit()]
                    need(values, "card value absent: " + name + " " + field)
                    actual = int(min(values, key=lambda n: float(n.get("x"))).text)
                need(actual == value, "same-ID illustrative card disagrees: " + name + " " + pid + " " + field)
        for name, pid, xmin, xmax in (("04-pool-compare", "2610", 541, 895), ("10-match-decisions", "2610", 842, 1264), ("03-team-workspace", "2628", 864, 1264), ("09-small-window", "2628", 360, 908)):
            need(any(re.search(r"\bID\s+" + pid + r"\b", n.text or "") for n in texts[name] if xmin <= float(n.get("x", "0")) <= xmax), "card full-ID identity missing: " + name)
        need("On: Wouters · Energy 27 · Ready" in [n.text for n in texts["10-match-decisions"]], "incoming condition differs from pinned card")
        row = next(n for n in texts["03-team-workspace"] if n.get("data-roster-slot") == "16")
        need(any(n.get("x") == "595" and n.get("y") == row.get("y") and n.text == "27" for n in texts["03-team-workspace"]), "bench condition differs from shared card snapshot")
        pool = trees["04-pool-compare"]
        pool_text = ["".join(n.itertext()) for n in texts["04-pool-compare"]]
        need("Rows 1–7 of 80 · Wheel / Page Down" in pool_text, "pool lacks visible subset count/scroll route")
        track = [n for n in pool.iter() if n.get("data-scroll-track") == "pool"]
        thumb = [n for n in pool.iter() if n.get("data-scroll-thumb") == "pool"]
        need(len(track) == len(thumb) == 1 and float(track[0].get("height")) > float(thumb[0].get("height")) > 0, "pool lacks actual contained scrollbar")
        bio = [n.text for n in texts["04-pool-compare"] if n.get("y") == "352"]
        need(len(bio) == 2 and bio[0] != bio[1], "comparison copies outgoing biography into incoming card")
        chars = [[n.text for n in texts["04-pool-compare"] if n.get("x") == x and any((n.text or "").startswith(c + " ") for c in CHARACTERISTICS)] for x in ("557", "926")]
        need(len(chars[0]) == len(chars[1]) == 5 and all(a != b for a, b in zip(*chars)), "comparison cards copy all characteristics")
        tab = [n for n in trees["05-competition"].iter() if n.get("data-tab") == "Groups"]
        need(len(tab) == 1 and tab[0].get("data-state") == "selected" and tab[0].get("fill") == "#006C5B", "competition has no visible selected Groups tab")
        need(any(n.text == "Groups" and n.get("fill") == "#FFFFFF" and n.get("x") == "345" for n in texts["05-competition"]), "selected Groups label not visibly contrasted")
        return "all10 tier/spacing sweep;four complete cards consistent;pool seven-of80 scroll;selectedGroups;ranks explicit"

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
        for name in ("evidence/runtime-06/report.json", "evidence/browser-03/report.json"):
            need(sha((self.path / name).read_bytes()) == PINNED_EVIDENCE[name], "observation report differs from the pinned reviewed report: " + name)
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
        self.quick_continuation_contracts()
        self.reuse_contracts()
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
            for phrase in ("Player problem:", "Dependencies:", "Original reference:", "Intended behavior:", "Owned surfaces / exclusions:", "## Acceptance criteria", "## Validation",
                           "Owner-approved queue amendment", "no automatic dispatch", "Bounded scope, acceptance preflight"):
                need(phrase in body, "child contract missing " + phrase + ": " + x["key"])
            need(len(re.findall(r"^\d\. \[designed\]", body, re.M)) >= 5, "child acceptance criteria missing")
            need("https://github.com/diegoami/goal2/blob/" + MANUAL + "/docs/original-game/" in body, "child original references not absolute/pinned")
        need(len(all_new_areas) == len(set(all_new_areas)), "duplicate new scope ownership")
        by = {x["key"]: x for x in items}
        for key, deps in {"B01": ["#242", "#243"], "B02": ["G05", "#265"], "B03": ["#248", "#249"], "B05": ["G01-G05", "#264", "#265"]}.items():
            for dep in deps:
                need(dep in by[key]["dependencies"], "dependency absent: " + key + " " + dep)
        for key, dep in (("B02", "#265"), ("B05", "#265"), ("B05", "#264")):
            need(dep in self.read(by[key]["contract"]), "contract/manifest dependency mismatch: " + key)
        self.mirror_contracts(by)
        index = (self.root / "docs/tasks/README.md").read_text()
        need("#251 projection" not in index, "task index extends retained-summary contract")
        for n in ISSUES.values():
            need(f"/issues/{n}" in index and f"/issues/{n}" in self.read("backlog.md"), "filed scope absent from proposed order")
        return "7 filed scoped issues mirrored from live amended bodies;9 existing owners preserved;dependencies, lanes and task index linked;no duplicate area ownership;unowned scopes tied to owner decisions"

    def mirror_contracts(self, by):
        """[designed: #253 reconciliation] Local child contracts equal the recorded live amended bodies; lane/priority agree."""
        receipt = self.data("evidence/reconcile-05/live-issue-bodies.json")
        mirrored = {r["key"]: r for r in receipt["mirrored"]}
        need(set(mirrored) == set(ISSUES), "live-body receipt omits a child scope")
        for key, record in mirrored.items():
            need(record["issue"] == ISSUES[key] and record["local_file"] == "docs/redesign-253/backlog/" + key + ".md", "receipt names the wrong issue/file: " + key)
            text = self.read("backlog/" + key + ".md")
            head, _, body = text.partition("\n\n")
            need(head.startswith("# " + key + ": ") and body.endswith("\n"), "child contract heading/format differs: " + key)
            need(sha(body[:-1].encode()) == record["live_body_sha256"], "local contract differs from the recorded live amended body: " + key)
            need(record["live_body_sha256"] == LIVE_BODY_SHA256[key], "contract and receipt differ from the pinned live amended body: " + key)
            live_dependencies = re.search(r"- \*\*Dependencies:\*\* (.*)", body).group(1).replace("[designed: approved queue, 2026-10-20] ", "")
            need(by[key]["dependencies"] == live_dependencies, "backlog.json dependencies differ from the pinned live body: " + key)
            need(body.startswith("## Owner-approved queue amendment") and "**Queue:**" in body, "child contract lacks the owner-approved queue amendment: " + key)
            need("O01 direction approval" not in body and "Explicit owner selection/approval of the #253 redesign direction is required" not in body,
                 "child contract keeps the superseded direction gate: " + key)
            x = by[key]
            need(x["lane"] == CHILD_LANE[key] and x["priority"].startswith(CHILD_PRIORITY[key] + " "), "child lane/priority differs from the approved queue: " + key)
            need("**Priority:** " + CHILD_PRIORITY[key] in body, "contract priority differs from the approved queue: " + key)
        shown = {}
        for key, cells in keyed_rows(self.read("backlog.md"), "ID / issue", r"\[(B\d\d)\]\([^)]*\) · \[#\d+\]\([^)]*\)", "backlog.md").items():
            need(re.fullmatch(r"\d", cells[1]) and re.match(r"P\d\b", cells[3]), "backlog.md child row lacks a lane or priority: " + key)
            shown[key] = (int(cells[1]), cells[3][:2])
        for key in ISSUES:
            need(shown.get(key) == (CHILD_LANE[key], CHILD_PRIORITY[key]), "backlog.md child lane/priority differs from the approved queue: " + key)
        for key in ("B01", "B03", "B04"):
            need("retract" in self.read("backlog/" + key + ".md"), "visual acceptance omits retractable bars: " + key)
        match = self.read("backlog/B04.md")
        need("Maximize pitch area" in match and "latest two lines" in match, "match contract omits maximum pitch / two-line commentary")
        referenced = {r["issue"]: r for r in receipt["referenced"]}
        need(270 in referenced and referenced[270]["mirrored"] is False, "#270 must be referenced, not mirrored or pre-split here")

    def decision_rows(self):
        rows = keyed_rows(self.read("decisions.md"), "ID", r"(O\d\d(?: / G\d\d)?)", "decisions.md", headers=("ID", "Decision / gap"))
        return {key: " | ".join(cells) for key, cells in rows.items()}

    @staticmethod
    def canonical_table(name, doc, header):
        """[designed: #253 rework R4] The one table headed `header`, parsed whole: each row is two issue numbers and a source. (pairs, its line indices)."""
        blocks = [b for b in table_blocks(doc.splitlines()) if table_cells(b[1][0], name) == header]
        need(len(blocks) == 1, f"{name} lacks exactly one '{' | '.join(header)}' table")
        _, rows = parse_block(blocks[0], name)
        pairs = []
        for _, line, cells in rows:
            m = re.fullmatch(r"#(\d+)", cells[0]), re.fullmatch(r"#(\d+)", cells[1])
            need(all(m) and cells[2], f"unparsed row in the '{header[0]}' table of {name}: {line.strip()[:70]}")
            pairs.append((int(m[0].group(1)), int(m[1].group(1)), cells[2]))
        start, block_lines = blocks[0]
        return pairs, set(range(start, start + len(block_lines)))

    def queue_dependencies(self, name, doc):
        """[designed: #253 rework R3/R4] Mechanical checks, not a reading of prose: (1) both canonical tables, parsed whole, equal the oracle
        pairs; (2) lane rows state no order word or arrow; (3) no reverse arrow in the file; (4) every line outside the canonical tables, table
        cells included, is scanned for a clause naming two issues around an order word or arrow that contradicts a pair; (5) no other table
        row has two bare issue numbers as its first two cells."""
        need("←" not in doc and "<-" not in doc, f"reverse arrow between queue issues in {name}")
        lines = doc.splitlines()
        dependencies, dependency_lines = self.canonical_table(name, doc, DEPENDENCY_HEADER)
        non_prerequisites, non_prerequisite_lines = self.canonical_table(name, doc, NOT_PREREQUISITE_HEADER)
        need(sorted(dependencies) == sorted(DEPENDENCIES), f"dependency table in {name} differs from the approved dependencies")
        need(sorted(non_prerequisites) == sorted(NOT_PREREQUISITE), f"non-prerequisite table in {name} differs from the approved pairs")
        canonical = dependency_lines | non_prerequisite_lines
        lane_lines = set()
        for block in table_blocks(lines):
            if block[0] in (min(dependency_lines), min(non_prerequisite_lines)):
                continue
            for index, line in enumerate(block[1], block[0]):
                cells = table_cells(line, name)
                need(not (len(cells) >= 2 and re.fullmatch(r"#\d+", cells[0]) and re.fullmatch(r"#\d+", cells[1])),
                     f"table row outside the canonical tables relates two issues in {name}: {line.strip()[:70]}")
                if re.match(r"\d[a-e]?(?:\s|$)", cells[0]) and len(cells) >= 3:
                    lane_lines.add(index)
        need(len(lane_lines) >= 5, f"queue lane rows missing in {name}")
        words = re.compile(r"(?i)\b(before|after|precede\w*|follow\w*|then|prerequisite\w*|predecessor\w*|successor\w*|depend\w*)\b|→|->")
        for index in sorted(lane_lines):
            hit = words.search(re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", lines[index]))
            need(not hit, f"queue lane text in {name} states an order outside the canonical dependency table: {hit.group(0) if hit else ''}")
        edges = {(a, b) for a, b, _ in DEPENDENCIES}
        rest = "\n".join(x for i, x in enumerate(lines) if i not in canonical and i not in lane_lines)
        rest = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", rest)
        for clause in re.split(r"[.;\n]", rest):
            tokens = list(re.finditer(r"#(\d+)\b|\b(before|precede\w*|then|after|follow\w*|succeed\w*)\b|→|->", clause, re.I))
            for i, tok in enumerate(tokens):
                if tok.group(1):
                    continue
                left = next((x for x in reversed(tokens[:i]) if x.group(1)), None)
                right = next((x for x in tokens[i + 1:] if x.group(1)), None)
                if left and right and left.group(1) != right.group(1):
                    a, b = int(left.group(1)), int(right.group(1))
                    backward = tok.group(2) is not None and re.match(r"(?i)after|follow|succeed", tok.group(2))
                    claim = (b, a) if backward else (a, b)
                    need((claim[1], claim[0]) not in edges, f"order statement contradicts the approved dependencies in {name}: #{a} {tok.group(0)} #{b}")

    def vision(self):
        """[designed: #253 reconciliation] The accepted #266 direction, its screens, the queue and the open choices. Relations
        (screen mappings, queue order) are compared with oracles held in this file, never with the registry they sit in."""
        self.gate()
        reg = self.data("package.json")
        need("recommended_direction" not in reg, "registry still carries the superseded recommendation")
        d = reg["accepted_direction"]
        need(d["merge_commit"] == VISION and d["issue"].endswith("/issues/266") and d["pull_request"].endswith("/pull/267")
             and d["owner_acceptance"].endswith("issues/266#issuecomment-6287825622") and d["docs"] == "docs/vision-266/", "accepted direction record differs")
        for phrase in ("black", "large characters", "attribute bars", "maximum-size match pitch", "hidden by default", "retractable"):
            need(phrase in d["summary"], "accepted direction summary omits: " + phrase)
        # accepted screens: byte-identical to the pinned merge commit; the plan never edits them
        need(reg["vision_screens"] == VISION_SCREENS, "accepted screen inventory differs from the nineteen of #266")
        story = (self.root / "docs/vision-266/storyboard.md").read_text()
        need(re.findall(r"^## (\d\d) ", story, re.M) == [s[:2] for s in VISION_SCREENS], "storyboard no longer lists the nineteen accepted screens")
        for name in VISION_SCREENS:
            for ext in (".png", ".svg"):
                rel = "docs/vision-266/screens/" + name + ext
                data = (self.root / rel).read_bytes()
                if ext == ".png":
                    png_size(data)
                need(sha(data) == sha(self.git("show", VISION + ":" + rel)), "accepted screen differs from the pinned merge commit: " + rel)
        # surfaces
        need(set(reg["surface_screens"]) == set(SURFACE_COVERAGE) == set(reg["surfaces"]), "surface-to-screen registry incomplete")
        counts = Counter()
        for r in self.rows("parity/destinations.tsv"):
            for s in set(re.findall(r"S\d+", r["destination"])):
                counts[s] += 1
        need(set(counts) <= set(SURFACE_COVERAGE), "parity destination names a surface the registry does not map")
        for s, record in reg["surface_screens"].items():
            need(record["coverage"] == SURFACE_COVERAGE[s], "surface coverage differs from the accepted-screen oracle: " + s)
            need(set(record["screens"]) <= set(VISION_SCREENS) and set(record.get("route_screens", [])) <= set(VISION_SCREENS), "surface cites an unknown accepted screen: " + s)
            if record["coverage"] == "drawn":
                need(record["screens"], "drawn surface without accepted screen: " + s)
            else:
                need(record["gap"] and re.search(r"#\d+|G0\d", record["owner"]) and (record["coverage"] != "undrawn" or not record["screens"]),
                     "undrawn/partial surface lacks a bounded owner or states a drawn screen: " + s)
                need(all(tok in record["owner"] for tok in SURFACE_OWNER_ORACLE[s]), "undrawn/partial surface names the wrong bounded owner: " + s)
            need(sorted(x[:2] for x in record["screens"]) == SURFACE_SCREEN_ORACLE[s], "surface screen identity differs from the independent oracle: " + s)
            need(sorted(x[:2] for x in record.get("route_screens", [])) == SURFACE_ROUTE_ORACLE.get(s, []), "surface route-screen identity differs from the independent oracle: " + s)
        text = self.read("vision-reconciliation.md")
        section = text.split("## Surface-to-screen mapping", 1)[1].split("## Parity destinations by original context", 1)[0]
        doc_rows = keyed_rows(section, "Surface", r"(S\d\d)(?: .*)?", "vision-reconciliation.md")
        need(set(doc_rows) == set(SURFACE_COVERAGE), "reconciliation surface table incomplete")
        for s, (_, coverage, cell, owner_cell, allocations) in doc_rows.items():
            need(coverage in ("drawn", "partial", "undrawn") and re.fullmatch(r"\d+", allocations), "reconciliation surface row lacks a coverage word or an allocation count: " + s)
            record = reg["surface_screens"][s]
            need(all(tok in owner_cell for tok in SURFACE_OWNER_ORACLE.get(s, set())), "reconciliation table names the wrong bounded owner: " + s)
            shown = set(re.findall(r"\b(\d\d)\b", cell))
            expected = {x[:2] for x in record["screens"]} | ({x[:2] for x in record.get("route_screens", [])} if record["coverage"] == "undrawn" else set())
            need(coverage == record["coverage"] and shown == expected, "reconciliation table disagrees with registry: " + s)
            need(int(allocations) == counts.get(s, 0), "reconciliation allocation count differs from the destination matrix: " + s)
        # parity destinations by original context
        context_section = text.split("## Parity destinations by original context", 1)[1].split("## Journey-to-screen mapping", 1)[0] if "## Parity destinations by original context" in text else ""
        expected_rows = context_screen_rows(reg, self.rows("parity/destinations.tsv"))
        need(set(expected_rows) == set(GROUPS), "parity context mapping incomplete")
        shown_rows = ["| " + " | ".join(c) + " |" for c in keyed_rows(context_section, "Context", r"([A-Z]{2})", "vision-reconciliation.md").values()]
        need(sorted(shown_rows) == sorted(expected_rows.values()), "reconciliation parity-context table disagrees with the destination matrix and surface registry")
        # journeys
        need(set(reg["journey_screens"]) == {f"J{i:02}" for i in range(1, 10)}, "journey-to-screen registry incomplete")
        journey_section = text.split("## Journey-to-screen mapping", 1)[1].split("## Superseded candidate layouts", 1)[0]
        journeys = {k: set(re.findall(r"\b(\d\d)\b", c[1])) for k, c in keyed_rows(journey_section, "Journey", r"(J\d\d)(?: .*)?", "vision-reconciliation.md").items()}
        for j, screens in reg["journey_screens"].items():
            need(screens and set(screens) <= set(VISION_SCREENS), "journey cites no/unknown accepted screen: " + j)
            need(sorted(x[:2] for x in screens) == JOURNEY_SCREEN_ORACLE[j], "journey screen identity differs from the independent oracle: " + j)
            need(journeys.get(j) == {x[:2] for x in screens}, "reconciliation journey table disagrees with registry: " + j)
        # candidate layouts are superseded, each with an accepted successor
        need(set(reg["superseded_layouts"]) == set(LAYOUTS), "superseded layout mapping incomplete")
        layout_section = text.split("## Superseded candidate layouts", 1)[1].split("## Approved queue", 1)[0]
        shown_layouts = {k: set(re.findall(r"\b(\d\d)\b", c[1])) for k, c in keyed_rows(layout_section, "Candidate sheet", r"(\d\d)(?: .*)?", "vision-reconciliation.md").items()}
        for name, successors in reg["superseded_layouts"].items():
            need(successors and {x[:2] for x in successors} == LAYOUT_SUCCESSOR[name], "superseded layout lacks its accepted successor: " + name)
            need(shown_layouts.get(name[:2]) == LAYOUT_SUCCESSOR[name], "reconciliation layout table disagrees with registry: " + name)
        lay = self.read("layouts.md")
        need("Superseded as screen recommendations" in lay and "historical evidence, not a recommendation" in lay, "layouts.md does not declare the candidate sheets superseded")
        need("not a recommendation" in (self.path / "layouts/SUPERSEDED.md").read_text(), "layouts directory lacks its superseded marker")
        # queue: ordered lanes, follow_on, directed dependency pairs in the registry and in each document's canonical tables
        qreg = reg["queue"]
        need([q["lane"] for q in qreg["lanes"]] == sorted(QUEUE_LANES), "queue lanes are not listed in lane order")
        lanes = {q["lane"]: q for q in qreg["lanes"]}
        for lane, expected in QUEUE_LANES.items():
            need(lanes[lane]["issues"] == expected, f"queue lane order differs from the approved order: lane {lane}")
            need(set(lanes[lane]) <= {"lane", "name", "issues", "separate", "follow_on", "note"}, f"queue lane carries an unreviewed relation field: lane {lane}")
            need(lanes[lane].get("follow_on", []) == FOLLOW_ON.get(lane, []), f"queue follow-on differs from the approved queue: lane {lane}")
        need(lanes[1].get("separate") == [208, 268] and not any("separate" in lanes[n] for n in (2, 3, 4, 5)), "queue ordering constraints differ")
        need([(x["before"], x["after"], x["source"]) for x in qreg["dependencies"]] == DEPENDENCIES, "queue dependencies in the registry differ from the approved pairs")
        need([(x["not_prerequisite"], x["of"], x["source"]) for x in qreg["not_prerequisite"]] == NOT_PREREQUISITE, "queue non-prerequisites in the registry differ from the approved pairs")
        need(all(any(a == n for _, a, _ in DEPENDENCIES) for ns in FOLLOW_ON.values() for n in ns), "a follow-on issue has no approved predecessor pair")
        index = (self.root / "docs/tasks/README.md").read_text()
        plan = self.read("backlog.md")
        for name, doc in (("docs/tasks/README.md", index), ("backlog.md", plan), ("vision-reconciliation.md", text)):
            self.queue_dependencies(name, doc)
        for n in sorted(QUEUE_EXTRA | {n for lane in QUEUE_LANES.values() for n in lane}):
            for name, doc in (("task index", index), ("backlog", plan), ("reconciliation", text)):
                need(f"/issues/{n}" in doc, f"queue issue absent from {name}: #{n}")
        need("referenced, not implemented or pre-split here" in plan and "referenced, not implemented or pre-split here" in text, "#270 is not recorded as referenced only")
        # open owner choices and unowned obligations
        rows = self.decision_rows()
        need("Closed" in rows.get("O01", "") and "resolved" in rows.get("O01", ""), "O01 must be closed: the direction is not asked again")
        for key in OPEN_CHOICES:
            need("[designed: open]" in rows.get(key, ""), "genuinely open owner choice missing or mislabeled: " + key)
        for key, contract in OBLIGATIONS.items():
            row = rows.get(key, "")
            need(row, "scope obligation missing: " + key)
            need("nowned" in row and contract + " before a full-parity claim" in row, "scope obligation lacks an explicit unowned statement: " + key)
            token = key.split(" / ")[-1]
            gap_section = text.split("## Scope gaps and their owners", 1)[1].split("## Open owner choices", 1)[0]
            gap_rows = keyed_rows(gap_section, "Obligation", r"(O\d\d|G\d\d)(?: .*)?", "vision-reconciliation.md")
            gap_row = " | ".join(gap_rows.get(token, []))
            need("unowned" in gap_row.lower() and "bounded" in gap_row.lower(), "reconciliation lacks the unowned scope-gap row: " + token)
        tech = self.read("technology.md")
        need("did not select a toolkit" in tech, "technology document must not claim a toolkit was selected")
        for phrase in ("retractable", "maximum-size pitch", "latest two commentary lines"):
            need(phrase in tech, "technology proof omits an accepted visual requirement: " + phrase)
        self.allocation_contracts()
        return "accepted #266 pinned and byte-identical (19 screens);15 surfaces/9 journeys/10 superseded layouts mapped;undrawn surfaces owned;queue lanes 1-5 incl. #270 referenced;O01 closed,O02-O07 open;G01-G05/O13/O14 explicitly unowned;inventory hash unchanged"

    def technology(self):
        self.gate()
        t = self.read("technology.md")
        for phrase in ("Python backend", "PySide6 Widgets", "Qt Quick", "Tauri2", "Electron", "Godot", "Windows", "Linux", "atomic", "ACK", "save", "migration", "not schedules", "No experimental prototype"):
            need(phrase.lower() in t.lower(), "technology constraint/alternative absent: " + phrase)
        for host in ("doc.qt.io", "v2.tauri.app", "electronjs.org", "docs.godotengine.org"):
            need("https://" + host in t or "https://www." + host in t, "missing primary technology source: " + host)
        need("2026-10-19" in t and "No numeric" in t, "capabilities/estimates not bounded")
        return "desktop/Python constraints;5 frontend approaches;primary sources;relative cost/migration/owner decisions"

    def merge_base(self):
        """[designed: #253 reconciliation] Changed files are measured from where this branch left main, not from the audited product pin."""
        if self.base:
            return self.base
        for ref in ("origin/main", "main"):
            try:
                return self.git("merge-base", "HEAD", ref).decode().strip()
            except subprocess.CalledProcessError:
                continue
        raise ValueError("no origin/main or main to measure the change from: fetch it or pass --base <rev>")

    def scope(self):
        need((self.path / "package.json").exists(), "proposal package absent")
        base = self.merge_base()
        changed = set(self.git("diff", "--name-only", base).decode().splitlines())
        changed.update(self.git("ls-files", "--others", "--exclude-standard").decode().splitlines())
        allowed = lambda x: x.startswith("docs/redesign-253/") or x in {"docs/tasks/README.md", "docs/model-trials.md", "harness.lock"}
        need(all(allowed(x) for x in changed), "out-of-scope changed file: " + str(sorted(x for x in changed if not allowed(x))))
        for path in self.path.rglob("*"):
            if not path.is_file():
                continue
            need(not path.is_symlink(), "package symlink")
            need(path.suffix.lower() not in (".sav", ".dat", ".gl", ".sum", ".hil", ".exe", ".wasm"), "original/runtime payload entered package")
            if path.suffix == ".json":
                json.loads(path.read_text())
            if path.suffix in (".md", ".py", ".mjs", ".json", ".tsv", ".svg"):
                need(len(path.read_text()) < 110000, "oversized planning file: " + path.name)
        return f"{len(changed)} changed files against {base[:8]} limited to the plan package, its task index, the focused process lesson and its harness.lock hash (accepted vision, product and engine untouched);JSON valid;no app/engine/dependency/original payload changes"


def context_screen_rows(reg, destinations):
    """[designed: #253 reconciliation] Per original context: the surfaces its allocations name and the accepted screens that draw them."""
    by_context = {}
    for r in destinations:
        by_context.setdefault(r["context"], set()).update(re.findall(r"S\d+", r["destination"]))
    rows = {}
    for context, surfaces in by_context.items():
        records = {s: reg["surface_screens"][s] for s in surfaces}
        screens = sorted({x[:2] for r in records.values() for x in r["screens"]})
        partial = sorted(s for s, r in records.items() if r["coverage"] == "partial")
        undrawn = sorted(s for s, r in records.items() if r["coverage"] == "undrawn")
        gaps = "; ".join(x for x in (("partial " + ", ".join(partial)) if partial else "", ("undrawn " + ", ".join(undrawn)) if undrawn else "") if x) or "none"
        rows[context] = "| " + context + " | " + ", ".join(sorted(surfaces)) + " | " + ", ".join(screens) + " | " + gaps + " |"
    return rows


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


_PKG = None


def negative_controls(package):
    """[designed: #253] Realistic omissions, not token injection; exact bytes restore."""
    global _PKG
    _PKG = package
    initial = run(package, CHECKS)
    need(all(x["pass"] for x in initial), "positive package must pass before controls: " + str(initial))
    src = "parity/source-fields.tsv"
    dst = "parity/destinations.tsv"
    def drop(text, prefix):
        return "".join(x for x in text.splitlines(keepends=True) if not x.startswith(prefix + "\t"))
    cases = [
        ("missing-skill-allocation", "parity", {dst: lambda t: drop(t, "SK12")}),
        ("missing-skill-from-both-inventories", "parity", {src: lambda t: drop(t, "SK12"), dst: lambda t: drop(t, "SK12")}),
        ("blank-destination", "parity", {dst: lambda t: set_cell(t, "SK12", "destination", "")}),
        ("missing-original-screen", "parity", {"evidence/screens-inspected.tsv": lambda t: drop(t, "captain-select.png")}),
        ("remove-operative-gate", "proposal", {"decisions.md": lambda t: re.sub(r"^## Approval gate\n.*?(?=^## |\Z)", "", t, flags=re.M | re.S)}),
        ("realistic-duplicate-campaign-owner", "backlog", {"backlog.json": duplicate_campaign}),
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
        ("country-screenshot-team-default-trace-omitted", "parity", {"evidence/screens-inspected.tsv": missing_country_tt}),
        ("quick-continuation-assigned-to-existing-scopes", "backlog", {dst: lambda t: set_cell(t, "LI08", "owner", "#198/#243/B04/#250")}),
        ("quick-continuation-omitted-from-gap", "backlog", {"capability-gaps.json": omit_quick_gap}),
        ("quick-continuation-register-assigned-to250", "backlog", {"capabilities.tsv": lambda t: set_cell(t, "Quick continuation during watched play", "owner", "#250", "capability")}),
        ("quick-continuation-drawn-enabled", "journeys", {"layouts/07-live-match.svg": enable_quick}),
        ("quick-continuation-flow-claimed-available", "journeys", {"journeys.md": lambda t: t.replace("Quick continuation is unavailable", "Quick continuation is available")}),
        ("supported-country-identity-marked-unowned", "parity", {dst: lambda t: set_cell(t, "CO01", "owner", "UNOWNED:G05")}),
        ("supported-friendly-route-marked-unowned", "backlog", {dst: lambda t: set_cell(t, "MP01-S", "owner", "UNOWNED:G01")}),
        ("captain-residual-allocation-dropped", "parity", {dst: lambda t: drop(t, "MP07-G")}),
        ("coordinated-mixed-source-and-parts-dropped", "parity", {src: lambda t: drop(t, "MP07"), dst: lambda t: drop(drop(t, "MP07-S"), "MP07-G")}),
        ("original-manager-rating-source-meaning-erased", "parity", {src: lambda t: set_cell(t, "HU01", "information", "Active managed country and manager name")}),
        ("split-rendered-information-erased", "parity", {"parity/match.md": lambda t: t.replace("; [designed allocation] " + SPLIT_FIELDS["MP01"]["S"][0], "", 1)}),
        ("hero-mislabeled-as-first-slice", "proposal", {"layouts/02-country-desk.svg": lambda t: t.replace("FULL-PARITY TARGET", "FIRST SLICE")}),
        ("hero-ranks-ambiguous", "proposal", {"layouts/02-country-desk.svg": lambda t: t.replace("Holland · world 14 · Europe 3", "World rank 14 / 8 · Europe rank 3 / 9")}),
        ("same-id-wouters-card-corrupted", "proposal", {"layouts/10-match-decisions.svg": wrong_wouters_card}),
        ("pool-scrollbar-omitted", "proposal", {"layouts/04-pool-compare.svg": lambda t: remove_svg_element(t, "data-scroll-track", "pool")}),
        ("pool-visible-count-omitted", "proposal", {"layouts/04-pool-compare.svg": lambda t: t.replace("Rows 1–7 of 80 · Wheel / Page Down", "Wheel / Page Down")}),
        ("comparison-biography-copied", "proposal", {"layouts/04-pool-compare.svg": lambda t: t.replace("24 yrs · caps 1 · goals 0 · 6′0″ · right foot", "29 yrs · caps 3 · goals 0 · 5′11″ · left foot")}),
        ("selected-competition-tab-omitted", "proposal", {"layouts/05-competition.svg": unselect_groups}),
        ("original-live-speed-departure-omitted", "proposal", {"decisions.md": lambda t: "\n".join(line for line in t.split("\n") if "↔-speed" not in line)}),
        ("team-bits-reassigned-to-player-card-display", "parity", {dst: lambda t: set_cell(t, "TT01", "reuse", "T84 read-only display; #248 owns personal edits only.")}),
        # [designed: #253 reconciliation] controls for the accepted-vision mapping, queue and open-choice records
        ("obsolete-recommendation-restored", "proposal", {"README.md": lambda t: t.replace("The direction is chosen.**", "The direction is chosen.** Recommend A: Country desk.")}),
        ("obsolete-recommendation-in-registry", "proposal", {"package.json": lambda t: edit_json(t, lambda d: d.update(recommended_direction="A"))}),
        ("visual-style-question-reasked", "proposal", {"decisions.md": lambda t: t.replace("\n\n## Unowned capability decisions", "\n| O15 | [designed: open] | Select the paper or the original look. | | |\n\n## Unowned capability decisions")}),
        ("direction-question-reasked", "vision", {"decisions.md": lambda t: t.replace("| O01 | [designed: resolved] **Closed** |", "| O01 | [designed: open] |")}),
        ("accepted-screen-dropped-from-registry", "vision", {"package.json": lambda t: edit_json(t, lambda d: d["vision_screens"].remove("19-campaign"))}),
        ("drawn-surface-without-screen", "vision", {"package.json": lambda t: edit_json(t, lambda d: d["surface_screens"]["S04"].update(screens=[]))}),
        ("undrawn-surface-claimed-drawn", "vision", {"package.json": lambda t: edit_json(t, lambda d: d["surface_screens"]["S06"].update(coverage="drawn", screens=["02-country-desk"]))}),
        ("undrawn-surface-owner-dropped", "vision", {"package.json": lambda t: edit_json(t, lambda d: d["surface_screens"]["S15"].update(owner=""))}),
        ("reconciliation-screen-claim-diverges", "vision", {"vision-reconciliation.md": lambda t: t.replace("| S05 Pool comparison | drawn | 04 |", "| S05 Pool comparison | drawn | 03 |")}),
        ("reconciliation-allocation-count-wrong", "vision", {"vision-reconciliation.md": lambda t: t.replace("| S08 Preparation | drawn | 05 | — | 106 |", "| S08 Preparation | drawn | 05 | — | 105 |")}),
        ("superseded-layout-without-successor", "vision", {"package.json": lambda t: edit_json(t, lambda d: d["superseded_layouts"].update({"05-competition": []}))}),
        ("candidate-layouts-recommended-again", "vision", {"layouts.md": lambda t: t.replace("Superseded as screen recommendations.", "Recommended screens.")}),
        ("accepted-screen-bytes-edited", "vision", {"../vision-266/screens/06-watched.svg": lambda t: t + "\n"}),
        ("queue-lane-issue-dropped", "vision", {"package.json": lambda t: edit_json(t, lambda d: d["queue"]["lanes"][0]["issues"].remove(270))}),
        ("task-index-drops-career-stream", "vision", {"../../docs/tasks/README.md": lambda t: t.replace("/issues/119)", "/issues/9119)")}),
        ("backlog-drops-cloud-issue", "vision", {"backlog.md": lambda t: t.replace("/issues/270)", "/issues/27)")}),
        ("gap-unowned-statement-removed", "vision", {"decisions.md": lambda t: t.replace("**Unowned: needs a bounded contract before a full-parity claim.**", "", 1)}),
        ("evidence-encoding-obligation-dropped", "vision", {"decisions.md": lambda t: "".join(x for x in t.splitlines(keepends=True) if not x.startswith("| O13 |"))}),
        ("parity-context-screens-overclaimed", "vision", {"vision-reconciliation.md": lambda t: t.replace("| ST | S01, S02 | 01 | partial S02 |", "| ST | S01, S02 | 01, 02 | none |")}),
        ("technology-claims-toolkit-selected", "vision", {"technology.md": lambda t: t.replace("did not select a toolkit or window arrangement", "selected a toolkit")}),
        ("technology-proof-omits-two-line-commentary", "vision", {"technology.md": lambda t: t.replace("only the latest two commentary lines by default", "commentary by default")}),
        ("child-contract-diverges-from-live-body", "backlog", {"backlog/B03.md": lambda t: t.replace("Split shared shell and Team/pool composition before dispatch.", "Compose everything at once.")}),
        ("child-priority-drifts-from-queue", "backlog", {"backlog.json": lambda t: edit_json(t, lambda d: next(x for x in d if x["key"] == "B06").update(priority="P1 · full-parity support prerequisite"))}),
        ("cloud-issue-mirrored-instead-of-referenced", "backlog", {"evidence/reconcile-05/live-issue-bodies.json": lambda t: edit_json(t, lambda d: d["referenced"][0].update(mirrored=True))}),
        # [designed: #253 rework R1/R2 and sweep] coordinated registry+prose edits, ordered dependencies and receipt pins
        ("pool-surface-coordinated-to-start-resume", "vision", {"package.json": lambda t: edit_json(t, lambda d: d["surface_screens"]["S05"].update(screens=["01-start-resume"])),
          "vision-reconciliation.md": lambda t: regen_context_rows(t.replace("| S05 Pool comparison | drawn | 04 |", "| S05 Pool comparison | drawn | 01 |"))}),
        ("conditional-journey-coordinated-to-start-resume", "vision", {"package.json": lambda t: edit_json(t, lambda d: d["journey_screens"].update(J07=["01-start-resume"])),
          "vision-reconciliation.md": lambda t: t.replace("| J07 Half-time, extra time, shoot-out | 07, 13 |", "| J07 Half-time, extra time, shoot-out | 01 |")}),
        ("journey-edges-replaced-with-unused", "journeys", {"package.json": lambda t: edit_json(t, lambda d: d["journeys"]["J07"].update(edges=["unused"]))}),
        ("journey-surfaces-replaced", "journeys", {"package.json": lambda t: edit_json(t, lambda d: d["journeys"]["J07"].update(surfaces=["S10", "S11", "S01"]))}),
        ("surface-owner-coordinated-wrong", "vision", {"package.json": lambda t: edit_json(t, lambda d: d["surface_screens"]["S06"].update(owner=d["surface_screens"]["S06"]["owner"].replace("#261", "#198"))),
          "vision-reconciliation.md": lambda t: t.replace("#261 composes the route and adds the screen to its contract; complete profile", "#198 composes the route and adds the screen to its contract; complete profile")}),
        ("child-lane-prose-drift", "backlog", {"backlog.md": lambda t: t.replace("[#260](https://github.com/diegoami/goal2/issues/260) | 3 |", "[#260](https://github.com/diegoami/goal2/issues/260) | 2 |")}),
        # [designed: #253 rework R3] directed dependency pairs: the reviewer's four attacks and the class around them
        ("foundation-arrows-reversed", "vision", {"backlog.md": lambda t: t.replace(
            "[#198](https://github.com/diegoami/goal2/issues/198) (PR #240; #254/#255 resolved), [#242](https://github.com/diegoami/goal2/issues/242) and [#243](https://github.com/diegoami/goal2/issues/243)",
            "[#198](https://github.com/diegoami/goal2/issues/198) (PR #240; #254/#255 resolved) ← [#242](https://github.com/diegoami/goal2/issues/242) ← [#243](https://github.com/diegoami/goal2/issues/243)")}),
        ("history-dependency-inverted-prose", "vision", {"backlog.md": lambda t: t.replace("retained-history browsing. |", "retained-history browsing must precede the base match journey. |")}),
        ("history-inverted-and-followon-removed-coordinated", "vision", {"package.json": lambda t: edit_json(t, lambda d: d["queue"]["lanes"][2].pop("follow_on")),
          "backlog.md": lambda t: drop_row(t.replace("retained-history browsing. |", "retained-history browsing must precede the base match journey. |"), 262, 251, "lane 3")}),
        ("followon-removed-in-registry-only", "vision", {"package.json": lambda t: edit_json(t, lambda d: d["queue"]["lanes"][2].pop("follow_on"))}),
        ("followon-removed-in-prose-only", "vision", {"backlog.md": lambda t: drop_row(t, 262, 251, "lane 3")}),
        ("lane-objects-swapped-in-registry-array", "vision", {"package.json": lambda t: edit_json(t, lambda d: d["queue"]["lanes"].insert(1, d["queue"]["lanes"].pop(2)))}),
        ("canonical-row-reversed-in-backlog", "vision", {"backlog.md": lambda t: swap_row(t, 110, 112, "lane 4")}),
        ("canonical-row-reversed-in-reconciliation", "vision", {"vision-reconciliation.md": lambda t: swap_row(t, 260, 261, "lane 3")}),
        ("canonical-row-reversed-in-task-index", "vision", {"../../docs/tasks/README.md": lambda t: swap_row(t, 198, 243, "lane 2")}),
        ("canonical-row-missing-in-reconciliation", "vision", {"vision-reconciliation.md": lambda t: drop_row(t, 198, 242, "lane 2")}),
        ("retirement-constraint-row-dropped", "vision", {"../../docs/tasks/README.md": lambda t: drop_row(t, 155, 117, "lane 4")}),
        ("non-prerequisite-row-dropped", "vision", {"../../docs/tasks/README.md": lambda t: t.replace("| #259 | #198 | lane 2 |\n", "", 1)}),
        ("career-order-reversed-everywhere", "vision", {"package.json": lambda t: edit_json(t, lambda d: d["queue"]["lanes"][3]["issues"].reverse()),
          "backlog.md": reverse_lane4_rows, "vision-reconciliation.md": reverse_lane4_rows, "../../docs/tasks/README.md": reverse_lane4_rows}),
        ("registry-dependency-reversed", "vision", {"package.json": lambda t: edit_json(t, lambda d: d["queue"]["dependencies"][0].update(before=242, after=198))}),
        ("order-word-contradicts-outside-lane-rows", "vision", {"backlog.md": lambda t: t.replace("they are not schedules.", "they are not schedules. #251 must precede #262.", 1)}),
        ("backward-order-word-contradicts-outside-lane-rows", "vision", {"vision-reconciliation.md": lambda t: t.replace("This reconciliation records a plan.", "This reconciliation records a plan; #261 follows #262.", 1)}),
        ("reverse-arrow-in-reconciliation", "vision", {"vision-reconciliation.md": lambda t: t.replace("## Scope gaps and their owners", "#262 <- #261\n\n## Scope gaps and their owners", 1)}),
        ("order-word-reintroduced-in-lane-row", "vision", {"backlog.md": lambda t: t.replace("(retirement and replacement safeguard)", "(retirement and replacement safeguard, before #117)", 1)}),
        ("child-dependencies-diverge-from-live-body", "backlog", {"backlog.json": lambda t: edit_json(t, lambda d: next(x for x in d if x["key"] == "B03").update(dependencies=next(y for y in d if y["key"] == "B03")["dependencies"] + " Also after #262."))}),
        ("reconciliation-scope-gap-row-removed", "vision", {"vision-reconciliation.md": lambda t: "".join(x for x in t.splitlines(keepends=True) if not x.startswith("| G04 "))}),
        ("foundation-order-reversed-in-registry", "vision", {"package.json": lambda t: edit_json(t, lambda d: d["queue"]["lanes"][1]["issues"].insert(0, d["queue"]["lanes"][1]["issues"].pop(1)))}),
        ("launch-lane-reordered-in-registry", "vision", {"package.json": lambda t: edit_json(t, lambda d: d["queue"]["lanes"][2]["issues"].insert(0, d["queue"]["lanes"][2]["issues"].pop(1)))}),
        ("layout-and-bounds-receipt-coordinated", "proposal", {"layouts/06-match-preparation.svg": lambda t: t + "\n",
          "evidence/layout-bounds-05.json": lambda t: edit_json(t, lambda d: next(x for x in d["layouts"] if x["svg"] == "06-match-preparation.svg").update(
              svg_sha256=sha((_PKG.path / "layouts/06-match-preparation.svg").read_bytes())))}),
        ("runtime-audit-source-and-report-coordinated", "current", {"evidence/runtime-06/audit-source.py": lambda t: t + "\n",
          "evidence/runtime-06/report.json": lambda t: edit_json(t, lambda d: d.update(audit_sha256=sha((_PKG.path / "evidence/runtime-06/audit-source.py").read_bytes())))}),
        ("contract-and-receipt-coordinated-edit", "backlog", {"backlog/B03.md": lambda t: t.replace("Split shared shell and Team/pool composition before dispatch.", "Compose everything at once."),
          "evidence/reconcile-05/live-issue-bodies.json": lambda t: edit_json(t, lambda d: next(x for x in d["mirrored"] if x["key"] == "B03").update(
              live_body_sha256=sha((_PKG.path / "backlog/B03.md").read_text().partition("\n\n")[2][:-1].encode())))})]

    intended_findings = {
        "quick-continuation-assigned-to-existing-scopes": "excluded capability assigned",
        "quick-continuation-omitted-from-gap": "gap field inventory differs",
        "quick-continuation-register-assigned-to250": "capability register silently extends",
        "quick-continuation-drawn-enabled": "07 lacks visible quick-continuation refusal/reason",
        "quick-continuation-flow-claimed-available": "J06 implies available fast-finish",
        "supported-country-identity-marked-unowned": "supported country identity/list/selection incorrectly unowned",
        "supported-friendly-route-marked-unowned": "supported/residual scope collapsed or misowned",
        "captain-residual-allocation-dropped": "need237 independent supported/residual allocations",
        "coordinated-mixed-source-and-parts-dropped": "234-field audit",
        "original-manager-rating-source-meaning-erased": "reviewed original field meanings/categories changed",
        "split-rendered-information-erased": "rendered source/allocation/destination/owner/reuse differs",
        "hero-mislabeled-as-first-slice": "delivery tier unlabelled/misleading",
        "hero-ranks-ambiguous": "ranks have ambiguous",
        "same-id-wouters-card-corrupted": "same-ID illustrative card disagrees",
        "pool-scrollbar-omitted": "pool lacks actual contained scrollbar",
        "pool-visible-count-omitted": "pool lacks visible subset count/scroll route",
        "comparison-biography-copied": "comparison copies outgoing biography",
        "selected-competition-tab-omitted": "no visible selected Groups tab",
        "original-live-speed-departure-omitted": "live-speed departure/acceptedT85 boundary unrecorded",
        "team-bits-reassigned-to-player-card-display": "TT reuse incorrectly assigned",
        "obsolete-recommendation-restored": "obsolete direction recommendation or selection question in README.md",
        "obsolete-recommendation-in-registry": "obsolete direction recommendation or selection question in package.json",
        "visual-style-question-reasked": "obsolete visual selection outside the historical section: paper",
        "direction-question-reasked": "O01 must be closed",
        "accepted-screen-dropped-from-registry": "accepted screen inventory differs",
        "drawn-surface-without-screen": "drawn surface without accepted screen: S04",
        "undrawn-surface-claimed-drawn": "surface coverage differs from the accepted-screen oracle: S06",
        "undrawn-surface-owner-dropped": "undrawn/partial surface lacks a bounded owner or states a drawn screen: S15",
        "reconciliation-screen-claim-diverges": "reconciliation table disagrees with registry: S05",
        "reconciliation-allocation-count-wrong": "reconciliation allocation count differs from the destination matrix: S08",
        "superseded-layout-without-successor": "superseded layout lacks its accepted successor: 05-competition",
        "candidate-layouts-recommended-again": "layouts.md does not declare the candidate sheets superseded",
        "accepted-screen-bytes-edited": "accepted screen differs from the pinned merge commit: docs/vision-266/screens/06-watched.svg",
        "queue-lane-issue-dropped": "queue lane order differs from the approved order: lane 1",
        "task-index-drops-career-stream": "queue issue absent from task index: #119",
        "backlog-drops-cloud-issue": "queue issue absent from backlog: #270",
        "gap-unowned-statement-removed": "scope obligation lacks an explicit unowned statement: O08 / G01",
        "evidence-encoding-obligation-dropped": "scope obligation missing: O13",
        "parity-context-screens-overclaimed": "reconciliation parity-context table disagrees with the destination matrix",
        "technology-claims-toolkit-selected": "technology document must not claim a toolkit was selected",
        "technology-proof-omits-two-line-commentary": "technology proof omits an accepted visual requirement: latest two commentary lines",
        "child-contract-diverges-from-live-body": "local contract differs from the recorded live amended body: B03",
        "child-priority-drifts-from-queue": "child lane/priority differs from the approved queue: B06",
        "cloud-issue-mirrored-instead-of-referenced": "#270 must be referenced, not mirrored or pre-split here",
        "pool-surface-coordinated-to-start-resume": "surface screen identity differs from the independent oracle: S05",
        "conditional-journey-coordinated-to-start-resume": "journey screen identity differs from the independent oracle: J07",
        "journey-edges-replaced-with-unused": "journey surfaces or edges differ from the independent oracle: J07",
        "journey-surfaces-replaced": "journey surfaces or edges differ from the independent oracle: J07",
        "surface-owner-coordinated-wrong": "undrawn/partial surface names the wrong bounded owner: S06",
        "child-lane-prose-drift": "backlog.md child lane/priority differs from the approved queue: B02",
        "foundation-arrows-reversed": "reverse arrow between queue issues in backlog.md",
        "history-dependency-inverted-prose": "queue lane text in backlog.md states an order outside the canonical dependency table: precede",
        "history-inverted-and-followon-removed-coordinated": "queue follow-on differs from the approved queue: lane 3",
        "followon-removed-in-registry-only": "queue follow-on differs from the approved queue: lane 3",
        "followon-removed-in-prose-only": "dependency table in backlog.md differs from the approved dependencies",
        "lane-objects-swapped-in-registry-array": "queue lanes are not listed in lane order",
        "canonical-row-reversed-in-backlog": "dependency table in backlog.md differs from the approved dependencies",
        "canonical-row-reversed-in-reconciliation": "dependency table in vision-reconciliation.md differs from the approved dependencies",
        "canonical-row-reversed-in-task-index": "dependency table in docs/tasks/README.md differs from the approved dependencies",
        "canonical-row-missing-in-reconciliation": "dependency table in vision-reconciliation.md differs from the approved dependencies",
        "retirement-constraint-row-dropped": "dependency table in docs/tasks/README.md differs from the approved dependencies",
        "non-prerequisite-row-dropped": "non-prerequisite table in docs/tasks/README.md differs from the approved pairs",
        "career-order-reversed-everywhere": "queue lane order differs from the approved order: lane 4",
        "registry-dependency-reversed": "queue dependencies in the registry differ from the approved pairs",
        "order-word-contradicts-outside-lane-rows": "order statement contradicts the approved dependencies in backlog.md",
        "backward-order-word-contradicts-outside-lane-rows": "order statement contradicts the approved dependencies in vision-reconciliation.md",
        "reverse-arrow-in-reconciliation": "reverse arrow between queue issues in vision-reconciliation.md",
        "order-word-reintroduced-in-lane-row": "queue lane text in backlog.md states an order outside the canonical dependency table: before",
        "child-dependencies-diverge-from-live-body": "backlog.json dependencies differ from the pinned live body: B03",
        "reconciliation-scope-gap-row-removed": "reconciliation lacks the unowned scope-gap row: G04",
        "foundation-order-reversed-in-registry": "queue lane order differs from the approved order: lane 2",
        "launch-lane-reordered-in-registry": "queue lane order differs from the approved order: lane 3",
        "layout-and-bounds-receipt-coordinated": "layout bounds receipt differs from the pinned reviewed receipt",
        "runtime-audit-source-and-report-coordinated": "observation report differs from the pinned reviewed report: evidence/runtime-06/report.json",
        "contract-and-receipt-coordinated-edit": "contract and receipt differ from the pinned live amended body: B03"}
    extra_cases, extra_findings = load_table_controls(package)
    cases += extra_cases
    intended_findings.update(extra_findings)
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
            if name in intended_findings:
                need(intended_findings[name] in result["finding"], "control rejected for unintended reason: " + name + " " + result["finding"])
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


def load_table_controls(package):
    """[designed: #253 rework R4] The table-parsing controls live in table_controls.py beside this file (kept apart so each file stays readable);
    the checkout under test supplies it, so a frozen copy of this helper needs only the tree."""
    import importlib.util
    path = package.path / "table_controls.py"
    need(path.is_file(), "table_controls.py missing from the package")
    spec = importlib.util.spec_from_file_location("table_controls", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.table_controls()


def regen_context_rows(text):
    """Coordinated-control helper: rebuild the reconciliation parity-context rows from the registry as it is on disk."""
    reg = json.loads((_PKG.path / "package.json").read_text())
    rows = context_screen_rows(reg, _PKG.rows("parity/destinations.tsv"))
    return "".join((rows[m.group(1)] + "\n") if (m := re.match(r"^\| ([A-Z]{2}) \|", line)) and m.group(1) in rows else line for line in text.splitlines(keepends=True))


def swap_row(text, before, after, source):
    """Control helper: write a canonical dependency row in the reverse direction."""
    old = f"| #{before} | #{after} | {source} |"
    assert old in text, old
    return text.replace(old, f"| #{after} | #{before} | {source} |", 1)


def drop_row(text, before, after, source):
    old = f"| #{before} | #{after} | {source} |\n"
    assert old in text, old
    return text.replace(old, "", 1)


def reverse_lane4_rows(text):
    return re.sub(r"^\| #(\d+) \| #(\d+) \| lane 4 \|$", lambda m: f"| #{m.group(2)} | #{m.group(1)} | lane 4 |", text, flags=re.M)


def edit_json(text, change):
    data = json.loads(text)
    change(data)
    return json.dumps(data, indent=2) + "\n"


def set_cell(text, key, column, value, key_column="id"):
    rows = list(csv.DictReader(io.StringIO(text), delimiter="\t"))
    next(r for r in rows if r[key_column] == key)[column] = value
    out = io.StringIO()
    writer = csv.DictWriter(out, fieldnames=list(rows[0]), delimiter="\t", lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    return out.getvalue()


def omit_quick_gap(text):
    data = json.loads(text)
    next(g for g in data["gaps"] if g["id"] == "G01")["fields"].remove("LI08")
    return json.dumps(data, indent=2) + "\n"


def change_svg_attribute(text, selector, attribute, value):
    tree = ET.fromstring(text)
    node = next(n for n in tree.iter() if selector(n))
    node.set(attribute, value)
    return ET.tostring(tree, encoding="unicode")


def enable_quick(text):
    tree = ET.fromstring(text)
    box = next(n for n in tree.iter() if n.get("data-action") == "quick-continuation")
    box.set("data-state", "available")
    box.set("fill", "#FFFFFF")
    next(n for n in tree.iter() if n.tag.endswith("text") and n.text == "Finish quickly · unavailable").text = "Finish quickly · supported stops"
    return ET.tostring(tree, encoding="unicode")


def unselect_groups(text):
    tree = ET.fromstring(text)
    box = next(n for n in tree.iter() if n.get("data-tab") == "Groups")
    box.set("data-state", "available")
    box.set("fill", "#FFFFFF")
    next(n for n in tree.iter() if n.tag.endswith("text") and n.text == "Groups").set("fill", "#182D36")
    return ET.tostring(tree, encoding="unicode")


def wrong_wouters_card(text):
    tree = ET.fromstring(text)
    next(n for n in tree.iter() if n.tag.endswith("text") and n.get("x") == "1029" and n.get("y") == "404").text = "4"
    return ET.tostring(tree, encoding="unicode")


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
    parser.add_argument("--base", default=None, help="revision the scope check measures changes from (default: merge-base with origin/main)")
    parser.add_argument("--check", choices=CHECKS)
    parser.add_argument("--all", action="store_true")
    parser.add_argument("--negative-controls", action="store_true")
    args = parser.parse_args()
    package = Package(args.root, args.base)
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
