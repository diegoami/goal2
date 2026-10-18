"""[designed: T66] Actual SDL child plus Qt/original end-to-end acceptance."""
import copy
from dataclasses import asdict
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch
from goal2.desktop.match_view import Display, raw_rating, completion
from goal2.desktop.watched import WatchedController
from goal2.desktop.jobs import QuickJobs

ROOT=Path(__file__).resolve().parents[2]


def pump(predicate, *, app=None, timeout=120):
    deadline=time.monotonic()+timeout
    while time.monotonic()<deadline:
        if app:app.processEvents()
        if predicate():return
        time.sleep(.01)
    raise AssertionError('owned process failed to reach acceptance boundary')


def model(path):
    from goal2.desktop.model import DesktopModel
    return DesktopModel.open(ROOT/'.cache/e010-r0008-halftime.sav',ROOT/'.cache/GOAL.DAT',path,country=4)


class PresentationTests(unittest.TestCase):
    def test_raw_rating_original_word_boundaries(self):
        for word,want in ((0x7fff,None),(55,55),(10055,55),(5000,5000),(5001,-4999),(0xffff,-1),(0x8000,-32768)):
            self.assertEqual(raw_rating(bytes(18)+word.to_bytes(2,'little')),want)

    def test_order_display_copy_and_once_completion(self):
        d=Display('owned');d.accept(['owned',0,'start',['Denmark','Germany']])
        event={'kind':'commentary','minute':12,'score':[1,0],'data':{'text':'original line'}}
        d.accept(['owned',1,'event',event]);event['data']['text']='changed'
        self.assertEqual(d.events[0]['data']['text'],'original line')
        self.assertEqual(d.lines()[:4],['Original engine — friendly','Denmark — Germany','12′   1 — 0','12′ original line'])
        for packet in (['stale',2,'event',event],['owned',1,'event',event],['owned',3,'event',event],['owned',2,'complete',{}]):
            before=copy.deepcopy(d.__dict__)
            with self.assertRaises(ValueError):d.accept(packet)
            self.assertEqual(d.__dict__,before)
        d.accept(['owned',2,'event',{'kind':'end','minute':90,'score':[1,0],'data':{}}])
        result={'board':{'statistics':{'corners':[3,4]},'bars':[[1,2],[3,4]]},'ratings':[[{'name':'A','raw':55}],[{'name':'B','raw':None}]],'man_of_the_match':'A'}
        d.accept(['owned',3,'complete',result])
        self.assertIn('corners: 3 — 4',d.lines());self.assertIn('A: 55',d.lines());self.assertIn('B: blank',d.lines())
        self.assertIn('Denmark — Raw rating',d.lines());self.assertIn('Man of the match: A',d.lines())
        with self.assertRaises(ValueError):d.accept(['owned',4,'complete',result])

    def test_real_sdl_surface_and_quit_event(self):
        import pygame
        pygame.init()
        try:
            surface=pygame.display.set_mode((640,360));surface.fill((17,33,49));pygame.display.flip()
            self.assertEqual(tuple(surface.get_at((2,2)))[:3],(17,33,49))
            pygame.event.post(pygame.event.Event(pygame.QUIT))
            from goal2.desktop.pygame_viewer import navigation
            self.assertTrue(any(navigation(event,0,True)[2] is False for event in pygame.event.get()))
            pygame.event.post(pygame.event.Event(pygame.MOUSEWHEEL,y=2))
            pygame.event.post(pygame.event.Event(pygame.KEYDOWN,key=pygame.K_END))
            states=[];scroll=20;follow=True
            for event in pygame.event.get():
                scroll,follow,running=navigation(event,scroll,follow);states.append((scroll,follow,running))
            self.assertEqual(states,[(14,False,True),(10**9,True,True)])
        finally:pygame.quit()

    def test_real_framebuffer_matches_original_text_projection(self):
        import pygame
        from goal2.desktop.pygame_viewer import render
        pygame.init()
        try:
            screen=pygame.display.set_mode((1000,720));font=pygame.font.Font(None,24)
            display=Display('owned');display.accept(['owned',0,'start',['Denmark','Germany']])
            display.accept(['owned',1,'event',{'kind':'commentary','minute':17,'score':[2,1],'data':{'text':'Actual original commentary'}}])
            render(screen,font,display)
            expected=pygame.Surface((1000,720));expected.fill((18,28,37))
            # [designed] Independent expected strings visit score, countries, minute and commentary pixels.
            for n,line in enumerate(['Original engine — friendly','Denmark — Germany','17′   2 — 1','17′ Actual original commentary']):
                expected.blit(font.render(line,True,(232,239,229)),(20,20+n*25))
            self.assertEqual(pygame.image.tobytes(screen,'RGB'),pygame.image.tobytes(expected,'RGB'),'SDL rendered text differs')
            display.accept(['owned',2,'event',{'kind':'end','minute':90,'score':[2,1],'data':{}}])
            display.accept(['owned',3,'complete',{'board':{'statistics':{'corners':[3,4]},'bars':[[1,2],[3,4]]},
                'ratings':[[{'name':'A','raw':55}],[{'name':'B','raw':None}]],'man_of_the_match':'A'}])
            render(screen,font,display)
            expected.fill((18,28,37))
            for n,line in enumerate(['Original engine — friendly','Denmark — Germany','90′   2 — 1','17′ Actual original commentary',
                'Original full-time board','Man of the match: A','corners: 3 — 4','Original bars: [[1, 2], [3, 4]]',
                'Denmark — Raw rating','A: 55','Germany — Raw rating','B: blank']):
                expected.blit(font.render(line,True,(232,239,229)),(20,20+n*25))
            self.assertEqual(pygame.image.tobytes(screen,'RGB'),pygame.image.tobytes(expected,'RGB'),'SDL board/raw rating pixels differ')
            live=Display('owned');live.accept(['owned',0,'start',['Denmark','Germany']])
            for n in range(18,49):
                live.accept(['owned',n-17,'event',{'kind':'commentary','minute':n,'score':[2,1],'data':{'text':f'Original line {n}'}}])
            self.assertEqual(render(screen,font,live,999),8)
            expected.fill((18,28,37))
            for n,line in enumerate(['Original engine — friendly','Denmark — Germany','48′   2 — 1']+
                                    [f'{n}′ Original line {n}' for n in range(26,49)]):
                expected.blit(font.render(line,True,(232,239,229)),(20,20+n*25))
            self.assertEqual(pygame.image.tobytes(screen,'RGB'),pygame.image.tobytes(expected,'RGB'),'live scroll lost pinned score or ordered commentary')
            from goal2.desktop.pygame_viewer import position
            self.assertEqual(position(live,8,False,False,True),(8,False,False))
            self.assertEqual(position(live,0,True,False,True),(10**9,True,False))
            live.accept(['owned',32,'event',{'kind':'end','minute':90,'score':[2,1],'data':{}}])
            rows=[{'name':f'Player {n}','raw':55} for n in range(20)]
            live.accept(['owned',33,'complete',{'board':{'statistics':{'corners':[3,4]},'bars':[[1,2],[3,4]]},
                'ratings':[rows,rows],'man_of_the_match':'A'}])
            board_scroll,follow,finished=position(live,0,True,False,True)
            self.assertEqual((board_scroll,follow,finished),(31,False,True))
            self.assertEqual(render(screen,font,live,board_scroll),31)
            self.assertEqual(position(live,7,False,True,False),(7,False,True))
        finally:pygame.quit()

    def test_qt_heartbeat_blocked_tail_and_actual_viewer_quit(self):
        from PySide6.QtCore import QTimer
        from PySide6.QtWidgets import QApplication
        from goal2.desktop.window import ManagementWindow
        from goal2.tests.test_watched_jobs import CONTROLLED
        app=QApplication.instance() or QApplication([])
        with tempfile.TemporaryDirectory() as folder:
            m=model(Path(folder)/'save');w=ManagementWindow(m);w.show();app.processEvents()
            w.watched.engine.command=[sys.executable,'-c',CONTROLLED,'blocked']
            w.confirm_draft()
            before=copy.deepcopy(m.state);beats=[];timer=QTimer();timer.setInterval(2);timer.timeout.connect(lambda:beats.append(1));timer.start()
            try:
                w.start_watched()
                pump(lambda:any(e['kind']=='full_time' for e in w.watched.display.events),app=app)
                count=len(beats)
                pump(lambda:len(beats)>count+12,app=app)
                self.assertTrue(w.watched.busy);self.assertIsNone(w.watched.display.result)
                self.assertEqual(m.state,before);self.assertFalse(w.save.isEnabled())
                # [designed] Actual SDL QUIT goes through the child loop, not a fabricated close acknowledgement.
                w.cancel_match()
                script="""import sys,pygame
from goal2.desktop import pygame_viewer
original=pygame.event.get
count=0
def events():
 global count
 count+=1
 return original()+([pygame.event.Event(pygame.QUIT)] if count==10 else [])
pygame.event.get=events
sys.exit(pygame_viewer.main())
"""
                w.watched.viewer_command=[sys.executable,'-c',script]
                w.start_watched();viewer=w.watched.process;engine=w.watched.engine.process
                pump(lambda:w.watched.process is None,app=app)
                self.assertIsNotNone(viewer.poll());self.assertIsNotNone(engine.poll())
                self.assertEqual(m.state,before);self.assertFalse(m.match_pending)
                from dataclasses import replace
                m.state.campaign.fixtures=tuple(replace(f,kind=2) for f in m.state.campaign.fixtures)
                w.tactics[0][1].setChecked(not w.tactics[0][1].isChecked())
                w.start_watched()
                self.assertIn('qualifiers are unsupported',w.status.text())
                self.assertFalse(w.watched.busy);self.assertIsNone(w.watched.process)
            finally:timer.stop();w.close();w.deleteLater();app.processEvents()

    def test_optional_dependency_and_qualifier_boundary(self):
        with tempfile.TemporaryDirectory() as folder:
            m=model(Path(folder)/'save');c=WatchedController(m);before=copy.deepcopy(m.state)
            try:
                with patch('goal2.desktop.watched.importlib.util.find_spec',return_value=None):
                    with self.assertRaisesRegex(ValueError,'pygame-ce.*pip install'):c.start()
                self.assertEqual(m.state,before);self.assertIsNone(c.process)
                m.state.campaign=None
                with self.assertRaisesRegex(ValueError,'scheduled friendlies only'):c.start()
                m.state=before
                from dataclasses import replace
                campaign=m.state.campaign
                campaign.fixtures=tuple(replace(f,kind=2) for f in campaign.fixtures)
                with self.assertRaisesRegex(ValueError,'qualifiers are unsupported'):c.start()
                self.assertIsNone(c.process)
            finally:c.close()

    def test_real_viewer_cancel_duplicate_and_failed_start_preserve_save(self):
        from goal2.tests.test_watched_jobs import CONTROLLED
        with tempfile.TemporaryDirectory() as folder:
            m=model(Path(folder)/'save');m.save(m.save_path);saved=m.save_path.read_bytes();before=copy.deepcopy(m.state)
            c=WatchedController(m,engine_command=[sys.executable,'-c',CONTROLLED,'blocked'])
            try:
                c.start(reference_seed=257,delay_byte=0,record_draws=True)
                viewer=c.process;engine=c.engine.process
                def seen():c.poll();return c.last_status and c.display.events
                pump(seen)
                with self.assertRaisesRegex(ValueError,'already running'):c.start()
                quick=QuickJobs(m)
                try:
                    with self.assertRaisesRegex(ValueError,'already running'):quick.start()
                finally:quick.cancel()
                with self.assertRaisesRegex(ValueError,'Saving during'):m.save(m.save_path)
                self.assertEqual(m.state,before);self.assertEqual(m.save_path.read_bytes(),saved)
                started=time.monotonic();c.cancel();c.cancel()
                self.assertLess(time.monotonic()-started,2)
                self.assertIsNotNone(viewer.poll());self.assertIsNotNone(engine.poll())
                self.assertEqual(m.state,before);self.assertEqual(m.save_path.read_bytes(),saved)
            finally:c.close()
            c=WatchedController(m,viewer_command=['/nonexistent/goal2-viewer'])
            try:
                with self.assertRaisesRegex(ValueError,'Cannot start original friendly'):c.start()
                self.assertIsNone(c.process);self.assertFalse(c.busy);self.assertFalse(m.match_pending)
                self.assertEqual(m.state,before)
            finally:c.close()
            from goal2.desktop.model import DesktopModel
            m=DesktopModel.open(ROOT/'.cache/e0afff6751747233-e006-1000-r0001.sav',ROOT/'.cache/GOAL.DAT',Path(folder)/'unused',country=4)
            before=copy.deepcopy(m.state);c=WatchedController(m)
            try:
                with self.assertRaisesRegex(ValueError,'Cannot start original friendly:.*extra time'):c.start()
                self.assertIsNone(c.process);self.assertFalse(c.busy);self.assertEqual(m.state,before)
            finally:c.close()

    def test_partial_startup_allocation_cleanup_and_retry_preserve_save(self):
        from goal2.tests.test_watched_jobs import CONTROLLED
        original_open=Path.open
        original_folder=tempfile.TemporaryDirectory
        for failed in ('folder','display','errors'):
            with self.subTest(allocation=failed),original_folder() as folder:
                m=model(Path(folder)/'save');m.save(m.save_path)
                before=copy.deepcopy(m.state);saved=m.save_path.read_bytes()
                c=WatchedController(m,engine_command=[sys.executable,'-c',CONTROLLED,'blocked'])
                acquired=[];directories=[];retry_handles=();injected=OSError(f'simulated {failed} allocation failure')
                def allocate(*args,**kwargs):
                    if failed=='folder':raise injected
                    result=original_folder(*args,**kwargs);directories.append(Path(result.name));return result
                def opening(path,*args,**kwargs):
                    if path.name==failed and path.parent.name.startswith('goal2-viewer-'):raise injected
                    result=original_open(path,*args,**kwargs)
                    if path.parent.name.startswith('goal2-viewer-'):acquired.append(result)
                    return result
                try:
                    error=None;cleanup_error=None
                    with patch('goal2.desktop.watched.tempfile.TemporaryDirectory',allocate),patch.object(Path,'open',opening),patch('goal2.desktop.watched.subprocess.Popen') as launch:
                        try:c.start()
                        except Exception as exc:error=exc
                        self.assertFalse(launch.called,'allocation failure launched a child')
                    automatically_closed=all(handle.closed for handle in acquired)
                    automatically_released=all(not directory.exists() for directory in directories)
                    try:c.close_viewer();c.close_viewer();c.cancel();c.cancel()
                    except Exception as exc:cleanup_error=exc
                    self.assertIsInstance(error,ValueError,'startup allocation did not report actionable error')
                    self.assertIn('Cannot start original friendly',str(error));self.assertIs(error.__cause__,injected)
                    self.assertIsNone(cleanup_error,'partial cleanup raised a secondary exception')
                    self.assertIsNone(c.process);self.assertFalse(c.busy);self.assertIsNone(c.engine.publication._pending)
                    self.assertFalse(getattr(m,'match_pending',False));self.assertTrue(m.state==before,'allocation failure changed complete state')
                    self.assertTrue(m.save_path.read_bytes()==saved,'failed allocation changed committed save bytes')
                    self.assertTrue(automatically_closed,'startup failure retained an acquired stream')
                    self.assertTrue(automatically_released,'startup failure retained its allocated folder')
                    self.assertTrue(all(handle.closed for handle in acquired),'partial allocation leaked an open stream')
                    self.assertTrue(all(not directory.exists() for directory in directories),'partial allocation retained its folder')
                    # [designed] Retry the same live bridge before terminal close, with real owned children.
                    c.start();viewer=c.process;engine=c.engine.process
                    retry_handles=(c.stream,c.errors)
                    def seen():c.poll();return c.last_status is not None and bool(c.display.events)
                    pump(seen)
                    c.cancel();c.cancel()
                    self.assertIsNotNone(viewer.poll());self.assertIsNotNone(engine.poll())
                    self.assertTrue(all(handle.closed for handle in retry_handles))
                    self.assertTrue(m.state==before,'allocation failure changed complete state');self.assertTrue(m.save_path.read_bytes()==saved,'retry changed committed save bytes')
                    close_error=None
                    try:c.close();c.close()
                    except Exception as exc:close_error=exc
                    self.assertIsNone(close_error,'terminal cleanup was not idempotent')
                finally:
                    # [designed] A failing before/control run must still release its test-owned resources.
                    try:c.close()
                    except Exception:pass
                    for handle in acquired+list(retry_handles):
                        if not handle.closed:handle.close()
                    if c.folder is not None:c.folder.cleanup();c.folder=None
                    c.engine.close()

    def test_malformed_stale_ack_and_engine_failure_preserve_state(self):
        from goal2.tests.test_watched_jobs import CONTROLLED
        for mode in ('malformed','stale','guest','closed','startup-timeout','oversized','bad-digest'):
            with self.subTest(mode=mode),tempfile.TemporaryDirectory() as folder:
                m=model(Path(folder)/'save');before=copy.deepcopy(m.state)
                script="import time;time.sleep(60)"
                c=WatchedController(m,viewer_command=[sys.executable,'-c',script],engine_command=[sys.executable,'-c',CONTROLLED,'guest' if mode=='guest' else 'blocked'])
                try:
                    c.start();viewer=c.process;engine=c.engine.process
                    if mode in ('guest','bad-digest'):
                        (c.directory/'status').write_text(json.dumps({'token':c.token,'kind':'ready','sequence':0,'digest':c.digests[0] if mode=='guest' else '0'*64}))
                    if mode=='startup-timeout':c.started-=11
                    if mode=='oversized':(c.directory/'status').write_text('x'*4097)
                    if mode in ('malformed','stale','closed'):
                        (c.directory/'status').write_text('[]' if mode=='malformed' else json.dumps({'token':'stale' if mode=='stale' else c.token,'kind':'closed','sequence':0,'digest':c.digests[0]}))
                    if mode=='closed':c.poll()
                    else:
                        with self.assertRaises(ValueError):pump(lambda:c.poll())
                    self.assertIsNone(c.process);self.assertFalse(c.busy)
                    self.assertIsNotNone(viewer.poll());self.assertIsNotNone(engine.poll());self.assertEqual(m.state,before)
                finally:c.close()


class OriginalQtAcceptance(unittest.TestCase):
    def test_original_qt_save_resume_repeat(self):
        import runpy
        acceptance=runpy.run_path(str(ROOT/'tools/desktop-ui/watched.py'))
        acceptance['main']()
