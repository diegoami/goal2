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
# [designed: T107] The core route's compact card: the same parts in 680 x 490 page pixels (rows of 26, a skill bar
# of 26 cells of 8), so the card, the strip and the routes fit the fixed page with T105's margin.
COMPACT_WIDTH, COMPACT_HEIGHT = 680, 490
# [designed: accepted vision #266 screen 11] Narrower than WIDTH, the card stacks its columns
# (skills, characteristics, tactics). [designed: T101] The fixed page always gives the card its
# full width; the stacked form remains for a card shown alone in a narrow widget.
NARROW_WIDTH, NARROW_HEIGHT = 400, 1110


def bar_text(value):
    return '—' if value is None else str(value)


class PlayerCardView(QWidget):
    """One complete card; set_card(card or None)."""
    page_painted = True

    def __init__(self, parent=None, compact=False):
        super().__init__(parent)
        self.compact = compact
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
        return self.logical_width() < (COMPACT_WIDTH if self.compact else WIDTH) - 0.5

    def sizeHint(self):
        s = self.scale()
        if self.compact:
            return QSize(round(COMPACT_WIDTH * s), round(COMPACT_HEIGHT * s))
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
        # [designed: T107] Over the core the performance is the original's star bar (1771:3827: 1..9 of 9), drawn
        # as a bar, never a number.
        stars = c.get('performance_bar')
        if stars is not None:
            performance = ''
        skill_cells = c.get('skill_cells', 25)
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
        if stars is not None:
            header = [(line.replace(' / Performance: ', ' / Performance').replace('Performance: ', 'Performance'),
                       tone, size) for line, tone, size in header]
        y = 66
        for line, tone, size in header:
            self.text(painter, 16, y, line, tone, size)
            if stars is not None and line.endswith('Performance'):
                font = QFont('DejaVu Sans Mono');font.setStyleHint(QFont.StyleHint.Monospace);font.setPixelSize(size)
                from PySide6.QtGui import QFontMetrics
                x = 16 + QFontMetrics(font).horizontalAdvance(line) + 12
                self.bar(painter, x, y, min(180, width - x - 16), stars, 9)
            y += 24
        top = y + 10
        # Twelve skills: label and 25-cell bar, no number.
        skill_width = (width - 160) if self.narrow else 208 if self.compact else 250
        step, gap = (26, 24) if self.compact else (30, 28)
        for i, (name, value) in enumerate(c['skills']):
            row = top + i * step
            self.text(painter, 16, row, name.capitalize(), GOLD, 20, True)
            self.bar(painter, 140, row, skill_width, value, skill_cells)
        # The tactics and the mark, then five characteristics: label and 14-cell bar with the
        # original's word inside it.
        x, top = (16, top + 12 * step + 20) if self.narrow else (360 if self.compact else 410, top)
        bar_x = x + (130 if self.compact else 150);bar_width = min(200, width - bar_x - 16)
        self.text(painter, x, top, 'TACTICS / P = PERSONAL', RED, 20, True)
        rows = [(name, word + (' P' if personal else '')) for name, word, personal in c['tactics']]
        for i, (name, word) in enumerate(rows + [('mark', c['mark'] or '—')]):
            row = top + gap + i * gap
            self.text(painter, x, row, name.capitalize(), GOLD, 20)
            self.text(painter, bar_x, row, word, GREEN, 18)
        top += gap * (len(rows) + 2) + 14
        for i, (name, word, bar, raw) in enumerate(c['characteristics']):
            row = top + i * (28 if self.compact else 32)
            self.text(painter, x, row, name.capitalize(), GOLD, 20, True)
            self.bar(painter, bar_x, row, bar_width, bar, 14)
            font = QFont('DejaVu Sans Mono');font.setStyleHint(QFont.StyleHint.Monospace);font.setPixelSize(16)
            from PySide6.QtGui import QFontMetrics
            painter.fillRect(QRectF(bar_x + 1, row - 15, QFontMetrics(font).horizontalAdvance(word) + 6, 18), QColor(GREY))
            self.text(painter, bar_x + 4, row, word, BLACK, 16)
        painter.end()


def core_card(card):
    """[designed: T107] goal2/core/views.player_card's card in this view's shape: the original's words, its bars
    (26 skill cells, 1771:3947's template; 14 per characteristic; 9 performance stars, 1771:3827) and no number
    where a bar fits; a pool player has no status word, as the original shows none."""
    feet, inches = card['height']
    foot = card['foot'] if ' ' in card['foot'] else card['foot'] + ' foot'
    return {'full_name': card['name'], 'role': card['code'], 'line': card['line'], 'age': card['age'],
            'caps': card['caps'], 'goals': card['goals'], 'height': f"{feet}'{inches:2}\"", 'foot': foot,
            'readiness': card['readiness'] or 'in the pool', 'position': card['position_name'],
            'club_position': card['club_position_name'], 'club_role': card['club_code'],
            'cards': card['cards'], 'performance': None, 'performance_bar': card['performance'] or 0,
            'skills': card['skills'], 'skill_cells': 26,
            'characteristics': [(n, w, b, None) for n, w, b in card['characteristics']],
            'tactics': card['tactics'], 'mark': card['mark']}
