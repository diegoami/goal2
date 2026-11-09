"""S06 The manager's desk: the landing page and home of an open career.

[designed: owner, 2026-11-03, #526 decision 1; docs/design/ui-2026-11, S06 and its mockup s06-hub.html; T164, #538]
After a new career (S04) or a load (S02) the player lands here, and every management screen returns here with Esc.
Everything the original's hub offers is on this page, nothing behind another screen [confirmed: T156-R1 step 13,
docs/original-game/images/t156-013-hub.png]:

- the manager (name; *rating unknown*, as the original shows a new manager's and as the mockup draws it: the Python
  route keeps no rating), the team with its world and continental rankings, the next opponents with theirs and the
  match's kind, the managers, and the twenty with their role codes, the eleven above the bench;
- the six options, in the original's order: *team info* (S07), *fixture list* (S11), *tournament* (S12), *history*
  (S13), *select squad* (Space, S08) and *play next game*. The cursor starts on *team info*, ↑↓ move it, Enter opens
  the option, a click on an option does the same [confirmed: T156-R1 steps 13, 36–41];
- **T** team tactics (S10), **Space** select squad (S08), **F1** help (S22); **F3** load a saved goal, **F4** load a
  saved summary, **F7** save, **F10** quit [confirmed: t156-013-hub.png, its bottom line].

[designed: T181, #575] F3 lists saved goals, F4 saved summaries. **F7** saves and **F10** quits through S21 (goal2/ui/s21_save.py), with
the save question when anything is unsaved. [designed: T168, #542]

*play next game* [designed: T167, #541]: the match day (goal2/ui/match_day.py), the original's screens in its order:
S14 the round, S15 the match menu, S16 the captain, S17 the pitch, S20 the boards, then the round's remaining results
and this desk again, with the result in the status line. A friendly and a qualifier alike (T176). The desk closes the
match day's bridges when the window closes (`closing`), and with them the engine process.

The banner names the competition as the original's hub does, *European Championship · QUALIFYING* and the year for a
European country (`DesktopModel.competition`, #563) [confirmed: t156-013-hub.png], drawn as the mockup: the year,
the name in the banner's light red, the phase [designed: s06-hub.html].

[designed: owner decision 14, #526] *re-import data*, a goal2 addition, opens S01 over the data folder (to add
GOAL.HLP later); Esc there returns to the desk. It is the last option, after the original's six and set apart under
a "goal2 addition" tag, so ↑↓ reach it and no key is added.

The next match says home or away after its kind, as the original's hub (*friendly away*): the home side is the
fixture's side B (`DesktopModel.home`, `venue`) [confirmed: F031 "Venue", 000E:724A; #562].

Two more goal2 additions, today's extras the original lacks, sit beside it under the same tag [designed: owner, §6
item 18 (docs/design/ui-2026-11, 2026-11-03); T177, #557], options reached by ↑↓ and Enter or a click, so no key of the
original's hub changes meaning:
- *manager's name* opens a name line in the manager's box, 14 characters at most, as S04's (`MANAGER_MAX`): typing and
  Backspace edit it, **Enter** gives the name through `DesktopModel.rename_manager`, as today's desk's *Manager name*
  does (docs/desktop-management.md, T92), **Esc** keeps the old one. The career is then unsaved (the model's
  `unsaved`).
- *new career* goes to S03 New game over the desk, as today's Game menu's *New campaign*; with anything unsaved it
  asks S21's *Do you want to save this game?* first (`s21_save.ask_to_save`, T87's question): **Y** the name box, then
  S03; **N** S03 without saving; **Esc** stays on the desk. Esc on S03 returns to the desk and its career; a career
  started on S04 replaces it.

Everything shown is the model's (`DesktopModel.summary`, `view`, `countries`; `goal2.game.country_card.card` for the
rankings), route (b) [designed: owner, 2026-11-03, #527 D2]. The desk never saves through the model: F7 saves through
`goal2.ui.saves.write` only (S21).
"""
from __future__ import annotations

from PySide6.QtCore import Qt

from goal2.desktop import data_setup
from goal2.game.country_card import card as country_card
from goal2.game.identities import MANAGER_MAX
from goal2.ui import theme
from goal2.ui.cell_parts import CellLineField, GridStrip, key_values
from goal2.ui.cells import CellLabel, CellPara, Cells
from goal2.ui.frame import Frame
from goal2.ui.s01_import import ImportScreen, checks
from goal2.ui.screen import Screen
from goal2.ui.squad_card import colour, full_name, squad_rows

# [designed: T211; docs/design/ui-2026-11/proposal/README.md] The desk's cells: 90 columns and the 25 rows between the title row and the
# two key rows; the left column 30 wide, the middle 34, the strip 24, an empty column between each.
BODY_COLS, BODY_ROWS = theme.COLS, theme.ROWS - 3
LEFT_COLS, LABEL_COLS = 30, 6
MIDDLE_AT, MIDDLE_COLS = LEFT_COLS + 1, 34
STRIP_AT = MIDDLE_AT + MIDDLE_COLS + 1


def panel(label, cols, rows):
    """A frame (a rule with its lowercase label) over a body of `cols` x `rows` cells: (frame, its body's cells)."""
    frame = Frame(label)
    inner = Cells(cols, rows, "panelRows")
    frame.add(inner, 1)
    return frame, inner

HINT = ("↑↓ chooses; Enter opens. Play next game opens the match menu, captain and watched pitch.")   # [designed: s06-hub.html]



def next_match(model):
    """(opponent's number or None, the match's kind in words) of the career's next fixture, from the model's own
    labels (`DesktopModel.fixture_label`: Friendly, Qualifier or the stage)."""
    state = model.state
    campaign = state.campaign
    if campaign is None:
        return None, "quick friendly"
    fixture = campaign.next_fixture
    if fixture is None:
        return None, "stage complete"
    opponent = fixture.side_b if fixture.side_a == state.managed_country else fixture.side_a
    kind = model.fixture_label(fixture).split(" / ", 1)[1].lower()
    # [confirmed: F031 "Venue", 000E:724A; t156-013-hub.png "friendly away"] the hub's home or away (#562)
    return opponent, f"{kind} {model.venue(fixture)}"


class DeskScreen(Screen):
    GRID = True   # [designed: T211] laid out on the 16 x 32 grid, no card
    title = "manager's desk"
    escape_text = None   # the home: nothing under it [designed: §3 "Navigation"]
    naming = False       # the manager's name line is open [designed: T177]

    def __init__(self, window, model):
        super().__init__(window)
        self.model = model
        self.message = ""
        self._banner()
        self.bind((Qt.Key.Key_F3,), 'load goal', lambda: self.recordings('goal'))
        self.bind((Qt.Key.Key_F4,), 'load summary', lambda: self.recordings('summary'))
        self.bind((Qt.Key.Key_F7,), "save", self.save)
        self.bind((Qt.Key.Key_F10,), "quit", self.quit)
        self.bind((Qt.Key.Key_T,), "team tactics", self.team_tactics)
        self._build()
        self.refresh()

    # Building.
    def _banner(self):
        """The competition's banner at the title bar's right end, as the original's and the mockup's."""
        self.banner = CellLabel("", "who")
        self.banner.setTextFormat(Qt.TextFormat.RichText)
        self.name_label.parentWidget().layout().addWidget(self.banner)

    def _build(self):
        """[designed: owner, 2026-11-08, #667; T211; docs/design/ui-2026-11/proposal/README.md, s06-hub] The desk on the 90 x 25
        cells between the title row and the key rows: three columns, one empty cell apart. At the left the frames of the manager, the
        team, the next opponent and the managers, and under them the hint and the screen's message; in the middle the six options as
        boxes of two rows, as the original's, and the goal2 additions as boxes under their tag; at the right the twenty."""
        body = Cells(BODY_COLS, BODY_ROWS, "deskBody")
        self.body_layout.addWidget(body, 1)
        self.area = body
        # The left column.
        manager, inner = panel("manager", LEFT_COLS, 2)
        rows, self.manager = key_values((("name", "name"), ("rating", "rating")), LEFT_COLS, LABEL_COLS)
        inner.put(rows, 0, 0, LEFT_COLS, 2)
        # [designed: owner, §6 item 18; T177] the name line of *manager's name*, as S04's, hidden until it opens
        self.name_field = CellLineField(MANAGER_MAX, count=True)
        self.name_field.hide()
        inner.put(self.name_field, LABEL_COLS + 1, 0, LEFT_COLS - LABEL_COLS - 1)
        body.put(manager, 0, 0, LEFT_COLS, 3)
        team, inner = panel("team", LEFT_COLS, 3)
        self.team_name = inner.text("", "h1", 0, 0, LEFT_COLS)
        rows, self.team_ranks = key_values((("world", "world"), ("continent", "continent")), LEFT_COLS, LABEL_COLS)
        inner.put(rows, 0, 1, LEFT_COLS, 2)
        body.put(team, 0, 4, LEFT_COLS, 4)
        opponents, inner = panel("next opponents", LEFT_COLS, 4)
        self.opponent_name = inner.text("", "h1", 0, 0, LEFT_COLS)
        colour(self.opponent_name, theme.VALUE)
        rows, self.opponent_ranks = key_values((("world", "world"), ("continent", "continent"), ("match", "match")),
                                               LEFT_COLS, LABEL_COLS)
        inner.put(rows, 0, 1, LEFT_COLS, 3)
        body.put(opponents, 0, 9, LEFT_COLS, 5)
        managers, inner = panel("managers", LEFT_COLS, 1)
        self.managers = inner.text("", "value", 0, 0, LEFT_COLS)
        self.managers.setTextFormat(Qt.TextFormat.RichText)
        body.put(managers, 0, 15, LEFT_COLS, 2)
        body.put(CellPara(HINT, "sub"), 0, 18, LEFT_COLS, 4)
        # The six options, in the original's order. [confirmed: t156-013-hub.png]
        self.add_option("team info", self.team_info, enter="Team info")
        self.add_option("fixture list", self.fixture_list, enter="Fixture list")
        self.add_option("tournament", self.tournament, enter="Tournament")
        self.add_option("history", self.history, enter="History")
        self.add_option("select squad", self.select_squad, key=Qt.Key.Key_Space, enter="Select squad")
        self.add_option("play next game", self.play_next_game, enter="Play next game")
        self.play_note = CellLabel("", "sub")
        # Space is on its option, not on the bar, as the mockup draws it. [designed: s06-hub.html]
        for binding in self.bindings:
            if binding.keys == (Qt.Key.Key_Space,):
                binding.shown = False
        self._refresh_bar()
        for index, option in enumerate(self.options):
            body.put(option, MIDDLE_AT, 3 * index, MIDDLE_COLS, 2)   # a row between boxes, as the original's
        body.put(self.play_note, MIDDLE_AT, 17, MIDDLE_COLS)
        self.note = CellPara("", "sub")
        colour(self.note, theme.VALUE)
        body.put(self.note, 0, 22, LEFT_COLS, 3)
        body.text("GOAL2 ADDITION", "tagNew", MIDDLE_AT, 18)
        # [designed: owner #598] the extra actions keep their full size, boxes as the six
        for index, (text, handler, enter) in enumerate((("manager's name", self.rename, "New manager's name"),
                                                        ("new career", self.new_career, "New career"),
                                                        ("re-import data", self.reimport, "Re-import data"))):
            body.put(self.add_option(text, handler, enter=enter), MIDDLE_AT, 19 + 2 * index, MIDDLE_COLS, 2)
        self.strip = GridStrip()
        for row in self.strip.rows:
            row.setCursor(Qt.CursorShape.ArrowCursor)   # the desk's strip is read only, as the original's
        body.put(self.strip, STRIP_AT, 0, GridStrip.COLS, GridStrip.PAGE + 2)

    # What is shown.
    def refresh(self):
        model, state = self.model, self.model.state
        names = model.goaldat.country_names
        from goal2.ui.s12_tournament import banner_text
        competition = model.competition()
        self.banner.setText(banner_text(competition) if competition is not None else
                            f'<span style="color:{theme.TITLE_BANNER}">{_escape(model.summary()["campaign"])}</span>')
        self.manager["name"].setText(model.manager)
        self.manager["rating"].setText("unknown")
        own = country_card(state, state.managed_country, model.goaldat)
        self.team_name.setText(names[state.managed_country])
        self._ranks(self.team_ranks, own)
        opponent, kind = next_match(model)
        if opponent is None:
            self.opponent_name.setText("—")
            self.opponent_ranks["world"].setText("—")
            self.opponent_ranks["continent"].setText("—")
        else:
            self.opponent_name.setText(names[opponent])
            self._ranks(self.opponent_ranks, country_card(state, opponent, model.goaldat))
        self.opponent_ranks["match"].setText(kind)
        self.play_note.setText(f"{names[opponent]} · {kind}" if opponent is not None else kind)
        self.managers.setText(f'1 · {_escape(model.manager)} '
                              f'<span style="color:{theme.TEXT_NORMAL}">({_escape(names[state.managed_country])})'
                              '</span>')
        rows, eleven = squad_rows(model)
        self.strip.show_rows(names[state.managed_country],
                             [(r["role"], r["line"], full_name(model, r["id"])) for r in rows], -1, eleven == 11)
        self.note.setText(self.message)

    @staticmethod
    def _ranks(values, card):
        """World and continental rank, the continent's name as the caption (Europe, America…), as the original."""
        values["world"].setText(str(card["world"]))
        values["continent"].caption.setText(card["continent"])
        values["continent"].setText(str(card["continental"]))

    def say(self, text):
        self.message = text
        self.note.setText(text)

    def shown(self):
        """Back from a screen the desk opened: read the model again (a swap, a new name, the tactics)."""
        self.message = ""
        self.refresh()

    # The name line. [designed: owner, §6 item 18; T177]
    def enter_hint_text(self):
        return "Give this name" if self.naming else super().enter_hint_text()

    def type_text(self, key, text) -> bool:
        """On the name line, printable characters and Backspace edit the name; nothing else moves."""
        if not self.naming:
            return False
        if key == Qt.Key.Key_Backspace:
            self.name_field.backspace()
            return True
        if text and len(text) == 1 and text.isprintable():
            self.name_field.type(text)
            return True
        return False

    def handle_key(self, key):
        if self.naming:
            if key in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
                self.give_name()
            elif key == Qt.Key.Key_Escape:
                self.close_name()
            elif key == Qt.Key.Key_F1:
                return super().handle_key(key)
            return True
        return super().handle_key(key)

    def press_enter(self):
        if self.naming:
            return self.give_name()
        return super().press_enter()

    def rename(self):
        """*manager's name*: the name line, empty, the current name shown in it until a key is typed."""
        self.naming = True
        self.name_field.placeholder = self.model.manager
        self.name_field.set_text("")
        self.name_field.set_active(True)
        self.name_field.show()
        self.manager["name"].hide()
        self.say("New manager: 14 characters maximum. Enter confirms; Esc cancels.")
        self._refresh_hint()

    def give_name(self):
        """Enter on the name line: the model's `rename_manager`, as today's desk; the career is then unsaved."""
        text = self.name_field.text.strip()
        if not text:
            return self.say("Type the manager's name first: 14 characters at most. Esc keeps the old one.")
        try:
            name = self.model.rename_manager(text)
        except ValueError as exc:
            return self.say(str(exc))
        self.close_name()
        self.say(f"The manager is now {name}.")
        return name

    def close_name(self):
        self.naming = False
        self.name_field.set_active(False)
        self.name_field.hide()
        self.manager["name"].show()
        self.message = ""
        self.refresh()
        self._refresh_hint()

    def new_career(self):
        """*new career*: S03 over the desk, after S21's save question when anything is unsaved (T87, T168)."""
        def to_s03():
            from goal2.ui.s03_new_game import NewGameScreen
            return self.window_.push(NewGameScreen(self.window_))
        if self.model.unsaved:
            from goal2.ui.s21_save import ask_to_save
            return ask_to_save(self.window_, self.model, to_s03, title="new career")
        return to_s03()

    # The actions.
    def recordings(self, kind):
        from goal2.ui.replays import open_list
        return open_list(self.window_, self.model, kind)

    def play_next_game(self):
        """The match day (goal2/ui/match_day.py): S14, S15, S16, S17, S20; what stops it is said here."""
        from goal2.ui.match_day import play_next_game
        opened = play_next_game(self.window_, self.model)
        if isinstance(opened, str):
            self.say(opened)
        return opened

    def team_info(self):
        from goal2.ui.s07_team_info import TeamInfoScreen
        return self.window_.push(TeamInfoScreen(self.window_, self.model))

    def fixture_list(self):
        from goal2.ui.s11_fixtures import FixturesScreen
        return self.window_.push(FixturesScreen(self.window_, self.model))

    def tournament(self):
        from goal2.ui.s12_tournament import TournamentScreen
        return self.window_.push(TournamentScreen(self.window_, self.model))

    def history(self):
        from goal2.ui.s13_history import HistoryScreen
        return self.window_.push(HistoryScreen(self.window_, self.model))

    def select_squad(self):
        from goal2.ui.s08_squad import open_squad
        return open_squad(self.window_, self.model)

    def team_tactics(self):
        from goal2.ui.s10_team_tactics import open_team_tactics
        return open_team_tactics(self.window_, self.model)

    def closing(self):
        """The window closes: the match day's bridges close, and with them the engine process (D3, #417)."""
        from goal2.ui.match_day import close_window
        close_window(self.window_)

    def reimport(self):
        return self.window_.push(ReimportScreen(self.window_, self.window_.target, self.window_.choose))

    def save(self):
        """F7: S21's name box over the desk; once saved, the desk says the name."""
        from goal2.ui.s21_save import save
        return save(self.window_, self.model)

    def quit(self):
        """F10: S21's quit question, then the save question when anything is unsaved."""
        from goal2.ui.s21_save import quit_game
        return quit_game(self.window_, self.model)


def _escape(text):
    import html
    return html.escape(text)


class ReimportScreen(ImportScreen):
    """S01 over the desk, to import the data folder again (to add GOAL.HLP). It opens on the data folder's own
    checks; Enter chooses a folder and imports it, by `data_setup`'s rules unchanged, and an import returns to the
    desk; Esc returns to the desk. [designed: owner decision 14, #526; T164]"""
    title = "re-import data"
    pre_game = False
    escape_text = "desk"

    def __init__(self, window, target: data_setup.Paths, choose=None):
        super().__init__(window, target, choose)
        from PySide6.QtWidgets import QLabel
        for widget in self.findChildren(QLabel, "tagNew"):
            widget.setText("GOAL2 ADDITION · RE-IMPORT DATA")
        self.folder = target.data
        self.result = checks(target.data)
        self._show()

    def offer(self, folder) -> bool:
        """The folder's checks and its import, as S01's; once imported, back to the desk."""
        self.folder = folder
        self.result = checks(folder)
        try:
            data_setup.import_folder(folder, self.target, data_setup.WINDOW_MANIFEST)
        except data_setup.ImportRefused as exc:
            self._show(f"{exc}\nChoose the folder that holds all the files.")
            return False
        except data_setup.SetupError as exc:
            self._show(str(exc))
            return False
        self._show()
        self.window_.pop()
        return True

    def escape(self):
        self.window_.pop()
