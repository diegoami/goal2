"""S12 Tournament: the groups, their tables and matches.

[designed: owner, 2026-11-03, #526; docs/design/ui-2026-11, S12 and its mockup s12-tournament.html; T178, #560] The
display (Qualifying, Finals, Championship) and the continent as tabs; the group's table, P W D L F A T, beside the
group's matches; the competition's banner at the title bar's right end [confirmed: T156-R1 steps 227–231, 316;
docs/original-game/images/t156-227-tournament-europe.png, t156-228-tournament-americas.png (the banner names the
continent shown: "American Championship"), t156-229-tournament-finals.png and t156-230-tournament-championship.png
(the Finals and Championship displays print FINALS), t156-316-group-table.png; M244-G1A-03 step 8]:

- **↑↓** another group of the continent, **Space** the next continent, **←→** the display, **Esc** the desk; a click
  on a tab chooses it, as its key does. Read only.
- **Ins** the Championship results, on the Finals display only: the original prints *Hit Ins for Championship
  results* from a World Cup bracket (M244-G4C-05 step 9) and prints no such line on the opening stage's displays
  (t156-229, t156-230) [confirmed: docs/original-game/coverage.md, T156-R1 step 231]. This route does not reach that
  bracket, so Ins says so [designed: T178, T242].
- It opens on the managed country's continent and group, on Qualifying.

Every number is the route's (`DesktopModel.tournament`: the world state's groups, `standings.group_table`); the
managed group's table is `competition_table`'s. The route plays only the opening stage until T170, so *Finals* and
*Championship* read *not reached yet*, as does a stage whose groups the route does not keep. The continents' order
on the tabs and under Space is the mockup's (Europe, Africa, Americas, Asia), the original's two rows read left to
right [designed: s12-tournament.html; t156-227: Europe, Africa / Americas, Asia].
"""
from __future__ import annotations

import html

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QHBoxLayout

from goal2.desktop.model import CHAMPIONSHIPS
from goal2.ui import theme
from goal2.ui.screen import Clickable, Screen, label, set_para
from goal2.ui.squad_card import colour, last_on_the_bar

DISPLAYS = ("Qualifying", "Finals", "Championship")   # [confirmed: t156-227, the display buttons]
# (continent number, tab) in the tabs' order. [confirmed: t156-227's continent buttons; F007 numbers 1..4 Europe,
# America, Africa, Asia]
TABS = ((1, "Europe"), (3, "Africa"), (2, "Americas"), (4, "Asia"))
GROUPS = 8   # [confirmed: F023 §3, eight groups per continent]
LETTERS = "ABCDEFGH"   # [confirmed: t156-227 "Group C"]
TABLE = (17, 4, 4, 4, 4, 4, 4, 4)   # team, P W D L F A T [designed: s12-tournament.html]
MATCH = (17, 10, 17)   # first side, score or v, second side
MATCH_ROWS = 12   # [confirmed: F023 §3, a double round robin of four: twelve matches; t156-227 lists twelve]
NOT_REACHED = "not reached yet"
LATER = ("The {display} display is not reached yet: this route plays only the opening stage until T170, and keeps "
         "no finals.")
NO_GROUPS = "This route keeps no groups for this stage yet: not reached yet (T170)."
INS = "The Championship results come with a World Cup bracket, which this route does not reach yet (T170)."


class Tab(Clickable):
    """A tab, as the mockup's `.btn`, highlighted as the original's selected button."""

    def __init__(self, text, handler):
        super().__init__("option")
        layout = QHBoxLayout(self)
        layout.setContentsMargins(14, 6, 14, 6)
        self.text_label = label(text, "optionText")
        layout.addWidget(self.text_label)
        self.setProperty("on", False)
        self.clicked.connect(handler)

    def set_on(self, on):
        self.setProperty("on", bool(on))
        from goal2.ui.start_look import refresh
        refresh(self)


class TournamentScreen(Screen):
    GRID = True   # [designed: owner, #667; T213]
    title = "tournament"
    escape_text = "desk"

    def __init__(self, window, model):
        super().__init__(window)
        self.model = model
        self.view = model.tournament()
        self.display = 0
        own = next((g for g in self.view["groups"] if g["managed"]), None) if self.view else None
        continent = own["continent"] if own else model.continent()
        self.tab = next(i for i, (number, _) in enumerate(TABS) if number == continent)
        self.group = own["group"] - 1 if own else 0
        self.message = ""
        from goal2.ui.cells import CellLabel
        self.banner = CellLabel("", "who")
        self.banner.setTextFormat(Qt.TextFormat.RichText)
        self.name_label.parentWidget().layout().addWidget(self.banner)
        self.bind((Qt.Key.Key_Up,), "", lambda: self.move_group(-1), shown=False)
        self.bind((Qt.Key.Key_Down,), "", lambda: self.move_group(1), shown=False)
        self.bind((), "group", None, captions=("↑", "↓"))
        self.bind((Qt.Key.Key_Space,), "continent", self.next_continent)
        self.bind((Qt.Key.Key_Left,), "", lambda: self.move_display(-1), captions=("←",), shown=False)
        self.bind((Qt.Key.Key_Right,), "", lambda: self.move_display(1), captions=("→",), shown=False)
        self.bind((), "display", None, captions=("←", "→"))
        self.bind((Qt.Key.Key_Insert,), "Championship results", self.championship_results)
        # [confirmed: t156-229-tournament-finals.png, t156-230-tournament-championship.png; M244-G4C-05 step 9,
        # m244-world-finals-bracket.png] The opening stage's Qualifying and Championship displays print no "Hit Ins
        # for Championship results" line; the World Cup bracket's Finals display does. The key is shown there only.
        self.ins_key = self.bindings[-1]
        self.ins_key.shown = False
        last_on_the_bar(self, self.escape_text)
        self._build()
        self._show()

    def _build(self):
        """[designed: owner, #667; T213] Tabs over the table and the twelve matches, in two framed cell columns."""
        from goal2.ui.cells import Cells, CellPara, CellLabel
        from goal2.ui.cell_parts import CellTableRow
        from goal2.ui.country_parts import framed
        body = Cells(90, 25, "tournamentBody")
        self.body_layout.addWidget(body, 1)
        body.text("display", "sub", 0, 0, 8)
        body.text("continent", "sub", 45, 0, 9)
        self.display_tabs = []
        self.continent_tabs = []
        for labels, store, start, step, width, choose in (
                (DISPLAYS,self.display_tabs,0,15,15,self.choose_display),
                ([name for _,name in TABS],self.continent_tabs,45,11,11,self.choose_continent)):
            for i, text in enumerate(labels):
                tab = Tab(text, lambda i=i, choose=choose: choose(i))
                tab.setObjectName("gridLine")
                tab.layout().setContentsMargins(0,0,0,0)
                old = tab.text_label
                tab.layout().removeWidget(old)
                old.setParent(None)
                old.deleteLater()
                tab.text_label = CellLabel(text,"optionText")
                tab.layout().addWidget(tab.text_label)
                body.put(tab,start+i*step,1,width)
                store.append(tab)
        table, inner = framed("", 45, 19)
        self.table_area = inner
        self.table_heading = table.rule
        self.header = CellTableRow(-1,TABLE)
        self.header.set(("team","P","W","D","L","F","A","T"),(theme.HEADING,)*8)
        self.header.setCursor(Qt.CursorShape.ArrowCursor)
        self._centre(self.header)
        inner.put(self.header,0,0,45)
        self.table_rows = []
        for i in range(4):
            row = CellTableRow(i,TABLE)
            row.setCursor(Qt.CursorShape.ArrowCursor)
            self._centre(row)
            inner.put(row,0,(2,6,10,18)[i],45)
            self.table_rows.append(row)
        self.note = CellPara("","sub")
        inner.put(self.note,0,14,45,3)
        self.message_label = CellPara("","sub")
        colour(self.message_label,theme.VALUE)
        inner.put(self.message_label,0,11,45,3)
        body.put(table,0,4,45,20)
        matches, inner = framed("",44,19)
        self.matches_heading = matches.rule
        self.match_rows = []
        for i in range(MATCH_ROWS):
            row = CellTableRow(i,MATCH,aligns=(Qt.AlignmentFlag.AlignRight,Qt.AlignmentFlag.AlignHCenter,None))
            row.setCursor(Qt.CursorShape.ArrowCursor)
            inner.put(row,0,round(i*18/11),44)
            self.match_rows.append(row)
        body.put(matches,46,4,44,20)

    @staticmethod
    def _centre(row):
        for cell in row.cells[1:]:
            cell.setAlignment(Qt.AlignmentFlag.AlignCenter)

    # What is shown.
    def continent(self):
        return TABS[self.tab][0]

    def shown_group(self):
        """The group on screen, from the model's view, or None (not reached yet)."""
        if self.view is None or self.display != 0:
            return None
        return next(g for g in self.view["groups"]
                    if g["continent"] == self.continent() and g["group"] == self.group + 1)

    def _show(self):
        for i, tab in enumerate(self.display_tabs):
            tab.set_on(i == self.display)
        for i, tab in enumerate(self.continent_tabs):
            tab.set_on(i == self.tab)
        banner = self.model.competition(self.continent(), None if self.display == 0 else "FINALS")
        self.banner.setText(banner_text(banner))
        group = self.shown_group()
        own = self.model.state.managed_country
        if group is None:
            self.table_area.move(self.note,0,3,45,5)
            self.table_area.move(self.message_label,0,10,45,6)
            self.table_heading.setText((DISPLAYS[self.display] + " · " + NOT_REACHED).upper())
            self.matches_heading.setText("MATCHES")
            self.header.hide()
            for row in self.table_rows + self.match_rows:
                row.hide()
            set_para(self.note, NO_GROUPS if self.display == 0 else LATER.format(display=DISPLAYS[self.display]))
        else:
            self.table_area.move(self.note,0,14,45,3)
            self.table_area.move(self.message_label,0,11,45,3)
            letter = LETTERS[group["group"] - 1]
            stage = self.view["stage"]
            what = ("World Cup qualifying" if stage >= 5
                    else CHAMPIONSHIPS[group["continent"]].split()[0].lower() + " qualifying")
            self.table_heading.setText(f"GROUP {letter} · {what}".upper())
            self.matches_heading.setText(f"GROUP {letter} MATCHES")
            self.header.show()
            for row, data in zip(self.table_rows, group["rows"]):
                tone = theme.VALUE if data["country"] == own else theme.TEXT_BRIGHT
                row.set((data["name"], str(data["played"]), str(data["won"]), str(data["drawn"]), str(data["lost"]),
                         str(data["goals_for"]), str(data["goals_against"]), str(data["points"])),
                        (tone,) * len(TABLE))
                row.show()
            for i, row in enumerate(self.match_rows):
                if i >= len(group["matches"]):
                    row.hide()
                    continue
                match = group["matches"][i]
                score = "v" if match["score"] is None else f"{match['score'][0]}–{match['score'][1]}"
                mine = own in (match["first"], match["second"])
                tone = theme.VALUE if mine else theme.TEXT_BRIGHT
                row.set((match["first_name"], score, match["second_name"]),
                        (tone, theme.TEXT_BRIGHT if match["score"] else theme.TEXT_NORMAL, tone))
                row.show()
            set_para(self.note, f"Group {group['group']} of {GROUPS} · ↑↓ another group, Space another continent.")
        set_para(self.message_label, self.message)

    def table(self):
        """The table as it reads: (team, P, W, D, L, F, A, T) per row; [] when not reached."""
        return [tuple(row.texts()) for row in self.table_rows if not row.isHidden()]

    def matches(self):
        return [tuple(row.texts()) for row in self.match_rows if not row.isHidden()]

    # The keys.
    def move_group(self, step):
        self.group = max(0, min(self.group + step, GROUPS - 1))
        self.message = ""
        self._show()

    def next_continent(self):
        self.choose_continent((self.tab + 1) % len(TABS))

    def choose_continent(self, i):
        self.tab = i
        self.message = ""
        self._show()

    def move_display(self, step):
        self.choose_display(max(0, min(self.display + step, len(DISPLAYS) - 1)))

    def choose_display(self, i):
        self.display = i
        self.ins_key.shown = i == DISPLAYS.index("Finals")   # [confirmed: the original prints the Ins line there]
        self._refresh_bar()
        self.message = ""
        self._show()

    def championship_results(self):
        self.message = INS
        set_para(self.message_label, INS)


def banner_text(banner):
    """The banner as rich text: the year in yellow, the name in the banner's light red, the phase in yellow, as the
    mockup draws it [designed: s12-tournament.html, s06-hub.html]."""
    if banner is None:
        return ""
    year = f'<span style="color:{theme.VALUE}">{banner["year"]}</span> '
    name = f'<span style="color:{theme.TITLE_BANNER}">{html.escape(banner["name"])}</span>'
    phase = (f' <span style="color:{theme.TEXT_NORMAL}">·</span> <span style="color:{theme.VALUE}">'
             f'{html.escape(banner["phase"])}</span>' if banner["phase"] else "")
    return year + name + phase
