"""[designed: T74] Retained Qt proofs reveal a control before the same real event."""
from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

def reveal(widget):
    window=widget.window()
    if not hasattr(window,'pages'):return
    for index,page in enumerate(window.pages):
        if page.isAncestorOf(widget):
            QTest.keyClick(window,Qt.Key.Key_1+index,Qt.KeyboardModifier.ControlModifier)
            page.ensureWidgetVisible(widget);QApplication.processEvents()
            return
