"""[designed: T118] Resume the unchanged original E031 shootout through its own decisions."""
import hashlib
import os
from pathlib import Path
import tempfile
import time
import unittest
from goal2.tests import requires

NAME='3ea57029282b849f-g1-03874-shootout-start.sav'
SHA='3ea57029282b849fd3114a995178f35e48c420c768f0702b9d3b7d48600dc1fc'
NEEDS=dict(modules=('unicorn',),files=(NAME,'GOAL.DAT'))

def started():
    from goal2.core import Core
    from goal2.core.driver import Driver
    raw=(requires.CACHE/NAME).read_bytes();assert hashlib.sha256(raw).hexdigest()==SHA
    return Driver(Core.start(raw).core)

@requires.need(**NEEDS)
class Announcement(unittest.TestCase):
    def test_the_unchanged_original_stops_at_its_qualified_announcement(self):
        d=started()
        self.assertEqual(d.wait.kind,'shootout-announcement')
        self.assertEqual(d.wait.site,'214B:098A')
        self.assertEqual(d.wait.view['message'],'penalty shoot out')
        self.assertIn('penalty shoot out  PRESS ANY KEY',d.wait.text)
        self.assertIsNone(d.core.stopped)
        frame=d.core._frame()
        self.assertEqual(frame.far_caller(frame.bp),'214B:054E')
        self.assertEqual(frame.far_caller(frame.up(frame.bp)),'0791:A137')


class Availability(unittest.TestCase):
    def test_current_match_availability_is_not_next_match_suspension(self):
        # Scalar record controls only: these are never guest memory or a constructed Core input.
        from goal2.core.views import _shootout_available
        player=bytearray(20);player[0x0E]=32
        self.assertTrue(_shootout_available(player))
        player[0x10]=0x10   # element5: next-match suspension, not 3216's current-match refusal
        self.assertTrue(_shootout_available(player))
        for bit in (0x80,0x20,0x04):
            player[0x10]=bit;self.assertFalse(_shootout_available(player))
        player[0x10]=0
        for energy in (0,128,255):
            player[0x0E]=energy;self.assertFalse(_shootout_available(player))


def complete_order(d):
    from goal2.core import views
    with d.core.live_frames():
        while d.wait.kind=='shootout-order':
            order=views.shootout_order(d.wait.state,d.wait.view)
            choice=next(p for p in order['players'] if p['available'] and p['rank'] is None)
            d.shootout_pick(choice['player'])


@requires.need(**NEEDS,slow=True)
class Order(unittest.TestCase):
    def test_original_order_undo_refusals_and_exact_partial_saved_replay(self):
        from goal2.core import Core,views
        from goal2.core.driver import Driver,DriverError
        d=started();d.shootout_start()
        self.assertEqual(d.wait.kind,'shootout-order')
        self.assertEqual(d.wait.view['needed'],11)
        from goal2.tests.test_core_screens_t103 import text_kind
        self.assertEqual(text_kind(d.wait.text),'shootout-order')
        order=views.shootout_order(d.wait.state,d.wait.view)
        for p in order['players']:self.assertIn(p['name'],d.wait.text)
        before=d.core.memory_sha256()
        with self.assertRaises(DriverError):d.shootout_pick(views.match_sides(d.wait.state)['bench'][0])
        self.assertEqual(d.core.memory_sha256(),before)
        first=order['players'][4]['player'];second=order['players'][0]['player']
        d.shootout_pick(first);d.shootout_pick(second)
        self.assertEqual(d.wait.view['picks'],[5,1])
        d.shootout_undo();self.assertEqual(d.wait.view['picks'],[5])
        before=d.core.memory_sha256()
        with self.assertRaises(DriverError):d.shootout_pick(first)
        self.assertEqual(d.core.memory_sha256(),before)
        self.assertEqual(d._pass(('manager-menu',)).kind,'shootout-order')
        self.assertEqual(d.core.memory_sha256(),before)  # no silent/default order
        saved=d.core.save();log_start=len(d.log)
        replay=Driver(Core.load(saved,goal_dat=requires.CACHE/'GOAL.DAT'))
        self.assertEqual(replay.wait.view,d.wait.view)
        complete_order(d)
        with replay.core.live_frames():
            for _,key in d.log[log_start:]:replay.core.press(key)
        self.assertEqual(d.wait.kind,'match-live')
        self.assertEqual(d.core.keys,replay.core.keys)
        self.assertEqual(d.core.memory_sha256(),replay.core.memory_sha256())

    def test_all_eleven_picks_are_required_then_original_kicks_reach_full_time(self):
        from goal2.core import views
        from goal2.tests.test_core_round_t108 import board_text
        d=started();d.shootout_start()
        for _ in range(5):
            order=views.shootout_order(d.wait.state,d.wait.view)
            p=next(p for p in order['players'] if p['available'] and p['rank'] is None)
            d.shootout_pick(p['player'])
        self.assertEqual(d.wait.kind,'shootout-order');self.assertEqual(len(d.wait.view['picks']),5)
        complete_order(d)
        with d.core.live_frames():
            for _ in range(12000):
                if d.wait.kind!='match-live':break
                d.live_step()
            else:self.fail('Original shootout did not finish within12000 complete poses')
        self.assertEqual(d.wait.kind,'match-summary-save-prompt')
        board=views.board(d.wait.state)
        self.assertEqual(dict(zip(map(str.upper,board['names']),board['score'])),board_text(d.wait.text)[0])
        self.assertNotEqual(*board['score'])
        self.assertTrue(d.wait.poll)
        self.assertIn('save the match summary',d.wait.text.lower())
        self.assertIsNone(d.core.stopped)


@requires.need(**(NEEDS|{'modules':('unicorn','PySide6','pygame')}),slow=True)
class Desktop(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
        from PySide6.QtWidgets import QApplication
        from goal2.desktop.style import load_fonts
        cls.app=QApplication.instance() or QApplication([]);load_fonts()

    def check_bounds(self,w):
        from goal2.desktop.fixed_page import problems
        for width,height in ((1440,900),(1050,780),(900,640),(2560,1600)):
            w.resize(width,height);self.app.processEvents();self.app.processEvents()
            self.assertEqual(problems(w),[],(width,height,problems(w)))
            page=w.pages[3];need=page.minimumSizeHint()
            self.assertLessEqual(need.width(),.9*page.width())
            self.assertLessEqual(need.height(),.9*page.height())

    def test_real_announcement_partial_save_cards_guards_and_four_size_bounds(self):
        from PySide6.QtCore import Qt
        from PySide6.QtTest import QTest
        from goal2.desktop.core_model import CoreModel
        from goal2.desktop.core_window import CoreWindow
        from goal2.desktop.fixed_page import problems
        d=started()
        with tempfile.TemporaryDirectory() as folder:
            model=CoreModel(d.core,requires.CACHE/'GOAL.DAT',Path(folder)/'game.g2core')
            w=CoreWindow(model);w.show();w.activateWindow();self.app.processEvents();w.finish_core()
            try:
                r=w.core_round;self.assertEqual(r.page_count.text(),'penalty shoot out')
                self.assertTrue(model.in_round);self.assertFalse(w.core_routes['play next game'].isEnabled())
                self.check_bounds(w)
                r.page_next.click();self.assertEqual(w.finish_core()[0],'done')
                self.assertEqual(r.views.currentIndex(),6);self.assertFalse(r.shootout_undo.isEnabled())
                before=model.memory_sha256();r.shootout_roster.set_current(4);self.app.processEvents()
                self.assertEqual(model.memory_sha256(),before)
                self.assertEqual(r.shootout_card.card['full_name'],r.state['order']['players'][4]['name'])
                QTest.keyClick(r.shootout_roster,Qt.Key.Key_Return)
                self.assertFalse(w.save_core());self.assertFalse(w.run_core('shootout_undo'))
                self.assertEqual(w.finish_core()[0],'done')
                self.assertEqual(model.core.wait.view['picks'],[5])
                self.assertTrue(w.save_core())
                saved=model.save_path
            finally:w.close();self.app.processEvents()
            model=CoreModel.from_save(saved,requires.CACHE/'GOAL.DAT')
            w=CoreWindow(model);w.show();self.app.processEvents();w.finish_core()
            try:
                r=w.core_round;self.assertEqual(model.core.wait.view['picks'],[5])
                self.assertTrue(model.in_round);self.assertTrue(r.shootout_undo.isEnabled())
                if os.environ.get('QT_SCALE_FACTOR'):
                    self.assertEqual(w.devicePixelRatioF(),float(os.environ['QT_SCALE_FACTOR']))
                self.check_bounds(w)
                before=model.memory_sha256()
                with self.assertRaises(ValueError):model.act('swap',0,1)
                self.assertEqual(model.memory_sha256(),before)
                r.shootout_roster.set_current(4);self.app.processEvents()
                self.assertFalse(r.shootout_pick.isEnabled())
                r.shootout_undo.click();self.assertEqual(w.finish_core()[0],'done')
                self.assertEqual(model.core.wait.view['picks'],[])
            finally:w.close();self.app.processEvents()

    def test_watched_shootout_finishes_through_the_real_desktop_viewer(self):
        from goal2.desktop.core_model import CoreModel
        from goal2.desktop.core_window import CoreWindow
        d=started();d.shootout_start()
        with tempfile.TemporaryDirectory() as folder:
            model=CoreModel(d.core,requires.CACHE/'GOAL.DAT',Path(folder)/'game.g2core')
            w=CoreWindow(model);w.show();self.app.processEvents();w.finish_core()
            try:
                r=w.core_round
                while model.core.wait.kind=='shootout-order':
                    p=next(p for p in r.state['order']['players'] if p['available'] and p['rank'] is None)
                    r.shootout_roster.set_current(p['slot']-1);r.shootout_pick.click()
                    self.assertEqual(w.finish_core()[0],'done')
                self.assertIsNotNone(r.viewer)
                deadline=time.monotonic()+180
                while r.state['stop']!='summary-save' and time.monotonic()<deadline:
                    self.app.processEvents();time.sleep(.002)
                self.assertEqual(r.state['stop'],'summary-save')
                self.assertEqual(r.views.currentIndex(),5)
                self.assertIn('FULL TIME',r.summary_board.text())
            finally:w.close();self.app.processEvents()

if __name__=='__main__':unittest.main()
