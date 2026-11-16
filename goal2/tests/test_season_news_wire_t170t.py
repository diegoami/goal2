"""[designed: T170t/#751] Lossless season news transport, not a save format.

[confirmed: archaeology fb6d3093, F039] NewsPageMemory carries 4000 raw
character/attribute bytes and provenance. Actual original cells never enter logs.
"""
import base64
import copy
import hashlib
import io
import json
import unittest
from dataclasses import asdict
from unittest.mock import patch

from goal2.engine.original_match.news import NewsPageMemory
from goal2.game.season import SeasonObservation, canonical_hash
from goal2.tests import pypy_engine, requires
from goal2.tests.test_season_session_t170b import state
from goal2.tests import test_season_worker_t170o as worker_tests


def digest(value):
    """Independent, typed comparison of every byte/value; only hashes are printed."""
    def data(item):
        if isinstance(item, bytes): return {'bytes.hex': item.hex()}
        if isinstance(item, tuple): return {'tuple': [data(v) for v in item]}
        if isinstance(item, list): return [data(v) for v in item]
        if isinstance(item, dict): return {k: data(v) for k,v in item.items()}
        return item
    return canonical_hash(data(value))


def pages():
    # Synthetic, covering every possible byte and distinct provenance.
    cells = (bytes(range(256))*16)[:4000]
    a = asdict(NewsPageMemory(cells, buffer_address=0x90000, data_segment=0x3000,
                             return_address='000E:05F6', country=27, side=0, manager=129,
                             flags_words=(0, 65535, 128), waiting_key=13, pushed_back=True,
                             key_code=13, seed_words=(1234, 65535)))
    b = copy.deepcopy(a); b.update(country=7, side=1, pushed_back=False, waiting_key=None)
    return (a, b, copy.deepcopy(a))


def observation(value, news):
    return asdict(SeasonObservation(1, 'complete', canonical_hash(value), canonical_hash(value),
                                  ({'fixture': 1, 'score': (2, 1)},), news, (1234, 5678)))


def packet(action, obs):
    from goal2.game.engine_server import Server, read_packet
    output = io.BytesIO(); server = Server(io.BytesIO(), output)
    result = {'request': 1, 'action': action, 'state': state(), 'observation': obs}
    with patch.object(server.season, 'dispatch', return_value=copy.deepcopy(result)):
        payload = json.dumps({'state': state(), 'keys': None}).encode() if action == 'open' else b''
        server._season({'op': 'season', 'request': 1, 'action': action}, payload)
    output.seek(0)
    return read_packet(output)


def parent(action):
    from goal2.game.engine_process import EngineProcess
    engine = EngineProcess(lambda *args: None); engine._life = object(); engine._season_active = True
    with patch.object(engine, '_send'):
        if action == 'open': engine.season_open(state())
        else: engine.season_request(action)
    return engine


class NewsWire(unittest.TestCase):
    def test_actual_server_and_parent_round_trip_all_cells_provenance_and_duplicates(self):
        value = state()
        for action in ('open', 'advance', 'resume', 'observe'):
            with self.subTest(action=action):
                news = pages() if action in ('advance', 'resume') else ()
                expected = observation(value, news); before = copy.deepcopy(expected)
                header, payload = packet(action, expected)
                self.assertEqual(header['kind'], 'season')
                engine = parent(action)
                kind, decoded = engine._decode(engine._life, header, payload)
                self.assertEqual(kind, 'season')
                self.assertTrue(decoded['observation'] == expected, 'lossy news/tuple transport')
                self.assertEqual(canonical_hash(decoded['state']), canonical_hash(value))
                self.assertIsInstance(decoded['observation']['news_pages'], tuple)
                self.assertFalse(engine.busy)
                if news:
                    first = decoded['observation']['news_pages'][0]
                    self.assertIs(type(first['cells']), bytes)
                    self.assertIs(type(first['flags_words']), tuple)
                    self.assertEqual(len(first['cells']), 4000)
                    first['country'] = -1
                    self.assertEqual(decoded['observation']['news_pages'][2]['country'], 27)
                self.assertTrue(expected == before, 'transport mutated caller observation')

    def test_malformed_news_and_corrupt_state_hash_do_not_reach_the_callback(self):
        from goal2.game.engine_server import ProtocolError
        from goal2.game.session_save import _restore_json_value
        header, payload = packet('resume', observation(state(), pages()))
        self.assertEqual(header['kind'], 'season')
        clean = _restore_json_value(header['value'], 'test')
        for bad in ('schema', 'base64', 'length', 'raw-cells', 'flags', 'seed',
                    'country', 'bool-int', 'pushed', 'address', 'missing', 'extra', 'pages', 'hash'):
            with self.subTest(bad=bad):
                value = copy.deepcopy(clean); page = value['observation']['news_pages'][0]
                if bad == 'schema': page['cells']['schema'] = 'save'
                elif bad == 'base64': page['cells']['base64'] = '!'*len(page['cells']['base64'])
                elif bad == 'length': page['cells']['base64'] = base64.b64encode(bytes(3999)).decode('ascii')
                elif bad == 'raw-cells': page['cells'] = bytes(4000)
                elif bad == 'flags': page['flags_words'] = (1, 2)
                elif bad == 'seed': page['seed_words'] = (1, -1)
                elif bad == 'country': page['country'] = '27'
                elif bad == 'bool-int': page['key_code'] = True
                elif bad == 'pushed': page['pushed_back'] = 1
                elif bad == 'address': page['return_address'] = 12
                elif bad == 'missing': del page['cells']
                elif bad == 'extra': page['unknown'] = 1
                elif bad == 'pages': value['observation']['news_pages'] = list(value['observation']['news_pages'])
                elif bad == 'hash': value['observation']['output_hash'] = 'wrong'
                engine = parent('resume')
                self.assertRaises(ProtocolError, engine._decode, engine._life,
                                  {'kind': 'season', 'value': value}, payload)

    def test_invalid_producer_metadata_refuses_and_generic_saves_still_reject_bytes(self):
        from goal2.game.session_save import _json_value
        self.assertRaises(TypeError, _json_value, bytes(4000))
        news = list(pages()); news[0]['country'] = True
        header, _ = packet('resume', observation(state(), tuple(news)))
        self.assertEqual(header['kind'], 'season_error')
        self.assertTrue(header['value']['lost'])


def answer(packet):
    # [designed: proof policy] No roster/tactical edits; dismiss optional offers,
    # use the native default for captain, takers and other stopped decisions.
    if packet['events'][-1]['data'].get('context') == 'substitution_opportunity':
        return {'opportunity': 'dismiss'}
    return {}


def direct_round(initial):
    import sys
    from goal2.engine.original_match.machine import Uc
    from goal2.game.season_worker import SeasonWorker
    assert sys.implementation.name == 'pypy' and sys.version_info[:2] == (3, 11) and Uc is None
    worker = SeasonWorker(); number = 0; events = []; preview_hash = None
    def ask(action, **fields):
        nonlocal number
        number += 1
        return worker.dispatch(dict(op='season', request=number, action=action, **fields))
    ask('open', state=initial); boundary = ask('advance')
    assert boundary['observation']['status'] == 'match'
    ask('configure')
    while True:
        got = ask('next', count=32); events.extend(got['events'])
        if got['decision'] is not None:
            if preview_hash is None:
                preview_hash = ask('preview', decision=got['decision'])['preview']['state_hash']
            ask('answer', decision=got['decision'], answer=answer(got))
        if got['exhausted']: break
    result = ask('resume')
    return dict(boundary_hash=canonical_hash(boundary['state']), preview_hash=preview_hash,
                state_hash=canonical_hash(result['state']), observation_hash=digest(result['observation']),
                events_hash=digest(events), fixtures=len(result['observation']['played_fixtures']),
                news=len(result['observation']['news_pages']), status=result['observation']['status'])


class FullPipe(unittest.TestCase):
    make_engine = worker_tests.Pipe.make_engine
    receive = worker_tests.Pipe.receive

    @requires.need(slow=True)
    def test_actual_complete_round_matches_direct_worker_and_delivers_news_once(self):
        from goal2.engine.original_match.image import Image
        from goal2.game import engine_tables
        from goal2.tests.test_prematch_preview_t170s import reference_raw
        initial = Image.from_bytes(reference_raw()).state(engine_tables.load())
        control = pypy_engine.start(__name__+':direct_round', initial)
        self.addCleanup(control._finalizer)
        engine = self.make_engine(); engine.season_open(initial)
        ready = self.receive('ready'); self.assertEqual(ready['implementation'], 'PyPy')
        self.assertEqual(ready['version'], [3, 11]); self.receive('season')
        engine.season_request('advance'); boundary = self.receive('season')
        self.assertEqual(boundary['observation']['status'], 'match')
        engine.season_request('configure'); self.receive('season')
        events = []; preview_hash = None
        while True:
            engine.season_request('next', count=32); got = self.receive('season'); events.extend(got['events'])
            if got['decision'] is not None:
                if preview_hash is None:
                    engine.season_request('preview', decision=got['decision']+1)
                    self.assertFalse(self.receive('season_error')['lost'])
                    engine.season_request('preview', decision=got['decision'])
                    preview_hash = self.receive('season')['preview']['state_hash']
                engine.season_request('answer', decision=got['decision'], answer=answer(got))
                self.receive('season')
            if got['exhausted']: break
        engine.season_request('resume'); result = self.receive('season')
        actual = dict(boundary_hash=canonical_hash(boundary['state']), preview_hash=preview_hash,
                      state_hash=canonical_hash(result['state']), observation_hash=digest(result['observation']),
                      events_hash=digest(events), fixtures=len(result['observation']['played_fixtures']),
                      news=len(result['observation']['news_pages']), status=result['observation']['status'])
        self.assertEqual(actual, control.result())
        self.assertEqual(actual['status'], 'complete'); self.assertGreater(actual['news'], 0)
        for _ in range(2):
            engine.season_request('observe'); seen = self.receive('season')
            self.assertEqual(canonical_hash(seen['state']), actual['state_hash'])
            self.assertEqual(seen['observation']['played_fixtures'], ())
            self.assertEqual(seen['observation']['news_pages'], ())
        self.assertTrue(engine.season_active)
        print('T170T_FULL '+json.dumps(actual, sort_keys=True), flush=True)


if __name__ == '__main__': unittest.main()
