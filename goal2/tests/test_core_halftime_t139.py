"""[designed: owner #456/T139] Half-time presentation cannot answer the original decision."""
import os
import time
import unittest
from unittest.mock import patch
from goal2.tests import requires


@requires.need(modules=('unicorn','PySide6'),files=('e010-r0001-halftime.sav','GOAL.DAT'))
class HalfTime(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from PySide6.QtWidgets import QApplication
        cls.app=QApplication.instance() or QApplication([])

    def window(self):
        from goal2.core import Core
        from goal2.core.driver import Driver
        from goal2.desktop.core_model import CoreModel
        from goal2.desktop.core_window import CoreWindow
        d=Driver(Core.start((requires.CACHE/'e010-r0001-halftime.sav').read_bytes()).core)
        d.press(13,expect=('match-menu-halftime',))
        # Defer the resume callback so each test controls the instant the interval arrives.
        with patch.object(CoreWindow,'resume_round'):
            w=CoreWindow(CoreModel(d.core,requires.CACHE/'GOAL.DAT',requires.CACHE/'unused-t139.g2core'))
            w.show();self.app.processEvents()
        self.addCleanup(w.close)
        return w

    def test_halftime_is_prominent_retains_decision_and_only_explicit_play_continues(self):
        w=self.window();r=w.core_round;b=r.bench
        state=w.model.round_state();before=w.model.core.save()
        # The actual original half-time state, not stale commentary, owns this transition.
        with patch.object(w,'activateWindow') as activate,patch.object(w,'raise_') as raise_window:
            r.finished('live_step',('done',state));self.app.processEvents()
            self.assertEqual(b.title.text(),'HALF TIME')
            self.assertIn('MAKE SUBSTITUTIONS NOW',b.interval_notice.text())
            self.assertTrue(b.interval_notice.isVisible())
            self.assertTrue(b.interval_notice.font().bold())
            self.assertGreater(b.interval_notice.font().pixelSize(),b.title.font().pixelSize())
            self.assertEqual(b.play.text(),'Start second half')
            self.assertIn('Start second half',b.play.accessibleName())
            self.assertEqual(r.views.currentWidget(),b.view)
            self.assertEqual(w.page_stack.currentIndex(),3)
            activate.assert_called_once();raise_window.assert_called_once()
            # Refresh and re-offer after a bench edit must not steal attention again.
            r.finished('substitute',('done',dict(state,substitution={'made':True})))
            b.refresh();b.escape()
            until=time.monotonic()+.12
            while time.monotonic()<until:self.app.processEvents()
            activate.assert_called_once()
            self.assertEqual(w.model.core.save(),before)
            self.assertFalse(w.core_jobs.busy)
            with patch.object(r,'start_play_on') as play:
                b.play.click();play.assert_called_once()
            self.assertEqual(w.model.core.save(),before)

    def test_warning_does_not_leak_to_pause_and_extra_time_names_its_phase(self):
        w=self.window();r=w.core_round;b=r.bench;state=w.model.round_state()
        r.finished('live_step',('done',state))
        b.offer(dict(state,stop='pause'),'pause')
        self.assertFalse(b.interval_notice.isVisible())
        self.assertEqual(b.title.text(),'PLAYERS / PAUSE')
        for stop,label,button in [('extra-time-start','EXTRA TIME','Play extra time'),
                                 ('extra-time-half','EXTRA-TIME HALF TIME','Continue extra time')]:
            b.offer(dict(state,stop=stop,interval_label=label),'half_time')
            self.assertIn(label,b.title.text())
            self.assertTrue(b.interval_notice.isVisible())
            self.assertEqual(b.play.text(),button)

    def test_minimized_main_is_restored_without_losing_maximized_state(self):
        from PySide6.QtCore import Qt
        w=self.window();w.showMaximized();self.app.processEvents()
        w.showMinimized();self.app.processEvents()
        w.core_round.finished('live_step',('done',w.model.round_state()));self.app.processEvents()
        self.assertFalse(w.isMinimized())
        self.assertTrue(w.windowState() & Qt.WindowState.WindowMaximized)
        b=w.core_round.bench
        self.assertTrue(b.interval_notice.isVisible())
        # All key bench controls remain inside their page at the supported desktop size.
        for control in (b.title,b.interval_notice,b.play,b.roster):
            rect=control.rect();top=control.mapTo(b.view,rect.topLeft());bottom=control.mapTo(b.view,rect.bottomRight())
            self.assertTrue(b.view.rect().contains(top),(control.objectName(),'top'))
            self.assertTrue(b.view.rect().contains(bottom),(control.objectName(),'bottom'))

    @requires.need(modules=('pygame',))
    def test_native_pitch_retains_interval_and_minimized_bench_receives_attention(self):
        import json
        import sys
        from goal2.core import views
        from goal2.desktop.core_viewer import CoreViewer
        from goal2.desktop.core_roles import pitch_identity
        w=self.window();r=w.core_round;state=w.model.round_state()
        # A real viewer receives the genuine final pose and then the original interval decision.
        with patch.dict(os.environ,{'SDL_AUDIODRIVER':'dummy'}):
            viewer=CoreViewer(pitch_identity(w.model.state,views.pitch_identity(w.model.state)))
        r.viewer=viewer
        self.addCleanup(viewer.close)
        viewer.pose(views.pitch(w.model.state,0,0),[],views.match_speed(w.model.state))
        def pump(predicate):
            deadline=time.monotonic()+15
            while time.monotonic()<deadline:
                self.app.processEvents();viewer.poll()
                if predicate():return
                time.sleep(.01)
            self.fail('Viewer did not acknowledge interval presentation')
        pump(lambda:viewer.drained)
        before=w.model.core.save();pid=viewer.process.pid
        w.showMinimized();self.app.processEvents()
        r.finished('live_step',('done',dict(state,commentary=[])))
        pump(lambda:viewer.last_status['sequence']==viewer.display.sequence)
        self.assertFalse(w.isMinimized())
        self.assertEqual(viewer.display.board(),'HALF TIME')
        self.assertIn('MAKE SUBSTITUTIONS NOW',viewer.display.board_note())
        self.assertEqual(viewer.process.pid,pid)
        self.assertEqual(viewer.frame_ack,0)
        self.assertEqual(r.pending_inputs,[])
        self.assertFalse(w.core_jobs.busy)
        self.assertEqual(w.model.core.save(),before)
        from goal2.desktop.fixed_page import problems
        for width,height in ((1440,900),(1050,780),(900,640),(2560,1600)):
            w.resize(round(.9*width),round(.9*height));self.app.processEvents()
            self.assertEqual(problems(w),[],(width,height,problems(w)))
        if os.environ.get('SDL_VIDEODRIVER')!='dummy' and os.environ.get('QT_QPA_PLATFORM') not in ('offscreen','minimal'):
            receipt=dict(platform=sys.platform,scale=w.devicePixelRatioF(),main_active=w.isActiveWindow(),
                         minimized=w.isMinimized(),same_viewer=viewer.process.pid==pid,
                         guest_unchanged=w.model.core.save()==before,pitch_instruction=viewer.display.board_note())
            (requires.CACHE/f'T139-native-{sys.platform}-{w.devicePixelRatioF()}.json').write_text(json.dumps(receipt,indent=2)+'\n')
            w.grab().save(str(requires.CACHE/f'T139-native-{sys.platform}-{w.devicePixelRatioF()}.png'))


class PitchFallback(unittest.TestCase):
    def test_pitch_keeps_instruction_when_main_window_cannot_take_foreground(self):
        from goal2.desktop.match_view import Display
        d=Display('test');d.accept(['test',0,'start',['HOME','AWAY']])
        d.accept(['test',1,'event',dict(kind='decision',minute=45,score=[0,0],data={'context':'half_time'})])
        self.assertIn('HALF TIME',d.board())
        self.assertIn('MAKE SUBSTITUTIONS NOW',d.board_note())
        self.assertIn('BENCH',d.board_note())


if __name__=='__main__':unittest.main()
