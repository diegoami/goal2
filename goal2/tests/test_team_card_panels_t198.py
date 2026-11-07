"""T198: real new-window TEAM fields from original-backed snapshots, with explicit view context."""
import copy
from pathlib import Path
import unittest
from goal2.tests import requires
from goal2.tests.test_ui_start_t163 import App
from goal2.tests.test_core_team_panels_t144 import FIXTURES

@requires.need(files=tuple(v[0] for v in FIXTURES.values())+('GOAL.DAT','e010-r0008-halftime.sav'),modules=('PySide6',))
class Panels(App):
    def snapshot(self,name):
        from goal2.desktop.model import DesktopModel
        from goal2.game.state import from_savestate
        from goal2.data.goaldat import load
        raw=(requires.CACHE/FIXTURES[name][0]).read_bytes()
        model=DesktopModel(load((requires.CACHE/'GOAL.DAT').read_bytes()),raw,self.tmp/'never-written.g2save')
        model.state=from_savestate(raw);model.mark_saved()
        return model

    def team_screen(self,model):
        from goal2.ui.s07_team_info import TeamInfoScreen
        w=self.window();s=TeamInfoScreen(w,model);w.push(s);self.app.processEvents();w.grab()
        return w,s

    def choose_country(self,screen,country):
        screen.index=next(i for i,c in enumerate(screen.order) if c[0]==country)
        screen.preview();screen._show();self.app.processEvents()

    def compare(self,view,data,active=False):
        from goal2.desktop.country_card import characteristic_view
        for key in ('skills','performance'):
            panel=data['team_skills' if key=='skills' else key] if key=='skills' or active else None
            shown=getattr(view,key)
            self.assertEqual(shown.panel,panel)
            for line,(bar,_) in shown.rows.items():
                wanted=None if panel is None else next(row['cells'] for row in panel['bars'] if row['line']==line)
                self.assertEqual(bar.value,(wanted,25))
        self.assertEqual(view.characteristics.cells.grid,characteristic_view(data['characteristics']['descriptors']))
        for row in data['characteristics']['numbers']:
            self.assertEqual(view.averages.values[row['field']].text(),row['text'])

    def test_all128_original_snapshot_cards_render_exact_panels_without_state_write(self):
        from goal2.game.country_card import card
        for fixture in FIXTURES:
            model=self.snapshot(fixture);before=copy.deepcopy(model.state);window,screen=self.team_screen(model)
            for country in range(1,129):
                with self.subTest(fixture=fixture,country=country):
                    self.choose_country(screen,country)
                    self.compare(screen.card_view,card(model.state,country,model.goaldat))
            self.assertEqual(model.state,before)
            window.close();self.app.processEvents()

    def test_active_snapshot_uses_original_gate_side_and_full_viewport(self):
        from goal2.game.country_card import card
        model=self.snapshot('friendly');before=copy.deepcopy(model.state);window,screen=self.team_screen(model)
        screen.card_view.match_context=True
        for country in (7,16,29):
            self.choose_country(screen,country)
            self.compare(screen.card_view,card(model.state,country,model.goaldat),active=True)
        # Declared synthetic display packet: preserve full original row-major overflow/crop.
        data=copy.deepcopy(card(model.state,16,model.goaldat));data['characteristics']['descriptors'][0]['cells']=164
        screen.card_view.set_card(data,{'caps':999,'age':999});self.app.processEvents()
        self.compare(screen.card_view,data,active=True)
        self.assertEqual(model.state,before)

    def test_fresh_browser_ignores_template_performance_and_uses_original_xi_numbers(self):
        self.data();window=self.window();screen=self.to_country_screen(window);screen.settle()
        self.assertEqual(screen.chosen()[1],'Denmark')
        from goal2.game.country_card import card
        from goal2.game.team_card import TeamMemory
        state=screen.browser.state;reader=TeamMemory(state)
        self.assertEqual([reader.read_ds(o,1)[0] for o in (0xC1E,0xC1F)],[1,1])
        before=copy.deepcopy(state);data=card(state,7,screen.browser.goaldat)
        self.assertIsNotNone(data['performance'],'the template gates alone would show old performance')
        self.compare(screen.card_view,data)
        self.assertEqual(screen.averages.values['age'].text(),'29','recorded original XI aggregate, not twenty mean28')
        self.assertEqual(state,before)

    def test_complete_text_pixels_and_navigation_fit_at_three_sizes(self):
        from PySide6.QtCore import Qt
        from PySide6.QtGui import QColor
        from goal2.desktop import fixed_page
        from goal2.ui import theme
        self.data();window=self.window();screen=self.to_country_screen(window);screen.settle();window.grab()
        before=copy.deepcopy(screen.browser.state)
        for width,height in ((1440,900),(1800,1125),(2110,1213)):
            window.resize(width,height);self.app.processEvents();window.grab()
            self.assertEqual(fixed_page.problems(window),[],(width,height))
            view=screen.card_view;cells=view.characteristics.cells
            self.assertGreaterEqual(cells.width()+1,cells.content_size().width())
            self.assertGreaterEqual(cells.height()+1,cells.content_size().height())
            self.assertGreaterEqual(cells.font().pixelSize(),round(24*window.frame.scale))
            for value in view.averages.values.values():
                self.assertGreaterEqual(value.font().pixelSize(),round(24*window.frame.scale))
                self.assertEqual(value.palette().color(value.foregroundRole()),QColor(theme.VALUE))
            for label in (*view.averages.labels.values(),*view.characteristics.labels.values()):
                self.assertEqual(label.palette().color(label.foregroundRole()),QColor(theme.CARD_LABEL))
            image=cells.grab().toImage()
            colors={image.pixelColor(x,y).name() for y in range(image.height()) for x in range(image.width())}
            self.assertIn('#aaaaaa',colors);self.assertIn('#aa00aa',colors)
        self.assertEqual(screen.browser.state,before)
        self.key(window,Qt.Key.Key_Down,2);screen.settle()
        self.assertEqual(screen.chosen()[1],'Holland')
        self.assertEqual(screen.averages.values['age'].text(),'28','retain original t156-005 numeric assertion')
        self.key(window,Qt.Key.Key_Space);self.assertEqual(len(window.current().cards),20)
        self.key(window,Qt.Key.Key_Escape);self.assertIs(window.current(),screen)

if __name__=='__main__':unittest.main()
