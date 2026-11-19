"""[designed: owner, 2026-11-02, #518] Launch's Saved career panel shows a core save (G2C1, docs/core.md) and
resumes it: the portable build's default save is a core save (T153), and it showed SAVE NOT USABLE."""
from pathlib import Path
import tempfile
import unittest

from goal2.tests import requires

NEEDS = dict(modules=('unicorn', 'PySide6'), files=('e006-r0001-main.sav', 'GOAL.DAT'))


@requires.need(**NEEDS)
class CoreSave(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from PySide6.QtWidgets import QApplication
        from goal2.desktop.core_model import CoreModel
        cls.app = QApplication.instance() or QApplication([])
        cls.folder = tempfile.TemporaryDirectory()
        cls.save = Path(cls.folder.name) / 'desktop.g2core'
        model = CoreModel.open(requires.CACHE / 'e006-r0001-main.sav', requires.CACHE / 'GOAL.DAT', cls.save)
        model.save()
        cls.desk, cls.memory = model.desk(), model.memory_sha256()

    @classmethod
    def tearDownClass(cls):
        cls.folder.cleanup()

    def window(self):
        from goal2.desktop.launch import LaunchWindow
        opened = []
        w = LaunchWindow(requires.CACHE / 'GOAL.DAT', None, self.save, opened.append,
                         core_boot=requires.CACHE / 'e039-r0005-date-call.sav')
        self.addCleanup(w.close)
        return w, opened

    def test_the_panel_summarises_a_core_save(self):
        w, _ = self.window()
        country = self.desk['team']['name']
        self.assertEqual(w.saved_country.text(), country.upper())
        self.assertEqual(w.saved_fields['manager'].text(), self.desk['manager'])
        self.assertIn(str(self.desk['year']), w.saved_fields['campaign'].text())
        self.assertTrue(w.resume.isEnabled());self.assertEqual(w.resume.text(), 'RESUME ' + country.upper())
        self.assertEqual(w.error.text(), '')

    def test_resume_opens_the_core_save_at_its_saved_state(self):
        from goal2.desktop.core_model import CoreModel
        w, opened = self.window()
        w.resume.click()
        self.assertEqual(len(opened), 1)
        self.assertIsInstance(opened[0], CoreModel)
        self.assertEqual(opened[0].memory_sha256(), self.memory)
        self.assertEqual(opened[0].save_path, self.save)

    def test_a_damaged_core_save_is_named_not_usable(self):
        """[designed] A truncated or corrupted core save shows SAVE NOT USABLE with Resume off, as read_saved promises,
        instead of raising zlib.error out of LaunchWindow: the portable start reads saves/desktop.g2core in the
        constructor, so one damaged file stopped every start with no window (#420's default-start path)."""
        from goal2.desktop.launch import LaunchWindow
        good = self.save.read_bytes()
        n = 8 + int.from_bytes(good[4:8], 'little')
        flipped = bytearray(good);flipped[n + (len(good) - n) // 2] ^= 0xFF
        damaged = {'truncated': good[:n + (len(good) - n) // 2], 'flipped': bytes(flipped)}
        for name, raw in damaged.items():
            with self.subTest(name), tempfile.TemporaryDirectory() as folder:
                path = Path(folder) / 'desktop.g2core';path.write_bytes(raw)
                w = LaunchWindow(requires.CACHE / 'GOAL.DAT', None, path, lambda model: None,
                                 core_boot=requires.CACHE / 'e039-r0005-date-call.sav')
                self.addCleanup(w.close)
                self.assertEqual(w.saved_country.text(), 'SAVE NOT USABLE')
                self.assertFalse(w.resume.isEnabled())
                self.assertIn('damaged', w.error.text())

    def test_open_refuses_a_file_that_is_not_a_savestate(self):
        from goal2.desktop.core_model import CoreModel
        with tempfile.TemporaryDirectory() as folder:
            bad = Path(folder) / 'not-a-zip.sav';bad.write_bytes(b'not a savestate')
            with self.assertRaises(ValueError):
                CoreModel.open(bad, requires.CACHE / 'GOAL.DAT', Path(folder) / 'x.g2core')


if __name__ == '__main__':
    unittest.main()
