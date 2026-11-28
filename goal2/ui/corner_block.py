"""[designed: owner, 2026-11-28, #673; T244] The original's corner block, redrawn as the rebuild's own line-art.

[confirmed: title-load-prompt.png, E015-r0001 state 2; t156-013-hub.png, m244-squad.png, country-select.png,
bulletin.png, team-tactics.png] Every original screen carries the same block at the top left: `(c) NE'93` above,
the GOAL letters drawn as thin cyan outlines, `v.2` below. [designed: owner, 2026-11-08, #667; T244] It is drawn
with lines and the one text size, never the original's bitmap and never a larger font.
"""
from __future__ import annotations

from PySide6.QtCore import QPointF, QRectF, QSize, Qt
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import QWidget

from goal2.ui import theme
from goal2.ui.cells import cell_w, row_px


class CornerBlock(QWidget):
    """The GOAL corner: `(c) NE'93`, the four letters as line-art, `v.2`; 12 cells by 5 rows."""

    COLS, ROWS = 12, 5

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("cornerBlock")
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)

    def sizeHint(self) -> QSize:
        return QSize(round(self.COLS * cell_w(self)), row_px(self) * self.ROWS)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, False)
        cell, row = cell_w(self), row_px(self)
        painter.setPen(QColor(theme.TEXT_NORMAL))
        painter.drawText(QRectF(0, 0, self.width(), row), int(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter),
                         "(c) NE'93")
        painter.setPen(QPen(QColor(theme.HEADING), max(1, round(cell / 9))))
        top, bottom = row * 1.05, row * 3.85
        width, gap, x = cell * 2.15, cell * 0.35, cell * 0.15
        for letter in "GOAL":
            self._letter(painter, letter, x, top, width, bottom)
            x += width + gap
        painter.setPen(QColor(theme.TEXT_NORMAL))
        painter.drawText(QRectF(0, row * 4, self.width(), row), int(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter),
                         "v.2")
        painter.end()

    @staticmethod
    def _letter(painter, letter, left, top, width, bottom):
        """One block letter as a thin outline: G, O, A, L, the four the corner has."""
        right, middle, mid_y = left + width, left + width / 2, (top + bottom) / 2
        point = QPointF
        if letter == "G":
            painter.drawPolyline([point(right, top), point(left, top), point(left, bottom), point(right, bottom),
                                  point(right, mid_y), point(middle, mid_y)])
        elif letter == "O":
            painter.drawRect(QRectF(left, top, width, bottom - top))
        elif letter == "A":
            painter.drawPolyline([point(left, bottom), point(middle, top), point(right, bottom)])
            painter.drawLine(point(left + width * 0.25, mid_y), point(right - width * 0.25, mid_y))
        elif letter == "L":
            painter.drawPolyline([point(left, top), point(left, bottom), point(right, bottom)])
