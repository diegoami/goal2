"""[designed: T116] Owner-default Watch and equivalent complete-pose stepping without redundant copies."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from goal2.tests import requires
from goal2.tests.test_core_watch_t109 import live, NEEDS


def raw_pose(driver):
    driver.live_step()
    while driver.wait.kind=='match-live' and driver.wait.view.get('slot') not in (22,None):
        driver.live_step()
    return driver.wait


@requires.need(**NEEDS)
class Pose(unittest.TestCase):
    def test_complete_pose_is_identical_without_materializing_intermediate_polls(self):
        from goal2.core import Core, views
        from goal2.core.driver import Driver
        original=live();other=Driver(Core.load(original.core.save()))
        raw_pose(original)
        from goal2.core.runner import decode_text
        with patch.object(other.core,'_make_wait',wraps=other.core._make_wait) as make, \
                patch('goal2.core.runner.decode_text',wraps=decode_text) as decode:
            with other.core.live_frames():other.live_step()
        self.assertEqual(make.call_count,1)
        self.assertLessEqual(decode.call_count,2)
        self.assertEqual(other.wait.view['slot'],22)
        self.assertEqual(other.core.memory_sha256(),original.core.memory_sha256())
        self.assertEqual(other.core.keys,original.core.keys)
        with patch('goal2.engine.original_match.image.Image.from_memory_component',side_effect=AssertionError('copied image')):
            actual=views.pitch(other.wait.state,0,0)
            commentary=views.commentary(other.wait.state)
        self.assertEqual(actual,views.pitch(original.wait.state,0,0))
        self.assertEqual(commentary,views.commentary(original.wait.state))
        self.assertTrue(other.wait.state._image.memory.readonly)
        self.assertIs(other.wait.state._image.memory.obj,other.wait.state._component)
        before=other.wait.state.memory_component();image=other.wait.state._image
        with other.core.live_frames():other.live_step()
        self.assertEqual(image.memory_component(),before)
        self.assertNotEqual(other.core.memory_component(),before)


@requires.need(**NEEDS,slow=True)
class Decisions(unittest.TestCase):
    def test_new_watched_kickoff_uses_original_right_before_its_first_complete_pose(self):
        from goal2.core import Core, views
        from goal2.core.driver import Driver, RIGHT
        from goal2.desktop.core_model import CoreModel
        d=Driver(Core.start((requires.CACHE/'e006-r0001-main.sav').read_bytes()).core)
        d.to_menu();d.round_start(watch=True);other=Driver(Core.load(d.core.save()))
        m=CoreModel(d.core,None,Path(tempfile.gettempdir())/'unused-t116.g2core')
        poses=[];make=d.core._make_wait
        def kept(*a,**kw):
            w=make(*a,**kw)
            if w.kind=='match-live':poses.append(w.view['slot'])
            return w
        with patch.object(d.core,'_make_wait',side_effect=kept):state=m.round_step('kick_off',None,True)
        self.assertEqual(poses,[22]);self.assertEqual(state['speed'],0)
        # Raw poll API, same queued original key; Core.keys records direct presses, while queued reads
        # are recorded on PassedScreen.keys (the existing core input-log contract).
        other.core.queue('match-live',RIGHT);other.kick_off(watch=True)
        self.assertEqual(views.match_speed(other.wait.state),0)
        while other.wait.kind=='match-live' and other.wait.view.get('slot')!=22:other.live_step()
        self.assertEqual(d.core.memory_sha256(),other.core.memory_sha256())
        self.assertEqual(d.core.keys,other.core.keys)
        self.assertIn(RIGHT,[key for page in d.core.wait.passed if page.kind=='match-live' for key in page.keys])

    def test_original_speed_limits_and_saved_speed_are_retained(self):
        from goal2.core import Core, views
        from goal2.core.driver import LEFT, RIGHT
        from goal2.desktop.core_model import CoreModel
        m=CoreModel(live().core,None,Path(tempfile.gettempdir())/'unused-t116.g2core')
        for _ in range(6):m.round_step('live_step',LEFT)
        self.assertEqual(views.match_speed(m.state),5)
        m=CoreModel(Core.load(m.core.save()),None,m.save_path)
        self.assertEqual(views.match_speed(m.state),5)
        for _ in range(6):m.round_step('live_step',RIGHT)
        self.assertEqual(views.match_speed(m.state),0)

    def test_enter_and_queued_enter_stop_before_the_next_pose_and_replay_exactly(self):
        from goal2.core import Core
        from goal2.core.driver import Driver
        start=live().core.save()
        for queued in (False,True):
            a,b=(Driver(Core.load(start)) for _ in range(2))
            for d in (a,b):
                if queued:d.core.queue('match-live',13)
            a.live_step(None if queued else 13)
            with b.core.live_frames():b.live_step(None if queued else 13)
            self.assertEqual(b.wait.kind,'match-menu');self.assertEqual(b.wait.view['context'],'pause')
            self.assertEqual(a.core.memory_sha256(),b.core.memory_sha256());self.assertEqual(a.core.keys,b.core.keys)
            self.assertFalse(b.core._live_frames)
        a,b=(Driver(Core.load(start)) for _ in range(2))
        for _ in range(4):
            raw_pose(a)
            with b.core.live_frames():b.live_step()
            self.assertEqual(a.core.memory_sha256(),b.core.memory_sha256())
            b=Driver(Core.load(b.core.save()))
        self.assertEqual(a.core.keys,b.core.keys)


@requires.need(**dict(NEEDS,modules=('unicorn','PySide6','pygame')),slow=True)
class Desktop(unittest.TestCase):
    def test_missing_input_history_stops_the_viewer_without_advancing_the_core(self):
        import json,sys
        from PySide6.QtWidgets import QApplication
        from goal2.desktop.core_model import CoreModel
        from goal2.desktop.core_window import CoreWindow
        from goal2.desktop.core_viewer import CoreViewer
        from goal2.desktop.pygame_viewer import frame_digest
        app=QApplication.instance() or QApplication([])
        with tempfile.TemporaryDirectory() as folder:
            m=CoreModel(live().core,None,Path(folder)/'game.g2core');w=CoreWindow(m)
            r=w.core_round;r.watch_suspended=True;w.show();app.processEvents();w.finish_core()
            try:
                state=m.round_step('live_step')
                v=r.viewer=CoreViewer(state['identity'],command=[sys.executable,'-c','import time;time.sleep(60)'])
                r.watch_suspended=False;r.finished('live_step',('done',state));frame=v.display.frames[-1]
                status=dict(token=v.token,kind='ready',sequence=v.display.sequence,digest=v.display.digest(),
                            frame_sequence=frame['sequence'],frame_digest=frame_digest(frame),controls=[[2,'right']])
                (v.directory/'status').write_text(json.dumps(status))
                before=m.memory_sha256();r.poll_viewer()
                self.assertIsNone(r.viewer);self.assertTrue(r.watch_suspended)
                self.assertIn('input history overflow',r.live_note.text())
                self.assertEqual(m.memory_sha256(),before);self.assertFalse(w.core_jobs.busy)
            finally:w.close();app.processEvents()

    def test_real_sdl_arrows_and_enter_reach_the_original_in_order(self):
        import sys,time
        from PySide6.QtWidgets import QApplication
        from goal2.desktop.core_model import CoreModel
        from goal2.desktop.core_window import CoreWindow
        from goal2.desktop.core_viewer import CoreViewer
        from goal2.core.driver import LEFT, RIGHT
        app=QApplication.instance() or QApplication([])
        with tempfile.TemporaryDirectory() as folder:
            m=CoreModel(live().core,None,Path(folder)/'game.g2core')
            w=CoreWindow(m);w.core_round.watch_suspended=True;w.show();app.processEvents();w.finish_core()
            try:
                state=m.round_step('live_step');r=w.core_round
                script=("import pygame,sys;from goal2.desktop import pygame_viewer as v;old=v.status;sent=[False];"
                        "exec(\"def write(p,x):\\n old(p,x)\\n if x.get('frame_sequence',-1)>=0 and not sent[0]:"
                        "\\n  sent[0]=True\\n  for key in (pygame.K_RIGHT,pygame.K_LEFT,pygame.K_RETURN):"
                        "pygame.event.post(pygame.event.Event(pygame.KEYDOWN,key=key))\");v.status=write;sys.exit(v.main())")
                r.viewer=CoreViewer(state['identity'],command=[sys.executable,'-c',script])
                r.watch_suspended=False;r.finished('live_step',('done',state))
                end=time.monotonic()+20
                while time.monotonic()<end:
                    app.processEvents()
                    if not w.core_jobs.busy and m.core.wait.view.get('context')=='pause':break
                    time.sleep(.005)
                self.assertEqual(m.core.wait.view.get('context'),'pause',w.status.text())
                self.assertEqual(m.core.keys[-3:],[RIGHT,LEFT,13])
                self.assertEqual(r.viewer.speed,1)
                self.assertEqual(r.viewer.display.speed_name(),'Fast')
            finally:w.close();app.processEvents()

    def test_watch_defaults_on_and_live_jobs_leave_hidden_management_pages_alone(self):
        from PySide6.QtWidgets import QApplication
        from goal2.desktop.core_model import CoreModel
        from goal2.desktop.core_window import CoreWindow
        app=QApplication.instance() or QApplication([])
        with tempfile.TemporaryDirectory() as folder:
            m=CoreModel(live().core,requires.CACHE/'GOAL.DAT',Path(folder)/'game.g2core')
            w=CoreWindow(m);w.core_round.watch_suspended=True;w.show();app.processEvents();w.finish_core()
            try:
                self.assertTrue(w.core_round.watch.isChecked())
                w.core_round.watch.click();self.assertFalse(w.core_round.watch.isChecked())
                with patch.object(w,'refresh',wraps=w.refresh) as refresh:
                    w.run_core('live_step');self.assertEqual(w.finish_core()[0],'done')
                    self.assertEqual(refresh.call_count,0)
                    w.run_core('live_step',13);self.assertEqual(w.finish_core()[0],'done')
                    self.assertEqual(m.round_state()['stop'],'pause');self.assertEqual(refresh.call_count,1)
            finally:w.close();app.processEvents()


if __name__=='__main__':unittest.main()
