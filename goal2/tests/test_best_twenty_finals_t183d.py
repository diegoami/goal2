"""[confirmed: E031 G4B.GL, F031; archaeology#725] Genuine finals refusal.

The private fixture was acquired by loading the unchanged E031 save in original
DOSBox-X, using ordinary keys. Its native trace and source/fixture hashes are in
measurements/725-retained-finals/native-v1.json. No finals byte is patched.
"""
import copy
import hashlib
import json
import unittest

from goal2.tests import requires

FIXTURE = 'T183-finals-G4B-manager-v1.g2core'
REPORT = requires.ROOT/'measurements/725-retained-finals/native-v1.json'


@requires.need(modules=('unicorn',), files=(FIXTURE, 'GOAL.DAT'))
class NativeFinals(unittest.TestCase):
    def test_genuine_finals_refusal_equals_original_keys_and_preserves_records(self):
        from goal2.core import Core
        from goal2.core.driver import Driver
        from goal2.core.screens import INSERT, RETURN
        from goal2.engine.original_match import Image
        from goal2.game import engine_tables
        from goal2.tests.pypy_engine import call
        from goal2.tests.test_best_twenty_t183a import records

        report = json.loads(REPORT.read_text())
        raw = (requires.CACHE/FIXTURE).read_bytes()
        self.assertEqual(hashlib.sha256(raw).hexdigest(), report['fixture']['sha256'])
        self.assertEqual(report['save_sha256'],
                         'cfcea0ae6b01c2828e1c157ffd7036c2865dca301d9698586ea8015548e4f293')
        self.assertEqual([r['key'] for r in report['trace']],
                         [None, 'y', 'Return', 'Down', 'Down', 'Down', 'Down',
                          'Return', 'Insert', 'Return', 'Escape'])
        d = Driver(Core.load(raw, goal_dat=requires.CACHE/'GOAL.DAT'))
        self.assertEqual(d.wait.kind, 'manager-menu')
        tables = engine_tables.load()
        image = Image.from_memory_component(d.wait.state.memory_component())
        game = image.far(0xA923)
        manager = image.memory[game+1]
        self.assertEqual((manager, image.memory[game+0x13+manager]), (1, 1))
        value = image.state(tables)
        unchanged = copy.deepcopy(value)
        # The real PyPy helper positively denies Unicorn and GOAL.EXE reads.
        answer = call('goal2.tests.test_best_twenty_t183a:native', value)
        self.assertEqual(value, unchanged)
        d.goto('select-squad')
        selected = records(Image.from_memory_component(d.wait.state.memory_component()))
        refused = d.press(INSERT, expect=('squad-change-refused',))
        self.assertEqual(refused.view, dict(message='cannot alter squad during finals', why='finals'))
        d.press(RETURN, expect=('select-squad',))
        expected = records(Image.from_memory_component(d.wait.state.memory_component()))
        actual = records(Image.from_state(answer['state'], tables))
        self.assertEqual(expected, selected, 'Original refusal and acknowledgement must preserve records')
        for key in expected:
            with self.subTest(record=key):
                self.assertEqual(actual[key], expected[key])
                blob = expected[key] if isinstance(expected[key], bytes) else json.dumps(
                    expected[key], separators=(',', ':')).encode()
                self.assertEqual(hashlib.sha256(blob).hexdigest(), report['equality'][key])
        self.assertIs(answer['allowed'], False)
        self.assertEqual(answer['refusal'], 'finals')
        self.assertEqual(answer['recruited'], [])
        self.assertEqual(answer['squad'], selected['squad'])
        self.assertEqual(answer['pool'], selected['pool'])
        self.assertEqual(len(set(answer['squad']+answer['pool'])), 100)
        self.assertEqual(answer['calls']['1771:52CC'], 1)
        self.assertEqual(answer['calls']['0791:DC7E'], 1)
        d.to_menu()
        self.assertEqual(d.wait.kind, 'manager-menu')
