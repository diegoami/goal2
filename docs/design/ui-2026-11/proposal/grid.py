"""[designed: owner, 2026-11-08; T177, #666] The character canvas the proposal screens are drawn on.

The whole point of the proposal is that GOAL2's look is a **grammar**, not a palette and a font, so
this module is the grammar and nothing else: a 90x28 grid of 16x32 cells (twice the original's
80x25 of 8x16), one text size, labels that sit on their rule, dash leaders, bars made of cells,
line-art for anything large, and a 4:3 presentation.

It is drawn with QPainter and the vendored font, offscreen, so a render is the real typeface at the
real cell and not an impression of it. It is a picture of the design, not app code; the widgets
that T162-T168 build are the place where this becomes the window.
"""
import os
import sys
from pathlib import Path

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
ROOT = Path(__file__).resolve().parents[4]
FONT = ROOT / 'docs/design/ui-2026-11/mockups/fonts/PxPlus_IBM_VGA_8x16.ttf'

from PySide6.QtCore import QRectF, Qt  # noqa: E402
from PySide6.QtGui import (QColor, QFont, QFontDatabase, QGuiApplication, QImage, QPainter,  # noqa: E402
                           QPainterPath, QPainterPathStroker, QPen)

# A font needs an application; offscreen, this starts no window.
APP = QGuiApplication.instance() or QGuiApplication(sys.argv[:1])

# The cell, and the page. Twice the original's 8x16 on 80x25 (owner's decision 1, 2026-11-08).
CW, CH = 16, 32
COLS, ROWS = 90, 28
W, H = COLS * CW, ROWS * CH                      # 1440 x 896, the logical page
ASPECT = 1.2                                     # the original's pixel aspect (owner's decision 2)

# The palette, by role, from README.md section 3 (read from the captures by palette.py).
BG = '#000000'
TEXT = '#ffffff'          # values, bright
MUTED = '#aaaaaa'         # text, normal; also the frame rule
DARK = '#555555'          # the dimmer rule
LABEL = '#aa5500'         # a frame's label, brown
RED = '#aa0000'           # a card's heading
CYAN = '#00aaaa'          # headings
HINT = '#aa00aa'          # the key hints, magenta
VALUE = '#ffff55'         # names and numbers that matter, yellow
TITLE = '#ff5555'         # the banner
GK, DEF, MID, ATT = '#00aa00', '#ff5555', '#00aaaa', '#ffff55'
BAR_FULL, BAR_EMPTY = '#aaaaaa', '#aa00aa'
GREEN = '#00aa00'
LINE = {'G': GK, 'D': DEF, 'M': MID, 'A': ATT}


class Screen:
    """A page of COLS x ROWS cells. Everything is placed in cells, never in pixels."""

    def __init__(self, cols=COLS, rows=ROWS):
        self.cols, self.rows = cols, rows
        self.image = QImage(cols * CW, rows * CH, QImage.Format.Format_RGB32)
        self.image.fill(QColor(BG))
        self.p = QPainter(self.image)
        self.p.setRenderHint(QPainter.RenderHint.Antialiasing, False)
        self.p.setRenderHint(QPainter.RenderHint.TextAntialiasing, False)
        self.family = QFontDatabase.applicationFontFamilies(
            QFontDatabase.addApplicationFont(str(FONT)))[0]

    # --- the one text size ------------------------------------------------------------------
    def font(self, pixels=CH):
        f = QFont(self.family)
        f.setPixelSize(pixels)
        f.setHintingPreference(QFont.HintingPreference.PreferNoHinting)
        f.setStyleStrategy(QFont.StyleStrategy.NoAntialias)
        return f

    def text(self, col, row, s, colour=TEXT, over=False):
        """Text at a cell. Every glyph on every screen is this size; nothing else is.

        `over` clears the cells first, so a label or a name interrupts the rule it sits on
        instead of being drawn through its dashes.
        """
        if over and s:
            self.p.fillRect(col * CW, row * CH, len(s) * CW, CH, QColor(BG))
        self.p.setFont(self.font())
        self.p.setPen(QPen(QColor(colour)))
        # The bitmap font's baseline sits at 0.8 of the cell; drawing by rect keeps the grid exact.
        self.p.drawText(QRectF(col * CW, row * CH, len(s) * CW + CW, CH),
                        int(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter), s)
        return col + len(s)

    def right(self, col_end, row, s, colour=TEXT, over=False):
        """Text ending at a cell, for a right-hand column."""
        return self.text(col_end - len(s), row, s, colour, over)

    def centre(self, col, width, row, s, colour=TEXT, over=False):
        return self.text(col + max(0, (width - len(s)) // 2), row, s, colour, over)

    def word_bar(self, col, row, cells, filled, word):
        """A characteristic: its word on the filled part, as the original prints it."""
        self.p.fillRect(col * CW, row * CH + 4, (len(word) + 1) * CW, CH - 9, QColor(BAR_FULL))
        self.text(col, row, f' {word}', '#000000')
        return self.bar(col + len(word) + 1, row, cells, filled)

    # --- rules, and labels that sit on them -------------------------------------------------
    def rule(self, col, row, width, label=None, colour=DARK, label_colour=LABEL, dash='-'):
        """A horizontal rule of dashes with its label sitting on it, lowercase, as the original's.

        `-name---------`, `-ranking-now-top-`, `----tactics-`: the label interrupts the rule and
        the rest of the line is dashes. This is the frame; there is no card and no padding.
        """
        self.text(col, row, dash * width, colour)
        if label:
            self.text(col + 1, row, label, label_colour, over=True)
        return row + 1

    def vrule(self, col, row, height, colour=DARK):
        x = col * CW + CW // 2
        self.p.setPen(QPen(QColor(colour), 2))
        self.p.drawLine(x, row * CH, x, (row + height) * CH)

    def button(self, col, row, width, height, label, colour=MUTED, text_colour=CYAN):
        """A route: a solid thin rectangle only as wide as its words, as the original's are."""
        self.p.setPen(QPen(QColor(colour), 2))
        self.p.drawRect(col * CW + CW // 2, row * CH + CH // 4,
                        (width - 1) * CW, (height - 1) * CH + CH // 2)
        self.text(col + 1 + max(0, (width - 2 - len(label)) // 2), row + height // 2,
                  label, text_colour)

    def box(self, col, row, width, height, label=None, colour=DARK, label_colour=LABEL):
        """A frame: a labelled rule on top, a plain rule at the foot, a thin side on each flank."""
        self.rule(col, row, width, label, colour, label_colour)
        self.rule(col, row + height - 1, width, None, colour)
        self.vrule(col, row + 1, height - 2, colour)
        self.vrule(col + width - 1, row + 1, height - 2, colour)

    def leader(self, col, row, width, left, right, colour=MUTED,
               left_colour=VALUE, right_colour=MUTED, dash='-'):
        """A row filled with dashes between its columns, as the original's lists are."""
        self.text(col, row, dash * width, colour)
        self.text(col, row, left, left_colour, over=True)
        self.text(col + width - len(right), row, right, right_colour, over=True)

    def highlight(self, col, row, width, s, colour=MUTED, text_colour='#000000'):
        """The cursor: a full-width light grey bar with black text, as the original's."""
        self.p.fillRect(col * CW, row * CH, width * CW, CH, QColor(colour))
        self.text(col, row, s, text_colour)

    # --- bars made of cells -----------------------------------------------------------------
    def bar(self, col, row, cells, filled, full=BAR_FULL, empty=BAR_EMPTY):
        """A bar is a row of separate cells, grey then magenta, never one continuous bar."""
        for i in range(cells):
            x = (col + i) * CW
            self.p.fillRect(x + 1, row * CH + 4, CW - 3, CH - 9,
                            QColor(full if i < filled else empty))
        return col + cells

    # --- line-art: anything larger than the one text size -----------------------------------
    def stencil(self, col, row, s, pixels=CH * 3, colour=MUTED, width=2.0):
        """A large title as outlined letters, as the original draws 'Fixtures' and 'Tactics'."""
        path = QPainterPath()
        f = self.font(pixels)
        path.addText(col * CW, row * CH + pixels * 0.82, f, s)
        stroker = QPainterPathStroker()
        stroker.setWidth(width)
        self.p.fillPath(stroker.createStroke(path), QColor(colour))

    def stencil_down(self, col, row, s, pixels=CH * 2, colour=MUTED, width=2.0):
        """The same, written downwards, as the original writes 'Tactics' on the tactics screen."""
        self.p.save()
        self.p.translate(col * CW, row * CH)
        self.p.rotate(90)
        self.stencil(0, 0, s, pixels, colour, width)
        self.p.restore()

    def blocks(self, col, row, s, pixels=CH * 4, colour=CYAN):
        """Large filled blocky glyphs: the match clock, in its corner, as the original's."""
        self.p.setFont(self.font(pixels))
        self.p.setPen(QPen(QColor(colour)))
        self.p.drawText(QRectF(col * CW, row * CH, len(s) * pixels, pixels * 1.2),
                        int(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter), s)

    def corner(self, col=0, row=0):
        """The GOAL corner block, on every screen, as the original has it."""
        self.text(col, row, '(c) NE93', MUTED)
        self.stencil(col, row + 1, 'goal', 44, CYAN, 2.0)
        self.text(col + 5, row + 3, 'v.2', MUTED)
        self.p.setPen(QPen(QColor(DARK), 2))
        self.p.drawRect(col * CW + 2, row * CH + 2, 10 * CW, 4 * CH + CH // 2)

    # --- the bottom line --------------------------------------------------------------------
    def keyline(self, left, right=(), row=None):
        """`F1help F3load goal` ... `F10quit`: key and word joined, no box, on the last row."""
        row = self.rows - 1 if row is None else row
        col = 0
        for key, word in left:
            col = self.text(col, row, key, TEXT)
            col = self.text(col, row, word, CYAN) + 1
        col = self.cols
        for key, word in reversed(right):
            col -= len(key) + len(word)
            self.text(col, row, key, TEXT)
            self.text(col + len(key), row, word, CYAN)
            col -= 1

    def hint(self, col, row, lines, colour=HINT):
        """The short magenta hint in the body of the screen, where the original puts it."""
        for i, line in enumerate(lines):
            self.text(col, row + i, line, colour)

    # --- output -----------------------------------------------------------------------------
    def save(self, path, presented=True):
        self.p.end()
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        image = self.image
        if presented:
            # The original's pixels are 1.2x taller than wide: the page is shown at 4:3.
            image = image.scaled(image.width(), round(image.height() * ASPECT),
                                 Qt.AspectRatioMode.IgnoreAspectRatio,
                                 Qt.TransformationMode.FastTransformation)
        image.save(str(path))
        return path
