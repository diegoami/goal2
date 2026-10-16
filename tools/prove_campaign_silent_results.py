#!/usr/bin/env python3
"""[designed: T48] Target consequential result/order/RNG/atomicity regressions."""
from pathlib import Path
import os,subprocess,sys
ROOT=Path(__file__).resolve().parents[1]
CASES=[
 ('single count batch','goal2/game/silent_results.py','score=qm.roll_quick_goals(12)','score=qm.roll_quick_goals(24)','test_one_source_contest_batch_extra_round_and_coin_keep_scores_and_rng_explicit'),
 ('decider extra count','goal2/game/silent_results.py','extra=qm.roll_quick_goals(4)','extra=qm.roll_quick_goals(12)','test_one_source_contest_batch_extra_round_and_coin_keep_scores_and_rng_explicit'),
 ('source coin polarity','goal2/game/silent_results.py','winner=int(qm.rng.rand(2)==1)','winner=int(qm.rng.rand(2)!=1)','test_one_source_contest_batch_extra_round_and_coin_keep_scores_and_rng_explicit'),
 ('ordered teams and draws','goal2/game/silent_results.py','qm.teams[:]=[fixture.side_a,fixture.side_b]','qm.teams[:]=[fixture.side_b,fixture.side_a]','test_lcg_accounting_and_stand_in_are_deterministic_and_do_not_touch_players'),
 ('prefix isolation','goal2/game/campaign_rounds.py','candidate = copy.deepcopy(state)','candidate = state','test_failed_prefix_suffix_and_browser_result_never_publish_partial_world_or_rng'),
 ('suffix isolation','goal2/game/campaign_rounds.py','candidate=copy.deepcopy(state)','candidate=state','test_failed_prefix_suffix_and_browser_result_never_publish_partial_world_or_rng'),
 ('source fixture order','goal2/game/campaign_rounds.py','fixture=world.fixtures[len(world.results)]','fixture=world.fixtures[len(world.fixtures)-len(world.results)-1]','test_first_two_turns_are_one_source_prefix_and_no_unattended_full_quick_loops'),
 ('CPU suffix completion','goal2/game/campaign_rounds.py','silent_until_managed(candidate,template,resolver_factory);validate_state(candidate)','validate_state(candidate)','test_first_two_turns_are_one_source_prefix_and_no_unattended_full_quick_loops'),
 ('duplicate identity','goal2/game/campaign_rounds.py',"row['fixture_id']!=fixture.fixture_id",'False','test_duplicate_order_and_rng_corruption_are_refused_by_save_decode'),
 ('RNG chain','goal2/game/campaign_rounds.py',"row['seed_before']!=seed or advance(seed,row['draws'])!=row['seed_after']",'False','test_duplicate_order_and_rng_corruption_are_refused_by_save_decode'),
 ('schedule persistence','goal2/game/campaign.py',"if self.world is not None:data['world']=self.world.to_data()",'if False:pass','test_full_source_schedule_saved_not_regenerated_and_identities_are_frozen'),
]
for name,relative,old,new,test in CASES:
 path=ROOT/relative;saved=path.read_bytes();source=saved.decode()
 if source.count(old)!=1:raise SystemExit(f'{name}: expected one proof site')
 try:
  path.write_text(source.replace(old,new))
  result=subprocess.run([sys.executable,'-B','-m','unittest','goal2.tests.test_campaign_silent_results.SilentRoundCases.'+test],cwd=ROOT,
                        env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1'},capture_output=True,text=True,timeout=60)
  output=result.stdout+result.stderr
  if result.returncode==0 or 'FAIL:' not in output or 'ERROR:' in output:raise SystemExit(f'{name}: expected targeted assertion failure\n{output[-2200:]}')
  print('PASS mutation:',name,flush=True)
 finally:path.write_bytes(saved)
print('PASS11 silent-result mutations; saved bytes restored')
