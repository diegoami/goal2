"""Original1981 retains the full157D TEAM panel during tactics editing (#646)."""
import copy
from PySide6.QtWidgets import QLabel
from goal2.tests import requires
from goal2.tests import test_tactics_characteristics_t202 as existing
from goal2.tests.test_ui_start_t163 import App
from goal2.tests.test_core_team_panels_t144 import FIXTURES


@requires.need(files=tuple(v[0] for v in FIXTURES.values())+('GOAL.DAT','e010-r0008-halftime.sav'), modules=('PySide6',))
class TeamTacticsLayout(App):
    def model(self, name='selection'):
        return existing.TacticsCharacteristics.model(self, name)

    def open(self, model):
        return existing.TacticsCharacteristics.open(self, model)

    def test_full_original_team_fields_and_xi_panels_remain_visible_while_editing(self):
        from goal2.game.country_card import card
        for fixture in FIXTURES:
            model=self.model(fixture);before=copy.deepcopy(model.state)
            window,screen=self.open(model)
            expected=card(model.state,model.state.managed_country,model.goaldat)
            self.assertTrue(hasattr(screen,'team_header'),'S10 omits original TEAM header')
            header=screen.team_header
            self.assertEqual(header.name.text(),expected['name'])
            for field in ('status','manager'):
                self.assertEqual(header.team[field].text(),expected[field] or '')
            for field in ('world','continental','top_world','top_continental'):
                self.assertEqual(header.ranks[field].text(),str(expected[field]))
            self.assertEqual(header.shape['skill'].text(),expected['skill'] or '')
            self.assertEqual(header.strip_view.attributes,expected['strips'])
            self.assertEqual(screen.skills.panel,expected['team_skills'])
            self.assertTrue(screen.performance.isHidden(),'career context is not a live performance observation')
            self.assertEqual({key:value.text() for key,value in screen.averages.values.items()},
                             {n['field']:n['text'] for n in expected['characteristics']['numbers']})
            self.assertEqual(model.state,before)
            window.leave();self.app.processEvents()

    def test_team_tactics_and_player_defaults_have_separate_visible_groups_in_original_order(self):
        model=self.model();window,screen=self.open(model)
        headings=[widget.text().upper() for widget in screen.findChildren(QLabel) if not widget.isHidden()]
        self.assertIn('TEAM TACTICS',headings)
        self.assertIn('PLAYER DEFAULTS',headings)
        self.assertEqual([row[0] for row in screen.lines()],
            ['defence system','protection','offside','positioning','possession','passing','tackling','marking'])
        self.assertLess(screen.rows[2].mapTo(screen,screen.rows[2].rect().bottomLeft()).y(),
                        screen.defaults_heading.mapTo(screen,screen.defaults_heading.rect().topLeft()).y())
        self.assertLess(screen.defaults_heading.mapTo(screen,screen.defaults_heading.rect().bottomLeft()).y(),
                        screen.rows[3].mapTo(screen,screen.rows[3].rect().topLeft()).y())
        window.leave()
