#!/usr/bin/env python3
"""[designed: T47] Restore saved source bytes after every targeted negative."""
from pathlib import Path
import os,subprocess,sys
ROOT=Path(__file__).resolve().parents[2]
CASES=[
 ('no re-entry','goal2/game/substitutions.py',"if incoming in current['removed']:","if False:",'test_unlimited_friendlies_five_other_kinds_no_reentry_and_invalid_choices_are_pure'),
 ('five non-friendly','goal2/game/substitutions.py',"if current['kind']!=1 and len(current['changes'])>=5:","if False:",'test_unlimited_friendlies_five_other_kinds_no_reentry_and_invalid_choices_are_pure'),
 ('friendly unlimited','goal2/game/substitutions.py',"if current['kind']!=1 and len(current['changes'])>=5:","if len(current['changes'])>=5:",'test_live_engine_allows_six_friendly_swaps_and_rejects_reentry_atomically'),
 ('incoming eligibility','goal2/game/substitutions.py',"if incoming not in current['available']:","if False:",'test_unlimited_friendlies_five_other_kinds_no_reentry_and_invalid_choices_are_pure'),
 ('pitch rebind','goal2/game/quick_match.py','qm.c5dc(chosen,slot,side,incoming)','None','test_real_swaps_mark_participants_rebind_pitch_keep_positions_and_persist_high_ids'),
 ('persistence','goal2/game/quick_match.py',"if self.plan['changes']:","if False:",'test_real_swaps_mark_participants_rebind_pitch_keep_positions_and_persist_high_ids'),
 ('captain full ID','goal2/game/substitutions.py',"candidate['captain']=incoming","candidate['captain']=incoming & 255",'test_real_swaps_mark_participants_rebind_pitch_keep_positions_and_persist_high_ids'),
 ('save refusal','goal2/desktop/model.py',"if getattr(self,'match_pending',False):","if False:",'test_actual_worker_pauses_does_not_publish_or_overwrite_save_and_continues_once'),
 ('stale continuation','goal2/desktop/jobs.py','if self.model.state is not self.original or encode(self.model.state,self.model.template_bytes)!=self.snapshot:','if False:','test_cancel_and_stale_halftime_preserve_the_active_game_and_prior_save'),
 ('second-half RNG continuity','goal2/game/quick_match.py','second_kickoff = qm.eight30b','second_kickoff = qm.eight30b;qm.rng.seed=4660','test_no_substitution_split_matches_prechange_complete_state_hashes_for_both_sides'),
 ('preview validation','goal2/desktop/jobs.py','self.validate_halftime(packet)','None','test_bad_preview_failed_worker_and_bad_continuation_leave_game_and_save_untouched'),
 ('Qt substitution wire','goal2/desktop/window.py','self.substitute.clicked.connect(self.substitute_halftime)','self.substitute.clicked.connect(lambda:None)',None),
 ('Qt continuation wire','goal2/desktop/window.py','self.continue_match.clicked.connect(self.continue_halftime)','self.continue_match.clicked.connect(lambda:None)',None),
]

def main():
 for name,relative,old,new,test in CASES:
  path=ROOT/relative;saved=path.read_bytes();text=saved.decode()
  if text.count(old)!=1:raise AssertionError(f'proof site changed: {name}')
  try:
   path.write_text(text.replace(old,new))
   if test:command=[sys.executable,'-B','-m','unittest','goal2.tests.test_campaign_substitutions.HalftimeCases.'+test]
   else:command=['/tmp/T69-desktop-venv/bin/python','-B','tools/desktop-ui/acceptance.py','--scenario','campaign-halftime','--template','.cache/e010-r0008-halftime.sav','--data','.cache/GOAL.DAT']
   result=subprocess.run(command,cwd=ROOT,env={**os.environ,'QT_QPA_PLATFORM':'offscreen','PYTHONDONTWRITEBYTECODE':'1'},capture_output=True,text=True,timeout=45)
   output=result.stdout+result.stderr
   expected='AssertionError' in output and 'ERROR:' not in output
   if result.returncode==0 or not expected:raise AssertionError(f'{name} did not fail intended check: {output[-2200:]}')
   print('PASS mutation:',name,flush=True)
  finally:path.write_bytes(saved)
if __name__=='__main__':main()
