"""[designed: owner #434/T134] Read-only direct comparison, followed by an explicit original exchange."""
import unittest
from goal2.tests import requires


@requires.need(modules=('unicorn','PySide6'),files=('e006-r0001-main.sav','GOAL.DAT'))
class Comparison(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from PySide6.QtWidgets import QApplication
        cls.app = QApplication.instance() or QApplication([])

    def window(self):
        from goal2.tests.test_core_team_t107 import model
        from goal2.desktop.core_window import CoreWindow
        w = CoreWindow(model());w.show();self.app.processEvents();w.navigate(2)
        self.addCleanup(w.close)
        return w

    def test_comparison_widget_paints_both_genuine_cards_without_touching_the_core(self):
        from goal2.tests.test_core_team_t107 import model
        from goal2.desktop.player_card import core_card
        from goal2.desktop.core_pool_compare import PlayerComparisonView
        from goal2.desktop.style import load_fonts
        load_fonts();m=model();before=m.core.save()
        left=core_card(m.card(m.team()['squad'][2]['player']))
        right=core_card(m.card(m.pool()['rows'][3]['player']))
        widget=PlayerComparisonView();widget.resize(1000,560);widget.set_cards(left,right)
        try:
            widget.show();self.app.processEvents();widget.repaint()
            for card in (left,right):self.assertIn(card['full_name'],widget.drawn)
            self.assertLessEqual(widget.bottom,560)
            image=widget.grab().toImage();image.save('.cache/T134-compare-preview.png')
            widget.set_cards(right,left);self.app.processEvents()
            self.assertNotEqual(widget.grab().toImage(),image)
            self.assertEqual(m.core.save(),before)
        finally:widget.close()

    def test_two_genuine_players_are_simultaneously_visible_and_browsing_changes_nothing(self):
        from goal2.desktop.player_card import core_card
        w = self.window();incoming=w.pool_selected();before=w.model.core.save()
        outgoing=w.team_roster.rows[w.team_roster.current][0]
        w.pool_compare.click();self.app.processEvents()
        self.assertEqual(w.core_pool_views.currentIndex(),1)
        self.assertEqual(w.pool_comparison.cards,[core_card(w.model.card(outgoing)),core_card(w.model.card(incoming))])
        w.pool_comparison.repaint()
        for card in w.pool_comparison.cards:
            self.assertIn(card['full_name'],w.pool_comparison.drawn)
            self.assertIn(f"CAPS {card['caps']}  GOALS {card['goals']}  AGE {card['age']}",w.pool_comparison.drawn)
        w.pool_compare_squad.setCurrentIndex(2);self.app.processEvents()
        self.assertEqual(w.pool_comparison.cards[0],core_card(w.model.card(w.pool_compare_squad.currentData())))
        self.assertEqual(w.pool_comparison.cards[1],core_card(w.model.card(incoming)))
        self.assertEqual(w.model.core.save(),before)
        w.pool_compare_back.click();self.assertEqual(w.core_pool_views.currentIndex(),0)
        self.assertEqual(w.pool_selected(),incoming)
        from PySide6.QtCore import Qt
        from PySide6.QtTest import QTest
        w.pool_compare.click();QTest.keyClick(w.pool_compare_squad,Qt.Key.Key_Escape)
        self.assertEqual(w.core_pool_views.currentIndex(),0)

    def test_explicit_exchange_uses_those_full_ids_and_cannot_repeat_a_stale_pair(self):
        from goal2.desktop.pool_page import core_compare_exchange
        w=self.window();incoming=w.pool_selected();w.pool_compare.click()
        outgoing=w.pool_compare_squad.currentData();before={r['player'] for r in w.model.team()['squad']}
        w.pool_compare_exchange.click();self.assertTrue(w.core_jobs.busy)
        self.assertEqual(w.finish_core()[0],'done')
        after={r['player'] for r in w.model.team()['squad']}
        self.assertEqual(after,(before-{outgoing})|{incoming})
        self.assertFalse(w.pool_compare_exchange.isEnabled())
        stable=w.model.core.save()
        self.assertFalse(core_compare_exchange(w));self.assertFalse(w.core_jobs.busy)
        self.assertEqual(w.model.core.save(),stable)

    def test_readable_complete_comparison_fits_the_retained_fixed_page_bounds(self):
        from goal2.desktop.fixed_page import problems
        w=self.window();w.pool_compare.click()
        for size in ((1440,900),(1050,780),(900,640),(2560,1600)):
            w.resize(*size);self.app.processEvents();w.pool_comparison.repaint()
            self.assertEqual(problems(w),[])
            page=w.pages[2];need=page.minimumSizeHint()
            self.assertLessEqual(need.width(),page.width()*.9)
            self.assertLessEqual(need.height(),page.height()*.9)
            self.assertLessEqual(w.pool_comparison.bottom,560)

    def test_busy_and_missing_selection_do_not_open_or_exchange(self):
        from goal2.desktop.pool_page import core_compare,core_compare_exchange
        w=self.window();before=w.model.core.save()
        w.pool_side='squad'
        self.assertFalse(core_compare(w));self.assertEqual(w.core_pool_views.currentIndex(),0)
        w.pool_side='pool';w.pool_compare.click();w.pool_compare_squad.setCurrentIndex(-1)
        self.assertFalse(core_compare_exchange(w));self.assertFalse(w.core_jobs.busy)
        self.assertEqual(w.model.core.save(),before)

    def test_busy_and_live_controls_do_not_rebuild_hidden_management_records(self):
        from unittest.mock import patch,PropertyMock
        from contextlib import ExitStack
        from goal2.desktop.pool_page import core_comparison_controls
        w=self.window();before=w.model.core.save()
        for mode in ('busy','round'):
            with self.subTest(mode=mode),ExitStack() as stack:
                stack.enter_context(patch.object(w.model,'team',side_effect=AssertionError('hidden team read')))
                stack.enter_context(patch.object(w.model,'pool',side_effect=AssertionError('hidden pool read')))
                if mode=='busy':
                    stack.enter_context(patch.object(type(w.core_jobs),'busy',new_callable=PropertyMock,return_value=True))
                else:
                    stack.enter_context(patch.object(type(w.model),'in_round',new_callable=PropertyMock,return_value=True))
                core_comparison_controls(w)
                self.assertFalse(w.pool_compare.isEnabled());self.assertFalse(w.pool_compare_exchange.isEnabled())
        self.assertEqual(w.model.core.save(),before)

    def test_saved_career_reopens_with_the_same_comparison_values(self):
        import tempfile
        from pathlib import Path
        from goal2.desktop.core_model import CoreModel
        from goal2.desktop.core_window import CoreWindow
        w=self.window();w.pool_compare.click();w.pool_compare_squad.setCurrentIndex(2)
        outgoing=w.pool_compare_squad.currentData();cards=w.pool_comparison.cards
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'comparison.g2core';w.model.save(path)
            loaded=CoreModel.from_save(path,requires.CACHE/'GOAL.DAT');again=CoreWindow(loaded)
            try:
                again.navigate(2);again.pool_compare.click()
                again.pool_compare_squad.setCurrentIndex(again.pool_compare_squad.findData(outgoing))
                self.assertEqual(again.pool_comparison.cards,cards)
                self.assertEqual(loaded.core.save(),w.model.core.save())
            finally:again.close()
