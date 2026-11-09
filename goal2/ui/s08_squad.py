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
from PySide6.QtWidgets import QApplication, QHBoxLayout

from goal2.ui import theme
from goal2.ui.cell_parts import GridCard, GridStrip
from goal2.ui.cells import CellLabel, CellPara, Cells
from goal2.ui.screen import Clickable, Screen
from goal2.ui.squad_card import colour, full_name, last_on_the_bar, squad_rows

# [designed: T211; docs/design/ui-2026-11/proposal/README.md, s08-squad] The squad's cells: 90 columns and the 25 rows between the title
# row and the two key rows. The card is 69 x 18 under two rows of buttons; the twenty (or the pool) in a frame of 20 columns at the
# right, a column apart; under the card the message; across the foot, under all of it, what a pick waits for.
BODY_COLS, BODY_ROWS = theme.COLS, theme.ROWS - 3
STRIP_COLS = 20
CARD_AT = 2
LEFT_COLS = GridCard.COLS
STRIP_AT = BODY_COLS - STRIP_COLS
WAIT_AT, WAIT_ROWS = GridStrip.PAGE + 2, 3

SEARCH_MAX = 12   # [designed: T177] a surname's length on this route (`rename_player`'s 12 characters)
# [designed: owner, §6 item 18; T177] the extra's words on the screen
ADDITION = "GOAL2 ADDITION · POOL SEARCH"
COMING_LATER = ("The assistant's recommended 20 is coming later: the original's assistant is not ported yet. "
                "Nothing was changed.")


def shift_held():
    return bool(QApplication.keyboardModifiers() & Qt.KeyboardModifier.ShiftModifier)


class SideButton(Clickable):
    """*Squad (20)* or *Pool* above the card, as the mockup's two buttons; the side shown is the highlight bar, a cell in from each
    edge of its text. [designed: T211]"""

    def __init__(self, text):
        super().__init__("sideButton")
        layout = QHBoxLayout(self)
        layout.setContentsMargins(theme.CELL_W, 0, theme.CELL_W, 0)
        layout.setSpacing(0)
        self.text = CellLabel(text, "sideText")
        layout.addWidget(self.text)
        self.set_on(False)

    def set_on(self, on):
        self.setStyleSheet(f"#sideButton {{ background: {theme.HIGHLIGHT if on else theme.GROUND}; }}")
        colour(self.text, theme.ON_HIGHLIGHT if on else theme.TEXT_BRIGHT)


class FilterButton(Clickable):
    """The pool's search line or its position filter, with its key: a click is the key. The key, a cell, then the words; a filter
    that is in use is in the value colour. [designed: T211]"""

    def __init__(self, caption, text, handler):
        super().__init__("filterButton")
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(theme.CELL_W)
        layout.addWidget(CellLabel(caption, "keyCap"))
        self.text = CellLabel(text, "value")
        layout.addWidget(self.text)
        layout.addStretch(1)
        self.clicked.connect(handler)

    def set_text(self, text, active=False):
        self.text.setText(text)
        colour(self.text, theme.VALUE if active else theme.TEXT_BRIGHT)


class SquadScreen(Screen):
    GRID = True   # [designed: T211] laid out on the 16 x 32 grid, no card
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
        # [designed: T165] Ins reads "coming later" (the hint at the title row names it: the assistant's recommended 20).
        # [designed: T211] The twelve keys and the Enter hint are two rows of cells, a cell apart (the grid's bar).
        last_on_the_bar(self, "desk")
        self.set_enter("Move player", self.press_move)
        self.refresh()

    # Building.
    def _build(self):
        """The squad on its cells [designed: T211]: the two buttons and the goal2 addition's tag, then its filters; under them the
        card; at the right the twenty. The hint of the keys is at the right of the title row (as the desk's banner is), the screen's
        message under the card, and what a pick waits for across the foot of the page, under the twenty."""
        body = Cells(BODY_COLS, BODY_ROWS, "squadBody")
        self.body_layout.addWidget(body, 1)
        self.area = body
        self.squad_button = SideButton("Squad (20)")
        self.pool_button = SideButton("Pool")
        self.squad_button.clicked.connect(lambda: self.show_side("squad"))
        self.pool_button.clicked.connect(lambda: self.show_side("pool"))
        body.put(self.squad_button, 0, 0, len("Squad (20)") + 2)
        body.put(self.pool_button, len("Squad (20)") + 3, 0, len("Pool") + 2)
        self.hint = CellLabel("←→ squad / pool · Ins assistant", "sub")
        self.name_label.parentWidget().layout().addWidget(self.hint)
        # [designed: owner, §6 item 18; T177] the pool's search and position filter, tagged as a goal2 addition
        body.text(ADDITION, "tagNew", len("Squad (20)") + len("Pool") + 6, 0)
        self.search_button = FilterButton("/", "", self.open_search)
        body.put(self.search_button, 0, 1, 27)
        self.position_button = FilterButton("P", "", lambda: self.step_position(1))
        body.put(self.position_button, 28, 1, 36)
        self.card = GridCard()
        body.put(self.card, 0, CARD_AT, GridCard.COLS, GridCard.ROWS)
        self.note = CellPara("", "sub")
        body.put(self.note, 0, CARD_AT + GridCard.ROWS, LEFT_COLS, 2)
        self.strip = GridStrip(STRIP_COLS)
        self.strip.chosen.connect(self.click_row)
        body.put(self.strip, STRIP_AT, 0, STRIP_COLS, GridStrip.PAGE + 2)
        self.main_layout.removeWidget(self.wait_box)
        body.put(self.wait_box, 0, WAIT_AT, BODY_COLS, WAIT_ROWS)

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
        return self.cursor["pool"] // GridStrip.PAGE if self.side == "pool" else 0

    def refresh(self):
        from goal2.game.player_card import card
        rows = self.rows()
        word = self.current()
        if self.side == "squad":
            shown, eleven = squad_rows(self.model)
            heading, gap, cursor = self.model.view()["country_name"], eleven == 11, self.cursor["squad"]
        else:
            start = self.page() * GridStrip.PAGE
            shown = rows[start:start + GridStrip.PAGE]
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
        position = index + (self.page() * GridStrip.PAGE if self.side == "pool" else 0)
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
