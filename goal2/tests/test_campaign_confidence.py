"""[designed: T43] Literal F019/F020 cases and campaign confidence transactions."""
import copy
import tempfile
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import unittest

from goal2.game import campaign_confidence as confidence
from goal2.game import campaign_energy as energy
from goal2.game.quick_match import run_full_match
from goal2.engine.quick_engine import QuickMatch
from goal2.engine.savestate import Savestate
from goal2.game.state import to_savestate
from goal2.web.server import WebSession, StalePlaySubmission
from goal2.tests import requires

ROOT = Path(__file__).resolve().parents[2]


def player(form=16, current=16, status=0):
    r = bytearray(20)
    r[12], r[13], r[14], r[16] = form, 16, current, status
    return bytes(r)


class Draws:
    def __init__(self, values):
        self.values = iter(values)
        self.bounds = []
        self.draws = 0
    def rand(self, bound):
        self.bounds.append(bound)
        self.draws += 1
        return next(self.values)


class ConfidenceReferenceCases(unittest.TestCase):
    def test_literal_rank_result_terms_and_kind_predicate(self):
        countries = [bytearray(191) for _ in range(3)]
        countries[1][0x2A:0x2D] = bytes((1, 1, 1))  # rating128
        countries[2][0x2A:0x2D] = bytes((32, 128, 4))  # rating1
        for scores, kind, expected in (((1, 0), 1, (-4, 4)), ((0, 0), 1, (-3, 3)),
                                       ((0, 1), 1, (-4, 4)), ((0, 1), 3, (-4, 8))):
            # Synthetic set containing kind3; actual integration reads its source image.
            self.assertEqual(confidence.result_deltas(countries, (1, 2), scores, kind, bytes((1 << 3,))), expected)
        countries[1][4] = 255  # no player/line-strength forecast substitution
        self.assertEqual(confidence.result_deltas(countries, (1, 2), (0, 0), 1, bytes((8,))), (-3, 3))

    def test_participants_bench_draw_order_clipping_and_untouched_bytes(self):
        cases = [(32, 4, 'starter', [], 32, []), (32, 4, 'substitute', [2, 1], 31, [2, 2]),
                 (1, -4, 'substitute', [1, 2], 2, [2, 2]),
                 (16, 99, 'unused', [4, 1], 13, [4, 2]),
                 (1, 99, 'unused', [1, 2], 2, [4, 2]), (255, 3, 'starter', [], 2, [])]
        for before, delta, role, values, expected, bounds in cases:
            with self.subTest(role=role, before=before, delta=delta):
                r = player(before, status=4)
                rng = Draws(values)
                after = confidence.participant(r, delta, role, rng)
                self.assertEqual(after[12], expected)
                self.assertEqual(after[:12] + after[13:], r[:12] + r[13:])
                self.assertEqual(rng.bounds, bounds)

    def test_morale_signed_wrap_fixed_divisor_and_availability_elements(self):
        roster = [player()] * 12
        eleven = list(range(1, 12))
        self.assertEqual(confidence.team_morale(roster, eleven), 16)
        roster[1] = player(128)
        for i in range(2, 12): roster[i] = player(0)
        self.assertEqual(confidence.team_morale(roster, eleven), 5946)
        for unavailable in (player(current=0), player(current=255), player(status=0x80),
                            player(status=0x20), player(status=0x04)):
            roster = [player()] * 12
            roster[1] = unavailable
            self.assertEqual(confidence.team_morale(roster, eleven), 15)
        for available in (player(status=0x08), player(status=0x10)):
            roster[1] = available
            self.assertEqual(confidence.team_morale(roster, eleven), 16)


@requires.need(**requires.HALFTIME)
class ConfidenceContinuations(unittest.TestCase):
    def setUp(self):
        self.session = WebSession.load(ROOT / '.cache/e010-r0008-halftime.sav', ROOT / '.cache/GOAL.DAT')
        self.session.new_campaign({'country': 4, 'start_year': 1990, 'seed_7b62': 4660, 'seed_8336': 33590})

    def play(self, session=None):
        session = session or self.session
        v = session.view()
        return session.play({'play_token': v['play_token'], 'fixture_id': v['campaign']['next_fixture']['fixture_id']})

    def make_qm(self):
        qm = QuickMatch(Savestate(to_savestate(self.session.state, original=self.session.template_bytes)))
        f = self.session.state.campaign.next_fixture
        qm.teams[:] = [f.side_a, f.side_b]
        for side in (0, 1):
            for index, word in enumerate(qm._squad(side)[:11], 1):
                slot = qm.side_base[side] + index
                qm.pitch[slot]["player"] = word
                qm.pitch[slot]["slot_no"] = slot
        return qm

    def test_shadow_preserves_scorer_after_temporary_reaction_in_actual_event_order(self):
        qm = self.make_qm()
        scorer, teammate = qm._squad(0)[:2]
        for side in (0, 1):
            for word in qm._squad(side):
                qm._player(word)[12:15] = bytes((16, 16, 16))
        confidence.begin(qm)
        # Actual engine reactions before the scorer affect what its flag-one call saves.
        qm.eight30b = qm.side_base[0] + 10
        qm.after_goal_form_swing()
        qm.record_goal_scorer_effects(scorer)
        qm.after_goal_form_swing()
        self.assertEqual(qm._player(scorer)[12], 19)
        confidence.restore(qm)
        self.assertEqual(qm._player(scorer)[12], 18)
        self.assertEqual(qm._player(teammate)[12], 16)
        self.assertEqual(int.from_bytes(qm._player(scorer)[10:12], 'little'), 1)

    def test_b7fa_interleaves_used_and_unused_confidence_with_recovery(self):
        qm = self.make_qm()
        words = [list(qm._squad(s)) for s in (0, 1)]
        for side in (0, 1):
            for word in words[side]: qm._player(word)[16] = 0
        qm._player(words[0][11])[16] = 4
        qm._player(words[0][12])[16] = 8
        confidence.begin(qm)
        qm.score = [1, 0]
        qm.rng = Draws([1] * 36)
        qm.rng.draws = 0
        calls = []
        original = confidence.participant
        def participant(record, delta, role, rng):
            calls.append(('confidence', role))
            return original(record, delta, role, rng)
        def recover(record, flag, rng, **kwargs):
            calls.append(('energy', bool(flag)))
            return bytes(record)
        with patch('goal2.game.campaign_pool.finish', return_value={}), patch.object(confidence, 'participant', side_effect=participant), patch.object(energy, 'recover_player', side_effect=recover):
            energy.finish(qm, self.session.state, with_confidence=True)
        self.assertEqual(calls[:2], [('energy', True), ('confidence', 'starter')])
        self.assertEqual(calls[22:26], [('energy', True), ('confidence', 'substitute'), ('confidence', 'unused'), ('energy', False)])
        self.assertEqual(qm.rng.bounds[:4], [2, 2, 4, 2])
        self.assertEqual(len(qm.rng.bounds), 36)
        self.assertEqual(qm._player(words[0][11])[16] & 4, 0)
        self.assertEqual(qm._player(words[0][12])[16], 8)

    def test_result_update_publishes_confidence_and_view_morale(self):
        state = self.session.state
        fixture = state.campaign.next_fixture
        for country, ranks in ((fixture.side_a, (1, 1, 1)), (fixture.side_b, (32, 128, 4))):
            r = bytearray(state.countries[country]); r[0x2A:0x2D] = bytes(ranks); state.countries[country] = bytes(r)
        for word in state.managed_squad:
            r = bytearray(state.players[word]); r[12:15] = bytes((16, 16, 16)); r[16] = 0; state.players[word] = bytes(r)
        with patch.object(QuickMatch, 'd733', return_value=None):
            view = self.play()
        for word in state.starting_eleven: self.assertEqual(self.session.state.players[word][12], 13)
        self.assertEqual(view['team_morale'], 13)
        self.assertTrue(all(p['confidence'] == 13 for p in view['players'] if p['id'] in state.starting_eleven))
        self.assertEqual(self.session.state.match_state['campaign_energy']['confidence_draws'], 36)

    def test_saved_uninterrupted_two_fixtures_and_read_load_idempotence(self):
        with tempfile.TemporaryDirectory() as directory:
            self.session.save_path = Path(directory) / 'confidence.g2save'
            self.session.save_to_configured_path()
            resumed = WebSession.resume(self.session.save_path, ROOT / '.cache/GOAL.DAT')
            for _ in range(2):
                self.play(); self.play(resumed)
                self.assertEqual(resumed.state, self.session.state)
                self.assertEqual(resumed.view()['team_morale'], self.session.view()['team_morale'])
            before = copy.deepcopy(self.session.state)
            self.session.view(); self.session.save_to_configured_path(); self.session.load_from_configured_path()
            self.assertEqual(self.session.state, before)

    def test_failure_rollback_stale_replay_and_stateless_candidate(self):
        before = copy.deepcopy(self.session.state)
        with patch.object(confidence, 'participant', side_effect=ValueError('injected confidence failure')):
            with self.assertRaisesRegex(ValueError, 'injected confidence'):
                self.play()
        self.assertEqual(self.session.state, before)
        run_full_match(Savestate(to_savestate(self.session.state, original=self.session.template_bytes)), self.session.state)
        self.assertEqual(self.session.state, before)
        v = self.session.view()
        payload = {'play_token': v['play_token'], 'fixture_id': v['campaign']['next_fixture']['fixture_id']}
        self.session.play(payload)
        after = copy.deepcopy(self.session.state)
        with self.assertRaises(StalePlaySubmission): self.session.play(payload)
        self.assertEqual(self.session.state, after)

    def test_view_recomputes_confirmed_xi_without_random_draws_or_persisted_aggregate(self):
        state = self.session.state
        for word in state.managed_squad:
            r = bytearray(state.players[word]); r[12:15] = bytes((16, 16, 16)); r[16] = 0; state.players[word] = bytes(r)
        before = copy.deepcopy(state)
        self.assertEqual(self.session.view()['team_morale'], 16)
        self.assertEqual(self.session.state, before)
        word = state.starting_eleven[0]
        r = bytearray(state.players[word]); r[12] = 32; state.players[word] = bytes(r)
        self.assertEqual(self.session.view()['team_morale'], 18)  # (6 + 32 + 10*16) // 11
        self.assertNotIn('team_morale', state.match_state)


if __name__ == '__main__':
    unittest.main()
