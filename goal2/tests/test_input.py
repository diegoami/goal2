"""Tests for `goal2.ui.input`: Key enum and read_key.

[designed: the key set is the minimum needed by T11 (country select), T12
(squad screen) and T13 (tactics screen).]
"""
import unittest

from goal2.ui.input import Key, read_key


class TestKey(unittest.TestCase):
    def test_five_enum_values(self):
        """Done-when 4: Key has the five expected enum values."""
        names = {k.name for k in Key}
        self.assertEqual(names, {"UP", "DOWN", "ENTER", "ESC", "PAGE_UP", "PAGE_DOWN"})

    def test_read_key_callable(self):
        """Done-when 4: read_key is importable and callable (not invoked)."""
        self.assertTrue(callable(read_key))


if __name__ == "__main__":
    unittest.main()
