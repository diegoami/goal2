"""S03 New game: how many managers, and the optional starting year.

[designed: owner, 2026-11-03, #526; docs/design/ui-2026-11, S03 and its mockup s03-new-game.html; T163, #537]
- The six numbers, 1 chosen. The design keeps the original's 1 to 6 managers, hot seat [owner decision 5]; the
  Python route has one manager, so 2 to 6 are shown, marked *coming later*, and choosing one only says so (#551).
- One optional field, the starting year [owner decision 9]: empty means the PC clock's year, as the original takes
  it. Either way the original's rule applies: the start year is the year + 1, rounded up to even, and its first
  stage is 2 (continental qualifying) when the start year is divisible by 4, else 5 (World Cup qualifying)
  [confirmed: NG-9, docs/assumptions.md]. The screen shows the start year and its first competition before Enter.
  The stage and its words are the model's own (`campaign.opening_calendar`, `model.STAGES`).
- **←→** number, **Tab** to the year field, **Enter** accept, **Esc** back to S02. A busy line shows while the game is
  prepared (the original's HANG ON A TICK, T156-R1 step 2).
"""
from __future__ import annotations

import datetime

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QFrame, QHBoxLayout, QVBoxLayout

from goal2.desktop.model import STAGES
from goal2.game.campaign import CampaignError, opening_calendar
from goal2.ui.screen import Clickable, Screen, label, para, set_para
from goal2.ui.start_look import LineField, refresh

MANAGERS = 6
# [confirmed: NG-9] the years DOS's clock answers (AH=2Ah); the original checks none, so goal2 takes the same range
DOS_YEARS = (1980, 2099)
BOX_WIDTH = 900   # [designed: s03-new-game.html, the column's `width:900px`]
WORDS = {2: "two", 3: "three", 4: "four", 5: "five", 6: "six"}


def clock_year() -> int:
    """The PC clock's year, as the original reads the DOS date. [confirmed: NG-9]"""
    return datetime.date.today().year


def start_year(year: int) -> int:
    """The original's start year from the clock's year: + 1, rounded up to even. [confirmed: NG-9, 1771:9B85]"""
    start = year + 1
    return start + start % 2


def first_competition(start: int) -> str:
    """The start year's first stage in the model's words, by `campaign.opening_calendar`."""
    return STAGES[opening_calendar(start)[1]]


class NewGameScreen(Screen):
    title = "new game · step 1 of 3"
    pre_game = True
    escape_text = "back to title"

    def __init__(self, window):
        super().__init__(window)
        self.chosen = 1
        self.bind((Qt.Key.Key_Left,), "", lambda: self.choose(self.chosen - 1), captions=("←",), shown=False)
        self.bind((Qt.Key.Key_Right,), "", lambda: self.choose(self.chosen + 1), captions=("→",), shown=False)
        self.bind((), "number", None, captions=("←", "→"))
        self.bind((Qt.Key.Key_Tab,), "starting year", self.toggle_year, captions=("Tab",))
        esc = next(b for b in self.bindings if Qt.Key.Key_Escape in b.keys)
        self.bindings.remove(esc)
        self.bindings.append(esc)
        self._refresh_bar()
        self._build()
        self.set_enter("Accept", self.accept)
        self._show()

    def _build(self):
        row = QHBoxLayout()
        row.addStretch(1)
        frame = QFrame()
        frame.setObjectName("box")
        frame.setFixedWidth(BOX_WIDTH)
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(34, 30, 34, 30)
        layout.setSpacing(0)
        layout.addWidget(label("NEW GAME", "boxHeading"))
        layout.addSpacing(14)
        layout.addWidget(label("How many managers?", "h1"))
        layout.addSpacing(6)
        width = BOX_WIDTH - 2 * 34 - 2
        intro = para("Each manager takes a country of their own; they play in turn at the manager's desk.", "sub")
        intro.setMinimumWidth(width)
        layout.addWidget(intro)
        layout.addSpacing(24)
        digits = QHBoxLayout()
        digits.setSpacing(14)
        self.digits = []
        for n in range(1, MANAGERS + 1):
            digit = Clickable("digit")
            digit.setFixedSize(70, 70)
            inner = QHBoxLayout(digit)
            inner.setContentsMargins(0, 0, 0, 0)
            text = label(str(n), "digitText" if n == 1 else "digitLater")
            text.setAlignment(Qt.AlignmentFlag.AlignCenter)
            inner.addWidget(text)
            digit.clicked.connect(lambda n=n: self.choose(n))
            digits.addWidget(digit)
            self.digits.append(digit)
        digits.addSpacing(10)
        digits.addWidget(label("2 to 6: coming later", "muted"), 0, Qt.AlignmentFlag.AlignVCenter)
        digits.addStretch(1)
        layout.addLayout(digits)
        layout.addSpacing(24)
        more = para("One manager is the usual game. With more, the country and name steps repeat for each, and the "
                    "desk gains next player.", "sub")
        more.setMinimumWidth(width)
        layout.addWidget(more)
        layout.addSpacing(10)
        year = QHBoxLayout()
        year.setSpacing(14)
        year.addWidget(para("Starting year\n(optional)", "muted"))
        self.year_field = LineField(4, on_click=self.toggle_year)
        self.year_field.setFixedWidth(160)
        year.addWidget(self.year_field)
        self.year_note = para("", "sub")
        year.addWidget(self.year_note, 1)
        layout.addLayout(year)
        layout.addSpacing(18)
        self.note_box = QFrame()
        self.note_box.setObjectName("box")
        note = QHBoxLayout(self.note_box)
        note.setContentsMargins(16, 14, 16, 14)
        self.note = para("", "value")
        self.note.setMinimumWidth(width - 34)
        note.addWidget(self.note, 1)
        layout.addWidget(self.note_box)
        row.addWidget(frame)
        row.addStretch(1)
        self.body_layout.addStretch(1)
        self.body_layout.addLayout(row)
        self.body_layout.addStretch(1)

    # What the screen shows.
    def year(self):
        """The start year the field gives (None while it holds no usable year), and the words that say so."""
        typed = self.year_field.text
        clock = clock_year()
        if not typed:
            year, source = clock, "the PC clock's year, as the original"
        elif len(typed) == 4 and DOS_YEARS[0] <= int(typed) <= DOS_YEARS[1]:
            year, source = int(typed), "your year"
        else:
            return None, f"a year from {DOS_YEARS[0]} to {DOS_YEARS[1]}, or empty for the PC clock's year ({clock})"
        start = start_year(year)
        try:
            words = first_competition(start)
        except CampaignError as exc:   # every start year of the rule is even, so this is not expected
            return None, str(exc)
        return start, f"{source}: the game starts in {start} with {words}"

    def _show(self, note=None):
        for n, digit in enumerate(self.digits, start=1):
            digit.setProperty("on", n == self.chosen)
            refresh(digit)
        self.year_field.placeholder = str(clock_year())
        self.year_field.set_text(self.year_field.text)
        _, words = self.year()
        set_para(self.year_note, words)
        if note is None and self.chosen > 1:
            note = self.later()
        self.note_plain = note or ""
        set_para(self.note, self.note_plain)
        self.note_box.setVisible(bool(note))

    def later(self):
        return (f"{WORDS[self.chosen].capitalize()} managers are coming later (#551): goal2 plays one manager for now. "
                "Choose 1.")

    def start_year_shown(self):
        """What the screen says of the start year now."""
        return self.year_note.text()

    def note_text(self):
        return self.note_plain if self.note_box.isVisible() else ""

    # The keys.
    def choose(self, n):
        self.chosen = max(1, min(n, MANAGERS))
        self._show()

    def toggle_year(self):
        self.year_field.set_active(not self.year_field.active)
        self._show()

    def type_text(self, key, text) -> bool:
        """While the year field is active, digits and Backspace edit it."""
        if not self.year_field.active:
            return False
        if key == Qt.Key.Key_Backspace:
            self.year_field.backspace()
        elif text and text.isdigit() and len(text) == 1:
            self.year_field.type(text)
        else:
            return False
        self._show()
        return True

    def accept(self):
        """Enter: with one manager and a usable year, prepare the game and go on to S04."""
        if self.chosen > 1:
            self._show(self.later())
            return None
        start, words = self.year()
        if start is None:
            self._show(f"The starting year cannot be used: type {words}.")
            return None
        self._show("Hang on a tick: preparing the 128 countries…")
        for _ in range(3):
            QApplication.processEvents()
        from goal2.ui.s04_country import CountryScreen
        try:
            screen = CountryScreen(self.window_, start)
        except ValueError as exc:
            self._show(str(exc))
            return None
        self._show()
        return self.window_.push(screen)

    def shown(self):
        self._show()
