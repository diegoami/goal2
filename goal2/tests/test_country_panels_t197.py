"""T197: current GameState adapter against accepted original-backed TEAM panel oracles."""
import copy
import unittest
from goal2.tests import requires
from goal2.tests.test_core_team_panels_t144 import FIXTURES
FIELDS=('status','skill','team_skills','performance','characteristics')

@requires.need(files=tuple(v[0] for v in FIXTURES.values())+('GOAL.DAT',))
class TeamPanels(unittest.TestCase):
    def load(self,name):
        from goal2.game.state import from_savestate
        from goal2.engine.original_match.image import Image
        from goal2.core.views import Memory
        from goal2.data.goaldat import load
        raw=(requires.CACHE/FIXTURES[name][0]).read_bytes()
        return from_savestate(raw),Memory(Image.from_savestate(raw)),load((requires.CACHE/'GOAL.DAT').read_bytes())

    def test_genuine_panels_match_delivered_original_backed_projection_for_all_countries(self):
        from goal2.game.country_card import card
        for fixture in FIXTURES:
            state,original,names=self.load(fixture);before=copy.deepcopy(state)
            for country in range(1,129):
                with self.subTest(fixture=fixture,country=country):
                    expected={**original.country_labels(country),**original.country_panels(country)}
                    shown=card(state,country,names)
                    self.assertEqual({f:shown[f] for f in FIELDS},expected)
                    self.assertEqual(shown['not_decoded'],())  # T200 delivers the final header fields on this route
            self.assertEqual(state,before)

    def test_managed_current_twenty_tactics_and_player_records_override_stale_raw_copies(self):
        from goal2.game.country_card import card
        state,original,names=self.load('selection');country=state.managed_country
        state.managed_squad[1],state.managed_squad[15]=state.managed_squad[15],state.managed_squad[1]
        state.country_tactics^=0x31
        word=state.managed_squad[2];record=bytearray(state.players[word]);record[14]=0;state.players[word]=bytes(record)
        # Mirror only the declared current inputs into an independent original-memory projection.
        address=original.far(0xA917)+191*country
        original.mem[address:address+40]=b''.join(w.to_bytes(2,'little') for w in state.managed_squad)
        original.mem[address+0x2D]=state.country_tactics
        player=original.far(0xA91B)+20*word;original.mem[player:player+20]=record
        before=copy.deepcopy(state);shown=card(state,country,names)
        self.assertEqual(shown['players'],state.managed_squad)
        self.assertEqual({f:shown[f] for f in FIELDS},{**original.country_labels(country),**original.country_panels(country)})
        self.assertEqual(state,before)

    def test_performance_visibility_retains_both_original_gates_and_actual_selected_side(self):
        from goal2.game.country_card import card
        from goal2.game.state import MEM_BASE
        for setup,menu in ((0,0),(0,1),(1,0),(1,1)):
            state,original,names=self.load('friendly');raw=bytearray(state.mem)
            for off,value in ((0xC1E,setup),(0xC1F,menu)):
                raw[MEM_BASE+original.ds*16+off]=value;original.mem[original.ds*16+off]=value
            state.mem=bytes(raw);before=copy.deepcopy(state)
            for country in (7,16,29):
                shown=card(state,country,names)['performance']
                self.assertEqual(shown,original.country_panels(country)['performance'])
                self.assertEqual(shown is not None,bool(setup and menu))
            self.assertEqual(state,before)

    def test_bounded_adapter_rejects_wrong_width_indices_and_memory_ranges(self):
        from goal2.game.team_card import TeamMemory
        state,_,_=self.load('selection');reader=TeamMemory(state)
        for method,limit,width in ((reader.country_record,128,191),(reader.player_record,3060,20),(reader.manager_record,134,3)):
            self.assertEqual(len(method(0)),width);self.assertEqual(len(method(limit)),width)
            for bad in (-1,limit+1,True,'1'):
                with self.subTest(reader=method.__name__,bad=bad),self.assertRaises(ValueError):method(bad)
        for args in ((-1,1),(65535,2),(0,0),(True,1)):
            with self.assertRaises(ValueError):reader.read_ds(*args)
        for args in ((-1,0,1),(0,65535,2),(True,0,1),(0,0,0)):
            with self.assertRaises(ValueError):reader.read_code(*args)
        state.players[1]=b'bad'
        with self.assertRaises(ValueError):reader.player_record(1)
        state.managed_squad.pop()
        with self.assertRaises(ValueError):reader.country_record(state.managed_country)

if __name__=='__main__':unittest.main()
