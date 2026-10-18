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
        self.put([sample(n) for n in range(100)])
        returned=[]
        while len(returned)<100:
            batch=self.jobs.poll_frames(self.token)
            self.assertLessEqual(len(batch),FRAME_POLL_BUDGET)
            self.assertLessEqual(len(self.jobs._frame_buffer),FRAME_READ_BUDGET+MAX_FRAME_PACKET)
            returned.extend(batch)
        self.assertEqual([f['sequence'] for f in returned],list(range(100)))
        self.assertEqual(self.jobs.events,[])
        self.jobs.ack_frames(self.token,99)
        for token,seq in [('stale',99),(self.token,99),(self.token,100),(self.token,True)]:
            with self.assertRaisesRegex(ValueError,'stale|invalid'):self.jobs.ack_frames(token,seq)
        self.assertTrue(self.jobs.busy)
        self.assertEqual(self.owner.state,self.before)

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


class OriginalPitchJobsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        adapter.WatchedAdapter.setUpClass();cls.raw=adapter.WatchedAdapter.raw

    def state(self):return adapter.WatchedAdapter.state(self)

    def test_actual_original_parity_movement_halves_pending_and_once_only(self):
        from PySide6.QtCore import QCoreApplication, QTimer
        app=QCoreApplication.instance() or QCoreApplication([])
        beats=[];timer=QTimer();timer.timeout.connect(lambda:beats.append(1));timer.start(1)
        try:
            for seed in (257,4660):
                owner=Owner(self.state(),self.raw);before=copy.deepcopy(owner.state)
                expected=run_watched_match(before,self.raw,Fixture(7,19,21),reference_seed=seed,delay_byte=0,record_draws=True)
                jobs=WatchedJobs(owner)
                try:
                    token=jobs.start(Fixture(7,19,21),reference_seed=seed,delay_byte=0,record_draws=True,frames=True)
                    events=[];frames=[];deadline=time.monotonic()+600
                    while not jobs.engine_complete:
                        self.assertLess(time.monotonic(),deadline,'actual original did not finish')
                        app.processEvents();events.extend(jobs.poll(token))
                        # [designed] Deliberately leave child finished before consuming any pose.
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
                    self.assertEqual(len(frames),expected.result['ticks'])
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
                    events.extend(jobs.poll(token))
                    self.assertFalse(jobs.busy);self.assertEqual(jobs.outcome,expected)
                    self.assertEqual(owner.state.mem,expected.memory)
                    self.assertEqual(owner.state.match_count,1)
                    self.assertNotIn('frames',owner.state.last_match)
                    with self.assertRaisesRegex(ValueError,'consumed'):jobs.ack_frames(token,len(frames)-1)
                    print(f'T82 actual seed={seed} frames={len(frames)} events={len(events)} memory_sha256={hashlib.sha256(expected.memory).hexdigest()} seeds={expected.seeds}',flush=True)
                finally:jobs.close()
            self.assertGreater(len(beats),100,'Qt heartbeat must remain live')
        finally:timer.stop()
