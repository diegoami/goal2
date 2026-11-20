"""[designed: #803] REST-only checkpoint reads/writes retain exact heads/checks."""
import json,unittest
from pathlib import Path
from goal2.tests.test_checkpoints_t149 import tool


class RestCheckpoint(unittest.TestCase):
    def setUp(self):self.cp=tool('checkpoint')

    def runner(self,issues=None,checks_error=False,fail_all=False):
        calls=[];posted=[]
        def run(args,cwd=None):
            calls.append(args)
            if args[:2]!=['gh','api']:return 1,'','HTTP403 GraphQL blocked'
            if fail_all:return 1,'','HTTP403 REST blocked'
            endpoint=args[2]
            if endpoint.endswith('pulls?state=open&per_page=50'):
                return 0,json.dumps([dict(number=9,title='change',head={'ref':'task/test','sha':'a'*40},draft=True,labels=[{'name':'task'}])]),''
            if '/check-runs?' in endpoint:
                if checks_error:return 1,'','checks unavailable'
                return 0,json.dumps({'check_runs':[dict(name='linux',status='completed',conclusion='success'),dict(name='windows',status='in_progress',conclusion=None)]}),''
            if endpoint.endswith('/status'):return 0,json.dumps({'statuses':[dict(context='security',state='success')]}),''
            if '/issues?' in endpoint:return 0,json.dumps(issues if issues is not None else [{'number':7},{'number':8,'pull_request':{}}]),''
            if endpoint.endswith('/issues/7/comments'):
                posted.append(json.loads(Path(args[args.index('--input')+1]).read_text()))
                return 0,json.dumps({'html_url':'https://github.com/example/repo/issues/7#issuecomment-1'}),''
            self.fail(args)
        return run,calls,posted

    def test_blocked_graphql_lists_exact_rest_heads_labels_and_checks(self):
        run,calls,_=self.runner();answer=self.cp.pulls('example/repo',run)
        self.assertNotIn('error',answer);p=answer['prs'][0]
        self.assertEqual((p['number'],p['headRefName'],p['headRefOid'],p['isDraft']),(9,'task/test','a'*40,True))
        self.assertEqual(p['labels'],[{'name':'task'}])
        summary=self.cp.checks(p['statusCheckRollup'])
        self.assertIn('success 2',summary);self.assertIn('in_progress 1 (windows)',summary)

    def test_rest_post_preserves_multiline_markdown_and_ignores_pull_requests(self):
        run,_,posted=self.runner();body='## Next\n\nLiteral `$(text)` and café\n'
        self.assertIn('issuecomment-1',self.cp.post('example/repo',body,run))
        self.assertEqual(posted,[{'body':body}])

    def test_failed_rest_fallback_is_reported(self):
        run,_,_=self.runner(fail_all=True);answer=self.cp.pulls('example/repo',run)
        self.assertIn('GraphQL blocked',answer['error']);self.assertIn('REST blocked',answer['error'])
        self.assertRaises(self.cp.CheckpointError,self.cp.post,'example/repo','body',run)

    def test_unreadable_checks_are_visible_instead_of_looking_green(self):
        run,_,_=self.runner(checks_error=True);answer=self.cp.pulls('example/repo',run)
        text=self.cp.checks(answer['prs'][0]['statusCheckRollup'])
        self.assertIn('error',text);self.assertIn('REST checks',text)

    def test_rest_post_refuses_ambiguous_or_missing_checkpoint(self):
        for issues in ([],[{'number':7},{'number':9}]):
            run,_,posted=self.runner(issues=issues)
            with self.subTest(issues=issues):
                self.assertRaisesRegex(self.cp.CheckpointError,'need exactly one',self.cp.post,'example/repo','body',run)
                self.assertEqual(posted,[])
