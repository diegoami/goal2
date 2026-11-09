#!/usr/bin/env python3
"""[designed: owner, 2026-11-08; T205, #666] Render the proposal's screens and the comparison strips.

    python3 docs/design/ui-2026-11/proposal/build.py            screens and strips
    python3 docs/design/ui-2026-11/proposal/build.py --screens  the screens only

A strip is three panels: the original capture (shown at 4:3, as it was seen), the window as it is
built today (the newest render the UI tasks left in `../T1*-screens/`), and the proposal. The
strips need ImageMagick (`magick`); without it the screens are still written and the strips are
skipped with a word. Needs the desktop extra, as the other UI tooling does.
"""
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
sys.path.insert(0, str(HERE))
import screens  # noqa: E402

# Each proposal screen: the original capture it comes from, and the newest render of the window
# as it is built today (the screen folders the UI tasks leave behind).
ORIGINALS = {
    's06-hub': ('manager-menu', 'T178-screens/s06-desk.png'),
    's08-squad': ('m244-squad', 'T165-screens/s08-squad.png'),
    's11-fixtures': ('fixtures-watch', 'T178-screens/s11-fixtures.png'),
    's05-bulletin': ('bulletin', 'T163-screens/s05-bulletin-stand-in.png'),
    's15-match-menu': ('match-menu', 'T167-screens/s15-match-menu.png'),
    's17-pitch': ('match-live', 'fix-583-screens/s17-pitch.png'),
}
PANEL = (620, 465)                      # each panel of a strip, at 4:3


def column(source, label, out):
    """One labelled panel of a strip."""
    width, height = PANEL
    subprocess.run(['magick', str(source), '-resize', f'{width}x{height}!',
                    '-bordercolor', '#333333', '-border', '2', str(out)], check=True)
    label_file = out.with_suffix('.label.png')
    subprocess.run(['magick', '-size', f'{width + 4}x34', 'xc:#101010', '-fill', 'white',
                    '-pointsize', '20', '-gravity', 'center', '-annotate', '0', label,
                    str(label_file)], check=True)
    subprocess.run(['magick', str(label_file), str(out), '-append', str(out)], check=True)
    label_file.unlink()
    return out


def strips(out):
    """The three-way comparison for each screen."""
    if not shutil.which('magick'):
        print('  (no ImageMagick: the comparison strips were not built)')
        return
    work = out / '.work'
    work.mkdir(parents=True, exist_ok=True)
    for name, (original, built) in ORIGINALS.items():
        today, label = HERE.parent / built, 'THE WINDOW TODAY'
        if not today.exists():
            # No render from a UI task: fall back to the design's own mockup, and say so.
            today, label = HERE.parent / f'images/{name}.png', "THE DESIGN'S MOCKUP"
        panels = [column(ROOT / f'docs/original-game/images/{original}.png',
                         'THE ORIGINAL (at 4:3)', work / 'a.png'),
                  column(today, label, work / 'b.png'),
                  column(out / f'{name}.png', 'THE PROPOSAL', work / 'c.png')]
        target = out / f'compare-{name}.png'
        subprocess.run(['magick', *[str(p) for p in panels], '+append',
                        '-bordercolor', '#101010', '-border', '8', str(target)], check=True)
        print(f'  {target.relative_to(ROOT)}')
    shutil.rmtree(work)


def main():
    out = HERE / 'images'
    for name, draw in screens.SCREENS.items():
        print(f'  {draw(out / f"{name}.png").relative_to(ROOT)}')
    if '--screens' not in sys.argv:
        strips(out)
    return 0


if __name__ == '__main__':
    sys.exit(main())
