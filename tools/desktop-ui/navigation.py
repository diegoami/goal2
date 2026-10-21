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
            # [designed: T99] A Team-page control lives in one of the page's views; show that view.
            views=getattr(window,'team_views',None)
            if views is not None and views.isAncestorOf(widget):
                window.team_view(next(i for i in range(views.count()) if views.widget(i).isAncestorOf(widget)))
                assert views.widget(views.currentIndex()).isAncestorOf(widget),'retained proof could not reveal Team view'
            page.ensureWidgetVisible(widget);QApplication.processEvents()
            return
