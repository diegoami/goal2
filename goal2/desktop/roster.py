"""[designed: T91; accepted vision #266 screens 02/03] The twenty in the original's style.

Each row: + in the XI or - on the bench, the initial and name in the line colour of the
player's role, the one-letter code, and C for the captain. The rows come from the window's
draft, never from a separate copy: the view only reads and reports what the player does.
"""
from PySide6.QtCore import Qt, QSize, Signal
from PySide6.QtGui import QColor, QFont, QFontMetrics, QPainter
from PySide6.QtWidgets import QWidget
from goal2.desktop.player_card import BLACK, GREY, CYAN, LINE

# [designed: T101] Rows of 26 page pixels: the twenty and the rule fit the fixed page beside the
# card, as in the original's squad screen [confirmed: `docs/original-game/images/m244-squad.png`].
ROW, TOP = 26, 46
WIDTH = 320
# [designed: T99] The gap holding the rule between the eleven and the bench.
RULE = 16


class RosterView(QWidget):
    """rows: [(word, name, code, line, in_xi, captain)]. Signals: current_changed(row);
    toggled(row) for Space or a double click when the view toggles the XI; activated(row) for
    Enter, or a double click when it does not."""
    current_changed = Signal(int)
    toggled = Signal(int)
    activated = Signal(int)

    def __init__(self, title='SQUAD', parent=None, toggles=True, capacity=20, marks=True, grouped=False):
        super().__init__(parent)
        self.title = title;self.rows = [];self.current = -1;self.toggles = toggles
        # [designed: T99; confirmed: `docs/original-game/images/m244-squad.png`] A grouped roster
        # is the original's strip: the eleven in the draft's order, a rule, then the bench; an
        # unavailable player is marked. `order` lists row indices in display order.
        self.grouped = grouped;self.order = [];self.unavailable = set()
        # [designed: T95] A fixed caption (e.g. "GREECE / 4-4-2") instead of the squad counts.
        self.caption = None
        self.setObjectName('roster');self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        # [designed: T95] A line-up holds eleven rows and needs no XI marks.
        self.capacity = capacity;self.marks = marks

    # [designed: T101] The strip is painted in page pixels through a scaled painter; its sizes and
    # its rows' rectangles are the page's, times the page scale (goal2/desktop/fixed_page.py).
    page_painted = True

    def scale(self):
        from goal2.desktop.fixed_page import scale_of
        return scale_of(self)

    def full_height(self):
        return TOP + self.capacity * ROW + 12 + (RULE if self.grouped else 0)

    def sizeHint(self):
        s = self.scale()
        return QSize(round(WIDTH * s), round(self.full_height() * s))

    def minimumSizeHint(self):
        s = self.scale()
        return QSize(round(300 * s), round(self.full_height() * s))

    def set_rows(self, rows, current=None, order=None, unavailable=()):
        self.rows = list(rows)
        if current is not None:self.current = current
        self.current = min(self.current, len(self.rows) - 1)
        if self.grouped and order is None:
            order = [i for i, r in enumerate(self.rows) if r[4]] + [i for i, r in enumerate(self.rows) if not r[4]]
        self.order = list(order) if order is not None else list(range(len(self.rows)))
        self.unavailable = set(unavailable)
        xi = sum(1 for r in self.rows if r[4])
        self.setAccessibleName(f'{self.title} {len(self.rows)}, XI {xi}, bench {len(self.rows) - xi}; '
                               + '; '.join(self.row_text(self.rows[i]) + (' unavailable' if self.rows[i][0] in self.unavailable else '')
                                           for i in self.order))
        self.update()

    @staticmethod
    def row_text(row):
        _, name, code, _, in_xi, captain = row
        return ('+ ' if in_xi else '- ') + name + ' ' + code + (' C' if captain else '')

    def eleven(self):
        """How many displayed rows come before the rule."""
        return sum(1 for r in self.rows if r[4]) if self.grouped else len(self.rows)

    def baseline(self, position):
        """The text baseline of display position `position`."""
        return TOP + 18 + position * ROW + (RULE if self.grouped and position >= self.eleven() else 0)

    def row_rect(self, row):
        """[designed: T99] The rectangle row index `row` is painted in, in widget pixels."""
        from PySide6.QtCore import QRect
        s = self.scale();y = self.baseline(self.order.index(row))
        return QRect(round(10 * s), round((y - 20) * s), self.width() - round(20 * s), round((ROW - 2) * s))

    def set_current(self, row, notify=True):
        if not self.rows or row == self.current or not 0 <= row < len(self.rows):return
        self.current = row;self.update()
        if notify:self.current_changed.emit(row)

    def keyPressEvent(self, event):
        key = event.key()
        position = self.order.index(self.current) if self.current in self.order else 0
        if key in (Qt.Key.Key_Down, Qt.Key.Key_Up) and self.order:
            self.set_current(self.order[max(0, min(len(self.order) - 1, position + (1 if key == Qt.Key.Key_Down else -1)))])
        elif key in (Qt.Key.Key_Home, Qt.Key.Key_End) and self.order:
            self.set_current(self.order[0 if key == Qt.Key.Key_Home else -1])
        elif key == Qt.Key.Key_Space and self.toggles and self.current >= 0:
            self.toggled.emit(self.current)
        elif key in (Qt.Key.Key_Return, Qt.Key.Key_Enter) and self.current >= 0:
            self.activated.emit(self.current)
        else:
            super().keyPressEvent(event)

    def row_at(self, y):
        y = y / self.scale()
        for position, row in enumerate(self.order):
            top = self.baseline(position) - 20
            if top <= y < top + ROW:return row
        return -1

    def mousePressEvent(self, event):
        self.setFocus(Qt.FocusReason.MouseFocusReason)
        row = self.row_at(event.position().y())
        # [designed: T99] A click on the current row reports it again, so a listener that has no
        # selection yet (the hidden table) follows the strip.
        if row >= 0 and row == self.current:self.current_changed.emit(row)
        else:self.set_current(row)

    def mouseDoubleClickEvent(self, event):
        row = self.row_at(event.position().y())
        if row >= 0:(self.toggled if self.toggles else self.activated).emit(row)

    def paintEvent(self, event):
        painter = QPainter(self);painter.fillRect(self.rect(), QColor(BLACK))
        s = self.scale();painter.scale(s, s);width = self.width() / s;height = self.height() / s
        painter.setPen(QColor('#ffff55' if self.hasFocus() else CYAN))
        painter.drawRect(1, 1, round(width) - 3, round(height) - 3)
        font = QFont('DejaVu Sans Mono');font.setStyleHint(QFont.StyleHint.Monospace)
        font.setPixelSize(20);font.setBold(True);painter.setFont(font);metrics = QFontMetrics(font)
        xi = sum(1 for r in self.rows if r[4])
        painter.setPen(QColor(CYAN));title = QFont(font);title.setPixelSize(17);painter.setFont(title)
        painter.drawText(14, 30, self.caption or f'{self.title} {len(self.rows)} / XI {xi} / BENCH {len(self.rows) - xi}')
        painter.setFont(font);code_x = round(width) - 64
        if self.grouped:
            rule = self.baseline(self.eleven()) - 20 - RULE // 2
            painter.setPen(QColor(CYAN));painter.drawLine(10, rule, round(width) - 10, rule)
        for position, i in enumerate(self.order):
            _, name, code, line, in_xi, captain = self.rows[i]
            y = self.baseline(position)
            colour = QColor(LINE.get(line, GREY))
            if i == self.current:
                painter.fillRect(10, y - 20, round(width) - 20, ROW - 2, QColor(GREY));colour = QColor(BLACK)
            painter.setPen(QColor(BLACK) if i == self.current else QColor(LINE['goalkeeper'] if in_xi else LINE['defence']))
            if self.marks:
                painter.drawText(14, y, '+' if in_xi else '-')
            elif self.rows[i][0] in self.unavailable:
                painter.setPen(QColor(BLACK) if i == self.current else QColor('#ff55ff'))
                painter.drawText(14, y, '!')
            painter.setPen(colour)
            painter.drawText(40, y, metrics.elidedText(name, Qt.TextElideMode.ElideRight, code_x - 48))
            painter.drawText(code_x, y, code + (' C' if captain else ''))
        painter.end()
