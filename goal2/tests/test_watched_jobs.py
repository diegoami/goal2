"""[designed: T65] Headless process, live observation and atomic ownership tests."""
import copy
import asyncio
from dataclasses import replace
import hashlib
import os
import signal
from pathlib import Path
import json
import struct
import sys
import time
import subprocess
import unittest
from unittest.mock import patch

from goal2.engine.original_match import Fixture, Image
from goal2.engine.original_match.match import Event
from goal2.game.watched_jobs import WatchedJobs, REPLY_BUDGET
from goal2.game.watched_match import FRIENDLY_SUBSTITUTIONS, _drive_match
from goal2.tests import test_watched_adapter as adapter
from goal2.tests.test_watched_publication import Owner
from goal2.tests import requires, pypy_engine

ROOT = Path(__file__).resolve().parents[2]

# [designed] Children use the real shared driver with a controlled original guest.
# [designed: T160] The child is the engine process (goal2.game.engine_server), as the window's.
CONTROLLED = r'''
import sys,json,time,signal
from unittest.mock import patch
from goal2.engine.original_match.match import Event
from goal2.game import engine_server
mode=sys.argv.pop(1)
if mode=='ignore':signal.signal(signal.SIGTERM,signal.SIG_IGN)
class Guest:
 def __init__(self,*args,**kwargs):self.answers=0;self.image=args[0];self.opts={}
 def events(self):
  if mode=='missing':raise ModuleNotFoundError('pip install unicorn')
  yield Event('minute',1,(0,0))
  if mode=='guest':raise RuntimeError('guest execution failed')
  yield Event('decision',46,(0,0),{'context':'unknown' if mode=='unsupported' else 'half_time','refused':mode=='refused'})
  if mode=='loop':yield Event('decision',46,(0,0),{'context':'half_time','refused':False})
  assert self.answers==1,'default answer missing'
  yield Event('commentary',46,(0,0),{'text':'after answer'})
  yield Event('decision',46,(0,0),{'context':'half_time','refused':False})
  assert self.answers==2,'second default answer missing'
  yield Event('full_time',90,(0,0))
  time.sleep(60)
  yield Event('end',90,(0,0))
 def answer(self):self.answers+=1
 def result(self):return {'complete':True}
 def memory_component(self):return self.image.memory_component()
with patch('goal2.game.watched_match.Match',Guest):sys.exit(engine_server.main())
'''

# [designed: T160] A stand-in engine: the protocol's framing and no match. It takes the game and a match request
# and sends nothing for it; a cancel is answered, `quit` or the end of stdin ends it. The tests deliver the match's
# replies themselves, as the engine's reader thread does (the job's _Match.put). With a mode in argv[1] it first
# sends, once the match is asked, the bytes that mode names.
IDLE = r'''
import os,struct,sys
from goal2.game.engine_server import read_packet, encode_packet
from goal2.game.session_save import _json_value
mode=sys.argv[1] if len(sys.argv)>1 else None
out=sys.stdout.buffer
def send(kind,value=None):out.write(encode_packet({'kind':kind,'value':_json_value(value)}));out.flush()
def event(**value):return dict(dict(kind='minute',minute=1,score=(0,0),data={}),**value)
BAD={
 'malformed':lambda:struct.pack('!I',1)+b'{',
 'unknown fields':lambda:encode_packet({'kind':'event','value':{'wrong':1}}),
 'event shape':lambda:encode_packet({'kind':'event','value':_json_value(event(kind=7))}),
 'truncated':lambda:b'\x00\x00',
 'oversized':lambda:struct.pack('!I',2**31),
}
send('ready',{'implementation':'stand-in','version':[0,0],'pid':os.getpid()})
while True:
 packet=read_packet(sys.stdin.buffer)
 if packet is None or packet[0]['op']=='quit':sys.exit(0)
 op=packet[0]['op']
 if op=='open':send('opened')
 elif op=='match' and mode in BAD:
  out.write(BAD[mode]());out.flush()
  if mode=='truncated':sys.exit(3)
 elif op=='match' and mode=='order':
  frame=dict(version=1,sequence=1,watermark=0,minute=1,score=[0,0],subtick=36,threshold=45,remaining=91,selector=1,
             attack=[1,-1],sentinel=11,ball=[-8,1,False],players=[[s,int(s<=11),s if s<=11 else s-11,100+s,-9,0,13,False] for s in range(1,23)])
  send('frame',frame)
 elif op=='cancel':send('cancelled')
'''
IDLE_COMMAND = [sys.executable, '-c', IDLE]


# [designed: #307] Setup waits for a job cancelled at once: wait() first joins the thread that
# encodes the job's input (26.7 MB, 0.37 s idle on Linux), which passed 2 s on a loaded Windows
# runner. These waits only end the setup; no test here bounds the encode itself.
SETUP_WAIT = 60


class WatchedJobsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        adapter.WatchedAdapter.setUpClass()
        cls.raw = adapter.WatchedAdapter.raw

    def setUp(self):
        self.owner = Owner(adapter.WatchedAdapter.state(self), self.raw)
        self.before = copy.deepcopy(self.owner.state)
        self.jobs = None

    def tearDown(self):
        if self.jobs is not None:
            self.jobs.close()

    def bridge(self, mode=None, script=None, idle=None):
        command = None
        if mode is not None:
            command = [sys.executable, '-c', CONTROLLED, mode]
        if script is not None:
            command = [sys.executable, '-c', script]
        if idle is not None:
            command = IDLE_COMMAND + ([idle] if idle else [])
        self.jobs = WatchedJobs(self.owner, command=command)
        return self.jobs.start(Fixture(7,19,21),reference_seed=257,delay_byte=0,record_draws=True)

    def until(self, token, predicate, *, hang_guard=30):
        deadline = time.monotonic() + hang_guard
        seen = []
        while time.monotonic() < deadline:
            seen.extend(self.jobs.poll(token))
            if predicate(seen):
                return seen
            time.sleep(.005)
        self.fail('controlled worker did not reach expected boundary')

    def test_live_order_default_answers_and_full_time_still_pending(self):
        token = self.bridge('blocked')
        events = self.until(token, lambda events:any(e.kind=='full_time' for e in events))
        self.assertEqual([e.kind for e in events],
            ['minute','decision','commentary','decision','full_time'])
        self.assertTrue(self.jobs.busy)
        self.assertIsNone(self.jobs.outcome)
        self.assertEqual(self.owner.state,self.before)
        async def scheduler():
            beats = []
            async def heartbeat():
                for n in range(20):
                    await asyncio.sleep(.001)
                    beats.append(n)
            async def progress():
                for _ in range(20):
                    self.assertEqual(self.jobs.poll(token),[])
                    await asyncio.sleep(.001)
            await asyncio.gather(heartbeat(), progress())
            return beats
        self.assertEqual(asyncio.run(scheduler()),list(range(20)))
        with self.assertRaisesRegex(ValueError,'already running'):
            self.jobs.start(Fixture(7,19,21))
        with self.assertRaisesRegex(ValueError,'already has'):
            WatchedJobs(self.owner)
        self.assertEqual(self.owner.state,self.before)

    def test_failure_classes_preserve_complete_state(self):
        for mode,message in [('missing','pip install unicorn'),('guest','guest execution failed'),
                             ('refused','refused'),('loop','no progress'),('unsupported','unsupported')]:
            with self.subTest(mode=mode):
                token = self.bridge(mode)
                with self.assertRaisesRegex(ValueError,message):
                    self.until(token, lambda events:False)
                self.assertFalse(self.jobs.busy)
                self.assertEqual(self.owner.state,self.before)
                self.jobs.close()

    def test_cancel_and_reap_and_close_outlast_a_slow_input_encoding(self):
        """[designed: #311; #254] One cancel during the input encoding times out and keeps the job
        (#254). cancel_and_reap and close, which must end it, retry until the encoding is done and
        the job is reaped, as on the loaded Windows runner (encoding slower than 0.5 s)."""
        from goal2.game import watched_jobs
        real = watched_jobs.encode
        def slow(*args, **kwargs):
            time.sleep(1.5);return real(*args, **kwargs)
        for end in ('cancel_and_reap', 'close'):
            with self.subTest(end=end), patch.object(watched_jobs, 'encode', slow):
                token = self.bridge('blocked')
                with self.assertRaises(subprocess.TimeoutExpired):
                    self.jobs.cancel(token)
                self.assertTrue(self.jobs.busy, 'a single cancel keeps the job owned (#254)')
                if end == 'cancel_and_reap':
                    self.jobs.cancel_and_reap(token)
                else:
                    self.jobs.close()
                self.assertFalse(self.jobs.busy)
                self.assertEqual(self.owner.state, self.before)
                self.jobs.close();self.jobs = None

    def test_killed_worker_and_bounded_shutdown(self):
        token = self.bridge('blocked')
        self.until(token,lambda events:bool(events))
        process = self.jobs.process
        process.kill();process.wait(timeout=2)
        with self.assertRaisesRegex(ValueError,'without completion'):
            self.until(token,lambda events:False)
        self.assertEqual(self.owner.state,self.before)
        self.jobs.close()
        token=self.bridge('ignore');process=self.jobs.process
        # [designed: T160] The cancel is a request on the pipe, not a signal: the guest is waited for where it no
        # longer reads it (after full time), so close must kill the engine. Before that, the engine answers it.
        self.until(token,lambda events:any(e.kind=='full_time' for e in events))
        self.jobs.close()
        self.assertIsNotNone(process.poll())
        if os.name == 'posix':self.assertEqual(process.poll(),-signal.SIGKILL)
        self.assertEqual(self.owner.state,self.before)

    def test_replacement_and_stale_cancel_cannot_touch_new_job(self):
        old=self.bridge('blocked')
        # [designed: #492] the worker runs (its input is encoded) before the job goes stale: the stale
        # poll's cancel waits 1 s, which a loaded CI runner's encode outlasted (#307's setup waits)
        self.until(old,lambda events:events,hang_guard=SETUP_WAIT)
        self.owner.state=copy.deepcopy(self.owner.state)
        replacement=copy.deepcopy(self.owner.state)
        with self.assertRaisesRegex(ValueError,'stale'):
            self.jobs.poll(old)
        self.assertEqual(self.owner.state,replacement)
        new=self.jobs.start(Fixture(7,19,21))
        self.assertNotEqual(old,new)
        with self.assertRaisesRegex(ValueError,'stale'):
            self.jobs.cancel(old)
        with self.assertRaisesRegex(ValueError,'stale'):
            self.jobs.poll(old)
        self.assertTrue(self.jobs.busy)
        self.assertEqual(self.jobs.publication._pending[0],new)
        self.jobs.cancel_and_reap(new)
        self.assertEqual(self.owner.state,replacement)

    def test_partial_oversized_wrong_identity_and_order_ipc(self):
        # [designed: T160] Each a stand-in engine's reply; an unreadable one ends the engine (T159), which the job
        # reports as the engine's exit with the reason. A packet carries no token: the old "wrong identity" record
        # has no counterpart (a reply sent before the match request can be read after it, as the match's).
        for mode,message in [('malformed','Invalid watched worker IPC'),('unknown fields','Invalid watched worker IPC'),
                             ('event shape','invalid watched event shape'),('truncated','truncated'),('oversized','exceeds'),
                             ('order','order/watermark')]:
            with self.subTest(message=message):
                try:
                    token=self.bridge(idle=mode)
                    with self.assertRaisesRegex(ValueError,message):
                        self.until(token,lambda events:False)
                    self.assertEqual(self.owner.state,self.before)
                finally:
                    self.jobs.close()

    def test_bridge_imports_without_ui_or_optional_runtime(self):
        import subprocess
        script = """
import importlib.abc,sys
class NoUI(importlib.abc.MetaPathFinder):
 def find_spec(self,fullname,path=None,target=None):
  if fullname.split('.')[0] in ('PySide6','pygame','unicorn','flask','http'):
   raise ImportError('forbidden dependency: '+fullname)
sys.meta_path.insert(0,NoUI())
import goal2.game.watched_jobs,goal2.game.engine_server
"""
        result=subprocess.run([sys.executable,'-c',script],cwd=ROOT,capture_output=True,text=True,timeout=30)
        self.assertEqual(result.returncode,0,result.stderr)

    def test_start_failures_clear_publication_and_allow_restart(self):
        self.jobs=WatchedJobs(self.owner)
        # A fixed worker: engine_python() probes interpreters with subprocess, which this test patches.
        self.jobs.command=[sys.executable,'-c',CONTROLLED,'blocked']
        for target in ('MatchEngine.claim','subprocess.Popen'):
            with patch('goal2.game.watched_jobs.'+target,side_effect=OSError('launch unavailable')):
                error = OSError if target == 'MatchEngine.claim' else ValueError
                with self.assertRaisesRegex(error,'launch unavailable'):
                    token = self.jobs.start(Fixture(7,19,21))
                    if target == 'subprocess.Popen':
                        self.until(token, lambda events:False)
            self.assertTrue(self.jobs.publication._pending is None,'failed launch must clear pending publication')
            self.assertFalse(self.jobs.busy)
            self.assertEqual(self.owner.state,self.before)
        token=self.jobs.start(Fixture(7,19,21))
        self.assertTrue(self.jobs.busy)
        self.jobs.cancel_and_reap(token)

    def launched(self, token):
        """[designed: T160] Poll until the match is asked of the engine."""
        deadline = time.monotonic() + SETUP_WAIT
        while not self.jobs._sent:
            self.assertEqual(self.jobs.poll(token), [])
            self.assertLess(time.monotonic(), deadline, 'the match was never asked')
            time.sleep(.005)

    def test_exited_burst_drains_in_bounded_batches_without_buffer_growth(self):
        token=self.bridge(idle='')
        self.launched(token)
        for number in range(2000):self.jobs._match.put('event',Event('minute',number,(0,0)))
        seen=[]
        for _ in range(70):
            events=self.jobs.poll(token)
            self.assertLessEqual(len(events),REPLY_BUDGET)
            seen.extend(events)
        self.assertEqual([event.minute for event in seen],list(range(2000)))
        self.assertEqual(self.owner.state,self.before)

    @requires.need(slow=True)  # [designed: #275] about 66 s alone on 32 CPUs
    def test_stream_outcome_mismatch_and_incomplete_tail_never_publish(self):
        # [designed] Real valid output isolates stream/tail validation from schema errors.
        # [designed: #500] Played once, under engine_python() in a child, before the loop: each mode's owner state is
        # the same (asserted equal to `before` after each mode).
        played=pypy_engine.call('goal2.game.watched_match:run_watched_match',self.owner.state,self.raw,Fixture(7,19,21),
                                reference_seed=257,delay_byte=0)
        for mode in ('mismatch','tail','trailing'):
            token=self.bridge(idle='')
            self.launched(token)
            outcome=played
            events=tuple(e for e in outcome.events if e.kind!='end') if mode=='tail' else outcome.events
            if mode=='tail':outcome=replace(outcome,events=events)
            # [designed: T160] The replies as the engine's reader delivers them; the real parent checks/publication.
            for event in events:self.jobs._match.put('event',event)
            if mode=='mismatch':outcome=replace(outcome,events=(replace(outcome.events[0],data={'tampered':True}),)+outcome.events[1:])
            self.jobs._match.put('complete',outcome)
            if mode=='trailing':self.jobs._match.put('death',{'code':1,'stderr':'','error':'ProtocolError: truncated'})
            with self.assertRaisesRegex(ValueError,{'mismatch':'live event stream','tail':'incomplete','trailing':'Invalid watched worker IPC'}[mode]):
                self.until(token,lambda events:False)
            self.assertEqual(self.owner.state,self.before)
            self.jobs.close()

    @requires.need(slow=True)  # [designed: #275] about 97 s alone on 32 CPUs
    def test_verified_normal_and_injury_jobs_equal_synchronous_and_publish_once(self):
        for seed in requires.cases((257,70)):  # [designed: #487]
            self.owner.state=adapter.WatchedAdapter.state(self)
            self.jobs=WatchedJobs(self.owner)
            # [designed: #500] the synchronous run under engine_python() in a child, beside the job's worker
            # [T180] the engine server plays a watched friendly with BM-7's budget: the reference is given the same
            pending=pypy_engine.start('goal2.game.watched_match:run_watched_match',self.before,self.raw,Fixture(7,19,21),
                                      reference_seed=seed,delay_byte=0,record_draws=True,
                                      substitutions=FRIENDLY_SUBSTITUTIONS)
            token=self.jobs.start(Fixture(7,19,21),reference_seed=seed,delay_byte=0,record_draws=True)
            start=time.monotonic()
            events=self.until(token,lambda events:not self.jobs.busy,hang_guard=600)
            elapsed=time.monotonic()-start
            outcome=self.jobs.outcome
            expected=pending.result()
            self.assertEqual(outcome,expected)
            self.assertEqual(tuple(events),expected.events)
            self.assertEqual(events[-1].kind,'end')
            self.assertLess(next(i for i,e in enumerate(events) if e.kind=='full_time'),len(events)-1)
            self.assertEqual(self.owner.state.mem,expected.memory)
            self.assertEqual(self.owner.state.last_match['original'],expected.result)
            self.assertEqual(self.owner.state.match_count,1)
            after=copy.deepcopy(self.owner.state)
            for action in (self.jobs.poll,self.jobs.cancel):
                with self.assertRaisesRegex(ValueError,'consumed'):action(token)
            self.assertEqual(self.owner.state,after)
            print(f'T65 seed={seed} seconds={elapsed:.3f} events={len(events)} memory_sha256={hashlib.sha256(outcome.memory).hexdigest()} seeds={outcome.seeds}',flush=True)
            self.jobs.close()

    def test_observation_occurs_before_guest_continues_and_answers(self):
        observed=[]
        image=Image(self.before.mem)
        class Guest:
            def events(inner):
                minute=Event('minute',1,(0,0))
                yield minute
                self.assertEqual(observed,[minute], 'minute must be observed before guest resumes')
                decision=Event('decision',46,(0,0),{'context':'half_time'})
                yield decision
                self.assertEqual(observed[-1],decision)
                yield Event('full_time',90,(0,0))
                self.assertEqual(observed[-1].kind,'full_time')
                yield Event('end',90,(0,0))
            def answer(inner):self.assertEqual(observed[-1].kind,'decision')
            def result(inner):return {'complete':True}
            def memory_component(inner):return image.memory_component()
        with patch('goal2.game.watched_match.Match',return_value=Guest()):
            outcome=_drive_match(self.before,image,Fixture(7,19,21),_observe=observed.append)
        self.assertEqual(tuple(observed),outcome.events)

    def test_declared_default_policy_repeated_injury_progress(self):
        # [designed] These accepted controlled guests require explicit empty/default answers.
        for name in ('test_each_default_decision_is_explicitly_answered',
                     'test_distinct_same_minute_notices_are_not_a_no_progress_loop',
                     'test_default_decision_policy_and_refusal_fail_closed'):
            getattr(adapter.WatchedAdapter,name)(self)

    def state(self):
        return adapter.WatchedAdapter.state(self)
