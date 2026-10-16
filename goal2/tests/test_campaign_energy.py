"""[designed: T42] Energy boundaries, literal F018 cases and campaign transactions."""
import copy
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from goal2.game import campaign_energy as energy
from goal2.game.quick_match import run_full_match
from goal2.game.state import to_savestate
from goal2.engine.savestate import Savestate
from goal2.web.server import WebSession, StalePlaySubmission

ROOT = Path(__file__).resolve().parents[2]


def record(fitness=16, current=8, age=30, peak=25):
    r = bytearray(20)
    r[1], r[2], r[12], r[13], r[14] = age, peak, 16, fitness, current
    return bytes(r)


class Draws:
    def __init__(self, values):
        self.values = iter(values)
        self.bounds = []
    def rand(self, bound):
        self.bounds.append(bound)
        return next(self.values)


class EnergyReferenceCases(unittest.TestCase):
    def apply(self, r, flag, draws, gradual=True, managed=True):
        rng = Draws(draws)
        after = energy.recover_player(r, flag, rng, gradual=gradual, managed=managed,
                                      caps=(32, 24), redraw_bases=(16, 13))
        return after, rng.bounds

    def test_literal_gradual_draw_order_rest_injury_caps_and_signed_edges(self):
        cases = [
            (record(), 1, [2, 8], (2, 8), (22, 22)),
            (record(), 0, [3, 1], (3, 2), (15, 15)),
            (record(current=0), 1, [1, 8, 2], (2, 8, 3), (9, 0)),
            (record(current=0), 0, [1, 8, 1], (2, 8, 3), (9, 9)),
            (record(current=255), 1, [2, 8, 3], (2, 8, 3), (22, 255)),
            (record(fitness=31, age=28), 1, [1, 8], (2, 8), (32, 32)),
            (record(fitness=31, age=29), 1, [1, 8], (2, 8), (24, 24)),
            (record(fitness=255, current=0), 0, [1, 8, 1], (2, 8, 3), (1, 1)),
        ]
        for before, flag, draws, bounds, expected in cases:
            with self.subTest(expected=expected, draws=draws):
                after, actual_bounds = self.apply(before, flag, draws)
                self.assertEqual(tuple(after[13:15]), expected)
                self.assertEqual(tuple(actual_bounds), bounds)
                self.assertEqual(after[:13] + after[15:], before[:13] + before[15:])

    def test_redraw_managed_unmanaged_age_threshold_and_clamp_order(self):
        # [derived: F007/F018, 1771:3558] Underlying draws are ordered, not averages.
        for before, managed, values, expected, bounds in (
            (record(age=29), True, [2, 40], (32, 32), [17, 48]),
            (record(age=30), True, [14, 1], (1, 0), [14, 39]),
            (record(age=29), False, [32], (32, 32), [32]),
            (record(age=30), False, [1], (14, 14), [26]),
        ):
            with self.subTest(managed=managed, expected=expected):
                after, actual = self.apply(before, 1, values, gradual=False, managed=managed)
                self.assertEqual(tuple(after[13:15]), expected)
                self.assertEqual(actual, bounds)

    def test_half_bonus_and_restoration_preserve_zero_negative_and_other_bytes(self):
        for initial, expected in ((0, 0), (1, 3), (30, 32), (31, 31), (32, 32), (128, 128), (255, 255)):
            r = record(fitness=19, current=initial)
            self.assertEqual(energy.half_bonus(r)[14], expected)
            restored = energy.restore_energy(r)
            self.assertEqual(restored[14], 19 if 0 < initial < 128 else initial)
            self.assertEqual(restored[:14] + restored[15:], r[:14] + r[15:])


class CampaignContinuations(unittest.TestCase):
    def setUp(self):
        self.session = WebSession.load(ROOT / '.cache/e010-r0008-halftime.sav', ROOT / '.cache/GOAL.DAT')
        self.session.new_campaign({'country': 4, 'start_year': 1990, 'seed_7b62': 4660, 'seed_8336': 33590})

    def play(self, session=None):
        session = session or self.session
        view = session.view()
        return session.play({'play_token': view['play_token'], 'fixture_id': view['campaign']['next_fixture']['fixture_id']})

    def test_boundaries_have_no_kickoff_bonus_then_half_bonus_and_fitness_restore(self):
        state = self.session.state
        player = state.starting_eleven[0]
        state.players[player] = record(fitness=18, current=10)
        seen = {}
        restored = []
        def minute(qm, tick, countdown):
            if tick in (0, 45, 46, 91):
                seen[tick] = qm._player(player)[14]
        def recover(r, *args, **kwargs):
            if r[0] == 0 and r[13] == 18:
                restored.append(r[14])
            return r
        with patch('goal2.game.quick_match.QuickMatch.d733', minute), patch.object(energy, 'recover_player', side_effect=recover):
            run_full_match(Savestate(to_savestate(state, original=self.session.template_bytes)), state, retain_state=True)
        self.assertEqual(seen, {0: 10, 45: 10, 46: 12, 91: 12})
        self.assertIn(18, restored)
        self.assertEqual(state.players[player][14], 18)

    def test_real_campaign_recovery_consumes_sixty_ordered_draws_and_publishes_once(self):
        start = self.session.view()
        captures = []
        original = energy.finish
        def finish(qm, state):
            before = qm.rng.seed
            meta = original(qm, state)
            captures.append((before, qm.rng.seed, meta))
            return meta
        with patch.object(energy, 'finish', side_effect=finish):
            result = self.play()
        self.assertEqual(len(captures), 1)
        before, after, metadata = captures[0]
        expected = before
        for _ in range(60):
            expected = (expected * 0x7ABD + 0x1B0F) & 65535
        self.assertEqual(after, expected)
        self.assertEqual(metadata['recovery_draws'], 60)
        self.assertEqual(metadata['fixture_id'], 'original:1378')
        self.assertEqual(self.session.state.rng_seed_7b62, expected)
        for player in result['players']:
            self.assertEqual(player['energy'], self.session.state.players[player['id']][14])
        before_replay = copy.deepcopy(self.session.state)
        with self.assertRaises(StalePlaySubmission):
            self.session.play({'play_token': start['play_token'], 'fixture_id': 'original:1378'})
        self.assertEqual(self.session.state, before_replay)

    def test_saved_before_recovery_resumes_to_identical_complete_two_fixture_state(self):
        with tempfile.TemporaryDirectory() as folder:
            self.session.save_path = Path(folder) / 'energy.g2save'
            self.session.save_to_configured_path()
            resumed = WebSession.resume(self.session.save_path, ROOT / '.cache/GOAL.DAT')
            for _ in range(2):
                self.play()
                self.play(resumed)
                self.assertEqual(resumed.state, self.session.state)
            before = copy.deepcopy(self.session.state)
            self.session.view()
            self.session.save_to_configured_path()
            self.session.load_from_configured_path()
            self.assertEqual(self.session.state, before)
            self.assertEqual(self.session.state.match_count, 2)
            self.assertEqual(self.session.state.match_state['campaign_energy']['fixture_id'], 'original:1471')

    def test_recovery_failure_leaves_active_state_and_queue_intact(self):
        before = copy.deepcopy(self.session.state)
        with patch.object(energy, 'recover_player', side_effect=ValueError('injected recovery failure')):
            with self.assertRaisesRegex(ValueError, 'injected recovery'):
                self.play()
        self.assertEqual(self.session.state, before)
        self.assertEqual(self.play()['match_count'], 1)

    def test_energy_completion_guard_refuses_a_second_transition(self):
        self.play()
        # Simulate a caller replaying the just-finished fixture before its ledger update.
        state = copy.deepcopy(self.session.state)
        state.campaign.completed_fixture_ids.clear()
        with self.assertRaisesRegex(ValueError, 'energy.*already'):
            energy.ensure_pending(state)


if __name__ == '__main__':
    unittest.main()
