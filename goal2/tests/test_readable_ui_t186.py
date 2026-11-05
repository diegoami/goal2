"""[designed: owner #598] Larger text, live injury labels and honest prominent pair feedback."""
import unittest
from types import SimpleNamespace
from goal2.tests import requires

@requires.need(modules=('PySide6','pygame'), **requires.HALFTIME)
class Readable(unittest.TestCase):
    def setUp(self):
        from goal2.tests.test_ui_replay_t181 import ReplayScreens
        ReplayScreens.setUp(self)
        from goal2.ui.s19_bench import BenchAnswer, BenchScreen
        words=self.model.state.managed_squad
        self.off,self.on=words[1],words[12]
        decision=SimpleNamespace(minute=45,score=[0,0],data=dict(context='half_time',eleven=words[:11],
            bench=words[11:],substitutions_left=5,injured=[self.off]))
        self.answer=BenchAnswer(self.model,decision)
        self.bench=self.window.push(BenchScreen(self.window,self.model,self.answer,names=('Italy','Poland')))
        self.app.processEvents()

    def test_normal_text_is_materially_larger(self):
        from goal2.ui import theme
        self.assertGreaterEqual(theme.TEXT,24)
        self.assertGreaterEqual(self.bench.counter.font().pixelSize(),24)

    def test_live_injury_stays_red_when_selected_and_has_a_word_label(self):
        from goal2.ui import theme
        from PySide6.QtGui import QColor
        self.bench.row=1
        self.bench.refresh()
        row=self.bench.strip.rows[1]
        self.assertIn('INJURED',row.texts()[-1])
        self.assertEqual(row.cells[-1].palette().color(row.cells[-1].foregroundRole()),QColor(theme.BAD))
        self.assertIn('injur',self.answer.card(self.off)['health'].lower())

    def test_pair_feedback_is_large_and_below_the_card(self):
        self.answer.enter(self.off);self.answer.enter(self.on)
        self.bench.refresh();self.app.processEvents()
        self.assertGreaterEqual(self.bench.note.font().pixelSize(),24)
        self.assertGreater(self.bench.note.mapTo(self.bench,self.bench.note.rect().topLeft()).y(),
                           self.bench.card.mapTo(self.bench,self.bench.card.rect().topLeft()).y())
        self.assertIn('off',self.bench.note.text())
        self.assertIn('on',self.bench.note.text())

    def test_roster_and_key_controls_fit_base_page(self):
        self.window.resize(1440,900);self.app.processEvents()
        bounds=self.bench.rect()
        for widget in [self.bench.strip.rows[-1],self.bench.enter_hint,self.bench.note]:
            box=widget.rect().translated(widget.mapTo(self.bench,widget.rect().topLeft()))
            self.assertTrue(bounds.contains(box),(widget.objectName(),box,bounds))
            self.assertGreaterEqual(widget.height(),widget.minimumSizeHint().height())

if __name__=='__main__': unittest.main()
