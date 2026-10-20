"""[designed: #253 rework R4/R5] Negative controls for the Markdown-table parsers of validate.py, loaded by `--negative-controls`.
Each control edits saved bytes only (validate.py restores them in finally and checks the hashes) and names the finding that must reject it."""
from __future__ import annotations
import json
import re


QUEUE_FILES = (("backlog.md", "backlog.md"), ("vision-reconciliation.md", "vision-reconciliation.md"), ("docs/tasks/README.md", "../../docs/tasks/README.md"))


def compact(line):
    """The same Markdown row without the spaces next to its pipes."""
    return "|".join(cell.strip() for cell in line.split("|"))


def after_line(text, prefix, new):
    """Insert `new` (text, or a function of the matched line) as a line directly after the first line that starts with `prefix`."""
    lines = text.split("\n")
    index = next(i for i, x in enumerate(lines) if x.startswith(prefix))
    return "\n".join(lines[:index + 1] + [new if isinstance(new, str) else new(lines[index])] + lines[index + 1:])


def duplicate_compact(prefix):
    return lambda t: after_line(t, prefix, compact)


def append_block(block):
    return lambda t: t.rstrip("\n") + "\n\n" + block + "\n"


def edit_json(text, change):
    data = json.loads(text)
    change(data)
    return json.dumps(data, indent=2) + "\n"


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


def queue_cases():
    return [
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
        ("launch-lane-reordered-in-registry", "vision", {"package.json": lambda t: edit_json(t, lambda d: d["queue"]["lanes"][2]["issues"].insert(0, d["queue"]["lanes"][2]["issues"].pop(1)))})]


def queue_findings():
    return {
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
    }


def table_controls():
    """[designed: #253 rework R4/R5] One control per manifestation of the table-parsing class, each in every document that carries the queue,
    plus the other table parsers swept in the same round. Returns (cases, intended findings)."""
    cases, findings = [], {}

    def add(name, check, edits, reason):
        cases.append((name, check, edits))
        findings[name] = reason

    last_dependency, last_non_prerequisite = "| #155 | #117 | lane 4 |", "| #259 | #243 | lane 2 |"
    for label, key in QUEUE_FILES:
        short = label.split("/")[-1].removesuffix(".md")
        add(f"compact-extra-dependency-row-in-{short}", "vision", {key: lambda t: after_line(t, last_dependency, "| #242 | #198 | lane 2|")},
            f"dependency table in {label} differs from the approved dependencies")
        add(f"compact-extra-non-prerequisite-row-in-{short}", "vision", {key: lambda t: after_line(t, last_non_prerequisite, "| #198 | #259 | lane 2|")},
            f"non-prerequisite table in {label} differs from the approved pairs")
        add(f"fully-compact-extra-dependency-row-in-{short}", "vision", {key: lambda t: after_line(t, last_dependency, "|#242|#198|lane 2|")},
            f"dependency table in {label} differs from the approved dependencies")
        add(f"dependency-row-without-closing-pipe-in-{short}", "vision", {key: lambda t: after_line(t, last_dependency, "| #242 | #198 | lane 2")},
            f"malformed table row in {label}")
        add(f"dependency-row-with-two-cells-in-{short}", "vision", {key: lambda t: after_line(t, last_dependency, "| #242 | #198 |")},
            f"table row with 2 cells under a 3-cell header in {label}")
        add(f"non-prerequisite-row-with-a-word-instead-of-an-issue-in-{short}", "vision", {key: lambda t: after_line(t, last_non_prerequisite, "| #198 | later | lane 2 |")},
            f"unparsed row in the 'Not a prerequisite' table of {label}")
        add(f"compact-header-copy-of-the-dependency-table-in-{short}", "vision", {key: append_block("|Before|After|Source|\n|---|---|---|\n|#242|#198|lane 2|")},
            f"{label} lacks exactly one 'Before | After | Source' table")
        add(f"issue-pair-table-with-another-header-in-{short}", "vision", {key: append_block("| Relation | Of | Note |\n| --- | --- | --- |\n| #242 | #198 | lane 2 |")},
            f"table row outside the canonical tables relates two issues in {label}")
        add(f"contradiction-clause-in-another-table-in-{short}", "vision",
            {key: append_block("[designed] Additional queue relation:\n\n| Relation |\n| --- |\n| #242 must precede #198 |")},
            f"order statement contradicts the approved dependencies in {label}")
        add(f"forward-arrow-in-another-table-in-{short}", "vision",
            {key: append_block("[designed] Additional queue relation:\n\n| Relation |\n| --- |\n| #251 → #262 |")},
            f"order statement contradicts the approved dependencies in {label}")
        add(f"contradiction-split-across-cells-in-another-table-in-{short}", "vision",
            {key: append_block("[designed] Additional queue relation:\n\n| Issue | Relation | Issue |\n| --- | --- | --- |\n| see #242 | must precede | #198 |")},
            f"order statement contradicts the approved dependencies in {label}")
    # a table runs to the first blank line: any line after the last row, of any shape, must be a well-formed row or the table fails
    continuations = (("pipeless-continuation-row", "#242 | #198 | lane 2", "malformed table row in {}"),
                     ("trailing-pipe-only-continuation-row", "#242 | #198 | lane 2 |", "malformed table row in {}"),
                     ("plain-text-line-after-the-last-row", "Plain text directly after the table.", "table must end with a blank line in {}"),
                     ("inline-html-led-row", "<b>#242</b> | #198 | lane 2", "malformed table row in {}"),
                     ("autolink-led-row", "<https://example.com> | #198 | lane 2", "malformed table row in {}"),
                     ("heading-line-directly-after-the-table", "## A heading directly after the table", "table must end with a blank line in {}"))
    for label, key in QUEUE_FILES:
        short = label.split("/")[-1].removesuffix(".md")
        for form, line, reason in continuations:
            add(f"{form}-after-the-dependency-table-in-{short}", "vision", {key: lambda t, line=line: after_line(t, last_dependency, line)}, reason.format(label))
            add(f"{form}-after-the-non-prerequisite-table-in-{short}", "vision", {key: lambda t, line=line: after_line(t, last_non_prerequisite, line)}, reason.format(label))
    for place, check, key, anchor in (("child-table-in-backlog", "backlog", "backlog.md", "| [B07]("), ("surface-table", "vision", "vision-reconciliation.md", "| S15 "),
                                      ("decision-table", "vision", "decisions.md", "| O07 |"), ("parity-matrix", "parity", "parity/management.md", "| ST06 |")):
        for form, line, reason in continuations:
            add(f"{form}-in-the-{place}", check, {key: lambda t, line=line, anchor=anchor: after_line(t, anchor, line)}, reason.format(key))
    add("compact-lane-row-with-an-order-word", "vision",
        {"backlog.md": lambda t: t.replace("(retirement and replacement safeguard)", "(retirement and replacement safeguard, before #117)", 1).replace("| 4 Independent career stream | Real", "|4 Independent career stream|Real", 1)},
        "queue lane text in backlog.md states an order outside the canonical dependency table: before")
    # the other table parsers swept in the same round
    add("duplicate-compact-child-row-in-backlog", "backlog", {"backlog.md": duplicate_compact("| [B02](")}, "duplicate B02 row in the ID / issue table of backlog.md")
    add("malformed-child-row-in-backlog", "backlog",
        {"backlog.md": lambda t: after_line(t, "| [B02](", "| [B09](backlog/B09.md) · [#999](https://github.com/diegoami/goal2/issues/999) | 3 |")},
        "table row with 2 cells under a 5-cell header in backlog.md")
    add("duplicate-compact-decision-row", "vision", {"decisions.md": duplicate_compact("| O02 |")}, "duplicate O02 row in the ID table of decisions.md")
    add("unparsed-decision-row", "vision", {"decisions.md": lambda t: after_line(t, "| O02 |", "| later | open | x | y |")}, "unparsed row in the ID table of decisions.md")
    add("duplicate-compact-allocation-row", "parity", {"parity/management.md": duplicate_compact("| ST01 |")}, "rendered matrix omitted/duplicated allocation")
    add("malformed-allocation-row", "parity", {"parity/management.md": lambda t: after_line(t, "| CS01 |", "| CS99 | x |")},
        "table row with 2 cells under a 5-cell header in parity/management.md")
    add("unparsed-allocation-row", "parity", {"parity/match.md": lambda t: after_line(t, "| MP01-S |", "| later | a | b | c | d |")}, "unparsed allocation row in parity/match.md")
    add("compact-extra-screen-hierarchy-row", "journeys", {"journeys.md": lambda t: after_line(t, "| S15 |", "|S16|x|y|")}, "screen hierarchy prose incomplete")
    add("duplicate-compact-surface-row", "vision", {"vision-reconciliation.md": duplicate_compact("| S02 New career |")},
        "duplicate S02 row in the Surface table of vision-reconciliation.md")
    add("compact-extra-surface-row", "vision", {"vision-reconciliation.md": lambda t: after_line(t, "| S15 ", "|S16 Extra|drawn|01|none|0|")}, "reconciliation surface table incomplete")
    add("duplicate-compact-context-row", "vision", {"vision-reconciliation.md": duplicate_compact("| ST | ")}, "duplicate ST row in the Context table of vision-reconciliation.md")
    add("duplicate-compact-journey-row", "vision", {"vision-reconciliation.md": duplicate_compact("| J02 ")}, "duplicate J02 row in the Journey table of vision-reconciliation.md")
    add("duplicate-compact-layout-row", "vision", {"vision-reconciliation.md": duplicate_compact("| 02 country desk |")},
        "duplicate 02 row in the Candidate sheet table of vision-reconciliation.md")
    add("duplicate-compact-scope-gap-row", "vision", {"vision-reconciliation.md": duplicate_compact("| G03 ")}, "duplicate G03 row in the Obligation table of vision-reconciliation.md")
    return cases + queue_cases(), {**findings, **queue_findings()}
