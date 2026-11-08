"""[designed: #643, T189/T194] Collect real scenarios; never execute their setup or matches."""
import importlib
import json
import os
from pathlib import Path
import subprocess
import sys
import unittest
from unittest.mock import patch

from goal2.tests import requires

ROOT = Path(__file__).resolve().parents[2]
MANIFEST = ROOT / 'measurements/643/selection.json'
CONTROLS = {
    'test_engine_pipe_t159': ('Framing', 'StandIn', 'TheChild'),
    'test_matches_on_pipe_t160': ('Tokens', 'Quit'),
    'test_ui_pitch_t166': ('BenchAndClose', 'Captain'),
    'test_ui_extras_t177': ('SearchAndFilter', 'Rename', 'NewCareer'),
    'test_watched_legacy_compatibility': ('LegacyCompatibilityTests.test_real_legacy_saves_roundtrip_without_relabeling_or_memory_rng_changes',),
    'test_watched_save': ('WatchedSaveTests.test_legacy_friendly_and_campaign_history_retain_v1_v2_meaning',),
    'test_desktop_competitive_jobs': ('CompetitiveJobsTests',),
    'test_ui_match_day_t167': ('HomeSide',),
    'test_watch_qualifiers_t176': ('Boundary',),
    'test_watched_bench_t102': ('BenchView', 'DroppedPause', 'PitchFreeze', 'EnterInPlay'),
    'test_watched_competitive_runtime': ('ConsumerAcceptanceTests',),
    'test_match_pitch_t94': ('Identity', 'FromTheGame'),
    'test_pitch_marks_t96': ('Glyphs', 'Frames', 'Drawing'),
    'test_live_team_tactics_610': ('TacticTransport', 'LiveTeamTactics'),
    'test_watched_adapter': ('WatchedAdapter.test_year_mapping_pinned_to_f025_both_start_calendars_and_wrap',
                             'WatchedAdapter.test_invalid_inputs_do_not_mutate_active_state',
                             'WatchedAdapter.test_each_default_decision_is_explicitly_answered',
                             'WatchedAdapter.test_distinct_same_minute_notices_are_not_a_no_progress_loop',
                             'WatchedAdapter.test_default_decision_policy_and_refusal_fail_closed'),
    'test_watched_publication': ('WatchedPublicationTests.test_cancel_and_wrong_tokens_preserve_active_state',),
}


def flatten(suite):
    for item in suite:
        if isinstance(item, unittest.TestSuite):
            yield from flatten(item)
        else:
            yield item


def selected(test):
    return not (getattr(type(test), '__unittest_skip__', False) or
                getattr(getattr(test, test._testMethodName), '__unittest_skip__', False))


def collect():
    """Use unittest's actual class/method and T182 load_tests collectors.

    Only optional dependency/file availability is modelled as prepared. The real
    requires.absent slow predicate and unittest skip markers remain authoritative.
    No collected TestCase or setUpClass is run; this needs no original asset bytes.
    """
    spec = json.loads(MANIFEST.read_text())
    absent = requires.absent
    loader = unittest.TestLoader()
    rows = {'scenarios': {}, 'wrappers': {}, 'controls': {}, 'layout': {}}
    def load(module, symbol):
        suite = loader.loadTestsFromName('goal2.tests.' + module + '.' + symbol)
        cases = list(flatten(suite))
        if not cases or any(isinstance(t, unittest.loader._FailedTest) for t in cases):
            raise AssertionError((module, symbol, loader.errors))
        return {t.id(): selected(t) for t in cases}
    with patch.object(requires, 'absent', side_effect=lambda **kw: absent(slow=kw.get('slow', False))):
        for item in spec['definitions']:
            rows['scenarios'].update(load(item['module'], item['symbol']))
        for module in spec['wrappers']:
            suite = loader.loadTestsFromModule(importlib.import_module('goal2.tests.' + module))
            rows['wrappers'][module] = {t.id(): selected(t) for t in flatten(suite)}
        for module, symbols in CONTROLS.items():
            for symbol in symbols:
                rows['controls'].update(load(module, symbol))
        # This one parity method was already slow; all synthetic fault controls stay fast.
        rows['controls'].pop('goal2.tests.test_desktop_competitive_jobs.CompetitiveJobsTests.'
                             'test_real_kind2_and_tied_knockout_match_direct_result_events_memory_seeds')
        from tools.check_premerge import LAYOUT_FIRST
        for module in LAYOUT_FIRST:
            suite = loader.loadTestsFromModule(importlib.import_module('goal2.tests.' + module))
            rows['layout'][module] = sorted(t.id() for t in flatten(suite))
    if loader.errors:
        raise AssertionError(loader.errors)
    rows['cases'] = requires.cases(range(10))
    return rows


@requires.need(modules=('PySide6', 'pygame', 'unicorn'))
class Selection(unittest.TestCase):
    def probe(self, slow):
        env = dict(os.environ, GOAL2_SLOW=str(int(slow)), PYTHONPATH=str(ROOT))
        env.pop('GOAL2_CASES', None)
        run = subprocess.run([sys.executable, '-B', str(Path(__file__).resolve()), '--collect'],
                             cwd=ROOT, env=env, text=True, capture_output=True, timeout=60)
        self.assertEqual(run.returncode, 0, run.stderr)
        return json.loads(run.stdout)

    def test_actual_collectors_select_full_matches_only_with_slow_and_keep_controls(self):
        fast, slow = self.probe(False), self.probe(True)
        self.assertGreater(len(fast['scenarios']), 23)
        self.assertEqual(set(fast['scenarios']), set(slow['scenarios']))
        self.assertFalse(any(fast['scenarios'].values()),
                         [k for k, v in fast['scenarios'].items() if v])
        self.assertTrue(all(slow['scenarios'].values()))
        self.assertEqual(set(fast['controls']), set(slow['controls']))
        self.assertTrue(all(fast['controls'].values()), fast['controls'])
        self.assertTrue(all(slow['controls'].values()), slow['controls'])
        self.assertEqual(fast['layout'], slow['layout'])
        self.assertEqual(len(fast['layout']), 11)
        for module in fast['wrappers']:
            self.assertEqual(set(fast['wrappers'][module]), set(slow['wrappers'][module]))
            for key, active in fast['wrappers'][module].items():
                if key in fast['scenarios']:
                    self.assertFalse(active, (module, key))
                    self.assertTrue(slow['wrappers'][module][key], (module, key))
        self.assertEqual(slow['cases'], list(range(10)))
        self.assertEqual(fast['cases'], [0])


if __name__ == '__main__':
    if '--collect' in sys.argv:
        print(json.dumps(collect(), sort_keys=True))
    else:
        unittest.main()
