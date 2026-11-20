"""[designed: T170ab/#808] Actual parent pitch feed and retained owner handoff."""
import json
from pathlib import Path
import queue
import tempfile
import time
from types import SimpleNamespace
import unittest

from goal2.tests import requires,pypy_engine
from goal2.tests import test_season_worker_t170o as wire
from goal2.tests.test_prematch_preview_t170s import reference_raw
from goal2.tests.test_season_news_wire_t170t import digest
from goal2.tests.test_season_pitch_t170ab import full_run,policy
from goal2.game.season import canonical_hash


class Pipe(unittest.TestCase):
    make_engine=wire.Pipe.make_engine
    receive=wire.Pipe.receive

    @requires.need(slow=True)
    def test_full_parent_feed_resume_news_equals_direct_sdk_and_actual_final_cpu(self):
        from goal2.engine.original_match.image import Image
        from goal2.game import engine_tables
        from goal2.game.engine_python import engine_python
        raw=reference_raw();expected=pypy_engine.call('goal2.tests.test_season_pitch_t170ab:full_run',raw,False,True)
        initial=Image.from_bytes(raw).state(engine_tables.load())
        folder=tempfile.TemporaryDirectory(prefix='goal2-native-pitch-proof-');self.addCleanup(folder.cleanup)
        proof=Path(folder.name)/'proof.json'
        # Read-only test observer in the actual PyPy server. No protocol fields,
        # source fixtures, answers or engine state are modified by this witness.
        script='''import hashlib,json,sys
from pathlib import Path
from goal2.game.engine_server import Server,main
from goal2.engine.original_match.machine import MEM_SIZE,REGS,Uc
assert sys.implementation.name=='pypy' and sys.version_info[:2]==(3,11) and Uc is None
real=Server.send
def send(self,kind,value=None,payload=b''):
    if kind=='season' and isinstance(value,dict) and value.get('action')=='next' and value.get('exhausted'):
        m=self.season.session.pending_match
        data=dict(memory_hash=hashlib.sha256(m.m.read(0,MEM_SIZE)).hexdigest(),all16=[m.m.reg(r) for r in REGS])
        Path(sys.argv[1]).write_text(json.dumps(data))
    return real(self,kind,value,payload)
Server.send=send
raise SystemExit(main())
'''
        engine=self.make_engine([engine_python(),'-u','-c',script,str(proof)])
        engine.season_open(initial);ready=self.receive('ready');self.assertEqual(ready['version'],[3,11]);self.receive('season')
        engine.season_request('advance');boundary=self.receive('season');pid=engine.pid
        engine.season_request('configure',frames=True);self.receive('season')
        events=[];frames=[]
        while True:
            engine.season_request('next',count=32);p=self.receive('season')
            self.assertEqual(p['event_count'],len(events)+len(p['events']))
            self.assertLessEqual(len(p['events'])+len(p['frames']),32)
            events.extend(p['events']);frames.extend(p['frames'])
            self.assertEqual(engine.pid,pid)
            if p['decision'] is not None:
                engine.season_request('answer',decision=p['decision'],answer=policy(p['events'][-1]['data']))
                self.receive('season')
            if p['exhausted']:break
        actual=json.loads(proof.read_text());engine.season_request('resume');resumed=self.receive('season')
        actual.update(events_hash=digest(events),frames_hash=digest(frames),events=len(events),frames=len(frames),
            boundary_hash=canonical_hash(boundary['state']),state_hash=canonical_hash(resumed['state']),
            observation_hash=digest(resumed['observation']))
        for key,value in actual.items():self.assertEqual(value,expected[key],key)
        self.assertGreater(len(frames),0);self.assertTrue(resumed['observation']['news_pages'])
        for _ in range(2):
            engine.season_request('observe');seen=self.receive('season')
            self.assertEqual(canonical_hash(seen['state']),actual['state_hash'])
            self.assertEqual(seen['observation']['news_pages'],());self.assertEqual(seen['observation']['played_fixtures'],())
        self.assertEqual(engine.pid,pid);self.assertFalse(engine._season_pitch)
        print('T170AB_PIPE '+json.dumps(actual,sort_keys=True),flush=True)


class Owner(unittest.TestCase):
    def until(self,condition,step=None,limit=120):
        end=time.monotonic()+limit
        while time.monotonic()<end:
            if step:step()
            if condition():return
            time.sleep(.002)
        self.fail('native pitch owner did not settle')

    def test_actual_optin_owner_edit_play_first_feed_and_disposal_share_one_child(self):
        from goal2.game.native_season import NativeSeasonOwner
        from goal2.engine.original_match.image import Image
        from goal2.game import engine_tables
        initial=Image.from_bytes(reference_raw()).state(engine_tables.load())
        owner=SimpleNamespace();native=NativeSeasonOwner(owner,initial,frames=True)
        def cleanup():native.close();self.until(lambda:native.disposed,limit=15)
        self.addCleanup(cleanup)
        self.until(lambda:native.status in ('boundary','lost'),native.poll)
        self.assertEqual(native.status,'boundary',native.message);native.advance()
        self.until(lambda:native.status in ('prematch','lost'),native.poll)
        self.assertEqual(native.status,'prematch',native.message);pid=native.pid;controller=native.controller
        before=canonical_hash(native.boundary_state)
        controller.set_team_tactic(1,not bool(controller.view.countries[controller.managed_country][0x2D]&1))
        def poll():
            try:controller.receive(*native.replies.get_nowait())
            except queue.Empty:pass
        self.until(lambda:not controller.pending,poll);self.assertEqual(controller.status,'ready',controller.message)
        controller.play(captain=None);self.until(lambda:not controller.pending,poll)
        self.assertEqual(controller.status,'handoff',controller.message);connection=native.handoff();p=connection.packet
        self.assertIn('frames',p);self.assertIn('event_count',p)
        while not p['frames']:
            if p['decision'] is not None:
                connection.send('answer',decision=p['decision'],answer=policy(p['events'][-1]['data']))
                kind,answer=native.replies.get(timeout=120);self.assertEqual((kind,answer['action']),('season','answer'))
            connection.send('next',count=32)
            kind,p=native.replies.get(timeout=120);self.assertEqual(kind,'season')
        self.assertEqual(p['frames'][0]['sequence'],0);self.assertEqual(p['frames'][0]['version'],2)
        self.assertEqual(len(p['frames'][0]['players']),22);self.assertEqual(native.pid,pid)
        self.assertIs(native.shared.match,native);self.assertEqual(canonical_hash(native.boundary_state),before)
        self.assertEqual(native.shared.engine.generation,1)


if __name__=='__main__':unittest.main()
