"""The placeholder home screen with no career open: it says the data is imported.

[designed: T162, #536; T164, #538] A career open in the window lands on the manager's desk (S06,
goal2/ui/s06_desk.py), which replaced this screen's career summary. What stays is the screen T162's tests and the
screenshot tool put at the bottom of the stack when no career is open; F1 opens the help.
"""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QHBoxLayout, QVBoxLayout

from goal2.ui.screen import Screen, label


class HomeScreen(Screen):
    title = "home"
    pre_game = True
    escape_text = None   # the bottom of the stack: nothing under it to go back to

    def __init__(self, window):
        super().__init__(window)
        self.body_layout.addStretch(1)
        row = QHBoxLayout()
        row.addStretch(1)
        box = QFrame()
        box.setObjectName("box")
        box.setFixedWidth(900)
        layout = QVBoxLayout(box)
        layout.setContentsMargins(34, 30, 34, 30)
        layout.setSpacing(6)
        layout.addWidget(label("Your data is imported", "h1"))
        text = label("No career is open: start or load one from S02 Start, and it opens on the manager's desk (S06). "
                     "F1 opens the original's help.", "sub")
        text.setWordWrap(True)
        layout.addWidget(text)
        row.addWidget(box, 0, Qt.AlignmentFlag.AlignCenter)
        row.addStretch(1)
        self.body_layout.addLayout(row)
        self.body_layout.addStretch(1)
