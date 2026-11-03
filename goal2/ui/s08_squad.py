"""S08 Squad and pool: who is in the twenty, in what position.

[designed: owner, 2026-11-03, #526; docs/design/ui-2026-11, S08 and its mockup s08-squad.html; T165] The player
card on the left; on the right the twenty or the pool (←→), as the original's SELECT YOUR TEAM screen [confirmed:
T156-R1 steps 14–29; docs/original-game/images/m244-squad.png, m244-pool.png, m244-pool-next.png]. Every change is
the model's own (`DesktopModel`, route (b), #527 D2): the screen holds no rule of the game.

- **↑↓** the player; on the pool they go on to the next or the previous page of twenty, as the original's pool list
  pages [designed: main session, 2026-11-03, T165; m244-pool, m244-pool-next].
- **←→** the squad (←) or the pool (→).
- **Enter** moves a player, the original's two Enters [confirmed: F031, `0791:DEA6`; T156-R1 step 17]: Enter on a
  pool player picks him, ← back, Enter on the player he replaces exchanges them (`DesktopModel.exchange`). Once a
  player is picked the Enter hint reads *put here*, and the screen says what it waits for (§3, "Stops"). Enter on a
  squad player first, then on a pool player, does the same exchange. [designed: T165] Enter on another player of the
  same side moves the pick to him, Enter on the picked player drops it; two squad players are not swapped on this
  route (the Python route keeps the eleven apart from the squad order).
- **Ins**, the assistant's recommended 20, is on the bar marked *coming later* and only says so: the original's
  assistant (`0791:DC7E`, F024/F031) is not ported, and today's *Suggest* runs it under Unicorn on the Core route,
  which m3 removes. [designed: owner, 2026-11-03, #509]
- **R** the next position, **Shift+R** the previous one, **C** the club position (`set_position`,
  `club_position`); **T** his tactics (S09); **F2** a new name, typed in the card's name line (`rename_player`);
  **Esc** back to the desk.
- The mouse does what the keys do [designed: owner, 2026-11-03, #526]: a click on a row moves the cursor to it, a
  click on the highlighted row is Enter; a click on a key of the bar, on the Enter hint or on *Squad* / *Pool* is
  that key.
"""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QHBoxLayout, QVBoxLayout

from goal2.ui import theme
from goal2.ui.screen import Clickable, Screen, label
from goal2.ui.squad_card import PlayerCard, Strip, colour, full_name, last_on_the_bar, squad_rows

COMING_LATER = ("The assistant's recommended 20 is coming later: the original's assistant is not ported yet. "
                "Nothing was changed.")


def shift_held():
    return bool(QApplication.keyboardModifiers() & Qt.KeyboardModifier.ShiftModifier)


class SideButton(Clickable):
    """*Squad (20)* or *Pool* above the card, as the mockup's two buttons; the side shown is the primary one."""

    def __init__(self, text):
        super().__init__("sideButton")
        layout = QHBoxLayout(self)
        layout.setContentsMargins(14, 6, 14, 6)
        self.text = label(text, "sideText")
        layout.addWidget(self.text)
        self.set_on(False)

    def set_on(self, on):
        background = theme.HIGHLIGHT if on else theme.GROUND
        self.setStyleSheet(f"#sideButton {{ background: {background}; border: 1px solid "
                           f"{theme.HIGHLIGHT if on else theme.FRAME_DARK}; }}")
        colour(self.text, theme.ON_HIGHLIGHT if on else theme.TEXT_BRIGHT)


class SquadScreen(Screen):
    title = "select squad"
    escape_text = "desk"
    picked = None     # (side, player) once a player is picked for a move
    editing = False   # the name line is open (F2)

    def __init__(self, window, model):
        super().__init__(window)
        self.model = model
        self.side = "squad"
        self.cursor = {"squad": 0, "pool": 0}
        self.message = ""
        self._build()
        self.bind((Qt.Key.Key_Up,), "", lambda: self.move(-1), captions=("",), shown=False)
        self.bind((Qt.Key.Key_Down,), "", lambda: self.move(1), captions=("",), shown=False)
        self.bind((), "player", None, captions=("↑", "↓"))
        self.bind((Qt.Key.Key_Left,), "", lambda: self.show_side("squad"), captions=("",), shown=False)
        self.bind((Qt.Key.Key_Right,), "", lambda: self.show_side("pool"), captions=("",), shown=False)
        self.bind((), "squad / pool", None, captions=("←", "→"))
        self.bind((Qt.Key.Key_Insert,), "coming later", self.assistant)
        self.bind((Qt.Key.Key_R,), "next position", lambda: self.reposition(-1 if shift_held() else 1))
        self.bind((Qt.Key.Key_C,), "club position", self.club_position)
        self.bind((Qt.Key.Key_T,), "his tactics", self.his_tactics)
        self.bind((Qt.Key.Key_F2,), "new name", self.new_name)
        # [designed: T165] Nine keys and the Enter hint fill the 1440 px bar: the keys sit 12 px apart, not 22, and
        # Ins reads "coming later" (the row above the card names it: the assistant's recommended 20).
        self.key_layout.setSpacing(12)
        last_on_the_bar(self, "desk")
        self.set_enter("Move player", self.press_move)
        self.refresh()

    # Building.
    def _build(self):
        main = QHBoxLayout()
        main.setSpacing(18)
        column = QVBoxLayout()
        column.setSpacing(14)
        top = QHBoxLayout()
        top.setSpacing(10)
        self.squad_button = SideButton("Squad (20)")
        self.pool_button = SideButton("Pool")
        self.squad_button.clicked.connect(lambda: self.show_side("squad"))
        self.pool_button.clicked.connect(lambda: self.show_side("pool"))
        top.addWidget(self.squad_button)
        top.addWidget(self.pool_button)
        top.addWidget(label("←→ toggles · Ins: the assistant's recommended 20 (coming later)", "sub"))
        top.addStretch(1)
        self.note = label("", "sub")
        top.addWidget(self.note)
        column.addLayout(top)
        self.card = PlayerCard()
        column.addWidget(self.card, 1)
        main.addLayout(column, 1)
        self.strip = Strip()
        self.strip.chosen.connect(self.click_row)
        main.addWidget(self.strip)
        self.body_layout.addLayout(main, 1)

    # What is shown.
    def rows(self, side=None):
        """The players of a side, in the strip's order: the squad's twenty, or the pool's eighty."""
        side = side or self.side
        if side == "squad":
            return squad_rows(self.model)[0]
        pool = self.model.pool_view()
        return pool["reserves"] if pool is not None else []

    def current(self):
        """The player whose card is shown: the cursor's, on the side shown."""
        rows = self.rows()
        if not rows:
            return None
        self.cursor[self.side] = max(0, min(self.cursor[self.side], len(rows) - 1))
        return rows[self.cursor[self.side]]["id"]

    def page(self):
        return self.cursor["pool"] // Strip.PAGE if self.side == "pool" else 0

    def refresh(self):
        from goal2.game.player_card import card
        rows = self.rows()
        word = self.current()
        if self.side == "squad":
            shown, eleven = squad_rows(self.model)
            heading, gap, cursor = self.model.view()["country_name"], eleven == 11, self.cursor["squad"]
        else:
            start = self.page() * Strip.PAGE
            shown = rows[start:start + Strip.PAGE]
            heading, gap, cursor = "Pool of players", False, self.cursor["pool"] - start
        self.strip.show_rows(heading, [(r["role"], r["line"], full_name(self.model, r["id"])) for r in shown],
                             cursor, gap)
        self.squad_button.set_on(self.side == "squad")
        self.pool_button.set_on(self.side == "pool")
        if word is not None:
            self.card.set_card(card(self.model.state, word, self.model.goaldat))
        self.note.setText(self.message)
        if self.picked is not None:
            self.wait_for(f"Put {full_name(self.model, self.picked[1])} here",
                          "← or → to the other side, then Enter on the player he replaces. Enter on him again "
                          "keeps the squad as it is.")
        else:
            self.wait_for(None)
        self._refresh_hint()

    def enter_hint_text(self):
        if self.editing:
            return "Give this name"
        return "Put here" if self.picked is not None else "Move player"

    def say(self, text):
        self.message = text
        self.refresh()

    # Keys.
    def handle_key(self, key):
        if self.editing:
            if key in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
                self.give_name()
                return True
            if key == Qt.Key.Key_Escape:
                self.close_name()
                return True
            if key == Qt.Key.Key_F1:
                return super().handle_key(key)
            return True
        return super().handle_key(key)

    def press_enter(self):
        if self.editing:
            return self.give_name()
        return super().press_enter()

    def move(self, step):
        rows = self.rows()
        if rows:
            self.cursor[self.side] = max(0, min(len(rows) - 1, self.cursor[self.side] + step))
        self.message = ""
        self.refresh()

    def show_side(self, side):
        if side == "pool" and self.model.pool_view() is None:
            return self.say("There is no pool outside a campaign.")
        self.side = side
        self.message = ""
        self.refresh()

    def click_row(self, index):
        """A click on a row moves the cursor there; on the highlighted row it is Enter."""
        position = index + (self.page() * Strip.PAGE if self.side == "pool" else 0)
        if position == self.cursor[self.side]:
            return self.press_enter()
        self.cursor[self.side] = position
        self.message = ""
        self.refresh()

    def press_move(self):
        """Enter: pick a player, or put the picked one in place of this one (the model's exchange)."""
        word = self.current()
        if word is None:
            return None
        here = (self.side, word)
        self.message = ""
        if self.picked is None or self.picked[0] == self.side:
            self.picked = None if self.picked == here else here
            return self.refresh()
        sides = {self.picked[0]: self.picked[1], self.side: word}
        self.picked = None
        try:
            self.model.exchange(sides["squad"], sides["pool"])
        except ValueError as exc:
            return self.say(str(exc))
        return self.refresh()

    def assistant(self):
        self.say(COMING_LATER)

    def edit(self, change):
        word = self.current()
        if word is None:
            return
        try:
            change(word)
        except ValueError as exc:
            return self.say(str(exc))
        self.message = ""
        self.refresh()

    def reposition(self, step):
        self.edit(lambda word: self.model.set_position(word, step))

    def club_position(self):
        self.edit(self.model.club_position)

    def his_tactics(self):
        from goal2.ui.s09_player_tactics import PlayerTacticsScreen
        word = self.current()
        if word is not None:
            self.window_.push(PlayerTacticsScreen(self.window_, self.model, word))

    def new_name(self):
        word = self.current()
        if word is None:
            return
        self.editing = True
        self.card.edit_name(True, self.model.goaldat.player_names[word])
        self._refresh_hint()

    def give_name(self):
        word = self.current()
        try:
            self.model.rename_player(word, self.card.name_line.edit.text())
        except ValueError as exc:
            self.message = str(exc)
            self.note.setText(self.message)
            return
        self.close_name()

    def close_name(self):
        self.editing = False
        self.card.edit_name(False)
        self.window_.setFocus()
        self.message = ""
        self.refresh()

    def shown(self):
        """Back from S09: read the model again."""
        self.refresh()


def open_squad(window, model):
    """Push S08 over the current screen; T164 calls it from the desk."""
    return window.push(SquadScreen(window, model))
