"""[designed: T86] Every scenario branch through the real controllers and fake children.

Branches: clock/score/commentary/frames, half-time, result/continuation, draw,
injury, supported decision, extra time, shoot-out, unsupported action,
failure/cancel, stale/duplicate packets and slow completion. Fake children only;
the shared protocol cases that also run against the real backend live in
test_scenario_contract.py.
"""
import copy
import json
import time
import unittest
from pathlib import Path

from goal2.desktop.competitive import CompetitiveJobs
from goal2.desktop.jobs import QuickJobs
from goal2.desktop.match_view import Display
from goal2.desktop.watched import WatchedController
from goal2.engine.original_match import Fixture
from goal2.game.watched_jobs import WatchedJobs
from goal2.game.watched_schema import validate_result
from goal2.scenario import ENGINE, scripts
from goal2.scenario.model import ScenarioModel
from goal2.scenario.runtime import RUNTIME
from goal2.scenario.worker import command


def finish(test, step, limit=20):
    deadline = time.monotonic() + limit
    while time.monotonic() < deadline:
        value = step()
        if value:
            return value
        time.sleep(.01)
    test.fail('fictional child exceeded its deadline')


def at_fixture(n):
    """[designed: T86] A model whose next fixture is original:<n>, reached through the real controllers."""
    model = ScenarioModel()
    for index in range(1, n):
        if index <= 2:
            model.state = scripts.quick_candidate(model.state, model.state.campaign.next_fixture,
                                                  'win' if index == 1 else 'draw')
        else:
            jobs = CompetitiveJobs(model, command=command('competitive'), runtime=RUNTIME)
            token = jobs.start()
            while jobs.busy:
                jobs.poll(token);time.sleep(.01)
            jobs.close()
    assert model.state.campaign.next_fixture.fixture_id == f'original:{n}'
    return model


class QuickBranches(unittest.TestCase):
    def setUp(self):
        self.model = ScenarioModel()

    def job(self, **options):
        job = QuickJobs(self.model, command=command('quick', **options), runtime=RUNTIME)
        self.addCleanup(job.cancel)
        return job

    def test_half_time_injury_supported_decision_and_continuation(self):
        job = self.job();job.start(halftime=True)
        finish(self, lambda: job.poll() is None and job.halftime)
        packet = job.halftime
        self.assertEqual(packet['score'], [0, 0])
        self.assertNotIn(10, packet['available'])  # [designed: T86] scripted 30' injury
        self.assertNotIn(19, packet['available'])  # injured before kick-off
        with self.assertRaisesRegex(ValueError, 'Incoming player is unavailable'):
            job.substitute(10, 19)
        job.substitute(10, 13)
        self.assertEqual(job.halftime['changes'], [[10, 13]])
        job.continue_match()
        with self.assertRaisesRegex(ValueError, 'already used'):
            job.continue_match()
        self.assertTrue(finish(self, job.poll))
        self.assertIsNone(job.poll())
        state = self.model.state
        self.assertEqual((state.match_count, state.last_match['engine']), (1, ENGINE))
        self.assertEqual(state.last_match['substitutions'], [[10, 13]])
        self.assertEqual(state.players[10][14], 0)
        self.assertEqual(self.model.view()['fixture'], 'Southmere — Northmarch (Friendly)')
        with self.assertRaisesRegex(ValueError, 'unavailable starters'):
            self.model.confirm(list(state.starting_eleven), state.captain, 0)

    def test_win_and_draw_results(self):
        for script, score in (('win', [2, 1]), ('draw', [1, 1])):
            with self.subTest(script=script):
                self.model = ScenarioModel()
                job = self.job(script=script);job.start()
                finish(self, job.poll)
                self.assertEqual(self.model.state.last_match['score'], score)
                self.assertEqual(self.model.state.campaign.results[-1]['score'], score)

    def test_slow_completion_publishes_once_only_after_exit(self):
        before = copy.deepcopy(self.model.state)
        job = self.job(fault='slow');job.start()
        polls = 0
        while job.process.poll() is None:
            self.assertIsNone(job.poll());polls += 1
            self.assertEqual(self.model.state, before)
            time.sleep(.01)
        self.assertGreater(polls, 3)
        self.assertTrue(finish(self, job.poll))
        self.assertIsNone(job.poll())
        self.assertEqual(self.model.state.match_count, 1)

    def test_early_output_waits_for_worker_exit(self):
        held = self.model.state
        job = self.job(fault='early');job.start()
        finish(self, lambda: job.output.exists())
        for _ in range(20):
            self.assertIsNone(job.poll())
            time.sleep(.005)
        self.assertIs(self.model.state, held)
        (job.directory / 'release').write_text('go')
        self.assertTrue(finish(self, job.poll))
        self.assertEqual(self.model.state.match_count, 1)

    def test_output_bound_to_another_template_or_count_is_refused(self):
        for fault in ('wrong-template', 'double-count'):
            with self.subTest(fault=fault):
                held = self.model.state
                job = self.job(fault=fault);job.start()
                with self.assertRaisesRegex(ValueError, 'Invalid friendly worker continuation'):
                    finish(self, job.poll)
                self.assertIs(self.model.state, held)
                self.assertFalse(self.model.match_pending)

    def test_bad_half_time_preview_cancels(self):
        held = self.model.state
        job = self.job(fault='bad-halftime');job.start(halftime=True)
        with self.assertRaisesRegex(ValueError, 'Invalid halftime preview: preview fixture changed'):
            finish(self, lambda: job.poll() is None and job.halftime)
        self.assertFalse(job.busy)
        self.assertIs(self.model.state, held)

    def test_stale_half_time_continuation_cancels(self):
        job = self.job();job.start(halftime=True)
        finish(self, lambda: job.poll() is None and job.halftime)
        self.model.state.country_tactics ^= 1
        with self.assertRaisesRegex(ValueError, 'Halftime continuation is stale'):
            job.continue_match()
        self.assertFalse(job.busy)

    def test_cancel_kills_a_child_that_ignores_terminate(self):
        before = copy.deepcopy(self.model.state)
        job = self.job(fault='ignore-term');job.start()
        time.sleep(.2)
        job.cancel()
        self.assertFalse(job.busy)
        self.assertFalse(self.model.match_pending)
        self.assertEqual(self.model.state, before)


class WatchedBranches(unittest.TestCase):
    def setUp(self):
        self.model = at_fixture(2)

    def bridge(self, frames=False, **options):
        jobs = WatchedJobs(self.model, command=command('watched', **options), runtime=RUNTIME)
        self.addCleanup(jobs.close)
        token = jobs.start(Fixture(3, 1, 2), frames=frames)
        return jobs, token

    def run_out(self, jobs, token):
        events = []
        while jobs.busy:
            events += jobs.poll(token)
            time.sleep(.005)
        return events

    def test_clock_score_commentary_half_time_decision_and_draw(self):
        jobs, token = self.bridge()
        events = self.run_out(jobs, token)
        kinds = [e.kind for e in events]
        for kind in ('minute', 'commentary', 'goal', 'decision', 'half_time', 'full_time'):
            self.assertIn(kind, kinds)
        self.assertEqual(kinds[-1], 'end')
        self.assertEqual(sorted(e.minute for e in events), [e.minute for e in events])
        self.assertEqual(next(e for e in events if e.kind == 'decision').data['context'], 'half_time')
        self.assertEqual(list(events[-1].score), [1, 1])
        validate_result(jobs.outcome.result)
        self.assertEqual(jobs.outcome.result['winner'], 2)
        self.assertEqual(self.model.state.last_match['mode'], 'watched')
        self.assertEqual(self.model.state.campaign.next_fixture.fixture_id, 'original:3')

    def test_injury_reaches_the_published_squad(self):
        jobs, token = self.bridge(script='injury')
        events = self.run_out(jobs, token)
        injury = next(e for e in events if e.kind == 'injury')
        self.assertEqual(self.model.state.players[injury.data['player']][14], 0)

    def test_slow_completion_never_publishes_early(self):
        held = self.model.state
        jobs, token = self.bridge(fault='slow')
        polls = 0
        while jobs.process.poll() is None:
            jobs.poll(token);polls += 1
            self.assertIs(self.model.state, held)
            time.sleep(.005)
        self.assertGreater(polls, 3)
        self.run_out(jobs, token)
        self.assertEqual(self.model.state.match_count, 2)

    def test_complete_packet_waits_for_child_exit(self):
        held = self.model.state
        jobs, token = self.bridge(fault='early')
        folder = Path(jobs._folder.name)
        # [derived: T86] _PreparingProcess launches the child on the owner's first poll.
        finish(self, lambda: jobs.poll(token) is not None and (folder / 'ready').exists())
        for _ in range(20):
            jobs.poll(token);time.sleep(.005)
        self.assertTrue(jobs.busy)
        self.assertIs(self.model.state, held)
        (folder / 'release').write_text('go')
        self.run_out(jobs, token)
        self.assertEqual(self.model.state.match_count, 2)

    def test_duplicate_mismatched_or_foreign_completion_is_refused(self):
        for fault, message in (('duplicate', 'identity/order'), ('mismatch', 'differs from live event stream'),
                               ('bad-result', 'differs from the pending fixture')):
            with self.subTest(fault=fault):
                held = self.model.state
                jobs, token = self.bridge(fault=fault)
                with self.assertRaisesRegex(ValueError, message):
                    self.run_out(jobs, token)
                self.assertFalse(jobs.busy)
                self.assertIs(self.model.state, held)
                jobs.close()

    def test_consumed_token_cannot_publish_again(self):
        jobs, token = self.bridge()
        self.run_out(jobs, token)
        published = self.model.state
        with self.assertRaisesRegex(ValueError, 'unknown or consumed watched completion token'):
            jobs.publication.complete(token, jobs.outcome)
        with self.assertRaisesRegex(ValueError, 'stale or consumed watched job token'):
            jobs.poll(token)
        self.assertIs(self.model.state, published)

    def test_frame_acknowledgements_are_cumulative_and_bounded(self):
        jobs, token = self.bridge(frames=True)
        delivered = []
        deadline = time.monotonic() + 20
        while len(delivered) < 3 and time.monotonic() < deadline:
            jobs.poll(token);delivered += jobs.poll_frames(token);time.sleep(.005)
        self.assertGreaterEqual(len(delivered), 3)
        jobs.ack_frames(token, 1)
        for sequence in (1, 0, len(delivered) + 50):
            with self.subTest(sequence=sequence), self.assertRaisesRegex(ValueError, 'stale or invalid pitch'):
                jobs.ack_frames(token, sequence)


class ControllerBranches(unittest.TestCase):
    def setUp(self):
        self.model = at_fixture(2)

    def controller(self, fault=None):
        watch = WatchedController(self.model, engine_command=command('watched'),
                                  viewer_command=command('viewer', fault=fault), runtime=RUNTIME)
        self.addCleanup(watch.close)
        return watch

    def test_frames_are_rendered_acknowledged_and_completion_shown(self):
        watch = self.controller();watch.start()
        self.assertTrue(finish(self, watch.poll))
        result = watch.engine.outcome.result
        self.assertEqual(watch.frame_ack, result['ticks'] - 1)
        self.assertEqual(set(watch.display.result), {'board', 'ratings', 'man_of_the_match'})
        lines = watch.display.lines()
        self.assertIn('1 min Kick-off: Southmere against Northmarch (fictional scenario)', lines)
        self.assertIn(f"Man of the match: {result['man_of_the_match_name']}", lines)
        self.assertFalse(self.model.match_pending)

    def test_viewer_status_faults_cancel_without_publication(self):
        for fault, frames, message in (('stale-token', True, 'malformed or stale viewer status'),
                                       ('regress', False, 'stale viewer acknowledgement'),
                                       ('crash', True, 'Pygame window exited')):
            with self.subTest(fault=fault):
                held = self.model.state
                watch = self.controller(fault);watch.start(frames=frames)
                with self.assertRaisesRegex(ValueError, message):
                    finish(self, watch.poll)
                self.assertFalse(watch.busy)
                self.assertFalse(self.model.match_pending)
                self.assertIs(self.model.state, held)
                watch.close()

    def test_unacknowledged_frames_block_publication_until_cancel(self):
        held = self.model.state
        watch = self.controller('no-ack');watch.start()
        deadline = time.monotonic() + 1.5
        while time.monotonic() < deadline:
            self.assertFalse(watch.poll());time.sleep(.01)
        self.assertTrue(watch.engine.engine_complete or watch.busy)
        self.assertIs(self.model.state, held)
        watch.cancel()
        self.assertFalse(self.model.match_pending)
        self.assertIs(self.model.state, held)

    def test_viewer_close_cancels_the_match(self):
        held = self.model.state
        watch = self.controller('close');watch.start(frames=False)
        finish(self, lambda: watch.poll() is False and not watch.busy)
        self.assertFalse(self.model.match_pending)
        self.assertIs(self.model.state, held)

    def test_display_refuses_wrong_token_and_out_of_order_packets(self):
        display = Display('t' * 48)
        for packet in (['x' * 48, 0, 'start', ['A', 'B']], ['t' * 48, 1, 'start', ['A', 'B']]):
            with self.subTest(packet=packet), self.assertRaisesRegex(ValueError, 'stale or out-of-order'):
                display.accept(packet)
        display.accept(['t' * 48, 0, 'start', ['A', 'B']])
        with self.assertRaisesRegex(ValueError, 'stale or out-of-order'):
            display.accept(['t' * 48, 0, 'event', {'kind': 'minute', 'minute': 1, 'score': [0, 0], 'data': {}}])


class CompetitiveBranches(unittest.TestCase):
    def play(self, model, script=None):
        jobs = CompetitiveJobs(model, command=command('competitive', script=script), runtime=RUNTIME)
        self.addCleanup(jobs.close)
        token = jobs.start()
        while jobs.busy:
            jobs.poll(token);time.sleep(.005)
        return jobs.outcome.result

    def test_regulation_extra_time_and_shoot_out(self):
        model = at_fixture(3)
        self.play(model)
        self.assertEqual(model.state.last_match['resolution']['regulation'], [2, 0])
        self.assertIsNone(model.state.last_match['resolution']['extra_time'])
        for script, stages in (('extra_time', {'regulation': [1, 1], 'extra_time': [1, 2], 'penalties': None, 'winner': 1}),
                               ('shootout', {'regulation': [0, 0], 'extra_time': [1, 1], 'penalties': [3, 4], 'winner': 1})):
            with self.subTest(script=script):
                model = at_fixture(4)
                result = self.play(model, script)
                validate_result(result, competitive=True)
                resolution = model.state.last_match['resolution']
                self.assertEqual({k: resolution[k] for k in stages}, stages)
                self.assertEqual(model.state.campaign.next_fixture.fixture_id, 'original:5')
                self.assertIn('Winner: Northmarch', model.result_text())

    def test_unsupported_actions_are_refused_and_named(self):
        model = at_fixture(3)
        with self.assertRaisesRegex(ValueError, 'Watch supports scheduled friendlies only'):
            WatchedController(model, engine_command=command('watched'), viewer_command=command('viewer'),
                              runtime=RUNTIME).start()
        del model._watched_jobs
        with self.assertRaisesRegex(ValueError, 'Quick supports scheduled friendlies only'):
            QuickJobs(model, command=command('quick'), runtime=RUNTIME).start()
        friendly = ScenarioModel()
        with self.assertRaisesRegex(ValueError, 'No supported pending competitive fixture'):
            CompetitiveJobs(friendly, command=command('competitive'), runtime=RUNTIME).start()
        model = at_fixture(5)
        self.assertEqual(model.view()['play_label'], 'Play unavailable')
        with self.assertRaisesRegex(ValueError, 'No supported pending competitive fixture'):
            CompetitiveJobs(model, command=command('competitive'), runtime=RUNTIME).start()
        self.assertFalse(model.match_pending)


if __name__ == '__main__':
    unittest.main()
