"""T200: stored top ranks and raw strip overlay against the actual original157D header."""
import copy
import unittest
from goal2.tests import requires

@requires.need(files=('e006-r0001-main.sav','GOAL.DAT'),modules=('unicorn',))
class Header(unittest.TestCase):
    def load(self):
        from goal2.engine.original_match.image import Image
        from goal2.game.state import from_savestate
        from goal2.data.goaldat import load
        raw=(requires.CACHE/'e006-r0001-main.sav').read_bytes()
        return Image.from_savestate(raw),from_savestate(raw),load((requires.CACHE/'GOAL.DAT').read_bytes())

    def test_matches_unhooked_original_top_text_and_strip_glyph_attributes(self):
        from goal2.engine.original_match.machine import Machine
        from goal2.game.country_card import card
        from goal2.game.state import MEM_BASE
        # Synthetic rows alter only explicitly declared display inputs, not played games.
        cases=((7,None,None,None),(20,None,None,None),(128,None,None,None),
               (7,(0,255),0,(0,15,242)),(7,(255,0),0,(255,31,128)),
               (7,(4,9),1,(1,2,3)),(7,(4,9),2,(4,5,6)))
        for country,top,mono,attributes in cases:
            with self.subTest(country=country,top=top,mono=mono,attributes=attributes):
                image,state,names=self.load();m=Machine(image.memory,image.load)
                memory=bytearray(state.mem)
                if top is not None:
                    world,continental=top;record=bytearray(state.countries[country]);record[0x29]=world;record[0x28]=continental
                    state.countries[country]=bytes(record)
                    m.write(m.far(0xA917)+191*country+0x28,bytes((continental,world)))
                if mono is not None:
                    m.wr(0xA964,mono,1);memory[MEM_BASE+m.DS*16+0xA964]=mono
                if attributes is not None:
                    offset=0x9D80+3*country;m.write(m.DS*16+offset,bytes(attributes))
                    memory[MEM_BASE+m.DS*16+offset:MEM_BASE+m.DS*16+offset+3]=bytes(attributes)
                state.mem=bytes(memory);before=copy.deepcopy(state)
                end=m.far_call('1771:157D',[],'1771:1934',ss=0x9000,sp=0x8000)
                #157D is nearRET2: its country argument immediately follows the near returnIP.
                m.write(0x98002,country.to_bytes(2,'little'))
                self.assertFalse(m._ports);self.assertFalse(m._handlers)
                self.assertIsNone(m.run(end,timeout_s=2,fresh=True));self.assertEqual(m.reg('sp'),0x8004)
                page=m.read(m.far(0xA96E),4000)
                printed=[page[(row*80+12)*2:(row*80+16)*2:2].decode('cp437').strip() for row in (11,12)]
                shown=card(state,country,names)
                self.assertEqual([str(shown['top_world']),str(shown['top_continental'])],printed)
                columns=[m.rd(0xD89+i,1) for i in (1,2,3)]
                cells=[(page[(12*80+c-1)*2],page[(12*80+c-1)*2+1]) for c in columns]
                if m.rd(0xA964,1):
                    self.assertIsNone(shown['strips'],'no colour overlay; original template keeps its grey glyphs')
                    self.assertEqual(cells,[(2,7)]*3)
                else:self.assertEqual(cells,[(2,attribute) for attribute in shown['strips']])
                self.assertEqual(state,before,'header reads never mutate the career')

    def test_all128_use_current_record_top_bytes_and_current_raw_table_without_mutation(self):
        from goal2.game.country_card import card
        image,state,names=self.load();before=copy.deepcopy(state)
        for country in range(1,129):
            with self.subTest(country=country):
                shown=card(state,country,names)
                self.assertEqual((shown['top_world'],shown['top_continental']),(state.countries[country][0x29],state.countries[country][0x28]))
                self.assertEqual(shown['strips'],tuple(image.memory[image.DS*16+0x9D80+3*country:image.DS*16+0x9D80+3*country+3]))
                self.assertEqual(shown['not_decoded'],())
        self.assertEqual(state,before)

if __name__=='__main__':unittest.main()
