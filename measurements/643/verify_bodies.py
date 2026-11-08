"""[designed: #643] Verify that approved definitions changed only by their slow decorator."""
import ast
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SPEC = json.loads(Path(__file__).with_name('selection.json').read_text())


def verify():
    checked = []
    for filename, expected in SPEC['source_ast'].items():
        tree = ast.parse((ROOT / filename).read_text())
        definitions = [row for row in SPEC['definitions'] if filename.endswith('/' + row['module'] + '.py')]
        for row in definitions:
            names = row['symbol'].split('.')
            node = next(n for n in tree.body if getattr(n, 'name', None) == names[0])
            if len(names) == 2:
                node = next(n for n in node.body if getattr(n, 'name', None) == names[1])
            decorators = [d for d in node.decorator_list if ast.unparse(d) == 'requires.need(slow=True)']
            assert len(decorators) == 1, row
            node.decorator_list.remove(decorators[0])
        actual = hashlib.sha256(ast.dump(tree, include_attributes=False).encode()).hexdigest()
        assert actual == expected, filename
        checked.append(filename)
    return {'baseline': SPEC['baseline'], 'definitions': len(SPEC['definitions']),
            'files': checked, 'only_approved_decorators_changed': True,
            'all_existing_bodies_assertions_fixtures_seeds_cases_thresholds_deadlines_identical': True}


if __name__ == '__main__':
    print(json.dumps(verify(), indent=2))
