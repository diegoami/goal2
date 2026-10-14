"""[designed: T28] Local starting-eleven draft selection and confirmation tests."""
import io
import unittest
from contextlib import redirect_stdout
from types import SimpleNamespace
from unittest.mock import patch

from goal2.ui import squad
from goal2.ui.input import Key
from goal2.ui.plain_renderer import render


def _data():
    return SimpleNamespace(
        player_names=[""] + [f"Player{i}" for i in range(1, 21)],
        player_initials=[""] + [f"P{i:02}" for i in range(1, 21)],
    )


def _state():
    return SimpleNamespace(
        managed_squad=list(range(1, 21)),
        starting_eleven=[],
        captain=0,
    )


class _Output(io.StringIO):
    def __init__(self):
        super().__init__()
        self.flushes = 0

    def flush(self):
        self.flushes += 1
        super().flush()


def _interactive(state, keys, observe=None):
    output = _Output()
    index = 0

    def read_key():
        nonlocal index
        if output.flushes != index + 1:
            raise AssertionError(f"screen was not flushed before key {index + 1}")
        if len(output.getvalue().splitlines()) != (index + 1) * 25:
            raise AssertionError(f"screen frame {index + 1} was incomplete before input")
        if any(len(row) != 80 for row in output.getvalue().splitlines()[-25:]):
            raise AssertionError("every frame row must be 80 columns")
        if observe is not None:
            observe(index, output.getvalue(), state)
        key = keys[index]
        index += 1
        return key

    with redirect_stdout(output), patch.object(squad, "read_key", side_effect=read_key):
        result = squad.run_squad_select(_data(), None, state=state)
    if index != len(keys):
        raise AssertionError(f"read {index} keys, expected {len(keys)}")
    return result


class TestElevenSelection(unittest.TestCase):
    def test_replaces_starter_with_bench_player_and_confirms_squad_order(self):
        state = _state()
        keys = [Key.SPACE, *([Key.DOWN] * 11), Key.SPACE, Key.ENTER]
        self.assertTrue(squad.run_squad_select(_data(), keys, state=state))
        self.assertEqual(state.starting_eleven, list(range(2, 13)))
        self.assertEqual(state.captain, 12)

    def test_valid_existing_eleven_is_the_initial_selection(self):
        state = _state()
        state.starting_eleven = list(range(3, 14))
        state.captain = 5
        frame = render(squad._render(_data(), state, cursor=5, page_size=20))
        self.assertIn("11/11", frame)
        self.assertIn("[ ]", frame.splitlines()[1])
        self.assertIn("[x]", frame.splitlines()[3])
        self.assertTrue(squad.run_squad_select(
            _data(), [*([Key.DOWN] * 4), Key.ENTER], state=state
        ))
        self.assertEqual(state.starting_eleven, list(range(3, 14)))
        self.assertEqual(state.captain, 5)

    def test_default_enter_confirms_first_eleven(self):
        state = _state()
        self.assertTrue(squad.run_squad_select(_data(), [Key.ENTER], state=state))
        self.assertEqual(state.starting_eleven, list(range(1, 12)))
        self.assertEqual(state.captain, 1)

    def test_under_eleven_enter_refuses_without_writing_then_retry_succeeds(self):
        state = _state()
        state.starting_eleven = [90] * 11
        state.captain = 90
        def inspect_invalid(index, screen, current):
            if index == 2:
                self.assertIn("10/11", screen)
                self.assertIn("exactly 11", screen.lower())
                self.assertEqual(current.starting_eleven, [90] * 11)
                self.assertEqual(current.captain, 90)

        self.assertTrue(_interactive(
            state, [Key.SPACE, Key.ENTER, Key.SPACE, Key.ENTER], inspect_invalid
        ))
        self.assertEqual(state.starting_eleven, list(range(1, 12)))
        self.assertEqual(state.captain, 1)

    def test_over_eleven_enter_refuses_then_can_be_corrected(self):
        state = _state()
        state.starting_eleven = [90] * 11
        state.captain = 90
        keys = [Key.DOWN] * 11 + [Key.SPACE, Key.ENTER, Key.SPACE, Key.UP, Key.ENTER]
        def inspect_invalid(index, screen, current):
            if index == 13:
                self.assertIn("12/11", screen)
                self.assertIn("exactly 11", screen.lower())
                self.assertEqual(current.starting_eleven, [90] * 11)
                self.assertEqual(current.captain, 90)

        self.assertTrue(_interactive(state, keys, inspect_invalid))
        self.assertEqual(state.starting_eleven, list(range(1, 12)))
        self.assertEqual(state.captain, 11)

    def test_excluded_cursor_cannot_be_captain_and_retry_succeeds(self):
        state = _state()
        keys = [Key.DOWN] * 11 + [Key.ENTER, *([Key.UP] * 11), Key.ENTER]
        def inspect_invalid(index, screen, current):
            if index == 12:
                self.assertIn("captain", screen.lower())
                self.assertIn("included", screen.lower())
                self.assertEqual(current.starting_eleven, [])
                self.assertEqual(current.captain, 0)

        self.assertTrue(_interactive(state, keys, inspect_invalid))
        self.assertEqual(state.starting_eleven, list(range(1, 12)))
        self.assertEqual(state.captain, 1)

    def test_escape_and_script_exhaustion_leave_existing_state_untouched(self):
        for keys in ([Key.SPACE, Key.ESC], []):
            with self.subTest(keys=keys):
                state = _state()
                state.starting_eleven = [30 + i for i in range(11)]
                state.captain = 90
                self.assertFalse(squad.run_squad_select(_data(), keys, state=state))
                self.assertEqual(state.starting_eleven, [30 + i for i in range(11)])
                self.assertEqual(state.captain, 90)

    def test_screen_shows_count_inclusion_cursor_captain_and_actionable_help(self):
        state = _state()
        state.starting_eleven = list(range(2, 13))
        frame = render(squad._render(_data(), state, cursor=12, page_size=20))
        lines = frame.splitlines()
        self.assertIn("11/11", lines[0])
        self.assertTrue(lines[12].startswith("> "))
        self.assertIn("[x]", lines[12])
        self.assertIn("CAPTAIN: Player12 (included)", lines[21])
        self.assertIn("SPACE", lines[24])
        self.assertIn("ENTER", lines[24])
        self.assertIn("ESC", lines[24])

    def test_screen_is_flushed_before_each_interactive_key(self):
        state = _state()
        first = render(squad._render(_data(), state, cursor=1, page_size=20))
        second = render(squad._render(_data(), state, cursor=2, page_size=20))
        self.assertIn("11/11", first)
        self.assertIn("[x]", first.splitlines()[1])
        self.assertTrue(second.splitlines()[2].startswith("> "))
        output = _Output()
        seen = 0

        def read_key():
            nonlocal seen
            self.assertEqual(output.getvalue(), first if seen == 0 else first + second)
            self.assertEqual(output.flushes, seen + 1)
            seen += 1
            return Key.DOWN if seen == 1 else Key.ENTER

        with redirect_stdout(output), patch.object(squad, "read_key", side_effect=read_key):
            self.assertTrue(squad.run_squad_select(_data(), None, state=state))
        self.assertEqual(seen, 2)
        self.assertEqual(output.getvalue(), first + second)


if __name__ == "__main__":
    unittest.main()
