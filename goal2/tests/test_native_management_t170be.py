"""[designed: T170be] Standalone management edits retain the native publication chain."""

import dataclasses
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from goal2.desktop.native_save_owner import NativeSaveOwner
from goal2.engine.original_match.image import GAME_PTR, Image
from goal2.game import engine_tables, native_season_save
from goal2.game.season import SeasonSession, canonical_hash
from goal2.game.season_publication import PublishedManagementEdit, SeasonCampaign, SeasonPublication
from goal2.tests import pypy_engine
from goal2.tests.test_prematch_preview_t170s import reference_raw
from goal2.tests.test_season_publication_t170c2 import step
from goal2.ui import saves


def source_state():
    return Image.from_bytes(reference_raw()).state(engine_tables.load())


def changed(state, mask=1):
    image = Image.from_state(state, engine_tables.load())
    image.memory[image.DS * 16 + 0x7B62] ^= mask
    return image.state()


def publish_edit(campaign, state, **overrides):
    request = dict(action='select-twenty', revision=campaign.revision,
                   input_hash=campaign.canonical_hash, output_hash=canonical_hash(state))
    request.update(overrides)
    return campaign.publish_management(state, **request)


def publish_round(campaign, state, status='complete'):
    session = SeasonSession(campaign.state)
    with patch('goal2.game.season.route.play_round', return_value=step(status, state)):
        observation = session.advance()
    publication = SeasonPublication(campaign)
    return publication.complete(publication.begin(observation).token, session)


def next_entry(state):
    session = SeasonSession(state)
    return dataclasses.asdict(session.advance())


class Management(unittest.TestCase):
    def setUp(self):
        self.state = source_state()
        self.campaign = SeasonCampaign(self.state)

    def test_mixed_history_round_trips_without_reassigning_round_numbers(self):
        first_state = changed(self.state)
        first = publish_round(self.campaign, first_state)
        before = native_season_save.encode(self.campaign)
        self.assertEqual(json.loads(before)['version'], 1)
        restored_v1 = native_season_save.decode(before)
        self.assertEqual(native_season_save.encode(restored_v1), before)

        edited = changed(first_state, 2)
        edit = publish_edit(restored_v1, edited)
        self.assertEqual(edit, PublishedManagementEdit('select-twenty', first.output_hash, canonical_hash(edited)))
        self.assertEqual(restored_v1.published, (first,))
        self.assertEqual(NativeSaveOwner(restored_v1).desk_view().status, 'complete')
        second = publish_round(restored_v1, changed(edited, 4))
        self.assertEqual((first.call_number, second.call_number), (1, 1))
        self.assertEqual(second.input_hash, edit.output_hash)
        expected = (first, edit, second)
        raw = native_season_save.encode(restored_v1)
        self.assertEqual(json.loads(raw)['version'], 2)
        fresh = native_season_save.decode(raw)
        self.assertEqual(fresh.committed_snapshot(), (restored_v1.state, expected))
        self.assertEqual((fresh.revision, fresh.published), (3, (first, second)))
        self.assertEqual(native_season_save.encode(fresh), raw)

    def test_old_or_tampered_requests_and_calendar_changes_never_install(self):
        edited = changed(self.state)
        for overrides, message in (
            ({'revision': True}, 'stale'), ({'revision': 1}, 'stale'),
            ({'input_hash': '0' * 64}, 'stale'), ({'output_hash': '0' * 64}, 'declared output'),
            ({'action': 'swap'}, 'unsupported'),
        ):
            with self.subTest(overrides=overrides), self.assertRaisesRegex(ValueError, message):
                publish_edit(self.campaign, edited, **overrides)
        image = Image.from_state(edited, engine_tables.load())
        image.memory[image.far(GAME_PTR) + 0x26] ^= 1
        with self.assertRaisesRegex(ValueError, 'manager or calendar'):
            publish_edit(self.campaign, image.state())
        self.assertEqual(self.campaign.committed_snapshot(), (self.state, ()))

    def test_exact_noop_does_not_advance_history_but_terminal_edit_refuses(self):
        self.assertIsNone(publish_edit(self.campaign, self.state))
        self.assertEqual(self.campaign.revision, 0)
        terminal = publish_round(self.campaign, self.state, 'deferred-rollover')
        with self.assertRaisesRegex(ValueError, 'after deferred rollover'):
            publish_edit(self.campaign, changed(self.state))
        self.assertEqual(self.campaign.committed_snapshot(), (self.state, (terminal,)))

    def test_failed_validation_and_a_rival_edit_cannot_be_overwritten(self):
        def refuse(_):
            raise ValueError('owner refused')

        campaign = SeasonCampaign(self.state, view=refuse)
        with self.assertRaisesRegex(ValueError, 'owner refused'):
            publish_edit(campaign, changed(self.state))
        self.assertEqual(campaign.committed_snapshot(), (self.state, ()))

        rival = changed(self.state, 2)
        installed = []

        def validate(candidate):
            if candidate.state != rival:
                installed.append(publish_edit(campaign, rival))

        campaign = SeasonCampaign(self.state, view=validate)
        with self.assertRaisesRegex(ValueError, 'stale'):
            publish_edit(campaign, changed(self.state))
        self.assertEqual(campaign.committed_snapshot(), (rival, tuple(installed)))

    def test_mixed_reader_rejects_invalid_type_discriminator_and_broken_chain(self):
        publish_round(self.campaign, changed(self.state))
        publish_edit(self.campaign, changed(self.campaign.state, 2))
        raw = native_season_save.encode(self.campaign)
        for edit, message in (
            (lambda rows: rows[1].update(kind='other'), 'history kind'),
            (lambda rows: rows[1].update(action='move'), 'ledger record'),
            (lambda rows: rows[1].update(input_hash='0' * 64), 'ledger chain'),
            (lambda rows: rows[1].update(output_hash='0' * 64), 'saved state'),
        ):
            with self.subTest(message=message):
                doc = json.loads(raw)
                doc.pop('sha256')
                edit(doc['history'])
                repaired = dict(doc, sha256=canonical_hash(doc))
                with self.assertRaisesRegex(native_season_save.NativeSeasonSaveError, message):
                    native_season_save.decode(json.dumps(repaired).encode())

    def test_actual_accepted_pypy_selection_survives_named_reload_and_next_entry(self):
        result = pypy_engine.call('goal2.tests.test_season_assistant_t183e:actual', self.state)
        self.assertTrue(result['result']['allowed'])
        self.assertEqual(result['result']['country'], NativeSaveOwner(self.campaign).desk_view().team.country)
        self.assertNotEqual(result['state'], self.state)
        declared = canonical_hash(result['state'])
        record = publish_edit(self.campaign, result['state'])
        self.assertEqual(record.output_hash, declared)
        self.assertEqual(self.campaign.published, ())
        with TemporaryDirectory() as directory:
            owner = NativeSaveOwner(self.campaign)
            path = saves.write(owner, Path(directory), 'Committed selection')
            restored = saves.load(path, Path(directory) / 'unused', native=True)
            self.assertEqual(restored.campaign.committed_snapshot(), (result['state'], (record,)))
            self.assertEqual(restored.desk_view(), owner.desk_view())
            self.assertIsNone(restored.desk_view().status)
            entry = pypy_engine.call(__name__ + ':next_entry', restored.campaign.state)
            self.assertEqual((entry['status'], entry['call_number'], entry['input_hash']), ('match', 1, declared))
