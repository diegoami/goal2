"""S15 Match menu: before kick-off, at half time, before extra time and at full time.

[designed: owner, 2026-11-03, #526, #523; docs/design/ui-2026-11 S15 and its mockup s15-match-menu.html; T167, #541]
[confirmed: T156-R1 steps 42, 47-49, 68-73, 193-198, 264; t156-042-match-menu.png, t156-193-fulltime-menu.png; E031
C36, C37]

- **Shows** the score, the kind of match, the location (the home side's country, `DesktopModel.home`, #562;
  t156-042 "location: Norway"), the time (before kick-off, HALF TIME, EXTRA TIME, FULL TIME), and both sides'
  formations and elevens, the home side on the left, each name in its side's kit (#583).
- **The actions**, *play* highlighted first as in the original (step 42): each side's team tactics and players,
  tournament (S12), match stats (S20), and **play** (before and during) or **exit** (after the final whistle).
  *play* names what follows: "choose your captain, then kick-off" before the match, "second half" at half time,
  "extra time" before it [designed: #523].
- **Arrows** follow the visible menu rows and country columns: Up/Down keeps the selected country,
  initially the managed side; Left/Right selects the corresponding column on tactics/players rows
  [confirmed: T156-R1 steps69-73; owner playtest #596].
- **Your side** before kick-off: team tactics opens S10 (also **T**), players opens S08 (also **Space**), and what they
  change is the model's, before the engine is asked. At a break of the match (half time, before extra time, a
  substitution opportunity: phase "stop", after S18's key, T156-R1 step 68) *players* opens the bench, S19, in *make
  substitutions now* mode, and *play* sends the bench's answer [designed: T180, #574].
  [designed: owner #610] Managed team tactics remain editable during pauses and breaks, with the original
  confirming each change while stopped. After the final whistle, players and tactics are read only. The
  other side's are read only (E031 C36: "view only").
- **Ins** turns the automatic action replay on or off; the label names the state, as the original's (E031 C37). The
  flag is stored in the data folder (`settings.json`, `automatic_action_replay`) [designed: T167]; the replay itself
  is T181's.
- **The watch question** [confirmed: F030 at 1bd066ca, `0791:E80D`]: where the original asks *Do you want to watch
  this match?* (`match_day.asks_watch`), the menu asks it before kick-off with **Y**/**N**; it has no timeout. N plays
  a quick result: S17 with R pressed (owner decision 3).
"""
from __future__ import annotations

from PySide6.QtCore import Qt

from goal2.ui import theme
from goal2.ui.pitch import HOME
from goal2.ui.screen import Screen
from goal2.ui.kits import for_fixture
from goal2.ui.squad_card import colour

TIMES = {"before": "before kick-off", "half": "HALF TIME", "extra": "EXTRA TIME", "full": "FULL TIME",
         "stop": "SUBSTITUTION OPPORTUNITY", "pause": "PAUSED"}
NEXT = {"before": "next: choose your captain, then kick-off", "half": "next: second half", "extra": "next: extra time",
        "stop": "next: play on", "pause": "resume the match"}
DURING = "These tactics and players are view only."
WATCH = "Do you want to watch this match? (Y/N)"   # [confirmed: E031 C35, "Do you want to watch this match ?"]


class MenuScreen(Screen):
    GRID = True   # [designed: owner, #667; T213]
    escape_text = "select Play / Exit"

    def __init__(self, window, day, phase, score=(0, 0)):
        self.escape_text = "resume match" if phase in ("pause", "half", "stop", "extra") else "select Play / Exit"
        super().__init__(window)
        self.day, self.phase = day, phase
        model, fixture = day.model, day.fixture
        self.model = model
        names = model.goaldat.country_names
        sides = (fixture.side_a, fixture.side_b)
        self.home_country, self.away_country = sides[HOME], sides[1 - HOME]
        own = model.state.managed_country
        self.menu_country = own
        self.country_options = {}
        self.title = f"match menu · {names[self.home_country]} v {names[self.away_country]}"
        self.name_label.setText(self.title)
        # [designed: owner, #667; T213] Score and situation over the two elevens and the existing two-country menu.
        from goal2.ui.cells import Cells, CellPara
        kits = for_fixture(model, fixture)
        body = Cells(90,25,"matchBody")
        self.body_layout.addWidget(body,1)
        head = Cells(90, 2, "matchHead")
        first = head.text(names[self.home_country], "h1", 0, 0, 16)
        colour(first, kits.colour(HOME))
        self.score_label = head.text(f"{score[HOME]}  v  {score[1-HOME]}", "h1", 17, 0, 10)
        second = head.text(names[self.away_country], "h1", 28, 0, 16)
        colour(second, kits.colour(1-HOME))
        self.situation = CellPara(f"{day.kind_name.upper()} · location: {names[model.home(fixture)]} · {TIMES[phase]}", "sub")
        head.put(self.situation, 0, 1, 90)
        self.replay_label = head.text("", "sub", 56, 0, 34)
        body.put(head,0,0,90,2)
        middle = Cells(90,20,"matchMenuBody")
        self.lineups = {}
        self._accepted_projection = None
        self.lineup_words = {}
        self.lineup_rows = {}
        self.lineup_headings = {}
        boxes = {c: self._lineup(c) for c in (self.home_country, self.away_country)}
        middle.put(boxes[self.home_country],0,0,28,20)
        from goal2.ui.cells import CellPara
        def option(text, handler, **kwargs):
            item = self.add_option(text, handler, rows=1, **kwargs)
            old = item.text_label
            item.layout().replaceWidget(old, CellPara(text,"optionText"))
            item.text_label = item.findChildren(CellPara)[0]
            old.setParent(None)
            old.deleteLater()
            return item
        for column,country in enumerate((self.home_country,self.away_country)):
            mine = country == own
            tactics = option(f"{names[country]} team tactics", lambda c=country:self.tactics(c),
                             key=Qt.Key.Key_T if mine else None,enter="Team tactics")
            players = option(f"{names[country]} players", lambda c=country:self.players(c),
                             key=Qt.Key.Key_Space if mine else None,enter="Players")
            self.country_options[country] = (tactics,players)
            middle.put(tactics,29+17*column,0,15,3)
            middle.put(players,29+17*column,4,15,3)
        tournament = option("tournament", self.tournament, enter="Tournament")
        stats = option("match stats", self.stats, enter="Match stats")
        middle.put(tournament,29,8,32,2)
        middle.put(stats,29,10,32,2)
        if phase == "full":
            self.play = option("exit", day.exit, enter="Exit")
        else:
            self.play = option(f"▶ play     {NEXT[phase]}", self.press_play, enter="Play")
        middle.put(self.play,29,16,32,4)
        self.shared_options = (tournament, stats, self.play)
        # [confirmed: T156-R1 69-73; T184] Vertical keys follow visible rows. The two
        # country columns are horizontal alternatives, not extra vertical entries.
        for binding in self.bindings:
            if binding.keys == (Qt.Key.Key_Up,):
                binding.handler = lambda: self.move_row(-1)
            elif binding.keys == (Qt.Key.Key_Down,):
                binding.handler = lambda: self.move_row(1)
        self.bind((Qt.Key.Key_Left,), "", lambda: self.select_country(self.home_country),
                  captions=("←",), shown=False)
        self.bind((Qt.Key.Key_Right,), "", lambda: self.select_country(self.away_country),
                  captions=("→",), shown=False)
        self.bind((), "country", None, captions=("←", "→"))
        self.note = CellPara("", "sub")
        colour(self.note, theme.VALUE)
        middle.put(self.note,29,12,32,4)
        middle.put(boxes[self.away_country],62,0,28,20)
        body.put(middle,0,2,90,20)
        self.main_layout.removeWidget(self.wait_box)
        body.put(self.wait_box,0,22,90,3)
        for binding in self.bindings:
            if binding.keys == (Qt.Key.Key_T,): binding.text = "team tactics"
            elif binding.keys == (Qt.Key.Key_Space,): binding.text = "players"
        self._refresh_bar()
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
        bench = self.day.bench if country == state.managed_country and self.phase != "before" else None
        if country == state.managed_country:
            eleven = list(bench.eleven if bench is not None else state.starting_eleven or state.managed_squad[:11])
            from goal2.game import roles
            codes, lines = roles.tables(state)
            positions = [bench.position(w) if bench is not None else state.players[w][6] for w in eleven]
            formation = "-".join(str(sum(1 for p in positions if p < 14 and lines[p] == line)) for line in (1, 2, 3))
        else:
            eleven, formation = info["players"][:11], info["formation"]
        from goal2.ui.country_parts import framed
        from goal2.ui.cell_parts import CellTableRow
        frame, column = framed(f"{names[country]} · {formation}",28,19)
        rows = []
        widgets = []
        for word in eleven:
            c = bench.card(word) if bench is not None else card(state, word, model.goaldat)
            injured = bench is not None and word in bench.injured
            line = CellTableRow(-1, (2,25), gaps=(0,1))
            from goal2.ui.squad_card import LINE_COLOUR
            line.set((c["role"], c["full_name"] + (" · INJURED" if injured else "")),
                     (LINE_COLOUR.get(c["line"], theme.TEXT_NORMAL), theme.BAD if injured else LINE_COLOUR.get(c["line"], theme.TEXT_NORMAL)))
            if country == self.away_country:
                line.cells[1].setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            line.setCursor(Qt.CursorShape.ArrowCursor)
            column.put(line,0,min(2*len(widgets),len(widgets)+8),28)
            rows.append(tuple(line.texts()))
            widgets.append(line)
        if bench is not None:
            self._accepted_projection = self._lineup_signature(bench)
        self.lineup_words[country] = list(eleven)
        self.lineups[country] = (formation, rows)
        self.lineup_rows[country] = widgets
        self.lineup_headings[country] = frame.rule
        return frame

    @staticmethod
    def _lineup_signature(bench):
        # Only these accepted fields affect these role/name/injury rows.
        # Request/tactics acknowledgements still refresh the status below.
        return (tuple(bench.eleven),tuple(bench.position(w) for w in bench.eleven),
                frozenset(w for w in bench.injured if w in bench.eleven))

    def refresh_accepted(self):
        """[designed: T203] Current accepted XI/cue after a stopped acknowledgement."""
        bench = self.day.bench
        if bench is None or self.phase == "before":
            return
        signature = self._lineup_signature(bench)
        if signature != self._accepted_projection:
            from goal2.game import roles
            from goal2.ui.squad_card import LINE_COLOUR
            country = self.model.state.managed_country
            codes, lines = roles.tables(self.model.state)
            positions = [bench.position(w) for w in bench.eleven]
            formation = "-".join(str(sum(1 for p in positions if p < 14 and lines[p] == line)) for line in (1,2,3))
            rows = []
            for row, word in zip(self.lineup_rows[country],bench.eleven):
                card = bench.card(word);injured = word in bench.injured
                row.set((card["role"],card["full_name"]+(" · INJURED" if injured else "")),
                        (LINE_COLOUR.get(card["line"],theme.TEXT_NORMAL),theme.BAD if injured else LINE_COLOUR.get(card["line"],theme.TEXT_NORMAL)))
                rows.append(tuple(row.texts()))
            self.lineup_words[country] = list(bench.eleven)
            self.lineups[country] = (formation,rows)
            self.lineup_headings[country].setText(f"{self.model.goaldat.country_names[country]} · {formation}".upper())
            self._accepted_projection = signature
        names = self.model.goaldat.country_names
        time = TIMES[self.phase] if self.phase != "stop" or bench.opportunity_visible else "MATCH STOPPED"
        self.situation.setText(f"{self.day.kind_name.upper()} · location: {names[self.model.home(self.day.fixture)]} · {time}")

    def highlight(self, index):
        super().highlight(index)
        option = self.highlighted()
        for country, pair in getattr(self, 'country_options', {}).items():
            if option in pair:
                self.menu_country = country
                break

    def move_row(self, step):
        rows = (*self.country_options[self.menu_country], *self.shared_options)
        index = rows.index(self.highlighted())
        target = rows[max(0, min(index + step, len(rows) - 1))]
        self.highlight(self.options.index(target))

    def select_country(self, country):
        current = self.highlighted()
        pair = self.country_options[self.menu_country]
        if current in pair:
            target = self.country_options[country][pair.index(current)]
            self.highlight(self.options.index(target))

    def restore_navigation(self, previous):
        """Keep row/country when a changed pre-match lineup rebuilds the menu (T184)."""
        previous_rows = (*previous.country_options[previous.menu_country], *previous.shared_options)
        row = previous_rows.index(previous.highlighted())
        self.menu_country = previous.menu_country
        rows = (*self.country_options[self.menu_country], *self.shared_options)
        self.highlight(self.options.index(rows[row]))

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

    def escape(self):
        # [confirmed: original 0791:ED8A; measurements/610-live-team-tactics/original-esc-v1]
        # Active-menu Esc resumes through the same XI validation as Play.
        if self.phase in ("pause", "half", "stop", "extra"):
            return self.press_play()
        self.highlight(self.options.index(self.play))
        action = "Exit" if self.phase == "full" else "Play"
        self.say(f"Choose {action} or press Enter to " +
                 ("return to the desk." if self.phase == "full" else
                  "continue. The match stays stopped until you choose Play."))

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
        if country == model.state.managed_country and self.day.bench is not None:
            return self.day.open_team_tactics()
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
        else:
            self.refresh_accepted()


class SavedGoalMenu(Screen):
    """[designed: T181; confirmed: t156-246-goal-replay-menu] S15 before a saved goal's S17 replay.

    The saved lineup display is frozen at kick-off. Live tactics, players and tournament actions are absent:
    this recording has no career or engine to change [designed: T181, #575].
    """
    GRID = True   # [designed: owner, #667; T213]
    title = 'match menu · saved goal'

    def __init__(self, window, model, record):
        super().__init__(window)
        self.record = record
        data = record['data']
        from goal2.ui.kits import Kits
        kits = Kits(tuple(data['kits']['shirt']), tuple(data['kits']['keeper']))
        from goal2.ui.cells import Cells, CellPara
        from goal2.ui.country_parts import framed
        body = Cells(90,25,"savedGoalBody")
        self.body_layout.addWidget(body,1)
        frame,inner = framed("saved goal",90,2)
        countries,score = data["countries"],data["score"]
        inner.text(f"{countries[HOME]}  {score[HOME]} v {score[1-HOME]}  {countries[1-HOME]}","h1",0,0,90)
        inner.text(f"{data['kind']} · {data['scorer']} · {data['minute']}′","sub",0,1,90)
        body.put(frame,0,0,90,3)
        for column,team in enumerate((HOME,1-HOME)):
            saved = data.get("menu",{}).get(str(team),["",[]])
            panel,inner = framed(f"{countries[team]} · {saved[0]}",44,11)
            for index,(role,name) in enumerate(saved[1]):
                colour(inner.text(f"{role}  {name}","value",14,index,30),kits.colour(team))
            body.put(panel,46*column,4,44,12)
        self.play = self.add_option("▶ play",lambda:self.play_goal(window,model),enter="Play")
        body.put(self.play,0,18,90,2)
        body.put(self.add_option("exit",window.pop,enter="Exit"),0,20,90,2)
        body.put(CellPara("Saved goal: play the recording, or Esc back to the list.","sub"),0,24,90)
        self.highlight(0)

    def play_goal(self, window, model):
        from goal2.ui.replays import play_saved
        return play_saved(window, model, self.record)
