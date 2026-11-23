"""T234/#819: accepted SDK extension; root consumers stay on twenty."""
import copy
import hashlib
import json
from pathlib import Path
import unittest

from goal2.tests import pypy_engine
from goal2.tests.test_prematch_preview_t170s import reference_raw

SOURCE = 'a492059d4fc65d2ad5e8dca6074f627127331fe2'
ROOT = Path(__file__).resolve().parents[2]


def entry(raw):
    import sys
    from goal2.engine.original_match.image import Image
    from goal2.game import engine_tables
    from goal2.game.season import SeasonSession
    assert sys.implementation.name == 'pypy'
    session = SeasonSession(Image.from_bytes(raw).state(engine_tables.load()))
    assert session.advance().status == 'match'
    return session.pending_match


def snapshot(m):
    from goal2.engine.original_match.machine import MEM_SIZE, REGS
    return (hashlib.sha256(m.m.read(0, MEM_SIZE)).hexdigest(),
            tuple(m.m.reg(r) for r in REGS), copy.deepcopy(m.opts),
            copy.deepcopy(m.st), copy.deepcopy(m.inputs))


def decision(stream):
    for event in stream:
        if event.kind == 'decision':
            return event.data
    raise AssertionError('missing actual decision')


def admission(raw):
    ordinary, empty = entry(raw), entry(raw)
    ordinary.configure_route_entry()
    empty.configure_route_entry(extra_players=[])
    assert snapshot(ordinary) == snapshot(empty)
    assert 'extra_players' not in ordinary.opts and 'national_roster' not in ordinary.st
    pool = ordinary._pool(); core = ordinary._squad(ordinary.opts['managed'])
    foreign = next(w for w in range(1, 3061) if w not in pool + core)
    bad = (False, True, '22', [True], [0], [3061], [pool[0]]*2,
           pool[:5], [core[0]], [foreign])
    for extras in bad:
        m = entry(raw); before = snapshot(m)
        try:
            m.configure_route_entry(extra_players=extras)
        except ValueError:
            pass
        else:
            raise AssertionError(('invalid extra accepted', extras))
        assert snapshot(m) == before
        m.configure_route_entry()  # The same unconsumed entry remains repairable.
    return dict(invalid=len(bad), default_equal=True)


def full_bench(raw, count):
    from goal2.engine.original_match.match import Match
    m = entry(raw); core = m._squad(m.opts['managed'])
    off, on = next((a, b) for a in core[1:11] for b in m._pool()
                   if m._available(a) and m._available(b)
                   and m._player(a, 6) == m._player(b, 6))
    extras = [on] + [w for w in m._pool() if w != on and m._available(w)
                     and m._player(w, 6) > 0][:count-1]
    members = set(core + extras); before = snapshot(m)
    m.configure_route_entry(extra_players=extras, pre_match_edits=True, live_players=True)
    assert snapshot(m)[:2] == before[:2]
    extras[0] = 0
    assert 0 not in m.opts['extra_players']
    stream = iter(m.events()); d = decision(stream)
    assert len(d['bench']) == 9 + count
    assert set(d['eleven'] + d['bench']) == members
    assert len(d['player_records']) == 20 + count
    m.answer(edit_only=True, substitutions=[(off, on)])
    d = decision(stream)
    assert on in d['eleven'] and off not in d['eleven']
    assert set(d['national_squad']) == members and off in d['bench']
    assert len(m._squad(m.opts['managed'])) == 20 and len(m._pool()) == 80
    assert set(m._squad(m.opts['managed'])).isdisjoint(m._pool())
    loaded = Match.load(m.save())
    assert loaded.waiting == m.waiting and snapshot(loaded) == snapshot(m)
    return dict(selected=len(members), bench=len(d['bench']), save_equal=True)


def halftime(raw, count):
    from goal2.engine.original_match.match import Match
    from goal2.engine.original_match import screens as S
    m = entry(raw)
    extras = [w for w in m._pool() if m._available(w) and m._player(w, 6) > 0][:count]
    members = set(m._squad(m.opts['managed']) + extras)
    m.configure_route_entry(extra_players=extras, pre_match_edits=True,
                            live_players=True, substitutions=5)
    stream = iter(m.events()); decision(stream); m.answer(quick=True)
    while True:
        d = decision(stream)
        if d['context'] == 'half_time': break
        m.answer(quick=True)
    assert len(d['bench']) == 9 + count and set(d['national_squad']) == members
    native = m._squad(m.opts['managed'])
    on = next(w for w in d['bench'] if w not in native and m._available(w))
    off = next(w for w in reversed(d['eleven']) if m._player(w, 6) > 0)
    budget = d['substitutions_left']; m.answer(substitutions=[(off, on)], quick=True)
    for event in stream:
        if event.kind == 'substitution': break
        if event.kind == 'decision': m.answer(quick=True)
    else: raise AssertionError('missing original substitution')
    assert on in m._squad(m.opts['managed'])[:11]
    assert off not in m._squad(m.opts['managed'])[:11] and not m._available(off)
    assert m.m.rd(S.SUBS_LEFT + m.side, 1) == budget - 1
    assert set(m._selected_squad()) == members
    loaded = Match.load(m.save()); assert snapshot(loaded) == snapshot(m)
    def finish(match, events):
        result = []
        for event in events:
            result.append((event.kind, event.minute, event.data))
            if event.kind == 'decision': match.answer(quick=True)
        return result
    remaining = finish(m, stream); resumed = finish(loaded, iter(loaded.events()))
    assert resumed == remaining
    assert loaded.result() == m.result() and loaded.records_after() == m.records_after()
    assert snapshot(loaded) == snapshot(m)
    assert set(m.result()['national_squad_after']) == members
    return dict(selected=len(members), final_equal=True, remaining_budget=budget-1)


class ExtendedBenchKit(unittest.TestCase):
    def test_source_inventory_is_the_accepted_bounded_adoption(self):
        manifest = json.loads((ROOT/'tools/watched-kit-hashes.json').read_text())
        self.assertEqual(manifest['source'], SOURCE)
        for rel, digest in manifest['files'].items():
            self.assertEqual(hashlib.sha256((ROOT/rel).read_bytes()).hexdigest(), digest)

    def test_default_and_invalid_extra_configuration_are_pure(self):
        result = pypy_engine.call(__name__+':admission', reference_raw())
        self.assertEqual(result, dict(invalid=10, default_equal=True))

    def test_partial_and_full_bench_native_promotion_and_waiting_save(self):
        for count in (1, 2, 3, 4):
            with self.subTest(count=count):
                result = pypy_engine.call(__name__+':full_bench', reference_raw(), count)
                self.assertEqual(result, dict(selected=20+count, bench=9+count, save_equal=True))

    def test_actual_halftime_extra_substitution_and_final_replay(self):
        for count in (2, 4):
            with self.subTest(count=count):
                result = pypy_engine.call(__name__+':halftime', reference_raw(), count)
                self.assertEqual(result['selected'], 20+count)
                self.assertTrue(result['final_equal'])
                self.assertEqual(result['remaining_budget'], 4)


if __name__ == '__main__': unittest.main()
