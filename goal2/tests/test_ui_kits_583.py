"""[#583] The kits the new window draws are the original's: 0791:1073 over the game's own colour bytes.

The claim it protects: no side has a colour of its own for being at home; each wears its country's kit as the
original computes it, and the capture that misled T166 comes out as the original drew it.
"""
import unittest
from pathlib import Path

from goal2.tests import requires
from goal2.ui import kits

ROOT = Path(__file__).resolve().parents[2]


class Rule(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        requires.require(files=("GOAL.DAT", "e010-r0008-halftime.sav"))
        from goal2.data.goaldat import load
        from goal2.engine.original_match.image import Image
        cls.image = Image.from_savestate((ROOT / ".cache/e010-r0008-halftime.sav").read_bytes())
        names = load((ROOT / ".cache/GOAL.DAT").read_bytes()).country_names
        cls.country = {name: names.index(name) for name in ("Italy", "Holland", "Norway", "Germany")}

    def kits(self, a, b, special=0):
        def read(off):
            return special if off == kits.SPECIAL else self.image.rd(off, 1)
        return kits.compute(read, self.country[a], self.country[b])

    def test_the_capture_norway_at_home_to_holland(self):
        """[confirmed: t156-045-kick-off.png] Both first colours are light red: Holland (team 0) plays in white,
        Norway in light red; Norway's keeper yellow, Holland's blue."""
        got = self.kits("Holland", "Norway")
        self.assertEqual(got.shirt, (15, 12))
        self.assertEqual(got.keeper, (9, 14))
        self.assertEqual((got.name(0), got.name(1)), ("WHITE", "LIGHT RED"))

    def test_italy_is_blue_at_home_and_away(self):
        self.assertEqual(self.kits("Holland", "Italy").name(1), "LIGHT BLUE")
        self.assertEqual(self.kits("Italy", "Germany").name(0), "LIGHT BLUE")

    def test_a_keeper_colour_equal_to_the_other_shirt_takes_the_second_byte(self):
        """0791:10F7 and 1111: Holland's keeper (9) equals Italy's shirt, so it takes Holland's second byte (15);
        Italy's keeper (12) equals Holland's shirt, so it takes Italy's second byte (14)."""
        got = self.kits("Holland", "Italy")
        self.assertEqual(got.shirt, (12, 9))
        self.assertEqual(got.keeper, (15, 14))

    def test_the_special_mode_is_fixed(self):
        """0791:1076: with DS:A964 set, 4 and 1, keepers 0xC and 9."""
        got = self.kits("Holland", "Norway", special=1)
        self.assertEqual((got.shirt, got.keeper), ((4, 1), (0xC, 9)))


if __name__ == "__main__":
    unittest.main()
