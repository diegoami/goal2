"""The match day: *play next game* on the desk, through the original's screens in the original's order.

[designed: owner, 2026-11-03, #526 decisions 1 and 3, #527 D3; docs/design/ui-2026-11 §1's thick arrows, §3 "Stops"
and "The match"; T167, #541] [confirmed: T156-R1 steps 36-45, 118-119, 191-198, 262-270, 310-313]

    desk → S14 round → S15 menu → S16 captain → S17 pitch → S20 half time → S15 (play: second half) → S17
         → S20 full time → S15 exit → S14 the rest of the round → desk

The claim it keeps: the match day the player goes through is the original's order of screens, and every answer given
on them is the answer the engine receives, sent once, through the bridge, in the order the engine asked:

- **The captain** chosen on S16 is confirmed through `DesktopModel.confirm` before kick-off; the engine plays with
  it (`Match(captain=…)`).
- **The stops** the match holds (`MatchController.stop`) [designed: T167; T180, #574]: half time and the menu before
  extra time go S20 → S15 (S20's Esc: the bench S19, then S15), and *play* answers them with the bench's answer; a
  set-piece taker goes to S16, whose choice is the answer; the shoot-out order to S18's notice, then S16. A
  substitution opportunity goes to S18 (*SUBSTITUTION OPPORTUNITY*), any key to S15 (phase "stop", whose *players*
  opens S19 in *make substitutions now* mode) and *play* answers it. The pause Esc or Enter asks for on S17 opens S19
  in request mode; its Esc answers and returns to the pitch. One bench answer (`s19_bench.BenchAnswer`) is built per
  bench decision and sent once; S09's mark and own tactics from S19 go in it. No stop keeps a default answer.
- **The engine's report** of a bench answer that refuses a pair shows S19 with the reason until a key (`refused`).
- **One bridge for the window's life** (D3): `MatchDay` keeps the owner's `WatchedJobs` (friendlies) and
  `CompetitiveJobs` (qualifiers, T176) open between matches, so every match of the window plays in the owner's one
  engine process; the desk closes them when the window closes (`DeskScreen.closing`).
- **The result** is published once, by the bridge (the friendly's or the competitive publication) at full time; the
  round's remaining results show on S14 after *exit*, then the desk.
- **The watch question** comes only where the original asks it (`asks_watch`, F030); N plays a quick result.
"""
from __future__ import annotations

import json

from PySide6.QtCore import QTimer

# [confirmed: goal2-archaeology F030 at 1bd066ca, 0791:E80D] The kinds the original asks "Do you want to watch this
# match?" for at the second stage whatever the fixture's mark: 8, 200, 201, 203, and 101, 103 when the second
# country's continent has a manager. The managed country's friendlies and qualifiers are never asked (T156-R1 steps
# 42, 264); the first stage asks only for a marked fixture of two computer sides.
WATCH_ASKED = (8, 200, 201, 203)
WATCH_ASKED_MANAGED_CONTINENT = (101, 103)
SETTINGS = "settings.json"   # [designed: T167] the window's own settings in the data folder


def asks_watch(model, fixture):
    """Whether the original asks *Do you want to watch this match?* before this managed fixture. [confirmed: F030]"""
    if fixture.kind in WATCH_ASKED:
        return True
    return (fixture.kind in WATCH_ASKED_MANAGED_CONTINENT
            and model.continent(fixture.side_b) == model.continent(model.state.managed_country))


def for_window(window, model):
    """The window's match day for this career: one per window, made again when another career is opened."""
    day = getattr(window, "match_day", None)
    if day is None or day.model is not model:
        if day is not None:
            day.close()
        day = window.match_day = MatchDay(window, model)
    return day


def play_next_game(window, model):
    """The desk's *play next game*: S14 for the next fixture. Returns the screen, or why it cannot start."""
    return for_window(window, model).begin()


def close_window(window):
    day = getattr(window, "match_day", None)
    if day is not None:
        day.close()


class MatchDay:
    asks_watch = staticmethod(asks_watch)   # a test may stand in a fixture the original asks for

    def __init__(self, window, model):
        self.window, self.model = window, model
        self.bridges = {}
        self.fixture = None
        self.before = None
        self.watch = None
        self.controller = None
        self.pitch = None
        self.bench = None          # the bench's answer to the decision held, built on S19 and S09 [designed: T180]
        self.replay_auto = self._settings().get("automatic_action_replay", False)

    # The window's bridges (D3).
    def bridge(self, competitive):
        key = "competitive" if competitive else "watched"
        bridge = self.bridges.get(key)
        if bridge is None or bridge.closed:
            if competitive:
                from goal2.desktop.competitive import CompetitiveJobs
                bridge = CompetitiveJobs(self.model)
            else:
                from goal2.game.watched_jobs import WatchedJobs
                bridge = WatchedJobs(self.model)
            self.bridges[key] = bridge
        return bridge

    def engine_pid(self):
        engine = getattr(self.model, "_match_engine", None)
        process = engine.engine.process if engine is not None else None
        return process.pid if process is not None else None

    def close(self):
        if self.controller is not None and not self.controller.finished:
            self.controller.cancel()
        for bridge in self.bridges.values():
            bridge.close()
        self.bridges = {}

    # The stored flag of the automatic action replay (Ins on S15).
    def _settings_path(self):
        return self.window.target.root / SETTINGS

    def _settings(self):
        try:
            data = json.loads(self._settings_path().read_text())
            return data if isinstance(data, dict) else {}
        except (OSError, ValueError):
            return {}

    def set_replay_auto(self, on):
        self.replay_auto = bool(on)
        data = self._settings()
        data["automatic_action_replay"] = self.replay_auto
        try:
            path = self._settings_path()
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(data, indent=1))
        except OSError:
            pass   # the flag stays for this window; nothing else depends on the file

    # The flow.
    @property
    def kind_name(self):
        from goal2.desktop.model import kind_word
        return kind_word(self.fixture.kind, self.fixture.stage)

    def begin(self):
        """S14 before your match."""
        from goal2.engine.original_match.match import KINDS
        model = self.model
        campaign = model.state.campaign
        if campaign is None or campaign.world is None:
            return "There is no round to play on this career."
        fixture = campaign.next_fixture
        if fixture is None:
            return "There is no match to play: the stage is complete."
        if fixture.kind not in KINDS:
            return "This fixture's kind is not supported by the engine."
        if self.controller is not None and not self.controller.finished:
            return "A match is already running."
        self.fixture, self.watch, self.controller, self.pitch, self.bench = fixture, None, None, None, None
        try:
            self.before = model.round_before()
        except ValueError as exc:
            return f"The round cannot start: {exc}"
        from goal2.ui.s14_round import RoundScreen
        return self.window.push(RoundScreen(self.window, self.before, self.to_menu))

    def _replace(self, screen):
        """The current match-day screen gives way to `screen` (the desk stays under the match day)."""
        self.window.pop()
        return self.window.push(screen)

    def to_menu(self):
        from goal2.ui.s15_match_menu import MenuScreen
        return self._replace(MenuScreen(self.window, self, "before"))

    def refresh_menu(self, menu):
        """Back on S15 before kick-off from S08 or S10: the elevens again, when yours changed."""
        from goal2.ui.s15_match_menu import MenuScreen

        def again():
            if self.window.current() is menu:
                fresh = MenuScreen(self.window, self, "before")
                if fresh.lineups != menu.lineups:
                    self._replace(fresh)
                else:
                    fresh.deleteLater()
        QTimer.singleShot(0, again)

    def play(self, menu):
        """S15's *play*: before kick-off the captain (S16); at a break the held stop is answered and play goes on."""
        if menu.phase == "before":
            return self.choose_captain()
        self.window.pop()                       # S15, back to S17
        bench, self.bench = self.bench, None
        self.pitch.resume(bench.value() if bench is not None else None)
        return self.pitch

    def choose_captain(self):
        from goal2.ui.s16_choose import ChooseScreen
        from goal2.ui.s17_pitch import suggested_captain
        state = self.model.state
        eleven = list(state.starting_eleven or state.managed_squad[:11])
        computer = suggested_captain(state)
        from goal2.game import eligibility
        available = eligibility.available_words(state.players, eleven)   # [derived: 1771:3216, F030's Enter]
        screen = ChooseScreen(self.window, self.model, "captain", eleven,
                              computer if computer is not None else eleven[0], self.kick_off,
                              available=available or eleven, computer=computer, match=self._match_name())
        return self.window.push(screen)

    def _match_name(self):
        from goal2.ui.pitch import HOME
        names = self.model.goaldat.country_names
        sides = (self.fixture.side_a, self.fixture.side_b)
        return f"{names[sides[HOME]]} v {names[sides[1 - HOME]]}"

    def kick_off(self, captain):
        """The captain chosen (or the computer's): confirmed through the model, then the match on the bridge."""
        from goal2.ui.s17_pitch import MatchController, PitchScreen
        window, model = self.window, self.model
        state = model.state
        eleven = list(state.starting_eleven or state.managed_squad[:11])
        if captain is not None:
            try:
                model.confirm(eleven, captain, state.country_tactics)
            except ValueError as exc:
                return self._back_to_desk(f"The match cannot start: {exc}")
        controller = MatchController(model, self.fixture, self.bridge(self.fixture.kind != 1),
                                     quick=self.watch is False)
        try:
            controller.start()
        except (OSError, ValueError) as exc:
            return self._back_to_desk(f"The match cannot start: {exc}")
        self.controller = controller
        menu = next((screen for screen in reversed(window.stack) if type(screen).__name__ == 'MenuScreen'), None)
        self.recorded_menu = ({str(t): menu.lineups[c] for t, c in enumerate((self.fixture.side_a, self.fixture.side_b))}
                              if menu is not None else {})
        while len(window.stack) > 1:
            window.pop()
        self.pitch = window.push(PitchScreen(window, model, controller, day=self))
        return self.pitch

    def _back_to_desk(self, text):
        window = self.window
        while len(window.stack) > 1:
            window.pop()
        say = getattr(window.current(), "say", None)
        if say is not None:
            say(text)
        return text

    # The stops, from S17.
    def stop(self, pitch, decision):
        from goal2.ui import s18_stop
        context = decision.data.get("context")
        if context in ("half_time", "extra_time", "substitution", "pause"):
            from goal2.ui.s19_bench import BenchAnswer
            self.bench = self.live_bench(pitch, decision)
            self._bench_feedback = None
        if context in ("half_time", "extra_time"):
            return self.show_board(pitch, "half" if context == "half_time" else "extra")
        names = pitch.controller.display.countries
        where = s18_stop.score_line(names, decision.score, decision.minute)
        if context == "substitution":
            # [confirmed: T156-R1 steps 67-68] the notice, then any key: the match menu
            return pitch.show_stop(s18_stop.NOTICE_SUBSTITUTION, s18_stop.SUBSTITUTION_OPPORTUNITY,
                                   f"{s18_stop.substitution_text(self.model, decision)} {where}. Press any key: the "
                                   f"match menu, where players opens the bench.",
                                   lambda key: self._stop_menu())
        if context == "pause":
            return self.open_bench(back=lambda: self._bench_played(pitch))
        if context == "shootout_order":
            # [confirmed: e031-shootout-start.png] the shoot-out's notice before its order
            return pitch.show_stop(s18_stop.NOTICE_SHOOTOUT, s18_stop.SHOOTOUT,
                                   f"{where}. Press any key: choose the order of your takers.",
                                   lambda key: self._shootout_order(pitch, decision))
        return self._taker(pitch, decision)

    def goal(self, pitch, event):
        """[designed: T181; confirmed: T156-R1 175–178] The goal's replay and save questions hold the live pitch."""
        from PySide6.QtCore import Qt
        from goal2.ui.replays import goal_data
        from goal2.ui.s18_stop import ACTION_REPLAY, SAVE_GOAL, YES_NO
        pitch.goal_record = goal_data(pitch, event)
        detail = f"{pitch.goal_record['scorer']} · {event['minute']}′"

        def save_question():
            pitch.show_stop('save-goal', SAVE_GOAL, detail, save_answer, YES_NO)

        def save_answer(key):
            if key == Qt.Key.Key_Y:
                from goal2.ui.replays import name_recording
                name_recording(self.window, pitch, 'goal', pitch.goal_record, finished)
            else:
                finished()

        def finished():
            pitch.goal_record = None
            pitch.controller.dismiss_goal()

        def replay_answer(key):
            if key == Qt.Key.Key_Y:
                pitch.start_replay(pitch.goal_record['frames'], save_question)
            else:
                save_question()
        if self.replay_auto:
            replay_answer(Qt.Key.Key_Y)
        else:
            pitch.show_stop('replay', ACTION_REPLAY, detail, replay_answer, YES_NO)

    def _taker(self, pitch, decision):
        from goal2.ui.s16_choose import ChooseScreen
        data = decision.data
        eleven = list(data.get("eleven") or [])
        screen = ChooseScreen(self.window, self.model, "taker", eleven, data.get("current"),
                              lambda word: self._chosen(pitch, {"taker": word}),
                              available=data.get("available"), role=data.get("role"), match=self._match_name())
        return self.window.push(screen)

    def _shootout_order(self, pitch, decision):
        from goal2.ui.s16_choose import ChooseScreen
        data = decision.data
        eleven = list(data.get("eleven") or [])
        screen = ChooseScreen(self.window, self.model, "order", eleven, eleven[0] if eleven else None,
                              lambda order: self._chosen(pitch, {"shootout_order": list(order)}),
                              available=data.get("available"), takers=data.get("takers") or 0,
                              match=self._match_name())
        return self.window.push(screen)

    def _stop_menu(self):
        """S18's key at a substitution opportunity: the match menu (S15, phase "stop")."""
        from goal2.ui.s15_match_menu import MenuScreen
        score = self.bench.score if self.bench is not None else (0, 0)
        return self.window.push(MenuScreen(self.window, self, "stop", score))

    def _names(self):
        return self.controller.display.countries if self.controller is not None else ("", "")

    def open_bench(self, back=None):
        """S19 for the bench decision held: from S15's *players* or S20's Esc (Esc back to S15), or at a pause
        (Esc answers and returns to the pitch)."""
        from goal2.ui.s19_bench import BenchScreen
        if self.bench is None:
            return None
        screen = BenchScreen(self.window, self.model, self.bench, names=self._names(), back=back, apply=self.edit_bench)
        screen.feedback_report = getattr(self, "_bench_feedback", None)
        return self.window.push(screen)

    def live_bench(self, pitch, decision):
        """[derived: original injury/player_tactics events] Display live accepted data without mutating a career."""
        from goal2.ui.s19_bench import BenchAnswer
        answer = BenchAnswer(self.model, decision, pitch.controller.opponents(), friendly=self.fixture.kind == 1)
        for event in self.controller.events:
            data = event["data"]
            if event["kind"] == "injury" and data.get("team") == self.controller.display.managed:
                if data.get("player") in answer.words(): answer.injured.add(data["player"])
            elif event["kind"] == "player_tactics":
                answer.live_own[data["player"]] = data["own_set"]
                answer.live_marking[data["player"]] = data["marking"]
        return answer

    def edit_bench(self, screen):
        """[designed: T188b] A completed pair is one operation, without continuing Play."""
        self._editing_screen = screen
        try:
            self.controller.edit_bench(screen.answer.value())
        except Exception as exc:
            self._editing_screen = None
            screen.pending = False
            screen.message = f"Substitution not submitted: {exc}"
            screen.refresh()

    def edited(self, pitch, decision, report):
        from goal2.ui.s19_bench import BenchAnswer
        previous = self.bench
        answer = self.live_bench(pitch, decision)
        if previous is not None:
            answer.injured.update(previous.injured)
            answer.live_own = {**previous.live_own, **answer.live_own}
            answer.live_marking = {**previous.live_marking, **answer.live_marking}
        self.bench = answer
        self._bench_feedback = report
        screen = getattr(self, "_editing_screen", None)
        self._editing_screen = None
        if screen is not None:
            screen.applied(answer, report)

    def _bench_played(self, pitch):
        """S19's Esc at a pause: the bench's answer is sent once and the match plays on."""
        self.window.pop()
        bench, self.bench = self.bench, None
        pitch.resume(bench.value() if bench is not None else None)
        return pitch

    def refused(self, pitch, report):
        """The engine refused a pair of the bench's answer: S19 with its reason until a key, then the match."""
        from goal2.ui.s19_bench import BenchAnswer, BenchScreen
        from types import SimpleNamespace
        decision = next((e for e in reversed(pitch.controller.shown()) if e["kind"] == "decision"
                         and e["data"].get("context") == report["context"]), None)
        decision = (SimpleNamespace(data=decision["data"], minute=decision["minute"], score=decision["score"])
                    if decision is not None else SimpleNamespace(data={"context": report["context"]}, minute=0,
                                                                  score=[0, 0]))
        answer = BenchAnswer(self.model, decision, friendly=self.fixture.kind == 1)
        answer.chosen = [list(p) for p in report["asked"]]

        def back():
            self.window.pop()
            pitch.dismiss()
        return self.window.push(BenchScreen(self.window, self.model, answer, names=self._names(), back=back,
                                            report=report))

    def _chosen(self, pitch, value):
        self.window.pop()                       # S16, back to S17
        pitch.resume(value)

    def show_board(self, pitch, phase):
        from goal2.ui.s20_board import BoardScreen, board
        controller = pitch.controller
        data = board(controller.shown(), phase, controller.quick)
        names = controller.display.countries
        bench = (lambda: self._board_bench(phase, data)) if phase != "full" and self.bench is not None else None
        screen = BoardScreen(self.window, self.model, names, self.kind_name.upper(), phase, data,
                             lambda note: self._after_board(phase, data, note), pitch.kits, bench=bench,
                             save_summary=phase == 'full' and not controller.quick)
        return self.window.push(screen)

    def _after_board(self, phase, data, note):
        from goal2.ui.s15_match_menu import MenuScreen
        menu = self._replace(MenuScreen(self.window, self, phase, data["score"]))
        menu.say(note)
        return menu

    def _board_bench(self, phase, data):
        """S20's Esc: the bench, over the menu it returns to. [confirmed: T156-R1 step 119, "Esc,◄┘-bench"]"""
        self._after_board(phase, data, None)
        return self.open_bench()

    def show_stats(self, menu):
        """S15's *match stats*: S20 for the match so far (nothing before kick-off)."""
        if self.controller is None:
            menu.say("No statistics before kick-off.")
            return None
        from goal2.ui.s20_board import BoardScreen, board
        controller = self.controller
        phase = menu.phase
        data = board(controller.shown(), phase, controller.quick)
        screen = BoardScreen(self.window, self.model, controller.display.countries, self.kind_name.upper(), phase,
                             data, lambda note: self.window.pop(), self.pitch.kits)
        return self.window.push(screen)

    def full_time(self, pitch):
        """S17's full time: the board, then the menu with *exit*. The bench's answer, and with it S09's marks, is
        gone: the original clears the marks after each match [confirmed: F010]."""
        self.bench = None
        return self.show_board(pitch, "full")

    def exit(self):
        """S15's *exit* after the final whistle: the round's remaining results on S14, then the desk."""
        from goal2.ui.s14_round import RoundScreen
        window = self.window
        while len(window.stack) > 1:
            window.pop()
        after = self.model.round_after(self.fixture.fixture_id)
        result = self.model.result_text().split("\n", 1)[0]
        return window.push(RoundScreen(window, self.before, lambda: self._home(f"Full time: {result}."), after=after))

    def _home(self, text):
        return self._back_to_desk(text)
