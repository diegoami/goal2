"""[designed: owner, 2026-11-13, #705; T225] The v0.1 player's path, offscreen, for the packaged smoke
(tools/portable/smoke.py): what `goal2.cmd` does on a player's first start, from their own GOAL.EXE and GOAL.DAT.

1. First start: a fresh per-user folder (LOCALAPPDATA on Windows, HOME elsewhere, set to a folder in --at), so the
   desktop's player defaults (`goal2.desktop.__main__._player_defaults`, what `goal2.cmd` with no argument runs) find
   no data and open the import dialog (`data_setup.make_dialog`); the dialog's Choose folder is answered with a stand-in
   for the player's goal install (GOAL.EXE and GOAL.DAT copied from --cache into --at, outside the build) and imports
   it (T222's import). The defaults then name the imported GOAL.EXE as the core's boot (`--core-boot`).
2. A new career on Launch (`goal2.desktop.launch.LaunchWindow`, the core route): the original's new game booted from
   that GOAL.EXE (CoreNewGame, `Core.boot_exe`), a country chosen in its browser, a manager's name, Start, the
   bulletins, then the main window (`window_for`, CoreWindow).
3. One watched match to full time: the desk's *play next game*, the original's own captain and Watch (C), the match
   in the pitch window (goal2/desktop/core_viewer.py, the pygame viewer, SDL's dummy driver), every stop answered by
   the round page's own controls (the computer's taker, no replay, play on at half time, the notice let pass, the
   summary not saved), until the round returns to the manager menu.

[designed: T225] The watched match is not paced (CoreModel.pacing off): T223's pacing waits the original's delays in
wall time, a whole match's worth, which a smoke does not need; the steps and their order are the window's.
It writes what it saw; the exit status is 1 when a step fails.

    python smoke_core.py --cache DIR --at DIR --out FILE [--expect-root DIR]

With --expect-root, goal2 must be imported from DIR's `python/`: the packaged run may not reach the source tree.
"""
import argparse
import json
import os
import platform
import shutil
import sys
import time
from pathlib import Path

COUNTRY = 20            # [designed: T225] Holland, as test_core_patches_t122's new career; any country would do
MANAGER = "K Ees"


def main(argv=None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cache", type=Path, required=True)
    parser.add_argument("--at", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--expect-root", type=Path)
    parser.add_argument("--limit", type=float, default=2400, help="seconds the match may take")
    args = parser.parse_args(argv)
    at = args.at.resolve()
    home = at / "user home ä"
    home.mkdir(parents=True)
    os.environ["LOCALAPPDATA" if sys.platform.startswith("win") else "HOME"] = str(home)
    for name, value in (("QT_QPA_PLATFORM", "offscreen"), ("SDL_VIDEODRIVER", "dummy"), ("SDL_AUDIODRIVER", "dummy")):
        os.environ.setdefault(name, value)
    import goal2
    where = Path(goal2.__file__).resolve()
    result = {"ui_python": f"{platform.python_implementation()} {platform.python_version()}",
              "ui_executable": sys.executable, "goal2": str(where), "steps": {}}
    steps = result["steps"]

    def done(code):
        result["pass"] = code == 0
        args.out.write_text(json.dumps(result, indent=1, ensure_ascii=False) + "\n")
        return code

    if args.expect_root is not None:
        root = args.expect_root.resolve()
        steps["from_the_build"] = {"pass": root / "python" in where.parents}
        if not steps["from_the_build"]["pass"]:
            return done(1)

    # 1. the first start: no data folder, the import dialog, the player's goal install
    from goal2.desktop import data_setup
    from goal2.desktop.__main__ import _player_defaults
    from goal2.core.exeboot import is_exe
    offered = at / "goal install ä"
    offered.mkdir()
    for name in (data_setup.BOOT_NAME, data_setup.DATA_NAME):
        shutil.copyfile(args.cache / name, offered / name)
    target = data_setup.paths()
    asked = []

    def dialog(paths):
        dlg = data_setup.make_dialog(paths, choose=lambda: str(offered))
        asked.append(dlg.intro.text())
        return dlg.choose_and_import()

    from PySide6.QtWidgets import QApplication
    app = QApplication.instance() or QApplication(sys.argv[:1])
    # An exception in a Qt slot is printed and the window carries on, which a player sees as a stuck page: the smoke
    # records it and fails.
    raised = result["exceptions"] = []
    shown = sys.excepthook

    def hook(kind, value, tb):
        import traceback
        raised.append("".join(traceback.format_exception(kind, value, tb))[-3000:])
        shown(kind, value, tb)
    sys.excepthook = hook
    before = data_setup.complete(target.data)
    data_setup.qt_dialog = dialog            # the dialog's own code, answered without a modal loop
    launch_args = argparse.Namespace(template=None, data=None, save=None, resume=None, country=None, core=None,
                                     core_boot=None)
    status = _player_defaults(launch_args)
    imported = sorted(p.name for p in target.data.iterdir()) if target.data.is_dir() else []
    boot = launch_args.core_boot
    steps["first_run_import"] = {
        "pass": status is None and not before and len(asked) == 1 and home in target.root.parents
                and boot == target.boot and boot.is_file() and is_exe(boot.read_bytes())
                and launch_args.data == target.goal_dat and launch_args.save == target.save
                and imported == sorted((data_setup.BOOT_NAME, data_setup.DATA_NAME)),
        "complete_before": before, "dialogs": len(asked), "data": imported, "core_boot": str(boot),
        "save": str(launch_args.save)}
    if not steps["first_run_import"]["pass"]:
        return done(1)

    # 2. a new career on Launch, booted from the imported GOAL.EXE
    from PySide6.QtCore import Qt
    from goal2.desktop.launch import LaunchWindow
    from goal2.desktop.window import window_for
    opened = []
    started = time.monotonic()
    launch = LaunchWindow(launch_args.data, None, launch_args.save, lambda model: opened.append(model),
                          core_boot=launch_args.core_boot)
    launch.show()
    launch.show_page(1)
    app.processEvents()
    ids = [launch.country_list.item(i).data(Qt.ItemDataRole.UserRole) for i in range(launch.country_list.count())]
    launch.country_list.setCurrentRow(ids.index(COUNTRY))
    launch.preview()
    launch.review()
    launch.manager_name.setText(MANAGER)
    launch.start.click()
    app.processEvents()
    bulletins = len(getattr(launch, "bulletins", []) or [])
    for _ in range(bulletins + 1):
        if opened:
            break
        launch.bulletin_next.click()
        app.processEvents()
    model = opened[0] if opened else None
    steps["new_career"] = {
        "pass": model is not None and launch.core_new.boot_path == boot and model.core.wait.kind == "manager-menu"
                and not launch_args.save.exists(),
        "error": launch.review_error.text(), "bulletins": bulletins, "s": round(time.monotonic() - started, 1),
        "at": model.core.wait.kind if model is not None else None}
    if not steps["new_career"]["pass"]:
        return done(1)

    # 3. one watched match, in the pitch window, to full time and back to the manager menu
    window = window_for(model)
    window.show()
    app.processEvents()
    model.pacing = False
    r = window.core_round
    stops, live = [], [0]
    finished = r.finished

    def seen(name, answer):
        kind, value = answer
        stop = value.get("stop") if kind == "done" and isinstance(value, dict) else kind
        if stop == "live":
            live[0] += 1
        elif not stops or stops[-1] != stop:
            stops.append(stop)
        return finished(name, answer)
    r.finished = seen
    started = time.monotonic()
    window.core_routes["play next game"].click()
    clicked = []

    def click(button):
        if button.isVisible() and button.isEnabled():
            clicked.append(button.text().split("\n")[0])
            button.click()
            return True
        return False
    viewers = set()
    while time.monotonic() - started < args.limit:
        app.processEvents()
        if r.viewer is not None:
            viewers.add(id(r.viewer))
        if window.model.core.stopped is not None or raised:
            break
        if window.core_jobs.busy:
            time.sleep(.002)
            continue
        if not model.in_round and "full-time" in stops and model.core.wait.kind == "manager-menu":
            break
        view = r.views.currentIndex()
        if view == 0:
            click(r.computer)
        elif view == 1:
            click(r.bench.play)
        elif view == 2:
            click(r.page_next)
        elif view == 3:
            click(r.notice_pass)
        elif view == 5:
            click(r.skip_summary)
        elif view == r.takers.choice_index:
            click(r.takers.computer)
        elif view == r.takers.preview_index:
            click(r.takers.back)
        elif view == r.replays.index:
            click(r.replays.skip)
        time.sleep(.002)
    wall = round(time.monotonic() - started, 1)
    from goal2.core import views
    settled = model.core.stopped is None and model.core.wait is not None   # [T227] a raise can leave a step running
    board = views.board(model.state) if settled else None
    steps["watched_match"] = {
        "pass": model.core.stopped is None and not raised and "full-time" in stops and live[0] > 100 and bool(viewers)
                and settled and not model.in_round and model.core.wait.kind == "manager-menu"
                and ("match-live", ord("r")) not in model.driver.log,
        "match_wall_s": wall, "live_poses": live[0], "stops": stops, "viewers": len(viewers),
        "at": model.core.wait.kind if model.core.wait is not None else None, "stopped": None if model.core.stopped is None else str(model.core.stopped), "status": window.status.text(),
        "clicked": clicked[-40:], "score": (board or {}).get("score")}
    window.close()
    app.processEvents()
    return done(0 if steps["watched_match"]["pass"] else 1)


if __name__ == "__main__":
    sys.exit(main())
