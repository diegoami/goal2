"""[designed: T170o/#735] Stateful worker contract; actual port runs only in PyPy."""
import json
import queue
import tempfile
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


def actual_worker(raw, late_captain=False, roster_case=None):
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
    configured_captain = a._squad(a.opts['managed'])[0] if late_captain else None
    ask('configure', captain=configured_captain, substitutions=2)
    PrematchSeam(a, captain=configured_captain, substitutions=2)
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
    roster_answer = roster = None
    if roster_case:
        from goal2.engine.original_match.match import PLAYER_POSITION
        d = a.waiting
        if roster_case == 'starter':
            pair = [d['eleven'][0], d['eleven'][1]]
        else:
            off = d['bench'][-1]
            on = next(w for w in d['pool'] if a._available(w)
                      and a._player(w, PLAYER_POSITION) != a._player(off, PLAYER_POSITION))
            pair = [off, on]
        roster_answer = {'edit_only': True, 'substitutions': [pair]}
        ask('answer', decision=second['decision'], answer=roster_answer)
        a.answer(**roster_answer)
        roster = next_decision()
        second = roster
    play_answer = ({'captain': next(w for w in reversed(a.waiting['eleven'])
                                   if w != configured_captain and a._available(w))}
                   if late_captain else {})
    ask('answer', decision=second['decision'], answer=play_answer); a.answer(**play_answer)
    observed = ask('next', count=1)
    assert observed['events'] == [asdict(next(stream))]
    assert a.m.read(0, MEM_SIZE) == b.m.read(0, MEM_SIZE)
    assert all(a.m.reg(r) == b.m.reg(r) for r in REGS)
    return {'state': value, 'first': first, 'edited': second, 'after_play': observed,
            'play_answer': play_answer,
            'configured_captain': configured_captain,
            'roster_answer': roster_answer, 'roster': roster,
            'entry_equal': True, 'post_play_sha256': hashlib.sha256(b.m.read(0, MEM_SIZE)).hexdigest()}


# [designed: T170p] Read-only test observer in the real PyPy pipe child. The
# original D010 return is the accepted captain, not a copied request value.
CAPTAIN_PROBE = '''
import json,sys
from pathlib import Path
from goal2.game.season_worker import SeasonWorker
dispatch = SeasonWorker.dispatch
def observed(self, header):
    result = dispatch(self, header)
    if header.get('action') == 'configure':
        match = self.session.pending_match
        active = [False]
        def prompt(replay):
            if not replay:
                active[0] = match.m.stack_word(2) == 1 and match.m.stack_word(4) == match.side
        def accepted(replay):
            if not replay and active[0]:
                Path(sys.argv[1]).write_text(json.dumps({'captain': match.m.reg('ax')}))
                active[0] = False
        match.m.at('0791:CC7B', prompt)
        match.m.at('0791:D010', accepted)
    return result
SeasonWorker.dispatch = observed
from goal2.game.engine_server import main
main()
'''


class Pipe(unittest.TestCase):
    def make_engine(self, command=None):
        from goal2.game.engine_process import EngineProcess
        self.replies = queue.Queue()
        engine = EngineProcess(lambda kind, value: self.replies.put((kind, value)), command=command)
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
        self.actual_pipe(False)

    def test_late_captain_crosses_the_actual_pipe_after_the_edits(self):
        self.actual_pipe(True)

    def actual_pipe(self, late_captain, roster_case=None):
        from pathlib import Path
        from goal2.engine.original_match.assets import REFERENCE, reference_image
        from goal2.tests import requires, pypy_engine
        requires.require(files=(REFERENCE['asset'],))
        raw = reference_image(Path(__file__).resolve().parents[2]/'.cache')
        expected = pypy_engine.call(__name__+':actual_worker', raw, late_captain, roster_case)
        command = None
        if late_captain:
            from goal2.game.engine_python import engine_python
            folder = tempfile.TemporaryDirectory(prefix='goal2-captain-probe-')
            self.addCleanup(folder.cleanup)
            report = Path(folder.name) / 'accepted.json'
            command = [engine_python(), '-c', CAPTAIN_PROBE, str(report)]
        engine = self.make_engine(command); engine.season_open(expected['state'])
        ready = self.receive('ready'); self.assertEqual(ready['version'], [3, 11])
        self.receive('season')
        engine.season_request('advance'); self.receive('season')
        engine.season_request('configure', captain=expected['configured_captain'], substitutions=2)
        self.receive('season')
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
        if roster_case:
            off = expected['roster_answer']['substitutions'][0][0]
            engine.season_request('answer', decision=packet['decision'],
                                  answer={'edit_only': True, 'substitutions': [[off, off]]})
            refused = self.receive('season_error')
            self.assertIn('pre-match swap', refused['error'])
            self.assertFalse(refused['lost'])
            self.assertTrue(engine.season_active)
            engine.season_request('answer', decision=packet['decision'], answer=expected['roster_answer'])
            self.receive('season')
            changed = []
            while True:
                engine.season_request('next', count=32)
                packet = self.receive('season'); changed.extend(packet['events'])
                if packet['decision'] is not None:
                    break
            self.assertEqual(changed, expected['roster']['events'])
        if late_captain:
            engine.season_request('answer', decision=packet['decision'], answer={'captain': True})
            refused = self.receive('season_error')
            self.assertIn('available player', refused['error'])
            self.assertFalse(refused['lost'])
            self.assertTrue(engine.season_active)
        engine.season_request('answer', decision=packet['decision'], answer=expected['play_answer'])
        self.receive('season')
        engine.season_request('next', count=1)
        self.assertEqual(self.receive('season')['events'], expected['after_play']['events'])
        if late_captain:
            from goal2.desktop.worker import read_json
            deadline = time.monotonic()+2
            accepted = read_json(report)
            while accepted is None and time.monotonic() < deadline:
                time.sleep(.01)
                accepted = read_json(report)
            self.assertEqual(accepted, expected['play_answer'])
        print('T170O_ENTRY '+json.dumps({'entry_equal': expected['entry_equal'],
              'post_play_sha256': expected['post_play_sha256'], 'pipe_pypy': ready}), flush=True)


class WireGuards(unittest.TestCase):
    def test_server_keeps_pure_refusals_but_discards_backend_failure(self):
        import io
        from goal2.game.engine_server import Server
        server = Server(io.BytesIO(), io.BytesIO()); sent = []
        server.send = lambda *args: sent.append(args)
        server._season({'op': 'season', 'request': 1, 'action': 'open'},
                       json.dumps({'state': state(), 'keys': None}).encode())
        held = server.season.session
        server._season({'op': 'season', 'request': 2, 'action': 'resume'}, b'')
        self.assertEqual(sent[-1][0], 'season_error')
        self.assertFalse(sent[-1][1]['lost']); self.assertIs(server.season.session, held)
        server.game = (None, b'legacy')
        self.assertRaises(ValueError, server._open, b'legacy')
        self.assertRaises(ValueError, server._match, {})
        with patch.object(held, 'advance', side_effect=RuntimeError('backend failed')):
            server._season({'op': 'season', 'request': 3, 'action': 'advance'}, b'')
        self.assertTrue(sent[-1][1]['lost'])
        self.assertIsNone(server.season.session)

    def test_parent_excludes_concurrent_requests_and_bad_reply_hash(self):
        from goal2.game.engine_process import EngineProcess
        from goal2.game.engine_server import ProtocolError
        engine = EngineProcess(lambda *args: None)
        engine._life = object(); engine._season_active = True
        with patch.object(engine, '_send'):
            engine.season_request('observe')
            self.assertTrue(engine.busy)
            self.assertRaises(ValueError, engine.season_request, 'advance')
            self.assertRaises(ValueError, engine.season_open, state())
            self.assertRaises(ValueError, engine.match, 'watched', None)
        reply = dict(kind='season', value={'request': 1, 'action': 'observe',
                                          'observation': {'output_hash': 'wrong'}})
        self.assertRaises(ProtocolError, engine._decode, engine._life, reply,
                          json.dumps(state()).encode())
        reply['value']['request'] = 2
        self.assertRaises(ProtocolError, engine._decode, engine._life, reply, b'{}')


if __name__ == '__main__':
    unittest.main()
