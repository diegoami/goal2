"""[designed: #802/#804] Test inputs cannot hide under documentation paths."""
import ast,os,re,subprocess,sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tools'))
import ci_changes
sys.path.remove(str(ROOT/'tools'))
from goal2.tests import test_ci_slow_runners_493 as previous


class InputPushes(unittest.TestCase):
    setUp=previous.CiChanges.setUp
    commit=previous.CiChanges.commit
    decide=previous.CiChanges.decide
    def test_every_existing_input_kind_runs_even_as_a_followup_push(self):
        previous=self.commit('goal2/ui/window.py')
        for path in ('docs/core.md','docs/design/ui-2026-11/README.md','docs/screens.md',
                     'docs/evidence/T62-watched-kit.json','measurements/643/selection.json',
                     'measurements/646-team-layout/expected-reviewed-runtime-698-v2.json',
                     'measurements/725-retained-finals/native-v1.json','measurements/T148/run_native.py',
                     'docs/design/ui-2026-11/check_density.py','docs/original-game/images/reference.png'):
            with self.subTest(path=path):
                self.commit(path)
                self.assertTrue(self.decide(previous,kind='code'))
                previous=self.run('rev-parse','HEAD')

    def test_ordinary_markdown_followup_still_skips(self):
        previous=self.commit('goal2/ui/window.py');self.commit('docs/handover-example.md')
        self.assertFalse(self.decide(previous,kind='code'))


class MainPushAndWindows(unittest.TestCase):
    def test_main_workflow_filters_match_the_selector_exceptions(self):
        expected=['**','!**/*.md',*sorted(ci_changes.MARKDOWN_INPUTS)]
        for name in ('ci.yml','windows.yml','package.yml'):
            with self.subTest(workflow=name):
                text=(ROOT/'.github/workflows'/name).read_text()
                push=text.split('  push:\n',1)[1].split('  workflow_dispatch:',1)[0]
                match=re.search(r'^    paths: (\[.*\])$',push,re.M)
                self.assertIsNotNone(match,'main must not ignore whole docs/measurements trees')
                self.assertEqual(ast.literal_eval(match[1]),expected)
                self.assertNotIn('paths-ignore:',push)

    def test_windows_missing_fixture_token_fails_owned_runs_and_allows_forks(self):
        text=(ROOT/'.github/workflows/windows.yml').read_text()
        blocks=text.split('      - name: Original-game files ')[1:]
        self.assertEqual(len(blocks),1)
        native=text.split('      - name: Original fixtures for the native probe',1)[1]
        self.assertIn('test -n "$GOAL2_RCLONE_TOKEN"',native)
        self.assertIn('native proof cannot run"; exit 1;',native)
        for block in blocks:
            script=block.split('        run: |\n',1)[1].split('          version=',1)[0]
            script='\n'.join(line[10:] for line in script.splitlines())
            for fork,expected in (('false',1),('true',0)):
                with self.subTest(block=block.splitlines()[0],fork=fork):
                    env=dict(os.environ,GOAL2_RCLONE_TOKEN='',FORK=fork)
                    result=subprocess.run(['bash','-c',script],env=env,text=True,capture_output=True)
                    self.assertEqual(result.returncode,expected,result.stdout+result.stderr)
                    self.assertIn('FORK:',block.split('        run:',1)[0])
