"""[designed: #363] Real injury walk-off service, original flags and completed-pose continuation."""
import hashlib
import os
from pathlib import Path
import tempfile
import time
import unittest
from goal2.tests import requires

NAME='g13-ecc7c9f3df3f5092-g4c-before-injury.g2core'
SHA='ecc7c9f3df3f5092254e4583864f3a345ecbe600f2af30601d8dc5f79f80b79c'
NEEDS=dict(modules=('unicorn',),files=(NAME,'GOAL.DAT'))

def loaded():
    from goal2.core import Core
    from goal2.core.driver import Driver
    raw=(requires.CACHE/NAME).read_bytes();assert hashlib.sha256(raw).hexdigest()==SHA
    return Driver(Core.load(raw,goal_dat=requires.CACHE/'GOAL.DAT'))

@requires.need(**NEEDS)
class Progress(unittest.TestCase):
    def test_real_injury_passes_the_animation_without_an_unknown_or_manager_pause(self):
        d=loaded()
        with d.core.live_frames():
            for _ in range(50):
                d.live_step()
                passed=[p for p in d.wait.passed if p.kind=='match-walkoff']
                if passed:break
            else:self.fail('The genuine injury was not reached within50 complete poses')
        self.assertIsNone(d.core.stopped)
        self.assertIn(d.wait.kind,('match-live','substitution-notice'))
        self.assertGreater(passed[0].polls,0)
        self.assertEqual(passed[0].keys,())

@requires.need(**NEEDS,slow=True)
class Protocol(unittest.TestCase):
    def test_clock_flags_and_saved_no_key_replay_match_the_original_return(self):
        from goal2.core import Core,views
        d=loaded();c=d.core;c.stop_at(*c.stops,'match-walkoff')
        with c.live_frames():
            for _ in range(50):
                if c.wait.kind=='match-walkoff':break
                c.advance()
            else:self.fail('Walk-off poll was not reached')
        self.assertEqual(c.wait.site,'0791:78F9');self.assertTrue(c.wait.poll)
        f=c._frame();old=(f.byte(f.bp,-3),f.byte(f.bp,-4))
        before_minute=views.Memory(c.wait.state).ds_word(0x831F)
        self.assertEqual((views.Memory(c.wait.state).ds_byte(0x8325),views.Memory(c.wait.state).ds_byte(0x9B41)),(0,0))
        c.advance();self.assertEqual(c.wait.kind,'match-walkoff')
        self.assertEqual(views.Memory(c.wait.state).ds_word(0x831F),before_minute)
        saved=c.save();replay=Core.load(saved,goal_dat=requires.CACHE/'GOAL.DAT')
        observed=[]
        # Read-only original return observer; it neither stops nor changes the guest.
        c.m.at('0791:7987',lambda again: observed.append((c.m.rd(0x8325,1),c.m.rd(0x9B41,1))))
        with c.live_frames():c.release()
        with replay.live_frames():replay.release()
        self.assertEqual(observed,[old])
        self.assertEqual(c.memory_sha256(),replay.memory_sha256())
        self.assertEqual(c.keys,replay.keys)

    def test_an_explicit_animation_key_is_consumed_by_the_original_flush_read(self):
        d=loaded();d.core.queue('match-walkoff','x')
        with d.core.live_frames():
            for _ in range(50):
                d.live_step()
                events=[p for p in d.wait.passed if p.kind=='match-walkoff']
                if events:break
            else:self.fail('Walk-off key was not consumed')
        self.assertEqual(events[0].keys,(ord('x'),))
        self.assertFalse(d.core.queued);self.assertIsNone(d.core.pending)
        self.assertIsNone(d.core.stopped)

@requires.need(**(NEEDS|{'modules':('unicorn','PySide6','pygame')}),slow=True)
class Desktop(unittest.TestCase):
    def test_the_real_viewer_crosses_the_injury_and_keeps_a_resumable_wait(self):
        os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
        from PySide6.QtWidgets import QApplication
        from goal2.desktop.style import load_fonts
        from goal2.desktop.core_model import CoreModel
        from goal2.desktop.core_window import CoreWindow
        app=QApplication.instance() or QApplication([]);load_fonts();d=loaded()
        with tempfile.TemporaryDirectory() as folder:
            model=CoreModel(d.core,requires.CACHE/'GOAL.DAT',Path(folder)/'game.g2core')
            w=CoreWindow(model);w.show();app.processEvents();w.finish_core()
            try:
                deadline=time.monotonic()+60
                while time.monotonic()<deadline:
                    app.processEvents();self.assertIsNone(model.core.stopped)
                    if not w.core_jobs.busy and model.core._polls.get('0791:78F9',0):break
                    time.sleep(.002)
                else:self.fail('The viewer did not cross the injury within60seconds')
                w.core_round.watch_suspended=True;w.core_round.viewer_timer.stop();w.finish_core()
                self.assertIn(model.core.wait.kind,('match-live','substitution-notice','match-menu'))
                self.assertTrue(w.save_core())
                resumed=CoreModel.from_save(model.save_path,requires.CACHE/'GOAL.DAT')
                self.assertEqual(resumed.memory_sha256(),model.memory_sha256())
            finally:w.close();app.processEvents()

if __name__=='__main__':unittest.main()
