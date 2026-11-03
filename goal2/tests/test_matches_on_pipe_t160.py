"""[designed: owner, 2026-11-03, #527 D3; T160] The window's watched and competitive matches play on the owner's one
engine process (goal2.game.watched_jobs.MatchEngine over goal2.game.engine_process; docs/engine-process.md), through
the bridge API they had on the file journals (docs/watched-jobs.md).

`Session` plays one window session on a real ManagementWindow, with `unicorn` unimportable in this process (a
meta-path blocker): a watched Play cancelled at its first event, a watched Play to its publication, then, on another
game (as Resume would load one), a competitive Play to its publication. All three are played by one engine pid under
PyPy 3.11, the unchanged game is sent once, and the engine has exited within 5 s of the window's close (#417).

`Tokens` drives stand-in engines (the protocol's framing, no match): the replies of a cancelled match, those sent
after its cancel and those of a match whose engine had to be killed, never reach the next match.
"""
import copy
import importlib.abc
import sys
import textwrap
import time
import unittest
from pathlib import Path

from goal2.engine.original_match import Fixture
from goal2.tests import requires

ROOT = Path(__file__).resolve().parents[2]
WAIT = 900                       # seconds for a whole match under PyPy on a loaded runner


class NoUnicorn(importlib.abc.MetaPathFinder):
    """Makes `unicorn` unimportable in this process."""

    def find_spec(self, name, path=None, target=None):
        if name == 'unicorn' or name.startswith('unicorn.'):
            raise ModuleNotFoundError(f'No module named {name!r} (blocked by test_matches_on_pipe_t160)', name=name)
        return None


def until(predicate, limit, what):
    deadline = time.monotonic() + limit
    while time.monotonic() < deadline:
        if predicate():
            return
        time.sleep(.005)
    raise AssertionError(f'{what} within {limit} s')


def other_game():
    """A competitive campaign game: test_campaign_competitive_publication.campaign(21, 2), built here because that
    helper asks for Unicorn, which Play no longer needs."""
    from goal2.engine.original_match import Image
    from goal2.engine.original_match.assets import reference_image
    from goal2.game.campaign import CampaignState, Fixture as Scheduled
    from goal2.game.campaign_pool import validate
    from goal2.game.state import from_savestate
    raw = reference_image(ROOT / '.cache')
    state = from_savestate(raw)
    state.managed_country, state.captain = 7, 0
    state.managed_squad = Image(state.mem).squad(7)
    state.starting_eleven = state.managed_squad[:11]
    state.country_tactics = state.countries[7][0x2D]
    state.campaign = CampaignState(2028, 1, 1, 2, state.rng_seed_7b62, state.rng_seed_8336,
                                   (Scheduled('original:21', 1, 1, 2, 2, 7, 19),))
    state.campaign.reserve_ids = validate(state)
    return state, raw


def play(jobs, token, limit=WAIT):
    """Poll a job to its end; its events."""
    seen = []

    def done():
        seen.extend(jobs.poll(token))
        return not jobs.busy
    until(done, limit, 'the match did not finish')
    return seen


@requires.need(modules=('PySide6', 'pygame'),
               files=(requires.WATCHED['files'][0], 'GOAL.DAT', 'e010-r0008-halftime.sav'))
class Session(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from PySide6.QtWidgets import QApplication
        from goal2.tests.test_pypy_worker_t152 import pypy
        cls.pypy = pypy()
        cls.app = QApplication.instance() or QApplication([])
        cls.other_game = other_game()
        blocker = NoUnicorn()
        hidden = {name: sys.modules.pop(name) for name in list(sys.modules)
                  if name == 'unicorn' or name.startswith('unicorn.')}
        sys.meta_path.insert(0, blocker)
        try:
            cls.run_session()
        finally:
            sys.meta_path.remove(blocker)
            sys.modules.update(hidden)

    @classmethod
    def run_session(cls):
        import tempfile
        from goal2.desktop.model import DesktopModel
        from goal2.desktop.window import ManagementWindow
        cls.folder = tempfile.TemporaryDirectory()
        model = DesktopModel.open(ROOT / '.cache/e010-r0008-halftime.sav', ROOT / '.cache/GOAL.DAT',
                                  Path(cls.folder.name) / 'session.g2save', country=4)
        window = ManagementWindow(model)
        out = cls.out = {'pids': {}, 'opens': {}}
        try:
            watched, competitive = window.watched, window.competitive
            # The pygame viewer is not this task's (B3, T166): a child that shows nothing stands in for it.
            watched.viewer_command = [sys.executable, '-c', 'import time;time.sleep(600)']
            engine = model._match_engine.engine
            before = copy.deepcopy(model.state)

            # A watched Play, cancelled at its first event.
            watched.start(frames=False)
            token = watched.engine_token
            seen = []
            until(lambda: seen.extend(watched.engine.poll(token)) or bool(seen), WAIT, 'no first event')
            out['ready'] = dict(engine.ready)
            out['pids']['cancelled'] = engine.pid
            watched.cancel()
            out['cancelled_state'] = model.state == before
            out['opens']['cancelled'] = engine.opens

            # A watched Play of the same, unchanged game, to its publication.
            watched.start(frames=False)
            out['pids']['watched'] = engine.pid
            out['watched_events'] = play(watched.engine, watched.engine_token)
            out['watched'] = watched.engine.outcome
            out['watched_published'] = model.state.last_match is not None and model.state.match_count == before.match_count + 1
            out['opens']['watched'] = engine.opens
            watched.cancel()                                   # the viewer stand-in, as the window's poll would

            # Another game, as Resume would load: a competitive Play to its publication.
            state, raw = cls.other_game
            model.state, model.template_bytes = state, raw
            token = competitive.start(record_draws=True)
            out['pids']['competitive'] = engine.pid
            out['competitive_events'] = play(competitive, token)
            out['competitive'] = competitive.outcome
            out['competitive_published'] = model.state.match_count == state.match_count + 1
            out['opens']['competitive'] = engine.opens
            out['pids']['last'] = engine.pid
            process = engine.process
        finally:
            started = time.monotonic()
            window.close()
            window.deleteLater()
            cls.app.processEvents()
        try:
            out['code'] = process.wait(timeout=5)
        except Exception as exc:                             # noqa: BLE001 - asserted below
            out['code'] = repr(exc)
        out['close_seconds'] = time.monotonic() - started
        out['engine_left'] = getattr(model, '_match_engine', None)

    @classmethod
    def tearDownClass(cls):
        cls.folder.cleanup()

    def test_one_engine_pid_plays_two_watched_and_one_competitive_match(self):
        pids = self.out['pids']
        self.assertEqual(set(pids.values()), {self.out['ready']['pid']})
        self.assertEqual((self.out['ready']['implementation'], self.out['ready']['version']), ('PyPy', [3, 11]))

    def test_the_game_is_sent_once_while_it_is_unchanged(self):
        opens = self.out['opens']
        self.assertEqual((opens['cancelled'], opens['watched']), (1, 1))
        self.assertEqual(opens['competitive'], 2)              # the resumed game is another game

    def test_the_engine_has_exited_within_5_s_of_the_window_s_close(self):
        self.assertEqual(self.out['code'], 0)
        self.assertLess(self.out['close_seconds'], 5)
        self.assertIsNone(self.out['engine_left'])

    def test_without_unicorn_a_watched_and_a_competitive_play_start_and_complete(self):
        self.assertTrue(self.out['cancelled_state'], 'the cancelled match changed the game')
        for kind in ('watched', 'competitive'):
            with self.subTest(kind=kind):
                outcome = self.out[kind]
                self.assertIsNotNone(outcome)
                self.assertEqual(tuple(self.out[f'{kind}_events']), outcome.events)
                self.assertEqual(outcome.events[-1].kind, 'end')
                self.assertTrue(self.out[f'{kind}_published'])


# --- the token: stand-in engines ------------------------------------------------------------------------------------

# The protocol's framing and no match. Each match sends `kickoff` (minute 0, or 1 for the second match), then, by
# mode: `answer` replies to a cancel with three more events (sent after the cancel) and `cancelled`; `deaf` ignores
# a cancel and keeps sending events.
STAND_IN = textwrap.dedent("""
    import os, queue, sys, threading, time
    from goal2.game.engine_server import read_packet, encode_packet
    from goal2.game.session_save import _json_value
    mode, out = sys.argv[1], sys.stdout.buffer
    def send(kind, value=None):
        out.write(encode_packet({"kind": kind, "value": _json_value(value)})); out.flush()
    def event(minute, text):
        return {"kind": "commentary", "minute": minute, "score": (0, 0), "data": {"text": text}}
    inbox = queue.Queue()
    def read():
        while True:
            packet = read_packet(sys.stdin.buffer)
            inbox.put(packet)
            if packet is None:
                return
    threading.Thread(target=read, daemon=True).start()
    send("ready", {"implementation": "stand-in", "version": [0, 0], "pid": os.getpid()})
    matches = 0
    while True:
        packet = inbox.get()
        if packet is None or packet[0]["op"] == "quit":
            sys.exit(0)
        op = packet[0]["op"]
        if op == "open":
            send("opened")
        elif op == "match":
            send("event", event(matches, "match %d" % matches))
            matches += 1
            if mode == "deaf":
                while True:
                    send("event", event(matches - 1, "still match %d" % (matches - 1))); time.sleep(.01)
        elif op == "cancel":
            for n in range(3):
                send("event", event(matches - 1, "after the cancel of match %d" % (matches - 1)))
            send("cancelled")
""")


class Tokens(unittest.TestCase):
    def setUp(self):
        from types import SimpleNamespace
        from goal2.game.watched_jobs import WatchedJobs
        from goal2.game.watched_publication import WatchedJob
        from goal2.tests.test_session_save import _state
        from unittest.mock import Mock, patch
        self.owner = SimpleNamespace(state=_state(), template_bytes=b'private template')
        self.before = copy.deepcopy(self.owner.state)
        self.WatchedJobs = WatchedJobs
        # The publication's begin is a stand-in's: these matches never complete.
        self.begin = patch('goal2.game.watched_publication.WatchedPublication.begin', autospec=True,
                           side_effect=lambda publication, fixture: WatchedJob(
                               __import__('secrets').token_hex(8), copy.deepcopy(self.before), fixture))
        self.begin.start()
        self.addCleanup(self.begin.stop)
        self.Mock = Mock

    def bridge(self, mode):
        jobs = self.WatchedJobs(self.owner, command=[sys.executable, '-c', STAND_IN, mode])
        self.addCleanup(jobs.close)
        return jobs

    def first_event(self, jobs, token):
        seen = []
        until(lambda: seen.extend(jobs.poll(token)) or bool(seen), 60, 'no first event')
        return seen

    def texts(self, events):
        return [e.data['text'] for e in events]

    def test_replies_sent_after_a_cancel_never_reach_the_next_match(self):
        jobs = self.bridge('answer')
        old = jobs.start(Fixture(7, 19, 21))
        self.assertEqual(self.texts(self.first_event(jobs, old)), ['match 0'])
        old_match = jobs._match
        pid = jobs.process.pid
        jobs.cancel(old)
        self.assertEqual(len(old_match.replies), 4)           # three events after the cancel, then `cancelled`
        new = jobs.start(Fixture(7, 19, 21))
        self.assertNotEqual(old, new)
        for action in (jobs.poll, jobs.cancel):
            with self.assertRaisesRegex(ValueError, 'stale'):
                action(old)
        seen = self.first_event(jobs, new)
        time.sleep(.2)
        seen.extend(jobs.poll(new))
        self.assertEqual(self.texts(seen), ['match 1'])       # nothing of match 0
        self.assertEqual(jobs.process.pid, pid)                # answered: the same process
        jobs.cancel(new)
        self.assertEqual(self.owner.state, self.before)

    def test_replies_of_a_match_whose_engine_was_killed_never_reach_the_next_match(self):
        jobs = self.bridge('deaf')
        old = jobs.start(Fixture(7, 19, 21))
        self.first_event(jobs, old)
        old_process = jobs.process
        started = time.monotonic()
        jobs.cancel(old)                                       # unanswered: killed after CANCEL_WAIT
        self.assertLess(time.monotonic() - started, 2)
        self.assertIsNotNone(old_process.poll())
        new = jobs.start(Fixture(7, 19, 21))
        seen = self.first_event(jobs, new)
        self.assertNotEqual(jobs.process.pid, old_process.pid)
        self.assertEqual(self.texts(seen)[0], 'match 0')       # the new process's first match
        self.assertTrue(all(text.endswith('match 0') for text in self.texts(seen)))
        self.assertEqual(jobs.shared.engine.opens, 2)          # the new process was sent the game
        jobs.cancel(new)


if __name__ == '__main__':
    unittest.main()
