"""[designed: owner, 2026-11-08, #667; T211] The shared parts of S06 and S08 on the 16 x 32 grid: the strip, key-value lines and a typed line.

[designed: docs/design/ui-2026-11/proposal/README.md] The same parts as `squad_card` and `start_look` draw as bordered cards,
drawn with the original's grammar: a panel is a `Frame` (a rule with its lowercase label, goal2/ui/frame.py), its body is placed
by cell (goal2/ui/cells.py), nothing is padded and nothing is a card. Each keeps the interface of the part it replaces (`Strip.rows`,
`Strip.gap`, `show_rows`, `key_value`'s values with their `caption`, `LineField`'s text and cursor), so a screen and its tests read
the same names; only the geometry is the grid's.
"""
from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QPainter
from PySide6.QtWidgets import QFrame, QHBoxLayout, QWidget

from goal2.ui import theme
from goal2.ui.cells import CellEdit, CellLabel, CellPara, Cells, row_px
from goal2.ui.frame import Frame, FrameRule
from goal2.ui.screen import Clickable
from goal2.ui.squad_card import CHARACTERISTIC_CELLS, LINE_COLOUR, NAME_MAX, SKILL_CELLS, Row, colour
from goal2.ui.start_look import LineField


def key_values(rows, cols, label_cols, label_name="cardLabel"):
    """The `.kv` lines as cells: brown labels at the left, their values `label_cols + 1` cells in. Returns (widget, {key: value
    label}) as `start_look.key_value` does, each value with its `caption` label. A value is one line: it is as long as its cells."""
    area = Cells(cols, len(rows), "keyValues")
    values = {}
    for r, (key, caption) in enumerate(rows):
        caption_label = area.text(caption, label_name, 0, r, label_cols)
        value = CellLabel("", "value")
        area.put(value, label_cols + 1, r, cols - label_cols - 1)
        value.caption = caption_label
        values[key] = value
    return area, values


class CellRow(Row):
    """A row of the strip: one row of cells, one cell in from each edge, the highlight bar behind it when it is the cursor's."""

    def __init__(self, index, reserve=(2, 0)):
        Clickable.__init__(self, "listRow")
        self.index = index
        self.underline = False
        layout = QHBoxLayout(self)
        layout.setContentsMargins(theme.CELL_W, 0, theme.CELL_W, 0)
        layout.setSpacing(0)
        self.cells = []
        self.tones = []
        for cols in reserve:
            cell = CellLabel("", "rowCell", reserve=cols)
            layout.addWidget(cell, 0 if cols else 1)
            self.cells.append(cell)
            self.tones.append(theme.TEXT_BRIGHT)
        self.on = False
        self.clicked.connect(lambda: self.chosen.emit(self.index))
        self._paint()


class GridStrip(Frame):
    """The list on the right as the original draws it: the twenty (the eleven, a gap, the bench) or a page of twenty of the
    pool, in a frame whose rule carries the country (`-holland---`). Rows are clicked through `chosen(index on the page)`."""
    chosen = Signal(int)
    PAGE = 20
    COLS = 24   # [designed: T211] one cell in, a code and its gap, a name of up to 14 characters, a cell out, and room for a name

    def __init__(self, cols=COLS):
        super().__init__("", "red")
        self.setObjectName("strip")
        self.cols = cols
        self.area = Cells(cols, self.PAGE + 1, "stripRows")
        self.add(self.area, 1)
        self.rows = []
        self.gap = QWidget()
        self.area.put(self.gap, 0, 11, self.cols)
        for i in range(self.PAGE):
            row = CellRow(i)
            row.chosen.connect(self.chosen.emit)
            self.area.put(row, 0, i + (1 if i > 10 else 0), self.cols)
            self.rows.append(row)

    def show_rows(self, heading, rows, current=-1, gap=True, injured=()):
        """`rows`: (code, line, name) for up to twenty rows; `current` the highlighted row (-1: none)."""
        self.set_label(heading)
        self.gap.setVisible(gap)
        for i, row in enumerate(self.rows):
            self.area.move(row, 0, i + (1 if i > 10 and gap else 0), self.cols)
            if i < len(rows):
                code, line, name = rows[i]
                row.setProperty("injured", i in injured)
                tone = LINE_COLOUR.get(line, theme.TEXT_NORMAL)
                row.set((code, name), (tone, tone))
                row.show()
            else:
                row.set(("", ""))
                row.hide()
            row.set_on(i == current)

    def shown_texts(self):
        return [row.texts() for row in self.rows if not row.isHidden()]


class CellLineField(LineField):
    """A typed line on the grid (the desk's manager name): its text, then a block cursor one cell wide while it is active, and
    the count. No border: the cursor says it is open."""

    def __init__(self, maximum, count=False, on_click=None):
        Clickable.__init__(self, "cellField")
        self.maximum, self.text, self.placeholder = maximum, "", ""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        self.shown = CellLabel("", "value")
        layout.addWidget(self.shown)
        self.cursor = QFrame()
        self.cursor.setObjectName("cursor")
        self.cursor.setFixedSize(theme.CELL_W, theme.CELL_H)
        layout.addWidget(self.cursor)
        layout.addStretch(1)
        self.count = CellLabel("", "muted") if count else None
        if self.count is not None:
            layout.addWidget(self.count)
        self.setProperty("active", False)
        if on_click is not None:
            self.clicked.connect(on_click)
        self._show()


class CellBar(QWidget):
    """A bar of the original's two colours, filled part light grey and the rest magenta [confirmed: §3 palette, "bar, filled" and
    "bar, empty"], one row of cells across and drawn inside it: the widget is whole cells, the bar a little less than the row's
    height (the cell's top and bottom are left black, so bars of rows that touch are rows). [designed: T211]"""
    INSET = 0.2   # of the row, above and below the bar

    def __init__(self):
        super().__init__()
        self.setObjectName("bar")
        self.value = None

    def set(self, filled, cells):
        """`filled` of `cells`; None shows no bar (the value is unavailable)."""
        self.value = (filled, cells)
        self.update()

    def paintEvent(self, event) -> None:
        if self.value is None or self.value[0] is None:
            return
        filled, cells = self.value
        filled = max(0, min(cells, filled))
        inset = round(self.height() * self.INSET)
        painter = QPainter(self)
        split = round(self.width() * filled / cells) if cells else 0
        painter.fillRect(0, inset, split, self.height() - 2 * inset, QColor(theme.BAR_FILLED))
        painter.fillRect(split, inset, self.width() - split, self.height() - 2 * inset, QColor(theme.BAR_EMPTY))
        painter.end()


class CellBars(Cells):
    """Rows of a label, a bar and a word, as `squad_card.Bars`, in cells: the label `label_cols` wide, the bar `bar_cols`, then the
    word. The same `rows`, `labels` and `set` as `Bars`."""

    def __init__(self, names, label_cols, bar_cols, word_cols):
        super().__init__(label_cols + bar_cols + word_cols + 2, len(names), "bars")
        self.rows, self.labels = {}, {}
        for r, name in enumerate(names):
            name_label = self.text(name, "barLabel", 0, r, label_cols)
            colour(name_label, theme.CARD_LABEL)   # [designed: owner611; T193] brown labels, as the original's
            bar = CellBar()
            self.put(bar, label_cols + 1, r, bar_cols)
            word = CellLabel("", "barWord")
            self.put(word, label_cols + bar_cols + 2, r, word_cols)
            self.labels[name], self.rows[name] = name_label, (bar, word)

    def set(self, name, filled, cells, word="", tone=theme.TEXT_BRIGHT):
        bar, word_label = self.rows[name]
        bar.set(filled, cells)
        word_label.setText(word)
        colour(word_label, tone)


class CellValues(Cells):
    """Lines of a brown label and its value, as `squad_card.KeyValues`, in cells. The same `values` and `set`."""

    def __init__(self, names, cols, label_cols):
        super().__init__(cols, len(names), "keyValues")
        self.values = {}
        for r, name in enumerate(names):
            colour(self.text(name, "kvKey", 0, r, label_cols), theme.CARD_LABEL)
            value = CellLabel("", "kvValue")
            self.put(value, label_cols + 1, r, cols - label_cols - 1)
            self.values[name] = value

    def set(self, name, text):
        self.values[name].setText(text)


class CellFacts(Cells):
    """Aligned rules of a label and values under them, as `squad_card.FactsTable`: each fact a rule with its lowercase label (red,
    as the facts' labels are: owner611) and its value under it, side by side, `widths` cells each; the value is a cell short of the
    rule's edge, the separation from the next. `rows` is the value's rows (a value that can be long wraps in them). The same `labels`,
    `values`, `set`, `text` and `setWordWrap`; `labels` are the rules."""

    def __init__(self, widths, rows=1):
        super().__init__(sum(widths.values()), 1 + rows, "facts")
        self.labels, self.values = {}, {}
        column = 0
        for name, width in widths.items():
            rule = FrameRule(name, "red")
            value = CellPara("", "factValue") if rows > 1 else CellLabel("", "factValue")
            self.put(rule, column, 0, width)
            self.put(value, column, 1, width - 1, rows)
            self.labels[name], self.values[name] = rule, value
            column += width

    def set(self, values, tone):
        for name, value in values.items():
            self.values[name].setText(str(value))
            colour(self.values[name], tone)

    def text(self):
        return " · ".join(f"{name} {value.text()}" for name, value in self.values.items())

    def setWordWrap(self, on):
        return None   # a value is as many rows of cells as it needs, never a wrap of the font's


class CellNameLine(QFrame):
    """F2's new name on the grid: `New name`, a line of up to twelve characters, then the count. No border: the typed line is open.
    [designed: main session, 2026-11-03, T165, from s04-country.html; T211]"""

    def __init__(self):
        super().__init__()
        self.setObjectName("nameLine")
        self.area = Cells(34, 1, "nameLineCells", self)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self.area)
        self.area.text("New name", "muted", 0, 0)
        self.edit = CellEdit()
        self.edit.setObjectName("nameEdit")
        self.edit.setMaxLength(NAME_MAX)
        self.edit.setFrame(False)
        self.edit.setTextMargins(0, 0, 0, 0)
        self.edit.setStyleSheet(f"background: {theme.GROUND}; color: {theme.TEXT_BRIGHT}; border: none; padding: 0px;")
        self.area.put(self.edit, 9, 0, 14)
        self.count = self.area.text("", "muted", 24, 0, 7)
        self.edit.textChanged.connect(self._count)
        self._count()

    def _count(self, *unused):
        self.count.setText(f"{len(self.edit.text())} / {NAME_MAX}")


class GridCard(Cells):
    """The S08 card on the grid, in the proposal's order [designed: T211; docs/design/ui-2026-11/proposal/README.md, s08-squad]: the name
    frame, then the facts in frames of one rule, the positions and the card's status under them, the skills at the left and the
    tactics over the characteristics at the right. The same attributes and methods as `squad_card.PlayerCard` (`code`, `name`, `facts`,
    `positions`, `readiness`, `name_line`, `skills`, `tactics`, `characteristics`, `set_card`, `edit_name`): a card is 69 x 18 cells."""
    COLS, ROWS = 69, 18
    FACTS = {"age": 5, "caps": 6, "goals": 7, "height": 8, "foot": 12, "performance": 15}
    POSITIONS = {"position": 19, "club position": 19, "cards": 17}
    NAME_COLS = 16
    HALF = 33   # the skills' frame; the tactics and characteristics take the rest, a cell apart

    def __init__(self):
        super().__init__(self.COLS, self.ROWS, "card")
        from goal2.game.player_card import SKILLS, TACTICS
        head = Frame("name")
        inner = Cells(self.NAME_COLS, 1, "nameRows")
        head.add(inner, 1)
        self.code = CellLabel("", "roleCode")
        inner.put(self.code, 0, 0, 1)
        self.name = CellLabel("", "h1")
        inner.put(self.name, 2, 0, self.NAME_COLS - 2)
        self.put(head, 0, 0, self.NAME_COLS, 2)
        self.facts = CellFacts(self.FACTS, rows=1)
        self.put(self.facts, self.NAME_COLS, 0, self.COLS - self.NAME_COLS, 2)
        self.positions = CellFacts(self.POSITIONS, rows=2)
        self.put(self.positions, 0, 2, sum(self.POSITIONS.values()), 3)
        status = Frame("readiness")
        status_body = Cells(14, 2, "readinessRows")
        status.add(status_body, 1)
        self.readiness = CellLabel("", "readiness")
        status_body.put(self.readiness, 0, 0, 13)
        self.put(status, sum(self.POSITIONS.values()), 2, self.COLS - sum(self.POSITIONS.values()), 3)
        self.name_line = CellNameLine()
        self.name_line.hide()
        self.put(self.name_line, 0, 1, 34)
        right_cols = self.COLS - self.HALF - 1
        skills = Frame("skills", "red")
        self.skills = CellBars(SKILLS, 10, 20, 1)
        skills.add(self.skills, 1)
        self.put(skills, 0, 5, self.HALF, 1 + len(SKILLS))
        tactics = Frame("tactics", "red")
        self.tactics = CellValues(TACTICS + ("mark",), right_cols, 10)
        tactics.add(self.tactics, 1)
        self.put(tactics, self.HALF + 1, 5, right_cols, 1 + len(TACTICS) + 1)
        characteristics = Frame("characteristics", "red")
        self.characteristics = CellBars(("hardness", "fitness", "energy", "morale", "leadership"), 10, 9, 14)
        characteristics.add(self.characteristics, 1)
        self.put(characteristics, self.HALF + 1, 5 + 1 + len(TACTICS) + 1, right_cols, 6)
        self.card = None

    def set_card(self, card):
        self.card = card
        self.code.setText(card["role"])
        colour(self.code, LINE_COLOUR.get(card["line"], theme.TEXT_NORMAL))
        self.name.setText(card["full_name"])
        # [designed: T193] Display-only compatibility with the existing raw card and T192's stars.
        stars = card.get("performance_bar")
        performance = ("*" * stars if stars is not None else "" if card["performance"] is None
                       else f"raw {card['performance']}")
        tone = LINE_COLOUR.get(card["line"], theme.TEXT_BRIGHT)
        self.facts.set({**{name: card[name] for name in ("age", "caps", "goals", "height", "foot")},
                        "performance": performance}, tone)
        self.readiness.setText(card["readiness"])
        self.positions.set({"position": card["position"], "club position": card["club_position"],
                            "cards": ", ".join(card["cards"]) or "none"}, tone)
        for name, value in card["skills"]:
            # [designed: owner, 2026-10-21, T99 "no numbers when you can have bars"] the bar alone.
            self.skills.set(name, value, SKILL_CELLS, "" if value is not None else "—")
        for name, word, personal in card["tactics"]:
            self.tactics.set(name, word + (" P" if personal else ""))
        self.tactics.set("mark", card["mark"] or "—")
        for name, word, bar, _raw in card["characteristics"]:
            self.characteristics.set(name, bar, CHARACTERISTIC_CELLS, word, tone=tone)

    def edit_name(self, on, text=""):
        """Show the name line in place of the name and its facts (F2), or the name again."""
        for widget in (self.name, self.facts):
            widget.setVisible(not on)
        self.name_line.setVisible(on)
        if on:
            self.name_line.edit.setText(text)
            self.name_line.edit.selectAll()
            self.name_line.edit.setFocus(Qt.FocusReason.ShortcutFocusReason)


__all__ = ["CellBar", "CellBars", "CellFacts", "CellLineField", "CellNameLine", "CellRow", "CellValues", "GridCard", "GridStrip",
           "key_values", "row_px"]
