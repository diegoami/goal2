"""[designed: T110] Complete bulletin columns, from a real original page and a maximal UI payload.

The sole real case starts E038's kept bulletin and E006's manager menu; no test changes guest memory.
"""
import copy
import os
from pathlib import Path
import tempfile
import unittest

from goal2.tests import requires

requires.require(modules=('unicorn', 'PySide6'), files=('e006-r0001-main.sav',
    'e038-r0001-after-name-1.sav', 'GOAL.DAT'))

from PySide6.QtCore import QPoint
from PySide6.QtGui import QAccessible
from PySide6.QtWidgets import QApplication, QFrame, QTableView, QCheckBox


class Bulletin(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
        cls.app = QApplication.instance() or QApplication([])
        from goal2.desktop.style import load_fonts
        load_fonts()

    def test_every_story_is_visible_in_its_column_and_the_game_does_not_change(self):
        from goal2.core import Core, views
        from goal2.desktop.core_model import CoreModel
        from goal2.desktop.core_window import CoreWindow
        from goal2.desktop.fixed_page import problems
        wait = Core.start((requires.CACHE / 'e038-r0001-after-name-1.sav').read_bytes())
        self.assertEqual(wait.kind, 'bulletin')
        real = views.bulletin(wait.state)
        for part in real.values():
            for line in [part['masthead'], *part['lines']]:
                self.assertIn(line, wait.text)
        # [derived: views.BULLETIN_PANELS] The original's boxes hold 9/13/9 lines of 20/22/20 cells.
        # These are our own presentation strings, not a constructed guest state.
        maximum = {name: {'masthead': name.upper() + ' PAPER',
                         'lines': [f'{name[0].upper()}{i:02d} ' + 'x' * (width - 4) for i in range(count)]}
                   for name, count, width in (('left', 9, 20), ('middle', 13, 22), ('right', 9, 20))}
        maximum['left']['lines'][0] = '<b>literal text</b>'
        self.assertGreater(sum(len(p['lines']) for p in maximum.values()), 18)
        with tempfile.TemporaryDirectory() as folder:
            model = CoreModel.open(requires.CACHE / 'e006-r0001-main.sav', requires.CACHE / 'GOAL.DAT',
                                   Path(folder) / 'game.g2core')
            before = model.memory_sha256()
            w = CoreWindow(model);w.show();self.app.processEvents()
            try:
                r = w.core_round
                for payload in (real, maximum):
                    r.queue = [('bulletin', copy.deepcopy(payload))];r.after = 'menu';r.next_page()
                    self.app.processEvents();self.app.processEvents()
                    panels = [p for p in r.holder.findChildren(QFrame)
                              if p.objectName() == 'bulletinPanel' and p.isVisible()]
                    self.assertEqual(len(panels), 3, 'the round needs the original three paper columns')
                    for name in ('left', 'middle', 'right'):
                        masthead, story = r.bulletin_columns.panels[name]
                        self.assertTrue(masthead.isVisible() and story.isVisible())
                        self.assertEqual(masthead.text(), payload[name]['masthead'])
                        self.assertEqual(story.text().splitlines(), payload[name]['lines'])
                        self.assertEqual(QAccessible.queryAccessibleInterface(story).text(QAccessible.Text.Name),
                                         story.text(), 'markup-looking text must remain literal')
                    x = [r.bulletin_columns.panels[n][0].mapTo(r.holder, QPoint(0, 0)).x()
                         for n in ('left', 'middle', 'right')]
                    self.assertLess(x[0], x[1]);self.assertLess(x[1], x[2])
                    for width, height in ((1440,900),(1050,780),(900,640),(2560,1600)):
                        w.resize(round(.9*width), round(.9*height));self.app.processEvents();self.app.processEvents()
                        self.assertEqual(problems(w), [], (width, height, problems(w)))
                    self.assertFalse(any(p.isVisible() for kind in (QTableView, QCheckBox)
                                         for p in r.holder.findChildren(kind)))
                    self.assertEqual(model.memory_sha256(), before)
                    r.page_next.click();self.app.processEvents()
                    self.assertEqual(w.page_stack.currentIndex(), 0)
                self.assertEqual(model.memory_sha256(), before)
            finally:
                w.close();self.app.processEvents()


if __name__ == '__main__':
    unittest.main()
