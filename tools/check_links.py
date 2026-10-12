#!/usr/bin/env python3
"""Fail if a relative link in a tracked Markdown file points at a file that does not exist, or a
tracked JSON file does not parse. Inline links and reference-style links (via their `[ref]: target`
definitions) are checked; code spans, fenced code blocks, web links and in-page anchors are not.
Exit 0 clean, 1 broken."""
# Copied from diegoami/game-archaeologist tools/check_links.py at formats-v1 (3365343), unchanged.
import json
import re
import subprocess
import sys
from pathlib import Path

INLINE = re.compile(r"\[[^\]]*\]\(([^)\s]+)\)")
REF_DEF = re.compile(r"^[ \t]*\[([^\]]+)\]:[ \t]*(\S+)")


def strip_code_spans(line):
    """Remove CommonMark code spans from one line, so links inside them are not checked. A run of N
    backticks opens a span that closes at the next run of exactly N backticks and may itself contain
    backticks; a run with no closing run of its own length is literal text. A backtick escaped by a
    preceding odd number of backslashes is literal text: it opens and closes no span. Spans never
    cross a line."""
    chars = list(line)
    for i, ch in enumerate(chars):
        if ch != "`":
            continue
        backslashes, j = 0, i - 1
        while j >= 0 and line[j] == "\\":
            backslashes, j = backslashes + 1, j - 1
        if backslashes % 2:
            chars[i] = " "
    line = "".join(chars)
    out, i, n = [], 0, len(line)
    while i < n:
        if line[i] != "`":
            out.append(line[i])
            i += 1
            continue
        opener_end = i
        while opener_end < n and line[opener_end] == "`":
            opener_end += 1
        width = opener_end - i
        close, closing_end = opener_end, None
        while close < n:
            if line[close] != "`":
                close += 1
                continue
            run_end = close
            while run_end < n and line[run_end] == "`":
                run_end += 1
            if run_end - close == width:
                closing_end = run_end
                break
            close = run_end
        if closing_end is None:
            out.append(line[i:opener_end])
            i = opener_end
        else:
            # A space, not nothing: `[a]`x`(b.md)` must not become the link `[a](b.md)`.
            out.append(" ")
            i = closing_end
    return "".join(out)


root = Path(subprocess.check_output(["git", "rev-parse", "--show-toplevel"], text=True).strip())
files = subprocess.check_output(["git", "ls-files", "-co", "--exclude-standard"], cwd=root, text=True).split()
problems = []
for name in files:
    path = root / name
    if not path.is_file():
        continue
    if name.endswith(".json"):
        try:
            json.loads(path.read_text(encoding="utf-8"))
        except ValueError as e:
            problems.append(f"{name}: invalid JSON: {e}")
    if not name.endswith(".md"):
        continue
    in_fence = False
    for n, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if line.lstrip().startswith("```"):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        # Inline code spans are not links; a reference definition can sit outside one.
        line = strip_code_spans(line)
        targets = INLINE.findall(line)
        definition = REF_DEF.match(line)
        if definition:
            targets.append(definition.group(2))
        for target in targets:
            if target.startswith("<") and target.endswith(">"):
                target = target[1:-1]
            if re.match(r"^[a-z][a-z0-9+.-]*:", target) or target.startswith("#"):
                continue
            target = target.split("#", 1)[0]
            if target and not (path.parent / target).exists():
                problems.append(f"{name}:{n}: broken link {target}")
print("\n".join(problems) if problems else f"links and JSON ok ({len(files)} files)")
sys.exit(1 if problems else 0)
