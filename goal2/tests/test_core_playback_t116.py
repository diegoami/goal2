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
