"""[designed: T30] Synthetic names keep result text checks fixture-independent."""
import io
import unittest
from contextlib import redirect_stdout
from types import SimpleNamespace
from unittest.mock import patch

from goal2.ui import result
from goal2.ui.input import Key
from goal2.ui.plain_renderer import render


def data():
    return SimpleNamespace(country_names=["", "Argentina", "Belgium", "Chile"],
                           player_names=["", "Ada Striker", "Bea Keeper", "Camila Wing", "Dara Midfielder"])


def match():
    goals = [{"team": 0, "minute": 12, "player": 1},
             {"team": 1, "minute": 44, "player": 3},
             {"team": 1, "minute": 68, "player": 4}]
    return {"teams": (1, 2), "managed_side": 1, "score": (1, 2), "goals": goals,
            "halves": ({"score": (1, 1), "goals": goals[:2]},
                       {"score": (1, 2), "goals": goals[2:]}),
            "seed_DS7B62": 0x1234, "seed_DS8336": 0x5678}


def state(managed=2):
    return SimpleNamespace(managed_country=managed, players=[bytes(20)] * 20)


class TestClearResults(unittest.TestCase):
    def frame(self, result_data=None, game_state=None, page=0, refusal=None):
        return render(result._build_grid(result_data or match(), refusal, full_match=True,
                                         page=page, goaldat=data(), state=game_state or state()))

    def test_named_score_halftime_and_managed_team_in_engine_order(self):
        frame = self.frame()
        self.assertIn("MANAGED: Belgium", frame)
        self.assertIn("FULL TIME: Argentina 1 - 2 Belgium", frame)
        self.assertIn("HALF TIME: Argentina 1 - 1 Belgium", frame)
        self.assertNotIn("0x1234", frame)
        self.assertNotIn("0x5678", frame)
        self.assertNotIn("DS:7B62", frame)
        self.assertNotIn("DS:8336", frame)

    def test_goal_side_and_player_names_on_both_halves(self):
        frame = self.frame()
        self.assertIn("12 H1 Argentina: Ada Striker", frame)
        self.assertIn("44 H1 Belgium: Camila Wing", frame)
        self.assertIn("68 H2 Belgium: Dara Midfielder", frame)
        self.assertNotIn("team 1", frame)
        self.assertNotIn("scorer 4", frame)

    def test_managed_side_zero_keeps_score_order(self):
        result_data = match()
        result_data.update(teams=(2, 1), managed_side=0, score=(3, 1))
        result_data["halves"] = ({"score": (1, 1), "goals": result_data["goals"][:2]},
                                 {"score": (3, 1), "goals": result_data["goals"][2:]})
        frame = self.frame(result_data, state(2))
        self.assertIn("MANAGED: Belgium", frame)
        self.assertIn("FULL TIME: Belgium 3 - 1 Argentina", frame)
        self.assertIn("HALF TIME: Belgium 1 - 1 Argentina", frame)
        self.assertIn("12 H1 Belgium: Ada Striker", frame)
        self.assertIn("44 H1 Argentina: Camila Wing", frame)

    def test_no_goals_and_refusal(self):
        result_data = match()
        result_data.update(goals=[], halves=({"score": (0, 0), "goals": []},
                                             {"score": (0, 0), "goals": []}), score=(0, 0))
        self.assertIn("NO GOALS", self.frame(result_data))
        refused = self.frame(None, refusal="normal friendly required")
        self.assertIn("REFUSED: normal friendly required", refused)

    def test_overflow_pages_include_last_goal_and_clear_actions(self):
        goals = [{"team": 0, "minute": n + 1, "player": 1} for n in range(20)]
        result_data = match()
        result_data.update(goals=goals, score=(18, 0),
                           halves=({"score": (9, 0), "goals": goals[:9]},
                                   {"score": (18, 0), "goals": goals[9:]}))
        first, second = self.frame(result_data, page=0), self.frame(result_data, page=1)
        self.assertIn("GOALS 1/2", first)
        self.assertIn("FRIENDLY RESULT - ASSUMED SETUP", second)
        self.assertIn("GOALS 2/2", second)
        self.assertIn("20 H2 Argentina: Ada Striker", second)
        self.assertIn("ENTER FINISH", second)
        self.assertIn("ESC QUIT", second)

    def test_flush_before_input_finish_and_quit(self):
        expected_frame = self.frame()
        class Output(io.StringIO):
            flushes = 0
            def flush(self):
                self.flushes += 1
                super().flush()
        for key, expected in ((Key.ENTER, True), (Key.ESC, False)):
            output = Output()
            def read():
                self.assertEqual(output.getvalue(), expected_frame)
                self.assertEqual(output.flushes, 1)
                return key
            with self.subTest(key=key), redirect_stdout(output), patch.object(result, "Savestate"), \
                 patch.object(result, "run_full_match", return_value=match()), \
                 patch.object(result, "read_key", side_effect=read):
                actual = result.run_result(b"synthetic", None, state=state(), full_match=True, goaldat=data())
            self.assertIs(actual, expected)

    def test_scripted_result_is_silent(self):
        output = io.StringIO()
        with redirect_stdout(output), patch.object(result, "Savestate"), \
             patch.object(result, "run_full_match", return_value=match()), \
             patch.object(result, "read_key") as reader:
            result.run_result(b"synthetic", [Key.ENTER], state=state(), full_match=True, goaldat=data())
        self.assertEqual(output.getvalue(), "")
        reader.assert_not_called()


if __name__ == "__main__":
    unittest.main()
