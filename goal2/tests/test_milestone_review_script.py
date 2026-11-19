"""[designed: owner, 2026-10-20] tools/milestone_review.sh: --print only shows the command (its header says so).

The script checked the candidate out before it looked at --print, leaving the checkout detached at the
candidate; and it fetched only origin's main and tags, so a pre-main candidate on a validation branch
(milestone #749) was reported as "not on origin". Both cases run here against a local origin, with a stub
`gh` that returns the issue body.
"""
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / 'tools' / 'milestone_review.sh'


def run(*args, cwd, env=None, check=True):
    return subprocess.run(args, cwd=cwd, env=env, check=check, capture_output=True, text=True)


@unittest.skipIf(shutil.which('bash') is None or os.name == 'nt', 'needs a POSIX bash')
class MilestoneReviewScript(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp, True)
        origin, seed = self.tmp / 'origin.git', self.tmp / 'seed'
        git_env = {**os.environ, 'GIT_AUTHOR_NAME': 't', 'GIT_AUTHOR_EMAIL': 't@t', 'GIT_COMMITTER_NAME': 't',
                   'GIT_COMMITTER_EMAIL': 't@t', 'GIT_CONFIG_GLOBAL': os.devnull, 'GIT_CONFIG_NOSYSTEM': '1'}
        self.git_env = git_env
        run('git', 'init', '-q', '--bare', str(origin), cwd=self.tmp, env=git_env)
        run('git', 'config', 'uploadpack.allowAnySHA1InWant', 'true', cwd=origin, env=git_env)
        run('git', 'init', '-q', '-b', 'main', str(seed), cwd=self.tmp, env=git_env)
        agent = seed / '.opencode' / 'agents' / 'milestone-reviewer.md'
        agent.parent.mkdir(parents=True)
        agent.write_text('---\nname: milestone-reviewer\n---\nReview it.\n')
        run('git', 'add', '.', cwd=seed, env=git_env)
        run('git', 'commit', '-q', '-m', 'one', cwd=seed, env=git_env)
        self.on_main = run('git', 'rev-parse', 'HEAD', cwd=seed, env=git_env).stdout.strip()
        (seed / 'b.txt').write_text('b\n')
        run('git', 'add', '.', cwd=seed, env=git_env)
        run('git', 'commit', '-q', '-m', 'two', cwd=seed, env=git_env)
        run('git', 'push', '-q', str(origin), 'main', cwd=seed, env=git_env)
        # A candidate only on a side branch of origin, as a pre-main milestone's validation branch.
        run('git', 'switch', '-q', '-c', 'validation', self.on_main, cwd=seed, env=git_env)
        (seed / 'c.txt').write_text('c\n')
        run('git', 'add', '.', cwd=seed, env=git_env)
        run('git', 'commit', '-q', '-m', 'side', cwd=seed, env=git_env)
        self.off_main = run('git', 'rev-parse', 'HEAD', cwd=seed, env=git_env).stdout.strip()
        run('git', 'push', '-q', str(origin), 'validation', cwd=seed, env=git_env)
        self.clone = self.tmp / 'clone'
        run('git', 'clone', '-q', '--single-branch', '-b', 'main', str(origin), str(self.clone), cwd=self.tmp,
            env=git_env)
        self.bin = self.tmp / 'bin'
        self.bin.mkdir()

    def review(self, candidate):
        gh = self.bin / 'gh'
        gh.write_text(f"#!/usr/bin/env bash\nprintf '%s\\n' 'Milestone.' '**Candidate**: `{candidate}`'\n")
        gh.chmod(0o755)
        env = {**self.git_env, 'PATH': f"{self.bin}{os.pathsep}{os.environ['PATH']}"}
        return run('bash', str(SCRIPT), '749', 'claude', 'opus', '--print', cwd=self.clone, env=env, check=False)

    def head(self):
        return (run('git', 'rev-parse', 'HEAD', cwd=self.clone, env=self.git_env).stdout.strip(),
                run('git', 'symbolic-ref', '-q', '--short', 'HEAD', cwd=self.clone, env=self.git_env,
                    check=False).stdout.strip())

    def test_print_leaves_the_checkout_where_it_is(self):
        before = self.head()
        result = self.review(self.on_main)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('claude -p --model opus', result.stdout)
        self.assertEqual(self.head(), before)
        self.assertEqual(before[1], 'main')

    def test_a_candidate_off_main_is_fetched_by_its_commit(self):
        result = self.review(self.off_main)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertNotIn('not on origin', result.stderr)
        self.assertEqual(self.head()[1], 'main')

    def test_an_unknown_candidate_is_refused(self):
        result = self.review('0' * 40)
        self.assertEqual(result.returncode, 2)
        self.assertIn('cannot be fetched', result.stderr)


if __name__ == '__main__':
    unittest.main()
