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

from goal2.ui import theme
from goal2.ui.screen import LINE_HEIGHT, Screen
from goal2.ui.squad_card import (NOT_DECODED, full_name, last_on_the_bar, rich,
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
    GRID = True   # [designed: owner, #667; T212b]
    preserve_player_edits = True
    title = "team tactics"
    escape_text = "desk"

    def __init__(self, window, model, *, answer=None, apply=None, back=None):
        # [designed: #799] The caller names the actual parent; held matches keep their default.
        self.escape_text = back if back is not None else "match menu" if answer is not None else "desk"
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
        """[designed: owner, #667; T212b] TEAM and its bars, the editor and traits, and the twenty in three cell columns."""
        from goal2.ui.cells import Cells, CellPara
        from goal2.ui.cell_parts import CellTableRow, CellValues, CellFacts, GridStrip
        from goal2.ui.country_parts import CellTeamHeader, CellLineBars, CellCharacteristics, framed
        body = Cells(90, 25, "tacticsBody")
        self.body_layout.addWidget(body, 1)
        self.team_header = CellTeamHeader(self.window_.family)
        self.country = self.team_header.name
        body.put(self.team_header, 0, 0, 34, 11)
        skills, inner = framed("skills", 34, 4)
        self.skills = CellLineBars()
        inner.put(self.skills, 0, 0, 34, 4)
        body.put(skills, 0, 11, 34, 5)
        self.performance_heading, inner = framed("performance", 34, 4)
        self.performance = CellLineBars()
        inner.put(self.performance, 0, 0, 34, 4)
        body.put(self.performance_heading, 0, 16, 34, 5)
        self.facts = CellPara("", "sub")
        body.put(self.facts, 0, 21, 34, 4)
        self.rows = []
        for caption, first, count, row in (("team tactics", 0, 3, 0), ("player defaults", 3, 5, 5)):
            frame, inner = framed(caption, 34, count)
            if first == 0:
                self.team_heading = frame.rule
            else:
                self.defaults_heading = frame.rule
            for i in range(first, first + count):
                line = CellTableRow(i, (14, 19, 0), gaps=(0, 1, 0))
                line.cells[2].hide()  # lines() retains the alternative; the original shows the current value only
                line.chosen.connect(self.click)
                inner.put(line, 0, i - first, 34)
                self.rows.append(line)
            body.put(frame, 35, row, 34, count + 1)
        traits, inner = framed("characteristics", 34, 7)
        self.averages = CellFacts({"caps": 17, "age": 17}, rows=2)
        inner.put(self.averages, 0, 0, 34, 3)
        self._characteristic_panel = CellCharacteristics()
        self._characteristic_fallback = CellValues(CHARACTERISTICS, 34, 8)
        for name in CHARACTERISTICS:
            self._characteristic_fallback.set(name, NOT_DECODED)
        inner.put(self._characteristic_panel, 0, 3, 25, 4)
        inner.put(self._characteristic_fallback, 0, 3, 34, 4)
        body.put(traits, 35, 12, 34, 8)
        self.characteristics = self._characteristic_panel if self.answer is None else self._characteristic_fallback
        self._characteristic_panel.setVisible(self.answer is None)
        self._characteristic_fallback.setVisible(self.answer is not None)
        self.note = CellPara("", "sub")
        body.put(self.note, 35, 21, 34, 4)
        self.strip = GridStrip(cols=20)
        body.put(self.strip, 70, 0, 20, 23)
        self.injury_hint = body.text("* injured", "sub", 70, 23, 20)

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
        if self.answer is not None:
            if getattr(self.answer, "opportunity_visible", False):
                facts += [(" · SUBSTITUTION OPPORTUNITY", theme.VALUE)]
            elif getattr(self.answer, "substitution_requested", False):
                facts += [(" · SUBSTITUTION REQUESTED", theme.VALUE)]
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


def open_team_tactics(window, model, *, back=None):
    """Push S10 over the current screen; T164 calls it from the desk."""
    return window.push(TeamTacticsScreen(window, model, **({'back': back} if back is not None else {})))
