#!/usr/bin/env python3
"""[designed: T64] Kill publication/save mutations without editing vendored engine files."""
from pathlib import Path
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[1]
MUTATIONS=[
    ('stop at full-time before original tail','goal2/game/watched_match.py',
     '        events.append(copy.deepcopy(ev))',
     "        events.append(copy.deepcopy(ev))\n        if ev.kind == 'full_time':break",
     'goal2.tests.test_watched_publication.WatchedPublicationTests.test_campaign_completes_and_appends_history_exactly_once',
     'the match is not over'),
    ('omit full returned Memory','goal2/game/watched_publication.py',
     '    candidate.mem=bytes(outcome.memory)',
     '    candidate.mem=bytes(state.mem)',
     'goal2.tests.test_watched_publication.WatchedPublicationTests.test_all_ten_strict_cases_publish_direct_runner_memory_once',
     'watched returned memory differs'),
    ('omit returned country records','goal2/game/watched_publication.py',
     'candidate.countries=image.countries()',
     'candidate.countries=list(state.countries)',
     'goal2.tests.test_watched_publication.WatchedPublicationTests.test_all_ten_strict_cases_publish_direct_runner_memory_once',
     'AssertionError'),
    ('omit returned squad order','goal2/game/watched_publication.py',
     '    candidate.managed_squad=image.squad(state.managed_country)',
     '    candidate.managed_squad=list(state.managed_squad)',
     'goal2.tests.test_watched_publication.WatchedPublicationTests.test_changed_job_and_malformed_completions_cannot_publish',
     'AssertionError'),
    ('accept result from another management input','goal2/game/watched_publication.py',
     "    if result['image_sha256'] != expected_image.sha256():",
     '    if False:',
     'goal2.tests.test_watched_publication.WatchedPublicationTests.test_changed_job_and_malformed_completions_cannot_publish',
     'ValueError not raised'),
    ('duplicate original player effects','goal2/game/watched_publication.py',
     '    candidate.players=image.players();candidate.countries=image.countries()',
     "    candidate.players=[bytes((2*a-b)&255 for a,b in zip(after,before)) for after,before in zip(image.players(),state.players)];candidate.countries=image.countries()",
     'goal2.tests.test_watched_publication.WatchedPublicationTests.test_all_ten_strict_cases_publish_direct_runner_memory_once',
     'AssertionError'),
    ('duplicate scheduled completion','goal2/game/watched_publication.py',
     '        campaign.complete_fixture(pending.fixture_id)',
     '        campaign.complete_fixture(pending.fixture_id)\n        campaign.completed_fixture_ids.append(pending.fixture_id)',
     'goal2.tests.test_watched_publication.WatchedPublicationTests.test_campaign_completes_and_appends_history_exactly_once',
     'AssertionError'),
    ('reuse completion token and old snapshot','goal2/game/watched_publication.py',
     "        self._pending=None\n        if self.owner.state is not original or self.owner.state!=snapshot or self.owner.template_bytes!=template:",
     '        if False:',
     'goal2.tests.test_watched_publication.WatchedPublicationTests.test_campaign_completes_and_appends_history_exactly_once',
     'ValueError not raised'),
    ('erase watched history after quick continuation','goal2/game/campaign_rounds.py',
     "                if not any(history['fixture_id']==row['fixture_id'] and watched(history)",
     "                if False and not any(history['fixture_id']==row['fixture_id'] and watched(history)",
     'goal2.tests.test_watched_save.WatchedSaveTests.test_fresh_1990_1992_campaign_history_and_deterministic_next_fixture',
     'SessionSaveError not raised'),
    ('erase latest watched result engine identity','goal2/game/watched_schema.py',
     "            if managed and managed[-1]['mode']=='watched' and not watched(last):",
     '            if False:',
     'goal2.tests.test_watched_save.WatchedSaveTests.test_fresh_1990_1992_campaign_history_and_deterministic_next_fixture',
     'SessionSaveError not raised'),
    ('forget original RNG after quick continuation','goal2/game/watched_schema.py',
     "                if (row['seed_after']!=image.rd(0x7B62) or row['secondary_after']!=image.rd(0x8336)",
     '                if (False',
     'goal2.tests.test_watched_save.WatchedSaveTests.test_fresh_1990_1992_campaign_history_and_deterministic_next_fixture',
     'SessionSaveError not raised'),
    ('omit watched save validation' ,'goal2/game/session_save.py',
     '''    try:
        from goal2.game.watched_schema import needs_version3, validate_saved_watched
        validate_saved_watched(state)
        if needs_version3(state) and version not in (_WATCHED_VERSION, VERSION):
            raise ValueError("watched results require session version 3")
    except (ValueError, IndexError, KeyError, TypeError) as exc:
        raise SessionSaveError(f"invalid watched data: {exc}") from exc
''',
     '',
     'goal2.tests.test_watched_save.WatchedSaveTests.test_watched_roundtrip_and_malformed_saves',
     'SessionSaveError not raised'),
]
for name,file,old,new,test,diagnostic in MUTATIONS:
    path=ROOT/file;saved=path.read_bytes()
    try:
        source=saved.decode()
        if source.count(old)!=1:raise AssertionError(f'mutation site changed: {name}')
        path.write_text(source.replace(old,new))
        result=subprocess.run([sys.executable,'-B','-m','unittest','-f',test,'-v'],cwd=ROOT,
                              capture_output=True,text=True,timeout=300)
        output=result.stdout+result.stderr
        if result.returncode==0 or diagnostic not in output or 'TimeoutError' in output:
            raise AssertionError(f'mutation did not fail the required assertion: {name}\n{output}')
        print(f'PASS mutation: {name} ({diagnostic})',flush=True)
    finally:path.write_bytes(saved)
print(f'PASS {len(MUTATIONS)} watched publication/save mutations; saved bytes restored')
