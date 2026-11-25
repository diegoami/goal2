"""S14 Round results: the round's other results, arriving one by one, before and after your match.

[designed: owner, 2026-11-03, #526; docs/design/ui-2026-11 S14 and its mockup s14-round.html; T167, #541]
[confirmed: T156-R1 steps 41, 262-263, t156-041-round1-results.png, t156-262-round2-results-rolling.png]

- **Before your match** the rows are the results the route resolves before it (`DesktopModel.round_before`, the
  publication's own `silent_until_managed`), each with its kind; your match is listed last, still to play.
- **After your match** (*exit* on S15 at full time) your result stands where your match was, and the results the
  route resolved after it until the round ends arrive (`DesktopModel.round_after`).
- Each row names the home side first, as the original's results page [derived: DesktopModel.home, #562;
  t156-041-round1-results.png "Luxembourg 0v1 Cyprus"].
- **Keys**: **Space** pauses the arrival, **←→** change its pace, **Enter** goes to your match (before) or to the
  desk (after). The original's "hit any key" is Enter here, as the design's bar says [designed: s14-round.html].
  The pace is goal2's [designed: T167; the original's own pace is not measured]: `PACES`, slowest first.
"""
from __future__ import annotations

from PySide6.QtCore import Qt, QTimer

from goal2.ui import theme
from goal2.ui.cell_parts import CellTableRow
from goal2.ui.cells import CellPara, Cells
from goal2.ui.frame import PanelOutline
from goal2.ui.screen import Screen
from goal2.ui.squad_card import colour

PACES = (1600, 1000, 600, 300, 120)   # ms between two results [designed: T167]
PACE = 2                              # the pace a round opens at [designed: T167]
ROWS = 16                             # established history limit before the managed fixture
ROW_WIDTHS = (16, 9, 16, 33)           # reserves the full competition name on an ordinary row
ROW_COLS = sum(ROW_WIDTHS)
PANEL_COLS = ROW_COLS + 4
PANEL_ROWS = ROWS + 5                  # two margins and room for the wrapped managed result


def score_text(row):
    return "v" if row["score"] is None else f"{row['score'][0]} - {row['score'][1]}"


class RoundScreen(Screen):
    """`before`: DesktopModel.round_before(); `after`: round_after(your fixture) once your match is published.
    `onward` is what Enter does."""
    GRID = True   # [designed: owner, #667; T213]
    escape_text = None

    def __init__(self, window, before, onward, after=None):
        super().__init__(window)
        self.onward = onward
        self.after = after
        number = (after or before)["round"]
        self.title = f"round {number} · results"
        self.name_label.setText(self.title)
        if after is None:
            self.settled = []
            self.arriving = list(before["results"])
            self.mine = dict(before["match"], note="your match is next")
        else:
            # your result where your match was, the rest of the round arriving after it
            mine = dict(after["match"], note="your match")
            self.settled = (list(before["results"]) if before is not None else []) + [mine]
            self.arriving = list(after["results"])
            self.mine = None
        self.shown_rows = list(self.settled)
        self.paused = False
        self.pace = PACE
        self.pause_key = self.bind((Qt.Key.Key_Space,), "pause", self.toggle_pause)
        self.bind((Qt.Key.Key_Left,), "", lambda: self.step_pace(-1), captions=("←",), shown=False)
        self.bind((Qt.Key.Key_Right,), "", lambda: self.step_pace(1), captions=("→",), shown=False)
        self.speed_key = self.bind((), "speed", lambda: self.step_pace(1), captions=("←", "→"))
        self.set_enter("To your match" if after is None else "To the desk", self.go_on)
        # [derived: T156-R1 steps 41, 262–263] Center the cyan results frame and keep completion at the foot.
        body = Cells(theme.COLS, theme.ROWS - 3, "roundBody")
        self.body_layout.addWidget(body, 1)
        panel = self.results_area = Cells(PANEL_COLS, PANEL_ROWS, "roundResults")
        body.put(panel, (body.cols - PANEL_COLS) // 2, 2, PANEL_COLS, PANEL_ROWS)
        self.rows = []
        for i in range(ROWS + 1):
            row = CellTableRow(i, ROW_WIDTHS,
                               aligns=(Qt.AlignmentFlag.AlignRight, Qt.AlignmentFlag.AlignHCenter, None, None))
            # The managed row also carries a note, which can wrap below the fixture type.
            old = row.cells[3]
            text = CellPara("", "rowCell")
            row.area.layout().takeAt(3)
            old.setParent(None)
            old.deleteLater()
            row.area.put(text, ROW_COLS - ROW_WIDTHS[-1], 0, ROW_WIDTHS[-1])
            row.cells[3] = text
            row.setCursor(Qt.CursorShape.ArrowCursor)
            panel.put(row, 2, i + 1, ROW_COLS)
            self.rows.append(row)
        panel.grid.addWidget(PanelOutline(panel, self._result_edges, colour=theme.HEADING))
        self.state_label = body.text("", "sub", 0, body.rows - 1, body.cols)
        self.state_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        colour(self.state_label, theme.VALUE)
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.arrive)
        self.timer.setInterval(PACES[self.pace])
        self._show()
        if self.arriving:
            self.timer.start()

    def _result_edges(self):
        right, bottom = self.results_area.width() - 1, self.results_area.height() - 1
        return ((0, 0, right, 0), (0, bottom, right, bottom), (0, 0, 0, bottom), (right, 0, right, bottom))

    def _show(self):
        rows = self.shown_rows[-(ROWS + 1):] if self.mine is None else self.shown_rows[-ROWS:] + [self.mine]
        at = 1
        for i, widget in enumerate(self.rows):
            if i >= len(rows):
                widget.set(("", "", "", ""))
                widget.hide()
                continue
            row = rows[i]
            kind = row["kind_name"]
            tones = (theme.VALUE, theme.TEXT_BRIGHT, theme.VALUE, theme.KEY_HINT)
            if "note" in row:
                kind = f"{kind} · {row['note']}"
                tones = (theme.VALUE,) * 4
            widget.set((row["home_name"], score_text(row), row["away_name"], kind), tones)
            height = 3 if len(kind) > ROW_WIDTHS[-1] else 1
            self.results_area.move(widget, 2, at, ROW_COLS, height)
            widget.area.move(widget.cells[3], ROW_COLS - ROW_WIDTHS[-1], 0, ROW_WIDTHS[-1], height)
            widget.show()
            at += height
        self._show_status()

    def _show_status(self):
        rolling = bool(self.arriving)
        action = "resume" if self.paused else "pause"
        if self.pause_key.shown != rolling or self.pause_key.text != action:
            self.pause_key.shown = self.speed_key.shown = rolling
            self.pause_key.text = action
            self._refresh_bar()
        state = "paused" if self.paused else "results arriving"
        self.state_label.setText(f"{state} · speed {self.pace + 1}/{len(PACES)}" if rolling else "")

    def arrive(self):
        """The next result arrives."""
        if self.paused or not self.arriving:
            return
        self.shown_rows.append(self.arriving.pop(0))
        if not self.arriving:
            self.timer.stop()
        self._show()

    def toggle_pause(self):
        self.paused = not self.paused
        self._show_status()

    def step_pace(self, step):
        self.pace = max(0, min(len(PACES) - 1, self.pace + step))
        self.timer.setInterval(PACES[self.pace])
        self._show_status()

    def visible(self):
        """The rows as they read now, your match last: (home, score, away, kind)."""
        return [tuple(row.texts()) for row in self.rows if not row.isHidden()]

    def go_on(self):
        self.timer.stop()
        return self.onward()
