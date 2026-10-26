"""[designed: owner #430/T138] Focus the owned pitch without original-key input."""
import os
from pathlib import Path
import sys
import time
import unittest
from unittest.mock import patch

from goal2.tests import requires


class Protocol(unittest.TestCase):
    def test_focus_requests_leave_pitch_frames_events_and_controls_alone(self):
        from goal2.desktop.match_view import Display
        display=Display('token')
        display.accept(['token',0,'start',['HOME','AWAY']])
        display.accept(['token',1,'pitch',{'rate':60}])
        before=(list(display.frames),display.frame,display.frame_sequence,list(display.events),display.consumed)
        display.accept(['token',2,'focus',1])
        self.assertEqual(display.focus_requests,1)
        display.accept(['token',3,'focus',2])
        self.assertEqual(display.focus_requests,2)
        self.assertEqual((list(display.frames),display.frame,display.frame_sequence,list(display.events),display.consumed),before)
        for value in (True,0,2,4,'3'):
            with self.assertRaises(ValueError):display.accept(['token',4,'focus',value])


@requires.need(modules=('pygame',))
class OwnedViewer(unittest.TestCase):
    def test_denied_focus_keeps_the_display_alive_and_does_not_restore_a_visible_window(self):
        from types import SimpleNamespace
        from unittest.mock import Mock
        from goal2.desktop.pygame_viewer import focus_display
        class Denied(Exception):pass
        window=SimpleNamespace(focus=Mock(side_effect=Denied('denied')),restore=Mock())
        pygame=SimpleNamespace(Window=SimpleNamespace(from_display_module=lambda:window),
                               display=SimpleNamespace(get_active=lambda:True),error=Denied)
        self.assertFalse(focus_display(pygame))
        window.restore.assert_not_called()
        window.focus.side_effect=None
        pygame.display.get_active=lambda:False
        self.assertTrue(focus_display(pygame));window.restore.assert_called_once()

    def test_focus_status_is_bounded_and_does_not_become_original_input(self):
        import json
        from goal2.desktop.core_viewer import CoreViewer
        viewer=CoreViewer(['HOME','AWAY'],command=[sys.executable,'-c','import time;time.sleep(30)'])
        self.addCleanup(viewer.close);viewer.show_window()
        value={'token':viewer.token,'kind':'ready','sequence':viewer.display.sequence,
               'digest':viewer.digests[viewer.display.sequence],'frame_sequence':-1,
               'controls':[],'focus_sequence':1,'focused':True}
        path=viewer.directory/'status';path.write_text(json.dumps(value))
        self.assertIsNone(viewer.poll());self.assertEqual(viewer.focus_ack,1)
        self.assertTrue(viewer.focused);self.assertEqual(list(viewer.controls),[])
        for bad in (0,2,True):
            path.write_text(json.dumps({**value,'focus_sequence':bad}))
            with self.assertRaises(ValueError):viewer.poll()
        path.write_text(json.dumps({**value,'sequence':2,'digest':viewer.digests[2]}))
        with self.assertRaises(ValueError):viewer.poll()

    def test_show_existing_owned_process_sends_no_pose_or_original_control(self):
        from goal2.desktop.core_viewer import CoreViewer
        viewer=CoreViewer(['HOME','AWAY'],command=[sys.executable,'-c','import time;time.sleep(30)'])
        self.addCleanup(viewer.close)
        pid=viewer.process.pid
        before=(viewer.display.frame_sequence,list(viewer.display.events),list(viewer.controls),viewer.requests)
        with patch('goal2.desktop.core_viewer._allow_foreground',return_value=True) as allow:
            viewer.show_window();viewer.show_window()
        self.assertEqual([c.args for c in allow.call_args_list],[(pid,),(pid,)])
        self.assertEqual(viewer.process.pid,pid)
        self.assertEqual(viewer.display.focus_requests,2)
        self.assertEqual((viewer.display.frame_sequence,list(viewer.display.events),list(viewer.controls),viewer.requests),before)
        self.assertEqual(viewer.display.sequence,4)
        viewer.process.terminate();viewer.process.wait(timeout=5)
        with self.assertRaises(ValueError):viewer.show_window()


@requires.need(modules=('unicorn','PySide6','pygame'),files=('e006-r0001-main.sav','GOAL.DAT'))
class Navigation(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from PySide6.QtWidgets import QApplication
        cls.app=QApplication.instance() or QApplication([])

    def window(self,live=False):
        from goal2.desktop.core_window import CoreWindow
        if live:
            from goal2.tests.test_core_watch_t109 import live as original_live
            from goal2.desktop.core_model import CoreModel
            model=CoreModel(original_live().core,requires.CACHE/'GOAL.DAT',requires.CACHE/'unused-window.g2core')
        else:
            from goal2.tests.test_core_team_t107 import model as initial
            model=initial()
        window=CoreWindow(model);window.core_round.watch_suspended=True
        self.addCleanup(window.close)
        window.show();self.app.processEvents();window.core_round.viewer_timer.stop()
        window.navigate(3)
        return window

    def test_no_match_is_disabled_and_suspended_live_match_has_an_explicit_resume(self):
        window=self.window()
        self.assertFalse(window.core_show_match.isEnabled())
        self.assertIn('no match',window.core_show_match.toolTip().lower())
        window.close()
        window=self.window(live=True)
        self.assertTrue(window.core_show_match.isEnabled())
        self.assertIn('RESUME',window.core_show_match.text())
        self.assertEqual(window.core_show_match.shortcut().toString(),'F8')

    def test_prominent_action_survives_all_fixture_views_and_busy_game_controls(self):
        from goal2.desktop.core_viewer import CoreViewer
        from goal2.desktop.fixed_page import scale_of
        from PySide6.QtCore import Qt
        from PySide6.QtTest import QTest
        window=self.window(live=True);round_view=window.core_round
        viewer=CoreViewer(round_view.state['identity'],command=[sys.executable,'-c','import time;time.sleep(30)'])
        round_view.viewer=viewer;round_view.watch_suspended=False
        before=window.model.core.save();pid=viewer.process.pid
        for index in (0,1,2):
            window.fixture_views.setCurrentIndex(index);window.refresh_round_controls();self.app.processEvents()
            self.assertTrue(window.core_show_match.isVisible())
            self.assertTrue(window.core_show_match.isEnabled())
            # Controls use the existing fixed-page scale; preserve44 page pixels.
            self.assertGreaterEqual(window.core_show_match.minimumHeight(),round(44*scale_of(window.core_show_match)))
            window.core_show_match.click()
        with patch.object(type(window.core_jobs),'busy',new_callable=lambda:property(lambda self:True)):
            window.refresh_round_controls()
            self.assertTrue(window.core_show_match.isEnabled())
            window.core_show_match.click()
        self.assertEqual(viewer.display.focus_requests,4)
        window.refresh_round_controls();window.activateWindow();self.app.processEvents()
        QTest.keyClick(window,Qt.Key.Key_F8);QTest.qWait(150);self.app.processEvents()
        self.assertEqual(viewer.display.focus_requests,5)
        self.assertEqual(viewer.process.pid,pid)
        self.assertEqual(window.model.core.save(),before)

        self.assertEqual(round_view.pending_inputs,[])
        self.assertIsNone(round_view.pending_stop)
        # A frozen decision still offers the existing pitch, without restarting the round_view.
        round_view.state={**round_view.state,'stop':'pause'};window.refresh_round_controls()
        from goal2.core.screens import LEFT
        round_view.pending_inputs=[LEFT]
        pending=('held-decision',('done',round_view.state));round_view.pending_stop=pending
        window.core_show_match.click()
        self.assertEqual(viewer.display.focus_requests,6)
        self.assertEqual(round_view.pending_inputs,[LEFT]);self.assertIs(round_view.pending_stop,pending)
        self.assertEqual(window.model.core.save(),before)

    def test_real_viewer_activation_and_minimized_restore_preserve_the_core(self):
        import json
        from goal2.desktop.core_viewer import CoreViewer
        from goal2.desktop.fixed_page import problems
        window=self.window(live=True);round_view=window.core_round
        state=window.model.round_step('live_step');round_view.state=state
        # Native hook minimizes only the SDL view; it sends no original-game input.
        script="""import pygame,sys,json
from goal2.desktop import pygame_viewer as v
original=v.status
minimized=False
def write(path,value):
 global minimized
 if value.get('frame_sequence',-1)>=0 and not minimized:
  minimized=True
  if pygame.display.get_driver()!='dummy':pygame.Window.from_display_module().minimize()
 if minimized and (pygame.display.get_driver()=='dummy' or not pygame.display.get_active()):
  path.with_name('minimized').write_text('yes')
 original(path,value)
v.status=write
sys.exit(v.main())
"""
        viewer=CoreViewer(state['identity'],command=[sys.executable,'-c',script])
        round_view.viewer=viewer;round_view.watch_suspended=False
        viewer.pose(state['pitch'],state['commentary'],state['speed'])
        before=window.model.core.save();pid=viewer.process.pid
        def pump(predicate):
            end=time.monotonic()+15
            while time.monotonic()<end:
                self.app.processEvents();viewer.poll()
                if predicate():return
                time.sleep(.01)
            self.fail(f'viewer timed out: {viewer.last_status}')
        pump(lambda:viewer.drained and (viewer.directory/'minimized').exists())
        window.raise_();window.activateWindow();self.app.processEvents()
        window.refresh_round_controls();window.core_show_match.click()
        pump(lambda:viewer.focus_ack==1)
        native=os.environ.get('SDL_VIDEODRIVER')!='dummy'
        if native:
            pump(lambda:viewer.focused)
        for count in (2,3):
            window.core_show_match.click();pump(lambda:viewer.focus_ack==count)
        self.assertEqual(viewer.process.pid,pid)
        self.assertEqual(viewer.display.frame_sequence,0)
        self.assertEqual(round_view.pending_inputs,[])
        self.assertEqual(window.model.core.save(),before)
        # Navigation must remain visible within the retained supported geometry budget.
        for width,height in ((1440,900),(1050,780),(900,640),(2560,1600)):
            window.resize(round(.9*width),round(.9*height));self.app.processEvents()
            self.assertEqual(problems(window),[],(width,height,problems(window)))
        Path('.cache/T138-window-native-'+str(window.devicePixelRatioF())+'.json').write_text(json.dumps(
            {'native':native,'focused':viewer.focused,'focus_ack':viewer.focus_ack,
             'same_pid':viewer.process.pid==pid,'guest_unchanged':window.model.core.save()==before}))

    def test_suspended_viewer_reopens_the_same_real_pose_without_kickoff_or_key(self):
        window=self.window(live=True);round_view=window.core_round
        round_view.state=window.model.round_step('live_step')
        before=window.model.core.save()
        window.refresh_round_controls();window.core_show_match.click()
        round_view.viewer_timer.stop()
        self.assertIsNotNone(round_view.viewer)
        self.assertFalse(window.core_jobs.busy)
        self.assertEqual(round_view.viewer.display.frame_sequence,0)
        self.assertEqual(round_view.viewer.display.frames[-1]['score'],round_view.state['pitch']['score'])
        self.assertEqual(window.model.core.save(),before)

    @requires.need(files=('t88-72d72b0dc1b809fe-corner-pitch-read.sav',))
    def test_reopen_on_a_genuine_taker_pitch_preserves_the_original_decision(self):
        from goal2.tests.test_core_takers_t120 import loaded
        from goal2.desktop.core_model import CoreModel
        from goal2.desktop.core_window import CoreWindow
        from goal2.desktop.fixtures_page import CoreRound
        model=CoreModel(loaded(2).core,requires.CACHE/'GOAL.DAT',requires.CACHE/'unused-focus-taker.g2core')
        with patch.object(CoreRound,'show_taker_pitch',return_value=None):
            window=CoreWindow(model);self.addCleanup(window.close)
            window.show();self.app.processEvents()
        round_view=window.core_round
        self.assertEqual(round_view.state['stop'],'taker-pitch')
        before=model.core.save();window.refresh_round_controls();window.core_show_match.click()
        round_view.viewer_timer.stop()
        self.assertIsNotNone(round_view.viewer)
        self.assertEqual(model.core.wait.kind,'set-piece-pitch')
        self.assertFalse(window.core_jobs.busy)
        self.assertEqual(round_view.viewer.display.frame_sequence,0)
        self.assertEqual(model.core.save(),before)
