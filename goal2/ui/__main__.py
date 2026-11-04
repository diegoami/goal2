"""`python -m goal2.ui`: the new window (docs/ui.md).

[designed: T162, #536; T163, #537] It opens S01 while the data folder lacks a file the new window needs, otherwise S02
Start. The portable build's launcher and default stay today's window (goal2/desktop) until T169 switches over.

    python -m goal2.ui [--data-root DIR] [--import FOLDER]
    QT_QPA_PLATFORM=offscreen python -m goal2.ui --screenshot DIR

`--data-root` is the per-user goal2 folder (default: data_setup.user_root(); the data is in its `data`).
`--import FOLDER` imports the data files in FOLDER as S01 does (GOAL.HLP too, when the folder has it), then starts.
`--screenshot DIR` writes PNGs at 1440x900 into DIR and exits: S01, the placeholder home and S22 always; S02 with
two saves, S03, S04 on Holland with its twenty and the name line, S05 with stand-in pages, S06 the manager's desk,
S07 team info, S11 fixtures, S12 tournament and S13 history with the new career, the match day of its first friendly
under PyPy 3.11, on a copy of the career (T167: S14 before and after the match, S15 before kick-off and at half time,
S16 the captain and a set-piece taker, S17 at kick-off and in play, S20 at half time and full time; T180: S18's
substitution opportunity and S19 making substitutions now and showing a refusal, on a 2028 Austria career whose
friendly has an injury at 3′), S11 and S13 again after its first round (the route's
quick friendly), S21's save box, quit question and save question over the desk (T168), and T177's extras: S02's
standalone friendly's country choice, S08's pool search and the desk's manager's name line, when it finds the data
the new window needs (data_setup.WINDOW_MANIFEST) in the --data-root's data folder or, in a checkout, in `.cache/`. It works in a temporary data folder of its own; the help is a stand-in text it writes there
and the bulletin pages are stand-ins labelled so (CLAUDE.md rule 14; the Python route has no bulletins yet, #509).
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
            friendly_shot(window, key, shot)
            key(Qt.Key.Key_N, "n")
            shot("s03-new-game.png")
            key(Qt.Key.Key_Return)
            screen = window.current()
            for _ in range(2):   # Denmark, Germany, Holland: the capture t156-005 [T164, #559]
                key(Qt.Key.Key_Down)
            screen.settle()
            key(Qt.Key.Key_Space)
            shot("s04-players.png")
            key(Qt.Key.Key_Escape)
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
            shot("s06-desk.png")
            extras_shots(window, key, shot)
            key(Qt.Key.Key_Return)   # the cursor starts on team info [T164]
            window.current().settle()
            shot("s07-team-info.png")
            key(Qt.Key.Key_Escape)
            for name in ("s11-fixtures.png", "s12-tournament.png", "s13-history.png"):
                key(Qt.Key.Key_Down)
                key(Qt.Key.Key_Return)
                shot(name)
                key(Qt.Key.Key_Escape)
            pitch_shots(app, window, career, shot)
            bench_shots(app, window, target, shot)
            # After the first round, played by the route's own quick friendly (goal2/desktop/worker.py `play`): S11's
            # round 2 and S13 with the recorded result. [designed: T178]
            from goal2.desktop import worker
            career.state = worker.play(career.state, career.template_bytes)
            window.open_career(career)
            for option, name in ((1, "s11-fixtures-round2.png"), (3, "s13-history-round2.png")):
                desk = window.current()
                desk.highlight(option)
                key(Qt.Key.Key_Return)
                shot(name)
                key(Qt.Key.Key_Escape)
            save_quit_shots(window, key, shot)
        window.leave()
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    return written


def friendly_shot(window, key, shot):
    """S02's standalone friendly (F): Holland chosen, the opponent highlighted, then Esc twice back to S02; nothing is
    played. [designed: owner, §6 item 18; T177]"""
    from PySide6.QtCore import Qt
    key(Qt.Key.Key_F, "f")
    chooser = window.current()
    while chooser.highlighted_country() != 20:   # Holland, 14th in the world
        key(Qt.Key.Key_Down)
    key(Qt.Key.Key_Return)
    key(Qt.Key.Key_Up)
    shot("s02-friendly.png")
    key(Qt.Key.Key_Escape)
    key(Qt.Key.Key_Escape)


def extras_shots(window, key, shot):
    """The desk's extras: S08's pool search ("van" typed after /) and the manager's name line on the desk, each left
    with Esc, so the career is unchanged and the cursor is back on team info. [designed: owner, §6 item 18; T177]"""
    from PySide6.QtCore import Qt
    desk = window.current()
    key(Qt.Key.Key_Space)
    key(Qt.Key.Key_Slash, "/")
    for character in "van":
        key(Qt.Key.Key_A, character)
    shot("s08-pool-search.png")
    key(Qt.Key.Key_Escape)   # clears the search
    key(Qt.Key.Key_Escape)   # the desk
    desk.highlight(next(i for i, o in enumerate(desk.options) if o.text_label.text() == "manager's name"))
    key(Qt.Key.Key_Return)
    for character in "Rinus Michels":
        key(Qt.Key.Key_A, character)
    shot("s06-rename.png")
    key(Qt.Key.Key_Escape)
    desk.highlight(0)


def save_quit_shots(window, key, shot):
    """S21 over the desk: F7's name box with a name typed (the mockup's), F10's question and the save question that
    follows it with the career unsaved; each cancelled after its picture, so nothing is written. [designed: T168]"""
    from PySide6.QtCore import Qt
    key(Qt.Key.Key_F7)
    for character in "Holland after round 1":
        key(Qt.Key.Key_A, character)
    shot("s21-save.png")
    key(Qt.Key.Key_Escape)
    key(Qt.Key.Key_F10)
    shot("s21-quit.png")
    key(Qt.Key.Key_Y, "y")
    shot("s21-save-question.png")
    key(Qt.Key.Key_Escape)


def pitch_shots(app, window, career, shot, limit=600):
    """The match day on a copy of the career, its first friendly from the desk's *play next game*: S14 the round,
    S15 before kick-off, S16 the captain, S17 at kick-off (the sides in their places) and in play (at 17′, the
    mockup's minute), S16 a set-piece taker, S20 at half time, S15 at half time, S20 at full time and S14 after it.
    Each screen is pictured the first time it shows, each stop answered as the player's default (Enter); the whole
    match waited for at most `limit` seconds. The copy is dropped afterwards, so the career is unchanged. The engine
    runs under PyPy 3.11; without it S17 on is not pictured. [designed: T166; T167]"""
    import copy
    import time
    from PySide6.QtCore import Qt
    from goal2.ui.match_day import close_window, play_next_game
    from goal2.ui.s14_round import RoundScreen
    from goal2.ui.s15_match_menu import MenuScreen
    from goal2.ui.s16_choose import ChooseScreen
    from goal2.ui.s17_pitch import PitchScreen
    from goal2.ui.s20_board import BoardScreen
    desk = window.open_career(copy.deepcopy(career))
    opened = play_next_game(window, desk.model)
    if not isinstance(opened, RoundScreen):
        print(f"The match day is not pictured: {opened}", file=sys.stderr)
        window.open_career(career)
        return

    def key(k):
        from PySide6.QtCore import QEvent
        from PySide6.QtGui import QKeyEvent
        window.keyPressEvent(QKeyEvent(QEvent.Type.KeyPress, k, Qt.KeyboardModifier.NoModifier, ""))
        app.processEvents()

    def until(done):
        deadline = time.monotonic() + limit
        while not done() and time.monotonic() < deadline:
            app.processEvents()
            time.sleep(.001)
        return done()
    until(lambda: not opened.arriving)
    shot("s14-round.png")
    key(Qt.Key.Key_Return)
    shot("s15-match-menu.png")
    key(Qt.Key.Key_Return)
    shot("s16-captain.png")
    key(Qt.Key.Key_Return)
    pitch = window.current()
    if not isinstance(pitch, PitchScreen):
        print(f"S17 is not pictured: {getattr(window.current(), 'note', None)}", file=sys.stderr)
        close_window(window)
        window.open_career(career)
        return
    controller = pitch.controller

    def lined_up():
        # Kick-off, as t156-045-kick-off.png: the sides have walked out to their places (at the toss the players
        # share a cell), the kick-off announced.
        frame = controller.display.frame
        return (frame is not None and controller.drawn >= frame["sequence"] and len(pitch.pitch.painted) >= 20
                and any("kick off" in line for line in pitch.lines))
    until(lined_up)
    shot("s17-pitch-kickoff.png")
    taken = set()

    def step():
        """Picture each stop the first time it shows, then answer it as the default (Enter)."""
        screen = window.current()
        if isinstance(screen, PitchScreen):
            if screen.stop_box.open:
                key(Qt.Key.Key_Space)   # [T180] S18's notice (the other side's substitution): any key
                return False
            frame = controller.display.frame
            if "s17" not in taken and frame is not None and frame["minute"] >= 17:
                taken.add("s17")
                shot("s17-pitch.png")
                for _ in range(4):
                    key(Qt.Key.Key_Right)   # the fastest speed for the rest
            return False
        if isinstance(screen, ChooseScreen) and "taker" not in taken:
            taken.add("taker")
            shot("s16-taker.png")
        elif isinstance(screen, BoardScreen) and screen.phase not in taken:
            taken.add(screen.phase)
            shot(f"s20-board-{screen.phase}.png")
        elif isinstance(screen, MenuScreen) and f"menu-{screen.phase}" not in taken:
            taken.add(f"menu-{screen.phase}")
            if screen.phase == "half":
                shot("s15-match-menu-half.png")
        elif isinstance(screen, RoundScreen):
            return True
        key(Qt.Key.Key_Return)
        return False
    if until(step):
        until(lambda: not window.current().arriving)
        shot("s14-round-after.png")
    close_window(window)
    window.open_career(career)


def bench_shots(app, window, target, shot, limit=600):
    """[designed: T180] S18 and S19 on a 2028 Austria career (its first friendly, Austria v Bulgaria, stops for an
    injury at 3′): S18 SUBSTITUTION OPPORTUNITY, S19 making substitutions now (the injured player taken off), then at
    half time a refused pair (the player taken off put on again) on S19. The career is dropped afterwards."""
    import time
    from PySide6.QtCore import QEvent, Qt
    from PySide6.QtGui import QKeyEvent
    from goal2.ui.match_day import close_window, play_next_game
    from goal2.ui.s04_country import new_career
    from goal2.ui.s14_round import RoundScreen
    model = new_career(target, 2, 2028, "K Ees")
    desk = window.open_career(model)
    opened = play_next_game(window, desk.model)
    if not isinstance(opened, RoundScreen):
        print(f"S18 and S19 are not pictured: {opened}", file=sys.stderr)
        return

    def key(k, text=""):
        window.keyPressEvent(QKeyEvent(QEvent.Type.KeyPress, k, Qt.KeyboardModifier.NoModifier, text))
        app.processEvents()

    def until(done):
        deadline = time.monotonic() + limit
        while not done() and time.monotonic() < deadline:
            app.processEvents()
            time.sleep(.001)
        return done()
    until(lambda: not opened.arriving)
    for _ in range(3):                      # S14, S15 play, S16 the captain
        key(Qt.Key.Key_Return)
    state = {"fast": False, "off": None}

    def outfield(answer, words):
        return [w for w in words if answer.position(w) != 0]

    def select(screen, word):
        words = screen.answer.words()
        while words[screen.row] != word:
            key(Qt.Key.Key_Down if words.index(word) > screen.row else Qt.Key.Key_Up)
        key(Qt.Key.Key_Return)

    def play_on(menu):
        while menu.highlighted() is not menu.play:
            key(Qt.Key.Key_Down)
        key(Qt.Key.Key_Return)

    def step():
        screen = window.current()
        kind = type(screen).__name__
        if kind == "PitchScreen":
            if not state["fast"]:
                state["fast"] = True
                for _ in range(4):
                    key(Qt.Key.Key_Right)
            if screen.stop_box.open:
                if screen.stop_box.kind == "substitution" and state["off"] is None:
                    shot("s18-match-stop.png")
                key(Qt.Key.Key_Space)
            return False
        if kind == "MenuScreen":
            if screen.phase == "stop" and state["off"] is None:
                key(Qt.Key.Key_Space)       # players: the bench
            else:
                play_on(screen)
            return False
        if kind == "BenchScreen":
            answer = screen.answer
            if screen.mode == "refused":
                shot("s19-bench-refused.png")
                return True
            if answer.context == "substitution" and state["off"] is None:
                injured = [w for w in answer.eleven if w in answer.injured][0]
                keeper = answer.position(injured) == 0
                select(screen, injured)
                select(screen, next(w for w in answer.bench if (answer.position(w) == 0) == keeper))
                shot("s19-bench.png")
                state["off"] = injured
            elif answer.context == "half_time" and state["off"] in answer.bench:
                select(screen, outfield(answer, answer.eleven)[1])
                select(screen, state["off"])
            key(Qt.Key.Key_Escape)
            return False
        if kind == "BoardScreen":
            key(Qt.Key.Key_Escape if screen.phase == "half" else Qt.Key.Key_Return)
            return False
        key(Qt.Key.Key_Return)
        return isinstance(screen, RoundScreen) and screen.after is not None
    until(step)
    close_window(window)


def import_data(folder, data_root=None) -> int:
    """`--import FOLDER`: the new window's own import (S01's, data_setup.WINDOW_MANIFEST, GOAL.HLP when the folder
    has it); 0 once imported, else 1 with data_setup's plain words. [designed: T163 6a]"""
    from goal2.desktop import data_setup
    target = data_setup.paths(data_root)
    try:
        copied = data_setup.import_folder(folder, target, data_setup.WINDOW_MANIFEST)
    except data_setup.SetupError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    print(f"Imported {', '.join(copied) or 'nothing new'} into {target.data}.")
    return 0


def run_window(data_root=None) -> int:
    from PySide6.QtWidgets import QApplication
    from goal2.desktop import data_setup
    from goal2.ui import theme
    from goal2.ui.window import Window
    app = QApplication.instance() or QApplication(sys.argv[:1])
    theme.install(app)
    window = Window(data_setup.paths(data_root))
    window.start()
    window.show()
    return app.exec()


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="python -m goal2.ui", description="goal2's new window (docs/ui.md)")
    parser.add_argument("--data-root", type=Path, help="the per-user goal2 folder (default: the user's)")
    parser.add_argument("--screenshot", type=Path, metavar="DIR", help="write PNGs of the screens and exit")
    parser.add_argument("--import", dest="folder", type=Path, metavar="FOLDER",
                        help="import the data files in FOLDER (GOAL.HLP too, when it is there), then start")
    args = parser.parse_args(argv)
    if args.screenshot is not None:
        for path in screenshots(args.screenshot, args.data_root):
            print(path)
        return 0
    if args.folder is not None and import_data(args.folder, args.data_root):
        return 1
    return run_window(args.data_root)


if __name__ == "__main__":
    raise SystemExit(main())
