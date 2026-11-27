"""[designed: T170ay] Save only committed native campaign boundaries."""

import base64
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import time
from types import SimpleNamespace
import unittest
from unittest.mock import patch
import zlib

from goal2.engine.original_match.image import Image
from goal2.game import engine_tables, native_season_save, session_save
from goal2.game.native_season_save import NativeSeasonSaveError, decode, encode, load, save
from goal2.game.season import SeasonSession, canonical_hash
from goal2.game.season_publication import SeasonCampaign, SeasonPublication
from goal2.tests import requires
from goal2.tests.season_oracle import component_of
from goal2.tests.test_native_season_t170aa import seed
from goal2.tests.test_season_oracle_t170d import ARTIFACTS, CASES, GOAL_DAT, checkpoint
from goal2.tests.test_season_publication_t170c2 import step
from goal2.tests.test_session_save import _state as legacy_state


def changed(state):
    image = Image.from_state(state, engine_tables.load())
    image.memory[image.DS * 16 + 0x7B62] ^= 1
    return image.state()


def serialized(document):
    payload = dict(document)
    payload.pop('sha256')
    return json.dumps(dict(payload, sha256=canonical_hash(payload))).encode('ascii')


class Save(unittest.TestCase):
    def setUp(self):
        self.state = seed()[0]['state']
        self.after = changed(self.state)
        self.campaign = SeasonCampaign(self.state)
        self.publication = SeasonPublication(self.campaign)

    def prepare(self, status='complete', value=None):
        session = SeasonSession(self.campaign.state)
        output = self.after if value is None else value
        with patch('goal2.game.season.route.play_round', return_value=step(status, output)):
            observed = session.advance()
        token = self.publication.begin(observed).token
        preparation = self.publication.prepare_completion(token, session)
        preparation.run()
        return token, preparation, observed

    def test_only_committed_state_is_saved_and_reloaded_detached(self):
        token, prepared, observed = self.prepare()
        initial = decode(encode(self.campaign))
        self.assertEqual((initial.state, initial.published, initial.revision), (self.state, (), 0))
        record = self.publication.publish_prepared(token, prepared)
        restored = decode(encode(self.campaign))
        self.assertEqual((restored.state, restored.published, restored.revision), (self.after, (record,), 1))
        self.assertEqual(encode(restored), encode(self.campaign))
        detached = restored.state
        detached['initialised'].clear()
        self.assertEqual(restored.state, self.after)
        with self.assertRaisesRegex(ValueError, 'already published'):
            SeasonPublication(restored).begin(observed)

    def test_worker_local_call_numbers_and_same_hash_terminal_are_retained(self):
        complete = self.publication.publish_prepared(*self.prepare()[:2])
        terminal = self.publication.publish_prepared(*self.prepare('deferred-rollover', self.after)[:2])
        restored = decode(encode(self.campaign))
        self.assertEqual([row.call_number for row in restored.published], [1, 1])
        self.assertEqual(restored.published, (complete, terminal))
        self.assertEqual(restored.canonical_hash, terminal.input_hash)
        self.assertEqual(terminal.input_hash, terminal.output_hash)
        self.assertEqual(restored.revision, 2)

    def test_refuses_corrupt_and_incompatible_data_including_legacy_documents(self):
        raw = encode(self.campaign)
        with self.assertRaises(NativeSeasonSaveError):
            decode(b'{bad json')
        with self.assertRaisesRegex(NativeSeasonSaveError, 'duplicated'):
            decode(raw[:-1] + b',"version":1}')
        with self.assertRaisesRegex(NativeSeasonSaveError, 'format or version'):
            decode(session_save.encode(legacy_state(), b'legacy'))
        with self.assertRaises(session_save.SessionSaveError):
            session_save.decode(raw)
        document = json.loads(raw)
        document['state']['header'] = 'ff'
        with self.assertRaisesRegex(NativeSeasonSaveError, 'checksum'):
            decode(json.dumps(document).encode())
        document = json.loads(raw)
        document['version'] = True
        with self.assertRaisesRegex(NativeSeasonSaveError, 'format or version'):
            decode(serialized(document))

    def test_checked_state_rejects_invalid_segments_tables_and_compressed_memory(self):
        for field, value in (
            ('load', True), ('load', 0xffff), ('header', '00'),
            ('tables_sha256', {}), ('memory', 'invalid!'),
            ('memory', base64.b64encode(zlib.compress(b'undersized')).decode('ascii')),
        ):
            with self.subTest(field=field, value=value):
                document = json.loads(encode(self.campaign))
                document['state'][field] = value
                with self.assertRaisesRegex(NativeSeasonSaveError, 'invalid native state'):
                    decode(serialized(document))
        document = json.loads(encode(self.campaign))
        image = Image.from_state(self.state, engine_tables.load())
        from goal2.engine.original_match.image import COUNTRIES_PTR, COUNTRY_SIZE, MANAGER

        image.memory[image.far(COUNTRIES_PTR) + 7 * COUNTRY_SIZE + MANAGER] = 0
        document['state'] = image.state()
        with self.assertRaisesRegex(NativeSeasonSaveError, 'one managed country'):
            decode(serialized(document))

    def test_ledger_order_duplicate_and_state_tail_are_checked_after_checksum(self):
        self.publication.publish_prepared(*self.prepare()[:2])
        self.publication.publish_prepared(*self.prepare('deferred-rollover', self.after)[:2])
        raw = encode(self.campaign)
        for edit, message in (
            (lambda rows: rows.reverse(), 'ledger chain'),
            (lambda rows: rows.append(dict(rows[-1])), 'duplicate'),
            (lambda rows: rows[-1].update(output_hash='0' * 64), 'saved state'),
            (lambda rows: rows[-1].update(status='match'), 'ledger record'),
            (lambda rows: rows[-1].update(call_number=True), 'ledger record'),
        ):
            with self.subTest(message=message):
                document = json.loads(raw)
                edit(document['published'])
                with self.assertRaisesRegex(NativeSeasonSaveError, message):
                    decode(serialized(document))

    def test_save_size_bounds_and_failed_replace_preserve_prior_file(self):
        with TemporaryDirectory() as directory:
            path = Path(directory) / 'native.g2native'
            save(path, self.campaign)
            raw = path.read_bytes()
            self.assertEqual(load(path).state, self.state)
            with patch.object(native_season_save, '_MAX_DOCUMENT', len(raw) - 1):
                with self.assertRaisesRegex(NativeSeasonSaveError, 'size limit'):
                    load(path)
                with self.assertRaisesRegex(NativeSeasonSaveError, 'size limit'):
                    save(path, self.campaign)
            with patch.object(native_season_save, '_MAX_MEMORY', 1024):
                with self.assertRaisesRegex(NativeSeasonSaveError, 'memory size'):
                    decode(raw)
            with patch('goal2.game.save_file.os.replace', side_effect=OSError('disk unavailable')):
                with self.assertRaisesRegex(NativeSeasonSaveError, 'cannot write'):
                    save(path, self.campaign)
            self.assertEqual(path.read_bytes(), raw)
            self.assertEqual(list(path.parent.iterdir()), [path])


@requires.need(modules=('unicorn',), files=('GOAL.DAT', ARTIFACTS[2]['name']))
class Actual(unittest.TestCase):
    def until(self, owner, statuses, timeout=120, *, poll=True):
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            status = owner.poll() if poll else owner.status
            if status in statuses:
                return status
            if status == 'lost':
                self.fail(owner.message)
            time.sleep(.002)
        self.fail(f'The native worker stayed at {owner.status}, expected {statuses}')

    def advance(self, campaign):
        from goal2.game.native_season import NativeSeasonOwner

        identity = SimpleNamespace(state='identity owner')
        owner = NativeSeasonOwner(identity, campaign.state)
        try:
            self.until(owner, ('boundary',))
            self.assertEqual(owner.shared.engine.ready['implementation'], 'PyPy')
            ready, = owner.take_observations()
            self.assertEqual((ready['observation']['status'], ready['state']), ('ready', campaign.state))
            owner.advance()
            status = self.until(owner, ('boundary', 'terminal', 'prematch'))
            self.assertNotEqual(status, 'prematch')
            packet, = owner.take_observations()
            SeasonPublication(campaign).complete_native(owner, packet)
            self.assertEqual(owner.take_observations(), [])
            self.assertEqual(identity.state, 'identity owner')
            return packet['observation']
        finally:
            owner.close()
            self.until(owner, ('closed',), 15, poll=False)

    def test_actual_reloaded_boundary_matches_fresh_worker_and_preserves_terminal(self):
        raw = component_of(checkpoint(CASES[2]), GOAL_DAT)
        campaign = SeasonCampaign(Image.from_bytes(raw).state(engine_tables.load()))
        first = self.advance(campaign)
        self.assertEqual(first['status'], 'complete')
        self.assertTrue(first['played_fixtures'])
        with TemporaryDirectory() as directory:
            path = Path(directory) / 'native.g2native'
            save(path, campaign)
            with patch('goal2.game.engine_process.EngineProcess.season_open',
                       side_effect=AssertionError('load must not open the worker')):
                restored = load(path)
            self.assertEqual((restored.state, restored.published, restored.revision),
                             (campaign.state, campaign.published, 1))
            direct = self.advance(campaign)
            reloaded = self.advance(restored)
            self.assertEqual(reloaded['status'], 'deferred-rollover')
            self.assertTrue(reloaded['played_fixtures'])
            self.assertTrue(reloaded['news_pages'])
            self.assertEqual(reloaded, direct)
            self.assertEqual((restored.state, restored.published, restored.revision),
                             (campaign.state, campaign.published, 2))
            save(path, restored)
            terminal = load(path)
            self.assertEqual(terminal.state, restored.state)
            self.assertEqual(terminal.published, restored.published)
            self.assertEqual(terminal.published[-1].status, 'deferred-rollover')
