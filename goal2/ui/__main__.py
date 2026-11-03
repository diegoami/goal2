"""`python -m goal2.ui`: the new window (docs/ui.md).

[designed: T162, #536] It opens S01 while the data folder is not imported, otherwise the placeholder home screen
(T163 replaces it with S02). The portable build's launcher and default stay today's window (goal2/desktop) until
T169 switches over.

    python -m goal2.ui [--data-root DIR]
    QT_QPA_PLATFORM=offscreen python -m goal2.ui --screenshot DIR

`--data-root` is the per-user goal2 folder (default: data_setup.user_root(); the data is in its `data`).
`--screenshot DIR` writes PNGs of S01, the placeholder home and S22 at 1440x900 into DIR and exits. It works in a
temporary data folder of its own and shows the help with a stand-in text it writes there, so no byte of the
original's files is in the pictures (CLAUDE.md rule 14).
"""
from __future__ import annotations

import argparse
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


def screenshots(out: Path) -> list[Path]:
    """PNGs of the new window's screens at 1440x900, in a temporary data folder of their own."""
    from PySide6.QtWidgets import QApplication
    from goal2.desktop import data_setup
    from goal2.ui import theme
    from goal2.ui.home import HomeScreen
    from goal2.ui.window import Window

    app = QApplication.instance() or QApplication(sys.argv[:1])
    theme.install(app)
    out.mkdir(parents=True, exist_ok=True)
    tmp = Path(tempfile.mkdtemp(prefix="goal2-ui-shots-"))
    written = []
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
        window.close()
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    return written


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="python -m goal2.ui", description="goal2's new window (docs/ui.md)")
    parser.add_argument("--data-root", type=Path, help="the per-user goal2 folder (default: the user's)")
    parser.add_argument("--screenshot", type=Path, metavar="DIR", help="write PNGs of S01, the home and S22 and exit")
    args = parser.parse_args(argv)
    if args.screenshot is not None:
        for path in screenshots(args.screenshot):
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
