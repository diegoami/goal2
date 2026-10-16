"""Tests for goal2.ai.cpu.

[confirmed: F007] Player record: ability byte at +4, position byte at +6.
[confirmed: F010] Country tactics byte at country[+0x2D].
[derived: T15] pick_computer_eleven returns top 11 by ability (ignoring
formation); tie-break by ascending squad index.
[derived: T15] get_computer_tactics returns country_record[0x2D].
"""
import unittest

from goal2.ai.cpu import get_computer_tactics, pick_computer_eleven


# ── Helpers ────────────────────────────────────────────────────────────────────

def _make_records(abilities: list[int]) -> list[bytes]:
    """Build a player-records list where each record's ability byte is abilities[i].

    Record layout (20 bytes per F007): byte[0] = country, byte[1] = age, byte[4] = ability,
    byte[6] = position. We zero-fill the rest.
    """
    records = []
    for a in abilities:
        rec = bytearray(20)
        rec[1] = 40 - (a % 25)
        rec[4] = a & 0xFF
        records.append(bytes(rec))
    return records


# ── pick_computer_eleven ─────────────────────────────────────────────────────

class TestPickComputerEleven(unittest.TestCase):

    def test_top_11_of_20_by_ability(self):
        # DW2: abilities [1, 20, 2, 19, 3, 18, 4, 17, 5, 16, 6, 15, 7, 14,
        #                 8, 13, 9, 12, 10, 11] (squad indices 0-19)
        # Sorted by descending ability, tie-break ascending squad index:
        #   ability 20 @ idx 1
        #   ability 19 @ idx 3
        #   ability 18 @ idx 5
        #   ability 17 @ idx 7
        #   ability 16 @ idx 9
        #   ability 15 @ idx 11
        #   ability 14 @ idx 13
        #   ability 13 @ idx 15
        #   ability 12 @ idx 17
        #   ability 11 @ idx 19
        #   ability 10 @ idx 18  <-- 11th-highest; player 19 (ability 11)
        #                              comes before player 20 (ability 10)
        #                              by squad index
        # Expected (derived from sorting): [1, 3, 5, 7, 9, 11, 13, 15, 17, 19, 18]
        # squad_indices are 1-based player numbers (1..20), so offset by +1 in records.
        # squad_indices = [1..20] maps to record indices 0..19.
        # We use record indices directly here (0-based).
        abilities = [1, 20, 2, 19, 3, 18, 4, 17, 5, 16,
                     6, 15, 7, 14, 8, 13, 9, 12, 10, 11]
        records = _make_records(abilities)
        squad = list(range(20))          # record indices 0..19 (squad members 1..20)

        result = pick_computer_eleven(records, squad)

        # Derive expected from sorting abilities descending, tie-break ascending index.
        # Each ability value appears once; descending order is indices of
        # decreasing ability values.
        indexed = sorted(enumerate(abilities), key=lambda ix: (-ix[1], ix[0]))
        expected = [idx for idx, _ in indexed[:11]]
        self.assertEqual(result, expected)
        # Specifically: [1, 3, 5, 7, 9, 11, 13, 15, 17, 19, 18]
        self.assertEqual(result, [1, 3, 5, 7, 9, 11, 13, 15, 17, 19, 18])

    def test_exactly_11_squad_members(self):
        # DW3: country with exactly 11 squad members — all 11 must be returned.
        # squad = [0..10], abilities = [1, 20, 2, 19, 3, 18, 4, 17, 5, 16, 6]
        # Descending ability: 20(idx1), 19(idx3), 18(idx5), 17(idx7), 16(idx9),
        #                    6(idx10), 5(idx4), 4(idx6), 3(idx2), 2(idx1), 1(idx0)
        # Actually just derive from the data.
        abilities = [1, 20, 2, 19, 3, 18, 4, 17, 5, 16, 6]
        records = _make_records(abilities)
        squad = list(range(11))

        result = pick_computer_eleven(records, squad)

        # Derive expected from sorting.
        indexed = sorted(enumerate(abilities), key=lambda ix: (-ix[1], ix[0]))
        expected = [idx for idx, _ in indexed]
        self.assertEqual(result, expected)
        self.assertEqual(len(result), 11)

    def test_too_few_squad_members_raises(self):
        records = _make_records([1] * 10)
        with self.assertRaises(ValueError) as ctx:
            pick_computer_eleven(records, list(range(10)))
        self.assertIn("at least 11", str(ctx.exception))

    def test_tie_break_prefers_earlier_squad_index(self):
        # All 11 squad members have the same ability, given in reversed squad order.
        # Without a tie-break (stable sort on ability only), the reversed order is
        # preserved and the result is [10, 9, ..., 0].  With ascending-index
        # tie-break the result must be [0, 1, ..., 10].
        abilities = [5] * 11
        records = _make_records(abilities)
        squad = list(range(10, -1, -1))     # reversed: [10, 9, ..., 0]
        result = pick_computer_eleven(records, squad)
        self.assertEqual(result, list(range(11)))

    def test_tie_break_with_distinct_pairs(self):
        # Two pairs of equal ability, given in reversed squad order:
        #   ability 7 at reversed indices 5 and 4  -> index 4 wins (lower)
        #   ability 3 at reversed indices 9 and 8  -> index 8 wins (lower)
        # Without tie-break, stable sort preserves reversed input order:
        #   [5, 4, ... 9, 8, ...].  With tie-break: [4, 5, 8, 9, ...].
        # Top 11 by descending ability, tie-break ascending index:
        #   10(idx0), 9(idx1), 8(idx2), 7(idx3), 7(idx4), 6(idx5),
        #   5(idx6), 4(idx7), 3(idx8), 3(idx9), 2(idx10)
        abilities = [10, 9, 8, 7, 7, 6, 5, 4, 3, 3, 2,
                     1, 0, 0, 0, 0, 0, 0, 0, 0]
        records = _make_records(abilities)
        squad = list(range(19, -1, -1))     # reversed: [19, 18, ..., 0]
        result = pick_computer_eleven(records, squad)
        expected = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
        self.assertEqual(result, expected)


# ── get_computer_tactics ─────────────────────────────────────────────────────

class TestGetComputerTactics(unittest.TestCase):

    def test_denmark_tactics_byte(self):
        # DW4: byte at 0x2D is 0x8B (Denmark per F010).
        # Build a 0xBF-byte country record with 0x8B at offset 0x2D.
        record = bytearray(0xBF)
        record[0x2D] = 0x8B
        result = get_computer_tactics(bytes(record))
        self.assertEqual(result, 0x8B)

    def test_various_byte_values(self):
        # DW5: any byte 0..255 is returned unchanged.
        for value in (0x00, 0x01, 0x7F, 0xFF):
            record = bytearray(0xBF)
            record[0x2D] = value
            self.assertEqual(get_computer_tactics(bytes(record)), value)

    def test_empty_record_raises(self):
        # Country record must be at least 0xBF bytes.
        with self.assertRaises(IndexError):
            get_computer_tactics(b"")


if __name__ == "__main__":
    unittest.main()
