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
        self.assertEqual(d.lines()[:4],['Original engine — friendly','Denmark — Germany','12 min   1 — 0','12 min original line'])
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
        from goal2.desktop.pygame_viewer import render,position
        pygame.init()
        try:
            screen=pygame.display.set_mode((1000,720));font=pygame.font.Font(None,24)
            d=Display('owned');d.accept(['owned',0,'start',['Denmark','Germany']])
            d.accept(['owned',1,'event',{'kind':'commentary','minute':17,'score':[2,1],'data':{'text':'Actual original commentary'}}])
            before=copy.deepcopy(d.__dict__);render(screen,font,d)
            expected=pygame.Surface((1000,720));expected.fill((8,28,24))
            for n,line in enumerate(['Original engine — friendly','Denmark — Germany','17 min   2 — 1']):
                expected.blit(font.render(line,True,(200,242,121) if n==2 else (245,242,232)),(20,16+n*30))
            expected.blit(font.render('17 min Actual original commentary',True,(245,242,232)),(20,112))
            self.assertEqual(pygame.image.tobytes(screen,'RGB'),pygame.image.tobytes(expected,'RGB'),'SDL rendered text differs')
            self.assertEqual(d.__dict__,before,'rendering mutated display state')
            d.accept(['owned',2,'event',{'kind':'end','minute':90,'score':[2,1],'data':{}}])
            d.accept(['owned',3,'complete',{'board':{'statistics':{'corners':[3,4]},'bars':[[1,2],[3,4]]},
                'ratings':[[{'name':'A','raw':55}],[{'name':'B','raw':None}]],'man_of_the_match':'A'}])
            render(screen,font,d)
            expected.fill((8,28,24))
            header=['Original engine — friendly','Denmark — Germany','90 min   2 — 1']
            rows=['17 min Actual original commentary','Original full-time board','Man of the match: A','corners: 3 — 4','Original bars: [[1, 2], [3, 4]]','Denmark — Raw rating','A: 55','Germany — Raw rating','B: blank']
            for n,line in enumerate(header):expected.blit(font.render(line,True,(200,242,121) if n==2 else (245,242,232)),(20,16+n*30))
            for n,line in enumerate(rows):expected.blit(font.render(line,True,(245,242,232)),(20,112+n*26))
            self.assertEqual(pygame.image.tobytes(screen,'RGB'),pygame.image.tobytes(expected,'RGB'),'SDL board/raw rating pixels differ')
            live=Display('owned');live.accept(['owned',0,'start',['Denmark','Germany']])
            for n in range(18,49):live.accept(['owned',n-17,'event',{'kind':'commentary','minute':n,'score':[2,1],'data':{'text':f'Original line {n}'}}])
            self.assertEqual(render(screen,font,live,999),9)
            expected.fill((8,28,24))
            for n,line in enumerate(['Original engine — friendly','Denmark — Germany','48 min   2 — 1']):
                expected.blit(font.render(line,True,(200,242,121) if n==2 else (245,242,232)),(20,16+n*30))
            for n in range(27,49):expected.blit(font.render(f'{n} min Original line {n}',True,(245,242,232)),(20,112+(n-27)*26))
            self.assertEqual(pygame.image.tobytes(screen,'RGB'),pygame.image.tobytes(expected,'RGB'),'live scroll lost pinned score or ordered commentary')
            self.assertEqual(position(live,8,False,False,True),(8,False,False))
            self.assertEqual(position(live,0,True,False,True),(10**9,True,False))
            live.accept(['owned',32,'event',{'kind':'end','minute':90,'score':[2,1],'data':{}}])
            rows=[{'name':f'Player {n}','raw':55} for n in range(20)]
            live.accept(['owned',33,'complete',{'board':{'statistics':{'corners':[3,4]},'bars':[[1,2],[3,4]]},'ratings':[rows,rows],'man_of_the_match':'A'}])
            board_scroll,follow,finished=position(live,0,True,False,True)
            self.assertEqual((board_scroll,follow,finished),(31,False,True))
            self.assertEqual(render(screen,font,live,board_scroll),31)
            self.assertEqual(position(live,7,False,True,False),(7,False,True))
        finally:pygame.quit()

    def test_wrapped_reading_preserves_long_text_and_compact_pitch_is_read_only(self):
        # [designed: T79] Independent character retention, bounds and canonical pitch samples.
        import pygame
        from goal2.desktop import pygame_viewer as viewer
        self.assertTrue(callable(getattr(viewer,'wrapped',None)),'readable wrapping is absent')
        wrapped,render_pitch=viewer.wrapped,viewer.render_pitch
        from goal2.tests.test_pygame_pitch_view import pitch,sample,send
        pygame.init()
        try:
            font=pygame.font.Font(None,24);line='Long original commentary '+('unbrokenname'*35)
            rows=wrapped(font,[line],860)
            self.assertGreater(len(rows),1);self.assertEqual(''.join(rows),line)
            self.assertTrue(all(font.size(row)[0]<=860 for row in rows))
            d=pitch();send(d,'frame',sample());d.advance(0);before=copy.deepcopy(d.__dict__)
            for size in ((900,640),(1000,720),(1440,900),(1800,1280)):
                surface=pygame.Surface(size);render_pitch(surface,font,d)
                self.assertEqual(tuple(surface.get_at((1,1)))[:3],(8,28,24))
                self.assertEqual(d.__dict__,before,'painting changed a delivered frame/packet')
        finally:pygame.quit()

    def test_wrapped_commentary_lands_at_board_and_scroll_retains_tail(self):
        # [designed: T79] A wrapped commentary row must not consume the board landing offset.
        import pygame
        from goal2.desktop.pygame_viewer import render_pitch,position,wrapped
        from goal2.tests.test_pygame_pitch_view import pitch,sample,send
        pygame.init()
        try:
            font=pygame.font.Font(None,24);d=pitch()
            send(d,'event',{'kind':'commentary','minute':7,'score':[1,0],'data':{'text':'long original words '*65}})
            f=sample();f['watermark']=1;send(d,'frame',f);d.advance(0)
            send(d,'event',{'kind':'end','minute':90,'score':[1,0],'data':{}})
            rows=[{'name':f'Player {n}','raw':55} for n in range(20)]
            send(d,'complete',{'board':{'statistics':{'corners':[3,4]},'bars':[[1,2],[3,4]]},'ratings':[rows,rows],'man_of_the_match':'Player 0'})
            import inspect
            options={'font':font} if 'font' in inspect.signature(position).parameters else {}
            scroll,follow,finished=position(d,0,True,False,True,**options)
            self.assertGreater(scroll,1)
            self.assertEqual(scroll,len(wrapped(font,d.lines()[3:4],960)))
            screen=pygame.Surface((1000,720));render_pitch(screen,font,d,scroll)
            title=font.render('Original full-time board',True,(245,242,232))
            expected=pygame.Surface(title.get_size());expected.fill((8,28,24));expected.blit(title,(0,0))
            self.assertEqual(pygame.image.tobytes(screen.subsurface((20,490,*title.get_size())),'RGB'),pygame.image.tobytes(expected,'RGB'))
            tail=render_pitch(screen,font,d,10**9)
            self.assertGreater(tail,scroll)
            label=font.render('Player 19: 55',True,(245,242,232));expected=pygame.Surface(label.get_size());expected.fill((8,28,24));expected.blit(label,(0,0))
            self.assertEqual(pygame.image.tobytes(screen.subsurface((20,490+7*26,*label.get_size())),'RGB'),pygame.image.tobytes(expected,'RGB'),'manual scroll lost the final rating row')
            self.assertEqual((follow,finished),(False,True))
        finally:pygame.quit()

    def test_qt_score_uses_consumed_pose_not_future_ingress(self):
        # [designed: T79] Parent presentation remembers frames before the controller drains ACKed ingress.
        from PySide6.QtWidgets import QApplication
        from goal2.desktop.window import ManagementWindow
        from goal2.tests.test_pygame_pitch_view import pitch,sample,send
        app=QApplication.instance() or QApplication([])
        with tempfile.TemporaryDirectory() as folder:
            m=model(Path(folder)/'save');w=ManagementWindow(m)
            try:
                d=pitch();send(d,'event',{'kind':'commentary','minute':88,'score':[9,8],'data':{'text':'FUTURE GOAL'}})
                f=sample();f['score']=[1,0];f['watermark']=0;send(d,'frame',f)
                w.watched.display=d;w.watched.token='owned';w.watched.frames_enabled=True;w.watched.frame_ack=-1
                with patch.object(type(w.watched),'busy',new_callable=lambda:property(lambda self:True)):
                    before=copy.deepcopy(d.__dict__);w.poll_watched()
                    self.assertEqual(d.__dict__,before)
                    self.assertNotIn('9 — 8',w.match_score.text());self.assertIn('first rendered sample',w.match_progress.text())
                    self.assertNotIn('88',w.status.text());self.assertNotIn('9 — 8',w.status.text())
                    w.watched.frame_ack=0;d.frames.popleft();w.poll_watched()
                    self.assertEqual(w.match_score.text(),'First 1 — 0 Second')
                    self.assertTrue(w.match_progress.text().startswith('7 min'))
                    self.assertNotIn('88',w.match_progress.text())
                    self.assertNotIn('88',w.status.text());self.assertNotIn('9 — 8',w.status.text())
                    w.watched.token='replacement';w.watched.frame_ack=-1;w.poll_watched()
                    self.assertEqual(w._match_poses,{})
                    self.assertIn('first rendered sample',w.match_progress.text())
            finally:w.close();app.processEvents()

    def test_named_match_surface_tracks_current_authority_instead_of_old_viewer(self):
        # [designed: T79] Visit New/preview/quick context with real controls and a bounded child.
        from PySide6.QtWidgets import QApplication,QWidget
        from goal2.desktop.window import ManagementWindow
        app=QApplication.instance() or QApplication([])
        with tempfile.TemporaryDirectory() as folder:
            m=model(Path(folder)/'save');w=ManagementWindow(m);w.show();app.processEvents()
            try:
                self.assertIsNotNone(w.findChild(QWidget,'matchSurface'))
                old=Display('old');old.accept(['old',0,'start',['Stale A','Stale B']]);w.watched.display=old
                w.refresh();self.assertEqual(w.match_provenance.text(),'No match played')
                self.assertNotIn('Stale',w.match_score.text())
                w.country.setCurrentIndex(w.country.findData(18));app.processEvents()
                self.assertEqual(w.match_provenance.text(),'Country preview')
                w.action(lambda:m.new_campaign(18),'New campaign created',replace=True)
                w.confirm_draft();w.jobs.command=[sys.executable,'-c','import time;time.sleep(60)'];w.start_match()
                self.assertTrue(w.jobs.busy,w.status.text())
                self.assertEqual(w.match_provenance.text(),'Quick simulation (rebuild setup)')
                self.assertNotIn('Stale',w.match_score.text());self.assertTrue(w.stop.isEnabled())
                w.cancel_match();self.assertEqual(w.match_provenance.text(),'No match played')
            finally:w.close();app.processEvents()

    def test_standings_tab_reaches_play_and_back_without_state_change(self):
        # [designed: T79] Preserve T78 keyboard order after adding the focusable match panel.
        from PySide6.QtCore import Qt
        from PySide6.QtTest import QTest
        from PySide6.QtWidgets import QApplication
        from goal2.desktop.window import ManagementWindow
        app=QApplication.instance() or QApplication([])
        with tempfile.TemporaryDirectory() as folder:
            m=model(Path(folder)/'save');m.save(m.save_path)
            before=copy.deepcopy(m.state);saved=m.save_path.read_bytes()
            w=ManagementWindow(m);w.show();w.page_stack.setCurrentIndex(3);app.processEvents()
            try:
                self.assertTrue(w.play.isEnabled())
                w.standings.setFocus();app.processEvents();self.assertIs(app.focusWidget(),w.standings)
                QTest.keyClick(w.standings,Qt.Key.Key_Tab);app.processEvents()
                self.assertIs(app.focusWidget(),w.play,'standings Tab must reach Play')
                QTest.keyClick(w.play,Qt.Key.Key_Backtab);app.processEvents()
                self.assertIs(app.focusWidget(),w.standings)
                visited=[]
                for _ in range(128):
                    target=app.focusWidget();visited.append(target.objectName())
                    QTest.keyClick(target,Qt.Key.Key_Tab);app.processEvents()
                    if app.focusWidget() is w.standings:break
                self.assertIn('matchSurface',visited,'match panel must remain keyboard reachable')
                self.assertEqual(m.state,before);self.assertEqual(m.save_path.read_bytes(),saved)
                self.assertFalse(getattr(m,'match_pending',False))
            finally:w.close();app.processEvents()

    def test_external_job_pending_context_preserves_state_save_and_resets(self):
        # [designed: T79] A completed view cannot identify an unrelated current match owner.
        from PySide6.QtWidgets import QApplication
        from goal2.desktop.window import ManagementWindow
        app=QApplication.instance() or QApplication([])
        with tempfile.TemporaryDirectory() as folder:
            m=model(Path(folder)/'save');m.save(m.save_path);saved=m.save_path.read_bytes();before=copy.deepcopy(m.state)
            w=ManagementWindow(m);external=QuickJobs(m,command=[sys.executable,'-c','import time;time.sleep(60)'])
            try:
                w.watched.display=Display('old-view');w._match_pose_token='old-view';w._match_poses={0:{'minute':90,'score':(8,7),'watermark':0}}
                external.start();child=external.process;w.set_busy(True)
                self.assertEqual(w.match_provenance.text(),'Match in progress')
                self.assertIn('active match owner',w.match_progress.text());self.assertEqual(w._match_poses,{})
                w.watched.cancel();w.poll_watched();w.set_busy(False)
                self.assertTrue(m.match_pending);self.assertIsNone(child.poll());self.assertFalse(w.save.isEnabled())
                self.assertEqual(w.match_provenance.text(),'Match in progress')
                self.assertEqual(m.state,before);self.assertEqual(m.save_path.read_bytes(),saved)
                external.cancel();w.set_busy(False)
                self.assertEqual(w.match_provenance.text(),'No match played');self.assertEqual(w._match_poses,{})
                self.assertEqual(m.state,before);self.assertEqual(m.save_path.read_bytes(),saved)
            finally:external.cancel();w.close();app.processEvents()

    def test_qt_heartbeat_blocked_tail_and_actual_viewer_quit(self):
        from PySide6.QtCore import QTimer
        from PySide6.QtWidgets import QApplication
        from goal2.desktop.window import ManagementWindow
        from goal2.tests.test_watched_jobs import CONTROLLED
        app=QApplication.instance() or QApplication([])
        with tempfile.TemporaryDirectory() as folder:
            m=model(Path(folder)/'save');w=ManagementWindow(m);original_start=w.watched.start;w.watched.start=lambda **kw:original_start(frames=False,**kw);w.show();app.processEvents()
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
                    with self.assertRaisesRegex(ValueError,'pygame-ce.*pip install'):c.start(frames=False,)
                self.assertEqual(m.state,before);self.assertIsNone(c.process)
                m.state.campaign=None
                with self.assertRaisesRegex(ValueError,'scheduled friendlies only'):c.start(frames=False,)
                m.state=before
                from dataclasses import replace
                campaign=m.state.campaign
                campaign.fixtures=tuple(replace(f,kind=2) for f in campaign.fixtures)
                with self.assertRaisesRegex(ValueError,'qualifiers are unsupported'):c.start(frames=False,)
                self.assertIsNone(c.process)
            finally:c.close()

    def test_real_viewer_cancel_duplicate_and_failed_start_preserve_save(self):
        from goal2.tests.test_watched_jobs import CONTROLLED
        with tempfile.TemporaryDirectory() as folder:
            m=model(Path(folder)/'save');m.save(m.save_path);saved=m.save_path.read_bytes();before=copy.deepcopy(m.state)
            c=WatchedController(m,engine_command=[sys.executable,'-c',CONTROLLED,'blocked'])
            try:
                c.start(frames=False,reference_seed=257,delay_byte=0,record_draws=True)
                viewer=c.process;engine=c.engine.process
                def seen():c.poll();return c.last_status and c.display.events
                pump(seen)
                with self.assertRaisesRegex(ValueError,'already running'):c.start(frames=False,)
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
                with self.assertRaisesRegex(ValueError,'Cannot start original friendly'):c.start(frames=False,)
                self.assertIsNone(c.process);self.assertFalse(c.busy);self.assertFalse(m.match_pending)
                self.assertEqual(m.state,before)
            finally:c.close()
            from goal2.desktop.model import DesktopModel
            m=DesktopModel.open(ROOT/'.cache/e0afff6751747233-e006-1000-r0001.sav',ROOT/'.cache/GOAL.DAT',Path(folder)/'unused',country=4)
            before=copy.deepcopy(m.state);c=WatchedController(m)
            try:
                with self.assertRaisesRegex(ValueError,'Cannot start original friendly:.*extra time'):c.start(frames=False,)
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
                        try:c.start(frames=False,)
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
                    c.start(frames=False,);viewer=c.process;engine=c.engine.process
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
                    c.start(frames=False,);viewer=c.process;engine=c.engine.process
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
        # [designed: #234] run_path does not add the helper's sibling import directory.
        original_path = sys.path[:]
        try:
            sys.path.insert(0, str(ROOT/'tools/desktop-ui'))
            acceptance=runpy.run_path(str(ROOT/'tools/desktop-ui/watched.py'))
            acceptance['main']()
        finally:
            sys.path[:] = original_path


class AcceptanceImportContextTests(unittest.TestCase):
    def test_direct_acceptance_load_restores_complete_import_path(self):
        import runpy
        original = sys.path[:]
        loader = runpy.run_path
        loaded = []
        def load(path):
            self.assertEqual(sys.path[0], str(ROOT/'tools/desktop-ui'))
            namespace = loader(path)
            loaded.append(namespace)
            def main():
                sys.path.append('acceptance-main-mutation')
                return 'bounded'
            return {**namespace, 'main':main}
        try:
            with patch.object(runpy, 'run_path', load):
                OriginalQtAcceptance().test_original_qt_save_resume_repeat()
            self.assertEqual(len(loaded), 1)
            self.assertTrue(callable(loaded[0]['main']))
            self.assertEqual(sys.path, original)
        finally:
            sys.path[:] = original

    def test_acceptance_exception_restores_complete_import_path(self):
        import runpy
        original = sys.path[:]
        failure = RuntimeError('bounded acceptance failure')
        def load(path):
            sys.path.insert(0, 'acceptance-loader-mutation')
            raise failure
        try:
            with patch.object(runpy, 'run_path', load):
                with self.assertRaises(RuntimeError) as caught:
                    OriginalQtAcceptance().test_original_qt_save_resume_repeat()
            self.assertIs(caught.exception, failure)
            self.assertEqual(sys.path, original)
        finally:
            sys.path[:] = original
