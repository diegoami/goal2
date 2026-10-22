"""[designed: T74] Retained Qt proofs reveal a control before the same real event."""
from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

def reveal(widget):
    window=widget.window()
    if not hasattr(window,'pages'):return
    for index,page in enumerate(window.pages):
        if page.isAncestorOf(widget):
            window.activateWindow();QApplication.processEvents()
            QTest.keyClick(window,Qt.Key.Key_1+index,Qt.KeyboardModifier.ControlModifier)
            assert window.page_stack.currentIndex()==index,'retained proof could not reveal page'
            # [designed: T99/T101] A control may live in one of the page's views (a route of the
            # fixed page); the window shows that view. Nothing scrolls: the control is then visible.
            window.reveal(widget);QApplication.processEvents()
            assert widget.isVisible(),'retained proof could not reveal the view holding '+(widget.objectName() or type(widget).__name__)
            return
