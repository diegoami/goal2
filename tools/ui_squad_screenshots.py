"""Pictures of S08 (squad, and pool with *put here*), S09 and S10 at 1440x900 (T165).

    QT_QPA_PLATFORM=offscreen python tools/ui_squad_screenshots.py DIR [--country N]

[designed: T165] `python -m goal2.ui --screenshot` belongs to T163 while T163 is open; this tool writes the squad
screens' pictures until T164 puts them on the desk. It needs the career files of the git-ignored `.cache/`
(GOAL.DAT and e010-r0008-halftime.sav, tools/artifacts.py), as the desktop tests do, and writes into DIR only.
"""
from __future__ import annotations

import argparse
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def screenshots(out: Path, country: int = 20) -> list[Path]:
    from PySide6.QtCore import Qt
    from PySide6.QtWidgets import QApplication
    from goal2.desktop import data_setup
    from goal2.desktop.model import DesktopModel
    from goal2.ui import theme
    from goal2.ui.s08_squad import open_squad
    from goal2.ui.s10_team_tactics import open_team_tactics
    from goal2.ui.window import Window

    app = QApplication.instance() or QApplication(sys.argv[:1])
    theme.install(app)
    out.mkdir(parents=True, exist_ok=True)
    tmp = Path(tempfile.mkdtemp(prefix="goal2-t165-shots-"))
    model = DesktopModel.open(ROOT / ".cache/e010-r0008-halftime.sav", ROOT / ".cache/GOAL.DAT", tmp / "career",
                              country=country)
    window = Window(data_setup.paths(tmp / "goal2"))
    window.resize(1440, 900)
    window.show()
    written = []

    def shot(name):
        for _ in range(3):
            app.processEvents()
        path = out / name
        window.grab().save(str(path))
        written.append(path)

    def key(k):
        window.current().handle_key(k)
        app.processEvents()

    squad = open_squad(window, model)
    shot("s08-squad.png")
    key(Qt.Key.Key_Right)
    key(Qt.Key.Key_Return)
    shot("s08-pool.png")
    key(Qt.Key.Key_Left)
    key(Qt.Key.Key_Down)
    shot("s08-put-here.png")
    squad.picked = None         # the picture only: no exchange is made
    squad.refresh()
    key(Qt.Key.Key_T)
    shot("s09-player-tactics.png")
    key(Qt.Key.Key_Escape)
    open_team_tactics(window, model)
    key(Qt.Key.Key_Return)
    shot("s10-team-tactics.png")
    window.close()
    return written


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("out", type=Path)
    parser.add_argument("--country", type=int, default=20, help="the managed country (default 20, the mockups')")
    args = parser.parse_args(argv)
    for path in screenshots(args.out, args.country):
        print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
