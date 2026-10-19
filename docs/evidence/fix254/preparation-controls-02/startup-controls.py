"""[designed: #254] Serial preparation/ownership controls, restoring exact source bytes."""
import hashlib,json,subprocess,sys
from pathlib import Path
root=Path.cwd();out=root/'.cache/fix254-startup-controls02';out.mkdir(exist_ok=False)
path=root/'goal2/game/watched_jobs.py';saved=path.read_bytes();text=saved.decode();rows=[]
mutants=[
 ('synchronous-preparation','self._thread.start()','self._thread.run()','test_encoding_and_input_write_are_private_and_start_poll_remain_responsive','AssertionError'),
 ('discard-live-preparer','        except subprocess.TimeoutExpired:\n            self.process.kill()\n            self.process.wait(timeout=0.5)','        except subprocess.TimeoutExpired:\n            self.process.kill()\n            pass','test_cancel_blocked_encoding_retains_ownership_and_retries_without_launch','TimeoutExpired not raised'),
 ('cancel-may-launch','self._cancelled = True','self._cancelled = False','test_cancel_blocked_encoding_retains_ownership_and_retries_without_launch','Expected'),
 ('release-before-cleanup',"    def _release(self):\n", "    def _release(self):\n        self.process = None\n",'test_cleanup_failure_keeps_lock_and_can_be_retried','False is not true')]
assert not subprocess.check_output(['git','status','--porcelain','--untracked-files=no'],text=True).strip()
try:
 for name,old,new,test,expected in mutants:
  assert text.count(old)==(2 if name=='cancel-may-launch'else 1),(name,text.count(old))
  try:
   path.write_text(text.replace(old,new));log=out/(name+'.log')
   with log.open('xb')as stream:run=subprocess.run([sys.executable,'-B','-m','unittest','goal2.tests.test_watched_startup.StartupTests.'+test,'-v'],stdin=subprocess.DEVNULL,stdout=stream,stderr=subprocess.STDOUT,timeout=30)
   output=log.read_text();assert run.returncode!=0 and expected in output,(name,run.returncode,output)
   rows.append({'name':name,'exit':run.returncode,'intended_failure':expected,'source_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'log_sha256':hashlib.sha256(log.read_bytes()).hexdigest()})
  finally:path.write_bytes(saved)
  assert path.read_bytes()==saved
finally:
 (out/'report.json').write_text(json.dumps({'claim':'Synthetic startup mutation controls, not native execution','rows':rows,'all_sources_restored':path.read_bytes()==saved,'source_sha256':hashlib.sha256(saved).hexdigest()},indent=2)+'\n')
assert len(rows)==4 and path.read_bytes()==saved
print('PASS four intended startup control failures; exact source restored')
