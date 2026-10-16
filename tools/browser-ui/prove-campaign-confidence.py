#!/usr/bin/env python3
"""[designed: T43] Require meaningful confidence regressions; restore saved bytes."""
from pathlib import Path
import os
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
CASES = (
    ('result integration', 'goal2/game/quick_match.py', 'with_confidence=True', 'with_confidence=False',
     'ConfidenceContinuations.test_result_update_publishes_confidence_and_view_morale'),
    ('participant update', 'goal2/game/campaign_confidence.py', 'out[12], = confidence.participant_values(record[12], delta, role, draws)', 'out[12] = record[12]',
     'ConfidenceReferenceCases.test_participants_bench_draw_order_clipping_and_untouched_bytes'),
    ('shadow restoration', 'goal2/game/campaign_confidence.py', 'for word, value in qm._campaign_confidence_shadow.items():', 'for word, value in ():',
     'ConfidenceContinuations.test_shadow_preserves_scorer_after_temporary_reaction_in_actual_event_order'),
    ('persistent scorer', 'goal2/game/campaign_confidence.py', 'shadow[word] = min(32, live - 256 if live >= 128 else live) & 255', 'pass',
     'ConfidenceContinuations.test_shadow_preserves_scorer_after_temporary_reaction_in_actual_event_order'),
    ('morale aggregate', 'goal2/game/campaign_confidence.py', 'return morale.team_panel_morale(values)', 'return 1',
     'ConfidenceReferenceCases.test_morale_signed_wrap_fixed_divisor_and_availability_elements'),
    ('unused ordering', 'goal2/game/campaign_energy.py', 'if with_confidence and not flag:', 'if False:',
     'ConfidenceContinuations.test_b7fa_interleaves_used_and_unused_confidence_with_recovery'),
    ('kind predicate', 'goal2/game/campaign_confidence.py', 'special = bool(kind_set[kind // 8] & (1 << (kind % 8)))', 'special = True',
     'ConfidenceReferenceCases.test_literal_rank_result_terms_and_kind_predicate'),
    ('availability set', 'goal2/game/campaign_confidence.py', 'not r[16] & 0xA4', 'not r[16] & 0xA8',
     'ConfidenceReferenceCases.test_morale_signed_wrap_fixed_divisor_and_availability_elements'),
)
for name, relative, before, after, test in CASES:
    path = ROOT / relative
    saved = path.read_bytes()
    text = saved.decode()
    if text.count(before) != 1:
        raise SystemExit(f'{name}: expected exactly one mutation site')
    try:
        path.write_text(text.replace(before, after))
        result = subprocess.run([sys.executable, '-B', '-m', 'unittest', 'goal2.tests.test_campaign_confidence.' + test, '-v'],
                                cwd=ROOT, env={**os.environ, 'PYTHONDONTWRITEBYTECODE': '1'},
                                capture_output=True, text=True, timeout=60)
        if result.returncode == 0 or 'FAIL:' not in result.stderr or 'ERROR:' in result.stderr:
            raise SystemExit(f'{name}: expected assertion failure, got:\n{result.stdout}{result.stderr}')
        print(f'PROVED {name}: targeted assertion failed')
    finally:
        path.write_bytes(saved)
print('PASS8 confidence mutations; saved source bytes restored')
