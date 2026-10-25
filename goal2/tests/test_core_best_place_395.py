"""[designed: #395] Genuine G15-variant achievement wait, strict frames and exact replay.

The input is the immutable original-key capture recorded on #395, not unchanged-original #400 evidence.
Synthetic frame proxies below only test classifier refusal; no executed guest state is edited.
"""
import hashlib
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from goal2.tests import requires

INPUT = 'g13-d5ebee1ea6d80c4a-best-place-before.g2core'
SHA = 'd5ebee1ea6d80c4a2a492eb7eb30d8a931226ce91e0b2b704b5ead6dd3b4c267'
NEEDS = dict(modules=('unicorn',), files=(INPUT, 'GOAL.DAT'))


def before():
    from goal2.core import Core
    raw = (requires.CACHE / INPUT).read_bytes()
    assert hashlib.sha256(raw).hexdigest() == SHA
    return Core.load(raw, goal_dat=requires.CACHE / 'GOAL.DAT')


def achievement():
    c = before()
    c.press(13)
    return c


@requires.need(**NEEDS)
class Achievement(unittest.TestCase):
    def test_actual_machine_wait_and_original_caption_plus_all_bulletin_columns(self):
        from goal2.core import views
        c = achievement();w = c.wait
        self.assertEqual((w.site, w.kind, w.poll), ('000E:05EC', 'bulletin-achievement', True))
        self.assertIsNone(c.stopped)
        self.assertEqual(c.patches, ('owner-substitutions-v1',))
        f = c._frame();p = f.up(f.bp)
        self.assertEqual((f.bp, p), (0x3E8C, 0x3E92))
        self.assertEqual((f.near_caller(f.bp), f.word(f.bp, 4), f.near_caller(p)), (0x624, p, 0x4F72))
        self.assertEqual(tuple(f.byte(p, n) for n in (4, 6, 8)), (0, 1, 0))
        self.assertEqual(f.word(p, 8), 0x2000, 'scratch high byte is not a flag')
        snap = c.m.snapshot()
        self.assertEqual(hashlib.sha256(snap['memory']).hexdigest(),
                         'e79997633c9a0d327f65ed3398ade680105d77779599ff09eccfadc8f92ff74d')
        self.assertEqual(hashlib.sha256(json.dumps(snap['regs'], sort_keys=True).encode()).hexdigest(),
                         '11079141c8784fcb86c5aef305b1f47b085f102cb8f73e520ffeb65a8b772492')
        content = views.achievement_bulletin(w.state)
        self.assertEqual(content['achievement'], 'BEST PLACE YET  !!')
        self.assertIn(content['achievement'], w.text)
        self.assertEqual({k: content[k] for k in ('left', 'middle', 'right')}, views.bulletin(w.state))
        self.assertTrue(any(content[k]['lines'] for k in ('left', 'middle', 'right')))
        self.assertEqual(c.m.snapshot(), snap, 'presentation must be a pure read')

    def test_unrelated_caller_link_or_low_byte_flag_remains_unknown(self):
        from goal2.core import screens
        c = achievement();f = c._frame();p = f.up(f.bp)
        self.assertEqual(screens.identify('000E:05EC', f), 'bulletin-achievement')
        near, word, byte = f.near_caller, f.word, f.byte
        with patch.object(f, 'near_caller', side_effect=lambda bp: 0x625 if bp == f.bp else near(bp)):
            self.assertIsNone(screens.identify('000E:05EC', f))
        with patch.object(f, 'near_caller', side_effect=lambda bp: 0x6964 if bp == p else near(bp)):
            self.assertIsNone(screens.identify('000E:05EC', f))
        with patch.object(f, 'word', side_effect=lambda bp, off: p + 2 if (bp, off) == (f.bp, 4) else word(bp, off)):
            self.assertIsNone(screens.identify('000E:05EC', f))
        with patch.object(f, 'byte', side_effect=lambda bp, off: 0 if (bp, off) == (p, 6) else byte(bp, off)), \
             patch.object(f, 'word', side_effect=lambda bp, off: 0x100 if (bp, off) == (p, 6) else word(bp, off)):
            self.assertIsNone(screens.identify('000E:05EC', f), 'high scratch byte cannot qualify a flag')
        self.assertIsNone(screens.identify('000E:05ED', f))

    def test_partial_save_replay_and_one_original_key_return_to_management(self):
        from goal2.core import Core
        from goal2.core.driver import Driver
        c = achievement();saved = c.save();r = Core.load(saved)
        self.assertEqual(c.m.snapshot(), r.m.snapshot());self.assertEqual(r.wait.view, c.wait.view)
        self.assertTrue(r.wait.poll);self.assertEqual(c.keys, r.keys)
        n = len(c.keys)
        d = Driver(c);d.round_continue()
        r.press(13)
        self.assertEqual((c.wait.kind, c.wait.site), ('manager-menu', '000E:75D1'))
        self.assertEqual(c.m.snapshot(), r.m.snapshot());self.assertEqual(c.keys, r.keys)
        self.assertEqual(len(c.keys), n + 1);self.assertIsNone(c.pending)
        self.assertEqual(d.log, [('bulletin-achievement', 13)])
        self.assertEqual(c.m.rd(0xA976, 1), 13)

    def test_no_key_keeps_a_wait_and_driver_preserves_preceding_bracket(self):
        from goal2.core import Core
        from goal2.core.driver import Driver
        c = achievement();r = Core.load(c.save());keys = list(c.keys)
        c.advance();r.advance()
        self.assertEqual((c.wait.kind, c.wait.site, c.wait.poll), ('bulletin-achievement', '000E:05EC', True))
        self.assertEqual(c.keys, keys);self.assertEqual(c.m.snapshot(), r.m.snapshot())
        c.release()
        self.assertEqual(c.wait.kind, 'bulletin-achievement', 'an untimed poll cannot be silently released')
        self.assertEqual(c.keys, keys)
        d = Driver(before());d._pass(('manager-menu',))
        self.assertEqual(d.wait.kind, 'bulletin-achievement')
        self.assertEqual(d.pages[0][0], 'championship-bracket')
        self.assertNotIn(('bulletin-achievement', 13), d.log)
        d.round_continue();self.assertEqual(d.wait.kind, 'manager-menu')


@requires.need(**{**NEEDS, 'files': (INPUT, 'GOAL.DAT', 'g13-b2497a51f41fa52a-g4c-loaded-manager.sav')}, slow=True)
class ScriptedRound(unittest.TestCase):
    def test_full_original_key_round_dismisses_once_and_matches_captured_continuation(self):
        from goal2.core.driver import Driver
        from goal2.tests.test_core_patches_t122 import manager, PATCH
        from goal2.tests.test_core_continuation_t111 import fix_eleven
        c = manager(1);c.apply_patch(PATCH);d = Driver(c)
        d.play_round(fix_eleven=fix_eleven, on_taker=lambda d, w: 'c')
        expected = achievement();expected.press(13)
        self.assertEqual(c.wait.kind, 'manager-menu')
        self.assertEqual(c.m.snapshot(), expected.m.snapshot());self.assertEqual(c.keys, expected.keys)
        self.assertEqual(d.log.count(('bulletin-achievement', 13)), 1)


@requires.need(**{**NEEDS, 'modules': ('unicorn', 'PySide6')})
class Desktop(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from PySide6.QtWidgets import QApplication
        from goal2.desktop.style import load_fonts
        cls.app = QApplication.instance() or QApplication([]);load_fonts()

    def test_real_resume_guards_complete_bulletin_bounds_and_continue(self):
        from concurrent.futures import Future
        from PySide6.QtCore import Qt
        from PySide6.QtTest import QTest
        from goal2.core import Core
        from goal2.desktop.core_model import CoreModel
        from goal2.desktop.core_window import CoreWindow
        from goal2.desktop.fixed_page import problems
        with tempfile.TemporaryDirectory() as folder:
            model = CoreModel(achievement(), requires.CACHE/'GOAL.DAT', Path(folder)/'partial.g2core')
            w = CoreWindow(model);w.show();w.activateWindow();self.app.processEvents();w.finish_core()
            try:
                r = w.core_round;content = model.round_state()['bulletin']
                self.assertTrue(model.in_round);self.assertEqual(r.page_next.text(), 'Continue (Enter)')
                self.assertTrue(r.bulletin_columns.achievement.isVisible())
                self.assertEqual(r.bulletin_columns.achievement.text(), content['achievement'])
                for name in ('left', 'middle', 'right'):
                    head, story = r.bulletin_columns.panels[name]
                    self.assertTrue(head.isVisible());self.assertTrue(story.isVisible())
                    self.assertEqual(head.text(), content[name]['masthead'])
                    self.assertEqual(story.text().splitlines(), content[name]['lines'])
                self.assertFalse(w.core_routes['play next game'].isEnabled())
                self.assertFalse(w.core_team_buttons['reposition'].isEnabled())
                self.assertFalse(w.begin_save_name())
                snap = model.core.m.snapshot()
                w.core_jobs.future = Future()
                self.assertFalse(w.save_core());self.assertFalse(w.run_core('round_continue'))
                r.next_page();self.assertEqual(model.core.m.snapshot(), snap)
                w.core_jobs.future = None
                self.assertTrue(w.save_core())
                self.assertEqual(Core.load(model.save_path.read_bytes()).m.snapshot(), snap)
                if os.environ.get('QT_SCALE_FACTOR'):
                    self.assertEqual(w.devicePixelRatioF(), float(os.environ['QT_SCALE_FACTOR']))
                for width, height in ((1440,900), (1050,780), (900,640), (2560,1600)):
                    w.resize(width, height);self.app.processEvents()
                    self.assertEqual(problems(w), [])
                    page=w.pages[3];need=page.minimumSizeHint()
                    self.assertLessEqual(need.width(), .9*page.width())
                    self.assertLessEqual(need.height(), .9*page.height())
                QTest.keyClick(r.page_next, Qt.Key.Key_Return);w.finish_core();self.app.processEvents()
                self.assertEqual(model.core.wait.kind, 'manager-menu')
                self.assertFalse(model.in_round)
            finally:
                w.core_jobs.future = None;w.close();self.app.processEvents()
