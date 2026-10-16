#!/usr/bin/env python3
"""[designed: T45] Require behavior failures and always restore source bytes."""
from pathlib import Path
import os
import subprocess
import sys
ROOT=Path(__file__).resolve().parents[1]
CASES=(
 ('captain full ID','goal2/game/campaign_pool.py','state.captain=candidate.captain','state.captain=candidate.captain & 255','test_campaign_pool.PoolCases.test_exchange_preserves_records_full_ids_xi_captain_country_words_and_roundtrip'),
 ('record preservation','goal2/game/campaign_pool.py','state.managed_squad=candidate.managed_squad;','state.players=[bytes(20)]*len(state.players);state.managed_squad=candidate.managed_squad;','test_campaign_pool.PoolCases.test_exchange_preserves_records_full_ids_xi_captain_country_words_and_roundtrip'),
 ('country ownership','goal2/game/campaign_pool.py','state.players[w][0]!=state.managed_country','False','test_campaign_pool.PoolCases.test_bad_ids_unavailable_foreign_duplicate_overlap_and_counts_reject_atomically'),
 ('eligibility gate','goal2/game/campaign_pool.py','eligibility.require_available(state.players,[incoming])','pass','test_campaign_pool.PoolCases.test_bad_ids_unavailable_foreign_duplicate_overlap_and_counts_reject_atomically'),
 ('tour gate','goal2/game/campaign_pool.py','if travelling(previous) and travelling(next_fixture):','if False:','test_campaign_pool.PoolCases.test_provisional_window_tour_competitive_exhausted_and_standalone'),
 ('reserve second bound','goal2/game/campaign_pool.py','second=qm.rng.rand(4)','second=qm.rng.rand(2)','test_campaign_pool_flow.PoolFlow.test_literal_pool_draw_bounds_order_and_status'),
 ('reserve confidence direction','goal2/game/campaign_pool.py','confidence.change(record[12],second-first)','confidence.change(record[12],first-second)','test_campaign_pool_flow.PoolFlow.test_literal_pool_draw_bounds_order_and_status'),
 ('reserve status','goal2/game/campaign_pool.py','eligibility.after_fixture(record,f.kind)','record','test_campaign_pool_flow.PoolFlow.test_literal_pool_draw_bounds_order_and_status'),
 ('prefix integration','goal2/game/campaign_energy.py','pool_transition = campaign_pool.finish(qm, state)','pool_transition = {}','test_campaign_pool_flow.PoolFlow.test_real_exchanged_player_and_ordered_prefix_continue_identically_after_resume'),
)
for name,relative,before,after,test in CASES:
 path=ROOT/relative;saved=path.read_bytes();source=saved.decode()
 if source.count(before)!=1:raise SystemExit(f'{name}: expected one site')
 try:
  path.write_text(source.replace(before,after))
  p=subprocess.run([sys.executable,'-B','-m','unittest','goal2.tests.'+test,'-v'],cwd=ROOT,env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1'},capture_output=True,text=True,timeout=60)
  if p.returncode==0 or 'FAIL:' not in p.stderr or 'ERROR:' in p.stderr:raise SystemExit(f'{name}: expected assertion failure\n{p.stdout}{p.stderr}')
  print(f'PROVED {name}: targeted assertion failed',flush=True)
 finally:path.write_bytes(saved)
# [designed] Moving an otherwise complete prefix must fail despite the same total seed steps.
path=ROOT/'goal2/game/campaign_energy.py';saved=path.read_bytes()
try:
 source=saved.decode().replace('pool_transition = campaign_pool.finish(qm, state)','pool_transition = None')
 source=source.replace('    qm._campaign_energy_complete = True','    if with_confidence:\n        pool_transition = campaign_pool.finish(qm, state)\n    qm._campaign_energy_complete = True')
 path.write_text(source)
 p=subprocess.run([sys.executable,'-B','-m','unittest','goal2.tests.test_campaign_pool_flow.PoolFlow.test_real_exchanged_player_and_ordered_prefix_continue_identically_after_resume','-v'],cwd=ROOT,env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1'},capture_output=True,text=True,timeout=60)
 if p.returncode==0 or 'FAIL:' not in p.stderr or 'ERROR:' in p.stderr:raise SystemExit('prefix order: expected assertion failure\n'+p.stderr)
 print('PROVED prefix order: targeted assertion failed',flush=True)
finally:path.write_bytes(saved)
print('PASS10 pool mutations; saved source bytes restored')
