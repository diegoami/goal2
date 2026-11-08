"""[designed: #643 amendment] Prove the two explicitly authorized fixture diffs."""
import ast
import copy
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[2]
BASELINE = '320c595cf5333a68c5d3f96347465c087b1a324b'
FILES = ('goal2/tests/test_checkpoints_t149.py', 'goal2/tests/test_desktop_competitive_jobs.py')


def digest(node):
    return hashlib.sha256(ast.dump(node, include_attributes=False).encode()).hexdigest()


def functions(tree):
    return {cls.name + '.' + node.name: node for cls in tree.body if isinstance(cls, ast.ClassDef)
            for node in cls.body if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))}


def verify():
    rows = []
    for filename in FILES:
        before = ast.parse(subprocess.check_output(['git', 'show', BASELINE + ':' + filename],
                                                   cwd=ROOT, text=True))
        after = ast.parse((ROOT / filename).read_text())
        old, new = functions(before), functions(after)
        assert old.keys() <= new.keys(), filename
        changes = []
        assertions = 0
        for name, original in old.items():
            current = copy.deepcopy(new[name])
            prior = copy.deepcopy(original)
            old_assertions = [digest(n) for n in ast.walk(original) if isinstance(n, ast.Assert) or
                              isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and
                              n.func.attr.startswith('assert')]
            new_assertions = [digest(n) for n in ast.walk(current) if isinstance(n, ast.Assert) or
                              isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and
                              n.func.attr.startswith('assert')]
            assert old_assertions == new_assertions, (filename, name, 'assertions changed')
            assertions += len(old_assertions)
            if name == 'Jobs.stop':
                loop = next(n for n in current.body if isinstance(n, ast.For))
                loop.iter.elts.reverse()  # undo only wrapper-before-child fixture cleanup order
                changes.append(name + ': wrapper-before-child cleanup order')
            elif name == 'Jobs.test_a_killed_job_is_vanished_not_running_or_finished':
                # Replace the old child-kill/try-wrapper sequence with the authorized two kills.
                index = next(i for i,n in enumerate(prior.body) if isinstance(n,ast.Expr) and
                             isinstance(n.value,ast.Call) and ast.unparse(n.value.func)=='os.kill')
                old_child = prior.body[index]
                old_wrapper = prior.body[index + 1].body[0]
                assert isinstance(prior.body[index + 1], ast.Try)
                prior.body[index:index + 2] = [old_wrapper, old_child]
                changes.append(name + ': wrapper-before-child fixture kill order')
            elif name == 'CompetitiveJobsTests.test_qt_heartbeat_while_worker_full_time_tail_is_blocked':
                index = next(i for i,n in enumerate(current.body) if isinstance(n,ast.With) and
                             ast.unparse(n.items[0].context_expr)=='_precise_heartbeat_clock()')
                current.body[index:index + 1] = current.body[index].body
                changes.append(name + ': observation wrapped in balanced Windows precision scope')
            assert digest(prior) == digest(current), (filename, name, 'unexpected body change')
        rows.append({'file': filename, 'old_ast_sha256': digest(before), 'new_ast_sha256': digest(after),
                     'old_assertion_count': assertions, 'all_old_assertions_identical': True,
                     'all_existing_functions_identical_except': changes,
                     'new_test_helpers': sorted(new.keys() - old.keys())})
    jobs = 'tools/jobs.py'
    assert subprocess.check_output(['git', 'show', BASELINE + ':' + jobs], cwd=ROOT) == (ROOT/jobs).read_bytes()
    return {'baseline': BASELINE, 'files': rows, 'jobs_production_source_identical': True,
            'heartbeat_original_guarded_calls_timer_period_observation_threshold_and_worker_assertions_identical': True}


if __name__ == '__main__':
    print(json.dumps(verify(), indent=2))
