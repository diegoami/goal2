"""[designed: T91; accepted vision #266 screens 02/03] The twenty in the original's style.

Each row: + in the XI or - on the bench, the initial and name in the line colour of the
player's role, the one-letter code, and C for the captain. The rows come from the window's
draft, never from a separate copy: the view only reads and reports what the player does.
"""
from PySide6.QtCore import Qt, QSize, Signal
from PySide6.QtGui import QColor, QFont, QFontMetrics, QPainter
from PySide6.QtWidgets import QWidget
from goal2.desktop.player_card import BLACK, GREY, CYAN, LINE

ROW, TOP = 30, 46
WIDTH = 360


class RosterView(QWidget):
    """rows: [(word, name, code, line, in_xi, captain)]. Signals: current_changed(row);
    toggled(row) for Space or a double click when the view toggles the XI; activated(row) for
    Enter, or a double click when it does not."""
    current_changed = Signal(int)
    toggled = Signal(int)
    activated = Signal(int)

    def __init__(self, title='SQUAD', parent=None, toggles=True):
        super().__init__(parent)
        self.title = title;self.rows = [];self.current = -1;self.toggles = toggles
        self.setObjectName('roster');self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setMinimumSize(300, TOP + 20 * ROW + 12)

    def sizeHint(self):
        return QSize(WIDTH, TOP + 20 * ROW + 12)

    def set_rows(self, rows, current=None):
        self.rows = list(rows)
        if current is not None:self.current = current
        self.current = min(self.current, len(self.rows) - 1)
        xi = sum(1 for r in self.rows if r[4])
        self.setAccessibleName(f'{self.title} {len(self.rows)}, XI {xi}, bench {len(self.rows) - xi}; '
                               + '; '.join(self.row_text(r) for r in self.rows))
        self.update()

    @staticmethod
    def row_text(row):
        _, name, code, _, in_xi, captain = row
        return ('+ ' if in_xi else '- ') + name + ' ' + code + (' C' if captain else '')

    def set_current(self, row, notify=True):
        if not self.rows or row == self.current or not 0 <= row < len(self.rows):return
        self.current = row;self.update()
        if notify:self.current_changed.emit(row)

    def keyPressEvent(self, event):
        key = event.key()
        if key in (Qt.Key.Key_Down, Qt.Key.Key_Up):
            self.set_current(max(0, min(len(self.rows) - 1, self.current + (1 if key == Qt.Key.Key_Down else -1))))
        elif key in (Qt.Key.Key_Home, Qt.Key.Key_End):
            self.set_current(0 if key == Qt.Key.Key_Home else len(self.rows) - 1)
        elif key == Qt.Key.Key_Space and self.toggles and self.current >= 0:
            self.toggled.emit(self.current)
        elif key in (Qt.Key.Key_Return, Qt.Key.Key_Enter) and self.current >= 0:
            self.activated.emit(self.current)
        else:
            super().keyPressEvent(event)

    def row_at(self, y):
        row = int((y - TOP + ROW - 8) // ROW)
        return row if 0 <= row < len(self.rows) else -1

    def mousePressEvent(self, event):
        self.setFocus(Qt.FocusReason.MouseFocusReason)
        self.set_current(self.row_at(event.position().y()))

    def mouseDoubleClickEvent(self, event):
        row = self.row_at(event.position().y())
        if row >= 0:(self.toggled if self.toggles else self.activated).emit(row)

    def paintEvent(self, event):
        painter = QPainter(self);painter.fillRect(self.rect(), QColor(BLACK))
        painter.setPen(QColor('#ffff55' if self.hasFocus() else CYAN))
        painter.drawRect(1, 1, self.width() - 3, self.height() - 3)
        font = QFont('DejaVu Sans Mono');font.setStyleHint(QFont.StyleHint.Monospace)
        font.setPixelSize(20);font.setBold(True);painter.setFont(font);metrics = QFontMetrics(font)
        xi = sum(1 for r in self.rows if r[4])
        painter.setPen(QColor(CYAN));title = QFont(font);title.setPixelSize(17);painter.setFont(title)
        painter.drawText(14, 30, f'{self.title} {len(self.rows)} / XI {xi} / BENCH {len(self.rows) - xi}')
        painter.setFont(font);code_x = self.width() - 64
        for i, (_, name, code, line, in_xi, captain) in enumerate(self.rows):
            y = TOP + 20 + i * ROW
            colour = QColor(LINE.get(line, GREY))
            if i == self.current:
                painter.fillRect(10, y - 22, self.width() - 20, ROW - 2, QColor(GREY));colour = QColor(BLACK)
            painter.setPen(QColor(BLACK) if i == self.current else QColor(LINE['goalkeeper'] if in_xi else LINE['defence']))
            painter.drawText(14, y, '+' if in_xi else '-')
            painter.setPen(colour)
            painter.drawText(40, y, metrics.elidedText(name, Qt.TextElideMode.ElideRight, code_x - 48))
            painter.drawText(code_x, y, code + (' C' if captain else ''))
        painter.end()


class Columns(QWidget):
    """[designed: T91; accepted vision #266 screen 11] Side by side when wide, stacked when not."""

    def __init__(self, breakpoint, parent=None):
        super().__init__(parent)
        from PySide6.QtWidgets import QBoxLayout
        self.breakpoint = breakpoint
        self.box = QBoxLayout(QBoxLayout.Direction.LeftToRight, self)
        self.box.setContentsMargins(0, 0, 0, 0);self.box.setSpacing(16)

    def arrange(self, width):
        """Choose the arrangement for this width. The window calls it as soon as it is resized,
        so a page laid out while hidden does not change height after it is shown."""
        from PySide6.QtWidgets import QBoxLayout
        direction = QBoxLayout.Direction.LeftToRight if width >= self.breakpoint else QBoxLayout.Direction.TopToBottom
        if self.box.direction() != direction:self.box.setDirection(direction)

    def resizeEvent(self, event):
        self.arrange(self.width())
        super().resizeEvent(event)

    def minimumSizeHint(self):
        # Stacked, the columns need only the widest one's width.
        from PySide6.QtWidgets import QBoxLayout
        hint = super().minimumSizeHint()
        if self.box.direction() == QBoxLayout.Direction.LeftToRight:
            widths = [self.box.itemAt(i).minimumSize().width() for i in range(self.box.count())]
            hint.setWidth(max(widths or [0]))
        return hint
