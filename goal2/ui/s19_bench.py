"""S19 Bench: substitutions during a match and at its breaks.

[designed: owner, 2026-11-03, #526; docs/design/ui-2026-11 S19 and its mockup s19-bench.png; T180, #574]
[confirmed: T156-R1 steps 74-81, 124-133, 279-301; E031 C41-C41k; E015-r0007 states 76, 82, 176;
images squad-substitution-take-off.png, -put-on.png, -illegal.png, t156-074-bench-requested.png,
t156-080-bench-request-cancelled.png, t156-124-halftime-bench.png, t156-132-substitution-made.png]

The claim it keeps: every substitution the player makes here is the pair the engine receives, and every refusal the
player sees is the engine's. It keeps today's bench's rules (goal2/desktop/bench_page.py `Bench`, T102):

- **The pairs** are made with two Enters, in either order (a starter then a bench player, or the other way round,
  E031 C41e-C41i), and passed to the engine as they are: the view never judges whether one is legal. Enter on a
  player of a chosen pair, with nobody marked, drops that pair.
- **The answer** is sent once, through the bridge (`WatchedJobs.answer`), in the order the engine asked: at a break
  when S15's *play* is pressed, at a pause when Esc returns to the pitch. It carries the pairs and the bench's other
  changes (`BenchAnswer.value`): R and C positions, and S09's own tactics and mark (watched_jobs.CHANGES).
- **The counter** is the decision's `substitutions_left`, the engine's; with none left it reads "no more
  substitutes" [confirmed: F027 E544; E015-r0013 state 790]. In a friendly it reads "unlimited": BM-7's budget is
  255 in the engine (watched_match.FRIENDLY_SUBSTITUTIONS), a number the player is not meant to count down
  [designed: owner BM-7, #73].
- **The engine's report** follows the answer once the original plays on: a refused pair shows here with the
  engine's reason (`mode` "refused") and waits for a key; made and requested pairs are noted on the pitch.
- **#316**: at the stoppage after a pause the requested pairs are offered again, and Esc says that they are still
  made (the engine's default answer there is what was asked for).

The modes, as the original names them: *make substitutions now* (`mode` "now": half time, a substitution
opportunity) and *substitution requested* (`mode` "request": the pause Esc or Enter asks for on S17, where Enter
requests or cancels a substitution, made at the next stoppage). Before extra time (`mode` "view") the route takes no
substitution (watched_match.PROMPT_CONTEXTS: the menu before extra time is answered with no change): the bench shows
the eleven and the counter and says so. [derived: goal2/game/watched_match.py `_drive_match`]
"""
from __future__ import annotations

import copy

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QHBoxLayout, QVBoxLayout

from goal2.ui import theme
from goal2.ui.screen import Screen, label, para, set_para
from goal2.ui.squad_card import PlayerCard, Strip, box, colour, full_name, last_on_the_bar

NO_MORE = "no more substitutes"                 # [confirmed: F027 E544; E015-r0013 state 790]
UNLIMITED = "substitutions: unlimited (friendly)"   # [designed: owner BM-7, #73]
MAKE_NOW = "MAKE SUBSTITUTIONS NOW"             # [confirmed: t156-124-halftime-bench.png, "make substitutions now"]
REQUESTED = "SUBSTITUTION REQUESTED"            # [confirmed: t156-074-bench-requested.png]
REQUEST = "REQUEST A SUBSTITUTION"              # [designed: T180] the request mode before a pair is chosen
REFUSED = "SUBSTITUTION NOT MADE"               # [designed: T180] the engine's refusal (squad-substitution-illegal)
VIEW = "NO SUBSTITUTIONS BEFORE EXTRA TIME"     # [derived: watched_match.PROMPT_CONTEXTS; designed: T180]
# [confirmed: the kit's Match._on_notice; designed: #316] Esc at the stoppage after a pause cannot cancel the request.
ESC_KEEPS_REQUESTED = "Esc: the requested substitutions are still made"
OFF, ON, MARKED = " v", " ^", " *"              # [designed: T102] the strip's marks: taken off, put on, first Enter
TIMES = {"half_time": "half time", "substitution": "substitution opportunity", "pause": "during play",
         "extra_time": "before extra time"}


class BenchAnswer:
    """The answer to one bench decision, as S19 and S09 build it: the pairs, positions, marks and own tactics.
    `value()` is what the match day sends, once: the pairs alone, or {'substitutions': pairs, 'positions',
    'marking', 'own_tactics'} when anything else changed (watched_match._drive_match takes either)."""

    def __init__(self, model, decision, opponents=(), friendly=False):
        data = decision.data
        self.model = model
        self.context = data.get("context")
        self.minute = decision.minute
        self.score = list(decision.score)
        self.eleven = list(data.get("eleven") or [])
        self.bench = list(data.get("bench") or [])
        self.left = data.get("substitutions_left", 0)
        self.now = bool(data.get("substitutions_now", self.context != "pause"))
        self.injured = set(data.get("injured") or [])
        self.at_kick = {int(w): int(code) for w, code in data.get("positions") or []}
        self.requested = [list(p) for p in data.get("requested") or []] if self.context == "substitution" else []
        # [confirmed: the kit's Match._on_menu] the original refused the eleven of the last answer (two keepers, …):
        # the decision is offered again with its message, and the view says it as it is
        self.refused = data.get("refused")
        self.chosen = [list(p) for p in self.requested]
        self.first = None          # the first Enter of a pair
        self.positions = {}        # word: position code, from R and C
        self.marking = {}          # word: opponent word, or 0 for none, from S09's mark line
        self.own = {}              # word: his own-tactics byte +0xF as S09 left it
        self.opponents = list(opponents)
        self.friendly = friendly

    # What it holds.
    @property
    def takes_substitutions(self):
        return self.context in ("half_time", "substitution", "pause")

    def words(self):
        return self.eleven + self.bench

    def position(self, word):
        return self.positions.get(word, self.at_kick.get(word, self.model.state.players[word][6]))

    def record(self, word):
        """His record as the bench shows it: the position and own tactics changed here."""
        record = bytearray(self.model.state.players[word])
        record[6] = self.position(word)
        if word in self.own:
            record[15] = self.own[word]
        return bytes(record)

    def state(self, word):
        """The model's state with his record as the bench shows it (a shallow copy; nothing is written back)."""
        state = copy.copy(self.model.state)
        players = list(state.players)
        players[word] = self.record(word)
        state.players = players
        return state

    def card(self, word):
        from goal2.game.player_card import card
        state = self.state(word)
        value = card(state, word, self.model.goaldat)
        if word in self.injured:
            value["health"] = "INJURED — live match"
            value["readiness"] = "INJURED — live match"
        if word in self.marking:
            value["mark"] = self.mark_text(word)
        return value

    # The pairs.
    def pair_of(self, word):
        return next((p for p in self.chosen if word in p), None)

    def enter(self, word):
        """Enter on a player: mark him; Enter on one of the other group makes the pair (either order); Enter on him
        again drops the mark; Enter on a player of a chosen pair with nobody marked drops that pair. Returns what
        happened, for the screen's line."""
        if self.first is None:
            pair = self.pair_of(word)
            if pair is not None:
                self.chosen.remove(pair)
                return "dropped"
            self.first = word
            return "marked"
        if self.first == word:
            self.first = None
            return "unmarked"
        if (self.first in self.eleven) == (word in self.eleven):
            self.first = word
            return "marked"
        off, on = (self.first, word) if self.first in self.eleven else (word, self.first)
        self.chosen = [p for p in self.chosen if p[0] != off and p[1] != on] + [[off, on]]
        self.first = None
        return "paired"

    # R, C and S09.
    def reposition(self, word):
        """R: the next of the fourteen positions (as S08's `set_position`), sent with the answer."""
        self.positions[word] = (self.position(word) + 1) % 14

    def club_position(self, word):
        """C: his club position +7 (as S08's `club_position`), sent with the answer."""
        self.positions[word] = self.model.state.players[word][7]

    def own_tactic(self, word, element):
        """Enter on S09's line `element` 1..4: the original's cycle (DesktopModel.own_tactic, F010 `1771:4B61`):
        the team's -> his own, clear -> his own, set -> the team's."""
        team = self.model.state.country_tactics
        bit = self.own.get(word, self.model.state.players[word][15])
        own, value = 1 << (element + 3), 1 << (element - 1)
        if not bit & own:
            bit = (bit | own) & ~value
        elif not bit & value:
            bit |= value
        else:
            bit = (bit & ~own & ~value) | (team & value)
        self.own[word] = bit & 255

    def mark_choices(self):
        """S09's mark line: unchanged, nobody, or one of their outfield players (slots 2..11, as 1771:49B8 offers
        them; the keeper, slot 1, is not). [confirmed: goal2-archaeology docs/engine-study/tactics.md, 49B8]"""
        return [None, 0] + self.opponents[1:11]

    def step_mark(self, word):
        choices = self.mark_choices()
        now = self.marking.get(word)
        following = choices[(choices.index(now) + 1) % len(choices)] if now in choices else choices[1]
        if following is None:
            self.marking.pop(word, None)
        else:
            self.marking[word] = following

    def mark_text(self, word):
        mark = self.marking.get(word)
        if mark is None:
            return "—"
        return "nobody" if mark == 0 else full_name(self.model, mark)

    # The answer.
    def own_tactics(self):
        out = {}
        for word, byte in self.own.items():
            before = self.model.state.players[word][15]
            changes = {}
            for element in (1, 2, 3, 4):
                own, value = 1 << (element + 3), 1 << (element - 1)
                old = bool(before & value) if before & own else None
                new = bool(byte & value) if byte & own else None
                if old != new:
                    changes[element] = new
            if changes:
                out[word] = changes
        return out

    def value(self):
        """What the engine receives: the pairs, with the other changes when there are any. Before extra time,
        nothing (play on)."""
        if not self.takes_substitutions:
            return []
        pairs = [list(p) for p in self.chosen]
        positions = {w: c for w, c in self.positions.items() if c != self.at_kick.get(w)}
        marking = {w: m for w, m in self.marking.items() if w in self.eleven}
        own = self.own_tactics()
        if not (positions or marking or own):
            return pairs
        return {"substitutions": pairs, "positions": positions, "marking": marking, "own_tactics": own}

    def counter(self, left=None):
        left = self.left if left is None else left
        if self.friendly and left != 0:
            return UNLIMITED
        return NO_MORE if left == 0 else f"substitutions left {left}"


class BenchScreen(Screen):
    """S19. `mode`: "now", "request", "view", or "refused" (the engine's report, shown until a key)."""

    def __init__(self, window, model, answer, *, mode=None, names=("", ""), back=None, report=None):
        self.mode = mode or ("refused" if report is not None else "view" if not answer.takes_substitutions
                             else "now" if answer.now else "request")
        self.escape_text = {"now": "match menu", "request": "back to the match", "view": "match menu",
                            "refused": "back to the match"}[self.mode]
        self.title = f"{names[0]} v {names[1]} · players"
        super().__init__(window)
        self.model, self.answer, self.names, self.back, self.report = model, answer, names, back, report
        self.row = 0
        self.message = ""
        self._build()
        if self.mode != "refused":
            self.bind((Qt.Key.Key_Up,), "", lambda: self.move(-1), captions=("",), shown=False)
            self.bind((Qt.Key.Key_Down,), "", lambda: self.move(1), captions=("",), shown=False)
            self.bind((), "player", None, captions=("↑", "↓"))
            self.bind((Qt.Key.Key_R,), "next position", self.reposition)
            self.bind((Qt.Key.Key_C,), "club position", self.club_position)
            self.bind((Qt.Key.Key_T,), "his tactics", self.his_tactics)
            self.set_enter("", self.press)
        else:
            self.set_enter("Back to the match", lambda: self.escape())
        last_on_the_bar(self, self.escape_text)
        if self.mode == "refused":
            self.set_enter("Back to the match", self.escape)
        elif self.answer.requested:
            self.message = ESC_KEEPS_REQUESTED
        self.refresh()

    def _build(self):
        main = QHBoxLayout()
        main.setSpacing(18)
        column = QVBoxLayout()
        column.setSpacing(14)
        head, inner = box(margins=(16, 12, 16, 12))
        row = QHBoxLayout()
        row.setSpacing(22)
        self.mode_label = label("", "h1")
        colour(self.mode_label, theme.VALUE)
        row.addWidget(self.mode_label)
        self.counter = label("", "value")
        self.counter.setStyleSheet(f"border: 1px solid {theme.FRAME}; padding: 6px 14px;")
        row.addWidget(self.counter)
        self.context = label("", "sub")
        inner.addWidget(self.context)
        row.addStretch(1)
        inner.addLayout(row)
        self.note = para("", "sub")
        colour(self.note, theme.VALUE)
        column.addWidget(head)
        self.card = PlayerCard()
        column.addWidget(self.card, 1)
        feedback, feedback_layout = box("SUBSTITUTION")
        feedback.setObjectName("benchFeedback")
        self.note.setObjectName("benchFeedbackText")
        self.note.setStyleSheet(f"color: {theme.VALUE}; font-size: {theme.TEXT}px;")
        feedback_layout.addWidget(self.note)
        column.addWidget(feedback)
        main.addLayout(column, 1)
        self.strip = Strip()
        self.strip.chosen.connect(self.click_row)
        main.addWidget(self.strip)
        self.body_layout.addLayout(main, 1)

    # What is shown.
    def current(self):
        words = self.answer.words()
        self.row = max(0, min(self.row, len(words) - 1))
        return words[self.row] if words else None

    def refresh(self):
        from goal2.game import roles
        answer = self.answer
        if self.mode == "refused":
            self.mode_label.setText(REFUSED)
        elif self.mode == "view":
            self.mode_label.setText(VIEW)
        elif self.mode == "now":
            self.mode_label.setText(MAKE_NOW)
        else:
            self.mode_label.setText(REQUESTED if answer.chosen else REQUEST)
        left = self.report["substitutions_left"] if self.report is not None else None
        self.counter.setText(answer.counter(left))
        names = self.names
        from goal2.ui.pitch import HOME
        self.context.setText(f"{TIMES.get(answer.context, answer.context)} · {names[HOME]} {answer.score[HOME]}-"
                             f"{answer.score[1 - HOME]} {names[1 - HOME]} · {answer.minute}′"
                             )
        table = roles.tables(self.model.state)
        off = {p[0] for p in answer.chosen}
        on = {p[1] for p in answer.chosen}
        rows = []
        for word in answer.words():
            code, line = roles.role(self.model.state, answer.position(word), cache=table)
            mark = OFF if word in off else ON if word in on else MARKED if word == answer.first else ""
            injury = " · INJURED" if word in answer.injured else ""
            rows.append((code, line, full_name(self.model, word) + mark + injury))
        heading = self.model.goaldat.country_names[self.model.state.managed_country]
        self.strip.show_rows(heading, rows, self.row, len(answer.eleven) == 11,
                             injured={i for i,w in enumerate(answer.words()) if w in answer.injured})
        word = self.current()
        if word is not None:
            self.card.set_card(answer.card(word))
        set_para(self.note, self.line())
        self._refresh_hint()

    def line(self):
        """The line under the mode: the refusal's reason, the pairs chosen, or what the screen waits for."""
        answer = self.answer
        if self.mode == "refused":
            return "Not made: " + "; ".join(f"{full_name(self.model, b)} on for {full_name(self.model, a)} off: "
                                            f"{('the change was not confirmed' if why == 'not made by the original' else why)}"
                                            for a, b, why in self.report["refused"]) + "."
        if self.mode == "view":
            return "The route takes no substitution before extra time: play on from the match menu."
        parts = []
        if answer.refused:
            parts.append(f"The original refused the eleven: {answer.refused}.")
        if answer.chosen:
            parts.append(("Requested: " if self.mode == "request" else "Chosen: ")
                         + ", ".join(f"{full_name(self.model, a)} off, {full_name(self.model, b)} on"
                                     for a, b in answer.chosen))
        if answer.first is not None:
            other = "a player of the bench" if answer.first in answer.eleven else "a player of the eleven"
            parts.append(f"{full_name(self.model, answer.first)} is marked: Enter on {other} makes the pair.")
        if self.message:
            parts.append(self.message)
        if not parts:
            parts.append("Made when the match plays on." if self.mode == "now"
                         else "Made at the next stoppage, as the original does.")
        return " ".join(parts)

    def enter_hint_text(self):
        if getattr(self, "answer", None) is None:
            return ""             # Screen.__init__ draws the bar before the bench is set
        if self.mode == "refused":
            return "Back to the match"
        if self.mode == "view":
            return ""
        word = self.current()
        answer = self.answer
        if word is None:
            return ""
        if answer.first is None and answer.pair_of(word) is not None:
            return "Cancel substitution request" if self.mode == "request" else "Cancel this substitution"
        if answer.first == word:
            return "Unmark this player"
        if self.mode == "request":
            return "Request substitution"
        # [confirmed: squad-substitution-take-off.png, -put-on.png] the original's prompt
        return "Take off this player" if word in answer.eleven else "Put on this player"

    # Keys.
    def handle_key(self, key):
        if self.mode == "refused" and key != Qt.Key.Key_F1:
            self.escape()
            return True
        return super().handle_key(key)

    def move(self, step):
        self.row = max(0, min(len(self.answer.words()) - 1, self.row + step))
        self.message = ""
        self.refresh()

    def click_row(self, index):
        if index == self.row:
            return self.press()
        self.row = index
        self.refresh()

    def press(self):
        """Enter: take off or put on (a pair once both are chosen), or drop a chosen pair."""
        word = self.current()
        if word is None or self.mode == "view":
            return
        self.message = ""
        self.answer.enter(word)
        self.refresh()

    def reposition(self):
        word = self.current()
        if word is not None and self.mode != "view":
            self.answer.reposition(word)
            self.refresh()

    def club_position(self):
        word = self.current()
        if word is not None and self.mode != "view":
            self.answer.club_position(word)
            self.refresh()

    def his_tactics(self):
        from goal2.ui.s09_player_tactics import PlayerTacticsScreen
        word = self.current()
        if word is not None:
            self.window_.push(PlayerTacticsScreen(self.window_, self.model, word, bench=self.answer))

    def escape(self):
        """Esc: back to S15 at a break; back to the pitch during play (the answer goes with it); after a refusal,
        back to the match."""
        if self.back is not None:
            return self.back()
        return self.window_.pop()

    def shown(self):
        """Back from S09: the card again (his tactics or mark may have changed)."""
        self.refresh()
