"""[designed: T106] Enter in the core route's manager-name line starts the career on its first bulletin.

The hint says "Type the name / Enter: start". `returnPressed` started the career, then QLineEdit left the Return
event unaccepted, so it reached `LaunchWindow.keyPressEvent`; by then `do_start` had moved the focus to the
bulletin's Next button, which that handler clicked: the first bulletin was skipped (with one bulletin, the manager
menu opened at once). T106's test calls `do_start()` directly, so it never pressed the key.
"""
import tempfile
import unittest
from pathlib import Path

from goal2.tests import requires

NEEDS = dict(modules=('unicorn', 'PySide6'), files=('GOAL.EXE', 'GOAL.DAT'))


@requires.need(**NEEDS)
class NameEnter(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from PySide6.QtWidgets import QApplication
        cls.app = QApplication.instance() or QApplication([])

    def test_enter_in_the_name_line_shows_the_first_bulletin(self):
        from PySide6.QtCore import Qt
        from PySide6.QtTest import QTest
        from goal2.desktop.launch import LaunchWindow
        folder = tempfile.TemporaryDirectory();self.addCleanup(folder.cleanup)
        w = LaunchWindow(requires.CACHE / 'GOAL.DAT', None, Path(folder.name) / 'none.g2core', lambda model: None,
                         core_boot=requires.CACHE / 'GOAL.EXE')
        self.addCleanup(w.close)
        w.show();self.app.processEvents()
        w.new_career.click();self.app.processEvents()
        w.review();self.app.processEvents()
        w.manager_name.setText('J Smith');w.manager_name.setFocus();self.app.processEvents()
        QTest.keyClick(w.manager_name, Qt.Key.Key_Return);self.app.processEvents()
        self.assertTrue(w.bulletins, 'the new game showed no bulletin')
        self.assertEqual(w.pages.currentIndex(), 4)
        self.assertEqual(w.bulletin_index, 0)


if __name__ == '__main__':
    unittest.main()
