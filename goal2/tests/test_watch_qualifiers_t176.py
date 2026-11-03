"""[designed: owner decision 1, #526; T176] The managed country's qualifiers are watched, as its friendlies are.

A watched qualifier is the `competitive` match on the owner's engine process (goal2.game.engine_server, T159/T160)
with the pitch samples and the bench, started by goal2.desktop.watched.WatchedController on the owner's
CompetitiveJobs bridge (the one competitive Play uses) and published by its CompetitivePublication. Each case plays
the match twice: through the controller, and with `_drive_match` on `prepare_competitive` in a PyPy child
(goal2.tests.pypy_engine.drive), on the state the publication prepares, with the same options and answers.

The substitution budget of a competition match is the rebuild's: five a side, `substitutions=(5, 5)`, which the
engine server passes for every competitive match [designed: owner BM-7, #73, 2026-10-15, retained 2026-10-24;
docs/assumptions.md BM-7]. The original's own is five in a friendly and two in any other kind [confirmed: F027 §4,
A4A1, as the vendored kit's Match docstring cites it; GOAL.HLP and E031 C41, docs/original-game/match-and-results.md];
the rebuild's rule overrides it for competition matches (docs/competitive-matches.md).

The game is test_matches_on_pipe_t160.other_game(): a campaign of the reference image, Denmark (7) managed, its next
fixture the qualifier original:21 against country 19 (kind 2). The friendly case plays the next friendly of the
E010-r0008 half-time save as before. The pygame viewer is not this task's: a child that shows nothing stands in for it,
and the test reads and acknowledges the samples itself, as the viewer would.
"""
import copy
from dataclasses import asdict
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import time
import unittest

from goal2.tests import requires

ROOT = Path(__file__).resolve().parents[2]
WAIT = 900                       # seconds for a whole match under PyPy on a loaded runner
VIEWER = [sys.executable, '-c', 'import time;time.sleep(900)']
OPTIONS = dict(delay_byte=0, record_draws=True)       # the controller's options (WatchedController.start)
BUDGET = (5, 5)                                       # the engine server's competitive budget (BM-7)


def digest(value):
    """A value as the pipe carries it (tuples as lists), hashed."""
    data = json.dumps(value, sort_keys=True, separators=(',', ':'), default=list)
    return hashlib.sha256(data.encode()).hexdigest()


def plain(value):
    return json.loads(json.dumps(value, sort_keys=True, default=list))


def choose(mode, data):
    """The answers of a case (test_watched_bench_t102.choose): outfield starters off for outfield bench players."""
    from goal2.tests.test_watched_bench_t102 import choose as bench_choose
    return bench_choose(mode, data)


class Answers:
    """The bench's answers for `_drive_match` in the child (its `policy`): the same as the test gives the
    controller's bench; no Enter in play."""

    def __init__(self, mode):
        self.mode = mode

    def decide(self, event):
        return choose(self.mode, event.data)

    def pause_now(self, sequence):
        return False

    def pause_dropped(self, sequence):
        pass

    def answered(self, report):
        pass


class Samples:
    """The pitch samples `_drive_match` takes in the child, as digests."""

    def __init__(self):
        self.digests = []

    def __call__(self, frame):
        self.digests.append(digest(frame))


def desktop_model(folder, name, game=None):
    """A desktop model on the half-time save; with `game` (state, template) the game is that one, as Resume would
    load it (test_matches_on_pipe_t160)."""
    from goal2.desktop.model import DesktopModel
    model = DesktopModel.open(ROOT / '.cache/e010-r0008-halftime.sav', ROOT / '.cache/GOAL.DAT',
                              Path(folder) / f'{name}.g2save', country=4)
    if game is not None:
        model.state, model.template_bytes = copy.deepcopy(game[0]), bytes(game[1])
    return model


def play(controller, mode):
    """Play the controller's started match to its publication, as the window's viewer and bench would: read every
    event and sample, acknowledge each sample, answer each bench decision by `mode`."""
    jobs, token = controller.engine, controller.engine_token
    events, samples, decisions = [], [], []
    ack = -1
    deadline = time.monotonic() + WAIT
    while True:
        if time.monotonic() > deadline:
            raise AssertionError('the watched match did not finish')
        events.extend(jobs.poll(token))
        if not jobs.busy:
            break
        samples.extend(digest(frame) for frame in jobs.poll_frames(token))
        if not jobs.busy:
            break
        received = jobs._frame_sequence - 1
        if received > ack:
            jobs.ack_frames(token, received)
            ack = received
        if jobs.waiting is not None:
            decisions.append(copy.deepcopy(jobs.waiting))
            jobs.answer(token, choose(mode, jobs.waiting.data))
        time.sleep(.003)
    return {'events': events, 'samples': samples, 'decisions': decisions, 'reports': list(jobs.reports),
            'outcome': jobs.outcome}


def reference(owner, fixture, mode, *, competitive):
    """`_drive_match` in a PyPy child on the state the publication prepares (the engine plays that state), with
    the controller's options and the same answers. Returns the pending child and the publication's job."""
    from goal2.game.watched_publication import CompetitivePublication, WatchedPublication
    from goal2.tests import pypy_engine
    publication = (CompetitivePublication if competitive else WatchedPublication)(owner)
    job = publication.begin(fixture)
    extra = {'substitutions': BUDGET} if competitive else {}
    pending = pypy_engine.start('goal2.tests.pypy_engine:drive', copy.deepcopy(job.state), bytes(owner.template_bytes),
                                fixture, observer=Samples(), competitive=competitive, policy=Answers(mode),
                                **extra, **OPTIONS)
    return pending, publication, job


@requires.need(modules=('pygame',), files=(requires.WATCHED['files'][0], 'GOAL.DAT', 'e010-r0008-halftime.sav'))
class WatchQualifiers(unittest.TestCase):
    """The cases, played once for the class, one at a time (two PyPy processes at once: the engine and the child)."""

    @classmethod
    def setUpClass(cls):
        from goal2.desktop.competitive import CompetitiveJobs, pending_fixture
        from goal2.desktop.watched import WatchedController
        from goal2.tests.test_matches_on_pipe_t160 import other_game
        cls.folder = tempfile.TemporaryDirectory()
        folder = cls.folder.name
        cls.game = other_game()
        cls.fixture = pending_fixture(cls.game[0])
        cls.out = {}
        closing = []
        try:
            # A watched qualifier: the owner holds a competitive bridge (as the window does) before the controller
            # starts; a second watched qualifier on an owner without one; and competitive Play.
            for mode in ('none', 'half1', 'half6'):
                model = desktop_model(folder, mode, cls.game)
                window_bridge = CompetitiveJobs(model) if mode == 'none' else None
                controller = WatchedController(model, viewer_command=VIEWER)
                closing += [controller] + ([window_bridge] if window_bridge else [])
                before = copy.deepcopy(model.state)
                child, publication, job = reference(desktop_model(folder, f'{mode}-reference', cls.game),
                                                    cls.fixture, mode, competitive=True)
                controller.start()
                bridge = controller.engine
                case = dict(play(controller, mode), before=before, model=model, bridge=bridge,
                            window_bridge=window_bridge, friendly_engine=controller.friendly_engine,
                            kind=bridge.KIND, pending_after=model.match_pending)
                drive, samples, _ = child.result(WAIT)
                case['reference'] = {'outcome': drive, 'samples': samples.digests}
                if mode == 'none':
                    publication.complete(job.token, drive)
                    case['reference']['state'] = publication.owner.state
                controller.cancel()                           # the viewer stand-in, as the window's poll would
                cls.out[mode] = case

            # Competitive Play (no pitch, no bench) of the same game, with the same options.
            model = desktop_model(folder, 'play', cls.game)
            jobs = CompetitiveJobs(model)
            closing.append(jobs)
            token = jobs.start(**OPTIONS)
            deadline = time.monotonic() + WAIT
            while jobs.busy:
                if time.monotonic() > deadline:
                    raise AssertionError('competitive Play did not finish')
                jobs.poll(token)
                time.sleep(.005)
            cls.out['play'] = {'outcome': jobs.outcome, 'model': model}

            # A watched friendly, as before: the friendly bridge, the friendly publication.
            model = desktop_model(folder, 'friendly')
            controller = WatchedController(model, viewer_command=VIEWER)
            closing.append(controller)
            pending = model.state.campaign.next_fixture
            from goal2.engine.original_match import Fixture
            fixture = Fixture(pending.side_a, pending.side_b, int(pending.fixture_id.split(':')[1]))
            before = copy.deepcopy(model.state)
            child, publication, job = reference(desktop_model(folder, 'friendly-reference'), fixture, 'none',
                                                competitive=False)
            controller.start()
            case = dict(play(controller, 'none'), before=before, model=model, bridge=controller.engine,
                        friendly_engine=controller.friendly_engine, kind=controller.engine.KIND)
            drive, samples, _ = child.result(WAIT)
            publication.complete(job.token, drive)
            case['reference'] = {'outcome': drive, 'samples': samples.digests, 'state': publication.owner.state}
            controller.cancel()
            cls.out['friendly'] = case
        finally:
            for item in reversed(closing):
                try:
                    item.close()
                except Exception:                           # noqa: BLE001 - the cases report the failure
                    pass

    @classmethod
    def tearDownClass(cls):
        cls.folder.cleanup()

    def same(self, mode):
        """The controller's match equals `_drive_match`'s: events, pitch samples, result, memory and seeds."""
        case = self.out[mode]
        outcome, want = case['outcome'], case['reference']['outcome']
        self.assertIsNotNone(outcome, f'{mode}: the watched match was not published')
        self.assertEqual(plain([asdict(e) for e in case['events']]), plain([asdict(e) for e in want.events]))
        self.assertEqual(plain([asdict(e) for e in outcome.events]), plain([asdict(e) for e in want.events]))
        self.assertEqual(case['samples'], case['reference']['samples'])
        self.assertEqual(len(case['samples']), want.result['ticks'])
        self.assertEqual(plain(outcome.result), plain(want.result))
        self.assertEqual(bytes(outcome.memory), bytes(want.memory))
        self.assertEqual(tuple(outcome.seeds), tuple(want.seeds))
        return case, outcome

    def managed(self, case, outcome):
        side = int(case['before'].managed_country == self.fixture.second)
        return [[e.data['off'], e.data['on']] for e in outcome.events
                if e.kind == 'substitution' and e.data['team'] == side]

    # --- the same match ---------------------------------------------------------------------------------------

    def test_a_watched_qualifier_is_the_competitive_match_on_the_owner_s_bridge(self):
        from goal2.desktop.competitive import CompetitiveJobs
        for mode in ('none', 'half1', 'half6'):
            with self.subTest(mode=mode):
                case = self.out[mode]
                self.assertIsInstance(case['bridge'], CompetitiveJobs)
                self.assertEqual(case['kind'], 'competitive')
                self.assertIsNot(case['bridge'], case['friendly_engine'])
                self.assertTrue(case['decisions'], 'the bench was never asked')
        # The owner's bridge, the window's competitive Play one, when it has one.
        self.assertIs(self.out['none']['bridge'], self.out['none']['window_bridge'])

    def test_played_with_default_answers_it_equals_drive_match_on_prepare_competitive(self):
        case, outcome = self.same('none')
        self.assertEqual(outcome.events[-1].kind, 'end')
        self.assertEqual(case['reports'], [])
        self.assertEqual(self.managed(case, outcome), [])

    def test_its_published_campaign_state_equals_drive_match_s_and_competitive_play_s(self):
        from goal2.game.watched_schema import COMPETITIVE_SCHEMA
        case, _ = self.same('none')
        state = case['model'].state
        self.assertEqual(state.match_count, case['before'].match_count + 1)   # published once
        self.assertEqual(state.last_match['schema'], COMPETITIVE_SCHEMA)       # by the competitive publication
        self.assertEqual(state, case['reference']['state'])
        play = self.out['play']
        self.assertEqual(plain([asdict(e) for e in play['outcome'].events]),
                         plain([asdict(e) for e in case['outcome'].events]))
        self.assertEqual(state, play['model'].state)
        self.assertFalse(case['pending_after'])

    # --- the bench ----------------------------------------------------------------------------------------------

    def test_one_substitution_at_half_time_equals_the_same_answer_through_drive(self):
        case, outcome = self.same('half1')
        half = [d for d in case['decisions'] if d.data['context'] == 'half_time']
        self.assertEqual(len(half), 1)
        pair = choose('half1', half[0].data)
        self.assertEqual(len(pair), 1)
        self.assertEqual(self.managed(case, outcome), pair)
        self.assertEqual(case['reports'][0]['made'], pair)
        self.assertEqual(case['reports'][0]['refused'], [])
        self.assertEqual(case['model'].state.match_count, case['before'].match_count + 1)

    def test_the_bench_offers_the_competition_budget_and_refuses_one_more(self):
        from goal2.game.watched_match import NO_MORE_SUBSTITUTES
        case, outcome = self.same('half6')
        limit = BUDGET[case['before'].managed_country == self.fixture.second]
        half = [d for d in case['decisions'] if d.data['context'] == 'half_time'][0]
        self.assertEqual(half.data['substitutions_left'], limit)
        asked = choose('half6', half.data)
        self.assertEqual(len(asked), limit + 1)
        self.assertEqual(self.managed(case, outcome), asked[:limit])
        report = case['reports'][0]
        self.assertEqual(report['made'], asked[:limit])
        self.assertEqual(report['refused'], [asked[limit] + [NO_MORE_SUBSTITUTES]])
        self.assertEqual(report['substitutions_left'], 0)

    # --- friendlies unchanged -------------------------------------------------------------------------------

    def test_a_watched_friendly_still_plays_and_publishes_as_before(self):
        from goal2.game.watched_jobs import WatchedJobs
        from goal2.game.watched_schema import COMPETITIVE_SCHEMA
        case, outcome = self.same('friendly')
        self.assertIs(case['bridge'], case['friendly_engine'])
        self.assertIs(type(case['bridge']), WatchedJobs)
        self.assertEqual(case['kind'], 'watched')
        state = case['model'].state
        self.assertEqual(state.match_count, case['before'].match_count + 1)
        self.assertNotEqual(state.last_match.get('schema'), COMPETITIVE_SCHEMA)
        self.assertEqual(state, case['reference']['state'])


class Boundary(unittest.TestCase):
    """Which fixtures Watch takes, without an engine."""

    def controller(self, kind, fixture_id='original:21'):
        from types import SimpleNamespace
        from unittest.mock import patch
        from goal2.desktop import watched
        scheduled = SimpleNamespace(kind=kind, fixture_id=fixture_id, side_a=7, side_b=19)
        model = SimpleNamespace(state=SimpleNamespace(campaign=SimpleNamespace(next_fixture=scheduled)))
        with patch.object(watched, 'WatchedJobs'):
            return watched.WatchedController(model), scheduled

    def test_watch_takes_a_scheduled_qualifier_and_refuses_an_unsupported_kind(self):
        controller, scheduled = self.controller(2)
        self.assertIs(controller.fixture(), scheduled)
        controller, scheduled = self.controller(1)
        self.assertIs(controller.fixture(), scheduled)
        for kind, fixture_id in ((255, 'original:21'), (2, 'drawn:3')):
            with self.subTest(kind=kind, fixture_id=fixture_id):
                controller, _ = self.controller(kind, fixture_id)
                with self.assertRaisesRegex(ValueError, 'scheduled friendlies and supported qualifiers only'):
                    controller.fixture()


if __name__ == '__main__':
    unittest.main()
