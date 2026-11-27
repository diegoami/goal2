"""[designed: T170ba] The Desk reads only the committed native campaign."""

from dataclasses import FrozenInstanceError, asdict
from pathlib import Path
from tempfile import TemporaryDirectory
import time
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from goal2.core.views import MANAGERS, Memory, desk
from goal2.desktop.native_save_owner import NativeSaveOwner
from goal2.engine.original_match.image import Image
from goal2.game import engine_tables
from goal2.game.season import canonical_hash
from goal2.game.season_publication import SeasonCampaign, SeasonPublication
from goal2.tests import requires
from goal2.tests.season_oracle import component_of
from goal2.tests.test_prematch_preview_t170s import reference_raw
from goal2.tests.test_season_oracle_t170d import ARTIFACTS, CASES, GOAL_DAT, checkpoint
from goal2.ui import saves


def fixture_owner(raw):
    return NativeSaveOwner(SeasonCampaign(Image.from_bytes(raw).state(engine_tables.load())))


class DeskChecks:
    def assert_core_parity(self, view, expected):
        self.assertEqual(asdict(view.team), expected['team'])
        self.assertEqual(asdict(view.manager), {
            'number': expected['manager_number'], 'name': expected['manager'],
            'country': expected['team']['country'],
        })
        self.assertEqual((view.rating, view.year, view.stage, view.stage_word, view.sacked),
                         tuple(expected[key] for key in ('rating', 'year', 'stage', 'stage_word', 'sacked')))
        self.assertEqual([asdict(row) for row in view.managers], expected['managers'])
        self.assertEqual([asdict(row) for row in view.starting_eleven], expected['squad'][:11])
        self.assertEqual([asdict(row) for row in view.bench], expected['squad'][11:])
        if expected['fixture'] is None:
            self.assertIsNone(view.fixture)
        else:
            self.assertEqual(asdict(view.fixture), {
                'index': expected['fixture'], 'opponent': expected['opponent'],
                'text': expected['fixture_kind'],
            })


class Projection(DeskChecks, unittest.TestCase):
    def test_original_desk_fields_and_named_save_round_trip_are_immutable(self):
        raw = reference_raw()
        owner = fixture_owner(raw)
        before = owner.campaign.committed_snapshot()
        with patch('goal2.game.engine_process.EngineProcess.season_open',
                   side_effect=AssertionError('the Desk must not open a worker')), \
             patch('goal2.game.season.route.play_round', side_effect=AssertionError('the Desk must not advance')):
            view = owner.desk_view()
            self.assert_core_parity(view, desk(Image.from_bytes(raw)))
            self.assertEqual((view.revision, view.status, view.state_hash), (0, None, canonical_hash(before[0])))
            self.assertEqual(view.team.name, 'Denmark')
            self.assertEqual(view.fixture.opponent.name, 'Sweden')
            self.assertEqual(len(view.starting_eleven), 11)
            self.assertEqual(len(view.bench), 9)
            for row, key, value in ((view, 'year', 1), (view.team, 'name', 'Other'),
                                    (view.fixture.opponent, 'country', 0), (view.bench[0], 'position', 0)):
                with self.assertRaises(FrozenInstanceError):
                    setattr(row, key, value)
            with TemporaryDirectory() as directory:
                path = saves.write(owner, Path(directory), 'Manager boundary')
                restored = saves.load(path, GOAL_DAT, native=True)
                self.assertEqual(restored.desk_view(), view)
                self.assertEqual(restored.summary(), owner.summary())
        self.assertEqual(owner.campaign.committed_snapshot(), before)

    def test_wrong_current_manager_is_refused_by_both_views(self):
        image = Image.from_bytes(reference_raw())
        mem = Memory(image)
        image.memory[mem.far(MANAGERS) + 3 * (0x80 + mem.game(1))] = 0
        owner = NativeSaveOwner(SeasonCampaign(image.state(engine_tables.load())))
        for read in (owner.desk_view, owner.summary):
            with self.assertRaisesRegex(ValueError, 'current manager differs from the saved country'):
                read()

    def test_dismissal_retains_the_original_no_fixture_condition(self):
        image = Image.from_bytes(reference_raw())
        mem = Memory(image)
        from goal2.engine.original_match.image import GAME_PTR

        image.memory[image.far(GAME_PTR) + 0x47 + mem.game(1)] = 1
        owner = NativeSaveOwner(SeasonCampaign(image.state(engine_tables.load())))
        view = owner.desk_view()
        self.assert_core_parity(view, desk(image))
        self.assertTrue(view.sacked)
        self.assertIsNone(view.fixture)
        self.assertEqual(owner.summary()['next'], 'No scheduled match')


@requires.need(modules=('unicorn',), files=('GOAL.DAT', ARTIFACTS[2]['name']))
class Actual(DeskChecks, unittest.TestCase):
    def until(self, owner, choices, *, poll=True, timeout=120):
        end = time.monotonic() + timeout
        while time.monotonic() < end:
            status = owner.poll() if poll else owner.status
            if status in choices:
                return status
            if status == 'lost':
                self.fail(owner.message)
            time.sleep(.002)
        self.fail(f'Expected {choices}, found {owner.status}')

    def test_native_desk_moves_only_after_verified_complete_and_deferred_publication(self):
        from goal2.game.native_season import NativeSeasonOwner

        raw = component_of(checkpoint(CASES[2]), GOAL_DAT)
        state = Image.from_bytes(raw).state(engine_tables.load())
        validated = []

        def validate(candidate):
            self.assertEqual(owner.desk_view(), expected)
            validated.append(candidate.record.output_hash)

        owner = NativeSaveOwner(SeasonCampaign(state, view=validate))
        publication = SeasonPublication(owner.campaign)
        native = NativeSeasonOwner(SimpleNamespace(), owner.campaign.state)
        try:
            self.until(native, ('boundary',))
            self.assertEqual(native.shared.engine.ready['implementation'], 'PyPy')
            native.take_observations()
            initial = owner.desk_view()
            expected = initial
            for count, status in enumerate(('complete', 'deferred-rollover'), 1):
                native.advance()
                self.assertEqual(owner.desk_view(), expected)
                self.until(native, ('boundary', 'terminal'))
                packet, = native.take_observations()
                self.assertEqual(packet['observation']['status'], status)
                self.assertTrue(packet['observation']['played_fixtures'])
                self.assertEqual(owner.desk_view(), expected)
                record = publication.complete_native(native, packet)
                self.assertEqual(validated[-1], record.output_hash)
                expected = owner.desk_view()
                self.assertEqual((expected.revision, expected.status, expected.state_hash),
                                 (count, status, record.output_hash))
                self.assert_core_parity(expected, desk(Image.from_state(packet['state'], engine_tables.load())))
            with TemporaryDirectory() as directory:
                path = saves.write(owner, directory, 'Deferred')
                self.assertEqual(saves.load(path, GOAL_DAT, native=True).desk_view(), expected)
            self.assertEqual(initial.revision, 0)
            self.assertIsNone(initial.status)
        finally:
            native.close()
            self.until(native, ('closed',), poll=False, timeout=15)
