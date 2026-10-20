"""[designed: T82] Actual original parity and synthetic hostile/slow-consumer tests."""
import copy
import hashlib
import json
from pathlib import Path
import struct
import time
import unittest
from unittest.mock import patch

from goal2.engine.original_match import Fixture
from goal2.game.watched_jobs import WatchedJobs
from goal2.game.watched_match import run_watched_match
from goal2.game.watched_pitch import (snapshot, validate, write_frame, MAX_FRAME_BYTES,
    MAX_FRAME_PACKET, MAX_FRAMES, FRAME_READ_BUDGET, FRAME_POLL_BUDGET)
from goal2.tests.test_watched_publication import Owner
from goal2.tests import test_watched_adapter as adapter
from goal2.tests import requires

ROOT = Path(__file__).resolve().parents[2]


def sample(sequence=0, watermark=0):
    return dict(version=1,sequence=sequence,watermark=watermark,minute=1,score=[0,0],
        subtick=36,threshold=45,remaining=91,selector=1,attack=[1,-1],sentinel=11,
        ball=[-8,1,False],players=[[s,int(s<=11),s if s<=11 else s-11,100+s,
                                  -9,0,13,False] for s in range(1,23)])


class PitchTransportTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        adapter.WatchedAdapter.setUpClass()
        cls.raw = adapter.WatchedAdapter.raw

    def setUp(self):
        self.owner=Owner(adapter.WatchedAdapter.state(self),self.raw)
        self.before=copy.deepcopy(self.owner.state)
        self.jobs=WatchedJobs(self.owner,command=['/bin/sleep','60'])
        self.token=self.jobs.start(Fixture(7,19,21),frames=True)
        self.process=self.jobs.process
        # [designed] Synthetic file injection never impersonates an actual original run.
        self.process.terminate();self.process.wait(timeout=2)
        self.alive=patch.object(self.process,'poll',return_value=None)
        self.alive.start()

    def tearDown(self):
        self.alive.stop()
        self.jobs.close()

    def put(self, frames):
        with open(self.jobs._frames.name,'ab') as f:
            for frame in frames:write_frame(f,self.token,frame)

    def reject(self, message):
        with self.assertRaisesRegex(ValueError,message):self.jobs.poll_frames(self.token)
        self.assertFalse(self.jobs.busy)
        self.assertEqual(self.owner.state,self.before)

    def test_separate_bounded_consumer_and_ack_order(self):
        self.put([sample(n) for n in range(300)])
        returned=[]
        while len(returned)<300:
            batch=self.jobs.poll_frames(self.token)
            self.assertLessEqual(len(batch),FRAME_POLL_BUDGET)
            self.assertLessEqual(len(self.jobs._frame_buffer),FRAME_READ_BUDGET+MAX_FRAME_PACKET)
            returned.extend(batch)
        self.assertEqual([f['sequence'] for f in returned],list(range(300)))
        self.assertEqual(self.jobs.events,[])
        self.jobs.ack_frames(self.token,299)
        for token,seq in [('stale',299),(self.token,299),(self.token,300),(self.token,True)]:
            with self.assertRaisesRegex(ValueError,'stale|invalid'):self.jobs.ack_frames(token,seq)
        self.assertTrue(self.jobs.busy)
        self.assertEqual(self.owner.state,self.before)

    def test_deferred_once_only_publication(self):
        from types import SimpleNamespace
        self.put([sample()])
        self.jobs._complete=SimpleNamespace(result={'ticks':1})
        self.jobs._engine_done=True
        with patch.object(self.jobs.publication,'publish_prepared',wraps=self.jobs.publication.publish_prepared) as complete, patch('goal2.game.watched_publication.completed_candidate',return_value=copy.deepcopy(self.before)):
            self.jobs._maybe_publish(self.token)
            self.assertTrue(self.jobs.busy,'publication must wait for frame delivery')
            self.assertEqual(len(self.jobs.poll_frames(self.token)),1)
            self.assertTrue(self.jobs.busy,'publication must wait for consumption acknowledgement')
            complete.assert_not_called()
            with self.assertRaisesRegex(ValueError,'invalid'):self.jobs.ack_frames(self.token,1)
            self.jobs.ack_frames(self.token,0)
            self.jobs._maybe_publish(self.token)
            deadline=time.monotonic()+5
            while self.jobs.busy:
                self.jobs._maybe_publish(self.token)
                self.assertLess(time.monotonic(),deadline,'owned candidate preparation did not finish')
                time.sleep(.001)
            complete.assert_called_once()
            self.assertFalse(self.jobs.busy)
            self.assertFalse(self.owner.match_pending)
            with self.assertRaisesRegex(ValueError,'consumed'):self.jobs.ack_frames(self.token,0)

    def test_cancel_after_engine_done_keeps_pending_state_and_prior_save(self):
        self.put([sample()]);self.jobs._engine_done=True
        self.assertTrue(self.owner.match_pending)
        with patch.object(self.jobs.publication,'publish_prepared') as complete, patch.object(self.jobs.publication,'prepare_completion') as prepare:
            self.jobs.close();complete.assert_not_called();prepare.assert_not_called()
        self.assertFalse(self.owner.match_pending)
        self.assertEqual(self.owner.state,self.before)
        self.assertIsNone(self.jobs.publication._pending)

    def test_completed_frame_count_must_match_original_ticks(self):
        from types import SimpleNamespace
        self.put([sample()]);self.jobs._engine_done=True
        self.jobs._complete=SimpleNamespace(result={'ticks':2})
        self.reject('count differs')

    def test_partial_tail_read_is_bounded(self):
        self.put([sample(n) for n in range(80)])
        with open(self.jobs._frames.name,'ab') as f:f.write(struct.pack('!I',2000)+b'{')
        count=0
        while count<80:
            frames=self.jobs.poll_frames(self.token);count+=len(frames)
            self.assertLessEqual(len(frames),FRAME_POLL_BUDGET)
            self.assertLessEqual(len(self.jobs._frame_buffer),FRAME_READ_BUDGET+MAX_FRAME_PACKET)
        self.assertEqual(count,80)
        self.assertEqual(self.jobs.poll_frames(self.token),[])
        self.jobs._engine_done=True
        self.reject('truncated')

    def test_token_rejection(self):
        with open(self.jobs._frames.name,'ab') as f:write_frame(f,'wrong',sample())
        self.reject('token differs')

    def test_sequence_rejection(self):
        self.put([sample(1)])
        self.reject('order/watermark')

    def test_schema_rejection(self):
        value=sample();value['players'][0][4]=128
        self.put([value]);self.reject('frame player')

    def test_watermark_regression_rejection(self):
        from goal2.engine.original_match.match import Event
        self.jobs.events=[Event('minute',1,(0,0))]
        self.put([sample(0,1),sample(1,0)])
        self.reject('order/watermark')

    def test_future_watermark_waits_then_rejects_at_completion(self):
        self.put([sample(0,1)])
        self.assertEqual(self.jobs.poll_frames(self.token),[])
        self.assertEqual(self.jobs._frame_sequence,0)
        self.jobs._engine_done=True
        self.reject('watermark exceeds')

    def test_truncated_and_oversized_records(self):
        with open(self.jobs._frames.name,'ab') as f:f.write(struct.pack('!I',MAX_FRAME_PACKET+1))
        self.reject('packet budget')

    def test_truncated_record_after_engine_completion(self):
        with open(self.jobs._frames.name,'ab') as f:f.write(b'\x00\x00')
        self.jobs._engine_done=True
        self.reject('truncated')

    def test_malformed_json(self):
        with open(self.jobs._frames.name,'ab') as f:f.write(struct.pack('!I',1)+b'{')
        self.reject('Invalid watched pitch IPC')

    def test_total_buffer_overflow(self):
        with open(self.jobs._frames.name,'ab') as f:f.truncate(MAX_FRAME_BYTES+1)
        self.reject('total budget')

    def test_writer_packet_total_and_count_budgets(self):
        import io
        for mode in ('packet','total','count'):
            value=sample();f=io.BytesIO()
            if mode=='packet':value['extra']='x'*MAX_FRAME_PACKET
            if mode=='total':f.seek(MAX_FRAME_BYTES)
            if mode=='count':value['sequence']=MAX_FRAMES
            with self.assertRaisesRegex(ValueError,'consumer too slow'):write_frame(f,self.token,value)

    def test_owned_death_and_worker_error_cancel_without_publication(self):
        import subprocess
        from goal2.game.watched_jobs import _write
        sibling=subprocess.Popen(['/bin/sleep','60'])
        try:
            with open(self.jobs._journal.name,'ab') as f:_write(f,self.token,0,'error','synthetic frame overflow')
            with self.assertRaisesRegex(ValueError,'synthetic frame overflow'):self.jobs.poll(self.token)
            self.assertIsNone(sibling.poll())
            self.assertFalse(self.owner.match_pending)
            self.assertEqual(self.owner.state,self.before)
        finally:
            sibling.terminate();sibling.wait(timeout=2)

    def test_child_death_without_completion_rejected(self):
        self.alive.stop()
        with self.assertRaisesRegex(ValueError,'without completion'):self.jobs.poll(self.token)
        self.assertEqual(self.owner.state,self.before)
        self.assertFalse(self.owner.match_pending)

    def test_cancel_close_and_owned_child_death_preserve_prior_save(self):
        from goal2.game.session_save import save
        import tempfile
        with tempfile.TemporaryDirectory() as folder:
            target=Path(folder)/'prior';save(target,self.owner.state,self.raw)
            before=target.read_bytes()
            self.put([sample()]);self.jobs.poll_frames(self.token)
            self.jobs.close()
            self.assertIsNotNone(self.process.returncode)
            self.assertEqual(self.owner.state,self.before)
            self.assertEqual(target.read_bytes(),before)
        with self.assertRaisesRegex(ValueError,'consumed'):self.jobs.ack_frames(self.token,0)

    def state(self):return adapter.WatchedAdapter.state(self)


class PitchObservationTests(unittest.TestCase):
    def test_raw_signed_identity_visibility_and_generic_countries(self):
        from types import SimpleNamespace
        from goal2.engine.original_match.match import PITCH, PITCH_SIZE, BALL, Event
        memory=bytearray(65536)
        def word(offset,value):memory[offset:offset+2]=value.to_bytes(2,'little')
        word(0x0640,11);word(0x831B,45);memory[0x8319]=255
        memory[0x7920:0x7922]=bytes([1,255])
        squads={2:list(range(201,212)),4:list(range(401,412))}
        for slot in range(1,23):
            pos=PITCH+PITCH_SIZE*slot
            memory[pos:pos+2]=bytes([128,127])
            memory[pos+6]=slot;memory[pos+18]=255
            word(pos+13,squads[4 if slot<=11 else 2][(slot-1)%11])
        memory[PITCH+PITCH_SIZE:PITCH+PITCH_SIZE+2]=bytes([11,0])
        memory[BALL:BALL+2]=bytes([11,0])
        class Machine:
            DS=0
            def read(self,pos,size):return bytes(memory[pos:pos+size])
            def rd(self,pos,size=2):return int.from_bytes(self.read(pos,size),'little')
        match=SimpleNamespace(m=Machine(),opts={'first':2,'second':4},_squad=lambda country:squads[country])
        frame=snapshot(match,Event('tick',46,(2,1)),0,7)
        self.assertEqual(frame['players'][0],[1,1,1,401,11,0,255,True])
        self.assertEqual(frame['players'][11],[12,0,1,201,-128,127,255,False])
        self.assertEqual(frame['ball'],[11,0,True]);self.assertEqual(frame['selector'],1)
        self.assertEqual(frame['attack'],[-1,1]);validate(frame,0,0)
        memory[PITCH+PITCH_SIZE+1]=1;memory[BALL+1]=1
        squads[4][0]=999;word(PITCH+PITCH_SIZE+13,999)
        rebound=snapshot(match,Event('tick',46,(2,1)),1,7)
        self.assertEqual(rebound['players'][0],[1,1,1,999,11,1,255,False])
        self.assertEqual(rebound['ball'],[11,1,False])


class OriginalPitchJobsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        adapter.WatchedAdapter.setUpClass();cls.raw=adapter.WatchedAdapter.raw

    def state(self):return adapter.WatchedAdapter.state(self)

    @requires.need(slow=True)  # [designed: #275] about 68 s alone on 32 CPUs
    def test_actual_finished_cancel_and_close_preserve_prior_save(self):
        from goal2.desktop.model import DesktopModel
        from goal2.game.session_save import save
        import tempfile
        for mode in ('cancel','close'):
            owner=Owner(self.state(),self.raw);before=copy.deepcopy(owner.state)
            jobs=WatchedJobs(owner)
            with tempfile.TemporaryDirectory() as folder:
                target=Path(folder)/'prior';save(target,owner.state,self.raw);prior=target.read_bytes()
                try:
                    token=jobs.start(Fixture(7,19,21),reference_seed=257,delay_byte=0,frames=True)
                    deadline=time.monotonic()+600
                    while not jobs.engine_complete:
                        self.assertLess(time.monotonic(),deadline,'actual original did not finish')
                        jobs.poll(token);time.sleep(.002)
                    self.assertIsNotNone(jobs.process.poll());self.assertTrue(owner.match_pending)
                    with self.assertRaisesRegex(ValueError,'Saving during a match'):DesktopModel.save(owner,target)
                    self.assertEqual(target.read_bytes(),prior)
                    jobs.cancel(token) if mode=='cancel' else jobs.close()
                    self.assertEqual(owner.state,before);self.assertFalse(owner.match_pending)
                    save(target,owner.state,self.raw);self.assertEqual(target.read_bytes(),prior)
                finally:jobs.close()

    @requires.need(slow=True)  # [designed: #275] about 178 s alone on 32 CPUs
    def test_actual_original_parity_movement_halves_pending_and_once_only(self):
        from PySide6.QtCore import QCoreApplication, QTimer
        app=QCoreApplication.instance() or QCoreApplication([])
        beats=[];timer=QTimer();timer.timeout.connect(lambda:beats.append(1));timer.start(1)
        try:
            for seed in (257,4660):
                owner=Owner(self.state(),self.raw);before=copy.deepcopy(owner.state)
                expected=run_watched_match(before,self.raw,Fixture(7,19,21),reference_seed=seed,delay_byte=0,record_draws=True)
                from goal2.game.watched_match import _drive_match, prepare_watched
                oracle=[]
                def check_raw(match,event,sequence,watermark):
                    from goal2.engine.original_match.match import PITCH, PITCH_SIZE, BALL
                    frame=snapshot(match,event,sequence,watermark)
                    self.assertEqual(event.kind,'tick')
                    for slot,player in enumerate(frame['players'],1):
                        raw=match.m.read(match.m.DS*16+PITCH+PITCH_SIZE*slot,PITCH_SIZE)
                        side=0 if slot>11 else 1;local=(slot-1)%11+1
                        self.assertEqual(player[:4],[raw[6],side,local,int.from_bytes(raw[13:15],'little')])
                        self.assertEqual(player[3],match._squad((7,19)[side])[local-1])
                        self.assertEqual(player[4:7],[int.from_bytes(raw[:1],'little',signed=True),int.from_bytes(raw[1:2],'little',signed=True),raw[18]])
                        self.assertEqual(player[7],int.from_bytes(raw[:2],'little')==match.m.rd(0x0640))
                    ball=match.m.read(match.m.DS*16+BALL,2)
                    self.assertEqual(frame['ball'],[int.from_bytes(ball[:1],'little',signed=True),int.from_bytes(ball[1:],'little',signed=True),int.from_bytes(ball,'little')==match.m.rd(0x0640)])
                    oracle.append(frame)
                    return frame
                with patch('goal2.game.watched_pitch.snapshot',side_effect=check_raw):
                    observed=_drive_match(before,prepare_watched(before,self.raw,Fixture(7,19,21)),Fixture(7,19,21),reference_seed=seed,delay_byte=0,record_draws=True,_observe_pitch=lambda f:None)
                self.assertEqual(observed,expected)
                jobs=WatchedJobs(owner)
                try:
                    token=jobs.start(Fixture(7,19,21),reference_seed=seed,delay_byte=0,record_draws=True,frames=True)
                    events=[];frames=[];deadline=time.monotonic()+600
                    while not jobs.engine_complete:
                        self.assertLess(time.monotonic(),deadline,'actual original did not finish')
                        app.processEvents();events.extend(jobs.poll(token))
                        if seed == 4660:
                            batch=jobs.poll_frames(token)
                            for frame in batch:
                                self.assertLessEqual(frame['watermark'],len(events))
                                frames.append(frame)
                        # [designed] Seed257 leaves all poses unread until child exit; seed4660 reads live.
                        time.sleep(.002)
                    self.assertTrue(jobs.busy);self.assertIsNone(jobs.outcome)
                    self.assertEqual(owner.state,before)
                    self.assertIsNotNone(jobs.process.poll())
                    from goal2.desktop.model import DesktopModel
                    with self.assertRaisesRegex(ValueError,'Saving during a match'):
                        DesktopModel.save(owner, ROOT/'.cache'/'must-not-save-pending')
                    while True:
                        batch=jobs.poll_frames(token)
                        self.assertLessEqual(len(batch),FRAME_POLL_BUDGET)
                        self.assertLessEqual(len(jobs._frame_buffer),FRAME_READ_BUDGET+MAX_FRAME_PACKET)
                        for frame in batch:
                            validate(frame,len(frames),frames[-1]['watermark'] if frames else 0)
                            self.assertLessEqual(frame['watermark'],len(events))
                            frames.append(frame)
                        if not batch:break
                        app.processEvents()
                    self.assertEqual(frames,oracle)
                    self.assertEqual(len(frames),expected.result['ticks'])
                    self.assertGreater(sum(a['players'][i][3]!=b['players'][i][3] for a,b in zip(frames,frames[1:]) for i in range(22)),0)
                    self.assertEqual(owner.state,before)
                    self.assertEqual(tuple(events),expected.events)
                    self.assertEqual({f['selector'] for f in frames},{0,1})
                    for selector in (0,1):
                        part=[f for f in frames if f['selector']==selector]
                        self.assertGreater(sum(a['ball']!=b['ball'] for a,b in zip(part,part[1:])),100)
                        self.assertGreater(sum(a['players']!=b['players'] for a,b in zip(part,part[1:])),100)
                    self.assertEqual(frames[-1]['minute'],93 if seed==257 else 91)
                    jobs.ack_frames(token,len(frames)-1)
                    self.assertIsNone(jobs.outcome)
                    # [designed: #254] Final ACK permits private candidate preparation;
                    # retain the existing deadline and every final parity assertion.
                    while jobs.busy:
                        self.assertLess(time.monotonic(),deadline,'actual original completion did not finish')
                        app.processEvents();events.extend(jobs.poll(token))
                        time.sleep(.002)
                    self.assertFalse(jobs.busy);self.assertEqual(jobs.outcome,expected)
                    self.assertEqual(owner.state.mem,expected.memory)
                    self.assertEqual(owner.state.match_count,1)
                    self.assertNotIn('frames',owner.state.last_match)
                    from goal2.game.session_save import encode, decode
                    restored,_=decode(encode(owner.state,self.raw))
                    self.assertEqual(restored.last_match,owner.state.last_match)
                    with self.assertRaisesRegex(ValueError,'consumed'):jobs.ack_frames(token,len(frames)-1)
                    print(f'T82 actual seed={seed} frames={len(frames)} events={len(events)} memory_sha256={hashlib.sha256(expected.memory).hexdigest()} seeds={expected.seeds}',flush=True)
                finally:jobs.close()
            self.assertGreater(len(beats),100,'Qt heartbeat must remain live')
        finally:timer.stop()
