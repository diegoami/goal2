"""[designed: owner, 2026-11-07] PR regression checks; full suites at milestones."""
import importlib
import io
import sys
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools'))
gate = importlib.import_module('check_premerge')
sys.path.remove(str(ROOT / 'tools'))


class ValidationPolicy(unittest.TestCase):
    def invoke(self, *flags, change_result=("goal2/engine/original_match/match.py",)):
        with patch.object(gate, 'check_checkout'), patch.object(gate, 'check_originals'), \
                patch.object(gate.subprocess, 'run'), patch.object(gate, 'check_tests') as tests, \
                patch.object(gate, 'slow_changes', return_value=change_result) as changes, \
                redirect_stdout(io.StringIO()):
            self.assertEqual(gate.main(['--expected-head', '0' * 40, *flags]), 0)
        return tests, changes

    def test_default_does_not_expand_an_engine_change_into_slow_suites(self):
        tests, changes = self.invoke()
        self.assertIs(tests.call_args.args[2], False)
        self.assertTrue(tests.call_args.kwargs['layout_slow'])
        changes.assert_not_called()

    def test_full_milestone_keeps_every_slow_module_enabled(self):
        tests, changes = self.invoke('--slow')
        self.assertIs(tests.call_args.args[2], True)
        self.assertTrue(tests.call_args.kwargs['layout_slow'])
        changes.assert_not_called()

    def test_explicit_fast_and_batch_fast_modes_remain_available(self):
        tests, _ = self.invoke('--fast')
        self.assertIs(tests.call_args.args[2], False)
        self.assertFalse(tests.call_args.kwargs['layout_slow'])
        tests, _ = self.invoke('--batch-fast')
        self.assertIs(tests.call_args.args[2], False)
        self.assertTrue(tests.call_args.kwargs['layout_slow'])

    def test_unreadable_main_does_not_implicitly_start_a_full_suite(self):
        tests, changes = self.invoke(change_result=None)
        self.assertIs(tests.call_args.args[2], False)
        changes.assert_not_called()

    def test_affected_scope_is_explicit_and_retains_the_import_graph_selection(self):
        from types import SimpleNamespace
        from unittest.mock import Mock
        graph = Mock()
        graph.affected.return_value = {'test_watched_adapter'}
        factory = Mock(return_value=graph)
        with patch.dict(sys.modules, {'slow_reach': SimpleNamespace(Graph=factory)}):
            tests, changes = self.invoke('--affected')
        changes.assert_called_once_with()
        self.assertEqual(tests.call_args.args[2], {'test_watched_adapter'})
        graph.affected.assert_called_once_with(('goal2/engine/original_match/match.py',))
