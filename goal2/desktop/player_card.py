"""[designed: T88; accepted vision #266 screen 03] The complete player card, painted in the
original style: black, large monospaced type, line colours, segmented bars with the raw value
beside each. The data is goal2.game.player_card's; no attribute total is ever drawn (#286).
"""
from PySide6.QtCore import Qt, QRectF, QSize
from PySide6.QtGui import QColor, QFont, QPainter
from PySide6.QtWidgets import QWidget

# [designed: accepted #266 render.py] The palette of the accepted screens.
BLACK, WHITE, GREY = '#000000', '#eeeeee', '#aaaaaa'
RED, CYAN, YELLOW, GREEN, MAGENTA, GOLD = '#ff5555', '#55ffff', '#ffff55', '#55ff55', '#ff55ff', '#ffbb33'
EMPTY = '#9b009b'
# [confirmed: F008 DS:699A; m244-squad] a role's line colour.
LINE = {'goalkeeper': GREEN, 'defence': RED, 'midfield': CYAN, 'attack': YELLOW, 'unknown': GREY}
WIDTH, HEIGHT = 760, 640
# [designed: accepted vision #266 screen 11] Narrower than WIDTH, the card stacks its columns
# (skills, characteristics, tactics) and scrolls vertically: same type size, never clipped.
NARROW_WIDTH, NARROW_HEIGHT = 400, 1110


def bar_text(value):
    return '—' if value is None else str(value)


class PlayerCardView(QWidget):
    """One complete card; set_card(card or None). Put it in a resizable QScrollArea."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.card = None
        self.setObjectName('playerCard');self.setMinimumSize(NARROW_WIDTH, HEIGHT)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)

    @property
    def narrow(self):
        return self.width() < WIDTH

    def sizeHint(self):
        return QSize(WIDTH, HEIGHT)

    def resizeEvent(self, event):
        height = NARROW_HEIGHT if self.narrow else HEIGHT
        if self.minimumHeight() != height:self.setMinimumHeight(height)
        super().resizeEvent(event)

    def set_card(self, card):
        self.card = card
        if card is not None:
            words = ', '.join(f"{name} {word}" for name, word, _, _ in card['characteristics'])
            self.setAccessibleName(f"{card['full_name']}, {card['role']}, {card['position']}; age {card['age']}; "
                                   + '; '.join(f'{n} {bar_text(v)}' for n, v in card['skills']) + '; ' + words)
        self.update()

    def text(self, painter, x, y, value, color, size=20, bold=False):
        font = QFont('DejaVu Sans Mono');font.setStyleHint(QFont.StyleHint.Monospace)
        font.setPixelSize(size);font.setBold(bold);painter.setFont(font)
        painter.setPen(QColor(color));painter.drawText(int(x), int(y), str(value))

    def bar(self, painter, x, y, width, filled, cells):
        """[designed: accepted #266] Segmented bar: light filled cells, magenta empty ones."""
        step = width / cells
        for i in range(cells):
            colour = WHITE if filled is not None and i < filled else EMPTY
            painter.fillRect(QRectF(x + i * step + 1, y - 15, step - 2, 18), QColor(colour))

    def paintEvent(self, event):
        painter = QPainter(self);painter.fillRect(self.rect(), QColor(BLACK))
        painter.setPen(QColor(RED));painter.drawRect(1, 1, self.width() - 3, self.height() - 3)
        c = self.card
        if c is None:
            self.text(painter, 20, 40, 'Choose a player', GREY);painter.end();return
        colour = LINE[c['line']]
        self.text(painter, 16, 38, c['full_name'].upper(), colour, 28, True)
        self.text(painter, self.width() - 60, 38, c['role'], colour, 30, True)
        cards = ', '.join(c['cards']) or 'none'
        performance = 'not recorded' if c['performance'] is None else f"raw {c['performance']} (meaning not decoded)"
        header = [(f"Age {c['age']} / Caps {c['caps']} / Goals {c['goals']}", WHITE, 20)]
        if self.narrow:
            header += [(f"{c['height']} / {c['foot']}", GREEN, 20), (c['readiness'].upper(), GREEN, 20),
                       (f"National {c['position']} ({c['role']})", WHITE, 18),
                       (f"Club {c['club_position']} ({c['club_role']})", WHITE, 18),
                       (f'Cards: {cards}', WHITE, 18), (f'Performance: {performance}', WHITE, 18)]
        else:
            header += [(f"{c['height']} / {c['foot']} / {c['readiness'].upper()}", GREEN, 20),
                       (f"National {c['position']} ({c['role']}) / Club {c['club_position']} ({c['club_role']})", WHITE, 18),
                       (f'Cards: {cards} / Performance: {performance}', WHITE, 18)]
        y = 70
        for line, tone, size in header:
            self.text(painter, 16, y, line, tone, size);y += 26
        top = y + 12
        # Twelve skills: label, 25-cell bar, the original-unit value.
        for i, (name, value) in enumerate(c['skills']):
            row = top + i * 30
            self.text(painter, 16, row, name.capitalize(), GOLD, 20, True)
            self.bar(painter, 140, row, 220, value, 25)
            self.text(painter, 368, row, bar_text(value), WHITE, 20)
        # Five characteristics: label, 14-cell bar, raw value, and the original's word.
        x, top = (16, top + 12 * 30 + 20) if self.narrow else (410, top)
        bar_x = x + 150
        for i, (name, word, bar, raw) in enumerate(c['characteristics']):
            row = top + i * 50
            self.text(painter, x, row, name.capitalize(), GOLD, 20, True)
            self.bar(painter, bar_x, row, 150, bar, 14)
            self.text(painter, bar_x + 156, row, bar_text(raw), WHITE, 20)
            self.text(painter, bar_x, row + 21, word, GREEN, 16)
        top += 5 * 50 + 16
        self.text(painter, x, top, 'TACTICS / P = PERSONAL', RED, 20, True)
        rows = [(name, word + (' P' if personal else '')) for name, word, personal in c['tactics']]
        for i, (name, word) in enumerate(rows + [('mark', c['mark'] or '—')]):
            row = top + 28 + i * 28
            self.text(painter, x, row, name.capitalize(), GOLD, 20)
            self.text(painter, bar_x, row, word, GREEN, 18)
        painter.end()
