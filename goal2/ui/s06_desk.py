"""S06 The manager's desk: the landing page and home of an open career.

[designed: owner, 2026-11-03, #526 decision 1; docs/design/ui-2026-11, S06 and its mockup s06-hub.html; T164, #538]
After a new career (S04) or a load (S02) the player lands here, and every management screen returns here with Esc.
Everything the original's hub offers is on this page, nothing behind another screen [confirmed: T156-R1 step 13,
docs/original-game/images/t156-013-hub.png]:

- the manager (name; *rating unknown*, as the original shows a new manager's and as the mockup draws it: the Python
  route keeps no rating), the team with its world and continental rankings, the next opponents with theirs and the
  match's kind, the managers, and the twenty with their role codes, the eleven above the bench;
- the six options, in the original's order: *team info* (S07), *fixture list* (S11), *tournament* (S12), *history*
  (S13), *select squad* (Space, S08) and *play next game*. The cursor starts on *team info*, ↑↓ move it, Enter opens the option, a click on an
  option does the same [confirmed: T156-R1 steps 13, 36–41];
- **T** team tactics (S10), **Space** select squad (S08), **F1** help (S22); **F3** load a saved goal, **F4** load a
  saved summary, **F7** save, **F10** quit [confirmed: t156-013-hub.png, its bottom line].

Placeholders [designed: T164, the task's scope]: *play next game* opens the match screens of T167; F3 comes with
T167, F4, F7 and F10 with T168. Until then each says which task brings it, on the desk, and does nothing else.

The banner names the competition as the original's hub does, *European Championship · QUALIFYING* and the year for a
European country (`DesktopModel.competition`, #563) [confirmed: t156-013-hub.png], drawn as the mockup: the year,
the name in the banner's light red, the phase [designed: s06-hub.html].

[designed: owner decision 14, #526] *re-import data*, a goal2 addition, opens S01 over the data folder (to add
GOAL.HLP later); Esc there returns to the desk. It is the seventh option, after the original's six and set apart under
a "goal2 addition" tag, so ↑↓ reach it and no key is added.

The venue of the next match is not shown: the Python route stores a fixture's two countries without assigning a
pitch role [designed: T41a, goal2/game/campaign.py `Fixture.side_a`], so the desk shows the match's kind only,
not the mockup's "away".

Everything shown is the model's (`DesktopModel.summary`, `view`, `countries`; `goal2.game.country_card.card` for the
rankings), route (b) [designed: owner, 2026-11-03, #527 D2]. The desk never saves: saving is T168's, through
`goal2.ui.saves.write`.
"""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QHBoxLayout, QVBoxLayout, QWidget

from goal2.desktop import data_setup
from goal2.game.country_card import card as country_card
from goal2.ui import theme
from goal2.ui.s01_import import ImportScreen, checks
from goal2.ui.screen import Screen, label, para, set_para
from goal2.ui.squad_card import Strip, box, colour, full_name, squad_rows
from goal2.ui.start_look import key_value

LEFT_WIDTH = 420   # [designed: s06-hub.html, the left column's `width:420px`]
HINT = ("Use ↑↓ to find an option, Enter to select it. Your own matches are watched: play next game leads to the "
        "match menu, the captain and the pitch.")   # [designed: s06-hub.html]
# What each placeholder says until its task builds it. [designed: T164 scope 1, "each names the task"]
LATER = {
    "play next game": "The match screens (S14–S20) come with T167: play next game opens them then.",
    "F3": "F3, load a saved goal, comes with T167.",
    "F4": "F4, load a saved summary, comes with T168.",
    "F7": "F7, save, comes with T168.",
    "F10": "F10, quit with the save question, comes with T168.",
}


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
    return opponent, model.fixture_label(fixture).split(" / ", 1)[1].lower()


class DeskScreen(Screen):
    title = "manager's desk"
    escape_text = None   # the home: nothing under it [designed: §3 "Navigation"]

    def __init__(self, window, model):
        super().__init__(window)
        self.model = model
        self.message = ""
        self._banner()
        for key, caption, text in ((Qt.Key.Key_F3, "F3", "load goal"), (Qt.Key.Key_F4, "F4", "load summary"),
                                   (Qt.Key.Key_F7, "F7", "save"), (Qt.Key.Key_F10, "F10", "quit")):
            self.bind((key,), text, lambda caption=caption: self.later(caption))
        self.bind((Qt.Key.Key_T,), "team tactics", self.team_tactics)
        self._build()
        self.refresh()

    # Building.
    def _banner(self):
        """The competition's banner at the title bar's right end, as the original's and the mockup's."""
        self.banner = label("", "who")
        self.banner.setTextFormat(Qt.TextFormat.RichText)
        self.name_label.parentWidget().layout().addWidget(self.banner)

    def _build(self):
        main = QHBoxLayout()
        main.setSpacing(18)
        left_widget = QWidget()
        left_widget.setFixedWidth(LEFT_WIDTH)
        left = QVBoxLayout(left_widget)
        left.setContentsMargins(0, 0, 0, 0)
        left.setSpacing(14)
        manager, inner = box("Manager")
        rows, self.manager = key_value((("name", "name"), ("rating", "rating")))
        inner.addWidget(rows)
        left.addWidget(manager)
        team, inner = box("Team")
        self.team_name = label("", "h1")
        inner.addWidget(self.team_name)
        rows, self.team_ranks = key_value((("world", "world"), ("continent", "continent")))
        inner.addWidget(rows)
        left.addWidget(team)
        opponents, inner = box("Next opponents")
        self.opponent_name = label("", "h1")
        colour(self.opponent_name, theme.VALUE)
        inner.addWidget(self.opponent_name)
        rows, self.opponent_ranks = key_value((("world", "world"), ("continent", "continent"), ("match", "match")))
        inner.addWidget(rows)
        left.addWidget(opponents)
        managers, inner = box("Managers")
        self.managers = label("", "value")
        self.managers.setTextFormat(Qt.TextFormat.RichText)
        inner.addWidget(self.managers)
        left.addWidget(managers)
        left.addStretch(1)
        main.addWidget(left_widget)
        middle = QVBoxLayout()
        middle.setSpacing(10)
        self.body_layout.addLayout(main, 1)
        # The six options, in the original's order. [confirmed: t156-013-hub.png]
        self.add_option("team info", self.team_info, enter="Team info")
        self.add_option("fixture list", self.fixture_list, enter="Fixture list")
        self.add_option("tournament", self.tournament, enter="Tournament")
        self.add_option("history", self.history, enter="History")
        self.add_option("select squad", self.select_squad, key=Qt.Key.Key_Space, enter="Select squad")
        play = self.add_option("play next game", lambda: self.later("play next game"), enter="Play next game")
        self.play_note = label("", "sub")
        play.layout().insertWidget(1, self.play_note)
        # Space is on its option, not on the bar, as the mockup draws it. [designed: s06-hub.html]
        for binding in self.bindings:
            if binding.keys == (Qt.Key.Key_Space,):
                binding.shown = False
        self._refresh_bar()
        for option in self.options:
            middle.addWidget(option)
        middle.addSpacing(4)
        middle.addWidget(para(HINT, "sub"))
        middle.addSpacing(10)
        self.note = para("", "sub")
        colour(self.note, theme.VALUE)
        middle.addWidget(self.note)
        middle.addStretch(1)
        addition = QHBoxLayout()
        addition.addWidget(label("GOAL2 ADDITION", "tagNew"), 0, Qt.AlignmentFlag.AlignLeft)
        addition.addStretch(1)
        middle.addLayout(addition)
        reimport = self.add_option("re-import data", self.reimport, enter="Re-import data")
        middle.addWidget(reimport)
        main.addLayout(middle, 1)
        self.strip = Strip()
        for row in self.strip.rows:
            row.setCursor(Qt.CursorShape.ArrowCursor)   # the desk's strip is read only, as the original's
        main.addWidget(self.strip)

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
        set_para(self.note, self.message)

    @staticmethod
    def _ranks(values, card):
        """World and continental rank, the continent's name as the caption (Europe, America…), as the original."""
        values["world"].setText(str(card["world"]))
        values["continent"].caption.setText(card["continent"])
        values["continent"].setText(str(card["continental"]))

    def say(self, text):
        self.message = text
        set_para(self.note, text)

    def shown(self):
        """Back from a screen the desk opened: read the model again (a swap, a new name, the tactics)."""
        self.message = ""
        self.refresh()

    # The actions.
    def later(self, what):
        """A placeholder: it says which task brings it, and does nothing else."""
        self.say(LATER[what])

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

    def reimport(self):
        return self.window_.push(ReimportScreen(self.window_, self.window_.target, self.window_.choose))


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
