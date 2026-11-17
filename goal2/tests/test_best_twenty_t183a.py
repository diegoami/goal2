"""[designed: T183a/#594] Native preparation + assistant versus real original keys.

[confirmed: F031, T125 0f9f87f4; selection 7fbfd2e9] The reference enters
SELECT TEAM before Ins; a direct DC7E call alone cannot establish this claim.
No guest records are fabricated for the original-action cases.
"""
import copy
import unittest
from pathlib import Path
from unittest.mock import patch

from goal2.tests import requires
from goal2.tests.pypy_engine import call
from goal2.game.best_twenty import recommend


def native(value):
    """Actual PyPy arm, with positive original-backend and EXE-read denial."""
    import builtins
    import io
    import sys
    assert sys.implementation.name == 'pypy'
    original_import, original_open = builtins.__import__, io.open

    def denied(name, *args, **kwargs):
        if name == 'unicorn' or name.startswith('unicorn.'):
            raise ImportError('T183a positive Unicorn denial')
        return original_import(name, *args, **kwargs)

    def no_exe(file, *args, **kwargs):
        if isinstance(file, (str, bytes, Path)) and str(file).lower().endswith('.exe'):
            raise AssertionError('T183a EXE read denied')
        return original_open(file, *args, **kwargs)

    with patch('builtins.__import__', denied), patch('io.open', no_exe), patch('builtins.open', no_exe):
        try:
            __import__('unicorn')
        except ImportError:
            pass
        else:
            raise AssertionError('Unicorn denial inactive')
        try:
            Path('GOAL.EXE').read_bytes()
        except AssertionError:
            pass
        else:
            raise AssertionError('EXE denial inactive')
        from goal2.engine.original_match.machine import Uc
        assert Uc is None
        before = copy.deepcopy(value)
        answer = recommend(value)
        assert value == before, 'native input mutated'
        return answer


def records(image):
    """The complete original records promised by T183, not an overall rating."""
    game, pool = image.far(0xA923), image.far(0xA927)
    manager = image.memory[game + 1]
    base = image.rd(0x6D18 + 2 * manager)
    country = image.memory[image.far(0xA91F) + 3 * (manager + 128)]
    squad = image.far(0xA917) + country * 191
    return dict(players=bytes(image.memory[image.far(0xA91B):image.far(0xA91B) + 3061 * 20]),
                countries=bytes(image.memory[image.far(0xA917):image.far(0xA917) + 129 * 191]),
                managers=bytes(image.memory[image.far(0xA91F):image.far(0xA91F) + 135 * 3]),
                game=bytes(image.memory[game:game + 0x100]),
                squad=[int.from_bytes(image.memory[squad + 2*i:squad + 2*i + 2], 'little') for i in range(20)],
                pool=[int.from_bytes(image.memory[pool + 2*(base+i):pool + 2*(base+i) + 2], 'little') for i in range(80)],
                seeds=(image.rd(0x7B62), image.rd(0x8336)))


@requires.need(modules=('unicorn',), files=('e006-r0001-main.sav', 'GOAL.DAT'))
class OriginalAction(unittest.TestCase):
    def source(self):
        from goal2.tests.test_core_team_t107 import start
        return start()

    def compare(self, driver):
        from goal2.core.screens import INSERT, RETURN
        from goal2.engine.original_match import Image
        from goal2.game import engine_tables
        tables = engine_tables.load()
        image = Image.from_memory_component(driver.wait.state.memory_component())
        value = image.state(tables)
        before = copy.deepcopy(value)
        answer = call('goal2.tests.test_best_twenty_t183a:native', value)
        self.assertEqual(value, before)
        driver.goto('select-squad')
        wait = driver.press(INSERT, expect=('select-squad', 'squad-change-refused'))
        refused = wait.kind == 'squad-change-refused'
        if refused:
            driver.press(RETURN, expect=('select-squad',))
        expected = records(Image.from_memory_component(driver.wait.state.memory_component()))
        actual = records(Image.from_state(answer['state'], tables))
        for key in expected:
            self.assertEqual(actual[key], expected[key], key)
        self.assertEqual(answer['allowed'], not refused)
        self.assertEqual(answer['squad'], expected['squad'])
        self.assertEqual(answer['pool'], expected['pool'])
        self.assertEqual(answer['calls'].get('1771:52CC', 0), 1)
        self.assertEqual(answer['calls'].get('0791:DC7E', 0), 1)
        self.assertEqual(len(set(answer['squad'] + answer['pool'])), 100)
        driver.to_menu()
        return answer

    def test_real_select_team_ins_includes_preparation(self):
        self.compare(self.source())

    @requires.need(slow=True)
    def test_repeated_selection_and_original_position_edit_and_exchange(self):
        from goal2.core import views
        d = self.source()
        self.compare(d)
        repeated = self.compare(d)
        # Original SELECT TEAM sorts within XI/bench on each entry; ordered
        # equality above remains mandatory even when membership needs no recruits.
        self.assertEqual(repeated['recruited'], [])
        squad = [p['player'] for p in views.team(d.wait.state)['squad']]
        word = squad[4]
        position = views.player_card(d.wait.state, word)['position']
        d.set_position(word, (position + 1) % 14)
        d.to_menu()
        self.compare(d)
        squad = [p['player'] for p in views.team(d.wait.state)['squad']]
        pool = [p['player'] for p in views.pool(d.wait.state)['rows']]
        self.assertIsNone(d.exchange(squad[-1], pool[0])['refused'])
        self.compare(d)

    @requires.need(slow=True, files=('e039-r0005-date-call.sav',))
    def test_original_new_careers_for_contrasting_countries(self):
        from goal2.core import Core
        from goal2.core.driver import Driver
        for country in (1, 4):
            with self.subTest(country=country):
                wait = Core.boot((requires.CACHE/'e039-r0005-date-call.sav').read_bytes(),
                                 (1991, 10, 4), goal_dat=requires.CACHE/'GOAL.DAT', title_key='n')
                d = Driver(wait.core)
                d.new_game(country, 'T Test')
                self.compare(d)

    def test_in_match_context_rejected_before_backend_and_input_unchanged(self):
        from goal2.engine.original_match import Image
        from goal2.game import engine_tables
        image = Image.from_memory_component(self.source().wait.state.memory_component())
        # Input validation control only: no original-action oracle claim for this edited flag.
        for field in (0xC1E, 0xC1F):
            with self.subTest(field=field):
                altered = copy.deepcopy(image)
                altered.memory[altered.DS*16 + field] = 1
                value = altered.state(engine_tables.load())
                before = copy.deepcopy(value)
                with patch('goal2.engine.original_match.port.engine.PortMachine', side_effect=AssertionError('backend entered')):
                    with self.assertRaisesRegex(ValueError, 'outside a match'):
                        recommend(value)
                self.assertEqual(value, before)

    @requires.need(slow=True, files=('g16-proof-279904b6-private.zip',))
    def test_retained_original_later_career_context(self):
        import hashlib
        from zipfile import ZipFile
        from goal2.core import Core
        from goal2.core.driver import Driver
        bundle = requires.CACHE/'g16-proof-279904b6-private.zip'
        self.assertEqual(hashlib.sha256(bundle.read_bytes()).hexdigest(),
                         '2332459f7bf64be1afd2e92fc61d81f3b9489bf9d01208a3e6ad8edb469d4cd9')
        with ZipFile(bundle) as z:
            raw = z.read('.cache/T123-proof-r2/annual-1.g2core')
        self.assertEqual(hashlib.sha256(raw).hexdigest(),
                         'f3edb478fb566c7a4437cba570b8719ab0510ec022f285fa056bdb7591173d48')
        d = Driver(Core.load(raw, goal_dat=requires.CACHE/'GOAL.DAT'))
        self.compare(d)
