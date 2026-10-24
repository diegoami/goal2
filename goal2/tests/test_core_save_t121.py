"""[confirmed: F030/53d7ef5; T121 original-key probes] Save decisions use real playable origins."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from goal2.tests import requires

NEEDS=dict(modules=('unicorn',),files=('e006-r0001-main.sav',))
NAME='save-game-name-entry'

def manager():
    from goal2.core import Core
    c=Core.start((requires.CACHE/'e006-r0001-main.sav').read_bytes()).core
    c.press(27)
    return c

def quitting(c):
    from goal2.core.screens import F10
    c.press(F10);c.press('y');c.press('y')
    return c

UNKNOWN_NAME = 'g13-332b2152935f2015-file-not-found.sav'
UNKNOWN_SHA = '332b2152935f201511ae0df602ecbc46722a6bad73540d023d90b927bb0f323d'

def unmapped():
    """Read-only observer of the real stopped machine, with no manufactured frames or keys."""
    import hashlib
    from goal2.core import Core, UnknownScreen
    data=(requires.CACHE/UNKNOWN_NAME).read_bytes()
    assert hashlib.sha256(data).hexdigest()==UNKNOWN_SHA
    class Observe(Core):
        latest=None
        def _run(self):
            Observe.latest=self
            return super()._run()
    try:
        Observe.start(data)
    except UnknownScreen as error:
        return Observe.latest,error
    raise AssertionError('the unrelated original caller was guessed')

@requires.need(**NEEDS)
class Saves(unittest.TestCase):
    def test_genuine_f7_cancel_and_save_are_the_exact_original_return(self):
        from goal2.core import Core
        from goal2.core.screens import F7
        from goal2.desktop.core_model import CoreModel
        with tempfile.TemporaryDirectory() as tmp:
            c=manager();c.press(F7)
            self.assertEqual(c.wait.kind,NAME);self.assertFalse(c.wait.view['quit'])
            original=Core.load(c.save());original.press(27)
            model=CoreModel(c,None,Path(tmp)/'game.g2core')
            target=model.resolve_save_name(True)
            self.assertEqual(c.wait.kind,'manager-menu')
            self.assertEqual(c.m.snapshot(),original.m.snapshot())
            replay=Core.load(target.read_bytes())
            self.assertEqual(replay.m.snapshot(),original.m.snapshot())
            self.assertEqual(replay.keys,original.keys)
            self.assertIsNone(c.quit_origin)
            c.press(F7);before=len(c.keys)
            model.resolve_save_name(False)
            self.assertEqual(len(c.keys),before+1);self.assertEqual(c.keys[-1],27)
            self.assertEqual(c.wait.kind,'manager-menu')

    def test_quit_origin_replays_exact_memory_and_keys_without_nesting(self):
        from goal2.core import Core
        from goal2.desktop.core_model import CoreModel
        with tempfile.TemporaryDirectory() as tmp:
            c=manager();snap=c.m.snapshot();keys=list(c.keys)
            quitting(c);self.assertTrue(c.wait.view['quit'])
            origin=c.quit_origin
            self.assertIsNone(Core.load(origin).quit_origin)
            saved=c.save();replay=Core.load(saved)
            self.assertEqual(replay.m.snapshot(),c.m.snapshot())
            self.assertEqual(replay.quit_origin,origin)
            self.assertEqual(Core.load(origin).m.snapshot(),snap)
            self.assertEqual(Core.load(origin).keys,keys)
            model=CoreModel(replay,None,Path(tmp)/'quit.g2core')
            live=replay.m.snapshot();target=model.resolve_save_name(True)
            self.assertEqual(target.read_bytes(),origin)
            self.assertEqual(replay.m.snapshot(),live)  # no live rewind or teardown
            self.assertEqual(Core.load(target.read_bytes()).wait.kind,'manager-menu')

    def test_cancelled_quit_clears_origin_and_an_import_without_it_is_explicit(self):
        from goal2.core import Core
        from goal2.core.screens import F10
        from goal2.desktop.core_model import CoreModel
        c=manager();c.press(F10);self.assertIsNotNone(c.quit_origin)
        c.press('n');self.assertEqual(c.wait.kind,'manager-menu');self.assertIsNone(c.quit_origin)
        quitting(c);c.quit_origin=None  # host metadata absence, not a guest state edit
        with tempfile.TemporaryDirectory() as tmp:
            model=CoreModel(Core.load(c.save()),None,Path(tmp)/'absent.g2core')
            with self.assertRaisesRegex(ValueError,'playable origin'):model.resolve_save_name(True)
            self.assertFalse(model.save_path.exists())
            live=model.core.m.snapshot();model.resolve_save_name(False)
            self.assertEqual(model.core.m.snapshot(),live);self.assertFalse(model.save_path.exists())

    def test_atomic_failure_keeps_destination_and_retry_has_a_playable_state(self):
        from goal2.desktop.core_model import CoreModel
        from goal2.core import Core
        from goal2.core.screens import F7
        for quit in (False,True):
            with self.subTest(quit=quit),tempfile.TemporaryDirectory() as tmp:
                c=manager();quitting(c) if quit else c.press(F7)
                target=Path(tmp)/'existing.g2core';target.write_bytes(b'previous')
                model=CoreModel(c,None,target)
                with patch('goal2.desktop.core_model.os.replace',side_effect=OSError('denied')):
                    with self.assertRaisesRegex(ValueError,'denied'):model.resolve_save_name(True)
                self.assertEqual(target.read_bytes(),b'previous')
                result=model.resolve_save_name(True) if quit else model.save()
                self.assertEqual(Core.load(result.read_bytes()).wait.kind,'manager-menu')

    def test_all_old_versions_load_without_a_fabricated_origin(self):
        from goal2.core import Core
        data=manager().save();n=int.from_bytes(data[4:8],'little');header=json.loads(data[8:8+n])
        for version in (1,2,3):
            state=dict(header,version=version);state.pop('quit_origin',None)
            if version == 1:
                state.pop('dos_time',None);state.pop('date',None)
            if version < 3:
                for field in ('at_poll','stops','released'):
                    state.pop(field,None)
            blob=json.dumps(state).encode();old=data[:4]+len(blob).to_bytes(4,'little')+blob+data[8+n:]
            c=Core.load(old);self.assertEqual(c.wait.kind,'manager-menu');self.assertIsNone(c.quit_origin)

    def test_context_qualification_rejects_load_mode_and_wrong_origin_without_execution(self):
        from goal2.core import screens
        c=manager();c.press(screens.F7);f=c._frame();bp=f.up(f.bp)
        self.assertEqual(screens._save_context(f,bp),'save')
        # Synthetic pure-classifier controls; none is executed as an original input.
        from copy import copy
        frame=copy(f);word=f.word
        opened=f.up(f.up(bp))
        frame.word=lambda b,o:1 if (b,o)==(opened,6) else word(b,o)
        self.assertIsNone(screens._save_context(frame,bp))
        frame=copy(f);far=f.far_caller
        origin=f.up(opened)
        frame.far_caller=lambda b:'000E:0000' if b==origin else far(b)
        self.assertIsNone(screens._save_context(frame,bp))

    def test_saved_origin_rejects_nesting_and_nonplayable_waits(self):
        from goal2.core import Core
        from goal2.core.screens import F7
        c=manager();quitting(c);nested=c.save()
        c.quit_origin=nested
        with self.assertRaisesRegex(ValueError,'another origin'):Core.load(c.save())
        other=manager();other.press(F7);c.quit_origin=other.save()
        with self.assertRaisesRegex(ValueError,'playable manager'):Core.load(c.save())


@requires.need(**NEEDS,slow=True)
@requires.need(modules=('PySide6',))
class Desktop(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from PySide6.QtWidgets import QApplication
        from goal2.desktop.style import load_fonts
        cls.app=QApplication.instance() or QApplication([])
        load_fonts()

    def test_real_save_cancel_close_atomic_retry_guards_and_bounds(self):
        from PySide6.QtCore import Qt
        from PySide6.QtTest import QTest
        from goal2.core import Core
        from goal2.core.screens import F7
        from goal2.desktop.core_model import CoreModel
        from goal2.desktop.core_window import CoreWindow
        from goal2.desktop.fixed_page import problems
        for quit in (False,True):
            with self.subTest(quit=quit),tempfile.TemporaryDirectory() as tmp:
                c=manager();quitting(c) if quit else c.press(F7)
                target=Path(tmp)/'desktop.g2core';w=CoreWindow(CoreModel(c,None,target))
                w.show();self.app.processEvents()
                self.assertEqual(w.page_stack.currentIndex(),4)
                for size in ((1440,900),(1050,780),(900,640),(2560,1600)):
                    w.resize(*size);self.app.processEvents()
                    self.assertEqual(problems(w),[])
                    page=w.pages[4];need=page.minimumSizeHint()
                    self.assertLessEqual(need.width(),.9*page.width());self.assertLessEqual(need.height(),.9*page.height())
                self.assertFalse(w.core_team_buttons['reposition'].isEnabled())
                snapshot=c.m.snapshot()
                # A pending job prevents save and cancel before any core access.
                from concurrent.futures import Future
                future=Future();w.core_jobs.future=future
                self.assertFalse(w.save_core());self.assertFalse(w.cancel_save_name())
                self.assertEqual(c.m.snapshot(),snapshot);w.core_jobs.future=None
                with patch('goal2.desktop.core_model.os.replace',side_effect=OSError('locked destination')):
                    QTest.mouseClick(w.save,Qt.MouseButton.LeftButton);self.app.processEvents()
                self.assertIn('locked destination',w.status.text());self.assertFalse(target.exists())
                QTest.mouseClick(w.save,Qt.MouseButton.LeftButton);self.app.processEvents()
                self.assertEqual(Core.load(target.read_bytes()).wait.kind,'manager-menu')
                if quit:self.assertFalse(w.isVisible())
                else:
                    self.assertEqual(c.wait.kind,'manager-menu')
                    self.assertTrue(w.core_team_buttons['reposition'].isEnabled())
                w.close();self.app.processEvents()

    def test_real_cancel_writes_nothing_and_terminal_close_keeps_actual_guest(self):
        from PySide6.QtCore import Qt
        from PySide6.QtTest import QTest
        from goal2.core.screens import F7
        from goal2.desktop.core_model import CoreModel
        from goal2.desktop.core_window import CoreWindow
        for quit in (False,True):
            with self.subTest(quit=quit),tempfile.TemporaryDirectory() as tmp:
                c=manager();quitting(c) if quit else c.press(F7)
                target=Path(tmp)/'no.g2core';w=CoreWindow(CoreModel(c,None,target))
                w.show();self.app.processEvents();snap=c.m.snapshot()
                QTest.mouseClick(w.cancel_save,Qt.MouseButton.LeftButton);self.app.processEvents()
                self.assertFalse(target.exists())
                if quit:self.assertFalse(w.isVisible());self.assertEqual(c.m.snapshot(),snap)
                else:self.assertEqual(c.wait.kind,'manager-menu')
                w.close();self.app.processEvents()

    def test_f7_keyboard_opens_original_decision_and_repeated_quit_never_nests(self):
        from PySide6.QtCore import Qt
        from PySide6.QtTest import QTest
        from goal2.desktop.core_model import CoreModel
        from goal2.desktop.core_window import CoreWindow
        with tempfile.TemporaryDirectory() as tmp:
            c=manager();w=CoreWindow(CoreModel(c,None,Path(tmp)/'keyboard.g2core'))
            w.show();w.activateWindow();self.app.processEvents()
            QTest.keyClick(w,Qt.Key.Key_F7);self.app.processEvents()
            self.assertEqual(c.wait.kind,NAME);self.assertEqual(w.page_stack.currentIndex(),4)
            QTest.mouseClick(w.cancel_save,Qt.MouseButton.LeftButton);self.app.processEvents()
            self.assertEqual(c.wait.kind,'manager-menu')
            from goal2.core.screens import F10
            for _ in range(2):
                c.press(F10);c.press('n');self.assertIsNone(c.quit_origin)
            w.close();self.app.processEvents()

    def test_f7_retains_a_real_round_and_its_busy_guard(self):
        from goal2.desktop.core_model import CoreModel
        from goal2.desktop.core_window import CoreWindow
        with tempfile.TemporaryDirectory() as tmp:
            c=manager();model=CoreModel(c,None,Path(tmp)/'round.g2core')
            model.driver.round_start()
            self.assertTrue(model.in_round)
            w=CoreWindow(model);w.show();self.app.processEvents()
            snapshot=c.m.snapshot();keys=list(c.keys)
            self.assertFalse(w.begin_save_name())
            self.assertEqual(c.m.snapshot(),snapshot);self.assertEqual(c.keys,keys)
            self.assertFalse(model.in_save_name)
            w.close();self.app.processEvents()
