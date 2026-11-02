"""[confirmed: F029/F030 at53d7ef5; designed: owner#429/T140] Genuine original-key replay."""
import os
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch
from goal2.tests import requires

NEEDS=dict(modules=('unicorn',),files=('e039-r0005-date-call.sav','GOAL.DAT'))
_PROMPT=None

def prompt():
    global _PROMPT
    from goal2.core import Core
    from goal2.desktop.core_model import CoreNewGame
    if _PROMPT is None:
        model,_=CoreNewGame(requires.CACHE/'e039-r0005-date-call.sav',requires.CACHE/'GOAL.DAT',
                           Path(tempfile.gettempdir())/'unused-t140.g2core').start(2028,16,'A Test')
        d=model.driver;d.round_start(watch=True);d.kick_off(watch=True,speed=0)
        # The baseline already classifies this real original prompt. Explicitly retaining
        # it lets the regression exercise the missing consumer without changing guest bytes.
        original_stop=d._stop
        with patch.object(d,'STOPS',tuple(dict.fromkeys(d.STOPS+('action-replay-prompt',)))), \
             patch.object(d,'_stop',lambda *k:original_stop(*k,'action-replay-prompt')):
            d.core.stops.add('action-replay-prompt')
            for _ in range(8000):
                if d.wait.kind=='action-replay-prompt':break
                with d.core.live_frames():
                    if d.wait.kind=='set-piece-select':d.taker_key('c')
                    elif d.wait.kind=='match-live':d.live_step()
                    else:raise AssertionError('Unexpected genuine stop '+d.wait.kind)
            else:raise AssertionError('Genuine career did not produce a replay question')
        _PROMPT=d.core.save()
    return Core.load(_PROMPT,goal_dat=requires.CACHE/'GOAL.DAT')

@requires.need(**NEEDS)
class Replay(unittest.TestCase):
    def driver(self):
        from goal2.core.driver import Driver
        self.assertTrue(callable(getattr(Driver,'replay',None)),'Driver lacks explicit original replay route')
        return Driver(prompt())

    def test_no_and_watch_without_saving_equal_original_keys(self):
        from goal2.core import Core
        for watch in (False,True):
            d=self.driver();other=Core.load(d.core.save(),goal_dat=requires.CACHE/'GOAL.DAT')
            with d.core.live_frames():d.replay(watch)
            other.stop_at(*d.core.stops)
            with other.live_frames():
                other.press('y' if watch else 'n')
                if watch:
                    self.assertEqual(other.wait.kind,'save-goal-prompt')
                    other.press('n')
            self.assertEqual(d.wait.kind,'match-live')
            self.assertEqual(d.core.m.snapshot(),other.m.snapshot())
            self.assertEqual(d.core.keys,other.keys)
            self.assertEqual(d.core.m.rd(0x0C20,1),int(watch))

    def test_replay_returns_to_live_without_a_second_goal(self):
        from goal2.core import views
        from goal2.desktop.core_model import CoreModel
        d=self.driver();score=views.board(d.wait.state)['score']
        m=CoreModel(d.core,requires.CACHE/'GOAL.DAT',Path(tempfile.gettempdir())/'unused-t140.g2core')
        self.assertEqual(m.round_state()['stop'],'replay')
        state=m.round_step('replay',True);self.assertTrue(state['replay'])
        for _ in range(2000):
            state=m.round_step('live_step')
            if not state['replay']:break
        else:self.fail('Original replay never ended')
        self.assertEqual(state['stop'],'live');self.assertEqual(state['pitch']['score'],score)
        self.assertEqual(score,[0,1])

    def test_save_goal_resume_and_invalid_context(self):
        from goal2.core import Core
        from goal2.core.driver import Driver,DriverError
        d=self.driver();d._stop('substitution-notice');d._press_poll('y')
        self.assertEqual(d.wait.kind,'save-goal-prompt')
        other=Driver(Core.load(d.core.save(),goal_dat=requires.CACHE/'GOAL.DAT'))
        with d.core.live_frames():d.replay(True)
        with other.core.live_frames():other.replay(True)
        self.assertEqual(d.core.m.snapshot(),other.core.m.snapshot())
        before=d.core.save()
        with self.assertRaises(DriverError):d.replay(False)
        self.assertEqual(d.core.save(),before)

    def test_old_watched_stop_configuration_retains_the_next_goal_question(self):
        d=self.driver()
        with d.core.live_frames():d.replay(False)
        d.core.stops.difference_update(('action-replay-prompt','save-goal-prompt'))
        for _ in range(3000):
            with d.core.live_frames():
                if d.wait.kind=='set-piece-select':d.taker_key('c')
                elif d.wait.kind=='match-live':d.live_step()
                else:break
        self.assertEqual(d.wait.kind,'action-replay-prompt')

@requires.need(**(NEEDS|dict(modules=('unicorn','PySide6','pygame'))))
class Desktop(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from PySide6.QtWidgets import QApplication
        cls.app=QApplication.instance() or QApplication([])

    def test_prompt_waits_for_explicit_choice_and_has_native_bounds(self):
        from goal2.desktop.core_model import CoreModel
        from goal2.desktop.core_window import CoreWindow
        from goal2.desktop.fixed_page import problems
        m=CoreModel(prompt(),requires.CACHE/'GOAL.DAT',Path(tempfile.gettempdir())/'unused-t140.g2core')
        w=CoreWindow(m);self.addCleanup(w.close);w.show();self.app.processEvents()
        r=w.core_round
        self.assertTrue(hasattr(r,'replays'),'Round has no replay choices')
        self.assertEqual(r.views.currentWidget(),r.replays.view)
        self.assertIn('without saving',r.replays.watch.text().lower())
        before=m.core.save()
        end=time.monotonic()+.15
        while time.monotonic()<end:self.app.processEvents()
        self.assertEqual(m.core.save(),before);self.assertFalse(w.core_jobs.busy)
        for width,height in ((1440,900),(1050,780),(900,640),(2560,1600)):
            w.resize(round(.9*width),round(.9*height));self.app.processEvents()
            self.assertEqual(problems(w),[],(width,height,problems(w)))
            p=w.pages[3];need=p.minimumSizeHint()
            self.assertLessEqual(need.width(),.9*p.width());self.assertLessEqual(need.height(),.9*p.height())
        with patch.object(w,'run_core',return_value=True) as run:
            r.replays.watch.click();run.assert_called_once_with('replay',True)
        self.assertEqual(m.core.save(),before)
        from PySide6.QtCore import Qt
        from PySide6.QtTest import QTest
        w.activateWindow();r.replays.watch.setFocus();self.app.processEvents()
        with patch.object(w,'run_core',return_value=True) as run:
            QTest.keyClick(r.replays.watch,Qt.Key.Key_N);self.app.processEvents()
            run.assert_called_once_with('replay',False)

    def record_closes(self, cls):
        """Every close of a pitch viewer during the test: its caller and what the viewer process wrote, for the
        failure message (the Windows runs of 2026-11-02 failed here only in CI, not when run by hand)."""
        import traceback
        closes, real = [], cls.close

        def recorded(viewer):
            output = ''
            try:
                if viewer.errors is not None:
                    viewer.errors.seek(0);output += viewer.errors.read().decode(errors='replace')[-2000:]
                if viewer.directory is not None and (viewer.directory/'status').exists():
                    output += '\nstatus: ' + (viewer.directory/'status').read_text()[:600]
            except OSError as exc:
                output += f'\n(output unreadable: {exc})'
            exited = None if viewer.process is None else viewer.process.poll()
            closes.append(f'closed={viewer.closed} exit={exited}\n' + ''.join(traceback.format_stack(limit=10))
                          + output)
            return real(viewer)
        patcher = patch.object(cls, 'close', recorded);patcher.start();self.addCleanup(patcher.stop)
        return closes

    @staticmethod
    def state_text(w, r, viewer, seen):
        """[#520] Where the replay stood when the bounded run gave up (it stalls only in the Windows CI job)."""
        rows = {'replay seen': seen, 'round stop': (r.state or {}).get('stop'),
                'round replay': (r.state or {}).get('replay'), 'watch suspended': r.watch_suspended,
                'viewer timer active': r.viewer_timer.isActive(), 'core job busy': w.core_jobs.busy,
                'pending inputs': r.pending_inputs, 'pending stop': r.pending_stop is not None,
                'viewer is r.viewer': r.viewer is viewer, 'viewer closed': viewer.closed,
                'viewer exit': None if viewer.process is None else viewer.process.poll(),
                'frames sent': viewer.display.frame_sequence, 'frames acknowledged': viewer.frame_ack,
                'drained': viewer.drained, 'viewer replaying': viewer.replaying,
                'shown replaying': getattr(viewer.display.visible(), 'replaying', None),
                'last status': viewer.last_status, 'status line': w.status.text(),
                'live note': r.live_note.text()}
        output = ''
        try:
            if viewer.errors is not None:
                viewer.errors.seek(0);output = viewer.errors.read().decode(errors='replace')[-2000:]
        except (OSError, ValueError) as exc:
            output = f'(unreadable: {exc})'
        return ('\n\nstate at the timeout:\n' + '\n'.join(f'  {k}: {v}' for k, v in rows.items())
                + '\nviewer stderr:\n' + (output or '(empty)'))

    @staticmethod
    def closes_text(closes):
        return '\n\nviewer closes during the test:\n' + ('\n---\n'.join(closes) or '(none)')

    def test_a_viewer_closed_here_is_replaced_never_written_to(self):
        """[designed: owner, 2026-11-02] A pitch viewer goal2 closed is never written to again: the next live
        stop starts a new one (four Windows runs on 2026-11-02 crashed with AttributeError in resume_viewer)."""
        from goal2.desktop.core_model import CoreModel
        from goal2.desktop.core_window import CoreWindow
        from goal2.core import views
        from goal2.desktop.core_roles import pitch_identity
        from goal2.desktop.core_viewer import CoreViewer
        m=CoreModel(prompt(),requires.CACHE/'GOAL.DAT',Path(tempfile.gettempdir())/'unused-t140.g2core')
        with patch.dict(os.environ,{'SDL_AUDIODRIVER':'dummy'}):
            w=CoreWindow(m);self.addCleanup(w.close);w.show();self.app.processEvents()
            r=w.core_round
            viewer=CoreViewer(pitch_identity(m.state,views.pitch_identity(m.state)));r.viewer=viewer
            viewer.close()
            self.assertTrue(viewer.closed);self.assertTrue(viewer.released)
            with self.assertRaisesRegex(ValueError,'closed'):viewer.decision('replay')
            r.finished('resume',('done',m.round_state()))      # the replay prompt: let go, not written to
            self.assertIsNone(r.viewer)
            r.replays.watch.click()
            self.assertEqual(w.finish_core(60)[0],'done')       # the replay's live stop: a new viewer
            r.viewer_timer.stop()
            self.assertIsNot(r.viewer,viewer);self.assertIsNotNone(r.viewer)
            self.assertFalse(r.viewer.closed);self.assertIsNone(r.viewer.process.poll())

    def test_an_exited_viewer_is_not_replaced_silently(self):
        """[designed: T109] At a live stop, a viewer whose process exited is not dropped and replaced: watching
        stops with its reason and the live wait stays resumable. (After a replay, show_match does replace it: the
        manager asked to watch, owner #430.) The process is waited for, so the check does not depend on how fast it
        exits (the first fix replaced it on Windows only, 2026-11-02)."""
        import sys
        from goal2.desktop.core_model import CoreModel
        from goal2.desktop.core_window import CoreWindow
        from goal2.desktop.core_viewer import CoreViewer
        m=CoreModel(prompt(),requires.CACHE/'GOAL.DAT',Path(tempfile.gettempdir())/'unused-t140.g2core')
        with patch.dict(os.environ,{'SDL_AUDIODRIVER':'dummy'}):
            w=CoreWindow(m);self.addCleanup(w.close);w.show();self.app.processEvents()
            r=w.core_round;r.watch_suspended=True
            r.finished('resume',('done',m.round_state()))
            r.replays.watch.click()
            self.assertEqual(w.finish_core(60)[0],'done')       # the replay, to its live stop
            state=m.round_state();self.assertEqual(state['stop'],'live')
            if r.viewer is not None:r.viewer.close();r.viewer=None
            viewer=CoreViewer(state['identity'],command=[sys.executable,'-c','raise SystemExit(1)'])
            r.viewer=viewer;viewer.process.wait(10)
            r.watch_suspended=False
            r.finished('resume',('done',state))
            end=time.monotonic()+10
            while r.viewer is not None and time.monotonic()<end:
                self.app.processEvents();time.sleep(.005)
            r.viewer_timer.stop()
            self.assertIsNone(r.viewer)
            self.assertTrue(r.watch_suspended)

    def test_native_viewer_shows_replay_then_live_in_the_same_owned_process(self):
        import json,sys
        from goal2.desktop.core_model import CoreModel
        from goal2.desktop.core_window import CoreWindow
        m=CoreModel(prompt(),requires.CACHE/'GOAL.DAT',Path(tempfile.gettempdir())/'unused-t140.g2core')
        with patch.dict(os.environ,{'SDL_AUDIODRIVER':'dummy'}):
            w=CoreWindow(m);self.addCleanup(w.close);w.show();self.app.processEvents()
            r=w.core_round
            from goal2.core import views
            from goal2.desktop.core_roles import pitch_identity
            from goal2.desktop.core_viewer import CoreViewer
            closes=self.record_closes(CoreViewer)
            viewer=CoreViewer(pitch_identity(m.state,views.pitch_identity(m.state)));r.viewer=viewer
            viewer.pose(views.pitch(m.state,0,0),[])
            deadline=time.monotonic()+15
            while not viewer.drained and time.monotonic()<deadline:
                viewer.poll();self.app.processEvents();time.sleep(.005)
            self.assertTrue(viewer.drained);pid=viewer.process.pid
            r.finished('resume',('done',m.round_state()))
            r.replays.watch.click()
            self.assertEqual(w.finish_core(60)[0],'done')
            self.assertIs(r.viewer,viewer,self.closes_text(closes))
            seen=False;deadline=time.monotonic()+45
            while time.monotonic()<deadline:
                self.app.processEvents()
                if viewer.display.visible().replaying:seen=True
                if seen and r.state['stop']=='live' and not r.state.get('replay'):
                    r.viewer_timer.stop();break
                time.sleep(.002)
            else:self.fail('Replay did not render and return to live within the bounded native run'
                           + self.state_text(w,r,viewer,seen) + self.closes_text(closes))
            if w.core_jobs.busy:w.finish_core(60)
            r.viewer_timer.stop()
            deadline=time.monotonic()+10
            while not viewer.drained and time.monotonic()<deadline:
                viewer.poll();self.app.processEvents();time.sleep(.005)
            self.assertTrue(viewer.drained);self.assertFalse(viewer.display.visible().replaying)
            self.assertEqual(viewer.process.pid,pid);self.assertEqual(r.pending_inputs,[])
            self.assertEqual(r.state['pitch']['score'],[0,1])
            self.assertFalse(m.core.stopped)
            if os.environ.get('SDL_VIDEODRIVER')!='dummy' and os.environ.get('QT_QPA_PLATFORM') not in ('offscreen','minimal'):
                data=dict(platform=sys.platform,ratio=w.devicePixelRatioF(),replay_seen=seen,
                          same_pid=viewer.process.pid==pid,live_again=True,score=r.state['pitch']['score'],
                          frame_ack=viewer.frame_ack,pending_inputs=r.pending_inputs)
                (requires.CACHE/f'T140-native-{sys.platform}-{w.devicePixelRatioF()}.json').write_text(json.dumps(data,indent=2)+'\n')

class Presentation(unittest.TestCase):
    def test_replay_caption_is_causal_to_the_displayed_pose(self):
        from goal2.desktop.match_view import Display
        from goal2.tests.test_pygame_pitch_view import sample
        d=Display('replay');d.accept(['replay',0,'start',['HOME','AWAY']]);d.accept(['replay',1,'pitch',dict(rate=60)])
        d.accept(['replay',2,'event',dict(kind='replay',minute=18,score=[0,0],data=dict(active=True))])
        self.assertFalse(getattr(d.visible(),'replaying',False))
        d.accept(['replay',3,'frame',sample(0,1)]);d.advance(0);d.rendered()
        self.assertTrue(d.visible().replaying)
        d.accept(['replay',4,'event',dict(kind='replay',minute=18,score=[0,1],data=dict(active=False))])
        self.assertTrue(d.visible().replaying)
        d.accept(['replay',5,'frame',sample(1,2)]);d.advance(1);d.rendered()
        self.assertFalse(d.visible().replaying)

if __name__=='__main__':unittest.main()
