"""[designed: owner playtest, 2026-11-16, #754; T215] Connected fine panel rules with lowercase labels.

[confirmed: docs/original-game/images/t156-006-name-entry.png and t156-124-halftime-bench.png] The original separates
panels and columns with connected horizontal and vertical lines. The owner requested these boundaries in the playtest.
`FrameRule` interrupts a horizontal rule with its brown/red label and joins the sides; `Frame` continues the sides and
bottom. [designed: owner playtest #778] Foreground outlines keep content from painting over those edges.
Lines are painted without Qt borders, added padding or a body fill, preserving every cell of content.

[designed: T210, retained] The one-row heading and minimum label width remain on the 16 x 32 grid; a panel narrower
than its complete label is reported by fixed_page.problems, never clipped. The textual rule API stays `-label---`.
"""
from __future__ import annotations

from PySide6.QtCore import QEvent, QRectF, QSize, Qt
from PySide6.QtGui import QColor, QFont, QPainter
from PySide6.QtWidgets import QSizePolicy, QVBoxLayout, QWidget

from goal2.desktop import fixed_page
from goal2.ui import cells, theme

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


class PanelOutline(QWidget):
    """[designed: owner playtest #778] Foreground rules that content cannot erase.

    A transparent, mouse-transparent layer preserves content geometry and input.
    Parent painting alone sits behind opaque child widgets and selected rows.
    """
    def __init__(self, parent, segments):
        super().__init__(parent)
        self.setObjectName('panelOutline')
        self._segments=segments
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.setStyleSheet('background: transparent;')
        parent.installEventFilter(self)
        self._place()
        self.show()

    def _place(self):
        self.setGeometry(self.parentWidget().rect())
        self.raise_()
        self.update()

    def eventFilter(self, watched, event):
        if event.type() in (QEvent.Type.Resize, QEvent.Type.Show,
                            QEvent.Type.ChildAdded, QEvent.Type.LayoutRequest):
            self._place()
        return False

    def paintEvent(self, event):
        painter=QPainter(self)
        painter.setPen(QColor(theme.FRAME))
        for line in self._segments():
            painter.drawLine(*line)
        painter.end()


class FrameRule(QWidget):
    """The one-row rule of a frame, drawn at the cell. Its height is one cell row (`cells.row_px`)."""

    def __init__(self, label: str, kind: str = "brown", parent: QWidget | None = None):
        super().__init__(parent)
        if kind not in KINDS:
            raise ValueError(f"a frame is {' or '.join(KINDS)}, not {kind!r}")
        self.setObjectName("frameRule")
        self.label, self.kind = label.lower(), kind
        # One row. [designed: T211] Its height is the page's row (`cells.row_px`, the cell rounded down) by the size hint of a fixed
        # policy, not a pair of recorded lengths that `fixed_page.apply` rounds to nearest: 28 rows must never exceed the page (at the
        # scale 0.98 a clamped Windows window has, a cell is 37.65 pixels and the nearest is 38).
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        # [designed: T211] The widget's colour is its label's, so what reads a widget's colour (the palette) reads the rule's
        # (the style sheet's `*` rule would otherwise make it white).
        self.setStyleSheet(f"color: {self.label_colour()};")

    def cell_width(self) -> float:
        """A cell's width in pixels as this page draws it (16 at scale 1)."""
        return theme.CELL_W * fixed_page.scale_of(self)

    def cols(self) -> int:
        """The cells across the rule: the width over the cell, rounded (a page's width is a whole number of pixels)."""
        return max(1, round(self.width() / self.cell_width()))

    def text(self) -> str:
        """What is drawn, cell by cell: `-name--------` to the edge."""
        return rule_text(self.label, self.cols())

    def setText(self, text: str) -> None:
        """[designed: T213, #667] A changing panel heading uses the same lowercase rule as a static one."""
        self.label = text.lower()
        self.updateGeometry()
        self.update()

    def label_colour(self) -> str:
        return KINDS[self.kind]

    def minimumSizeHint(self) -> QSize:
        # floor: a rounded edge never squeezes it
        return QSize(int((len(self.label) + 2) * self.cell_width()), cells.row_px(self))

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
        # [designed: owner playtest, #754] A connected fine rule, with the label interrupting it.
        middle = self.height() // 2
        painter.setPen(QColor(DASH_COLOUR))
        painter.drawLine(0, middle, self.width()-1, middle)
        for index, glyph in enumerate(self.label, 1):
            rect = QRectF(index * width, 0, width, height)
            painter.fillRect(rect, QColor(theme.GROUND))
            painter.setPen(QColor(self.label_colour()))
            painter.drawText(rect, int(Qt.AlignmentFlag.AlignCenter), glyph)
        painter.setPen(QColor(theme.FRAME))
        painter.drawLine(0,middle,0,self.height()-1)
        painter.drawLine(self.width()-1,middle,self.width()-1,self.height()-1)
        painter.end()


class Frame(QWidget):
    """A connected outline and labelled rule, without layout margins, spacing or a body fill."""

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
        self.outline=PanelOutline(self,self._outline_segments)

    def _outline_segments(self):
        top=max(0,self.rule.height()//2);bottom=self.height()-1;right=self.width()-1
        return ((0,top,0,bottom),(right,top,right,bottom),(0,bottom,right,bottom))

    @property
    def label(self) -> str:
        return self.rule.label

    def set_label(self, label: str) -> None:
        """A new label on the rule (a panel whose title is its content: a strip's country). [designed: T211]"""
        self.rule.label = label.lower()
        self.rule.updateGeometry()
        self.rule.update()

    def add(self, widget: QWidget, stretch: int = 0) -> QWidget:
        """Put `widget` in the panel under the rule."""
        self.body.addWidget(widget, stretch)
        return widget
