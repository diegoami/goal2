"""S04 Country and manager's name, and the country's twenty (read only).

[designed: owner, 2026-11-03, #526; docs/design/ui-2026-11, S04 and its mockup s04-country.html; T163, #537]
- The country card as the mockup draws it, with what today's browse page shows (goal2/desktop/launch.py over
  goal2/game/country_card.py): name, manager, status, skill, world and continental ranking (top not decoded),
  formation and its eleven role codes, strips, team tactics, player defaults, the bars and characteristics, and the
  first match. Fields the Python route has not decoded say so in `country_card.NOT_DECODED`'s words, as today.
- The country list in groups of 16: **↑↓** country, **←→** group of 16, **Ins** world or continental ranking,
  **Space** the country's twenty (`PlayersScreen`, read only). [confirmed: T156-R1 steps 3–5; E031 C13–C15b]
- The list is in the order of the ranking Ins selects (`ordered`): under *continental* each continent's 32 by their
  rank within it, Europe first (Denmark, Germany, Holland, Sweden…), under *world* the world ranks. It opens on
  *continental*, at Denmark. [confirmed: T156-R1 step 3 opens on Denmark, and step 5, two Downs later, shows Holland
  third with *continental* selected: docs/original-game/images/t156-005-country-holland.png; m244-team-info-2030
  shows *world* selected and the world order, Germany, Argentina, Italy…; #559]
- The card (`CountryCard`) is shared with S07 Team info (goal2/ui/s07_team_info.py), which shows it for any
  country of the open career. [designed: docs/design/ui-2026-11, S07 "the S04 card"; T164]
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
from goal2.ui import saves, theme
from goal2.ui.screen import Screen, label, para, set_para
from goal2.ui.squad_card import colour
from goal2.ui.start_look import LineField, Row, box, coloured_codes, key_value, refresh

GROUP = 16           # [confirmed: T156-R1 step 3; s04-country.html] the list shows 16 countries at a time
LIST_WIDTH = 390     # [designed: owner #598] retain complete country/ranking text at 24px
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


def averages(state, words=None):
    """[designed: T163] Legacy twenty-player mean retained for existing callers.

    [confirmed: F038; T198] The TEAM view consumes the delivered XI aggregate,
    including its original seed/divisor and availability rules. Holland's28
    happens to agree with this helper; Denmark's original29 differs from28 here.
    This helper is not an original TEAM-panel oracle and supplies no displayed value.
    """
    words = list(state.managed_squad) if words is None else list(words)
    records = [state.players[word] for word in words]
    values = {"age": [r[1] for r in records], "caps": [r[8] | r[9] << 8 for r in records]}
    return {key: sum(v) // len(v) for key, v in values.items()}


def ordered(countries, continental):
    """The countries in the list's order: under `continental` by continent (Europe, America, Africa, Asia) and their
    rank within it, else by world rank. `countries` are `DesktopModel.countries()` rows (number, name, world,
    continent, rank within it). [confirmed: t156-005-country-holland.png, m244-team-info-2030.png; #559]"""
    key = (lambda c: (c[3], c[4], c[0])) if continental else (lambda c: (c[2], c[0]))
    return sorted(countries, key=key)


class CountryCard(QWidget):
    """The country card, S04's and S07's: the header (name, status, manager, world and continental ranking, top,
    formation and its eleven role codes, skill, strips), then skills and performance, team tactics and player
    defaults, characteristics with the original XI caps and age. `chooser` adds S04's own parts: "Player 1 ·
    choose your country", the first match and the level of difficulty. [designed: s04-country.html,
    s07-team-info.html; T163, T164]"""

    def __init__(self, chooser=False, *, match_context=False, family=None):
        super().__init__()
        if type(match_context) is not bool:
            raise ValueError("match_context must be a boolean")
        self.match_context = match_context
        self.family = family or theme.FONT_FAMILY
        self.chooser = chooser
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)
        header, inner = box()
        inner.setContentsMargins(16, 8, 16, 8)
        inner.setSpacing(2)
        top = QHBoxLayout()
        who = QVBoxLayout()
        who.setSpacing(2)
        if chooser:
            who.addWidget(label("Player 1 · choose your country", "sub"))
        self.name = label("", "h1")
        who.addWidget(self.name)
        self.first = label("", "sub")
        who.addWidget(self.first)
        self.first.setVisible(chooser)
        top.addLayout(who)
        top.addStretch(1)
        if chooser:
            level = QVBoxLayout()
            level.addWidget(label("level of difficulty", "sub"), 0, Qt.AlignmentFlag.AlignRight)
            level.addWidget(label(NOT_DECODED, "undecoded"), 0, Qt.AlignmentFlag.AlignRight)
            level.addStretch(1)
            top.addLayout(level)
        inner.addLayout(top)
        facts = QHBoxLayout()
        facts.setSpacing(28)
        team, self.team = key_value((("status", "status"), ("manager", "manager")))
        from goal2.ui.country_header import RankColumns, StripGlyphs
        ranks = RankColumns(); self.ranks = ranks.values
        shape, self.shape = key_value((("formation", "formation"), ("skill", "skill"), ("strips", "strips")))
        old_strips = self.shape["strips"]
        shape.layout().removeWidget(old_strips)
        self.strip_view = StripGlyphs(self.family)
        self.strip_view.caption = old_strips.caption
        shape.layout().addWidget(self.strip_view, 2, 1)
        old_strips.hide(); old_strips.deleteLater(); self.shape["strips"] = self.strip_view
        for part in (team, ranks, shape):
            facts.addWidget(part, 0, Qt.AlignmentFlag.AlignTop)
        facts.addStretch(1)
        inner.addLayout(facts)
        self.role_codes = label("", "value")
        self.role_codes.setTextFormat(Qt.TextFormat.RichText)
        inner.addWidget(self.role_codes)
        layout.addWidget(header)
        panels = QHBoxLayout()
        panels.setSpacing(18)
        skills, inner = box("Skills")
        from goal2.ui.team_card import LineBars, CharacteristicPanel
        from goal2.ui.squad_card import FactsTable
        self.skills = LineBars()
        inner.addWidget(self.skills)
        inner.addSpacing(8)
        self.performance_heading = label("PERFORMANCE", "boxHeading")
        inner.addWidget(self.performance_heading)
        self.performance = LineBars()
        inner.addWidget(self.performance)
        inner.addStretch(1)
        tactics, inner = box("Team tactics")
        inner.setSpacing(4)
        inner.setContentsMargins(16, 10, 16, 10)
        tactic_rows, self.tactics = key_value((("defence system", "defence system"), ("protection", "protection"),
                                               ("offside", "offside")))
        inner.addWidget(tactic_rows)
        inner.addSpacing(8)
        defaults_heading = label("PLAYER DEFAULTS", "boxHeading")
        inner.addWidget(defaults_heading)
        default_rows, self.defaults = key_value((("positioning", "positioning"), ("possession", "possession"),
                                                 ("passing", "passing"), ("tackling", "tackling"),
                                                 ("marking", "marking")))
        inner.addWidget(default_rows)
        inner.addStretch(1)
        traits, inner = box("Characteristics")
        self.averages = FactsTable(("caps", "age"))
        for heading in self.averages.labels.values():
            colour(heading, theme.CARD_LABEL)
        inner.addWidget(self.averages)
        self.characteristics = CharacteristicPanel(self.family)
        inner.addWidget(self.characteristics)
        inner.addStretch(1)
        for part in (skills, tactics, traits):
            panels.addWidget(part, 2 if part is tactics else 1)
        layout.addLayout(panels, 1)

    def set_card(self, c, average, first=None):
        """Show decoded card fields. `average` remains accepted for existing callers; original numbers take precedence."""
        self.name.setText(c["name"])
        # [confirmed: F036–F038; T198] Consume original panels; the old twenty
        # mean is not the TEAM number. Browser context cannot inherit match flags.
        self.skills.set_panel(c["team_skills"])
        performance = c["performance"] if self.match_context else None
        self.performance.set_panel(performance)
        self.performance.setVisible(performance is not None)
        self.performance_heading.setVisible(performance is not None)
        traits = c["characteristics"]
        self.averages.set({n["field"]: n["text"] for n in traits["numbers"]}, theme.VALUE)
        self.characteristics.set_panel(traits)
        if first is not None:
            self.first.setText("first: " + first)
        self.team["status"].setText(c.get("status", NOT_DECODED))
        self.team["manager"].setText(c["manager"] or "")
        self.ranks["world"].setText(str(c["world"]))
        self.ranks["continental"].caption.setText(c["continent"])
        self.ranks["continental"].setText(str(c["continental"]))
        self.ranks["top_world"].setText(str(c["top_world"]) if "top_world" in c else NOT_DECODED)
        self.ranks["top_continental"].setText(str(c["top_continental"]) if "top_continental" in c else NOT_DECODED)
        self.shape["formation"].setTextFormat(Qt.TextFormat.RichText)
        self.shape["formation"].setText(c['formation'])
        self.role_codes.setText(coloured_codes(
            (code, CODE_LINE.get(code, "unknown")) for code in c["eleven"]))
        self.shape["skill"].setText(c.get("skill", NOT_DECODED) or "")
        if "strips" in c: self.strip_view.set_strips(c["strips"])
        else: self.strip_view.set_unknown()
        for values, pairs in ((self.tactics, c["team_tactics"]), (self.defaults, c["player_defaults"])):
            for key, value in pairs:
                values[key].setText(value)
        for widget in (*self.team.values(), *self.ranks.values(), *self.shape.values()):
            if widget is self.strip_view: continue
            if widget.text() == NOT_DECODED: widget.setText("unknown")
            widget.setObjectName("undecoded" if widget.text() in (NOT_DECODED, "unknown") else "value")
        refresh(self)


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
        self.continental = True   # [confirmed: T156-R1 steps 3-5] the browser opens on continental, at Denmark
        self.order = ordered(self.countries, self.continental)
        self.index = 0
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
        self.card_view = CountryCard(chooser=True, family=self.window_.family)
        for name in ("name", "first", "team", "ranks", "shape", "skills", "performance", "tactics", "defaults",
                     "averages", "characteristics"):
            setattr(self, name, getattr(self.card_view, name))
        left.addWidget(self.card_view, 1)
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
        number, name, world, continent, within = self.order[self.index]
        start = self.index // GROUP * GROUP
        self.list_heading.setText("COUNTRIES · " + ("CONTINENTAL RANK" if self.continental else "WORLD RANK"))
        for i, row in enumerate(self.rows):
            n, country_name, w, _, inside = self.order[start + i]
            row.set_cells([country_name, str(inside if self.continental else w)])
            row.set_on(start + i == self.index)
        self.group_note.setText(f"{start + GROUP} of {len(self.order)} · ←→ next group")
        self._show_card()
        if self.naming:
            self.set_enter("Start the career", self.press_enter_key)
        else:
            self.set_enter(f"Choose {name}", self.press_enter_key)

    def _show_card(self):
        if self.card is not None:
            self.card_view.set_card(self.card, self.average, self.first_match)

    def preview(self):
        """The highlighted country's card, from a private new campaign of the model, as today's Launch."""
        self.timer.stop()
        number = self.order[self.index][0]
        if self.previewed == number:
            return
        self.browser.new_campaign(number, self.start_year)
        self.card = country_card(self.browser.state, number, self.browser.goaldat)
        summary = self.browser.summary()
        self.first_match = f"{summary['campaign']}: {summary['next']}"
        self.average = averages(self.browser.state)
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

    def visible_ranks(self):
        return [row.cells[1].text() for row in self.rows]

    # The keys.
    def move(self, step):
        if not self.naming:
            self.index = max(0, min(self.index + step, len(self.order) - 1))
            self.timer.start()
            self._show()

    def group(self, step):
        if not self.naming:
            groups = len(self.order) // GROUP
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
        """Ins: the other ranking; the list takes its order and the highlight stays on the same country."""
        if not self.naming:
            number = self.order[self.index][0]
            self.continental = not self.continental
            self.order = ordered(self.countries, self.continental)
            self.index = next(i for i, c in enumerate(self.order) if c[0] == number)
            self._show()

    def players(self):
        if self.naming:
            return None
        self.settle()
        return self.window_.push(PlayersScreen(self.window_, self.browser, self.order[self.index][1]))

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
        number = self.order[self.index][0]
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

    def __init__(self, window, browser, country_name, country=None):
        super().__init__(window)
        from goal2.game.player_card import card
        from goal2.ui.squad_card import PlayerCard, Strip, squad_rows
        if country is None or country == browser.state.managed_country:
            rows, eleven = squad_rows(browser)
            words = [row["id"] for row in rows]
        else:
            # [confirmed: F008 squad list, F024] another country's twenty from its record, slots 1..11 its eleven
            # [designed: T164, S07's Space]
            words, eleven = country_card(browser.state, country, browser.goaldat)["players"], 11
        self.cards = [card(browser.state, word, browser.goaldat) for word in words]
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
