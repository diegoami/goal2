"""Owner611: aligned visible facts and contrasting semantic colours, with real Qt input."""
import tempfile
import unittest
from pathlib import Path
from goal2.tests import requires
from goal2.tests.reflow_pending import assert_fits

@requires.need(modules=('PySide6',), **requires.HALFTIME)
class CardTable(unittest.TestCase):
    def setUp(self):
        from PySide6.QtWidgets import QApplication
        from goal2.desktop import data_setup
        from goal2.tests.test_ui_squad_t165 import career
        from goal2.ui import theme
        from goal2.ui.window import Window
        from goal2.ui.s08_squad import open_squad
        self.app=QApplication.instance() or QApplication([]);theme.install(self.app)
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.model=career();self.window=Window(data_setup.paths(Path(self.temp.name)))
        self.window.open_career(self.model);self.window.show();self.screen=open_squad(self.window,self.model)
        self.app.processEvents();self.window.grab()  # normal initial paint before display mutations (#617)
        self.addCleanup(self.window.leave)

    def test_all_twenty_keep_aligned_facts_values_and_full_controls_at_three_sizes(self):
        from goal2.desktop import fixed_page
        from goal2.game.player_card import card
        fields=('age','caps','goals','height','foot','performance')
        for width,height in ((1440,900),(1800,1125),(2110,1213)):
            self.window.resize(width,height)
            for row in range(20):
                self.screen.cursor['squad']=row;self.screen.refresh();self.app.processEvents()
                view=self.screen.card;data=card(self.model.state,self.screen.current(),self.model.goaldat)
                self.assertEqual(tuple(view.facts.labels),fields)
                for key in fields:
                    label,value=view.facts.labels[key],view.facts.values[key]
                    self.assertEqual(label.x(),value.x(),(key,row,width))
                    self.assertLess(label.y(),value.y())
                    self.assertTrue(value.isVisible())
                    self.assertGreaterEqual(label.font().pixelSize(),round(24*self.window.frame.scale))
                    self.assertGreaterEqual(value.font().pixelSize(),round(24*self.window.frame.scale))
                    if key!='performance':self.assertEqual(value.text(),str(data[key]))
                self.assertEqual(tuple(view.positions.labels),('position','club position','cards'))
                self.assertEqual(view.positions.values['position'].text(),data['position'])
                self.assertEqual(view.positions.values['club position'].text(),data['club_position'])
                self.assertEqual(view.positions.values['cards'].text(),', '.join(data['cards']) or 'none')
                self.assertEqual(len([r for r in self.screen.strip.rows if r.isVisible()]),20)
                assert_fits(self, self.window, (row,width,height))
    def test_fact_and_characteristic_roles_have_actual_distinct_palette_and_pixels(self):
        from PySide6.QtGui import QColor
        from goal2.ui import theme
        view=self.screen.card
        label=view.facts.labels['age'];value=view.facts.values['age']
        tone=theme.GOALKEEPER  # selected first player's actual goalkeeper card
        self.assertEqual(label.palette().color(label.foregroundRole()),QColor(theme.CARD_HEADING))
        self.assertEqual(value.palette().color(value.foregroundRole()),QColor(tone))
        hardness=view.characteristics.labels['hardness']
        _,word=view.characteristics.rows['hardness']
        self.assertEqual(hardness.palette().color(hardness.foregroundRole()),QColor(theme.CARD_LABEL))
        self.assertEqual(word.palette().color(word.foregroundRole()),QColor(tone))
        for widget,expected in ((label,theme.CARD_HEADING),(value,tone),(hardness,theme.CARD_LABEL),(word,tone)):
            image=widget.grab().toImage()
            count=sum(image.pixelColor(x,y).name()==expected for x in range(image.width()) for y in range(image.height()))
            self.assertGreater(count,0,(widget.text(),expected))

    def test_keyboard_rename_cancel_and_mouse_player_selection_keep_facts(self):
        from PySide6.QtCore import Qt
        from PySide6.QtTest import QTest
        current=self.screen.current();before=self.screen.card.facts.text()
        QTest.keyClick(self.window,Qt.Key.Key_F2);self.app.processEvents()
        self.assertTrue(self.screen.card.facts.isHidden())
        QTest.keyClick(self.screen.card.name_line.edit,Qt.Key.Key_Escape);self.app.processEvents()
        self.assertFalse(self.screen.card.facts.isHidden())
        self.assertEqual(self.screen.card.facts.text(),before)
        QTest.mouseClick(self.screen.strip.rows[1],Qt.MouseButton.LeftButton);self.app.processEvents()
        self.assertNotEqual(self.screen.current(),current)
        self.assertEqual(self.screen.card.facts.values['age'].text(),str(self.model.state.players[self.screen.current()][1]))

    def test_captain_and_taker_cards_retain_the_table_and_legal_selection(self):
        from PySide6.QtCore import Qt
        from PySide6.QtTest import QTest
        from goal2.desktop import fixed_page
        from goal2.ui.s16_choose import ChooseScreen
        words=self.model.state.managed_squad[:11]
        for mode in ('captain','taker'):
            chosen=[]
            screen=self.window.push(ChooseScreen(self.window,self.model,mode,words,words[0],chosen.append))
            screen.timer.stop()
            for width,height in ((1440,900),(1800,1125),(2110,1213)):
                self.window.resize(width,height);self.app.processEvents()
                self.assertIn('performance',screen.card.facts.labels)
                assert_fits(self, self.window, (mode,width,height))
            QTest.keyClick(self.window,Qt.Key.Key_Down)
            QTest.keyClick(self.window,Qt.Key.Key_Return);self.app.processEvents()
            self.assertEqual(chosen,[words[1]])
            self.window.pop()

@requires.need(modules=('PySide6','pygame'), **requires.HALFTIME)
class BenchTable(unittest.TestCase):
    def setUp(self):
        from goal2.tests.test_immediate_bench_t188 import ImmediateBench
        ImmediateBench.setUp(self)
        self.window.grab()
        self.bench.row=self.bench.answer.words().index(self.off)

    def test_bench_table_retains_large_feedback_all_twenty_rows_and_readiness(self):
        from goal2.desktop import fixed_page
        for width,height in ((1440,900),(1800,1125),(2110,1213)):
            self.window.resize(width,height);self.bench.refresh();self.app.processEvents()
            self.assertIn('age',self.bench.card.facts.labels)
            self.assertIn('cards',self.bench.card.positions.labels)
            self.assertIn('INJURED',self.bench.card.readiness.text())
            self.assertEqual(len([r for r in self.bench.strip.rows if r.isVisible()]),20)
            assert_fits(self, self.window, (width,height))
    def test_long_valid_card_values_and_refusal_feedback_are_not_clipped_or_shortened(self):
        from goal2.desktop import fixed_page
        # Declared UI-only extreme-field fixture; no natural game state is claimed.
        value=dict(self.bench.card.card)
        value.update(position='defensive midfielder',club_position='defensive midfielder',foot='two footed',
                     cards=['carried booking','booked','sent off'])
        for width,height in ((1440,900),(1800,1125),(2110,1213)):
            self.window.resize(width,height)
            self.bench.feedback_report={'made':[], 'requested':[],
                'refused':[[self.off,self.on,'This player already left the field and cannot return to this match.']]}
            self.bench.refresh()
            self.bench.card.set_card(value)
            for _ in range(3):self.app.processEvents()
            self.assertEqual(self.bench.card.positions.values['cards'].text(),'carried booking, booked, sent off')
            self.assertEqual(self.bench.card.positions.values['position'].text(),'defensive midfielder')
            self.assertEqual(self.bench.card.facts.values['foot'].text(),'two footed')
            assert_fits(self, self.window, (width,height))
if __name__=='__main__':unittest.main()
