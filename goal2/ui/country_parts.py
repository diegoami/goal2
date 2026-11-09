"""[designed: owner, 2026-11-09, #667; T211b] The parts of the country card (S04, S07) on the 16 x 32 grid.

[designed: docs/design/ui-2026-11/proposal/README.md; fidelity-review.md §3] The same panels as `country_header`, `team_card` and
`start_look.key_value` draw as bordered cards (still S10's: it is reflowed later), drawn with the original's grammar: a panel is a
`Frame` (a rule with its lowercase label, goal2/ui/frame.py), its body is placed by cell (goal2/ui/cells.py), nothing is padded and
nothing is a card. Each keeps the interface of the part it replaces (`LineBars.rows`, `.labels`, `.panel`, `.set_panel`;
`DescriptorCells.grid`, `.labels`, `.content_size`; `StripGlyphs.set_strips`; `FactsTable.values`, `.labels`, `.text`), so the
screens and their tests read the same names; only the geometry is the grid's.
"""
from __future__ import annotations

from PySide6.QtCore import QRectF, QSize, Qt
from PySide6.QtGui import QColor, QFont, QPainter
from PySide6.QtWidgets import QHBoxLayout, QWidget

from goal2.desktop.country_card import characteristic_view
from goal2.game.country_card import NOT_DECODED
from goal2.ui import theme
from goal2.ui.cell_parts import CellBar
from goal2.ui.cells import CellLabel, Cells, cell_w, row_px
from goal2.ui.country_header import StripGlyphs
from goal2.ui.frame import Frame
from goal2.ui.kits import DOS
from goal2.ui.squad_card import colour

LINES = ("keeper", "defence", "midfield", "attack")
FIELDS = ("hardness", "fitness", "energy", "morale")
LINE_LABEL_COLS = 8      # "midfield"
LINE_BAR_COLS = 25       # [confirmed: goal2.game.team_card: a line's bar is 25 cells; team_card.LineBars draws bar.set(.., 25)]
DESCRIPTOR_COLS = 16     # [confirmed: F038, goal2/desktop/country_card.characteristic_view: columns 46..61 of the original's page]


def framed(label, cols, rows, kind="red"):
    """A panel: a frame (a rule with its lowercase label) over a body of `cols` x `rows` cells. Returns (frame, its body's cells)."""
    frame = Frame(label, kind)
    inner = Cells(cols, rows, "panelRows")
    frame.add(inner, 1)
    return frame, inner


class CellLineBars(Cells):
    """The four lines' bars (keeper, defence, midfield, attack) as `team_card.LineBars`, in cells: a brown label, a bar of 25 cells
    that is a row of the original's two colours. The same `panel`, `rows`, `labels`, `set_panel` and `text`."""

    def __init__(self):
        super().__init__(LINE_LABEL_COLS + 1 + LINE_BAR_COLS, len(LINES), "lineBars")
        self.panel = None
        self.rows, self.labels = {}, {}
        for number, name in enumerate(LINES):
            heading = CellLabel(name, "barLabel")
            colour(heading, theme.CARD_LABEL)
            self.put(heading, 0, number, LINE_LABEL_COLS)
            bar = CellBar()
            self.put(bar, LINE_LABEL_COLS + 1, number, LINE_BAR_COLS)
            self.rows[name], self.labels[name] = (bar, heading), heading
        self.set_panel(None)

    def set_panel(self, panel):
        self.panel = panel
        values = {} if panel is None else {row["line"]: row["cells"] for row in panel["bars"]}
        for name, (bar, _) in self.rows.items():
            bar.set(values.get(name), LINE_BAR_COLS)
        self.setAccessibleName(self.text())

    def text(self):
        return " · ".join(f"{name} " + ("undrawn" if bar.value[0] is None else f"{bar.value[0]} of {LINE_BAR_COLS}")
                          for name, (bar, _) in self.rows.items())


class CellStripGlyphs(StripGlyphs):
    """The three strips of the team as `country_header.StripGlyphs` draws them (a face on its raw VGA attribute's colours), at the
    cell: a face is a cell, with a cell between faces (`☻ ☻ ☻`), never the font's measured advance."""

    def sizeHint(self):
        cols = len("unknown") if self.unknown else 5
        return QSize(int(cols * cell_w(self)), row_px(self))

    def minimumSizeHint(self):
        return self.sizeHint()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setFont(self.font())
        try:
            if self.unknown:
                painter.setPen(QColor(theme.TEXT_NORMAL))
                painter.drawText(self.rect(), int(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter), "unknown")
                return
            width = cell_w(self)
            for index, attribute in enumerate(self.display_attributes):
                rect = QRectF(2 * index * width, 0, width, self.height())
                painter.fillRect(rect, QColor(DOS[(attribute >> 4) & 7]))
                painter.setPen(QColor(DOS[attribute & 15]))
                painter.drawText(rect, int(Qt.AlignmentFlag.AlignCenter), "☻")
        finally:
            painter.end()


class CellDescriptorRow(QWidget):
    """One of the characteristics' rows: 16 cells, the highlighted part the bar's light grey with black text, the rest the empty bar's
    `■` or the value's text, drawn glyph by glyph at the cell as `team_card._CellRow` does (one glyph in one cell)."""

    def __init__(self):
        super().__init__()
        self.grid = []

    def paintEvent(self, event):
        painter = QPainter(self)
        font = QFont(self.font())
        painter.setFont(font)
        width, height = cell_w(self), self.height()
        for column, (character, active) in enumerate(self.grid):
            rect = QRectF(column * width, 0, width, height)
            if active:
                painter.fillRect(rect, QColor(theme.BAR_FILLED))
            painter.setPen(QColor("#000000" if active else theme.BAR_EMPTY if character == "■" else theme.VALUE))
            painter.drawText(rect, int(Qt.AlignmentFlag.AlignCenter), character)
        painter.end()


class CellDescriptors(QWidget):
    """The four characteristics, each a brown label and its 16-cell row (the original's rows 20..23, columns 46..61), as
    `team_card.DescriptorCells`: the same `grid`, `labels`, `row_widgets`, `set_panel` and `content_size`. The rows are placed by
    cell in `area` (`grid` is the original's viewport, as it was)."""
    LABEL_COLS = 8
    COLS = LABEL_COLS + 1 + DESCRIPTOR_COLS

    def __init__(self):
        super().__init__()
        self.setObjectName("descriptors")
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        self.area = Cells(self.COLS, len(FIELDS), "descriptorCells")
        layout.addWidget(self.area)
        self.grid = []
        self.labels, self.row_widgets = {}, []
        for number, field in enumerate(FIELDS):
            heading = self.area.text(field, "barLabel", 0, number, self.LABEL_COLS)
            colour(heading, theme.CARD_LABEL)
            row = CellDescriptorRow()
            self.area.put(row, self.LABEL_COLS + 1, number, DESCRIPTOR_COLS)
            self.labels[field] = heading
            self.row_widgets.append(row)

    def set_panel(self, panel):
        self.grid = characteristic_view(panel["descriptors"])
        for widget, row in zip(self.row_widgets, self.grid):
            widget.grid = row
            widget.update()

    def content_size(self):
        """What the rows need: the label, a cell, 16 cells across and a row each down."""
        return QSize(int(self.COLS * cell_w(self)), row_px(self, len(FIELDS)))


class CellCharacteristics(Cells):
    """`team_card.CharacteristicPanel` in cells: the descriptors (`cells`, `labels`), the panel they were set from, its text."""

    def __init__(self):
        super().__init__(CellDescriptors.LABEL_COLS + 1 + DESCRIPTOR_COLS, len(FIELDS), "characteristics")
        self.cells = CellDescriptors()
        self.put(self.cells, 0, 0, self.cols, self.rows)
        self.labels = self.cells.labels
        self.panel = None

    def set_panel(self, panel):
        self.panel = panel
        self.cells.set_panel(panel)
        self.setAccessibleName(self.text())

    def text(self):
        return "" if self.panel is None else " · ".join(f"{d['field']} {d['text']}" for d in self.panel["descriptors"])


class CellFactsLine(Cells):
    """The average caps and age of the eleven as `squad_card.FactsTable` shows them, on one row: a brown label and its value, side
    by side. The same `labels`, `values`, `set`, `text` and `setWordWrap`."""
    LABEL_COLS, VALUE_COLS = 4, 3

    def __init__(self, cols, names=("caps", "age")):
        super().__init__(cols, 1, "factsLine")
        self.labels, self.values = {}, {}
        column = 0
        for name in names:
            label = CellLabel(name, "factLabel")
            colour(label, theme.CARD_LABEL)
            self.put(label, column, 0, self.LABEL_COLS)
            value = CellLabel("", "factValue")
            self.put(value, column + self.LABEL_COLS + 1, 0, self.VALUE_COLS)
            self.labels[name], self.values[name] = label, value
            column += self.LABEL_COLS + self.VALUE_COLS + 2

    def set(self, values, tone):
        for name, value in values.items():
            self.values[name].setText(str(value))
            colour(self.values[name], tone)

    def text(self):
        return " · ".join(f"{name} {value.text()}" for name, value in self.values.items())

    def setWordWrap(self, on):
        return None   # a value is as many cells as it needs, never a wrap of the font's


def decoded(widget, text):
    """A value of the card: `text`, or `unknown` (in the normal colour, as `undecoded`) for what the Python route has not decoded."""
    shown = "unknown" if text == NOT_DECODED else text
    widget.setText(shown)
    widget.setObjectName("undecoded" if shown in (NOT_DECODED, "unknown") else "value")


__all__ = ["CellCharacteristics", "CellDescriptorRow", "CellDescriptors", "CellFactsLine", "CellLineBars", "CellStripGlyphs",
           "decoded", "framed"]
