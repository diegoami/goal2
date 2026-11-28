"""[designed: T170bi] Original manager-menu roster actions versus the real PyPy port."""

from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from goal2.core import Core
from goal2.core.driver import Driver
from goal2.core.screens import INSERT, RETURN
from goal2.desktop.native_save_owner import NativeSaveOwner
from goal2.engine.original_match import Image
from goal2.game import engine_tables
from goal2.game.season_publication import SeasonCampaign
from goal2.tests import requires
from goal2.tests.pypy_engine import call
from goal2.tests.test_best_twenty_finals_t183d import FIXTURE, REPORT
from goal2.tests.test_best_twenty_t183a import records
from goal2.tests.test_core_team_t107 import start
from goal2.tests.test_prematch_preview_t170s import reference_raw
from goal2.ui import saves


def native(state, first, second, omit_swap=False):
    from copy import deepcopy
    import io
    import sys
    from goal2.engine.original_match import port
    from goal2.engine.original_match.machine import Uc
    from goal2.game.native_roster_move import move_player

    assert sys.implementation.name == 'pypy' and Uc is None
    before = deepcopy(state)
    original_open = io.open

    def no_exe(file, *args, **kwargs):
        if str(file).lower().endswith('.exe'):
            raise AssertionError('the native roster operation must not read GOAL.EXE')
        return original_open(file, *args, **kwargs)

    load = port.load

    def ports(specs):
        if omit_swap and specs == ['all']:
            return load(['all', 'selection.squad-word-swap-omitted'])
        return load(specs)

    with patch('builtins.open', no_exe), patch('io.open', no_exe), patch.object(port, 'load', ports):
        result = move_player(state, first, second)
    assert state == before
    return result


class Guards(unittest.TestCase):
    def test_invalid_words_and_held_state_never_construct_the_port(self):
        from goal2.game.native_roster_move import move_player

        image = Image.from_bytes(reference_raw())
        tables = engine_tables.load()
        original = records(image)
        first, second = original['squad'][:2]
        foreign = next(word for word in range(1, 3061) if word not in original['squad'] + original['pool'])
        state = image.state(tables)
        with patch('goal2.game.native_roster_move.PortMachine', side_effect=AssertionError('port entered')):
            for pair in ((first, first), (True, second), (first, 0), (first, 3061)):
                with self.subTest(pair=pair), self.assertRaisesRegex(ValueError, 'distinct native player words'):
                    move_player(state, *pair)
            for pair in ((first, foreign), tuple(original['pool'][:2])):
                with self.subTest(pair=pair), self.assertRaisesRegex(ValueError, 'one squad and one pool'):
                    move_player(state, *pair)
            for offset in (0xC1E, 0xC1F):
                held = Image.from_bytes(reference_raw())
                held.memory[held.DS * 16 + offset] = 1
                with self.subTest(offset=offset), self.assertRaisesRegex(ValueError, 'manager boundary'):
                    move_player(held.state(tables), first, second)

    def test_original_same_position_swap_must_happen_before_sorting(self):
        image = Image.from_bytes(reference_raw())
        state = image.state(engine_tables.load())
        players = records(image)
        squad, rows = players['squad'], players['players']
        first, second = next((a, b) for i, a in enumerate(squad[:11]) for b in squad[i + 1:11]
                             if rows[a * 20 + 6] == rows[b * 20 + 6])
        answer = call(__name__ + ':native', state, first, second)
        self.assertIsNone(answer['refusal'])
        with self.assertRaisesRegex(RuntimeError, 'word swap differs'):
            call(__name__ + ':native', state, first, second, omit_swap=True)


@requires.need(modules=('unicorn',), files=('e006-r0001-main.sav', 'GOAL.DAT'))
class Original(unittest.TestCase):
    def compare(self, driver, first, second, refusal=None):
        tables = engine_tables.load()
        source = Image.from_memory_component(driver.wait.state.memory_component())
        state = source.state(tables)
        answer = call(__name__ + ':native', state, first, second)
        driver._open_squad()
        for word in (first, second):
            selected = driver._to_player(word)
            wait = driver.press(RETURN, expect=(selected.kind, 'squad-change-refused'))
            if wait.kind == 'squad-change-refused':
                self.assertEqual(wait.view['why'], refusal)
                driver.press(RETURN, expect=(selected.kind,))
                break
        else:
            self.assertIsNone(refusal)
        driver.to_menu()
        self.assertEqual(answer['refusal'], refusal)
        if refusal is not None:
            self.assertIsNone(answer['state'])
            original = records(source)
            refused_records = records(Image.from_memory_component(driver.wait.state.memory_component()))
            self.assertEqual(refused_records['players'], original['players'])
            self.assertEqual(set(refused_records['squad']), set(original['squad']))
            self.assertEqual(set(refused_records['pool']), set(original['pool']))
            return state, answer
        candidate = Image.from_state(answer['state'], tables)
        self.assertEqual(candidate.rd(0xC1B), source.rd(0xC1B))
        actual = records(candidate)
        expected = records(Image.from_memory_component(driver.wait.state.memory_component()))
        # [confirmed: E44F E7D9, DDCB] The original moves the pool cursor; the host owns it in this operation.
        original_game = records(source)['game']
        game = bytearray(expected['game'])
        manager = original_game[1]
        for offset in (0x52 + 2 * manager, 0x5E + 2 * manager):
            self.assertEqual(actual['game'][offset:offset + 2], original_game[offset:offset + 2])
            game[offset:offset + 2] = original_game[offset:offset + 2]
        expected['game'] = bytes(game)
        for record in expected:
            self.assertEqual(actual[record], expected[record], record)
        return state, answer

    def test_squad_moves_and_both_pool_orders_match_original_and_save(self):
        for first_index, second_index in ((1, 2), (2, 3), (18, 19), (1, 11), (13, -1), (-1, 13)):
            with self.subTest(pair=(first_index, second_index)):
                driver = start()
                squad, pool = driver._team(), driver._pool()
                first = squad[first_index] if first_index >= 0 else pool[-3]
                second = squad[second_index] if second_index >= 0 else pool[4]
                state, answer = self.compare(driver, first, second)
                self.assertEqual(answer['players'], [first, second])
                if second_index == -1:
                    campaign = SeasonCampaign(state)
                    row = campaign.publish_management(
                        answer['state'], action='squad-move', revision=0,
                        input_hash=answer['input_hash'], output_hash=answer['output_hash'])
                    with TemporaryDirectory() as directory:
                        file = saves.write(NativeSaveOwner(campaign), directory, 'Roster move')
                        loaded = saves.load(file, Path(directory) / 'unused', native=True)
                        self.assertEqual(loaded.campaign.committed_snapshot(), (answer['state'], (row,)))

    @requires.need(files=(FIXTURE,))
    def test_genuine_finals_refuses_either_exchange_order(self):
        import hashlib
        import json

        raw = (requires.CACHE / FIXTURE).read_bytes()
        self.assertEqual(hashlib.sha256(raw).hexdigest(), json.loads(REPORT.read_text())['fixture']['sha256'])
        for pool_first in (False, True):
            driver = Driver(Core.load(raw, goal_dat=requires.CACHE / 'GOAL.DAT'))
            pair = driver._team()[12], driver._pool()[4]
            self.compare(driver, *(pair[::-1] if pool_first else pair), refusal='finals')

    @requires.need(slow=True, files=('g16-proof-279904b6-private.zip',))
    def test_genuine_tour_refuses_the_pool_pick(self):
        import hashlib
        from zipfile import ZipFile
        from goal2.tests.eleven_repair import fix_eleven

        bundle = requires.CACHE / 'g16-proof-279904b6-private.zip'
        self.assertEqual(hashlib.sha256(bundle.read_bytes()).hexdigest(),
                         '2332459f7bf64be1afd2e92fc61d81f3b9489bf9d01208a3e6ad8edb469d4cd9')
        with ZipFile(bundle) as archive:
            raw = archive.read('.cache/T123-proof-r2/annual-3.g2core')
        driver = Driver(Core.load(raw, goal_dat=requires.CACHE / 'GOAL.DAT'))
        # [confirmed: T183a] Enter the tour from the original recommended squad.
        driver._open_squad()
        driver.press(INSERT, expect=('select-squad',))
        driver.to_menu()
        driver.play_round(fix_eleven=fix_eleven, on_taker=lambda *_: 13, on_replay=lambda *_: False)
        self.compare(driver, driver._pool()[4], driver._team()[12], refusal='tour')
