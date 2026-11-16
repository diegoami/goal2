"""The placeholder home screen with no career open: it says the data is imported.

[designed: T162, #536; T164, #538] A career open in the window lands on the manager's desk (S06,
goal2/ui/s06_desk.py), which replaced this screen's career summary. What stays is the screen T162's tests and the
screenshot tool put at the bottom of the stack when no career is open; F1 opens the help.
"""
from __future__ import annotations


from goal2.ui.screen import Screen


class HomeScreen(Screen):
    GRID = True   # [designed: owner, #667; T216]
    title = "home"
    pre_game = True
    escape_text = None

    def __init__(self, window):
        super().__init__(window)
        from goal2.ui.cells import Cells,CellPara
        from goal2.ui.country_parts import framed
        body=Cells(90,25,"homeBody")
        self.body_layout.addWidget(body,1)
        frame,inner=framed("data",64,6)
        inner.text("Your data is imported","h1",0,0,64)
        inner.put(CellPara("No career is open: start or load one from S02 Start, and it opens on the manager's desk (S06). F1 opens the original's help.","sub"),0,2,64,4)
        body.put(frame,13,8,64,7)
