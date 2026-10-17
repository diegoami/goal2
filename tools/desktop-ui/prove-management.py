#!/usr/bin/env python3
"""[designed: T69] Prove controller and actual widget wiring; restore all bytes."""
from pathlib import Path
import os
import subprocess
import sys
ROOT=Path(__file__).resolve().parents[2]
CASES=(
 ('captain full ID','goal2/desktop/model.py','candidate.captain=captain;','candidate.captain=captain & 255;','test_desktop_model.DesktopModelCases.test_confirm_full_ids_and_bits_is_atomic_and_rejects_unavailable'),
 ('tactics publication','goal2/desktop/model.py','candidate.country_tactics=tactics','candidate.country_tactics=0','test_desktop_model.DesktopModelCases.test_confirm_full_ids_and_bits_is_atomic_and_rejects_unavailable'),
 ('availability','goal2/desktop/model.py','eligibility.require_available(self.state.players,eleven)','pass','test_desktop_model.DesktopModelCases.test_confirm_full_ids_and_bits_is_atomic_and_rejects_unavailable'),
 ('resume publication','goal2/desktop/model.py','self.state=candidate;self.template_bytes=raw;','self.template_bytes=raw;','test_desktop_model.DesktopModelCases.test_save_resume_preserves_complete_state_without_regeneration_and_rejects_bad_input'),
 ('saved tactics','goal2/desktop/model.py','save_state(Path(path),self.state,self.template_bytes)','candidate=copy.copy(self.state);candidate.country_tactics=0;save_state(Path(path),candidate,self.template_bytes)','test_desktop_model.DesktopModelCases.test_save_resume_preserves_complete_state_without_regeneration_and_rejects_bad_input'),
 ('dependency instruction','goal2/desktop/__main__.py','Install the desktop extra:','Instructions omitted:','test_desktop_entry.DesktopEntryCases.test_missing_qt_reports_install_instruction_before_reading_assets'),
 ('confirm widget wire','goal2/desktop/window.py','self.confirm.clicked.connect(self.confirm_draft)','self.confirm.clicked.connect(lambda:None)',None),
 ('country draft isolation','goal2/desktop/window.py','        self.country.currentIndexChanged.connect(self.country_changed)','        self.country.currentIndexChanged.connect(self.country_changed)\n        self.country.currentIndexChanged.connect(lambda _:self.model.new_campaign(self.country.currentData()))',None),
)
for name,relative,before,after,test in CASES:
 path=ROOT/relative;saved=path.read_bytes();source=saved.decode()
 if source.count(before)!=1:raise SystemExit(f'{name}: expected one mutation site')
 try:
  path.write_text(source.replace(before,after))
  cmd=([sys.executable,'-B','-m','unittest','goal2.tests.'+test,'-v'] if test else [sys.executable,'-B','tools/desktop-ui/acceptance.py','--scenario','management','--template','.cache/e010-r0008-halftime.sav','--data','.cache/GOAL.DAT'])
  p=subprocess.run(cmd,cwd=ROOT,env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1','QT_QPA_PLATFORM':'offscreen'},capture_output=True,text=True,timeout=60)
  expected=('FAIL:' in p.stderr and 'ERROR:' not in p.stderr) if test else 'AssertionError' in p.stderr
  if p.returncode==0 or not expected:raise SystemExit(f'{name}: expected behavioral assertion failure\n{p.stdout}{p.stderr}')
  print(f'PROVED {name}: targeted assertion failed',flush=True)
 finally:path.write_bytes(saved)
print('PASS8 desktop mutations; saved source bytes restored')
