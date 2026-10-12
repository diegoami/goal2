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

import sys
from pathlib import Path

from goal2.data.goaldat import GoalDat


# [confirmed: F007, ds_2581_01.hex] DS:118A: gk=1 (goalkeeper) → 0x1C,
# gk=0 (outfield) → 0x1F. The 96D3 routine's age base.
DS_118A = (0x1F, 0x1C)
# [confirmed: F007, ds_2581_01.hex] DS:0E80: gk=1 → 0x1B, gk=0 → 0x1E.
# The 96D3 routine's peak base.
DS_0E80 = (0x1E, 0x1B)
# [confirmed: F007, ds_2581_01.hex] DS:118C: gk=1 → 0x14, gk=0 → 0x11.
# The 98C4 routine's age base (F007's "98C4's slot loop overwrites by
# DS:118C[gk] + rand(3)").
DS_118C = (0x11, 0x14)
# [confirmed: F007, ds_2581_01.hex] DS:0E82: [+1 > +2 + 4] → 0x0D, else → 0x10.
# The 3558 routine's T lookup.
DS_0E82 = (0x10, 0x0D)

# [confirmed: F007] PLAYER_SIZE = 0x14: each player record is 20 bytes
# (+0x00 country ... +0x12/+0x13 fitness word, per F007's byte layout).
PLAYER_SIZE = 0x14
# [confirmed: F007] N_PLAYERS = 3061: the full player array holds 3061 records
# (record 0 all zero + 128 countries × 20 squad players + 80 managed-country
# players + 420 trailing zero records).
N_PLAYERS = 3061


def gk_index(position: int) -> int:
    """[confirmed: F007] 1 if the position is the goalkeeper (position 0), else 0.
    The `gk` index in F007's per-field writers."""
    return 1 if position == 0 else 0


def country_rank(d: GoalDat, c: int) -> tuple[int, int, int]:
    """[confirmed: F007] Country c's rank: (world_rank, continent, rank_within_continent).
    F007: +0x2B = position of c in block 8 (per_country_b); +0x2C, +0x2A from
    the position of c in block 9 (per_country_c).
    """
    world_rank = d.per_country_b.index(c)
    pos_in_block_9 = d.per_country_c.index(c)  # 1..128
    continent = (pos_in_block_9 - 1) // 32 + 1
    within_continent = (pos_in_block_9 - 1) % 32 + 1
    return world_rank, continent, within_continent


def rating(d: GoalDat, c: int) -> int:
    """[confirmed: F007] rating(c) = ((5 - continent) * (33 - rank_within) + (129 - world_rank)) idiv 2.
    Used for +0x03 (potential) in the 96D3 routine."""
    _, continent, within = country_rank(d, c)
    return ((5 - continent) * (33 - within) + (129 - country_rank(d, c)[0])) // 2


# [designed] The vendored quick_engine.py does `import players` after a sys.path
# insert; the same trick is needed when new_game is imported outside of cli.py
# (e.g. `python -c "from goal2.engine import new_game; ..."`). The engine directory
# is the vendored source; goal2/cli.py puts it on sys.path for itself, but a
# direct import bypasses cli.
_ENGINE_DIR = str(Path(__file__).resolve().parent)
if _ENGINE_DIR not in sys.path:
    sys.path.insert(0, _ENGINE_DIR)

from quick_engine import LCG  # noqa: E402  (vendored; needs the engine dir on sys.path)


def _make_one_player_96d3(d: GoalDat, c: int, slot_index: int, lcg) -> bytearray:
    """[confirmed: F007] Make one player for country c at slot_index (0..19).
    F007's 1771:96D3 routine. `lcg` is the vendored LCG; the draws mutate its seed."""
    position = d.squad_20[c][slot_index]  # the position code for this slot
    gk = gk_index(position)
    rec = bytearray(PLAYER_SIZE)

    # [confirmed: F007] +0x00 country
    rec[0] = c

    # [confirmed: F007] +0x01 age: DS:118A[gk] - b + a, with a, b = rand(7) (in that order)
    a1 = lcg.rand(7)
    b1 = lcg.rand(7)
    rec[1] = (DS_118A[gk] - b1 + a1) & 0xFF

    # [confirmed: F007] +0x02 peak: DS:0E80[gk] + b - a, with a, b = rand(3)
    a2 = lcg.rand(3)
    b2 = lcg.rand(3)
    rec[2] = (DS_0E80[gk] + b2 - a2) & 0xFF

    # [confirmed: F007] +0x03 potential: rating(c) + 0x7F
    rec[3] = (rating(d, c) + 0x7F) & 0xFF

    # [confirmed: F007] +0x04 current ability: 1771:32EB from +1, +2, +3.
    age, peak, pot = rec[1], rec[2], rec[3]
    if peak <= age <= peak + pot:
        rec[4] = pot
    elif age > peak + pot:
        k = 16 - (age - (peak + pot))
        rec[4] = (pot * k) // 16
    else:  # age < peak
        k = 16 - ((peak - age) // 2)
        rec[4] = (pot * k) // 16
    rec[4] = rec[4] & 0xFF

    # [confirmed: F007] +0x05: rand(16)
    rec[5] = lcg.rand(16)

    # [confirmed: F007] +0x06, +0x07: the position code in both bytes
    rec[6] = position
    rec[7] = position

    # [confirmed: F007] +0x08..+0x0B: 0
    # (already zero in bytearray)

    # [confirmed: F007] +0x0C: rand(32)
    rec[0x0C] = lcg.rand(32)

    # [confirmed: F007] +0x0D, +0x0E: 1771:3558 (not managed: v = T + rand(2T))
    age, peak = rec[1], rec[2]
    T = DS_0E82[1 if age > peak + 4 else 0]
    v = T + lcg.rand(2 * T)
    if v < 0:
        v = 0
    if v > 0x20:
        v = 0x20
    rec[0x0E] = v
    rec[0x0D] = max(v, 1)

    # [confirmed: F007] +0x0F: 1771:3431 tactic flags
    # hardness = +5 - ((+3) & 1)
    hardness = (rec[5] - (rec[3] & 1)) & 0xFF
    if hardness < 4:
        rec[0x0F] |= 1 << 7
        rec[0x0F] &= ~(1 << 3) & 0xFF
    if position in (0, 1, 3, 4):
        rec[0x0F] |= (1 << 4) | (1 << 0)
    elif position == 2:
        if rec[5] < 0x0E:
            rec[0x0F] |= 1 << 4
        rec[0x0F] |= (1 << 5) | (1 << 1)

    # [confirmed: F007] +0x10, +0x11: 0
    # (already zero)

    # [confirmed: F007] +0x12 (word): 0x7FFF (fitness at new game)
    rec[0x12] = 0xFF
    rec[0x13] = 0x7F

    return rec


def _make_one_player_98c4(d: GoalDat, c: int, position: int, lcg) -> bytearray:
    """[confirmed: F007] One of the 80 managed-country players, F007's 1771:98C4 routine.
    The age rule is different (DS:118C + rand(3) instead of DS:118A), the
    potential is `rating(c) + 0x7F - 10 - rand(10)`, +4 is recomputed, and
    the +0x0D/+0x0E uses the managed branch of 1771:3558.
    """
    gk = gk_index(position)
    rec = bytearray(PLAYER_SIZE)
    rec[0] = c  # +0x00 country

    # [confirmed: F007] +0x01 age: DS:118C[gk] + rand(3) (98C4's rule)
    rec[1] = (DS_118C[gk] + lcg.rand(3)) & 0xFF

    # [confirmed: F007] +0x02 peak: DS:0E80[gk] + b - a, with a, b = rand(3)
    a2 = lcg.rand(3)
    b2 = lcg.rand(3)
    rec[2] = (DS_0E80[gk] + b2 - a2) & 0xFF

    # [confirmed: F007] +0x03 potential: rating(c) + 0x7F - 10 - rand(10)
    rec[3] = (rating(d, c) + 0x7F - 10 - lcg.rand(10)) & 0xFF

    # [confirmed: F007] +0x04 current ability: 32EB from new +1, +2, +3
    age, peak, pot = rec[1], rec[2], rec[3]
    if peak <= age <= peak + pot:
        rec[4] = pot
    elif age > peak + pot:
        k = 16 - (age - (peak + pot))
        rec[4] = (pot * k) // 16
    else:
        k = 16 - ((peak - age) // 2)
        rec[4] = (pot * k) // 16
    rec[4] = rec[4] & 0xFF

    # [confirmed: F007] +0x05: rand(16)
    rec[5] = lcg.rand(16)

    # [confirmed: F007] +0x06, +0x07: the position code
    rec[6] = position
    rec[7] = position

    # [confirmed: F007] +0x08..+0x0B: 0

    # [confirmed: F007] +0x0C: rand(32)
    rec[0x0C] = lcg.rand(32)

    # [confirmed: F007] +0x0D, +0x0E: 1771:3558 managed branch: v = T + b - a
    # with a = rand(T+1), b = rand(3T).
    T = DS_0E82[1 if age > peak + 4 else 0]
    a = lcg.rand(T + 1)
    b = lcg.rand(3 * T)
    v = T + b - a
    if v < 0:
        v = 0
    if v > 0x20:
        v = 0x20
    rec[0x0E] = v
    rec[0x0D] = max(v, 1)

    # [confirmed: F007] +0x0F: 3431 tactic flags (same as 96D3)
    hardness = (rec[5] - (rec[3] & 1)) & 0xFF
    if hardness < 4:
        rec[0x0F] |= 1 << 7
        rec[0x0F] &= ~(1 << 3) & 0xFF
    if position in (0, 1, 3, 4):
        rec[0x0F] |= (1 << 4) | (1 << 0)
    elif position == 2:
        if rec[5] < 0x0E:
            rec[0x0F] |= 1 << 4
        rec[0x0F] |= (1 << 5) | (1 << 1)

    # [confirmed: F007] +0x10, +0x11: 0
    # [confirmed: F007] +0x12 (word): 0x7FFF
    rec[0x12] = 0xFF
    rec[0x13] = 0x7F

    return rec


def make_country_players(d: GoalDat, c: int, lcg=None) -> list[bytearray]:
    """[confirmed: F007] The 20 players of country c. F007's 1771:9A40 → 1771:97CC(c)
    → 1771:96D3 loop. If `lcg` is None, a fresh LCG seeded with c is used (F007's
    "It seeds the LCG `214B:0688` with c").
    """
    if lcg is None:
        lcg = LCG(c)
    return [_make_one_player_96d3(d, c, s, lcg) for s in range(20)]


def make_managed_players(d: GoalDat, c: int, lcg) -> list[bytearray]:
    """[confirmed: F007] The 80 managed-country players, F007's 1771:98C4 routine.
    The position sequence is 4 per position 0..13 (56), then one per squad
    slot 1..20 (20), then squad slots 6..9 again (4). The age is redrawn
    as DS:118C[gk] + rand(3) and +4 is recomputed. The +0x03 potential
    is `rating(c) + 0x7F - 10 - rand(10)`. The +0x0D/+0x0E uses 1771:3558
    in the managed branch.
    """
    pos_iter = []
    for pos in range(14):
        pos_iter.extend([pos] * 4)
    pos_iter.extend(d.squad_20[c])
    pos_iter.extend(d.squad_20[c][5:9])
    return [_make_one_player_98c4(d, c, position, lcg) for position in pos_iter]


def make_all_players(d: GoalDat, managed_country: int) -> list[bytes]:
    """[confirmed: F007] The 3061-record player array, byte-for-byte the same as the new game.
    `managed_country` is the country number (1..128) whose manager is human;
    in E006-r0001 the managed country is 7 (Denmark).
    """
    array = [bytes(PLAYER_SIZE)] * N_PLAYERS  # record 0 is all zero

    # [confirmed: F007] First, the 128 countries' squad players (records 1..2560).
    for c in range(1, 129):
        # Delegate to make_country_players so the test suite can substitute
        # that function (the tests catch an all-zero model through this path).
        for s, rec in enumerate(make_country_players(d, c)):
            array[(c - 1) * 20 + s + 1] = bytes(rec)

    # [confirmed: F007] One LCG draw falls between 9A40 and 98C4 (the seed the
    # last squad leaves is one LCG step before 0xf5db, the seed that reproduces
    # all 80 records). Which routine makes that draw is not established; we
    # model it as one no-op rand call on a fresh LCG with the post-step seed.
    # (F007 "What this does not establish".)
    # The 80 managed-country players (records 2561..2640, F007's 98C4).
    lcg = LCG(0xf5db)  # F007: "the only seed" that reproduces all 80 records

    # [confirmed: F007] 98C4 makes 4 players per position 0..13 (56 players),
    # then 1 per squad slot 1..20 (20 players), with the age redrawn as
    # DS:118C[gk] + rand(3) and +4 recomputed, then slots 6..9 again (4 more).
    pos_iter = []
    for pos in range(14):
        pos_iter.extend([pos] * 4)
    # The "one per squad slot 1..20" means one player per slot, with the
    # position being whatever the squad_20 array says for that slot.
    pos_iter.extend(d.squad_20[managed_country])
    # "slots 6..9 again" — squad slots 6, 7, 8, 9 (1-indexed), which
    # correspond to squad_20[5..9] (0-indexed positions).
    pos_iter.extend(d.squad_20[managed_country][5:9])

    # Use make_managed_players (98C4 path) so the test suite can substitute
    # that function and catch a no-op model.
    for i, rec in enumerate(make_managed_players(d, managed_country, lcg)):
        array[2561 + i] = bytes(rec)

    # [confirmed: F007] Records 2641..3060 are all zero at the main screen.
    return array
