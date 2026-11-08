"""[designed: owner, 2026-11-08; T177, #666] The proposal's screens, drawn on the character canvas.

Six screens of `docs/design/ui-2026-11/README.md` section 2, drawn with the grammar the backlog
asks for, so the grammar can be judged as a picture instead of as prose. Their content is the
approved design's own (run T156-R1: Holland, Norway, the same twenty), so each can be put beside
the mockup it would replace and the original capture it came from.

Nothing here is app code. It is `grid.py` plus the content of the screens.
"""
from grid import (ATT, BAR_EMPTY, BAR_FULL, CYAN, DARK, DEF, GK, GREEN, HINT, LABEL, MID, MUTED,
                  RED, TEXT, TITLE, VALUE, Screen)

# The twenty, as the approved mockups show them: role code, initial and surname, line.
SQUAD = [('G', 'F V Breukelen', 'G'), ('S', 'R Koeman', 'D'), ('C', 'B Van Aerle', 'D'),
         ('C', 'A V Tiggelen', 'D'), ('D', 'J Wouters', 'M'), ('m', 'R Witschge', 'M'),
         ('M', 'F Rijkaard', 'M'), ('F', 'D Bergkamp', 'M'), ('w', 'B Roy', 'A'),
         ('W', 'R Gullit', 'A'), ('$', 'M Van Basten', 'A')]
BENCH = [('G', 'S Menzo', 'G'), ('S', 'F De Boer', 'D'), ('C', 'D Blind', 'D'),
         ('Ç', 'W Jonk', 'M'), ('Ç', 'P Bosz', 'M'), ('M', "J Van't Ship", 'M'),
         ('m', 'A Winter', 'M'), ('$', 'P Van Vossen', 'A'), ('$', 'W Kieft', 'A')]
LINE = {'G': GK, 'D': DEF, 'M': MID, 'A': ATT}


def strip(s, col, row, title='Holland', width=27, selected=None):
    """The squad strip: the name carries the line colour, the role code is a right-hand column."""
    s.rule(col, row, width, title, DARK, CYAN)
    r = row + 1
    for index, player in enumerate(SQUAD):
        code, name, line = player
        if selected == index:
            s.highlight(col + 1, r, width - 2, f' {name}')
            s.right(col + width - 1, r, code, '#000000')
        else:
            s.text(col + 2, r, name, LINE[line])
            s.right(col + width - 2, r, code, LINE[line])
        r += 1
    s.rule(col + 1, r, width - 2, None, DARK)
    r += 1
    for code, name, line in BENCH:
        s.text(col + 2, r, name, LINE[line])
        s.right(col + width - 2, r, code, LINE[line])
        r += 1
    s.vrule(col, row + 1, r - row - 1, DARK)
    s.vrule(col + width - 1, row + 1, r - row - 1, DARK)
    return r


def banner(s, col, width, row, year='2028', name='EUROPEAN CHAMPIONSHIP', stage='QUALIFYING'):
    """The competition's banner where the original has it: blocky letters, not larger text."""
    s.stencil(col, row, name, 46, TITLE, 2.0)
    s.rule(col, row + 2, width, None, DARK)
    s.centre(col, width, row + 3, stage, VALUE)
    s.text(col + width - 6, row, year, VALUE)


def hub(path):
    """S06 Manager's desk, against docs/original-game/images/manager-menu.png."""
    s = Screen()
    s.corner()
    banner(s, 13, 48, 0)

    # Left: the manager, the team, the opponents, the managers' board. Frames touch and nest.
    s.vrule(0, 6, 19, '#aa0000')
    s.rule(1, 6, 16, 'name', DARK)
    s.text(2, 7, 'E Go', TEXT)
    s.vrule(17, 6, 2, '#aa0000')
    s.rule(18, 6, 14, 'rating', DARK)
    s.text(19, 7, 'unknown', TEXT)

    s.rule(1, 9, 16, 'team', DARK)
    s.text(2, 10, 'Holland', TEXT)
    s.rule(1, 11, 16, 'rankings', DARK, RED)
    s.text(2, 12, 'World  :  14', TEXT)
    s.text(2, 13, 'Europe :   3', TEXT)

    s.vrule(17, 9, 7, '#aa0000')
    s.rule(18, 9, 14, 'managers', DARK)
    for i in range(1, 7):
        s.text(19, 9 + i, str(i), VALUE)
    s.text(21, 10, 'E Go', TEXT)
    s.rule(18, 16, 14, None, DARK)

    s.rule(1, 15, 16, 'next opponents', DARK)
    s.text(2, 16, 'Norway', TEXT)
    s.rule(1, 17, 16, 'rankings', DARK, RED)
    s.text(2, 18, 'World  :  32', TEXT)
    s.text(2, 19, 'Europe :  18', TEXT)
    s.rule(1, 20, 16, None, DARK)
    s.text(2, 21, 'friendly away', TEXT)
    s.rule(1, 22, 16, None, DARK)

    # The six routes: boxes the width of their words, as the original's are.
    options = ['team info', 'fixture list', 'tournament', 'history', 'select squad',
               'play next game']
    row = 6
    for i, option in enumerate(options):
        width = 18
        if i == 0:
            s.p.setPen(s.p.pen())
            s.highlight(36, row + 1, width, f'   {option}')
        else:
            s.button(36, row, width, 3, option)
        row += 3

    # The hint in the body, in magenta, where the original puts it.
    s.hint(19, 18, ['Use \u2191\u2193 to', 'find option'])
    s.hint(19, 21, ['Hit \u25c4\u2518 to', 'select', 'option'])

    strip(s, 62, 1, 'Holland', 27, selected=None)
    s.keyline([('F1', 'help'), ('F3', 'load goal'), ('F4', 'load summary'), ('F7', 'save')],
              [('F10', 'quit')])
    return s.save(path)


def squad(path):
    """S08 Squad and pool, against docs/original-game/images/m244-squad.png."""
    s = Screen()
    s.corner()
    s.hint(13, 0, ['- Use ↔ to toggle between your squad and',
                   '  the pool of other players available to you.',
                   '- Use ↕ to find player, ◄┘ to select.'])
    s.text(13, 3, 'Hit Ins for assistant’s recommended 20', GREEN)

    # The card: label on the rule, value under it, the whole width of the card.
    s.rule(0, 5, 61, 'name', DARK)
    s.text(1, 6, 'F V Breukelen', GK)
    for col, label, value in ((20, 'age', '33'), (27, 'caps', '0'), (35, 'goals', '0'),
                              (43, 'height', "6' 1\""), (50, 'bias', 'right foot')):
        s.rule(col, 5, 0, None, DARK)
        s.text(col, 5, label, LABEL)
        s.text(col, 6, value, TEXT)
    s.rule(0, 7, 61, 'position', DARK)
    s.text(1, 8, 'goalkeeper', GREEN)
    s.text(20, 7, 'club position', LABEL)
    s.text(20, 8, 'goalkeeper', GREEN)
    s.text(40, 7, 'cards', LABEL)
    s.text(40, 8, '—', TEXT)
    s.button(44, 7, 17, 3, 'ready to play', MUTED, TEXT)

    # Skills: the label, then a bar of cells, then the value. Short, beside its label.
    skills = [('keeping', 8), ('kicking', 7), ('tackling', 6), ('heading', 6), ('marking', 2),
              ('passing', 2), ('crossing', 2), ('feinting', 2), ('control', 2), ('dribbling', 2),
              ('shooting', 2), ('penalties', 2)]
    s.rule(0, 10, 30, 'skills', DARK, RED)
    for i, (name, value) in enumerate(skills):
        s.text(1, 11 + i, name, LABEL)
        s.bar(11, 11 + i, 16, value * 16 // 9)
        s.right(29, 11 + i, str(value), TEXT)

    s.rule(31, 10, 30, 'tactics', DARK, RED)
    for i, (name, value) in enumerate((('position', 'leave box P'), ('possession', 'keep ball'),
                                       ('passing', 'throw the ball'),
                                       ('tackling', 'avoid injury'), ('mark', '—'))):
        s.text(32, 11 + i, name, LABEL)
        s.text(44, 11 + i, value, GREEN)

    s.rule(31, 17, 30, 'characteristics', DARK, RED)
    for i, (name, word, value) in enumerate((('hardness', 'pushy', 6), ('fitness', 'ok', 4),
                                             ('energy', 'fine', 5), ('morale', 'brimming', 7),
                                             ('leadership', 'none', 1))):
        s.text(32, 18 + i, name, LABEL)
        s.word_bar(43, 18 + i, 8, value, word)

    strip(s, 62, 1, 'Holland', 27, selected=0)
    s.keyline([('F2', 'new name'), ('R,C', 'reposition'), ('T', 'tactics')],
              [('◄┘', 'move player'), ('Esc', 'exit')])
    return s.save(path)


def fixtures(path):
    """S11 Fixtures, against docs/original-game/images/fixtures-watch.png."""
    s = Screen()
    s.corner()
    s.stencil(14, 0, 'Fixtures', 76, DARK, 2.0)
    s.text(16, 4, 'and results', CYAN)
    s.hint(58, 0, ['Use ↑↓ to scroll'])
    s.hint(58, 2, ['Hit ◄┘ to', 'watch match'])

    rows = [('R.C.S', 'Holland', 'friendly', True), ('N.Ireland', 'Switzerland', 'friendly', False),
            ('Malta', 'Bulgaria', 'friendly', False), ('Denmark', 'Austria', 'friendly', False),
            ('Denmark', 'R.C.S', 'qualifying', False), ('Cyprus', 'Wales', 'friendly', False),
            ('Greece', 'Hungary', 'friendly', False), ('Germany', 'Albania', 'friendly', False),
            ('Yugoslavia', 'Russia', 'friendly', False), ('Germany', 'Greece', 'qualifying', False),
            ('Switzerland', 'Holland', 'qualifying', False), ('Russia', 'Wales', 'qualifying', False),
            ('Finland', 'Portugal', 'friendly', False), ('England', 'Spain', 'friendly', False),
            ('Eire', 'Luxembourg', 'friendly', False), ('Norway', 'Sweden', 'friendly', False)]
    left, width = 10, 70
    s.vrule(left - 1, 6, len(rows) + 1, '#aa0000')
    s.vrule(left + width, 6, len(rows) + 1, '#aa0000')
    for i, (a, b, kind, on) in enumerate(rows):
        row = 6 + i
        if on:
            s.highlight(left, row, width, '')
            s.right(left + 32, row, a, '#000000')
            s.text(left + 34, row, 'v', '#000000')
            s.text(left + 38, row, b, '#000000')
            s.text(left + 56, row, kind, '#000000')
        else:
            s.text(left, row, '-' * width, DARK)
            s.right(left + 32, row, a, VALUE, over=True)
            s.text(left + 34, row, 'v', CYAN, over=True)
            s.text(left + 38, row, b, VALUE, over=True)
            s.text(left + 56, row, kind, HINT if kind == 'friendly' else TEXT, over=True)
    s.keyline([], [('Esc', 'exit')])
    return s.save(path)


def bulletin(path):
    """S05 Bulletin, against docs/original-game/images/bulletin.png: three papers, not three panels."""
    s = Screen()
    s.corner()
    # The page's rules run the full width, behind the papers, as on a newspaper page.
    from PySide6.QtGui import QColor as _C
    for row in range(1, 27, 2):
        s.p.fillRect(0, row * 32 + 16, s.cols * 16, 2, _C('#555555'))

    papers = [(13, 20, 7, 20, '#aaaaaa', '#aa0000', 'D A I L Y  R A G',
               ['WELCOME', 'ABOARD', 'K EES !']),
              (35, 24, 4, 21, '#0000aa', '#aa5500', 'THE SOCCER BULLETIN',
               ['HOLLAND', 'APPOINT A NEW', 'MANAGER']),
              (62, 22, 6, 20, '#00aa00', '#ffffff', '✻ Sporting Times ✻',
               ['CAN K EES', 'DO THE JOB ?'])]
    for col, width, row, height, paper, masthead, title, headline in papers:
        s.p.fillRect(col * 16, row * 32, width * 16, height * 32, s.p.pen().color())
        from PySide6.QtGui import QColor
        s.p.fillRect(col * 16, row * 32, width * 16, height * 32, QColor(paper))
        s.p.fillRect(col * 16 + 8, row * 32 + 8, width * 16 - 16, height * 32 - 16, QColor('#000000'))
        s.p.fillRect(col * 16 + 12, row * 32 + 12, width * 16 - 24, height * 32 - 24, QColor(paper))
        black = '#000000'
        s.centre(col, width, row + 1, title, masthead)
        for i, line in enumerate(headline):
            s.centre(col, width, row + 3 + i, line, black)
        # Greeked body text in columns, and a halftone block, as the original draws them.
        body_row = row + 3 + len(headline) + 1
        columns = 3 if width > 21 else 2
        column_width = (width - 2) // columns
        for c in range(columns):
            for r in range(body_row, row + height - 2):
                if c == 1 and body_row + 2 <= r < body_row + 6:
                    continue
                s.text(col + 1 + c * column_width, r, '=' * (column_width - 1), '#444444')
        for r in range(body_row + 2, body_row + 6):
            for cc in range(column_width - 1):
                x, y = (col + 1 + column_width + cc) * 16, r * 32
                for dy in range(0, 32, 4):
                    for dx in range((cc + r) % 2 * 4, 16, 8):
                        s.p.fillRect(x + dx, y + dy, 4, 2, QColor('#777777'))
    s.highlight(38, 26, 15, '  hit any key')
    return s.save(path)


def score_panel(s, home='NORWAY', away='HOLLAND', scores=('0', '0'), kind='FRIENDLY',
                note=None, clock=None):
    """The score panel the original puts at the top of every match screen."""
    s.text(13, 1, home, TITLE)
    s.text(13 + len(home), 1, '-' * (20 - len(home)), '#aa0000')
    s.text(13, 2, 'versus', TEXT)
    s.text(13, 3, away, TITLE)
    s.text(13 + len(away), 3, '-' * (20 - len(away)), '#aa0000')
    s.vrule(12, 0, 5, '#aa0000')
    s.vrule(37, 0, 5, '#aa0000')
    for row, value in zip((1, 3), scores):
        s.button(33, row - 1, 4, 3, value, MUTED, TEXT)
    s.text(40, 1, kind, HINT)
    if note:
        s.text(40, 3, note, TEXT)
    # The clock, in its corner: large blocky digits, empty before kick-off.
    if clock:
        s.blocks(80, 0, clock, 96)
    else:
        for i in range(2):
            s.button(80 + i * 4, 0, 4, 4, '', MUTED)


def match_menu(path):
    """S15 Match menu, against docs/original-game/images/match-menu.png: two mirrored sides."""
    from PySide6.QtGui import QColor
    s = Screen()
    s.corner()
    score_panel(s)
    s.centre(0, s.cols, 5, 'location: Norway', LABEL)

    for col, side, shape, inboard in ((2, 'Norway', '4-5-1', 22), (69, 'Holland', '3-5-2', 55)):
        s.button(col, 6, 19, 3, side, MUTED, VALUE)
        s.vrule(col + 9, 9, 1, DARK)                      # the connector to this side's children
        s.button(col if col < 40 else col + 9, 10, 10, 3, shape, MUTED, TEXT)
        s.vrule(col + 9, 13, 1, DARK)
        for i, (code, name, line) in enumerate(SQUAD):
            s.text(col + 1, 14 + i, name, LINE[line])
            s.right(col + 18, 14 + i, code, LINE[line])
        s.vrule(col - 1 if col < 40 else col + 19, 7, 18, '#aa0000')
        # Its own two routes, facing inward, joined to its header.
        s.button(inboard, 10, 13, 3, 'team tactics', MUTED, CYAN)
        s.button(inboard, 14, 13, 3, 'players', MUTED, CYAN)
        s.p.setPen(s.p.pen())
        s.vrule(col + 9 if col < 40 else col + 9, 9, 1, DARK)

    # The middle column: what both sides share, with play highlighted as the original highlights it.
    s.button(37, 8, 14, 3, 'tournament', MUTED, CYAN)
    s.button(37, 12, 14, 3, 'match stats', MUTED, CYAN)
    s.highlight(39, 17, 10, '   play')
    s.hint(38, 20, ['Use \u2195\u2194', 'then \u25c4\u2518', 'to select', 'option'])

    # The stands at the foot, as the original draws them.
    for i in range(7):
        s.p.fillRect((26 + i * 6) * 16, 25 * 32, 5 * 16, 32 + 16, QColor('#aa5500'))
    s.centre(0, s.cols, 24, 'Hit INS to turn automatic action replay OFF', TITLE)
    s.keyline([('\u2195', 'choose')], [('Esc', 'exit')])
    return s.save(path)


def pitch(path):
    """S17 Pitch, against docs/original-game/images/match-live.png."""
    from PySide6.QtGui import QColor, QPen
    s = Screen()
    s.corner()
    score_panel(s, scores=('0', '1'), note='Bergkamp scores', clock='17')

    # The pitch: the original's own proportions, measured from match-live.png.
    top, bottom = 6 * 32, 26 * 32
    left, right = 2 * 16, 88 * 16
    length, height = right - left, bottom - top
    s.p.setPen(QPen(QColor(MUTED), 2))
    s.p.drawRect(left, top, length, height)
    s.p.drawLine(left + length // 2, top, left + length // 2, bottom)
    box_depth = round(length * 0.162)                    # 16.2 % of the length, as the original
    box_height = round(height * 0.67)
    for x0 in (left, right - box_depth):
        s.p.drawRect(x0, top + (height - box_height) // 2, box_depth, box_height)
    goal = round(height * 0.19)
    for x0, w in ((left - 10, 10), (right, 10)):
        s.p.drawRect(x0, top + (height - goal) // 2, w, goal)
    # Corner flags: magenta squares, as the original's.
    for x in (left, right):
        for y in (top, bottom):
            s.p.fillRect(x - 4, y - 4, 8, 8, QColor('#aa00aa'))

    home = [('S', 0.30, 0.22), ('M', 0.34, 0.33), ('C', 0.27, 0.42), ('C', 0.33, 0.50),
            ('$', 0.36, 0.50), ('M', 0.33, 0.62), ('C', 0.30, 0.72), ('¢', 0.38, 0.78),
            ('G', 0.03, 0.50), ('W', 0.42, 0.40), ('D', 0.40, 0.60)]
    away = [('C', 0.62, 0.25), ('B', 0.66, 0.28), ('M', 0.60, 0.40), ('D', 0.64, 0.45),
            ('C', 0.58, 0.52), ('W', 0.63, 0.55), ('M', 0.60, 0.68), ('F', 0.55, 0.60),
            ('S', 0.70, 0.50), ('G', 0.96, 0.50), ('Ç', 0.52, 0.47)]
    for letters, colour in ((home, TITLE), (away, TEXT)):
        for ch, fx, fy in letters:
            col = (left + fx * length) / 16
            row = (top + fy * height) / 32
            s.text(round(col), round(row), ch, colour)
    s.p.fillRect(left + round(0.47 * length), top + round(0.50 * height), 8, 8, QColor(TEXT))

    s.keyline([('↕', '-display'), ('↔', '-speed»»»»»'),
               ('R', '-result'), ('spacebar', '-commentary'), ('F9', '-♪')],
              [('Esc,◄┘', '-bench')])
    return s.save(path)


SCREENS = {'s06-hub': hub, 's08-squad': squad, 's11-fixtures': fixtures, 's05-bulletin': bulletin,
           's15-match-menu': match_menu, 's17-pitch': pitch}
