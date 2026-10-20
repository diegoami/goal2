"""[designed: T70] Real process lifecycle, complete continuation and rollback."""
import copy
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch
from types import SimpleNamespace
from goal2.tests import requires
from goal2.desktop.model import DesktopModel
from goal2.desktop.jobs import QuickJobs
from goal2.desktop.worker import play
from goal2.game.session_save import encode

ROOT=Path(__file__).resolve().parents[2]

@requires.need(**requires.HALFTIME)
class QuickJobCases(unittest.TestCase):
    def setUp(self):
        self.folder=tempfile.TemporaryDirectory();self.addCleanup(self.folder.cleanup)
        self.model=DesktopModel.open(ROOT/'.cache/e010-r0008-halftime.sav',ROOT/'.cache/GOAL.DAT',Path(self.folder.name)/'game.g2save',country=4)
    def job(self,command=None):
        job=QuickJobs(self.model,command=command);self.addCleanup(job.cancel);return job
    def finish(self,job):
        deadline=time.monotonic()+15
        while time.monotonic()<deadline:
            if job.poll():return
            time.sleep(.01)
        self.fail('Worker deadline exceeded')
    def test_candidate_isolation_and_process_result_equal_direct_two_matches_with_resume(self):
        direct=copy.deepcopy(self.model.state)
        for n in range(2):
            before=copy.deepcopy(self.model.state)
            direct_before=copy.deepcopy(direct)
            expected=play(direct,self.model.template_bytes)
            self.assertEqual(direct,direct_before)
            self.assertEqual(self.model.state,before)
            job=self.job();job.start()
            self.assertIsNotNone(job.process.pid)
            with self.assertRaisesRegex(ValueError,'already'):job.start()
            self.assertEqual(self.model.state,before)
            self.finish(job);self.assertEqual(self.model.state,expected)
            self.assertIsNone(job.poll());self.assertEqual(self.model.state.match_count,n+1)
            self.assertEqual(len(self.model.state.campaign.results),n+1)
            direct=expected
            self.model.save(self.model.save_path);self.model.resume(self.model.save_path)
        self.assertEqual(self.model.state,direct)
    def test_failure_and_bad_output_leave_active_state_unchanged(self):
        before=copy.deepcopy(self.model.state)
        for code in ("import sys;sys.stderr.write('deliberate failure');sys.exit(7)","import pathlib,sys;pathlib.Path(sys.argv[-1]).write_bytes(b'bad')"):
            job=self.job([sys.executable,'-c',code]);job.start()
            with self.assertRaises(ValueError):self.finish(job)
            self.assertFalse(job.busy);self.assertEqual(self.model.state,before)
    def test_stale_completion_refuses_replaced_and_mutated_active_state(self):
        for replace in (True,False):
            job=self.job();job.start()
            if replace:self.model.confirm(list(self.model.state.starting_eleven),self.model.state.starting_eleven[0],self.model.state.country_tactics)
            else:self.model.state.country_tactics^=1
            before=copy.deepcopy(self.model.state)
            with self.assertRaisesRegex(ValueError,'stale'):self.finish(job)
            self.assertEqual(self.model.state,before)
    def test_cancel_reaps_blocked_and_sigterm_ignoring_process_with_bounded_wait(self):
        before=copy.deepcopy(self.model.state)
        for code in ('import time;time.sleep(60)','import signal,time;signal.signal(signal.SIGTERM,signal.SIG_IGN);print("ready",flush=True);time.sleep(60)'):
            job=self.job([sys.executable,'-c',code]);job.start();process=job.process
            time.sleep(.12);start=time.monotonic();job.cancel()
            self.assertLess(time.monotonic()-start,2)
            self.assertIsNotNone(process.poll());self.assertFalse(job.busy)
            self.assertEqual(self.model.state,before);self.assertIsNone(job.poll())
    # [designed: T76/#233] Simulate only owned-folder sharing errors; real child cancellation stays in the path.
    def cleanup_fixture(self):
        self.model.save(self.model.save_path)
        before=encode(self.model.state,self.model.template_bytes);saved=self.model.save_path.read_bytes()
        job=self.job([sys.executable,'-c','import time;time.sleep(60)']);job.start()
        return job,before,saved

    def sharing_error(self):
        error=PermissionError('owned worker stderr still closing');error.winerror=32
        return error

    def assert_preserved(self,before,saved):
        self.assertEqual(encode(self.model.state,self.model.template_bytes),before)
        self.assertEqual(self.model.save_path.read_bytes(),saved)

    def test_transient_windows_sharing_cleanup_retries_then_releases_ownership(self):
        job,before,saved=self.cleanup_fixture();folder=job.folder;directory=Path(folder.name);cleanup=folder.cleanup
        calls=[]
        def transient():
            calls.append(True)
            if len(calls)==1:raise self.sharing_error()
            cleanup()
        start=time.monotonic()
        with patch.object(folder,'cleanup',side_effect=transient):
            try:job.cancel()
            except PermissionError:self.fail('transient WinError32 was not retried')
        self.assertEqual(len(calls),2);self.assertLess(time.monotonic()-start,2)
        self.assertFalse(job.busy);self.assertIsNone(job.folder);self.assertFalse(self.model.match_pending)
        self.assertFalse(directory.exists());self.assert_preserved(before,saved)

    def test_permanent_windows_sharing_is_bounded_retains_ownership_and_can_retry(self):
        job,before,saved=self.cleanup_fixture();folder=job.folder;process=job.process;directory=Path(folder.name)
        elapsed=[0.0];sleeps=[]
        def sleep(seconds):sleeps.append(seconds);elapsed[0]+=seconds
        clock=SimpleNamespace(monotonic=lambda:elapsed[0],sleep=sleep)
        error=self.sharing_error();attempt_times=[]
        def permanent():attempt_times.append(elapsed[0]);raise error
        with patch('goal2.desktop.jobs.time',clock,create=True),patch.object(folder,'cleanup',side_effect=permanent) as cleanup:
            with self.assertRaises(PermissionError) as raised:job.cancel()
            self.assertIs(raised.exception,error)
            self.assertIs(job.process,process,'cleanup failure lost process ownership')
            self.assertIs(job.folder,folder);self.assertTrue(job.busy);self.assertTrue(self.model.match_pending)
            self.assertGreater(cleanup.call_count,1);self.assertTrue(sleeps);self.assertLessEqual(elapsed[0],.5)
            self.assertTrue(all(value<.5 for value in attempt_times),'cleanup retried after deadline')
        self.assert_preserved(before,saved);job.cancel()
        self.assertIsNone(job.folder);self.assertFalse(job.busy);self.assertFalse(directory.exists())
        self.assertFalse(self.model.match_pending);self.assert_preserved(before,saved)

    def test_nonsharing_cleanup_errors_propagate_without_retry_and_retain_ownership(self):
        denied=PermissionError('not a sharing violation');denied.winerror=5
        for error in (denied,PermissionError('no Windows sharing code'),OSError('other cleanup error')):
            with self.subTest(error=repr(error)):
                job,before,saved=self.cleanup_fixture();folder=job.folder;process=job.process
                clock=SimpleNamespace(monotonic=lambda:0,sleep=lambda _:self.fail('nonsharing error was retried'))
                with patch('goal2.desktop.jobs.time',clock,create=True),patch.object(folder,'cleanup',side_effect=error) as cleanup:
                    with self.assertRaises(type(error)) as raised:job.cancel()
                    self.assertIs(raised.exception,error);self.assertEqual(cleanup.call_count,1)
                    self.assertIs(job.process,process,'cleanup failure lost process ownership');self.assertIs(job.folder,folder)
                    self.assertTrue(self.model.match_pending)
                self.assert_preserved(before,saved);job.cancel();self.assertIsNone(job.folder)
                self.assertFalse(job.busy);self.assert_preserved(before,saved)

    def test_failed_launch_cleanup_can_retry_without_a_process(self):
        self.model.save(self.model.save_path);before=encode(self.model.state,self.model.template_bytes);saved=self.model.save_path.read_bytes()
        folder=tempfile.TemporaryDirectory(prefix='goal2-owned-launch-failure-');self.addCleanup(folder.cleanup)
        job=self.job();error=self.sharing_error()
        with patch('goal2.desktop.jobs.tempfile.TemporaryDirectory',return_value=folder),patch('goal2.desktop.jobs.subprocess.Popen',side_effect=FileNotFoundError('missing owned launcher')):
            with patch.object(folder,'cleanup',side_effect=error),patch('goal2.desktop.jobs.time',SimpleNamespace(monotonic=iter((0,1)).__next__,sleep=lambda _:None),create=True):
                with self.assertRaises(PermissionError):job.start()
        self.assertIsNone(job.process);self.assertIs(job.folder,folder);self.assert_preserved(before,saved)
        with self.assertRaisesRegex(ValueError,'cleanup'):job.start()
        job.cancel();self.assertIsNone(job.folder,'pending folder without a process was not retried')
        self.assertFalse(Path(folder.name).exists());self.assert_preserved(before,saved)

    def test_launch_failure_and_unsupported_fixture_are_atomic(self):
        job=self.job(['/missing/goal2-worker'])
        before=copy.deepcopy(self.model.state)
        with self.assertRaises(OSError):job.start()
        self.assertFalse(job.busy);self.assertEqual(self.model.state,before)
        direct=self.model.state
        for _ in range(2):direct=play(direct,self.model.template_bytes)
        self.model.state=direct;before=copy.deepcopy(direct)
        self.assertNotEqual(direct.campaign.next_fixture.kind,1)
        with self.assertRaisesRegex(ValueError,'unsupported'):self.job().start()
        self.assertEqual(self.model.state,before)
    def test_standalone_repeat_retains_complete_state_without_campaign(self):
        self.model.new_friendly(13);self.assertIsNone(self.model.state.campaign)
        direct=copy.deepcopy(self.model.state)
        for _ in range(2):
            direct=play(direct,self.model.template_bytes)
            job=self.job();job.start();self.finish(job)
            self.assertEqual(self.model.state,direct)
        self.model.save(self.model.save_path);self.model.resume(self.model.save_path)
        self.assertEqual(self.model.state,direct)
    def test_candidate_matches_existing_transport_independent_campaign_publication(self):
        # [designed] Independent existing transition oracle, only in tests.
        from goal2.web.server import WebSession
        from goal2.engine.savestate import Savestate
        raw=self.model.template_bytes
        web=WebSession(copy.deepcopy(self.model.state),self.model.goaldat,Savestate(raw),raw)
        for _ in range(2):
            expected=play(self.model.state,raw)
            web.play({'play_token':web._play_token,'fixture_id':web.state.campaign.next_fixture.fixture_id})
            self.assertEqual(expected,web.state)
            self.model.state=expected

    def test_unrenderable_saved_result_is_rejected_before_resume_publication(self):
        before=copy.deepcopy(self.model.state)
        for match in ({'teams':(1,2)}, {'teams':(1,2),'score':(0,0),'goals':[{'team':3,'minute':1,'player':1}]}):
            bad=copy.deepcopy(before);bad.last_match=match
            self.model.save_path.write_bytes(encode(bad,self.model.template_bytes))
            with self.assertRaisesRegex(ValueError,'saved match'):self.model.resume(self.model.save_path)
            self.assertEqual(self.model.state,before)

    def test_worker_and_jobs_import_without_qt_unicorn_or_web(self):
        code="""import sys
class Block:
 def find_spec(self,name,*args):
  if name.startswith(('PySide6','unicorn','goal2.web')):raise RuntimeError(name)
sys.meta_path.insert(0,Block())
import goal2.desktop.worker,goal2.desktop.jobs
"""
        result=subprocess.run([sys.executable,'-c',code],cwd=ROOT,capture_output=True,text=True)
        self.assertEqual(result.returncode,0,result.stderr)

if __name__=='__main__':unittest.main()
