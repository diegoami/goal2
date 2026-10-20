"""[designed: T86 rework 2] One control per guard call site that no earlier control reaches alone.

Each test is named in docs/cloud-270/mutations.py with the mutation that removes only
its site. `python3 docs/cloud-270/mutations.py --sites` checks that every raise or
guard call in the swept files is listed there or explicitly classified.
"""
import copy
import dataclasses
import json
import time
import unittest

from goal2.desktop.competitive import CompetitiveJobs
from goal2.desktop.jobs import QuickJobs
from goal2.desktop.watched import WatchedController
from goal2.engine.original_match import Fixture
from goal2.game.watched_jobs import WatchedJobs
from goal2.game.watched_match import WatchedOutcome
from goal2.scenario import TEMPLATE, factory, require_scenario, scripts
from goal2.scenario.model import ScenarioModel
from goal2.scenario.runtime import RUNTIME
from goal2.scenario.worker import command
from goal2.tests.test_scenario_branches import at_fixture, finish
from goal2.tests.test_scenario_guards import outcome_for

FRIENDLY = Fixture(1, 2, 1)


class PublicationSites(unittest.TestCase):
    def setUp(self):
        self.model = ScenarioModel()
        self.publication = RUNTIME.publication(self.model)

    def test_begin_rechecks_the_owner_after_construction(self):
        # R4: the owner changes after the publication was built, before begin.
        for change in ('mark', 'template'):
            with self.subTest(change=change):
                model = ScenarioModel();publication = RUNTIME.publication(model)
                if change == 'mark':
                    model.state.scenario = 'career'
                else:
                    model.template_bytes = b'career template'
                with self.assertRaisesRegex(ValueError, 'Fictional publication refused'):
                    publication.begin(FRIENDLY)
                self.assertIsNone(publication._pending)

    def test_one_pending_job_and_one_preparation(self):
        job = self.publication.begin(FRIENDLY)
        with self.assertRaisesRegex(ValueError, 'a watched job is already pending'):
            self.publication.begin(FRIENDLY)
        self.publication.prepare_completion(job.token, outcome_for(job, FRIENDLY))
        with self.assertRaisesRegex(ValueError, 'watched completion is already preparing'):
            self.publication.prepare_completion(job.token, outcome_for(job, FRIENDLY))

    def test_preparation_must_be_bound_and_finished(self):
        job = self.publication.begin(FRIENDLY)
        preparation = self.publication.prepare_completion(job.token, outcome_for(job, FRIENDLY))
        with self.assertRaisesRegex(ValueError, 'watched completion is still preparing'):
            self.publication.publish_prepared(job.token, preparation)
        other = copy.copy(preparation);other.ready = True
        with self.assertRaisesRegex(ValueError, 'unknown or consumed watched completion preparation'):
            self.publication.publish_prepared(job.token, other)
        self.assertEqual(self.model.state.match_count, 0)

    def test_failed_preparation_is_raised_not_published(self):
        job = self.publication.begin(FRIENDLY)
        preparation = self.publication.prepare_completion(job.token, {'result': {}})
        preparation.run()
        with self.assertRaisesRegex(ValueError, 'completed watched outcome required'):
            self.publication.publish_prepared(job.token, preparation)
        self.assertEqual(self.model.state.match_count, 0)

    def test_each_memory_relation_is_checked(self):
        for case, message in (('json', 'fictional completion memory is not scenario data'),
                              ('image', 'fictional completion memory differs from its result'),
                              ('seeds', 'fictional completion memory differs from its result'),
                              ('seed_after', 'fictional completion memory differs from its result')):
            with self.subTest(case=case):
                model = ScenarioModel();publication = RUNTIME.publication(model)
                job = publication.begin(FRIENDLY)
                good = outcome_for(job, FRIENDLY)
                memory, seeds = json.loads(good.memory), good.seeds
                if case == 'json':
                    raw = b'not json'
                else:
                    if case == 'image':
                        memory['image_sha256'] = '1' * 64
                    if case == 'seeds':
                        memory['seeds'] = [1, 2]
                    if case == 'seed_after':
                        memory['seeds'] = [1, 2];seeds = (1, 2)
                    raw = json.dumps(memory).encode()
                outcome = WatchedOutcome(good.result, raw, good.events, seeds, good.engine_year)
                preparation = publication.prepare_completion(job.token, outcome);preparation.run()
                with self.assertRaisesRegex(ValueError, message):
                    publication.publish_prepared(job.token, preparation)
                self.assertEqual(model.state.match_count, 0)

    def test_completion_board_requires_scenario_memory(self):
        job = self.publication.begin(FRIENDLY)
        good = outcome_for(job, FRIENDLY)
        self.assertEqual(set(RUNTIME.completion(good, self.model.goaldat.player_names)),
                         {'board', 'ratings', 'man_of_the_match'})
        foreign = WatchedOutcome(good.result, json.dumps(dict(json.loads(good.memory), mark='career')).encode(),
                                 good.events, good.seeds, good.engine_year)
        with self.assertRaisesRegex(ValueError, 'fictional completion memory is not scenario data'):
            RUNTIME.completion(foreign, self.model.goaldat.player_names)


class CodecAndModelSites(unittest.TestCase):
    def test_codec_refuses_unmarked_malformed_or_untyped_data(self):
        state = factory.new_state()
        payload = json.loads(factory.encode(state, TEMPLATE))
        payload['state']['scenario'] = 'career'
        with self.assertRaisesRegex(ValueError, 'not a fictional scenario state'):
            factory.decode(json.dumps(payload).encode())
        payload = json.loads(factory.encode(state, TEMPLATE));payload['state']['players'].pop()
        with self.assertRaisesRegex(ValueError, 'invalid fictional player records'):
            factory.decode(json.dumps(payload).encode())
        with self.assertRaisesRegex(ValueError, 'template bytes required'):
            factory.encode(state, 'not bytes')
        with self.assertRaisesRegex(ValueError, 'not a fictional scenario file: '):
            factory.decode(b'\x00 not json')

    def test_require_scenario_refuses_unmarked_values(self):
        with self.assertRaisesRegex(ValueError, 'Probe refused: not a fictional scenario game'):
            require_scenario(object(), 'Probe')

    def test_quick_check_refuses_unmarked_state(self):
        state = factory.new_state();state.scenario = 'career'
        with self.assertRaisesRegex(ValueError, 'Fictional quick match refused: not a fictional'):
            RUNTIME.check(state, TEMPLATE)

    def test_view_refuses_malformed_squads_and_records_and_pool_queries(self):
        model = ScenarioModel()
        short = copy.deepcopy(model.state);short.managed_squad.pop()
        with self.assertRaisesRegex(ValueError, 'Invalid managed country or squad'):
            model.view(short)
        broken = copy.deepcopy(model.state);broken.players[1] = bytes(19)
        with self.assertRaisesRegex(ValueError, 'Invalid player record'):
            model.view(broken)
        with self.assertRaisesRegex(ValueError, 'invalid pool search or position'):
            model.pool_view(position=9)

    def test_scripts_refuse_unknown_names_and_extra_time_in_friendlies(self):
        state = factory.new_state();pending = state.campaign.next_fixture
        with self.assertRaisesRegex(ValueError, 'unknown fictional script'):
            scripts.script_for('original:1', 'penalties-only')
        with self.assertRaisesRegex(ValueError, 'fictional quick friendly cannot play extra time'):
            scripts.quick_candidate(state, pending, 'extra_time')
        with self.assertRaisesRegex(ValueError, 'fictional friendly cannot play extra time'):
            scripts.match(state, FRIENDLY, '0' * 64, competitive=False, name='shootout')


class ControllerSites(unittest.TestCase):
    def wait_refused(self, jobs, token, message, frames=False):
        with self.assertRaisesRegex(ValueError, message):
            deadline = time.monotonic() + 20
            while jobs.busy and time.monotonic() < deadline:
                jobs.poll(token)
                if frames and jobs.busy:
                    jobs.poll_frames(token)
                time.sleep(.005)
        self.assertFalse(jobs.busy)

    def test_unknown_and_long_truncated_journal_records_fail(self):
        for fault, message in (('unknown-kind', 'invalid watched IPC record'),
                               ('truncated-long', 'truncated watched IPC record')):
            with self.subTest(fault=fault):
                model = ScenarioModel()
                jobs = WatchedJobs(model, command=command('watched', fault=fault), runtime=RUNTIME)
                self.addCleanup(jobs.close)
                self.wait_refused(jobs, jobs.start(FRIENDLY), message)

    def test_frame_token_and_frame_stale_owner_cancel(self):
        model = ScenarioModel()
        jobs = WatchedJobs(model, command=command('watched', fault='frame-wrong-token'), runtime=RUNTIME)
        self.addCleanup(jobs.close)
        self.wait_refused(jobs, jobs.start(FRIENDLY, frames=True), 'pitch frame token differs', frames=True)
        jobs.close()
        jobs = WatchedJobs(model, command=command('watched', fault='hang'), runtime=RUNTIME)
        token = jobs.start(FRIENDLY, frames=True)
        finish(self, lambda: jobs.poll(token))
        model.state.country_tactics ^= 1
        with self.assertRaisesRegex(ValueError, 'Invalid watched pitch IPC: watched job is stale'):
            jobs.poll_frames(token)
        self.assertFalse(jobs.busy)
        jobs.close()

    def test_stale_tokens_are_refused_at_every_entry(self):
        model = ScenarioModel()
        jobs = WatchedJobs(model, command=command('watched', fault='hang'), runtime=RUNTIME);self.addCleanup(jobs.close)
        token = jobs.start(FRIENDLY, frames=True)
        for name, call in (('poll', lambda: jobs.poll('0' * 48)), ('poll_frames', lambda: jobs.poll_frames('0' * 48)),
                           ('ack_frames', lambda: jobs.ack_frames('0' * 48, 0)), ('cancel', lambda: jobs.cancel('0' * 48))):
            with self.subTest(entry=name), self.assertRaisesRegex(ValueError, 'stale or consumed watched job token'):
                call()
            self.assertTrue(jobs.busy)
        jobs.cancel(token)

    def test_watched_bridge_runs_one_job_and_respects_a_pending_match(self):
        model = ScenarioModel()
        jobs = WatchedJobs(model, command=command('watched', fault='hang'), runtime=RUNTIME);self.addCleanup(jobs.close)
        token = jobs.start(FRIENDLY)
        with self.assertRaisesRegex(ValueError, 'watched bridge is closed or a match is already running'):
            jobs.start(FRIENDLY)
        jobs.cancel(token)
        model.match_pending = True
        with self.assertRaisesRegex(ValueError, 'Another match is already pending'):
            jobs.start(FRIENDLY, frames=True)
        self.assertFalse(jobs.busy)

    def test_controller_refuses_while_a_match_is_pending(self):
        model = ScenarioModel();model.match_pending = True
        watch = WatchedController(model, engine_command=command('watched'), viewer_command=command('viewer'),
                                  runtime=RUNTIME)
        self.addCleanup(watch.close)
        with self.assertRaisesRegex(ValueError, 'A match is already running'):
            watch.start()
        self.assertIsNone(watch.process)

    def test_quick_preview_shape_values_and_identity_are_checked(self):
        for fault, message in (('halftime-missing-key', 'Invalid halftime preview: missing preview fields'),
                               ('halftime-bad-values', 'Invalid halftime preview: invalid preview values'),
                               ('halftime-bad-captain', 'Invalid halftime preview: preview differs from the pending game')):
            with self.subTest(fault=fault):
                model = ScenarioModel();held = model.state
                job = QuickJobs(model, command=command('quick', fault=fault), runtime=RUNTIME);self.addCleanup(job.cancel)
                job.start(halftime=True)
                with self.assertRaisesRegex(ValueError, message):
                    finish(self, lambda: job.poll() is None and job.halftime)
                self.assertFalse(job.busy)
                self.assertIs(model.state, held)

    def test_substitution_needs_a_pending_half_time_decision(self):
        model = ScenarioModel()
        job = QuickJobs(model, command=command('quick', fault='hang'), runtime=RUNTIME);self.addCleanup(job.cancel)
        job.start(halftime=True)
        with self.assertRaisesRegex(ValueError, 'No pending halftime decision'):
            job.substitute(10, 13)

    def test_competitive_binds_the_original_index_format_and_one_job(self):
        for fixture_id, message in (('x:3', 'needs an original:<number> scheduled fixture'),
                                    ('original:03', 'needs an original:<number> scheduled fixture')):
            with self.subTest(fixture_id=fixture_id):
                model = at_fixture(3)
                calendar = model.state.campaign
                calendar.fixtures = tuple(dataclasses.replace(f, fixture_id=fixture_id) if f.fixture_id == 'original:3'
                                          else f for f in calendar.fixtures)
                jobs = CompetitiveJobs(model, command=command('competitive'), runtime=RUNTIME);self.addCleanup(jobs.close)
                with self.assertRaisesRegex(ValueError, message):
                    jobs.start()
                self.assertFalse(model.match_pending)
        model = at_fixture(3)
        jobs = CompetitiveJobs(model, command=command('competitive', fault='hang'), runtime=RUNTIME)
        self.addCleanup(jobs.close)
        jobs.start()
        with self.assertRaisesRegex(ValueError, 'competitive bridge is closed or a match is already running'):
            jobs.start()


if __name__ == '__main__':
    unittest.main()
