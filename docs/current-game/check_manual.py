#!/usr/bin/env python3
"""[designed: T204] The current-game manual's own check.

It exits 0 only when the manual and its images agree:

1. every row of `image-provenance.tsv` has its image, with the recorded SHA-256;
2. every PNG under `images/` has a row;
3. every screen is written up: its name appears in one of the Markdown chapters;
4. every `images/...` link in the chapters resolves.

Run it after a re-capture (`tools/desktop-ui/manual-screens.py`): a changed hash means the build
draws that screen differently now, which is what the manual is for.

    python3 docs/current-game/check_manual.py
"""
import hashlib
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
TSV = HERE / 'image-provenance.tsv'
IMAGES = HERE / 'images'
CHAPTERS = ('README.md', 'flow.md', 'screen-inventory.md', 'match.md', 'capture-method.md')
HEADER = ('screen', 'image', 'route', 'reached', 'png_sha256')


def rows():
    lines = TSV.read_text().splitlines()
    if not lines or tuple(lines[0].split('\t')) != HEADER:
        raise SystemExit(f'{TSV.name}: the header must be {HEADER}')
    for number, line in enumerate(lines[1:], start=2):
        row = line.split('\t')
        if len(row) != len(HEADER):
            raise SystemExit(f'{TSV.name}:{number}: {len(row)} columns, expected {len(HEADER)}')
        yield dict(zip(HEADER, row))


def main():
    problems = []
    text = '\n'.join((HERE / name).read_text() for name in CHAPTERS)
    named = set()

    for row in rows():
        named.add(row['screen'])
        image = HERE / row['image']
        if not image.exists():
            problems.append(f"{row['screen']}: {row['image']} is not there")
            continue
        digest = hashlib.sha256(image.read_bytes()).hexdigest()
        if digest != row['png_sha256']:
            problems.append(f"{row['screen']}: {row['image']} is {digest[:12]}…, "
                            f"the table says {row['png_sha256'][:12]}… "
                            f"(re-capture, then update the table)")
        if row['screen'] not in text:
            problems.append(f"{row['screen']}: no chapter mentions it")
        if not row['reached'].strip():
            problems.append(f"{row['screen']}: the table does not say how it was reached")

    for image in sorted(IMAGES.glob('*.png')):
        if image.stem not in named:
            problems.append(f'{image.name}: no row in {TSV.name}')

    for link in sorted(set(re.findall(r']\((images/[\w.+-]+\.png)\)', text))):
        if not (HERE / link).exists():
            problems.append(f'a chapter links {link}, which is not there')

    if problems:
        print(f'{len(problems)} problem(s):')
        for problem in problems:
            print(f'  - {problem}')
        return 1
    print(f'{len(named)} screens, all present, hashed and written up.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
