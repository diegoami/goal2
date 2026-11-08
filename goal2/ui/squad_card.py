"""The parts S08, S09 and S10 share: the player card, the squad strip, bars, key-value lines and table rows.

[designed: owner, 2026-11-03, #526; docs/design/ui-2026-11, S08–S10 and their mockups s08-squad.html,
s09-player-tactics.html, s10-team-tactics.html] Everything shown is read from `DesktopModel` (`view`, `pool_view`)
and from `goal2.game.player_card.card`, the card's data as today's Team page shows it [designed: T88]; nothing here
changes the game.

The parts are built once, when a screen is made, and only their texts and colours change afterwards: the window
scales the lengths a screen holds when it is pushed (goal2/desktop/fixed_page.py), so no widget is added later.
Colours come from `theme` by role. They are set on each widget by itself, as colour only, so the window's style sheet
(and its scaled lengths) stays T162's.
"""
from __future__ import annotations

import html

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QFrame, QGridLayout, QHBoxLayout, QLineEdit, QSizePolicy, QVBoxLayout, QWidget

from goal2.ui import theme
from goal2.ui.screen import Clickable, label

# [confirmed: docs/design/ui-2026-11/README.md §3, "Role codes are coloured by line"; F002 R011]
LINE_COLOUR = {"goalkeeper": theme.GOALKEEPER, "defence": theme.DEFENCE, "midfield": theme.MIDFIELD,
               "attack": theme.ATTACK}
SKILL_CELLS = 25   # [confirmed: goal2.game.skills, F008: each skill bar is 0..25 long]
CHARACTERISTIC_CELLS = 14   # [confirmed: goal2.game.player_card, F008: a characteristic's bar of 14]
NAME_MAX = 12   # [designed: T92, goal2.game.identities.PLAYER_MAX; the task: at most 12 characters]
NOT_DECODED = "not decoded yet (G05)"   # [designed: T144, goal2.game.country_card.NOT_DECODED]


def colour(widget, value):
    widget.setStyleSheet(f"color: {value}; background: transparent;")


def box(heading=None, margins=(16, 14, 16, 14), spacing=10):
    """A framed box, as the mockups' `.box`, with its cyan heading (`.box > h2`)."""
    frame = QFrame()
    frame.setObjectName("box")
    layout = QVBoxLayout(frame)
    layout.setContentsMargins(*margins)
    layout.setSpacing(spacing)
    if heading:
        layout.addWidget(label(heading.upper(), "boxHeading"))
    return frame, layout


def rich(parts):
    """Rich text from (text, colour or None) parts, escaped."""
    out = []
    for text, tone in parts:
        text = html.escape(text)
        out.append(f'<span style="color:{tone}">{text}</span>' if tone else text)
    return "".join(out)


class Bar(QFrame):
    """A bar of the original's two colours: the filled part light grey, the rest magenta. [confirmed: §3 palette,
    "bar, filled" and "bar, empty"] Its two parts share the width by stretch, so it scales with the page."""

    def __init__(self):
        super().__init__()
        self.setFixedHeight(13)   # [designed: mockups/style.css, `.bar { height: 13px }`]
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        self.filled, self.empty = QFrame(), QFrame()
        for part, tone in ((self.filled, theme.BAR_FILLED), (self.empty, theme.BAR_EMPTY)):
            part.setStyleSheet(f"background: {tone};")
            part.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Expanding)
            layout.addWidget(part)
        self.value = None

    def set(self, filled, cells):
        """`filled` of `cells`; None shows no bar (the value is unavailable)."""
        self.value = (filled, cells)
        layout = self.layout()
        if filled is None:
            self.filled.hide()
            self.empty.hide()
            return
        filled = max(0, min(cells, filled))
        self.filled.setVisible(filled > 0)
        self.empty.setVisible(filled < cells)
        layout.setStretch(0, filled)
        layout.setStretch(1, cells - filled)


class Bars(QWidget):
    """Rows of a label, a bar and a word, as the mockups' `.bars` grid (110 px, the bar, then the word).
    [designed: T165] The word column is 120 px, not the mockup's 104, so the original's longest words ("could be
    worse", F008's DS:6EB4 table) fit."""

    def __init__(self, names, word_width=120):
        super().__init__()
        grid = QGridLayout(self)
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setHorizontalSpacing(10)
        grid.setVerticalSpacing(2)
        self.rows = {}
        self.labels = {}
        for r, name in enumerate(names):
            name_label = label(name, "barLabel")
            name_label.setFixedWidth(132)
            # [designed: owner611; T193] Original brown labels remain distinct from values.
            colour(name_label, theme.CARD_LABEL)
            self.labels[name] = name_label
            bar = Bar()
            word = label("", "barWord")
            word.setFixedWidth(round(word_width * 1.5))
            grid.addWidget(name_label, r, 0)
            grid.addWidget(bar, r, 1)
            grid.addWidget(word, r, 2)
            self.rows[name] = (bar, word)
        grid.setColumnStretch(1, 1)

    def set(self, name, filled, cells, word="", tone=theme.TEXT_BRIGHT):
        bar, word_label = self.rows[name]
        bar.set(filled, cells)
        word_label.setText(word)
        colour(word_label, tone)


class KeyValues(QWidget):
    """Lines of a label and its value: brown labels as the mockups' `.kv` (card labels, brown), or bright ones as
    their `.bars` labels."""

    def __init__(self, names, label_width=96, tone=theme.CARD_LABEL):
        super().__init__()
        grid = QGridLayout(self)
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setHorizontalSpacing(16)
        grid.setVerticalSpacing(4)
        self.values = {}
        for r, name in enumerate(names):
            key = label(name, "kvKey")
            key.setFixedWidth(round(label_width * 1.5))
            colour(key, tone)
            value = label("", "kvValue")
            grid.addWidget(key, r, 0)
            grid.addWidget(value, r, 1)
            self.values[name] = value
        grid.setColumnStretch(1, 1)

    def set(self, name, text):
        self.values[name].setText(text)


class Row(Clickable):
    """A row of a list or table: its cells, and the highlight bar when it is the cursor's (`.list li.on`,
    `tr.on td`). A click reports the row; the screen decides what it does."""
    chosen = Signal(int)

    def __init__(self, index, widths, margins=(8, 2, 8, 2), underline=False):
        super().__init__("listRow")
        self.index = index
        self.underline = underline
        layout = QHBoxLayout(self)
        layout.setContentsMargins(*margins)
        layout.setSpacing(10)
        self.cells = []
        self.tones = []
        for width in widths:
            cell = label("", "rowCell")
            if width:
                cell.setFixedWidth(width)
            layout.addWidget(cell, 0 if width else 1)
            self.cells.append(cell)
            self.tones.append(theme.TEXT_BRIGHT)
        self.on = False
        self.clicked.connect(lambda: self.chosen.emit(self.index))
        self._paint()

    def set(self, texts, tones=None):
        for i, cell in enumerate(self.cells):
            cell.setText(texts[i] if i < len(texts) else "")
        self.tones = list(tones) if tones else [theme.TEXT_BRIGHT] * len(self.cells)
        self._paint()

    def set_on(self, on):
        self.on = bool(on)
        self._paint()

    def texts(self):
        return [cell.text() for cell in self.cells]

    def _paint(self):
        rule = f"border-bottom: 1px solid {theme.FRAME_DARK};" if self.underline else ""
        if self.on:
            self.setStyleSheet(f"#listRow {{ background: {theme.HIGHLIGHT}; {rule} }}")
        else:
            self.setStyleSheet(f"#listRow {{ background: {theme.GROUND}; {rule} }}")
        for cell, tone in zip(self.cells, self.tones):
            colour(cell, theme.BAD if self.property("injured") else theme.ON_HIGHLIGHT if self.on else tone)


def full_name(model, word):
    """[confirmed: F008] The card's name: the initial and the surname (renames applied, T92)."""
    goaldat = model.goaldat
    initial = goaldat.player_initials[word] if word < len(goaldat.player_initials) else ""
    return (initial + " " if initial else "") + goaldat.player_names[word]


def squad_rows(model):
    """The twenty in the strip's order: the eleven, then the bench in squad order, as the original's strip shows
    them [confirmed: docs/original-game/images/m244-squad.png; designed: T99]; and how many are the eleven."""
    rows = {r["id"]: r for r in model.view()["players"]}
    state = model.state
    eleven = [w for w in state.starting_eleven if w in rows] if len(state.starting_eleven) == 11 else []
    bench = [w for w in state.managed_squad if w not in eleven]
    return [rows[w] for w in eleven + bench], len(eleven)


class Strip(QFrame):
    """The list on the right, as the original's: the twenty (the eleven, a gap, the bench) or a page of twenty of
    the pool. Rows are clicked through `chosen(index on the page)`."""
    chosen = Signal(int)
    PAGE = 20

    def __init__(self):
        super().__init__()
        self.setObjectName("box")
        self.setFixedWidth(390)   # [designed: owner #598] room for 24px names and live injury labels
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(0)
        self.heading = label("", "boxHeading")
        layout.addWidget(self.heading)
        layout.addSpacing(10)
        self.rows = []
        self.gap = QWidget()
        self.gap.setFixedHeight(10)   # `.strip .sep { height: 10px }`
        for i in range(self.PAGE):
            row = Row(i, (30, 0))
            row.chosen.connect(self.chosen.emit)
            layout.addWidget(row)
            self.rows.append(row)
            if i == 10:
                layout.addWidget(self.gap)
        layout.addStretch(1)

    def show_rows(self, heading, rows, current=-1, gap=True, injured=()):
        """`rows`: (code, line, name) for up to twenty rows; `current` the highlighted row (-1: none)."""
        self.heading.setText(heading.upper())
        self.gap.setVisible(gap)
        for i, row in enumerate(self.rows):
            if i < len(rows):
                code, line, name = rows[i]
                row.setProperty("injured", i in injured)
                # [confirmed: t156-014-squad; owner #637] The full name shares the role colour.
                tone = LINE_COLOUR.get(line, theme.TEXT_NORMAL)
                row.set((code, name), (tone, tone))
                row.show()
            else:
                row.set(("", ""))
                row.hide()
            row.set_on(i == current)

    def shown_texts(self):
        return [row.texts() for row in self.rows if not row.isHidden()]


def code_label(code, line, name="roleCode"):
    widget = label(code, name)
    widget.setFixedWidth(22)
    widget.setAlignment(Qt.AlignmentFlag.AlignCenter)
    colour(widget, LINE_COLOUR.get(line, theme.TEXT_NORMAL))
    return widget


class NameLine(QFrame):
    """F2's new name: a line drawn as S04's name line (the mockups' `.field`: the text, then the count of
    characters), at most twelve characters. [designed: main session, 2026-11-03, T165, from s04-country.html]"""

    def __init__(self):
        super().__init__()
        self.setObjectName("field")
        layout = QHBoxLayout(self)
        layout.setContentsMargins(14, 6, 14, 6)
        layout.setSpacing(8)
        layout.addWidget(label("New name", "muted"))
        self.edit = QLineEdit()
        self.edit.setObjectName("nameEdit")
        self.edit.setMaxLength(NAME_MAX)
        self.edit.setFrame(False)
        self.edit.setStyleSheet(f"background: {theme.GROUND}; color: {theme.TEXT_BRIGHT}; border: none;")
        layout.addWidget(self.edit, 1)
        self.count = label("", "muted")
        layout.addWidget(self.count)
        self.edit.textChanged.connect(self._count)
        self._count()

    def _count(self, *unused):
        self.count.setText(f"{len(self.edit.text())} / {NAME_MAX}")


class FactsTable(QWidget):
    """[designed: owner611; T193] Aligned labelled cells, preserving the readable field values.

    [confirmed: original1771:42BC, T156 initial squad] Six facts and three position/card cells.
    text()/setWordWrap() retain the card consumers' metadata interface.
    """
    def __init__(self, names):
        super().__init__()
        grid = QGridLayout(self)
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setHorizontalSpacing(10)
        grid.setVerticalSpacing(0)
        self.labels, self.values = {}, {}
        for column, name in enumerate(names):
            heading = label(name, "factLabel")
            colour(heading, theme.CARD_HEADING)
            value = label("", "factValue")
            value.setWordWrap(True)
            grid.addWidget(heading, 0, column)
            grid.addWidget(value, 1, column)
            grid.setColumnStretch(column, 1)
            self.labels[name], self.values[name] = heading, value

    def set(self, values, tone):
        for name, value in values.items():
            self.values[name].setText(str(value))
            colour(self.values[name], tone)

    def text(self):
        return " · ".join(f"{name} {value.text()}" for name, value in self.values.items())

    def setWordWrap(self, on):
        for value in self.values.values():
            value.setWordWrap(on)


class PlayerCard(QFrame):
    """The S08 card: the name line, the position line, the twelve skills, his tactics and the five
    characteristics, every field today's card shows (goal2.game.player_card.card) in the mockup's layout."""

    def __init__(self):
        super().__init__()
        self.setObjectName("box")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(6)
        head = QHBoxLayout()
        head.setSpacing(16)
        self.code = code_label("", "unknown")
        self.name = label("", "h1")
        self.facts = FactsTable(("age", "caps", "goals", "height", "foot", "performance"))
        self.readiness = label("", "readiness")
        self.name_line = NameLine()
        self.name_line.hide()
        for widget in (self.code, self.name):
            head.addWidget(widget, 0, Qt.AlignmentFlag.AlignBaseline)
        head.addWidget(self.name_line, 1)
        head.addStretch(1)
        head.addWidget(self.readiness, 0, Qt.AlignmentFlag.AlignBaseline)
        self.head = head
        layout.addLayout(head)
        layout.addWidget(self.facts)
        self.positions = FactsTable(("position", "club position", "cards"))
        layout.addWidget(self.positions)
        columns = QHBoxLayout()
        columns.setSpacing(24)
        left = QVBoxLayout()
        # [designed: T193] Leave fractional-font rounding room without reducing the24px text.
        left.setSpacing(4)
        left.addWidget(label("SKILLS", "boxHeading"))
        from goal2.game.player_card import SKILLS, TACTICS
        self.skills = Bars(SKILLS, word_width=24)
        self.skills.layout().setVerticalSpacing(0)
        left.addWidget(self.skills)
        left.addStretch(1)
        columns.addLayout(left, 1)
        right_widget = QWidget()
        right_widget.setFixedWidth(430)
        right = QVBoxLayout(right_widget)
        right.setContentsMargins(0, 0, 0, 0)
        right.setSpacing(4)
        right.addWidget(label("TACTICS", "boxHeading"))
        self.tactics = KeyValues(TACTICS + ("mark",))
        self.tactics.layout().setVerticalSpacing(2)
        right.addWidget(self.tactics)
        right.addSpacing(8)
        right.addWidget(label("CHARACTERISTICS", "boxHeading"))
        self.characteristics = Bars(("hardness", "fitness", "energy", "morale", "leadership"))
        self.characteristics.layout().setVerticalSpacing(0)
        right.addWidget(self.characteristics)
        right.addStretch(1)
        columns.addWidget(right_widget)
        layout.addLayout(columns, 1)
        self.card = None

    def set_card(self, card):
        self.card = card
        self.code.setText(card["role"])
        colour(self.code, LINE_COLOUR.get(card["line"], theme.TEXT_NORMAL))
        self.name.setText(card["full_name"])
        # [designed: T193] Display-only compatibility with the existing raw card and T192's stars.
        stars = card.get("performance_bar")
        performance = ("*" * stars if stars is not None else "" if card["performance"] is None
                       else f"raw {card['performance']}")
        tone = LINE_COLOUR.get(card["line"], theme.TEXT_BRIGHT)
        self.facts.set({**{name: card[name] for name in ("age", "caps", "goals", "height", "foot")},
                        "performance": performance}, tone)
        self.readiness.setText(card["readiness"])
        self.positions.set({"position": card["position"], "club position": card["club_position"],
                            "cards": ", ".join(card["cards"]) or "none"}, tone)
        for name, value in card["skills"]:
            # [designed: owner, 2026-10-21, T99 "no numbers when you can have bars"] the bar alone.
            self.skills.set(name, value, SKILL_CELLS, "" if value is not None else "—")
        for name, word, personal in card["tactics"]:
            self.tactics.set(name, word + (" P" if personal else ""))
        self.tactics.set("mark", card["mark"] or "—")
        for name, word, bar, _raw in card["characteristics"]:
            self.characteristics.set(name, bar, CHARACTERISTIC_CELLS, word, tone=tone)

    def edit_name(self, on, text=""):
        """Show the name line in place of the name and its facts (F2), or the name again."""
        for widget in (self.name, self.facts):
            widget.setVisible(not on)
        self.name_line.setVisible(on)
        if on:
            self.name_line.edit.setText(text)
            self.name_line.edit.selectAll()
            self.name_line.edit.setFocus(Qt.FocusReason.ShortcutFocusReason)


def last_on_the_bar(screen, text):
    """Move Esc's key (named `text`) to the end of the bottom bar, after the screen's own keys, as the S08–S10
    mockups list it; F1 stays first, as T162 puts it."""
    esc = [b for b in screen.bindings if b.text == text and Qt.Key.Key_Escape in b.keys]
    screen.bindings = [b for b in screen.bindings if b not in esc] + esc
    screen._refresh_bar()
