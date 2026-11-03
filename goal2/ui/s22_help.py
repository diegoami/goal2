"""S22 Help: the original's help text, from the imported GOAL.HLP, over the screen F1 was pressed on.

[designed: owner, 2026-11-03, #526, #536; docs/design/ui-2026-11, S22 and its mockup s22-help.html] F1 on any screen
opens it; Esc closes it and returns to the same screen. The text is the player's own GOAL.HLP from the data folder
(imported by S01), decoded as code page 437, in the window's VGA font, and it scrolls with ↑↓, PgUp/PgDn and the
mouse wheel. The mockup's viewer is illustrative (no capture of the original's help viewer exists yet), so the text
is shown whole, as the file holds it. With no GOAL.HLP imported, the box says so in plain words and how to add it.

GOAL.HLP is CR LF text [confirmed: goal2-archaeology sources/goal-hlp.md, "CR LF line ends"]; a DOS text file ends
at its first Ctrl-Z (0x1A), the end-of-file mark, which is not text [derived: the MS-DOS text-file convention].
No byte of GOAL.HLP is in the repository (CLAUDE.md rule 14): the tests write a stand-in of their own.
"""
from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QPainter, QTextBlockFormat, QTextCursor
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QTextEdit, QSizePolicy, QVBoxLayout, QWidget

from goal2.desktop import data_setup
from goal2.ui import theme
from goal2.ui.screen import LINE_HEIGHT, Clickable, Screen, kbd, label

DOS_EOF = b"\x1a"
# [designed: owner decision 13; T163] the help box's place on the 1440x900 page: between the title bar (64 px) and
# the bottom bar (70 px), less a margin, and wide enough for the help's 80 columns
TOP, BOTTOM, MARGIN, WIDTH = 64, 70, 10, 1100
NO_HELP = ("goal2 has no help text: {name} was not imported with your data files.\n\n"
           "To add it, put {name} in the folder that holds your data files and import that folder again "
           "(python -m goal2.desktop.data_setup FOLDER). The other files stay as they are.")


def decode(raw: bytes) -> str:
    """GOAL.HLP's bytes as text: up to the DOS end-of-file mark, code page 437, CR LF read as one line end."""
    return raw.split(DOS_EOF, 1)[0].decode("cp437").replace("\r\n", "\n")


def help_text(path: Path):
    """The help text at `path`, or None when there is no file there."""
    try:
        return decode(Path(path).read_bytes())
    except FileNotFoundError:
        return None


class Scrim(QWidget):
    """The screen under a box, dimmed. [derived: docs/design/ui-2026-11/mockups/style.css, `.scrim`]"""

    def paintEvent(self, event):
        painter = QPainter(self)
        colour = QColor(theme.GROUND)
        colour.setAlpha(theme.SCRIM_ALPHA)
        painter.fillRect(self.rect(), colour)


class HelpScreen(Screen):
    title = "help"
    escape_text = "close"
    offers_help = False

    def __init__(self, window, under, target: data_setup.Paths):
        super().__init__(window)
        self.under = under
        self.text = help_text(target.help)
        self.bind((Qt.Key.Key_Up,), "", lambda: self.scroll(-1), shown=False)
        self.bind((Qt.Key.Key_Down,), "", lambda: self.scroll(1), shown=False)
        self.bind((), "scroll", None, captions=("↑", "↓"))
        self.bind((Qt.Key.Key_PageUp,), "", lambda: self.scroll(-1, page=True), shown=False)
        self.bind((Qt.Key.Key_PageDown,), "", lambda: self.scroll(1, page=True), shown=False)
        self.bind((), "page", None, captions=("PgUp", "PgDn"))
        # The screen F1 was pressed on, as it was, under the scrim.
        backdrop = QLabel()
        backdrop.setObjectName("backdrop")
        if under is not None:
            backdrop.setPixmap(under.grab(under.body.parentWidget().geometry()))
        backdrop.setScaledContents(True)
        backdrop.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Ignored)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.body_layout.addWidget(backdrop)
        self.scrim = Scrim(self)
        self.scrim.setObjectName("scrim")
        self._dialog()

    def _dialog(self):
        """[designed: owner decision 13, #526, #536; T163] The text box fills most of the screen, not the mockup's nine
        lines: the original's help is a long text. The heading, the tag and Close share one row above it; the keys
        that scroll are on the bottom bar."""
        outer = QVBoxLayout(self.scrim)
        outer.setContentsMargins(0, TOP + MARGIN, 0, BOTTOM + MARGIN)
        row = QHBoxLayout()
        row.addStretch(1)
        dialog = QFrame()
        dialog.setObjectName("dialog")
        dialog.setFixedWidth(WIDTH)
        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(26, 18, 26, 18)
        layout.setSpacing(0)
        head = QHBoxLayout()
        head.setSpacing(18)
        head.addWidget(label("Help", "h2"))
        head.addWidget(label("F1 · THE ORIGINAL'S HELP", "tag"), 0, Qt.AlignmentFlag.AlignVCenter)
        head.addStretch(1)
        close = Clickable("enterHint")
        close_layout = QHBoxLayout(close)
        close_layout.setContentsMargins(22, 8, 22, 8)
        close_layout.setSpacing(10)
        close_layout.addWidget(label("Close", "enterText"))
        close_layout.addWidget(kbd("Esc"))
        close.clicked.connect(self.escape)
        self.close_button = close
        head.addWidget(close)
        layout.addLayout(head)
        layout.addSpacing(12)
        self.viewer = QTextEdit()
        self.viewer.setObjectName("helpText")
        self.viewer.setReadOnly(True)
        self.viewer.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.viewer.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.viewer.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.viewer.setLineWrapMode(QTextEdit.LineWrapMode.WidgetWidth)
        self.viewer.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.viewer.setPlainText(self.text if self.text is not None else NO_HELP.format(name=data_setup.HELP_NAME))
        spaced = QTextCursor(self.viewer.document())
        spaced.select(QTextCursor.SelectionType.Document)
        block = QTextBlockFormat()
        block.setLineHeight(LINE_HEIGHT, QTextBlockFormat.LineHeightTypes.ProportionalHeight.value)
        spaced.mergeBlockFormat(block)
        layout.addWidget(self.viewer, 1)
        row.addWidget(dialog)
        row.addStretch(1)
        outer.addLayout(row, 1)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.scrim.setGeometry(self.rect())
        self.scrim.raise_()

    def shown(self):
        self.scrim.setGeometry(self.rect())
        self.scrim.raise_()

    def line_step(self) -> int:
        """One line of the help text, in the viewer's scroll units (pixels)."""
        return max(1, round(self.viewer.fontMetrics().lineSpacing() * LINE_HEIGHT / 100))

    def scroll(self, direction, page=False):
        """↑↓ scroll a line, PgUp/PgDn a page (the viewer's height)."""
        bar = self.viewer.verticalScrollBar()
        bar.setValue(bar.value() + direction * (bar.pageStep() if page else self.line_step()))

    def shown_text(self) -> str:
        return self.viewer.toPlainText()
