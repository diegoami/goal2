"""Tests for `goal2.main_loop`.

[derived: T15's screen function signatures and return conventions;
A-WATCH-1 — result is T14's stand-in; GA-4 — keys flow through the driver.]
[designed: the screen ordering, the shared-state contract, and the
next-fixture placeholder text.]
"""
import unittest
from unittest.mock import MagicMock, patch, call

from goal2 import loop as goal2_loop
from goal2.data.goaldat import GoalDat
from goal2.game.state import GameState
from goal2.main_loop import run_main_loop
from goal2.game.state import to_savestate
from goal2.ui.input import Key

# [designed: _PLACEHOLDER_BYTES is a non-empty bytes string that the
# patched to_savestate replaces with b"saved"; run_result receives the
# mocked-saved bytes (not _PLACEHOLDER_BYTES), proving the wire-up.]
_PLACEHOLDER_BYTES = b"<placeholder>"


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
    """Done-when 2, 3, 4: call order and shared state through preview."""

    def test_country_select_called_first_with_state(self):
        """Done-when 2: run_country_select is called first and receives state."""
        gd = _make_goaldat()
        state = _make_state()

        with patch("goal2.main_loop.run_country_select") as mock_cs, \
             patch("goal2.main_loop.run_squad_select") as mock_sq, \
             patch("goal2.main_loop.run_tactics_select") as mock_tac, \
             patch("goal2.main_loop.run_result") as mock_res:

            mock_cs.return_value = None  # Esc immediately

            run_main_loop(gd, state, _PLACEHOLDER_BYTES, keys=_keys(Key.ESC))

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
            run_main_loop(gd, state, _PLACEHOLDER_BYTES, keys=_keys(*([Key.DOWN] * 6), Key.ENTER))

            self.assertEqual(state.managed_country, 7)

    def test_screens_called_in_order_with_same_state(self):
        """Done-when 4: selection, preview and result share state in order."""
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

        def spy_preview(*args, **kwargs):
            call_order.append("preview")
            tracker["preview_state"] = kwargs.get("state")
            return True

        def spy_re(*args, **kwargs):
            call_order.append("result")
            tracker["re_state"] = kwargs.get("state")
            tracker["full_match"] = kwargs.get("full_match")
            tracker["re_arg"] = args[0] if args else None
            return True
        # [designed: re_arg captures the first positional arg — the savestate bytes
        # (saved) — so the assertion below proves run_result received the saved
        # bytes, not the original bytes passed into run_main_loop.]
        # NOTE: mutate main_loop.py to pass original_savestate_bytes to
        # run_result instead of saved; this assertion fails, and so does the
        # corresponding order/state test below.

        with patch("goal2.main_loop.run_country_select", spy_cs), \
             patch("goal2.main_loop.run_squad_select", spy_sq), \
             patch("goal2.main_loop.run_tactics_select", spy_ta), \
             patch("goal2.main_loop.run_match_preview", spy_preview), \
             patch("goal2.main_loop.run_result", spy_re), \
             patch("goal2.main_loop.to_savestate", return_value=b"saved") as mock_save:

            run_main_loop(gd, state, _PLACEHOLDER_BYTES, keys=_keys(Key.ENTER))

        self.assertEqual(call_order, ["country_select", "squad_select", "tactics_select", "preview", "result"])
        # [derived: T17 — to_savestate's contract is (state, original=bytes);
        # the assertion below proves run_main_loop calls it with the in-memory
        # state and the original savestate bytes.]
        mock_save.assert_called_once_with(state, original=_PLACEHOLDER_BYTES)
        # All four calls received the same state object
        self.assertIs(tracker["cs_state"], state)
        self.assertIs(tracker["sq_state"], state)
        self.assertIs(tracker["ta_state"], state)
        self.assertIs(tracker["preview_state"], state)
        self.assertIs(tracker["re_state"], state)
        # NOTE: run_result received the SAVED bytes (b"saved"), not the originals
        self.assertEqual(tracker["re_arg"], b"saved")
        self.assertTrue(tracker["full_match"])


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

            rc = run_main_loop(gd, state, _PLACEHOLDER_BYTES, keys=_keys(Key.ESC))

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

            rc = run_main_loop(gd, state, _PLACEHOLDER_BYTES,
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

            rc = run_main_loop(gd, state, _PLACEHOLDER_BYTES,
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
             patch("goal2.main_loop.run_match_preview", return_value=True), \
             patch("goal2.main_loop.run_result") as mock_res, \
             patch("goal2.main_loop.to_savestate", return_value=b"saved") as mock_save:

            mock_cs.return_value = 7
            mock_sq.return_value = True
            mock_tac.return_value = True
            mock_res.return_value = False  # Esc

            rc = run_main_loop(gd, state, _PLACEHOLDER_BYTES,
                               keys=_keys(Key.ENTER, Key.ENTER, Key.ENTER, Key.ESC))

        self.assertEqual(rc, 0)
        mock_save.assert_called_once()


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
             patch("goal2.main_loop.run_match_preview", return_value=True), \
             patch("goal2.main_loop.run_result") as mock_res, \
             patch("goal2.main_loop.to_savestate", return_value=b"saved") as mock_save:

            mock_cs.return_value = 7
            mock_sq.return_value = True
            mock_tac.return_value = True
            mock_res.return_value = True

            rc, output = self._capture_stdout(
                run_main_loop, gd, state, _PLACEHOLDER_BYTES,
                keys=_keys(Key.ENTER, Key.ENTER, Key.ENTER, Key.ENTER))

        self.assertEqual(rc, 0)
        self.assertIn("7", output)
        self.assertIn("Next fixture", output)
        mock_save.assert_called_once_with(state, original=_PLACEHOLDER_BYTES)

    def test_placeholder_missing_fails(self):
        """Deleting the placeholder line makes stdout empty and this test fails."""
        gd = _make_goaldat()
        state = _make_state()
        state.managed_country = 42

        with patch("goal2.main_loop.run_country_select") as mock_cs, \
             patch("goal2.main_loop.run_squad_select") as mock_sq, \
             patch("goal2.main_loop.run_tactics_select") as mock_tac, \
             patch("goal2.main_loop.run_match_preview", return_value=True), \
             patch("goal2.main_loop.run_result") as mock_res, \
             patch("goal2.main_loop.to_savestate", return_value=b"saved") as mock_save:

            mock_cs.return_value = 42
            mock_sq.return_value = True
            mock_tac.return_value = True
            mock_res.return_value = True

            rc, output = self._capture_stdout(
                run_main_loop, gd, state, _PLACEHOLDER_BYTES,
                keys=_keys(Key.ENTER, Key.ENTER, Key.ENTER, Key.ENTER))

        self.assertEqual(rc, 0)
        self.assertIn("42", output)
        mock_save.assert_called_once_with(state, original=_PLACEHOLDER_BYTES)


class TestEndToEnd(unittest.TestCase):
    """Done-when 8: full end-to-end smoke with empty key sequences."""

    def test_all_screens_called_with_empty_keys_sequence(self):
        """Done-when 8: every screen is called when all return Enter (True)."""
        gd = _make_goaldat()
        state = _make_state()

        with patch("goal2.main_loop.run_country_select") as mock_cs, \
             patch("goal2.main_loop.run_squad_select") as mock_sq, \
             patch("goal2.main_loop.run_tactics_select") as mock_tac, \
             patch("goal2.main_loop.run_match_preview", return_value=True), \
             patch("goal2.main_loop.run_result") as mock_res, \
             patch("goal2.main_loop.to_savestate", return_value=b"saved") as mock_save:

            # Empty keys: each screen's key_iter hits StopIteration and breaks,
            # acting as if Enter was pressed on every screen.
            mock_cs.return_value = 7
            mock_sq.return_value = True
            mock_tac.return_value = True
            mock_res.return_value = True

            rc = run_main_loop(gd, state, _PLACEHOLDER_BYTES, keys=iter([]))

        self.assertEqual(rc, 0)
        mock_cs.assert_called_once()
        mock_sq.assert_called_once()
        mock_tac.assert_called_once()
        mock_res.assert_called_once()
        mock_save.assert_called_once_with(state, original=_PLACEHOLDER_BYTES)


class TestLoopCLI(unittest.TestCase):
    """Regression: `python -m goal2.loop` calls main() with argv=None; the
    handler must not raise TypeError on `len(None)` (Luna R1, 2026-10-13)."""

    def test_main_with_none_argv_does_not_raise_typeerror(self):
        """loop.main(None) must handle the missing argv without TypeError.

        With the regression present (no `if argv is None: argv = sys.argv`
        guard), the call raises `TypeError: object of type 'NoneType' has no
        len()`. With the fix, argv falls back to sys.argv and the function
        proceeds (returning 2 when sys.argv has no script-relative arguments,
        or running the loop when it does).
        """
        try:
            goal2_loop.main(None)
        except TypeError as exc:
            self.fail(
                f"loop.main(None) raised TypeError ({exc}); the "
                f"`if argv is None: argv = sys.argv` guard is missing"
            )


if __name__ == "__main__":
    unittest.main()


class TestKeysAreConsumedSequentially(unittest.TestCase):
    """Regression: keys must be consumed sequentially across screens.

    Each screen does `iter(keys)` internally, so passing a list `keys`
    would replay it from the start for every screen. The fix wraps
    `keys` once at the top of run_main_loop, so every stage including the
    preview shares one iterator. (Luna R2, 2026-10-13; T29)

    Mutation: remove the `keys = iter(keys) if keys is not None else None`
    line in run_main_loop. Each screen receives the raw list; each spy
    drains the full list and the test fails because later stages see the
    same keys again instead of the remaining shared iterator contents.
    """

    def test_keys_consumed_sequentially_across_screens(self):
        """With a shared iterator, screens consume keys in order; each
        subsequent screen sees only what is left after the previous one."""
        keys_seen = {}

        def make_spy(name):
            def spy(goaldat, keys, *, state=None, full_match=False):
                keys_seen[name] = list(keys) if keys is not None else []
                if name == "re":
                    self.assertTrue(full_match)
                return 7 if name == "cs" else True
            return spy

        def preview_spy(goaldat, savestate, keys, *, state):
            keys_seen["preview"] = list(keys) if keys is not None else []
            return True

        with patch("goal2.main_loop.run_country_select", make_spy("cs")), \
             patch("goal2.main_loop.run_squad_select", make_spy("sq")), \
             patch("goal2.main_loop.run_tactics_select", make_spy("ta")), \
             patch("goal2.main_loop.run_match_preview", preview_spy), \
             patch("goal2.main_loop.run_result", make_spy("re")), \
             patch("goal2.main_loop.to_savestate", return_value=b"saved") as mock_save:

            gd = _make_goaldat()
            state = _make_state()
            # A list (not yet an iterator): without the fix, each screen
            # would replay the full list. With the fix, the wrapper turns
            # this into an iterator that cs drains; sq/ta/re see [].
            scripted = [Key.ENTER, Key.ENTER, Key.ENTER, Key.ENTER]
            run_main_loop(gd, state, _PLACEHOLDER_BYTES, keys=scripted)

        # cs drains the iterator completely (saw all 4)
        self.assertEqual(len(keys_seen["cs"]), 4)
        # subsequent screens see no keys (the iterator is exhausted)
        self.assertEqual(keys_seen["sq"], [])
        self.assertEqual(keys_seen["ta"], [])
        self.assertEqual(keys_seen["preview"], [])
        self.assertEqual(keys_seen["re"], [])
        mock_save.assert_called_once_with(state, original=_PLACEHOLDER_BYTES)
