"""[designed: T26] Continuous friendly regression tests on synthetic engine memory."""
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from goal2.tests.test_cpu_tactics_change import build_state, squad_words, C0, C1
from goal2.engine.quick_engine import QuickMatch
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


if __name__ == "__main__":
    unittest.main()
