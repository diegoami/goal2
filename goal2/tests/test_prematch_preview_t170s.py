"""[designed: T170s/#746] Current data is a preview, never a completed round.

[confirmed: archaeology fb6d3093, T170r] records_after reads the held Match's
current state/2 without playing on. Real dispatcher controls run in PyPy only.
"""
import copy
import hashlib
import json
import unittest
from unittest.mock import patch

from goal2.game.season import canonical_hash
from goal2.tests import pypy_engine, requires
from goal2.tests.test_season_session_t170b import state, step
from goal2.tests import test_season_worker_t170o as worker_tests


def reference_raw():
    from pathlib import Path
    from goal2.engine.original_match.assets import REFERENCE, reference_image
    requires.require(files=(REFERENCE['asset'],))
    return reference_image(Path(__file__).resolve().parents[2]/'.cache')


def real_preview(raw, complete=False, previews=True):
    import sys
    from goal2.engine.original_match.image import Image, PLAYERS_PTR, PLAYER_SIZE, COUNTRY_SIZE
    from goal2.engine.original_match.machine import REGS, Uc
    from goal2.engine.original_match.match import TACTICS
    from goal2.game import engine_tables
    from goal2.game.season_worker import SeasonWorker, SeasonRequestError
    assert sys.implementation.name == 'pypy' and sys.version_info[:2] == (3, 11) and Uc is None
    tables = engine_tables.load(); initial = Image.from_bytes(raw).state(tables)
    worker = SeasonWorker(); number = 0
    def ask(action, **fields):
        nonlocal number
        number += 1
        return worker.dispatch(dict(op='season', request=number, action=action, **fields))
    def refused(action, **fields):
        before = snapshot()
        try: ask(action, **fields)
        except SeasonRequestError: pass
        else: raise AssertionError('expected pure refusal: '+action)
        assert snapshot() == before
    ask('open', state=initial); ask('advance')
    match = worker.session.pending_match
    def snapshot():
        return (match.memory_component(), tuple(match.m.reg(r) for r in REGS),
                copy.deepcopy(match.st), copy.deepcopy(match.opts), copy.deepcopy(match.inputs),
                copy.deepcopy(getattr(match, '_replay_actions', None)),
                getattr(match, '_replay_events', None),
                copy.deepcopy(match._frame_state()), worker.session.state,
                copy.deepcopy(vars(worker.session._keys)), worker.session.observe(),
                worker.decision, worker.exhausted, worker._decision_number,
                id(worker.stream), id(worker.seam), id(worker.session.pending_match))
    refused('preview', decision=1)  # no configuration/decision yet
    ask('configure'); refused('preview', decision=1)
    events = []
    def next_decision():
        while True:
            packet = ask('next', count=32); events.extend(packet['events'])
            if packet['decision'] is not None or packet['exhausted']: return packet
    packet = next_decision(); boundary = worker.session.state
    snapshots = []; edits = []
    def preview():
        decision = packet['decision']; before = snapshot()
        got = ask('preview', decision=decision)
        assert snapshot() == before
        assert set(got) == {'request', 'action', 'preview', 'state'}
        assert got['preview'] == {'schema': 'goal2/prematch-preview/1', 'decision': decision,
                                  'state_hash': canonical_hash(got['state'])}
        assert got['state'] == match.records_after()
        current = Image.from_state(got['state'], tables)
        assert current.squad(match.opts['managed']) == match.waiting['eleven'] + match.waiting['bench']
        assert current.countries()[match.opts['managed']][TACTICS] == match._tactics()
        players = current.players(); base = match.m.far(PLAYERS_PTR)
        words = set(match._pool())
        for country in match.waiting['team_context']['sides']:
            assert current.squad(country) == match._squad(country)
            assert current.countries()[country] == match.m.read(match._country(country), COUNTRY_SIZE)
            words.update(current.squad(country))
        for word in words:
            assert players[word] == match.m.read(base + PLAYER_SIZE*word, PLAYER_SIZE)
        snapshots.append(copy.deepcopy(got))
        got['state']['header'] = 'caller mutation'; got['preview']['decision'] = -1
        again = ask('preview', decision=decision)
        assert again['state'] == snapshots[-1]['state'] and snapshot() == before
        assert 'observation' not in again
        for invalid in (None, True, '1', decision+1): refused('preview', decision=invalid)
    if previews: preview()
    d = match.waiting; positions = dict(d['positions'])
    pair = next([a,b] for i,a in enumerate(d['eleven']) for b in d['eleven'][i+1:]
                if positions[a] == positions[b])
    pool_word = next(w for w in d['pool'] if match._available(w))
    for answer in ({'edit_only': True, 'substitutions': [pair]},
                   {'edit_only': True, 'tactics': {'8': not bool(d['tactics'] & 128)}},
                   {'edit_only': True, 'substitutions': [[d['bench'][-1], pool_word]]}):
        old = packet['decision']; edits.append(answer)
        ask('answer', decision=old, answer=answer)
        if previews: refused('preview', decision=old)  # consumed, before re-decision
        packet = next_decision()
        if previews:
            refused('preview', decision=old); preview()
    assert worker.session.state == boundary
    assert match.records_after() != boundary
    if previews:
        assert len({canonical_hash(s['state']) for s in snapshots}) == 4
    ask('answer', decision=packet['decision'], answer={})
    packet = ask('next', count=1); events.extend(packet['events'])
    if complete:
        while not packet['exhausted']:
            if packet['decision'] is not None:
                if previews: refused('preview', decision=packet['decision'])  # actual non-pre-match stop
                ask('answer', decision=packet['decision'], answer={})
            packet = next_decision()
        assert match.over
        final_memory = hashlib.sha256(match.memory_component()).hexdigest()
        registers = [match.m.reg(r) for r in REGS]
        result = ask('resume')
        assert result['observation']['status'] == 'complete'
        observed = ask('observe')
        assert observed['state'] == result['state']
        assert not observed['observation']['played_fixtures'] and not observed['observation']['news_pages']
        return dict(state_hash=canonical_hash(result['state']),
                    observation_hash=canonical_hash(result['observation']), memory=final_memory,
                    registers=registers, events=canonical_hash(events),
                    status=result['observation']['status'],
                    fixtures=len(result['observation']['played_fixtures']),
                    news_pages=len(result['observation']['news_pages']))
    return dict(initial=initial, boundary=boundary, snapshots=snapshots, edits=edits,
                after_play=packet, memory=hashlib.sha256(match.memory_component()).hexdigest(),
                registers=[match.m.reg(r) for r in REGS])


class PreviewWorker(unittest.TestCase):
    def test_actual_current_read_detaches_and_preserves_the_held_match(self):
        result = pypy_engine.call(__name__+':real_preview', reference_raw())
        self.assertEqual(len(result['snapshots']), 4)
        self.assertNotEqual(canonical_hash(result['snapshots'][-1]['state']), canonical_hash(result['boundary']))
        baseline = pypy_engine.call(__name__+':real_preview', reference_raw(), previews=False)
        self.assertGreater(result['after_play']['request'], baseline['after_play']['request'])
        self.assertEqual({k:v for k,v in result['after_play'].items() if k != 'request'},
                         {k:v for k,v in baseline['after_play'].items() if k != 'request'})
        self.assertEqual(result['memory'], baseline['memory'])
        self.assertEqual(result['registers'], baseline['registers'])

    @requires.need(slow=True)
    def test_actual_play_and_route_resume_are_identical_with_and_without_previews(self):
        raw = reference_raw()
        result = pypy_engine.call(__name__+':real_preview', raw, complete=True)
        self.assertEqual(result,
                         pypy_engine.call(__name__+':real_preview', raw, complete=True, previews=False))
        print('T170S_FULL '+json.dumps(result, sort_keys=True), flush=True)

    def test_no_session_and_wrong_context_are_pure_guards(self):
        from types import SimpleNamespace
        from goal2.game.season_worker import SeasonWorker, SeasonRequestError
        worker = SeasonWorker()
        def ask(action, **fields):
            return worker.dispatch(dict(op='season', request=1, action=action, **fields))
        self.assertRaises(SeasonRequestError, ask, 'preview', decision=1)
        value = state()
        match = SimpleNamespace(over=False, waiting={'context': 'stopped'})
        with patch('goal2.game.season.route.play_round', return_value=step('match', value, match=match)):
            ask('open', state=value); ask('advance')
        worker.seam = object(); worker.decision = 1
        before = worker.session.observe()
        self.assertRaises(SeasonRequestError, ask, 'preview', decision=1)
        self.assertIs(worker.session.pending_match, match)
        self.assertEqual(worker.decision, 1)
        self.assertEqual(worker.session.observe(), before)


class PreviewPipe(unittest.TestCase):
    make_engine = worker_tests.Pipe.make_engine
    receive = worker_tests.Pipe.receive
    def test_preview_over_real_pipe_and_repairable_stale_decision(self):
        expected = pypy_engine.call(__name__+':real_preview', reference_raw())
        engine = self.make_engine(); engine.season_open(expected['initial'])
        self.receive('ready'); self.receive('season')
        engine.season_request('advance'); self.receive('season')
        engine.season_request('preview', decision=1)
        self.assertFalse(self.receive('season_error')['lost'])
        engine.season_request('configure'); self.receive('season')
        for index, snapshot in enumerate(expected['snapshots']):
            while True:
                engine.season_request('next', count=32); packet = self.receive('season')
                if packet['decision'] is not None: break
            engine.season_request('preview', decision=packet['decision']+1)
            self.assertFalse(self.receive('season_error')['lost'])
            engine.season_request('preview', decision=packet['decision'])
            got = self.receive('season')
            self.assertEqual(canonical_hash(got['state']), canonical_hash(snapshot['state']))
            self.assertEqual(got['preview'], snapshot['preview'])
            self.assertNotIn('observation', got)
            answer = expected['edits'][index] if index < len(expected['edits']) else {}
            engine.season_request('answer', decision=packet['decision'], answer=answer)
            self.receive('season')
        engine.season_request('next', count=1)
        self.assertEqual(self.receive('season')['events'], expected['after_play']['events'])
        engine.season_request('observe')
        self.assertEqual(canonical_hash(self.receive('season')['state']), canonical_hash(expected['boundary']))


class PreviewWire(unittest.TestCase):
    def test_parent_validates_preview_identity_hash_and_busy_before_returning_it(self):
        from goal2.game.engine_process import EngineProcess
        from goal2.game.engine_server import ProtocolError
        value = state(); data = json.dumps(value).encode()
        for corrupt in ('schema', 'decision', 'bool-decision', 'hash', 'observation', 'json', None):
            engine = EngineProcess(lambda *args: None); engine._life = object(); engine._season_active = True
            with patch.object(engine, '_send'):
                for invalid in (None, True, '7', 0, -1):
                    self.assertRaises(ValueError, engine.season_request, 'preview', decision=invalid)
                    self.assertFalse(engine.busy)
                engine.season_request('preview', decision=7)
                self.assertRaises(ValueError, engine.season_request, 'preview', decision=7)
                self.assertRaises(ValueError, engine.season_request, 'answer', decision=7, answer={})
            preview = {'schema': 'goal2/prematch-preview/1', 'decision': 7, 'state_hash': canonical_hash(value)}
            reply = {'kind': 'season', 'value': {'request': 1, 'action': 'preview', 'preview': preview}}
            if corrupt == 'schema': preview['schema'] = 'observation'
            elif corrupt == 'decision': preview['decision'] = 8
            elif corrupt == 'bool-decision': preview['decision'] = True
            elif corrupt == 'hash': preview['state_hash'] = 'wrong'
            elif corrupt == 'observation': reply['value']['observation'] = {'output_hash': canonical_hash(value)}
            if corrupt is not None:
                self.assertRaises(ProtocolError, engine._decode, engine._life, reply,
                                  b'not-json' if corrupt == 'json' else data)
            else:
                kind, decoded = engine._decode(engine._life, reply, data)
                self.assertEqual((kind, decoded['state']), ('season', value))
                self.assertFalse(engine.busy)


if __name__ == '__main__': unittest.main()
