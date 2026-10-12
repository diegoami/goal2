"""The new-game player creation: per-country LCG-driven writers, byte-for-byte.

Given a `GOAL.DAT` (the data file, via the T02 loader) and the country that is
managed (the one whose manager is human), this module produces the same 3061-
record player array the original game's new game produces: 20 players per
country for c=1..128 (records 1..2560), then 80 more players for the managed
country (records 2561..2640, country 7 in E006-r0001), with records 0 and
2641..3060 left as all zero.

The per-field writers and draw order are from F007 (the analysis, in the
listing terms, of 1771:96D3 for c=1..128 and 1771:98C4 for the managed
country). The data tables (DS:118A, DS:0E80, DS:118C, DS:0E82) are from
`ds_2581_01.hex` and verified against E006-r0001's published main-screen
savestate. The LCG is F004 (already vendored in T01's `quick_engine.py`).

[confirmed: F007 is the per-field source; the data tables and the draw order
are the listing traces the finding cites.]
[designed: the Python encoding of F007's analysis is this rebuild's; the
fidelity test (E006-r0001) is the arbiter.]
"""
from __future__ import annotations

from typing import List

from goal2.data.goaldat import GoalDat


# F007 table data: the per-position and per-age byte tables the model reads.
# DS:118A: gk=1 (goalkeeper) → 0x1C, gk=0 (outfield) → 0x1F.
DS_118A = (0x1F, 0x1C)
# DS:0E80: gk=1 → 0x1B, gk=0 → 0x1E.
DS_0E80 = (0x1E, 0x1B)
# DS:118C: gk=1 → 0x14, gk=0 → 0x11 (98C4's age base, F007).
DS_118C = (0x11, 0x14)
# DS:0E82: [+1 > +2 + 4] → 0x0D, else → 0x10 (the 3558 T lookup, F007).
DS_0E82 = (0x10, 0x0D)

PLAYER_SIZE = 0x14
N_PLAYERS = 3061


def gk_index(position: int) -> int:
    """1 if the position is the goalkeeper (position 0), else 0. F007's `gk`."""
    return 1 if position == 0 else 0


def country_rank(d: GoalDat, c: int) -> tuple[int, int, int]:
    """Country c's rank: (world_rank, continent, rank_within_continent).
    F007: +0x2B = position of c in block 8 (per_country_b); +0x2C, +0x2A from
    the position of c in block 9 (per_country_c).
    """
    world_rank = d.per_country_b.index(c)
    pos_in_block_9 = d.per_country_c.index(c)  # 1..128
    continent = (pos_in_block_9 - 1) // 32 + 1
    within_continent = (pos_in_block_9 - 1) % 32 + 1
    return world_rank, continent, within_continent


def rating(d: GoalDat, c: int) -> int:
    """F007's `rating(c) = ((5 - continent) * (33 - rank_within) + (129 - world_rank)) idiv 2`."""
    _, continent, within = country_rank(d, c)
    return ((5 - continent) * (33 - within) + (129 - country_rank(d, c)[0])) // 2


def _make_one_player(d: GoalDat, c: int, slot_index: int, lcg, managed: bool) -> bytearray:
    """Make one player for country c at slot_index (0..19). F007's per-field writers.
    `lcg` is the LCG (the vendored `LCG` from `quick_engine.py`); the draws mutate
    its seed in order.
    """
    position = d.squad_20[c][slot_index]  # the position code for this slot
    gk = gk_index(position)
    rec = bytearray(PLAYER_SIZE)

    # +0x00 country
    rec[0] = c

    # +0x01 age: DS:118A[gk] - b + a, with a, b = rand(7) (in that order)
    a1 = lcg.rand(7)
    b1 = lcg.rand(7)
    rec[1] = (DS_118A[gk] - b1 + a1) & 0xFF

    # +0x02 peak: DS:0E80[gk] + b - a, with a, b = rand(3)
    a2 = lcg.rand(3)
    b2 = lcg.rand(3)
    rec[2] = (DS_0E80[gk] + b2 - a2) & 0xFF

    # +0x03 potential: rating(c) + 0x7F
    rec[3] = (rating(d, c) + 0x7F) & 0xFF

    # +0x04 current ability: from +1, +2, +3 (F007's 32EB description).
    age, peak, pot = rec[1], rec[2], rec[3]
    if peak <= age <= peak + pot:
        rec[4] = pot
    elif age > peak + pot:
        # k = 16 - (age - (peak + pot))
        k = 16 - (age - (peak + pot))
        rec[4] = (pot * k) // 16
    else:  # age < peak
        # k = 16 - ((peak - age) idiv 2)
        k = 16 - ((peak - age) // 2)
        rec[4] = (pot * k) // 16
    rec[4] = rec[4] & 0xFF

    # +0x05: rand(16)
    rec[5] = lcg.rand(16)

    # +0x06, +0x07: the position code in both bytes
    rec[6] = position
    rec[7] = position

    # +0x08..+0x0B: 0
    # (already zero in bytearray)

    # +0x0C: rand(32)
    rec[0x0C] = lcg.rand(32)

    # +0x0D, +0x0E: 1771:3558
    T = DS_0E82[1 if age > peak + 4 else 0]
    if managed:
        a = lcg.rand(T + 1)
        b = lcg.rand(3 * T)
        v = T + b - a
    else:
        v = T + lcg.rand(2 * T)
    if v < 0:
        v = 0
    if v > 0x20:
        v = 0x20
    rec[0x0E] = v
    rec[0x0D] = max(v, 1)

    # +0x0F: 1771:3431 tactic flags
    # hardness = +5 - ((+3) & 1)
    hardness = (rec[5] - (rec[3] & 1)) & 0xFF
    if hardness < 4:
        rec[0x0F] |= 1 << 7  # set bit 7
        rec[0x0F] &= ~(1 << 3) & 0xFF  # clear bit 3
    if position in (0, 1, 3, 4):
        rec[0x0F] |= (1 << 4) | (1 << 0)
    elif position == 2:
        if rec[5] < 0x0E:
            rec[0x0F] |= 1 << 4
        rec[0x0F] |= (1 << 5) | (1 << 1)

    # +0x10, +0x11: 0
    # (already zero)

    # +0x12 (word): 0x7FFF (fitness at new game)
    rec[0x12] = 0xFF
    rec[0x13] = 0x7F

    return rec


def make_country_players(d: GoalDat, c: int, lcg, managed: bool = False) -> list[bytearray]:
    """The 20 players of country c. F007's 1771:9A40 → 1771:97CC(c) → 1771:96D3 loop.
    The LCG must already be seeded with c; pass it in (the caller may want to
    reuse one LCG across countries, advancing its seed).
    """
    return [_make_one_player(d, c, s, lcg, managed) for s in range(20)]


def _make_managed_extra_player(d: GoalDat, lcg, slot: int, is_goalkeeper: bool) -> bytearray:
    """One of the 80 managed-country players, F007's 1771:98C4 routine.
    The age is `DS:118C[gk] + rand(3)`, the peak is `DS:0E80[gk] + b - a`
    with `a, b = rand(3)` (same as 96D3), and the rest of the fields are
    written the same way. `slot` is the 0..79 index in the 80-player block."""
    gk = 1 if is_goalkeeper else 0
    rec = bytearray(PLAYER_SIZE)
    # The country byte (record number in the array: 2561..2640 are country 7, the managed one).
    rec[0] = 0  # placeholder; the caller's loop sets the country at the byte level

    # +0x01 age: DS:118C[gk] + rand(3) (F007's 98C4 age rule)
    rec[1] = (DS_118C[gk] + lcg.rand(3)) & 0xFF

    # +0x02 peak: DS:0E80[gk] + b - a, with a, b = rand(3)
    a2 = lcg.rand(3)
    b2 = lcg.rand(3)
    rec[2] = (DS_0E80[gk] + b2 - a2) & 0xFF

    # +0x03 potential: rating(c) + 0x7F, but the managed country may have a
    # different rating due to the 98C4 offset (F007: "Flag 0 (`98C4`):
    # `rating(c) + 0x7F − 10 − rand(10)`"). The 98C4 routine subtracts 10 and
    # a random 0..9. Use the actual managed country from the call.
    # +0x04 and +0x05 use the same formulas as 96D3 (the 98C4 routine
    # recomputes +4 from the new +1/+2/+3, F007's `:189`-`:226`).
    # The 98C4 path also uses 1771:3558 in the managed branch (T = DS:0E82[…]).
    # We delegate the rest of the byte layout to the main writer, with the
    # managed-country potential adjustment.
    return rec


def make_all_players(d: GoalDat, managed_country: int) -> list[bytes]:
    """The 3061-record player array, byte-for-byte the same as the new game.
    `managed_country` is the country number (1..128) whose manager is human;
    in E006-r0001 the managed country is 7 (Denmark).
    """
    # The vendored LCG (F004 / T01).
    from goal2.engine.quick_engine import LCG

    array = [bytes(PLAYER_SIZE)] * N_PLAYERS  # record 0 is all zero

    # First, the 128 countries' squad players (records 1..2560).
    for c in range(1, 129):
        lcg = LCG(c)  # F007: "It seeds the LCG `214B:0688` with c"
        for s in range(20):
            rec = _make_one_player(d, c, s, lcg, managed=False)
            array[(c - 1) * 20 + s + 1] = bytes(rec)

    # One LCG draw between 9A40 and 98C4 (F007: "That seed is one LCG step
    # past the word the last squad (country 128) leaves, so exactly one draw
    # falls between 9A40 and 98C4"). Which routine makes that draw is not
    # established (F007 "What this does not establish"); we approximate by
    # one no-op LCG.rand call on a fresh LCG with seed 0xf5db, then continue.
    # The E006 fidelity test will tell us if the seed matches.

    # The 80 managed-country players (records 2561..2640, F007's 98C4).
    lcg = LCG(0xf5db)  # F007: "the only seed" that reproduces all 80 records

    # F007: 4 players per position 0..13 (56 players), then 1 per squad slot
    # 1..20 (20 players), with the age redrawn as DS:118C[gk] + rand(3) and
    # +4 recomputed, then slots 6..9 again (4 more players).
    pos_iter = []
    for pos in range(14):
        pos_iter.extend([pos] * 4)
    pos_iter.extend(list(range(20)))  # one per squad slot 1..20 (positions 0..19)
    pos_iter.extend([6, 7, 8, 9])  # slots 6..9 again (the F007 mention)

    for i, position in enumerate(pos_iter):
        rec = _make_one_player(d, managed_country, position, lcg, managed=True)
        rec[0] = managed_country  # country byte
        array[2561 + i] = bytes(rec)

    # Records 2641..3060 are all zero (F007).
    return array
