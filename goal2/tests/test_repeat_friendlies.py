"""[designed: T32] Consecutive assumed friendlies retain successful state."""
import io
import hashlib
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

# [designed: T01 vendored import layout] Register the engine's sibling reader.
from goal2 import cli  # noqa: F401

from goal2.engine.quick_engine import QuickMatch
from goal2.engine.savestate import Savestate
from goal2.game import state as game_state_module
from goal2.game.quick_match import run_full_match
from goal2.main_loop import run_main_loop
from goal2.tests.test_cpu_tactics_change import build_state, squad_words, C0
from goal2.ui import next_action, result, squad
from goal2.ui.input import Key
from goal2.ui.plain_renderer import render


def _game_state():
    return SimpleNamespace(
        managed_country=C0,
        managed_squad=squad_words(C0),
        starting_eleven=squad_words(C0)[:11],
        captain=squad_words(C0)[0],
        country_tactics=0x20,
        players=[bytes(20) for _ in range(3061)],
        countries=[bytes(0xBF) for _ in range(129)],
        rng_seed_7b62=0,
        rng_seed_8336=0,
        match_count=0,
        last_match=None,
    )


class RetainedRunner(unittest.TestCase):
    def test_default_runner_remains_stateless(self):
        state = build_state(seed=0x1234)
        game = _game_state()
        before = (list(game.players), game.rng_seed_7b62, game.rng_seed_8336,
                  game.match_count, game.last_match)
        run_full_match(state, game)
        self.assertEqual((game.players, game.rng_seed_7b62, game.rng_seed_8336,
                          game.match_count, game.last_match), before)

    def test_retained_runner_commits_records_seeds_summary_once(self):
        state = build_state(seed=0x1234)
        game = _game_state()
        def mutate(qm, minute, countdown):
            if minute == 45:
                qm.playerrec[squad_words(C0)[0]][0x0E] = 19
                qm.rng.seed = 0x4567

        with patch.object(QuickMatch, "d733", mutate):
            result = run_full_match(state, game, retain_state=True)
        player = squad_words(C0)[0]
        self.assertEqual(game.players[player][0x0E], 19)
        self.assertEqual(game.rng_seed_7b62, result["seed_DS7B62"])
        self.assertEqual(game.rng_seed_8336, result["seed_DS8336"])
        self.assertEqual(game.match_count, 1)
        self.assertEqual(game.last_match["score"], result["score"])
        self.assertEqual(game.last_match["goals"], result["goals"])
        self.assertEqual(game.managed_squad, squad_words(C0))
        self.assertEqual(game.starting_eleven, squad_words(C0)[:11])
        self.assertEqual(game.captain, squad_words(C0)[0])
        self.assertEqual(game.country_tactics, 0x20)

    def test_failure_does_not_commit_partial_mutations(self):
        state = build_state(seed=0x1234)
        game = _game_state()
        before = (list(game.players), game.rng_seed_7b62, game.rng_seed_8336,
                  game.match_count, game.last_match)

        def fail_in_second_half(qm, minute, countdown):
            if minute == 50:
                qm.playerrec[squad_words(C0)[0]][0x0E] = 1
                qm.rng.seed = 0xABCD
                raise RuntimeError("synthetic simulation failure")

        with patch.object(QuickMatch, "d733", fail_in_second_half), \
             self.assertRaisesRegex(RuntimeError, "synthetic simulation failure"):
            run_full_match(state, game, retain_state=True)
        self.assertEqual((game.players, game.rng_seed_7b62, game.rng_seed_8336,
                          game.match_count, game.last_match), before)


class RepeatFriendlyLoop(unittest.TestCase):
    def _state(self):
        return game_state_module.GameState(
            players=[bytes(20) for _ in range(3061)],
            countries=[bytes(0xBF) for _ in range(129)],
            managed_country=1, managed_squad=list(range(1, 21)),
            rng_seed_7b62=1, rng_seed_8336=2, match_state={},
            vga=bytes(4000), mem=bytearray(1 << 16),
        )

    def test_main_loop_repeats_same_country_and_keeps_choices(self):
        state = self._state()
        state.managed_country = 7
        state.managed_squad = list(range(121, 141))
        state.starting_eleven = list(range(121, 132))
        state.captain = 125
        state.country_tactics = 0x42
        goaldat = SimpleNamespace()
        seen = []

        def screen(name, ret=True):
            def call(*args, **kwargs):
                seen.append((name, state.managed_country, tuple(state.starting_eleven),
                             state.captain, state.country_tactics))
                return ret
            return call

        def finished(*args, **kwargs):
            seen.append(("result", state.managed_country, tuple(state.starting_eleven),
                         state.captain, state.country_tactics))
            state.match_count += 1
            return True

        keys = [Key.DOWN, Key.ENTER, Key.ENTER]  # Play again, then quit by default.
        with patch("goal2.main_loop.run_country_select", return_value=7) as choose, \
             patch("goal2.main_loop.run_squad_select", side_effect=screen("squad")) as select_squad, \
             patch("goal2.main_loop.run_tactics_select", side_effect=screen("tactics")) as select_tactics, \
             patch("goal2.main_loop.run_match_preview", side_effect=screen("preview")), \
             patch("goal2.main_loop.run_result", side_effect=finished), \
             patch("goal2.main_loop.to_savestate", side_effect=[b"first", b"second"]):
            run_main_loop(goaldat, state, b"original", keys=iter(keys))
        choose.assert_called_once()
        self.assertEqual(select_squad.call_count, 2)
        self.assertEqual(select_tactics.call_count, 2)
        self.assertEqual([row[0] for row in seen],
                         ["squad", "tactics", "preview", "result"] * 2)
        for _, country, eleven, captain, tactics in seen:
            self.assertEqual(country, 7)
            self.assertEqual(eleven, tuple(range(121, 132)))
            self.assertEqual(captain, 125)
            self.assertEqual(tactics, 0x42)

    def test_quit_cancel_and_exhaustion_never_start_a_second_match(self):
        for keys in ([Key.ESC], []):
            with self.subTest(keys=keys):
                state = self._state()
                with patch("goal2.main_loop.run_country_select", return_value=7), \
                     patch("goal2.main_loop.run_squad_select", return_value=True), \
                     patch("goal2.main_loop.run_tactics_select", return_value=True), \
                     patch("goal2.main_loop.run_match_preview", return_value=True), \
                     patch("goal2.main_loop.run_result", return_value=True) as result_screen, \
                     patch("goal2.main_loop.to_savestate", return_value=b"saved"):
                    # Model a completed first match; menu Esc/exhaustion must stop.
                    def finish(*args, **kwargs):
                        state.match_count += 1
                        return True
                    result_screen.side_effect = finish
                    run_main_loop(SimpleNamespace(), state, b"original", keys=iter(keys))
                result_screen.assert_called_once()

    def test_refused_match_does_not_offer_or_start_another(self):
        state = self._state()
        with patch("goal2.main_loop.run_country_select", return_value=7), \
             patch("goal2.main_loop.run_squad_select", return_value=True), \
             patch("goal2.main_loop.run_tactics_select", return_value=True), \
             patch("goal2.main_loop.run_match_preview", return_value=True), \
             patch("goal2.main_loop.run_result", return_value=True) as result_screen, \
             patch("goal2.main_loop.run_next_action") as next_action_screen, \
             patch("goal2.main_loop.to_savestate", return_value=b"saved"):
            run_main_loop(SimpleNamespace(), state, b"original", keys=iter([Key.ENTER]))
        result_screen.assert_called_once()
        next_action_screen.assert_not_called()

    def test_next_action_menu_visible_flushed_and_scripted_silent(self):
        first = render(next_action._build_grid(1))
        second = render(next_action._build_grid(0))
        self.assertIn("Play another friendly", second)
        self.assertIn("Quit", first)
        out = io.StringIO()
        with redirect_stdout(out):
            self.assertFalse(next_action.run_next_action(iter([])))
        self.assertEqual(out.getvalue(), "")
        class FlushOutput(io.StringIO):
            flushes = 0

            def flush(self):
                self.flushes += 1
                super().flush()

        output = FlushOutput()
        reads = 0

        def read_menu_key():
            nonlocal reads
            self.assertEqual(output.flushes, reads + 1)
            frame = output.getvalue()
            self.assertIn("Play another friendly", frame)
            reads += 1
            return (Key.DOWN, Key.ENTER)[reads - 1]

        with redirect_stdout(output), patch.object(next_action, "read_key", side_effect=read_menu_key):
            self.assertTrue(next_action.run_next_action())
        self.assertEqual(output.flushes, 2)
        self.assertEqual(reads, 2)
        self.assertFalse(next_action.run_next_action([Key.ESC]))

    def test_full_friendly_result_opts_into_retention(self):
        state = self._state()
        result_data = {
            "teams": (1, 2), "managed_side": 0, "score": (0, 0),
            "goals": [], "seed_DS7B62": 1, "seed_DS8336": 2,
            "halves": ({"score": (0, 0), "goals": []},
                       {"score": (0, 0), "goals": []}),
        }
        with patch.object(result, "Savestate", return_value=object()), \
             patch.object(result, "run_full_match", return_value=result_data) as runner:
            self.assertTrue(result.run_result(b"fixture", [Key.ENTER], state=state,
                                               full_match=True))
        self.assertTrue(runner.call_args.kwargs["retain_state"])

    def test_squad_rows_show_current_energy_without_shifting_captain(self):
        state = self._state()
        state.players[1] = bytes(14) + bytes([14]) + bytes(5)
        state.captain = 5
        data = SimpleNamespace(player_names=[""] + [f"P{i}" for i in range(1, 22)],
                               player_initials=[""] + ["P"] * 21)
        frame = render(squad._render(data, state, cursor=1, page_size=20))
        self.assertIn("Energy:14", frame.splitlines()[1])
        self.assertEqual(frame.splitlines()[5][78:80], " C")

    def test_e010_two_match_adapter_roundtrip_carries_energy_and_both_seeds(self):
        """[designed: T32] Actual cached E010 input feeds two retained runs."""
        root = Path(__file__).resolve().parents[2]
        fixture = root / ".cache" / "e010-r0001-halftime.sav"
        if not fixture.is_file():
            self.skipTest("cached E010-r0001 savestate unavailable")
        original = fixture.read_bytes()
        # [confirmed: E010 release manifest] E010-r0001 asset digest prefix.
        self.assertTrue(hashlib.sha256(original).hexdigest().startswith(
            "e1dee7e2f5ad443e"))
        game = game_state_module.from_savestate(original)
        player = 122
        self.assertIn(player, game.managed_squad)
        # [confirmed: E010-r0001] Pin the fixture's initial player and seeds.
        self.assertEqual(game.players[player][0x0E], 25)
        self.assertEqual((game.rng_seed_7b62, game.rng_seed_8336), (42903, 20904))
        game.starting_eleven = list(game.managed_squad[:11])
        first_input = game_state_module.to_savestate(game, original=original)
        first = run_full_match(Savestate(first_input), game, retain_state=True)
        first_finished_energy = game.players[player][0x0E]
        self.assertNotEqual(first_finished_energy, 25)
        self.assertNotEqual(first["seed_DS7B62"], 42903)
        self.assertEqual(first["seed_DS8336"], 20904)
        second_input = game_state_module.to_savestate(game, original=original)
        seen = []
        original_d733 = QuickMatch.d733

        def inspect_second_start(qm, minute, countdown):
            if minute == 0:
                seen.append((qm.rng.seed, qm.seed2, qm._player(player)[0x0E]))
            return original_d733(qm, minute, countdown)

        with patch.object(QuickMatch, "d733", inspect_second_start):
            second = run_full_match(Savestate(second_input), game, retain_state=True)
        self.assertEqual(seen, [(first["seed_DS7B62"], first["seed_DS8336"],
                                 first_finished_energy)])
        self.assertEqual(game.match_count, 2)
        self.assertEqual(game.last_match["score"], second["score"])
        self.assertNotEqual(second["seed_DS7B62"], first["seed_DS7B62"])
        self.assertEqual(second["seed_DS8336"], first["seed_DS8336"])


if __name__ == "__main__":
    unittest.main()
