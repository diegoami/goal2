"""[designed: T170ac/#810] Actual retained driver/SDK equality and pitch paint.

Full backend computation remains PyPy-only. Public logs contain digests/counts.
"""
import copy
from dataclasses import asdict
import hashlib
import json
from pathlib import Path
import queue
import tempfile
import time
from types import SimpleNamespace
import unittest

from goal2.game.native_driver import NativeMatchDriver
from goal2.game.native_season import NativeSeasonOwner
from goal2.game.season import canonical_hash
from goal2.game.watched_jobs import MatchEngine
from goal2.tests import pypy_engine,requires
from goal2.tests.test_prematch_preview_t170s import reference_raw
from goal2.tests.test_season_news_wire_t170t import digest


class Answers:
    def __init__(self):self.edited=False
    def __call__(self,data):
        context=data.get('context')
        if context=='pre_match':return {'captain':None}
        if context=='pause' and not self.edited:
            self.edited=True
            return dict(edit_only=True,tactics={1:not bool(data['tactics']&1)})
        if context=='substitution_opportunity':return {'opportunity':'dismiss'}
        if context=='set_piece':return {'taker':None}
        return {}


def direct(raw):
    import sys
    from goal2.engine.original_match.image import Image
    from goal2.engine.original_match.machine import MEM_SIZE,REGS,Uc
    from goal2.game import engine_tables
    from goal2.game.season import SeasonSession
    from goal2.game.prematch_seam import PrematchSeam
    from goal2.game.watched_pitch import snapshot
    assert sys.implementation.name=='pypy' and sys.version_info[:2]==(3,11) and Uc is None
    initial=Image.from_bytes(raw).state(engine_tables.load());session=SeasonSession(initial)
    session.advance();boundary=canonical_hash(session.state);match=session.pending_match;identity=id(match)
    PrematchSeam(match,frames=True);events=[];frames=[];answers=Answers();pauses=0
    for event in match.events():
        if event.kind=='tick':
            frames.append(snapshot(match,event,len(frames),len(events)))
            if len(frames)==1:match.pause();pauses+=1
        else:events.append(asdict(event))
        if event.kind=='decision':match.answer(**answers(event.data))
        assert id(session.pending_match)==identity
    memory=hashlib.sha256(match.m.read(0,MEM_SIZE)).hexdigest();all16=[match.m.reg(r) for r in REGS]
    obs=session.resume(match)
    return dict(events_hash=digest(events),frames_hash=digest(frames),events=len(events),frames=len(frames),
        boundary_hash=boundary,memory_hash=memory,all16=all16,state_hash=canonical_hash(session.state),
        observation_hash=digest(asdict(obs)),status=obs.status,pauses=pauses,edited=answers.edited)


class Actual(unittest.TestCase):
    def until(self,condition,step=None,limit=120):
        end=time.monotonic()+limit
        while time.monotonic()<end:
            if step:step()
            if condition():return
            time.sleep(.001)
        self.fail('native driver operation did not settle')

    def prepare(self,owner,state,**options):
        native=NativeSeasonOwner(owner,state,frames=True,**options)
        def cleanup():native.close();self.until(lambda:native.disposed,limit=15)
        self.addCleanup(cleanup)
        self.until(lambda:native.status in ('boundary','lost'),native.poll)
        self.assertEqual(native.status,'boundary',native.message);native.take_observations()
        native.advance();self.until(lambda:native.status in ('prematch','lost'),native.poll)
        self.assertEqual(native.status,'prematch',native.message)
        observed=native.take_observations();prefix=native.take_entry_events();controller=native.controller
        controller.play(captain=None)
        def poll():
            try:controller.receive(*native.replies.get_nowait())
            except queue.Empty:pass
        self.until(lambda:not controller.pending,poll)
        self.assertEqual(controller.status,'handoff',controller.message);prefix.extend(controller.take_events())
        driver=NativeMatchDriver(native);self.assertEqual(len(prefix),driver.event_base)
        return native,driver,prefix,observed[-1]

    @requires.need(slow=True)
    def test_complete_pause_edit_paced_driver_and_resume_equal_direct_sdk(self):
        from goal2.engine.original_match.image import Image
        from goal2.game import engine_tables
        from goal2.game.engine_python import engine_python
        raw=reference_raw();expected=pypy_engine.call(__name__+':direct',raw)
        initial=Image.from_bytes(raw).state(engine_tables.load())
        tmp=tempfile.TemporaryDirectory(prefix='goal2-native-driver-proof-');self.addCleanup(tmp.cleanup)
        proof=Path(tmp.name)/'cpu.json';owner=SimpleNamespace(state='unchanged');keeper=object()
        shared=MatchEngine.join(owner,keeper);self.addCleanup(shared.leave,owner,keeper)
        script='''import hashlib,json,sys
from pathlib import Path
from goal2.game.engine_server import Server,main
from goal2.engine.original_match.machine import MEM_SIZE,REGS,Uc
assert sys.implementation.name=='pypy' and sys.version_info[:2]==(3,11) and Uc is None
real=Server.send
def send(self,kind,value=None,payload=b''):
    if kind=='season' and isinstance(value,dict) and value.get('action')=='next' and value.get('exhausted'):
        m=self.season.session.pending_match
        Path(sys.argv[1]).write_text(json.dumps(dict(memory_hash=hashlib.sha256(m.m.read(0,MEM_SIZE)).hexdigest(),all16=[m.m.reg(r) for r in REGS])))
    return real(self,kind,value,payload)
Server.send=send
raise SystemExit(main())
'''
        shared.engine.command=[engine_python(),'-u','-c',script,str(proof)]
        native,driver,prefix,boundary=self.prepare(owner,initial);pid=native.pid;answers=Answers();requested=False
        now=0.;end=time.monotonic()+900
        while time.monotonic()<end:
            now+=1.;sample=driver.tick(now)
            if sample is not None:
                driver.painted(sample['sequence'])
                if not requested:self.assertTrue(driver.request_pause());requested=True
            if driver.status=='decision':driver.answer(answers(driver.waiting['event']['data']))
            if driver.status=='complete':break
            self.assertNotIn(driver.status,('lost','closed'),driver.error)
            self.assertEqual(native.pid,pid);time.sleep(.0005)
        self.assertEqual(driver.status,'complete',driver.error);self.assertTrue(answers.edited)
        self.assertEqual(driver.pause_requests,1);self.assertEqual(driver.dropped_pauses,0)
        driver.resume();self.until(lambda:driver.status in ('resumed','lost'),lambda:driver.tick(now+10))
        self.assertEqual(driver.status,'resumed',driver.error)
        packets=native.take_observations();self.assertEqual(len(packets),1);self.assertEqual(native.take_observations(),[])
        result=json.loads(proof.read_text())
        result.update(events_hash=digest(prefix+driver.events),frames_hash=digest(driver.frames),
            events=len(prefix)+len(driver.events),frames=len(driver.frames),boundary_hash=canonical_hash(boundary['state']),
            state_hash=canonical_hash(native.boundary_state),observation_hash=digest(packets[0]['observation']),
            status=packets[0]['observation']['status'],pauses=driver.pause_requests,edited=answers.edited)
        self.assertEqual(result,expected);self.assertEqual(owner.state,'unchanged')
        self.assertEqual(native.pid,pid);self.assertIs(shared.match,native)
        self.assertEqual(shared.engine.generation,1);self.assertEqual(native.status,'boundary')
        with self.assertRaises(ValueError):driver.resume()
        driver.close();self.assertFalse(native.disposed)
        print('T170AC_FULL '+json.dumps(result,sort_keys=True),flush=True)


@requires.need(modules=('PySide6',),files=('GOAL.DAT',))
class Pitch(Actual):
    # The full test above is deliberately not inherited into the fast UI proof.
    test_complete_pause_edit_paced_driver_and_resume_equal_direct_sdk=None

    def test_actual_pitch_paints_acknowledged_samples_and_holds_backend_when_reading(self):
        from PySide6.QtCore import QTimer
        from PySide6.QtWidgets import QApplication
        from goal2.data.goaldat import load
        from goal2.desktop.model import DesktopModel
        from goal2.desktop.match_view import Display
        from goal2.desktop.watched import pitch_identity
        from goal2.engine.original_match.image import Image
        from goal2.game import engine_tables
        from goal2.ui.pitch import PitchWidget
        from goal2.ui.kits import compute
        from goal2.ui import theme
        root=Path(__file__).resolve().parents[2];raw=reference_raw()
        tmp=tempfile.TemporaryDirectory(prefix='goal2-driver-paint-');self.addCleanup(tmp.cleanup)
        model=DesktopModel(load((root/'.cache/GOAL.DAT').read_bytes()),raw,Path(tmp.name)/'unused')
        initial=Image.from_bytes(raw).state(engine_tables.load())
        native,driver,prefix,boundary=self.prepare(model,initial)
        # Display metadata only; this state is never used to construct/run the Match.
        # The pre-match controller keeps its verified view through handoff.
        model.state=native.controller.view.display_state()
        app=QApplication.instance() or QApplication([]);theme.install(app)
        display=Display('native-paint');display.accept(['native-paint',0,'start',pitch_identity(model,native.fixture)])
        display.accept(['native-paint',1,'pitch',{'rate':60}]);widget=PitchWidget(lambda:display,driver.painted,theme.load_font())
        image=Image.from_memory_component(model.state.mem)
        widget.kits=compute(lambda off:image.rd(off,1),native.fixture.side_a,native.fixture.side_b)
        widget.resize(1000,560);widget.show();self.addCleanup(lambda:(widget.close(),widget.deleteLater(),app.processEvents()))
        beats=[];timer=QTimer();timer.setInterval(2);timer.timeout.connect(lambda:beats.append(True));timer.start();self.addCleanup(timer.stop)
        end=time.monotonic()+120;now=0.
        while driver.painted_sequence<9 and time.monotonic()<end:
            now+=1;sample=driver.tick(now)
            if sample is not None:display.frame=sample;widget.update()
            if driver.status=='decision':driver.answer({})
            app.processEvents();self.assertNotEqual(driver.status,'lost',driver.error);time.sleep(.001)
        self.assertGreaterEqual(driver.painted_sequence,9);self.assertGreater(len(widget.painted),0);self.assertGreater(len(beats),2)
        count=len(driver.frames);driver.set_held(True)
        for _ in range(10):driver.tick(now+100);app.processEvents()
        self.assertEqual(len(driver.frames),count)
        self.assertEqual(native.shared.engine.generation,1)


if __name__=='__main__':unittest.main()
