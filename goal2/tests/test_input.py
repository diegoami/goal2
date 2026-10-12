"""Tests for `goal2.ui.input`: Key enum and read_key.

[designed: the key set is the minimum needed by T11 (country select), T12
(squad screen) and T13 (tactics screen).]
"""
import io
import unittest
from unittest.mock import patch

from goal2.ui.input import Key, read_key


class TestKey(unittest.TestCase):
    def test_six_enum_values(self):
        """Done-when 4: Key has the six expected enum values."""
        names = {k.name for k in Key}
        self.assertEqual(names, {"UP", "DOWN", "ENTER", "ESC", "PAGE_UP", "PAGE_DOWN"})

    def test_read_key_callable(self):
        """Done-when 4: read_key is importable and callable (not invoked)."""
        self.assertTrue(callable(read_key))


class TestReadKey(unittest.TestCase):
    """R1 fix tests: read_key must not over-read the next key."""

    def test_arrow_up_then_enter(self):
        """Up sequence \\x1b[A then Enter \\n returns UP then ENTER."""
        fake_stdin = io.BytesIO(b"\x1b[A\n")
        k1 = read_key(fake_stdin)
        k2 = read_key(fake_stdin)
        self.assertEqual(k1, Key.UP)
        self.assertEqual(k2, Key.ENTER)

    def test_page_up(self):
        """PageUp sequence \\x1b[5~ returns PAGE_UP."""
        fake_stdin = io.BytesIO(b"\x1b[5~")
        k = read_key(fake_stdin)
        self.assertEqual(k, Key.PAGE_UP)


if __name__ == "__main__":
    unittest.main()
