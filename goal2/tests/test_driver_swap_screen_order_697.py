"""[fix #697] Driver.swap must check the marked slot against the order the squad screen shows.

The squad screen (SELECT YOUR TEAM) re-sorts the country record on entry, so the slot it
marks a player at is the order it shows then — not the manager menu's snapshot order,
which an injury may have left unsorted (T170e's round-6 menu raised "did not mark player
125: (1, 11)" with the mark being right; the workaround lives in test_season_1992_t170e).

One designed synthesis: the record's squad words are exchanged in the saved menu state
before the tested Core loads it, so the menu snapshot holds an order the screen's entry
sort does not match. Every later change is the original's own, through the Driver's keys.
"""
import unittest

from goal2.tests import requires
from goal2.tests.test_core_team_t107 import start, NEEDS


def unsorted_menu():
    """(Driver, off, on): the E006 manager menu with squad slots 1 and 11 exchanged, so the
    menu's snapshot order differs from the squad screen's entry-sorted order."""
    from goal2.core import views
    scratch = start()
    state = scratch.wait.state
    country = views.team(state)["country"]
    m = scratch.core.m
    record = m.far(0xA917) + 191 * country
    words = [int.from_bytes(m.read(record + 2 * i, 2), "little") for i in range(20)]
    assert all(words[i] for i in (1, 11)), "the template's squad needs players at slots 1 and 11"
    m.write(record + 2 * 1, words[11].to_bytes(2, "little"))
    m.write(record + 2 * 11, words[1].to_bytes(2, "little"))
    from goal2.core import Core
    from goal2.core.driver import Driver
    driver = Driver(Core.load(scratch.core.save(), goal_dat=requires.CACHE / "GOAL.DAT"))
    assert [r["player"] for r in views.team(driver.wait.state)["squad"]][1] == words[11]
    return driver, words[11], words[1]


@requires.need(**NEEDS, slow=True)
class SwapScreenOrder(unittest.TestCase):
    def test_a_swap_succeeds_when_the_menu_order_is_not_the_screens(self):
        driver, off, on = unsorted_menu()                  # off is in the eleven, on is not
        squad = driver.swap(off, on)                       # the screen's own order decides the mark
        eleven, bench = squad[:11], squad[11:]
        self.assertIn(on, eleven)
        self.assertIn(off, bench)
        self.assertEqual(driver.wait.kind, "manager-menu")
