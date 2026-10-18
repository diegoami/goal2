#!/usr/bin/env python3
"""[designed: #182] Validate the proposed GUI backlog's semantic coverage and assets.
This checks planning completeness; it does not accept any future runtime behavior.
"""
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
PLAN = ROOT / 'docs/design/football-gui'
TOPICS = {'state', 'keyboard', 'scaling', 'windows', 'regression'}


def check(root=ROOT):
    plan = root / 'docs/design/football-gui'
    errors = []
    if not (plan / 'plan.json').is_file():
        return ['missing design manifest, screen artifacts and bounded task contracts']
    manifest = json.loads((plan / 'plan.json').read_text())
    tasks = manifest['tasks']
    ids = {task['id'] for task in tasks}
    if ids != {f'T{n}' for n in range(74, 80)}:
        errors.append('expected the six reserved implementation slices T74–T79')
    mapping = {'Easy': 'Luna High', 'Medium': 'Sol Low', 'Hard': 'Sol Medium'}
    for task in tasks:
        if task['implementer'] != mapping.get(task['difficulty']) or task['reviewer'] != 'MiniMax M3':
            errors.append(f"{task['id']}: owner model mapping missing")
        if not TOPICS <= set(task['acceptance_topics']):
            errors.append(f"{task['id']}: acceptance misses state/keyboard/scaling/Windows/regression")
        for key in ('owns', 'negative_control', 'platform_evidence', 'depends_on'):
            if not task[key]:
                errors.append(f"{task['id']}: missing {key}")
        if not (root / task['contract']).is_file():
            errors.append(f"{task['id']}: missing reviewable task contract")
        if task['id'] in task['depends_on']:
            errors.append(f"{task['id']}: self dependency")
    def visit(name, seen):
        if name in seen:
            errors.append(f'dependency cycle at {name}')
            return
        item = next(t for t in tasks if t['id'] == name)
        for dep in item['depends_on']:
            if dep in ids:
                visit(dep, seen | {name})
    for name in ids:
        visit(name, set())
    if 'T66' not in next(t for t in tasks if t['id'] == 'T79')['depends_on']:
        errors.append('match presentation must wait for the T66 integration seam')
    required = {'overview', 'squad-tactics', 'match-result'}
    if set(manifest['screens']) != required:
        errors.append('missing overview, squad/tactics or match/result screen')
    for path in manifest['assets']:
        p = plan / path
        if not p.is_file():
            errors.append(f'missing original design artifact: {path}')
        if p.suffix.lower() not in {'.html', '.css', '.js', '.svg', '.md'}:
            errors.append(f'unexpected reference/game binary in design assets: {path}')
    contexts = manifest['prototype_contexts']
    if not {'active', 'preview', 'busy', 'unsupported', 'empty-result'} <= set(contexts):
        errors.append('prototype lacks an ownership/capability context')
    if manifest['runtime_changes'] or not manifest['illustrative_data']:
        errors.append('planning must remain separate from runtime and original data')
    return errors


if __name__ == '__main__':
    problems = check()
    for problem in problems:
        print('FAIL', problem)
    if problems:
        sys.exit(1)
    print('PASS six bounded contracts; dependency graph/model assignments; ownership/platform acceptance; three original screens')
