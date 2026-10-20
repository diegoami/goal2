"""[designed: T86] The documented walkthrough command is deterministic and redraw-neutral."""
import json
import re
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def walkthrough(*extra):
    run = subprocess.run([sys.executable, '-m', 'goal2.scenario', 'walkthrough', *extra], cwd=ROOT,
                         capture_output=True, timeout=300)
    if run.returncode:
        raise AssertionError(run.stderr.decode(errors='replace'))
    return run.stdout


class WalkthroughTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.first = walkthrough()

    def test_two_runs_are_byte_identical(self):
        self.assertEqual(walkthrough(), self.first)

    def test_redraw_and_view_calls_never_advance_the_session(self):
        self.assertEqual(walkthrough('--redraw', '4'), self.first)

    def test_session_reaches_every_next_fixture_through_the_controllers(self):
        record = json.loads(self.first)
        self.assertIn('not original data, not a career', record['lane'])
        self.assertEqual(record['final']['completed'], [f'original:{n}' for n in range(1, 5)])
        self.assertEqual(record['final']['match_count'], 4)
        self.assertEqual([r['mode'] for r in record['final']['results']],
                         ['quick', 'watched', 'competitive', 'competitive'])
        self.assertTrue(all(r['engine'] == 'goal2-scenario:fictional:1' for r in record['final']['results']))
        self.assertEqual(record['fixture_1_quick']['next'], 'Southmere — Northmarch (Friendly)')
        self.assertEqual(record['fixture_2_watched']['frames_rendered'], 24)
        self.assertEqual(record['fixture_4_competitive']['last_match']['resolution']['penalties'], [3, 4])
        unsupported = record['fixture_5_unsupported']
        self.assertEqual(unsupported['view']['play_label'], 'Play unavailable')
        self.assertIn('Saving refused', unsupported['save'])
        # [designed: T86] No job token or private temporary path reaches the record.
        text = self.first.decode()
        self.assertIsNone(re.search('[0-9a-f]{48}', text))
        self.assertNotIn('goal2-', text.replace('goal2-scenario:fictional:1', ''))


if __name__ == '__main__':
    unittest.main()
