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
- **A** (or **Ins**), the assistant's recommended 20, explicitly asks the original assistant through the owner's shared
  PyPy process. [confirmed: T183a/F031] The original orders the selection; [derived: T183b] current opening-career
  metadata supplies its input. [designed: owner, T183c] Progress and cancellation stay responsive; only a current,
  verified result is published. Full later native-calendar acceptance remains T183's separate gate.
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

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import QApplication, QHBoxLayout, QMenu

from goal2.ui import theme
from goal2.ui.cell_parts import CellTableRow, GridCard, GridStrip
from goal2.ui.cells import CellLabel, CellPara, Cells
from goal2.ui.frame import PanelOutline
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
ASSISTANT_WAIT = "The assistant is choosing twenty.\nEsc: cancel and return to desk."
ASSISTANT_UNAVAILABLE = "The assistant is not available for this career yet.\nYour selection is unchanged."
ASSISTANT_IDLE = "A: ask your assistant to choose twenty.\nThe full squad and pool are considered."
ROLE_AT = STRIP_COLS - 3


class SquadStrip(GridStrip):
    """[designed: #862; m244-squad.png] Keep the line colour and place the role behind a rail."""

    def __init__(self, *, expanded):
        super().__init__(STRIP_COLS, count=24 if expanded else GridStrip.PAGE, compact=expanded)
        self.role_rail = PanelOutline(self.area, self._role_segments)
        self.area.layout().addWidget(self.role_rail)

    def make_row(self, index):
        name_cols = ROLE_AT - 1
        row = CellTableRow(index, (2, name_cols), (Qt.AlignmentFlag.AlignRight, None), (1, 1), plain=True)
        role, name = row.cells
        row.area.move(name, 1, 0, name_cols)
        row.area.move(role, ROLE_AT, 0, 2)
        return row

    def _role_segments(self):
        x = round(self.area.width() * ROLE_AT / self.cols)
        return ((x, 0, x, self.area.height() - 1),)


def shift_held():
    return bool(QApplication.keyboardModifiers() & Qt.KeyboardModifier.ShiftModifier)


class SideButton(Clickable):
    """*Squad (20)* or *Pool* above the card, as the mockup's two buttons; the side shown is the highlight bar, a cell in from each
    edge of its text (the button is two cells wider than its text and the text is centred: no margin whose rounded pixels could
    squeeze it at a fractional scale). [designed: T211]"""

    def __init__(self, text):
        super().__init__("sideButton")
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        self.text = CellLabel(text, "sideText")
        self.text.setAlignment(Qt.AlignmentFlag.AlignCenter)
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
        self.text.reserve = len(text) + 1
        self.text.setText(text)
        colour(self.text, theme.VALUE if active else theme.TEXT_BRIGHT)


class SquadScreen(Screen):
    GRID = True   # [designed: T211] laid out on the 16 x 32 grid, no card
    title = "select squad"
    escape_text = "desk"
    picked = None     # (side, player) once a player is picked for a move
    editing = False   # the name line is open (F2)
    searching = False   # the pool's search line is open (/) [designed: T177]
    _assistant_token = None   # Screen builds its Enter hint before subclass initialisation.

    def __init__(self, window, model, *, back=None):
        # [designed: #799] The caller names the actual parent; held matches keep their default.
        self.escape_text = back if back is not None else 'match menu' if getattr(model, 'held_prematch', False) else 'desk'
        super().__init__(window)
        self.model = model
        self._assistant_jobs = None
        self._assistant_token = None
        self._assistant_timer = QTimer(self)
        self._assistant_timer.setInterval(20)
        self._assistant_timer.timeout.connect(self._poll_assistant)
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
        # [designed: owner playtest, #766] A is accessible without an Insert key.
        self.bind((Qt.Key.Key_A, Qt.Key.Key_Insert), "assistant", self.assistant, captions=("A",))
        if self.can_resize():
            self.bind((Qt.Key.Key_F6,), "squad size", self.choose_size, shown=False)
        self.bind((Qt.Key.Key_R,), "next position", lambda: self.reposition(-1 if shift_held() else 1))
        self.bind((Qt.Key.Key_C,), "club position", self.club_position)
        self.bind((Qt.Key.Key_T,), "his tactics", self.his_tactics)
        self.bind((Qt.Key.Key_F2,), "new name", self.new_name)
        # [designed: owner, §6 item 18; T177] The pool's search and position filter, keys the original's S08 lacks.
        self.search_binding = self.bind((Qt.Key.Key_Slash,), "search", self.open_search)
        self.position_binding = self.bind((Qt.Key.Key_P,), "position",
                                          lambda: self.step_position(-1 if shift_held() else 1))
        # [designed: T183c/#766] The assistant action is explicit; no selection runs on screen entry.
        # [designed: T211] The twelve keys and the Enter hint are two rows of cells, a cell apart (the grid's bar).
        last_on_the_bar(self, self.escape_text)
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
        self.name_label.reserve = len(self.title) + 1
        hint = "←→ squad / pool · A assistant"
        self.hint = CellLabel(hint, "sub", reserve=len(hint) + 2)
        self.name_label.parentWidget().layout().addWidget(self.hint)
        # [designed: owner, §6 item 18; T177] the pool's search and position filter, tagged as a goal2 addition
        body.text(ADDITION, "tagNew", len("Squad (20)") + len("Pool") + 6, 0, len(ADDITION) + 2)
        self.size_button = FilterButton("F6", "", self.choose_size)
        body.put(self.size_button, 52, 0, 17)
        self.size_button.setVisible(self.can_resize())
        self.size_menu = QMenu(self)
        self.size_menu.setStyleSheet(
            f"QMenu {{ background: {theme.GROUND}; border: 1px solid {theme.FRAME}; }} "
            f"QMenu::item:selected {{ background: {theme.HIGHLIGHT}; color: {theme.ON_HIGHLIGHT}; }}")
        self.size_actions = {}
        for capacity in (20, 22, 24):
            action = self.size_menu.addAction(f"{capacity} players")
            action.setCheckable(True)
            action.triggered.connect(lambda checked=False, size=capacity: self.resize_selection(size))
            self.size_actions[capacity] = action
        self.search_button = FilterButton("/", "", self.open_search)
        body.put(self.search_button, 0, 1, 27)
        self.position_button = FilterButton("P", "", lambda: self.step_position(1))
        body.put(self.position_button, 28, 1, 36)
        self.card = GridCard(segmented_bars=True)
        body.put(self.card, 0, CARD_AT, GridCard.COLS, GridCard.ROWS)
        self.note = CellPara("", "sub")
        body.put(self.note, 0, CARD_AT + GridCard.ROWS, LEFT_COLS, 2)
        self.strip = None
        self.use_strip(expanded=False)
        self.main_layout.removeWidget(self.wait_box)
        body.put(self.wait_box, 0, WAIT_AT, BODY_COLS, WAIT_ROWS)

    def use_strip(self, *, expanded):
        if self.strip is not None:
            if self.strip.compact == expanded:
                return
            self.strip.hide()
            self.area.layout().removeWidget(self.strip)
            self.strip.setParent(None)
            self.strip.deleteLater()
        self.strip = SquadStrip(expanded=expanded)
        self.strip.chosen.connect(self.click_row)
        self.area.put(self.strip, STRIP_AT, 0, STRIP_COLS, BODY_ROWS if expanded else GridStrip.PAGE + 2)

    # What is shown.
    def capacity(self):
        return getattr(self.model.state, 'squad_capacity', 20)

    def can_resize(self):
        return (not getattr(self.model, 'held_prematch', False)
                and callable(getattr(self.model, 'resize_squad', None))
                and self.model.state.campaign is not None)

    def choose_size(self):
        if not self.can_resize() or self._assistant_blocked() or self.editing or self.searching:
            return
        for value, action in self.size_actions.items():
            action.setChecked(value == self.capacity())
        self.size_menu.popup(self.size_button.mapToGlobal(self.size_button.rect().bottomLeft()))
        self.size_menu.setActiveAction(self.size_actions[self.capacity()])

    def resize_selection(self, capacity):
        if not self.can_resize() or self._assistant_blocked() or self.editing or self.searching:
            return
        if capacity != self.capacity():
            try:
                self.model.resize_squad(capacity)
            except ValueError as exc:
                return self.say(str(exc))
            self.picked = None
            self.side = "squad"
        return self.say(f"Squad size {capacity}.")

    def rows(self, side=None):
        """Return the ordered player rows and, on Squad, any vacant selected places."""
        side = side or self.side
        if side == "squad":
            rows = squad_rows(self.model)[0]
            if self.capacity() != 20:
                view = self.model.view()
                players = {row["id"]: row for row in view["players"]}
                for slot, word in enumerate(view["squad_slots"][20:]):
                    rows.append(players[word] if word is not None else
                                {"id": None, "role": "", "line": None, "extra_slot": slot})
            return rows
        pool = self.model.pool_view(query=self.query, position=self.position)
        return pool["reserves"] if pool is not None else []

    def current_row(self):
        rows = self.rows()
        if not rows:
            return None
        self.cursor[self.side] = max(0, min(self.cursor[self.side], len(rows) - 1))
        return rows[self.cursor[self.side]]

    def current(self):
        """The player whose card is shown, if the cursor is over a player."""
        row = self.current_row()
        return row["id"] if row is not None else None

    def page(self):
        return self.cursor["pool"] // GridStrip.PAGE if self.side == "pool" else 0

    def refresh(self):
        from goal2.game.player_card import card
        rows = self.rows()
        word = self.current()
        expanded = self.side == "squad" and self.capacity() != 20
        self.use_strip(expanded=expanded)
        wait_cols = LEFT_COLS if self.capacity() != 20 else BODY_COLS
        self.area.move(self.wait_box, 0, WAIT_AT, wait_cols, WAIT_ROWS)
        if self.side == "squad":
            shown, eleven = rows, len(self.model.state.starting_eleven)
            heading, gap, cursor = self.model.view()["country_name"], eleven == 11, self.cursor["squad"]
        else:
            start = self.page() * GridStrip.PAGE
            shown = rows[start:start + GridStrip.PAGE]
            heading = f"Pool {start + 1}–{start + len(shown)} of {len(rows)}" if shown else "Pool · 0 players"
            gap, cursor = False, self.cursor["pool"] - start
        self.strip.show_rows(heading, [(r["role"], r["line"], full_name(self.model, r["id"])
                                       if r["id"] is not None else "Empty place") for r in shown],
                             cursor, gap)
        self.squad_button.text.setText(f"Squad ({self.capacity()})")
        self.size_button.set_text(f"Size {self.capacity()}")
        self.squad_button.set_on(self.side == "squad")
        self.pool_button.set_on(self.side == "pool")
        # [designed: #862] The card belongs to the current selection, even after filtering.
        self.card.setVisible(word is not None)
        if word is None:
            self.card.card = None
        else:
            player = (self.model.card(word) if getattr(self.model, 'held_prematch', False)
                      else card(self.model.state, word, self.model.goaldat))
            self.card.set_card(player)
            # [designed: #862] Call out injury, suspension and dismissal on the card.
            unavailable = player["readiness"] in ("injured", "suspended", "sent off")
            colour(self.card.readiness, theme.BAD if unavailable else theme.TEXT_BRIGHT)
        self._show_filters(rows)
        if self._assistant_token is not None:
            self.message = self.assistant_wait()
        if getattr(self.model, 'held_block_reason', ''):
            self.message = self.model.held_block_reason
        idle = ASSISTANT_IDLE if self.capacity() == 20 else "A: choose twenty and fill the extra places."
        if expanded and word is None:
            idle = "Enter: choose a player from the pool. A: ask your assistant."
        self.note.setText(self.message or (idle if self.side == 'squad' else
                                          'Left: show your squad for the assistant.'))
        if self.picked is not None and self.picked[0] == "vacancy" and self._assistant_token is None:
            self.wait_for("Fill empty place", "Enter on a pool player to select him.")
        elif self.picked is not None and self._assistant_token is None:
            detail = ("Enter on another squad player swaps them; → to the pool, then Enter on the player "
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
        if self._assistant_token is not None:
            return "Please wait"
        if self.searching:
            return "Keep search"
        if self.editing:
            return "Give this name"
        if (self.picked is None and getattr(self, "side", None) == "squad"
                and self.capacity() != 20 and self.current() is None):
            return "Fill place"
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
        """A click on a row moves the cursor there; on the highlighted row it is Enter. While the name line is open
        the cursor stays on the player being renamed, as ↑↓ do (the click would hand the name to another player)."""
        if self.editing:
            return None
        position = index + (self.page() * GridStrip.PAGE if self.side == "pool" else 0)
        if position == self.cursor[self.side]:
            return self.press_enter()
        self.cursor[self.side] = position
        self.message = ""
        self.refresh()

    def press_move(self):
        """Enter: pick a player, or put the picked one in place of this one (the model's exchange)."""
        if getattr(self.model, 'held_block_reason', ''):
            return self.say(self.model.held_block_reason)
        if self._assistant_blocked():
            return
        row = self.current_row()
        if row is None:
            return None
        word = row["id"]
        if word is None:
            slot = row["extra_slot"]
            if self.picked is not None and self.picked[0] == "pool":
                return self.fill_place(slot, self.picked[1])
            self.picked = ("vacancy", slot)
            return self.show_side("pool")
        if self.picked is not None and self.picked[0] == "vacancy":
            if self.side == "pool":
                return self.fill_place(self.picked[1], word)
            self.picked = None
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

    def fill_place(self, slot, word):
        try:
            self.model.fill_extra(slot, word)
        except ValueError as exc:
            return self.say(str(exc))
        self.picked = None
        self.side = "squad"
        self.cursor["squad"] = 20 + slot
        return self.say("Extra place filled.")

    # The pool's search and position filter. [designed: owner, §6 item 18; T177]
    def open_search(self):
        """/: the pool, with the search line open."""
        if self._assistant_blocked():
            return
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
        if self._assistant_blocked() or self.editing or self.searching:
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
        if self._assistant_blocked():
            return
        if self.editing or self.searching:
            return self.say("Finish the entry with Enter or Esc first.")
        # [confirmed: E44F E772..E788] Ins acts from the squad pane only.
        if self.side != 'squad':
            return self.say("Left: show your squad, then A for the assistant.")
        try:
            self._assistant_jobs = self.model.assistant_jobs()
            self._assistant_token = self._assistant_jobs.start()
        except ValueError as exc:
            if getattr(self.model, 'held_prematch', False):
                return self.say(str(exc))
            return self.say("The assistant is not available right now.\nFinish the current action, then try again.")
        self.say(self.assistant_wait())
        self._assistant_timer.start()

    def _assistant_blocked(self):
        if self._assistant_token is not None:
            self.say(self.assistant_wait())
            return True
        return False

    def assistant_wait(self):
        if self.capacity() == 20:
            return ASSISTANT_WAIT
        return f"The assistant is choosing your {self.capacity()}-place squad.\nEsc: cancel and return to desk."

    def _poll_assistant(self):
        from goal2.game.best_twenty_jobs import AssistantStale
        try:
            result = self._assistant_jobs.poll(self._assistant_token)
        except AssistantStale:
            result = {'status':'stale'}
        except ValueError:
            result = {'status':'error','reason':'failed'}
        if result is None:
            return
        self._assistant_timer.stop()
        self._assistant_token = None
        status = result['status']
        if status == 'complete':
            self.picked = None
            count = result['recruited']
            message = (f"Recruited {count} player{'s' if count != 1 else ''}.\nReview your twenty before playing."
                       if count else "No stronger players found.\nYour twenty is ready to review.")
            if 'extra_filled' in result:
                message=(f"Filled {result['extra_filled']} of {result['capacity']-20} extra places.\n"
                         f"Review your {result['capacity']} squad places before playing.")
        elif status == 'refused':
            message = { 'finals': 'Cannot alter squad during finals.',
                        'tour': 'Cannot alter squad whilst on tour.' }.get(result['reason'], 'The assistant could not select a squad.')
        elif status == 'cancelled':
            message = 'Assistant selection cancelled.'
        elif status == 'stale':
            message = 'Your career changed.\nAsk the assistant again.'
        elif result.get('reason') == 'unavailable':
            message = ASSISTANT_UNAVAILABLE
        else:
            message = 'The assistant could not finish.\nYour selection is unchanged; try again.'
        self.say(message)

    def stop_assistant(self, *, close=False):
        """[designed: T183c] No late reply may outlive this view/career/window."""
        pending = self._assistant_token is not None
        self._assistant_timer.stop()
        if self._assistant_jobs is not None:
            if self._assistant_token is not None:
                self._assistant_jobs.cancel(self._assistant_token)
            if close:
                self._assistant_jobs.close()
        self._assistant_token = None
        if pending:
            self.message = 'Assistant selection cancelled.'
            self.refresh()

    def escape(self):
        self.stop_assistant()
        return super().escape()

    def edit(self, change):
        if self._assistant_blocked():
            return
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
        if self._assistant_blocked():
            return
        from goal2.ui.s09_player_tactics import PlayerTacticsScreen
        word = self.current()
        if word is not None:
            self.window_.push(PlayerTacticsScreen(self.window_, self.model, word,
                bench=self.model if getattr(self.model, 'held_prematch', False) else None))

    def new_name(self):
        if self._assistant_blocked():
            return
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


def open_squad(window, model, *, back=None):
    """Push S08 over the current screen; T164 calls it from the desk."""
    return window.push(SquadScreen(window, model, **({'back': back} if back is not None else {})))
