"""[fix #698] The shared eleven repair from the manager menu; T111's match-menu arm unchanged.

One designed synthesis (as test_driver_swap_screen_order_697 documents): an eleven player's
energy byte +0xE is zeroed in the saved menu state, so the manager menu's card no longer
reads "ready to play" (views.player_card: energy 0 prints the energy word, not 1771:4298).
Every later change is the original's own, through the Driver's keys.
"""
import unittest

from goal2.tests import requires
from goal2.tests.test_core_team_t107 import start, NEEDS

PLAYERS, PLAYER_SIZE = 0xA91B, 0x14       # [confirmed: goal2/core/views.py] the card's own arithmetic


@requires.need(**NEEDS, slow=True)
class ManagerMenuRepair(unittest.TestCase):
    def test_the_first_unfit_eleven_player_is_swapped_by_the_originals_squad_keys(self):
        from goal2.core import Core, views
        from goal2.core.driver import Driver
        from goal2.tests.eleven_repair import repair_eleven
        scratch = start()
        state = scratch.wait.state
        mem = views.Memory(state)
        rows = views.team(state)["squad"]
        cards = {r["player"]: views.player_card(state, r["player"]) for r in rows}
        fit = mem.code_str(0x1771, 0x4298)
        # an eleven player with a fit same-line bench partner, so the policy's choice exists
        off_row = next(r for r in rows if r["eleven"] and any(
            not q["eleven"] and q["line"] == r["line"] and cards[q["player"]]["readiness"] == fit
            for q in rows))
        record = scratch.core.m.far(PLAYERS) + PLAYER_SIZE * off_row["player"] + 0xE
        scratch.core.m.write(record, b"\x00")
        driver = Driver(Core.load(scratch.core.save(), goal_dat=requires.CACHE / "GOAL.DAT"))
        off, on = repair_eleven(driver)
        self.assertEqual(off, off_row["player"])
        eleven = [r["player"] for r in views.team(driver.wait.state)["squad"] if r["eleven"]]
        self.assertNotIn(off, eleven)
        self.assertIn(on, eleven)
        self.assertEqual(driver.wait.kind, "manager-menu")
