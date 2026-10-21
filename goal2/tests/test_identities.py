"""[designed: T92; confirmed: E031 C15/C30] Renaming a player and the manager."""
import json
from pathlib import Path
import tempfile
import unittest

from goal2.tests import requires

requires.require(modules=('PySide6',), **requires.HALFTIME)

from PySide6.QtTest import QTest  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402
from goal2.desktop.model import DesktopModel, MANAGER  # noqa: E402
from goal2.desktop.window import ManagementWindow  # noqa: E402
from goal2.game import identities  # noqa: E402
from goal2.game.session_save import SessionSaveError, decode, encode  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]


def document(model):
    return json.loads(encode(model.state, model.template_bytes))


class Validation(unittest.TestCase):
    def test_lengths_and_characters(self):
        clean = identities.clean
        self.assertEqual(clean('  Abcdefghijkl ', 12), 'Abcdefghijkl')
        self.assertRaises(ValueError, clean, 'Abcdefghijklm', 12)
        self.assertEqual(clean('Abcdefghijklmn', 14), 'Abcdefghijklmn')
        self.assertRaises(ValueError, clean, 'Abcdefghijklmno', 14)
        for bad in ('', '   ', 'Na€me', 'Tab\there'):
            self.assertRaises(ValueError, clean, bad, 12)
        self.assertEqual(clean('Müller', 12), 'Müller', 'CP437 letters are allowed')


class Renaming(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.folder = tempfile.TemporaryDirectory();self.addCleanup(self.folder.cleanup)
        self.model = DesktopModel.open(ROOT / '.cache/e010-r0008-halftime.sav', ROOT / '.cache/GOAL.DAT',
                                       Path(self.folder.name) / 'game.g2save', country=8)
        self.window = ManagementWindow(self.model);self.window.resize(1440, 900);self.window.show()
        QTest.qWaitForWindowActive(self.window)
        self.addCleanup(lambda: (self.window.close(), self.window.deleteLater(), self.app.processEvents()))

    def answer(self, text):
        self.window.prompt_text = lambda *args: text

    def test_an_unrenamed_session_saves_as_before(self):
        doc = document(self.model)
        self.assertIn(doc['version'], (1, 2, 3));self.assertNotIn('identities', doc['state'])
        self.assertEqual(self.model.manager, MANAGER)

    def test_a_renamed_player_shows_everywhere_and_nothing_else_changes(self):
        w = self.window;w.navigate(1)
        captain = w.draft()[1];row = self.model.state.managed_squad.index(captain)
        w.table.setCurrentCell(row, 1);before = document(self.model)
        w.tactics[0][1].click();draft = w.draft()  # an unconfirmed tactics draft
        self.answer('  Hagi ');w.rename_selected()
        self.assertEqual(self.model.state.player_renames, {captain: 'Hagi'})
        self.assertEqual(w.status.text(), f"Renamed {self.model._goaldat.player_names[captain]} to Hagi")
        initial = self.model.goaldat.player_initials[captain]
        self.assertEqual(w.team_roster.rows[row][1], f'{initial} Hagi')
        self.assertEqual(w.team_card.card['full_name'], f'{initial} Hagi')
        self.assertEqual(w.table.item(row, 1).text(), 'Hagi')
        self.assertIn('Hagi', w.desk_captain.text());self.assertEqual(w.captain.currentText(), 'Hagi')
        self.assertEqual(self.model.view()['players'][row]['name'], 'Hagi')
        # The goal list and the watched match's ratings read the same table.
        self.assertEqual(self.model.goaldat.player_names[captain], 'Hagi')
        self.assertEqual((w.draft(), w.table.currentRow()), (draft, row), 'draft and selection kept')
        after = document(self.model)
        self.assertEqual(after['version'], 4);self.assertEqual(after['state'].pop('identities'), {'players': {str(captain): 'Hagi'}})
        self.assertEqual(after['state'], before['state'], 'only the names differ')
        self.assertTrue(self.model.unsaved)
        # Pool cards name him too.
        w.navigate(2);w.table.setCurrentCell(row, 1)
        self.assertEqual(w.pool_out_card.card['name'], 'Hagi')
        # The original name removes the rename.
        w.navigate(1);self.answer(self.model._goaldat.player_names[captain]);w.rename_selected()
        self.assertEqual(self.model.state.player_renames, {})
        self.assertNotIn('identities', document(self.model)['state'])

    def test_cancel_and_invalid_names_change_nothing(self):
        w = self.window;w.navigate(1);before = document(self.model)
        self.answer(None);w.rename_selected()
        self.answer('Thirteenchars');w.rename_selected()
        self.assertIn('at most 12', w.status.text())
        self.answer('   ');w.rename_manager()
        self.assertEqual(document(self.model), before);self.assertFalse(self.model.unsaved)

    def test_manager_name_shows_and_survives_resume_and_a_new_campaign(self):
        w = self.window
        word = self.model.state.managed_squad[3];self.model.rename_player(word, 'Popescu')
        self.answer('Anghel Iordanescu');w.rename_manager()
        self.assertIn('at most 14', w.status.text());self.assertEqual(self.model.manager, MANAGER)
        self.answer('A Iordanescu');w.rename_manager()
        self.assertEqual(self.model.manager, 'A Iordanescu')
        self.assertTrue(w.career_line.text().startswith('A Iordanescu / '))
        self.assertIn('A Iordanescu', w.desk_own.text())
        self.model.save(self.model.save_path)
        resumed = DesktopModel.from_save(self.model.save_path, ROOT / '.cache/GOAL.DAT')
        self.assertEqual((resumed.state.player_renames, resumed.manager), ({word: 'Popescu'}, 'A Iordanescu'))
        self.assertEqual(resumed.goaldat.player_names[word], 'Popescu')
        self.assertEqual(resumed.summary()['manager'], 'A Iordanescu')
        resumed.new_campaign(5)
        self.assertEqual((resumed.state.player_renames, resumed.manager), ({}, 'A Iordanescu'))

    def test_a_preview_or_a_running_match_refuses(self):
        w = self.window;called = []
        w.prompt_text = lambda *args: called.append(args) or 'Nobody'
        w.country.setCurrentIndex(w.country.findData(13));self.app.processEvents()
        self.assertIsNotNone(w.preview);w.navigate(1);w.rename_selected();w.rename_manager()
        self.assertFalse(w.rename.isEnabled() or w.desk_manager.isEnabled())
        w.country.setCurrentIndex(w.country.findData(8));self.app.processEvents()
        self.model.match_pending = True
        try:
            w.rename_selected();self.assertIn('match', w.status.text().lower())
        finally:
            self.model.match_pending = False
        self.assertEqual(called, []);self.assertEqual(self.model.state.player_renames, {})

    def test_a_preview_shows_original_names_and_the_same_manager(self):
        w = self.window;word = self.model.state.managed_squad[0]
        self.model.rename_player(word, 'Smith');self.model.rename_manager('Coach');w.refresh()
        w.country.setCurrentIndex(w.country.findData(13));self.app.processEvents()
        self.assertEqual(w.preview.goaldat.player_names[word], self.model._goaldat.player_names[word])
        self.assertTrue(w.career_line.text().startswith('Coach / '))

    def test_a_malformed_rename_is_refused_on_save(self):
        self.model.state.player_renames = {5: 'Thirteenchars'}
        with self.assertRaises(SessionSaveError):
            encode(self.model.state, self.model.template_bytes)

    def test_a_malformed_identities_object_is_refused(self):
        self.model.rename_player(self.model.state.managed_squad[0], 'Smith')
        doc = document(self.model)
        for bad in ({}, {'players': {}}, {'players': {'0': 'X'}}, {'players': {'01': 'X'}},
                    {'players': {'5': ' X'}}, {'players': {'5': 'Thirteenchars'}}, {'players': {}, 'manager': ''},
                    {'players': {'5': 'X'}, 'extra': 1}, {'players': ['X']}):
            doc['state']['identities'] = bad
            with self.assertRaises(SessionSaveError, msg=bad):
                decode(json.dumps(doc).encode())
        doc['state'].pop('identities')
        with self.assertRaises(SessionSaveError):
            decode(json.dumps(doc).encode())  # version 4 requires identities
        doc['version'] = 3;state, _ = decode(json.dumps(doc).encode())
        self.assertEqual((state.player_renames, state.manager_name), ({}, ''))


if __name__ == '__main__':
    unittest.main()
