"""[designed: owner #435/T135] Original-assistant queries run on a copy, never on the active career."""
import hashlib
import threading
import unittest
from goal2.tests import requires


@requires.need(modules=('unicorn',),files=('e006-r0001-main.sav','GOAL.DAT'))
class Assistant(unittest.TestCase):
    def model(self):
        from goal2.tests.test_core_team_t107 import model
        return model()

    def original_selection(self,core):
        from goal2.core import Core,views
        from goal2.core.driver import Driver
        from goal2.core.screens import INSERT,RETURN
        d=Driver(Core.load(core.save(),goal_dat=requires.CACHE/'GOAL.DAT'))
        d.goto('select-squad');wait=d.press(INSERT,expect=('select-squad','squad-change-refused'))
        refusal=wait.view['message'] if wait.kind=='squad-change-refused' else None
        if refusal:d.press(RETURN,expect=('select-squad',))
        d.to_menu()
        return d,refusal

    def test_proposals_match_an_independent_original_key_run_and_preserve_the_active_core(self):
        from goal2.desktop.core_pool_suggest import propose
        from goal2.core import views
        m=self.model();before=m.core.save();expected,refusal=self.original_selection(m.core)
        answer=propose(m.core,m.data_path)
        self.assertEqual(answer['refusal'],refusal)
        self.assertEqual(answer['assistant_sha256'],hashlib.sha256(expected.core.save()).hexdigest())
        self.assertEqual(answer['selected'],[p['player'] for p in views.team(expected.wait.state)['squad']])
        self.assertEqual(answer['input_sha256'],hashlib.sha256(before).hexdigest())
        old={p['player'] for p in m.team()['squad']};new=set(answer['selected'])
        all_pairs=answer['proposals']+answer['rejected']
        self.assertEqual({p['outgoing'] for p in all_pairs},old-new)
        self.assertEqual({p['incoming'] for p in all_pairs},new-old)
        from goal2.core import Core
        from goal2.core.driver import Driver
        for p in answer['proposals']:
            trial=Driver(Core.load(before,goal_dat=m.data_path))
            self.assertIsNone(trial.exchange(p['outgoing'],p['incoming'])['refused'])
            self.assertEqual(p['validation_sha256'],hashlib.sha256(trial.core.save()).hexdigest())
        self.assertEqual(m.core.save(),before)

    def test_model_action_exposes_the_query_without_applying_it(self):
        m=self.model();before=m.core.save();answer=m.act('suggest_pool')
        self.assertEqual(answer['input_sha256'],hashlib.sha256(before).hexdigest())
        self.assertEqual(m.core.save(),before)

    def test_cancelled_query_does_not_even_load_a_clone(self):
        from unittest.mock import patch
        from goal2.desktop.core_pool_suggest import propose
        m=self.model();before=m.core.save();cancel=threading.Event();cancel.set()
        with patch('goal2.core.Core.load',side_effect=AssertionError('cancelled query loaded a clone')):
            answer=propose(m.core,m.data_path,cancel)
        self.assertTrue(answer['cancelled']);self.assertEqual(answer['proposals'],[])
        self.assertEqual(m.core.save(),before)

    def test_a_squad_the_original_keeps_produces_no_recruitment_proposals(self):
        from goal2.desktop.core_pool_suggest import propose
        from goal2.core import Core
        m=self.model();selected,refusal=self.original_selection(m.core)
        self.assertIsNone(refusal)
        # Setup is a genuine original assistant action in the independent Core, never record writes.
        prepared=Core.load(selected.core.save(),goal_dat=requires.CACHE/'GOAL.DAT');before=prepared.save()
        answer=propose(prepared,m.data_path)
        self.assertEqual(answer['proposals'],[])
        self.assertEqual(prepared.save(),before)

    @requires.need(files=('g16-proof-279904b6-private.zip',))
    def test_genuine_finals_context_follows_actual_original_selection_and_legality(self):
        from zipfile import ZipFile
        from goal2.core import Core
        from goal2.desktop.core_pool_suggest import propose
        bundle=requires.CACHE/'g16-proof-279904b6-private.zip'
        self.assertEqual(hashlib.sha256(bundle.read_bytes()).hexdigest(),
                         '2332459f7bf64be1afd2e92fc61d81f3b9489bf9d01208a3e6ad8edb469d4cd9')
        with ZipFile(bundle) as z:raw=z.read('.cache/T123-proof-r2/annual-1.g2core')
        self.assertEqual(hashlib.sha256(raw).hexdigest(),'f3edb478fb566c7a4437cba570b8719ab0510ec022f285fa056bdb7591173d48')
        core=Core.load(raw,goal_dat=requires.CACHE/'GOAL.DAT');before=core.save()
        expected,refusal=self.original_selection(core)
        answer=propose(core,requires.CACHE/'GOAL.DAT')
        self.assertEqual(answer['refusal'],refusal)
        self.assertEqual(answer['assistant_sha256'],hashlib.sha256(expected.core.save()).hexdigest())
        self.assertEqual(core.save(),before)

    def test_original_exchange_refusal_response_excludes_the_proposal(self):
        from unittest.mock import patch
        from goal2.desktop.core_pool_suggest import propose
        m=self.model();before=m.core.save()
        # Host protocol control: not evidence that this particular original state naturally refuses.
        with patch('goal2.core.driver.Driver.exchange',return_value={'refused':'control refusal'}):
            answer=propose(m.core,m.data_path)
        self.assertTrue(answer['rejected']);self.assertEqual(answer['proposals'],[])
        self.assertTrue(all(p['reason']=='control refusal' for p in answer['rejected']))
        self.assertEqual(m.core.save(),before)


@requires.need(modules=('unicorn','PySide6'),files=('e006-r0001-main.sav','GOAL.DAT'))
class SuggestionUI(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from PySide6.QtWidgets import QApplication
        cls.app=QApplication.instance() or QApplication([])

    def window(self):
        from goal2.tests.test_core_team_t107 import model
        from goal2.desktop.core_window import CoreWindow
        w=CoreWindow(model());w.show();self.app.processEvents();w.navigate(2)
        self.addCleanup(w.close);return w

    def test_suggest_opens_actual_proposals_without_applying_them_and_one_exchange_is_explicit(self):
        w=self.window();before=w.model.core.save();w.pool_suggest.click()
        self.assertTrue(w.core_jobs.busy);self.assertEqual(w.finish_core()[0],'done')
        self.assertTrue(w.core_suggestion_mode);self.assertEqual(w.core_pool_views.currentIndex(),1)
        self.assertEqual(w.model.core.save(),before)
        proposal=w.core_pool_suggestions['proposals'][0]
        self.assertEqual(w.pool_compare_squad.currentData(),proposal['outgoing'])
        self.assertEqual(w.core_compare_in,proposal['incoming'])
        self.assertIn('assistant',w.pool_comparison.explanation.lower())
        w.pool_compare_exchange.click();self.assertEqual(w.finish_core()[0],'done')
        self.assertIn(proposal['incoming'],[p['player'] for p in w.model.team()['squad']])
        self.assertFalse(w.core_suggestion_mode)
        self.assertFalse(w.pool_compare_exchange.isEnabled())

    def test_cancel_discards_a_query_and_preserves_the_active_career(self):
        w=self.window();before=w.model.core.save();w.pool_suggest.click()
        self.assertTrue(w.pool_suggest.isEnabled())
        self.assertIn('Cancel',w.pool_suggest.text());w.pool_suggest.click()
        self.assertEqual(w.finish_core()[0],'done')
        self.assertIn('cancel',w.status.text().lower())
        self.assertFalse(w.core_suggestion_mode);self.assertEqual(w.model.core.save(),before)

    def test_copy_failure_is_not_reported_as_an_active_game_stop(self):
        from unittest.mock import patch
        w=self.window();before=w.model.core.save()
        with patch.object(w.model,'act',side_effect=RuntimeError('controlled query failure')):
            w.pool_suggest.click();self.assertEqual(w.finish_core()[0],'done')
        self.assertIn('controlled query failure',w.status.text())
        self.assertIsNone(w.model.core.stopped);self.assertTrue(w.pool_move.isEnabled())
        self.assertEqual(w.model.core.save(),before)

    def test_a_changed_career_invalidates_a_suggestion_before_exchange(self):
        from goal2.desktop.pool_page import core_compare_exchange
        w=self.window();w.pool_suggest.click();w.finish_core()
        player=w.pool_compare_squad.currentData()
        w.model.act('rename',player,'Z Edited')
        before=w.model.core.save()
        self.assertFalse(core_compare_exchange(w));self.assertFalse(w.core_jobs.busy)
        self.assertFalse(w.core_suggestion_mode);self.assertEqual(w.model.core.save(),before)

    def test_suggestion_layout_fits_and_names_roles_and_reasons_are_readable(self):
        from PySide6.QtGui import QFont,QFontMetrics
        from goal2.desktop.fixed_page import problems
        w=self.window();w.pool_suggest.click();w.finish_core()
        for size in ((1440,900),(1050,780),(900,640),(2560,1600)):
            w.resize(*size);self.app.processEvents();w.pool_comparison.repaint()
            self.assertEqual(problems(w),[])
            page=w.pages[2];need=page.minimumSizeHint()
            self.assertLessEqual(need.width(),page.width()*.9)
            self.assertLessEqual(need.height(),page.height()*.9)
            self.assertLessEqual(w.pool_comparison.bottom,560)
        font=QFont('DejaVu Sans Mono');font.setPixelSize(16)
        self.assertLessEqual(QFontMetrics(font).horizontalAdvance(w.pool_comparison.explanation),960)

    def test_no_changes_is_reported_without_recruitment_or_a_stale_comparison(self):
        from goal2.core.screens import INSERT
        w=self.window();d=w.model.driver;d.goto('select-squad');d.press(INSERT,expect=('select-squad',));d.to_menu()
        w.refresh();before=w.model.core.save();w.pool_suggest.click();w.finish_core()
        self.assertFalse(w.core_suggestion_mode);self.assertFalse(w.pool_compare_exchange.isEnabled())
        self.assertIn('keep',w.status.text())
        self.assertEqual(w.pool_comparison.cards,[None,None])
        self.assertEqual(w.model.core.save(),before)
