"""[designed: T183e/#773] Explicit native assistant at completed boundaries.

Synthetic boundary controls test session ownership, not original calendar rules.
Actual cases use original manager states and the genuine G4B finals fixture.
"""
import copy
import unittest
from unittest.mock import patch

from goal2.game.season import SeasonSession, canonical_hash
from goal2.tests.test_season_session_t170b import state, step


def reply(value, allowed=True):
    return dict(state=copy.deepcopy(value), allowed=allowed,
                refusal=None if allowed else 'finals', country=7, manager=1,
                changed=True, recruited=[42], calls={'1771:52CC': 1, '0791:DC7E': 1})


class Ownership(unittest.TestCase):
    def test_complete_boundary_keeps_round_keys_and_once_only_deltas(self):
        from goal2.engine.original_match.route import Keys
        from goal2.engine.original_match import Image
        from goal2.game import engine_tables
        value = state()
        image = Image.from_state(value, engine_tables.load())
        image.memory[image.DS*16+0x7B62] ^= 1  # Synthetic candidate control only.
        selected = image.state(engine_tables.load())
        keys = Keys({'site': 13}); keys.poll('site')
        page, fixture = {'text': ['page']}, {'fixture': 1, 'score': [2, 1]}
        session = SeasonSession(value, keys=keys)
        with patch('goal2.game.season.route.play_round', side_effect=[
                step('complete', value, (fixture,), (page,)),
                step('complete', selected, (fixture,), (page,))]) as play:
            first = session.advance()
            cursors = session._fixture_cursor, session._news_cursor
            answer = reply(selected)
            with patch('goal2.game.best_twenty.recommend', return_value=answer):
                result = session.select_twenty()
            self.assertEqual(session.state, selected)
            observed = result['observation']
            self.assertEqual((observed.status, observed.call_number, observed.input_hash),
                             (first.status, first.call_number, first.input_hash))
            self.assertEqual(observed.output_hash, canonical_hash(selected))
            self.assertEqual(observed.played_fixtures, ())
            self.assertEqual(observed.news_pages, ())
            self.assertEqual((session._fixture_cursor, session._news_cursor), cursors)
            self.assertEqual(keys.waiting, 13)
            self.assertIs(session._keys, keys)
            result['selection']['recruited'].append(99)
            answer['state']['header'] = 'caller corruption'
            self.assertEqual(session.state, selected)
            again = session.advance()
            self.assertEqual((again.call_number, len(again.played_fixtures), len(again.news_pages)), (2, 1, 1))
            self.assertEqual(play.call_args_list[1].args[0], selected)
            self.assertIs(play.call_args_list[1].args[2], keys)

    def test_refusal_never_retains_or_exposes_private_candidate(self):
        value = state(); session = SeasonSession(value); before = session.observe()
        answer = reply({'schema': 'discard this refused private candidate'}, allowed=False)
        with patch('goal2.game.best_twenty.recommend', return_value=answer):
            result = session.select_twenty()
        self.assertEqual(session.state, value)
        self.assertEqual(session.observe(), before)
        self.assertEqual(result['observation'], before)
        self.assertEqual(result['selection']['refusal'], 'finals')
        self.assertFalse(result['selection']['changed'])
        self.assertEqual(result['selection']['recruited'], [])
        self.assertNotIn('state', result['selection'])

    def test_errors_and_malformed_allowed_candidate_preserve_boundary(self):
        session = SeasonSession(state()); before = session.state; observed = session.observe()
        def failed(value):
            value['header'] = 'backend changes its private input'
            raise RuntimeError('backend failed')
        for backend, error in ((failed, RuntimeError), (lambda value: reply({'schema': 'bad'}), ValueError)):
            with self.subTest(error=error), patch('goal2.game.best_twenty.recommend', side_effect=backend):
                self.assertRaises(error, session.select_twenty)
            self.assertEqual(session.state, before)
            self.assertEqual(session.observe(), observed)

    def test_held_and_terminal_boundaries_refuse_before_helper(self):
        for status in ('match', 'deferred-rollover'):
            with self.subTest(status=status):
                session = SeasonSession(state()); token = object()
                held = object() if status == 'match' else None
                with patch('goal2.game.season.route.play_round', return_value=step(
                        status, state(), match=held, continuation=token if held else None)):
                    session.advance()
                before = session.observe()
                with patch('goal2.game.best_twenty.recommend', side_effect=AssertionError('helper entered')):
                    self.assertRaises(ValueError, session.select_twenty)
                self.assertEqual(session.observe(), before)
                self.assertIs(session.pending_match, held)


def actual(value, advance=False):
    """Actual production Session operation under positive backend/EXE denial."""
    import builtins
    import io
    import sys
    from pathlib import Path
    from goal2.engine.original_match import route
    from goal2.engine.original_match.machine import REGS, MEM_SIZE, Uc
    from goal2.game.best_twenty import recommend
    assert sys.implementation.name == 'pypy' and Uc is None
    original_import, original_open = builtins.__import__, io.open
    def denied(name, *args, **kwargs):
        if name == 'unicorn' or name.startswith('unicorn.'):
            raise ImportError('T183e Unicorn denied')
        return original_import(name, *args, **kwargs)
    def no_exe(file, *args, **kwargs):
        if isinstance(file, (str, bytes, Path)) and str(file).lower().endswith('.exe'):
            raise AssertionError('T183e EXE read denied')
        return original_open(file, *args, **kwargs)
    with patch('builtins.__import__', denied), patch('io.open', no_exe), patch('builtins.open', no_exe):
        try: __import__('unicorn')
        except ImportError: pass
        else: raise AssertionError('Unicorn denial inactive')
        try: Path('GOAL.EXE').read_bytes()
        except AssertionError: pass
        else: raise AssertionError('EXE denial inactive')
        expected = recommend(copy.deepcopy(value))
        keys = route.Keys(route.DEFAULT_KEYS)
        session = SeasonSession(value, keys=keys)
        before = session.observe(); original = copy.deepcopy(value)
        result = session.select_twenty()
        assert value == original and keys.waiting is None
        assert result['selection']['allowed'] == expected['allowed']
        assert result['selection']['refusal'] == expected['refusal']
        assert result['observation'].call_number == 0
        assert result['observation'].input_hash == before.input_hash
        assert result['observation'].news_pages == result['observation'].played_fixtures == ()
        assert session.state == (expected['state'] if expected['allowed'] else value)
        selected = session.state
        if expected['allowed']:
            expected_again = recommend(selected)
            repeated = session.select_twenty()
            assert session.state == expected_again['state']
            assert repeated['selection']['recruited'] == expected_again['recruited'] == []
        if advance:
            reference = route.play_round(session.state, session._tables, route.Keys(route.DEFAULT_KEYS))
            next_round = session.advance()
            assert session.state == reference.state and next_round.status == reference.status == 'match'
            match, parent = session.pending_match, session._continuation.m
            assert match.m.read(0, MEM_SIZE) == reference.match.m.read(0, MEM_SIZE)
            assert {r: match.m.reg(r) for r in REGS} == {r: reference.match.m.reg(r) for r in REGS}
            memory, registers = match.m.read(0, MEM_SIZE), {r: match.m.reg(r) for r in REGS}
            parent_memory, parent_regs = parent.read(0, MEM_SIZE), {r: parent.reg(r) for r in REGS}
            boundary = session.observe(); key_state = copy.deepcopy(vars(keys))
            continuation = session._continuation
            with patch('goal2.game.best_twenty.recommend', side_effect=AssertionError('held helper entered')):
                try: session.select_twenty()
                except ValueError: pass
                else: raise AssertionError('held selection accepted')
            assert session.pending_match is match and session._continuation is continuation
            assert session.observe() == boundary and vars(keys) == key_state
            assert match.m.read(0, MEM_SIZE) == memory and {r: match.m.reg(r) for r in REGS} == registers
            assert parent.read(0, MEM_SIZE) == parent_memory and {r: parent.reg(r) for r in REGS} == parent_regs
    return dict(result=result['selection'], state=selected, advance=advance)


class Native(unittest.TestCase):
    def test_original_opening_and_following_actual_route_entry(self):
        from goal2.tests.test_best_twenty_t183a import OriginalAction, records
        from goal2.tests.pypy_engine import call
        from goal2.engine.original_match import Image
        from goal2.game import engine_tables
        driver = OriginalAction().source()
        value = Image.from_memory_component(driver.wait.state.memory_component()).state(engine_tables.load())
        original = OriginalAction().compare(driver)
        observed = call(__name__+':actual', value, True)
        self.assertTrue(observed['result']['allowed'])
        self.assertEqual(records(Image.from_state(observed['state'], engine_tables.load())),
                         records(Image.from_state(original['state'], engine_tables.load())))

    def test_genuine_finals_refusal_keeps_native_session(self):
        from goal2.tests import requires
        from goal2.tests.test_best_twenty_finals_t183d import FIXTURE, REPORT
        requires.require(modules=('unicorn',), files=(FIXTURE, 'GOAL.DAT'))
        import hashlib, json
        from goal2.core import Core
        from goal2.core.driver import Driver
        from goal2.engine.original_match import Image
        from goal2.game import engine_tables
        from goal2.tests.pypy_engine import call
        from goal2.tests.test_best_twenty_t183a import OriginalAction
        raw = (requires.CACHE/FIXTURE).read_bytes()
        self.assertEqual(hashlib.sha256(raw).hexdigest(), json.loads(REPORT.read_text())['fixture']['sha256'])
        driver = Driver(Core.load(raw, goal_dat=requires.CACHE/'GOAL.DAT'))
        value = Image.from_memory_component(driver.wait.state.memory_component()).state(engine_tables.load())
        original = OriginalAction().compare(driver)
        observed = call(__name__+':actual', value)
        self.assertEqual(observed['result']['refusal'], original['refusal'])
        self.assertFalse(observed['result']['allowed'])
        self.assertEqual(observed['state'], value)
