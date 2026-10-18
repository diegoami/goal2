"""[designed: T81] Evidence-tool contract and saved-byte negative controls.

[confirmed: F013, kit424d599] Expectations use original signed draw operands,
A260 squad binding, 2BE5 half comparison and 2DCA/2E00 predicates.
"""
import copy
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import time
import unittest
from types import SimpleNamespace

from tools import probe_watched_pitch as probe

ROOT = Path(__file__).resolve().parents[2]
EVIDENCE = ROOT / 'docs/evidence/T81'


class ProjectionTests(unittest.TestCase):
    def test_signed_draw_axes(self):
        self.assertEqual([probe.signed(x) for x in (0, 127, 128, 247, 248, 255)],
                         [0, 127, -128, -9, -8, -1])
        # [derived: 8537/8F10] Asymmetric original byte operands expose inversion.
        self.assertEqual(probe.project_xy(-3, 17), [17, -3], 'original draw axes')
        self.assertEqual(probe.draw_offset(-3, 17), 1872)
        self.assertEqual(probe.project_xy(4, -31), [-31, 4])

    def test_identity_uses_fixture_side_and_local_slot(self):
        # [confirmed: A260/2974] Low pitch slots bind fixture second, high first.
        for slot, team, number, player in [(1, 1, 1, 372), (11, 1, 11, 378),
                                            (12, 0, 1, 121), (22, 0, 11, 131)]:
            row = probe.project_player(dict(slot=slot, player=player, x=248, y=17,
                                            state=9, team=team), 11)
            self.assertEqual((row['team'], row['number'], row['player']),
                             (team, number, player), 'original squad identity')
            self.assertEqual(row['screen'], [17, -8])
            self.assertEqual(row['state'], 9)
        # [designed] A changed player word is an identity rebind, never a shirt.
        row = probe.project_player(dict(slot=1, player=999, x=0, y=0, state=1), 11)
        self.assertEqual((row['number'], row['player']), (1, 999))

    def test_half_selector_and_terminal_boundaries(self):
        for threshold, remaining, flag in [(45, 91, 1), (45, 46, 1), (45, 45, 0),
                                            (45, 44, 0), (255, 0, 1), (128, 0, 1)]:
            self.assertEqual(probe.attack_selector(threshold, remaining), flag, 'original half selector')
        for kind, data, expected in [('tick', {}, True), ('half_time', {}, True),
                                      ('decision', {'context': 'half_time'}, True),
                                      ('end', {}, False), ('full_time', {}, False),
                                      ('commentary', {}, False),
                                      ('decision', {'context': 'substitution'}, False)]:
            event = SimpleNamespace(kind=kind, data=data)
            self.assertEqual(probe.observe_boundary(event), expected, 'completed pitch boundary')

    def test_predicates_are_not_lifecycle_clamps(self):
        for x, y, inside in [(8, 37, True), (-8, -37, True), (9, 37, False),
                              (8, 38, False), (-9, -39, False), (11, 0, False)]:
            self.assertEqual(probe.predicate(x, y, probe.IN_PLAY), inside)
        for x, y, inside in [(9, 39, True), (-9, -39, True), (10, 0, False), (0, 40, False)]:
            self.assertEqual(probe.predicate(x, y, probe.MOVEMENT), inside)
        # [confirmed: 8537] Drawing tests the exact packed sentinel, not state or
        # in-play predicate. Initialization (-9,0) must survive unclamped.
        hidden = probe.project_player(dict(slot=1, player=372, x=11, y=0, state=1), 11)
        initial = probe.project_player(dict(slot=1, player=372, x=247, y=0, state=1), 11)
        other = probe.project_player(dict(slot=1, player=372, x=11, y=1, state=1), 11)
        self.assertTrue(hidden['hidden'], 'original sentinel visibility')
        self.assertTrue(probe.hidden_xy(11, 0, 11), 'original sentinel visibility')
        self.assertFalse(probe.hidden_xy(-9, 0, 11))
        self.assertFalse(probe.hidden_xy(11, 1, 11))
        self.assertFalse(initial['hidden'])
        self.assertFalse(other['hidden'])
        self.assertEqual(initial['x'], -9)


class FidelityTests(unittest.TestCase):
    @staticmethod
    def outcome():
        # [designed] Synthetic bytes, never original guest bytes.
        return dict(events=[dict(kind='goal', minute=7, score=[1, 0], data={'player': 123}),
                            dict(kind='end', minute=91, score=[1, 0], data={})],
                    result=dict(score=[1, 0], nested=dict(tail=[1, 2, 3])),
                    memory=b'synthetic complete memory', seeds=(5, 9))

    def test_canonical_fidelity(self):
        baseline = self.outcome()
        sampled = copy.deepcopy(baseline)
        sampled['events'].insert(0, dict(kind='tick', minute=0, score=[0, 0], data={'subtick': 0}))
        probe.assert_fidelity(baseline, sampled)

    def test_all_complete_outcomes_are_compared(self):
        for kind, message in [('events', 'canonical events changed'), ('result', 'complete result changed'),
                              ('memory', 'complete Memory changed'), ('seeds', 'both RNG seeds changed')]:
            baseline = self.outcome()
            changed = copy.deepcopy(baseline)
            if kind == 'events':
                changed[kind][0]['data']['player'] = 124
            elif kind == 'result':
                changed[kind]['nested']['tail'][-1] = 4
            elif kind == 'memory':
                changed[kind] += b'changed'
            else:
                changed[kind] = (5, 10)
            with self.subTest(kind=kind), self.assertRaisesRegex(AssertionError, message):
                probe.assert_fidelity(baseline, changed)


class ReportTests(unittest.TestCase):
    def test_retained_full_cases(self):
        report = json.loads((EVIDENCE / 'runtime-03.json').read_text())
        self.assertEqual(report['source']['pin'], '424d5998076da1e4efc399c2715689ddb44d3e1a')
        self.assertEqual(report['source']['observer_sha256'], hashlib.sha256(Path(probe.__file__).read_bytes()).hexdigest())
        self.assertEqual(report['source']['vendor_files_verified'], 16)
        self.assertEqual(report['inputs']['seeds'], [257, 4660])
        self.assertEqual(report['inputs']['fixture'], [7, 19, 21])
        self.assertEqual(len(report['cases']), 2)
        for case, ticks, changes in zip(report['cases'], [4279, 4146], [4277, 4144]):
            with self.subTest(seed=case['seed']):
                b, o = case['baseline'], case['observed']
                self.assertFalse(b['sampled'])
                self.assertTrue(o['sampled'])
                self.assertEqual(b['outcome'], o['outcome'])
                self.assertEqual(o['counts']['ticks'], ticks)
                self.assertEqual(o['counts']['repeated_reads'], ticks)
                self.assertEqual(o['counts']['changed_poses'], changes)
                self.assertEqual(o['half_flags'], [0, 1])
                self.assertGreater(o['counts']['ball_changes'], 0)
                transition = [t for t in o['transitions'] if t['reason'] == 'adjacent tick half flag change']
                self.assertEqual(len(transition), 1)
                before, after = transition[0]['before'], transition[0]['after']
                self.assertEqual(after['sequence'], before['sequence'] + 1)
                self.assertEqual((before['half_flag'], after['half_flag']), (1, 0))
                self.assertEqual(before['threshold'], 45)
                self.assertEqual((before['remaining'], after['remaining']), (46, 45))
                self.assertEqual(before['attack_by_team'], [1, -1])
                self.assertEqual(after['attack_by_team'], [-1, 1])
                self.assertEqual(o['first']['players'][0]['team'], 1)
                self.assertEqual(o['first']['players'][11]['team'], 0)
                self.assertEqual(o['first']['sentinel_word'], 11)
                self.assertEqual(o['first']['initialization_word'], 247)


class SavedByteControls(unittest.TestCase):
    def test_saved_byte_mutations_fail_intended_assertions(self):
        # [designed] A new immutable receipt per invocation. Mutate only the
        # non-vendored tool, restore exact saved bytes even on failure. A fresh
        # cache prefix plus -B excludes existing timestamp/size-based bytecode.
        path = ROOT / 'tools/probe_watched_pitch.py'
        saved = path.read_bytes()
        folder = EVIDENCE / ('controls-' + str(time.time_ns()))
        folder.mkdir()
        mutations = [
            ('sentinel-visibility', 'return ((x & 255) | ((y & 255) << 8)) == sentinel', 'return False',
             'ProjectionTests.test_predicates_are_not_lifecycle_clamps', 'original sentinel visibility'),
            ('half-unsigned', 'return int(signed(threshold) < remaining)', 'return int(threshold < remaining)',
             'ProjectionTests.test_half_selector_and_terminal_boundaries', 'original half selector'),
            ('terminal-pose', "event.kind in ('tick', 'half_time')", "event.kind in ('tick', 'half_time', 'end')",
             'ProjectionTests.test_half_selector_and_terminal_boundaries', 'completed pitch boundary'),
            ('inverted-axes', 'return [y, x]', 'return [x, y]',
             'ProjectionTests.test_signed_draw_axes', 'original draw axes'),
            ('inverted-identity', 'team = 1 if slot <= 11 else 0', 'team = 0 if slot <= 11 else 1',
             'ProjectionTests.test_identity_uses_fixture_side_and_local_slot', 'original squad identity'),
            ('canonical-outcome', "return [copy.deepcopy(event) for event in events if event['kind'] != 'tick']",
             "result = [copy.deepcopy(event) for event in events if event['kind'] != 'tick']\n"
             "    if any(event['kind'] == 'tick' for event in events):\n"
             "        result[-1]['score'] = [9, 9]\n    return result",
             'FidelityTests.test_canonical_fidelity', 'canonical events changed'),
        ]
        receipts = []
        try:
            for name, old, new, test, message in mutations:
                self.assertEqual(saved.decode().count(old), 1, 'mutation site is unique')
                path.write_bytes(saved.replace(old.encode(), new.encode()))
                run = subprocess.run([sys.executable, '-B', '-X', 'pycache_prefix=' + str(ROOT / '.cache/tmp' / ('t81-controls-' + str(time.time_ns()))), '-m', 'unittest',
                                      'goal2.tests.test_pitch_observation.' + test, '-v'],
                                     cwd=ROOT, capture_output=True, text=True, timeout=30)
                output = run.stdout + run.stderr
                (folder / (name + '.log')).write_text(output)
                self.assertEqual(run.returncode, 1, output)
                self.assertIn('FAIL:', output)
                self.assertNotIn('ERROR:', output)
                self.assertIn(message, output)
                receipts.append(dict(name=name, test=test, assertion=message, returncode=run.returncode,
                                     source_before_sha256=hashlib.sha256(saved).hexdigest(),
                                     mutated_source_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                                     log_sha256=hashlib.sha256(output.encode()).hexdigest()))
                path.write_bytes(saved)
                self.assertEqual(path.read_bytes(), saved)
        finally:
            path.write_bytes(saved)
            (folder / 'receipt.json').write_text(json.dumps(dict(controls=receipts,
                source_restored_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                exact_saved_bytes_restored=path.read_bytes() == saved), indent=2) + '\n')
        self.assertEqual(path.read_bytes(), saved)


if __name__ == '__main__':
    unittest.main()
