"""[designed: T86] Fictional factory/model: complete data, real reads, fiction mark and refusals."""
import copy
import importlib.util
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from goal2.desktop.model import DesktopModel
from goal2.game import eligibility
from goal2.scenario import ENGINE, MARK, TEMPLATE, factory, is_scenario
from goal2.scenario.model import ScenarioModel
from goal2.scenario.runtime import RUNTIME, ScenarioPublication

ROOT = Path(__file__).resolve().parents[2]
VIEW_KEYS = {'countries', 'country', 'country_name', 'players', 'morale', 'play_label', 'fixture'}
ROW_KEYS = {'id', 'name', 'position', 'ability', 'energy', 'confidence', 'availability'}


class ScenarioFactoryTests(unittest.TestCase):
    def setUp(self):
        self.model = ScenarioModel()

    def test_factory_supplies_country_squad_pool_cards_xi_captain_tactics_and_fixtures(self):
        state = self.model.state
        self.assertEqual(state.scenario, MARK)
        self.assertEqual(len(state.managed_squad), 20)
        self.assertEqual(len(set(state.managed_squad)), 20)
        self.assertEqual(len(state.reserves), 10)
        self.assertEqual(len(state.starting_eleven), 11)
        self.assertIn(state.captain, state.starting_eleven)
        self.assertEqual(state.country_tactics, factory.TACTICS)
        self.assertEqual([f.kind for f in state.campaign.fixtures], [1, 1, 2, 200, 4])
        names = self.model.goaldat.player_names
        self.assertEqual(len(set(names[1:])), len(names) - 1)  # [designed: T86] unique fictional names
        card = self.model.card(state.captain)
        self.assertEqual(len(card['skills']), 12)
        self.assertEqual(len(card['characteristics']), 5)
        self.assertIn('fictional', card['evidence'])
        with self.assertRaisesRegex(ValueError, 'No fictional card'):
            self.model.card(40)

    def test_view_and_pool_keep_the_desktop_dto_keys_and_real_availability(self):
        view = self.model.view()
        self.assertEqual(set(view), VIEW_KEYS)
        self.assertTrue(all(set(row) == ROW_KEYS for row in view['players']))
        injured = next(row for row in view['players'] if row['id'] == factory.INJURED_AT_START)
        self.assertEqual(injured['availability'], eligibility.info(self.model.state.players[19]))
        self.assertEqual(injured['availability']['reasons'], ['Injured'])
        self.assertEqual(view['play_label'], 'Play quick friendly')
        pool = self.model.pool_view()
        self.assertEqual(set(pool), {'squad', 'reserves', 'window'})
        self.assertTrue(pool['window']['allowed'])
        self.assertEqual(len(pool['reserves']), 10)
        self.assertEqual(self.model.pool_view(query='zzz')['reserves'], [])

    def test_confirm_validates_like_desktop_model_and_is_atomic(self):
        before = copy.deepcopy(self.model.state)
        held = self.model.state
        eleven = list(before.starting_eleven)
        for args, message in (((eleven[:10], eleven[0], 0), 'Choose eleven distinct'),
                              ((eleven, 2, 0), 'Captain'), ((eleven, eleven[0], 256), 'eight-bit'),
                              (([19] + eleven[1:], eleven[1], 0), 'unavailable starters')):
            with self.subTest(message=message), self.assertRaisesRegex(ValueError, message):
                self.model.confirm(*args)
            self.assertIs(self.model.state, held)
            self.assertEqual(self.model.state, before)
        self.model.confirm(eleven, eleven[0], 7)
        self.assertEqual((self.model.state.captain, self.model.state.country_tactics), (eleven[0], 7))
        self.assertEqual(before.country_tactics, factory.TACTICS)

    def test_exchange_repairs_eleven_and_captain_only_in_a_friendly_window(self):
        self.model.exchange(9, 101)
        self.assertIn(101, self.model.state.managed_squad)
        self.assertIn(9, self.model.state.reserves)
        self.assertEqual(self.model.state.captain, 101)
        with self.assertRaisesRegex(ValueError, 'one squad player'):
            self.model.exchange(9, 102)

    def test_reads_never_advance_or_mutate_the_session(self):
        before = copy.deepcopy(self.model.state)
        for _ in range(5):
            self.model.view();self.model.pool_view();self.model.result_text()
            self.model.card(self.model.state.captain);self.model.competition_table()
        self.assertEqual(self.model.state, before)

    def test_fiction_is_marked_and_refused_by_career_paths(self):
        self.assertTrue(is_scenario(self.model))
        with self.assertRaisesRegex(ValueError, 'fictional scenario, not a career'):
            self.model.save('career.g2save')
        with self.assertRaisesRegex(ValueError, 'Resume refused'):
            self.model.resume('career.g2save')
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'scenario.json'
            path.write_bytes(RUNTIME.encode(self.model.state, TEMPLATE))
            real = DesktopModel(factory.Names(), TEMPLATE, Path(folder) / 'career.g2save')
            with self.assertRaisesRegex(ValueError, 'Cannot resume game'):
                real.resume(path)
            real.state = self.model.state
            with self.assertRaisesRegex(ValueError, 'Cannot save game'):
                real.save(Path(folder) / 'career.g2save')
            self.assertFalse((Path(folder) / 'career.g2save').exists())
            path.write_bytes(b'{"format": "goal2-session"}')
            with self.assertRaisesRegex(ValueError, 'not a fictional scenario file'):
                RUNTIME.load(path)
        unmarked = copy.deepcopy(self.model.state);unmarked.scenario = 'career'
        with self.assertRaisesRegex(ValueError, 'not a fictional scenario state'):
            RUNTIME.encode(unmarked, TEMPLATE)
        owner = ScenarioModel();owner.state = unmarked
        with self.assertRaisesRegex(ValueError, 'Fictional publication refused'):
            ScenarioPublication(owner)
        foreign = ScenarioModel();foreign.template_bytes = b'career template'
        with self.assertRaisesRegex(ValueError, 'foreign template'):
            ScenarioPublication(foreign)
        with self.assertRaisesRegex(ValueError, 'Fictional quick match refused'):
            RUNTIME.check(unmarked, TEMPLATE)
        self.assertEqual(ENGINE, 'goal2-scenario:fictional:1')

    def test_desktop_entry_has_no_demo_fallback(self):
        source = '\n'.join(p.read_text() for p in (ROOT / 'goal2/desktop').glob('*.py'))
        self.assertNotIn('goal2.scenario', source)
        for argv, expected in ((['--data', '/nonexistent'], 'choose exactly one of --template or --resume'),
                               (['--template', '/nonexistent', '--data', '/nonexistent'],
                                'Cannot open game' if importlib.util.find_spec('PySide6') else 'Desktop needs PySide6')):
            with self.subTest(argv=argv):
                run = subprocess.run([sys.executable, '-m', 'goal2.desktop'] + argv, cwd=ROOT,
                                     capture_output=True, text=True, timeout=60)
                self.assertEqual(run.returncode, 2)
                self.assertIn(expected, run.stderr)
                self.assertNotIn('ictional', run.stdout + run.stderr)
                self.assertNotIn('scenario', run.stdout + run.stderr)


if __name__ == '__main__':
    unittest.main()
