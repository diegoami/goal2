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
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QSizePolicy, QVBoxLayout

from goal2.ui import saves
from goal2.ui.s22_help import Scrim
from goal2.ui.screen import Clickable, Screen, kbd, label, para, set_para
from goal2.ui.start_look import LineField

WIDTH = 640   # [designed: s21-save-quit.html, the dialog's width at 1440x900]
# [designed: s21-save-quit.html] the box's words; the prompt is the original's "Please enter name of saved game"
# [confirmed: t156-233-save-name-prompt]
SAVE_HEAD = "Save the game"
SAVE_TEXT = "Please enter the name of the saved game."
SAVE_NOTE = "Any name; the last one you used is offered. The start screen lists your saves by these names."
QUIT_TEXT = "Are you sure you want to quit?"            # [confirmed: t156-239-quit-confirm]
SAVE_QUESTION = "Do you want to save this game?"        # [confirmed: t156-240-quit-save-prompt]


def button(text, caption, handler, primary=False):
    """A button of the box, its key cap at the right, as the mockup's `.btn` (`.primary`: the highlight bar)."""
    item = Clickable("enterHint" if primary else "option")
    row = QHBoxLayout(item)
    row.setContentsMargins(18, 10, 18, 10)
    row.setSpacing(10)
    row.addWidget(label(text, "enterText" if primary else "optionText"))
    row.addWidget(kbd(caption))
    item.clicked.connect(handler)
    return item


class BoxScreen(Screen):
    """A box over the screen it was opened from: that screen as it was, dimmed, and the box in the middle, as S22's.
    Its title is the screen's under it and the box's (*manager's desk · save*), as the mockup's."""
    escape_text = "cancel"
    offers_help = False
    box_title = ""

    def __init__(self, window, under):
        self.title = f"{under.title} · {self.box_title}" if under is not None and under.title else self.box_title
        super().__init__(window)
        self.under = under
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
        outer = QVBoxLayout(self.scrim)
        outer.addStretch(1)
        row = QHBoxLayout()
        row.addStretch(1)
        self.dialog = QFrame()
        self.dialog.setObjectName("dialog")
        self.dialog.setFixedWidth(WIDTH)
        self.box = QVBoxLayout(self.dialog)
        self.box.setContentsMargins(30, 24, 30, 26)
        self.box.setSpacing(14)
        self.head = label("", "h2")
        self.box.addWidget(self.head)
        self.text = para("", "value")
        self.box.addWidget(self.text)
        row.addWidget(self.dialog)
        row.addStretch(1)
        outer.addLayout(row)
        outer.addStretch(1)

    def buttons(self, items):
        """The box's buttons, at its right end."""
        row = QHBoxLayout()
        row.setSpacing(12)
        row.addStretch(1)
        for item in items:
            row.addWidget(item)
        self.box.addLayout(row)
        return row

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.scrim.setGeometry(self.rect())
        self.scrim.raise_()

    def shown(self):
        self.scrim.setGeometry(self.rect())
        self.scrim.raise_()


class QuestionScreen(BoxScreen):
    """A yes/no question: **Y**, **N**, and **Esc** to cancel when `cancel` is given (else Esc is N)."""

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
    box_title = "save"

    def __init__(self, window, under, model, done=None, cancelled=None):
        super().__init__(window, under)
        self.model, self.done, self.cancelled = model, done, cancelled
        self.replacing = None   # the other save's file while the box asks whether to replace it
        self.head.setText(SAVE_HEAD)
        set_para(self.text, SAVE_TEXT)
        self.field = LineField(saves.NAME_MAX)
        self.field.set_text(saves.last_name(model) or "")
        self.field.set_active(True)
        self.fresh = bool(self.field.text)   # the proposal: the first key typed replaces it
        self.box.addWidget(self.field)
        self.note = para(SAVE_NOTE, "sub")
        self.box.addWidget(self.note)
        self.problem = para("", "error")
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
