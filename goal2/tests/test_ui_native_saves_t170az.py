"""[designed: T170az] Existing Save and Continue controls for explicit native owners."""

import json
from pathlib import Path
import shutil
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch
import zipfile

from goal2.desktop import data_setup
from goal2.desktop.native_save_owner import NativeSaveOwner
from goal2.engine.original_match.image import Image
from goal2.game import engine_tables, native_season_save
from goal2.game.season_publication import PublishedCall, SeasonCampaign
from goal2.tests import pypy_engine, requires
from goal2.tests.season_oracle import component_of
from goal2.tests.test_prematch_preview_t170s import reference_raw
from goal2.tests.test_season_oracle_t170d import ARTIFACTS, CASES, GOAL_DAT, checkpoint
from goal2.ui import saves


def reference_owner():
    state = Image.from_bytes(reference_raw()).state(engine_tables.load())
    return NativeSaveOwner(SeasonCampaign(state))


def named_payload(path, raw, *, meta_size=None):
    meta = dict(format=saves.FORMAT, version=saves.NATIVE_VERSION, name='Invalid',
                saved='2026-11-27T00:00:00+00:00')
    with zipfile.ZipFile(path, 'w', zipfile.ZIP_DEFLATED) as archive:
        archive.writestr(saves.META, json.dumps(meta) if meta_size is None else b' ' * meta_size)
        archive.writestr(saves.NATIVE_SESSION, raw)


class Archive(unittest.TestCase):
    def setUp(self):
        folder = TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.folder = Path(folder.name)
        self.owner = reference_owner()

    def test_explicit_native_list_has_real_summary_and_default_loader_refuses(self):
        path = saves.write(self.owner, self.folder, 'A native campaign')
        self.assertFalse(self.owner.unsaved)
        self.assertEqual(saves.entries(self.folder, GOAL_DAT), [])
        with self.assertRaisesRegex(saves.SaveError, 'explicit native career opener'):
            saves.load(path, GOAL_DAT)
        entry, = saves.entries(self.folder, GOAL_DAT, native=True)
        self.assertEqual(entry.name, 'A native campaign')
        self.assertEqual(entry.model.summary(), {
            'country': 'Denmark', 'manager': 'B Ob',
            'year_stage': '2028 · Continental qualifying', 'next': 'Sweden',
        })
        self.assertFalse(entry.model.unsaved)
        self.assertEqual(entry.model.campaign.state, self.owner.campaign.state)

    @requires.need(**requires.HALFTIME)
    def test_legacy_and_native_names_coexist_and_each_replacement_stays_in_its_route(self):
        from goal2.desktop.model import DesktopModel

        legacy = DesktopModel.open(requires.CACHE / data_setup.TEMPLATE_NAME, GOAL_DAT,
                                   self.folder / 'unused', country=20)
        first = saves.write(legacy, self.folder, 'Same name')
        original = first.read_bytes()
        second = saves.write(self.owner, self.folder, 'Same name')
        self.assertEqual((first.name, second.name), ('same-name.g2game', 'same-name.native.g2game'))
        self.assertEqual(first.read_bytes(), original)
        self.assertEqual(saves.replaces(reference_owner(), self.folder, 'Same name'), second)
        self.assertIsNone(saves.replaces(self.owner, self.folder, 'Same name'))
        self.assertIsInstance(saves.load(first, GOAL_DAT, native=True), DesktopModel)
        self.assertEqual({entry.path for entry in saves.entries(self.folder, GOAL_DAT, native=True)},
                         {first, second})
        self.assertEqual([entry.path for entry in saves.entries(self.folder, GOAL_DAT)], [first])

    def test_native_write_failure_keeps_prior_bytes_name_path_and_dirty_status(self):
        path = saves.write(self.owner, self.folder, 'Kept')
        old = path.read_bytes()
        replacement = reference_owner()
        with patch('goal2.ui.saves.write_atomic', side_effect=OSError('read only')):
            with self.assertRaisesRegex(saves.SaveError, 'cannot write'):
                saves.write(replacement, self.folder, 'Kept')
        self.assertEqual(path.read_bytes(), old)
        self.assertTrue(replacement.unsaved)
        self.assertEqual((replacement.save_name, replacement.save_path, replacement.saved), (None, None, None))
        self.assertEqual(list(self.folder.iterdir()), [path])

    def test_invalid_native_archive_uses_native_validation_and_bounded_reads(self):
        path = self.folder / 'invalid.native.g2game'
        named_payload(path, b'not native')
        with self.assertRaisesRegex(saves.SaveError, 'cannot read native save'):
            saves.load(path, GOAL_DAT, native=True)
        entry, = saves.entries(self.folder, GOAL_DAT, native=True)
        self.assertIsNone(entry.model)
        self.assertEqual(entry.name, 'Invalid')
        self.assertEqual(saves.entries(self.folder, GOAL_DAT), [])
        raw = native_season_save.encode(self.owner.campaign)
        named_payload(path, raw)
        with patch.object(native_season_save, '_MAX_DOCUMENT', len(raw) - 1):
            with self.assertRaisesRegex(saves.SaveError, 'size limit'):
                saves.load(path, GOAL_DAT, native=True)
        named_payload(path, raw, meta_size=65537)
        with self.assertRaisesRegex(saves.SaveError, 'metadata exceeds its size limit'):
            saves.load(path, GOAL_DAT, native=True)


@requires.need(modules=('PySide6', 'unicorn'),
               files=(*requires.HALFTIME['files'], ARTIFACTS[2]['name']))
class Journey(unittest.TestCase):
    def setUp(self):
        from PySide6.QtWidgets import QApplication
        from goal2.ui.window import Window

        self.app = QApplication.instance() or QApplication([])
        folder = TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.target = data_setup.paths(Path(folder.name))
        self.target.data.mkdir()
        for name, _ in data_setup.WINDOW_MANIFEST:
            shutil.copyfile(requires.CACHE / name, self.target.data / name)
        self.loaded = []
        self.window = Window(self.target, open_native_save=self.loaded.append)
        self.window.show()
        self.addCleanup(self.close_window)

    def close_window(self):
        self.window.leave()
        self.window.deleteLater()
        self.app.processEvents()

    def key(self, key):
        from PySide6.QtTest import QTest

        QTest.keyClick(self.window, key)
        self.app.processEvents()

    def test_f7_and_continue_restore_a_real_committed_round_and_retry_a_bad_read(self):
        from PySide6.QtCore import Qt
        from PySide6.QtTest import QTest
        from goal2.ui.s02_start import StartScreen
        from goal2.ui.s21_save import SaveScreen, save
        from goal2.ui.screen import Screen

        image = Image.from_bytes(component_of(checkpoint(CASES[2]), GOAL_DAT))
        state = image.state(engine_tables.load())
        _, output, observed = pypy_engine.call('goal2.tests.test_native_round_view_t170aw:advance', state)
        self.assertEqual(observed['status'], 'complete')
        record = PublishedCall(*(observed[key] for key in ('call_number', 'status', 'input_hash', 'output_hash')))
        owner = NativeSaveOwner(SeasonCampaign.from_committed(output, (record,)))
        self.window.career = owner
        home = self.window.push(Screen(self.window))
        home.bind((Qt.Key.Key_F7,), 'save', lambda: save(self.window, owner))

        self.key(Qt.Key.Key_F7)
        self.assertIsInstance(self.window.current(), SaveScreen)
        QTest.keyClicks(self.window, 'Native round')
        self.key(Qt.Key.Key_Escape)
        self.assertIs(self.window.current(), home)
        self.assertIsNone(owner.save_path)
        self.assertTrue(owner.unsaved)

        self.key(Qt.Key.Key_F7)
        QTest.keyClicks(self.window, 'Native round')
        self.key(Qt.Key.Key_Return)
        self.assertIs(self.window.current(), home)
        self.assertFalse(owner.unsaved)
        self.key(Qt.Key.Key_F7)
        self.assertEqual(self.window.current().field.text, 'Native round')
        self.key(Qt.Key.Key_Escape)

        start = self.window.start()
        self.assertIsInstance(start, StartScreen)
        self.assertIn('Continue Denmark', start.continue_text.text())
        self.assertEqual(start.facts['manager'].text(), owner.summary()['manager'])
        known = owner.save_path.read_bytes()
        owner.save_path.write_bytes(b'broken')
        self.key(Qt.Key.Key_Y)
        self.assertIn('cannot be opened', start.problem.text())
        self.assertIn('not a goal2 save', start.problem.text())
        self.assertIs(self.window.career, owner)
        self.assertFalse(self.loaded)
        self.key(Qt.Key.Key_N)
        self.assertIsNone(start.failed)
        self.key(Qt.Key.Key_Y)
        self.assertIsNotNone(start.failed)
        owner.save_path.write_bytes(known)
        self.key(Qt.Key.Key_Y)
        self.assertIsNone(start.failed)
        self.assertEqual(len(self.loaded), 1)

        self.window.start()
        self.key(Qt.Key.Key_Return)
        self.assertEqual(len(self.loaded), 2)
        for restored in self.loaded:
            self.assertIsNot(restored, owner)
            self.assertEqual(restored.campaign.state, output)
            self.assertEqual(restored.campaign.published, (record,))
            self.assertEqual(restored.campaign.revision, 1)
            self.assertFalse(restored.unsaved)
            self.assertEqual(restored.save_name, owner.save_name)
