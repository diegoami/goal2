"""[designed: T27] Plain-text navigation markers for the three selection screens."""
import io
import unittest
from contextlib import redirect_stdout
from types import SimpleNamespace
from unittest.mock import patch

from goal2.ui import country_select, squad, tactics
from goal2.ui.input import Key


class Output(io.StringIO):
    def __init__(self):
        super().__init__()
        self.flushes = 0

    def flush(self):
        self.flushes += 1
        super().flush()


def _fixture():
    return SimpleNamespace(
        country_names=[""] + [f"Country{i:03d}" for i in range(1, 129)],
        player_names=[""] + [f"Player{i:02d}" for i in range(1, 21)],
        player_initials=[""] + [chr(64 + i) for i in range(1, 21)],
        squad_20=[list(range(1, 21)) for _ in range(129)],
        managed_country=1,
        managed_squad=list(range(1, 21)),
        starting_eleven=[],
        captain=0,
        country_tactics=0,
        countries=[bytes(0xBF) for _ in range(129)],
    )


def _selected_line(output, body_rows, expected_row, expected_label):
    lines = output.getvalue().splitlines()
    expected_frame_count = getattr(output, "expected_frame_count", 0)
    if len(lines) != 25 * expected_frame_count:
        raise AssertionError(
            f"expected {expected_frame_count} complete frames, got {len(lines) // 25}"
        )
    frame = lines[-25:]
    if len(frame) != 25:
        raise AssertionError(f"expected a 25-row frame, got {len(frame)} rows")
    if any(len(line) != 80 for line in frame):
        raise AssertionError("every plain frame row must contain 80 columns")
    selected = [row for row in body_rows if frame[row].startswith("> ")]
    if selected != [expected_row]:
        raise AssertionError(f"expected only body row {expected_row} selected, got {selected}")
    if not frame[expected_row].startswith("> " + expected_label):
        raise AssertionError(f"selected row lost label {expected_label!r}: {frame[expected_row]!r}")
    for row in body_rows:
        if row != expected_row and not frame[row].startswith("  "):
            raise AssertionError(f"unselected row {row} lacks a blank two-column marker")


def _drive(module, run, keys, body_rows, selected):
    output = Output()
    reads = 0

    def read():
        nonlocal reads
        output.expected_frame_count = reads + 1
        _selected_line(output, body_rows, *selected[reads])
        if output.flushes != reads + 1:
            raise AssertionError("frame was not flushed before interactive input")
        key = keys[reads]
        reads += 1
        return key

    with redirect_stdout(output), patch.object(module, "read_key", side_effect=read):
        result = run()
    if reads != len(keys):
        raise AssertionError(f"expected {len(keys)} key reads, got {reads}")
    return result, output.getvalue()


class TestVisibleNavigation(unittest.TestCase):
    def setUp(self):
        self.data = _fixture()

    def test_country_marker_tracks_movement_and_page_changes(self):
        steps = ((1, "Country001"), (2, "Country002"), (22, "Country022"),
                 (2, "Country002"), (1, "Country001"))
        chosen, output = _drive(
            country_select,
            lambda: country_select.run_country_select(self.data, None, page_size=20),
            [Key.DOWN, Key.PAGE_DOWN, Key.PAGE_UP, Key.UP, Key.ENTER],
            list(range(1, 21)),
            [(country - ((country - 1) // 20) * 20, label) for country, label in steps],
        )
        self.assertEqual(chosen, 1)
        self.assertEqual(output.count("> "), 5)

    def test_country_page_bounds_keep_selection_at_first_and_last_country(self):
        result, output = _drive(
            country_select,
            lambda: country_select.run_country_select(
                self.data, None, initial_country=1, page_size=20),
            [Key.PAGE_UP, Key.UP, Key.ENTER], list(range(1, 21)),
            [(1, "Country001")] * 3,
        )
        self.assertEqual(result, 1)
        result, output = _drive(
            country_select,
            lambda: country_select.run_country_select(
                self.data, None, initial_country=128, page_size=20),
            [Key.PAGE_DOWN, Key.DOWN, Key.ENTER], list(range(1, 21)),
            [(8, "Country128")] * 3,
        )
        self.assertEqual(result, 128)

    def test_squad_marker_preserves_player_number_name_and_captain_columns(self):
        self.data.captain = 2
        steps = ((1, " 1  A Player01"), (2, " 2  B Player02"),
                 (1, " 1  A Player01"))
        result, output = _drive(
            squad,
            lambda: squad.run_squad_select(self.data, None, state=self.data),
            [Key.DOWN, Key.UP, Key.ENTER],
            list(range(1, 21)),
            steps,
        )
        self.assertTrue(result)
        frame = output.splitlines()[-25:]
        self.assertEqual(frame[2][78:80], " C")
        self.assertEqual(frame[1][78:80], "  ")
        self.assertTrue(frame[1].startswith(">  1  A Player01"))

    def test_squad_marker_stays_visible_at_both_movement_bounds(self):
        steps = [(1, " 1  A Player01"), (1, " 1  A Player01")]
        steps += [(row, f"{row:2d}  {chr(64 + row)} Player{row:02d}")
                  for row in range(2, 20)]
        steps += [(20, "20  T Player20"), (20, "20  T Player20")]
        keys = [Key.UP, Key.DOWN] + [Key.DOWN] * 19 + [Key.ENTER]
        result, _ = _drive(
            squad,
            lambda: squad.run_squad_select(self.data, None, state=self.data),
            keys, list(range(1, 21)), steps,
        )
        self.assertTrue(result)

    def test_tactics_marker_tracks_rows_without_replacing_checkbox(self):
        steps = ((1, "[ ]  half pitch / full pitch"),
                 (2, "[ ]  short kicks / long kicks"),
                 (2, "[X]  short kicks / long kicks"),
                 (1, "[ ]  half pitch / full pitch"))
        result, output = _drive(
            tactics,
            lambda: tactics.run_tactics_select(self.data, None),
            [Key.DOWN, Key.SPACE, Key.UP, Key.ENTER],
            list(range(1, 9)),
            steps,
        )
        self.assertTrue(result)
        self.assertEqual(output.count("> "), 4)

    def test_tactics_marker_stays_visible_at_both_movement_bounds(self):
        labels = (
            "[ ]  half pitch / full pitch", "[ ]  short kicks / long kicks",
            "[ ]  stay back / push forward", "[ ]  stay back / push forward",
            "[ ]  keep ball / quick pass", "[ ]  short passes / long passes",
            "[ ]  avoid injury / go in hard", "[ ]  zone / man to man",
        )
        steps = [(1, labels[0]), (1, labels[0])]
        steps += [(row, labels[row - 1]) for row in range(2, 8)]
        steps += [(8, labels[7]), (8, labels[7])]
        keys = [Key.UP, Key.DOWN] + [Key.DOWN] * 7 + [Key.ENTER]
        result, _ = _drive(
            tactics, lambda: tactics.run_tactics_select(self.data, None),
            keys, list(range(1, 9)), steps,
        )
        self.assertTrue(result)


if __name__ == "__main__":
    unittest.main()
