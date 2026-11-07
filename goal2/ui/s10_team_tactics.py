"""S10 Team tactics: the team's eight lines.

[designed: owner, 2026-11-03, #526; docs/design/ui-2026-11, S10 and its mockup s10-team-tactics.html; T165] Each
line with its value now and the other option, in the original's order: defence system, protection, offside, then
the player defaults positioning, possession, passing, tackling and marking [confirmed: F010, the team tactics
screen 1771:1981 lists element DS:6BBF[row]: 5, 6, 7, 1, 2, 3, 4, 8; the words from goal2.game.country_card,
F008]. ↑↓ choose a line; before a match Enter uses `DesktopModel.set_team_tactic`.
[designed: owner #610] At a match stop Enter submits a team-tactics-only original menu edit; the returned
decision confirms the actual flag before further input. Career state is published only at full time. Esc returns. A click on a line
moves the cursor to it, a click on the highlighted line is Enter [designed: T165].

The formation is counted from the eleven's lines [derived: goal2/game/country_card.py; today's Team tactics]. The
characteristics panel says "not decoded yet (G05)" where the Python route has no value, as today's country card
does [designed: T144; main session, 2026-11-03, T165].
"""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QHBoxLayout, QVBoxLayout

from goal2.ui import theme
from goal2.ui.screen import LINE_HEIGHT, Screen, label, para
from goal2.ui.squad_card import (NOT_DECODED, KeyValues, Row, Strip, box, full_name, last_on_the_bar, rich,
                                 squad_rows)

# [confirmed: F010 element order DS:6BBF; the names of goal2.game.country_card]
LINES = (("defence system", 5), ("protection", 6), ("offside", 7), ("positioning", 1), ("possession", 2),
         ("passing", 3), ("tackling", 4), ("marking", 8))
CHARACTERISTICS = ("hardness", "fitness", "energy", "morale")
DEFAULTS = "The last five lines are the defaults every player follows unless his own tactics say otherwise (P)."
WIDTHS = (200, 176, 0)


def words(state, element):
    """(the word with the element clear, the word with it set)."""
    from goal2.game.country_card import tactic_word
    from goal2.game.player_card import _Memory
    memory = _Memory(state)
    return tactic_word(memory, element, 0), tactic_word(memory, element, 1)


class TeamTacticsScreen(Screen):
    preserve_player_edits = True
    title = "team tactics"
    escape_text = "desk"

    def __init__(self, window, model, *, answer=None, apply=None):
        self.escape_text = "match menu" if answer is not None else "desk"
        super().__init__(window)
        self.model = model
        self.answer, self.apply = answer, apply
        self.pending = False
        self.message = ""
        self._requested = None
        self.line = 0
        self.changed = None
        self._build()
        self.bind((Qt.Key.Key_Up,), "", lambda: self.choose(self.line - 1), captions=("",), shown=False)
        self.bind((Qt.Key.Key_Down,), "", lambda: self.choose(self.line + 1), captions=("",), shown=False)
        self.bind((), "line", None, captions=("↑", "↓"))
        last_on_the_bar(self, self.escape_text)
        self.set_enter("Change line", self.change)
        self.refresh()

    def _build(self):
        main = QHBoxLayout()
        main.setSpacing(18)
        column = QVBoxLayout()
        column.setSpacing(14)
        head, head_layout = box()
        row = QHBoxLayout()
        row.setSpacing(28)
        self.country = label("", "h1")
        self.facts = label("", "sub")
        self.facts.setTextFormat(Qt.TextFormat.RichText)
        row.addWidget(self.country, 0, Qt.AlignmentFlag.AlignVCenter)
        row.addWidget(self.facts, 0, Qt.AlignmentFlag.AlignVCenter)
        row.addStretch(1)
        head_layout.addLayout(row)
        column.addWidget(head)
        boxes = QHBoxLayout()
        boxes.setSpacing(18)
        table, table_layout = box("Team tactics · player defaults")
        table_layout.setSpacing(0)
        table_layout.addSpacing(10)
        header = Row(-1, WIDTHS, margins=(8, 4, 8, 4), underline=True)
        header.set(("LINE", "NOW", "OTHER OPTION"), (theme.HEADING,) * 3)
        for cell in header.cells: cell.setWordWrap(True)
        header.setCursor(Qt.CursorShape.ArrowCursor)
        table_layout.addWidget(header)
        self.rows = []
        for i in range(len(LINES)):
            line = Row(i, WIDTHS, margins=(8, 6, 8, 6), underline=True)
            line.chosen.connect(self.click)
            table_layout.addWidget(line)
            for cell in line.cells: cell.setWordWrap(True)
            self.rows.append(line)
        table_layout.addSpacing(14)
        self.note = para("", "sub")
        self.note.setMinimumWidth(560)
        table_layout.addWidget(self.note)
        table_layout.addStretch(1)
        boxes.addWidget(table, 1)
        right, right_layout = box("Characteristics")
        right.setFixedWidth(360)
        self.characteristics = KeyValues(CHARACTERISTICS, label_width=110, tone=theme.TEXT_BRIGHT)
        for name in CHARACTERISTICS:
            self.characteristics.set(name, NOT_DECODED)
        for value in self.characteristics.values.values(): value.setWordWrap(True)
        right_layout.addWidget(self.characteristics)
        right_layout.addStretch(1)
        boxes.addWidget(right)
        column.addLayout(boxes, 1)
        main.addLayout(column, 1)
        self.strip = Strip()
        main.addWidget(self.strip)
        self.body_layout.addLayout(main, 1)

    def refresh(self):
        model, state = self.model, self.model.state
        view = model.view()
        rows, eleven = squad_rows(model)
        if self.answer is not None:
            rows = [self.answer.card(w) for w in self.answer.words()]
            eleven = len(self.answer.eleven)
        lineup = rows[:eleven]
        formation = "-".join(str(sum(1 for r in lineup if r["line"] == line))
                             for line in ("defence", "midfield", "attack"))
        facts = [("formation ", None), (formation, theme.TEXT_BRIGHT)]
        fixture = state.campaign.next_fixture if state.campaign is not None else None
        if fixture is not None:
            opponent = fixture.side_b if fixture.side_a == state.managed_country else fixture.side_a
            facts += [(" · next ", None), (model.goaldat.country_names[opponent], theme.TEXT_BRIGHT)]
        self.country.setText(view["country_name"])
        self.facts.setText(rich(facts))
        for i, ((name, element), line) in enumerate(zip(LINES, self.rows)):
            clear, set_ = words(state, element)
            byte = state.country_tactics if self.answer is None else self.answer.team_tactics
            now = byte >> (element - 1) & 1
            line.set((name, set_ if now else clear, clear if now else set_),
                     (theme.TEXT_BRIGHT, theme.TEXT_BRIGHT, theme.TEXT_NORMAL))
            line.set_on(i == self.line)
        parts = [(DEFAULTS, None)]
        if self.changed is not None:
            name, before, after = self.changed
            parts = [(f"Changed just now: {name} {before} → ", None), (after, theme.VALUE),
                     (". Match remains paused." if self.answer is not None else ".", None)]
        if self.pending:
            parts = [("Applying team tactics. Waiting for the game to confirm; the match stays paused.", theme.VALUE)]
        elif self.message:
            parts = [(self.message, theme.VALUE)]
        self.note.setText(f'<p style="line-height:{LINE_HEIGHT}%">{rich(parts)}</p>')
        self.strip.show_rows(view["country_name"],
                             [(r["role"], r["line"], full_name(model, r["id"])) for r in rows], -1, eleven == 11)
        self._refresh_hint()

    def lines(self):
        """The lines as they read: (line, now, other option)."""
        return [tuple(line.texts()) for line in self.rows]

    def choose(self, index):
        if self.pending: return
        self.line = max(0, min(len(LINES) - 1, index))
        self.refresh()

    def click(self, index):
        if index == self.line:
            return self.change()
        return self.choose(index)

    def enter_hint_text(self):
        if getattr(self, "pending", False):
            return "Applying..."
        return super().enter_hint_text()

    def escape(self):
        if self.pending:
            return
        return super().escape()

    def handle_key(self, key):
        if self.pending and key != Qt.Key.Key_F1:
            return True
        return super().handle_key(key)

    def change(self):
        if self.pending: return
        name, element = LINES[self.line]
        _, before, after = self.lines()[self.line]
        self.message = ""
        if self.answer is not None:
            self._requested = (element, not bool(self.answer.team_tactics & (1 << (element - 1))), name, before, after)
            self.pending = True
            self.refresh()
            self.apply(self, self._requested[0], self._requested[1])
        else:
            self.model.set_team_tactic(element)
            self.changed = (name, before, after)
            self.refresh()

    def applied(self, answer, report):
        self.answer = answer
        self.pending = False
        element, wanted, name, before, after = self._requested
        if bool(answer.team_tactics & (1 << (element - 1))) == wanted:
            self.changed = (name, before, after)
        else:
            self.changed = None
            self.message = "The game did not accept that tactic change. The current value is shown."
        self._requested = None
        self.refresh()

    def shown(self):
        self.refresh()


def open_team_tactics(window, model):
    """Push S10 over the current screen; T164 calls it from the desk."""
    return window.push(TeamTacticsScreen(window, model))
