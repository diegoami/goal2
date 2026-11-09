"""[designed: owner, 2026-11-08, #666, #667; T210] The frame: a rule with its lowercase label sitting on it.

[designed: owner, 2026-11-08; docs/design/ui-2026-11/fidelity-review.md §3] The original's frame is a rule with its label on
it, lowercase, brown or red, the rule continuing as dashes to the panel's edge: `-rankings-----`, `-characteristics-`. Panels
touch and nest; there is no padding, no fill and no card (a bordered box with an uppercase cyan heading inside it). The
proposal draws it (docs/design/ui-2026-11/proposal/grid.py `Screen.rule`: the dashes in the dark frame colour, the label in
brown or red over the rule, one leading dash). This is the widget that draws it, once, for every screen.

The rule **is** the frame: one row of cells, drawn glyph by glyph at the cell (`theme.CELL_W` across, a row down, at the page's
scale and stretch), never a Qt border with text drawn over it. A panel is a `Frame`: the rule on top and the body under it
(`Frame.body`, a layout with no margin and no spacing), so the panel's edge is the widget's edge and the dashes run to it.

[designed: T210] The label is lowercase whatever it is given (the grammar's), and the rule is never narrower than its label
plus the leading dash and one dash after it: `minimumSizeHint` says so, so a panel too narrow for its label is a finding of
`fixed_page.problems` (a squeezed widget), never a clipped label.
"""
from __future__ import annotations

from PySide6.QtCore import QRectF, QSize, Qt
from PySide6.QtGui import QColor, QFont, QPainter
from PySide6.QtWidgets import QSizePolicy, QVBoxLayout, QWidget

from goal2.desktop import fixed_page
from goal2.ui import theme

DASH = "-"
# [confirmed: docs/design/ui-2026-11/README.md §3 palette table: "card labels, brown" `#aa5500`, "card headings, red"
# `#aa0000`, "frame lines, dark grey" `#555555`] [designed: T210] A frame's label is brown, or red for a heading panel; its
# dashes are the dark frame colour, as the proposal draws them.
KINDS = {"brown": theme.CARD_LABEL, "red": theme.CARD_HEADING}
DASH_COLOUR = theme.FRAME_DARK


def rule_text(label: str, cols: int) -> str:
    """The rule as characters: one dash, the lowercase label, dashes to `cols` cells (`-name--------`). Never narrower than
    the label with a dash on each side."""
    label = label.lower()
    cols = max(cols, len(label) + 2)
    return DASH + label + DASH * (cols - 1 - len(label))


class FrameRule(QWidget):
    """The one-row rule of a frame, drawn at the cell. Its height is one cell row (a length the page scales)."""

    def __init__(self, label: str, kind: str = "brown", parent: QWidget | None = None):
        super().__init__(parent)
        if kind not in KINDS:
            raise ValueError(f"a frame is {' or '.join(KINDS)}, not {kind!r}")
        self.setObjectName("frameRule")
        self.label, self.kind = label.lower(), kind
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setMinimumHeight(theme.CELL_H)   # one row; apply() scales it with the page's vertical scale
        self.setMaximumHeight(theme.CELL_H)

    def cell_width(self) -> float:
        """A cell's width in pixels as this page draws it (16 at scale 1)."""
        return theme.CELL_W * fixed_page.scale_of(self)

    def cols(self) -> int:
        """The cells across the rule: the width over the cell, rounded (a page's width is a whole number of pixels)."""
        return max(1, round(self.width() / self.cell_width()))

    def text(self) -> str:
        """What is drawn, cell by cell: `-name--------` to the edge."""
        return rule_text(self.label, self.cols())

    def label_colour(self) -> str:
        return KINDS[self.kind]

    def minimumSizeHint(self) -> QSize:
        return QSize(round((len(self.label) + 2) * self.cell_width()), self.minimumHeight())

    def sizeHint(self) -> QSize:
        return self.minimumSizeHint()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor(theme.GROUND))
        font = QFont(self.font())   # the page's font: its pixel size and stretch are the page's cell
        font.setStyleStrategy(QFont.StyleStrategy.NoAntialias)
        painter.setFont(font)
        width = self.cell_width()
        height = self.height()
        for index, glyph in enumerate(self.text()):
            on_label = 1 <= index <= len(self.label)
            painter.setPen(QColor(self.label_colour() if on_label else DASH_COLOUR))
            # One glyph in one cell, so a platform whose font engine rounds the advance cannot move the next one.
            painter.drawText(QRectF(index * width, 0, width, height), int(Qt.AlignmentFlag.AlignCenter), glyph)
        painter.end()


class Frame(QWidget):
    """A panel: its rule on top, its body under it. No margin, no spacing, no border: the rule is the frame."""

    def __init__(self, label: str, kind: str = "brown", parent: QWidget | None = None):
        super().__init__(parent)
        self.setObjectName("frame")
        self.rule = FrameRule(label, kind)
        self.body = QVBoxLayout()
        self.body.setContentsMargins(0, 0, 0, 0)
        self.body.setSpacing(0)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self.rule, 0, Qt.AlignmentFlag.AlignTop)   # on top, whatever the body (or its absence) leaves
        layout.addLayout(self.body, 1)

    @property
    def label(self) -> str:
        return self.rule.label

    def add(self, widget: QWidget, stretch: int = 0) -> QWidget:
        """Put `widget` in the panel under the rule."""
        self.body.addWidget(widget, stretch)
        return widget
