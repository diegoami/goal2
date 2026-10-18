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
            self.assertTrue(any(event.type==pygame.QUIT for event in pygame.event.get()))
        finally:pygame.quit()

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
                with self.assertRaisesRegex(ValueError,'already running'):QuickJobs(m).start()
                with self.assertRaisesRegex(ValueError,'Saving during'):m.save(m.save_path)
                self.assertEqual(m.state,before);self.assertEqual(m.save_path.read_bytes(),saved)
                started=time.monotonic();c.cancel();c.cancel()
                self.assertLess(time.monotonic()-started,2)
                self.assertIsNotNone(viewer.poll());self.assertIsNotNone(engine.poll())
                self.assertEqual(m.state,before);self.assertEqual(m.save_path.read_bytes(),saved)
            finally:c.close()
            c=WatchedController(m,viewer_command=['/nonexistent/goal2-viewer'])
            try:
                with self.assertRaises(OSError):c.start()
                self.assertIsNone(c.process);self.assertFalse(c.busy);self.assertFalse(m.match_pending)
                self.assertEqual(m.state,before)
            finally:c.close()

    def test_malformed_stale_ack_and_engine_failure_preserve_state(self):
        from goal2.tests.test_watched_jobs import CONTROLLED
        for mode in ('malformed','stale','guest','closed'):
            with self.subTest(mode=mode),tempfile.TemporaryDirectory() as folder:
                m=model(Path(folder)/'save');before=copy.deepcopy(m.state)
                script="import time;time.sleep(60)"
                c=WatchedController(m,viewer_command=[sys.executable,'-c',script],engine_command=[sys.executable,'-c',CONTROLLED,'guest' if mode=='guest' else 'blocked'])
                try:
                    c.start();viewer=c.process;engine=c.engine.process
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
