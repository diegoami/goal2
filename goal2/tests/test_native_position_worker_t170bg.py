"""[designed: T170bg] Real PyPy position candidates and controlled pipe failures."""

import json
import queue
import sys
import unittest

from goal2.core.views import pool
from goal2.engine.original_match import Image
from goal2.game import engine_tables
from goal2.game.engine_process import EngineProcess
from goal2.game.engine_server import read_packet, write_packet
from goal2.game.season import canonical_hash
from goal2.game.season_publication import SeasonCampaign
from goal2.tests.pypy_engine import call
from goal2.tests.test_prematch_preview_t170s import reference_raw


def controlled_worker():
    incoming, outgoing = sys.stdin.buffer, sys.stdout.buffer
    mode = sys.argv[-1]
    header, raw = read_packet(incoming)
    if mode == 'dead':
        return
    binding = {field: header[field] for field in ('request', 'revision', 'input_hash', 'player', 'key')}
    write_packet(outgoing, {'kind': 'ready', 'value': {}})
    if mode == 'timeout':
        read_packet(incoming)
        return
    state = json.loads(raw)
    word = binding['player']
    row = Image.from_state(state, engine_tables.load()).players()[word]
    value = dict(binding, output_hash=canonical_hash(state), position=(row[6] + 1) % 14, club_position=row[7])
    if mode == 'stale':
        value['request'] -= 1
    elif mode == 'revision':
        value['revision'] += 1
    elif mode == 'word':
        value['player'] += 1
    elif mode == 'key':
        value['key'] = 'C'
    elif mode == 'hash':
        value['output_hash'] = 'wrong'
    elif mode == 'position':
        value['position'] = row[6]
    elif mode == 'malformed':
        raw = b'{'
    write_packet(outgoing, {'kind': 'position', 'value': value}, raw)
    read_packet(incoming)


class Worker(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        image = Image.from_bytes(reference_raw())
        country, = image.managed_countries()
        cls.squad_word = image.squad(country)[1]
        cls.pool_word = next(row['player'] for row in pool(image)['rows'] if row['player'])
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

    def edit(self, worker, word, key='R', revision=0, state=None):
        return worker.edit_position(self.state if state is None else state, revision=revision, player=word, key=key)

    def test_real_pypy_position_matches_direct_and_publishes_once(self):
        worker, replies = self.engine()
        campaign = SeasonCampaign(self.state)
        for word in (self.squad_word, self.pool_word):
            for key in ('R', 'C'):
                state, revision = campaign.state, campaign.revision
                control = call('goal2.tests.test_native_position_t170bf:produce', state, word, key)
                request = self.edit(worker, word, key, revision, state)
                result = self.reply(replies, 'position')
                self.assertEqual(worker.ready['implementation'], 'PyPy')
                self.assertEqual(worker.generation, 1)
                self.assertEqual(result, dict(control, request=request, revision=revision, key=key))
                self.assertEqual(campaign.state, state)
                fields = {k: result[k] for k in ('revision', 'input_hash', 'output_hash')}
                record = campaign.publish_management(result['state'], action='player-position', **fields)
                self.assertEqual(campaign.state, result['state'])
                if record is not None:
                    with self.assertRaisesRegex(ValueError, 'stale'):
                        campaign.publish_management(result['state'], action='player-position', **fields)

    def test_real_refusal_and_cancel_keep_child_for_next_explicit_edit(self):
        worker, replies = self.engine()
        image = Image.from_state(self.state, engine_tables.load())
        country, = image.managed_countries()
        domain = set(image.squad(country)) | {row['player'] for row in pool(image)['rows']}
        foreign = next(w for w in range(1, len(image.players())) if w not in domain)
        request = self.edit(worker, foreign)
        self.assertEqual(self.reply(replies, 'position_error')['request'], request)
        with worker._lock:
            request = self.edit(worker, self.squad_word)
            self.assertFalse(worker.cancel_position(request + 1))
            self.assertTrue(worker.cancel_position(request))
            self.assertTrue(worker.busy)
            with self.assertRaisesRegex(ValueError, 'pending'):
                self.edit(worker, self.squad_word)
        self.assertEqual(self.reply(replies, 'position_cancelled'), {'request': request})
        self.assertFalse(worker.busy)
        next_request = self.edit(worker, self.squad_word)
        self.assertGreater(next_request, request)
        self.assertEqual(self.reply(replies, 'position')['request'], next_request)
        self.assertEqual(worker.generation, 1)

    def test_held_season_excludes_standalone_position_requests(self):
        worker, replies = self.engine()
        worker.season_open(self.state)
        self.reply(replies, 'season')
        with self.assertRaisesRegex(ValueError, 'held season'):
            self.edit(worker, self.squad_word)
        worker.season_request('discard')
        self.reply(replies, 'season')
        self.edit(worker, self.squad_word)
        self.reply(replies, 'position')
        self.assertEqual(worker.generation, 1)

    def test_bad_replies_and_death_clear_pending_without_replay(self):
        for mode in ('stale', 'revision', 'word', 'key', 'hash', 'position', 'unchanged', 'malformed', 'dead'):
            with self.subTest(mode=mode):
                worker, replies = self.engine([sys.executable, '-m', __name__, mode])
                request = self.edit(worker, self.squad_word)
                death = self.reply(replies, 'death')
                if mode != 'dead':
                    self.assertIn('position', death['error'])
                self.assertFalse(worker.busy)
                self.assertFalse(worker.cancel_position(request))
                self.assertIsNone(worker.pid)
                self.assertEqual(worker.generation, 1)
        worker.command = None
        next_request = self.edit(worker, self.squad_word)
        self.assertGreater(next_request, request)
        self.assertEqual(self.reply(replies, 'position')['request'], next_request)
        self.assertEqual(worker.generation, 2)

    def test_cancel_timeout_ends_unresponsive_child(self):
        worker, replies = self.engine([sys.executable, '-m', __name__, 'timeout'], cancel_deadline=1)
        request = self.edit(worker, self.squad_word)
        self.reply(replies, 'ready')
        self.assertTrue(worker.cancel_position(request))
        self.reply(replies, 'death')
        self.assertFalse(worker.busy)


if __name__ == '__main__':
    controlled_worker()
