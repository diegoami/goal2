"""[designed: #253 rework R4/R5] Negative controls for the Markdown-table parsers of validate.py, loaded by `--negative-controls`.
Each control edits saved bytes only (validate.py restores them in finally and checks the hashes) and names the finding that must reject it."""
from __future__ import annotations


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
    # GFM continuation: every line after the last row, pipe-led or not, is a further row of the same table until a blank line
    continuations = (("pipeless-continuation-row", "#242 | #198 | lane 2", "malformed table row in {}"),
                     ("trailing-pipe-only-continuation-row", "#242 | #198 | lane 2 |", "malformed table row in {}"),
                     ("plain-text-line-after-the-last-row", "Plain text directly after the table.", "table row without pipes in {}"))
    for label, key in QUEUE_FILES:
        short = label.split("/")[-1].removesuffix(".md")
        for form, line, reason in continuations:
            add(f"{form}-after-the-dependency-table-in-{short}", "vision", {key: lambda t, line=line: after_line(t, last_dependency, line)}, reason.format(label))
            add(f"{form}-after-the-non-prerequisite-table-in-{short}", "vision", {key: lambda t, line=line: after_line(t, last_non_prerequisite, line)}, reason.format(label))
    for place, check, key, anchor in (("child-table-in-backlog", "backlog", "backlog.md", "| [B07]("), ("surface-table", "vision", "vision-reconciliation.md", "| S15 "),
                                      ("decision-table", "vision", "decisions.md", "| O02 |"), ("parity-matrix", "parity", "parity/management.md", "| ST01 |")):
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
    return cases, findings
