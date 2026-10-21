"""[designed: T87] Save, Save as, and the decisions before replacing or quitting a game."""
import copy
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from goal2.tests import requires

requires.require(modules=('PySide6',), **requires.HALFTIME)

from PySide6.QtCore import Qt  # noqa: E402
from PySide6.QtTest import QTest  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402
from goal2.desktop.model import DesktopModel  # noqa: E402
from goal2.desktop.window import ManagementWindow  # noqa: E402
from goal2.game import session_save  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]


class Closing:
    """A user's close request (window manager, not a programmatic close())."""
    def __init__(self):self.ignored = False
    def spontaneous(self):return True
    def ignore(self):self.ignored = True
    def accept(self):pass


class Decisions(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        folder = tempfile.TemporaryDirectory();self.addCleanup(folder.cleanup)
        self.folder = Path(folder.name);self.save = self.folder / 'game.g2save'
        self.model = DesktopModel.open(ROOT / '.cache/e010-r0008-halftime.sav', ROOT / '.cache/GOAL.DAT', self.save, country=4)
        self.window = ManagementWindow(self.model);self.window.show()
        self.addCleanup(lambda: (self.window.close(), self.window.deleteLater(), self.app.processEvents()))
        self.asked = []
        # An unexpected question fails instead of opening a modal box that would wait forever.
        unexpected = patch.object(self.window, 'ask', side_effect=AssertionError('unexpected question'))
        unexpected.start();self.addCleanup(unexpected.stop)

    def answer(self, *choices):
        """Script the player's answers; record each question."""
        replies = list(choices)
        def ask(title, text, options):
            self.asked.append((title, text, [key for key, _ in options]))
            return replies.pop(0)
        return patch.object(self.window, 'ask', side_effect=ask)

    def progress(self):
        """A confirmed change since the last save."""
        state = self.model.state
        self.model.confirm(list(state.starting_eleven), state.starting_eleven[0], state.country_tactics ^ 1)
        self.window.refresh()

    def draft(self):
        box = self.window.tactics[0][1];box.setChecked(not box.isChecked())

    def files(self):
        return sorted((p.name, p.read_bytes()) for p in self.folder.iterdir())

    def test_a_clean_game_replaces_and_quits_without_asking(self):
        with self.answer():
            self.window.country.setCurrentIndex(self.window.country.findData(9))
            self.window.new.click()
            self.assertEqual(self.model.state.managed_country, 9)
            self.window.quit_game()
        self.assertEqual(self.asked, []);self.assertFalse(self.window.isVisible())

    def test_unsaved_progress_and_a_draft_are_named_and_cancel_changes_nothing(self):
        self.progress();self.draft()
        before = copy.deepcopy(self.model.state);files = self.files()
        with self.answer('cancel'):
            self.window.friendly.click()
        title, text, options = self.asked[0]
        self.assertIn('progress confirmed since the last save', text)
        self.assertIn('unconfirmed squad, captain or tactics draft', text)
        self.assertEqual(options, ['save', 'discard', 'cancel'])
        self.assertEqual((self.model.state, self.files()), (before, files))
        self.assertIn('cancelled; nothing changed', self.window.status.text())

    def test_a_draft_alone_cannot_be_saved_away(self):
        self.draft()
        with self.answer('cancel'):
            self.window.new.click()
        self.assertEqual(self.asked[0][2], ['discard', 'cancel'], 'Save never confirms a draft')
        self.assertNotIn('progress', self.asked[0][1])

    def test_continue_without_saving_replaces_and_writes_nothing(self):
        self.progress();files = self.files()
        with self.answer('discard'):
            self.window.country.setCurrentIndex(self.window.country.findData(9))
            self.window.new.click()
        self.assertEqual(self.model.state.managed_country, 9)
        self.assertEqual(self.files(), files)

    def test_save_and_continue_writes_the_confirmed_state_then_replaces(self):
        self.progress();self.draft()
        confirmed = copy.deepcopy(self.model.state)
        with self.answer('save'):
            self.window.country.setCurrentIndex(self.window.country.findData(9))
            self.window.new.click()
        saved, _ = session_save.load(self.save)
        self.assertEqual(saved, confirmed, 'the draft is excluded; the confirmed state is saved')
        self.assertEqual(self.model.state.managed_country, 9)

    def test_a_failed_save_keeps_the_decision_pending(self):
        self.model.save(self.save);prior = self.save.read_bytes()
        self.progress();before = copy.deepcopy(self.model.state)
        with self.answer('save', 'save'), patch.object(self.model, 'save', side_effect=ValueError('Cannot save game: disk full')):
            self.window.new.click()
            closing = Closing();self.window.closeEvent(closing)
        self.assertEqual(self.model.state, before)
        self.assertTrue(closing.ignored, 'the window must stay open')
        self.assertEqual(self.save.read_bytes(), prior)
        self.assertIn('disk full', self.window.status.text())

    def test_a_users_close_asks_but_a_programmatic_close_does_not(self):
        self.progress()
        with self.answer('cancel'):
            closing = Closing();self.window.closeEvent(closing)
        self.assertTrue(closing.ignored);self.assertEqual(len(self.asked), 1)
        with self.answer():
            self.window.close()
        self.assertFalse(self.window.isVisible());self.assertEqual(len(self.asked), 1)

    def test_quitting_during_a_match_offers_no_save(self):
        self.progress();self.model.match_pending = True
        try:
            with self.answer('cancel'):
                self.window.quit_game()
        finally:
            self.model.match_pending = False
        self.assertEqual(self.asked[0][2], ['discard', 'cancel'])
        self.assertIn('running match will be cancelled', self.asked[0][1])
        self.assertTrue(self.window.isVisible())

    def test_save_as_asks_before_overwriting_another_file(self):
        other = self.folder / 'other.g2save';other.write_bytes(b'keep me')
        with self.answer('cancel'):
            self.assertFalse(self.window.save_to(str(other)))
        self.assertEqual(other.read_bytes(), b'keep me')
        self.assertEqual(self.asked[0][2], ['overwrite', 'cancel'])
        with self.answer('overwrite'):
            self.assertTrue(self.window.save_to(str(other)))
        self.assertEqual(session_save.load(other)[0], self.model.state)
        self.assertEqual(self.model.save_path, other)
        with self.answer():
            self.assertTrue(self.window.save_to(str(other)), 'saving over the current file does not ask')
        self.assertEqual(len(self.asked), 2)

    def test_resume_replacement_asks_too(self):
        self.model.save(self.save);self.progress()
        with self.answer('discard'):
            self.window.resume.click()
        self.assertEqual(self.asked[0][0], 'Resume another save')
        self.assertFalse(self.model.unsaved)

    def test_ctrl_s_and_ctrl_q_use_the_same_paths(self):
        self.progress()
        self.window.activateWindow();QTest.qWaitForWindowActive(self.window);self.window.table.setFocus()
        QTest.keyClick(self.window, Qt.Key.Key_S, Qt.KeyboardModifier.ControlModifier);self.app.processEvents()
        self.assertTrue(self.save.is_file());self.assertFalse(self.model.unsaved)
        self.draft()
        with self.answer('cancel'):
            QTest.keyClick(self.window, Qt.Key.Key_Q, Qt.KeyboardModifier.ControlModifier);self.app.processEvents()
        self.assertEqual(self.asked[0][0], 'Quit');self.assertTrue(self.window.isVisible())

    def test_the_engines_squad_reorder_is_not_a_draft(self):
        state = self.model.state
        state.starting_eleven = list(reversed(state.starting_eleven));self.model.mark_saved()
        self.window.refresh()
        self.assertEqual(self.window.losses(), [])


if __name__ == '__main__':
    unittest.main()
