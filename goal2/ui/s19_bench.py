"""S19: authoritative squad edits while a match is legally stopped.

[designed: owner playtest2026-11-05, #592/#599; T188b] No substitution queue during play. At half-time or an
original substitution opportunity, two player selections submit one edit-only answer. Until its reply input is
held; the original's new decision alone updates the eleven, bench and counter. Play later continues. Refusals
stay at the usable stopped squad with one correctly directed on/off message. Ordinary in-play pauses permit
supported tactical edits and explain that substitutions require a legal stoppage.

[confirmed: original T156-R1 steps124–137, t156-132-substitution-made.png] The half-time squad changes before Play.
[derived: accepted original injury/player_tactics events] Known match injuries and accepted personal settings
survive a refresh; pending UI values never masquerade as an accepted swap or get resubmitted on Play.
[designed: owner BM-7, #73] A friendly displays unlimited substitutions (the bridge's original byte budget255).
[confirmed: F027 E544; E015-r0013 state790] A zero budget displays no more substitutes.
The engine kit's legacy queue API remains available to reference clients; this player screen does not create it.
"""
from __future__ import annotations

import copy

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import QHBoxLayout, QVBoxLayout

from goal2.ui import theme
from goal2.ui.screen import Screen, label, para, set_para
from goal2.ui.squad_card import PlayerCard, Strip, box, colour, full_name, last_on_the_bar

NO_MORE = "no more substitutes"                 # [confirmed: F027 E544; E015-r0013 state 790]
UNLIMITED = "substitutions: unlimited (friendly)"   # [designed: owner BM-7, #73]
MAKE_NOW = "MAKE SUBSTITUTIONS NOW"             # [confirmed: t156-124-halftime-bench.png, "make substitutions now"]
# [confirmed: original t156-124-halftime-bench.png; owner #608] VGA bright green.
MAKE_NOW_GREEN = "#55ff55"
# [designed: #608] Half-second paint phases; the original cadence has not been measured.
CUE_PHASE_MS = 500
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
        self.chosen = []  # [designed: owner #599] earlier requests are not new selections
        self.first = None          # the first Enter of a pair
        self.positions = {}        # word: position code, from R and C
        self.marking = {}          # word: opponent word, or 0 for none, from S09's mark line
        self.own = {}              # word: his own-tactics byte +0xF as S09 left it
        self.live_own = {}         # confirmed player_tactics events, not pending edits
        self.live_marking = {}
        self.opponents = list(opponents)
        self.friendly = friendly

    # What it holds.
    @property
    def takes_substitutions(self):
        return self.context in ("half_time", "substitution") and self.now

    def words(self):
        return self.eleven + self.bench

    def position(self, word):
        return self.positions.get(word, self.at_kick.get(word, self.model.state.players[word][6]))

    def record(self, word):
        """His record as the bench shows it: the position and own tactics changed here."""
        record = bytearray(self.model.state.players[word])
        record[6] = self.position(word)
        if word in self.own or word in self.live_own:
            record[15] = self.own.get(word, self.live_own.get(word))
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
        if word in self.marking or word in self.live_marking:
            value["mark"] = self.mark_text(word)
        return value

    # The pairs.
    def pair_of(self, word):
        return next((p for p in self.chosen if word in p), None)

    def enter(self, word):
        """Enter on a player: mark him; Enter on one of the other group makes the pair (either order); Enter on him
        again drops the mark; Enter on a player of a chosen pair with nobody marked drops that pair. Returns what
        happened, for the screen's line."""
        if not self.takes_substitutions:
            return "unavailable"
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
        bit = self.own.get(word, self.live_own.get(word, self.model.state.players[word][15]))
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
        mark = self.marking.get(word, self.live_marking.get(word))
        if mark is None:
            return "—"
        return "nobody" if mark == 0 else full_name(self.model, mark)

    # The answer.
    def own_tactics(self):
        out = {}
        for word, byte in self.own.items():
            before = self.live_own.get(word, self.model.state.players[word][15])
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
        if self.context not in ("half_time", "substitution", "pause"):
            return []
        pairs = [list(p) for p in self.chosen] if self.takes_substitutions else []
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

    def __init__(self, window, model, answer, *, mode=None, names=("", ""), back=None, report=None, apply=None):
        self.mode = mode or ("refused" if report is not None else "view" if answer.context not in ("half_time", "substitution", "pause")
                             else "now" if answer.now else "request")
        self.escape_text = {"now": "match menu", "request": "back to the match", "view": "match menu",
                            "refused": "back to the match"}[self.mode]
        self.title = f"{names[0]} v {names[1]} · players"
        super().__init__(window)
        self.model, self.answer, self.names, self.back, self.report = model, answer, names, back, report
        self.row = 0
        self.message = ""
        self.apply = apply
        self.pending = False
        self.feedback_report = None
        self.cue_timer = QTimer(self)
        self.cue_timer.setInterval(CUE_PHASE_MS)
        self.cue_timer.timeout.connect(self._blink_cue)
        self._cue_lit = True
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
        # [designed: owner #599/#598] Use the full-width status row so large feedback
        # and all twenty players fit together, including a three-line original refusal.
        self.body_layout.setSpacing(8)
        head, inner = box(margins=(16,12,16,12))
        row=QHBoxLayout()
        row.setSpacing(22)
        self.mode_label=label("","h1")
        colour(self.mode_label,theme.VALUE)
        row.addWidget(self.mode_label)
        self.counter=label("","benchCounter")
        row.addWidget(self.counter)
        self.context=label("","benchMetadata")
        self.context.setWordWrap(True)
        row.addWidget(self.context,1)
        inner.addLayout(row)
        self.body_layout.addWidget(head)
        main=QHBoxLayout()
        main.setSpacing(18)
        column=QVBoxLayout()
        column.setSpacing(6)
        self.card=PlayerCard()
        self.card.layout().setContentsMargins(16,5,16,5)
        # [designed: T193] Room for all labelled facts plus long feedback at native fractional font metrics.
        self.card.layout().setSpacing(1)
        for metadata in (self.card.facts,self.card.positions):
            metadata.setWordWrap(True)
            metadata.setObjectName("benchMetadata")
        column.addWidget(self.card,1)
        feedback, feedback_layout=box("SUBSTITUTION",margins=(16,8,16,8))
        feedback.setObjectName("benchFeedback")
        feedback_layout.setSpacing(4)
        self.note=para("","benchFeedbackText")
        self.note.setStyleSheet(f"color: {theme.VALUE};")
        feedback_layout.addWidget(self.note)
        column.addWidget(feedback)
        main.addLayout(column,1)
        self.strip=Strip()
        self.strip.setFixedWidth(466)
        self.strip.layout().setContentsMargins(16,10,16,10)
        for player in self.strip.rows:
            player.layout().setContentsMargins(8,0,8,0)
        self.strip.chosen.connect(self.click_row)
        main.addWidget(self.strip)
        self.body_layout.addLayout(main,1)

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
            self.mode_label.setText("SUBSTITUTIONS ONLY AT STOPPAGES")
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
        self._sync_cue()

    def _sync_cue(self):
        """Blink only when this visible squad can make another immediate swap."""
        available = (self.mode == "now" and self.answer.takes_substitutions
                     and self.answer.left > 0 and not self.pending)
        if available and self.isVisible():
            if not self.cue_timer.isActive():
                self._cue_lit = True
                self.cue_timer.start()
        else:
            self.cue_timer.stop()
            self._cue_lit = True
        colour(self.mode_label, MAKE_NOW_GREEN if available and self._cue_lit
               else "transparent" if available else theme.VALUE)

    def _blink_cue(self):
        self._cue_lit = not self._cue_lit
        self._sync_cue()

    def showEvent(self, event):
        super().showEvent(event)
        self._sync_cue()

    def hideEvent(self, event):
        self.cue_timer.stop()
        super().hideEvent(event)

    def closeEvent(self, event):
        self.cue_timer.stop()
        super().closeEvent(event)

    def line(self):
        """The line under the mode: the refusal's reason, the pairs chosen, or what the screen waits for."""
        answer = self.answer
        if self.pending:
            return "Applying substitution. Waiting for the game to confirm the changed squad."
        if self.mode == "refused":
            return "Not made: " + "; ".join(f"{full_name(self.model, b)} on for {full_name(self.model, a)} off: "
                                            f"{('the change was not confirmed' if why == 'not made by the original' else why)}"
                                            for a, b, why in self.report["refused"]) + "."
        if self.mode == "view":
            return "The route takes no substitution before extra time: play on from the match menu."
        parts = []
        if self.feedback_report:
            report = self.feedback_report
            if report["made"]:
                parts.append("Made: " + "; ".join(f"{full_name(self.model,b)} on for {full_name(self.model,a)} off"
                                               for a,b in report["made"]) + ".")
            if report["refused"]:
                parts.append("Not made: " + "; ".join(f"{full_name(self.model,b)} on for {full_name(self.model,a)} off: "
                    + ("change not confirmed" if why == "not made by the original" else why)
                    for a,b,why in report["refused"]) + ".")
        if self.mode == "request":
            parts.append("Substitutions require half-time or an offered stoppage. Tactical changes are available here.")
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
            parts.append("Select both players to make the substitution here, before Play." if self.mode == "now"
                         else "Substitutions require a legal stoppage.")
        return " ".join(parts)

    def enter_hint_text(self):
        if getattr(self, "answer", None) is None:
            return ""             # Screen.__init__ draws the bar before the bench is set
        if self.pending:
            return "Applying substitution..."
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
            return "Substitutions only at a stoppage"
        # [confirmed: squad-substitution-take-off.png, -put-on.png] the original's prompt
        return "Take off this player" if word in answer.eleven else "Put on this player"

    # Keys.
    def handle_key(self, key):
        if self.pending and key != Qt.Key.Key_F1:
            return True
        if self.mode == "refused" and key != Qt.Key.Key_F1:
            self.escape()
            return True
        return super().handle_key(key)

    def move(self, step):
        if self.pending: return
        self.row = max(0, min(len(self.answer.words()) - 1, self.row + step))
        self.message = ""
        self.refresh()

    def click_row(self, index):
        if self.pending: return
        if index == self.row:
            return self.press()
        self.row = index
        self.refresh()

    def press(self):
        """Enter: take off or put on (a pair once both are chosen), or drop a chosen pair."""
        if self.pending: return
        word = self.current()
        if word is None or self.mode == "view":
            return
        self.message = ""
        if not self.answer.takes_substitutions:
            self.message = "Substitutions are available only at a legal stoppage."
            self.refresh()
            return
        action = self.answer.enter(word)
        if action == "paired" and self.apply is not None:
            self.pending = True
            self.refresh()
            self.apply(self)
        else:
            self.refresh()

    def reposition(self):
        if self.pending: return
        word = self.current()
        if word is not None and self.mode != "view":
            self.answer.reposition(word)
            self.refresh()

    def club_position(self):
        if self.pending: return
        word = self.current()
        if word is not None and self.mode != "view":
            self.answer.club_position(word)
            self.refresh()

    def his_tactics(self):
        if self.pending: return
        from goal2.ui.s09_player_tactics import PlayerTacticsScreen
        word = self.current()
        if word is not None:
            self.window_.push(PlayerTacticsScreen(self.window_, self.model, word, bench=self.answer))

    def escape(self):
        """Esc: back to S15 at a break; back to the pitch during play (the answer goes with it); after a refusal,
        back to the match."""
        if self.pending: return
        if self.back is not None:
            return self.back()
        return self.window_.pop()

    def applied(self, answer, report):
        """[designed: T188b] Only the engine's new stopped decision changes the list/counter."""
        self.answer = answer
        self.pending = False
        self.feedback_report = report
        self.message = ""
        self.refresh()

    def shown(self):
        """Back from S09: the card again (his tactics or mark may have changed)."""
        self.refresh()
