"""[designed: owner, 2026-11-02, #523/T155] Playing the next match is obvious.

From a new Core career's main window: the desk's one primary control plays the next game and reaches the captain
stop; there the suggested captain is selected, and the action that kicks off chooses watching ("Kick off and
watch", Enter) or the original's quick result ("Kick off, quick result", Q). No checkable button on the round page
is labelled as an action. The captain choice itself is the original's [confirmed:
`docs/original-game/match-and-results.md`, `images/captain-select.png`]; T143 preselects the original's best leader.
"""
import os
import tempfile
import unittest
from pathlib import Path

from goal2.tests import requires

NEEDS = dict(modules=('unicorn', 'PySide6', 'pygame'), files=('e039-r0005-date-call.sav', 'GOAL.DAT'))


@requires.need(**NEEDS)
class PlayNext(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
        os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
        os.environ.setdefault('SDL_AUDIODRIVER', 'dummy')
        from PySide6.QtWidgets import QApplication
        from goal2.desktop.core_model import CoreNewGame
        cls.app = QApplication.instance() or QApplication([])
        cls.folder = tempfile.TemporaryDirectory()
        # Launch's New career: the original's new game played to its first manager menu.
        model, _ = CoreNewGame(requires.CACHE / 'e039-r0005-date-call.sav', requires.CACHE / 'GOAL.DAT',
                               Path(cls.folder.name) / 'new.g2core').start(2028, 16, 'A Test')
        cls.saved = model.core.save()

    @classmethod
    def tearDownClass(cls):
        cls.folder.cleanup()

    def setUp(self):
        from goal2.core import Core
        from goal2.desktop.core_model import CoreModel
        from goal2.desktop.core_window import CoreWindow
        self.model = CoreModel(Core.load(self.saved, goal_dat=requires.CACHE / 'GOAL.DAT'), requires.CACHE / 'GOAL.DAT',
                               Path(self.folder.name) / 'game.g2core')
        self.assertFalse(self.model.in_round)
        self.w = CoreWindow(self.model);self.w.show();self.app.processEvents()
        self.addCleanup(self.close)

    def close(self):
        self.w.close();self.app.processEvents()

    def play_next(self):
        """The window's first page shows the primary play-next control without navigation; it reaches the captain."""
        w = self.w
        self.assertEqual(w.page_stack.currentIndex(), 0, 'the window opens on its first page')
        play = w.play_next
        self.assertTrue(play.property('primary'), 'the play-next control is the primary one')
        self.assertTrue(play.isVisible() and play.isEnabled())
        self.assertFalse(play.visibleRegion().isEmpty())
        self.assertIn('PLAY NEXT', play.text().upper())
        play.click();self.assertEqual(w.finish_core(300)[0], 'done');self.app.processEvents()
        r = w.core_round
        while w.fixture_views.currentIndex() == 2 and r.views.currentIndex() == 2:   # the round's results first
            r.page_next.click();self.app.processEvents()
        self.assertEqual(self.model.round_state()['stop'], 'captain')
        self.assertEqual((w.page_stack.currentIndex(), w.fixture_views.currentIndex(), r.views.currentIndex()), (3, 2, 0))
        return r

    def suggested(self, r):
        choice = self.model.round_state()['captain']
        roster = r.captain_roster
        self.assertEqual(roster.rows[roster.current][0], choice['recommended'], 'the suggested captain is selected')
        name = next(row[1] for row in roster.rows if row[0] == choice['recommended'])
        self.assertIn(name, r.captain_note.text(), 'the suggested captain is shown')
        self.assertIn('choose another captain', r.captain_note.text(), 'the page says the captain can be changed')
        return choice['recommended']

    def test_play_next_is_on_the_first_page_and_reaches_the_captain(self):
        self.suggested(self.play_next())

    def test_the_watch_action_kicks_off_watched_with_the_suggested_captain(self):
        from goal2.core import views
        r = self.play_next();captain = self.suggested(r)
        self.assertIn('watch', r.kick_off.text().lower())
        r.kick_off.click();self.assertEqual(self.w.finish_core(300)[0], 'done');self.app.processEvents()
        self.assertEqual(self.model.core.wait.kind, 'match-live')
        self.assertIsNotNone(r.viewer, 'the pitch viewer is started')
        self.assertIsNone(r.viewer.process.poll())
        self.assertNotIn(('match-live', ord('r')), self.model.driver.log)
        self.assertEqual(views.match_sides(self.model.state)['captain'], captain)

    def test_the_quick_action_kicks_off_unwatched(self):
        from goal2.core import views
        r = self.play_next();captain = self.suggested(r)
        self.assertIn('quick result', r.quick.text().lower())
        r.quick.click();self.assertEqual(self.w.finish_core(300)[0], 'done');self.app.processEvents()
        self.assertIsNone(r.viewer, 'no pitch viewer for the quick result')
        self.assertIn(('match-live', ord('r')), self.model.driver.log)
        self.assertNotEqual(self.model.core.wait.kind, 'match-live')
        self.assertEqual(views.match_sides(self.model.state)['captain'], captain)

    def test_the_advertised_q_and_c_keys_are_bound_at_the_captain_stop(self):
        from unittest.mock import patch
        from PySide6.QtCore import Qt
        from PySide6.QtTest import QTest
        r = self.play_next();captain = self.suggested(r)
        self.assertIn('(Q)', r.quick.text());self.assertIn('(C)', r.computer.text())
        for key, expected in ((Qt.Key.Key_Q, ('kick_off', captain, False)), (Qt.Key.Key_C, ('kick_off', None, True))):
            with patch.object(self.w, 'run_core', return_value=False) as action:
                QTest.keyClick(r.captain_roster, key);self.app.processEvents()
                action.assert_called_once_with(*expected)

    def test_no_checkable_button_on_the_round_page_is_labelled_as_an_action(self):
        from PySide6.QtWidgets import QAbstractButton
        r = self.play_next()
        toggles = [b.text() for b in r.holder.findChildren(QAbstractButton) if b.isCheckable()]
        self.assertEqual(toggles, [], 'a control that looks like an action only toggles a setting')


if __name__ == '__main__':
    unittest.main()
