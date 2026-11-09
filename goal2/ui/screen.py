"""The `Screen` base class: a title bar, a body, an optional "waiting for" line and the bottom key bar.

[designed: owner, 2026-11-03, #526, #536; docs/design/ui-2026-11 §3, "Navigation", "The Enter hint", "Stops", "The
keyboard"] Every screen of the new window is a `Screen`:
- its **title bar** holds the GOAL2 corner and the screen's name (`title`); the screens before a game (S01–S04)
  add the corner's note "the 1993 game, rebuilt" and show the name in normal text, the others in bright text, as
  the mockups draw them;
- its **bottom bar** lists every key of the screen (`bind`), in the key-hint magenta, and at its right end the
  Enter hint, drawn as the original's highlight bar: what Enter does now, on the highlighted option;
- a screen that waits for the player says so above its body (`wait_for`), with the key that answers.

[designed: owner, 2026-11-08, #667; T211] A screen that sets `GRID` is laid out on the 16 x 32 grid (docs/design/ui-2026-11/
fidelity-review.md §3, goal2/ui/cells.py): the title bar is one row, the page has no margin and no padding (a screen's panels
are placed by cell, separated by one empty cell), a key of the bottom bar is its caption and its word joined (`F1help`, no box),
the bar is as many rows as its keys need (never fewer than `KEY_ROWS`, so the page does not move when the Enter hint changes),
and an option is a bordered box of two rows or a line of one. The other screens keep the layout they were drawn with until
they are reflowed (T211b, T212-T214); `GRID` goes when the last one is.

Keys and the mouse take one path: a key's binding, a click on an option, on a key of the bottom bar or on the Enter
hint all call `Binding.run` or `Screen.activate`, and so the same handler. [designed: owner, 2026-11-03, #526: "the
mouse does what the keys do"]
"""
from __future__ import annotations

import html

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QPainter
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QSizePolicy, QVBoxLayout, QWidget

from goal2.ui import cells, theme

ENTER_KEYS = (Qt.Key.Key_Return, Qt.Key.Key_Enter)
LINE_HEIGHT = 135   # [designed: docs/design/ui-2026-11/mockups/style.css, body `line-height: 1.35`]


def label(text: str, name: str, parent=None) -> QLabel:
    widget = QLabel(text, parent)
    widget.setObjectName(name)
    return widget


class Clickable(QFrame):
    """A frame that reports a left click released over it."""
    clicked = Signal()

    def __init__(self, name: str, parent=None):
        super().__init__(parent)
        self.setObjectName(name)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and self.rect().contains(event.position().toPoint()):
            self.clicked.emit()
            event.accept()
            return
        super().mouseReleaseEvent(event)


def para(text: str, name: str, parent=None) -> QLabel:
    """A wrapped paragraph at the mockups' line height (`line-height: 1.35`)."""
    widget = label("", name, parent)
    widget.setTextFormat(Qt.TextFormat.RichText)
    widget.setWordWrap(True)
    set_para(widget, text)
    return widget


def set_para(widget: QLabel, text: str):
    lines = "<br>".join(html.escape(line) for line in text.split("\n"))
    widget.setText(f'<p style="line-height:{LINE_HEIGHT}%">{lines}</p>' if text else "")


def kbd(caption: str, parent=None) -> QLabel:
    """A key cap, as the mockups' `kbd`."""
    cap = label(caption, "kbd", parent)
    cap.setAlignment(Qt.AlignmentFlag.AlignCenter)
    cap.setMinimumWidth(26)
    cap.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
    return cap


class Binding:
    """Keys of a screen, their captions on the bottom bar, what they do (`text`) and the handler."""

    def __init__(self, keys, captions, text, handler, shown=True):
        self.keys, self.captions, self.text, self.handler, self.shown = tuple(keys), tuple(captions), text, handler, shown

    def run(self):
        return self.handler()


class Option(Clickable):
    """A clickable option of a screen: its text, its own key if it has one, and what Enter does on it."""

    def __init__(self, screen, text, handler, key=None, enter=None):
        super().__init__("option")
        self.screen, self.handler, self.key = screen, handler, key
        self.enter = enter if enter is not None else text
        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 9, 16, 9)
        layout.setSpacing(12)
        self.text_label = label(text, "optionText")
        layout.addWidget(self.text_label)
        layout.addStretch(1)
        if key is not None:
            layout.addWidget(kbd(key_name(key)))
        self.setProperty("on", False)
        self.clicked.connect(lambda: screen.activate(self))

    def set_on(self, on: bool):
        self.setProperty("on", bool(on))
        for widget in (self, *self.findChildren(QWidget)):
            widget.style().unpolish(widget)
            widget.style().polish(widget)


class GridOption(Option):
    """An option on the grid: a box of two rows (a one-pixel border at the box's edge, its text between the two lines, as the
    original's hub draws them: boxes of two rows) or a line of one (`rows=1`: the highlight bar alone). The border is drawn at the
    edge, never a style sheet's border, which would take a pixel from the cell the text sits in. Boxes that touch show their two
    borders as one line of two pixels, the original's. [designed: owner, 2026-11-08, #667; T211;
    docs/design/ui-2026-11/proposal/README.md; confirmed: docs/original-game/images/manager-menu.png]"""

    def __init__(self, screen, text, handler, key=None, enter=None, rows=2):
        Clickable.__init__(self, "gridOption" if rows > 1 else "gridLine")
        self.screen, self.handler, self.key, self.rows = screen, handler, key, rows
        self.enter = enter if enter is not None else text
        layout = QHBoxLayout(self)
        layout.setContentsMargins(theme.CELL_W if rows > 1 else 0, 0, theme.CELL_W if rows > 1 else 0, 0)
        layout.setSpacing(theme.CELL_W)
        self.text_label = cells.CellLabel(text, "optionText")
        layout.addWidget(self.text_label)
        layout.addStretch(1)
        if key is not None:
            layout.addWidget(cells.CellLabel(key_name(key), "keyCap"))
        self.setProperty("on", False)
        self.clicked.connect(lambda: screen.activate(self))

    def paintEvent(self, event) -> None:
        super().paintEvent(event)
        if self.rows > 1 and not self.property("on"):
            painter = QPainter(self)
            painter.setPen(QColor(theme.FRAME))
            painter.drawRect(self.rect().adjusted(0, 0, -1, -1))
            painter.end()


def key_name(key) -> str:
    """The caption of a key on the bottom bar."""
    names = {Qt.Key.Key_Escape: "Esc", Qt.Key.Key_Return: "Enter", Qt.Key.Key_Enter: "Enter", Qt.Key.Key_Up: "↑",
             Qt.Key.Key_Down: "↓", Qt.Key.Key_PageUp: "PgUp", Qt.Key.Key_PageDown: "PgDn", Qt.Key.Key_Space: "Space",
             Qt.Key.Key_Insert: "Ins"}
    if key in names:
        return names[key]
    if Qt.Key.Key_F1 <= key <= Qt.Key.Key_F12:
        return f"F{int(key) - int(Qt.Key.Key_F1) + 1}"
    return chr(int(key))


class Screen(QWidget):
    """One screen of the window. Subclasses set `title`, build their body in `self.body_layout`, `bind` their keys,
    add `options` and say what Esc does (`escape_text`, `escape`)."""

    title = ""
    pre_game = False      # the title bar of S01–S04: the corner's note, the name in normal text
    escape_text = "back"  # what Esc does, on the bottom bar; None: Esc does nothing here
    offers_help = True    # F1 opens the help (S22) from this screen
    GRID = False          # laid out on the 16 x 32 grid (T211): see the module's docs
    KEY_ROWS = 2          # on the grid: the rows the bottom bar always has, so the page does not move with the Enter hint

    def __init__(self, window):
        super().__init__()
        self.window_ = window
        self.setObjectName("screen")
        self.setProperty("grid", self.GRID)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.bindings: list[Binding] = []
        self.options: list[Option] = []
        self.cursor = -1
        self.enter_action = None   # (text, handler) when Enter does one thing with no options
        self._choose = None
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)
        outer.addWidget(self._title_bar())
        main = QWidget()
        main.setObjectName("body")
        self.main_layout = QVBoxLayout(main)
        self.main_layout.setContentsMargins(*((0, 0, 0, 0) if self.GRID else (24, 18, 24, 18)))
        self.main_layout.setSpacing(0 if self.GRID else 18)
        self.wait_box = self._wait_box()
        self.main_layout.addWidget(self.wait_box)
        self.body = QWidget()
        self.body.setObjectName("body")
        self.body_layout = QVBoxLayout(self.body)
        self.body_layout.setContentsMargins(0, 0, 0, 0)
        self.body_layout.setSpacing(0 if self.GRID else 14)
        self.main_layout.addWidget(self.body, 1)
        outer.addWidget(main, 1)
        from goal2.ui.key_flow import KeyBar
        self.key_bar = KeyBar()
        self.key_bar.setObjectName("keyRow" if self.GRID else "keyBar")
        self.key_bar.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Minimum)
        from goal2.ui.key_flow import KeyFlow
        self.key_layout = KeyFlow(self.key_bar)
        if self.GRID:
            # [designed: T211] flush left, a cell between keys, the rows touching, the keys on the bottom rows
            self.key_layout.rows = self.KEY_ROWS
            self.key_layout.setContentsMargins(0, 0, 0, 0)
            self.key_layout.setSpacing(theme.CELL_W)
            self.key_layout.line_spacing = 0
            self.key_layout.bottom = True
        else:
            self.key_layout.setContentsMargins(24, 8, 24, 8)
            self.key_layout.setSpacing(12)
        outer.addWidget(self.key_bar)
        self.enter_hint = Clickable("enterBar" if self.GRID else "enterHint")
        hint_layout = QHBoxLayout(self.enter_hint)
        hint_layout.setContentsMargins(*((theme.CELL_W, 0, theme.CELL_W, 0) if self.GRID else (22, 12, 22, 12)))
        hint_layout.setSpacing(theme.CELL_W if self.GRID else 10)
        self.enter_text = cells.CellLabel("", "enterText") if self.GRID else label("", "enterText")
        hint_layout.addWidget(self.enter_text)
        hint_layout.addWidget(self._cap("Enter"))
        self.enter_hint.clicked.connect(self.press_enter)
        if self.offers_help:
            self.bind((Qt.Key.Key_F1,), "help", window.open_help)
        if self.escape_text is not None:
            self.bind((Qt.Key.Key_Escape,), self.escape_text, self.escape)

    # The title bar and the "waiting for" line.
    def _cap(self, caption):
        """A key's caption: a key cap with its box, or on the grid the caption alone in a row of cells."""
        return cells.CellLabel(caption, "keyCap") if self.GRID else kbd(caption)

    def _title_bar(self):
        bar = QFrame()
        bar.setObjectName("titleRow" if self.GRID else "titleBar")
        bar.setFixedHeight(theme.CELL_H if self.GRID else 64)   # one row on the grid
        layout = QHBoxLayout(bar)
        layout.setContentsMargins(*((theme.CELL_W, 0, theme.CELL_W, 0) if self.GRID else (24, 0, 24, 0)))
        layout.setSpacing(theme.CELL_W if self.GRID else 28)
        corner = QHBoxLayout()
        corner.setSpacing(theme.CELL_W if self.GRID else 6)
        make = cells.CellLabel if self.GRID else label   # the same call: (text, object name)
        corner.addWidget(make("GOAL2", "brand"))
        if self.pre_game:
            corner.addWidget(make("the 1993 game, rebuilt", "brandNote"))
        layout.addLayout(corner)
        self.name_label = make(self.title, "crumb" if self.pre_game else "who")
        layout.addWidget(self.name_label)
        layout.addStretch(1)
        return bar

    def _wait_box(self):
        box = QFrame()
        if self.GRID:
            # [designed: T211] the headline over its detail, on the page: no border, no padding, rows of cells
            box.setObjectName("waitRow")
            layout = QVBoxLayout(box)
            layout.setContentsMargins(0, 0, 0, 0)
            layout.setSpacing(0)
            self.wait_head = cells.CellLabel("", "waitHead")
            self.wait_detail = cells.CellPara("", "sub")
            layout.addWidget(self.wait_head)
            layout.addWidget(self.wait_detail)
            box.hide()
            return box
        box.setObjectName("waitBox")
        layout = QHBoxLayout(box)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(20)
        self.wait_head = label("", "waitHead")
        self.wait_detail = para("", "sub")
        self.wait_detail.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        layout.addWidget(self.wait_head)
        layout.addWidget(self.wait_detail, 1)
        box.hide()
        return box

    def wait_for(self, headline, detail=""):
        """Say what the screen waits for and which key answers it (None: the screen waits for nothing).
        [designed: #523, docs/design/ui-2026-11 §3, "Stops"; drawn as the S16 mockup's box]"""
        if headline is None:
            self.wait_box.hide()
            return
        self.wait_head.setText(headline)
        if self.GRID:
            self.wait_detail.setText(detail)
        else:
            set_para(self.wait_detail, detail)
        self.wait_box.show()

    # Keys.
    def bind(self, keys, text, handler, captions=None, shown=True) -> Binding:
        binding = Binding(keys, captions or tuple(key_name(k) for k in keys), text, handler, shown)
        self.bindings.append(binding)
        self._refresh_bar()
        return binding

    def set_enter(self, text, handler):
        """What Enter does on a screen without options; drawn as the Enter hint."""
        self.enter_action = (text, handler)
        self._refresh_hint()

    def add_option(self, text, handler, key=None, enter=None, rows=2) -> Option:
        """A clickable option; ↑↓ move the highlight over the options and Enter does the highlighted one. On the grid it is a box
        of `rows` = 2 rows, or a line of 1."""
        option = (GridOption(self, text, handler, key, enter, rows=rows) if self.GRID
                  else Option(self, text, handler, key, enter))
        self.options.append(option)
        if key is not None:
            self.bind((key,), text, lambda o=option: self.activate(o))
        if len(self.options) == 1:
            self.bind((Qt.Key.Key_Up,), "", lambda: self.highlight(self.cursor - 1), shown=False)
            self.bind((Qt.Key.Key_Down,), "", lambda: self.highlight(self.cursor + 1), shown=False)
            self._choose = self.bind((), "choose", None, captions=("↑", "↓"))
            self.highlight(0)
        return option

    def highlight(self, index):
        if not self.options:
            return
        self.cursor = max(0, min(index, len(self.options) - 1))
        for i, option in enumerate(self.options):
            option.set_on(i == self.cursor)
        self._refresh_hint()

    def highlighted(self):
        return self.options[self.cursor] if self.options else None

    def activate(self, option):
        """An option chosen by its key, by Enter on it or by a click: highlight it and run its handler."""
        self.highlight(self.options.index(option))
        return option.handler()

    def press_enter(self):
        if self.options:
            return self.activate(self.highlighted())
        if self.enter_action is not None:
            return self.enter_action[1]()
        return None

    def enter_hint_text(self):
        """What the Enter hint says now ('' when Enter does nothing here)."""
        if self.options:
            return self.highlighted().enter
        return self.enter_action[0] if self.enter_action else ""

    def handle_key(self, key) -> bool:
        """Run what `key` does on this screen; False when it does nothing here."""
        if key in ENTER_KEYS:
            if self.options or self.enter_action:
                self.press_enter()
                return True
            return False
        for binding in self.bindings:
            if key in binding.keys and binding.handler is not None:
                binding.run()
                return True
        return False

    def escape(self):
        """Esc: back to the screen this one was opened from, unless the screen says otherwise."""
        self.window_.pop()

    # The bottom bar.
    def _refresh_bar(self):
        while self.key_layout.count():
            item = self.key_layout.takeAt(0)
            widget = item.widget()
            if widget is not None and widget is not self.enter_hint:
                widget.setParent(None)
                widget.deleteLater()
        # ↑↓ to choose an option come after the screen's own keys, as on the S06 mockup's bar.
        for binding in sorted(self.bindings, key=lambda b: b is self._choose):
            if not binding.shown:
                continue
            item = Clickable("keyItem")
            row = QHBoxLayout(item)
            row.setContentsMargins(0, 0, 0, 0)
            row.setSpacing(0 if self.GRID else 7)
            for caption in binding.captions:
                row.addWidget(self._cap(caption))
            row.addWidget(cells.CellLabel(binding.text, "keyLabel") if self.GRID else label(binding.text, "keyLabel"))
            item.binding = binding
            if binding.handler is not None:
                item.clicked.connect(binding.run)
            self.key_layout.addWidget(item)
        self.key_layout.addWidget(self.enter_hint)
        self._refresh_hint()

    def _refresh_hint(self):
        text = self.enter_hint_text()
        self.enter_text.setText(text)
        self.enter_hint.setVisible(bool(text))

    def key_texts(self):
        """The bottom bar as it reads: (captions, text) for each key it lists."""
        return [(b.captions, b.text) for b in sorted(self.bindings, key=lambda b: b is self._choose) if b.shown]

    def shown(self):
        """Called when the screen becomes the window's current one."""
