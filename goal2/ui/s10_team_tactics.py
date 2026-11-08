"""S10 Team tactics: the team's eight lines.

[designed: owner, 2026-11-03, #526; docs/design/ui-2026-11, S10 and its mockup s10-team-tactics.html; T165] Each
line with its current value, in the original's order: defence system, protection, offside, then
the player defaults positioning, possession, passing, tackling and marking [confirmed: F010, the team tactics
screen 1771:1981 lists element DS:6BBF[row]: 5, 6, 7, 1, 2, 3, 4, 8; the words from goal2.game.country_card,
F008]. ↑↓ choose a line; before a match Enter uses `DesktopModel.set_team_tactic`.
[designed: owner #610] At a match stop Enter submits a team-tactics-only original menu edit; the returned
decision confirms the actual flag before further input. Career state is published only at full time. Esc returns. A click on a line
moves the cursor to it, a click on the highlighted line is Enter [designed: T165].

The formation is counted from the eleven's lines [derived: goal2/game/country_card.py; today's Team tactics]. The
characteristics panel uses the accepted original TEAM reader before a match [confirmed: original1771:1981
calls157D; F038; T202]. Complete live snapshots use the same immutable reader with the accepted XI order
[derived: #641, F038]; legacy clients without current records retain the explicit fallback.
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
WIDTHS = (200, 0, 0)


def words(state, element, *, memory=None):
    """(the word with the element clear, the word with it set)."""
    from goal2.game.country_card import tactic_word
    from goal2.game.player_card import _Memory
    memory = _Memory(state) if memory is None else memory
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
        from goal2.ui.country_header import TeamHeader
        from goal2.ui.team_card import CharacteristicPanel, LineBars
        from goal2.ui.squad_card import FactsTable
        left = QVBoxLayout()
        left.setSpacing(10)
        self.team_header = TeamHeader(self.window_.family, compact=True)
        self.country = self.team_header.name
        left.addWidget(self.team_header)
        bars, bars_layout = box('Skills')
        self.skills = LineBars()
        bars_layout.addWidget(self.skills)
        self.performance_heading = label('PERFORMANCE', 'boxHeading')
        self.performance = LineBars()
        bars_layout.addWidget(self.performance_heading)
        bars_layout.addWidget(self.performance)
        left.addWidget(bars)
        self.facts = label('', 'sub')
        self.facts.setWordWrap(True)
        self.facts.setTextFormat(Qt.TextFormat.RichText)
        left.addWidget(self.facts)
        left.addStretch(1)
        main.addLayout(left, 1)
        table, table_layout = box()
        table_layout.setSpacing(2)
        self.team_heading = label('TEAM TACTICS', 'boxHeading')
        table_layout.addWidget(self.team_heading)
        self.defaults_heading = label('PLAYER DEFAULTS', 'boxHeading')
        self.rows = []
        for i in range(len(LINES)):
            if i == 3:
                table_layout.addSpacing(8)
                table_layout.addWidget(self.defaults_heading)
            line = Row(i, WIDTHS, margins=(8, 4, 8, 4), underline=True)
            line.chosen.connect(self.click)
            for cell in line.cells: cell.setWordWrap(True)
            # Original1981 shows label/current value. Retain the alternative in
            # the existing lines() API, without a duplicate visible table.
            line.cells[2].hide()
            table_layout.addWidget(line)
            self.rows.append(line)
        table_layout.addSpacing(8)
        self.averages = FactsTable(('caps','age'))
        table_layout.addWidget(self.averages)
        self._characteristic_panel = CharacteristicPanel(self.window_.family)
        self._characteristic_fallback = KeyValues(CHARACTERISTICS, label_width=110, tone=theme.TEXT_BRIGHT)
        for name in CHARACTERISTICS:
            self._characteristic_fallback.set(name, NOT_DECODED)
        for value in self._characteristic_fallback.values.values(): value.setWordWrap(True)
        table_layout.addWidget(self._characteristic_panel)
        table_layout.addWidget(self._characteristic_fallback)
        self.characteristics = self._characteristic_panel if self.answer is None else self._characteristic_fallback
        self._characteristic_panel.setVisible(self.answer is None)
        self._characteristic_fallback.setVisible(self.answer is not None)
        self.note = para('', 'sub')
        self.note.setMinimumWidth(520)
        table_layout.addWidget(self.note)
        table_layout.addStretch(1)
        main.addWidget(table, 2)
        self.strip = Strip()
        self.injury_hint = label('* injured', 'sub')
        self.strip.layout().insertWidget(self.strip.layout().count()-1, self.injury_hint)
        main.addWidget(self.strip)
        self.body_layout.addLayout(main, 1)

    def refresh(self):
        model, state = self.model, self.model.state
        # One fresh immutable projection per decision/refresh; cursor movement
        # remains presentation-only. Pending position drafts still drive the
        # formation/strip below, while traits use accepted current raw records.
        records = getattr(self.answer, "live_records", None) if self.answer is not None else None
        trait_state = state if self.answer is None else None
        if records:
            from goal2.ui.live_cards import card_state
            trait_state = card_state(state, records, self.answer.team_tactics)
            trait_state.managed_squad = list(self.answer.words())
        decoded = trait_state is not None
        self._characteristic_panel.setVisible(decoded)
        self._characteristic_fallback.setVisible(not decoded)
        self.characteristics = self._characteristic_panel if decoded else self._characteristic_fallback
        from goal2.game.team_card import TeamMemory
        from goal2.game.country_card import card as country_card
        memory = TeamMemory(trait_state if decoded else state)
        context = ... if self.answer is None else getattr(self.answer, 'team_context', None)
        card = country_card(trait_state if decoded else state, state.managed_country,
                            model.goaldat, memory=memory, performance_context=context)
        if decoded:
            traits = card['characteristics']
            self.characteristics.set_panel(traits)
            self.averages.set({n['field']:n['text'] for n in traits['numbers']}, theme.VALUE)
        else:
            self.averages.set({'caps':NOT_DECODED,'age':NOT_DECODED}, theme.TEXT_NORMAL)
        self.skills.set_panel(card['team_skills'] if decoded else None)
        performance = card['performance'] if self.answer is not None and decoded else None
        self.performance.set_panel(performance)
        self.performance.setVisible(performance is not None)
        self.performance_heading.setVisible(performance is not None)
        if self.answer is None:
            rows, eleven = squad_rows(model)
        else:
            from goal2.game import roles
            table = roles.tables(state)
            rows = []
            for word in self.answer.words():
                code, line = roles.role(state, self.answer.position(word), cache=table)
                rows.append({"id": word, "role": code, "line": line})
            eleven = len(self.answer.eleven)
        country_name = model.goaldat.country_names[state.managed_country]
        lineup = rows[:eleven]
        formation = "-".join(str(sum(1 for r in lineup if r["line"] == line))
                             for line in ("defence", "midfield", "attack"))
        facts = [("formation ", None), (formation, theme.TEXT_BRIGHT)]
        fixture = state.campaign.next_fixture if state.campaign is not None else None
        if fixture is not None:
            opponent = fixture.side_b if fixture.side_a == state.managed_country else fixture.side_a
            facts += [(" · next ", None), (model.goaldat.country_names[opponent], theme.TEXT_BRIGHT)]
        card = {**card, 'formation':formation, 'eleven':[r['role'] for r in lineup]}
        self.team_header.set_card(card)
        self.facts.setText(rich(facts))
        for i, ((name, element), line) in enumerate(zip(LINES, self.rows)):
            clear, set_ = words(state, element, memory=memory)
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
        injured = getattr(self.answer, 'injured', ())
        self.injury_hint.setVisible(bool(injured))
        self.strip.show_rows(country_name,
                             [(r["role"], r["line"], full_name(model, r["id"]) +
                               (' *' if r['id'] in injured else '')) for r in rows], -1, eleven == 11,
                             injured=[i for i,r in enumerate(rows) if r["id"] in injured])
        self._refresh_hint()

    def lines(self):
        """The lines as they read: (line, now, other option)."""
        return [tuple(line.texts()) for line in self.rows]

    # [designed: owner #636] Cursor movement changes presentation only.
    # Mutable roles/formation/flags are decoded afresh on every real refresh.
    def choose(self, index):
        if self.pending: return
        previous = self.line
        self.line = max(0, min(len(LINES) - 1, index))
        self.rows[previous].set_on(False)
        self.rows[self.line].set_on(True)
        self._refresh_hint()

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
