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

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import QHBoxLayout, QVBoxLayout

from goal2.game.country_card import card as country_card
from goal2.ui import theme
from goal2.ui.s04_country import GROUP, LIST_WIDTH, PREVIEW_MS, CountryCard, PlayersScreen, averages, ordered
from goal2.ui.s06_desk import next_match
from goal2.ui.screen import Screen, label, para, set_para
from goal2.ui.squad_card import Row as TableRow, Strip, box as card_box, colour
from goal2.ui.start_look import Row, box

MARK = "next opponent"   # [designed: s07-team-info.html]


class TeamInfoScreen(Screen):
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
        self.set_enter("", self.fixtures)
        self.preview()
        self._show()

    def _build(self):
        row = QHBoxLayout()
        row.setSpacing(18)
        self.card_view = CountryCard()
        row.addWidget(self.card_view, 1)
        countries, inner = box()
        countries.setFixedWidth(LIST_WIDTH)
        inner.addWidget(label("CHECK OUT ALL THE COMPETITORS", "boxHeading"))
        inner.setSpacing(0)
        inner.addSpacing(8)
        self.rows = []
        for i in range(GROUP):
            r = Row([None, 130], on_click=lambda i=i: self.click_row(i))
            r.cells[1].setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            inner.addWidget(r)
            self.rows.append(r)
        inner.addSpacing(10)
        self.group_note = label("", "sub")
        inner.addWidget(self.group_note)
        inner.addSpacing(10)
        self.note = para("", "sub")
        colour(self.note, theme.VALUE)
        inner.addWidget(self.note)
        inner.addStretch(1)
        row.addWidget(countries)
        self.body_layout.addLayout(row, 1)

    # What is shown.
    def _show(self):
        number, name = self.order[self.index][:2]
        start = self.index // GROUP * GROUP
        for i, row in enumerate(self.rows):
            n, country_name = self.order[start + i][:2]
            row.set_cells([country_name, MARK if n == self.opponent else ""])
            row.set_on(start + i == self.index)
        ranking = "continental" if self.continental else "world"
        self.group_note.setText(f"{start + GROUP} of {len(self.order)} · {ranking} ranking")
        self.set_enter(f"Fixtures of {name}", self.fixtures)
        self._show_card()

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
        return [row.cells[1].text() for row in self.rows]

    def say(self, text):
        set_para(self.note, text)

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
            return open_team_tactics(self.window_, self.model)
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
    title = "team info · players"
    pre_game = False


class CountryTacticsScreen(Screen):
    """S07's T on another country: its eight lines, in the original's order, read only, beside its twenty.
    [confirmed: F010, the team tactics screen's order DS:6BBF; the words of goal2.game.country_card, F008]"""
    title = "team info · tactics"

    def __init__(self, window, model, country):
        super().__init__(window)
        from goal2.ui.s10_team_tactics import LINES, words
        state = model.state
        c = country_card(state, country, model.goaldat)
        tactics = state.countries[country][0x2D]   # [confirmed: F010] the country's tactics +0x2D
        column = QVBoxLayout()
        column.setSpacing(14)
        head, head_layout = card_box()
        head_row = QHBoxLayout()
        head_row.setSpacing(28)
        head_row.addWidget(label(c["name"], "h1"))
        head_row.addWidget(label(f"formation {c['formation']} · read only: only your own tactics are yours to change",
                                 "sub"))
        head_row.addStretch(1)
        head_layout.addLayout(head_row)
        column.addWidget(head)
        table, table_layout = card_box("Team tactics · player defaults")
        table_layout.setSpacing(0)
        table_layout.addSpacing(10)
        self.rows = []
        for name, element in LINES:
            clear, set_ = words(state, element)
            line = TableRow(-1, (200, 0), margins=(8, 6, 8, 6), underline=True)
            line.set((name, set_ if tactics >> (element - 1) & 1 else clear), (theme.TEXT_BRIGHT, theme.TEXT_BRIGHT))
            line.setCursor(Qt.CursorShape.ArrowCursor)
            table_layout.addWidget(line)
            self.rows.append(line)
        table_layout.addStretch(1)
        column.addWidget(table, 1)
        main = QHBoxLayout()
        main.setSpacing(18)
        main.addLayout(column, 1)
        strip = Strip()
        from goal2.game.player_card import card
        cards = [card(state, word, model.goaldat) for word in c["players"]]
        strip.show_rows(c["name"], [(p["role"], p["line"], p["full_name"]) for p in cards], -1, True)
        for row in strip.rows:
            row.setCursor(Qt.CursorShape.ArrowCursor)
        main.addWidget(strip)
        self.body_layout.addLayout(main, 1)

    def lines(self):
        return [tuple(row.texts()) for row in self.rows]
