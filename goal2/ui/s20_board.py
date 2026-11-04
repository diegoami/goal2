"""S20 Match board: the statistics at half time, before extra time and at full time.

[designed: owner, 2026-11-03, #526; docs/design/ui-2026-11 S20 and its mockup s20-board.html; T167, #541]
[confirmed: T156-R1 steps 118-119, 191-192, 270, 310; t156-119-halftime-board.png, t156-192-fulltime-board.png,
t156-270-quick-halftime.png, t156-310-quick-fulltime.png]

Everything shown is what the bridge's events and outcome give (`board`); nothing is invented:

- the score, the half-time score, each side's scorers and minutes (the `goal` events);
- at full time the original's board as the engine read it at the final whistle (the `full_time` event: its nine
  counters, the two bar rows and the man of the match) [confirmed: the kit's `Match._board`, STAT_NAMES, F014];
- at half time the engine reads no board: bookings and red cards are counted from the events (`booking`,
  `sending_off`) [derived], and the other counters say that the route has them at full time only;
- the bar rows are the board's raw words, labelled as the original labels them [confirmed: F026 at 1bd066ca:
  "possession" and "territory" are the board's labels, not a decoded quantity; how the bar scales them is not
  decoded], so no percentage is made up;
- after a quick result (R on S17, or N to the watch question) a QUICK RESULT banner stands in place of the
  statistics, the scorers kept, as in the original (t156-270, t156-310).

The home side is named first (`DesktopModel.home`, #562), each name in its side's kit (#583). **Enter** continues (to S15); **Esc**
the bench (S19) in *make substitutions now* mode, at half time and before extra time [confirmed: T156-R1 step 119,
"Esc,◄┘-bench"; designed: T180]: its Esc returns to S15, whose *play* sends the bench's answer. At full time, and on
the board S15's *match stats* opens, there is no bench: Esc continues as Enter does.
"""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QHBoxLayout

from goal2.ui import theme
from goal2.ui.pitch import HOME
from goal2.ui.screen import Screen, label, para
from goal2.ui.squad_card import Row, box, colour, full_name

# The design's nine counters, in the original board's order. [confirmed: the kit's STAT_NAMES; s20-board.html]
COUNTERS = (("corners", "corners"), ("free_kicks", "free kicks"), ("penalties", "penalties"), ("shots", "shots"),
            ("on_target", "on target"), ("saves", "saves"), ("fouls", "fouls"), ("bookings", "bookings"),
            ("red_cards", "red cards"))
EVENT_COUNTERS = {"bookings": "booking", "red_cards": "sending_off"}   # counted from the events at half time
TIMES = {"half": "HALF TIME", "extra": "EXTRA TIME", "full": "FULL TIME"}
NOT_YET = "at full time"   # what a counter the route has only at the final whistle says before it [designed: T167]


def board(events, phase, quick):
    """The board's data from the events shown (dicts with kind, minute, score, data): {'score' [team 0, team 1],
    'half_time' (or None), 'scorers' [[(name, minute)] per team], 'counters' {name: [t0, t1] or None},
    'bars' [[t0, t1], [t0, t1]] or None, 'man_of_the_match' (word or None), 'quick'}."""
    score = list(events[-1]["score"]) if events else [0, 0]
    half = next((list(e["score"]) for e in events if e["kind"] == "half_time"), None)
    scorers = [[], []]
    for e in events:
        # [confirmed: the kit's Match._flush] a goal taken back is a `goal` event with no scorer row (player 0)
        if e["kind"] == "goal" and e["data"].get("player"):
            scorers[e["data"]["team"]].append((e["data"].get("player"), e["minute"]))
    full = next((e["data"] for e in events if e["kind"] == "full_time"), None) if phase == "full" else None
    counters = {}
    for key, _ in COUNTERS:
        if full is not None:
            counters[key] = list(full["statistics"][key])
        elif key in EVENT_COUNTERS:
            counters[key] = [sum(1 for e in events if e["kind"] == EVENT_COUNTERS[key] and e["data"].get("team") == t)
                             for t in (0, 1)]
        else:
            counters[key] = None
    if full is not None:
        score = list(full["final_score"]) if phase == "full" else score
    return {"score": score, "half_time": half, "scorers": scorers, "counters": counters,
            "bars": [list(b) for b in full["bars"]] if full is not None else None,
            "man_of_the_match": full["man_of_the_match"] if full is not None else None, "quick": quick}


class BoardScreen(Screen):
    escape_text = "bench"

    def __init__(self, window, model, names, kind, phase, data, onward, kits, bench=None, save_summary=False):
        """`names`: the countries as [team 0, team 1]; `kind`: FRIENDLY, QUALIFYING…; `phase`: half, extra, full;
        `kits`: the match's kits (goal2/ui/kits.py), each name in its side's shirt, as the original's board
        [confirmed: t156-192-fulltime-board.png, Norway light red and Holland white; #583]; `bench`: what Esc opens
        (S19), None where there is no bench (Esc then continues)."""
        self.escape_text = "bench" if bench is not None else "continue"
        super().__init__(window)
        self.model, self.data, self.onward, self.phase, self.bench = model, data, onward, phase, bench
        self.countries, self.kind, self.kits = list(names), kind, kits
        self.save_summary = save_summary
        home, away = HOME, 1 - HOME
        self.title = f"{names[home]} v {names[away]} · {TIMES[phase].lower()}"
        self.name_label.setText(self.title)
        self.set_enter("Continue", self.go_on)
        head, inner = box(None)
        row = QHBoxLayout()
        row.setSpacing(24)
        inner.addLayout(row)
        first = label(names[home], "h1")
        colour(first, kits.colour(home))
        row.addWidget(first)
        score = data["score"]
        self.score_label = label(f"{score[home]}  {score[away]}", "h1")
        row.addWidget(self.score_label)
        second = label(names[away], "h1")
        colour(second, kits.colour(away))
        row.addWidget(second)
        row.addWidget(label(TIMES[phase], "h1"))
        half = data["half_time"]
        detail = (f"half time {half[home]}:{half[away]} · " if half is not None and phase != "half" else "") + kind
        row.addWidget(label(detail, "sub"))
        row.addStretch(1)
        motm = data["man_of_the_match"]
        motm_name = data['motm_name'] if 'motm_name' in data else full_name(model, motm) if motm else ''
        self.motm = label(f"MAN OF THE MATCH {motm_name}" if motm_name else "", "value")
        colour(self.motm, theme.VALUE)
        row.addWidget(self.motm)
        self.body_layout.addWidget(head)
        middle = QHBoxLayout()
        middle.setSpacing(18)
        self.scorer_texts = []
        scorer_boxes = []
        for team in (home, away):
            frame, column = box(f"{names[team]} scorers")
            frame.setFixedWidth(300)
            frozen = data.get('scorer_names')
            lines = [f"{frozen[team][i] if frozen is not None else full_name(model, w) if w else '?'} {m}′"
                     for i, (w, m) in enumerate(data['scorers'][team])] or ['—']
            self.scorer_texts.append(lines)
            for line in lines:
                column.addWidget(label(line, "value"))
            column.addStretch(1)
            scorer_boxes.append(frame)
        stats, column = box("Match statistics")
        self.stat_rows = []
        if data["quick"]:
            banner = label("QUICK RESULT", "h1")
            banner.setAlignment(Qt.AlignmentFlag.AlignCenter)
            colour(banner, theme.KEY_HINT)
            column.addStretch(1)
            column.addWidget(banner)
            column.addStretch(1)
            self.banner = banner
        else:
            self.banner = None
            heading = Row(-1, (220, 0, 220))
            heading.set((names[home], "", names[away]), (theme.HEADING,) * 3)
            column.addWidget(heading)
            for key, text in COUNTERS:
                values = data["counters"][key]
                line = Row(-1, (220, 0, 220), underline=True)
                if values is None:
                    line.set((NOT_YET, text, NOT_YET), (theme.TEXT_NORMAL, theme.TEXT_NORMAL, theme.TEXT_NORMAL))
                else:
                    line.set((str(values[home]), text, str(values[away])),
                             (theme.TEXT_BRIGHT, theme.TEXT_NORMAL, theme.TEXT_BRIGHT))
                for cell in line.cells:
                    cell.setAlignment(Qt.AlignmentFlag.AlignCenter)
                line.setCursor(Qt.CursorShape.ArrowCursor)
                column.addWidget(line)
                self.stat_rows.append(tuple(line.texts()))
            bars = data["bars"]
            for name, values in zip(("possession", "territory"), bars or (None, None)):
                text = (f"{name}: {values[home]} · {values[away]} (the board's counts; its bar is not decoded)"
                        if values is not None else f"{name}: {NOT_YET}")
                column.addWidget(label(text, "sub"))
            column.addStretch(1)
        middle.addWidget(scorer_boxes[0])
        middle.addWidget(stats, 1)
        middle.addWidget(scorer_boxes[1])
        self.body_layout.addLayout(middle, 1)
        self.note = para("", "sub")
        self.body_layout.addWidget(self.note)
        if save_summary:
            from goal2.ui.screen import set_para
            set_para(self.note, 'Do you want to save the match summary? (Y/N)')
            self.bind((Qt.Key.Key_Y,), 'save summary', self.save_board)
            self.bind((Qt.Key.Key_N,), 'continue', self.without_saving)
            self.set_enter('Answer Y or N', self.go_on)

    def without_saving(self):
        self.save_summary = False
        return self.onward(None)

    def save_board(self):
        if self.save_summary:
            from goal2.ui.replays import name_recording, summary_data
            return name_recording(self.window_, self, 'summary', summary_data(self), self.without_saving)

    def go_on(self):
        if not self.save_summary:
            return self.onward(None)

    def escape(self):
        """Esc: the bench (S19), else continue."""
        if self.save_summary:
            return self.without_saving()
        if self.bench is not None:
            return self.bench()
        return self.onward(None)
