"""`python -m goal2.ui`: the new window (docs/ui.md).

[designed: T162, #536; T163, #537] It opens S01 while the data folder lacks a file the new window needs, otherwise S02
Start. The portable build's launcher and default stay today's window (goal2/desktop) until T169 switches over.

    python -m goal2.ui [--data-root DIR]
    QT_QPA_PLATFORM=offscreen python -m goal2.ui --screenshot DIR

`--data-root` is the per-user goal2 folder (default: data_setup.user_root(); the data is in its `data`).
`--screenshot DIR` writes PNGs at 1440x900 into DIR and exits: S01, the placeholder home and S22 always; S02 with
two saves, S03, S04 with the name line, S05 with stand-in pages and the home with the new career when it finds the
data the new window needs (data_setup.WINDOW_MANIFEST) in the --data-root's data folder or, in a checkout, in
`.cache/`. It works in a temporary data folder of its own; the help is a stand-in text it writes there and the
bulletin pages are stand-ins labelled so (CLAUDE.md rule 14; the Python route has no bulletins yet, #509).
"""
from __future__ import annotations

import argparse
import datetime
import shutil
import sys
import tempfile
from pathlib import Path

# A stand-in help text for the pictures: goal2's own words, as code page 437 bytes with CR LF line ends and the DOS
# end-of-file mark, the shape of a help file. [designed: T162]
STAND_IN_HELP = (
    "──── goal2 stand-in help text ────\r\n\r\n"
    "This picture shows the help viewer with a text written by goal2's screenshot\r\n"
    "tool, not the original's help. With your own GOAL.HLP imported, F1 shows the\r\n"
    "original's help here, decoded as code page 437, in the window's VGA font.\r\n\r\n"
    "■ Up and Down scroll a line, PgUp and PgDn a page; the mouse wheel scrolls too.\r\n"
    "■ Esc closes the help and returns to the screen F1 was pressed on.\r\n\r\n"
    + "".join(f"Line {n} of the stand-in text.\r\n" for n in range(1, 31))
).encode("cp437") + b"\x1a"


# Stand-in bulletin pages for the S05 picture, labelled as such: goal2's own words, no news of a career.
# [designed: owner, 2026-11-03, #509]
STAND_IN_PAGES = [
    {"tag": "STAND-IN", "left": {"masthead": "STAND-IN STORY", "lines": ["goal2's screenshot tool wrote this page."]},
     "middle": {"masthead": f"STAND-IN PAGE {n}", "lines": ["NO NEWS OF A CAREER", "The Python route has no bulletins yet."]},
     "right": {"masthead": "STAND-IN STORY", "lines": ["The news arrives with its port (#509)."]}}
    for n in (1, 2)
]


def career_source(data_root=None):
    """A folder holding the new window's files (WINDOW_MANIFEST), or None: the data root's data, else `.cache/`."""
    from goal2.desktop import data_setup
    candidates = [data_setup.paths(data_root).data]
    candidates.append(Path(__file__).resolve().parents[2] / ".cache")
    for folder in candidates:
        if data_setup.complete(folder, data_setup.WINDOW_MANIFEST):
            return folder
    return None


def screenshots(out: Path, data_root=None) -> list[Path]:
    """PNGs of the new window's screens at 1440x900, in a temporary data folder of their own."""
    from PySide6.QtCore import Qt
    from PySide6.QtWidgets import QApplication
    from goal2.desktop import data_setup
    from goal2.ui import saves, theme
    from goal2.ui.home import HomeScreen
    from goal2.ui.s04_country import new_career
    from goal2.ui.s05_bulletin import BulletinScreen
    from goal2.ui.window import Window

    app = QApplication.instance() or QApplication(sys.argv[:1])
    theme.install(app)
    out.mkdir(parents=True, exist_ok=True)
    tmp = Path(tempfile.mkdtemp(prefix="goal2-ui-shots-"))
    written = []
    source = career_source(data_root)
    try:
        target = data_setup.paths(tmp / "goal2")
        offered = tmp / "offered"
        offered.mkdir()
        (offered / data_setup.HELP_NAME).write_bytes(STAND_IN_HELP)   # not the released file: refused as wrong
        window = Window(target, choose=lambda: str(offered))
        window.resize(1440, 900)
        window.show()

        def shot(name):
            for _ in range(3):
                app.processEvents()
            path = out / name
            window.grab().save(str(path))
            written.append(path)

        def key(k, text=""):
            from PySide6.QtGui import QKeyEvent
            from PySide6.QtCore import QEvent
            window.keyPressEvent(QKeyEvent(QEvent.Type.KeyPress, k, Qt.KeyboardModifier.NoModifier, text))
            app.processEvents()

        window.start()
        shot("s01-import-first.png")
        window.current().choose_and_import()
        shot("s01-import.png")
        window.replace_home(HomeScreen(window))
        shot("home.png")
        window.open_help()
        shot("s22-help-missing.png")
        window.pop()
        target.data.mkdir(parents=True, exist_ok=True)
        target.help.write_bytes(STAND_IN_HELP)
        window.open_help()
        shot("s22-help.png")
        window.pop()
        if source is None:
            print("no GOAL.DAT and template found (data root or .cache/): S02-S05 are not pictured", file=sys.stderr)
        else:
            target.help.unlink()   # the stand-in is not the released GOAL.HLP: the data check would refuse it
            for name, _ in data_setup.WINDOW_MANIFEST:
                shutil.copyfile(source / name, target.data / name)
            now = saves.now()
            for country, year, name, ago in ((20, 1992, "Holland after the draw", 0),
                                             (4, 1990, "Bulgaria, World Cup run", 2)):
                model = new_career(target, country, year, "K Ees" if country == 20 else "D Penev")
                saves.write(model, target.saves, name, saved=now - datetime.timedelta(hours=ago))
            window.start()
            shot("s02-start.png")
            key(Qt.Key.Key_N, "n")
            shot("s03-new-game.png")
            key(Qt.Key.Key_Return)
            screen = window.current()
            for _ in range(19):
                key(Qt.Key.Key_Down)
            screen.settle()
            key(Qt.Key.Key_Return)
            for character in "Kees":
                key(Qt.Key.Key_A, character)
            shot("s04-country.png")
            key(Qt.Key.Key_Return)
            career = window.career
            window.replace_home(BulletinScreen(window, STAND_IN_PAGES, lambda: window.open_career(career)))
            shot("s05-bulletin-stand-in.png")
            key(Qt.Key.Key_Return)
            key(Qt.Key.Key_Return)
            shot("home-career.png")
        window.close()
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    return written


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="python -m goal2.ui", description="goal2's new window (docs/ui.md)")
    parser.add_argument("--data-root", type=Path, help="the per-user goal2 folder (default: the user's)")
    parser.add_argument("--screenshot", type=Path, metavar="DIR", help="write PNGs of the screens and exit")
    args = parser.parse_args(argv)
    if args.screenshot is not None:
        for path in screenshots(args.screenshot, args.data_root):
            print(path)
        return 0
    from PySide6.QtWidgets import QApplication
    from goal2.desktop import data_setup
    from goal2.ui import theme
    from goal2.ui.window import Window
    app = QApplication.instance() or QApplication(sys.argv[:1])
    theme.install(app)
    window = Window(data_setup.paths(args.data_root))
    window.start()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
