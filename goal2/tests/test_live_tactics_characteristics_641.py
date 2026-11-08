"""#641 current stopped-squad TEAM traits; independent Core projection, no new formulas."""
import copy
from types import SimpleNamespace
import unittest
from unittest import mock
from goal2.tests import requires
from goal2.tests import test_tactics_characteristics_t202 as existing
from goal2.tests.test_ui_start_t163 import App
from goal2.tests.test_core_team_panels_t144 import FIXTURES


def shown_traits(screen):
    panel=screen.characteristics
    return panel.text() if hasattr(panel,'text') else ' · '.join(value.text() for value in panel.values.values())


def expected_panel(model,data):
    """T202's original-backed memory projection, built without UI live_cards."""
    from goal2.engine.original_match.image import Image
    from goal2.core.views import Memory
    original=Memory(Image.from_memory_component(model.state.mem))
    words=list(data['eleven'])+list(data['bench'])
    address=original.far(0xA917)+191*model.state.managed_country
    original.mem[address:address+40]=b''.join(word.to_bytes(2,'little') for word in words)
    original.mem[address+0x2D]=data['tactics']
    for word,raw in data['player_records']:
        address=original.far(0xA91B)+20*word
        original.mem[address:address+20]=bytes.fromhex(raw)
    return original.country_panels(model.state.managed_country)['characteristics']


@requires.need(files=tuple(v[0] for v in FIXTURES.values())+('GOAL.DAT','e010-r0008-halftime.sav'),modules=('PySide6',))
class LiveTacticsCharacteristics(App):
    def model(self,name='friendly'):
        return existing.TacticsCharacteristics.model(self,name)

    def decision(self,model,*,swapped=False,injured=False,tactics=None):
        words=list(model.state.managed_squad)
        if swapped:words[1],words[15]=words[15],words[1]
        pairs=[]
        for index,word in enumerate(words):
            record=bytearray(model.state.players[word])
            # Declared authored current-record fixture, not natural play.
            record[12]=3+index%3;record[13]=7;record[14]=0 if injured and index==3 else 5
            record[1]=31;record[8:10]=(50+index).to_bytes(2,'little')
            pairs.append([word,bytes(record).hex()])
        data=dict(context='half_time',eleven=words[:11],bench=words[11:],positions=[[w,bytes.fromhex(raw)[6]] for w,raw in pairs],
            player_records=pairs,tactics=model.state.country_tactics if tactics is None else tactics,
            substitutions_now=True,substitutions_left=5)
        return SimpleNamespace(data=data,minute=45,score=[0,0])

    def screen(self,model,decision):
        from goal2.ui.s19_bench import BenchAnswer
        from goal2.ui.s10_team_tactics import TeamTacticsScreen
        answer=BenchAnswer(model,decision)
        window=self.window();window.open_career(model)
        screen=TeamTacticsScreen(window,model,answer=answer,apply=lambda *args:None)
        window.push(screen);self.app.processEvents()
        return window,screen

    def test_complete_current_twenty_and_accepted_xi_match_original_projection_without_state_write(self):
        from goal2.desktop.country_card import characteristic_view
        for swapped,injured in ((False,False),(True,False),(True,True)):
            model=self.model();decision=self.decision(model,swapped=swapped,injured=injured)
            before=copy.deepcopy(model.state);packet=copy.deepcopy(decision.data)
            window,screen=self.screen(model,decision)
            expected=expected_panel(model,decision.data)
            self.assertNotIn('not decoded',shown_traits(screen))
            self.assertEqual(screen.characteristics.panel,expected)
            self.assertEqual(screen.characteristics.cells.grid,characteristic_view(expected['descriptors']))
            self.assertEqual(model.state,before);self.assertEqual(decision.data,packet)
            window.leave();self.app.processEvents()

    def test_acknowledgement_refresh_replaces_records_order_flags_without_new_widgets_or_stale_panel(self):
        from PySide6.QtWidgets import QWidget
        from goal2.ui.s19_bench import BenchAnswer
        model=self.model();first=self.decision(model)
        window,screen=self.screen(model,first);identities={id(w) for w in screen.findChildren(QWidget)}
        self.assertNotIn('not decoded',shown_traits(screen))
        first_expected=expected_panel(model,first.data)
        second=self.decision(model,swapped=True,injured=True,tactics=first.data['tactics']^16)
        answer=BenchAnswer(model,second);before=copy.deepcopy(model.state)
        screen.pending=True;screen._requested=(5,bool(answer.team_tactics&16),'defence','before','after')
        screen.applied(answer,None);self.app.processEvents()
        self.assertEqual(screen.characteristics.panel,expected_panel(model,second.data))
        self.assertNotEqual(first_expected,screen.characteristics.panel)
        self.assertEqual({id(w) for w in screen.findChildren(QWidget)},identities)
        self.assertFalse(screen.pending);self.assertIs(screen.answer,answer);self.assertEqual(model.state,before)
        window.leave()

    def test_pending_position_formation_semantics_remain_separate_from_accepted_trait_inputs(self):
        model=self.model();decision=self.decision(model,swapped=True)
        window,screen=self.screen(model,decision);expected=expected_panel(model,decision.data)
        answer=screen.answer;word=answer.eleven[3];answer.positions[word]=(answer.position(word)+1)%14
        before=copy.deepcopy(model.state);draft=dict(answer.positions)
        screen.refresh()
        self.assertNotIn('not decoded',shown_traits(screen))
        self.assertEqual(screen.characteristics.panel,expected)
        self.assertEqual(answer.positions,draft);self.assertEqual(model.state,before)
        self.assertEqual(answer.position(word),draft[word])
        window.leave()

    def test_trait_refresh_and_cursor_navigation_never_decode_full_player_cards(self):
        model=self.model();decision=self.decision(model)
        with mock.patch('goal2.game.player_card.card',side_effect=AssertionError('full card decode is outside trait projection')):
            window,screen=self.screen(model,decision)
            self.assertNotIn('not decoded',shown_traits(screen))
            with mock.patch.object(screen,'refresh',side_effect=AssertionError('cursor must stay presentation-only')):
                for line in range(8):screen.choose(line)
            screen.refresh()
        window.leave()

if __name__=='__main__':unittest.main()
