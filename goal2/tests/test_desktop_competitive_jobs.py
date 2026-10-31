"""[designed: T80] Real competitive subprocess parity plus explicit synthetic faults."""
import copy
from dataclasses import replace
from functools import lru_cache
import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch
from goal2.desktop.competitive import CompetitiveJobs, pending_fixture
from goal2.desktop.model import DesktopModel
from goal2.game.session_save import encode
from goal2.game.watched_jobs import _write
from goal2.tests.test_campaign_competitive_publication import campaign
from goal2.tests.test_campaign_competitive_match import run
from goal2.data.goaldat import load
from goal2.tests import requires

ROOT = Path(__file__).resolve().parents[2]


@lru_cache(maxsize=2)
def direct(kind):
    s, raw, fixture = campaign(21 if kind == 2 else 42, kind)
    return run(s, raw, fixture, record_draws=True)


# [designed] Synthetic protocol fixtures replay a genuine accepted original outcome;
# they deliberately do not claim another engine execution or fidelity evidence.
REPLAY = r'''
import copy,json,struct,sys,time,signal
from pathlib import Path
from goal2.game.watched_jobs import _write
from goal2.game.session_save import _restore_json_value
mode,fixture_file=sys.argv[1:3];source=Path(sys.argv[3]);journal=Path(sys.argv[4])
request=json.loads((source.parent/'request.json').read_text());token=request['token']
if mode=='ignore':signal.signal(signal.SIGTERM,signal.SIG_IGN)
packets=[]
with open(fixture_file,'rb') as stream:
 while header:=stream.read(4):
  packets.append(_restore_json_value(json.loads(stream.read(struct.unpack('!I',header)[0])),'fixture'))
if mode=='partial':journal.write_bytes(b'\x00\x00');sys.exit(0)
if mode=='malformed':journal.write_bytes(struct.pack('!I',1)+b'{');sys.exit(0)
if mode=='death':sys.exit(4)
with journal.open('ab') as stream:
 if mode in ('blocked','ignore'):
  from goal2.engine.original_match.match import Event
  _write(stream,token,0,'event',Event('full_time',90,(0,0)))
  time.sleep(60);sys.exit(0)
 sequence=0
 for _,_,kind,value in packets:
  if mode=='tail' and kind=='event' and value['kind']=='end':continue
  if kind=='complete':
   if mode=='tail':value['events']=[e for e in value['events'] if e['kind']!='end']
   if mode=='result':value['result']['first']=19
   if mode=='memory':value['memory']='eA=='
   if mode=='mismatch':value['events'][0]['minute']+=1
  _write(stream,'wrong' if mode=='identity' else token,sequence,kind,value);sequence+=1
 if mode=='duplicate':_write(stream,token,sequence,'complete',packets[-1][3])
 if mode=='trailing':stream.write(b'\x00\x00')
 if mode=='waitexit':
  (source.parent/'ready').write_text('complete')
  while not (source.parent/'release').exists():time.sleep(.005)
sys.exit(5 if mode=='nonzero' else 0)
'''


class CompetitiveJobsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        requires.require(**requires.WATCHED)
        requires.require(files=("GOAL.DAT",))
        cls.data = load((ROOT/'.cache/GOAL.DAT').read_bytes())
        cls.fixture_dir = tempfile.TemporaryDirectory(prefix='goal2-T80-fixtures-')
        cls.fixture_file = Path(cls.fixture_dir.name)/'knockout.json-journal'
        out = direct(200)
        with cls.fixture_file.open('wb') as stream:
            for n, event in enumerate(out.events):_write(stream,'fixture',n,'event',event)
            _write(stream,'fixture',len(out.events),'complete',out)

    @classmethod
    def tearDownClass(cls):cls.fixture_dir.cleanup()

    def setUp(self):
        self.folder = tempfile.TemporaryDirectory(prefix='goal2-T80-save-')
        self.addCleanup(self.folder.cleanup)
        s, raw, self.fixture = campaign()
        self.owner = DesktopModel(self.data, raw, Path(self.folder.name)/'prior.g2save')
        self.owner.state = s
        self.owner.save(self.owner.save_path)
        self.saved = self.owner.save_path.read_bytes()
        self.before = copy.deepcopy(s)
        self.jobs = None

    def bridge(self, mode=None):
        command = None if mode is None else [sys.executable,'-c',REPLAY,mode,str(self.fixture_file)]
        self.jobs = CompetitiveJobs(self.owner, command=command)
        self.addCleanup(self.jobs.close)
        return self.jobs.start(record_draws=True)

    def until(self, token, predicate, *, limit=45):
        deadline = time.monotonic()+limit
        seen=[]
        while time.monotonic()<deadline:
            seen.extend(self.jobs.poll(token))
            if predicate(seen):return seen
            time.sleep(.002)
        self.fail('worker did not reach the bounded test boundary')

    def unchanged(self):
        self.assertEqual(self.owner.state,self.before,'failed/pending job published active state')
        self.assertEqual(self.owner.save_path.read_bytes(),self.saved,'failed/pending job changed prior save')

    @requires.need(slow=True)  # [designed: #275] about 90 s alone on 32 CPUs
    def test_real_kind2_and_tied_knockout_match_direct_result_events_memory_seeds(self):
        for kind,index in requires.cases(((2,21),(200,42))):  # [designed: #487]
            with self.subTest(kind=kind):
                s,raw,fixture=campaign(index,kind)
                self.owner.state=s;self.owner.template_bytes=raw
                self.jobs=CompetitiveJobs(self.owner);self.addCleanup(self.jobs.close)
                before=copy.deepcopy(s);token=self.jobs.start(record_draws=True)
                self.assertEqual(self.owner.state,before)
                events=self.until(token,lambda seen:not self.jobs.busy,limit=180)
                expected=direct(kind)
                self.assertEqual(self.jobs.outcome,expected,'competitive subprocess differs from direct original execution')
                self.assertEqual(tuple(events),expected.events)
                self.assertEqual(self.owner.state.mem,expected.memory)
                self.assertEqual(self.owner.state.last_match['original'],expected.result)
                self.assertEqual(self.owner.state.last_match['seeds'],list(expected.seeds))
                self.assertEqual(self.owner.state.match_count,before.match_count+1)
                self.assertEqual(expected.result['substitution_budget'],[5,5])
                if kind==200:
                    self.assertEqual(expected.result['score'],[0,0]);self.assertIsNotNone(expected.result['shootout'])
                after=copy.deepcopy(self.owner.state)
                for operation in (self.jobs.poll,self.jobs.cancel):
                    with self.assertRaisesRegex(ValueError,'consumed'):operation(token)
                self.assertEqual(self.owner.state,after,'duplicate completion changed active state')
                self.assertFalse(self.owner.match_pending)
                self.owner.save(self.owner.save_path);self.owner.resume(self.owner.save_path)
                self.assertEqual(self.owner.state,after)
                print(f'T80 REAL kind={kind} index={index} events={len(events)} memory_sha256={hashlib.sha256(expected.memory).hexdigest()} seeds={expected.seeds}',flush=True)
                self.owner.match_pending=True
                self.jobs.close()
                self.assertTrue(self.owner.match_pending,'finished competitive close unlocked another job')
                self.owner.match_pending=False

    def test_complete_packet_waits_for_successful_exit_and_full_tail(self):
        token=self.bridge('waitexit')
        self.until(token,lambda seen:self.jobs._complete is not None)
        self.assertTrue(self.jobs.busy);self.assertIsNone(self.jobs.outcome)
        self.unchanged()
        (Path(self.jobs._folder.name)/'release').write_text('release')
        self.until(token,lambda seen:not self.jobs.busy)
        self.assertEqual(self.owner.state.mem,direct(200).memory)
        self.assertEqual(self.owner.state.match_count,self.before.match_count+1)

    def test_fault_outputs_never_publish_or_change_prior_save(self):
        for mode,message in (('identity','identity/order'),('result','invalid watched result identity'),('memory','invalid'),
                             ('tail','incomplete'),('mismatch','live event stream'),('duplicate','identity/order'),
                             ('partial','truncated'),('malformed','Invalid watched worker IPC'),
                             ('trailing','truncated'),('nonzero','without completion'),('death','without completion')):
            with self.subTest(mode=mode):
                token=self.bridge(mode)
                try:
                    with self.assertRaisesRegex(ValueError,message):self.until(token,lambda seen:not self.jobs.busy)
                    self.assertFalse(self.jobs.busy);self.assertFalse(self.owner.match_pending)
                    self.unchanged()
                finally:
                    self.jobs.close()
                    self.owner.state=copy.deepcopy(self.before)

    def test_duplicate_completion_packet_is_rejected(self):
        token=self.bridge('duplicate')
        with self.assertRaisesRegex(ValueError,'identity/order'):
            self.until(token,lambda seen:not self.jobs.busy)
        self.unchanged()

    def test_missing_original_end_tail_is_rejected(self):
        token=self.bridge('tail')
        with self.assertRaisesRegex(ValueError,'incomplete'):
            self.until(token,lambda seen:not self.jobs.busy)
        self.unchanged()

    def test_changed_owner_is_rejected_before_any_publication(self):
        token=self.bridge('blocked');self.until(token,lambda seen:bool(seen))
        self.owner.state=copy.deepcopy(self.owner.state)
        with self.assertRaisesRegex(ValueError,'stale'):
            self.jobs.poll(token)
        self.unchanged()

    def test_stale_owner_input_template_and_duplicate_tokens(self):
        for mutation in ('owner','tactics','captain','template'):
            with self.subTest(mutation=mutation):
                token=self.bridge('blocked');self.until(token,lambda seen:bool(seen))
                with self.assertRaisesRegex(ValueError,'already running'):self.jobs.start()
                if mutation=='owner':self.owner.state=copy.deepcopy(self.owner.state)
                elif mutation=='tactics':self.owner.state.country_tactics^=1
                elif mutation=='captain':self.owner.state.captain=self.owner.state.starting_eleven[1]
                else:self.owner.template_bytes+=b'x'
                changed=copy.deepcopy(self.owner.state)
                with self.assertRaisesRegex(ValueError,'stale'):self.jobs.poll(token)
                self.assertEqual(self.owner.state,changed,'stale job overwrote changed input')
                self.assertEqual(self.owner.save_path.read_bytes(),self.saved)
                self.jobs.close();self.owner.state=copy.deepcopy(self.before)
                _,self.owner.template_bytes,_=campaign()
        old=self.bridge('blocked');self.jobs.cancel_and_reap(old)
        new=self.jobs.start()
        with self.assertRaisesRegex(ValueError,'stale'):self.jobs.cancel(old)
        self.assertEqual(self.jobs.token,new);self.assertTrue(self.jobs.busy)
        self.jobs.cancel_and_reap(new);self.unchanged()

    def test_launch_runtime_resource_and_pending_failures_are_actionable(self):
        self.jobs=CompetitiveJobs(self.owner);self.addCleanup(self.jobs.close)
        with patch('goal2.game.watched_jobs.subprocess.Popen',side_effect=OSError('launch unavailable')):
            with self.assertRaisesRegex(ValueError,'launch unavailable'):
                token=self.jobs.start()
                self.until(token,lambda seen:False)
        self.assertFalse(self.jobs.busy);self.assertIsNone(self.jobs.publication._pending);self.unchanged()
        import builtins
        original_import=builtins.__import__
        def without_unicorn(name,*args,**kwargs):
            if name=='unicorn':raise ImportError('synthetic missing optional runtime')
            return original_import(name,*args,**kwargs)
        with patch('builtins.__import__',side_effect=without_unicorn):
            with self.assertRaisesRegex(ValueError,"pip install.*desktop,watched"):self.jobs.start()
        raw=self.owner.template_bytes;self.owner.template_bytes=b'broken'
        with self.assertRaisesRegex(ValueError,'Check the local game resources'):self.jobs.start()
        self.owner.template_bytes=raw;self.unchanged()
        self.owner.match_pending=True
        with self.assertRaisesRegex(ValueError,'Another match'):self.jobs.start()
        self.assertTrue(self.owner.match_pending);self.owner.match_pending=False
        with self.assertRaisesRegex(ValueError,'already has'):CompetitiveJobs(self.owner)

    def test_cancel_close_death_and_save_pending_have_bounded_owned_lifecycle(self):
        for action in ('cancel','close','kill','ignore'):
            with self.subTest(action=action):
                token=self.bridge('ignore' if action=='ignore' else 'blocked')
                self.until(token,lambda seen:bool(seen));process=self.jobs.process
                with self.assertRaisesRegex(ValueError,'Saving during a match'):self.owner.save(self.owner.save_path)
                start=time.monotonic()
                if action=='kill':
                    process.kill();process.wait(timeout=2)
                    with self.assertRaisesRegex(ValueError,'without completion'):self.until(token,lambda seen:False)
                elif action=='cancel':self.jobs.cancel(token)
                else:self.jobs.close()
                self.assertLess(time.monotonic()-start,2)
                self.assertIsNotNone(process.poll());self.assertFalse(self.owner.match_pending)
                if action=='ignore' and os.name=='posix':self.assertEqual(process.returncode,-signal.SIGKILL)
                self.unchanged();self.jobs.close()

    def test_cancel_leaves_an_unrelated_child_alive(self):
        unrelated=subprocess.Popen([sys.executable,'-c','import time;time.sleep(60)'],
                                   stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        try:
            token=self.bridge('blocked');self.until(token,lambda seen:bool(seen))
            owned=self.jobs.process;self.jobs.cancel(token)
            self.assertIsNotNone(owned.poll())
            self.assertIsNone(unrelated.poll(),'competitive cancellation reaped an unrelated child')
            self.unchanged()
        finally:
            unrelated.terminate();unrelated.wait(timeout=2)

    def test_qt_heartbeat_while_worker_full_time_tail_is_blocked(self):
        from PySide6.QtCore import QCoreApplication,QTimer
        app=QCoreApplication.instance() or QCoreApplication([])
        token=self.bridge('blocked');self.until(token,lambda seen:bool(seen))
        beats=[];timer=QTimer();timer.setInterval(1);timer.timeout.connect(lambda:beats.append(1));timer.start()
        deadline=time.monotonic()+.12
        while time.monotonic()<deadline:
            self.jobs.poll(token);app.processEvents();time.sleep(.001)
        timer.stop()
        self.assertGreater(len(beats),10,'Qt heartbeat blocked by competitive worker')
        self.assertTrue(self.jobs.busy);self.assertIsNone(self.jobs.outcome);self.unchanged()

    def test_inactive_close_never_unlocks_another_match(self):
        self.jobs=CompetitiveJobs(self.owner);self.addCleanup(self.jobs.close)
        self.owner.match_pending=True
        self.jobs.close()
        self.assertTrue(self.owner.match_pending,'inactive competitive close unlocked another match')
        self.owner.match_pending=False
        self.unchanged()

    def test_only_canonical_pending_competitive_fixtures_are_bound(self):
        self.assertEqual(pending_fixture(self.owner.state),self.fixture)
        for state in (replace(self.owner.state,campaign=None),):
            with self.assertRaisesRegex(ValueError,'No supported'):pending_fixture(state)
        from dataclasses import replace as dc_replace
        for fid,kind in (('original:042',200),('42',200),('original:42',1),('original:42',4)):
            bad=copy.deepcopy(self.owner.state)
            bad.campaign.fixtures=(dc_replace(bad.campaign.fixtures[0],fixture_id=fid,kind=kind),)
            with self.assertRaises(ValueError):pending_fixture(bad)


if __name__=='__main__':unittest.main()
