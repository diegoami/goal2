"""#653 current human identity belongs to the selected managed TEAM header."""
import copy
from goal2.tests import requires
from goal2.tests.test_ui_start_t163 import App


@requires.need(modules=('PySide6',),**requires.HALFTIME)
class TeamManager(App):
    def model(self,name='K Ees'):
        from goal2.desktop.model import DesktopModel
        model=DesktopModel.open(requires.CACHE/'e010-r0008-halftime.sav',requires.CACHE/'GOAL.DAT',self.tmp/'private.g2save',country=2)
        model.new_campaign(2,2028)
        if name is not None:model.rename_manager(name)
        self.assertEqual(model.state.countries[2][0x2E],129)
        return model

    def test_named_human_manager_is_current_and_other_country_never_inherits_it(self):
        from goal2.game.country_card import card
        model=self.model();before=copy.deepcopy(model.state)
        self.assertEqual(card(model.state,2,model.goaldat)['manager'],'K Ees')
        other_before=card(model.state,7,model.goaldat)
        model.rename_manager('New manager')
        self.assertEqual(card(model.state,2,model.goaldat)['manager'],'New manager')
        self.assertEqual(card(model.state,7,model.goaldat),other_before)
        self.assertEqual(before.manager_name,'K Ees')
        self.assertEqual(model.state.countries,before.countries)

    def test_computer_manager_selection_uses_its_record_index_instead_of_country(self):
        from goal2.game.country_card import card
        for country in (7,2):
            model=self.model();record=bytearray(model.state.countries[country])
            record[0x2E]=3;model.state.countries[country]=bytes(record)  # authored transfer boundary
            before=copy.deepcopy(model.state)
            expected=model.goaldat.manager_initials[3]+' '+model.goaldat.manager_names[3]
            self.assertEqual(card(model.state,country,model.goaldat)['manager'],expected)
            self.assertEqual(model.state,before)

    def test_unnamed_preview_keeps_existing_country_default_without_writing_identity(self):
        from goal2.game.country_card import card
        model=self.model(None);before=copy.deepcopy(model.state)
        expected=model.goaldat.manager_initials[2]+' '+model.goaldat.manager_names[2]
        self.assertEqual(card(model.state,2,model.goaldat)['manager'],expected)
        self.assertEqual(model.state,before)

    def test_tactics_header_uses_renamed_human_without_changing_career_or_other_fields(self):
        from goal2.ui.s10_team_tactics import TeamTacticsScreen
        model=self.model();before=copy.deepcopy(model.state)
        window=self.window();window.open_career(model)
        screen=TeamTacticsScreen(window,model);window.push(screen);self.app.processEvents()
        self.assertEqual(screen.team_header.team['manager'].text(),'K Ees')
        old_skills=copy.deepcopy(screen.skills.panel);old_traits=copy.deepcopy(screen.characteristics.panel)
        model.rename_manager('New manager');screen.refresh()
        self.assertEqual(screen.team_header.team['manager'].text(),'New manager')
        self.assertEqual(screen.skills.panel,old_skills);self.assertEqual(screen.characteristics.panel,old_traits)
        self.assertEqual(model.state.players,before.players);self.assertEqual(model.state.countries,before.countries)
        window.leave()
