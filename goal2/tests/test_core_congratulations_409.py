"""[designed: #409] Genuine G16/G15-variant congratulations, original animation and key consumption.

Source: first failed T123 run at9d0142cb, original keys only. Frame proxies and
host classifier controls below never edit guest data/registers or substitute game events.
"""
import hashlib
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from goal2.tests import requires

INPUT='g16-bdf6c0842365fb09-congratulations-before.g2core'
SHA='bdf6c0842365fb09a2767f5710ce8f2ecbba3340a43b19bc7ad8aa14bac82901'
KIND='bulletin-congratulations'
NEEDS=dict(modules=('unicorn',),files=(INPUT,'GOAL.DAT'))


def before():
    from goal2.core import Core
    raw=(requires.CACHE/INPUT).read_bytes()
    assert hashlib.sha256(raw).hexdigest()==SHA
    return Core.load(raw,goal_dat=requires.CACHE/'GOAL.DAT')


def entered():
    c=before();c.press(13);return c


@requires.need(**NEEDS)
class Congratulations(unittest.TestCase):
    def test_actual_finite_poll_machine_and_original_caption_and_papers(self):
        from goal2.core import views
        c=entered();w=c.wait
        self.assertEqual((w.kind,w.site,w.poll),(KIND,'000E:0515',True))
        self.assertIsNone(c.stopped)
        f=c._frame();p=f.up(f.bp);root=f.up(p)
        self.assertEqual((f.bp,p,root),(0x3B92,0x3B9A,0x3BA0))
        self.assertEqual((f.near_caller(f.bp),f.word(f.bp,4),f.byte(f.bp,6)),(0x5B5,p,0))
        self.assertEqual((f.near_caller(p),f.word(p,4),f.near_caller(root)),(0x624,root,0x6625))
        self.assertEqual(tuple(f.byte(root,n) for n in (4,6,8)),(0,0,1))
        snap=c.m.snapshot()
        self.assertEqual(hashlib.sha256(snap['memory']).hexdigest(),'bad191a2055b55d3e6572e60373e7eb525f85d9f1e6a35543d7aa18ff42e05bc')
        self.assertEqual(hashlib.sha256(json.dumps(snap['regs'],sort_keys=True).encode()).hexdigest(),'86a2656d1da2fd6145d0c3c4d15848b1227bee39bd1bf6e278ec6b620f93be05')
        data=views.congratulations_bulletin(w.state)
        self.assertEqual(data['achievement'],'Congratulations !!');self.assertIn(data['achievement'],w.text)
        self.assertEqual({k:data[k] for k in ('left','middle','right')},views.bulletin(w.state))
        self.assertEqual(c.m.snapshot(),snap)

    def test_original_no_key_finishes_sixteen_polls_then_keeps_the_untimed_wait(self):
        from goal2.core import screens
        c=entered();keys=list(c.keys)
        c.release()
        self.assertEqual((c.wait.kind,c.wait.site,c.wait.poll),(KIND,'000E:05EC',True))
        self.assertEqual(dict(c.wait.polls)['000E:0515'],15)  # first poll was the preceding explicit wait
        self.assertEqual(c.keys,keys)
        # Independent old host-I/O classification: the already supported title
        # poll supplies no key. The original16-loop body/speaker/RNG runs unchanged.
        oracle=before();identify=screens.identify
        with patch.object(screens,'identify',side_effect=lambda site,frame: 'title-tune' if site=='000E:0515' else identify(site,frame)):
            oracle.press(13)
        self.assertEqual(dict(oracle.wait.polls)['000E:0515'],16)
        self.assertEqual(c.m.snapshot(),oracle.m.snapshot());self.assertEqual(c.keys,oracle.keys)
        c.advance();self.assertEqual(c.wait.site,'000E:05EC')
        c.release();self.assertEqual(c.wait.site,'000E:05EC')
        self.assertEqual(c.keys,keys)

    def test_one_early_key_and_saved_replay_return_to_management_without_a_second_read(self):
        from goal2.core import Core,screens
        from goal2.core.driver import Driver
        for main_wait in (False,True):
            with self.subTest(main_wait=main_wait):
                c=entered()
                if main_wait:c.release()
                saved=c.save();r=Core.load(saved,goal_dat=requires.CACHE/'GOAL.DAT')
                n=len(c.keys);d=Driver(c);d.round_continue();r.press(13)
                self.assertEqual(c.wait.kind,'manager-menu');self.assertEqual(c.wait.site,'000E:75D1')
                self.assertEqual(c.m.snapshot(),r.m.snapshot());self.assertEqual(c.keys,r.keys)
                self.assertEqual(len(c.keys),n+1);self.assertIsNone(c.pending)
                self.assertEqual(d.log,[(KIND,13)])
        c=before();c.queue(KIND,ord('n'));c.press(13)
        self.assertEqual(c.wait.kind,'manager-menu')
        self.assertEqual(dict(c.wait.polls)['000E:0515'],1)
        self.assertEqual([k for p in c.wait.passed for k in p.keys],[ord('n')])
        oracle=before();identify=screens.identify
        with patch.object(screens,'identify',side_effect=lambda site,frame: 'title-tune' if site in ('000E:0515','000E:05EC') else identify(site,frame)):
            oracle.queue('title-tune',ord('n'));oracle.press(13)
        self.assertEqual(c.m.snapshot(),oracle.m.snapshot());self.assertEqual(c.keys,oracle.keys)

    def test_unknown_callers_links_modes_and_other_flags_remain_refused(self):
        from goal2.core import screens
        c=entered();f=c._frame();p=f.up(f.bp);root=f.up(p)
        near,word,byte=f.near_caller,f.word,f.byte
        self.assertEqual(screens.identify('000E:0515',f),KIND)
        for target,value in ((f.bp,0x5C7),(p,0x625),(root,0x4F72)):
            with patch.object(f,'near_caller',side_effect=lambda bp,t=target,v=value: v if bp==t else near(bp)):
                self.assertIsNone(screens.identify('000E:0515',f))
        with patch.object(f,'word',side_effect=lambda bp,off:p+2 if (bp,off)==(f.bp,4) else word(bp,off)):
            self.assertIsNone(screens.identify('000E:0515',f))
        for bp,off,val in ((f.bp,6,4),(root,4,1),(root,6,1),(root,8,0)):
            with patch.object(f,'byte',side_effect=lambda b,o,t=(bp,off),v=val: v if (b,o)==t else byte(b,o)):
                self.assertIsNone(screens.identify('000E:0515',f))
        with patch.object(f,'word',side_effect=lambda bp,off:word(bp,off)|0x1200 if (bp,off) in ((f.bp,6),(root,4),(root,6),(root,8)) else word(bp,off)):
            self.assertEqual(screens.identify('000E:0515',f),KIND,'high scratch bytes are not boolean flags')


@requires.need(**{**NEEDS,'modules':('unicorn','PySide6')})
class Desktop(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from PySide6.QtWidgets import QApplication
        from goal2.desktop.style import load_fonts
        cls.app=QApplication.instance() or QApplication([]);load_fonts()

    def test_actual_partial_resume_save_guards_caption_columns_bounds_and_continue(self):
        from concurrent.futures import Future
        from PySide6.QtCore import Qt
        from PySide6.QtTest import QTest
        from goal2.core import Core
        from goal2.desktop.core_model import CoreModel
        from goal2.desktop.core_window import CoreWindow
        from goal2.desktop.fixed_page import problems
        with tempfile.TemporaryDirectory() as folder:
            model=CoreModel(entered(),requires.CACHE/'GOAL.DAT',Path(folder)/'partial.g2core')
            w=CoreWindow(model);w.show();w.activateWindow();self.app.processEvents();w.finish_core()
            try:
                r=w.core_round;data=model.round_state()['bulletin']
                self.assertEqual(r.page_next.text(),'Continue (Enter)')
                self.assertEqual(r.bulletin_columns.achievement.text(),'Congratulations !!')
                self.assertTrue(r.bulletin_columns.achievement.isVisible())
                for name in ('left','middle','right'):
                    head,story=r.bulletin_columns.panels[name]
                    self.assertTrue(head.isVisible());self.assertTrue(story.isVisible())
                    self.assertEqual(head.text(),data[name]['masthead']);self.assertEqual(story.text().splitlines(),data[name]['lines'])
                self.assertTrue(model.in_round);self.assertFalse(w.begin_save_name())
                self.assertFalse(w.core_routes['play next game'].isEnabled())
                self.assertFalse(w.core_team_buttons['reposition'].isEnabled())
                snap=model.core.m.snapshot();w.core_jobs.future=Future()
                self.assertFalse(w.save_core());self.assertFalse(w.run_core('round_continue'))
                r.next_page();self.assertEqual(model.core.m.snapshot(),snap)
                w.core_jobs.future=None;self.assertTrue(w.save_core())
                self.assertEqual(Core.load(model.save_path.read_bytes()).m.snapshot(),snap)
                if os.environ.get('QT_SCALE_FACTOR'):self.assertEqual(w.devicePixelRatioF(),float(os.environ['QT_SCALE_FACTOR']))
                for size in ((1440,900),(1050,780),(900,640),(2560,1600)):
                    w.resize(*size);self.app.processEvents();self.assertEqual(problems(w),[])
                    page=w.pages[3];need=page.minimumSizeHint()
                    self.assertLessEqual(need.width(),.9*page.width());self.assertLessEqual(need.height(),.9*page.height())
                QTest.keyClick(r.page_next,Qt.Key.Key_Return);w.finish_core();self.app.processEvents()
                self.assertEqual(model.core.wait.kind,'manager-menu');self.assertFalse(model.in_round)
            finally:
                w.core_jobs.future=None;w.close();self.app.processEvents()
