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
from goal2.ui.screen import Screen
from goal2.ui.squad_card import colour

PACES = (1600, 1000, 600, 300, 120)   # ms between two results [designed: T167]
PACE = 2                              # the pace a round opens at [designed: T167]
ROWS = 16                             # rows the box holds [designed: s14-round.png's box]
HINT = ("The results arrive one by one; Space pauses, ←→ change the pace. Then your match: the match menu, where you "
        "pick the team, choose the captain and kick off.")   # [designed: s14-round.html]


def score_text(row):
    return "v" if row["score"] is None else f"{row['score'][0]} - {row['score'][1]}"


from goal2.ui.cell_parts import CellTableRow


class RoundRow(CellTableRow):
    """[designed: T213, #667] Keep the results table's row separators without a CSS border taking a pixel from its cells."""

    def paintEvent(self, event):
        super().paintEvent(event)
        import math
        from PySide6.QtGui import QColor, QPainter, QPen
        from goal2.desktop import fixed_page
        width = max(1, math.ceil(2 * fixed_page.scale_y_of(self)))
        painter = QPainter(self)
        painter.setPen(QPen(QColor(theme.FRAME_DARK), width))
        y = self.height() - (width + 1) // 2
        painter.drawLine(0, y, self.width(), y)
        painter.end()


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
        self.title = f"play next game · round {number}"
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
        self.bind((Qt.Key.Key_Space,), "pause", self.toggle_pause)
        self.bind((Qt.Key.Key_Left,), "", lambda: self.step_pace(-1), captions=("←",), shown=False)
        self.bind((Qt.Key.Key_Right,), "", lambda: self.step_pace(1), captions=("→",), shown=False)
        self.bind((), "speed", lambda: self.step_pace(1), captions=("←", "→"))
        self.set_enter("To your match" if after is None else "To the desk", self.go_on)
        # [designed: owner, #667; T213] Seventeen results across the page; the final column wraps a long stage and match note.
        from goal2.ui.cells import Cells, CellPara
        from goal2.ui.cell_parts import CellTableRow
        from goal2.ui.country_parts import framed
        body = Cells(90, 25, "roundBody")
        self.body_layout.addWidget(body, 1)
        frame, inner = framed(f"round {number} · the results so far", 90, 19)
        self.results_area = inner
        self.rows = []
        for i in range(ROWS + 1):
            row = RoundRow(i, (16, 9, 16, 49), aligns=(Qt.AlignmentFlag.AlignRight, Qt.AlignmentFlag.AlignHCenter,None,None))
            # The last result may name the stage and "your match is next": it has three rows while ordinary results take one.
            old = row.cells[3]
            text = CellPara("", "rowCell")
            row.area.layout().takeAt(3)
            old.setParent(None)
            old.deleteLater()
            row.area.put(text, 41, 0, 49, 3 if i == ROWS else 1)
            row.cells[3] = text
            row.setCursor(Qt.CursorShape.ArrowCursor)
            inner.put(row, 0, i, 90, 3 if i == ROWS else 1)
            self.rows.append(row)
        body.put(frame, 0, 0, 90, 20)
        hint = CellPara(HINT, "sub")
        hint.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignTop)
        body.put(hint, 0, 21, 90, 3)
        self.state_label = body.text("", "sub", 0, 24, 90)
        colour(self.state_label, theme.VALUE)
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.arrive)
        self.timer.setInterval(PACES[self.pace])
        self._show()
        if self.arriving:
            self.timer.start()

    # What is shown: the newest rows that fit, your match last.
    def _show(self):
        rows = self.shown_rows[-ROWS:] if self.mine is not None else self.shown_rows[-(ROWS + 1):]
        mine = self.mine
        for i, widget in enumerate(self.rows):
            widget.cells[3].setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
            if i < len(rows):
                r = rows[i]
                if "note" in r:
                    widget.cells[3].setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignTop)
                    widget.set((r["home_name"], score_text(r), r["away_name"], f"{r['kind_name']} · {r['note']}"),
                               (theme.VALUE,) * 4)
                else:
                    widget.set((r["home_name"], score_text(r), r["away_name"], r["kind_name"]),
                               (theme.TEXT_BRIGHT, theme.TEXT_BRIGHT, theme.TEXT_BRIGHT, theme.TEXT_NORMAL))
                widget.show()
            elif i == len(rows) and mine is not None:
                widget.cells[3].setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignTop)
                widget.set((mine["home_name"], score_text(mine), mine["away_name"],
                            f"{mine['kind_name']} · {mine['note']}"), (theme.VALUE,) * 4)
                widget.show()
            else:
                widget.set(("", "", "", ""))
                widget.hide()
        at = 0
        for widget in self.rows:
            if widget.isHidden():
                continue
            height = 3 if len(widget.cells[3].text()) > 49 else 1
            self.results_area.move(widget, 0, at, 90, height)
            widget.area.move(widget.cells[3], 41, 0, 49, height)
            at += height
        if self.arriving:
            state = "paused" if self.paused else "the results are arriving"
        else:
            state = "the round is complete" if self.after is not None else "every result before your match is in"
        self.state_label.setText(state)

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
        self._show()

    def step_pace(self, step):
        self.pace = max(0, min(len(PACES) - 1, self.pace + step))
        self.timer.setInterval(PACES[self.pace])

    def visible(self):
        """The rows as they read now, your match last: (home, score, away, kind)."""
        return [tuple(row.texts()) for row in self.rows if not row.isHidden()]

    def go_on(self):
        self.timer.stop()
        return self.onward()
