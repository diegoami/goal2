"""[designed: #254] Completion preparation controls, preserving exact file bytes."""
import hashlib,json,subprocess,sys
from pathlib import Path
root=Path.cwd();out=root/'.cache/fix254-completion-controls02';out.mkdir(exist_ok=False)
files={name:(root/name).read_bytes()for name in('goal2/game/watched_jobs.py','goal2/game/watched_publication.py')};rows=[]
mutants=[
 ('synchronous-candidate','goal2/game/watched_jobs.py','self._completion_thread.start()','self._completion_thread.run()','goal2.tests.test_watched_completion.CompletionTests.test_slow_candidate_keeps_poll_responsive_and_publishes_once_on_owner_thread','AssertionError'),
 ('missing-owner-recheck','goal2/game/watched_publication.py','        self._check_owner(pending)\n        self.owner.view(preparation.candidate)','        self.owner.view(preparation.candidate)','goal2.tests.test_watched_completion.CompletionTests.test_changed_owner_identity_is_rechecked_after_preparation','ValueError not raised'),
 ('discard-live-candidate','goal2/game/watched_jobs.py',"            if thread.is_alive():\n                raise subprocess.TimeoutExpired('watched completion preparation', 1.0)","            if thread.is_alive():\n                pass",'goal2.tests.test_watched_completion.CompletionTests.test_cancel_timeout_retains_worker_and_lock_then_retries_without_publication','TimeoutExpired not raised'),
 ('accept-forged-candidate','goal2/game/watched_publication.py','if self._preparation is None or preparation is not self._preparation:','if self._preparation is None or preparation is None:','goal2.tests.test_watched_completion.CompletionTests.test_unprepared_forged_duplicate_and_cancelled_candidates_cannot_publish','ValueError not raised'),
 ('lost-terminated-poll','goal2/game/watched_jobs.py','return self._process.poll() if self._process is not None else 0','return self.returncode','goal2.tests.test_watched_startup.StartupTests.test_terminated_worker_can_be_reaped_by_poll_without_wait','terminated owned process never reaped by poll'),
 ('missing-final-ack','goal2/game/watched_jobs.py','            if self._frame_ack != self._frame_sequence - 1:\n                return','            if False:\n                return','goal2.tests.test_watched_completion.CompletionTests.test_completion_cannot_start_before_final_frame_ack','AssertionError')]
assert not subprocess.check_output(['git','status','--porcelain','--untracked-files=no'],text=True).strip()
try:
 for name,file,old,new,test,expected in mutants:
  path=root/file;saved=files[file];text=saved.decode();assert text.count(old)==1,(name,text.count(old))
  try:
   path.write_text(text.replace(old,new));log=out/(name+'.log')
   with log.open('xb')as stream:r=subprocess.run([sys.executable,'-B','-m','unittest',test,'-v'],stdin=subprocess.DEVNULL,stdout=stream,stderr=subprocess.STDOUT,timeout=30)
   output=log.read_text();assert r.returncode!=0 and expected in output,(name,r.returncode,output)
   rows.append({'name':name,'file':file,'exit':r.returncode,'intended_failure':expected,'mutant_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'log_sha256':hashlib.sha256(log.read_bytes()).hexdigest()})
  finally:path.write_bytes(saved)
  assert all((root/n).read_bytes()==b for n,b in files.items())
finally:
 (out/'report.json').write_text(json.dumps({'claim':'Synthetic completion/startup mutation controls, not native execution','rows':rows,'all_sources_restored':all((root/n).read_bytes()==b for n,b in files.items()),'source_sha256':{n:hashlib.sha256(b).hexdigest()for n,b in files.items()}},indent=2)+'\n')
assert len(rows)==6
print('PASS six intended completion/lifecycle rejection controls; exact source restored')
