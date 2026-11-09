"""[designed: owner, 2026-11-08, #667, #668; T211] The parts a screen on the 16 x 32 grid is made of: text in cells, panels placed by cell.

[designed: owner, 2026-11-08; docs/design/ui-2026-11/fidelity-review.md §3] A screen is 90 x 28 cells; every edge of a panel is
a whole number of cells, separation is one empty cell and nothing is padded (T210's `grid_check` says which widget is off the
cell). The page is a fixed 90 x 28 whatever the window (goal2/desktop/fixed_page.py scales it as a whole), so a screen on the
grid places its panels **by cell**, not by the size a font's line box happens to have:

- `CellLabel` is a line of text one row high whose size is its text's cells (a character is a cell wide, a line a row high), not
  the font's measured line box. A platform's font may round the advance or add a pixel to a line (a measured Windows runner did:
  T209); the cell is what the page draws, so the label's size does not move with it.
- `CellPara` is a paragraph wrapped to its width in cells, a row to a line.
- `Cells` is a widget whose children are placed by cell (`put(widget, col, row, cols, rows)`), through `CellGrid`, a layout that
  turns a cell into the page's pixels (the rounded edge of its column and row) and never into a measured size.

[designed: T211] A cell is `theme.CELL_W` x `theme.CELL_H` logical pixels, drawn at the page's horizontal scale and at the
vertical one (scale x the 4:3 stretch): 16 x 38.4 pixels at scale 1. A row's pixels are `row_px`, rounded down, and the rows
of a panel add up to its height; across, an edge is the rounded multiple of the exact cell.
"""
from __future__ import annotations

import html
import re
import textwrap

from PySide6.QtCore import QRect, QSize, Qt
from PySide6.QtGui import QColor, QPainter
from PySide6.QtWidgets import QLabel, QLayout, QLineEdit, QSizePolicy, QWidget, QWidgetItem

from goal2.desktop import fixed_page
from goal2.ui import theme

_TAGS = re.compile(r"<[^>]*>")


def cell_w(widget) -> float:
    """A cell's width in pixels as the page `widget` is on draws it (16 at scale 1)."""
    return theme.CELL_W * fixed_page.scale_of(widget)


def cell_h(widget) -> float:
    """A row's height in pixels as the page draws it, exact (38.4 at scale 1: the 1.2 stretch)."""
    return theme.CELL_H * fixed_page.scale_y_of(widget)


def row_px(widget, rows: int = 1) -> int:
    """`rows` rows in whole pixels: a row is the cell's height rounded **down** (38 at scale 1, 43 at 1.12), so rows stacked add up as
    the layout adds them and 28 of them never exceed the page (rounded up, 28 rows are 5 pixels too many at the scale 0.98 a clamped
    Windows window has, where a cell is 37.65 pixels)."""
    return rows * max(1, int(cell_h(widget) + 1e-6))


def span_px(widget, rows: int) -> int:
    """The height of a panel of `rows` rows as the page's own height is made (the exact cell times the rows, rounded: 77 for two
    rows at scale 1, where `row_px` stacks 38 and 38): what a bar at the foot of the page is, so the body between the title row and
    the bar takes up the page's 4:3 slack and nothing else."""
    return max(1, round(rows * cell_h(widget)))


def plain(text: str) -> str:
    """The characters a label's text draws: rich text without its tags."""
    return html.unescape(_TAGS.sub("", text))


class CellLabel(QLabel):
    """A line of text one row high. Its size is its characters' cells, never the font's line box."""

    def __init__(self, text: str = "", name: str = "", parent=None, reserve: int = 0):
        super().__init__(text, parent)
        if name:
            self.setObjectName(name)
        self.reserve = reserve   # cells the label keeps whatever its text (a column that other rows share)
        self.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)

    def cols(self) -> int:
        """The cells the text takes: one per character (the widest line when it has several)."""
        lines = plain(self.text()).split("\n")
        return max(self.reserve, *(len(line) for line in lines))

    def sizeHint(self) -> QSize:
        return QSize(int(self.cols() * cell_w(self)), row_px(self))   # a pixel under the exact cells: a rounded edge never squeezes it

    def minimumSizeHint(self) -> QSize:
        return self.sizeHint()


class CellPara(QLabel):
    """A paragraph in cells: the text wrapped at the characters its width holds, a row to a line, drawn line by line."""

    def __init__(self, text: str = "", name: str = "", parent=None):
        super().__init__("", parent)
        if name:
            self.setObjectName(name)
        self.setWordWrap(True)
        self.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        self.setText(text)

    def columns(self, width: int | None = None) -> int:
        width = self.width() if width is None else width
        return max(1, int(width / cell_w(self) + 0.5))

    def lines(self, width: int | None = None) -> list[str]:
        text = plain(self.text())
        out: list[str] = []
        for part in text.split("\n"):
            out.extend(textwrap.wrap(part, self.columns(width), drop_whitespace=True) or [""] if text else [])
        return out

    def hasHeightForWidth(self) -> bool:
        return True

    def heightForWidth(self, width: int) -> int:
        return row_px(self, len(self.lines(width)))

    def sizeHint(self) -> QSize:
        return QSize(round(30 * cell_w(self)), row_px(self, max(1, len(self.lines()))))

    def minimumSizeHint(self) -> QSize:
        return QSize(round(cell_w(self)), row_px(self, 1))

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setFont(self.font())
        painter.setPen(QColor(self.palette().color(self.foregroundRole())))
        for index, line in enumerate(self.lines()):
            top = round(index * cell_h(self))
            across = self.alignment() & Qt.AlignmentFlag.AlignHorizontal_Mask   # left unless the paragraph was given another (T212)
            painter.drawText(QRect(0, top, self.width(), row_px(self)), int(across | Qt.AlignmentFlag.AlignVCenter), line)
        painter.end()


class CellGrid(QLayout):
    """Children placed by cell inside a `cols` x `rows` area: a column's left edge is `round(col x cell)` across and a row's top
    edge is `row x row height` down. The cell across is the area's width over `cols`; the row's height is the page's, rounded to
    whole pixels (`row_px`, 38 at scale 1: T210's check accepts the cell rounded down), so a page whose height is a few pixels over
    its rows (the 4:3 slack) keeps its rows whole and the slack falls under the last of them."""

    def __init__(self, parent: QWidget, cols: int, rows: int):
        super().__init__(parent)
        self.cols, self.rows = cols, rows
        self.items: list[tuple[QWidgetItem, tuple[int, int, int, int]]] = []
        self.setContentsMargins(0, 0, 0, 0)

    def addItem(self, item) -> None:   # QLayout's own: a plain item takes the whole area
        self.items.append((item, (0, 0, self.cols, self.rows)))

    def put(self, widget: QWidget, col: int, row: int, cols: int, rows: int = 1) -> QWidget:
        self.addChildWidget(widget)
        self.items.append((QWidgetItem(widget), (col, row, cols, rows)))
        self.invalidate()
        return widget

    def move(self, widget: QWidget, col: int, row: int, cols: int, rows: int = 1) -> None:
        for index, (item, _) in enumerate(self.items):
            if item.widget() is widget:
                self.items[index] = (item, (col, row, cols, rows))
                self.invalidate()
                return
        raise ValueError(f"{widget!r} is not placed in this grid")

    def count(self) -> int:
        return len(self.items)

    def itemAt(self, index: int):
        return self.items[index][0] if 0 <= index < len(self.items) else None

    def takeAt(self, index: int):
        return self.items.pop(index)[0] if 0 <= index < len(self.items) else None

    def expandingDirections(self):
        return Qt.Orientation.Horizontal | Qt.Orientation.Vertical

    def pitch(self, rect: QRect) -> tuple[float, float]:
        owner = self.parentWidget()
        across = rect.width() / max(1, self.cols)
        whole = row_px(owner)   # a row is whole pixels (38 at scale 1), so nested panels add up with no rounding
        down = min(whole, rect.height() / max(1, self.rows)) if rect.height() > 0 else whole
        return across, down

    def setGeometry(self, rect: QRect) -> None:
        super().setGeometry(rect)
        across, down = self.pitch(rect)
        for item, (col, row, cols, rows) in self.items:
            left, right = round(col * across), round((col + cols) * across)
            top, bottom = round(row * down), round((row + rows) * down)   # `down` is whole unless the area is short
            item.setGeometry(QRect(rect.x() + left, rect.y() + top, right - left, bottom - top))

    def sizeHint(self) -> QSize:
        return self.minimumSize()

    def minimumSize(self) -> QSize:
        owner = self.parentWidget()
        # A pixel under the exact cells: a parent that hands out rounded edges is never squeezed by a rounding.
        return QSize(max(0, int(self.cols * cell_w(owner)) - 1), max(0, row_px(owner, self.rows) - 1))


class Cells(QWidget):
    """A `cols` x `rows` area whose children are placed by cell."""

    def __init__(self, cols: int, rows: int, name: str = "cells", parent=None):
        super().__init__(parent)
        self.setObjectName(name)
        self.grid = CellGrid(self, cols, rows)
        self.cols, self.rows = cols, rows

    def put(self, widget: QWidget, col: int, row: int, cols: int, rows: int = 1) -> QWidget:
        widget.setParent(self)
        return self.grid.put(widget, col, row, cols, rows)

    def move(self, widget: QWidget, col: int, row: int, cols: int, rows: int = 1) -> None:
        self.grid.move(widget, col, row, cols, rows)

    def text(self, text: str, name: str, col: int, row: int, cols: int | None = None) -> CellLabel:
        """A one-row label at a cell, `cols` wide (as many as its text has by default)."""
        widget = CellLabel(text, name)
        return self.put(widget, col, row, cols if cols is not None else max(1, len(plain(text))))


class CellEdit(QLineEdit):
    """A one-row line edit: its size is a row, never the font's line box and the frame's margins."""

    def sizeHint(self) -> QSize:
        return QSize(round(8 * cell_w(self)), row_px(self))

    def minimumSizeHint(self) -> QSize:
        return QSize(round(cell_w(self)), row_px(self))


__all__ = ["CellEdit", "CellGrid", "CellLabel", "CellPara", "Cells", "cell_h", "cell_w", "plain", "row_px"]
