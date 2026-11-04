"""S15 Match menu: before kick-off, at half time, before extra time and at full time.

[designed: owner, 2026-11-03, #526, #523; docs/design/ui-2026-11 S15 and its mockup s15-match-menu.html; T167, #541]
[confirmed: T156-R1 steps 42, 47-49, 68-73, 193-198, 264; t156-042-match-menu.png, t156-193-fulltime-menu.png; E031
C36, C37]

- **Shows** the score, the kind of match, the location (the home side's country, `DesktopModel.home`, #562;
  t156-042 "location: Norway"), the time (before kick-off, HALF TIME, EXTRA TIME, FULL TIME), and both sides'
  formations and elevens, the home side on the left in light red, as the original's menu.
- **The actions**, *play* highlighted first as in the original (step 42): each side's team tactics and players,
  tournament (S12), match stats (S20), and **play** (before and during) or **exit** (after the final whistle).
  *play* names what follows: "choose your captain, then kick-off" before the match, "second half" at half time,
  "extra time" before it [designed: #523].
- **Your side** before kick-off: team tactics opens S10 (also **T**), players opens S08 (also **Space**), and what they
  change is the model's, before the engine is asked. At a break of the match (half time, before extra time, a
  substitution opportunity: phase "stop", after S18's key, T156-R1 step 68) *players* opens the bench, S19, in *make
  substitutions now* mode, and *play* sends the bench's answer [designed: T180, #574]. Team tactics during the match,
  and players after the final whistle, open read only: the bridge plays the state it was given [designed: T167]. The
  other side's are read only (E031 C36: "view only").
- **Ins** turns the automatic action replay on or off; the label names the state, as the original's (E031 C37). The
  flag is stored in the data folder (`settings.json`, `automatic_action_replay`) [designed: T167]; the replay itself
  is T168's.
- **The watch question** [confirmed: F030 at 1bd066ca, `0791:E80D`]: where the original asks *Do you want to watch
  this match?* (`match_day.asks_watch`), the menu asks it before kick-off with **Y**/**N**; it has no timeout. N plays
  a quick result: S17 with R pressed (owner decision 3).
"""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QHBoxLayout, QVBoxLayout

from goal2.ui import theme
from goal2.ui.pitch import HOME
from goal2.ui.screen import Screen, label, para
from goal2.ui.squad_card import Row, box, colour

TIMES = {"before": "before kick-off", "half": "HALF TIME", "extra": "EXTRA TIME", "full": "FULL TIME",
         "stop": "SUBSTITUTION OPPORTUNITY"}
NEXT = {"before": "next: choose your captain, then kick-off", "half": "next: second half", "extra": "next: extra time",
        "stop": "next: play on"}
DURING = "During the match your team tactics are shown read only; players opens the bench at a break."
WATCH = "Do you want to watch this match? (Y/N)"   # [confirmed: E031 C35, "Do you want to watch this match ?"]


class MenuScreen(Screen):
    escape_text = None

    def __init__(self, window, day, phase, score=(0, 0)):
        super().__init__(window)
        self.day, self.phase = day, phase
        model, fixture = day.model, day.fixture
        self.model = model
        names = model.goaldat.country_names
        sides = (fixture.side_a, fixture.side_b)
        self.home_country, self.away_country = sides[HOME], sides[1 - HOME]
        own = model.state.managed_country
        self.title = f"match menu · {names[self.home_country]} v {names[self.away_country]}"
        self.name_label.setText(self.title)
        head, inner = box(None)
        row = QHBoxLayout()
        row.setSpacing(24)
        inner.addLayout(row)
        first = label(names[self.home_country], "h1")
        colour(first, theme.HOME_SIDE)
        row.addWidget(first)
        self.score_label = label(f"{score[HOME]}  v  {score[1 - HOME]}", "h1")
        row.addWidget(self.score_label)
        row.addWidget(label(names[self.away_country], "h1"))
        self.situation = label(f"{day.kind_name.upper()} · location: {names[model.home(fixture)]} · {TIMES[phase]}",
                               "sub")
        row.addWidget(self.situation)
        row.addStretch(1)
        self.replay_label = label("", "sub")
        row.addWidget(self.replay_label)
        self.body_layout.addWidget(head)
        middle = QHBoxLayout()
        middle.setSpacing(18)
        self.lineups = {}
        boxes = {c: self._lineup(c) for c in (self.home_country, self.away_country)}
        middle.addWidget(boxes[self.home_country])
        centre = QVBoxLayout()
        centre.setSpacing(12)
        sides_row = QHBoxLayout()
        sides_row.setSpacing(12)
        for country in (self.home_country, self.away_country):
            column = QVBoxLayout()
            column.setSpacing(10)
            mine = country == own
            column.addWidget(self.add_option(f"{names[country]} team tactics",
                                             (lambda c=country: self.tactics(c)),
                                             key=Qt.Key.Key_T if mine else None, enter="Team tactics"))
            column.addWidget(self.add_option(f"{names[country]} players", (lambda c=country: self.players(c)),
                                             key=Qt.Key.Key_Space if mine else None, enter="Players"))
            sides_row.addLayout(column, 1)
        centre.addLayout(sides_row)
        centre.addWidget(self.add_option("tournament", self.tournament, enter="Tournament"))
        centre.addWidget(self.add_option("match stats", self.stats, enter="Match stats"))
        if phase == "full":
            self.play = self.add_option("exit", day.exit, enter="Exit")
        else:
            self.play = self.add_option(f"▶ play     {NEXT[phase]}", self.press_play, enter="Play")
        centre.addWidget(self.play)
        self.note = para("", "sub")
        colour(self.note, theme.VALUE)
        centre.addWidget(self.note)
        centre.addStretch(1)
        middle.addLayout(centre, 1)
        middle.addWidget(boxes[self.away_country])
        self.body_layout.addLayout(middle, 1)
        self.bind((Qt.Key.Key_Insert,), "action replay on/off", self.toggle_replay)
        self.watch_bindings = []
        self.highlight(self.options.index(self.play))
        self._show_replay()
        if phase == "before" and day.watch is None and day.asks_watch(model, fixture):
            self.wait_for(WATCH, "Y: watch it on the pitch · N: a quick result (S17 with R pressed). The question "
                                 "waits for your answer, as the original's.")
            self.bind((Qt.Key.Key_Y,), "watch", lambda: self.answer_watch(True))
            self.bind((Qt.Key.Key_N,), "quick result", lambda: self.answer_watch(False))

    def _lineup(self, country):
        """A side's formation and eleven: yours from the model's eleven, the other from its record (F008, F024)."""
        from goal2.game.country_card import card as country_card
        from goal2.game.player_card import card
        state, model = self.model.state, self.model
        names = model.goaldat.country_names
        info = country_card(state, country, model.goaldat)
        if country == state.managed_country:
            eleven = list(state.starting_eleven or state.managed_squad[:11])
            from goal2.game import roles
            codes, lines = roles.tables(state)
            positions = [state.players[w][6] for w in eleven]
            formation = "-".join(str(sum(1 for p in positions if p < 14 and lines[p] == line)) for line in (1, 2, 3))
        else:
            eleven, formation = info["players"][:11], info["formation"]
        frame, column = box(f"{names[country]} · {formation}")
        frame.setFixedWidth(300)
        rows = []
        for word in eleven:
            c = card(state, word, model.goaldat)
            line = Row(-1, (22, 0))
            from goal2.ui.squad_card import LINE_COLOUR
            line.set((c["role"], c["full_name"]), (LINE_COLOUR.get(c["line"], theme.TEXT_NORMAL), theme.TEXT_BRIGHT))
            line.setCursor(Qt.CursorShape.ArrowCursor)
            column.addWidget(line)
            rows.append(tuple(line.texts()))
        column.addStretch(1)
        self.lineups[country] = (formation, rows)
        return frame

    def say(self, text):
        from goal2.ui.screen import set_para
        set_para(self.note, text or "")

    def _show_replay(self):
        on = self.day.replay_auto
        self.replay_label.setText(f"automatic action replay {'ON' if on else 'OFF'} (Ins)")

    def toggle_replay(self):
        self.day.set_replay_auto(not self.day.replay_auto)
        self._show_replay()

    def answer_watch(self, watch):
        self.day.watch = bool(watch)
        self.wait_for(None)
        self.bindings = [b for b in self.bindings if b.keys not in ((Qt.Key.Key_Y,), (Qt.Key.Key_N,))]
        self._refresh_bar()
        self.say("You watch this match." if watch else "A quick result: the pitch shows HANG ON A TICK.")

    def press_play(self):
        if self.phase == "before" and self.day.watch is None and self.day.asks_watch(self.model, self.day.fixture):
            self.say("Answer the question first: Y to watch, N for a quick result.")
            return None
        return self.day.play(self)

    # The actions.
    def during(self):
        return self.phase != "before"

    def tactics(self, country):
        window, model = self.window_, self.model
        if country == model.state.managed_country and not self.during():
            from goal2.ui.s10_team_tactics import open_team_tactics
            return open_team_tactics(window, model)
        from goal2.ui.s07_team_info import CountryTacticsScreen
        if country == model.state.managed_country:
            self.say(DURING)
        return window.push(CountryTacticsScreen(window, model, country))

    def players(self, country):
        window, model = self.window_, self.model
        if country == model.state.managed_country and not self.during():
            from goal2.ui.s08_squad import open_squad
            return open_squad(window, model)
        if country == model.state.managed_country and self.day.bench is not None:
            return self.day.open_bench()   # S19 at a break [designed: T180]
        from goal2.ui.s07_team_info import TeamPlayersScreen
        if country == model.state.managed_country:
            self.say(DURING)
            country = None
        return window.push(TeamPlayersScreen(window, model, model.goaldat.country_names[
            model.state.managed_country if country is None else country], country=country))

    def tournament(self):
        from goal2.ui.s12_tournament import TournamentScreen
        return self.window_.push(TournamentScreen(self.window_, self.model))

    def stats(self):
        return self.day.show_stats(self)

    def shown(self):
        """Back from S08 or S10 before kick-off: the elevens again (a swap may have changed yours)."""
        if self.phase == "before":
            self.day.refresh_menu(self)
