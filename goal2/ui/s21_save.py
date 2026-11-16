"""S21 Save and quit: the name box and the yes/no questions of saving and quitting, over the screen they came from.

[designed: owner, 2026-11-03, #526; docs/design/ui-2026-11, S21 and its mockup s21-save-quit.html; T168, #542]
- **F7, save.** *Please enter the name of the saved game.* The box proposes the last name used (the loaded save's or
  the last saved, none for a new career); Enter saves through `goal2.ui.saves.write`, Esc cancels. The original
  proposes a name and the first key typed replaces it, Backspace edits it [confirmed: T156-R1 steps 233–237,
  t156-233-save-name-prompt (SAVED proposed), t156-237-save-name-typed (T156 typed over it)]. A free name, not the
  original's 8.3 file name [designed: owner decision 8, #526].
- **Replace.** A name another save already has asks *Replace it?* **Y**/**N** first: N returns to the name, Y saves
  over it. [designed: T168, #542 scope 1]
- **A failed save** says why in the box, and nothing is replaced (`saves.write`). [designed: T168]
- **F10, quit.** *Are you sure you want to quit?* **Y**/**N**, then, when anything is unsaved, *Do you want to save
  this game?* **Y** (the name box, then quit) or **N** (quit) [confirmed: T156-R1 steps 239–241,
  t156-239-quit-confirm, t156-240-quit-save-prompt; E031 C23–C26b]. Esc on a question cancels: nothing is lost, the
  player stays [designed: T168, §3 "Stops": no stop loses progress silently].
- **The close button** asks the second question when anything is unsaved, with Esc to stay (`Window.closeEvent`),
  as today's window asks *Save and continue / Continue without saving / Cancel* [designed: T87,
  docs/desktop-management.md].

*Unsaved* is the model's own `unsaved`: progress since the career was created, loaded or saved [designed: T87].

The original asks on its bottom line, over the hub [confirmed: the captures above]; goal2 asks in a box over the
screen, dimmed, as the mockup draws it [designed: s21-save-quit.html].
"""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QHBoxLayout, QLabel, QSizePolicy

from goal2.ui import saves, theme
from goal2.ui.s22_help import Scrim
from goal2.ui.screen import Screen, set_para

# [designed: s21-save-quit.html] the box's words; the prompt is the original's "Please enter name of saved game"
# [confirmed: t156-233-save-name-prompt]
SAVE_HEAD = "Save the game"
SAVE_TEXT = "Please enter the name of the saved game."
SAVE_NOTE = "Any name; the last one you used is offered. The start screen lists your saves by these names."
QUIT_TEXT = "Are you sure you want to quit?"            # [confirmed: t156-239-quit-confirm]
SAVE_QUESTION = "Do you want to save this game?"        # [confirmed: t156-240-quit-save-prompt]


def button(text,caption,handler,primary=False):
    """[designed: T216] The same direct action and key caption, without padding taking space from its cells."""
    from goal2.ui.cell_parts import CellKeyItem
    return CellKeyItem(text,caption,handler,len(text)+len(caption)+1,primary=primary)


class BoxScreen(Screen):
    """A bottom-anchored prompt frame over readable main content; the current title and key bar remain visible."""
    GRID = True   # [designed: owner, #667; T216]
    escape_text="cancel"
    offers_help=False
    box_title=""
    COLS=48

    def __init__(self,window,under):
        self.title=f"{under.title} · {self.box_title}" if under is not None and under.title else self.box_title
        super().__init__(window)
        from PySide6.QtCore import QEvent
        from goal2.ui.cells import Cells,CellLabel,CellPara
        from goal2.ui.frame import Frame
        self.under=under
        backdrop=QLabel();backdrop.setObjectName("backdrop")
        if under is not None:backdrop.setPixmap(under.grab(under.body.parentWidget().geometry()))
        backdrop.setScaledContents(True);backdrop.setSizePolicy(QSizePolicy.Policy.Ignored,QSizePolicy.Policy.Ignored)
        from PySide6.QtWidgets import QStackedLayout,QWidget
        host=QWidget();host.setObjectName("overlayHost")
        stack=QStackedLayout(host);stack.setContentsMargins(0,0,0,0)
        stack.setStackingMode(QStackedLayout.StackingMode.StackAll)
        self.scrim=Scrim(host,alpha=theme.PROMPT_SCRIM_ALPHA);self.scrim.setObjectName("scrim")
        stack.addWidget(backdrop);stack.addWidget(self.scrim);stack.setCurrentWidget(self.scrim)
        self.body_layout.addWidget(host,1)
        layout=QHBoxLayout(self.scrim);layout.setContentsMargins(0,0,0,0)
        self.canvas=Cells(90,25,"dialogBody");layout.addWidget(self.canvas)
        self.dialog=Frame(self.box_title or "question")
        self.dialog.setAttribute(Qt.WidgetAttribute.WA_StyledBackground,True)
        self.dialog.setStyleSheet("#frame { background: "+theme.GROUND+"; }")
        self.box=self.dialog.body
        self.head=CellLabel("","h2");self.box.addWidget(self.head)
        self.text=CellPara("","value");self.box.addWidget(self.text)
        self.canvas.put(self.dialog,(90-self.COLS)//2,0,self.COLS,1)
        self._box_rows=None;self._placing=False
        self.dialog.installEventFilter(self)

    def buttons(self,items):
        from PySide6.QtCore import QEvent
        from goal2.ui.cells import Cells
        from goal2.ui import theme
        class Buttons(Cells):
            def __init__(self):
                super().__init__(BoxScreen.COLS,1,"dialogButtons")
                self.setFixedHeight(theme.CELL_H)
                self.buttons=list(items)
                for item in self.buttons:self.put(item,0,0,item.cols);item.installEventFilter(self)
                self.reflow()
            def reflow(self):
                visible=[item for item in self.buttons if not item.isHidden()]
                at=self.cols-sum(item.cols for item in visible)-max(0,len(visible)-1)
                for item in visible:self.move(item,at,0,item.cols);at+=item.cols+1
            def eventFilter(self,obj,event):
                if event.type() in (QEvent.Type.ShowToParent,QEvent.Type.HideToParent):self.reflow()
                return super().eventFilter(obj,event)
            def resizeEvent(self,event):
                super().resizeEvent(event);self.reflow()
        row=Buttons();self.box.addWidget(row);return row

    def _place_box(self):
        if self._placing:return
        import math
        from goal2.ui.cells import cell_w,row_px
        self._placing=True
        try:
            width=round(self.COLS*cell_w(self))
            height=self.dialog.layout().totalHeightForWidth(width)
            if height<0:height=self.dialog.minimumSizeHint().height()
            rows=max(1,math.ceil(height/row_px(self)))
            if rows!=self._box_rows:
                self._box_rows=rows
                self.canvas.move(self.dialog,(90-self.COLS)//2,max(0,25-rows),self.COLS,rows)
        finally:self._placing=False

    def eventFilter(self,obj,event):
        from PySide6.QtCore import QEvent
        if obj is getattr(self,"dialog",None) and event.type()==QEvent.Type.LayoutRequest:self._place_box()
        return super().eventFilter(obj,event)

    def resizeEvent(self,event):
        super().resizeEvent(event)
        self._place_box()

    def shown(self):
        self._place_box()


class QuestionScreen(BoxScreen):
    """A yes/no question: **Y**, **N**, and **Esc** to cancel when `cancel` is given (else Esc is N)."""

    GRID = True   # [designed: owner, #667; T216]

    def __init__(self, window, under, title, head, question, yes, no, cancel=None):
        self.box_title = title
        super().__init__(window, under)
        self.yes, self.no, self.cancel = yes, no, cancel
        self.head.setText(head)
        set_para(self.text, f"{question} (Y/N)")
        self.bind((Qt.Key.Key_Y,), "yes", self.yes)
        self.bind((Qt.Key.Key_N,), "no", self.no)
        esc = next(b for b in self.bindings if Qt.Key.Key_Escape in b.keys)
        self.bindings.remove(esc)
        self.bindings.append(esc)   # Esc last on the bar, as the mockups list it
        esc.text = "cancel" if cancel is not None else "no"
        self._refresh_bar()
        items = [button("Yes", "Y", self.yes), button("No", "N", self.no)]
        if cancel is not None:
            items.append(button("Cancel", "Esc", self.escape))
        self.buttons(items)

    def escape(self):
        return (self.cancel or self.no)()


class SaveScreen(BoxScreen):
    """F7's name box: the proposed name, typed over or accepted; Enter saves, Esc cancels. `done` runs once saved,
    `cancelled` on Esc (default: back to the screen under the box)."""
    GRID = True   # [designed: owner, #667; T216]
    box_title = "save"

    def __init__(self, window, under, model, done=None, cancelled=None):
        super().__init__(window, under)
        self.model, self.done, self.cancelled = model, done, cancelled
        self.replacing = None   # the other save's file while the box asks whether to replace it
        self.head.setText(SAVE_HEAD)
        set_para(self.text, SAVE_TEXT)
        from goal2.ui.cell_parts import CellLineField
        from goal2.ui.cells import CellPara
        self.field = CellLineField(saves.NAME_MAX)
        self.field.set_text(saves.last_name(model) or "")
        self.field.set_active(True)
        self.fresh = bool(self.field.text)   # the proposal: the first key typed replaces it
        self.box.addWidget(self.field)
        self.note = CellPara(SAVE_NOTE, "sub")
        self.box.addWidget(self.note)
        self.problem = CellPara("", "error")
        self.problem.hide()
        self.box.addWidget(self.problem)
        self.save_buttons = [button("Cancel", "Esc", self.escape), button("Save", "Enter", self.press_enter, True)]
        self.replace_buttons = [button("Replace", "Y", self.replace), button("No", "N", self.keep)]
        self.buttons(self.save_buttons + self.replace_buttons)
        self.y = self.bind((Qt.Key.Key_Y,), "replace", self.replace, shown=False)
        self.n = self.bind((Qt.Key.Key_N,), "keep it", self.keep, shown=False)
        self._mode()

    @property
    def name(self):
        return self.field.text

    def _mode(self):
        asking = self.replacing is not None
        self.field.setVisible(not asking)
        self.note.setVisible(not asking)
        for item in self.save_buttons:
            item.setVisible(not asking)
        for item in self.replace_buttons:
            item.setVisible(asking)
        self.y.shown = self.n.shown = asking
        if asking:
            set_para(self.text, f"A save named “{saves.clean_name(self.name)}” is there already. Replace it? (Y/N)")
            self.enter_action = None
            self._refresh_bar()
        else:
            set_para(self.text, SAVE_TEXT)
            self._refresh_bar()
            self.set_enter("Save", self.save)

    # Typing.
    def type_text(self, key, text) -> bool:
        """On the name: printable characters and Backspace edit it; the first character typed replaces the
        proposal. While the box asks to replace, keys go to Y and N."""
        if self.replacing is not None:
            return False
        if key == Qt.Key.Key_Backspace:
            self.fresh = False
            self.field.backspace()
            return True
        if text and len(text) == 1 and text.isprintable():
            if self.fresh:
                self.field.set_text("")
                self.fresh = False
            self.field.type(text)
            return True
        return False

    # Saving.
    def say(self, text):
        set_para(self.problem, text)
        self.problem.setVisible(bool(text))

    def save(self):
        """Enter: save under the name, after asking when another save has it."""
        folder = self.window_.target.saves
        try:
            other = saves.replaces(self.model, folder, self.name)
        except saves.SaveError as exc:
            self.say(f"The game was not saved: {exc}.")
            return None
        if other is not None:
            self.replacing = other
            self.say("")
            self._mode()
            return None
        return self.write()

    def write(self):
        try:
            path = saves.write(self.model, self.window_.target.saves, self.name)
        except saves.SaveError as exc:
            self.replacing = None
            self._mode()
            self.say(f"The game was not saved: {exc}. Nothing was replaced.")
            return None
        name = saves.last_name(self.model)
        self.window_.pop()
        if self.done is not None:
            self.done()
        else:
            told = getattr(self.window_.current(), "say", None)
            if told is not None:
                told(f"Saved as “{name}”.")
        return path

    def replace(self):
        if self.replacing is not None:
            return self.write()
        return None

    def keep(self):
        """N: the other save stays; back to the name."""
        if self.replacing is not None:
            self.replacing = None
            self._mode()
        return None

    def escape(self):
        if self.replacing is not None:
            return self.keep()
        self.window_.pop()
        if self.cancelled is not None:
            self.cancelled()
        return None


# The flows.
def save(window, model, done=None, cancelled=None):
    """F7: the name box over the current screen."""
    return window.push(SaveScreen(window, window.current(), model, done, cancelled))


def ask_to_save(window, model, then, cancelled=None, title="quit"):
    """*Do you want to save this game?* Y: the name box, then `then`; N: `then` at once; Esc: stay. `title` names the
    box after what follows it (*quit*; the desk's *new career*, T177)."""
    def yes():
        window.pop()
        save(window, model, done=then, cancelled=cancelled)

    def no():
        window.pop()
        then()

    def cancel():
        window.pop()
        if cancelled is not None:
            cancelled()
    return window.push(QuestionScreen(window, window.current(), title, "Save", SAVE_QUESTION, yes, no, cancel))


def quit_game(window, model):
    """F10: *Are you sure you want to quit?* N stays; Y quits, after asking to save when anything is unsaved."""
    def yes():
        window.pop()
        if model is not None and model.unsaved:
            ask_to_save(window, model, window.leave)
        else:
            window.leave()

    def no():
        window.pop()
    return window.push(QuestionScreen(window, window.current(), "quit", "Quit", QUIT_TEXT, yes, no))
