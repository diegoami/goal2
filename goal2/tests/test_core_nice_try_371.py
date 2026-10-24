"""[confirmed: T88, archaeology9aa9f27c] Original sent-off substitution refusal, without guest edits."""
import hashlib
import os
from pathlib import Path
import tempfile
import unittest
from goal2.tests import requires

NAME='t88-eeea2f27f96f4812-before-nice-try.g2core'
SHA='eeea2f27f96f481248f2fb2377990e7923f6b2fc7e80422ef8d6e5ddcfb20e8f'
SOURCE='g13-fc5b0f392a66334c-stoppage-positions.g2core'
SOURCE_SHA='fc5b0f392a66334c3395605d0113d56f67788c7b4a7b4b176364fb028ce119e2'
NEEDS=dict(modules=('unicorn',),files=(NAME,SOURCE,'GOAL.DAT'))

def loaded(name=NAME):
    from goal2.core import Core
    raw=(requires.CACHE/name).read_bytes()
    assert hashlib.sha256(raw).hexdigest()==(SHA if name==NAME else SOURCE_SHA)
    return Core.load(raw,goal_dat=requires.CACHE/'GOAL.DAT')

def selection(c):
    from goal2.core import views
    b=views.bench(c.wait.state)
    return {k:b[k] for k in ('eleven','bench','left')}

@requires.need(**NEEDS)
class Recovery(unittest.TestCase):
    def test_actual_warning_replays_and_returns_to_the_same_bench(self):
        from goal2.core import Core,views
        c=loaded();before=selection(c)
        self.assertEqual(c.wait.kind,'squad-substitution-put-on')
        self.assertEqual(c.wait.view['marked'],11)
        self.assertEqual(c.wait.view['player'],132)
        w=c.press(13)
        self.assertEqual(w.kind,'substitution-refused')
        self.assertEqual(w.site,'214B:098A')
        self.assertEqual(w.view['message'],'Nice try')
        f=c._frame();box=f.up(f.up(f.bp))
        self.assertEqual(f.far_caller(f.bp),'214B:054E')
        self.assertEqual(f.far_caller(f.up(f.bp)),'214B:1793')
        self.assertEqual(f.far_caller(box),'0791:E19F')
        self.assertEqual(views.player_card(w.state,125)['status'],0x20)
        self.assertEqual(views.player_card(w.state,132)['status'],0)
        self.assertEqual(selection(c),before)
        blob=c.save();other=Core.load(blob,goal_dat=requires.CACHE/'GOAL.DAT')
        for key,kind in ((13,'squad-substitution-put-on'),(27,'match-menu')):
            self.assertEqual(c.press(key).kind,kind)
            self.assertEqual(other.press(key).kind,kind)
            self.assertEqual(other.memory_sha256(),c.memory_sha256())
            self.assertEqual(other.keys,c.keys)
            if key==13:self.assertIsNone(c.wait.view['marked'])
            self.assertEqual(selection(c),before)
        self.assertIsNone(c.stopped)
        self.assertEqual(c.wait.view['context'],'stoppage')

    def test_driver_passes_the_real_pair_and_preserves_the_original_refusal(self):
        from goal2.core.driver import Driver
        c=loaded(SOURCE);d=Driver(c);before=selection(c)
        result=d.substitute(125,132)
        self.assertFalse(result['made']);self.assertEqual(result['refused'],'Nice try')
        self.assertEqual(selection(c),before);self.assertEqual(c.wait.kind,'match-menu')
        self.assertTrue(any(kind=='substitution-refused' for kind,key in d.log))
        # Replay the exact original keys directly, including the warning dismissal and bench Esc.
        direct=loaded(SOURCE)
        for _,key in d.log:direct.press(key)
        self.assertEqual(direct.memory_sha256(),c.memory_sha256())
        self.assertEqual(direct.keys,c.keys)

@requires.need(**(NEEDS|{'modules':('unicorn','PySide6')}),slow=True)
class Desktop(unittest.TestCase):
    def test_worker_reports_refusal_and_keeps_the_round_playable(self):
        os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
        from PySide6.QtWidgets import QApplication
        from goal2.desktop.core_model import CoreModel
        from goal2.desktop.core_window import CoreWindow
        from goal2.desktop.style import load_fonts
        app=QApplication.instance() or QApplication([]);load_fonts()
        with tempfile.TemporaryDirectory() as folder:
            c=loaded(SOURCE);before=selection(c)
            model=CoreModel(c,requires.CACHE/'GOAL.DAT',Path(folder)/'refused.g2core')
            w=CoreWindow(model);w.show();app.processEvents();w.finish_core()
            try:
                w.run_core('substitute',125,132)
                self.assertTrue(w.core_jobs.busy)
                self.assertFalse(w.save_core())
                w.finish_core();app.processEvents()
                self.assertIn('Nice try',w.core_round.bench.message_label.text())
                self.assertEqual(selection(c),before);self.assertTrue(model.in_round)
                self.assertTrue(w.save_core())
                resumed=CoreModel.from_save(model.save_path,requires.CACHE/'GOAL.DAT')
                self.assertEqual(resumed.memory_sha256(),model.memory_sha256())
                w.run_core('play_on');w.finish_core();app.processEvents()
                self.assertIsNone(c.stopped)
            finally:w.close();app.processEvents()

if __name__=='__main__':unittest.main()
