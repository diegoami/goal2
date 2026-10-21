"""[designed: #278] The game ships its monospace font, so Qt and the pitch view look and measure
the same on every platform, Windows included (which has no DejaVu Sans Mono)."""
import unittest
from unittest.mock import patch

from goal2.tests import requires


class Bundled(unittest.TestCase):
    def test_both_faces_and_their_licence_ship_with_the_package(self):
        from goal2.desktop import style
        for path in style.FONT_FILES:
            self.assertTrue(path.is_file(), path)
        licence = style.FONT_FILES[0].with_name('LICENSE').read_text()
        self.assertIn('Bitstream Vera', licence)

    @requires.need(modules=('PySide6',))
    def test_qt_registers_the_bundled_family(self):
        from PySide6.QtGui import QFontDatabase
        from PySide6.QtWidgets import QApplication, QMainWindow
        from goal2.desktop.style import apply_style
        app = QApplication.instance() or QApplication([])
        window = QMainWindow();apply_style(window);self.addCleanup(window.deleteLater)
        from goal2.desktop.style import load_fonts
        ids = load_fonts()
        self.assertEqual(len(ids), 2);self.assertNotIn(-1, ids, 'a bundled face failed to load')
        self.assertEqual({f for i in ids for f in QFontDatabase.applicationFontFamilies(i)}, {'DejaVu Sans Mono'})
        app.processEvents()

    @requires.need(modules=('pygame',))
    def test_the_pitch_font_has_the_marks_without_a_system_font(self):
        import pygame
        from goal2.desktop import pygame_viewer as viewer
        pygame.init();self.addCleanup(pygame.quit);viewer._FONTS.clear()
        # As on Windows: no system DejaVu Sans Mono for pygame to find.
        with patch('pygame.font.match_font', return_value=None):
            for bold in (False, True):
                font = viewer.mono(20, bold);viewer._FONTS.clear()
                self.assertTrue(all(m is not None for m in font.metrics('☺☻◄►')), 'the marks need their glyphs')
                self.assertEqual(len({m[4] for m in font.metrics('iW☺')}), 1, 'monospaced: one advance width')


if __name__ == '__main__':
    unittest.main()
