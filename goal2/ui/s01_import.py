"""S01 Import your data: the first start's screen over `goal2.desktop.data_setup`'s check and copy.

[designed: owner, 2026-11-02, T153; owner, 2026-11-03, #526, #536; docs/design/ui-2026-11, S01 and its mockup
s01-import.html] On the first start only, the player chooses the folder that holds the data files. The screen shows
each file, what it is for and the result of its check (found and verified, missing, not the right file); GOAL.HLP,
the original's help that F1 shows, is optional. What is wrong is said in plain words, `data_setup`'s own. Enter
chooses the folder, Esc quits. The rules (names, digests, what is optional, what is copied where) are
`data_setup`'s, unchanged: this screen only shows them.

[designed: owner, 2026-11-03, #527, D2; T163, #537] The new window's careers run on the Python route, so its files are
`data_setup.WINDOW_MANIFEST`: GOAL.DAT and the E010 half-time template that a new career starts from. The Core's boot
state, which the mockup's third row names, is not asked for; the template takes its row.
"""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFileDialog, QFrame

from goal2.desktop import data_setup
from goal2.ui.screen import Screen, set_para

# What each file is needed for, as the S01 mockup says it; GOAL.HLP is marked optional, as data_setup.OPTIONAL has
# it. [designed: docs/design/ui-2026-11/mockups/s01-import.html; T153]
NEEDED_FOR = {
    data_setup.DATA_NAME: "countries, players, fixtures",
    data_setup.HELP_NAME: "the original's help (F1), optional",
    data_setup.TEMPLATE_NAME: "a new career's start",   # [designed: T163] in the place of the boot state's row
}
ROWS = (data_setup.DATA_NAME, data_setup.HELP_NAME, data_setup.TEMPLATE_NAME)   # the mockup's order

# The check column's words, by result. [designed: s01-import.html for the first two; T162 for the others]
CHECK = {
    "verified": ("✓ found, verified", "good"),
    "missing": ("✗ missing in this folder", "bad"),
    "wrong": ("✗ not the right file", "bad"),
    "absent": ("not in this folder (optional)", "none"),
    "unchecked": ("not checked yet", "none"),
}
INTRO = ("goal2 plays the original's game from your own data files. Choose the folder that holds them; goal2 checks "
         "each file and copies it into its data folder. Your saved careers are never touched.")


def checks(folder) -> dict:
    """Each file's check in `folder`, by `data_setup`'s own rules: 'verified', 'missing', 'wrong' or, for an
    optional file the folder does not have, 'absent'."""
    found = dict(data_setup.problems(folder, data_setup.WINDOW_MANIFEST))
    optional = {name for name, _ in data_setup.OPTIONAL}
    out = {}
    for name in ROWS:
        if name in found:
            out[name] = found[name]
        elif name in optional and data_setup.find(folder, name) is None:
            out[name] = "absent"
        else:
            out[name] = "verified"
    return out


class FixedWidthBox(QFrame):
    """[designed: T186] Measure wrapped content at this box's actual fixed width."""
    def minimumSizeHint(self):
        hint=super().minimumSizeHint()
        if self.layout() is not None:
            needed=self.layout().totalHeightForWidth(self.width())
            if needed>=0:
                hint.setHeight(needed)
        return hint


class ImportScreen(Screen):
    GRID = True   # [designed: owner, #667; T214]
    title = "first start"
    pre_game = True
    escape_text = "quit"

    def __init__(self, window, target: data_setup.Paths, choose=None):
        super().__init__(window)
        self.target = target
        self.choose = choose or (lambda: QFileDialog.getExistingDirectory(self, "The folder with your data files")
                                 or None)
        self.folder = None
        self.result = {name: "unchecked" for name in ROWS}
        self._build()
        self.set_enter("Choose folder…", self.choose_and_import)

    def _build(self):
        """[designed: owner, #667; T214] All three files across the page, with complete errors and a wrapped folder path."""
        from goal2.ui.cells import Cells,CellPara
        from goal2.ui.country_parts import framed
        body=Cells(90,25,"importBody")
        self.body_layout.addWidget(body,1)
        body.text("GOAL2 ADDITION · FIRST START ONLY","tagNew",0,0,90)
        frame,inner=framed("import your game data",90,17)
        inner.put(CellPara(INTRO,"sub"),0,0,90,3)
        for col,head,width in ((0,"file",26),(26,"needed for",34),(60,"check",30)):
            inner.text(head,"cardLabel",col,4,width)
        self.cells={}
        for row,name in enumerate(ROWS,5):
            inner.text(name,"value",0,row,26)
            inner.text(NEEDED_FOR[name],"sub",26,row,34)
            self.cells[name]=inner.text("","value",60,row,30)
        self.error=CellPara("","error")
        inner.put(self.error,0,9,90,8)  # [designed: T215] use both spare rows for complete Windows refusal paths
        body.put(frame,0,1,90,18)
        folder,inner=framed("folder",90,4)
        self.folder_label=CellPara("","fieldValue")
        self.folder_label.setTextFormat(Qt.TextFormat.PlainText)
        inner.put(self.folder_label,0,0,90,4)
        body.put(folder,0,20,90,5)
        self._show()

    def _show(self, message=""):
        for name, cell in self.cells.items():
            text, kind = CHECK[self.result[name]]
            cell.setText(text)
            cell.setProperty("check", kind)
            from goal2.ui.squad_card import colour
            from goal2.ui import theme
            colour(cell,{"good":theme.GOOD,"bad":theme.BAD}.get(kind,theme.TEXT_NORMAL))
            cell.style().unpolish(cell)
            cell.style().polish(cell)
        self.message = message
        set_para(self.error, message)
        self.error.setVisible(bool(message))
        self.folder_label.setText(str(self.folder) if self.folder is not None else "—")

    def check_text(self, name) -> str:
        return self.cells[name].text()

    def choose_and_import(self):
        """Enter: choose a folder, check each file, and import it; True once imported (the window goes on to S02
        Start). A refused folder stays on screen with each file's check and the plain words of the refusal."""
        folder = self.choose()
        if not folder:
            return False
        return self.offer(folder)

    def offer(self, folder) -> bool:
        self.folder = folder
        self.result = checks(folder)
        try:
            data_setup.import_folder(folder, self.target, data_setup.WINDOW_MANIFEST)
        except data_setup.ImportRefused as exc:
            self._show(f"{exc}\nChoose the folder that holds all the files.")
            return False
        except data_setup.SetupError as exc:
            self._show(str(exc))
            return False
        self._show()
        from goal2.ui.s02_start import StartScreen
        self.window_.replace_home(StartScreen(self.window_))
        return True

    def escape(self):
        """Esc quits: S01 is the first screen. [designed: docs/design/ui-2026-11, S01: "Quit (Esc)"]"""
        self.window_.close()
