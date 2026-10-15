"""[designed: T29] The preview names the runner's matchup and gates kickoff."""
import io
import unittest
from contextlib import redirect_stdout
from types import SimpleNamespace
from unittest.mock import patch

from goal2.tests.test_cpu_tactics_change import build_state, C0, C1, squad_words
from goal2.engine.quick_engine import QuickMatch
from goal2.ui import preview
from goal2.ui.input import Key
from goal2.ui.plain_renderer import render


def _state(country):
    squad = squad_words(country) if country in (C0, C1) else list(range(61, 81))
    return SimpleNamespace(
        managed_country=country,
        managed_squad=squad,
        starting_eleven=squad[:11],
        captain=squad[0],
        country_tactics=0,
        players=[bytes(20)] * 3061,
        countries=[bytes(0xBF)] * 129,
    )


def _goaldat():
    countries = [""] * 129
    countries[C0], countries[C1], countries[3] = "Sweden", "Denmark", "Albania"
    players = [""] * 3061
    for n in range(1, len(players)):
        players[n] = f"Player {n}"
    return SimpleNamespace(country_names=countries, player_names=players)


class _Output(io.StringIO):
    def __init__(self):
        super().__init__()
        self.flushes = 0

    def flush(self):
        self.flushes += 1
        super().flush()


class MatchPreview(unittest.TestCase):
    def setUp(self):
        self.data = _goaldat()
        self.template = build_state()

    def test_expected_names_follow_actual_engine_sides_for_both_template_sides_and_third_country(self):
        cases = [
            (C0, "Sweden", "Denmark", (C0, C1), 0),
            (C1, "Denmark", "Sweden", (C0, C1), 1),
            (3, "Albania", "Denmark", (3, C1), 0),
        ]
        for country, own_name, opponent_name, expected_teams, expected_side in cases:
            with self.subTest(country=country):
                teams, managed_side, opponent = preview.resolve_full_matchup(
                    self.template, _state(country))
                # These expected names and team indices are pinned independently
                # from the resolver's result, so a wrong opponent cannot bless itself.
                self.assertEqual(teams, expected_teams)
                self.assertEqual(managed_side, expected_side)
                frame = render(preview._render(
                    self.data, _state(country), teams, managed_side, opponent))
                self.assertIn(f"YOUR TEAM: {own_name}", frame)
                self.assertIn(f"OPPONENT: {opponent_name}", frame)

    def test_runner_uses_the_same_resolution_for_both_template_sides_and_third_country(self):
        from goal2.game.quick_match import run_full_match

        for country, expected in ((C0, (C0, C1)), (C1, (C0, C1)), (3, (3, C1))):
            with self.subTest(country=country), patch.object(QuickMatch, "d733"):
                result = run_full_match(self.template, _state(country))
                self.assertEqual(result["teams"], expected)

    def test_preview_lists_selected_eleven_and_names_the_captain(self):
        state = _state(C0)
        frame = render(preview._render(self.data, state, (C0, C1), 0, C1))
        for player in state.starting_eleven:
            self.assertIn(f"Player {player}", frame)
        self.assertIn(f"Player {state.captain} (C)", frame)
        self.assertNotIn("DS:", frame)
        self.assertNotIn("0x", frame)

    def test_action_text_and_confirmation(self):
        state = _state(C0)
        with patch.object(preview, "Savestate", return_value=self.template):
            self.assertTrue(preview.run_match_preview(
                self.data, b"synthetic", iter([Key.ENTER]), state=state))
        frame = render(preview._render(self.data, state, (C0, C1), 0, C1))
        self.assertIn("ENTER PLAY MATCH", frame)
        self.assertIn("ESC QUIT", frame)

    def test_interactive_frame_is_printed_and_flushed_before_input(self):
        state = _state(C0)
        frame = render(preview._render(self.data, state, (C0, C1), 0, C1))
        output = _Output()

        def read():
            self.assertEqual(output.getvalue(), frame)
            self.assertEqual(output.flushes, 1)
            return Key.ENTER

        with patch.object(preview, "Savestate", return_value=self.template), \
                redirect_stdout(output), patch.object(preview, "read_key", side_effect=read):
            self.assertTrue(preview.run_match_preview(
                self.data, b"synthetic", None, state=state))
        self.assertEqual(output.getvalue(), frame)

    def test_escape_and_exhaustion_never_start_simulation_and_scripted_flow_is_silent(self):
        state = _state(C0)
        for keys in (iter([Key.ESC]), iter([])):
            output = io.StringIO()
            with self.subTest(keys=keys), patch.object(preview, "Savestate", return_value=self.template), \
                    patch.object(QuickMatch, "d733") as simulate, redirect_stdout(output), \
                    patch.object(preview, "read_key") as reader:
                self.assertFalse(preview.run_match_preview(
                    self.data, b"synthetic", keys, state=state))
                simulate.assert_not_called()
                reader.assert_not_called()
                self.assertEqual(output.getvalue(), "")

    def test_unsupported_template_is_visible_and_enter_cannot_confirm(self):
        state = _state(C0)
        for offset, value in ((0x9A3D, b"\x01"), (0x7C36, b"\x01")):
            unsupported = build_state()
            unsupported.put(offset, value)
            output = _Output()
            reads = 0

            def read():
                nonlocal reads
                self.assertIn("REFUSED:", output.getvalue())
                self.assertEqual(output.flushes, reads + 1)
                reads += 1
                return (Key.ENTER, Key.ESC)[reads - 1]

            with self.subTest(offset=offset), redirect_stdout(output), \
                    patch.object(preview, "Savestate", return_value=unsupported), \
                    patch.object(preview, "read_key", side_effect=read), \
                    patch.object(QuickMatch, "d733") as simulate:
                self.assertFalse(preview.run_match_preview(
                    self.data, b"synthetic", None, state=state))
            self.assertIn("MATCH NOT STARTED", output.getvalue())
            self.assertEqual(reads, 2)
            simulate.assert_not_called()

    def test_main_loop_stops_before_result_when_preview_is_not_confirmed(self):
        from goal2.main_loop import run_main_loop
        from goal2.game.state import GameState

        state = GameState(
            players=[bytes(20)] * 3061,
            countries=[bytes(0xBF)] * 129,
            managed_country=C0, managed_squad=squad_words(C0),
            rng_seed_7b62=0, rng_seed_8336=0, match_state={},
            vga=bytes(4000), mem=bytes(1 << 16),
            starting_eleven=squad_words(C0)[:11], captain=squad_words(C0)[0],
        )
        with patch("goal2.main_loop.run_country_select", return_value=C0), \
                patch("goal2.main_loop.run_squad_select", return_value=True), \
                patch("goal2.main_loop.run_tactics_select", return_value=True), \
                patch("goal2.main_loop.to_savestate", return_value=b"saved"), \
                patch("goal2.main_loop.run_match_preview", return_value=False) as show, \
                patch("goal2.main_loop.run_result") as result:
            self.assertEqual(run_main_loop(self.data, state, b"original", iter([])), 0)
        show.assert_called_once()
        result.assert_not_called()


if __name__ == "__main__":
    unittest.main()
