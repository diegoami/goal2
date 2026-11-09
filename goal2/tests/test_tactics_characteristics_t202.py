"""Original1981 draws157D: pre-match tactics must retain its F038characteristics."""
import copy
import hashlib
import unittest
from goal2.tests import requires
from goal2.tests.reflow_pending import assert_fits, assert_room
from goal2.tests.test_ui_start_t163 import App
from goal2.tests.test_core_team_panels_t144 import FIXTURES

@requires.need(files=tuple(v[0] for v in FIXTURES.values())+('GOAL.DAT','e010-r0008-halftime.sav'),modules=('PySide6',))
class TacticsCharacteristics(App):
    def model(self,name):
        from goal2.desktop.model import DesktopModel
        from goal2.game.state import from_savestate
        from goal2.data.goaldat import load
        raw=(requires.CACHE/FIXTURES[name][0]).read_bytes()
        self.assertEqual(hashlib.sha256(raw).hexdigest(),FIXTURES[name][1])
        model=DesktopModel(load((requires.CACHE/'GOAL.DAT').read_bytes()),raw,self.tmp/'never-written.g2save')
        model.state=from_savestate(raw);model.mark_saved()
        return model

    def open(self,model):
        from PySide6.QtCore import Qt
        from goal2.ui.s10_team_tactics import TeamTacticsScreen
        w=self.window();w.open_career(model);self.key(w,Qt.Key.Key_T);screen=w.current()
        self.assertIsInstance(screen,TeamTacticsScreen);self.app.processEvents();w.grab()
        return w,screen

    def test_genuine_snapshots_and_current_inputs_match_original_backed_panel_without_state_write(self):
        from goal2.engine.original_match.image import Image
        from goal2.core.views import Memory
        from goal2.desktop.country_card import characteristic_view
        for fixture in FIXTURES:
            model=self.model(fixture);w,s=self.open(model)
            original=Memory(Image.from_savestate((requires.CACHE/FIXTURES[fixture][0]).read_bytes()))
            for changed in (False,True):
                state=model.state;country=state.managed_country
                if changed:
                    # Explicit current-record boundary, not a naturally played injury.
                    state.managed_squad[1],state.managed_squad[15]=state.managed_squad[15],state.managed_squad[1]
                    word=state.managed_squad[2];record=bytearray(state.players[word]);record[14]=0;state.players[word]=bytes(record)
                    addr=original.far(0xA917)+191*country
                    original.mem[addr:addr+40]=b''.join(p.to_bytes(2,'little') for p in state.managed_squad)
                    addr=original.far(0xA91B)+20*word;original.mem[addr:addr+20]=record
                before=copy.deepcopy(state);s.refresh();self.app.processEvents()
                expected=original.country_panels(country)['characteristics']
                self.assertEqual(s.characteristics.panel,expected)
                self.assertEqual(s.characteristics.cells.grid,characteristic_view(expected['descriptors']))
                self.assertNotIn('not decoded',s.characteristics.text())
                self.assertEqual(state,before)
            w.leave();self.app.processEvents()

    def test_readable_cells_pixels_and_bounds_fit_three_sizes_while_all_eight_tactics_and_mouse_return_work(self):
        from PySide6.QtCore import Qt
        from PySide6.QtGui import QColor
        from goal2.desktop import fixed_page
        from goal2.ui import theme
        from goal2.ui.s10_team_tactics import LINES
        model=self.model('selection');w,s=self.open(model)
        for width,height in ((1440,900),(1800,1125),(2110,1213)):
            w.resize(width,height);self.app.processEvents();w.grab()
            assert_fits(self, w, (width,height))
            cells=s.characteristics.cells
            assert_room(self,w,cells.width()+1,cells.content_size().width())
            assert_room(self,w,cells.height()+1,cells.content_size().height())
            self.assertGreaterEqual(cells.font().pixelSize(),round(24*w.frame.scale))
            for label in cells.labels.values():self.assertEqual(label.palette().color(label.foregroundRole()),QColor(theme.CARD_LABEL))
            image=cells.grab().toImage();colors={image.pixelColor(x,y).name() for y in range(image.height()) for x in range(image.width())}
            self.assertIn(theme.BAR_FILLED,colors);self.assertIn(theme.BAR_EMPTY,colors)
        expected=copy.deepcopy(model.state)
        for index,(_,element) in enumerate(LINES):
            old_line=s.line
            self.click(s.rows[index])
            if old_line!=index:
                self.assertEqual(model.state,expected,'first click selects another line')
                self.click(s.rows[index])
            expected.country_tactics^=1<<(element-1)
            self.assertEqual(model.state,expected)
        self.key(w,Qt.Key.Key_Escape)
        from goal2.ui.s06_desk import DeskScreen
        self.assertIsInstance(w.current(),DeskScreen)
        self.assertEqual(model.state,expected)

    def test_live_stop_retains_explicit_fallback_and_pending_confirmation_without_career_write(self):
        from types import SimpleNamespace
        from PySide6.QtCore import Qt
        from goal2.ui.s19_bench import BenchAnswer
        from goal2.ui.s10_team_tactics import TeamTacticsScreen,CHARACTERISTICS
        model=self.model('friendly');words=model.state.managed_squad
        decision=SimpleNamespace(minute=45,score=[0,0],data=dict(context='half_time',eleven=words[:11],bench=words[11:],tactics=model.state.country_tactics))
        answer=BenchAnswer(model,decision);before=copy.deepcopy(model.state);sent=[]
        w=self.window();s=TeamTacticsScreen(w,model,answer=answer,apply=lambda screen,element,wanted:sent.append((element,wanted)))
        w.push(s);self.app.processEvents()
        self.assertTrue(all(s.characteristics.values[field].text()=='not decoded yet (G05)' for field in CHARACTERISTICS))
        self.key(w,Qt.Key.Key_Return);self.assertTrue(s.pending)
        self.key(w,Qt.Key.Key_Escape);self.assertIs(w.current(),s)
        self.assertEqual(sent,[(5,not bool(answer.team_tactics&16))]);self.assertEqual(model.state,before)

if __name__=='__main__':unittest.main()
