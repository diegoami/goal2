#!/usr/bin/env python3
"""[designed: T46] Require meaningful setup failures; restore saved bytes."""
from pathlib import Path
import os,subprocess,sys
ROOT=Path(__file__).resolve().parents[1]
CASES=(
 ('ability field','goal2/ai/cpu.py','ability = player_records[idx][4]','ability = player_records[idx][1]','test_literal_ability_is_not_age_and_ties_use_full_id'),
 ('ID tie','goal2/ai/cpu.py','return (-ability, idx)','return (-ability, -idx)','test_literal_ability_is_not_age_and_ties_use_full_id'),
 ('availability','goal2/game/computer.py','eligible = available_words(state.players, squad)','eligible = squad','test_pure_preparation_filters_unavailable_ability_not_age_and_preserves_all_state'),
 ('foreign record','goal2/game/computer.py','state.players[w][0]!=country','False','test_malformed_squad_foreign_players_human_side_and_too_few_reject'),
 ('human protection','goal2/game/computer.py','if country==state.managed_country:','if False:','test_malformed_squad_foreign_players_human_side_and_too_few_reject'),
 ('preview preparation','goal2/game/quick_match.py','        prepare_computer(game_state, teams[1-managed_side])','        pass','test_malformed_squad_foreign_players_human_side_and_too_few_reject'),
 ('actual pitch preparation','goal2/game/quick_match.py',"computer_eleven=list(prepared['eleven'])","computer_eleven=list(opponent_country['squad'][:11])",'test_runner_and_preview_use_current_opponent_for_both_managed_sides'),
 ('stored tactics input','goal2/game/computer.py',"'tactics':get_computer_tactics(record)","'tactics':0",'test_match_local_tactics_do_not_overwrite_stored_next_setup'),
 ('country publication scope','goal2/game/quick_match.py','        players = list(game_state.players)', '        changed=bytearray(game_state.countries[opponent]);changed[45]=qm._country(opponent)["tactics"];game_state.countries[opponent]=bytes(changed)\n        players = list(game_state.players)','test_match_local_tactics_do_not_overwrite_stored_next_setup'),
)
for name,relative,before,after,test in CASES:
 path=ROOT/relative;saved=path.read_bytes();source=saved.decode()
 if source.count(before)!=1:raise SystemExit(f'{name}: expected one site')
 try:
  path.write_text(source.replace(before,after))
  p=subprocess.run([sys.executable,'-B','-m','unittest','goal2.tests.test_campaign_cpu.CampaignCPU.'+test,'-v'],cwd=ROOT,env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1'},capture_output=True,text=True,timeout=60)
  if p.returncode==0 or 'FAIL:' not in p.stderr or 'ERROR:' in p.stderr:raise SystemExit(f'{name}: expected assertion failure\n{p.stdout}{p.stderr}')
  print(f'PROVED {name}: targeted assertion failed',flush=True)
 finally:path.write_bytes(saved)
print('PASS9 CPU mutations; saved bytes restored')
