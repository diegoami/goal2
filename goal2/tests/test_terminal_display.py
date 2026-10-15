"""T31 terminal and interactive presentation contract tests."""
import io
import os
import unittest
from contextlib import redirect_stdout
from contextlib import ExitStack
from types import SimpleNamespace
from unittest.mock import patch

from goal2.ui import country_select, preview, result, squad, tactics
from goal2.ui.grid import Grid
from goal2.ui.input import Key
from goal2.ui.plain_renderer import display, render


class Stream(io.StringIO):
    def __init__(self, *, terminal=False):
        super().__init__()
        self.terminal = terminal
        self.flushes = 0

    def isatty(self):
        return self.terminal

    def flush(self):
        self.flushes += 1
        super().flush()


class TestTerminalDisplay(unittest.TestCase):
    def test_terminal_redraws_two_frames_without_scrolling(self):
        grid = Grid()
        grid.draw_text(0, 0, "FRAME")
        expected = render(grid).rstrip("\n")
        output = Stream(terminal=True)
        with patch.dict(os.environ, {"TERM": "xterm-256color"}):
            display(grid, output)
            display(grid, output)
        self.assertEqual(output.getvalue(), ("\x1b[2J\x1b[H" + expected) * 2)
        self.assertFalse(output.getvalue().endswith("\n"))
        self.assertEqual(output.flushes, 2)

    def test_redirected_and_dumb_terminal_keep_plain_append_frames(self):
        grid = Grid()
        grid.draw_text(0, 0, "PLAIN")
        frame = render(grid)
        redirected = Stream(terminal=False)
        with patch.dict(os.environ, {"TERM": "xterm"}):
            display(grid, redirected)
        self.assertEqual(redirected.getvalue(), frame)

        dumb = Stream(terminal=True)
        with patch.dict(os.environ, {"TERM": "dumb"}):
            display(grid, dumb)
        self.assertEqual(dumb.getvalue(), frame)
        self.assertNotIn("\x1b", redirected.getvalue() + dumb.getvalue())

    def test_pure_render_stays_plain_and_terminated(self):
        grid = Grid()
        self.assertEqual(len(render(grid)), 25 * 81)
        self.assertTrue(render(grid).endswith("\n"))
        self.assertNotIn("\x1b", render(grid))

    def test_all_five_interactive_screens_flush_before_each_read(self):
        data = SimpleNamespace(
            country_names=[""] + [f"Country{i}" for i in range(1, 129)],
            player_names=[""] + [f"Player{i}" for i in range(1, 21)],
            player_initials=[""] + ["P"] * 20,
        )
        state = SimpleNamespace(
            managed_country=1, managed_squad=list(range(1, 21)),
            starting_eleven=list(range(1, 12)), captain=1, country_tactics=0,
        )
        result_data = {"score": (1, 0), "goals": [], "seed_DS7B62": 1,
                       "seed_DS8336": 2}
        full_result = {
            "teams": (1, 2), "managed_side": 0, "score": (1, 0),
            "goals": [], "seed_DS7B62": 1, "seed_DS8336": 2,
            "halves": ({"score": (1, 0), "goals": []},
                       {"score": (1, 0), "goals": []}),
        }
        cases = [
            (country_select, lambda: country_select.run_country_select(data, None), [Key.ENTER],
             country_select._render(data, 1, 20)),
            (squad, lambda: squad.run_squad_select(data, None, state=state), [Key.ENTER],
             squad._render(data, state, 1, 20)),
            (tactics, lambda: tactics.run_tactics_select(data, None), [Key.ENTER],
             tactics._build_grid(0, 1)),
            (preview, lambda: preview.run_match_preview(
                data, b"synthetic", None, state=state), [Key.ENTER],
             preview._build_grid(data, state, (1, 2), 0, 2, None)),
            (result, lambda: result.run_result(b"synthetic", None), [Key.ENTER],
             result._build_grid(result_data, None)),
            (result, lambda: result.run_result(b"synthetic", None, state=state,
                                               full_match=True, goaldat=data),
             [Key.ENTER], result._build_grid(full_result, None, full_match=True,
                                             state=state, goaldat=data)),
        ]
        for module, run, keys, expected_grid in cases:
            with self.subTest(screen=module.__name__):
                output = Stream(terminal=True)
                reads = 0
                expected = "\x1b[2J\x1b[H" + render(expected_grid).rstrip("\n")

                def read():
                    nonlocal reads
                    self.assertEqual(output.flushes, reads + 1)
                    self.assertEqual(output.getvalue(), expected)
                    reads += 1
                    return keys[reads - 1]

                with patch.dict(os.environ, {"TERM": "xterm-256color"}), \
                     redirect_stdout(output), ExitStack() as stack:
                    stack.enter_context(patch.object(module, "read_key", side_effect=read))
                    if module is preview:
                        stack.enter_context(patch.object(preview, "Savestate", return_value=object()))
                        stack.enter_context(patch.object(preview, "resolve_full_matchup",
                                                         return_value=((1, 2), 0, 2)))
                    if module is result:
                        stack.enter_context(patch.object(result, "Savestate", return_value=object()))
                        if run is cases[4][1]:
                            stack.enter_context(patch.object(result._qe, "simulate",
                                                             return_value=result_data))
                        else:
                            stack.enter_context(patch.object(result, "run_full_match",
                                                             return_value=full_result))
                    run()
                self.assertEqual(reads, 1)
                self.assertEqual(output.flushes, 1)

    def test_all_screens_have_actionable_headings_and_help(self):
        data = SimpleNamespace(country_names=[""] + ["Country"] * 128,
                               player_names=[""] + ["Player"] * 20,
                               player_initials=[""] + ["P"] * 20)
        state = SimpleNamespace(managed_country=1, managed_squad=list(range(1, 21)),
                                 starting_eleven=list(range(1, 12)), captain=1,
                                 country_tactics=0)
        grids = [
            country_select._render(data, 1, 20),
            squad._render(data, state, 1, 20),
            tactics._build_grid(0, 1),
            preview._build_grid(data, state, (1, 2), 0, 2, None),
            result._build_grid({"score": (0, 0), "goals": [], "seed_DS7B62": 1,
                                "seed_DS8336": 2}, None),
        ]
        frames = [render(grid) for grid in grids]
        expectations = [
            ("SELECT COUNTRY", "UP/DOWN MOVE", "ENTER SELECT", "ESC QUIT"),
            ("SELECT ELEVEN", "UP/DOWN", "SPACE TOGGLE", "ENTER CONFIRM", "ESC CANCEL"),
            ("TACTICS", "UP/DOWN MOVE", "SPACE TOGGLE", "ENTER CONFIRM", "ESC QUIT"),
            ("MATCH PREVIEW", "ENTER PLAY MATCH", "ESC QUIT"),
            ("RESULT", "ENTER CONTINUE", "ESC QUIT"),
        ]
        for frame, terms in zip(frames, expectations):
            for term in terms:
                with self.subTest(term=term):
                    self.assertIn(term, frame)

    def test_scripted_iterables_remain_silent(self):
        data = SimpleNamespace(country_names=[""] + ["Country"] * 128,
                               player_names=[""] + ["Player"] * 20,
                               player_initials=[""] + ["P"] * 20)
        state = SimpleNamespace(managed_country=1, managed_squad=list(range(1, 21)),
                                 starting_eleven=list(range(1, 12)), captain=1,
                                 country_tactics=0)
        calls = [
            lambda: country_select.run_country_select(data, [Key.ENTER]),
            lambda: squad.run_squad_select(data, [Key.ENTER], state=state),
            lambda: tactics.run_tactics_select(data, [Key.ENTER]),
            lambda: preview.run_match_preview(data, b"synthetic", [Key.ESC], state=state),
            lambda: result.run_result(b"synthetic", [Key.ESC]),
        ]
        output = io.StringIO()
        with patch.object(preview, "Savestate", return_value=object()), \
             patch.object(preview, "resolve_full_matchup", return_value=((1, 2), 0, 2)), \
             patch.object(result, "Savestate", return_value=object()), \
             patch.object(result._qe, "simulate", return_value={"score": (0, 0), "goals": [],
                                                                  "seed_DS7B62": 1, "seed_DS8336": 2}), \
             redirect_stdout(output):
            for run in calls:
                run()
        self.assertEqual(output.getvalue(), "")


if __name__ == "__main__":
    unittest.main()
