"""Tests for `goal2.main_loop`.

[derived: T15's screen function signatures and return conventions;
A-WATCH-1 — result is T14's stand-in; GA-4 — keys flow through the driver.]
[designed: the screen ordering, the shared-state contract, and the
next-fixture placeholder text.]
"""
import unittest
from unittest.mock import MagicMock, patch, call

from goal2.data.goaldat import GoalDat
from goal2.engine.state import GameState
from goal2.main_loop import run_main_loop
from goal2.ui.input import Key


def _keys(*items: Key):
    """Return an iterator that yields Key values then stops cleanly."""
    return iter(items)


def _make_goaldat() -> GoalDat:
    """Return a minimal GoalDat with distinctive country names."""
    gd = GoalDat()
    gd.country_names = [""] + [f"Country{i}" for i in range(1, 129)]
    gd.player_names = [f"P{i}" for i in range(3061)]
    gd.player_initials = [""] + ["X"] * 3060
    gd.squad_20 = [[i] * 20 for i in range(129)]
    return gd


def _make_state() -> GameState:
    """Return a GameState with placeholder fields."""
    return GameState(
        players=[b"\x00" * 20] * 3061,
        countries=[b"\x00" * 0xBF] * 129,
        managed_country=1,
        managed_squad=list(range(20)),
        rng_seed_7b62=0,
        rng_seed_8336=0,
        match_state={},
        vga=b"\x00" * 4000,
        mem=bytearray(1 << 16),
    )


class TestRunMainLoopOrderAndState(unittest.TestCase):
    """Done-when 2, 3, 4: call order and shared state."""

    def test_country_select_called_first_with_state(self):
        """Done-when 2: run_country_select is called first and receives state."""
        gd = _make_goaldat()
        state = _make_state()

        with patch("goal2.main_loop.run_country_select") as mock_cs, \
             patch("goal2.main_loop.run_squad_select") as mock_sq, \
             patch("goal2.main_loop.run_tactics_select") as mock_tac, \
             patch("goal2.main_loop.run_result") as mock_res:

            mock_cs.return_value = None  # Esc immediately

            run_main_loop(gd, state, "/fake/savestate", keys=_keys(Key.ESC))

            mock_cs.assert_called_once()
            _, kwargs = mock_cs.call_args
            self.assertIs(kwargs.get("state"), state)

    def test_managed_country_set_after_country_select(self):
        """Done-when 3: after country select returns 7, state.managed_country == 7."""
        gd = _make_goaldat()
        state = _make_state()
        state.managed_country = 1  # pre-set, confirm it changes

        # Only mock the screens we don't want to exercise; country_select
        # runs for real so it sets state.managed_country.
        # Keys: DOWN×6 + ENTER from country 1 lands on country 7.
        with patch("goal2.main_loop.run_squad_select") as mock_sq, \
             patch("goal2.main_loop.run_tactics_select") as mock_tac, \
             patch("goal2.main_loop.run_result") as mock_res:

            mock_sq.return_value = False  # Esc on squad

            # DOWN×6 + ENTER from country 1 lands on country 7
            run_main_loop(gd, state, "/fake/savestate", keys=_keys(*([Key.DOWN] * 6), Key.ENTER))

            self.assertEqual(state.managed_country, 7)

    def test_all_four_screens_called_in_order_with_same_state(self):
        """Done-when 4: squad, tactics, result called in order, all with the same state object."""
        gd = _make_goaldat()
        state = _make_state()
        # Mutable tracker so plain-function spies can update it
        tracker = {"cs_state": None, "sq_state": None, "ta_state": None, "re_state": None}
        call_order = []

        def spy_cs(*args, **kwargs):
            call_order.append("country_select")
            tracker["cs_state"] = kwargs.get("state")
            return 7

        def spy_sq(*args, **kwargs):
            call_order.append("squad_select")
            tracker["sq_state"] = kwargs.get("state")
            return True

        def spy_ta(*args, **kwargs):
            call_order.append("tactics_select")
            tracker["ta_state"] = kwargs.get("state")
            return True

        def spy_re(*args, **kwargs):
            call_order.append("result")
            tracker["re_state"] = kwargs.get("state")
            return True

        with patch("goal2.main_loop.run_country_select", spy_cs), \
             patch("goal2.main_loop.run_squad_select", spy_sq), \
             patch("goal2.main_loop.run_tactics_select", spy_ta), \
             patch("goal2.main_loop.run_result", spy_re):

            run_main_loop(gd, state, "/fake/savestate", keys=_keys(Key.ENTER))

        self.assertEqual(call_order, ["country_select", "squad_select", "tactics_select", "result"])
        # All four calls received the same state object
        self.assertIs(tracker["cs_state"], state)
        self.assertIs(tracker["sq_state"], state)
        self.assertIs(tracker["ta_state"], state)
        self.assertIs(tracker["re_state"], state)


class TestEscAbortsLoop(unittest.TestCase):
    """Done-when 5: Esc from any screen returns 0 without calling later screens."""

    def test_esc_on_country_select_skips_all_others(self):
        """Done-when 5: None from country_select → squad, tactics, result not called."""
        gd = _make_goaldat()
        state = _make_state()

        with patch("goal2.main_loop.run_country_select") as mock_cs, \
             patch("goal2.main_loop.run_squad_select") as mock_sq, \
             patch("goal2.main_loop.run_tactics_select") as mock_tac, \
             patch("goal2.main_loop.run_result") as mock_res:

            mock_cs.return_value = None  # Esc

            rc = run_main_loop(gd, state, "/fake/savestate", keys=_keys(Key.ESC))

        self.assertEqual(rc, 0)
        mock_sq.assert_not_called()
        mock_tac.assert_not_called()
        mock_res.assert_not_called()

    def test_esc_on_squad_select_skips_tactics_and_result(self):
        """Done-when 5: False from squad_select → tactics, result not called."""
        gd = _make_goaldat()
        state = _make_state()

        with patch("goal2.main_loop.run_country_select") as mock_cs, \
             patch("goal2.main_loop.run_squad_select") as mock_sq, \
             patch("goal2.main_loop.run_tactics_select") as mock_tac, \
             patch("goal2.main_loop.run_result") as mock_res:

            mock_cs.return_value = 7
            mock_sq.return_value = False  # Esc

            rc = run_main_loop(gd, state, "/fake/savestate",
                               keys=_keys(Key.ENTER, Key.ESC))

        self.assertEqual(rc, 0)
        mock_cs.assert_called_once()
        mock_sq.assert_called_once()
        mock_tac.assert_not_called()
        mock_res.assert_not_called()

    def test_esc_on_tactics_select_skips_result(self):
        """Done-when 5: False from tactics_select → result not called."""
        gd = _make_goaldat()
        state = _make_state()

        with patch("goal2.main_loop.run_country_select") as mock_cs, \
             patch("goal2.main_loop.run_squad_select") as mock_sq, \
             patch("goal2.main_loop.run_tactics_select") as mock_tac, \
             patch("goal2.main_loop.run_result") as mock_res:

            mock_cs.return_value = 7
            mock_sq.return_value = True
            mock_tac.return_value = False  # Esc

            rc = run_main_loop(gd, state, "/fake/savestate",
                               keys=_keys(Key.ENTER, Key.ENTER, Key.ESC))

        self.assertEqual(rc, 0)
        mock_res.assert_not_called()

    def test_esc_on_result_returns_zero(self):
        """Done-when 5: False from run_result → returns 0 (no further screens)."""
        gd = _make_goaldat()
        state = _make_state()

        with patch("goal2.main_loop.run_country_select") as mock_cs, \
             patch("goal2.main_loop.run_squad_select") as mock_sq, \
             patch("goal2.main_loop.run_tactics_select") as mock_tac, \
             patch("goal2.main_loop.run_result") as mock_res:

            mock_cs.return_value = 7
            mock_sq.return_value = True
            mock_tac.return_value = True
            mock_res.return_value = False  # Esc

            rc = run_main_loop(gd, state, "/fake/savestate",
                               keys=_keys(Key.ENTER, Key.ENTER, Key.ENTER, Key.ESC))

        self.assertEqual(rc, 0)


class TestNextFixturePlaceholder(unittest.TestCase):
    """Done-when 6: placeholder line printed to stdout using managed_country."""

    def _capture_stdout(self, fn, *args, **kwargs):
        import io, sys
        captured = io.StringIO()
        old = sys.stdout
        sys.stdout = captured
        try:
            rc = fn(*args, **kwargs)
        finally:
            sys.stdout = old
        return rc, captured.getvalue()

    def test_placeholder_contains_country_number(self):
        """Done-when 6: placeholder contains the country number chosen (7)."""
        gd = _make_goaldat()
        state = _make_state()
        state.managed_country = 7

        with patch("goal2.main_loop.run_country_select") as mock_cs, \
             patch("goal2.main_loop.run_squad_select") as mock_sq, \
             patch("goal2.main_loop.run_tactics_select") as mock_tac, \
             patch("goal2.main_loop.run_result") as mock_res:

            mock_cs.return_value = 7
            mock_sq.return_value = True
            mock_tac.return_value = True
            mock_res.return_value = True

            rc, output = self._capture_stdout(
                run_main_loop, gd, state, "/fake/savestate",
                keys=_keys(Key.ENTER, Key.ENTER, Key.ENTER, Key.ENTER))

        self.assertEqual(rc, 0)
        self.assertIn("7", output)
        self.assertIn("Next fixture", output)

    def test_placeholder_missing_fails(self):
        """Deleting the placeholder line makes stdout empty and this test fails."""
        gd = _make_goaldat()
        state = _make_state()
        state.managed_country = 42

        with patch("goal2.main_loop.run_country_select") as mock_cs, \
             patch("goal2.main_loop.run_squad_select") as mock_sq, \
             patch("goal2.main_loop.run_tactics_select") as mock_tac, \
             patch("goal2.main_loop.run_result") as mock_res:

            mock_cs.return_value = 42
            mock_sq.return_value = True
            mock_tac.return_value = True
            mock_res.return_value = True

            rc, output = self._capture_stdout(
                run_main_loop, gd, state, "/fake/savestate",
                keys=_keys(Key.ENTER, Key.ENTER, Key.ENTER, Key.ENTER))

        self.assertEqual(rc, 0)
        self.assertIn("42", output)


class TestEndToEnd(unittest.TestCase):
    """Done-when 8: full end-to-end smoke with empty key sequences."""

    def test_all_screens_called_with_empty_keys_sequence(self):
        """Done-when 8: every screen is called when all return Enter (True)."""
        gd = _make_goaldat()
        state = _make_state()

        with patch("goal2.main_loop.run_country_select") as mock_cs, \
             patch("goal2.main_loop.run_squad_select") as mock_sq, \
             patch("goal2.main_loop.run_tactics_select") as mock_tac, \
             patch("goal2.main_loop.run_result") as mock_res:

            # Empty keys: each screen's key_iter hits StopIteration and breaks,
            # acting as if Enter was pressed on every screen.
            mock_cs.return_value = 7
            mock_sq.return_value = True
            mock_tac.return_value = True
            mock_res.return_value = True

            rc = run_main_loop(gd, state, "/fake/savestate", keys=iter([]))

        self.assertEqual(rc, 0)
        mock_cs.assert_called_once()
        mock_sq.assert_called_once()
        mock_tac.assert_called_once()
        mock_res.assert_called_once()


if __name__ == "__main__":
    unittest.main()
