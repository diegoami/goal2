"""#552: the mark line's protected-zone flag is element 7 of +0x10 (0x40), not 0x80 (suspended).
[confirmed: goal2-archaeology F027 line 28 (element 7 is the player screen's own flag, element 8 is suspended);
docs/engine-study/tactics.md line 43 (status element 7 is protection 0x40)]"""
import unittest

from goal2.game.player_card import readiness, tactics


class Memory:
    """Stand-in for the card's word tables: every Pascal string reads as its address."""
    def pascal(self, address, length):
        return f'@{address:04X}'


def record(status):
    r = bytearray(20)
    r[6] = 2          # a defender: the mark line is shown from role 2 up
    r[0x0E] = 1       # fit
    r[0x10] = status
    return bytes(r)


class ProtectFlag(unittest.TestCase):
    def test_protection_is_0x40(self):
        _, mark = tactics(Memory(), record(0x40), 0)
        self.assertEqual(mark, 'Protect zone P')

    def test_a_suspended_player_is_not_shown_protecting(self):
        r = record(0x80)
        _, mark = tactics(Memory(), r, 0)
        self.assertNotEqual(mark, 'Protect zone P')
        self.assertEqual(readiness(r), 'suspended')


if __name__ == '__main__':
    unittest.main()
