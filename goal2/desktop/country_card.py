"""[designed: T89; accepted vision #266] The original country card, painted in the accepted style.

The data is goal2.game.country_card's: decoded fields in colour, the fields with no finding yet
in grey as "not decoded yet (G05)". Space opens the players (T88).
"""
from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QColor, QFont, QPainter
from PySide6.QtWidgets import QWidget
from goal2.desktop.player_card import BLACK, WHITE, GREY, RED, CYAN, YELLOW, GREEN, MAGENTA, GOLD, LINE
from goal2.game.country_card import NOT_DECODED

WIDTH, HEIGHT = 740, 640
NARROW_WIDTH, NARROW_HEIGHT = 300, 1320
# [confirmed: F008 DS:699A] a code's line, by the code itself.
CODE_LINE = {'G': 'goalkeeper', 'S': 'defence', 'C': 'defence', 'b': 'defence', 'B': 'defence',
             'D': 'midfield', 'Ç': 'midfield', 'm': 'midfield', 'M': 'midfield', 'F': 'midfield',
             'w': 'midfield', 'W': 'midfield', '¢': 'attack', '$': 'attack'}


class CountryCardView(QWidget):
    # [designed: T101] Painted in page pixels through a scaled painter (goal2/desktop/fixed_page.py);
    # the fixed page always gives it WIDTH x HEIGHT, the stacked form remains for a narrow widget.
    page_painted = True

    def __init__(self, parent=None):
        super().__init__(parent)
        self.card = None;self.first = '';self.bottom = 0
        self.setObjectName('countryCard')
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)

    def scale(self):
        from goal2.desktop.fixed_page import scale_of
        return scale_of(self)

    @property
    def narrow(self):
        return self.width() / self.scale() < WIDTH - 0.5

    def sizeHint(self):
        s = self.scale()
        return QSize(round(WIDTH * s), round(HEIGHT * s))

    def minimumSizeHint(self):
        return self.sizeHint()

    def set_card(self, card, first=''):
        if card is not None and 'squad' in card:
            from goal2.desktop.core_roles import role_code
            card = {**card, 'eleven': [role_code(p) for p in card['squad'][:11]]}
        self.card = card;self.first = first
        if card is not None:
            self.setAccessibleName(f"{card['name']}; manager {card['manager']}; world {card['world']}; "
                                   f"{card['continent']} {card['continental']}; formation {card['formation']}; "
                                   f"status {card.get('status', NOT_DECODED)}; "
                                   f"skill {card.get('skill', NOT_DECODED) or ''}; "
                                   + '; '.join(f'{n} {w}' for n, w in card['team_tactics'] + card['player_defaults']))
        self.update()

    def text(self, painter, x, y, value, color, size=20, bold=False):
        font = QFont('DejaVu Sans Mono');font.setStyleHint(QFont.StyleHint.Monospace)
        font.setPixelSize(size);font.setBold(bold);painter.setFont(font)
        painter.setPen(QColor(color));painter.drawText(int(x), int(y), str(value))
        self.bottom = max(self.bottom, int(y) + painter.fontMetrics().descent())

    def rows(self, painter, x, y, title, rows, label_width=190):
        """A titled group of name/value rows; narrow cards put long values on their own line."""
        self.text(painter, x, y, title, RED, 20, True);y += 30
        for name, value in rows:
            # [designed: T137] Delivered manager0 draws a blank; an absent key
            # still uses the legacy route's explicit undecoded placeholder.
            value = '' if value is None else value
            missing = value == NOT_DECODED
            self.text(painter, x, y, name.capitalize(), GOLD, 19)
            if self.narrow and (missing or len(value) > 12):
                y += 22;self.text(painter, x + 16, y, value, GREY if missing else GREEN, 16)
            else:
                self.text(painter, x + label_width, y, value, GREY if missing else GREEN, 16 if missing else 19)
            y += 27
        return y + 10

    def paintEvent(self, event):
        painter = QPainter(self);painter.fillRect(self.rect(), QColor(BLACK));self.bottom = 0
        s = self.scale();painter.scale(s, s)
        painter.setPen(QColor(CYAN));painter.drawRect(1, 1, round(self.width() / s) - 3, round(self.height() / s) - 3)
        c = self.card
        if c is None:
            self.text(painter, 20, 40, 'Choose a country', GREY);painter.end();return
        narrow = self.narrow
        self.text(painter, 16, 52, c['name'].upper(), YELLOW, 40 if narrow else 44, True)
        team = [('manager', c['manager']), ('status', c.get('status', NOT_DECODED)),
                ('skill', c.get('skill', NOT_DECODED))]
        y = self.rows(painter, 16, 92, 'TEAM', team, 130)
        # Ranking now / top: the original's two columns; top is not decoded yet.
        self.text(painter, 16, y, 'RANKING', RED, 20, True)
        self.text(painter, 150, y, 'NOW', WHITE, 19);self.text(painter, 220, y, 'TOP', WHITE, 19)
        for label, now in (('World', c['world']), (c['continent'], c['continental'])):
            y += 27
            self.text(painter, 16, y, label, GOLD, 19);self.text(painter, 150, y, f'{now:>3}', CYAN, 19)
            self.text(painter, 230, y, '—', GREY, 19)
        y += 22;self.text(painter, 16, y, 'Top: ' + NOT_DECODED, GREY, 15)
        y += 36;self.text(painter, 16, y, 'FORMATION', RED, 20, True);self.text(painter, 150, y, c['formation'], CYAN, 22, True)
        y += 30
        for i, code in enumerate(c['eleven']):
            self.text(painter, 16 + i * 24, y, code, LINE[CODE_LINE.get(code, 'unknown')], 20, True)
        y += 34;self.text(painter, 16, y, 'STRIPS', RED, 20, True)
        y += 22;self.text(painter, 32, y, NOT_DECODED, GREY, 15)
        x, y = (16, y + 44) if narrow else (400, 92)
        y = self.rows(painter, x, y, 'TEAM TACTICS', c['team_tactics'], 195)
        y = self.rows(painter, x, y, 'PLAYER DEFAULTS', c['player_defaults'], 195)
        undecoded = [('team skills', NOT_DECODED), ('performance', NOT_DECODED), ('characteristics', NOT_DECODED)]
        y = self.rows(painter, x, y, 'TEAM BARS', undecoded, 195)
        if self.first:
            # The first fixture runs across the card, under both columns.
            campaign, _, fixture = self.first.partition(': ')
            y = max(y, 560) if not narrow else y
            self.text(painter, 16, y, 'FIRST', RED, 20, True)
            self.text(painter, 100, y, campaign + ('' if narrow else ': ' + fixture), WHITE, 16)
            if narrow:
                y += 24;self.text(painter, 100, y, fixture, WHITE, 16)
            y += 30
        self.text(painter, 16, y + 4, 'SPACE: PLAYERS', MAGENTA, 20, True)
        painter.end()
