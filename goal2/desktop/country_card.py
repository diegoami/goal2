"""[designed: T89; accepted vision #266] The original country card, painted in the accepted style.

Core cards consume the reviewed F034..F038 display projections. The legacy
Python route retains its explicit missing-field fallback. Space opens players
in the country browser; Team Info keeps its existing tactic controls/Back route.
"""
from PySide6.QtCore import Qt, QSize, QRectF
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
TEAM_HIGHLIGHT, TEAM_EMPTY = '#aaaaaa', '#aa00aa'  # [derived: F036/F038] DOS attributes 0x70/0x05.


def characteristic_view(descriptors):
    """[derived: proposed F038] Crop the original's rows20..23/columns46..61.

    Highlight extents retain their original 80-column row-major coordinates;
    they are never clamped to16. Subsequent descriptor text is drawn before its
    own highlight, in the original order. Cells outside this viewport stay out
    of the card; the decoded full extent remains available in the card data.
    """
    cells = {(row, column): ['■', False] for row in range(20, 24) for column in range(46, 62)}
    for d in descriptors:
        start = (d['row'] - 1) * 80 + d['column'] - 1
        for offset, character in enumerate(d['text']):
            row, column = divmod(start + offset, 80)
            key = (row + 1, column + 1)
            if key in cells:cells[key] = [character, False]
        for (row, column), cell in cells.items():
            if start <= (row - 1) * 80 + column - 1 < start + d['cells']:
                cell[1] = True
    return [[tuple(cells[row, column]) for column in range(46, 62)] for row in range(20, 24)]


class CountryCardView(QWidget):
    # [designed: T101] Painted in page pixels through a scaled painter (goal2/desktop/fixed_page.py);
    # the fixed page always gives it WIDTH x HEIGHT, the stacked form remains for a narrow widget.
    page_painted = True

    def __init__(self, parent=None, team_info=False):
        super().__init__(parent)
        from goal2.desktop.style import load_fonts
        load_fonts()
        self.team_info = team_info;self.reader = None;self.painted_bars = []
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
        return QSize(round((300 if self.team_info else WIDTH) * s), round((600 if self.team_info else HEIGHT) * s))

    def minimumSizeHint(self):
        return self.sizeHint()

    def set_card(self, card, first='', reader=None):
        self.first = first;self.reader = reader
        self._card_data(card)
        self.update()

    def set_reader(self, reader):
        """Refresh on exposure; hidden Team Info does no decoder work."""
        self.reader = reader
        self.update()

    def _card_data(self, card):
        if card is not None and 'squad' in card:
            from goal2.desktop.core_roles import role_code
            card = {**card, 'eleven': [role_code(p) for p in card['squad'][:11]]}
        self.card = card
        if card is not None:
            self.setAccessibleName(f"{card['name']}; manager {card['manager']}; world {card['world']}; "
                                   f"{card['continent']} {card['continental']}; formation {card['formation']}; "
                                   f"status {card.get('status', NOT_DECODED)}; "
                                   f"skill {card.get('skill', NOT_DECODED) or ''}; "
                                   + '; '.join(f'{n} {w}' for n, w in card['team_tactics'] + card['player_defaults']))
            if 'team_skills' in card:
                lines = []
                for key, title in (('team_skills', 'Team skills'), ('performance', 'Performance')):
                    panel = card[key]
                    lines.append(title + (' has not started' if panel is None else ': ' + ', '.join(
                        f"{b['line']} {b['cells']}/25" for b in panel['bars'])))
                lines.extend(f"{d['field']} {d['text']}" for d in card['characteristics']['descriptors'])
                lines.extend(f"{d['field']} {d['text']}" for d in card['characteristics']['numbers'])
                self.setAccessibleName(self.accessibleName() + '; ' + '; '.join(lines))

    def text(self, painter, x, y, value, color, size=20, bold=False):
        font = QFont('DejaVu Sans Mono');font.setStyleHint(QFont.StyleHint.Monospace)
        font.setPixelSize(size);font.setBold(bold);painter.setFont(font)
        painter.setPen(QColor(color));painter.drawText(int(x), int(y), str(value))
        self.bottom = max(self.bottom, int(y) + painter.fontMetrics().descent())
        self.right = max(self.right, float(x) + painter.fontMetrics().horizontalAdvance(str(value)))

    def fitted(self, painter, value, width, preferred, bold=False):
        font = QFont('DejaVu Sans Mono');font.setStyleHint(QFont.StyleHint.Monospace);font.setBold(bold)
        from PySide6.QtGui import QFontMetrics
        size = preferred
        while size > 8:
            font.setPixelSize(size)
            if QFontMetrics(font).horizontalAdvance(str(value)) <= width:break
            size -= 1
        return size

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
                at = x + label_width
                size = self.fitted(painter, value, self.width()/self.scale()-at-16, 16 if missing else 19)
                self.text(painter, at, y, value, GREY if missing else GREEN, size)
            y += 27
        return y + 10

    def bar(self, painter, x, y, filled, width=150, count=25):
        """[derived: F036/F037] Unchanged template glyphs, highlighted prefix."""
        self.painted_bars.append((x, y, width, count, filled))
        step = width / count
        for i in range(count):
            active = filled is not None and i < filled
            if active:
                painter.fillRect(QRectF(x+i*step, y-16, step, 20), QColor(TEAM_HIGHLIGHT))
            self.text(painter, x+i*step+0.5, y-3, '■', BLACK if active else TEAM_EMPTY,
                      max(8, min(13, int(step/0.6))))

    def panels(self, painter, card, x, y, columns, group_width=224, compact=False):
        """The same decoded panels in a three-column footer or stacked Team Info."""
        end = y
        label_width = 84 if compact else 72
        bar_width = group_width - label_width - 2
        descriptor_step = max(9, bar_width/25) if compact else 9
        descriptor_size = min(16, int(descriptor_step/0.6)) if compact else 13
        for index, (key, title) in enumerate((('team_skills', 'TEAM SKILLS'), ('performance', 'PERFORMANCE'),
                                               ('characteristics', 'CHARACTERISTICS'))):
            left, top = (x+240*index, y) if columns == 3 else (x, end)
            self.text(painter, left, top, title, RED, 16, True)
            if key != 'characteristics':
                panel = card[key]
                bars = [None]*4 if panel is None else [b['cells'] for b in panel['bars']]
                for row, (name, value) in enumerate(zip(('Keeper', 'Defence', 'Midfield', 'Attack'), bars)):
                    base = top + 30 + 25*row
                    self.text(painter, left, base, name, GOLD, 15 if compact else 13)
                    self.bar(painter, left+label_width, base, value, width=bar_width)
                bottom = top + 130
            else:
                panel = card[key]
                for offset, number in enumerate(panel['numbers']):
                    self.text(painter, left+(group_width/2)*offset, top+24,
                              number['field'].capitalize()+' '+number['text'], CYAN, 14)
                grid = characteristic_view(panel['descriptors'])
                for row, descriptor in enumerate(panel['descriptors']):
                    base = top + 48 + 25*row
                    self.text(painter, left, base, descriptor['field'].capitalize(), GOLD, 15 if compact else 13)
                    for column, (character, active) in enumerate(grid[row]):
                        at = left + label_width + descriptor_step*column
                        if active:
                            painter.fillRect(QRectF(at, base-16, descriptor_step, 20), QColor(TEAM_HIGHLIGHT))
                        self.text(painter, at, base, character,
                                  BLACK if active else TEAM_EMPTY if character == '■' else GREEN, descriptor_size)
                bottom = top + 148
            end = max(end, bottom)
        return end

    def compact_team(self, painter, card):
        """The existing Team Info column leaves the roster/tactic controls visible."""
        width = self.width()/self.scale()-32
        title = card['name'].upper()+' / '+card['formation']
        self.text(painter, 16, 38, title, YELLOW, self.fitted(painter, title, width, 26, True), True)
        for row, (name, value) in enumerate((('Manager', card['manager']), ('Status', card['status']),
                                             ('Skill', card['skill']))):
            self.text(painter, 16, 72+24*row, name, GOLD, 15)
            value = '' if value is None else value
            self.text(painter, 110, 72+24*row, value, GREEN,
                      self.fitted(painter, value, self.width()/self.scale()-126, 16))
        self.panels(painter, card, 16, 148, 1, group_width=min(340, width), compact=True)

    def paintEvent(self, event):
        # [designed: T144] Re-exposure uses current pure memory data, not a
        # cached quick-engine sum or a guest call. No update() loop in painting.
        if self.reader is not None:self._card_data(self.reader())
        self.painted_bars = []
        painter = QPainter(self);painter.fillRect(self.rect(), QColor(BLACK));self.bottom = 0;self.right = 0
        s = self.scale();painter.scale(s, s)
        painter.setPen(QColor(CYAN));painter.drawRect(1, 1, round(self.width() / s) - 3, round(self.height() / s) - 3)
        c = self.card
        if c is None:
            self.text(painter, 20, 40, 'Choose a country', GREY);painter.end();return
        if self.team_info and all(key in c for key in ('team_skills', 'performance', 'characteristics')):
            self.compact_team(painter, c);painter.end();return
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
        left_bottom = y
        decoded = all(key in c for key in ('team_skills', 'performance', 'characteristics'))
        x, y = (16, y + 44) if narrow else (400, 92)
        y = self.rows(painter, x, y, 'TEAM TACTICS', c['team_tactics'], 195)
        y = self.rows(painter, x, y, 'PLAYER DEFAULTS', c['player_defaults'], 195)
        if decoded:
            y = self.panels(painter, c, 16, max(y, left_bottom)+28, 1 if narrow else 3)
        else:
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
        if not self.team_info:self.text(painter, 16, y + 4, 'SPACE: PLAYERS', MAGENTA, 20, True)
        painter.end()
