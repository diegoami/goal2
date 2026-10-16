"""[designed: T70] Real process lifecycle, complete continuation and rollback."""
import copy
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch
from goal2.desktop.model import DesktopModel
from goal2.desktop.jobs import QuickJobs
from goal2.desktop.worker import play
from goal2.game.session_save import encode

ROOT=Path(__file__).resolve().parents[2]

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
