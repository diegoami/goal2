"""Interactive output regression tests. [designed: T23's display contract]

Synthetic data and engine results keep these checks independent of private assets.
"""
import io
import unittest
from contextlib import redirect_stdout
from types import SimpleNamespace
from unittest.mock import patch

from goal2.ui import country_select, squad, tactics, result
from goal2.ui.input import Key
from goal2.ui.plain_renderer import render


class Output(io.StringIO):
    """[designed] Record flushes as well as frame contents before input."""

    def __init__(self):
        super().__init__()
        self.flushes = 0

    def flush(self):
        self.flushes += 1
        super().flush()


class TestScreenOutput(unittest.TestCase):
    def setUp(self):
        self.data = SimpleNamespace(
            country_names=[""] + [f"Country{i}" for i in range(1, 129)],
            squad_20=[list(range(1, 21)) for _ in range(129)],
            player_names=[""] + [f"Player{i}" for i in range(1, 21)],
            player_initials=[""] + ["X"] * 20,
        )
        self.state = SimpleNamespace(
            managed_country=1, managed_squad=list(range(1, 21)),
            starting_eleven=[], captain=0, country_tactics=0,
        )
        self.match_result = {
            "score": (2, 1),
            "goals": [{"team": 0, "minute": 67, "player": 4}],
            "seed_DS7B62": 0x1234, "seed_DS8336": 0x5678,
        }

    def assert_interactive(self, module, run, frames, keys):
        """[designed] Inspect each accumulated frame and flush before returning a key."""
        output = Output()
        reads = 0

        def read():
            nonlocal reads
            self.assertEqual(output.getvalue(), "".join(frames[:reads + 1]))
            self.assertEqual(output.flushes, reads + 1)
            key = keys[reads]
            reads += 1
            return key

        with redirect_stdout(output), patch.object(module, "read_key", side_effect=read):
            value = run()
        self.assertEqual(reads, len(keys))
        self.assertEqual(output.getvalue(), "".join(frames))
        return value

    def test_country_is_displayed_and_redrawn_before_input(self):
        frames = [render(country_select._render(self.data, cursor, 20))
                  for cursor in (1, 2)]
        self.assertIn("Country2", frames[1])
        chosen = self.assert_interactive(
            country_select,
            lambda: country_select.run_country_select(self.data, None, state=self.state),
            frames, [Key.DOWN, Key.ENTER],
        )
        self.assertEqual(chosen, 2)

    def test_squad_is_displayed_and_redrawn_before_input(self):
        frames = [render(squad._render(self.data, self.state, cursor, 20))
                  for cursor in (1, 2)]
        self.assertIn("Player2", frames[1])
        self.assertTrue(self.assert_interactive(
            squad, lambda: squad.run_squad_select(self.data, None, state=self.state),
            frames, [Key.DOWN, Key.ENTER],
        ))

    def test_tactics_navigation_and_toggle_are_redrawn_before_input(self):
        frames = [render(tactics._build_grid(byte, cursor))
                  for byte, cursor in ((0, 1), (0, 2), (0x20, 2))]
        self.assertIn("TACTICS  0x20", frames[-1])
        self.assertTrue(self.assert_interactive(
            tactics, lambda: tactics.run_tactics_select(self.data, None, state=self.state),
            frames, [Key.DOWN, Key.SPACE, Key.ENTER],
        ))

    def test_result_is_displayed_before_each_input(self):
        frame = render(result._build_grid(self.match_result, None))
        self.assertIn("FINAL SCORE  2-1", frame)
        self.assertIn("scorer 4", frame)
        with patch.object(result, "Savestate"), \
             patch.object(result._qe, "simulate", return_value=self.match_result) as engine:
            self.assertTrue(self.assert_interactive(
                result, lambda: result.run_result(b"synthetic", None),
                [frame, frame], [Key.DOWN, Key.ENTER],
            ))
        engine.assert_called_once()

    def test_refusals_are_displayed_before_input(self):
        for error in (result.FoulPathNotModelled, result.ExtraTimeNotModelled):
            with self.subTest(error=error.__name__), patch.object(result, "Savestate"), \
                 patch.object(result._qe, "simulate", side_effect=error("synthetic refusal")):
                frame = render(result._build_grid(None, "synthetic refusal"))
                self.assertIn("REFUSED: synthetic refusal", frame)
                self.assertFalse(self.assert_interactive(
                    result, lambda: result.run_result(b"synthetic", None), [frame], [Key.ESC],
                ))

    def test_selection_escape_displays_frame_before_abort(self):
        cases = [
            (country_select, lambda: country_select.run_country_select(self.data, None),
             render(country_select._render(self.data, 1, 20)), None),
            (squad, lambda: squad.run_squad_select(self.data, None, state=self.state),
             render(squad._render(self.data, self.state, 1, 20)), False),
            (tactics, lambda: tactics.run_tactics_select(self.data, None),
             render(tactics._build_grid(0, 1)), False),
        ]
        for module, run, frame, expected in cases:
            with self.subTest(screen=module.__name__):
                self.assertIs(self.assert_interactive(module, run, [frame], [Key.ESC]), expected)

    def test_scripted_keys_remain_silent(self):
        cases = [
            (country_select, lambda: country_select.run_country_select(self.data, [Key.ENTER])),
            (squad, lambda: squad.run_squad_select(self.data, [Key.ENTER], state=self.state)),
            (tactics, lambda: tactics.run_tactics_select(self.data, [Key.SPACE, Key.ENTER])),
            (result, lambda: result.run_result(b"synthetic", [Key.ENTER])),
        ]
        with patch.object(result, "Savestate"), \
             patch.object(result._qe, "simulate", return_value=self.match_result):
            for module, run in cases:
                with self.subTest(screen=module.__name__), redirect_stdout(Output()) as output, \
                     patch.object(module, "read_key") as reader:
                    run()
                    self.assertEqual(output.getvalue(), "")
                    self.assertEqual(output.flushes, 0)
                    reader.assert_not_called()
