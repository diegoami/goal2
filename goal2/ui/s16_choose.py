"""S16 Choose a player: the captain before kick-off, a set-piece taker during play, the penalty order before a
shoot-out.

[designed: owner, 2026-11-03, #526, #523; docs/design/ui-2026-11 S16 and its mockup s16-captain.html; T167, #541]
[confirmed: T156-R1 steps 43-47, 56-58, 265-266, t156-043-captain.png, t156-046-goal-kick-taker.png,
t156-056-corner-taker.png; E031 C38-C38b]

- **The headline** says what the match waits for ("Choose your captain to kick off"), as the design adds it
  [designed: #523, the owner did not know that kick-off waits for a captain].
- **The prompt** [confirmed: goal2-archaeology F030 at 1bd066ca, `0791:CC7B`]: the eleven, the highlight starting
  on the current pick; **↑↓** move it, **Enter** chooses the highlighted player, **C** the computer's pick. With no
  key the current pick stands after the original's wait: 1000 polls of 10 nominal ms, 10.0 s (`WAIT_MS`); ↑↓
  restart the wait, as any key but Enter, Esc and C does. The role's title is the original's (`DS:0A29`: CAPTAIN,
  CORNER, PENALTY, FREE KICK, GOAL KICK).
- **The captain**: the current pick is the computer's (T143's rule, `s17_pitch.suggested_captain`, the original's
  `1F3C`); the chosen captain is confirmed through `DesktopModel.confirm` before kick-off, and the engine plays with
  it (`Match(captain=…)`).
- **A taker**: the decision's `current` (the stored taker if available, else the computer's pick at entry). Enter
  sends the highlighted player, no key sends none (the current pick stands). **C** sends none too [derived: F030:
  the original's C takes `1FDD`'s pick made at entry, which the kit does not expose; it differs from the current
  pick only when a stored taker is available]. The answer reaches the engine as the kit's `Match.answer(taker=…)`.
- **The shoot-out order**: Enter adds the highlighted player to the order, **Esc** undoes the last pick, and the
  order goes to the engine once as many are picked as the original needs (`takers`); **C** sends the picks so far,
  the rest by the original's Enter [confirmed: the kit's `_order_key`, 9B93].
"""
from __future__ import annotations

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import QHBoxLayout

from goal2.ui import theme
from goal2.ui.screen import Screen, label
from goal2.ui.squad_card import PlayerCard, Strip, full_name

WAIT_MS = 10_000   # [confirmed: F030, 0791:CC7B wait_or_key(1000) of 10 nominal ms]
ROLES = {1: "captain", 2: "corner", 3: "penalty", 4: "free kick", 5: "goal kick"}   # [confirmed: F030, DS:0A29]


class ChooseScreen(Screen):
    """`mode`: 'captain', 'taker' or 'order'. `eleven`: the player words in the strip's order; `current` where the
    highlight starts; `available`: who can be chosen; `answer(value)` gets the choice once: a player word (or None
    for no key / C on a taker), or the order's list."""
    escape_text = None

    def __init__(self, window, model, mode, eleven, current, answer, *, available=None, role=1, takers=0,
                 computer=None, match="", decision_data=None):
        super().__init__(window)
        from goal2.game.player_card import card
        self.model, self.mode, self.answer_to = model, mode, answer
        self.eleven = list(eleven)
        self.available = list(available) if available is not None else list(eleven)
        self.computer = computer
        self.takers = takers
        self.picks = []
        self.done = False
        state = model.state
        if decision_data is not None:
            from goal2.ui.live_cards import player_snapshot, card_state
            state = card_state(state, player_snapshot(decision_data), decision_data.get("tactics"))
        self.cards = [card(state, w, model.goaldat) for w in self.eleven]
        self.index = self.eleven.index(current) if current in self.eleven else 0
        what = ROLES.get(role, "taker")
        self.title = f"{match} · {'penalty order' if mode == 'order' else what}"
        self.name_label.setText(self.title)
        if mode == "captain":
            self.wait_for("Choose your captain to kick off",
                          "The match starts as soon as a captain is chosen. The highlight starts on the computer's "
                          "pick. Enter: the highlighted player · C: computer select · no key: the computer's pick "
                          "stands after the original's wait (10 s).")
            enter = "Captain: kick off"
        elif mode == "taker":
            self.wait_for(f"Choose your {what} taker",
                          "The match waits for its taker. Enter: the highlighted player · C: computer select · no key: "
                          "the current pick stands after the original's wait (10 s).")
            enter = f"{what.capitalize()} taker"
        else:
            self.wait_for("Choose your penalty takers",
                          f"Pick {takers} takers in order; Enter adds the highlighted player, Esc undoes a pick, "
                          "C leaves the rest to the original's order.")
            enter = "Add to the order"
        self.bind((Qt.Key.Key_Up,), "", lambda: self.move(-1), shown=False)
        self.bind((Qt.Key.Key_Down,), "", lambda: self.move(1), shown=False)
        self.bind((), "player", None, captions=("↑", "↓"))
        self.bind((Qt.Key.Key_C,), "computer select", self.computer_select)
        if mode == "order":
            self.bind((Qt.Key.Key_Escape,), "undo a pick", self.undo)
        self.set_enter(enter, self.choose)
        row = QHBoxLayout()
        row.setSpacing(18)
        self.card = PlayerCard()
        row.addWidget(self.card, 1)
        self.strip = Strip()
        self.strip.chosen.connect(self.click)
        row.addWidget(self.strip)
        self.body_layout.addLayout(row, 1)
        self.order_label = label("", "sub")
        self.order_label.setStyleSheet(f"color: {theme.VALUE}; background: transparent;")
        self.body_layout.addWidget(self.order_label)
        self.timer = QTimer(self)
        self.timer.setSingleShot(True)
        self.timer.setInterval(WAIT_MS)
        self.timer.timeout.connect(self.no_key)
        if mode != "order":
            self.timer.start()
        self._show()

    def _show(self):
        names = self.model.goaldat.country_names
        rows = [(c["role"], c["line"], c["full_name"]) for c in self.cards]
        self.strip.show_rows(f"{names[self.model.state.managed_country]}'s eleven", rows, self.index, False)
        self.card.set_card(self.cards[self.index])
        if self.mode == "order":
            picked = ", ".join(full_name(self.model, w) for w in self.picks) or "none yet"
            self.order_label.setText(f"Order: {picked} ({len(self.picks)} of {self.takers})")

    def highlighted(self):
        return self.eleven[self.index]

    def move(self, step):
        self.index = (self.index + step) % len(self.eleven)
        if self.mode != "order":
            self.timer.start()   # [confirmed: F030] Up/Down restart the wait
        self._show()

    def click(self, index):
        if index == self.index:
            return self.choose()
        self.index = index
        self._show()

    def _give(self, value):
        if self.done:
            return
        self.done = True
        self.timer.stop()
        self.answer_to(value)

    def choose(self):
        word = self.highlighted()
        if self.mode == "order":
            if word in self.picks or word not in self.available:
                return
            self.picks.append(word)
            self._show()
            if len(self.picks) >= self.takers:
                self._give(list(self.picks))
            return
        if word not in self.available:
            return   # [confirmed: F030] an unavailable player is not taken; the prompt waits on
        self._give(word)

    def computer_select(self):
        if self.mode == "captain":
            self._give(self.computer)
        elif self.mode == "taker":
            self._give(None)
        else:
            self._give(list(self.picks))

    def no_key(self):
        """The original's wait ran out: the current pick stands."""
        self._give(self.computer if self.mode == "captain" else None)

    def undo(self):
        if self.picks:
            self.picks.pop()
            self._show()

    def closing(self):
        self.timer.stop()
