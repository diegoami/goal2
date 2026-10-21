"""[designed: T86] Launch: saved-career summary, Resume, failures with Retry/Load another, and a
reviewed new career that writes nothing until it is started."""
import json
from pathlib import Path
import tempfile
import unittest

from goal2.tests import requires

requires.require(modules=('PySide6',), **requires.HALFTIME)

from PySide6.QtCore import Qt  # noqa: E402
from PySide6.QtTest import QTest  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402
from goal2.desktop.launch import LaunchWindow  # noqa: E402
from goal2.desktop.model import DesktopModel  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
TEMPLATE = ROOT / '.cache/e010-r0008-halftime.sav'
DATA = ROOT / '.cache/GOAL.DAT'


class Launch(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])
        cls.folder = tempfile.TemporaryDirectory()
        cls.save = Path(cls.folder.name) / 'career.g2save'
        model = DesktopModel.open(TEMPLATE, DATA, cls.save, country=4)
        model.new_campaign(4, 1992);model.save(cls.save)
        cls.saved_bytes = cls.save.read_bytes()

    @classmethod
    def tearDownClass(cls):
        cls.folder.cleanup()

    def setUp(self):
        self.opened = []

    def window(self, path=None, template=TEMPLATE):
        window = LaunchWindow(DATA, template, path or self.save, self.opened.append)
        window.show();QTest.qWaitForWindowExposed(window)
        self.addCleanup(lambda: (window.close(), window.deleteLater(), self.app.processEvents()))
        return window

    def key(self, window, key):
        QTest.keyClick(window.focusWidget() or window, key);self.app.processEvents()

    def files(self):
        return sorted((p.name, p.read_bytes()) for p in Path(self.folder.name).iterdir())

    def test_summary_names_the_saved_career(self):
        w = self.window()
        expected = DesktopModel.from_save(self.save, DATA).summary()
        self.assertEqual(w.saved_country.text(), 'BULGARIA')
        self.assertEqual({k: v.text() for k, v in w.saved_fields.items()},
                         {k: expected[k] for k in w.saved_fields})
        self.assertEqual(expected['campaign'], '1992 Continental qualifying')
        self.assertIn('#265', expected['manager'])
        self.assertTrue(w.resume.isEnabled());self.assertEqual(w.resume.text(), 'RESUME BULGARIA')
        self.assertFalse(w.retry.isVisible())

    def test_resume_opens_the_validated_saved_game(self):
        w = self.window()
        w.resume.click();self.app.processEvents()
        self.assertEqual(len(self.opened), 1)
        self.assertEqual(self.opened[0].state, DesktopModel.from_save(self.save, DATA).state)
        self.assertEqual(self.save.read_bytes(), self.saved_bytes)

    def test_failures_offer_retry_and_load_another_and_change_nothing(self):
        broken = Path(self.folder.name) / 'broken.g2save';broken.write_bytes(b'not a save')
        doc = json.loads(self.saved_bytes);doc['version'] = 99
        newer = Path(self.folder.name) / 'newer.g2save';newer.write_text(json.dumps(doc))
        cases = ((Path(self.folder.name) / 'missing.g2save', 'no save here yet'),
                 (broken, 'invalid session save JSON'), (newer, 'unsupported session save version: 99'))
        for path, reason in cases:
            before = self.files()
            w = self.window(path)
            self.assertIn(reason, w.error.text())
            self.assertFalse(w.resume.isEnabled());self.assertTrue(w.retry.isVisible())
            w.resume.click();w.retry.click();self.app.processEvents()
            self.assertEqual((self.opened, self.files()), ([], before))
            # Load another reaches the good save from the same window.
            w.other_path.setText(str(self.save));w.load_other.click()
            self.assertTrue(w.resume.isEnabled());self.assertEqual(w.error.text(), '')
        # Retry reads the file again once it has been repaired.
        w = self.window(broken);broken.write_bytes(self.saved_bytes);w.retry.click()
        self.assertEqual(w.saved_country.text(), 'BULGARIA')

    def test_new_career_browses_and_reviews_without_writing_then_starts(self):
        before = self.files()
        w = self.window()
        w.new_career.click()
        self.assertEqual(w.pages.currentIndex(), 1)
        w.country_list.setCurrentRow(6);w.start_year.setCurrentIndex(w.start_year.findData(1992))
        w.preview()
        self.assertEqual(w.preview_country.text(), 'DENMARK')
        self.assertIn('1992 Continental qualifying', w.preview_fields['first'].text())
        self.assertIn('G05/O12', w.preview_fields['profile'].text())
        self.assertEqual(len(w.roster.text().splitlines()), 20)
        w.to_review.click()
        self.assertEqual(w.pages.currentIndex(), 2)
        self.assertEqual(w.review_fields['country'].text(), 'Denmark')
        self.assertEqual(w.review_fields['campaign'].text(), '1992 Continental qualifying')
        self.assertEqual((self.opened, self.files()), ([], before), 'browsing and review must not write or open')
        w.start.click()
        expected = DesktopModel.open(TEMPLATE, DATA, self.save, country=1);expected.new_campaign(7, 1992)
        self.assertEqual(len(self.opened), 1)
        self.assertEqual(self.opened[0].state, expected.state)
        self.assertEqual(self.opened[0].save_path, self.save)
        self.assertEqual(self.files(), before, 'starting a career writes no save')

    def test_new_career_needs_the_template(self):
        w = self.window(template=None)
        self.assertFalse(w.new_career.isEnabled())
        self.assertTrue(w.resume.isEnabled())

    def test_keyboard_matches_the_hint_line(self):
        w = self.window()
        self.assertIs(w.focusWidget(), w.resume)
        self.key(w, Qt.Key.Key_Down);self.assertIs(w.focusWidget(), w.new_career)
        self.key(w, Qt.Key.Key_Up);self.assertIs(w.focusWidget(), w.resume)
        self.key(w, Qt.Key.Key_Down);self.key(w, Qt.Key.Key_Return)
        self.assertEqual(w.pages.currentIndex(), 1);self.assertIs(w.focusWidget(), w.country_list)
        for _ in range(6):self.key(w, Qt.Key.Key_Down)
        self.assertEqual(w.country_list.currentItem().data(Qt.ItemDataRole.UserRole), 7)
        self.key(w, Qt.Key.Key_Escape);self.assertEqual(w.pages.currentIndex(), 0)
        w.new_career.setFocus();self.key(w, Qt.Key.Key_Return);self.key(w, Qt.Key.Key_Return)
        self.assertEqual(w.pages.currentIndex(), 2);self.assertIs(w.focusWidget(), w.start)
        self.assertEqual(w.review_fields['country'].text(), 'Denmark')
        self.key(w, Qt.Key.Key_Escape);self.assertEqual(w.pages.currentIndex(), 1)
        self.key(w, Qt.Key.Key_Escape);w.other_path.setFocus();w.other_path.setText(str(self.save))
        self.key(w, Qt.Key.Key_Return)
        self.assertEqual((self.opened, w.focusWidget()), ([], w.resume), 'Enter in the path field loads; it must not also resume')
        w.new_career.setFocus();self.key(w, Qt.Key.Key_Return)
        self.key(w, Qt.Key.Key_Return);self.key(w, Qt.Key.Key_Return)
        self.assertEqual(len(self.opened), 1)
        self.assertEqual(self.opened[0].state.managed_country, 7)


if __name__ == '__main__':
    unittest.main()
