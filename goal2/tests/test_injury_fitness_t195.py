"""F008/1771:42BC: fitness word/bar for zero energy, independently drawn by the original."""
import copy
import unittest
from goal2.tests import requires
from goal2.tests.reflow_pending import assert_fits

@requires.need(modules=('unicorn',),files=('e006-r0001-main.sav','GOAL.DAT'))
class InjuryFitness(unittest.TestCase):
    def test_matches_unhooked_original_energy_zero_and_healthy_cards(self):
        from goal2.engine.original_match.image import Image,PLAYER_SIZE
        from goal2.engine.original_match.machine import Machine
        from goal2.game.state import from_savestate
        from goal2.data.goaldat import load
        from goal2.game.player_card import card
        from goal2.tests.test_player_card import right_panel,painted
        raw=(requires.CACHE/'e006-r0001-main.sav').read_bytes()
        image=Image.from_savestate(raw);state=from_savestate(raw)
        names=load((requires.CACHE/'GOAL.DAT').read_bytes())
        word=int.from_bytes(image.countries()[7][:2],'little')
        for energy,fitness in ((0,25),(0,0),(0,32),(0,200),(1,25),(32,32)):
            with self.subTest(energy=energy,fitness=fitness):
                record=bytearray(image.players()[word]);record[13]=fitness;record[14]=energy
                machine=Machine(image.memory,image.load)
                machine.write(machine.far(0xA91B)+PLAYER_SIZE*word,bytes(record))
                end=machine.far_call('1771:42BC',[word],'1771:4D8A',ss=0x9000,sp=0x8000)
                self.assertFalse(machine._ports);self.assertFalse(machine._handlers)
                self.assertIsNone(machine.run(end,timeout_s=2,fresh=True))
                self.assertEqual(machine.reg('sp'),0x8006)
                screen=machine.read(machine.far(0xA96E),4000)
                rows=[screen[160*r:160*(r+1):2].decode('cp437') for r in range(25)]
                cells=[[(screen[2*(80*r+c)],screen[2*(80*r+c)+1]) for c in range(80)] for r in range(25)]
                expected_word=right_panel(rows,19,'fitness')
                expected_bar=painted(cells,19,47,60)
                state.players[word]=bytes(record);before=copy.deepcopy(state)
                value=next(row for row in card(state,word,names)['characteristics'] if row[0]=='fitness')
                self.assertEqual(value[1:3],(expected_word,expected_bar))
                self.assertEqual(value[3],fitness,'raw fitness byte remains available')
                self.assertEqual(state,before,'display reads never mutate the career')
                if energy==0:
                    self.assertEqual(expected_word,'injured')
                    self.assertEqual(expected_bar,0)


@requires.need(modules=('PySide6','pygame'),**requires.HALFTIME)
class InjuryFitnessScreen(unittest.TestCase):
    def test_stopped_card_shows_injury_word_and_empty_fitness_bar_without_state_write(self):
        from goal2.tests.test_immediate_bench_t188 import ImmediateBench
        from goal2.desktop import fixed_page
        ImmediateBench.setUp(self)
        word=self.off
        record=bytearray(self.model.state.players[word]);record[13]=25;record[14]=0
        self.model.state.players[word]=bytes(record)
        self.bench.row=self.bench.answer.words().index(word)
        before=copy.deepcopy(self.model.state)
        for width,height in ((1440,900),(1800,1125),(2110,1213)):
            self.window.resize(width,height);self.bench.refresh()
            for _ in range(3):self.app.processEvents()
            bar,word_label=self.bench.card.characteristics.rows['fitness']
            self.assertEqual(word_label.text(),'injured')
            self.assertEqual(bar.value,(0,14))
            self.assertTrue(bar.filled.isHidden())
            self.assertIn('INJURED',self.bench.card.readiness.text())
            assert_fits(self, self.window)
        self.assertEqual(self.model.state,before)

if __name__=='__main__':unittest.main()
