"""[designed: T88; accepted vision #266 screen 03] The complete player card, painted in the
original style: black, large monospaced type, line colours, segmented bars. The data is
goal2.game.player_card's; no attribute total is ever drawn (#286).

[designed: owner, 2026-10-21, T99 "no numbers when you can have bars"; confirmed:
`docs/original-game/images/m244-squad.png`] As in the original, a skill is its bar alone, and a
characteristic is its bar with the descriptor word inside it; the raw values stay in the
accessible name.
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
# [designed: T101] The card is composed for the fixed page: the name, four header lines, then the
# twelve skills on the left and the tactics above the five characteristics on the right, as the
# original's squad screen [confirmed: `docs/original-game/images/m244-squad.png`]. It is painted in
# page pixels through a scaled painter (goal2/desktop/fixed_page.py).
WIDTH, HEIGHT = 760, 530
# [designed: accepted vision #266 screen 11] Narrower than WIDTH, the card stacks its columns
# (skills, characteristics, tactics). [designed: T101] The fixed page always gives the card its
# full width; the stacked form remains for a card shown alone in a narrow widget.
NARROW_WIDTH, NARROW_HEIGHT = 400, 1110


def bar_text(value):
    return '—' if value is None else str(value)


class PlayerCardView(QWidget):
    """One complete card; set_card(card or None)."""
    page_painted = True

    def __init__(self, parent=None):
        super().__init__(parent)
        self.card = None;self.drawn = [];self.bottom = 0
        self.setObjectName('playerCard')
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)

    def scale(self):
        from goal2.desktop.fixed_page import scale_of
        return scale_of(self)

    def logical_width(self):
        return self.width() / self.scale()

    @property
    def narrow(self):
        return self.logical_width() < WIDTH - 0.5

    def sizeHint(self):
        s = self.scale()
        return QSize(round(WIDTH * s), round(HEIGHT * s))

    def minimumSizeHint(self):
        return self.sizeHint()

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
        self.drawn.append(str(value))
        # [designed: T101] The lowest painted line, for the check that nothing falls below the card.
        self.bottom = max(self.bottom, int(y) + painter.fontMetrics().descent())

    def fitted(self, value, width, size, bold=True):
        """The largest pixel size up to `size` at which `value` fits `width` (never elided)."""
        from PySide6.QtGui import QFontMetrics
        while size > 10:
            font = QFont('DejaVu Sans Mono');font.setStyleHint(QFont.StyleHint.Monospace)
            font.setPixelSize(size);font.setBold(bold)
            if QFontMetrics(font).horizontalAdvance(value) <= width:break
            size -= 1
        return size

    def bar(self, painter, x, y, width, filled, cells):
        """[designed: accepted #266] Segmented bar: light filled cells, magenta empty ones."""
        step = width / cells
        for i in range(cells):
            colour = WHITE if filled is not None and i < filled else EMPTY
            painter.fillRect(QRectF(x + i * step + 1, y - 15, step - 2, 18), QColor(colour))

    def paintEvent(self, event):
        # Every string painted, for the checks that no number stands beside a bar.
        self.drawn = [];self.bottom = 0
        painter = QPainter(self);painter.fillRect(self.rect(), QColor(BLACK))
        s = self.scale();painter.scale(s, s);width = round(self.width() / s)
        painter.setPen(QColor(RED));painter.drawRect(1, 1, width - 3, round(self.height() / s) - 3)
        c = self.card
        if c is None:
            self.text(painter, 20, 40, 'Choose a player', GREY);painter.end();return
        colour = LINE[c['line']]
        name = c['full_name'].upper()
        self.text(painter, 16, 38, name, colour, self.fitted(name, width - 100, 28), True)
        self.text(painter, width - 60, 38, c['role'], colour, 30, True)
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
        y = 66
        for line, tone, size in header:
            self.text(painter, 16, y, line, tone, size);y += 24
        top = y + 10
        # Twelve skills: label and 25-cell bar, no number.
        skill_width = (width - 160) if self.narrow else 250
        for i, (name, value) in enumerate(c['skills']):
            row = top + i * 30
            self.text(painter, 16, row, name.capitalize(), GOLD, 20, True)
            self.bar(painter, 140, row, skill_width, value, 25)
        # The tactics and the mark, then five characteristics: label and 14-cell bar with the
        # original's word inside it.
        x, top = (16, top + 12 * 30 + 20) if self.narrow else (410, top)
        bar_x = x + 150;bar_width = min(200, width - bar_x - 16)
        self.text(painter, x, top, 'TACTICS / P = PERSONAL', RED, 20, True)
        rows = [(name, word + (' P' if personal else '')) for name, word, personal in c['tactics']]
        for i, (name, word) in enumerate(rows + [('mark', c['mark'] or '—')]):
            row = top + 28 + i * 28
            self.text(painter, x, row, name.capitalize(), GOLD, 20)
            self.text(painter, bar_x, row, word, GREEN, 18)
        top += 28 * (len(rows) + 2) + 14
        for i, (name, word, bar, raw) in enumerate(c['characteristics']):
            row = top + i * 32
            self.text(painter, x, row, name.capitalize(), GOLD, 20, True)
            self.bar(painter, bar_x, row, bar_width, bar, 14)
            font = QFont('DejaVu Sans Mono');font.setStyleHint(QFont.StyleHint.Monospace);font.setPixelSize(16)
            from PySide6.QtGui import QFontMetrics
            painter.fillRect(QRectF(bar_x + 1, row - 15, QFontMetrics(font).horizontalAdvance(word) + 6, 18), QColor(GREY))
            self.text(painter, bar_x + 4, row, word, BLACK, 16)
        painter.end()
