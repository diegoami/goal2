"""[designed: owner #436] Caps are visible pool data and remain attached to full player IDs."""
import unittest
from goal2.tests import requires


@requires.need(modules=('unicorn', 'PySide6'), files=('e006-r0001-main.sav', 'GOAL.DAT'))
class PoolCaps(unittest.TestCase):
    def test_existing_pool_rows_show_the_actual_original_caps_word_without_changing_state(self):
        from PySide6.QtWidgets import QApplication
        from goal2.tests.test_core_team_t107 import model
        from goal2.desktop.core_window import CoreWindow
        app = QApplication.instance() or QApplication([])
        m = model();w = CoreWindow(m)
        try:
            before = m.core.save()
            expected = {r[0]:m.card(r[0])['caps'] for r in w.pool_strip.rows}
            self.assertEqual(w.pool_strip.caps, expected)
            for row in w.pool_strip.rows:
                self.assertEqual(w.pool_strip.detail_text(row), str(expected[row[0]]))
                self.assertIn(f"CAPS {expected[row[0]]}", w.pool_strip.accessibleName())
            self.assertEqual(m.core.save(), before)
        finally:
            w.close();app.processEvents()

    def test_caps_keep_zero_and_large_words_and_fit_beside_full_names(self):
        from PySide6.QtWidgets import QApplication
        from PySide6.QtGui import QFont, QFontMetrics
        from goal2.desktop.core_pool_roster import PoolRoster
        from goal2.desktop.style import load_fonts
        app = QApplication.instance() or QApplication([])
        load_fonts()
        roster = PoolRoster();roster.resize(314, 640)
        rows = [(2561,'A ABCDEFGHIJ','m','midfield',False,False),
                (2562,'B KLMNOPQRST','M','midfield',False,False)]
        roster.caps = {2561:0,2562:65535};roster.set_rows(rows,0)
        self.assertEqual([roster.detail_text(r) for r in rows], ['0','65535'])
        font = QFont('DejaVu Sans Mono');font.setPixelSize(20);font.setBold(True)
        metrics = QFontMetrics(font)
        count_font = QFont(font);count_font.setPixelSize(16);count_metrics = QFontMetrics(count_font)
        # Independent geometric requirement: full12-character name, five digits and role all fit.
        self.assertLessEqual(40 + max(metrics.horizontalAdvance(r[1]) for r in rows) + 4
                             + count_metrics.horizontalAdvance('65535') + 12, 314 - 64)
        self.assertIn('CAPS 0', roster.accessibleName())
        self.assertIn('CAPS 65535', roster.accessibleName())
        roster.show();app.processEvents()
        before = roster.grab().toImage()
        roster.caps[2562] = 0;roster.set_rows(rows,0);app.processEvents()
        after = roster.grab().toImage()
        self.assertNotEqual(before, after, 'The caps change must reach the actual painted roster')
        roster.close()

    def test_caps_reader_keeps_the_high_byte_of_the_original_word(self):
        from types import SimpleNamespace
        from goal2.desktop.core_pool_roster import caps_for
        # [confirmed: F002 player20-byte record +8/+9] Host-only boundary control, no guest mutation.
        raw = bytearray(40);raw[28:30] = bytes((1,2))
        state = SimpleNamespace(_image=SimpleNamespace(memory=raw,DS=0,load=0,far=lambda ptr:0))
        self.assertEqual(caps_for(state,[1]), {1:513})
