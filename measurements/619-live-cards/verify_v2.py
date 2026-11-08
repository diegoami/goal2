"""Verify #619 public evidence and current source bindings; no engine run."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
FOLDER = Path(__file__).resolve().parent
index = json.loads((FOLDER / 'acceptance-v2.json').read_text())
for group in ('sources_sha256', 'evidence_sha256'):
    for name, expected in index[group].items():
        actual = hashlib.sha256((ROOT / name).read_bytes()).hexdigest()
        if actual != expected:
            raise SystemExit(f'{group} hash mismatch: {name}')
for case in index['passing_cases']:
    lines = (ROOT / case['log']).read_text().splitlines()
    if not lines or lines[-1] != 'OK':
        raise SystemExit('case is not a complete PASS: ' + case['name'])
    for line in lines:
        if line.startswith('LIVE_CARDS_619 '):
            value = json.loads(line.split(' ', 1)[1])
            observations = value['observations']
            if any(not (row.get('all_records_and_rendered_fields_equal') or row.get('all_cards_equal')
                        or row.get('all_complete_decisions_equal')) for row in observations):
                raise SystemExit('incomplete card equality receipt: ' + case['name'])
            if sum(row['records'] for row in observations) != case['record_checks']:
                raise SystemExit('record count mismatch: ' + case['name'])
print(f"#619 bindings PASS: {len(index['sources_sha256'])} sources, "
      f"{len(index['evidence_sha256'])} evidence files, {len(index['passing_cases'])} complete passing cases")
