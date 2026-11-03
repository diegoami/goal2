"""S11 Fixtures: the coming round, and which matches are watched.

[designed: owner, 2026-11-03, #526; docs/design/ui-2026-11, S11 and its mockup s11-fixtures.html; T178, #560] The
round's fixtures in the order they are played, each with its kind and what happens at kick-off, **✓** on the matches
that will be watched [confirmed: T156-R1 step 224, docs/original-game/images/t156-224-fixture-list.png: the fixture
list, its kinds "friendly" and "qualifying", ↑↓ to scroll, ✓ on the watched match; E031 C17–C18]:

- **↑↓** move the highlight and scroll the list; **Esc** back to the screen it was opened from (the desk, or S07).
- **Enter** does what the highlighted row's action names, on the Enter hint:
  - your own match: *watch match*, always on: your own matches are watched [designed: owner decision 1, #526];
  - another country's match: the original's ✓ toggle (*watch match* / *auto result*) is not built. The Python route
    cannot play a computer-vs-computer match watched: `goal2.game.watched_match.prepare_watched`, which the engine
    server calls for every watched friendly, refuses a fixture without the managed country ("managed country must be
    a fixture endpoint"), and `campaign_rounds.World` refuses a watched row on a silent fixture. So the row is an
    *auto result* and Enter says watching it comes later [designed: T178's task, "do not build a toggle that does
    nothing"];
  - your own friendly: *cancel or rearrange* has no call on the route, so Enter says it comes later.
- A click on a row moves the highlight to it; a click on the highlighted row is Enter [designed: owner, 2026-11-03,
  #526, "the mouse does what the keys do"; as T165's rows].

The list is the model's (`DesktopModel.fixture_list`): a round is what one *play next game* plays on this route.
With a country (S07's Enter), the list is that country's coming fixtures instead. The route keeps no venue
(T41a, #562), so the two sides have no *home* and *away* headings. This screen changes nothing.
"""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QVBoxLayout

from goal2.ui import theme
from goal2.ui.screen import Screen, para, set_para
from goal2.ui.squad_card import Row, box, colour, last_on_the_bar

VISIBLE = 18   # [designed: s11-fixtures.html, the box's height at 1440x900 holds about eighteen rows]
# Watch, the first side, v, the second side, the match's kind, what happens at kick-off. [designed: s11-fixtures.html]
WIDTHS = (120, 300, 40, 260, 230, 0)
CHECK = "✓"   # [confirmed: t156-224-fixture-list.png, the mark on the watched row]
LATER_WATCH = ("Watching another country's match comes later (a follow-up of #560): this route's engine plays only "
               "your own match watched.")
LATER_FRIENDLY = ("Cancelling or rearranging your own friendly comes later (a follow-up of #560): this route has no "
                  "call for it yet.")
OWN_WATCHED = "Your own matches are always watched: play next game on the desk kicks this one off."
NOTE = ("✓ marks a match you will watch: your own, always. The column on the right says what happens at kick-off. "
        "Watching another country's match, and cancelling or rearranging your own friendly, come later.")


def action(row):
    """(what happens at kick-off, the Enter hint, Enter's answer) for one fixture row of the model."""
    if row["own"]:
        if row["kind"] == 1:
            return "your match", "Cancel or rearrange: later", LATER_FRIENDLY
        return "your match", "Watch match", OWN_WATCHED
    return "auto result", "Watch match: later", LATER_WATCH


class FixturesScreen(Screen):
    title = "fixture list"

    def __init__(self, window, model, country=None, back="desk"):
        self.escape_text = back
        super().__init__(window)
        self.model = model
        self.country = country
        self.listing = model.fixture_list(country)
        self.items = self.listing["rows"] if self.listing else []
        self.index = 0
        self.top = 0
        self.message = ""
        if country is not None:
            self.name_label.setText(f"fixture list · {model.goaldat.country_names[country]}")
        self.bind((Qt.Key.Key_Up,), "", lambda: self.move(-1), shown=False)
        self.bind((Qt.Key.Key_Down,), "", lambda: self.move(1), shown=False)
        self.bind((), "scroll", None, captions=("↑", "↓"))
        last_on_the_bar(self, self.escape_text)
        self._build()
        self.set_enter("", self.enter)
        self._show()

    def _build(self):
        frame, inner = box(self.heading())
        inner.setSpacing(0)
        inner.addSpacing(10)
        header = Row(-1, WIDTHS, margins=(8, 4, 8, 4), underline=True)
        header.set(("WATCH", "", "", "", "MATCH", "AT KICK-OFF"), (theme.HEADING,) * len(WIDTHS))
        header.setCursor(Qt.CursorShape.ArrowCursor)
        self._align(header)
        inner.addWidget(header)
        self.rows = []
        for i in range(VISIBLE):
            row = Row(i, WIDTHS, margins=(8, 5, 8, 5), underline=True)
            self._align(row)
            row.chosen.connect(self.click_row)
            inner.addWidget(row)
            self.rows.append(row)
        inner.addSpacing(12)
        self.empty = para("", "sub")
        inner.addWidget(self.empty)
        inner.addWidget(para(NOTE, "sub"))
        inner.addSpacing(8)
        self.note = para("", "sub")
        colour(self.note, theme.VALUE)
        inner.addWidget(self.note)
        inner.addStretch(1)
        column = QVBoxLayout()
        column.addWidget(frame, 1)
        self.body_layout.addLayout(column, 1)

    @staticmethod
    def _align(row):
        row.cells[0].setAlignment(Qt.AlignmentFlag.AlignCenter)
        row.cells[1].setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        row.cells[2].setAlignment(Qt.AlignmentFlag.AlignCenter)

    def heading(self):
        if self.listing is None:
            return "Fixtures and results"
        if self.country is not None:
            return f"Fixtures · {self.model.goaldat.country_names[self.country]} · the coming matches"
        return f"Fixtures and results · round {self.listing['round']}"

    # What is shown.
    def _show(self):
        self.top = max(0, min(self.top, self.index, len(self.items) - VISIBLE))
        if self.index >= self.top + VISIBLE:
            self.top = self.index - VISIBLE + 1
        for i, row in enumerate(self.rows):
            n = self.top + i
            if n >= len(self.items):
                row.hide()
                continue
            item = self.items[n]
            happens = action(item)[0]
            tone = theme.VALUE if item["own"] else theme.TEXT_BRIGHT
            row.set((CHECK if item["watch"] else "", item["first_name"], "v", item["second_name"], item["kind_name"],
                     happens), (tone, tone, theme.TEXT_NORMAL, tone, tone, tone))
            row.set_on(n == self.index)
            row.show()
        if self.listing is None:
            empty = "This career has no fixture schedule (a standalone friendly or an older save)."
        elif not self.items:
            empty = "No coming fixtures: the stage is complete, and the next one is not reached yet (T170)."
        else:
            empty = f"{self.index + 1} of {len(self.items)}"
        set_para(self.empty, empty)
        set_para(self.note, self.message)
        self.set_enter(action(self.items[self.index])[1] if self.items else "", self.enter)

    def shown_rows(self):
        """The rows as they read: (watch, first, v, second, kind, at kick-off)."""
        return [tuple(row.texts()) for row in self.rows if not row.isHidden()]

    # The keys.
    def move(self, step):
        if not self.items:
            return
        self.index = max(0, min(self.index + step, len(self.items) - 1))
        self.message = ""
        self._show()

    def click_row(self, i):
        n = self.top + i
        if n == self.index:
            return self.enter()
        if n < len(self.items):
            self.index = n
            self.message = ""
            self._show()
        return None

    def enter(self):
        """What the highlighted row's action names; on this route each says what it does or when it comes."""
        if not self.items:
            return
        self.message = action(self.items[self.index])[2]
        set_para(self.note, self.message)
