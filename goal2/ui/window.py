"""The new window: one main window that holds one screen at a time, on a stack.

[designed: owner, 2026-11-03, #526, #536; docs/design/ui-2026-11 §3, "Navigation"] One screen at a time, as in the
original. `push` opens a screen over the current one, `pop` returns to the one under it (Esc, by default) and
`replace_home` empties the stack and starts again from a screen: S01 until the data is imported, then S02 Start, and
the manager's desk (S06) once a career is open (`open_career`) [designed: T164, #538]. F1 on any screen opens the help (S22) over it, and Esc there
returns to the same screen. [designed: T163, #537; docs/design/ui-2026-11 §1, the journey]
Closing the window never loses unsaved progress silently: it asks S21's save question first (`closeEvent`), and
`leave` closes once the player has answered (F10's questions or the close button's). [designed: T168, #542]

The page is composed for 1440x900 and scales as a whole with the window, as today's fixed pages do
[designed: docs/design/ui-2026-11 §3, "Text size"; T101]: the window's central widget is
`goal2.desktop.fixed_page.FixedPage`, reused unchanged, and each screen's lengths are recorded and scaled when it
is pushed.
"""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QMainWindow, QStackedWidget

from goal2.desktop import data_setup, fixed_page
from goal2.ui import start_look, theme


class Window(QMainWindow):
    def __init__(self, target: data_setup.Paths | None = None, choose=None):
        super().__init__()
        self.target = target if target is not None else data_setup.paths()
        self.choose = choose   # the folder chooser S01 uses (None: the system's)
        self.setWindowTitle("goal2")
        self.family = theme.load_font()
        self.setFont(self._font())
        # [designed: T163] the start and new-game screens' additions (goal2/ui/start_look.py) follow the theme's sheet
        self.sheet = theme.stylesheet(self.family) + start_look.stylesheet()
        self.page = QStackedWidget()
        self.page.setObjectName("page")
        self.frame = fixed_page.FixedPage(self.page, self.sheet, self)
        self.frame.setStyleSheet(f"#fixedPage {{ background: {theme.GROUND}; }}")
        self.setCentralWidget(self.frame)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.stack = []
        self.career = None   # the open career, a DesktopModel, once S02 or S04 opened one
        self.leaving = False   # the player chose to quit: closing asks nothing more [designed: T168]
        self.resize(fixed_page.WIDTH, fixed_page.HEIGHT)

    def _font(self):
        from PySide6.QtGui import QFont
        font = QFont(self.family)
        font.setPixelSize(theme.TEXT)
        return font

    # The stack.
    def current(self):
        return self.stack[-1] if self.stack else None

    def push(self, screen):
        self.stack.append(screen)
        self.page.addWidget(screen)
        fixed_page.record(self.page)
        fixed_page.apply(self.page, self.frame.scale, self.sheet)
        self.page.setCurrentWidget(screen)
        self.setFocus()
        screen.shown()
        return screen

    def pop(self):
        """Back to the screen under the current one; the bottom screen stays."""
        if len(self.stack) < 2:
            return self.current()
        screen = self.stack.pop()
        self.page.removeWidget(screen)
        screen.deleteLater()
        self.page.setCurrentWidget(self.stack[-1])
        self.setFocus()
        self.stack[-1].shown()
        return self.stack[-1]

    def replace_home(self, screen):
        """Empty the stack and start from `screen`."""
        while self.stack:
            old = self.stack.pop()
            self.page.removeWidget(old)
            old.deleteLater()
        return self.push(screen)

    def start(self):
        """The first screen: S01 while the data folder lacks a file of the new window's manifest, else S02 Start."""
        from goal2.ui.s01_import import ImportScreen
        from goal2.ui.s02_start import StartScreen
        if data_setup.complete(self.target.data, data_setup.WINDOW_MANIFEST):
            return self.replace_home(StartScreen(self))
        return self.replace_home(ImportScreen(self, self.target, self.choose))

    def open_career(self, model, pages=()):
        """A career started (S04) or loaded (S02): its bulletin pages first (S05), if it has any, then the manager's
        desk (S06), the career's home. [designed: owner, 2026-11-03, #509] The Python route has no bulletins yet, so
        a new career goes straight to the desk until the news is ported. [designed: T164, #538]"""
        from goal2.ui.s06_desk import DeskScreen
        self.career = model
        pages = list(pages)
        if pages:
            from goal2.ui.s05_bulletin import BulletinScreen
            return self.replace_home(BulletinScreen(self, pages, lambda: self.open_career(model)))
        return self.replace_home(DeskScreen(self, model))

    def open_help(self):
        """F1: the help (S22) over the current screen."""
        from goal2.ui.s22_help import HelpScreen
        return self.push(HelpScreen(self, self.current(), self.target))

    # Keys go to the current screen; a screen with a typed line (S03's year, S04's name) sees the key's text first.
    def keyPressEvent(self, event):
        # [designed: owner #612] A held key must not cross screen boundaries.
        if event.isAutoRepeat() and event.key() in (Qt.Key.Key_Escape, Qt.Key.Key_Return, Qt.Key.Key_Enter):
            event.accept()
            return
        screen = self.current()
        typed = getattr(screen, "type_text", None)
        if typed is not None and typed(event.key(), event.text()):
            event.accept()
            return
        if screen is not None and screen.handle_key(event.key()):
            event.accept()
            return
        super().keyPressEvent(event)

    def leave(self):
        """Quit once the player has answered: F10's questions, or the close button's. Nothing more is asked."""
        self.leaving = True
        self.close()

    def closeEvent(self, event):
        """Closing the window: each screen on the stack that holds something running ends it first (S17 cancels its
        match through the bridge, publishing nothing). [designed: T166, #540] Then, when the open career has unsaved
        progress (the model's `unsaved`), the window stays and asks *Do you want to save this game?* (S21): Y the name
        box then close, N close, Esc stay, with the cancelled match's screens gone. Nothing unsaved closes at once.
        [designed: T168, #542; T87's question, docs/desktop-management.md]"""
        running = [screen for screen in self.stack if getattr(screen, "closing", None) is not None]
        for screen in reversed(running):
            screen.closing()
        if self.leaving or self.career is None or not self.career.unsaved:
            super().closeEvent(event)
            return
        event.ignore()
        from goal2.ui.s21_save import BoxScreen, ask_to_save
        # The cancelled match's screens go down to the stack's base (the desk, which also ends its match day's
        # bridges: its `closing` is no reason to keep what is above it).
        if any(screen is not self.stack[0] for screen in running):
            while len(self.stack) > 1:
                self.pop()
        while isinstance(self.current(), BoxScreen) and len(self.stack) > 1:
            self.pop()
        ask_to_save(self, self.career, self.leave)

    def focusNextPrevChild(self, next_):
        """Tab is a key of the screens (S03's starting year), not a move of Qt's focus. [designed: owner decision 9,
        #526; docs/design/ui-2026-11 §3, "The keyboard"]"""
        return False
