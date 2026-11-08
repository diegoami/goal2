"""[designed: #639] Force the former fixture race using only newly created fake-job PIDs."""
import importlib.util,os,signal,subprocess,sys,tempfile,time,unittest
from pathlib import Path
root=Path(__file__).resolve().parents[2]
with tempfile.TemporaryDirectory() as folder:
 p=Path(folder)/'old_checkpoints.py';p.write_text(subprocess.check_output(['git','show','320c595c:goal2/tests/test_checkpoints_t149.py'],text=True))
 spec=importlib.util.spec_from_file_location('old_checkpoints',p);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);m.ROOT=root
 case=m.Jobs('test_a_killed_job_is_vanished_not_running_or_finished');case.setUp();real_kill=os.kill
 def forced(pid,sig):
  real_kill(pid,sig)
  if sig != signal.SIGKILL:return
  job=case.jobs.read(case.root,'killed')
  if pid==job.get('command_pid'):
   done=case.until('killed','finished');assert done['exit_code']==-9,done
 try:
  from unittest.mock import patch
  with patch.object(m.os,'kill',side_effect=forced):
   try:case.test_a_killed_job_is_vanished_not_running_or_finished()
   except AssertionError as exc:
    assert 'never vanished' in str(exc) and "'exit_code': -9" in str(exc),exc
    print('FORCED OLD RACE reproduced:',str(exc))
   else:raise AssertionError('old vanished fixture unexpectedly passed')
 finally:case.doCleanups()
