#!/usr/bin/env python3
"""[designed: T157] Check that the design maps every original screen.

The original screens are:
  - every classified kind in docs/original-game/screen-inventory.md (its first table, `kind` in column 1);
  - every original image embedded in the chapters of docs/original-game/ (T156's playthrough first), named by
    its file name without .png.
The design's mapping is the table between `<!-- mapping:start -->` and `<!-- mapping:end -->` in this folder's
README.md. Each row's first cell is a new screen (`S01`..`Snn`) or `dropped`; the backticked names in the row are
the original screens it replaces. A `dropped` row must give a reason in its last cell.

It also checks the screens: every new screen named in the mapping has a section heading `### Snn` in the README,
and a mockup `images/snn-*.png` that exists and that the README embeds.

Exit 0 when nothing is missing, 1 otherwise; every problem is printed.
    python3 docs/design/ui-2026-11/check_mapping.py
"""
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
ORIGINAL = ROOT / "docs" / "original-game"
README = HERE / "README.md"

KIND = re.compile(r"^\|\s*`([a-z0-9-]+)`\s*\|")
EMBED = re.compile(r"!\[[^\]]*\]\(images/([A-Za-z0-9_.-]+)\.png\)")
TICK = re.compile(r"`([A-Za-z0-9_.-]+)`")
SCREEN = re.compile(r"^S\d\d$")


def original_screens():
    """Name -> where it comes from."""
    found = {}
    inventory = (ORIGINAL / "screen-inventory.md").read_text(encoding="utf-8")
    first_table = inventory.split("## ", 1)[0]
    for line in first_table.splitlines():
        m = KIND.match(line)
        if m:
            found.setdefault(m.group(1), "screen-inventory.md")
    for chapter in sorted(ORIGINAL.glob("*.md")):
        for name in EMBED.findall(chapter.read_text(encoding="utf-8")):
            found.setdefault(name, chapter.name)
    return found


def mapping(text):
    """Rows of the mapping table: (first cell, names, last cell, line number)."""
    if "<!-- mapping:start -->" not in text or "<!-- mapping:end -->" not in text:
        return None
    start = text.index("<!-- mapping:start -->")
    body = text[start:text.index("<!-- mapping:end -->")]
    line0 = text[:start].count("\n") + 1
    rows = []
    for offset, line in enumerate(body.splitlines()):
        if not line.startswith("|") or set(line.replace("|", "").strip()) <= set("-: "):
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        first = cells[0].strip("*")
        if first.lower() in ("new screen", "screen"):
            continue
        rows.append((first, TICK.findall("|".join(cells[1:])), cells[-1], line0 + offset))
    return rows


def main():
    problems = []
    originals = original_screens()
    text = README.read_text(encoding="utf-8") if README.exists() else ""
    rows = mapping(text)
    if rows is None:
        print(f"{README.relative_to(ROOT)}: no mapping table (<!-- mapping:start --> ... <!-- mapping:end -->)")
        print(f"{len(originals)} original screens, 0 mapped")
        return 1
    mapped, screens = {}, set()
    for first, names, last, line in rows:
        if SCREEN.match(first):
            screens.add(first)
        elif first.lower() == "dropped":
            if len(last) < 10 or not re.search(r"[A-Za-z]{3}", last):
                problems.append(f"README.md:{line}: dropped row without a reason")
        else:
            problems.append(f"README.md:{line}: first cell {first!r} is neither Snn nor dropped")
            continue
        for name in names:
            if name in originals:
                mapped.setdefault(name, first)
            elif not SCREEN.match(name):
                problems.append(f"README.md:{line}: `{name}` is not an original screen")
    for name, source in sorted(originals.items()):
        if name not in mapped:
            problems.append(f"unmapped: `{name}` ({source})")
    for screen in sorted(screens):
        if not re.search(rf"^### {screen}\b", text, re.M):
            problems.append(f"{screen}: no section '### {screen}' in README.md")
        images = sorted((HERE / "images").glob(f"{screen.lower()}-*.png"))
        if not images:
            problems.append(f"{screen}: no mockup images/{screen.lower()}-*.png")
        for image in images:
            if f"](images/{image.name})" not in text:
                problems.append(f"{screen}: mockup images/{image.name} is not embedded in README.md")
    for problem in problems:
        print(problem)
    dropped = sum(1 for v in mapped.values() if v.lower() == "dropped")
    print(f"{len(originals)} original screens: {len(mapped) - dropped} mapped to {len(screens)} new screens, "
          f"{dropped} dropped, {len(originals) - len(mapped)} missing; {len(problems)} problems")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
