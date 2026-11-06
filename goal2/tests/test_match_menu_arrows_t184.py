"""[confirmed: T156-R1 69-73; owner #596] S15 arrows follow rows and country columns.

Country labels/data here are declared UI-only fixtures; this tests actual Qt controls,
not game rules or original match evidence.
"""
import os
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
from goal2.tests import requires
requires.require(modules=('PySide6',))
from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QWidget
from goal2.desktop import data_setup
from goal2.ui import theme
from goal2.ui.screen import Screen
from goal2.ui.s15_match_menu import MenuScreen
from goal2.ui.window import Window


class MenuArrows(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.application = QApplication.instance() or QApplication([])
        theme.install(cls.application)

    def menu(self, own=1, phase='half'):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        window = Window(data_setup.paths(Path(folder.name)))
        self.addCleanup(lambda: (setattr(window, 'leaving', True), window.close()))
        window.push(Screen(window))
        names = {1: 'Italy', 2: 'Poland'}
        model = SimpleNamespace(state=SimpleNamespace(managed_country=own),
                                goaldat=SimpleNamespace(country_names=names), home=lambda fixture: 1)
        day = SimpleNamespace(model=model, fixture=SimpleNamespace(side_a=1, side_b=2),
                              kind_name='friendly', replay_auto=False, watch=True,
                              asks_watch=lambda *args: False, exit=lambda: None,
                              set_replay_auto=lambda *args: None, refresh_menu=lambda *args: None)
        def lineup(screen, country):
            screen.lineups[country] = ('4-4-2', [])
            return QWidget()
        with patch.object(MenuScreen, '_lineup', lineup), patch('goal2.ui.s15_match_menu.for_fixture') as kits:
            kits.return_value.colour.return_value = theme.HEADING
            screen = MenuScreen(window, day, phase)
        window.push(screen)
        window.show()
        self.application.processEvents()
        def visit(kind, country):
            child = Screen(window)
            child.title = f'{names[country]} {kind}'
            child.name_label.setText(child.title)
            return window.push(child)
        screen.players = lambda country: visit('players', country)
        screen.tactics = lambda country: visit('team tactics', country)
        return window, screen

    def key(self, window, key):
        QTest.keyClick(window, key)
        self.application.processEvents()

    def caption(self, screen):
        return screen.highlighted().text_label.text()

    def choose(self, screen, text):
        screen.highlight(next(i for i, o in enumerate(screen.options) if o.text_label.text() == text))

    def test_up_from_play_reaches_managed_players_for_either_side_and_phase(self):
        for own in (1, 2):
            for phase in ('before', 'half', 'stop'):
                with self.subTest(own=own, phase=phase):
                    window, screen = self.menu(own, phase)
                    for _ in range(3): self.key(window, Qt.Key.Key_Up)
                    self.assertEqual(self.caption(screen), f'{screen.model.goaldat.country_names[own]} players')

    def test_left_and_right_select_visible_country_without_changing_row(self):
        window, screen = self.menu()
        self.choose(screen, 'Italy players')
        self.key(window, Qt.Key.Key_Left)
        self.assertEqual(self.caption(screen), f'{screen.model.goaldat.country_names[screen.home_country]} players')
        self.key(window, Qt.Key.Key_Right)
        self.assertEqual(self.caption(screen), f'{screen.model.goaldat.country_names[screen.away_country]} players')
        self.key(window, Qt.Key.Key_Up)
        self.assertEqual(self.caption(screen), f'{screen.model.goaldat.country_names[screen.away_country]} team tactics')

    def test_rows_do_not_visit_the_other_column_and_remember_it_after_shared_rows(self):
        for country in ('Italy', 'Poland'):
            with self.subTest(country=country):
                window, screen = self.menu()
                self.choose(screen, country + ' players')
                self.key(window, Qt.Key.Key_Down)
                self.assertEqual(self.caption(screen), 'tournament')
                for _ in range(2): self.key(window, Qt.Key.Key_Down)
                for _ in range(3): self.key(window, Qt.Key.Key_Up)
                self.assertEqual(self.caption(screen), country + ' players')

    def test_enter_and_escape_keep_the_chosen_country_and_option(self):
        window, screen = self.menu()
        self.choose(screen, 'Italy players')
        self.key(window, Qt.Key.Key_Left)
        expected = self.caption(screen)
        self.key(window, Qt.Key.Key_Return)
        self.assertEqual(window.current().title, expected)
        self.key(window, Qt.Key.Key_Escape)
        self.assertIs(window.current(), screen)
        self.assertEqual(self.caption(screen), expected)

    def test_mouse_and_own_shortcuts_keep_their_targets(self):
        for own in (1, 2):
            with self.subTest(own=own):
                window, screen = self.menu(own)
                name = screen.model.goaldat.country_names[own]
                self.key(window, Qt.Key.Key_Space)
                self.assertEqual(window.current().title, name + ' players')
                self.key(window, Qt.Key.Key_Escape)
                self.key(window, Qt.Key.Key_T)
                self.assertEqual(window.current().title, name + ' team tactics')
                self.key(window, Qt.Key.Key_Escape)
                target = next(o for o in screen.options if o.text_label.text() == 'Poland players')
                target.clicked.emit()
                self.assertEqual(window.current().title, 'Poland players')

    def test_lineup_rebuild_preserves_the_country_and_row(self):
        window, previous = self.menu(phase='before')
        self.choose(previous, 'Poland players')
        _, fresh = self.menu(phase='before')
        fresh.restore_navigation(previous)
        self.assertEqual(self.caption(fresh), 'Poland players')
        self.key(fresh.window_, Qt.Key.Key_Up)
        self.assertEqual(self.caption(fresh), 'Poland team tactics')


if __name__ == '__main__':
    unittest.main()
