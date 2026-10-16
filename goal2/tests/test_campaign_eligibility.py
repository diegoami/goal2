"""[designed: T44] F027 availability and status transitions through real sessions."""
import copy
import tempfile
from pathlib import Path
from unittest.mock import patch
import unittest
from goal2.game import eligibility
from goal2.game.quick_match import run_full_match
from goal2.engine.quick_engine import QuickMatch
from goal2.engine.savestate import Savestate
from goal2.game.state import to_savestate
from goal2.web.server import WebSession

ROOT = Path(__file__).resolve().parents[2]


def record(status=0, current=16):
    r = bytearray(range(20))
    r[14], r[16] = current, status
    return bytes(r)


class EligibilityReferenceCases(unittest.TestCase):
    def test_availability_reasons_and_one_based_element_neighbors(self):
        for r, expected in [(record(), ()), (record(current=0), ('Injured',)),
                            (record(current=255), ('Unavailable energy',)),
                            (record(status=0x80), ('Suspended',)),
                            (record(status=0x20), ('Sent off',)),
                            (record(status=0x04), ('Substituted off',)),
                            (record(status=0x08), ()), (record(status=0x10), ())]:
            self.assertEqual(eligibility.reasons(r), expected)
        self.assertEqual(eligibility.info(record(status=0x88))['carried_bookings'], 1)
        self.assertEqual(eligibility.info(record(status=0x88))['ban_fixtures'], 1)
        self.assertEqual(eligibility.info(eligibility.after_fixture(record(status=0x88), 1))['ban_fixtures'], 0)
        self.assertEqual(eligibility.reasons(record(status=0xA4, current=0)),
                         ('Injured', 'Suspended', 'Sent off', 'Substituted off'))

    def test_b27f_literal_transitions_preserve_all_other_bytes(self):
        for before, expected in [(0, 0), (0x80, 0), (0x10, 8), (0x18, 0x80),
                                 (0x20, 0x80), (0x28, 0x88), (0x90, 8),
                                 (0xFF, 0xC7), (0x44, 0x44)]:
            for kind in (1, 2, 5):
                r = record(before)
                after = eligibility.after_fixture(r, kind)
                self.assertEqual(after[16], expected)
                self.assertEqual(after[:16] + after[17:], r[:16] + r[17:])
                self.assertEqual(eligibility.after_fixture(r, 0), r, 'kind0 serves no ban')

    def test_available_words_and_selection_refusal_are_pure(self):
        players = [record()] * 21
        players[1] = record(status=0x80)
        players[2] = record(current=0)
        before = list(players)
        self.assertEqual(eligibility.available_words(players, list(range(1, 21))), list(range(3, 21)))
        with self.assertRaisesRegex(ValueError, 'unavailable'):
            eligibility.require_available(players, list(range(1, 12)))
        eligibility.require_available(players, list(range(3, 14)))
        self.assertEqual(players, before)


class EligibilityContinuations(unittest.TestCase):
    def setUp(self):
        self.session = WebSession.load(ROOT / '.cache/e010-r0008-halftime.sav', ROOT / '.cache/GOAL.DAT')
        self.session.new_campaign({'country': 4, 'start_year': 1990, 'seed_7b62': 4660, 'seed_8336': 33590})

    def change(self, word, **fields):
        r = bytearray(self.session.state.players[word])
        for offset, value in fields.items(): r[int(offset)] = value
        self.session.state.players[word] = bytes(r)

    def play(self, session=None):
        session = session or self.session
        v = session.view()
        return session.play({'play_token': v['play_token'], 'fixture_id': v['campaign']['next_fixture']['fixture_id']})

    def test_unavailable_starter_blocks_preview_and_play_without_state_change(self):
        word = self.session.state.starting_eleven[0]
        for fields in ({'14': 0}, {'14': 16, '16': 0x80}):
            self.change(word, **fields)
            before = copy.deepcopy(self.session.state)
            v = self.session.view()
            self.assertFalse(v['matchup']['available'])
            self.assertFalse(next(p for p in v['players'] if p['id'] == word)['availability']['available'])
            with self.assertRaisesRegex(ValueError, 'unavailable'):
                self.play()
            self.assertEqual(self.session.state, before)

    def test_management_rejects_unavailable_eleven_then_allows_human_repair(self):
        state = self.session.state
        word = state.starting_eleven[0]
        self.change(word, **{'16': 0x80})
        before = copy.deepcopy(state)
        payload = {'country': 4, 'starting_eleven': list(state.starting_eleven),
                   'captain': state.starting_eleven[1], 'tactics': state.country_tactics}
        with self.assertRaisesRegex(ValueError, 'unavailable'):
            self.session.confirm_management(payload)
        self.assertEqual(self.session.state, before)
        payload['starting_eleven'][0] = state.managed_squad[-1]
        v = self.session.confirm_management(payload)
        self.assertTrue(v['matchup']['available'])
        self.assertNotIn(word, self.session.state.starting_eleven)
        self.assertEqual(self.session.state.players[word][16], 0x80)

    def test_computer_uses_only_available_players_and_refuses_fewer_than_eleven(self):
        state = self.session.state
        fixture = state.campaign.next_fixture
        opponent = fixture.side_b
        squad = [int.from_bytes(state.countries[opponent][i:i+2], 'little') for i in range(0, 40, 2)]
        for word, fields in [(squad[0], {'14': 0, '1': 127, '4': 255}),
                             (squad[1], {'16': 0x80, '1': 127, '4': 255})]: self.change(word, **fields)
        captured = []
        def minute(qm, clock, remaining):
            if clock == 0:
                captured.extend(qm.pitch[qm.side_base[1] + n]['player'] for n in range(1, 12))
        with patch.object(QuickMatch, 'd733', minute): self.play()
        self.assertEqual(len(captured), 11)
        self.assertTrue(set(captured).isdisjoint(squad[:2]))
        for word in squad[:10]: self.change(word, **{'16': 0x80})
        # Restore the first fixture as a direct candidate; this is explicit test state.
        # [designed: T48] Explicit legacy candidate reset, not a committed world turn.
        self.session.state.campaign.world=None
        self.session.state.campaign.completed_fixture_ids.clear()
        self.session.state.campaign.results.clear()
        self.session.state.match_state.clear()
        before = copy.deepcopy(self.session.state)
        with self.assertRaisesRegex(ValueError, 'opponent'):
            self.play()
        self.assertEqual(self.session.state, before)

    def test_status_persists_through_save_and_expires_only_at_next_played_fixture(self):
        state = self.session.state
        booked = state.managed_squad[-1]
        serving = state.managed_squad[-2]
        self.change(booked, **{'16': 0x08})
        self.change(serving, **{'16': 0xC1})
        def event(qm, clock, remaining):
            if clock == 91: qm._player(booked)[16] |= 0x10  # explicit test booking
        with patch.object(QuickMatch, 'd733', event): self.play()
        self.assertEqual(self.session.state.players[booked][16], 0x80)
        self.assertEqual(self.session.state.players[serving][16], 0x41)
        with tempfile.TemporaryDirectory() as directory:
            self.session.save_path = Path(directory) / 'eligibility.g2save'
            self.session.save_to_configured_path()
            resumed = WebSession.resume(self.session.save_path, ROOT / '.cache/GOAL.DAT')
            self.assertEqual(resumed.state, self.session.state)
            self.assertEqual(resumed.state.players[booked][16], 0x80)
            before = copy.deepcopy(resumed.state)
            resumed.view(); resumed.save_to_configured_path(); resumed.load_from_configured_path()
            self.assertEqual(resumed.state, before)
            with patch.object(QuickMatch, 'd733', return_value=None):
                self.play(); self.play(resumed)
            self.assertEqual(resumed.state, self.session.state)
            self.assertEqual(resumed.state.players[booked][16], 0)

    def test_injured_bench_recovers_via_existing_fixture_energy_transition(self):
        word = self.session.state.managed_squad[-1]
        self.change(word, **{'14': 0})
        v = self.session.view()
        self.assertEqual(next(p for p in v['players'] if p['id'] == word)['availability']['reasons'], ['Injured'])
        with patch.object(QuickMatch, 'd733', return_value=None): self.play()
        self.assertGreater(self.session.state.players[word][14], 0)
        self.assertTrue(next(p for p in self.session.view()['players'] if p['id'] == word)['availability']['available'])

    def test_status_runs_once_and_only_for_fixture_countries(self):
        other = 2001  # country101, outside the first fixture4/1
        self.change(other, **{'16': 0x80})
        before = self.session.state.players[other]
        original = eligibility.finish
        calls = []
        def finish(qm, state):
            result = original(qm, state)
            calls.append(result)
            with self.assertRaisesRegex(ValueError, 'already'):
                original(qm, state)
            return result
        with patch.object(eligibility, 'finish', side_effect=finish): self.play()
        self.assertEqual(len(calls), 1)
        self.assertEqual(self.session.state.players[other], before)
        self.assertEqual(self.session.state.match_state['campaign_energy']['eligibility'], calls[0])

    def test_failure_discards_status_candidate_and_stateless_simulation(self):
        word = self.session.state.managed_squad[-1]
        self.change(word, **{'16': 0x80})
        before = copy.deepcopy(self.session.state)
        with patch.object(eligibility, 'after_fixture', side_effect=ValueError('injected status failure')):
            with self.assertRaisesRegex(ValueError, 'injected status'):
                self.play()
        self.assertEqual(self.session.state, before)
        run_full_match(Savestate(to_savestate(self.session.state, original=self.session.template_bytes)), self.session.state)
        self.assertEqual(self.session.state, before)


if __name__ == '__main__':
    unittest.main()
