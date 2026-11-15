"""[fix #682] The taker screen's roster heading is whole at the taker view's width.

`docs/current-game/images/boot-round-taker.png`: the corner-taker screen's roster heading read
"FIRST ELEVEN 11 / XI 11 / BE", clipped mid-word — the taker roster is fixed at 300 page
pixels while the counted heading was neither elided nor shortened. The roster holds the first
eleven only (11 rows, XI 11, bench 0), so the counts are constants; the caption (T95's
fixed-caption path) holds the whole heading. The page is composed once at 1440x900 and scaled
(fixed_page), so the fit is asserted in real windows at both sizes the manual ships at.
"""
import unittest
from types import SimpleNamespace

from goal2.tests import requires

SIZES = ((1440, 900), (900, 640))
MARGIN, RIGHT = 14, 4          # roster.py's paint: drawText(14, 30, ...) inside the border


def heading_font():
    from PySide6.QtGui import QFont
    font = QFont('DejaVu Sans Mono')
    font.setStyleHint(QFont.StyleHint.Monospace)
    font.setPixelSize(17)
    font.setBold(True)
    return font


def taker_pages(window, views):
    from goal2.desktop.core_takers import TakerPages
    pages = TakerPages(SimpleNamespace(window=window, views=views))
    pages.roster.set_rows([(i + 1, f'PLAYER {i + 1}', 'GK' if i == 0 else 'DF',
                            'goalkeeper' if i == 0 else 'defence', True, i == 0) for i in range(11)])
    return pages


@requires.need(modules=("PySide6",))
class TakerRosterHeading(unittest.TestCase):
    def test_the_taker_roster_builds_the_whole_heading(self):
        from PySide6.QtWidgets import QApplication, QStackedWidget
        QApplication.instance() or QApplication([])
        pages = taker_pages(None, QStackedWidget())
        self.assertEqual(pages.roster.caption, 'FIRST ELEVEN')    # the counts are constants (11 / XI 11 / BENCH 0)
        self.assertEqual(pages.roster.heading(), 'FIRST ELEVEN')  # the source text the paint draws

    def test_the_heading_fits_the_taker_width_at_both_window_sizes(self):
        from PySide6.QtGui import QFontMetrics
        from PySide6.QtWidgets import QApplication, QMainWindow, QStackedWidget
        QApplication.instance() or QApplication([])
        metrics = QFontMetrics(heading_font())
        for width, height in SIZES:
            with self.subTest(window=(width, height)):
                window = QMainWindow(); window.resize(width, height)
                views = QStackedWidget(); window.setCentralWidget(views)
                pages = taker_pages(window, views)
                scale = min(width / 1440, height / 900)          # fixed_page's own arithmetic
                window.setProperty('pageScale', scale)
                pages.roster.setFixedWidth(round(300 * scale))   # fixed_page.apply's rule: explicit sizes scale
                page_width = pages.roster.width() / pages.roster.scale()
                self.assertAlmostEqual(page_width, 300, delta=1)  # the taker view's fixed page width
                self.assertLessEqual(metrics.horizontalAdvance(pages.roster.heading()),
                                     page_width - MARGIN - RIGHT)
                self.assertGreater(metrics.horizontalAdvance('FIRST ELEVEN 11 / XI 11 / BENCH 0'),
                                   page_width - MARGIN - RIGHT)   # the counted heading did clip


if __name__ == '__main__':
    unittest.main()
