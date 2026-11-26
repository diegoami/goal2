"""S07 Team info: check out all the competitors.

[designed: owner, 2026-11-03, #526; docs/design/ui-2026-11, S07 and its mockup s07-team-info.html; T164, #538] S04's
card (`goal2.ui.s04_country.CountryCard`) for any country of the open career, beside the country list, the next
opponent marked [confirmed: M244-G4C-05 steps 2–6, docs/original-game/images/m244-team-info-2030.png, "Check out all
the competitors"]:

- **↑↓** the country, **←→** the next or previous group of 16, as S04's list; **Ins** world or continental ranking,
  the list in that ranking's order (`s04_country.ordered`, #559). It opens on the world ranking, as the capture and
  the mockup show it, with the cursor on the next opponent, as the mockup draws it.
- **Space** the country's twenty, read only (T165's card: `s04_country.PlayersScreen`).
- **T** its tactics: for your own country S10 Team tactics, the screen the desk's T opens; for any other country its
  eight lines read only (`CountryTacticsScreen`) [designed: T164: only your own tactics are yours to change].
- **Enter** its fixtures: S11 with that country's coming fixtures (T178, #560); Esc there returns here.
- **Esc** back to the desk. A click on a country highlights it, as ↑↓ do [designed: owner, 2026-11-03, #526].

Everything is read from the career (`DesktopModel.countries`, `goal2.game.country_card.card`); this screen changes
nothing [designed: owner, 2026-11-03, #527 D2].
"""
from __future__ import annotations

from PySide6.QtCore import QRectF, Qt, QTimer
from PySide6.QtGui import QFontMetricsF, QPainter

from goal2.game.country_card import card as country_card
from goal2.ui import theme
from goal2.ui.cell_parts import CellTableRow
from goal2.ui.cells import CellLabel, CellPara, Cells
from goal2.ui.country_parts import framed
from goal2.ui.frame import DASH
from goal2.ui.s04_country import (BODY_COLS, BODY_ROWS, GROUP, LIST_AT, LIST_COLS, PREVIEW_MS, CountryCard, PlayersScreen, averages,
                                  ordered)
from goal2.ui.s06_desk import next_match
from goal2.ui.screen import Screen
from goal2.ui.squad_card import colour

MARK = "next opponent"   # [designed: s07-team-info.html]
MARK_COLS = len(MARK)
NAME_COLS = LIST_COLS - MARK_COLS - 1


class CountryRowLabel(CellLabel):
    """[designed: #862] Keep the full row text when Windows rounds font advances up."""

    def paintEvent(self, event):
        text = self.text()
        if not text or not self.width():
            return
        painter = QPainter(self)
        font = self.font()
        painter.setFont(font)
        painter.setPen(self.palette().color(self.foregroundRole()))
        advance = QFontMetricsF(font, self).horizontalAdvance(text)
        scale = min(1.0, self.width() / max(1.0, advance))
        painter.scale(scale, 1.0)
        rect = QRectF(0, 0, self.width() / scale, self.height())
        painter.drawText(rect, int(self.alignment()), text)
        painter.end()


class TeamInfoScreen(Screen):
    GRID = True   # [designed: T211b] laid out on the 16 x 32 grid, no card
    title = "team info"
    escape_text = "desk"

    def __init__(self, window, model):
        super().__init__(window)
        self.model = model
        self.countries = model.countries()
        self.continental = False
        self.order = ordered(self.countries, self.continental)
        self.opponent, _ = next_match(model)
        start = self.opponent if self.opponent is not None else model.state.managed_country
        self.index = next(i for i, c in enumerate(self.order) if c[0] == start)
        self.previewed = None
        self.card = None
        self.timer = QTimer(self)
        self.timer.setSingleShot(True)
        self.timer.setInterval(PREVIEW_MS)
        self.timer.timeout.connect(self.preview)
        self.bind((Qt.Key.Key_Up,), "", lambda: self.move(-1), shown=False)
        self.bind((Qt.Key.Key_Down,), "", lambda: self.move(1), shown=False)
        self.bind((Qt.Key.Key_Left,), "", lambda: self.group(-1), captions=("←",), shown=False)
        self.bind((Qt.Key.Key_Right,), "", lambda: self.group(1), captions=("→",), shown=False)
        self.bind((), "country", None, captions=("↑", "↓", "←", "→"))
        self.bind((Qt.Key.Key_Insert,), "world / continental rank", self.toggle_rank)
        self.bind((Qt.Key.Key_Space,), "players", self.players)
        self.bind((Qt.Key.Key_T,), "tactics", self.tactics)
        esc = next(b for b in self.bindings if Qt.Key.Key_Escape in b.keys)
        self.bindings.remove(esc)
        self.bindings.append(esc)
        self._refresh_bar()
        self._build()
        # [designed: #862; M244-G4C-05 step 3] The selection already names the country.
        self.enter_text.reserve = len("Fixtures") + 1
        self.set_enter("Fixtures", self.fixtures)
        self.preview()
        self._show()

    def _build(self):
        """[designed: #667, T211b, #862] The S04 card and the framed country list sit side by side."""
        body = Cells(BODY_COLS, BODY_ROWS, "teamBody")
        self.body_layout.addWidget(body, 1)
        self.area = body
        self.card_view = CountryCard(family=self.window_.family, rows=CountryCard.ROWS_WITH_PERFORMANCE)
        body.put(self.card_view, 0, 0, CountryCard.COLS, CountryCard.ROWS_WITH_PERFORMANCE)
        self.countries_frame, inner = framed("world ranking", LIST_COLS, GROUP + 1)
        self.rows = []
        for i in range(GROUP):
            row = CellTableRow(i, (NAME_COLS, MARK_COLS), gaps=(0, 1), plain=True, label_type=CountryRowLabel)
            row.chosen.connect(self.click_row)
            inner.put(row, 0, i, LIST_COLS)
            self.rows.append(row)
        self.group_note = inner.text("", "sub", 1, GROUP, LIST_COLS - 2)
        body.put(self.countries_frame, LIST_AT, 0, LIST_COLS, GROUP + 2)
        self.note = CellPara("", "sub")
        colour(self.note, theme.VALUE)
        body.put(self.note, LIST_AT, GROUP + 3, LIST_COLS, 2)

    # What is shown.
    def _show(self):
        start = self.index // GROUP * GROUP
        for i, row in enumerate(self.rows):
            n, country_name = self.order[start + i][:2]
            self._show_country(row, country_name, n == self.opponent)
            row.set_on(start + i == self.index)
        ranking = "continental" if self.continental else "world"
        self.countries_frame.set_label(f"{ranking} ranking")
        self.group_note.setText(f"{start + 1}–{start + GROUP} of {len(self.order)}")
        self._show_card()

    @staticmethod
    def _show_country(row, name, next_opponent):
        """[designed: #862; m244-team-info-2030.png] Fill the row after the name, leaving the opponent cue readable."""
        if next_opponent:
            name_width, detail_width = NAME_COLS, MARK_COLS
            detail, tone = MARK, theme.VALUE
        else:
            name_width = len(name)
            detail_width = LIST_COLS - name_width - 3
            detail, tone = DASH * detail_width, theme.FRAME_DARK
        row.area.move(row.cells[0], 0, 0, name_width)
        row.area.move(row.cells[1], name_width + 1, 0, detail_width)
        row.set_cells((name, detail), (theme.TEXT_BRIGHT, tone))

    def _show_card(self):
        if self.card is not None:
            self.card_view.set_card(self.card, self.average)

    def preview(self):
        """The highlighted country's card from the career's state."""
        self.timer.stop()
        number = self.order[self.index][0]
        if self.previewed == number:
            return
        state = self.model.state
        self.card = country_card(state, number, self.model.goaldat)
        words = state.managed_squad if number == state.managed_country else self.card["players"]
        self.average = averages(state, words)
        self.previewed = number
        self._show_card()

    def settle(self):
        """The card for the highlighted country now (the preview's pause skipped)."""
        self.preview()

    def chosen(self):
        """(number, name) of the highlighted country."""
        return self.order[self.index][:2]

    def visible_names(self):
        return [row.cells[0].text() for row in self.rows]

    def marks(self):
        return [MARK if row.cells[1].text() == MARK else "" for row in self.rows]

    def say(self, text):
        self.note.setText(text)

    # The keys.
    def move(self, step):
        self.index = max(0, min(self.index + step, len(self.order) - 1))
        self.say("")
        self.timer.start()
        self._show()

    def group(self, step):
        groups = len(self.order) // GROUP
        group = max(0, min(self.index // GROUP + step, groups - 1))
        self.index = group * GROUP + self.index % GROUP
        self.say("")
        self.timer.start()
        self._show()

    def click_row(self, i):
        self.index = self.index // GROUP * GROUP + i
        self.say("")
        self.timer.start()
        self._show()

    def toggle_rank(self):
        """Ins: the other ranking; the highlight stays on the same country."""
        number = self.order[self.index][0]
        self.continental = not self.continental
        self.order = ordered(self.countries, self.continental)
        self.index = next(i for i, c in enumerate(self.order) if c[0] == number)
        self._show()

    def players(self):
        self.settle()
        number, name = self.chosen()
        return self.window_.push(TeamPlayersScreen(self.window_, self.model, name, country=number))

    def tactics(self):
        self.settle()
        number, _ = self.chosen()
        if number == self.model.state.managed_country:
            from goal2.ui.s10_team_tactics import open_team_tactics
            return open_team_tactics(self.window_, self.model, back="team info")
        return self.window_.push(CountryTacticsScreen(self.window_, self.model, number))

    def fixtures(self):
        """Enter: S11 with the highlighted country's coming fixtures (T178, #560)."""
        from goal2.ui.s11_fixtures import FixturesScreen
        self.settle()
        return self.window_.push(FixturesScreen(self.window_, self.model, country=self.chosen()[0], back="team info"))

    def shown(self):
        """Back from S10 or the players: the card again (your own tactics may have changed)."""
        self.previewed = None
        self.preview()


class TeamPlayersScreen(PlayersScreen):
    """S07's Space: the country's twenty, read only, on T165's card."""
    GRID = True   # [designed: owner, #667; T212b]
    title = "team info · players"
    pre_game = False



class CountryTacticsScreen(Screen):
    """S07's T: another country's eight lines, read only, beside its twenty."""
    GRID = True   # [designed: owner, #667; T212b]
    # [confirmed: F010, the team tactics screen's order DS:6BBF; the words of goal2.game.country_card, F008]
    title = "team info · tactics"

    def __init__(self, window, model, country):
        super().__init__(window)
        from goal2.ui.s10_team_tactics import LINES, words
        state = model.state
        c = country_card(state, country, model.goaldat)
        tactics = state.countries[country][0x2D]   # [confirmed: F010] the country's tactics +0x2D
        from goal2.ui.cell_parts import CellTableRow, GridStrip
        body = Cells(90, 25, "countryTacticsBody")
        self.body_layout.addWidget(body, 1)
        head, inner = framed("team", 69, 2)
        inner.text(c["name"], "h1", 0, 0, 34)
        note = CellPara(f"formation {c['formation']} · read only", "sub")
        inner.put(note, 35, 0, 34, 2)
        body.put(head, 0, 0, 69, 3)
        self.rows = []
        for heading, first, count, at in (("team tactics", 0, 3, 5), ("player defaults", 3, 5, 12)):
            frame, inner = framed(heading, 69, count * 2)
            for index in range(first, first + count):
                name, element = LINES[index]
                clear, set_ = words(state, element)
                line = CellTableRow(-1, (17, 34), aligns=(None, Qt.AlignmentFlag.AlignHCenter), gaps=(17, 1))
                line.set((name, set_ if tactics >> (element - 1) & 1 else clear),
                         (theme.TEXT_BRIGHT, theme.TEXT_BRIGHT))
                line.setCursor(Qt.CursorShape.ArrowCursor)
                inner.put(line, 0, 2 * (index - first), 69)
                self.rows.append(line)
            body.put(frame, 0, at, 69, count * 2 + 1)
        footer = body.text("only your own tactics are yours to change", "sub", 0, 24, 69)
        footer.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self.strip = GridStrip(cols=20)
        from goal2.game.player_card import card
        cards = [card(state, word, model.goaldat) for word in c["players"]]
        self.strip.show_rows(c["name"], [(p["role"], p["line"], p["full_name"]) for p in cards], -1, True)
        for row in self.strip.rows:
            row.setCursor(Qt.CursorShape.ArrowCursor)
        body.put(self.strip, 70, 0, 20, 22)

    def lines(self):
        return [tuple(row.texts()) for row in self.rows]
