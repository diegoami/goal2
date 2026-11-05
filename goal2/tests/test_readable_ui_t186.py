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

    def test_roster_and_key_controls_fit_base_and_large_pages(self):
        from goal2.desktop import fixed_page
        for width,height in ((1440,900),(2110,1213),(2880,1800)):
            self.window.resize(width,height)
            for _ in range(3): self.app.processEvents()
            self.assertEqual(fixed_page.problems(self.window),[],(width,height))

    def test_refusal_is_honest_and_names_on_then_off_once(self):
        from goal2.ui.s19_bench import BenchScreen
        from goal2.ui.squad_card import full_name
        report=dict(asked=[[self.off,self.on]],made=[],requested=[],
                    refused=[[self.off,self.on,'not made by the original']],substitutions_left=5)
        screen=self.window.push(BenchScreen(self.window,self.model,self.answer,
            names=('Italy','Poland'),report=report))
        self.app.processEvents()
        text=screen.note.text()
        self.assertLess(text.index(full_name(self.model,self.on)),text.index(full_name(self.model,self.off)))
        self.assertIn('not confirmed',text)
        self.assertNotIn('not made by the original',text)
        self.assertTrue(screen.wait_box.isHidden())
        self.assertIn('Back to the match',screen.enter_hint_text())

    def test_keyboard_pair_feedback_does_not_claim_acceptance_or_decrement_budget(self):
        from PySide6.QtCore import Qt
        from PySide6.QtTest import QTest
        self.bench.row=self.answer.words().index(self.off)
        self.bench.refresh()
        QTest.keyClick(self.window,Qt.Key.Key_Return)
        self.bench.row=self.answer.words().index(self.on)
        self.bench.refresh()
        QTest.keyClick(self.window,Qt.Key.Key_Return)
        self.app.processEvents()
        self.assertEqual(self.answer.chosen,[[self.off,self.on]])
        self.assertIn('Chosen:',self.bench.note.text())
        self.assertNotIn('Made:',self.bench.note.text())
        self.assertEqual(self.answer.left,5)

    def test_long_pitch_commentary_keeps_complete_recent_entries_inside_the_page(self):
        from goal2.desktop import fixed_page
        self.window.pop()  # S19 back to S17; no match process exists in this declared UI packet fixture.
        last='19: A Player With A Long Name scored after an assist by Another Long Player Name.'
        self.pitch.lines=[f'{i}: Earlier Player scored after a long passage of play.' for i in range(19)]+[last]
        for width,height in ((1440,900),(2110,1213)):
            self.window.resize(width,height)
            for _ in range(3):
                self.app.processEvents();self.pitch.refresh()
            self.assertEqual(fixed_page.problems(self.window),[],(width,height))
            self.assertIn(last,self.pitch.commentary.text())
            self.assertLessEqual(self.pitch.commentary.heightForWidth(self.pitch.commentary.width()),
                                 self.pitch.commentary.height())

    def test_reading_pause_banner_fits_with_long_recent_commentary_and_restores_the_header(self):
        from PySide6.QtCore import Qt
        from PySide6.QtTest import QTest
        from goal2.desktop import fixed_page
        self.window.pop()
        text='A player with a long surname scored following an assist from another named player.'
        for minute in (12,13):
            event=dict(kind='commentary',minute=minute,score=[0,0],data={'text':text})
            self.controller._send('event',event)
            self.controller.events.append(event)
        self.controller.released=len(self.controller.events)
        self.pitch.refresh()
        QTest.keyClick(self.window,Qt.Key.Key_Space)
        for width,height in ((1440,900),(2110,1213)):
            self.window.resize(width,height)
            for _ in range(3):self.app.processEvents();self.pitch.refresh()
            self.assertTrue(self.pitch.wait_head.isVisible())
            self.assertIn('PAUSED',self.pitch.wait_head.text())
            self.assertEqual(fixed_page.problems(self.window),[],(width,height))
        QTest.keyClick(self.window,Qt.Key.Key_Space)
        self.app.processEvents()
        self.assertTrue(self.pitch.home.isVisible())
        self.assertTrue(self.pitch.wait_box.isHidden())

if __name__=='__main__': unittest.main()
