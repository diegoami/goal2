#!/usr/bin/env python3
"""[designed: T42] Remove energy behaviors and require targeted regression failures.

Each source mutation restores its saved bytes in finally. Vendored code is never
changed. Run sequentially with other checks, with local campaign inputs staged.
"""
from pathlib import Path
import os
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
TEST = 'goal2.tests.test_campaign_energy.'
CASES = (
    ('half boundary', 'goal2/game/quick_match.py', 'campaign_energy.half_time(qm)', 'pass',
     'CampaignContinuations.test_boundaries_have_no_kickoff_bonus_then_half_bonus_and_fitness_restore'),
    ('fitness restoration', 'goal2/game/campaign_energy.py', 'return energy.restore(record, record[12])', 'return bytes(record)',
     'EnergyReferenceCases.test_half_bonus_and_restoration_preserve_zero_negative_and_other_bytes'),
    ('fixture recovery', 'goal2/game/quick_match.py', 'energy_transition = campaign_energy.finish(qm, game_state, with_confidence=True) if campaign is not None else None', 'energy_transition = None',
     'CampaignContinuations.test_real_campaign_recovery_consumes_sixty_ordered_draws_and_publishes_once'),
    ('completion guard', 'goal2/game/campaign_energy.py', "if prior.get('fixture_id') == fixture.fixture_id:", 'if False:',
     'CampaignContinuations.test_energy_completion_guard_refuses_a_second_transition'),
    ('saved transition', 'goal2/game/quick_match.py', 'if energy_transition is not None:', 'if False:',
     'CampaignContinuations.test_real_campaign_recovery_consumes_sixty_ordered_draws_and_publishes_once'),
    ('recovery selection', 'goal2/game/campaign_energy.py', 'gradual = in_set or (state.countries[country][0x2C] != host_continent)', 'gradual = False',
     'CampaignContinuations.test_gradual_selector_side_order_participating_bench_and_simulation_once'),
    ('participant set element', 'goal2/game/campaign_energy.py', 'bool(record[0x10] & 0x04)', 'bool(record[0x10] & 0x08)',
     'CampaignContinuations.test_gradual_selector_side_order_participating_bench_and_simulation_once'),
    ('redraw cap', 'goal2/game/campaign_energy.py', 'if energy.signed(value) > 32:', 'if energy.signed(value) > 64:',
     'EnergyReferenceCases.test_redraw_managed_unmanaged_age_threshold_and_clamp_order'),
)
for name, relative, before, after, test in CASES:
    path = ROOT / relative
    saved = path.read_bytes()
    text = saved.decode()
    if text.count(before) != 1:
        raise SystemExit(f'{name}: expected exactly one mutation site')
    try:
        path.write_text(text.replace(before, after))
        result = subprocess.run([sys.executable, '-B', '-m', 'unittest', TEST + test, '-v'],
                                cwd=ROOT, env={**os.environ, 'PYTHONDONTWRITEBYTECODE': '1'},
                                capture_output=True, text=True, timeout=60)
        if result.returncode == 0 or 'FAIL:' not in result.stderr or 'ERROR:' in result.stderr:
            raise SystemExit(f'{name}: expected behavioral assertion failure, got:\n{result.stdout}{result.stderr}')
        print(f'PROVED {name}: targeted assertion failed')
    finally:
        path.write_bytes(saved)
print('PASS 8 energy mutations; saved source bytes restored')
