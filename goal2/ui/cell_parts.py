"""[designed: owner, 2026-11-08, #667; T211] The shared parts of S06 and S08 on the 16 x 32 grid: the strip, key-value lines and a typed line.

[designed: docs/design/ui-2026-11/proposal/README.md] The same parts as `squad_card` and `start_look` draw as bordered cards,
drawn with the original's grammar: a panel is a `Frame` (a rule with its lowercase label, goal2/ui/frame.py), its body is placed
by cell (goal2/ui/cells.py), nothing is padded and nothing is a card. Each keeps the interface of the part it replaces (`Strip.rows`,
`Strip.gap`, `show_rows`, `key_value`'s values with their `caption`, `LineField`'s text and cursor), so a screen and its tests read
the same names; only the geometry is the grid's.
"""
from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QFrame, QHBoxLayout, QWidget

from goal2.ui import theme
from goal2.ui.cells import CellLabel, Cells
from goal2.ui.frame import Frame
from goal2.ui.screen import Clickable
from goal2.ui.squad_card import LINE_COLOUR, Row
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

    def __init__(self):
        super().__init__("", "red")
        self.setObjectName("strip")
        self.area = Cells(self.COLS, self.PAGE + 1, "stripRows")
        self.add(self.area, 1)
        self.rows = []
        self.gap = QWidget()
        self.area.put(self.gap, 0, 11, self.COLS)
        for i in range(self.PAGE):
            row = CellRow(i)
            row.chosen.connect(self.chosen.emit)
            self.area.put(row, 0, i + (1 if i > 10 else 0), self.COLS)
            self.rows.append(row)

    def show_rows(self, heading, rows, current=-1, gap=True, injured=()):
        """`rows`: (code, line, name) for up to twenty rows; `current` the highlighted row (-1: none)."""
        self.set_label(heading)
        self.gap.setVisible(gap)
        for i, row in enumerate(self.rows):
            self.area.move(row, 0, i + (1 if i > 10 and gap else 0), self.COLS)
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


__all__ = ["CellLineField", "CellRow", "GridStrip", "key_values"]
