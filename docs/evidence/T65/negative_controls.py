from pathlib import Path
import os,subprocess,sys,json,time
root=Path.cwd(); folder=Path(sys.argv[1]) if len(sys.argv)>1 else root/'.cache'/('T65-controls-'+str(time.time_ns()));folder.mkdir(parents=True,exist_ok=False); env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1')
match=root/'goal2/game/watched_match.py';jobs=root/'goal2/game/watched_jobs.py'
base='goal2.tests.test_watched_jobs.WatchedJobsTests.'
controls=[
 ('live-observer',match,'            _observe(copy.deepcopy(ev))','            pass',base+'test_observation_occurs_before_guest_continues_and_answers','minute must be observed before guest resumes'),
 ('explicit-answer',match,"            match.answer(quick=True) if quick_at_half_time and ev.data.get('context')=='half_time' else match.answer()",'            pass',base+'test_declared_default_policy_repeated_injury_progress','default answer missing'),
 ('refusal',match,"if ev.data.get('refused') or identity == previous_decision:",'if identity == previous_decision:',base+'test_declared_default_policy_repeated_injury_progress','must refuse'),
 ('no-progress',match,"if ev.data.get('refused') or identity == previous_decision:","if ev.data.get('refused'):",base+'test_declared_default_policy_repeated_injury_progress','RuntimeError not raised'),
 ('stale-owner',jobs,'if (self.owner.state is not self._original or self.owner.state != self._snapshot\n                    or self.owner.template_bytes != self._template):','if False:',base+'test_replacement_and_stale_cancel_cannot_touch_new_job','ValueError not raised'),
 ('stale-cancel',jobs,'    def cancel(self, token):\n        self._check_token(token)','    def cancel(self, token):\n        pass',base+'test_replacement_and_stale_cancel_cannot_touch_new_job','ValueError not raised'),
 ('stream-identity',jobs,'                    if tuple(self.events) != value.events:','                    if False:',base+'test_stream_outcome_mismatch_and_incomplete_tail_never_publish','live event stream'),
 ('bounded-read',jobs,'self._journal.read(READ_BUDGET)','self._journal.read(READ_BUDGET * 4)',base+'test_large_partial_record_reads_are_bounded','1 != 0'),
 ('start-cleanup',jobs,'            self.publication.cancel()\n            self._release()\n            raise','            self._release()\n            raise',base+'test_start_failures_clear_publication_and_allow_restart','AssertionError'),
]
report=[]
for name,path,old,new,test,intended in controls:
 saved=path.read_bytes();text=saved.decode();assert text.count(old)==1,(name,text.count(old))
 try:
  path.write_text(text.replace(old,new))
  result=subprocess.run([sys.executable,'-B','-m','unittest',test,'-v'],cwd=root,env=env,capture_output=True,text=True,timeout=180)
  output=result.stdout+result.stderr
  if any(len(line)>1000 for line in output.splitlines()):raise AssertionError('refuse to retain an unsanitized large state repr')
  (folder/f'control-{name}.log').write_text(output)
  good=result.returncode!=0 and 'FAIL:' in output and 'ERROR:' not in output and intended in output and 'ModuleNotFoundError' not in output and 'TimeoutExpired' not in output
  report.append(dict(control=name,test=test,exit=result.returncode,intended_assertion=intended,behavioral_failure=good))
  print(name,good,flush=True)
  if not good:raise AssertionError(output)
 finally:path.write_bytes(saved)
(folder/'controls.json').write_text(json.dumps(report,indent=2)+'\n')
