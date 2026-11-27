"""[designed: T170bf] Original standalone R/C parity, then native publication."""

from copy import deepcopy
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from goal2.desktop.native_save_owner import NativeSaveOwner
from goal2.engine.original_match.image import GAME_PTR, Image
from goal2.engine.original_match.machine import Uc
from goal2.game import engine_tables
from goal2.game.native_position import edit_position
from goal2.game.season_publication import SeasonCampaign
from goal2.tests import pypy_engine, requires
from goal2.tests.test_best_twenty_t183a import records
from goal2.tests.test_core_team_t107 import start
from goal2.tests.test_prematch_preview_t170s import reference_raw
from goal2.ui import saves


def produce(state, word, key):
    import builtins
    import io
    import os
    import sys

    assert sys.implementation.name == 'pypy' and Uc is None
    native_open = io.open

    def no_exe(file, *args, **kwargs):
        if isinstance(file, (str, bytes, Path)) and os.fsdecode(file).lower().endswith('.exe'):
            raise AssertionError('the native position producer must not read GOAL.EXE')
        return native_open(file, *args, **kwargs)

    before = deepcopy(state)
    with patch('builtins.open', no_exe), patch('io.open', no_exe):
        result = edit_position(state, word, key)
    assert state == before
    return result


class Guards(unittest.TestCase):
    def test_refused_requests_do_not_construct_a_port_machine(self):
        image = Image.from_bytes(reference_raw())
        tables = engine_tables.load()
        value = image.state(tables)
        country, = image.managed_countries()
        word = image.squad(country)[0]
        from goal2.core.views import pool

        domain = set(image.squad(country)) | {row['player'] for row in pool(image)['rows']}
        foreign = next(w for w in range(1, 3061) if w not in domain)
        with patch('goal2.game.native_position.PortMachine', side_effect=AssertionError('port entered')):
            for bad in (None, True, 67, 'c', 'Shift+R'):
                with self.subTest(key=bad), self.assertRaisesRegex(ValueError, 'original R or C'):
                    edit_position(value, word, bad)
            for bad in (0, True, 3061):
                with self.subTest(player=bad), self.assertRaisesRegex(ValueError, 'valid player word'):
                    edit_position(value, bad, 'R')
            with self.assertRaisesRegex(ValueError, 'current native squad or pool'):
                edit_position(value, foreign, 'C')
            for offset in (0xC1E, 0xC1F):
                held = Image.from_bytes(reference_raw())
                held.memory[held.DS * 16 + offset] = 1
                with self.subTest(offset=offset), self.assertRaisesRegex(ValueError, 'manager boundary'):
                    edit_position(held.state(tables), word, 'R')
            dismissed = Image.from_bytes(reference_raw())
            game = dismissed.far(GAME_PTR)
            dismissed.memory[game + 0x47 + dismissed.memory[game + 1]] = 1
            with self.assertRaisesRegex(ValueError, 'active native manager'):
                edit_position(dismissed.state(tables), word, 'C')


@requires.need(modules=('unicorn',), files=('e006-r0001-main.sav', 'GOAL.DAT'))
class Original(unittest.TestCase):
    def test_original_squad_and_pool_r_and_c_match_and_survive_named_reload(self):
        tables = engine_tables.load()
        for pane in ('squad', 'pool'):
            driver = start()
            word = (driver._team() if pane == 'squad' else driver._pool())[1]
            if pane == 'squad':
                driver.set_position(word, 13)
            for key in ('R', 'C'):
                with self.subTest(pane=pane, key=key):
                    source = Image.from_memory_component(driver.wait.state.memory_component())
                    state = source.state(tables)
                    before = records(source)
                    result = pypy_engine.call(__name__ + ':produce', state, word, key)
                    candidate = Image.from_state(result['state'], tables)
                    actual = records(candidate)

                    driver._open_squad()
                    selected = driver._to_player(word)
                    driver.press(key.lower(), expect=(selected.kind,))
                    driver.to_menu()
                    original = Image.from_memory_component(driver.wait.state.memory_component())
                    expected = records(original)
                    at = 20 * word
                    old_position, club_position = before['players'][at + 6:at + 8]
                    position = (old_position + 1) % 14 if key == 'R' else club_position
                    if pane == 'squad' and key == 'R':
                        self.assertEqual(position, 0)
                    self.assertEqual((result['player'], result['position'], result['club_position']),
                                     (word, position, club_position))
                    # [confirmed: E44F E7D9, DDCB] The original has moved its pool scroll and cursor
                    # to show the selected player. The atomic producer keeps the incoming UI words.
                    game = source.far(GAME_PTR)
                    manager = source.memory[game + 1]
                    cursors = (0x52 + 2 * manager, 0x5E + 2 * manager)
                    expected_game = bytearray(expected['game'])
                    for offset in cursors:
                        self.assertEqual(actual['game'][offset:offset + 2], before['game'][offset:offset + 2])
                        expected_game[offset:offset + 2] = before['game'][offset:offset + 2]
                    expected['game'] = bytes(expected_game)
                    for field in expected:
                        self.assertEqual(actual[field], expected[field], field)

                    campaign = SeasonCampaign(state)
                    row = campaign.publish_management(
                        result['state'], action='player-position', revision=0,
                        input_hash=result['input_hash'], output_hash=result['output_hash'])
                    self.assertEqual(row.action, 'player-position')
                    self.assertEqual(campaign.published, ())
                    self.assertEqual(campaign.canonical_hash, result['output_hash'])
                    with TemporaryDirectory() as directory:
                        path = saves.write(NativeSaveOwner(campaign), directory, 'Edited position')
                        owner = saves.load(path, Path(directory) / 'unused', native=True)
                        self.assertEqual(owner.campaign.committed_snapshot(), (result['state'], (row,)))
