#!/usr/bin/env python3
"""[designed: T70] Delete consequential behavior; require assertion failures."""
from pathlib import Path
import subprocess
import sys
ROOT=Path(__file__).resolve().parents[2]
CASES=[
 ('candidate isolation','goal2/game/campaign_rounds.py','candidate=copy.deepcopy(state)','candidate=state','test_candidate_isolation_and_process_result_equal_direct_two_matches_with_resume'),
 ('one in-flight','goal2/desktop/jobs.py',"if self.busy:raise ValueError('A friendly is already running')","if False:raise ValueError('A friendly is already running')",'test_candidate_isolation_and_process_result_equal_direct_two_matches_with_resume'),
 ('stale completion','goal2/desktop/jobs.py','if model.state is not self.original or encode(model.state,model.template_bytes)!=self.snapshot:','if False:','test_stale_completion_refuses_replaced_and_mutated_active_state'),
 ('publication','goal2/desktop/jobs.py','model.state=candidate','model.state=model.state','test_candidate_isolation_and_process_result_equal_direct_two_matches_with_resume'),
 ('history','goal2/game/campaign_rounds.py',"campaign.results.append({'fixture_id':fixture.fixture_id,'teams':list(result['teams']),'score':list(result['score'])})",'pass','test_candidate_isolation_and_process_result_equal_direct_two_matches_with_resume'),
 ('Qt play wire','goal2/desktop/window.py','self.play.clicked.connect(self.start_match)','self.play.clicked.connect(lambda:None)',None),
 ('Qt cancel wire','goal2/desktop/window.py','self.stop.clicked.connect(self.cancel_match)','self.stop.clicked.connect(lambda:None)',None),
]

def main():
 for name,relative,old,new,test in CASES:
  path=ROOT/relative;saved=path.read_bytes();text=saved.decode()
  if text.count(old)!=1:raise AssertionError(f'proof site changed: {name}')
  try:
   path.write_text(text.replace(old,new))
   if test:command=[sys.executable,'-B','-m','unittest','goal2.tests.test_desktop_quick_jobs.QuickJobCases.'+test]
   else:command=['/tmp/T69-desktop-venv/bin/python','-B','tools/desktop-ui/acceptance.py','--scenario','worker','--template','.cache/e010-r0008-halftime.sav','--data','.cache/GOAL.DAT']
   import os
   result=subprocess.run(command,cwd=ROOT,env={**os.environ,'QT_QPA_PLATFORM':'offscreen','PYTHONDONTWRITEBYTECODE':'1'},capture_output=True,text=True,timeout=45)
   output=result.stdout+result.stderr
   if result.returncode==0 or ('AssertionError' not in output) or ('ERROR:' in output):raise AssertionError(f'{name} did not fail an assertion: {output[-2000:]}')
   print('PASS mutation:',name,flush=True)
  finally:path.write_bytes(saved)
if __name__=='__main__':main()
