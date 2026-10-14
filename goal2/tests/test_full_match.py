"""[designed: T26] Continuous friendly regression tests on synthetic engine memory."""
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from goal2.tests.test_cpu_tactics_change import build_state, squad_words, C0, C1
from goal2.engine.quick_engine import ExtraTimeNotModelled, QuickMatch
from goal2.game.quick_match import run_full_match


def game_state():
    return SimpleNamespace(
        managed_country=C0, managed_squad=squad_words(C0),
        starting_eleven=squad_words(C0)[:11], country_tactics=0x20,
        players=[bytes(20)] * 3061,
        countries=[bytes(0xBF)] * 129,
    )


class FullMatch(unittest.TestCase):
    def test_cited_minutes_and_continuous_instance(self):
        state = build_state(seed=0x1234)
        game = game_state()
        calls = []
        original = QuickMatch.d733

        def spy(qm, minute, countdown):
            calls.append((id(qm), minute, countdown, qm.rng.seed, tuple(qm.score), qm.eight30b))
            return original(qm, minute, countdown)

        with patch.object(QuickMatch, "d733", spy):
            result = run_full_match(state, game)
        self.assertEqual(len(calls), 92)
        self.assertEqual([(c[1], c[2]) for c in calls], [(m, 91-m) for m in range(92)])
        self.assertEqual(len({c[0] for c in calls}), 1)
        self.assertEqual(calls[0][4], (0, 0))
        self.assertEqual(calls[46][3], result["halves"][0]["seed_DS7B62"])
        self.assertEqual(calls[46][4], result["halves"][0]["score"])
        self.assertNotEqual(calls[0][5], calls[46][5])
        self.assertEqual(result["score"], result["halves"][1]["score"])
        self.assertEqual(result["goals"], result["halves"][0]["goals"] + result["halves"][1]["goals"])

    def test_selected_team_and_determinism(self):
        a = run_full_match(build_state(seed=0x1234), game_state())
        b = run_full_match(build_state(seed=0x1234), game_state())
        self.assertEqual(a, b)
        self.assertEqual(a["teams"], (C0, C1))
        self.assertEqual(a["managed_side"], 0)

    def test_reset_and_mutable_state_survives_half_time(self):
        """[designed: T26] Reset once, then retain every mutable engine field."""
        state = build_state()
        state.put(0x9B3C, bytes([9, 8]))
        state.put(0x9B3A, bytes([1, 2]))
        state.put(0x8332, bytes([1, 1]))
        state.put(0x8334, bytes([1, 1]))
        seen = []

        def sentinel(qm, minute, countdown):
            if minute == 0:
                self.assertEqual(qm.score, [0, 0])
                self.assertEqual(qm.sub_budget, [5, 5])
                self.assertEqual(qm.once_8332, [0, 0])
                self.assertEqual(qm.once_8334, [0, 0])
                self.assertEqual(qm.goals, [])
                seen.append((id(qm.rng), qm.eight30b))
            if minute == 45:
                qm.score[0] = 2
                qm.rng.seed = 0x5678
                qm.goals.append({"team": 0, "minute": 45, "player": 21})
                qm.playerrec[21][0xE] = 17
                qm.pitch[12]["player"] = 22
                qm._country(C0)["tactics"] = 0x42
                qm.sub_budget[1] = 3
                qm.once_8332[1] = 1
            if minute == 46:
                seen.append((id(qm.rng), qm.eight30b))
                self.assertEqual(qm.score, [2, 0])
                self.assertEqual(qm.rng.seed, 0x5678)
                self.assertEqual(qm.goals[0]["minute"], 45)
                self.assertEqual(qm.playerrec[21][0xE], 17)
                self.assertEqual(qm.pitch[12]["player"], 22)
                self.assertEqual(qm._country(C0)["tactics"], 0x42)
                self.assertEqual(qm.sub_budget[1], 3)
                self.assertEqual(qm.once_8332[1], 1)
                qm.goals.append({"team": 1, "minute": 46, "player": 41})

        with patch.object(QuickMatch, "d733", sentinel):
            result = run_full_match(state, game_state())
        self.assertEqual(seen, [(seen[0][0], 21), (seen[0][0], 10)])
        self.assertEqual(result["kickoffs"], (21, 10))
        self.assertEqual(result["halves"][0]["goals"], [
            {"team": 0, "minute": 45, "player": 21}])
        self.assertEqual(result["halves"][1]["goals"], [
            {"team": 1, "minute": 46, "player": 41}])
        self.assertEqual(result["score"], (2, 0))

    def test_selected_country_replaces_side_zero_and_applies_lineups(self):
        """[designed: T26] An absent selected team replaces side zero."""
        state = build_state()
        game = game_state()
        game.managed_country = 3
        game.managed_squad = list(range(61, 81))
        game.starting_eleven = list(range(71, 81)) + [61]
        game.country_tactics = 0x46

        def inspect(qm, minute, countdown):
            if minute:
                return
            self.assertEqual(qm.teams, [3, C1])
            self.assertEqual(qm._country(3)["squad"][:11], game.starting_eleven)
            self.assertEqual(qm._country(3)["tactics"], 0x46)
            self.assertGreater(qm._country(3)["managed"], 0x80)
            self.assertLessEqual(qm._country(C1)["managed"], 0x80)
            self.assertEqual([qm.pitch[s]["player"] for s in range(12, 23)],
                             game.starting_eleven)
            self.assertEqual([qm.pitch[s]["player"] for s in range(1, 12)],
                             sorted(squad_words(C1))[:11])

        with patch.object(QuickMatch, "d733", inspect):
            result = run_full_match(state, game)
        self.assertEqual(result["teams"], (3, C1))

    def test_selected_existing_side_one_and_cpu_ability(self):
        """[designed: T26] Preserve side zero and use the CPU ability picker."""
        state = build_state()
        state.put(0x831A, b"\x01")
        game = game_state()
        game.managed_country = C1
        game.managed_squad = squad_words(C1)
        game.starting_eleven = list(reversed(squad_words(C1)[:11]))
        records = list(game.players)
        strongest = squad_words(C0)[-1]
        records[strongest] = bytes([0, 255]) + bytes(18)
        game.players = records

        def inspect(qm, minute, countdown):
            if minute:
                return
            self.assertEqual(qm.teams, [C0, C1])
            self.assertEqual(qm._country(C0)["squad"][0], strongest)
            self.assertEqual(qm.pitch[12]["player"], strongest)
            self.assertEqual([qm.pitch[s]["player"] for s in range(1, 12)],
                             game.starting_eleven)
            self.assertEqual(qm._country(C1)["tactics"], game.country_tactics)

        with patch.object(QuickMatch, "d733", inspect):
            result = run_full_match(state, game)
        self.assertEqual(result["managed_side"], 1)
        self.assertEqual(result["kickoffs"], (10, 21))

    def test_refuses_unsupported_templates(self):
        """[designed: T26] Foul and extra-time templates stay unsupported."""
        foul = build_state()
        foul.put(0x9A3D, b"\x01")
        with self.assertRaisesRegex(ValueError, "normal friendly"):
            run_full_match(foul, game_state())
        extra = build_state()
        extra.put(0x7C36, b"\x01")
        with self.assertRaises(ExtraTimeNotModelled):
            run_full_match(extra, game_state())


if __name__ == "__main__":
    unittest.main()
