#!/usr/bin/env python3
"""[designed: owner, 2026-11-08; T177, #666] Render the proposal's screens into images/.

    python3 docs/design/ui-2026-11/proposal/build.py [--raw]

`--raw` also writes the logical page (90x28 cells of 16x32, 1440x896) beside the presented one,
which is that page at the original's 4:3 (a 1.2 vertical stretch).
"""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import screens  # noqa: E402

def main():
    out = HERE / 'images'
    for name, draw in screens.SCREENS.items():
        path = draw(out / f'{name}.png')
        print(f'  {path.relative_to(HERE.parents[3])}')
    return 0

if __name__ == '__main__':
    sys.exit(main())
