"""S04 Country and manager's name, and the country's twenty (read only).

[designed: owner, 2026-11-03, #526; docs/design/ui-2026-11, S04 and its mockup s04-country.html; T163, #537]
- The country card as the mockup draws it, with what today's browse page shows (goal2/desktop/launch.py over
  goal2/game/country_card.py): name, manager, status, skill, world and continental ranking (top not decoded),
  formation and its eleven role codes, strips, team tactics, player defaults, the bars and characteristics, and the
  first match. Fields the Python route has not decoded say so in `country_card.NOT_DECODED`'s words, as today.
- The country list in groups of 16: **↑↓** country, **←→** group of 16, **Ins** world or continental ranking,
  **Space** the country's twenty (`PlayersScreen`, read only). [confirmed: T156-R1 steps 3–5; E031 C13–C15b]
- **Enter** chooses the country and opens the name line on the same screen (14 characters at most, the original's
  name entry, 1771:09A0); **Enter** again starts the career, **Esc** aborts the name, then goes back to S03.
  [confirmed: T156-R1 steps 6–11]

The career is the model's: each previewed country is a private `DesktopModel.new_campaign` as today's Launch makes
it, and Start makes a fresh model with `new_campaign(country, start year)` and `rename_manager(name)`; the screen
copies no career rule. [designed: owner, 2026-11-03, #527, D2]
"""
from __future__ import annotations

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import QFrame, QHBoxLayout, QVBoxLayout, QWidget

from goal2.desktop import data_setup
from goal2.desktop.model import CONTINENTS, DesktopModel
from goal2.game.country_card import NOT_DECODED, card as country_card
from goal2.game.identities import MANAGER_MAX
from goal2.ui import saves
from goal2.ui.screen import Screen, label, para, set_para
from goal2.ui.start_look import LineField, Row, box, coloured_codes, key_value, refresh

GROUP = 16           # [confirmed: T156-R1 step 3; s04-country.html] the list shows 16 countries at a time
LIST_WIDTH = 300     # [designed: s04-country.html, the list's `width:300px`]
PREVIEW_MS = 120     # [designed: T86, Launch's preview delay] the card follows the highlight after a pause
NAME_NOTE = "Enter on a country opens this line; Enter again starts the career."
# [confirmed: F008 DS:699A] a role code's line, by the code itself (goal2/desktop/country_card.py's table)
from goal2.desktop.country_card import CODE_LINE  # noqa: E402


def paths(target):
    """The files a new career starts from (data_setup.WINDOW_MANIFEST) and where it would be saved."""
    return (target.data / data_setup.TEMPLATE_NAME, target.goal_dat,
            target.saves / f"new-career{saves.SUFFIX}")


def new_career(target, country, start_year, name):
    """The career S04 starts: the model's own new campaign for the country and start year, under the manager's
    name. [designed: owner, 2026-11-03, #527, D2; T163]"""
    template, data, save = paths(target)
    model = DesktopModel.open(template, data, save, country=country)
    model.new_campaign(country, start_year)
    model.rename_manager(name)
    return model


def averages(model):
    """The twenty's average caps and age, rounded to a whole number, as the S04 mockup shows them ("average caps 0 ·
    age 28"). [designed: T163 6a; design S04 "average caps and age"] They are the cards' own `age` and `caps`
    (goal2.game.player_card.card: record byte 1, and the word at 8): read here from the same record bytes, because a
    whole card costs about a tenth of a second (it reads the emulator memory), and the test checks them against the
    cards."""
    records = [model.state.players[word] for word in model.state.managed_squad]
    values = {"age": [r[1] for r in records], "caps": [r[8] | r[9] << 8 for r in records]}
    return {key: round(sum(v) / len(v)) for key, v in values.items()}


class CountryScreen(Screen):
    title = "new game · step 2 of 3 · country and name"
    pre_game = True

    def __init__(self, window, start_year):
        super().__init__(window)
        self.start_year = start_year
        self.target = window.target
        template, data, save = paths(self.target)
        self.browser = DesktopModel.open(template, data, save, country=1)   # private: never published
        self.countries = self.browser.countries()   # (number, name, world, continent, rank within it)
        self.index = 0
        self.continental = False
        self.naming = False
        self.previewed = None
        self.card = None
        self.timer = QTimer(self)
        self.timer.setSingleShot(True)
        self.timer.setInterval(PREVIEW_MS)
        self.timer.timeout.connect(self.preview)
        self.bind((Qt.Key.Key_Up,), "", lambda: self.move(-1), shown=False)
        self.bind((Qt.Key.Key_Down,), "", lambda: self.move(1), shown=False)
        self.bind((), "country", None, captions=("↑", "↓"))
        self.bind((Qt.Key.Key_Left,), "", lambda: self.group(-1), captions=("←",), shown=False)
        self.bind((Qt.Key.Key_Right,), "", lambda: self.group(1), captions=("→",), shown=False)
        self.bind((), "group of 16", None, captions=("←", "→"))
        self.bind((Qt.Key.Key_Insert,), "world / continental rank", self.toggle_rank)
        self.bind((Qt.Key.Key_Space,), "players", self.players)
        esc = next(b for b in self.bindings if Qt.Key.Key_Escape in b.keys)
        self.bindings.remove(esc)
        self.bindings.append(esc)
        self._refresh_bar()
        self._build()
        self.set_enter("", self.press_enter_key)
        self.preview()
        self._show()

    # The screen.
    def _build(self):
        row = QHBoxLayout()
        row.setSpacing(18)
        left = QVBoxLayout()
        left.setSpacing(14)
        header, layout = box()
        top = QHBoxLayout()
        who = QVBoxLayout()
        who.setSpacing(2)
        who.addWidget(label("Player 1 · choose your country", "sub"))
        self.name = label("", "h1")
        who.addWidget(self.name)
        self.first = label("", "sub")
        who.addWidget(self.first)
        top.addLayout(who)
        top.addStretch(1)
        level = QVBoxLayout()
        level.addWidget(label("level of difficulty", "sub"), 0, Qt.AlignmentFlag.AlignRight)
        level.addWidget(label(NOT_DECODED, "undecoded"), 0, Qt.AlignmentFlag.AlignRight)
        level.addStretch(1)
        top.addLayout(level)
        layout.addLayout(top)
        facts = QHBoxLayout()
        facts.setSpacing(28)
        team, self.team = key_value((("status", "status"), ("manager", "manager")))
        ranks, self.ranks = key_value((("world", "world"), ("continental", "continent"), ("top", "top")))
        shape, self.shape = key_value((("formation", "formation"), ("skill", "skill"), ("strips", "strips")))
        for part in (team, ranks, shape):
            facts.addWidget(part, 0, Qt.AlignmentFlag.AlignTop)
        facts.addStretch(1)
        layout.addLayout(facts)
        left.addWidget(header)
        panels = QHBoxLayout()
        panels.setSpacing(18)
        skills, inner = box("Skills")
        self.skills = label(NOT_DECODED, "undecoded")
        inner.addWidget(self.skills)
        inner.addSpacing(8)
        inner.addWidget(label("PERFORMANCE", "boxHeading"))
        self.performance = label(NOT_DECODED, "undecoded")
        inner.addWidget(self.performance)
        inner.addStretch(1)
        tactics, inner = box("Team tactics")
        tactic_rows, self.tactics = key_value((("defence system", "defence system"), ("protection", "protection"),
                                               ("offside", "offside")))
        inner.addWidget(tactic_rows)
        inner.addSpacing(8)
        inner.addWidget(label("PLAYER DEFAULTS", "boxHeading"))
        default_rows, self.defaults = key_value((("positioning", "positioning"), ("possession", "possession"),
                                                 ("passing", "passing"), ("tackling", "tackling"),
                                                 ("marking", "marking")))
        inner.addWidget(default_rows)
        inner.addStretch(1)
        traits, inner = box("Characteristics")
        self.averages = label("", "sub")
        inner.addWidget(self.averages)
        self.characteristics = label(NOT_DECODED, "undecoded")
        inner.addWidget(self.characteristics)
        inner.addStretch(1)
        for part in (skills, tactics, traits):
            panels.addWidget(part, 1)
        left.addLayout(panels, 1)
        name_box = QFrame()
        name_box.setObjectName("box")
        name_row = QHBoxLayout(name_box)
        name_row.setContentsMargins(16, 14, 16, 14)
        name_row.setSpacing(16)
        name_row.addWidget(label("Manager's name", "muted"))
        self.field = LineField(MANAGER_MAX, count=True, on_click=self.press_enter_key)
        self.field.setFixedWidth(360)
        name_row.addWidget(self.field)
        self.name_note = para(NAME_NOTE, "sub")
        name_row.addWidget(self.name_note, 1)
        left.addWidget(name_box)
        row.addLayout(left, 1)
        countries, inner = box()
        countries.setFixedWidth(LIST_WIDTH)
        self.list_heading = label("", "boxHeading")
        inner.addWidget(self.list_heading)
        inner.setSpacing(0)
        inner.addSpacing(8)
        self.rows = []
        for i in range(GROUP):
            r = Row([None, 40], on_click=lambda i=i: self.click_row(i))
            r.cells[1].setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            inner.addWidget(r)
            self.rows.append(r)
        inner.addSpacing(10)
        self.group_note = label("", "sub")
        inner.addWidget(self.group_note)
        inner.addStretch(1)
        row.addWidget(countries)
        self.body_layout.addLayout(row, 1)

    def _show(self):
        number, name, world, continent, within = self.countries[self.index]
        start = self.index // GROUP * GROUP
        self.list_heading.setText("COUNTRIES · " + ("CONTINENTAL RANK" if self.continental else "WORLD RANK"))
        for i, row in enumerate(self.rows):
            n, country_name, w, _, inside = self.countries[start + i]
            row.set_cells([country_name, str(inside if self.continental else w)])
            row.set_on(start + i == self.index)
        self.group_note.setText(f"{start + GROUP} of {len(self.countries)} · ←→ next group")
        self._show_card()
        if self.naming:
            self.set_enter("Start the career", self.press_enter_key)
        else:
            self.set_enter(f"Choose {name}", self.press_enter_key)

    def _show_card(self):
        c = self.card
        if c is None:
            return
        self.name.setText(c["name"])
        self.averages.setText("average caps {caps} · age {age}".format(**self.average))
        self.first.setText("first: " + self.first_match)
        self.team["status"].setText(c.get("status", NOT_DECODED))
        self.team["manager"].setText(c["manager"] or "")
        self.ranks["world"].setText(str(c["world"]))
        self.ranks["continental"].caption.setText(c["continent"])
        self.ranks["continental"].setText(str(c["continental"]))
        self.ranks["top"].setText(NOT_DECODED)
        self.shape["formation"].setTextFormat(Qt.TextFormat.RichText)
        self.shape["formation"].setText(f"{c['formation']}  " + coloured_codes(
            (code, CODE_LINE.get(code, "unknown")) for code in c["eleven"]))
        self.shape["skill"].setText(c.get("skill", NOT_DECODED) or "")
        self.shape["strips"].setText(NOT_DECODED)
        for values, pairs in ((self.tactics, c["team_tactics"]), (self.defaults, c["player_defaults"])):
            for key, value in pairs:
                values[key].setText(value)
        for widget in (*self.team.values(), *self.ranks.values(), *self.shape.values()):
            widget.setObjectName("undecoded" if widget.text() == NOT_DECODED else "value")
        refresh(self)

    def preview(self):
        """The highlighted country's card, from a private new campaign of the model, as today's Launch."""
        self.timer.stop()
        number = self.countries[self.index][0]
        if self.previewed == number:
            return
        self.browser.new_campaign(number, self.start_year)
        self.card = country_card(self.browser.state, number, self.browser.goaldat)
        summary = self.browser.summary()
        self.first_match = f"{summary['campaign']}: {summary['next']}"
        self.average = averages(self.browser)
        self.previewed = number
        self._show_card()

    def settle(self):
        """The card for the highlighted country now (the preview's pause skipped)."""
        self.preview()

    def chosen(self):
        """(number, name) of the highlighted country."""
        return self.countries[self.index][:2]

    def visible_names(self):
        return [row.cells[0].text() for row in self.rows]

    def visible_ranks(self):
        return [row.cells[1].text() for row in self.rows]

    # The keys.
    def move(self, step):
        if not self.naming:
            self.index = max(0, min(self.index + step, len(self.countries) - 1))
            self.timer.start()
            self._show()

    def group(self, step):
        if not self.naming:
            groups = len(self.countries) // GROUP
            group = max(0, min(self.index // GROUP + step, groups - 1))
            self.index = group * GROUP + self.index % GROUP
            self.timer.start()
            self._show()

    def click_row(self, i):
        """A click on a country highlights it, as ↑↓ do."""
        if not self.naming:
            self.index = self.index // GROUP * GROUP + i
            self.timer.start()
            self._show()

    def toggle_rank(self):
        if not self.naming:
            self.continental = not self.continental
            self._show()

    def players(self):
        if self.naming:
            return None
        self.settle()
        return self.window_.push(PlayersScreen(self.window_, self.browser, self.countries[self.index][1]))

    def type_text(self, key, text) -> bool:
        """On the name line, printable characters and Backspace edit the name; nothing else moves."""
        if not self.naming:
            return False
        if key == Qt.Key.Key_Backspace:
            self.field.backspace()
            return True
        if text and len(text) == 1 and text.isprintable():
            self.field.type(text)
            return True
        return False

    def press_enter_key(self):
        """Enter: choose the country and open the name line; on the name line, start the career."""
        self.settle()
        if not self.naming:
            self.naming = True
            self.field.set_active(True)
            self._note(NAME_NOTE)
            self._show()
            return None
        return self.start()

    def start(self):
        name = self.field.text.strip()
        if not name:
            self._note("Type the manager's name first: 14 characters at most.", error=True)
            return None
        number = self.countries[self.index][0]
        try:
            model = new_career(self.target, number, self.start_year, name)
        except ValueError as exc:
            self._note(str(exc), error=True)
            return None
        return self.window_.open_career(model)

    def _note(self, text, error=False):
        set_para(self.name_note, text)
        self.name_note.setObjectName("error" if error else "sub")
        refresh(self.name_note)

    def escape(self):
        """Esc aborts the name and keeps the country list; Esc again goes back to S03."""
        if self.naming:
            self.naming = False
            self.field.set_text("")
            self.field.set_active(False)
            self._note(NAME_NOTE)
            self._show()
            return
        self.window_.pop()


class PlayersScreen(Screen):
    """The country's twenty, read only: T165's S08 card (goal2/ui/squad_card.py `PlayerCard`, bars without numbers
    [designed: owner, 2026-10-21, T99], with performance and cards) beside its strip of the twenty.
    [confirmed: T156-R1 step 4, Space in the country browser; designed: S04 "the S08 card, read only"; T163 6a]"""
    title = "new game · step 2 of 3 · players"
    pre_game = True

    def __init__(self, window, browser, country_name):
        super().__init__(window)
        from goal2.game.player_card import card
        from goal2.ui.squad_card import PlayerCard, Strip, squad_rows
        rows, eleven = squad_rows(browser)
        self.cards = [card(browser.state, row["id"], browser.goaldat) for row in rows]
        self.eleven = eleven
        self.index = 0
        self.bind((Qt.Key.Key_Up,), "", lambda: self.move(-1), shown=False)
        self.bind((Qt.Key.Key_Down,), "", lambda: self.move(1), shown=False)
        self.bind((), "player", None, captions=("↑", "↓"))
        esc = next(b for b in self.bindings if Qt.Key.Key_Escape in b.keys)
        self.bindings.remove(esc)
        self.bindings.append(esc)
        self._refresh_bar()
        row = QHBoxLayout()
        row.setSpacing(18)
        self.card = PlayerCard()
        row.addWidget(self.card, 1)
        self.strip = Strip()
        self.strip.chosen.connect(self.pick)
        row.addWidget(self.strip)
        self.body_layout.addLayout(row, 1)
        self.heading = f"{country_name} · the twenty"
        self._show()

    def _show(self):
        c = self.cards[self.index]
        self.card.set_card(c)
        self.strip.show_rows(self.heading, [(c["role"], c["line"], c["full_name"]) for c in self.cards],
                             self.index, gap=self.eleven == 11)

    @property
    def player_name(self):
        return self.card.name

    def move(self, step):
        self.index = max(0, min(self.index + step, len(self.cards) - 1))
        self._show()

    def pick(self, i):
        self.index = i
        self._show()
