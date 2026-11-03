"""The look the start and new-game screens (S02–S05) add to the window's style sheet, and the small parts they share.

[designed: owner, 2026-11-03, #526; docs/design/ui-2026-11/mockups/style.css] Colours are `theme`'s, by role only;
text sizes are whole multiples of the 16 px cell (16, 32, 48 and 64 px, §3 "Text size"). The window appends
`stylesheet()` to `theme.stylesheet`, so the page scales these lengths with the rest (goal2/desktop/fixed_page.py).
"""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QGridLayout, QHBoxLayout, QLabel, QVBoxLayout, QWidget

from goal2.ui import theme
from goal2.ui.screen import Clickable, kbd, label

# A role code's colour by its line, as the original colours them. [confirmed: docs/design/ui-2026-11 §3, the
# palette table and "Role codes are coloured by line"]
LINE_COLOUR = {"goalkeeper": theme.GOALKEEPER, "defence": theme.DEFENCE, "midfield": theme.MIDFIELD,
               "attack": theme.ATTACK}
BIG = 3 * theme.CELL      # 48 px: the bulletin's masthead [designed: style.css, s05's front page]
HUGE = 4 * theme.CELL     # 64 px: the title's GOAL2 [designed: style.css, s02's brand]


def stylesheet() -> str:
    t = theme
    return f"""
#titleBrand {{ color: {t.HEADING}; font-size: {HUGE}px; }}
#boxHeading {{ color: {t.HEADING}; }}
#cardLabel {{ color: {t.CARD_LABEL}; }}
#value, #cell {{ color: {t.TEXT_BRIGHT}; }}
#undecoded {{ color: {t.TEXT_NORMAL}; }}
#bigValue {{ color: {t.VALUE}; font-size: {t.HEADING_SIZE}px; }}
#row {{ background: {t.GROUND}; border-bottom: 1px solid {t.FRAME_DARK}; }}
#row[on="true"] {{ background: {t.HIGHLIGHT}; }}
#row[on="true"] QLabel {{ color: {t.ON_HIGHLIGHT}; }}
#row #bad {{ color: {t.BAD}; }}
#primary {{ background: {t.HIGHLIGHT}; border: 1px solid {t.HIGHLIGHT}; }}
#primary QLabel {{ color: {t.ON_HIGHLIGHT}; }}
#primaryText {{ font-size: {t.HEADING_SIZE}px; }}
#primary #kbd {{ border: 1px solid {t.ON_HIGHLIGHT}; background: transparent; }}
#digit {{ background: {t.GROUND}; border: 1px solid {t.FRAME_DARK}; }}
#digit[on="true"] {{ background: {t.HIGHLIGHT}; border: 1px solid {t.HIGHLIGHT}; }}
#digitText {{ font-size: {t.HEADING_SIZE}px; color: {t.TEXT_BRIGHT}; }}
#digitLater {{ font-size: {t.HEADING_SIZE}px; color: {t.TEXT_NORMAL}; }}
#digit[on="true"] QLabel {{ color: {t.ON_HIGHLIGHT}; }}
#lineField {{ background: {t.GROUND}; border: 2px solid {t.FRAME_DARK}; }}
#lineField[active="true"] {{ border: 2px solid {t.FRAME}; }}
#cursor {{ background: {t.TEXT_BRIGHT}; }}
#bad {{ color: {t.BAD}; }}
#masthead {{ color: {t.TEXT_BRIGHT}; font-size: {BIG}px; }}
#story {{ color: {t.TEXT_BRIGHT}; font-size: {t.HEADING_SIZE}px; }}
#bulletinTitle {{ color: {t.TEXT_BRIGHT}; font-size: {BIG}px; }}
#rule {{ background: {t.FRAME_DARK}; }}
#gk {{ color: {t.GOALKEEPER}; }}
#def {{ color: {t.DEFENCE}; }}
#mid {{ color: {t.MIDFIELD}; }}
#att {{ color: {t.ATTACK}; }}
"""


def refresh(widget):
    """Restyle `widget` and its children after a dynamic property changed."""
    for w in (widget, *widget.findChildren(QWidget)):
        w.style().unpolish(w)
        w.style().polish(w)


def box(heading=None, name="box"):
    """A framed box with its cyan heading, as the mockups' `.box > h2`; returns (frame, layout)."""
    frame = QFrame()
    frame.setObjectName(name)
    layout = QVBoxLayout(frame)
    layout.setContentsMargins(16, 14, 16, 14)
    layout.setSpacing(8)
    if heading is not None:
        layout.addWidget(label(heading.upper(), "boxHeading"))
    return frame, layout


def key_value(rows, label_name="cardLabel"):
    """The mockups' `.kv` grid: brown labels and their values; returns (widget, {key: value label})."""
    widget = QWidget()
    grid = QGridLayout(widget)
    grid.setContentsMargins(0, 0, 0, 0)
    grid.setHorizontalSpacing(16)
    grid.setVerticalSpacing(4)
    values = {}
    for r, (key, caption) in enumerate(rows):
        caption_label = label(caption, label_name)
        grid.addWidget(caption_label, r, 0)
        value = label("", "value")
        grid.addWidget(value, r, 1)
        values[key] = value
        values[key].caption = caption_label
    grid.setColumnStretch(1, 1)
    return widget, values


class Row(Clickable):
    """A row of a list with the original's highlight bar: cells of fixed widths (None: the rest)."""

    def __init__(self, widths, on_click=None):
        super().__init__("row")
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 4, 8, 4)
        layout.setSpacing(0)
        self.cells = []
        for width in widths:
            cell = label("", "cell")
            if width is not None:
                cell.setFixedWidth(width)
                layout.addWidget(cell)
            else:
                layout.addWidget(cell, 1)
            self.cells.append(cell)
        self.setProperty("on", False)
        if on_click is not None:
            self.clicked.connect(on_click)

    def set_cells(self, texts, names=None):
        for i, (cell, text) in enumerate(zip(self.cells, texts)):
            cell.setText(text)
            cell.setObjectName(names[i] if names and names[i] else "cell")
        refresh(self)

    def set_on(self, on):
        self.setProperty("on", bool(on))
        refresh(self)


class KeyItem(Clickable):
    """A menu item with its key cap at the right end, as the mockups' `.menu .item` with `kbd`."""

    def __init__(self, text, caption, handler, name="option"):
        super().__init__(name)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(12)
        self.text_label = label(text, "optionText")
        self.text_label.setWordWrap(True)
        layout.addWidget(self.text_label, 1)
        layout.addWidget(kbd(caption), 0, Qt.AlignmentFlag.AlignVCenter)
        self.clicked.connect(handler)


class LineField(Clickable):
    """A typed line (S03's year, S04's name): its text, a block cursor while it is active, and an optional count."""

    def __init__(self, maximum, count=False, on_click=None):
        super().__init__("lineField")
        self.maximum, self.text, self.placeholder = maximum, "", ""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(14, 10, 14, 10)
        layout.setSpacing(2)
        self.shown = label("", "value")
        layout.addWidget(self.shown)
        self.cursor = QFrame()
        self.cursor.setObjectName("cursor")
        self.cursor.setFixedSize(12, 22)
        layout.addWidget(self.cursor)
        layout.addStretch(1)
        self.count = label("", "muted") if count else None
        if self.count is not None:
            layout.addWidget(self.count)
        self.setProperty("active", False)
        if on_click is not None:
            self.clicked.connect(on_click)
        self._show()

    @property
    def active(self):
        return bool(self.property("active"))

    def set_active(self, active):
        self.setProperty("active", bool(active))
        self._show()
        refresh(self)

    def set_text(self, text):
        self.text = text[:self.maximum]
        self._show()

    def type(self, character) -> bool:
        if len(self.text) >= self.maximum:
            return False
        self.set_text(self.text + character)
        return True

    def backspace(self):
        self.set_text(self.text[:-1])

    def _show(self):
        empty = not self.text
        self.shown.setText(self.placeholder if empty else self.text)
        self.shown.setObjectName("muted" if empty else "value")
        self.cursor.setVisible(self.active)
        if self.count is not None:
            self.count.setText(f"{len(self.text)} / {self.maximum}")
        refresh(self.shown)


def coloured_codes(codes_and_lines) -> str:
    """Role codes coloured by line, as rich text (each with its code: nothing depends on colour alone)."""
    import html
    return " ".join(f'<span style="color:{LINE_COLOUR.get(line, theme.TEXT_NORMAL)}">{html.escape(code)}</span>'
                    for code, line in codes_and_lines)
