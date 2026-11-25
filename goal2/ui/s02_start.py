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
so F changes no key's meaning. It remains a secondary action; the friendly returns here with
its result on this screen, and nothing is saved.
"""
from __future__ import annotations

from PySide6.QtCore import Qt

from goal2.desktop.model import STAGES, campaign_year
from goal2.ui import saves, theme
from goal2.ui.screen import Screen, set_para
from goal2.ui.start_look import refresh

COLUMNS = (("Name", 18), ("Country", 16), ("Year · stage", 24), ("Next", 16), ("Saved", 16))
VISIBLE = 5   # [designed: T163] rows of the list shown at once; the window of rows follows the highlight


def year_stage(model) -> str:
    """'2028 · Continental qualifying', from the model's own year and stage words."""
    campaign = model.state.campaign
    if campaign is None:
        return "friendly"
    return f"{campaign_year(campaign)} · {STAGES[campaign.stage]}"


class StartScreen(Screen):
    GRID = True   # [designed: owner, #667; T214]
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
        self.esc = next(b for b in self.bindings if Qt.Key.Key_Escape in b.keys)
        self.bindings.remove(self.esc)
        self.bindings.append(self.esc)
        self._refresh_bar()
        self._build()
        self.read()

    # The screen.
    def _build(self):
        """[designed: #862; confirmed: T156-R1 step 0] Keep the title's choice near the foot."""
        from goal2.ui.cells import Cells, CellPara
        from goal2.ui.cell_parts import CellKeyItem, CellTableRow
        from goal2.ui.country_parts import framed
        from goal2.ui.frame import PanelOutline
        from goal2.ui import theme
        body = self.area = Cells(90, 25, "startBody")
        self.body_layout.addWidget(body, 1)
        banner = self.banner = Cells(90, 1, "startBanner")
        subtitle = banner.text("International football management", "titleBrand", 0, 0, 90)
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)

        def rules():
            right, bottom = banner.width() - 1, banner.height() - 1
            return ((0, 0, right, 0), (0, bottom, right, bottom))

        banner.grid.addWidget(PanelOutline(banner, rules))
        body.put(banner, 0, 0, 90)
        self.continue_box, inner = framed("continue", 90, 6)
        self.continue_item = CellKeyItem("", "Enter", self.press_enter, 90, rows=2, primary=True)
        self.continue_text=self.continue_item.text_label
        inner.put(self.continue_item, 0, 0, 90, 2)
        self.facts={}
        for name,row,rows in (("manager",2,1),("next",3,1),("saved",4,2)):
            inner.text(name,"cardLabel",0,row,7)
            value=CellPara("","value")
            value.setTextFormat(Qt.TextFormat.PlainText)
            inner.put(value, 8, row, 82, rows)
            self.facts[name]=value
        body.put(self.continue_box, 0, 1, 90, 7)
        self.menu_box, menu = framed("load a saved game?", 90, 2)
        self.new_item = CellKeyItem("New game", "N", self.press_n, 42, primary=True)
        self.load_item = CellKeyItem("Load selected save", "Y", self.press_y, 42)
        self.empty_load = menu.text("No saved careers", "sub", 47, 0, 42)
        self.friendly_item = CellKeyItem("Standalone friendly", "F", self.press_f, 42)
        self.quit_item = CellKeyItem("Quit", "Esc", self.escape, 42)
        menu.put(self.new_item, 1, 0, 42)
        menu.put(self.load_item, 47, 0, 42)
        menu.put(self.friendly_item, 1, 1, 42)
        menu.put(self.quit_item, 47, 1, 42)
        body.put(self.menu_box, 0, 22, 90, 3)
        self.list_box,inner=framed("saved games",90,11)
        widths=tuple(width for _,width in COLUMNS)
        heads=CellTableRow(-1,widths)
        heads.set_cells([h.lower() for h,_ in COLUMNS],[theme.CARD_LABEL]*5)
        heads.setCursor(Qt.CursorShape.ArrowCursor)
        inner.put(heads,0,0,90)
        self.rows=[]
        for i in range(VISIBLE):
            row=CellTableRow(i,widths,wrap_rows=2,plain=True)
            row.chosen.connect(self.click_row)
            inner.put(row,0,1+2*i,90,2)
            self.rows.append(row)
        body.put(self.list_box,0,8,90,12)
        self.message=CellPara("","sub")
        self.message.hide()
        body.put(self.message, 0, 20, 90, 2)
        self.problem=CellPara("","error")
        body.put(self.problem, 0, 16, 90, 6)

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
        failed = self.failed is not None
        self.area.move(self.banner, 0, 0 if has else 10, 90)
        self.continue_box.setVisible(newest is not None and not failed)
        self.list_box.setVisible(has and not failed)
        self.load_item.setVisible(has or failed)
        self.empty_load.setVisible(not has and not failed)
        self.friendly_item.setVisible(not failed)
        self.quit_item.setVisible(not failed)
        self.y.shown = has or failed
        self.f.shown = not failed
        self.esc.text = "back" if failed else "quit"
        self.choose_binding.shown = len(self.entries) > 1 and not failed
        self.menu_box.set_label("try again?" if failed else "load a saved game?")
        self.new_item.text_label.setText("Back to saves" if failed else "New game")
        self.load_item.text_label.setText("Try again" if failed else "Load selected save")
        self.new_item.setProperty("on", newest is None and not failed)
        refresh(self.new_item)
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
        self.problem.setVisible(failed)
        self.message.setVisible(not failed and bool(self.message.text()))
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
                              [theme.TEXT_BRIGHT, theme.BAD, theme.TEXT_BRIGHT, theme.TEXT_BRIGHT, theme.TEXT_BRIGHT])
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
        self.message.setVisible(bool(text) and self.failed is None)

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
