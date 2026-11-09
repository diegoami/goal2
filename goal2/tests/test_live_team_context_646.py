"""#646 strict display-context boundary and original-backed live TEAM projection."""
import copy
from types import SimpleNamespace
import unittest
from goal2.tests import requires
from goal2.tests.reflow_pending import assert_fits
from goal2.tests import test_live_tactics_characteristics_641 as current
from goal2.tests.test_ui_start_t163 import App
from goal2.tests.test_core_team_panels_t144 import FIXTURES


class ContextSchema(unittest.TestCase):
    def packet(self):
        return dict(eleven=[7],bench=[],player_records=[[7,'00'*20]],
                    team_context=dict(match_set_up=1,in_match_menu_used=255,sides=[7,19]))

    def test_invalid_context_fails_before_snapshot_consumption(self):
        from goal2.ui.live_cards import player_snapshot
        for invalid in (None,[],{},dict(match_set_up=True,in_match_menu_used=1,sides=[7,19]),
                dict(match_set_up=256,in_match_menu_used=1,sides=[7,19]),
                dict(match_set_up=1,in_match_menu_used=-1,sides=[7,19]),
                dict(match_set_up=1,in_match_menu_used=1,sides=[7,7]),
                dict(match_set_up=1,in_match_menu_used=1,sides=[0,19]),
                dict(match_set_up=1,in_match_menu_used=1,sides=[7,129]),
                dict(match_set_up=1,in_match_menu_used=1,sides=[7,19],extra=0)):
            packet=self.packet();packet['team_context']=invalid;before=copy.deepcopy(packet)
            with self.subTest(invalid=invalid),self.assertRaises(ValueError):player_snapshot(packet)
            self.assertEqual(packet,before)


@requires.need(files=tuple(v[0] for v in FIXTURES.values())+('GOAL.DAT','e010-r0008-halftime.sav'),modules=('PySide6',))
class LiveTeamContext(App):
    def model(self):
        return current.LiveTacticsCharacteristics.model(self)

    def decision(self, model):
        return current.LiveTacticsCharacteristics.decision(self,model,swapped=True,injured=True)

    def screen(self, model, decision):
        return current.LiveTacticsCharacteristics.screen(self,model,decision)

    def expected(self,model,data):
        from goal2.core.views import Memory
        from goal2.engine.original_match.image import Image
        memory=Memory(Image.from_memory_component(model.state.mem))
        address=memory.far(0xA917)+191*model.state.managed_country
        words=data['eleven']+data['bench']
        memory.mem[address:address+40]=b''.join(w.to_bytes(2,'little') for w in words)
        memory.mem[address+0x2D]=data['tactics']
        for word,raw in data['player_records']:
            address=memory.far(0xA91B)+20*word
            memory.mem[address:address+20]=bytes.fromhex(raw)
        context=data['team_context']
        for offset,value in ((0xC1E,context['match_set_up']),(0xC1F,context['in_match_menu_used'])):
            memory.mem[memory.ds*16+offset]=value
        for offset,value in zip((0x9B34,0x9B36),context['sides']):
            address=memory.ds*16+offset;memory.mem[address:address+2]=value.to_bytes(2,'little')
        return memory.country_panels(model.state.managed_country)

    def test_current_skills_performance_and_xi_numbers_equal_independent_original_for_all_gates_and_sides(self):
        model=self.model();decision=self.decision(model)
        country=model.state.managed_country;other=19 if country!=19 else 7
        for flags in ((0,0),(1,0),(0,255),(1,255)):
            for sides in ([country,other],[other,country]):
                data=copy.deepcopy(decision.data)
                data['team_context']=dict(match_set_up=flags[0],in_match_menu_used=flags[1],sides=sides)
                before=copy.deepcopy(model.state);packet=copy.deepcopy(data)
                window,screen=self.screen(model,SimpleNamespace(data=data,minute=45,score=[0,0]))
                expected=self.expected(model,data)
                self.assertTrue(hasattr(screen,'skills'),'S10 omits current original skills')
                self.assertEqual(screen.skills.panel,expected['team_skills'])
                self.assertEqual(screen.performance.panel,expected['performance'])
                self.assertEqual(screen.performance.isHidden(),not bool(flags[0] and flags[1]))
                self.assertEqual(screen.characteristics.panel,expected['characteristics'])
                self.assertEqual({key:value.text() for key,value in screen.averages.values.items()},
                    {row['field']:row['text'] for row in expected['characteristics']['numbers']})
                if flags==(1,255) and sides[0]==country:
                    from goal2.desktop import fixed_page
                    for width,height in ((1440,900),(1800,1125),(2110,1213)):
                        window.resize(width,height);self.app.processEvents();window.grab()
                        assert_fits(self, window, (width,height))
                        self.assertEqual(len(screen.strip.shown_texts()),20)
                        for widget in (*screen.team_header.team.values(),*screen.team_header.ranks.values(),
                                       *screen.team_header.shape.values(),*screen.skills.labels.values(),
                                       *screen.performance.labels.values(),*screen.averages.values.values()):
                            self.assertGreaterEqual(widget.font().pixelSize(),round(24*window.frame.scale))
                        self.assertFalse(screen.performance.isHidden())
                self.assertEqual(data,packet);self.assertEqual(model.state,before)
                self.assertTrue(screen.injury_hint.isVisible())
                injured=screen.answer.injured
                for row,word in zip(screen.strip.rows,screen.answer.words()):
                    self.assertEqual(bool(row.property('injured')),word in injured)
                    self.assertEqual(row.texts()[1].endswith(' *'),word in injured)
                window.leave();self.app.processEvents()
