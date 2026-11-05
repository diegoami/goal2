"""S17's pitch: the original's pitch lines and surround, each player's mark coloured by side, and the ball.

[designed: owner, 2026-11-03, #526 decision 2; docs/design/ui-2026-11 S17, its mockup s17-pitch.html; T166, #540] The
pitch is a widget of the main window, painted from the pitch sample the screen has selected (`Display.frame`,
goal2/desktop/match_view.py) and nothing else: it reads no game state and drives nothing. Once a sample is painted
it reports it (`drawn`), and only then does the screen acknowledge it to the bridge (T102's pacing).

- **The geometry** is the in-play grid of the samples, |x| <= 8 rows and |y| <= 37 columns, screen = [y, x]
  [confirmed: F013, kit424d599 seg_0791_05.asm:535-598; goal2/desktop/pygame_viewer.py `GRID`], with the pygame
  viewer's margin for positions beyond the lines and its schematic boxes [designed: T94, pygame_viewer.py].
- **The marks**: the original's five display styles stepped with Up/Down, role codes by default; keepers are always a
  face, the one on the ball a filled face [confirmed: 0791:9372, 0791:05C6, 0791:0691; pygame_viewer.py `glyph`,
  `MARKS`]. One character per grid cell, the last drawn in the original's order shows [confirmed: DS:0883,
  pygame_viewer.py `DRAW_ORDER`].
- **The colours** [confirmed: 0791:1073, goal2/ui/kits.py; t156-045-kick-off.png; #583]: pitch lines grey, the
  surround green [confirmed: docs/design/ui-2026-11 §3, the table], and each side in the kit the original computes at
  kick-off from its country's colour bytes: the outfield players in the shirt, the keepers (slots 1 and 12) in the
  second colour [confirmed: 0791:045D/0691; pygame_viewer.py `kit_palette`]. The home side is the fixture's side B,
  team 1 of the samples (`DesktopModel.home`, #562) [confirmed: F031 "Venue"]; home has no colour of its own (T166
  drew it light red from one capture, where light red was Norway's kit: #583).
- **The ball** shows only on an empty cell [confirmed: 0791:8F10 draw_ball], as a small bright square, as the mockup
  draws it [designed: s17-pitch.html].
- **Space** enlarges the commentary: the whole commentary over the right part of the pitch, as the original's
  commentary page covers it [confirmed: E031 C08, C39c; match-commentary.png].

The officials are not drawn: the palette has no role for their colour [designed: T166; a design question].
"""
from __future__ import annotations

from PySide6.QtCore import QPoint, QRect, Qt
from PySide6.QtGui import QColor, QFont, QPainter, QPen
from PySide6.QtWidgets import QWidget

from goal2.desktop.pygame_viewer import DEFAULT_MARKS, DRAW_ORDER, GRID, MARGIN, glyph
from goal2.ui import theme

WIDTH, HEIGHT = 1000, 560   # [designed: s17-pitch.html, `.pitch` 1000x560]
SURROUND = 14               # the green band's depth, in page pixels [designed: s17-pitch.png]


# The samples' team that plays at home: the fixture's side B (`DesktopModel.home`) [confirmed: F031 "Venue"; #562].
HOME = 1


KEEPERS = (1, 12)   # the keepers' slots [confirmed: 0791:045D/0691; pygame_viewer.py `glyph`]


def side_colour(team: int, kits, keeper: bool = False) -> str:
    """The colour of a side's marks: its kit (goal2/ui/kits.py), the keeper in the second colour. [#583]"""
    return kits.colour(team, keeper)


class PitchWidget(QWidget):
    """Paints `screen.display.frame`; calls `on_drawn(sequence)` once a sample has been painted."""

    def __init__(self, display_source, on_drawn, family):
        super().__init__()
        self.setObjectName("pitch")
        self.setFixedSize(WIDTH, HEIGHT)
        self.page_painted = True          # repainted when the window rescales (fixed_page.apply)
        self.display_source = display_source
        self.on_drawn = on_drawn
        self.family = family
        self.marks = DEFAULT_MARKS
        self.kits = None                  # the match's kits (goal2/ui/kits.py), set by S17 at kick-off
        self.enlarged = False
        self.commentary = []              # the enlarged commentary's lines, oldest first
        self.painted = []                 # what the last paint drew: (slot, team, text, colour, QRect)

    # Geometry, in widget pixels.
    def scale(self) -> float:
        return self.width() / WIDTH

    def field(self) -> QRect:
        inset = round((SURROUND + 10) * self.scale())
        return self.rect().adjusted(inset, inset, -inset, -inset)

    def cell(self):
        field = self.field()
        return field.width() / (2 * (GRID[1] + MARGIN[1])), field.height() / (2 * (GRID[0] + MARGIN[0]))

    def at(self, gx, gy) -> QPoint:
        """A grid position (x across, y along) on the widget; beyond the drawn margin, at its edge."""
        field = self.field()
        sx, sy = self.cell()
        gx = max(-GRID[0] - MARGIN[0], min(GRID[0] + MARGIN[0], gx))
        gy = max(-GRID[1] - MARGIN[1], min(GRID[1] + MARGIN[1], gy))
        centre = field.center()
        return QPoint(round(centre.x() + gy * sx), round(centre.y() + gx * sy))

    def type_at(self, size) -> QFont:
        font = QFont(self.family)
        font.setPixelSize(max(1, round(size * self.scale())))
        return font

    # Painting.
    def paintEvent(self, event):
        painter = QPainter(self)
        try:
            self._paint(painter)
        finally:
            painter.end()
        frame = getattr(self.display_source(), "frame", None)
        if frame is not None:
            self.on_drawn(frame["sequence"])

    def _paint(self, painter):
        scale = self.scale()
        painter.fillRect(self.rect(), QColor(theme.GROUND))
        self._surround(painter, scale)
        self._lines(painter, scale)
        display = self.display_source()
        self.painted = []
        frame = getattr(display, "frame", None)
        if frame is not None:
            self._players(painter, display, frame)
        if self.enlarged:
            self._commentary(painter, scale)

    def _surround(self, painter, scale):
        """The green band round the pitch, dotted as the mockup draws it. [designed: s17-pitch.png]"""
        dot = max(1, round(4 * scale))
        step = max(2, round(10 * scale))
        band = self.rect().adjusted(dot, dot, -2 * dot, -2 * dot)
        colour = QColor(theme.PITCH_SURROUND)
        for x in range(band.left(), band.right() + 1, step):
            painter.fillRect(x, band.top(), dot, dot, colour)
            painter.fillRect(x, band.bottom(), dot, dot, colour)
        for y in range(band.top(), band.bottom() + 1, step):
            painter.fillRect(band.left(), y, dot, dot, colour)
            painter.fillRect(band.right(), y, dot, dot, colour)

    def _lines(self, painter, scale):
        """Touchlines and goal lines, the halfway line, the centre circle, the boxes and the goal mouths
        [confirmed: t156-045-kick-off.png; designed: T94, the boxes' depth 10 and half-width 5 are schematic, the
        mouth |x| < 2 is evidenced (pygame_viewer.py)]."""
        pen = QPen(QColor(theme.PITCH_LINES))
        pen.setWidth(max(1, round(2 * scale)))
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        top_left, bottom_right = self.at(-GRID[0], -GRID[1]), self.at(GRID[0], GRID[1])
        painter.drawRect(QRect(top_left, bottom_right))
        centre = self.at(0, 0)
        painter.drawLine(centre.x(), top_left.y(), centre.x(), bottom_right.y())
        sx, sy = self.cell()
        painter.drawEllipse(centre, round(4.7 * sx), round(2 * sy))
        for side in (-1, 1):
            line = self.at(0, side * GRID[1]).x()
            depth = self.at(0, side * (GRID[1] - 10)).x()
            painter.drawRect(QRect(QPoint(min(line, depth), self.at(-5, 0).y()),
                                   QPoint(max(line, depth), self.at(5, 0).y())))
            mouth = line + side * round(1.2 * sx)
            painter.drawRect(QRect(QPoint(min(line, mouth), self.at(-2, 0).y()),
                                   QPoint(max(line, mouth), self.at(2, 0).y())))

    def _players(self, painter, display, frame):
        font = self.type_at(2 * theme.CELL)
        painter.setFont(font)
        sx, sy = self.cell()
        holder = frame.get("officials", {}).get("holder")
        players = {p[0]: p for p in frame["players"]}
        occupied = {}
        for slot in DRAW_ORDER:
            _, team, number, word, px, py, _state, hidden = players[slot]
            if hidden:
                continue
            point = self.at(px, py)
            text = glyph(self.marks, slot, display.code(word, number), frame["selector"], holder)
            occupied[(point.x(), point.y())] = (slot, team, text, side_colour(team, self.kits, slot in KEEPERS))
        size = round(2 * theme.CELL * self.scale())
        for (x, y), (slot, team, text, colour) in occupied.items():
            box = QRect(x - size // 2, y - size // 2, size, size)
            painter.setPen(QColor(colour))
            painter.drawText(box, Qt.AlignmentFlag.AlignCenter, text)
            self.painted.append((slot, team, text, colour, box))
        bx, by, hidden = frame["ball"]
        ball = self.at(bx, by)
        if not hidden and (ball.x(), ball.y()) not in occupied:
            side = max(2, round(6 * self.scale()))
            painter.fillRect(ball.x() - side // 2, ball.y() - side // 2, side, side, QColor(theme.TEXT_BRIGHT))

    def _commentary(self, painter, scale):
        """Space: the whole commentary over the right part of the pitch, newest at the bottom."""
        field = self.field()
        panel = QRect(round(field.left() + field.width() * 0.45), field.top() + round(6 * scale),
                      round(field.width() * 0.55) - round(6 * scale), field.height() - round(12 * scale))
        painter.fillRect(panel, QColor(theme.GROUND))
        pen = QPen(QColor(theme.HEADING))
        pen.setWidth(max(1, round(2 * scale)))
        painter.setPen(pen)
        painter.drawRect(panel)
        painter.setFont(self.type_at(theme.CELL))
        line = round(theme.CELL * 1.5 * scale)
        rows = max(1, (panel.height() - 2 * line) // line)
        painter.setPen(QColor(theme.HEADING))
        painter.drawText(panel.left() + line, panel.top() + line, "COMMENTARY")
        painter.setPen(QColor(theme.TEXT_BRIGHT))
        for n, text in enumerate(self.commentary[-rows:]):
            painter.drawText(panel.left() + line, panel.top() + 2 * line + n * line + line // 2, text)
