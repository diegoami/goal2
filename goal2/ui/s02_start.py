"""S02 Start: continue the newest save, load another, or start a new game.

[designed: owner, 2026-11-03, #526; docs/design/ui-2026-11, S02 and its mockup s02-start.html; T163, #537] The
title's question, *load a saved game?*, with the obvious answer first:
- *Continue* (Enter) opens the newest save [owner decision 4];
- the saved games, by the free names they were saved under [owner decision 8], each with its country, year and stage,
  next match and the time it was saved, read through the model's validating loader (goal2/ui/saves.py);
- **Y** loads the highlighted save, **N** starts a new game (S03), ↑↓ choose a save, Esc quits;
- a save that cannot be opened says why on this screen, with **Y** try again and **N** back, as the original's
  "file not found · try again? (Y/N)" [confirmed: T156-R1 steps 242–244; E031 C11–C12; E015-r0008 state 10];
- with no save, only *New game*.
The saves live in the data root's `saves` folder (`data_setup.Paths.saves`).

**F**, a standalone friendly between any two countries, outside a career, is a GOAL2 ADDITION the original lacks
[designed: owner, §6 item 18 (docs/design/ui-2026-11, 2026-11-03); T177, #557]: today's *New standalone friendly*
(goal2/ui/friendly.py). The original's title takes only Y and N [confirmed: T156-R1 steps 0, 242–244; E031 C11–C12],
so F changes no key's meaning. It is the menu's last item, under the addition's tag; the friendly returns here with
its result on this screen, and nothing is saved.
"""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QHBoxLayout, QVBoxLayout, QWidget

from goal2.desktop.model import STAGES, campaign_year
from goal2.ui import saves
from goal2.ui.screen import Screen, kbd, label, para, set_para
from goal2.ui.start_look import KeyItem, Row, box, key_value, refresh

COLUMNS = (("Name", 300), ("Country", 130), ("Year · stage", 360), ("Next", 240), ("Saved", None))
VISIBLE = 5   # [designed: T163] rows of the list shown at once; the window of rows follows the highlight
WIDTH = 1360  # [designed: owner #598] complete save metadata at 24px


def year_stage(model) -> str:
    """'2028 · Continental qualifying', from the model's own year and stage words."""
    campaign = model.state.campaign
    if campaign is None:
        return "friendly"
    return f"{campaign_year(campaign)} · {STAGES[campaign.stage]}"


class StartScreen(Screen):
    title = "title"
    pre_game = True
    escape_text = "quit"

    def __init__(self, window):
        super().__init__(window)
        self.target = window.target
        self.entries = []
        self.cursor_row = 0
        self.top = 0
        self.failed = None   # the entry whose opening failed: the screen asks Y try again / N back
        self.y = self.bind((Qt.Key.Key_Y,), "load a saved game", self.press_y)
        self.n = self.bind((Qt.Key.Key_N,), "new game", self.press_n)
        self.f = self.bind((Qt.Key.Key_F,), "friendly", self.press_f)   # [designed: owner, §6 item 18; T177]
        self.bind((Qt.Key.Key_Up,), "", lambda: self.move(-1), shown=False)
        self.bind((Qt.Key.Key_Down,), "", lambda: self.move(1), shown=False)
        self.choose_binding = self.bind((), "choose save", None, captions=("↑", "↓"))
        # Esc last on the bar, as the mockup lists it.
        esc = next(b for b in self.bindings if Qt.Key.Key_Escape in b.keys)
        self.bindings.remove(esc)
        self.bindings.append(esc)
        self._refresh_bar()
        self._build()
        self.read()

    # The screen.
    def _build(self):
        column = QWidget()
        column.setFixedWidth(WIDTH)
        layout = QVBoxLayout(column)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(18)
        head = QVBoxLayout()
        head.setSpacing(4)
        head.addWidget(label("GOAL2", "titleBrand"), 0, Qt.AlignmentFlag.AlignHCenter)
        head.addWidget(label("the 1993 international management game · version 2", "sub"), 0,
                       Qt.AlignmentFlag.AlignHCenter)
        layout.addLayout(head)
        top = QHBoxLayout()
        top.setSpacing(18)
        self.continue_box, inner = box("Continue")
        self.continue_item = QFrame()
        self.continue_item.setObjectName("primary")
        self.continue_item.setCursor(Qt.CursorShape.PointingHandCursor)
        row = QHBoxLayout(self.continue_item)
        row.setContentsMargins(18, 16, 18, 16)
        row.setSpacing(12)
        self.continue_text = para("", "primaryText")
        row.addWidget(self.continue_text, 1)
        row.addWidget(kbd("Enter"), 0, Qt.AlignmentFlag.AlignVCenter)
        self.continue_item.mouseReleaseEvent = lambda event: self.press_enter()
        inner.addWidget(self.continue_item)
        inner.addSpacing(6)
        facts, self.facts = key_value((("manager", "manager"), ("next", "next"), ("saved", "saved")))
        inner.addWidget(facts)
        inner.addStretch(1)
        top.addWidget(self.continue_box, 1)
        self.menu_box, menu = box("Load a saved game?")
        self.menu_box.setFixedWidth(400)
        self.load_item = KeyItem("Load another save", "Y", self.press_y)
        self.new_item = KeyItem("New game", "N", self.press_n)
        self.quit_item = KeyItem("Quit", "Esc", self.escape)
        for item in (self.load_item, self.new_item, self.quit_item):
            menu.addWidget(item)
        # [designed: owner, §6 item 18; T177] the standalone friendly, under the addition's tag
        menu.addSpacing(6)
        tag = QHBoxLayout()
        tag.addWidget(label("GOAL2 ADDITION", "tagNew"))
        tag.addStretch(1)
        menu.addLayout(tag)
        self.friendly_item = KeyItem("Standalone friendly", "F", self.press_f)
        menu.addWidget(self.friendly_item)
        menu.addStretch(1)
        top.addWidget(self.menu_box)
        layout.addLayout(top)
        self.list_box, inner = box("Saved games")
        heads = Row([w for _, w in COLUMNS])
        heads.set_cells([h.upper() for h, _ in COLUMNS], ["boxHeading"] * len(COLUMNS))
        heads.setCursor(Qt.CursorShape.ArrowCursor)
        inner.addWidget(heads)
        self.rows = []
        for i in range(VISIBLE):
            r = Row([w for _, w in COLUMNS], on_click=lambda i=i: self.click_row(i))
            r.cells[1].setWordWrap(True)
            inner.addWidget(r)
            self.rows.append(r)
        self.message = para("", "sub")   # what came back to the title: the standalone friendly's result [T177]
        self.message.hide()
        layout.addWidget(self.message)
        self.problem = para("", "error")
        self.problem.setMinimumWidth(WIDTH - 34)
        inner.addWidget(self.problem)
        layout.addWidget(self.list_box)
        outer = QHBoxLayout()
        outer.addStretch(1)
        outer.addWidget(column)
        outer.addStretch(1)
        self.body_layout.addStretch(1)
        self.body_layout.addLayout(outer)
        self.body_layout.addStretch(1)

    def read(self):
        """Read every save again, newest first, and show them."""
        self.entries = saves.entries(self.target.saves, self.target.goal_dat)
        self.cursor_row = min(self.cursor_row, max(0, len(self.entries) - 1))
        self.failed = None
        self._show()

    def newest(self):
        """The newest save that opens: what Continue opens."""
        return next((e for e in self.entries if e.model is not None), None)

    def _show(self):
        has = bool(self.entries)
        newest = self.newest()
        self.continue_box.setVisible(newest is not None)
        self.list_box.setVisible(has)
        self.load_item.setVisible(has)
        self.y.shown = has
        self.choose_binding.shown = has and len(self.entries) > 1
        if newest is not None:
            summary = newest.model.summary()
            set_para(self.continue_text, f"Continue {summary['country']}, {year_stage(newest.model)}")
            self.facts["manager"].setText(newest.model.manager)
            self.facts["next"].setText(summary["next"])
            self.facts["saved"].setText(f"“{newest.name}” · {saves.when(newest.saved)}")
        if self.failed is not None:
            self.y.text, self.n.text = "try again", "back"
            set_para(self.problem, f"“{self.failed.name}” cannot be opened: {self.failed.error}\n"
                                   "Y: try again · N: back to the list")
            self.enter_action = None
        else:
            self.y.text, self.n.text = "load a saved game", "new game"
            set_para(self.problem, "")
            if newest is not None:
                self.set_enter("Continue", self.do_continue)
            else:
                self.set_enter("New game", self.press_n)
        self.problem.setVisible(self.failed is not None)
        self._show_rows()
        self._refresh_bar()

    def _show_rows(self):
        if self.cursor_row < self.top:
            self.top = self.cursor_row
        elif self.cursor_row >= self.top + VISIBLE:
            self.top = self.cursor_row - VISIBLE + 1
        for i, row in enumerate(self.rows):
            index = self.top + i
            if index >= len(self.entries):
                row.hide()
                continue
            entry = self.entries[index]
            if entry.model is not None:
                summary = entry.model.summary()
                row.set_cells([entry.name, summary["country"], year_stage(entry.model), summary["next"],
                               saves.when(entry.saved)])
            else:
                row.set_cells([entry.name, "cannot be opened", "", "", saves.when(entry.saved)],
                              [None, "bad", None, None, None])
            row.set_on(index == self.cursor_row)
            row.show()

    # The keys.
    def move(self, step):
        if self.failed is None and self.entries:
            self.cursor_row = max(0, min(self.cursor_row + step, len(self.entries) - 1))
            self._show_rows()

    def click_row(self, i):
        """A click on a save highlights it, as ↑↓ do."""
        if self.failed is None and self.top + i < len(self.entries):
            self.cursor_row = self.top + i
            self._show_rows()

    def highlighted_entry(self):
        return self.entries[self.cursor_row] if self.entries else None

    def press_y(self):
        if self.failed is not None:
            return self.open_entry(self.failed)   # try again
        entry = self.highlighted_entry()
        return self.open_entry(entry) if entry is not None else None

    def press_f(self):
        """F: the standalone friendly's country choice (goal2/ui/friendly.py). [designed: owner, §6 item 18; T177]"""
        if self.failed is not None:
            return None
        from goal2.ui.friendly import open_friendly
        return open_friendly(self.window_)

    def say(self, text):
        """A line under the title's boxes: what a standalone friendly ended with (S17's result line)."""
        set_para(self.message, text)
        self.message.setVisible(bool(text))

    def press_n(self):
        if self.failed is not None:
            self.read()                           # back to the list, read again
            return None
        from goal2.ui.s03_new_game import NewGameScreen
        return self.window_.push(NewGameScreen(self.window_))

    def do_continue(self):
        newest = self.newest()
        return self.open_entry(newest) if newest is not None else None

    def open_entry(self, entry):
        """Open `entry`'s career, read again at the moment of opening; a save that fails says why here."""
        try:
            model = saves.load(entry.path, self.target.goal_dat)
        except saves.SaveError as exc:
            entry.error, entry.model = str(exc), None
            self.failed = entry
            self._show()
            return None
        self.failed = None
        return self.window_.open_career(model)

    def escape(self):
        """Esc quits: S02 is the title. [designed: docs/design/ui-2026-11, S02: "Esc quit"]"""
        if self.failed is not None:
            self.press_n()
            return
        self.window_.close()

    def shown(self):
        refresh(self)
