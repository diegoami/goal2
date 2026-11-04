"""S18 Match stop: a box over the pitch with the event that stops the match, the score and the minute.

[designed: owner, 2026-11-03, #526; docs/design/ui-2026-11 S18 and its mockup s18-match-stop.png; T180, #574]
[confirmed: T156-R1 steps 67-68, 149-150, 274; t156-067-substitution-opportunity.png,
t156-149-opponent-substitution.png, t156-274-quick-substitution-opportunity.png; E031 g1 step 3874,
e031-shootout-start.png; M244-G4C-07 step 55, m244-shootout-prompt.png]

The notices, each answered by any key, as the original's "press any key":

- **SUBSTITUTION OPPORTUNITY** (`NOTICE_SUBSTITUTION`): the engine's `substitution` decision (your player injured, or
  the stoppage after a requested substitution). The key opens the match menu (S15), as in the original (T156-R1 step
  68), whose *players* opens the bench (S19) in *make substitutions now* mode.
- **The other side's substitution** (`NOTICE_OPPONENT`): "SUBSTITUTION Leonharsen on for Nilsen" in the original
  (t156-149). The engine does not wait for it; the pitch holds its display until the key, then plays on.
- **The penalty shoot-out** (`NOTICE_SHOOTOUT`): before the shoot-out order (S16), as the original's notice
  (e031-shootout-start).

The box belongs to S17 (`PitchScreen.stop_box`): it is drawn over the pitch, and while it shows every key answers it.
The goal questions (*action replay?*, *save this goal?*) are T181's: `show(..., answers=...)` takes keys with their
words for a question; T181 asks those questions once the goal's sample has been painted.
"""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QHBoxLayout, QVBoxLayout

from goal2.ui import theme
from goal2.ui.screen import label, para, set_para
from goal2.ui.squad_card import colour

NOTICE_SUBSTITUTION = "substitution"
NOTICE_OPPONENT = "opponent"
NOTICE_SHOOTOUT = "shootout"
TAG = "THE MATCH STOPS"                 # [designed: s18-match-stop.png]
ANY_KEY = "press any key"               # [confirmed: t156-067, t156-149: "press any key"]
SUBSTITUTION_OPPORTUNITY = "SUBSTITUTION OPPORTUNITY"   # [confirmed: t156-067]
SHOOTOUT = "PENALTY SHOOT-OUT"          # [confirmed: E031 C44-C46b; s17_pitch.STOPS]
# [confirmed: T156-R1 steps 175–177] The goal questions; only Y or N answers them.
ACTION_REPLAY = 'Do you want an action replay?'
SAVE_GOAL = 'Do you want to save this goal?'
YES_NO = {Qt.Key.Key_Y: 'Y yes', Qt.Key.Key_N: 'N no'}
WIDTH = 640


class StopBox(QFrame):
    """The box over the pitch: its tag, the event's headline, the score and minute with what the key does, and the
    keys that answer it. `show_stop` raises it; `answer(key)` runs the stop's handler once and hides it."""

    def __init__(self, parent):
        super().__init__(parent)
        self.setObjectName("stopBox")
        self.setStyleSheet(f"#stopBox {{ background: {theme.GROUND}; border: 2px solid {theme.HEADING}; }}")
        self.setFixedWidth(WIDTH)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 26, 30, 26)
        layout.setSpacing(14)
        tag_row = QHBoxLayout()
        self.tag = label(TAG, "tag")
        tag_row.addWidget(self.tag)
        tag_row.addStretch(1)
        layout.addLayout(tag_row)
        self.headline = label("", "h1")
        self.headline.setWordWrap(True)
        layout.addWidget(self.headline)
        self.detail = para("", "value")
        layout.addWidget(self.detail)
        keys = QHBoxLayout()
        keys.addStretch(1)
        self.key_hint = label(ANY_KEY, "keyLabel")
        colour(self.key_hint, theme.KEY_HINT)
        keys.addWidget(self.key_hint)
        self.keys_row = keys
        layout.addLayout(keys)
        self.kind = None
        self.handler = None
        self.answers = {}
        self.hide()

    def show_stop(self, kind, headline, detail, handler, answers=None):
        """Show a stop: `handler(key)` runs once on the answering key. `answers` {Qt key: words} makes it a
        question answered only by those keys (T181); without it any key answers, as the original's notices."""
        self.kind, self.handler, self.answers = kind, handler, dict(answers or {})
        self.headline.setText(headline)
        set_para(self.detail, detail)
        self.key_hint.setText(" · ".join(self.answers.values()) if self.answers else ANY_KEY)
        self.place()
        self.show()
        self.raise_()

    @property
    def open(self):
        return self.kind is not None

    def texts(self):
        """The box as it reads: (headline, detail, key hint)."""
        return self.headline.text(), self.detail.text(), self.key_hint.text()

    def answer(self, key):
        """A key while the box shows: the stop's handler, once. False when the key does not answer a question."""
        if self.kind is None or (self.answers and key not in self.answers):
            return False
        handler = self.handler
        self.kind, self.handler, self.answers = None, None, {}
        self.hide()
        if handler is not None:
            handler(key)
        return True

    def place(self):
        """Centred over the pitch (the parent's `pitch` widget), as the mockup draws it."""
        parent = self.parentWidget()
        pitch = getattr(parent, "pitch", None)
        self.adjustSize()
        if pitch is None:
            return
        centre = pitch.mapTo(parent, pitch.rect().center())
        self.move(max(0, centre.x() - self.width() // 2), max(0, centre.y() - self.height() // 2))


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
