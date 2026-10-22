"""[designed: T102] The bench in a watched match, proven against the vendored engine.

Each engine case plays the next scheduled friendly of a new campaign from the E010-r0008 template
(country 4) twice: through the worker and its parent (WatchedJobs with the bench and the pitch
samples), and with the vendored Match called directly on an independently written image
(test_watched_adapter.direct_image), the same seed and the same answers. The engine cases run in
parallel processes; the bench view is checked on the window with a stub controller.
"""
from concurrent.futures import ProcessPoolExecutor
import copy
from dataclasses import asdict
import hashlib
from pathlib import Path
import struct
import tempfile
import time
import unittest

from goal2.tests import requires

ROOT = Path(__file__).resolve().parents[2]
# [designed: T102] The pause case: the Enter reaches the worker while it waits to write sample
# PAUSE_FRAME + 1, so the original takes it after that sample.
PAUSE_FRAME = 300


def model(path):
    from goal2.desktop.model import DesktopModel
    return DesktopModel.open(ROOT / '.cache/e010-r0008-halftime.sav', ROOT / '.cache/GOAL.DAT', path, country=4)


def fixture_of(state):
    from goal2.engine.original_match import Fixture
    pending = state.campaign.next_fixture
    return Fixture(pending.side_a, pending.side_b, int(pending.fixture_id.split(':')[1]))


def choose(mode, data):
    """The answers of a case, from the decision's own data: outfield starters for outfield bench
    players, in squad order (keepers would make the original refuse the eleven)."""
    positions = dict(map(tuple, data['positions']))
    starters = [w for w in data['eleven'] if positions[w] != 0]
    bench = [w for w in data['bench'] if positions[w] != 0]
    count = {'half1': 1, 'half6': 6}.get(mode)
    if count and data['context'] == 'half_time':
        return [[a, b] for a, b in zip(starters[1:], bench)][:count]
    if mode == 'pause' and data['context'] == 'pause':
        return [[starters[4], bench[0]]]
    return []


def reference(mode, state, fixture, pause_after=None):
    """The vendored Match called directly: the same seed (none), delay byte and answers; `answer()`
    with nothing given when the answer is empty; `pause()` after sample `pause_after`."""
    from goal2.engine.original_match import Match, screens
    from goal2.tests.test_watched_adapter import direct_image
    match = Match(direct_image(state), fixture, managed=state.managed_country, captain=state.captain or None,
                  record_draws=True, delay_byte=0)
    match.opts['ticks'] = True
    events, ticks, decisions = [], 0, 0
    for ev in match.events():
        if ev.kind == 'tick':
            ticks += 1
            if pause_after is not None and ticks == pause_after + 1:
                match.pause()
            continue
        events.append(asdict(ev))
        if ev.kind == 'decision':
            decisions += 1
            if decisions > 30:
                raise RuntimeError('reference decisions do not progress')
            pairs = choose(mode, ev.data)
            match.answer(substitutions=pairs) if pairs else match.answer()
    left = match.m.rd(screens.SUBS_LEFT + match.side, 1)
    return {'result': match.result(), 'memory': hashlib.sha256(match.memory_component()).hexdigest(),
            'events': events, 'substitutions_left': left}


def default(state, original, fixture):
    """Today's play-on default: run_watched_match."""
    from goal2.game.watched_match import run_watched_match
    outcome = run_watched_match(state, original, fixture, delay_byte=0, record_draws=True)
    return {'result': outcome.result, 'memory': hashlib.sha256(outcome.memory).hexdigest(),
            'events': [asdict(e) for e in outcome.events]}


class Job:
    """One worker run through its parent, answering by `mode`; it acknowledges pitch samples as a
    viewer would, holds them for the pause case, and records the pacing it observes."""

    def __init__(self, mode, folder):
        from goal2.game.watched_jobs import WatchedJobs
        self.mode = mode
        self.model = model(Path(folder) / f'{mode}.g2save')
        self.before = copy.deepcopy(self.model.state)
        self.fixture = fixture_of(self.model.state)
        self.jobs = WatchedJobs(self.model)
        self.token = self.jobs.start(self.fixture, delay_byte=0, record_draws=True, frames=True, bench=True)
        self.events, self.decisions = [], []
        self.ack = -1
        self.offset, self.written = 0, 0
        self.worst = 0
        self.paused = mode != 'pause'
        self.held = None

    def count_written(self):
        """Samples the worker has written, read from its frames journal."""
        path = Path(self.jobs._frames.name)
        with path.open('rb') as stream:
            stream.seek(self.offset)
            data = stream.read()
        position = 0
        while len(data) - position >= 4:
            size = struct.unpack('!I', data[position:position + 4])[0]
            if len(data) - position < size + 4:
                break
            position += size + 4;self.written += 1
        self.offset += position

    def step(self):
        from goal2.game.watched_jobs import LEAD
        jobs, token = self.jobs, self.token
        self.events.extend(jobs.poll(token))
        if not jobs.busy:
            return False
        jobs.poll_frames(token)
        if not jobs.busy:
            # The last poll published the match and released the job's folder.
            return False
        self.count_written()
        self.worst = max(self.worst, self.written - 1 - self.ack)
        received = jobs._frame_sequence - 1
        limit = received if self.paused else min(received, PAUSE_FRAME - LEAD)
        if not self.paused and self.written - 1 == PAUSE_FRAME:
            # The worker waits for an acknowledgement before sample PAUSE_FRAME + 1: it stays there.
            if self.held is None:
                self.held = time.monotonic()
            elif time.monotonic() - self.held > 1:
                self.blocked = self.written
                jobs.pause(token);self.paused = True
        if limit > self.ack:
            jobs.ack_frames(token, limit);self.ack = limit
        if jobs.waiting is not None:
            self.decisions.append(copy.deepcopy(jobs.waiting))
            jobs.answer(token, choose(self.mode, jobs.waiting.data))
        return True


@requires.need(modules=('unicorn',), files=(*requires.WATCHED['files'], 'GOAL.DAT', 'e010-r0008-halftime.sav'))
class EngineCases(unittest.TestCase):
    """The engine cases, played once for the class: half1, half6 and pause through the worker and
    directly, none through the worker and run_watched_match."""

    @classmethod
    def setUpClass(cls):
        from goal2.game import campaign_rounds
        from goal2.game.watched_jobs import LEAD
        cls.folder = tempfile.TemporaryDirectory()
        modes = ('half1', 'half6', 'pause', 'none')
        jobs = {mode: Job(mode, cls.folder.name) for mode in modes}
        with ProcessPoolExecutor(4) as pool:
            futures = {}
            for mode, job in jobs.items():
                # The state the worker plays: the round prepared as WatchedPublication.begin does.
                state = campaign_rounds.prepare(job.before, job.model.template_bytes, competitive=False)
                if mode == 'none':
                    futures[mode] = pool.submit(default, state, job.model.template_bytes, job.fixture)
                else:
                    futures[mode] = pool.submit(reference, mode, state, job.fixture,
                                                PAUSE_FRAME + 1 if mode == 'pause' else None)
            deadline = time.monotonic() + 900
            running = dict(jobs)
            while running:
                if time.monotonic() > deadline:
                    raise AssertionError('watched bench jobs did not finish')
                for mode in list(running):
                    if not running[mode].step():
                        del running[mode]
                time.sleep(.003)
            cls.references = {mode: future.result() for mode, future in futures.items()}
        cls.jobs = jobs
        cls.lead = LEAD

    @classmethod
    def tearDownClass(cls):
        for job in getattr(cls, 'jobs', {}).values():
            job.jobs.close()
        cls.folder.cleanup()

    def same(self, mode):
        job, want = self.jobs[mode], self.references[mode]
        outcome = job.jobs.outcome
        self.assertIsNotNone(outcome, mode)
        self.assertEqual([asdict(e) for e in outcome.events], want['events'])
        self.assertEqual(outcome.result, want['result'])
        self.assertEqual(hashlib.sha256(outcome.memory).hexdigest(), want['memory'])
        return job, outcome

    def managed(self, job, outcome):
        side = int(job.before.managed_country == job.fixture.second)
        return [[e.data['off'], e.data['on']] for e in outcome.events
                if e.kind == 'substitution' and e.data['team'] == side]

    def test_half_time_substitution_is_seed_exact(self):
        job, outcome = self.same('half1')
        half = [d for d in job.decisions if d.data['context'] == 'half_time']
        self.assertEqual(len(half), 1)
        pair = choose('half1', half[0].data)
        self.assertEqual(self.managed(job, outcome), pair)
        self.assertEqual(job.jobs.reports[0]['made'], pair)
        self.assertEqual(job.jobs.reports[0]['refused'], [])

    def test_mid_play_pause_then_substitution_at_the_next_stoppage(self):
        job, outcome = self.same('pause')
        self.assertEqual(job.blocked, PAUSE_FRAME + 1, 'the worker ran past the held acknowledgement')
        contexts = [d.data['context'] for d in job.decisions]
        self.assertEqual(contexts[:2], ['pause', 'substitution'])
        pause, stoppage = job.decisions[:2]
        pair = choose('pause', pause.data)
        self.assertEqual(stoppage.data['requested'], pair)
        self.assertGreater(stoppage.minute, pause.minute)
        self.assertEqual(job.jobs.reports[0]['requested'], pair)
        self.assertEqual(self.managed(job, outcome), pair)
        made = next(e for e in outcome.events if e.kind == 'substitution' and [e.data['off'], e.data['on']] == pair[0])
        self.assertEqual(made.minute, stoppage.minute)

    def test_five_substitutions_then_no_more_substitutes(self):
        job, outcome = self.same('half6')
        asked = choose('half6', [d for d in job.decisions if d.data['context'] == 'half_time'][0].data)
        self.assertEqual(len(asked), 6)
        self.assertEqual(self.managed(job, outcome), asked[:5])
        report = job.jobs.reports[0]
        self.assertEqual(report['made'], asked[:5])
        from goal2.game.watched_match import NO_MORE_SUBSTITUTES
        self.assertEqual(report['refused'], [asked[5] + [NO_MORE_SUBSTITUTES]])
        self.assertEqual(report['substitutions_left'], 0)
        self.assertEqual(self.references['half6']['substitutions_left'], 0)

    def test_play_on_equals_the_default_byte_for_byte(self):
        job, outcome = self.same('none')
        self.assertTrue(job.decisions, 'the bench was never asked')
        self.assertEqual(job.jobs.reports, [])

    def test_pacing_never_exceeds_the_lead(self):
        for mode, job in self.jobs.items():
            with self.subTest(mode=mode):
                self.assertLessEqual(job.worst, self.lead)
        self.assertEqual(self.jobs['pause'].worst, self.lead, 'the held case reaches the lead exactly')

    def test_the_substitute_stays_in_the_published_eleven(self):
        for mode in ('half1', 'half6', 'pause'):
            with self.subTest(mode=mode):
                job = self.jobs[mode];state = job.model.state
                swaps = self.managed(job, job.jobs.outcome)
                self.assertEqual(state.match_count, job.before.match_count + 1)
                for off, on in swaps:
                    self.assertIn(on, state.managed_squad[:11])
                    self.assertIn(on, state.starting_eleven)
                    self.assertNotIn(off, state.starting_eleven)
                self.assertEqual(set(state.starting_eleven), set(state.managed_squad[:11]))
        job = self.jobs['none']
        self.assertEqual(job.model.state.starting_eleven, job.before.starting_eleven)


@requires.need(**requires.WATCHED)
class CancelWhileWaiting(unittest.TestCase):
    def test_a_worker_waiting_for_the_bench_is_cancelled_within_the_contract(self):
        """[designed: #254, #311] A worker blocked on a bench answer still ends by cancel_and_reap."""
        import sys
        from goal2.engine.original_match import Fixture
        from goal2.game.watched_jobs import WatchedJobs
        from goal2.tests import test_watched_adapter as adapter
        from goal2.tests.test_watched_jobs import CONTROLLED
        from goal2.tests.test_watched_publication import Owner
        adapter.WatchedAdapter.setUpClass();self.raw = adapter.WatchedAdapter.raw
        owner = Owner(adapter.WatchedAdapter.state(self), self.raw)
        before = copy.deepcopy(owner.state)
        jobs = WatchedJobs(owner, command=[sys.executable, '-c', CONTROLLED, 'blocked'])
        try:
            token = jobs.start(Fixture(7, 19, 21), bench=True)
            deadline = time.monotonic() + 60
            while jobs.waiting is None:
                self.assertLess(time.monotonic(), deadline, 'the bench decision never arrived')
                jobs.poll(token);time.sleep(.01)
            process = jobs.process;time.sleep(.5)
            self.assertIsNone(process.poll(), 'the worker should be waiting for the answer')
            started = time.monotonic();jobs.cancel_and_reap(token)
            self.assertLess(time.monotonic() - started, 2)
            self.assertIsNotNone(process.poll());self.assertFalse(jobs.busy)
            self.assertEqual(owner.state, before)
        finally:
            jobs.close()


class PitchFreeze(unittest.TestCase):
    def test_the_view_freezes_on_a_decision_once_its_samples_are_shown(self):
        from goal2.desktop.match_view import Display
        from goal2.tests.test_pygame_pitch_view import sample
        d = Display('owned');d.accept(['owned', 0, 'start', ['Bulgaria', 'Albania']])
        d.accept(['owned', 1, 'pitch', {'rate': 60}])
        d.accept(['owned', 2, 'event', {'kind': 'commentary', 'minute': 45, 'score': [0, 0], 'data': {'text': 'x'}}])
        d.accept(['owned', 3, 'frame', sample(0, 1)])
        d.accept(['owned', 4, 'event', {'kind': 'half_time', 'minute': 46, 'score': [0, 0], 'data': {}}])
        d.accept(['owned', 5, 'event', {'kind': 'decision', 'minute': 46, 'score': [0, 0], 'data': {'context': 'half_time'}}])
        self.assertIsNone(d.board(), 'a sample before the decision is still to be shown')
        d.advance(0.0)
        self.assertEqual(d.board(), 'HALF TIME')
        # The causal watermark still holds: the board is drawn over the frozen sample.
        self.assertEqual(len(d.visible().events), 1)
        d.accept(['owned', 6, 'frame', sample(1, 3)])
        self.assertIsNone(d.board(), 'the answer resumes play')


@requires.need(modules=('pygame', 'PySide6'), files=('GOAL.DAT', 'e010-r0008-halftime.sav'))
class EnterInPlay(unittest.TestCase):
    def test_each_enter_in_the_status_asks_the_original_once(self):
        """The viewer's Enter count reaches the parent, which asks the engine to pause when it grows."""
        import json, sys
        from unittest.mock import patch
        from goal2.desktop.watched import WatchedController
        sleep = [sys.executable, '-c', 'import time;time.sleep(60)']
        with tempfile.TemporaryDirectory() as folder:
            m = model(Path(folder) / 'save')
            c = WatchedController(m, engine_command=sleep, viewer_command=sleep)
            try:
                c.start()
                self.assertTrue(c.engine._bench, 'the pitch route has the bench')
                status = lambda n: json.dumps({'token': c.token, 'kind': 'ready', 'sequence': c.display.sequence,
                                              'digest': c.display.digest(), 'frame_sequence': -1,
                                              'frame_digest': None, 'requests': n})
                with patch.object(c.engine, 'poll', return_value=[]), patch.object(c.engine, 'poll_frames', return_value=[]), \
                        patch.object(c.engine, 'pause') as pause:
                    for n in (0, 1, 1, 3):
                        (c.directory / 'status').write_text(status(n));c.poll()
                    self.assertEqual(pause.call_count, 2)
                    (c.directory / 'status').write_text(status(2))
                    with self.assertRaisesRegex(ValueError, 'bench request'):c.poll()
            finally:
                c.close()


class StubWatched:
    """The window's watched controller, reduced to the bench's channel."""
    def __init__(self, decision):
        self.decision = decision;self.busy = True;self.reports = [];self.answers = []

    def answer(self, pairs):
        self.answers.append([list(p) for p in pairs]);self.decision = None

    def poll(self):
        return False

    def cancel(self):
        self.busy = False

    def close(self):
        self.busy = False


@requires.need(modules=('PySide6',), files=('GOAL.DAT', 'e010-r0008-halftime.sav'))
class BenchView(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from PySide6.QtWidgets import QApplication
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        from goal2.desktop.window import ManagementWindow
        from goal2.engine.original_match.match import Event
        self.folder = tempfile.TemporaryDirectory()
        self.model = model(Path(self.folder.name) / 'bench.g2save')
        self.window = ManagementWindow(self.model);self.window.show();self.app.processEvents()
        state = self.model.state
        self.eleven = list(state.starting_eleven)
        self.bench = [w for w in state.managed_squad if w not in self.eleven]
        self.decision = Event('decision', 46, (1, 0), {
            'substitutions_now': True, 'refused': None, 'context': 'half_time', 'eleven': self.eleven,
            'bench': self.bench, 'injured': [self.eleven[3]], 'positions': [], 'substitutions_left': 5,
            'tactics': state.country_tactics})
        self.real = self.window.watched
        self.stub = self.window.watched = StubWatched(self.decision)

    def tearDown(self):
        self.window.watched = self.real
        self.window.close();self.window.deleteLater();self.app.processEvents()
        self.folder.cleanup()

    def test_bench_fits_the_fixed_page_at_every_size(self):
        from goal2.desktop.fixed_page import problems
        from goal2.desktop.bench_page import VIEW
        self.window.bench.poll()
        self.assertEqual(self.window.fixture_views.currentIndex(), VIEW)
        bench = self.window.bench
        for chosen, message in (([], ''), ([[a, b] for a, b in zip(self.eleven[1:7], self.bench[1:7])],
                                           'Not made: a long refusal; another long refusal. Press Enter.')):
            bench.chosen = chosen;bench.message = message;bench.refresh()
            for size in ((1440, 900), (1050, 780), (900, 640), (2560, 1600)):
                with self.subTest(size=size, chosen=len(chosen)):
                    self.window.resize(*size);self.app.processEvents();self.app.processEvents()
                    self.assertEqual(problems(self.window), [])
        # The original's screen: the counter from the decision, the prompt, injured marked, bars.
        self.assertEqual(bench.counter.text(), 'substitutions left 5')
        self.assertEqual(bench.roster.unavailable, {self.eleven[3]})
        self.assertIn('take off this player', bench.prompt.text())

    def test_keyboard_alone_completes_a_swap(self):
        from PySide6.QtCore import Qt
        from PySide6.QtTest import QTest
        bench = self.window.bench;self.window.bench.poll();self.app.processEvents()
        roster = bench.roster
        self.assertTrue(roster.hasFocus())
        QTest.keyClick(roster, Qt.Key.Key_Down);QTest.keyClick(roster, Qt.Key.Key_Down)
        self.assertIn('take off this player', bench.prompt.text())
        QTest.keyClick(roster, Qt.Key.Key_Return)
        for _ in range(11):
            QTest.keyClick(roster, Qt.Key.Key_Down)
        self.assertIn('put on this player', bench.prompt.text())
        QTest.keyClick(roster, Qt.Key.Key_Return)
        self.assertEqual(bench.chosen, [[self.eleven[2], self.bench[2]]])
        QTest.keyClick(roster, Qt.Key.Key_Tab);self.app.processEvents()
        self.assertTrue(bench.play.hasFocus(), self.app.focusWidget())
        QTest.keyClick(bench.play, Qt.Key.Key_Return);self.app.processEvents()
        self.assertEqual(self.stub.answers, [[[self.eleven[2], self.bench[2]]]])

    def test_escape_with_nothing_chosen_plays_on(self):
        from PySide6.QtCore import Qt
        from PySide6.QtTest import QTest
        bench = self.window.bench;bench.poll();self.app.processEvents()
        QTest.keyClick(bench.roster, Qt.Key.Key_Return)
        QTest.keyClick(bench.roster, Qt.Key.Key_Escape)
        self.assertEqual((bench.chosen, bench.mark, self.stub.answers), ([], None, []))
        QTest.keyClick(bench.roster, Qt.Key.Key_Escape)
        self.assertEqual(self.stub.answers, [[]])
        self.assertNotEqual(self.window.fixture_views.currentIndex(), 4)

    def test_refusal_shows_the_original_message_and_the_engine_counter(self):
        from goal2.game.watched_match import NO_MORE_SUBSTITUTES
        bench = self.window.bench;bench.poll()
        pairs = [[a, b] for a, b in zip(self.eleven[1:7], self.bench[1:7])]
        bench.chosen = [list(p) for p in pairs];bench.play_on()
        self.assertEqual(self.stub.answers, [pairs])
        self.stub.reports.append({'context': 'half_time', 'asked': pairs, 'made': pairs[:5], 'requested': [],
                                  'refused': [pairs[5] + [NO_MORE_SUBSTITUTES]], 'substitutions_left': 0})
        bench.poll()
        self.assertEqual(self.window.fixture_views.currentIndex(), 4)
        self.assertEqual(bench.counter.text(), NO_MORE_SUBSTITUTES)
        self.assertIn(NO_MORE_SUBSTITUTES, bench.message_label.text())

    def test_pause_says_the_swap_waits_for_the_stoppage(self):
        bench = self.window.bench
        self.stub.decision = type(self.decision)('decision', 5, (0, 0), dict(self.decision.data, context='pause',
                                                                              substitutions_now=False))
        bench.poll()
        self.assertIn('next stoppage', bench.message_label.text())
        self.assertIn('next stoppage', bench.context.text())


if __name__ == '__main__':
    unittest.main()
