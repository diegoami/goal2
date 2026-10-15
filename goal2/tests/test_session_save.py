"""Synthetic round-trip and menu/CLI checks for rebuild session saves. [designed: T33]"""
import json
import tempfile
import unittest
import zipfile
from contextlib import redirect_stderr
from io import StringIO
from pathlib import Path
from unittest.mock import patch

from goal2.game.session_save import (
    VERSION, SessionSaveError, decode, encode, load, save,
)
from goal2.game.state import GameState
from goal2 import loop
from goal2.main_loop import run_main_loop
from goal2.ui import next_action
from goal2.ui.input import Key


def _state():
    return GameState(
        players=[bytes([i % 251]) * 20 for i in range(3061)],
        countries=[bytes([i % 251]) * 0xBF for i in range(129)],
        managed_country=42,
        managed_squad=list(range(1001, 1021)),
        rng_seed_7b62=0xABCD,
        rng_seed_8336=0x7654,
        match_state={"clock": 91, "score": (2, 1), "minute": 92, "half": 2},
        vga=b"synthetic vga\x00" * 19,
        mem=bytearray(b"synthetic memory\xFF" * 31),
        starting_eleven=[1010, 1002, 1003, 1004, 1005, 1006, 1007, 1008, 1009, 1001, 1011],
        captain=538,
        country_tactics=0xA5,
        match_count=7,
        last_match={"score": (2, 1), "teams": (42, 8),
                    "goals": [{"team": 0, "minute": 88, "player": 538}]},
    )


class SessionSaveRoundTrip(unittest.TestCase):
    def test_round_trip_preserves_every_field_and_template(self):
        original = _state()
        raw = encode(original, b"template bytes with\x00 and\xff")
        loaded, template = decode(raw)
        self.assertEqual(template, b"template bytes with\x00 and\xff")
        for field in ("players", "countries", "managed_country", "managed_squad",
                      "starting_eleven", "captain", "country_tactics", "rng_seed_7b62",
                      "rng_seed_8336", "match_state", "vga", "mem", "match_count", "last_match"):
            self.assertEqual(getattr(loaded, field), getattr(original, field), field)
        self.assertGreater(loaded.captain, 255)
        self.assertEqual(loaded.managed_country, 42)
        self.assertNotEqual(loaded.starting_eleven, loaded.managed_squad[:11])

    def test_rejects_corrupt_unsupported_and_bad_shapes(self):
        with self.assertRaisesRegex(SessionSaveError, "invalid session save JSON"):
            decode(b"{not json")
        doc = json.loads(encode(_state(), b"template"))
        doc["version"] = VERSION + 1
        with self.assertRaisesRegex(SessionSaveError, "unsupported session save version"):
            decode(json.dumps(doc).encode())
        doc = json.loads(encode(_state(), b"template"))
        doc["state"]["captain"] = 70000
        with self.assertRaisesRegex(SessionSaveError, "captain"):
            decode(json.dumps(doc).encode())
        doc = json.loads(encode(_state(), b"template"))
        del doc["state"]["last_match"]
        with self.assertRaisesRegex(SessionSaveError, "missing or unknown fields"):
            decode(json.dumps(doc).encode())

    def test_deterministic_continuation_uses_identical_loaded_state_and_template(self):
        state = _state()
        raw = encode(state, b"fixed synthetic halftime template")
        resumed, template = decode(raw)
        # Deterministic continuation inputs are the exact complete state and
        # template bytes consumed by the next-match adapter. [designed: T33]
        self.assertEqual(encode(resumed, template), raw)
        self.assertEqual((resumed.rng_seed_7b62, resumed.rng_seed_8336),
                         (state.rng_seed_7b62, state.rng_seed_8336))
        self.assertEqual(resumed.players, state.players)
        self.assertEqual(resumed.countries, state.countries)


class AtomicSave(unittest.TestCase):
    def test_serialization_and_replace_failures_preserve_previous_file(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "session.g2save"
            path.write_bytes(b"old save")
            bad_state = _state()
            bad_state.match_state = {"not_json": object()}
            with self.assertRaisesRegex(SessionSaveError, "cannot serialize"):
                save(path, bad_state, b"template")
            self.assertEqual(path.read_bytes(), b"old save")
            with patch("goal2.game.session_save.os.fsync", side_effect=OSError("write failed")):
                with self.assertRaisesRegex(SessionSaveError, "cannot write session save"):
                    save(path, _state(), b"template")
            self.assertEqual(path.read_bytes(), b"old save")
            with patch("goal2.game.session_save.os.replace", side_effect=OSError("disk is read-only")):
                with self.assertRaisesRegex(SessionSaveError, "cannot write session save"):
                    save(path, _state(), b"template")
            self.assertEqual(path.read_bytes(), b"old save")
            self.assertEqual(list(Path(directory).iterdir()), [path])

    def test_path_load_reports_malformed_save(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "bad.g2save"
            path.write_bytes(b"not a save")
            with self.assertRaises(SessionSaveError):
                load(path)


class SaveMenu(unittest.TestCase):
    def test_save_success_quits_and_default_enter_still_quits(self):
        saved = []
        self.assertFalse(next_action.run_next_action(
            [Key.UP, Key.ENTER], on_save=lambda: saved.append("saved")))
        self.assertEqual(saved, ["saved"])
        self.assertFalse(next_action.run_next_action([Key.ENTER]))
        self.assertTrue(next_action.run_next_action([Key.UP, Key.UP, Key.ENTER]))

    def test_save_failure_stays_for_retry_and_shows_error(self):
        calls = []
        def save_then_succeed():
            calls.append(1)
            if len(calls) == 1:
                raise OSError("disk full")
        self.assertFalse(next_action.run_next_action(
            [Key.UP, Key.ENTER, Key.ENTER], on_save=save_then_succeed))
        self.assertEqual(len(calls), 2)
        frame = next_action._build_grid(1, "Save failed: disk full")
        from goal2.ui.plain_renderer import render
        self.assertIn("Save failed: disk full", render(frame))


class ResumeFlow(unittest.TestCase):
    def test_resume_menu_precedes_country_selection_and_simulation(self):
        state = _state()
        country_calls = []
        def choose(*args, **kwargs):
            country_calls.append(True)
            return 42
        with patch("goal2.main_loop.run_country_select", side_effect=choose), \
             patch("goal2.main_loop.run_result") as result:
            self.assertEqual(run_main_loop(object(), state, b"template", keys=[Key.ENTER], resume=True), 0)
        self.assertEqual(country_calls, [])
        result.assert_not_called()

    def test_resume_play_keeps_saved_country_and_skips_country_selection(self):
        state = _state()
        observed = []
        country_calls = []
        def choose(*args, **kwargs):
            country_calls.append(True)
            return 42
        with patch("goal2.main_loop.run_country_select", side_effect=choose), \
             patch("goal2.main_loop.run_squad_select", side_effect=lambda gd, keys, state: observed.append(state.managed_country) or False):
            self.assertEqual(run_main_loop(object(), state, b"template",
                                           keys=[Key.UP, Key.UP, Key.ENTER], resume=True), 0)
        self.assertEqual(country_calls, [])
        self.assertEqual(observed, [42])


class SessionCli(unittest.TestCase):
    def test_legacy_cli_and_resume_cli_paths(self):
        with tempfile.TemporaryDirectory() as directory:
            legacy = Path(directory) / "legacy.sav"
            goal = Path(directory) / "GOAL.DAT"
            session = Path(directory) / "session.g2save"
            legacy.write_bytes(b"legacy")
            goal.write_bytes(b"goal data")
            legacy_state = _state()
            with patch.object(loop, "load_goaldat", return_value="data"), \
                 patch.object(loop, "from_savestate", return_value=legacy_state), \
                 patch.object(loop, "run_main_loop", return_value=0) as run:
                self.assertEqual(loop.main(["loop", "--save", str(session), str(legacy), str(goal)]), 0)
                args, kwargs = run.call_args
                self.assertEqual(args, ("data", legacy_state, b"legacy"))
                self.assertFalse(kwargs.get("resume", False))
                self.assertTrue(callable(kwargs["on_save"]))
                kwargs["on_save"]()
            saved_state, saved_template = load(session)
            self.assertEqual(saved_state.managed_country, 42)
            self.assertEqual(saved_template, b"legacy")
            with patch.object(loop, "load_goaldat", return_value="data"), \
                 patch.object(loop, "load_session", return_value=(_state(), b"template")), \
                 patch.object(loop, "from_savestate", return_value="validated template"), \
                 patch.object(loop, "to_savestate", return_value=b"continuation"), \
                 patch.object(loop, "run_main_loop", return_value=0) as run:
                self.assertEqual(loop.main(["loop", "--resume", str(session), str(goal)]), 0)
                args, kwargs = run.call_args
                self.assertEqual(args, ("data", run.call_args.args[1], b"template"))
                self.assertTrue(kwargs["resume"])
                self.assertTrue(callable(kwargs["on_save"]))

    def test_resume_rejects_corrupt_template_and_loaded_memory_before_terminal(self):
        with tempfile.TemporaryDirectory() as directory:
            save_path = Path(directory) / "session.g2save"
            goal_path = Path(directory) / "GOAL.DAT"
            save_path.write_bytes(b"session marker")
            goal_path.write_bytes(b"goal data")
            with patch.object(loop, "load_goaldat", return_value="data"), \
                 patch.object(loop, "load_session", return_value=(_state(), b"not a zip")), \
                 patch.object(loop, "from_savestate", side_effect=zipfile.BadZipFile("bad archive")), \
                 patch.object(loop, "to_savestate") as adapt, \
                 patch.object(loop, "terminal_input") as terminal, \
                 patch.object(loop, "run_main_loop") as run:
                with redirect_stderr(StringIO()) as error:
                    self.assertEqual(loop.main(["loop", "--resume", str(save_path), str(goal_path)]), 2)
                self.assertIn("bad archive", error.getvalue())
            adapt.assert_not_called()
            terminal.assert_not_called()
            run.assert_not_called()

            with patch.object(loop, "load_goaldat", return_value="data"), \
                 patch.object(loop, "load_session", return_value=(_state(), b"valid template")), \
                 patch.object(loop, "from_savestate", return_value="parsed template"), \
                 patch.object(loop, "to_savestate", side_effect=ValueError("saved Memory is too short")), \
                 patch.object(loop, "terminal_input") as terminal, \
                 patch.object(loop, "run_main_loop") as run:
                with redirect_stderr(StringIO()) as error:
                    self.assertEqual(loop.main(["loop", "--resume", str(save_path), str(goal_path)]), 2)
                self.assertIn("saved Memory is too short", error.getvalue())
            terminal.assert_not_called()
            run.assert_not_called()

    def test_cli_rejects_bad_save_before_entering_play(self):
        with tempfile.TemporaryDirectory() as directory:
            save_path = Path(directory) / "bad.g2save"
            goal_path = Path(directory) / "GOAL.DAT"
            save_path.write_bytes(b"bad")
            goal_path.write_bytes(b"goal data")
            with patch.object(loop, "load_goaldat", return_value="data"), \
                 patch.object(loop, "run_main_loop") as run:
                self.assertEqual(loop.main(["loop", "--resume", str(save_path), str(goal_path)]), 2)
            run.assert_not_called()


if __name__ == "__main__":
    unittest.main()
