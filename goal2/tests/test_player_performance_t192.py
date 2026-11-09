"""Original1771:3827 star thresholds; UI records are declared display fixtures, not live match proof."""
import copy
import unittest
from goal2.tests import requires
from goal2.tests.reflow_pending import assert_fits

# [confirmed: original1771:3827, accepted port performance_text_state at80831d9a]
# Literal boundary oracles are independent of the implementation helper.
CASES = ((0x7FFF, 0), (0, 1), (4, 1), (5, 2), (54, 2), (55, 3), (104, 3), (105, 4),
         (154, 4), (155, 5), (204, 5), (205, 6), (254, 6), (255, 7), (354, 7),
         (355, 8), (454, 8), (455, 9), (5000, 9), (5001, 1), (10000, 1), (10004, 1),
         (10005, 2), (10054, 2), (10055, 3), (10105, 4), (10205, 6), (10355, 8),
         (10455, 9), (0xFFFF, 1), (0x8000, 9), (0x8036, 9), (0x8037, 1), (0x7FFE, 9))

class PerformanceWord(unittest.TestCase):
    def test_original_thresholds_substitute_encoding_signed_words_and_blank(self):
        from goal2.game.player_card import performance_stars
        for word, expected in CASES:
            with self.subTest(word=word): self.assertEqual(performance_stars(word), expected)

    def test_rejects_non_word_inputs_instead_of_inventing_a_rating(self):
        from goal2.game.player_card import performance_stars
        for word in (-1, 65536, True, None, '55'):
            with self.subTest(word=word), self.assertRaises(ValueError): performance_stars(word)

@requires.need(modules=('PySide6',), **requires.HALFTIME)
class CardData(unittest.TestCase):
    def test_real_card_exposes_stars_without_changing_raw_rating_or_career(self):
        from goal2.tests.test_ui_squad_t165 import career
        from goal2.game.player_card import card
        model = career()
        word = model.state.managed_squad[0]
        for raw, expected in CASES:
            record = bytearray(model.state.players[word])
            record[18:20] = raw.to_bytes(2, 'little')
            model.state.players[word] = bytes(record)
            before = copy.deepcopy(model.state)
            value = card(model.state, word, model.goaldat)
            self.assertEqual(value.get('performance_bar'), expected, raw)
            self.assertEqual(value['performance'], None if raw==0x7FFF else raw)
            self.assertEqual(model.state, before)

@requires.need(modules=('PySide6',), **requires.HALFTIME)
class PerformanceScreen(unittest.TestCase):
    def test_blank_and_rated_players_render_original_stars_at_readable_sizes(self):
        from PySide6.QtWidgets import QApplication
        from goal2.desktop import fixed_page
        from goal2.tests.test_ui_squad_t165 import career
        from goal2.ui.window import Window
        from goal2.ui.s08_squad import open_squad
        from goal2.desktop import data_setup
        from goal2.ui import theme
        from pathlib import Path
        import tempfile
        app = QApplication.instance() or QApplication([])
        theme.install(app)
        model = career()
        with tempfile.TemporaryDirectory() as folder:
            window = Window(data_setup.paths(Path(folder)))
            window.open_career(model)
            window.show()
            screen = open_squad(window, model)
            try:
                word = screen.current()
                for raw, expected in ((0x7FFF, ''), (205, '******'), (10055, '***')):
                    record = bytearray(model.state.players[word])
                    record[18:20] = raw.to_bytes(2, 'little')
                    model.state.players[word] = bytes(record)
                    for width, height in ((1440, 900), (1800, 1125), (2110, 1213)):
                        window.resize(width, height)
                        screen.refresh()
                        app.processEvents()
                        facts = screen.card.facts.text()
                        self.assertIn('performance', facts)
                        self.assertEqual(facts.count('*'), len(expected), (raw, facts))
                        self.assertNotIn('not recorded', facts)
                        self.assertNotIn('not decoded', facts)
                        self.assertNotIn('raw ', facts)
                        assert_fits(self, window, (raw, width, height))
                        self.assertFalse(screen.card.facts.grab().isNull())
            finally:
                window.leave(); window.deleteLater(); app.processEvents()

@requires.need(modules=('unicorn',), files=('e006-r0001-main.sav',))
class OriginalFunction(unittest.TestCase):
    def test_exact_original_guest_routine_agrees_on_all_boundary_words(self):
        # [designed: T192] Explicit synthetic routine-entry fixture, not a natural match.
        # Original code and callees execute under Unicorn with no port/body hooks.
        from goal2.engine.original_match.image import Image, PLAYER_SIZE
        from goal2.engine.original_match.machine import Machine
        from goal2.game.player_card import performance_stars
        image = Image.from_savestate((requires.CACHE/'e006-r0001-main.sav').read_bytes())
        for value, expected in CASES:
            with self.subTest(word=value):
                machine = Machine(image.memory, image.load)
                player = 1
                machine.write(machine.far(0xA91B)+PLAYER_SIZE*player+18, value.to_bytes(2,'little'))
                machine.wr(0x0E86,99,1)  # sentinel must leave the existing string length alone
                ss, sp = 0x9000, 0x8000
                # Near Pascal call: returnIP, column, row, player; routine returns with ret6.
                for index, word in enumerate((0x3947,60,8,player)):
                    machine.write(ss*16+sp+2*index,word.to_bytes(2,'little'))
                for name, word in (('ss',ss),('sp',sp),('bp',0x1234),('ds',machine.DS),
                                   ('es',machine.DS),('cs',machine.seg(0x1771)),('eip',0x3827),('eflags',0x202)):
                    machine.set_reg(name,word)
                self.assertFalse(machine._ports)
                self.assertFalse(machine._handlers)
                self.assertIsNone(machine.run(machine.lin('1771:3947'),timeout_s=2,fresh=True))
                self.assertEqual(machine.reg('sp'),sp+8)
                actual = machine.rd(0x0E86,1)
                self.assertEqual(actual,99 if value==0x7FFF else expected)
                self.assertEqual(performance_stars(value),0 if value==0x7FFF else actual)

if __name__ == '__main__': unittest.main()
