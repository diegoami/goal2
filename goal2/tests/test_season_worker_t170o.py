"""[designed: T170o/#735] Stateful worker contract; actual port runs only in PyPy."""
import json
import queue
import time
import unittest
from dataclasses import asdict
from unittest.mock import patch

from goal2.game.season import SeasonSession
from goal2.tests.test_season_session_t170b import state, step


class Worker(unittest.TestCase):
    def setUp(self):
        from goal2.game.season_worker import SeasonWorker
        self.worker = SeasonWorker()
        self.number = 0

    def ask(self, action, **kwargs):
        self.number += 1
        return self.worker.dispatch(dict(op='season', request=self.number, action=action, **kwargs))

    def test_calls_share_session_keys_deltas_and_terminal(self):
        value = state()
        page = {'text': ['same']}
        with patch('goal2.game.season.route.play_round', side_effect=[
                step('complete', value, pages=(page, page)), step('deferred-rollover', value)]) as play:
            opened = self.ask('open', state=value)
            self.assertEqual(opened['observation']['status'], 'ready')
            first = self.ask('advance')
            self.assertEqual(len(first['observation']['news_pages']), 2)
            first['observation']['news_pages'][0]['text'].append('caller mutation')
            self.assertEqual(self.ask('observe')['observation']['news_pages'], ())
            self.assertEqual(self.ask('advance')['observation']['status'], 'deferred-rollover')
            self.assertEqual(self.ask('advance')['observation']['call_number'], 2)
            self.assertIs(play.call_args_list[0].args[2], play.call_args_list[1].args[2])
            self.assertEqual(play.call_count, 2)
            self.assertEqual(self.ask('discard'), {'request': self.number, 'action': 'discard'})
            self.assertRaises(ValueError, self.ask, 'observe')

    def test_pending_match_bounded_events_explicit_answer_and_same_object_resume(self):
        from goal2.engine.original_match.match import Event
        class Match:
            over = False
            def __init__(self):
                self.answers = []
            def configure_route_entry(self, **kwargs):
                self.configuration = kwargs
            def events(self):
                yield Event('decision', 0, (0, 0), {'context': 'pre_match', 'eleven': [1]})
                if not self.answers:
                    raise AssertionError('worker implicitly played on')
                for n in range(40):
                    yield Event('minute', n, (0, 0))
                self.over = True
            def answer(self, **kwargs):
                self.answers.append(kwargs)
        value = state(); match = Match()
        with patch('goal2.game.season.route.play_round', return_value=step('match', value, match=match)), \
                patch('goal2.game.season.route.resume_round', return_value=step('complete', value)) as resume:
            self.ask('open', state=value); self.ask('advance')
            self.assertRaises(ValueError, self.ask, 'advance')
            self.assertRaises(ValueError, self.ask, 'resume')
            self.assertRaises(ValueError, self.ask, 'next')  # configure first
            self.ask('configure', captain=1, substitutions=2)
            self.assertRaises(ValueError, self.ask, 'configure')
            first = self.ask('next', count=32)
            decision = first['decision']
            self.assertEqual(len(first['events']), 1)
            self.assertRaises(ValueError, self.ask, 'next')
            self.assertRaises(ValueError, self.ask, 'answer', decision=decision+1, answer={})
            self.assertEqual(match.answers, [])
            self.ask('answer', decision=decision, answer={})
            self.assertRaises(ValueError, self.ask, 'answer', decision=decision, answer={})
            self.assertEqual(len(self.ask('next', count=32)['events']), 32)
            self.assertRaises(ValueError, self.ask, 'next', count=33)
            self.assertEqual(len(self.ask('next', count=32)['events']), 8)
            self.assertTrue(match.over)
            self.ask('resume')
            self.assertIs(resume.call_args.args[1], match)
            self.assertRaises(ValueError, self.ask, 'resume')
            self.assertEqual(resume.call_count, 1)

    def test_malformed_open_preserves_current_session_and_no_object_aliases(self):
        self.ask('open', state=state())
        held = self.worker.session
        self.assertRaises(ValueError, self.ask, 'open', state={'schema': 'wrong'})
        self.assertIs(self.worker.session, held)
        detached = self.ask('observe')['state']; detached['header'] = 'bad'
        self.assertNotEqual(self.ask('observe')['state']['header'], 'bad')
        self.assertRaises(ValueError, self.ask, 'observe', extra=True)


def actual_worker(raw):
    """Source-bound entry and prematch against direct answers, in a PyPy child."""
    import hashlib
    import sys
    from goal2.engine.original_match.image import Image
    from goal2.engine.original_match.machine import MEM_SIZE, REGS, Uc
    from goal2.game import engine_tables
    from goal2.game.prematch_seam import PrematchSeam
    from goal2.game.season_worker import SeasonWorker
    assert sys.implementation.name == 'pypy' and sys.version_info[:2] == (3, 11)
    assert Uc is None
    value = Image.from_bytes(raw).state(engine_tables.load())
    direct = SeasonSession(value); expected = direct.advance()
    worker = SeasonWorker(); number = 0
    def ask(action, **kwargs):
        nonlocal number
        number += 1
        return worker.dispatch(dict(op='season', request=number, action=action, **kwargs))
    ask('open', state=value)
    assert ask('advance')['observation'] == asdict(expected)
    a, b = direct.pending_match, worker.session.pending_match
    assert a.m.read(0, MEM_SIZE) == b.m.read(0, MEM_SIZE)
    assert all(a.m.reg(r) == b.m.reg(r) for r in REGS)
    ask('configure', substitutions=2); PrematchSeam(a, substitutions=2)
    stream = iter(a.events())
    def next_decision():
        events = []
        while True:
            packet = ask('next', count=32)
            events.extend(packet['events'])
            if packet['decision'] is not None:
                break
        reference = []
        for ev in stream:
            reference.append(asdict(ev))
            if ev.kind == 'decision':
                break
        assert events == reference
        return packet
    first = next_decision()
    answer = {'edit_only': True, 'tactics': {'8': not bool(a.waiting['tactics'] & 128)}}
    ask('answer', decision=first['decision'], answer=answer)
    a.answer(edit_only=True, tactics={8: answer['tactics']['8']})
    second = next_decision()
    assert b.waiting == a.waiting and b.waiting['edited']
    ask('answer', decision=second['decision'], answer={}); a.answer()
    observed = ask('next', count=1)
    assert observed['events'] == [asdict(next(stream))]
    assert a.m.read(0, MEM_SIZE) == b.m.read(0, MEM_SIZE)
    assert all(a.m.reg(r) == b.m.reg(r) for r in REGS)
    return {'state': value, 'first': first, 'edited': second, 'after_play': observed,
            'entry_equal': True, 'post_play_sha256': hashlib.sha256(b.m.read(0, MEM_SIZE)).hexdigest()}


class Pipe(unittest.TestCase):
    def make_engine(self):
        from goal2.game.engine_process import EngineProcess
        self.replies = queue.Queue()
        engine = EngineProcess(lambda kind, value: self.replies.put((kind, value)))
        self.addCleanup(engine.close)
        return engine

    def receive(self, kind, timeout=120):
        end = time.monotonic()+timeout
        while time.monotonic() < end:
            got, value = self.replies.get(timeout=max(.01, end-time.monotonic()))
            if got == kind:
                return value
            if got in ('death', 'error', 'season_error'):
                self.fail(f'{got}: {value}')
        self.fail(f'no {kind} reply')

    def test_real_pipe_terminal_discard_and_no_replay_after_death(self):
        from goal2.engine.original_match.image import Image
        from goal2.engine.original_match import route
        from goal2.game import engine_tables
        # [confirmed: route.py] stage 4/8 is deferred without entering the backend.
        value = state(); image = Image.from_state(value, engine_tables.load())
        # Synthetic state's GAME_PTR is zero: cursor/count are already zero.
        image.memory[0x3C] = 4
        image.memory[0x3D] = 1
        value = image.state(engine_tables.load())
        engine = self.make_engine()
        engine.season_open(value)
        self.assertEqual(self.receive('ready')['implementation'], 'PyPy')
        self.assertEqual(self.receive('season')['observation']['status'], 'ready')
        self.assertRaises(ValueError, engine.open_encoded, b'legacy')
        engine.season_request('advance')
        final = self.receive('season')
        self.assertEqual(final['observation']['status'], 'deferred-rollover')
        pid = engine.pid
        engine.season_request('advance')
        self.assertEqual(self.receive('season')['observation'], final['observation'])
        self.assertEqual(engine.pid, pid)
        engine.process.kill(); self.receive('death')
        self.assertRaises(ValueError, engine.season_request, 'observe')
        self.assertIsNone(engine.process)
        engine.season_open(value); self.receive('ready'); self.receive('season')
        engine.season_request('discard'); self.receive('season')
        self.assertFalse(engine.season_active)

    def test_actual_held_entry_and_prematch_are_direct_answers_over_the_pipe(self):
        from pathlib import Path
        from goal2.engine.original_match.assets import REFERENCE, reference_image
        from goal2.tests import requires, pypy_engine
        requires.require(files=(REFERENCE['asset'],))
        raw = reference_image(Path(__file__).resolve().parents[2]/'.cache')
        expected = pypy_engine.call(__name__+':actual_worker', raw)
        engine = self.make_engine(); engine.season_open(expected['state'])
        ready = self.receive('ready'); self.assertEqual(ready['version'], [3, 11])
        self.receive('season')
        engine.season_request('advance'); self.receive('season')
        engine.season_request('configure', substitutions=2); self.receive('season')
        streamed = []
        while True:
            engine.season_request('next', count=32)
            packet = self.receive('season'); streamed.extend(packet['events'])
            if packet['decision'] is not None:
                break
        self.assertEqual(streamed, expected['first']['events'])
        want = not bool(streamed[-1]['data']['tactics'] & 128)
        engine.season_request('answer', decision=packet['decision'],
                              answer={'edit_only': True, 'tactics': {'8': want}})
        self.receive('season')
        edited = []
        while True:
            engine.season_request('next', count=32)
            packet = self.receive('season'); edited.extend(packet['events'])
            if packet['decision'] is not None:
                break
        self.assertEqual(edited, expected['edited']['events'])
        engine.season_request('answer', decision=packet['decision'], answer={})
        self.receive('season')
        engine.season_request('next', count=1)
        self.assertEqual(self.receive('season')['events'], expected['after_play']['events'])
        print('T170O_ENTRY '+json.dumps({'entry_equal': expected['entry_equal'],
              'post_play_sha256': expected['post_play_sha256'], 'pipe_pypy': ready}), flush=True)


if __name__ == '__main__':
    unittest.main()
