#!/usr/bin/env python3
"""[designed: T41] Prove routing, completion, tokens, rollback and history tests bite.

Mutate one source site per subprocess, restoring its saved bytes in finally.
Run from any checkout with the ignored local campaign test inputs staged.
"""
from pathlib import Path
import os
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
MODULE = "goal2.tests.test_campaign_friendlies.CampaignFriendlies."
CASES = (
    ("scheduled pair", "goal2/game/quick_match.py",
     'if getattr(game_state, "campaign", None) is not None:', "if False:",
     "test_actual_runner_uses_both_scheduled_pairs_and_stops_at_qualifier"),
    ("completion", "goal2/web/server.py",
     "candidate.campaign.complete_fixture(fixture.fixture_id)", "pass  # mutation: omit completion",
     "test_actual_runner_uses_both_scheduled_pairs_and_stops_at_qualifier"),
    ("stale token", "goal2/web/server.py",
     "not secrets.compare_digest(token, self._play_token)", "False",
     "test_stale_duplicate_wrong_fixture_and_management_tokens"),
    ("atomic publication", "goal2/web/server.py",
     "# Validate the full next browser view before making candidate state authoritative.",
     "self.state = candidate  # mutation: publish before response validation",
     "test_failed_simulation_and_failed_response_never_publish"),
    ("history persistence", "goal2/game/campaign.py",
     '"results": [dict(row, teams=list(row["teams"]), score=list(row["score"])) for row in self.results],',
     '"results": [],', "test_history_roundtrip_and_tampered_history_rejection"),
)
for label, relative, before, after, test in CASES:
    path = ROOT / relative
    saved = path.read_bytes()
    text = saved.decode()
    if text.count(before) != 1:
        raise SystemExit(f"{label}: expected exactly one mutation site")
    try:
        path.write_text(text.replace(before, after))
        result = subprocess.run([sys.executable, "-B", "-m", "unittest", MODULE + test, "-v"],
                                cwd=ROOT, env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
                                capture_output=True, text=True, timeout=60)
        if result.returncode == 0 or "FAIL:" not in result.stderr or "ERROR:" in result.stderr:
            raise SystemExit(f"{label}: expected assertion failure, got:\n{result.stdout}{result.stderr}")
        print(f"PROVED {label}: targeted behavioral assertion failed")
    finally:
        path.write_bytes(saved)
print("PASS 5 mutation proofs; saved source bytes restored")
