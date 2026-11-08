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
from PySide6.QtWidgets import QVBoxLayout

from goal2.ui import theme
from goal2.ui.screen import Screen, label, para
from goal2.ui.squad_card import Row, box, colour

PACES = (1600, 1000, 600, 300, 120)   # ms between two results [designed: T167]
PACE = 2                              # the pace a round opens at [designed: T167]
ROWS = 16                             # rows the box holds [designed: s14-round.png's box]
HINT = ("The results arrive one by one; Space pauses, ←→ change the pace. Then your match: the match menu, where you "
        "pick the team, choose the captain and kick off.")   # [designed: s14-round.html]


def score_text(row):
    return "v" if row["score"] is None else f"{row['score'][0]} - {row['score'][1]}"


class RoundScreen(Screen):
    """`before`: DesktopModel.round_before(); `after`: round_after(your fixture) once your match is published.
    `onward` is what Enter does."""
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
        frame, inner = box(f"Round {number} · the results so far")
        inner.setSpacing(0)
        self.rows = []
        for i in range(ROWS + 1):
            row = Row(i, (300, 110, 260, 0), underline=True)
            row.setCursor(Qt.CursorShape.ArrowCursor)
            row.cells[0].setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            row.cells[1].setAlignment(Qt.AlignmentFlag.AlignCenter)
            inner.addWidget(row)
            self.rows.append(row)
        inner.addSpacing(14)
        inner.addWidget(para(HINT, "sub"))
        self.state_label = label("", "sub")
        colour(self.state_label, theme.VALUE)
        inner.addWidget(self.state_label)
        inner.addStretch(1)
        column = QVBoxLayout()
        column.setContentsMargins(140, 0, 140, 0)
        column.addWidget(frame, 1)
        self.body_layout.addLayout(column, 1)
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
            if i < len(rows):
                r = rows[i]
                if "note" in r:
                    widget.set((r["home_name"], score_text(r), r["away_name"], f"{r['kind_name']} · {r['note']}"),
                               (theme.VALUE,) * 4)
                else:
                    widget.set((r["home_name"], score_text(r), r["away_name"], r["kind_name"]),
                               (theme.TEXT_BRIGHT, theme.TEXT_BRIGHT, theme.TEXT_BRIGHT, theme.TEXT_NORMAL))
                widget.show()
            elif i == len(rows) and mine is not None:
                widget.set((mine["home_name"], score_text(mine), mine["away_name"],
                            f"{mine['kind_name']} · {mine['note']}"), (theme.VALUE,) * 4)
                widget.show()
            else:
                widget.set(("", "", "", ""))
                widget.hide()
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
