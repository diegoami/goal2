"""S18 Match stop: the event that stops the match, on the key line at the foot of the screen, as the original shows it.

[designed: owner, 2026-11-03, #526; T180, #574; owner, 2026-11-27, #862: on the key line, the pitch and the band in view]
[confirmed: T156-R1 steps 67-68, 149-150, 175, 274; t156-067-substitution-opportunity.png (a grey label at the left, a magenta
*press any key* at the right), t156-149-opponent-substitution.png (the grey `SUBSTITUTION`, the players in cyan),
t156-175-replay-prompt.png (the question in cyan, across the line), t156-274-quick-substitution-opportunity.png; E031 g1 step
3874, e031-shootout-start.png (green across the line); M244-G4C-07 step 55, m244-shootout-prompt.png]

The stop replaces the key line: a bar across the screen over the bottom bar, as tall as the bar (two rows) or, when its words need
more, the rows they take above it. Its last row has the headline at the left and the answer at the right; its detail sits on that row
when it fits, else on the rows above. The pitch's field and the top band are never covered.

[designed: owner #636] Opted-in substitution opportunities use the original timed poll horizon.
UI Esc accepts with original Enter, then the actual legal bench opens; an ignored notice sends
no key. Source headline0x70 and hint0x8D colours are retained; the headline blink is the
owner's adaptation, kept on the key line so the notice is as prominent as #426 asked (owner, 2026-11-27).
This is separate from the compatibility notices below.

The legacy presentation, each answered by any key:

- **SUBSTITUTION OPPORTUNITY** (`NOTICE_SUBSTITUTION`): the engine's `substitution` decision (your player injured, or
  the stoppage after a requested substitution). The key opens the match menu (S15), as in the original (T156-R1 step
  68), whose *players* opens the bench (S19) in *make substitutions now* mode.
- **The other side's substitution** (`NOTICE_OPPONENT`): "SUBSTITUTION Leonharsen on for Nilsen" in the original
  (t156-149). The engine does not wait for it; the pitch holds its display until the key, then plays on.
- **The penalty shoot-out** (`NOTICE_SHOOTOUT`): before the shoot-out order (S16), as the original's notice
  (e031-shootout-start).

The bar belongs to S17 (`PitchScreen.stop_box`); while it shows every key answers it, and a click answers as the keys do: on the
bar, Enter (any key); on an answer of a question, that answer's key. The goal questions (*action replay?*, *save this goal?*)
are T181's: `show(..., answers=...)` takes keys with their words for a question; T181 asks those questions once the goal's
sample has been painted.
"""
from __future__ import annotations

import math

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import QFrame

from goal2.ui import cells, theme
from goal2.ui.cells import CellLabel, CellPara
from goal2.ui.screen import Clickable
from goal2.ui.squad_card import colour

NOTICE_SUBSTITUTION = "substitution"
NOTICE_OPPONENT = "opponent"
NOTICE_SHOOTOUT = "shootout"
TAG = "THE MATCH STOPS"                 # [designed: s18-match-stop.png] (the box's; the key line has no tag)
ANY_KEY = "press any key"               # [confirmed: t156-067, t156-149: "press any key"]
SUBSTITUTION_OPPORTUNITY = "SUBSTITUTION OPPORTUNITY"   # [confirmed: t156-067]
NO_GOALKEEPER = "HAS NO GOALKEEPER"  # [confirmed: upstream695 keeper notice template0x0B]
SHOOTOUT = "PENALTY SHOOT-OUT"          # [confirmed: E031 C44-C46b; s17_pitch.STOPS]
SUBSTITUTION = "SUBSTITUTION"           # [confirmed: t156-149, the grey label before the players]
# [confirmed: T156-R1 steps 175–177] The goal questions; only Y or N answers them.
ACTION_REPLAY = 'Do you want an action replay?'
SAVE_GOAL = 'Do you want to save this goal?'
YES_NO = {Qt.Key.Key_Y: 'Y yes', Qt.Key.Key_N: 'N no'}
# The colours. [confirmed: t156-067 (black on grey, magenta), t156-175 (cyan), e031-shootout-start (green)]
LABEL_GREY = "#aaaaaa"
LABEL_TEXT = "#000000"
MIN_ROWS = 2   # the bottom bar's rows (Screen.KEY_ROWS): the stop covers the whole key line
# [designed: T212] The bar is the screen's width in cells; kept for the API: `cols` is set by `place`.
COLS = 40
TIMED_COLS = (24, 46)


class StopBox(QFrame):
    """The stop on the key line: its headline, its detail and the keys that answer it. `show_stop` raises it; `answer(key)` runs the
    stop's handler once and hides it."""

    def __init__(self, parent):
        super().__init__(parent)
        self.setObjectName("stopBox")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setStyleSheet(f"#stopBox {{ background: {theme.GROUND}; }}")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.cols = COLS
        self.tag = CellLabel(TAG, "tag", self)   # the box's tag: the key line has none
        self.tag.hide()
        self.headline = CellLabel("", "h1", self)
        self.label = CellLabel("", "h1", self)    # a notice's grey label when its headline is split (t156-149)
        self.rest = CellLabel("", "value", self)  # the rest of a split headline, cyan
        self.detail = CellPara("", "value", self)
        self.key_hint = CellLabel(ANY_KEY, "keyLabel", self)
        self.key_hint.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self.answer_items = {}
        self.kind = None
        self.handler = None
        self.answers = {}
        self.timed = False
        self._inline = True
        self.opportunity_timer = QTimer(self)
        self.opportunity_timer.setSingleShot(True)
        self.opportunity_timer.timeout.connect(self._expire_opportunity)
        self.blink_timer = QTimer(self)
        self.blink_timer.setInterval(250)
        self.blink_timer.timeout.connect(self._blink_opportunity)
        self._opportunity_lit = True
        self.hide()

    def show_stop(self, kind, headline, detail, handler, answers=None):
        """Show a stop: `handler(key)` runs once on the answering key. `answers` {Qt key: words} makes it a
        question answered only by those keys (T181); without it any key answers, as the original's notices."""
        self.cancel()
        self.setStyleSheet(f"#stopBox {{ background: {theme.GROUND}; }}")
        self.detail.setStyleSheet("")
        self.kind, self.handler, self.answers = kind, handler, dict(answers or {})
        self.headline.setText(headline)
        self.detail.setText(detail)
        self.key_hint.setText(" · ".join(self.answers.values()) if self.answers else ANY_KEY)
        split = kind == NOTICE_OPPONENT and headline.startswith(SUBSTITUTION + " ")
        self.label.setText(SUBSTITUTION if split else "")
        self.rest.setText(headline[len(SUBSTITUTION) + 1:] if split else "")
        self.headline.setVisible(not split)
        self.label.setVisible(split)
        self.rest.setVisible(split)
        self.detail.setVisible(bool(detail))
        self._answer_items()
        if self.answers:
            # [confirmed: t156-175] a question is cyan across the line
            colour(self.headline, theme.HEADING)
            colour(self.key_hint, theme.HEADING)
        elif kind == NOTICE_SHOOTOUT:
            # [confirmed: e031-shootout-start.png] the shoot-out's notice is green
            colour(self.headline, theme.GOALKEEPER)
            colour(self.key_hint, theme.GOALKEEPER)
        else:
            # [confirmed: t156-067, t156-149] a notice's label is black on grey, its key hint magenta
            for widget in (self.headline, self.label):
                widget.setStyleSheet(f"color: {LABEL_TEXT}; background: {LABEL_GREY};")
            colour(self.key_hint, theme.KEY_HINT)
        colour(self.rest, theme.HEADING)
        colour(self.detail, theme.TEXT_NORMAL)
        self.place()
        self.show()
        self.raise_()

    def _answer_items(self):
        """A question's answers as clickable words at the right; a notice's key hint is one label."""
        for item in self.answer_items.values():
            item.setParent(None)
            item.deleteLater()
        self.answer_items = {}
        for key, words in self.answers.items():
            item = Clickable("stopAnswer", self)
            text = CellLabel(words, "keyLabel", item)
            colour(text, theme.HEADING)
            item.text = text
            item.clicked.connect(lambda k=key: self._click(k))
            item.show()
            self.answer_items[key] = item
        self.key_hint.setVisible(not self.answers)

    def show_opportunity(self, data, handler, *, detail=None):
        """[confirmed: original7FCF/CC2E; #695]400/1000 polls,10 nominal ms.
        [designed: owner #636] Flashing heading; UI Esc accepts. [designed: owner, 2026-11-27, #862] On the key line.
        Ordinary source headline0x70 is black on gray; keeper source0x0B is
        light cyan on black (HAS NO GOALKEEPER). Both hints use blinking magenta0x8D.
        The headline blink is the owner's presentation adaptation.
        """
        # Full packets are validated before the view. This method also supports
        # the focused widget's minimal timing input without constructing a stop.
        from goal2.game.native_choice import opportunity_duration
        duration = opportunity_duration(data)
        keeper = data['keeper_unavailable']
        self.show_stop(NOTICE_SUBSTITUTION, NO_GOALKEEPER if keeper else SUBSTITUTION_OPPORTUNITY, detail or '', handler)
        self.timed = True
        self._opportunity_keeper = keeper
        self.detail.setVisible(bool(detail))
        if detail:
            colour(self.detail, '#55ffff' if keeper else theme.TEXT_BRIGHT)
        background = '#000000' if keeper else LABEL_GREY
        self.setStyleSheet(f'#stopBox {{ background: {theme.GROUND}; }} #stopBox #h1 {{ background: {background}; }}')
        self.key_hint.setText('Esc / Enter: open the bench')
        self._opportunity_lit = True
        self._opportunity_colours()
        self.place();self.raise_()
        self.blink_timer.start()
        self.opportunity_timer.start(duration)

    def _opportunity_colours(self):
        keeper = self._opportunity_keeper
        foreground = ('#55ffff' if keeper else '#000000') if self._opportunity_lit else ('#000000' if keeper else LABEL_GREY)
        background = '#000000' if keeper else LABEL_GREY
        self.headline.setStyleSheet(f'color:{foreground};background:{background};')
        self.key_hint.setStyleSheet(f"color:{'#ff55ff' if self._opportunity_lit else '#000000'};background:#000000;")

    def _blink_opportunity(self):
        if self.timed and self.open:
            self._opportunity_lit = not self._opportunity_lit
            self._opportunity_colours()

    def _expire_opportunity(self):
        if self.timed and self.open:
            self.answer(None)

    def cancel(self):
        self.opportunity_timer.stop();self.blink_timer.stop()
        self.timed = False
        self.kind, self.handler, self.answers = None, None, {}
        self.hide()

    @property
    def open(self):
        return self.kind is not None

    def texts(self):
        """The stop as it reads: (headline, detail, key hint)."""
        return self.headline.text(), self.detail.text(), self.key_hint.text()

    def answer(self, key):
        """A key while the stop shows: the stop's handler, once. False when the key does not answer a question."""
        if self.kind is None or (self.answers and key not in self.answers):
            return False
        handler = self.handler
        self.opportunity_timer.stop(); self.blink_timer.stop(); self.timed = False
        self.kind, self.handler, self.answers = None, None, {}
        self.hide()
        if handler is not None:
            handler(key)
        return True

    # The mouse: a click answers as the keys do. [designed: owner, 2026-11-03, #526: "the mouse does what the keys do"]
    def _click(self, key):
        screen = self.parentWidget()
        answer = getattr(screen, "answer_stop_box", None)
        return answer(key) if answer is not None else self.answer(key)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and self.open and not self.answers \
                and self.rect().contains(event.position().toPoint()):
            self._click(Qt.Key.Key_Return)
            event.accept()
            return
        super().mouseReleaseEvent(event)

    # The cells. [designed: T212; #862]
    def inner_cols(self):
        """The cells of the words: the whole bar."""
        return self.cols

    def _left(self):
        """The headline's words at the left of the last row."""
        if self.label.isVisibleTo(self):
            return self._span(self.label, self.label.text()) + 1 + self._span(self.rest, self.rest.text())
        return self._span(self.headline, self.headline.text())

    def _span(self, widget, text):
        """[designed: #862, Windows at 100% in a short window] The whole cells a text takes: its characters, or more where the
        system's glyph advance at a fractional cell width runs past them (29 characters drew 319 px over 299 px of cells)."""
        cell = cells.cell_w(self)
        return max(len(text), math.ceil((widget.fontMetrics().horizontalAdvance(text) - 1) / cell))

    def _right(self):
        """The answer's words at the right of the last row."""
        if self.answers:
            return sum(self._span(item.text, words) for words, item in zip(self.answers.values(), self.answer_items.values())) + len(self.answers) - 1
        return self._span(self.key_hint, self.key_hint.text())

    def rows(self):
        """The bar's rows: the key line's two, or the detail's rows above the last row when the detail does not fit on it."""
        detail = self.detail.text() if not self.detail.isHidden() else ""
        self._inline = not detail or self._left() + 1 + len(detail) + 1 + self._right() <= self.cols
        above = 0 if self._inline else len(self.detail.lines(round(self.cols * cells.cell_w(self))))
        return max(MIN_ROWS, 1 + above)

    def place(self):
        """The bar across its screen at the foot, over the key line, in whole cells."""
        parent = self.parentWidget()
        cell, row = cells.cell_w(self), cells.row_px(self)
        width = parent.width() if parent is not None else round(self.cols * cell)
        self.cols = max(1, round(width / cell))
        rows = self.rows()
        # [designed: T211's rows] The bar is the page's last `rows` rows, each where the page puts it (row k at the exact cell height
        # times k, rounded), so its lines sit on the page's grid and its foot covers the bottom bar exactly.
        exact = cells.cell_h(self)
        first = (parent.height() / exact if parent is not None else rows) - rows

        def y(k):
            return round((first + k) * exact) - round(first * exact)

        height = y(rows)
        self.resize(width, height)
        last = y(rows - 1)
        row = y(rows) - last
        at = 0
        if self.label.isVisibleTo(self):
            span = self._span(self.label, self.label.text())
            self.label.setGeometry(0, last, round(span * cell), row)
            at = span + 1
            span = self._span(self.rest, self.rest.text())
            self.rest.setGeometry(round(at * cell), last, round(span * cell), row)
            at += span
        else:
            span = max(1, self._span(self.headline, self.headline.text()))
            self.headline.setGeometry(0, last, round(span * cell), row)
            at = span
        right = self._right()
        if self.answers:
            column = self.cols - right
            for words, item in zip(self.answers.values(), self.answer_items.values()):
                span = self._span(item.text, words)
                item.setGeometry(round(column * cell), last, round(span * cell), row)
                item.text.setGeometry(0, 0, round(span * cell), row)
                column += span + 1
        else:
            self.key_hint.setGeometry(round((self.cols - right) * cell), last, round(right * cell), row)
        if not self.detail.isHidden():
            if self._inline:
                start = at + 1
                self.detail.setGeometry(round(start * cell), last, round((self.cols - right - 1 - start) * cell), row)
            else:
                lines = len(self.detail.lines(round(self.cols * cell)))
                self.detail.setGeometry(0, y(rows - 1 - lines), round(self.cols * cell), last - y(rows - 1 - lines))
        if parent is not None:
            self.move(0, parent.height() - height)


def score_line(names, score, minute):
    """'Norway 0 - 1 Holland, 83′' with the home side first, as the pitch's header. [designed: s18-match-stop.png]"""
    from goal2.ui.pitch import HOME
    return f"{names[HOME]} {score[HOME]} - {score[1 - HOME]} {names[1 - HOME]}, {minute}′"


def substitution_text(model, decision):
    """The SUBSTITUTION OPPORTUNITY's detail: who is injured, or the substitutions asked for at a pause.
    [confirmed: the kit's Match._on_notice: the original offers the notice after an injury or a requested
    substitution (0791:8062)]"""
    from goal2.ui.squad_card import full_name
    data = decision.data
    injured = [w for w in data.get("injured") or [] if w in (data.get("eleven") or [])]
    parts = []
    if injured:
        parts.append(", ".join(full_name(model, w) for w in injured) + (" is" if len(injured) == 1 else " are")
                     + " injured.")
    if data.get("requested"):
        parts.append("Your requested substitutions can be made now.")
    if data.get("refused"):
        # [confirmed: the kit's Match._on_menu] the original refused the eleven: offered again, with its message
        parts.append(f"The original refused the eleven: {data['refused']}.")
    return " ".join(parts) or "Your side may make a substitution."


def opponent_text(model, event):
    """[confirmed: t156-149, "SUBSTITUTION Leonharsen on for Nilsen"] The other side's substitution."""
    from goal2.ui.squad_card import full_name
    data = event["data"]
    return f"SUBSTITUTION {full_name(model, data['on'])} on for {full_name(model, data['off'])}"
