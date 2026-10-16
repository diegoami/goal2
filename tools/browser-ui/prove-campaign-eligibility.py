#!/usr/bin/env python3
"""[designed: T44] Require meaningful eligibility regressions; restore saved bytes."""
from pathlib import Path
import os
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
CASES = (
    ('kickoff gate', 'goal2/game/quick_match.py', 'eligibility.validate_teams(game_state, teams, managed_side)', 'pass',
     'EligibilityContinuations.test_unavailable_starter_blocks_preview_and_play_without_state_change'),
    ('management gate', 'goal2/web/server.py', 'eligibility.require_available(self.state.players, eleven)', 'pass',
     'EligibilityContinuations.test_management_rejects_unavailable_eleven_then_allows_human_repair'),
    ('computer filtering', 'goal2/game/computer.py', 'eligible = available_words(state.players, squad)', 'eligible = squad',
     'EligibilityContinuations.test_computer_uses_only_available_players_and_refuses_fewer_than_eleven'),
    ('ban expiry', 'goal2/game/eligibility.py', 'status = out[16] & ~0x80', 'status = out[16]',
     'EligibilityReferenceCases.test_b27f_literal_transitions_preserve_all_other_bytes'),
    ('second booking', 'goal2/game/eligibility.py', 'status = (status | 0x80) & ~0x08', 'status &= ~0x08',
     'EligibilityContinuations.test_status_persists_through_save_and_expires_only_at_next_played_fixture'),
    ('status persistence', 'goal2/game/eligibility.py', 'qm.playerrec.update(updated)', 'pass',
     'EligibilityContinuations.test_status_persists_through_save_and_expires_only_at_next_played_fixture'),
    ('completion guard', 'goal2/game/eligibility.py', "if getattr(qm, '_campaign_eligibility_complete', False):", 'if False:',
     'EligibilityContinuations.test_status_runs_once_and_only_for_fixture_countries'),
    ('unrelated bits', 'goal2/game/eligibility.py', 'out[16] = status & ~0x10', 'out[16] = (status & ~0x10) & 0xB8',
     'EligibilityReferenceCases.test_b27f_literal_transitions_preserve_all_other_bytes'),
    ('unplayed kind0', 'goal2/game/eligibility.py', 'if kind == 0:', 'if False:',
     'EligibilityReferenceCases.test_b27f_literal_transitions_preserve_all_other_bytes'),
    ('fixture integration', 'goal2/game/quick_match.py', 'energy_transition["eligibility"] = eligibility.finish(qm, game_state)', 'energy_transition["eligibility"] = None',
     'EligibilityContinuations.test_status_runs_once_and_only_for_fixture_countries'),
)
for name, relative, before, after, test in CASES:
    path = ROOT / relative
    saved = path.read_bytes()
    text = saved.decode()
    if text.count(before) != 1:
        raise SystemExit(f'{name}: expected exactly one mutation site')
    try:
        path.write_text(text.replace(before, after))
        result = subprocess.run([sys.executable, '-B', '-m', 'unittest', 'goal2.tests.test_campaign_eligibility.' + test, '-v'],
                                cwd=ROOT, env={**os.environ, 'PYTHONDONTWRITEBYTECODE': '1'},
                                capture_output=True, text=True, timeout=60)
        if result.returncode == 0 or 'FAIL:' not in result.stderr or 'ERROR:' in result.stderr:
            raise SystemExit(f'{name}: expected assertion failure, got:\n{result.stdout}{result.stderr}')
        print(f'PROVED {name}: targeted assertion failed')
    finally:
        path.write_bytes(saved)
print('PASS10 eligibility mutations; saved source bytes restored')
