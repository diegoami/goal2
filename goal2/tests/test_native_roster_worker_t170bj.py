"""[designed: T170bj] Actual PyPy roster transport and controlled protocol failures."""

import json
import queue
import sys
import unittest

from goal2.core import Core
from goal2.core.driver import Driver
from goal2.core.screens import INSERT
from goal2.engine.original_match import Image
from goal2.game import engine_tables
from goal2.game.engine_process import EngineProcess
from goal2.game.engine_server import read_packet, write_packet
from goal2.game.season import canonical_hash
from goal2.game.season_publication import SeasonCampaign
from goal2.tests import requires
from goal2.tests.pypy_engine import call
from goal2.tests.test_best_twenty_finals_t183d import FIXTURE, REPORT
from goal2.tests.test_best_twenty_t183a import records
from goal2.tests.test_prematch_preview_t170s import reference_raw


def controlled_worker():
    incoming, outgoing = sys.stdin.buffer, sys.stdout.buffer
    mode = sys.argv[-1]
    header, raw = read_packet(incoming)
    if mode == 'dead':
        return
    write_packet(outgoing, {'kind': 'ready', 'value': {}})
    if mode == 'timeout':
        read_packet(incoming)
        return

    state = json.loads(raw)
    binding = {key: header[key] for key in ('request', 'revision', 'input_hash', 'players')}
    value = dict(binding, output_hash=canonical_hash(state), refusal=None)
    if mode == 'wrong_operation':
        write_packet(outgoing, {'kind': 'position_error', 'value': {'request': binding['request'],
                                                                  'error': 'wrong operation'}})
        return
    if mode == 'request':
        value['request'] += 1
    elif mode == 'revision':
        value['revision'] += 1
    elif mode == 'order':
        value['players'] = list(reversed(value['players']))
    elif mode == 'numeric_word':
        value['players'][0] = float(value['players'][0])
    elif mode == 'input_hash':
        value['input_hash'] = 'wrong'
    elif mode == 'hash':
        value['output_hash'] = 'wrong'
    elif mode == 'payload':
        raw = b'{'
    elif mode == 'unknown_refusal':
        value.update(refusal='unknown', output_hash=None)
        raw = b''
    elif mode == 'refusal_with_state':
        value.update(refusal='tour')
    elif mode == 'wrong_context':
        value.update(refusal='finals', output_hash=None)
        raw = b''
    write_packet(outgoing, {'kind': 'roster_move', 'value': value}, raw)
    read_packet(incoming)


class Worker(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        image = Image.from_bytes(reference_raw())
        source = records(image)
        cls.squad = tuple(source['squad'])
        cls.pool = tuple(source['pool'])
        cls.state = image.state(engine_tables.load())

    def engine(self, command=None, **options):
        replies = queue.Queue()
        worker = EngineProcess(lambda kind, value: replies.put((kind, value)), command=command, **options)
        self.addCleanup(worker.close)
        return worker, replies

    def reply(self, replies, kind):
        actual, value = replies.get(timeout=30)
        if actual == 'ready' and kind != 'ready':
            actual, value = replies.get(timeout=30)
        self.assertEqual(actual, kind, value)
        return value

    def test_real_worker_matches_direct_and_publishes_verified_move_once(self):
        worker, replies = self.engine()
        campaign = SeasonCampaign(self.state)
        pairs = ((self.squad[2], self.squad[3]), (self.squad[0], self.squad[12]),
                 (self.squad[13], self.pool[5]), (self.pool[-3], self.squad[12]))
        for index, pair in enumerate(pairs):
            with self.subTest(pair=pair):
                before, revision = campaign.state, campaign.revision
                expected = call('goal2.tests.test_native_roster_move_t170bi:native', before, *pair)
                request = worker.move_roster(before, revision=revision, first=pair[0], second=pair[1])
                packet = self.reply(replies, 'roster_move')
                self.assertEqual(packet, dict(expected, request=request, revision=revision))
                self.assertEqual(worker.ready['implementation'], 'PyPy')
                self.assertEqual(worker.generation, 1)
                self.assertEqual(campaign.state, before)
                if index == len(pairs) - 1:
                    fields = {k: packet[k] for k in ('revision', 'input_hash', 'output_hash')}
                    row = campaign.publish_management(packet['state'], action='squad-move', **fields)
                    self.assertEqual(row.action, 'squad-move')
                    self.assertEqual(campaign.state, packet['state'])
                    with self.assertRaisesRegex(ValueError, 'stale'):
                        campaign.publish_management(packet['state'], action='squad-move', **fields)

    def test_real_cancel_fences_candidate_and_excludes_position(self):
        worker, replies = self.engine()
        first, second = self.squad[0], self.pool[0]
        with worker._lock:
            request = worker.move_roster(self.state, revision=0, first=first, second=second)
            self.assertFalse(worker.cancel_position(request))
            self.assertFalse(worker.cancel_roster_move(request + 1))
            self.assertTrue(worker.cancel_roster_move(request))
            with self.assertRaisesRegex(ValueError, 'pending'):
                worker.edit_position(self.state, revision=0, player=first, key='R')
        self.assertEqual(self.reply(replies, 'roster_move_cancelled'), {'request': request})
        position = worker.edit_position(self.state, revision=0, player=first, key='R')
        self.assertGreater(position, request)
        self.assertEqual(self.reply(replies, 'position')['request'], position)
        self.assertEqual(worker.generation, 1)

    def test_held_season_excludes_roster_moves_until_discard(self):
        worker, replies = self.engine()
        worker.season_open(self.state)
        self.reply(replies, 'season')
        with self.assertRaisesRegex(ValueError, 'held season'):
            worker.move_roster(self.state, revision=0, first=self.squad[0], second=self.squad[12])
        worker.season_request('discard')
        self.reply(replies, 'season')
        worker.move_roster(self.state, revision=0, first=self.squad[0], second=self.squad[12])
        self.reply(replies, 'roster_move')

    def test_malformed_packets_end_the_child_and_restart_requires_a_new_request(self):
        modes = ('request', 'revision', 'order', 'numeric_word', 'input_hash', 'hash', 'payload', 'membership',
                 'unknown_refusal', 'refusal_with_state', 'wrong_context', 'wrong_operation', 'dead')
        first, second = self.squad[0], self.squad[12]
        for mode in modes:
            with self.subTest(mode=mode):
                worker, replies = self.engine([sys.executable, '-m', __name__, mode])
                if mode in ('unknown_refusal', 'refusal_with_state'):
                    second = self.pool[0]
                else:
                    second = self.squad[12]
                request = worker.move_roster(self.state, revision=0, first=first, second=second)
                death = self.reply(replies, 'death')
                if mode != 'dead':
                    self.assertIn('roster_move', death['error'])
                self.assertFalse(worker.busy)
                self.assertIsNone(worker.pid)
                self.assertFalse(worker.cancel_roster_move(request))
        worker.command = None
        retry = worker.move_roster(self.state, revision=0, first=first, second=second)
        self.assertGreater(retry, request)
        self.assertEqual(self.reply(replies, 'roster_move')['request'], retry)
        self.assertEqual(worker.generation, 2)

    def test_unresponsive_cancel_holds_slot_until_death(self):
        worker, replies = self.engine([sys.executable, '-m', __name__, 'timeout'], cancel_deadline=1)
        request = worker.move_roster(self.state, revision=0, first=self.squad[0], second=self.pool[0])
        self.reply(replies, 'ready')
        self.assertTrue(worker.cancel_roster_move(request))
        self.assertTrue(worker.busy)
        self.reply(replies, 'death')
        self.assertFalse(worker.busy)
        self.assertIsNone(worker.pid)

    def check_refusal(self, driver, reason):
        image = Image.from_memory_component(driver.wait.state.memory_component())
        state = image.state(engine_tables.load())
        campaign = SeasonCampaign(state)
        source = records(image)
        worker, replies = self.engine()
        pair = source['squad'][12], source['pool'][4]
        for first, second in (pair, pair[::-1]):
            request = worker.move_roster(state, revision=0, first=first, second=second)
            expected = call('goal2.tests.test_native_roster_move_t170bi:native', state, first, second)
            self.assertEqual(expected['refusal'], reason)
            self.assertIsNone(expected['state'])
            self.assertIsNone(expected['output_hash'])
            self.assertEqual(self.reply(replies, 'roster_move'), dict(expected, request=request, revision=0))
        self.assertEqual(campaign.committed_snapshot(), (state, ()))
        self.assertEqual(worker.generation, 1)

    @requires.need(modules=('unicorn',), files=(FIXTURE, 'GOAL.DAT'))
    def test_real_finals_refusal_is_bound_and_carries_no_state(self):
        import hashlib
        raw = (requires.CACHE / FIXTURE).read_bytes()
        self.assertEqual(hashlib.sha256(raw).hexdigest(), json.loads(REPORT.read_text())['fixture']['sha256'])
        self.check_refusal(Driver(Core.load(raw, goal_dat=requires.CACHE / 'GOAL.DAT')), 'finals')

    @requires.need(modules=('unicorn',), slow=True, files=('g16-proof-279904b6-private.zip', 'GOAL.DAT'))
    def test_real_tour_refusal_is_bound_and_carries_no_state(self):
        import hashlib
        from zipfile import ZipFile

        from goal2.tests.eleven_repair import fix_eleven

        bundle = requires.CACHE / 'g16-proof-279904b6-private.zip'
        self.assertEqual(hashlib.sha256(bundle.read_bytes()).hexdigest(),
                         '2332459f7bf64be1afd2e92fc61d81f3b9489bf9d01208a3e6ad8edb469d4cd9')
        with ZipFile(bundle) as archive:
            raw = archive.read('.cache/T123-proof-r2/annual-3.g2core')
        driver = Driver(Core.load(raw, goal_dat=requires.CACHE / 'GOAL.DAT'))
        driver._open_squad()
        driver.press(INSERT, expect=('select-squad',))
        driver.to_menu()
        driver.play_round(fix_eleven=fix_eleven, on_taker=lambda *_: 13, on_replay=lambda *_: False)
        self.check_refusal(driver, 'tour')


if __name__ == '__main__':
    controlled_worker()
