"""The placeholder home screen: the open career's summary, until T164 builds the manager's desk (S06).

[designed: T162, #536; T163, #537] S02 Start opens it once a save is loaded or continued, S04 once a new career has
started (`Window.open_career`). It shows the career's summary as the Python route's model gives it
(`DesktopModel.summary`) and says that the desk comes next; F1 opens the help. Without a career (T162's tests) it
says only that the data is imported.
"""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QHBoxLayout, QVBoxLayout

from goal2.ui.screen import Screen, label

ROWS = (("country", "country"), ("manager", "manager"), ("campaign", "campaign"), ("next", "next"),
        ("then", "then"), ("team", "team"))


class HomeScreen(Screen):
    title = "home"
    pre_game = True
    escape_text = None   # the bottom of the stack: nothing under it to go back to

    def __init__(self, window, model=None):
        super().__init__(window)
        self.model = model
        self.body_layout.addStretch(1)
        row = QHBoxLayout()
        row.addStretch(1)
        box = QFrame()
        box.setObjectName("box")
        box.setFixedWidth(900)
        layout = QVBoxLayout(box)
        layout.setContentsMargins(34, 30, 34, 30)
        layout.setSpacing(6)
        self.values = {}
        if model is None:
            layout.addWidget(label("Your data is imported", "h1"))
            text = label("No career is open. This is a placeholder for the manager's desk (S06), which comes next. "
                         "F1 opens the original's help.", "sub")
        else:
            from goal2.ui.start_look import key_value
            summary = model.summary()
            layout.addWidget(label(f"{summary['country']}, {model.manager}", "h1"))
            layout.addSpacing(10)
            facts, self.values = key_value(ROWS)
            for key, value in self.values.items():
                value.setText(summary[key])
            layout.addWidget(facts)
            layout.addSpacing(10)
            text = label("This is a placeholder for the manager's desk (S06), which comes next. F1 opens the "
                         "original's help.", "sub")
        text.setWordWrap(True)
        layout.addWidget(text)
        row.addWidget(box, 0, Qt.AlignmentFlag.AlignCenter)
        row.addStretch(1)
        self.body_layout.addLayout(row)
        self.body_layout.addStretch(1)
