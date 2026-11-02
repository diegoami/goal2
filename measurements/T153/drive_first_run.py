"""[designed: T153] Done-when 2's playtest driven headlessly: the desktop's own entry (`-m goal2.desktop`, through the
portable launcher when --build-root is given), offscreen, its widgets operated by a timer in the same process.

    python drive_first_run.py PHASE --owner DIR --out FILE [--build-root ROOT] [--country-row N] [--year 1990|1992]

PHASE, each a fresh process (so "quit, restart" is real):
- first: no arguments. The import dialog must appear; Choose folder is clicked twice, first with an empty folder (its
  refusal is recorded), then with the owner's data folder DIR (the system's folder chooser answers with it). Then
  Launch (the core route): New career, a country, Review, the manager's name, Start career, the bulletins, the main
  window. One round is then played *watched* through the window's model (CoreModel.round_step, the calls the window's
  round page makes; the pygame pitch viewer is not opened), answering each stop as goal2/core/cycle_player.py does,
  declining replays and the DOS summary. Then the Save page's Save button (the default save path), and the window
  is closed.
- second: no arguments. The import dialog must not appear; Launch must.
- resume: `--resume <the default save>`. The main window must open the saved core, its memory equal to the one saved.
- launch-resume: no arguments; Launch's Saved career panel must name the core save, and its Resume button must open
  the main window over it (#518/#519), its memory equal to the one saved.

Nothing of the original is in this file or its output: only names, digests, sizes and the original's own words
for the country and the result.
"""
import argparse
import hashlib
import json
import os
import runpy
import sys
import tempfile
import time
import traceback
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")


def run_desktop(argv, build_root):
    """`-m goal2.desktop argv`, through the portable launcher when there is a build."""
    if build_root is not None:
        sys.path.insert(0, str(build_root))
        import goal2_launch
        call = lambda: goal2_launch.main(argv, root=build_root)
    else:
        def call():
            sys.argv = ["goal2.desktop"] + list(argv)
            return runpy.run_module("goal2.desktop", run_name="__main__", alter_sys=True)
    try:
        call()
    except SystemExit as exc:
        return exc.code
    return None


def windows():
    from PySide6.QtWidgets import QApplication
    return [w for w in QApplication.topLevelWidgets() if w.isVisible()]


def find(kind):
    return next((w for w in windows() if type(w).__name__ == kind or w.objectName() == kind), None)


def play_round(model, log, budget=60000):
    """One round from the manager menu, watched, through the model's round steps; returns the stops seen."""
    from goal2.core import views
    stops, steps = {}, 0
    state = model.round_step("round_start", True)
    while model.core.wait.kind != "manager-menu":
        steps += 1
        if steps > budget:
            raise RuntimeError(f"the round did not end in {budget} steps")
        stop = state["stop"]
        stops[stop] = stops.get(stop, 0) + 1
        kind = model.core.wait.kind
        if stop == "live":
            state = model.round_step("live_step")
        elif stop == "captain":
            state = model.round_step("kick_off")
        elif stop in ("replay", "replay-save"):
            state = model.round_step("replay", False)
        elif stop == "summary-save":
            state = model.round_step("summary_done")
        elif stop == "notice":
            state = model.round_step("notice", False)
        elif stop == "full-time":
            state = model.round_step("finish")
        elif stop in ("half-time", "stoppage", "pause", "extra-time-start", "extra-time-half"):
            state = model.round_step("play_on")
        elif stop in ("round-paused", "bulletin-achievement", "bulletin-congratulations"):
            state = model.round_step("round_continue")
        elif stop == "shootout-announcement":
            state = model.round_step("shootout_start")
        elif stop == "shootout-order":
            pick = next(r for r in state["order"]["players"] if r["available"] and r["rank"] is None)
            state = model.round_step("shootout_pick", pick["player"])
        elif stop in ("taker", "taker-pitch"):
            state = model.round_step("taker_key", "c" if stop == "taker" else "\r")
        else:
            raise RuntimeError(f"unhandled stop {stop} at {kind}")
    log["round"] = {"steps": steps, "stops": stops, "pages": len(state.get("pages") or [])}
    log["desk_after_round"] = {k: v for k, v in views.desk(model.state).items() if isinstance(v, (str, int, bool))}


def main():
    p = argparse.ArgumentParser()
    p.add_argument("phase", choices=("first", "second", "resume", "launch-resume"))
    p.add_argument("--owner", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--build-root", type=Path)
    p.add_argument("--country-row", type=int, default=0)
    p.add_argument("--year", type=int, default=1992)
    p.add_argument("--timeout", type=int, default=3600)
    args = p.parse_args()
    from PySide6.QtCore import QTimer
    from PySide6.QtWidgets import QApplication, QFileDialog
    app = QApplication.instance() or QApplication(sys.argv[:1])
    from goal2.desktop import data_setup
    target = data_setup.paths()
    log = {"phase": args.phase, "python": sys.version, "executable": sys.executable, "platform": sys.platform,
           "data_folder": str(target.data), "saves_folder": str(target.saves), "events": [], "errors": []}
    import goal2
    log["goal2_from"] = str(Path(goal2.__file__).resolve().parent)
    log["engine_python"] = os.environ.get("GOAL2_ENGINE_PYTHON")
    log["complete_before"] = data_setup.complete(target.data)
    empty = Path(tempfile.mkdtemp(prefix="goal2-t153-empty-"))
    answers = [str(empty), str(args.owner)]
    QFileDialog.getExistingDirectory = staticmethod(lambda *a, **k: answers.pop(0) if answers else "")
    shown = []
    real_dialog = data_setup.qt_dialog

    def dialog(t):
        shown.append(time.time())
        return real_dialog(t)
    data_setup.qt_dialog = dialog
    started = time.monotonic()
    stage = {"name": "start"}

    def event(text, **extra):
        log["events"].append(dict(t=round(time.monotonic() - started, 2), what=text, **extra))
        print(log["events"][-1], flush=True)

    def robot():
        try:
            step()
        except Exception as exc:
            log["errors"].append(traceback.format_exc())
            print(traceback.format_exc(), flush=True)
            for w in windows():
                w.close()
            app.quit()
        if time.monotonic() - started > args.timeout:
            log["errors"].append("timeout")
            app.quit()

    def step():
        name = stage["name"]
        setup = find("dataSetup")
        if setup is not None and name in ("start", "refused"):
            if name == "start":
                event("import dialog shown", intro=setup.intro.text())
                setup.choose_button.click()
                event("chose an empty folder", status=setup.status.text())
                log["refusal"] = setup.status.text()
                stage["name"] = "refused"
            else:
                setup.choose_button.click()
                event("chose the owner's data folder", folder=str(args.owner))
                stage["name"] = "imported"
            return
        launch = find("LaunchWindow")
        if launch is not None and args.phase == "second" and name == "start":
            event("Launch shown", dialog_shown=bool(shown), saved=launch.saved_country.text(),
                  saved_error=launch.error.text())
            stage["name"] = "done";launch.close();return
        if launch is not None and args.phase == "first" and name in ("start", "imported"):
            event("Launch shown", saved=launch.saved_country.text())
            launch.new_career.click()
            launch.start_year.setCurrentIndex(launch.start_year.findData(args.year))
            launch.country_list.setCurrentRow(args.country_row)
            launch.preview()
            launch.to_review.click()
            country = launch.review_fields["country"].text()
            launch.manager_name.setText("T Fiftythree")
            event("review", country=country, year=args.year)
            log["country"] = country
            launch.start.click()
            event("career started", error=launch.review_error.text())
            stage["name"] = "bulletins";return
        if launch is not None and name == "bulletins" and launch.pages.currentIndex() == 4:
            launch.bulletin_next.click();event("bulletin page passed");return
        if launch is not None and args.phase == "launch-resume" and name == "start":
            log["launch_saved"] = {"country": launch.saved_country.text(), "resume": launch.resume.text(),
                                   "error": launch.error.text()}
            event("Launch shown", dialog_shown=bool(shown), **log["launch_saved"])
            stage["name"] = "resuming";launch.resume.click();return
        core = find("CoreWindow")
        if core is not None and args.phase == "first" and name in ("bulletins", "imported"):
            model = core.model
            event("main window", title=core.title.text(), save_path=str(model.save_path))
            play_round(model, log)
            core.refresh();core.refresh_round_controls()
            event("round played watched", **log["round"])
            core.navigate(4)
            core.save.click()
            event("saved", status=core.status.text())
            saved = Path(core.path.text())
            log["save"] = {"path": str(saved), "bytes": saved.stat().st_size,
                           "sha256": hashlib.sha256(saved.read_bytes()).hexdigest(),
                           "memory_sha256": model.memory_sha256()}
            stage["name"] = "done";core.close();return
        if core is not None and (args.phase, name) in (("resume", "start"), ("launch-resume", "resuming")):
            log["resumed"] = {"memory_sha256": core.model.memory_sha256(), "save_path": str(core.model.save_path),
                              "title": core.title.text()}
            event("resumed", **log["resumed"])
            stage["name"] = "done";core.close();return

    timer = QTimer();timer.setInterval(200);timer.timeout.connect(robot);timer.start()
    argv = [] if args.phase != "resume" else ["--resume", str(target.save)]
    log["argv"] = argv
    log["exit"] = run_desktop(argv, args.build_root)
    try:
        timer.stop()
    except RuntimeError:                 # the desktop's teardown (app.shutdown) has deleted it
        pass
    log["dialog_shown"] = len(shown)
    log["complete_after"] = data_setup.complete(target.data)
    log["data_files"] = sorted(p.name for p in target.data.iterdir()) if target.data.is_dir() else []
    log["seconds"] = round(time.monotonic() - started, 1)
    log["stage"] = stage["name"]
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(log, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: log[k] for k in ("phase", "exit", "stage", "dialog_shown", "complete_after", "errors")}))
    return 0 if stage["name"] == "done" and not log["errors"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
