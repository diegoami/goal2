"""[designed: T115] Original-key round pause: caller, current results, replay and desktop recovery."""
import hashlib
import json
import os
from pathlib import Path
import tempfile
import unittest

from goal2.tests import requires

INPUT = 'g13-78a03f2f42b4c68b-round-pause.g2core'
SHA = '78a03f2f42b4c68bc7c5e3ca368271ec75365c29c0cc9d9e9c88c956213a66cd'
NEEDS = dict(modules=('unicorn',), files=(INPUT, 'GOAL.DAT'))
SIZES = ((1440,900),(1050,780),(900,640),(2560,1600))
CAPTAIN_INPUT = json.loads((requires.ROOT/'docs/evidence/T115/artifacts.json').read_text())['artifacts'][1]


def loaded(name=INPUT, sha=SHA):
    from goal2.core import Core
    from goal2.core.driver import Driver
    raw = (requires.CACHE / name).read_bytes()
    assert hashlib.sha256(raw).hexdigest() == sha
    return Driver(Core.load(raw, goal_dat=requires.CACHE / 'GOAL.DAT'))


@requires.need(**NEEDS)
class Pause(unittest.TestCase):
    def test_original_space_stops_at_the_exact_caller_with_the_current_fixture(self):
        from goal2.core import views
        from goal2.tests.test_core_round_t108 import results_text
        d = loaded()
        wait = d.round_start()
        self.assertEqual((wait.kind,wait.site), ('round-paused','214B:098A'))
        frame = d.core._frame()
        box = frame.up(frame.bp)
        self.assertEqual(frame.far_caller(frame.bp),'214B:054E')
        self.assertEqual(frame.far_caller(box),'000E:6BD5')
        self.assertEqual((wait.view['first'],wait.view['last']),(706,706))
        self.assertEqual(wait.view['message'],'PAUSE')
        self.assertIn('PAUSE  PRESS ANY KEY',wait.text)
        rows = views.round_results(wait.state,wait.view['first'],wait.view['last'])['rows']
        self.assertEqual(results_text(wait.text), [(r['first_name'],*r['score'],r['second_name'],r['kind_name']) for r in rows])
        self.assertEqual(len(rows),1)
        self.assertEqual((rows[0]['first_name'],rows[0]['second_name']),('Belgium','Iceland'))
        self.assertEqual(rows[0]['score'],(0,0))
        self.assertIsNone(d.core.stopped)
        self.assertIn(('round-playing',32),d.log)
        self.assertNotIn(('round-paused',13),d.log)


@requires.need(**NEEDS,slow=True)
class Replay(unittest.TestCase):
    def test_repeated_original_space_preserves_the_current_fixture_and_sliding_window(self):
        from goal2.core import views
        from goal2.tests.test_core_round_t108 import results_text
        d = loaded();d.round_start()
        for current in range(707,724):
            d.core.queue('round-playing',32)
            wait = d.round_continue()
            self.assertEqual(wait.kind,'round-paused')
            first = max(706,current-15)
            self.assertEqual((wait.view['first'],wait.view['last']),(first,current))
            rows = views.round_results(wait.state,first,current)['rows']
            self.assertEqual([r['number'] for r in rows],list(range(first,current+1)))
            self.assertEqual(results_text(wait.text),[(r['first_name'],*r['score'],r['second_name'],r['kind_name']) for r in rows])

    def test_continue_uses_enter_and_preserves_exact_saved_replay_and_earlier_pages(self):
        from goal2.core import Core
        from goal2.core.driver import Driver,UnexpectedScreen
        d = loaded();d.round_start();saved = d.core.save()
        replay = Driver(Core.load(saved,goal_dat=requires.CACHE/'GOAL.DAT'))
        self.assertEqual(replay.wait.view,d.wait.view)
        before = d.core.memory_sha256()
        wait = d.round_continue()
        self.assertNotEqual(d.core.memory_sha256(),before)
        self.assertIn(wait.kind,('match-menu','manager-menu'))
        self.assertIn(('round-paused',13),d.log)
        # Independent original Enter then the driver's existing passing route, preserving every page.
        replay.core.press(13)
        replay._pass(('match-menu','manager-menu'))
        self.assertEqual(d.core.memory_sha256(),replay.core.memory_sha256())
        self.assertEqual(d.core.keys,replay.core.keys)
        self.assertEqual(d.pages,replay.pages)
        self.assertTrue(d.pages)
        self.assertEqual(d.pages[0][0],'round-results')
        before = d.core.memory_sha256()
        with self.assertRaises(UnexpectedScreen):d.round_continue()
        self.assertEqual(d.core.memory_sha256(),before)


@requires.need(**(NEEDS|{'modules':('unicorn','PySide6')}),slow=True)
class Desktop(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
        from PySide6.QtWidgets import QApplication
        from goal2.desktop.style import load_fonts
        cls.app = QApplication.instance() or QApplication([])
        load_fonts()

    @requires.need(files=(CAPTAIN_INPUT['name'],))
    def test_continue_keeps_the_results_before_the_later_captain(self):
        from goal2.desktop.core_model import CoreModel
        from goal2.desktop.core_window import CoreWindow
        d = loaded(CAPTAIN_INPUT['name'],CAPTAIN_INPUT['sha256'])
        with tempfile.TemporaryDirectory() as folder:
            model = CoreModel(d.core,requires.CACHE/'GOAL.DAT',Path(folder)/'game.g2core')
            w = CoreWindow(model);w.show();self.app.processEvents()
            try:
                r = w.core_round
                r.first_page = 999  # a previous round's pages must not hide this round's pages
                r.start();self.assertEqual(w.finish_core()[0],'done')
                self.assertEqual(model.core.wait.kind,'round-paused')
                self.assertEqual(r.first_page,0)
                r.page_next.click();self.assertEqual(w.finish_core()[0],'done')
                self.assertEqual(model.round_state()['stop'],'captain')
                self.assertEqual(r.views.currentIndex(),2)
                self.assertEqual(r.shown,model.driver.pages[0])
                self.assertEqual(r.shown[0],'round-results')
                self.assertFalse(r.queue)
                self.assertTrue(model.in_round)
                self.assertFalse(w.core_routes['play next game'].isEnabled())
                r.next_page()
                self.assertEqual(r.views.currentIndex(),0)
                self.assertTrue(r.captain_roster.rows)
            finally:w.close();self.app.processEvents()

    def test_reach_save_resume_and_continue_keep_guards_pages_and_layout(self):
        from PySide6.QtCore import Qt
        from PySide6.QtTest import QTest
        from goal2.desktop.core_model import CoreModel
        from goal2.desktop.core_window import CoreWindow
        from goal2.desktop.fixed_page import problems
        d = loaded()
        with tempfile.TemporaryDirectory() as folder:
            model = CoreModel(d.core,requires.CACHE/'GOAL.DAT',Path(folder)/'game.g2core')
            w = CoreWindow(model);w.show();self.app.processEvents()
            try:
                w.core_routes['play next game'].click();w.finish_core()
                self.assertEqual(model.round_state()['stop'],'round-paused')
                self.assertTrue(model.in_round)
                self.assertFalse(w.core_routes['play next game'].isEnabled())
                self.assertTrue(w.save_core())
                saved = model.save_path
            finally:w.close();self.app.processEvents()
            model = CoreModel.from_save(saved,requires.CACHE/'GOAL.DAT')
            w = CoreWindow(model);w.show();w.activateWindow();self.app.processEvents();w.finish_core()
            try:
                r = w.core_round
                self.assertEqual(model.core.wait.kind,'round-paused')
                self.assertEqual(r.page_next.text(),'Continue (Enter)')
                self.assertIn('PAUSE',r.page_count.text())
                self.assertIn('Belgium',str(r.page_board.lines))
                self.assertIn('Iceland',str(r.page_board.lines))
                if os.environ.get('QT_SCALE_FACTOR'):
                    self.assertEqual(w.devicePixelRatioF(),float(os.environ['QT_SCALE_FACTOR']))
                self.assertFalse(w.core_routes['play next game'].isEnabled())
                self.assertFalse(w.core_team_buttons['reposition'].isEnabled())
                before = model.memory_sha256()
                with self.assertRaises(ValueError):model.act('swap',0,1)
                self.assertEqual(model.memory_sha256(),before)
                for width,height in SIZES:
                    w.resize(width,height);self.app.processEvents();self.app.processEvents()
                    self.assertEqual(problems(w),[],(width,height,problems(w)))
                    page = w.pages[3];need = page.minimumSizeHint()
                    self.assertLessEqual(need.width(),.9*page.width())
                    self.assertLessEqual(need.height(),.9*page.height())
                r.page_next.setFocus();QTest.keyClick(r.page_next,Qt.Key.Key_Return)
                self.assertTrue(w.core_jobs.busy)
                self.assertFalse(w.save_core())
                self.assertFalse(w.run_core('round_continue'))
                self.assertEqual(w.finish_core()[0],'done')
                self.assertNotEqual(model.memory_sha256(),before)
                self.assertEqual(r.queue,model.driver.pages[1:])
                self.assertEqual(r.page_next.text(),'Next > (Enter)')
                while r.queue:r.next_page()
                r.next_page()
                if model.round_state()['stop']=='captain':
                    self.assertEqual(r.views.currentIndex(),0)
                else:self.assertEqual(model.core.wait.kind,'manager-menu')
            finally:w.close();self.app.processEvents()
