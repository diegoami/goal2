"""[designed: T170au] Verified news projection and exactly-once S05 delivery."""

from copy import deepcopy
from dataclasses import asdict
from tempfile import TemporaryDirectory
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

from goal2.engine.original_match.news import NewsPageMemory
from goal2.tests import requires


def news(story):
    cells = bytearray(b' \x07' * 2000)

    def write(row, col, text):
        index = 2 * (80 * row + col)
        encoded = text.encode('cp437')
        cells[index:index + 2 * len(encoded):2] = encoded

    write(8, 3, 'Left')
    write(6, 29, 'Middle')
    write(8, 57, 'Right')
    write(10, 3, story)
    write(11, 3, '≡░')
    write(20, 29, '<last line>')
    write(18, 57, 'Café')
    return asdict(NewsPageMemory(cells, country=7, waiting_key=13, seed_words=(1, 2)))


class Projection(unittest.TestCase):
    def test_preserves_order_columns_and_original_provenance(self):
        from goal2.game.bulletin_view import native_bulletins

        first = {'news_pages': (news('Entry one'), news('Entry two'))}
        second = {'news_pages': (news('Final'), news('Final'))}
        source = deepcopy((first, second))
        pages = native_bulletins(first, second)
        self.assertEqual([page['left']['lines'] for page in pages],
                         [['Entry one'], ['Entry two'], ['Final'], ['Final']])
        self.assertEqual(pages[0]['middle'], {'masthead': 'Middle', 'lines': ['<last line>']})
        self.assertEqual(pages[0]['right'], {'masthead': 'Right', 'lines': ['Café']})
        pages[2]['left']['lines'].append('Edited presentation')
        self.assertEqual(pages[3]['left']['lines'], ['Final'])
        self.assertEqual((first, second), source)
        with self.assertRaises(ValueError):
            native_bulletins({'news_pages': (dict(news('Bad'), cells=b'bad'),)})


@requires.need(modules=('PySide6',))
class Window(unittest.TestCase):
    def setUp(self):
        from PySide6.QtWidgets import QApplication
        from goal2.desktop import data_setup
        from goal2.ui import theme
        from goal2.ui.native_match_day import NativeMatchDay
        from goal2.ui.screen import Screen
        from goal2.ui.window import Window

        self.app = QApplication.instance() or QApplication([])
        theme.install(self.app)
        folder = TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.window = Window(data_setup.paths(Path(folder.name)))
        self.window.push(Screen(self.window))
        self.window.show()
        self.addCleanup(self.close_window)
        self.owner = Mock(managed_country=7)
        self.packet = {'observation': {'news_pages': (news('Final'),)}}
        self.owner.take_observations.return_value = [self.packet]
        self.callback = Mock()
        with patch('goal2.ui.native_match_day.NativeSeasonOwner', return_value=self.owner):
            self.day = NativeMatchDay(self.window, SimpleNamespace(state=SimpleNamespace(managed_country=7)), {},
                                      on_boundary=self.callback, on_failure=Mock(), on_goal=Mock(),
                                      on_tournament=Mock(), on_stats=Mock(), show_bulletins=True)
        self.day.timer.stop()
        self.day.entry_observation = {'observation': {'news_pages': (news('Entry'),)}}

    def close_window(self):
        self.window.leaving = True
        self.window.close()
        self.window.deleteLater()
        self.app.processEvents()

    def test_help_defers_delivery_and_final_acknowledgement_is_once(self):
        from PySide6.QtCore import Qt
        from PySide6.QtTest import QTest
        from goal2.ui.s05_bulletin import BulletinScreen
        from goal2.ui.s22_help import HelpScreen

        QTest.keyClick(self.window, Qt.Key.Key_F1)
        self.assertIsInstance(self.window.current(), HelpScreen)
        self.day.deliver_boundary()
        self.owner.take_observations.assert_not_called()
        QTest.keyClick(self.window, Qt.Key.Key_Escape)
        self.day.deliver_boundary()
        page = self.window.current()
        self.assertIsInstance(page, BulletinScreen)
        self.assertEqual(page.panels['left'][3].text(), 'Entry')
        finish = page.then
        QTest.keyClick(self.window, Qt.Key.Key_Return)
        self.assertEqual(page.panels['left'][3].text(), 'Final')
        self.callback.assert_not_called()
        QTest.keyClick(self.window, Qt.Key.Key_Return)
        finish()
        self.callback.assert_called_once_with(self.day, self.packet)
        self.assertEqual(self.day.phase, 'finished')

    def test_close_during_bulletin_does_not_deliver_a_boundary(self):
        self.day.deliver_boundary()
        finish = self.day.bulletin.then
        self.window.leaving = True
        self.window.close()
        finish()
        self.owner.close.assert_called_once()
        self.callback.assert_not_called()
