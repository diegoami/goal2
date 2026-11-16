"""[designed: T170k/T170m, #726] The window's pre-kick-off sequence over the held-Match seam.

T170i's mapping (#718): on the SeasonSession's held pending route Match, the window's
S10 tactic value, S08 within-twenty swap, pool exchange, declared captain and play map
onto T132's pre-match decision answers. The pool arm is live in the kit since T170l
(archaeology #713 at e02711cb), so [T170m] the exchange is a real answer; T170k's named
refusal retired with it. Mock-only controls here check the translation; the real proof is
the source-bound PyPy control: the exact window sequence through the seam equals the same
answers given directly on a second session built from the same accepted state.
"""
import unittest

from goal2.game.prematch_seam import PrematchSeam


class _StubMatch:
    def __init__(self):
        self.configured = None
        self.answers = []

    def configure_route_entry(self, **kwargs):
        self.configured = kwargs

    def answer(self, **kwargs):
        self.answers.append(kwargs)


class SeamMapping(unittest.TestCase):
    """Mock-only controls: the translation and the named refusal. The source-bound PyPy
    control below carries the actual proof (mock-only cannot satisfy it)."""

    def test_configuration_is_once_and_exactly_the_seam_flags(self):
        m = _StubMatch()
        PrematchSeam(m, captain=121, substitutions=2)
        self.assertEqual(m.configured, {'captain': 121, 'substitutions': 2, 'pre_match_edits': True,
                                        'live_players': True, 'set_piece': True,
                                        'substitution_control': True, 'record_draws': True})

    def test_the_window_actions_translate_to_one_answer_each(self):
        m = _StubMatch()
        seam = PrematchSeam(m)
        seam.set_team_tactic(8, True)
        seam.swap(121, 131)
        seam.exchange(122, 2561)                     # [T170m] the pool control is the same answer
        seam.play()
        self.assertEqual(m.answers, [{'edit_only': True, 'tactics': {8: True}},
                                     {'edit_only': True, 'substitutions': [[121, 131]]},
                                     {'edit_only': True, 'substitutions': [[122, 2561]]},
                                     {}])

    def test_late_captain_play_preserves_word_default_and_omission(self):
        m = _StubMatch()
        seam = PrematchSeam(m)
        seam.play(captain=2614)
        seam.play(captain=None)
        seam.play()
        self.assertEqual(m.answers, [{'captain': 2614}, {'captain': None}, {}])


def seam_sequence(raw, element=8, budget=2, late_captain=False):
    """Actual PyPy dispatcher, no original backend fallback: the window's exact pre-kick-off
    sequence through the seam, and the same answers given directly, on two SeasonSessions
    built from one accepted state. The two paths must stop identically after the swap."""
    import builtins, hashlib, json, sys
    assert sys.implementation.name == 'pypy' and sys.version_info[:2] == (3, 11)
    original_import = builtins.__import__

    def denied(name, *args, **kwargs):
        if name == 'unicorn' or name.startswith('unicorn.'):
            raise ImportError('T170k positive Unicorn denial')
        return original_import(name, *args, **kwargs)

    builtins.__import__ = denied
    try:
        __import__('unicorn')
    except ImportError:
        pass
    else:
        raise AssertionError('Unicorn denial inactive')
    from goal2.engine.original_match import route
    from goal2.engine.original_match.image import Image
    from goal2.engine.original_match.machine import MEM_SIZE, REGS, Uc
    from goal2.game import engine_tables
    from goal2.game.season import SeasonSession
    from goal2.game.prematch_seam import PrematchSeam
    assert Uc is None
    tables = engine_tables.load()
    value = Image.from_bytes(raw).state(tables)

    def run(via_seam):
        keys = route.Keys(route.DEFAULT_KEYS)
        session = SeasonSession(value, tables, keys)
        assert session.advance().status == 'match'
        match = session.pending_match
        assert match is not None and not match.over
        squad = match._squad(match.opts['managed'])
        captain = squad[0]                               # the S16 choice: an eligible eleven word
        accepted_captains = []
        prompt_role = [False]
        def prompt(replay):
            if not replay:
                prompt_role[0] = match.m.stack_word(2) == 1 and match.m.stack_word(4) == match.side
        def accepted(replay):
            if not replay and prompt_role[0]:
                accepted_captains.append(match.m.reg('ax'))
                prompt_role[0] = False
        match.m.at('0791:CC7B', prompt)
        match.m.at('0791:D010', accepted)

        def decision():
            for ev in match.events():
                if ev.kind == 'decision' and ev.data['context'] == 'pre_match':
                    return ev.data
            raise AssertionError('no pre_match decision')

        def seam_or_direct(exchange=False, **answer):
            if via_seam:
                if 'captain' in answer:
                    seam.play(captain=answer['captain'])
                elif 'tactics' in answer:
                    seam.set_team_tactic(element, answer['tactics'][element])
                elif 'substitutions' in answer:
                    off, on = answer['substitutions'][0]
                    (seam.exchange if exchange else seam.swap)(off, on)
                else:
                    seam.play()
            else:
                # [confirmed: archaeology #711/#713] the same answers given directly: edits are
                # edit_only answers (the pool word included, at a pre-match edit), play is empty.
                match.answer(edit_only=bool(answer) and 'captain' not in answer, **answer)

        if via_seam:
            seam = PrematchSeam(match, captain=captain, substitutions=budget)
        else:
            match.configure_route_entry(captain=captain, substitutions=budget, pre_match_edits=True,
                                        live_players=True, set_piece=True, substitution_control=True,
                                        record_draws=True)
        first = decision()
        want = not bool(first['tactics'] >> (element - 1) & 1)
        seam_or_direct(tactics={element: want})
        second = decision()
        pos = dict((w, c) for w, c in second['positions'])
        off = second['eleven'][-1]
        on = next(w for w in second['bench'] if w and pos.get(w) == pos[off])
        seam_or_direct(substitutions=[[off, on]])
        third = decision()
        # [T170m] the pool exchange: a made-pool word in, the same position out (EA09's rule at
        # play; the pool is published in the decision beside the bench).
        from goal2.engine.original_match.match import PLAYER_POSITION
        pool_off = third['eleven'][-1]
        pool_word = next(w for w in third['pool'] if match._player(w, PLAYER_POSITION) == pos[pool_off])
        seam_or_direct(exchange=True, substitutions=[[pool_off, pool_word]])
        fourth = decision()
        stop_hash = hashlib.sha256(match.m.read(0, MEM_SIZE)).hexdigest()
        seam_or_direct(**({'captain': pool_word} if late_captain else {}))
        kinds = []
        for ev in match.events():
            kinds.append(ev.kind)
            if ev.kind == 'minute':
                break
        keep = ('context', 'eleven', 'bench', 'tactics')
        assert accepted_captains == [pool_word if late_captain else captain]
        strip = lambda d: {k: d.get(k) for k in keep} | {'edited': d.get('edited')}
        return dict(captain=captain, off=off, on=on, want=want, pool_off=pool_off, pool_word=pool_word,
                    first=strip(first), second=strip(second), third=strip(third), fourth=strip(fourth),
                    pool_keeps_off=pool_off in fourth['pool'], pool_loses_word=pool_word not in fourth['pool'],
                    stop_hash=stop_hash, play_hash=hashlib.sha256(match.m.read(0, MEM_SIZE)).hexdigest(),
                    accepted_captains=accepted_captains,
                    registers={r: match.m.reg(r) for r in REGS},
                    draws_sha256=hashlib.sha256(json.dumps(match.st['draws']).encode()).hexdigest(),
                    kinds=kinds, minute=match.st['minute'],
                    substitution_events=len(match.st['log']['substitutions']))

    receipt = {'seam': run(True), 'direct': run(False), 'unicorn_denied': True,
               'element': element, 'budget': budget}
    assert 'unicorn' not in sys.modules
    return receipt


class ActualSeamSequence(unittest.TestCase):
    def test_late_pool_captain_after_all_edits_equals_direct_answers(self):
        from pathlib import Path
        from goal2.engine.original_match.assets import REFERENCE, reference_image
        from goal2.tests import requires, pypy_engine
        requires.require(files=(REFERENCE['asset'],))
        raw = reference_image(Path(__file__).resolve().parents[2] / '.cache')
        receipt = pypy_engine.call(__name__ + ':seam_sequence', raw, late_captain=True)
        self.assertEqual(receipt['seam'], receipt['direct'])
        for path in (receipt['seam'], receipt['direct']):
            self.assertEqual(path['accepted_captains'], [path['pool_word']])
        print('T170P_LATE_CAPTAIN ' + __import__('json').dumps(receipt, sort_keys=True), flush=True)

    def test_the_windows_sequence_through_the_seam_equals_the_same_answers_direct(self):
        import json
        from pathlib import Path
        from goal2.engine.original_match.assets import REFERENCE, reference_image
        from goal2.tests import requires, pypy_engine
        requires.require(files=(REFERENCE['asset'],))
        raw = reference_image(Path(__file__).resolve().parents[2] / '.cache')
        receipt = pypy_engine.call(__name__ + ':seam_sequence', raw)
        seam, direct = receipt['seam'], receipt['direct']
        self.assertTrue(receipt['unicorn_denied'])
        for path in (seam, direct):
            self.assertEqual((path['first']['context'], path['first'].get('edited')), ('pre_match', None))
            self.assertEqual(path['second']['edited'], True)
            self.assertEqual(path['third']['edited'], True)
            self.assertEqual(path['fourth']['edited'], True)
            self.assertIn(path['on'], path['third']['eleven'])
            self.assertNotIn(path['off'], path['third']['eleven'])
            self.assertIn(path['pool_word'], path['fourth']['eleven'])
            self.assertNotIn(path['pool_off'], path['fourth']['eleven'])
            self.assertTrue(path['pool_keeps_off'] and path['pool_loses_word'])   # the word-list exchange
            self.assertEqual(bool(path['fourth']['tactics'] >> (receipt['element'] - 1) & 1), path['want'])
            self.assertIn('commentary', path['kinds'])
            self.assertIn('minute', path['kinds'])
            self.assertGreaterEqual(path['minute'], 1)
            self.assertEqual(path['substitution_events'], 0)
        self.assertEqual(seam, direct)                    # same decisions, same elevens, same kick-off
        self.assertEqual(seam['stop_hash'], direct['stop_hash'])   # identical stop after the swap
        print('T170K_SEAM ' + json.dumps(receipt, sort_keys=True), flush=True)


if __name__ == '__main__':
    unittest.main()
