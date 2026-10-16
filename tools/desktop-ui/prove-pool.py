#!/usr/bin/env python3
"""[designed: T71] Prove desktop exchange and identities with restored mutations."""
from pathlib import Path
import os
import subprocess
import sys
ROOT=Path(__file__).resolve().parents[2]
CASES=[
 ('exchange publication','goal2/desktop/model.py','self.state=candidate','self.state=self.state','test_view_filters_are_pure_and_exchange_matches_t45_full_identity_repair'),
 ('full reserve ID','goal2/desktop/model.py','campaign_pool.exchange(candidate,outgoing,incoming)','campaign_pool.exchange(candidate,outgoing,incoming & 255)','test_view_filters_are_pure_and_exchange_matches_t45_full_identity_repair'),
 ('copied candidate rollback','goal2/desktop/model.py','candidate=copy.deepcopy(self.state)','candidate=self.state','test_invalid_unavailable_closed_and_validation_failure_are_atomic'),
 ('search/filter','goal2/desktop/model.py','query=query,position=position',"query='',position=None",None),
 ('Qt exchange wire','goal2/desktop/window.py','self.exchange.clicked.connect(self.exchange_selected)','self.exchange.clicked.connect(lambda:None)',None),
 ('reserve rows','goal2/desktop/window.py',"self.reserves.setRowCount(len(view['reserves']))","self.reserves.setRowCount(len(view['reserves'])-1)",None),
]

def main():
 for name,relative,old,new,test in CASES:
  path=ROOT/relative;saved=path.read_bytes();text=saved.decode()
  count=text.count(old)
  if count<1:raise AssertionError(f'proof site changed: {name}')
  try:
   # [designed] Publication mutant may also affect other model transitions;
   # the focused test starts from a known valid generated game before exchange.
   if name=='exchange publication':
    start=text.index('    def exchange(');end=text.index('    def result_text(',start)
    text=text[:start]+text[start:end].replace(old,new)+text[end:]
   else:text=text.replace(old,new)
   path.write_text(text)
   if test:command=[sys.executable,'-B','-m','unittest','goal2.tests.test_desktop_pool.DesktopPoolCases.'+test]
   else:command=['/tmp/T69-desktop-venv/bin/python','-B','tools/desktop-ui/acceptance.py','--scenario','campaign-pool','--template','.cache/e010-r0008-halftime.sav','--data','.cache/GOAL.DAT']
   result=subprocess.run(command,cwd=ROOT,env={**os.environ,'QT_QPA_PLATFORM':'offscreen','PYTHONDONTWRITEBYTECODE':'1'},capture_output=True,text=True,timeout=45)
   output=result.stdout+result.stderr
   expected='AssertionError' in output and 'ERROR:' not in output
   if result.returncode==0 or not expected:raise AssertionError(f'{name} did not fail targeted check: {output[-1800:]}')
   print('PASS mutation:',name,flush=True)
  finally:path.write_bytes(saved)
if __name__=='__main__':main()
