"""[designed: T158] The PySide6 candidate (today's toolkit): S06 and S16 to kick-off as native Qt widgets.

    python tools/tech_probe/qt_probe.py [--quit-after S] [--screenshot DIR]

Native widgets (QLabel, QFrame) styled by one style sheet in the design's palette and font, so focus, mouse and
the accessibility tree see real widgets; the pitch is one painted widget (QPainter), animated at 60 Hz. The page
is the design's fixed 1440x900; goal2's FixedPage (T101) shows how a whole page is scaled in Qt. Prints
`READY <s>` (seconds since the probe started) after the window's first paint. Throwaway.
"""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

START = time.perf_counter()
sys.path.insert(0, str(Path(__file__).resolve().parent))
import common  # noqa: E402
import screens  # noqa: E402
from PySide6.QtCore import Qt, QTimer, QEvent, QRectF, QPointF  # noqa: E402
from PySide6.QtGui import QFont, QFontDatabase, QPainter, QPen, QColor  # noqa: E402
from PySide6.QtWidgets import QApplication, QWidget, QFrame, QLabel, QHBoxLayout, QVBoxLayout, QGridLayout  # noqa: E402

P = screens.PALETTE
FAMILY = "PxPlus IBM VGA 8x16"
STYLE = f"""
* {{ font-family: "{FAMILY}"; font-size: 16px; color: {P['bright']}; background: transparent; }}
#root {{ background: {P['ground']}; }}
#top, #keys {{ border-color: {P['frame_dark']}; border-style: solid; }}
#top {{ border-width: 0 0 2px 0; }} #keys {{ border-width: 2px 0 0 0; }}
.box {{ border: 2px solid {P['frame_dark']}; }}
.title {{ color: {P['cyan']}; }}
.brand {{ color: {P['cyan']}; font-size: 32px; }}
.big {{ font-size: 32px; }}
.sel {{ color: {P['yellow']}; }}
.muted {{ color: {P['normal']}; }}
.label {{ color: {P['brown']}; }}
.hint {{ color: {P['magenta']}; }}
.banner {{ color: {P['light_red']}; }}
.item {{ border: 2px solid {P['frame_dark']}; }}
.item[on="true"], .row[on="true"], .primary {{ background: {P['highlight']}; color: #000; border-color: {P['highlight']}; }}
.item[on="true"] QLabel, .row[on="true"] QLabel, .primary QLabel {{ color: #000; }}
.kbd {{ border: 1px solid {P['frame_dark']}; padding: 1px 7px; color: {P['bright']}; }}
.primary .kbd, .item[on="true"] .kbd {{ border-color: #000; color: #000; }}
"""


def label(text, cls="", parent=None):
    w = QLabel(text, parent)
    if cls:
        w.setProperty("class", cls)
    return w


def colour(text, key):
    w = QLabel(text)
    w.setStyleSheet(f"color: {P[key]};")
    return w


class Clickable(QFrame):
    def __init__(self, on_click, name):
        super().__init__()
        self.on_click = on_click
        self.setAccessibleName(name)
        self.setCursor(Qt.PointingHandCursor)
        self.setFocusPolicy(Qt.NoFocus)

    def mousePressEvent(self, event):
        self.on_click()


def box(title, *widgets, width=None):
    f = QFrame()
    f.setProperty("class", "box")
    v = QVBoxLayout(f)
    v.setContentsMargins(16, 14, 16, 14)
    v.setSpacing(8)
    if title:
        v.addWidget(label(title.upper(), "title"))
    for w in widgets:
        v.addWidget(w) if isinstance(w, QWidget) else v.addLayout(w)
    if width:
        f.setFixedWidth(width)
    return f


def kv(pairs):
    g = QGridLayout()
    g.setHorizontalSpacing(16)
    g.setVerticalSpacing(4)
    for i, (k, v) in enumerate(pairs):
        g.addWidget(label(k, "label"), i, 0)
        g.addWidget(label(str(v)), i, 1)
    g.setColumnStretch(1, 1)
    return g


def bars(rows):
    g = QGridLayout()
    g.setHorizontalSpacing(10)
    g.setVerticalSpacing(5)
    for i, (name, value, word) in enumerate(rows):
        g.addWidget(label(name), i, 0)
        g.addWidget(Bar(value / 9, f"{name} {word}"), i, 1)
        g.addWidget(label(word, "" if not word.isdigit() else "muted"), i, 2)
    g.setColumnStretch(1, 1)
    return g


class Bar(QWidget):
    """A skill or characteristic bar: filled grey, empty magenta, as the original's card."""
    def __init__(self, fraction, name):
        super().__init__()
        self.fraction = min(1.0, fraction)
        self.setFixedHeight(13)
        self.setMinimumWidth(120)
        self.setAccessibleName(name)

    def paintEvent(self, event):
        p = QPainter(self)
        p.fillRect(self.rect(), QColor(P["bar_empty"]))
        p.fillRect(0, 0, int(self.width() * self.fraction), self.height(), QColor(P["bar"]))


def role(line, code):
    w = colour(code, screens.LINE_COLOUR[line])
    w.setFixedWidth(22)
    w.setAlignment(Qt.AlignCenter)
    return w


class Pitch(QWidget):
    """The kick-off: lines, the 22 role codes, the moving ball; painted, 60 frames a second."""
    def __init__(self):
        super().__init__()
        self.setFixedSize(1000, 560)
        self.setAccessibleName("Pitch: Norway v Holland, kick-off")
        self.timer = QTimer(self)
        self.timer.setInterval(16)
        self.timer.timeout.connect(self.update)
        self.timer.start()

    def paintEvent(self, event):
        p = QPainter(self)
        w, h = self.width(), self.height()
        p.fillRect(0, 0, w, h, QColor("#000"))
        pen = QPen(QColor(P["frame"]), 2)
        p.setPen(pen)
        p.drawRect(1, 1, w - 3, h - 3)
        p.drawLine(w // 2, 0, w // 2, h)
        p.drawRect(0, h // 4, int(w * .15), h // 2)
        p.drawRect(w - int(w * .15), h // 4, int(w * .15), h // 2)
        p.drawEllipse(QPointF(w / 2, h / 2), 60, 60)
        font = QFont(FAMILY)
        font.setPixelSize(32)
        font.setStyleStrategy(QFont.NoAntialias)
        p.setFont(font)
        for side, key in ((screens.AWAY, "away"), (screens.HOME, "home")):
            p.setPen(QColor(P[key]))
            for x, y, code in side:
                p.drawText(QRectF(x * w / 100 - 15, y * h / 100 - 16, 30, 32), Qt.AlignCenter, code)
        bx, by = screens.ball(time.perf_counter() - START)
        p.fillRect(QRectF(bx * w / 100 - 4, by * h / 100 - 4, 8, 8), QColor("#fff"))


class Window(QWidget):
    def __init__(self):
        super().__init__()
        self.setObjectName("root")
        self.setFixedSize(screens.W, screens.H)
        self.setWindowTitle("GOAL2 prototype (PySide6)")
        self.setFocusPolicy(Qt.StrongFocus)
        self.screen, self.cursor, self.pick, self.notice = "desk", 0, screens.COMPUTER_PICK, ""
        self.body = QVBoxLayout(self)
        self.body.setContentsMargins(0, 0, 0, 0)
        self.page = None
        self.render()

    # ---- frame
    def top(self, who, banner=""):
        f = QFrame()
        f.setObjectName("top")
        f.setFixedHeight(64)
        h = QHBoxLayout(f)
        h.setContentsMargins(24, 0, 24, 0)
        h.setSpacing(28)
        h.addWidget(label("GOAL2", "brand"))
        h.addWidget(label(who))
        h.addStretch(1)
        if banner:
            h.addWidget(label(banner, "banner"))
        return f

    def keys(self, items, primary, on_enter):
        f = QFrame()
        f.setObjectName("keys")
        f.setFixedHeight(70)
        h = QHBoxLayout(f)
        h.setContentsMargins(24, 0, 24, 0)
        h.setSpacing(22)
        for ks, text in items:
            for k in ks:
                h.addWidget(label(k, "kbd"), 0, Qt.AlignVCenter)
            h.addWidget(label(text, "hint"))
        if self.notice:
            h.addWidget(colour(self.notice, "yellow"))
        h.addStretch(1)
        button = Clickable(on_enter, f"{primary} (Enter)")
        button.setProperty("class", "primary")
        b = QHBoxLayout(button)
        b.setContentsMargins(22, 12, 22, 12)
        b.addWidget(label(primary))
        b.addWidget(label("Enter", "kbd"))
        h.addWidget(button, 0, Qt.AlignVCenter)
        return f

    # ---- screens
    def desk(self):
        page = QWidget()
        v = QVBoxLayout(page)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(0)
        v.addWidget(self.top("manager's desk", "2028 European Championship · QUALIFYING"))
        main = QHBoxLayout()
        main.setContentsMargins(24, 18, 24, 18)
        main.setSpacing(18)
        left = QVBoxLayout()
        left.setSpacing(14)
        left.addWidget(box("Manager", kv([("name", "K Ees"), ("rating", "unknown")]), width=420))
        left.addWidget(box("Team", label("Holland", "big"), kv([("world", 14), ("Europe", 3)]), width=420))
        left.addWidget(box("Next opponents", label("Norway", "big sel"),
                           kv([("world", 32), ("Europe", 18), ("match", "friendly · away")]), width=420))
        left.addWidget(box("Managers", label("1 · K Ees (Holland)"), width=420))
        left.addStretch(1)
        main.addLayout(left)
        middle = QVBoxLayout()
        middle.setSpacing(10)
        for i, (text, sub, key) in enumerate(screens.MENU):
            item = Clickable(lambda i=i: self.click_menu(i), text)
            item.setProperty("class", "item")
            item.setProperty("on", "true" if i == self.cursor else "false")
            h = QHBoxLayout(item)
            h.setContentsMargins(16, 10, 16, 10)
            h.addWidget(label(text))
            if sub:
                h.addWidget(label(sub, "muted"))
            h.addStretch(1)
            if key:
                h.addWidget(label(key, "kbd"))
            middle.addWidget(item)
        note = label("Use ↑↓ to find an option, Enter to select it. Your own matches are watched: play next game "
                     "leads to the match menu, the captain and the pitch.", "muted")
        note.setWordWrap(True)
        middle.addWidget(note)
        middle.addStretch(1)
        main.addLayout(middle, 1)
        strip = QVBoxLayout()
        strip.setSpacing(2)
        for i, (line, code, name) in enumerate(screens.SQUAD):
            if i == 11:
                strip.addSpacing(10)
            h = QHBoxLayout()
            h.addWidget(role(line, code))
            h.addWidget(label(name), 1)
            strip.addLayout(h)
        strip.addStretch(1)
        main.addWidget(box("Holland", strip, width=280))
        v.addLayout(main, 1)
        v.addWidget(self.keys([(["F1"], "help"), (["F3"], "load goal"), (["F4"], "load summary"), (["F7"], "save"),
                               (["F10"], "quit"), (["T"], "team tactics"), (["↑", "↓"], "choose")],
                              screens.MENU_HINT[self.cursor], self.activate))
        return page

    def captain(self):
        c = screens.card(self.pick)
        page = QWidget()
        v = QVBoxLayout(page)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(0)
        v.addWidget(self.top("Norway v Holland · captain"))
        main = QVBoxLayout()
        main.setContentsMargins(24, 18, 24, 18)
        main.setSpacing(14)
        head = QHBoxLayout()
        head.addWidget(label("Choose your captain to kick off", "big sel"))
        why = label("The match starts as soon as a captain is chosen. The highlight starts on the computer's pick. "
                    "Enter: the highlighted player · C: computer select · no key: the computer's pick stands after "
                    "the original's wait.", "muted")
        why.setWordWrap(True)
        head.addWidget(why, 1)
        main.addWidget(box("", head))
        row = QHBoxLayout()
        row.setSpacing(18)
        name = QHBoxLayout()
        name.addWidget(role(c["line"], c["code"]))
        name.addWidget(label(c["name"], "big"))
        name.addWidget(label(c["facts"], "muted"))
        name.addStretch(1)
        name.addWidget(label("ready to play"))
        cols = QHBoxLayout()
        cols.setSpacing(24)
        skills = QVBoxLayout()
        skills.addWidget(label("SKILLS", "title"))
        skills.addLayout(bars([(n, v, str(v)) for n, v in c["skills"]]))
        skills.addStretch(1)
        cols.addLayout(skills, 1)
        right = QVBoxLayout()
        right.addWidget(label("TACTICS", "title"))
        right.addLayout(kv(c["tactics"]))
        right.addWidget(label("CHARACTERISTICS", "title"))
        right.addLayout(bars([(n, v + 1, w) for n, v, w in c["characteristics"]]))
        right.addStretch(1)
        holder = QWidget()
        holder.setLayout(right)
        holder.setFixedWidth(420)
        cols.addWidget(holder)
        row.addWidget(box("", name, label(f"position {c['position']} · club position {c['position']} · cards none",
                                          "muted"), cols), 1)
        eleven = QVBoxLayout()
        eleven.setSpacing(0)
        for i, (line, code, nm) in enumerate(screens.ELEVEN):
            r = Clickable(lambda i=i: self.click_player(i), nm)
            r.setProperty("class", "row")
            r.setProperty("on", "true" if i == self.pick else "false")
            h = QHBoxLayout(r)
            h.setContentsMargins(10, 5, 10, 5)
            h.addWidget(role(line, code) if i != self.pick else label(code))
            h.addWidget(label(nm), 1)
            eleven.addWidget(r)
        eleven.addStretch(1)
        row.addWidget(box("Holland's eleven", eleven, width=300))
        main.addLayout(row, 1)
        v.addLayout(main, 1)
        v.addWidget(self.keys([(["↑", "↓"], "player"), (["C"], "computer select"), (["Esc"], "desk (prototype only)")],
                              "Captain: kick off", lambda: self.go("kickoff")))
        return page

    def kickoff(self):
        page = QWidget()
        v = QVBoxLayout(page)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(0)
        v.addWidget(self.top("watching · Norway v Holland"))
        main = QVBoxLayout()
        main.setContentsMargins(24, 18, 24, 18)
        main.setSpacing(14)
        score = QHBoxLayout()
        score.setSpacing(18)
        home = colour("Norway", "home")
        home.setProperty("class", "big")
        score.addWidget(home)
        score.addWidget(label("0", "big"))
        score.addWidget(label("0", "big"))
        score.addWidget(label("Holland", "big"))
        score.addSpacing(30)
        score.addWidget(label("1′", "big"))
        score.addWidget(label("FRIENDLY", "muted"))
        score.addStretch(1)
        last = QVBoxLayout()
        for c in screens.COMMENTARY:
            last.addWidget(label(c[3:]))
        score.addLayout(last)
        main.addWidget(box("", score))
        row = QHBoxLayout()
        row.setSpacing(18)
        row.addWidget(Pitch(), 0, Qt.AlignTop)
        comm = QVBoxLayout()
        for c in screens.COMMENTARY + [f"1′ {screens.ELEVEN[self.pick][2]} captains Holland",
                                       "Speed »»»»» · marks: positions · your side: white"]:
            line = label(c, "muted" if c.startswith("Speed") else "")
            line.setWordWrap(True)
            comm.addWidget(line)
        comm.addStretch(1)
        row.addWidget(box("Commentary", comm), 1)
        main.addLayout(row, 1)
        v.addLayout(main, 1)
        v.addWidget(self.keys([(["↑", "↓"], "display"), (["←", "→"], "speed"), (["R"], "result"),
                               (["Space"], "commentary"), (["F9"], "sound")], "Bench (Esc: desk in the prototype)",
                              lambda: self.go("desk")))
        return page

    def render(self):
        if self.page is not None:
            self.body.removeWidget(self.page)
            self.page.hide()
            self.page.setParent(None)
            self.page.deleteLater()
        self.page = {"desk": self.desk, "captain": self.captain, "kickoff": self.kickoff}[self.screen]()
        self.body.addWidget(self.page)
        self.setStyleSheet(STYLE)

    def go(self, screen):
        self.screen, self.notice = screen, ""
        if screen == "captain":
            self.pick = screens.COMPUTER_PICK
        self.render()

    def activate(self):
        if self.cursor == screens.PLAY:
            return self.go("captain")
        self.notice = f"{screens.MENU_HINT[self.cursor]}: not in the prototype"
        self.render()

    def click_menu(self, i):
        self.cursor = i
        self.activate()

    def click_player(self, i):
        self.pick = i
        self.render()

    def keyPressEvent(self, event):
        k = event.key()
        if self.screen == "desk":
            if k == Qt.Key_Down:
                self.cursor = (self.cursor + 1) % len(screens.MENU)
            elif k == Qt.Key_Up:
                self.cursor = (self.cursor - 1) % len(screens.MENU)
            elif k in (Qt.Key_Return, Qt.Key_Enter):
                return self.activate()
            elif k in (Qt.Key_F1, Qt.Key_F3, Qt.Key_F4, Qt.Key_F7, Qt.Key_F10, Qt.Key_T, Qt.Key_Space):
                self.notice = f"{event.text() or 'F-key'}: not in the prototype"
            else:
                return
        elif self.screen == "captain":
            if k == Qt.Key_Down:
                self.pick = (self.pick + 1) % 11
            elif k == Qt.Key_Up:
                self.pick = (self.pick - 1) % 11
            elif k in (Qt.Key_Return, Qt.Key_Enter):
                return self.go("kickoff")
            elif k == Qt.Key_C:
                self.pick = screens.COMPUTER_PICK
                return self.go("kickoff")
            elif k == Qt.Key_Escape:
                return self.go("desk")
            else:
                return
        elif k in (Qt.Key_Escape, Qt.Key_Return, Qt.Key_Enter):
            return self.go("desk")
        else:
            return
        self.render()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--quit-after", type=float)
    parser.add_argument("--screenshot", type=Path, help="write desk.png, captain.png and kickoff.png there and quit")
    args = parser.parse_args()
    app = QApplication(sys.argv[:1])
    QFontDatabase.addApplicationFont(str(common.FONT))
    font = QFont(FAMILY)
    font.setPixelSize(16)
    font.setStyleStrategy(QFont.NoAntialias)
    app.setFont(font)
    window = Window()
    if args.screenshot:
        args.screenshot.mkdir(parents=True, exist_ok=True)
        window.show()
        for name in ("desk", "captain", "kickoff"):
            window.go(name)
            app.processEvents()
            window.grab().save(str(args.screenshot / f"qt-{name}.png"))
        return 0
    painted = []

    class Filter(QWidget):
        def eventFilter(self, obj, event):
            if event.type() == QEvent.Paint and not painted:
                painted.append(True)
                QTimer.singleShot(0, lambda: print(f"READY {time.perf_counter() - START:.4f}", flush=True))
                if args.quit_after is not None:
                    QTimer.singleShot(int(args.quit_after * 1000), app.quit)
            return False
    f = Filter()
    window.installEventFilter(f)
    window.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
