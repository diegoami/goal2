"""S09 Player tactics: one player's own tactics.

[designed: owner, 2026-11-03, #526; docs/design/ui-2026-11, S09 and its mockup s09-player-tactics.html; T165]
Reached by T from S08. Between matches the original shows four lines here: position, possession, passing and
tackling, each with its value and **P** on a line set for this player [confirmed: F010, `1771:4B61`; F008's tactics
panel]. The fifth line, mark, appears in the original only when a match is set up with an opponent (`1771:49B8`,
F010; goal2-archaeology docs/engine-study/tactics.md), so it comes with the match screens. Arrows choose the line,
Enter alters it through `DesktopModel.own_tactic`, Esc returns to the card. A click on a line moves the cursor to it,
a click on the highlighted line is Enter [designed: T165].
"""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QHBoxLayout, QVBoxLayout

from goal2.ui.screen import Screen, label, para
from goal2.ui.squad_card import (CHARACTERISTIC_CELLS, SKILL_CELLS, Bars, Row, Strip, box, code_label, colour,
                                 full_name, last_on_the_bar, squad_rows, LINE_COLOUR)
from goal2.ui import theme

LINES = ("position", "possession", "passing", "tackling")   # [confirmed: F008, F010: own-tactics rows 1..4]
EXPLAIN = ("Enter steps the highlighted line to its next option. P marks a line set for this player, not by the "
           "team's defaults. The mark line comes with the match screens: the original offers it only when a match "
           "is set up.")


class PlayerTacticsScreen(Screen):
    escape_text = "back to the card"

    def __init__(self, window, model, word):
        self.title = f"select squad · {full_name(model, word)} · tactics"
        super().__init__(window)
        self.model, self.word = model, word
        self.line = 0
        self._build()
        self.bind((Qt.Key.Key_Up,), "", lambda: self.choose(self.line - 1), captions=("",), shown=False)
        self.bind((Qt.Key.Key_Down,), "", lambda: self.choose(self.line + 1), captions=("",), shown=False)
        self.bind((Qt.Key.Key_Left,), "", lambda: self.choose(self.line - 1), captions=("",), shown=False)
        self.bind((Qt.Key.Key_Right,), "", lambda: self.choose(self.line + 1), captions=("",), shown=False)
        self.bind((), "line", None, captions=("↑", "↓", "←", "→"))
        last_on_the_bar(self, self.escape_text)
        self.set_enter("Alter tactic", self.alter)
        self.refresh()

    def _build(self):
        main = QHBoxLayout()
        main.setSpacing(18)
        column = QVBoxLayout()
        column.setSpacing(14)
        head, head_layout = box(margins=(16, 14, 16, 14))
        row = QHBoxLayout()
        row.setSpacing(20)
        self.code = code_label("", "unknown")
        self.name = label("", "h1")
        self.facts = label("", "sub")
        for widget in (self.code, self.name, self.facts):
            row.addWidget(widget, 0, Qt.AlignmentFlag.AlignBaseline)
        row.addStretch(1)
        head_layout.addLayout(row)
        column.addWidget(head)
        boxes = QHBoxLayout()
        boxes.setSpacing(18)
        own, own_layout = box("His own tactics")
        own.setFixedWidth(560)
        own_layout.setSpacing(0)
        own_layout.addSpacing(10)
        self.rows = []
        for i in range(len(LINES)):
            line = Row(i, (210, 0), margins=(8, 6, 8, 6), underline=True)
            line.chosen.connect(self.click)
            own_layout.addWidget(line)
            self.rows.append(line)
        own_layout.addSpacing(14)
        explain = para(EXPLAIN, "sub")
        explain.setMinimumWidth(560 - 2 * 16 - 2)
        own_layout.addWidget(explain)
        own_layout.addStretch(1)
        boxes.addWidget(own)
        right, right_layout = box("Skills")
        from goal2.game.player_card import SKILLS
        self.skills = Bars(SKILLS, word_width=24)
        right_layout.addWidget(self.skills)
        right_layout.addSpacing(4)
        right_layout.addWidget(label("CHARACTERISTICS", "boxHeading"))
        self.characteristics = Bars(("hardness", "fitness", "energy", "morale", "leadership"))
        right_layout.addWidget(self.characteristics)
        right_layout.addStretch(1)
        boxes.addWidget(right, 1)
        column.addLayout(boxes, 1)
        main.addLayout(column, 1)
        self.strip = Strip()
        main.addWidget(self.strip)
        self.body_layout.addLayout(main, 1)

    def card(self):
        from goal2.game.player_card import card
        return card(self.model.state, self.word, self.model.goaldat)

    def refresh(self):
        card = self.card()
        self.code.setText(card["role"])
        colour(self.code, LINE_COLOUR.get(card["line"], theme.TEXT_NORMAL))
        self.name.setText(card["full_name"])
        self.facts.setText(f"{card['position']} · club position {card['club_position']} · {card['readiness']}")
        for line, (name, word, personal) in zip(self.rows, card["tactics"]):
            line.set((name, word + (" P" if personal else "")))
        for i, line in enumerate(self.rows):
            line.set_on(i == self.line)
        for name, value in card["skills"]:
            self.skills.set(name, value, SKILL_CELLS, "" if value is not None else "—")
        for name, word, bar, _raw in card["characteristics"]:
            self.characteristics.set(name, bar, CHARACTERISTIC_CELLS, word)
        rows, eleven = squad_rows(self.model)
        current = next((i for i, r in enumerate(rows) if r["id"] == self.word), -1)
        self.strip.show_rows(self.model.view()["country_name"],
                             [(r["role"], r["line"], full_name(self.model, r["id"])) for r in rows], current,
                             eleven == 11)

    def lines(self):
        """The lines as they read: (line, value with P)."""
        return [tuple(line.texts()) for line in self.rows]

    def choose(self, index):
        self.line = max(0, min(len(LINES) - 1, index))
        self.refresh()

    def click(self, index):
        if index == self.line:
            return self.alter()
        return self.choose(index)

    def alter(self):
        """Enter: the highlighted line one step on, through the model (rows 1..4 are elements 1..4)."""
        self.model.own_tactic(self.word, self.line + 1)
        self.refresh()
