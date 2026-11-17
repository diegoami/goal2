"""[designed: T170u/#753] Accepted T135 native R/C through one held Match.

[confirmed: archaeology fc6b5294, F010/F031] Numeric positions and explicit
club actions have distinct native key paths; pure admission precedes replay.
"""
import copy
import hashlib
import io
import json
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from goal2.game.prematch_seam import PrematchSeam
from goal2.game.season import canonical_hash
from goal2.tests import pypy_engine
from goal2.tests import test_season_worker_t170o as wire
from goal2.tests.test_prematch_preview_t170s import reference_raw
from goal2.tests.test_season_session_t170b import state, step


class Mapping(unittest.TestCase):
    def test_numeric_and_club_methods_keep_original_value_types(self):
        class Match:
            def configure_route_entry(self, **fields): pass
            def answer(self, **fields): self.fields = fields
        m = Match(); seam = PrematchSeam(m)
        seam.set_position(121, 3)
        self.assertEqual(m.fields, {'edit_only': True, 'positions': {121: 3}})
        seam.club_position(2564)
        self.assertEqual(m.fields, {'edit_only': True, 'positions': {2564: 'club'}})
        self.assertRaises(ValueError, seam.set_position, 121, True)
        self.assertRaises(ValueError, seam.set_position, 121, '3')
        self.assertRaises(ValueError, seam.set_position, 121, 14)


def position_sequence(raw, via_seam=True):
    import sys
    from dataclasses import asdict
    from goal2.engine.original_match.image import Image
    from goal2.engine.original_match.machine import REGS, MEM_SIZE, Uc
    from goal2.game import engine_tables
    from goal2.game.season import SeasonSession
    assert sys.implementation.name == 'pypy' and sys.version_info[:2] == (3, 11) and Uc is None
    tables = engine_tables.load(); initial = Image.from_bytes(raw).state(tables)
    session = SeasonSession(initial); assert session.advance().status == 'match'
    m = session.pending_match; seam = PrematchSeam(m); events = []; entries = []
    def entered(replay):
        if not replay: entries.append([m.m.stack_word(4), m.m.rd(0xA976, 1)])
    m.m.at('1771:4952', entered)  # original player argument and actual R/C byte
    def decision():
        for event in m.events():
            events.append(asdict(event))
            if event.kind == 'decision': return event.data
        raise AssertionError('missing pre-match decision')
    first = decision(); boundary_hash = canonical_hash(session.state)
    words = [first['eleven'][0], first['bench'][0], first['pool'][0]]
    original = {word:m._player(word, 6) for word in words}
    stages = []; answers = []
    for word in words:
        for goal in ((m._player(word, 6)+1) % 14, 'club'):
            fields = {'edit_only': True, 'positions': {word: goal}}; answers.append(fields)
            before = len(events)
            if via_seam:
                if goal == 'club': seam.club_position(word)
                else: seam.set_position(word, goal)
            else: m.answer(**fields)
            d = decision(); preview = m.records_after(); image = Image.from_state(preview, tables)
            assert image.players()[word][6] == (m._player(word, 7) if goal == 'club' else goal)
            assert image.squad(m.opts['managed']) == d['eleven']+d['bench']
            assert canonical_hash(session.state) == boundary_hash
            assert not any(e['kind'] in ('tick','minute','substitution') for e in events[before:])
            stages.append(dict(word=word, goal=goal, preview_hash=canonical_hash(preview),
                               memory=hashlib.sha256(m.m.read(0, MEM_SIZE)).hexdigest(),
                               all16=[m.m.reg(r) for r in REGS]))
    for word, pos in original.items():
        if m._player(word, 6) != pos:
            fields = {'edit_only': True, 'positions': {word:pos}}; answers.append(fields)
            m.answer(**fields); d = decision()
            stages.append(dict(word=word,goal=pos,preview_hash=canonical_hash(m.records_after()),
                               memory=hashlib.sha256(m.m.read(0,MEM_SIZE)).hexdigest(),
                               all16=[m.m.reg(r) for r in REGS]))
    for word in words:
        assert [word,ord('R')] in entries and [word,ord('C')] in entries
    if via_seam: seam.play()
    else: m.answer()
    after = asdict(next(m.events()))
    return dict(initial=initial, boundary_hash=boundary_hash, stages=stages, answers=answers,
                entries=entries, events_hash=canonical_hash(events), after_play=after,
                memory=hashlib.sha256(m.m.read(0,MEM_SIZE)).hexdigest(),
                all16=[m.m.reg(r) for r in REGS])


def worker_guards(raw):
    from goal2.engine.original_match.image import Image
    from goal2.engine.original_match.machine import REGS
    from goal2.game import engine_tables
    from goal2.game.season_worker import SeasonWorker, SeasonRequestError
    w = SeasonWorker(); number = 0
    def ask(action, **fields):
        nonlocal number
        number += 1
        return w.dispatch(dict(op='season', request=number, action=action, **fields))
    ask('open', state=Image.from_bytes(raw).state(engine_tables.load())); ask('advance'); ask('configure')
    while True:
        packet = ask('next',count=32)
        if packet['decision'] is not None: break
    m = w.session.pending_match; word = m.waiting['eleven'][0]; n = packet['decision']
    def snapshot():
        return (m.memory_component(), [m.m.reg(r) for r in REGS], copy.deepcopy(m.st),
                copy.deepcopy(m.opts), copy.deepcopy(m.inputs), copy.deepcopy(m._replay_actions),
                m._replay_events, copy.deepcopy(m._frame_state()), w.decision, w.session.state)
    cases = [dict(edit_only=True,positions={word:True}),dict(edit_only=True,positions={65535:3}),
             dict(edit_only=True,positions={word:14}),dict(positions={word:3}),
             dict(edit_only=True,positions={word:3},own_tactics={word:{1:True}}),
             dict(edit_only=True,positions={word:3},quick=True)]
    for fields in cases:
        before = snapshot()
        try: ask('answer',decision=n,answer=fields)
        except SeasonRequestError: pass
        else: raise AssertionError('invalid position consumed decision')
        assert snapshot() == before
    ask('answer',decision=n,answer={'edit_only':True,'positions':{word:'club'}})
    while True:
        repaired = ask('next',count=32)
        if repaired['decision'] is not None: break
    assert repaired['decision'] != n
    return len(cases)


class Actual(unittest.TestCase):
    def test_seam_and_direct_answers_equal_full_memory_registers_and_events(self):
        raw = reference_raw(); actual = pypy_engine.call(__name__+':position_sequence', raw)
        direct = pypy_engine.call(__name__+':position_sequence', raw, False)
        # Exclude only private input state from failure output; compare its hash.
        self.assertEqual(canonical_hash(actual.pop('initial')),canonical_hash(direct.pop('initial')))
        self.assertEqual(actual,direct)
        print('T170U_POSITION '+json.dumps({'stages':actual['stages'], 'entries':actual['entries'],
              'memory':actual['memory'], 'all16':actual['all16']},sort_keys=True),flush=True)

    def test_all_invalid_position_packets_are_pure_and_repairable(self):
        self.assertEqual(pypy_engine.call(__name__+':worker_guards',reference_raw()),6)


class PositionPipe(unittest.TestCase):
    make_engine = wire.Pipe.make_engine
    receive = wire.Pipe.receive
    def test_actual_pipe_repairs_and_previews_each_xi_bench_pool_position_and_club(self):
        expected = pypy_engine.call(__name__+':position_sequence',reference_raw())
        engine = self.make_engine(); engine.season_open(expected['initial'])
        ready = self.receive('ready'); self.assertEqual(ready['implementation'],'PyPy')
        self.receive('season'); engine.season_request('advance'); self.receive('season')
        engine.season_request('configure'); self.receive('season')
        for index, (fields, stage) in enumerate(zip(expected['answers'], expected['stages'])):
            while True:
                engine.season_request('next',count=32); packet = self.receive('season')
                if packet['decision'] is not None: break
            n = packet['decision']
            engine.season_request('preview',decision=n); before = self.receive('season')['preview']['state_hash']
            if index:
                self.assertEqual(before,expected['stages'][index-1]['preview_hash'])
            engine.season_request('answer',decision=n,answer={'edit_only':True,'positions':{stage['word']:True}})
            self.assertFalse(self.receive('season_error')['lost'])
            self.assertTrue(engine.season_active)
            engine.season_request('preview',decision=n)
            self.assertEqual(self.receive('season')['preview']['state_hash'],before)
            engine.season_request('answer',decision=n+1,answer=fields)
            self.assertFalse(self.receive('season_error')['lost'])
            engine.season_request('answer',decision=n,answer=fields); self.receive('season')
        while True:
            engine.season_request('next',count=32); packet = self.receive('season')
            if packet['decision'] is not None: break
        engine.season_request('preview',decision=packet['decision'])
        self.assertEqual(self.receive('season')['preview']['state_hash'], expected['stages'][-1]['preview_hash'])
        engine.season_request('observe')
        self.assertEqual(self.receive('season')['observation']['output_hash'],expected['boundary_hash'])
        engine.season_request('answer',decision=packet['decision'],answer={}); self.receive('season')
        engine.season_request('next',count=1)
        self.assertEqual(self.receive('season')['events'],[expected['after_play']])


class FailureBoundary(unittest.TestCase):
    def test_backend_failure_is_not_relabelled_as_pure_position_refusal(self):
        from goal2.game.engine_server import Server
        server = Server(io.BytesIO(),io.BytesIO()); sent = []; server.send = lambda *args:sent.append(args)
        server.season.dispatch(dict(op='season',request=1,action='open',state=state()))
        match = SimpleNamespace(waiting={'context':'pre_match'})
        def failed(**fields): raise RuntimeError('backend failure')
        match.answer = failed
        with patch('goal2.game.season.route.play_round',return_value=step('match',state(),match=match)):
            server.season.dispatch(dict(op='season',request=2,action='advance'))
        server.season.decision = 1
        server._season(dict(op='season',request=3,action='answer',decision=1,
                            answer={'edit_only':True,'positions':{'1':2}}),b'')
        self.assertTrue(sent[-1][1]['lost']); self.assertIsNone(server.season.session)


if __name__ == '__main__': unittest.main()
