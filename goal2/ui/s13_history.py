"""S13 History: how the country has done over the seasons.

[designed: owner, 2026-11-03, #526; docs/design/ui-2026-11, S13 and its mockup s13-history.html; T178, #560] The
design's five boxes, in the mockup's places: statistics and successes, the results by season beside the top scorers
and caps, and the records [confirmed: M244-G1A-03 step 12, docs/original-game/images/m244-history.png]. **Esc** the
desk; read only.

Only the results box has a source on the Python route: this career's results (`DesktopModel.history`, from
`campaign.results`), one row per season and competition (season, competition, W D L F A, best place) and under it
the season's results as played, friendlies too. The original's history is not decoded (goal2-archaeology
spec/team-analysis.md C-TEAM-12) and the route keeps no runs, successes, scorers, caps or records, so those four
boxes say they are kept from a later version, naming #509 Track B; the template's memory holds another career's
history, so no value is read from it [designed: T178's task, "no value is shown from the template's memory"].
"""
from __future__ import annotations

from PySide6.QtCore import Qt

from goal2.ui import theme
from goal2.ui.screen import Screen, para, set_para
from goal2.ui.squad_card import last_on_the_bar

LATER = "Kept from a later version: this route keeps no {what} yet (#509, Track B)."
SEASON = (8, 12, 4, 4, 4, 4, 4, 50)   # season, competition, W D L F A, best place [designed: s13-history.html]
RESULT = (0, 16, 9, 16, 49)   # a result under its season: (indent), first side, score, second side, kind
ROWS = 9   # [designed: the results box's height at 1440x900]


class HistoryScreen(Screen):
    GRID = True   # [designed: owner, #667; T213]
    title = "history"
    escape_text = "desk"

    def __init__(self, window, model):
        super().__init__(window)
        self.model = model
        self.seasons = model.history() or []
        self.name_label.setText(f"history · {model.goaldat.country_names[model.state.managed_country]}")
        last_on_the_bar(self, self.escape_text)
        self._build()
        self._show()

    def _build(self):
        """[designed: owner, #667; T213] Results retain nine lines; the four explicit unavailable panels keep their complete words."""
        from goal2.ui.cells import Cells, CellPara
        from goal2.ui.cell_parts import CellTableRow
        from goal2.ui.country_parts import framed
        body = Cells(90,25,"historyBody")
        self.body_layout.addWidget(body,1)
        self.later = {}
        self.later_frames = {}
        self.area = body
        for title,key,what,col,row,cols,rows in (
                ("statistics","statistics","runs of wins and defeats",0,0,22,6),
                ("successes","successes","successes",23,0,22,6),
                ("top scorers","scorers","scorers",46,0,22,6),
                ("top caps","caps","caps",69,0,21,6),
                ("records","records","biggest wins and defeats",0,21,90,4)):
            frame,inner = framed(title,cols,rows-1)
            text = CellPara(LATER.format(what=what),"sub")
            inner.put(text,0,0,cols,rows-1)
            self.later[key] = text
            self.later_frames[key] = (frame,inner,text)
            body.put(frame,col,row,cols,rows)
        frame,inner = framed("results",90,13)
        self.result_frame, self.result_area = frame, inner
        header = CellTableRow(-1,SEASON)
        header.set(("season","","W","D","L","F","A","best place"),(theme.HEADING,)*8)
        self._centre(header)
        inner.put(header,0,0,90)
        self.rows = []
        for i in range(ROWS):
            season = CellTableRow(i,SEASON)
            self._centre(season)
            result = CellTableRow(i,RESULT)
            result.cells[0].hide()
            result.cells[1].setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            result.cells[2].setAlignment(Qt.AlignmentFlag.AlignCenter)
            # [designed: T213] The full-width result keeps the longest stage name on its existing line.
            for row in (season,result):
                row.setCursor(Qt.CursorShape.ArrowCursor)
                inner.put(row,0,i+1,90)
            self.rows.append((season,result))
        self.results_note = CellPara("","sub")
        inner.put(self.results_note,0,10,90,3)
        body.put(frame,0,7,90,14)

    @staticmethod
    def _later(inner, what):
        text = para(LATER.format(what=what), "sub")
        inner.addWidget(text)
        inner.addStretch(1)
        return text

    @staticmethod
    def _centre(row):
        for cell in row.cells[2:7]:
            cell.setAlignment(Qt.AlignmentFlag.AlignCenter)

    def lines(self):
        """(season, competition, W, D, L, F, A, best) and the results under it, as rows of texts."""
        out = []
        for season in self.seasons:
            out.append(("season", (season["season"], season["competition"], str(season["won"]),
                                   str(season["drawn"]), str(season["lost"]), str(season["goals_for"]),
                                   str(season["goals_against"]), season["best"])))
            for result in season["results"]:
                out.append(("result", ("", result["first_name"], f"{result['score'][0]} v {result['score'][1]}",
                                       result["second_name"], result["kind_name"])))
        return out

    def _show(self):
        lines = self.lines()
        # [designed: T213] A fresh career has only a season line. Use two wide rows of notices around that short table;
        # once there are more results, the full nine-line table gets the middle and the notices share the top row.
        sparse = len(lines) <= 3
        placements = ({"statistics":(0,0,45,5),"successes":(46,0,44,5),"scorers":(0,15,45,5),"caps":(46,15,44,5)}
                      if sparse else {"statistics":(0,0,22,6),"successes":(23,0,22,6),"scorers":(46,0,22,6),"caps":(69,0,21,6)})
        for key,(col,row,cols,rows) in placements.items():
            frame,inner,text = self.later_frames[key]
            inner.cols,inner.rows = cols,rows-1
            inner.grid.cols,inner.grid.rows = cols,rows-1
            inner.move(text,0,0,cols,rows-1)
            self.area.move(frame,col,row,cols,rows)
        self.result_area.rows = self.result_area.grid.rows = 7 if sparse else 13
        self.area.move(self.result_frame,0,6 if sparse else 7,90,8 if sparse else 14)
        self.result_area.move(self.results_note,0,4 if sparse else 10,90,3)
        for i, (season, result) in enumerate(self.rows):
            kind, texts = lines[i] if i < len(lines) else (None, ())
            season.setVisible(kind == "season")
            result.setVisible(kind == "result")
            if kind == "season":
                season.set(texts, (theme.TEXT_BRIGHT,) * 7 + (theme.VALUE,))
            elif kind == "result":
                # A result under its season: the two sides, the score and the kind [designed: T178, the box lists
                # the results the route keeps].
                result.set(texts, (theme.TEXT_NORMAL, theme.TEXT_BRIGHT, theme.VALUE, theme.TEXT_BRIGHT,
                                   theme.TEXT_NORMAL))
        hidden = len(lines) - len(self.rows)
        note = "This career's results, the season's competition counted on its row; friendlies are listed under it."
        if hidden > 0:
            note += f" {hidden} older lines are not shown."
        set_para(self.results_note, note)

    def shown_texts(self):
        return [tuple(row.texts()) for pair in self.rows for row in pair if not row.isHidden()]
