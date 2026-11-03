"""A standalone friendly between any two countries, outside a career: a GOAL2 ADDITION, from S02.

[designed: owner, §6 item 18 (docs/design/ui-2026-11, 2026-11-03); T177, #557] The original has no friendly outside a
career; today's window has *Other games > New standalone friendly* (docs/desktop-management.md,
`DesktopModel.new_friendly`), and the owner kept it. **F** on S02 opens this screen.

- **The choice.** One list of the 128 countries in groups of 16, in world-ranking order, as S04's list under *world*
  (`s04_country.ordered`): **↑↓** country, **←→** group of 16, **Enter** chooses your country, then the opponent, and
  kicks off; **Esc** steps back (the opponent, then your country, then S02). The same country cannot play itself. A
  click on a country highlights it, a click on the highlighted one is Enter. [designed: T177, S04's keys]
- **The match** [designed: T177]: a private model, `DesktopModel.new_friendly(your country)` (fresh records, no
  campaign ledger, as today's), with the original's suggested captain as the desk's *play next game* sets it
  (`s17_pitch.suggested_captain`, T143's rule) through `DesktopModel.confirm`; then S17 plays it watched through the
  bridge, on the controller that is on main (`s17_pitch.MatchController`), your country first (the home side, light
  red). The engine's fixture index is the template's own (`Image.fixture_index`, the friendly the template was set up
  for), so no index is invented.
- **Back to S02** at full time (or on a cancel), with S17's result line on S02. Nothing is saved: the model is never
  the window's career (`window.career`), so no save question follows, and nothing calls a save.
"""
from __future__ import annotations

from types import SimpleNamespace

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QHBoxLayout, QVBoxLayout, QWidget

from goal2.desktop.model import DesktopModel
from goal2.ui.s04_country import GROUP, LIST_WIDTH, ordered, paths
from goal2.ui.screen import Screen, label, para, set_para
from goal2.ui.start_look import Row, box, key_value

ADDITION = "GOAL2 ADDITION · STANDALONE FRIENDLY"
NOTE = ("A friendly between any two countries, outside a career; nothing is saved. It plays on the pitch as your own "
        "matches do, and returns to the start screen with the result.")
STEPS = ("Choose your country", "Choose the opponent")


def standalone_fixture(model, opponent):
    """The friendly's fixture for S17's controller: your country first, the opponent, the template's own fixture
    index, a friendly (kind 1). [designed: T177]"""
    from goal2.engine.original_match import Image
    index = Image.from_memory_component(model.state.mem).fixture_index()
    return SimpleNamespace(side_a=model.state.managed_country, side_b=opponent, fixture_id=f"original:{index}", kind=1)


def new_friendly(target, country):
    """The private model of a standalone friendly for `country`: `DesktopModel.new_friendly`, as today's window, with
    the original's suggested captain set through `confirm`, as the desk's *play next game* does. Its save path is
    never written."""
    from goal2.ui.s17_pitch import suggested_captain
    template, data, save = paths(target)
    model = DesktopModel.open(template, data, save.with_name(f"standalone-friendly{save.suffix}"), country=country)
    model.new_friendly(country)
    state = model.state
    captain = suggested_captain(state)
    if captain is not None:
        model.confirm(list(state.starting_eleven or state.managed_squad[:11]), captain, state.country_tactics)
    return model


class FriendlyScreen(Screen):
    title = "standalone friendly"
    pre_game = True

    def __init__(self, window):
        super().__init__(window)
        self.target = window.target
        self.browser = DesktopModel.open(*paths(self.target), country=1)   # the names and ranks only
        self.order = ordered(self.browser.countries(), False)
        self.index = 0
        self.chosen = []   # your country, then the opponent: country numbers
        self.model = None
        self.bind((Qt.Key.Key_Up,), "", lambda: self.move(-1), shown=False)
        self.bind((Qt.Key.Key_Down,), "", lambda: self.move(1), shown=False)
        self.bind((), "country", None, captions=("↑", "↓"))
        self.bind((Qt.Key.Key_Left,), "", lambda: self.group(-1), captions=("←",), shown=False)
        self.bind((Qt.Key.Key_Right,), "", lambda: self.group(1), captions=("→",), shown=False)
        self.bind((), "group of 16", None, captions=("←", "→"))
        esc = next(b for b in self.bindings if Qt.Key.Key_Escape in b.keys)
        self.bindings.remove(esc)
        self.bindings.append(esc)
        self._refresh_bar()
        self._build()
        self.set_enter("", self.choose)
        self._show()

    # The screen.
    def _build(self):
        row = QHBoxLayout()
        row.setSpacing(18)
        left_widget = QWidget()
        left = QVBoxLayout(left_widget)
        left.setContentsMargins(0, 0, 0, 0)
        left.setSpacing(14)
        tag = QHBoxLayout()
        tag.addWidget(label(ADDITION, "tagNew"))
        tag.addStretch(1)
        left.addLayout(tag)
        match, inner = box("The friendly")
        rows, self.sides = key_value((("yours", "your country"), ("opponent", "opponent")))
        inner.addWidget(rows)
        left.addWidget(match)
        self.step = label("", "h1")
        left.addWidget(self.step)
        self.note = para(NOTE, "sub")
        left.addWidget(self.note)
        left.addStretch(1)
        row.addWidget(left_widget, 1)
        countries, inner = box()
        countries.setFixedWidth(LIST_WIDTH)
        inner.addWidget(label("COUNTRIES · WORLD RANK", "boxHeading"))
        inner.setSpacing(0)
        inner.addSpacing(8)
        self.rows = []
        for i in range(GROUP):
            r = Row([None, 40], on_click=lambda i=i: self.click_row(i))
            r.cells[1].setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            inner.addWidget(r)
            self.rows.append(r)
        inner.addSpacing(10)
        self.group_note = label("", "sub")
        inner.addWidget(self.group_note)
        inner.addStretch(1)
        row.addWidget(countries)
        self.body_layout.addLayout(row, 1)

    def name(self, number):
        return self.browser.goaldat.country_names[number]

    def _show(self):
        start = self.index // GROUP * GROUP
        for i, row in enumerate(self.rows):
            number, country_name, world, _, _ = self.order[start + i]
            row.set_cells([country_name, str(world)])
            row.set_on(start + i == self.index)
        self.group_note.setText(f"{start + GROUP} of {len(self.order)} · ←→ next group")
        for key, i in (("yours", 0), ("opponent", 1)):
            self.sides[key].setText(self.name(self.chosen[i]) if len(self.chosen) > i else "—")
        highlighted = self.order[self.index][1]
        if len(self.chosen) == 0:
            self.step.setText(STEPS[0])
            self.set_enter(f"Choose {highlighted}", self.choose)
        else:
            self.step.setText(STEPS[1])
            self.set_enter(f"Kick off v {highlighted}", self.choose)
        self.escape_binding().text = "back" if self.chosen else "start screen"
        self._refresh_bar()

    def escape_binding(self):
        return next(b for b in self.bindings if Qt.Key.Key_Escape in b.keys)

    def say(self, text):
        set_para(self.note, text)

    def visible_names(self):
        return [row.cells[0].text() for row in self.rows]

    # The keys.
    def move(self, step):
        self.index = max(0, min(self.index + step, len(self.order) - 1))
        self._show()

    def group(self, step):
        groups = len(self.order) // GROUP
        self.index = max(0, min(self.index // GROUP + step, groups - 1)) * GROUP + self.index % GROUP
        self._show()

    def click_row(self, i):
        position = self.index // GROUP * GROUP + i
        if position == self.index:
            return self.choose()
        self.index = position
        self._show()
        return None

    def highlighted_country(self):
        return self.order[self.index][0]

    def choose(self):
        """Enter: your country, then the opponent, which kicks off."""
        number = self.highlighted_country()
        if not self.chosen:
            self.chosen.append(number)
            self.say(NOTE)
            self._show()
            return None
        if number == self.chosen[0]:
            self.say(f"{self.name(number)} cannot play itself: choose another country.")
            return None
        self.chosen.append(number)
        self._show()
        return self.kick_off()

    def kick_off(self):
        """S17 over S02 on the friendly; a friendly that cannot start says why here."""
        from goal2.ui.s17_pitch import MatchController, PitchScreen
        yours, opponent = self.chosen
        try:
            model = new_friendly(self.target, yours)
            controller = MatchController(model, standalone_fixture(model, opponent))
            controller.start()
        except (OSError, ValueError) as exc:
            self.chosen.pop()
            self._show()
            self.say(f"The friendly cannot start: {exc}")
            return None
        self.model = model
        window = self.window_
        window.pop()   # back to S02, which S17 returns to at full time
        try:
            screen = PitchScreen(window, model, controller)
        except BaseException:
            controller.cancel()
            raise
        return window.push(screen)

    def escape(self):
        """Esc: the opponent's choice, then your country's, then back to S02."""
        if self.chosen:
            self.chosen.pop()
            self.say(NOTE)
            self._show()
            return
        self.window_.pop()


def open_friendly(window):
    """F on S02: the friendly's country choice over it."""
    return window.push(FriendlyScreen(window))
