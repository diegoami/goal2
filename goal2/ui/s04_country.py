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
from PySide6.QtWidgets import QHBoxLayout

from goal2.desktop import data_setup
from goal2.desktop.model import DesktopModel
from goal2.game.country_card import NOT_DECODED, card as country_card
from goal2.game.identities import MANAGER_MAX
from goal2.ui import saves, theme
from goal2.ui.cell_parts import CellLineField, CellTableRow, key_values
from goal2.ui.cells import CellLabel, CellPara, Cells
from goal2.ui.country_parts import (CellCharacteristics, CellFactsLine, CellLineBars, CellStripGlyphs, decoded, framed)
from goal2.ui.screen import Screen
from goal2.ui.start_look import coloured_codes, refresh

GROUP = 16           # [confirmed: T156-R1 step 3; s04-country.html] the list shows 16 countries at a time
# [designed: T211b; docs/design/ui-2026-11/proposal/README.md] The cells of S04 and S07: 90 columns and the 25 rows between the title row
# and the two key rows. The card is 60 columns (34 and 25 with a cell between), the list at its right 29 (a country's 15 characters,
# or one of 14 and the mark "next opponent", with room for a rank of three digits): 60 + 1 + 29 = 90.
BODY_COLS, BODY_ROWS = theme.COLS, theme.ROWS - 3
LIST_WIDTH = 390     # [designed: owner #598] the list's width in pixels on the screens not yet on the grid (the standalone friendly's, goal2/ui/friendly.py)
LIST_COLS, RANK_COLS = 29, 4
LIST_AT = BODY_COLS - LIST_COLS
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


class CountryCard(Cells):
    """The country card, S04's and S07's, on the 16 x 32 grid [designed: owner, 2026-11-08, #667; T211b; docs/design/ui-2026-11/
    proposal/README.md]: two columns of frames (a rule with its lowercase label), a cell apart, touching down their column as the
    original's card does. At the left, 34 cells: the team (its name, status, manager, skill, formation and strips), the skills, the
    performance (only with `match_context`) and the team tactics; at the right, 25: the ranking now and top, the eleven's role codes,
    the characteristics with the original XI's average caps and age, and the player defaults. S04 puts its name line under the right
    column (`rows` 23 instead of 21). The same names as the card it replaces (`name`, `team`, `ranks`, `shape`, `strip_view`,
    `role_codes`, `skills`, `performance`, `performance_heading`, `tactics`, `defaults`, `averages`, `characteristics`, `set_card`);
    the first match S04 shows over it is S04's own (`CountryScreen.first`). [designed: s04-country.html, s07-team-info.html; T163,
    T164; T211b]"""
    LEFT, GAP, RIGHT = 34, 1, 25
    COLS = LEFT + GAP + RIGHT
    ROWS = 21                  # the right column's 21 rows, with a row between its frames (the left's are 18)
    ROWS_WITH_PERFORMANCE = 24 # the left column's, with the performance shown: S07's card (S04's is never in a match context)
    RIGHT_AT = LEFT + GAP

    def __init__(self, chooser=False, *, match_context=False, family=None, rows=ROWS):
        if type(match_context) is not bool:
            raise ValueError("match_context must be a boolean")
        super().__init__(self.COLS, rows, "countryCard")
        self.match_context = match_context
        self.family = family or theme.FONT_FAMILY
        self.chooser = chooser
        left, right = self.LEFT, self.RIGHT
        # The team: its name, then status, manager, skill, formation and the strips. [designed: s04-country.html]
        team, inner = framed("team", left, 6)
        self.name = inner.text("", "h1", 0, 0, left)
        self.team, self.shape = {}, {}
        for row, (store, key) in enumerate((("team", "status"), ("team", "manager"), ("shape", "skill"),
                                            ("shape", "formation"), ("shape", "strips")), 1):
            caption = inner.text(key, "cardLabel", 0, row, 9)
            value = CellStripGlyphs(self.family) if key == "strips" else CellLabel("", "value")
            inner.put(value, 10, row, left - 10)
            value.caption = caption
            getattr(self, store)[key] = value
        self.strip_view = self.shape["strips"]
        self.shape["formation"].setTextFormat(Qt.TextFormat.RichText)
        self.put(team, 0, 0, left, 7)
        skills, inner = framed("skills", left, 4)
        self.skills = CellLineBars()
        inner.put(self.skills, 0, 0, left, 4)
        self.put(skills, 0, 8, left, 5)
        self.performance_heading, inner = framed("performance", left, 4)
        self.performance = CellLineBars()
        inner.put(self.performance, 0, 0, left, 4)
        self.put(self.performance_heading, 0, 14, left, 5)
        self.performance_heading.hide()
        self.tactics_frame, inner = framed("team tactics", left, 3)
        tactic_rows, self.tactics = key_values((("defence system", "defence system"), ("protection", "protection"),
                                                ("offside", "offside")), left, 14)
        inner.put(tactic_rows, 0, 0, left, 3)
        self.put(self.tactics_frame, 0, 14, left, 4)
        # The ranking now and at the top, and the eleven's role codes. [designed: s04-country.html]
        ranking, inner = framed("ranking", right, 3)
        inner.text("now", "sub", 8, 0, 7)
        inner.text("top", "sub", 16, 0, 7)
        self.ranks = {}
        for row, (key, caption) in enumerate((("world", "world"), ("continental", "")), 1):   # the continent's name is set with the card
            caption_label = inner.text(caption, "cardLabel", 0, row, 7)
            for column, name in ((8, key), (16, "top_" + key)):
                value = CellLabel("", "value")
                inner.put(value, column, row, 7)
                value.caption = caption_label
                self.ranks[name] = value
        self.put(ranking, self.RIGHT_AT, 0, right, 4)
        eleven, inner = framed("line-up", right, 1)
        self.role_codes = inner.text("", "value", 0, 0, right)
        self.role_codes.setTextFormat(Qt.TextFormat.RichText)
        self.put(eleven, self.RIGHT_AT, 5, right, 2)
        # The characteristics, with the original XI's caps and age, and the player defaults. [designed: s04-country.html]
        traits, inner = framed("characteristics", right, 5)
        self.averages = CellFactsLine(right)
        inner.put(self.averages, 0, 0, right, 1)
        self.characteristics = CellCharacteristics()
        inner.put(self.characteristics, 0, 1, right, 4)
        self.put(traits, self.RIGHT_AT, 8, right, 6)
        defaults, inner = framed("player defaults", right, 5)
        default_rows, self.defaults = key_values((("positioning", "positioning"), ("possession", "possession"),
                                                  ("passing", "passing"), ("tackling", "tackling"),
                                                  ("marking", "marking")), right, 11)
        inner.put(default_rows, 0, 0, right, 5)
        self.put(defaults, self.RIGHT_AT, 15, right, 6)

    def set_card(self, c, average=None):
        """Show decoded card fields. `average` remains accepted for existing callers; original numbers take precedence."""
        self.name.setText(c["name"])
        # [confirmed: F036–F038; T198] Consume original panels; the old twenty
        # mean is not the TEAM number. Browser context cannot inherit match flags.
        self.skills.set_panel(c["team_skills"])
        performance = c["performance"] if self.match_context else None
        self.performance.set_panel(performance)
        self.performance_heading.setVisible(performance is not None)
        # [designed: T211b] the team tactics follow what is shown above them: touching the skills, or the performance
        self.move(self.tactics_frame, 0, 14 + (6 if performance is not None else 0), self.LEFT, 4)
        traits = c["characteristics"]
        self.averages.set({n["field"]: n["text"] for n in traits["numbers"]}, theme.VALUE)
        self.characteristics.set_panel(traits)
        self.team["status"].setText(c.get("status", NOT_DECODED))
        self.team["manager"].setText(c["manager"] or "")
        self.ranks["world"].setText(str(c["world"]))
        self.ranks["continental"].caption.setText(c["continent"])
        self.ranks["continental"].setText(str(c["continental"]))
        self.ranks["top_world"].setText(str(c["top_world"]) if "top_world" in c else NOT_DECODED)
        self.ranks["top_continental"].setText(str(c["top_continental"]) if "top_continental" in c else NOT_DECODED)
        self.shape["formation"].setText(c["formation"])
        self.role_codes.setText(coloured_codes((code, CODE_LINE.get(code, "unknown")) for code in c["eleven"]))
        self.shape["skill"].setText(c.get("skill", NOT_DECODED) or "")
        if "strips" in c:
            self.strip_view.set_strips(c["strips"])
        else:
            self.strip_view.set_unknown()
        for widget in (*self.team.values(), *self.ranks.values(), *self.shape.values()):
            if widget is not self.strip_view:
                decoded(widget, widget.text())
        for values, pairs in ((self.tactics, c["team_tactics"]), (self.defaults, c["player_defaults"])):
            for key, value in pairs:
                values[key].setText(value)
        refresh(self)


class CountryScreen(Screen):
    GRID = True   # [designed: T211b] laid out on the 16 x 32 grid, no card
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
        """[designed: owner, 2026-11-08, #667; T211b; docs/design/ui-2026-11/proposal/README.md] The 90 x 25 cells between the title row
        and the key rows: the prompt, the level of difficulty and the first match across the top; under them the card (60 x 21: its two
        columns of frames) at the left and at the right the sixteen countries in a frame, with the manager's name in a frame under
        them."""
        body = Cells(BODY_COLS, BODY_ROWS, "countryBody")
        self.body_layout.addWidget(body, 1)
        self.area = body
        body.text("Player 1 · choose your country", "sub", 0, 0)
        body.text("level of difficulty", "sub", 49, 0)
        body.put(CellLabel(NOT_DECODED, "undecoded"), 69, 0, len(NOT_DECODED))
        self.first = body.text("", "sub", 0, 1, BODY_COLS)
        self.card_view = CountryCard(chooser=True, family=self.window_.family, rows=CountryCard.ROWS)
        for name in ("name", "team", "ranks", "shape", "skills", "performance", "tactics", "defaults", "averages",
                     "characteristics"):
            setattr(self, name, getattr(self.card_view, name))
        body.put(self.card_view, 0, 2, CountryCard.COLS, CountryCard.ROWS)
        self.countries_frame, inner = framed("continental rank", LIST_COLS, GROUP + 1)
        self.list_heading = self.countries_frame.rule
        self.rows = []
        for i in range(GROUP):
            row = CellTableRow(i, (LIST_COLS - RANK_COLS, RANK_COLS), (None, Qt.AlignmentFlag.AlignRight))
            row.chosen.connect(self.click_row)
            inner.put(row, 0, i, LIST_COLS)
            self.rows.append(row)
        self.group_note = CellPara("", "sub")   # "16 of 128 · ←→ next group": 25 characters, a row
        inner.put(self.group_note, 0, GROUP, LIST_COLS)
        body.put(self.countries_frame, LIST_AT, 2, LIST_COLS, GROUP + 2)
        # The manager's name under the list: the line (open once a country is chosen) and what it says.
        name_frame, inner = framed("manager's name", LIST_COLS, 4)
        self.field = CellLineField(MANAGER_MAX, count=True, on_click=self.press_enter_key)
        inner.put(self.field, 0, 0, LIST_COLS)
        self.name_note = CellPara(NAME_NOTE, "sub")
        inner.put(self.name_note, 0, 1, LIST_COLS, 3)
        body.put(name_frame, LIST_AT, GROUP + 4, LIST_COLS, 5)

    def _show(self):
        number, name, world, continent, within = self.order[self.index]
        start = self.index // GROUP * GROUP
        self.countries_frame.set_label("continental rank" if self.continental else "world rank")
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
            self.card_view.set_card(self.card, self.average)
            self.first.setText("first: " + self.first_match)

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
        self.name_note.setText(text)
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
