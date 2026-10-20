"""[designed: T86 rework 1] One control per guard that docs/cloud-270/seam.md or a scenario
docstring claims, where the earlier tests reached the outcome through another guard.
Each control is named in docs/cloud-270/mutations.py with the mutation that removes
only its guard.
"""
import copy
import hashlib
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch

from goal2.desktop.competitive import CompetitiveJobs
from goal2.desktop.jobs import QuickJobs
from goal2.desktop.watched import WatchedController
from goal2.engine.original_match import Fixture
from goal2.game.watched_jobs import WatchedJobs
from goal2.game.watched_match import WatchedOutcome
from goal2.scenario import TEMPLATE, factory, real, scripts
from goal2.scenario.model import ScenarioModel
from goal2.scenario.runtime import RUNTIME
from goal2.scenario.worker import command
from goal2.tests.test_scenario_branches import at_fixture, finish


def outcome_for(job, fixture, *, competitive=False):
    """[designed: T86] The scripted outcome a fake child would send for this job."""
    image = hashlib.sha256(factory.encode(job.state, TEMPLATE)).hexdigest()
    played = scripts.match(job.state, fixture, image, competitive=competitive)
    return WatchedOutcome(played['result'], played['memory'], tuple(played['events']), played['seeds'],
                          played['engine_year'])


class PublicationGuards(unittest.TestCase):
    def setUp(self):
        self.model = ScenarioModel()
        self.fixture = Fixture(1, 2, 1)

    def refused(self, fault, message, *, model=None, fixture=None, competitive=False):
        model = model or self.model
        held, before = model.state, copy.deepcopy(model.state)
        if competitive:
            jobs = CompetitiveJobs(model, command=command('competitive', fault=fault), runtime=RUNTIME)
            token = jobs.start()
        else:
            jobs = WatchedJobs(model, command=command('watched', fault=fault), runtime=RUNTIME)
            token = jobs.start(fixture or self.fixture)
        self.addCleanup(jobs.close)
        with self.assertRaisesRegex(ValueError, message):
            deadline = time.monotonic() + 20
            while jobs.busy and time.monotonic() < deadline:
                jobs.poll(token);time.sleep(.005)
        self.assertFalse(jobs.busy)
        self.assertIs(model.state, held)
        self.assertEqual(model.state, before)

    def test_malformed_result_is_refused_by_result_validation(self):
        # R1: shots [-1, -1] passes every other check; only validate_result refuses it.
        self.refused('bad-stats', 'invalid watched statistics')

    def test_incomplete_event_stream_is_refused(self):
        self.refused('no-end', 'watched completion differs from the pending fixture or is incomplete')

    def test_foreign_input_image_is_refused(self):
        self.refused('bad-image', 'watched completion differs from the declared input image')

    def test_unmarked_completion_memory_is_refused(self):
        self.refused('bad-memory', 'fictional completion memory differs from its result')

    def test_competitive_kind_must_match_the_job(self):
        self.refused('bad-kind', 'completed kind differs from competitive job', model=at_fixture(4), competitive=True)

    def test_job_must_be_the_scheduled_fixture(self):
        jobs = WatchedJobs(self.model, command=command('watched'), runtime=RUNTIME);self.addCleanup(jobs.close)
        with self.assertRaisesRegex(ValueError, 'fictional job differs from the scheduled fixture'):
            jobs.start(Fixture(1, 3, 2))
        self.assertFalse(jobs.busy)

    def test_publish_refuses_an_owner_changed_after_preparation(self):
        # R2: the inherited final _check_owner in publish_prepared is the only guard reached.
        for change in ('value', 'object'):
            with self.subTest(change=change):
                model = ScenarioModel()
                publication = RUNTIME.publication(model)
                job = publication.begin(self.fixture)
                preparation = publication.prepare_completion(job.token, outcome_for(job, self.fixture))
                preparation.run()
                self.assertIsNone(preparation.error)
                if change == 'value':
                    model.state.country_tactics ^= 1
                else:
                    model.state = copy.deepcopy(model.state)
                changed = model.state
                with self.assertRaisesRegex(ValueError, 'watched completion is stale; active state changed'):
                    publication.publish_prepared(job.token, preparation)
                self.assertIs(model.state, changed)
                self.assertEqual(model.state.match_count, 0)

    def test_prepare_refuses_an_owner_changed_before_preparation(self):
        publication = RUNTIME.publication(self.model)
        job = publication.begin(self.fixture)
        self.model.state.country_tactics ^= 1
        with self.assertRaisesRegex(ValueError, 'watched completion is stale; active state changed'):
            publication.prepare_completion(job.token, outcome_for(job, self.fixture))
        with self.assertRaisesRegex(ValueError, 'unknown or consumed'):
            publication.prepare_completion(job.token, outcome_for(job, self.fixture))


class ViewerGuards(unittest.TestCase):
    def refused(self, engine_fault, viewer_fault, message):
        model = ScenarioModel()
        held = model.state
        watch = WatchedController(model, engine_command=command('watched', fault=engine_fault),
                                  viewer_command=command('viewer', fault=viewer_fault), runtime=RUNTIME)
        self.addCleanup(watch.close)
        watch.start()
        with self.assertRaisesRegex(ValueError, message):
            finish(self, watch.poll)
        self.assertFalse(model.match_pending)
        self.assertIs(model.state, held)

    def test_status_digest_must_match_the_sent_stream(self):
        self.refused(None, 'bad-digest', 'invalid viewer acknowledgement')

    def test_status_cannot_acknowledge_unsent_packets(self):
        self.refused(None, 'future', 'invalid viewer acknowledgement')

    def test_frame_acknowledgement_must_name_the_delivered_frame(self):
        self.refused(None, 'bad-frame-digest', 'invalid rendered pitch acknowledgement')

    def test_frame_count_must_equal_completed_ticks(self):
        self.refused('few-frames', None, 'pitch frame count differs from completed ticks')


class ModelAndRuntimeGuards(unittest.TestCase):
    def test_calendar_completes_only_the_next_fixture_with_its_resolution(self):
        calendar = factory.new_state().campaign
        with self.assertRaisesRegex(ValueError, 'expected next fixture'):
            calendar.complete_fixture('original:2')
        with self.assertRaisesRegex(ValueError, 'friendly completion cannot have competitive resolution'):
            calendar.complete_fixture('original:1', resolution={'kind': 2})
        calendar.complete_fixture('original:1');calendar.complete_fixture('original:2')
        with self.assertRaisesRegex(ValueError, 'competitive completion needs its resolution'):
            calendar.complete_fixture('original:3')
        bad = {'kind': 2, 'winner': 1, 'regulation': [2, 0], 'extra_time': None, 'penalties': None}
        with self.assertRaisesRegex(ValueError, 'competitive winner differs'):
            calendar.complete_fixture('original:3', resolution=bad, score=[2, 0])
        self.assertEqual(calendar.completed_fixture_ids, ['original:1', 'original:2'])

    def test_quick_check_refuses_unavailable_starters_and_foreign_templates(self):
        state = factory.new_state()
        with self.assertRaisesRegex(ValueError, 'foreign template'):
            RUNTIME.check(state, b'career template')
        state.starting_eleven[0] = factory.INJURED_AT_START
        with self.assertRaisesRegex(ValueError, 'unavailable starters'):
            RUNTIME.check(state, TEMPLATE)

    def test_quick_refuses_a_competitive_fixture(self):
        model = at_fixture(3)
        with self.assertRaisesRegex(ValueError, 'Quick supports scheduled friendlies only'):
            QuickJobs(model, command=command('quick'), runtime=RUNTIME).start()
        self.assertFalse(model.match_pending)

    def test_view_and_result_text_refuse_unmarked_or_foreign_results(self):
        model = ScenarioModel()
        unmarked = copy.deepcopy(model.state);unmarked.scenario = 'career'
        with self.assertRaisesRegex(ValueError, 'Fictional view refused'):
            model.view(unmarked)
        foreign = copy.deepcopy(model.state)
        foreign.last_match = {'engine': 'original-match:x', 'teams': [1, 2], 'score': [0, 0], 'goals': []}
        with self.assertRaisesRegex(ValueError, 'Invalid fictional match result'):
            model.result_text(foreign)

    def test_exchange_window_closes_outside_friendlies(self):
        model = at_fixture(3)
        self.assertFalse(model.pool_view()['window']['allowed'])
        with self.assertRaisesRegex(ValueError, 'Exchange window is closed'):
            model.exchange(2, 101)

    def test_competitive_play_refuses_while_another_match_is_pending(self):
        model = at_fixture(3);model.match_pending = True
        jobs = CompetitiveJobs(model, command=command('competitive'), runtime=RUNTIME);self.addCleanup(jobs.close)
        with self.assertRaisesRegex(ValueError, 'Another match is already running'):
            jobs.start()
        self.assertFalse(jobs.busy)

    def test_real_backend_reports_every_missing_item(self):
        with tempfile.TemporaryDirectory() as folder, patch.object(real, 'ROOT', Path(folder)):
            self.assertEqual(real.missing('quick'), list(real.NEEDS['quick']))
            self.assertTrue(real.not_configured('quick').startswith('real backend: not configured (.cache/GOAL.DAT, '))
            for name in real.NEEDS['quick']:
                (Path(folder) / name).parent.mkdir(exist_ok=True);(Path(folder) / name).write_bytes(b'')
            self.assertIsNone(real.not_configured('quick'))
            with patch('importlib.util.find_spec', return_value=None):
                self.assertIn('unicorn', real.missing('watched')[-1])


if __name__ == '__main__':
    unittest.main()
