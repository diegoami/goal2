"""[designed: owner, 2026-11-03, T169] The new window (goal2.ui) offscreen, for the packaged smoke (tools/portable/smoke.py):
its first start on an empty per-user folder shows S01, imports a stand-in for the player's data folder through S01 and
shows S02 Start; then a new career (Holland, 1992) plays its first friendly through the match day from the desk's *play
next game* (S14, S15, S16 with the computer's captain, S17 with R, the quick result, its worker under
GOAL2_ENGINE_PYTHON, then the boards and menus back to the desk; T167). It writes what it saw.

    python smoke_window.py --cache DIR --at DIR --out FILE [--expect-root DIR]

The stand-in data folder is made in --at from the new window's files (data_setup.WINDOW_MANIFEST: GOAL.DAT and the
Python route's template) found in --cache, outside the build; the per-user folder is a fresh one in --at too, so the
player's own is never touched. With --expect-root, goal2 must be imported from DIR's `python/` and the worker must be
DIR's PyPy: the packaged run may not reach the source tree. The exit status is 1 when a step fails.
"""
import argparse
import json
import os
import platform
import shutil
import sys
import time
from pathlib import Path


def main(argv=None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cache", type=Path, required=True)
    parser.add_argument("--at", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--expect-root", type=Path)
    parser.add_argument("--limit", type=float, default=1800, help="seconds the match may take")
    args = parser.parse_args(argv)
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    import goal2
    from goal2.desktop import data_setup
    from goal2.game.engine_python import engine_python
    where = Path(goal2.__file__).resolve()
    result = {"ui_python": f"{platform.python_implementation()} {platform.python_version()}",
              "ui_executable": sys.executable, "goal2": str(where), "steps": {}}
    steps = result["steps"]

    def done(code):
        result["pass"] = code == 0
        args.out.write_text(json.dumps(result, indent=1) + "\n")
        return code

    if args.expect_root is not None:
        root = args.expect_root.resolve()
        steps["from_the_build"] = {"pass": root / "python" in where.parents
                                   and Path(engine_python()).resolve() == root / "pypy" / "pypy.exe",
                                   "engine_python": engine_python()}
        if not steps["from_the_build"]["pass"]:
            return done(1)

    at = args.at.resolve()
    offered, user = at / "offered data ä", at / "user root ä"
    offered.mkdir(parents=True)
    for name, _ in data_setup.WINDOW_MANIFEST:
        shutil.copyfile(args.cache / name, offered / name)

    from PySide6.QtWidgets import QApplication
    from goal2.ui import theme
    from goal2.ui.s01_import import ImportScreen
    from goal2.ui.s02_start import StartScreen
    from goal2.ui.s04_country import new_career
    from PySide6.QtCore import QEvent, Qt
    from PySide6.QtGui import QKeyEvent
    from goal2.ui.match_day import play_next_game
    from goal2.ui.s06_desk import DeskScreen
    from goal2.ui.s14_round import RoundScreen
    from goal2.ui.s16_choose import ChooseScreen
    from goal2.ui.s17_pitch import PitchScreen
    from goal2.ui.window import Window
    app = QApplication.instance() or QApplication(sys.argv[:1])
    theme.install(app)
    target = data_setup.paths(user)
    window = Window(target, choose=lambda: str(offered))
    window.show()
    app.processEvents()

    # S01 on the first start, its import, then S02
    window.start()
    app.processEvents()
    first = type(window.current()).__name__
    imported = window.current().choose_and_import() if isinstance(window.current(), ImportScreen) else False
    app.processEvents()
    steps["s01_import_then_s02"] = {"pass": first == "ImportScreen" and imported
                                    and isinstance(window.current(), StartScreen)
                                    and data_setup.complete(target.data, data_setup.WINDOW_MANIFEST),
                                    "first": first, "imported": imported, "then": type(window.current()).__name__,
                                    "data": sorted(p.name for p in target.data.iterdir()) if target.data.is_dir() else []}
    if not steps["s01_import_then_s02"]["pass"]:
        return done(1)

    def key(k, text=""):
        window.keyPressEvent(QKeyEvent(QEvent.Type.KeyPress, k, Qt.KeyboardModifier.NoModifier, text))
        app.processEvents()

    # a new career's first friendly through the match day (T167): S14 Enter, S15 Enter (play), S16 C (the computer's
    # captain), S17 R (the quick result), then the boards, menus and round back to the desk
    model = new_career(target, 20, 1992, "K Ees")
    window.open_career(model)
    started = time.monotonic()
    opened = play_next_game(window, model)
    if not isinstance(opened, RoundScreen):
        steps["match"] = {"pass": False, "not_started": str(opened)}
        return done(1)
    key(Qt.Key.Key_Return)
    key(Qt.Key.Key_Return)
    key(Qt.Key.Key_C, "c")
    pitch = window.current()
    if not isinstance(pitch, PitchScreen):
        steps["match"] = {"pass": False, "not_started": type(pitch).__name__}
        return done(1)
    controller = pitch.controller
    worker = controller.bridge.interpreter
    pitch.quick_result()
    while not isinstance(window.current(), DeskScreen) and time.monotonic() - started < args.limit:
        app.processEvents()
        current = window.current()
        if isinstance(current, ChooseScreen):
            key(Qt.Key.Key_C, "c")
        elif current is not pitch and not (isinstance(current, RoundScreen) and current.arriving):
            key(Qt.Key.Key_Return)
        time.sleep(.005)
    wall = round(time.monotonic() - started, 1)
    if not pitch.ended:
        pitch.closing()
    outcome = controller.outcome
    steps["match"] = {"pass": outcome is not None and controller.error is None
                      and (args.expect_root is None
                           or Path(worker).resolve() == args.expect_root.resolve() / "pypy" / "pypy.exe"),
                      "worker": worker, "match_wall_s": wall, "error": controller.error,
                      "events": len(outcome.events) if outcome is not None else None,
                      "score": outcome.result.get("score") if outcome is not None else None,
                      "then": type(window.current()).__name__}
    window.leave()
    app.processEvents()
    return done(0 if steps["match"]["pass"] else 1)


if __name__ == "__main__":
    sys.exit(main())
