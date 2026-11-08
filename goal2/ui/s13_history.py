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
from PySide6.QtWidgets import QHBoxLayout, QVBoxLayout

from goal2.ui import theme
from goal2.ui.screen import Screen, para, set_para
from goal2.ui.squad_card import Row, box, colour, last_on_the_bar

LATER = "Kept from a later version: this route keeps no {what} yet (#509, Track B)."
SEASON = (110, 120, 50, 50, 50, 50, 50, 0)   # season, competition, W D L F A, best place [designed: s13-history.html]
RESULT = (110, 0, 90, 0, 140)   # a result under its season: (indent), first side, score, second side, kind
ROWS = 9   # [designed: the results box's height at 1440x900]


class HistoryScreen(Screen):
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
        top = QHBoxLayout()
        top.setSpacing(18)
        self.later = {}
        statistics, inner = box("Statistics")
        self.later["statistics"] = self._later(inner, "runs of wins and defeats")
        top.addWidget(statistics, 1)
        successes, inner = box("Successes")
        successes.setFixedWidth(360)
        self.later["successes"] = self._later(inner, "successes")
        top.addWidget(successes)
        self.body_layout.addLayout(top)
        middle = QHBoxLayout()
        middle.setSpacing(18)
        results, inner = box("Results")
        inner.setSpacing(0)
        inner.addSpacing(10)
        header = Row(-1, SEASON, margins=(8, 4, 8, 4), underline=True)
        header.set(("SEASON", "", "W", "D", "L", "F", "A", "BEST PLACE"), (theme.HEADING,) * len(SEASON))
        header.setCursor(Qt.CursorShape.ArrowCursor)
        self._centre(header)
        inner.addWidget(header)
        # Each line is a season's row or a result under it: both are made now, one of them shown.
        self.rows = []
        for i in range(ROWS):
            season = Row(i, SEASON, margins=(8, 4, 8, 4), underline=True)
            self._centre(season)
            result = Row(i, RESULT, margins=(8, 4, 8, 4), underline=True)
            result.cells[1].setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            result.cells[2].setAlignment(Qt.AlignmentFlag.AlignCenter)
            for row in (season, result):
                row.setCursor(Qt.CursorShape.ArrowCursor)
                inner.addWidget(row)
            self.rows.append((season, result))
        inner.addSpacing(8)
        self.results_note = para("", "sub")
        inner.addWidget(self.results_note)
        inner.addStretch(1)
        middle.addWidget(results, 1)
        scorers, inner = box("Top scorers")
        scorers.setFixedWidth(300)
        self.later["scorers"] = self._later(inner, "scorers")
        middle.addWidget(scorers)
        caps, inner = box("Top caps")
        caps.setFixedWidth(300)
        self.later["caps"] = self._later(inner, "caps")
        middle.addWidget(caps)
        self.body_layout.addLayout(middle, 1)
        records, inner = box("Records")
        self.later["records"] = self._later(inner, "biggest wins and defeats")
        column = QVBoxLayout()
        column.addWidget(records)
        self.body_layout.addLayout(column)

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
