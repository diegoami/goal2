"""The placeholder home screen, shown once the data folder is imported.

[designed: T162, #536] It holds the place of S02 Start, which T163 builds and which replaces it; until then it only
says that the data is imported and that F1 opens the help.
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
        text = label("This is a placeholder for the start screen (S02), which comes next. F1 opens the original's "
                     "help.", "sub")
        text.setWordWrap(True)
        layout.addWidget(text)
        row.addWidget(box, 0, Qt.AlignmentFlag.AlignCenter)
        row.addStretch(1)
        self.body_layout.addLayout(row)
        self.body_layout.addStretch(1)
