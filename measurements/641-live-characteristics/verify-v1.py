"""Static #641 source/evidence verification; never executes a game."""
import argparse,hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];FOLDER=Path(__file__).resolve().parent
p=argparse.ArgumentParser();p.add_argument('--private',action='store_true');args=p.parse_args()
index=json.loads((FOLDER/'acceptance-v1.json').read_text())
for group in ('sources_sha256','evidence_sha256'):
 for name,expected in index[group].items():
  assert hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==expected,(group,name)
assert hashlib.sha256((ROOT/'docs/design/ui-2026-11/manual-fidelity.md').read_bytes()).hexdigest()==index['fidelity_note_sha256']
if args.private:
 for name,expected in index['private_sha256'].items():
  assert hashlib.sha256(Path(name).read_bytes()).hexdigest()==expected,name
proof=index['actual_worker']
assert proof['complete'] and proof['full_same_choice_result_events_rng_memory_career_equal']
assert proof['state_event_identity_unchanged'] and proof['accepted_order_changed']
assert proof['traits_changed_vs_declared_kickoff_input'] and proof['natural_energy_changed_vs_declared_kickoff_input']
assert index['event_fields_removed']==[] and index['engine_or_trait_formulas_changed']==False
print(f"#641 bindings PASS: {len(index['sources_sha256'])} sources, {len(index['evidence_sha256'])} evidence files"
 +(f", {len(index['private_sha256'])} private artifacts" if args.private else ''))
