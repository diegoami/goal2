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
  squad player first, then on a pool player, does the same exchange. Enter on the picked player drops the pick.
  [confirmed: m244-squad, T156-R1 steps 14–29; designed: T164, #555] Enter on a squad player and then on another squad
  player swaps them, as the original's *move player* within the twenty chooses the eleven: a starter and a bench
  player swap in and out, two starters change places (`DesktopModel.swap`, which publishes the eleven as `confirm`
  does). An unavailable starter can be moved to the bench this way. Two bench players keep the squad's order (the
  model says why). [designed: T165] Enter on another pool player moves the pick to him.
- **Ins**, the assistant's recommended 20, is on the bar marked *coming later* and only says so: the original's
  assistant (`0791:DC7E`, F024/F031) is not ported, and today's *Suggest* runs it under Unicorn on the Core route,
  which m3 removes. [designed: owner, 2026-11-03, #509]
- **R** the next position, **Shift+R** the previous one, **C** the club position (`set_position`,
  `club_position`); **T** his tactics (S09); **F2** a new name, typed in the card's name line (`rename_player`);
  **Esc** back to the desk.
- The mouse does what the keys do [designed: owner, 2026-11-03, #526]: a click on a row moves the cursor to it, a
  click on the highlighted row is Enter; a click on a key of the bar, on the Enter hint or on *Squad* / *Pool* is
  that key.
- **The pool's search and position filter**, a GOAL2 ADDITION the original lacks [designed: owner, §6 item 18
  (docs/design/ui-2026-11, 2026-11-03); T177, #557], as today's Pool page has them (docs/desktop-management.md,
  `DesktopModel.pool_view(query=, position=)`): **/** opens the search line over the pool, typing filters by name,
  accents folded (`campaign_pool.fold`: "muller" finds "Müller"), Backspace edits, Enter keeps the filter and closes
  the line, Esc clears it; **P** steps the position filter through the original's fourteen position codes and back
  to all (**Shift+P** the other way). The rows the pool shows are `pool_view(query, position)`'s, and the two Enters
  exchange from a filtered list as from the whole pool. Neither key is one of the original's on this screen (its
  bottom line lists F2, R, C, T, Enter, Esc; its top line ←→, ↑↓, Enter, Ins [confirmed: E031 C06, C27, C29–C31;
  docs/original-game/squad-and-tactics.md]); a click on the search line or on the position filter is the key.
"""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QHBoxLayout, QVBoxLayout, QWidget

from goal2.ui import theme
from goal2.ui.screen import Clickable, Screen, kbd, label, para
from goal2.ui.squad_card import PlayerCard, Strip, colour, full_name, last_on_the_bar, squad_rows

SEARCH_MAX = 12   # [designed: T177] a surname's length on this route (`rename_player`'s 12 characters)
# [designed: owner, §6 item 18; T177] the extra's words on the screen
ADDITION = "GOAL2 ADDITION · POOL SEARCH"
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


class FilterButton(Clickable):
    """The pool's search line or its position filter, with its key cap: a click is the key."""

    def __init__(self, caption, text, handler):
        super().__init__("filterButton")
        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 4, 10, 4)
        layout.setSpacing(8)
        layout.addWidget(kbd(caption))
        self.text = label(text, "value")
        layout.addWidget(self.text)
        self.clicked.connect(handler)

    def set_text(self, text, active=False):
        self.text.setText(text)
        self.setStyleSheet(f"#filterButton {{ background: {theme.GROUND}; border: 1px solid "
                           f"{theme.FRAME if active else theme.FRAME_DARK}; }}")


class SquadScreen(Screen):
    title = "select squad"
    escape_text = "desk"
    picked = None     # (side, player) once a player is picked for a move
    editing = False   # the name line is open (F2)
    searching = False   # the pool's search line is open (/) [designed: T177]

    def __init__(self, window, model):
        super().__init__(window)
        self.model = model
        self.side = "squad"
        self.cursor = {"squad": 0, "pool": 0}
        self.message = ""
        self.query = ""        # the pool's search, by name [designed: T177]
        self.position = None   # the pool's position filter: a position code 0-13, or None for all
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
        # [designed: owner, §6 item 18; T177] The pool's search and position filter, keys the original's S08 lacks.
        self.search_binding = self.bind((Qt.Key.Key_Slash,), "search", self.open_search)
        self.position_binding = self.bind((Qt.Key.Key_P,), "position",
                                          lambda: self.step_position(-1 if shift_held() else 1))
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
        top.addWidget(label("←→ squad / pool · Ins assistant", "sub"))
        top.addStretch(1)
        self.note = label("", "sub")
        top.addWidget(self.note)
        column.addLayout(top)
        # [designed: owner, §6 item 18; T177] the pool's search and position filter, tagged as a goal2 addition
        extras = QHBoxLayout()
        extras.setSpacing(10)
        extras.addWidget(label(ADDITION, "tagNew"))
        self.search_button = FilterButton("/", "", self.open_search)
        self.search_button.setFixedWidth(340)
        extras.addWidget(self.search_button)
        self.position_button = FilterButton("P", "", lambda: self.step_position(1))
        extras.addWidget(self.position_button)
        extras.addStretch(1)
        column.addLayout(extras)
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
        pool = self.model.pool_view(query=self.query, position=self.position)
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
        self._show_filters(rows)
        self.note.setText(self.message)
        if self.picked is not None:
            detail = ("Enter on another player of the twenty swaps them; → to the pool, then Enter on the player "
                      "who replaces him. Enter on him again keeps the squad as it is." if self.picked[0] == "squad"
                      else "← to the squad, then Enter on the player he replaces. Enter on him again keeps the squad "
                      "as it is.")
            self.wait_for(f"Put {full_name(self.model, self.picked[1])} here", detail)
        else:
            self.wait_for(None)
        self._refresh_hint()

    def _refresh_bar(self):
        """[designed: T177] The bar has no room for two more items at 1440 px (T165's nine leave 5 px), so pairs of
        related keys share a column, one above the other: R over C (the positions), / over P (the pool's search and
        filter). Each key keeps its own item, caption, text and click."""
        super()._refresh_bar()
        pairs = getattr(self, "PAIRS", None)
        if pairs is None or not hasattr(self, "position_binding"):
            return
        items = {item.binding.text: item for item in self.key_bar.findChildren(Clickable, "keyItem")
                 if getattr(item, "binding", None) is not None}
        for upper, lower in pairs:
            if upper not in items or lower not in items:
                continue
            column = QWidget()
            column.setObjectName("keyColumn")
            stack = QVBoxLayout(column)
            stack.setContentsMargins(0, 0, 0, 0)
            stack.setSpacing(4)
            index = self.key_layout.indexOf(items[upper])
            for text in (upper, lower):
                self.key_layout.removeWidget(items[text])
                stack.addWidget(items[text])
            self.key_layout.insertWidget(index, column)

    PAIRS = (("next position", "club position"), ("search", "position"))

    def _show_filters(self, rows):
        cursor = "▌" if self.searching else ""
        if self.query or self.searching:
            text = f"search: {self.query}{cursor}"
        else:
            text = "search the pool by name"
        self.search_button.set_text(text, self.searching)
        self.position_button.set_text(f"position: {self.position_name()}", self.position is not None)
        if self.side == "pool" and not rows and (self.query or self.position is not None):
            self.message = self.message or "No player of the pool matches the search."

    def position_name(self):
        """The position filter's words: the original's code and position name, or *all*."""
        if self.position is None:
            return "all"
        from goal2.game import roles
        return f"{roles.tables(self.model.state)[0][self.position]} · {roles.names(self.model.state)[self.position]}"

    def enter_hint_text(self):
        if self.searching:
            return "Keep search"
        if self.editing:
            return "Give this name"
        return "Put here" if self.picked is not None else "Move player"

    def say(self, text):
        self.message = text
        self.refresh()

    # Keys.
    def type_text(self, key, text) -> bool:
        """On the search line, printable characters and Backspace edit the search; the pool follows each key."""
        if not self.searching:
            return False
        if key == Qt.Key.Key_Backspace:
            self.set_query(self.query[:-1])
            return True
        if text and len(text) == 1 and text.isprintable():
            if len(self.query) < SEARCH_MAX:
                self.set_query(self.query + text)
            return True
        return False

    def handle_key(self, key):
        if self.searching:
            if key in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
                self.close_search()
                return True
            if key == Qt.Key.Key_Escape:
                self.close_search(clear=True)
                return True
            if key in (Qt.Key.Key_F1, Qt.Key.Key_Up, Qt.Key.Key_Down):
                return super().handle_key(key)
            return True
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
        if self.searching:
            return self.close_search()
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
        if self.picked is None or self.picked == here or (self.picked[0] == self.side == "pool"):
            self.picked = None if self.picked == here else here
            return self.refresh()
        if self.picked[0] == self.side:   # two squad players: the swap within the twenty (#555)
            first = self.picked[1]
            self.picked = None
            try:
                self.model.swap(first, word)
            except ValueError as exc:
                return self.say(str(exc))
            return self.refresh()
        sides = {self.picked[0]: self.picked[1], self.side: word}
        self.picked = None
        try:
            self.model.exchange(sides["squad"], sides["pool"])
        except ValueError as exc:
            return self.say(str(exc))
        return self.refresh()

    # The pool's search and position filter. [designed: owner, §6 item 18; T177]
    def open_search(self):
        """/: the pool, with the search line open."""
        if self.editing:
            return None
        if self.side != "pool":
            self.show_side("pool")
            if self.side != "pool":
                return None
        self.searching = True
        self.message = ""
        return self.refresh()

    def close_search(self, clear=False):
        """Enter keeps the search, Esc clears it; the line closes either way."""
        self.searching = False
        if clear:
            return self.set_query("")
        return self.refresh()

    def set_query(self, query):
        self.query = query
        self.cursor["pool"] = 0
        self.message = ""
        self.refresh()

    def step_position(self, step):
        """P: the next of the original's fourteen position codes, then all again; Shift+P the other way."""
        if self.editing or self.searching:
            return None
        if self.side != "pool":
            self.show_side("pool")
            if self.side != "pool":
                return None
        values = [None, *range(14)]
        self.position = values[(values.index(self.position) + step) % len(values)]
        self.cursor["pool"] = 0
        self.message = ""
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
