#!/usr/bin/env python3
"""A model of GOAL.EXE's quick-result match engine (`0791:D733` and everything it reaches),
seed-exact for the second half of a quick match (T23, Q010; E010).

Given a DOSBox-X savestate of the game taken at the **half-time stall** of a quick result (quick mode
`DS:9A3E` = 1, the first half over, the game waiting for a key in `0791:ED8A` inside `0791:9A32`),
`simulate(state)` replays the second half the way the executable does and returns the final score,
the second half's goal minutes with their scorers, and the two seed words (`DS:7B62`, `DS:8336`)
after the match. Every constant below cites the listing line it comes from
(`static/goal-exe/code/`, addresses SEGMENT:OFFSET; data offsets are DS offsets).

Method: the half-time wait consumes no RNG (E010's notes batch 2, probe e010-probe), so the state at
the stall is the exact input. The model runs one `D733` per game minute for the 46 second-half
minutes (`831F` = 46..91, `831B` = 45..0; `0791:970C` advances the minute after every `D733` because
`D733` zeroes `DS:831D`, seg_0791_16.asm:97D3-9828, :6-91).

What the model does NOT cover, and says so loudly at run time:
- the foul path `0791:D5C1` (reached only when `DS:9A3D` != 0 at the stall): the draws up to the
  `278A` compare are implemented, but the `7EEF` branch beyond it (bookings, and the walk-off
  `7B77`/`7D56` -> `7881` -> `94E8`, which steps the second seed `DS:8336` a number of times the
  listing reading has not pinned down) is refused with `FoulPathNotModelled`. Every E010 run has
  `9A3D` = 0 (a friendly), where `D5C1` is never called (seg_0791_21.asm:DACB-DAD9);
- extra time (`DS:7C36` != 0) and penalties: refused (`ExtraTimeNotModelled`);
- `0791:230C`'s keeper tail after its pitch sort (2541-2570): the sort itself is modelled; the tail
  rewrites one pitch record's display fields, which the engine does not read;
- the watched engine `0791:9564` (out of scope, a later task).

Standard library only."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "driver"))
import players  # noqa: E402  (the driver's reader of the player and country arrays)

PLAYER_SIZE = players.PLAYER_SIZE      # 0x14 bytes per player record ([DS:A91B])
COUNTRY_SIZE = players.COUNTRY_SIZE    # 0xBF bytes per country record ([DS:A917])

# --- RNG: 214B:0688 (seg_214B_01.c:552-562) -----------------------------------------
LCG_MUL, LCG_ADD = 0x7ABD, 0x1B0F      # seed = seed*0x7ABD + 0x1B0F (16-bit)


class LCG:
    """The main stream `DS:7B62` (through the far pointer `DS:A978`, `214B:06B1`)."""

    def __init__(self, seed):
        self.seed = seed & 0xFFFF
        self.draws = 0

    def rand(self, n):
        """`214B:0688(n, ptr)`: step, then ((new_seed * n) >> 16) + 1, n as an unsigned word."""
        self.seed = (self.seed * LCG_MUL + LCG_ADD) & 0xFFFF
        self.draws += 1
        return ((self.seed * (n & 0xFFFF)) >> 16) + 1

    def chance(self, n):
        """`214B:06D0(n)`: rand(n) == 1 (one draw)."""
        return self.rand(n) == 1


def s16(v):
    v &= 0xFFFF
    return v - 0x10000 if v >= 0x8000 else v


def s8(v):
    v &= 0xFF
    return v - 0x100 if v >= 0x80 else v


def idiv(a, b):
    """x86 idiv: truncation toward zero."""
    q = abs(a) // abs(b)
    return -q if (a < 0) != (b < 0) else q


def bit_elem(n, byte):
    """`214B:0C57(n, setbyte)` (seg_214B_02.asm:423-439): element n of a one-byte set = bit n-1."""
    return (byte >> ((n - 1) & 0xFF)) & 1


class QuickEngineError(RuntimeError):
    pass


class FoulPathNotModelled(QuickEngineError):
    """D5C1's 7EEF branch would fire; the walk-off seed steps are not pinned down (see module doc)."""


class ExtraTimeNotModelled(QuickEngineError):
    pass


class QuickMatch:
    """The whole second half, with the game's memory the savestate holds as the only input."""

    # --- tables read from the data segment (dumped from the savestate at __init__) ---
    SCORER_TABLE = 0xA6B     # 31 bytes: dummy base at 0xA6B + the 30 entries 0xA6C..0xA89; the draw
                             # reads the byte at 0xA6B + rand(30) (D973-D984: r in 1..30), so index 30
                             # (byte 0xA89) is legal and the base 0xA6B itself is never selected
    ATTEMPTS = 0xA8A         # [12, 16], indexed by (8319 == 0x0F) (D79D-D7B4)
    MINUTE_RANGE = 0xA8C     # [90, 120], same index (D8D1-D8ED)
    STATS1 = 0xA8E           # [33, 10], element 1 chance (D809-D83A)
    STATS5 = 0xA90           # [60, 30], element 5 chance (D7C0-D7F1); the same bytes read as a
                             # slot map A90[r], r in 2..11 (= 13-r), pick D5C1's side-0 pitch slot
    POS_LINE = 0xD4E         # position -> line (seg_1771_02.asm:0D3D-0D68), 16 bytes
    FORMATION = 0x99A        # per position 8 bytes: count, then +7 roles (aae8: 0x99A + 8*(player+6),
                             #  seg_0791_17.asm:AB03-AB63)
    POS_STRING = 0x8CE       # Pascal string; Pos(position char) is a9b8/aae8's "count"
                             # (seg_0791_17.asm:A9EC-A9F6, 23E4:06E3 = Pos)
    BENCH_VALUE = 0x8D5      # a9b8's value table, 8D5[14*(+6) + (+7)] (seg_0791_17.asm:AA4E-AA68)
    R008 = 0x9B7C            # per-country default tactics byte (BD83, seg_0791_19.asm:BDA6-BDC3)
    MANAGERS_PTR = 0xA91F    # far pointer to the manager table; byte 1 of each 3 (1771:0AA7)
    BEC7_NEWPOS = 0xA28      # BEC7's replacement position (seg_0791_19.asm:BF36-BF56)
    FOOT_TABLE = 0xE60       # 3088: E60[14*E7C[player % 3] + (+7)] (seg_1771_05.asm:30A2-30CD)
    FOOT_INDEX = 0xE7C       # E7C[player % 3] (30B2-30BA)
    F2FAD_A, F2FAD_B = 0xE54, 0xE46  # 2FAD = E54[w % 12] + E46[+7] (seg_1771_04.asm:2FB3-2FF2)

    def __init__(self, state):
        self.state = state
        self.rng = LCG(state.ds_word(0x7B62))          # F004: the main stream
        self.seed2 = state.ds_word(0x8336)              # F004: the second stream (speaker only)
        self.score = list(state.ds_bytes(0x9B3C, 2))    # score bytes, engine teams 0 and 1
        self.teams = [state.ds_word(0x9B34), state.ds_word(0x9B36)]  # D77E-D798 pair 9B34 with side 0
        self.flag80fc = state.ds_bytes(0x80FC, 1)[0]    # D785: the flag of 0BC4's side-1 call
        self.eight31a = state.ds_bytes(0x831A, 1)[0]    # the first half's kick-off side
        self.ninea3d = state.ds_bytes(0x9A3D, 1)[0]     # the foul gate (DACB)
        self.eight319 = state.ds_bytes(0x8319, 1)[0]    # the half length marker (0x2D normal)
        self.sevenc36 = state.ds_bytes(0x7C36, 1)[0]    # extra-time flag (F0F6)
        self.minute_mark = 0x80 if (state.ds_bytes(0x8324, 1)[0] or state.ds_bytes(0x7C39, 1)[0]) else 0
        self.sevenc39 = state.ds_bytes(0x7C39, 1)[0]   # 6443's goal-commentary selector (645D/64BF)
        self.sub_budget = list(state.ds_bytes(0x9B3A, 2))   # DS:066B[9A3D] at A4A1 (5 per team, friendly)
        self.once_8332 = list(state.ds_bytes(0x8332, 2))    # C01A's once flags
        self.once_8334 = list(state.ds_bytes(0x8334, 2))    # C0DF's once flags
        if self.sevenc36:
            raise ExtraTimeNotModelled("DS:7C36 set at half time: extra time is not modelled")
        # --- the mutable game state -------------------------------------------------
        self.countries = {}   # country -> {"squad": [20 words], "tactics": +0x2D byte, "managed": +0x2E}
        self.playerrec = {}   # player word -> mutable bytearray(0x14)
        self.pitch = {}       # pitch slot 1..22 -> {"slot_no": pitch+6 byte, "player": +0xD word}
        for c in self.teams:
            self._country(c)
        for slot in range(1, 23):
            base = 0x80E8 + 0x16 * slot                    # the pitch record (8062: 813B-8148)
            self.pitch[slot] = {"slot_no": state.ds_bytes(base + 6, 1)[0],
                                "player": state.ds_word(base + 0xD)}
            self._player(self.pitch[slot]["player"])
        # the key that leaves the stall sets 830B = 0668[831A == 0] + 10 (9A32; the inverted index
        # against 998C's, seg_0791_16.asm:344-436); keeper slots are 1 and 12 (0791:045D)
        self.eight30b = ((0 if self.eight31a == 0 else 11) + 10) & 0xFF
        # --- tables -------------------------------------------------------------------
        g = self._ds
        self.t_scorer = g(self.SCORER_TABLE, 31)   # 31 bytes: t_scorer[r] = byte at 0xA6B + r, r in 1..30
        self.t_attempts = g(self.ATTEMPTS, 2)
        self.t_minutes = g(self.MINUTE_RANGE, 2)
        self.t_stats1 = g(self.STATS1, 2)
        self.t_stats5 = g(self.STATS5, 2)
        self.t_slotmap = g(0xA90, 12)    # D5C1's slot map: byte at 0xA90 + r (D5D7)
        self.t_posline = g(self.POS_LINE, 16)
        self.t_formation = g(self.FORMATION, 8 * 16)
        self.t_posstring = g(self.POS_STRING, 0x18)
        self.t_benchvalue = g(self.BENCH_VALUE, 0xE0)
        self.t_r008 = g(self.R008, players.N_COUNTRIES)
        self.t_newpos = g(self.BEC7_NEWPOS, 2)
        self.t_foot = g(self.FOOT_TABLE, 0xE0)
        self.t_footix = g(self.FOOT_INDEX, 3)
        self.t_2fad_a = g(self.F2FAD_A, 12)
        self.t_2fad_b = g(self.F2FAD_B, 16)
        self.t_formdelta = g(0x7920, 2)    # 6443's 7cc5 +0xC delta (64CC-64DE: byte [7C39!=0?0:1])
        self.t_fitness = g(0x720, 0x28)    # 1E53's +0x12 delta per ring id (1E9C-1EAB)
        self.t_goal_id = 0x27 if self.sevenc39 else 0x26   # 6443's 2aa3 id (645D-6471)
        self.side_base = g(0x668, 2)          # DS:0668 bytes = [11, 0]: team t plays 0668[t]+1..+11
        mseg, moff = self._far(self.MANAGERS_PTR)
        self.managers = bytearray(state.memory(mseg * 16 + moff, 0x400))   # 0AA7: (+0x2E)*3 + 1
        self.goals = []       # {"team", "minute", "player", "squad_slot", "stored_byte"}

    # --- savestate helpers -----------------------------------------------------------
    def _ds(self, off, n):
        return bytearray(self.state.ds_bytes(off, n))

    def _far(self, off):
        return self.state.ds_word(off + 2), self.state.ds_word(off)

    def _country(self, c):
        if c not in self.countries:
            carr = players.countries(self.state)
            base = COUNTRY_SIZE * c
            self.countries[c] = {
                "squad": players.squad(carr, c)[:],
                "tactics": carr[base + 0x2D],
                "managed": carr[base + 0x2E],
            }
        return self.countries[c]

    def _player(self, w):
        if w not in self.playerrec:
            parr = players.players(self.state)
            self.playerrec[w] = bytearray(parr[PLAYER_SIZE * w:PLAYER_SIZE * w + PLAYER_SIZE])
        return self.playerrec[w]

    def _squad(self, t):
        return self._country(self.teams[t])["squad"]

    def _tactics(self, t):
        return self._country(self.teams[t])["tactics"]

    def _pitch_squad_index(self, slot):
        """2BB1 (seg_0791_05.asm:233-250): the pitch record's own +6 decides: <= 11 -> itself,
        else - 11. Slot numbers 1..11 are team 1's, 12..22 team 0's."""
        n = self.pitch[slot]["slot_no"]
        return n if n <= 11 else n - 11

    # --- the player predicates (1771's segment) --------------------------------------

    def unavailable(self, w):
        """1771:3216 (seg_1771_05.asm:188-238): +0xE < 1 signed, or +0x10 element 8, 6 or 3."""
        p = self._player(w)
        if s8(p[0xE]) < 1:
            return True
        return bool(bit_elem(8, p[0x10]) or bit_elem(6, p[0x10]) or bit_elem(3, p[0x10]))

    def two_footed(self, w):
        """1771:3041 (seg_1771_05.asm:40-84): (+5) + (+2) == 0x1E."""
        p = self._player(w)
        return p[5] + p[2] == 0x1E

    def foot_index(self, w):
        """1771:3088 (seg_1771_05.asm:87-136): E60[14*E7C[w % 3] + (+7)]."""
        p = self._player(w)
        return self.t_foot[14 * self.t_footix[w % 3] + p[7]]

    def wrong_foot(self, w):
        """1771:3179 (seg_1771_05.asm:139-213); the position sets at CS:3139 (88 04) and CS:3159 (10 09),
        read with 23E4:08DF (element e = bit e, byte e>>3)."""
        p = self._player(w)
        pos = p[6]
        foot = self.foot_index(w)
        set_3139 = {3, 7, 10}    # 88 04: byte0 bits 3,7 and byte1 bit 2 (elements 3,7,10)
        set_3159 = {4, 8, 11}    # 10 09: byte0 bit 4 and byte1 bits 8,11 (elements 4,8,11)
        if foot != 0 and not self.two_footed(w) and pos in set_3139:
            return True
        if foot == 0 and pos in set_3159:
            return True
        if pos == 0:
            return p[7] != 0
        return p[7] == 0

    def player_strength(self, w):
        """1771:377E (seg_1771_05.asm:763-824)."""
        if self.unavailable(w):
            return 0
        p = self._player(w)
        v = (p[4] + s8(p[0xE]) - 0x3E) & 0xFFFF
        if s8(p[0xC]) >= 0x20:
            v = (v - idiv(s16(v), 0x10)) & 0xFFFF
        else:
            v = (v + s8(p[0xC])) & 0xFFFF
        if s16(v) < 0:
            v = 0
        elif s16(v) > 0x100:
            v = 0x100
        if self.wrong_foot(w):
            v = idiv(s16(v), 2) & 0xFFFF
        return v

    def hardness(self, w):
        """1771:2FFB (seg_1771_04.asm:1100-1113): (+5) - ((+3) & 1), as an unsigned byte."""
        p = self._player(w)
        return (p[5] - (p[3] & 1)) & 0xFF

    def set_player_tactics(self, w):
        """1771:3431 (seg_1771_05.asm:406-484); the position set at CS:3411 = bytes 1B 00, read
        with 23E4:08DF (element e at bit e of byte e>>3) -> positions {0,1,3,4}."""
        p = self._player(w)
        if self.hardness(w) < 4:                    # cmp al,4; jae skips (unsigned)
            p[0xF] |= 1 << 7                        # 33CD: set element 8 (seg_1771_05.asm:33E7-33F4)
            p[0xF] &= ~(1 << 3) & 0xFF              # 33CD: clear element 4 (33F9-3406)
        pos = p[6]
        if pos in {0, 1, 3, 4}:
            p[0xF] |= 1 << 4                        # element 5
            p[0xF] |= 1 << 0                        # element 1
        elif pos == 2:
            if p[5] < 0xE:                          # jae skips (unsigned)
                p[0xF] |= 1 << 4                    # element 5
            p[0xF] |= 1 << 5                        # element 6
            p[0xF] |= 1 << 1                        # element 2

    def bbff(self, value, c):
        """0791:BBFF (seg_0791_19.asm:427-458): +0x2D := value, then 3431 per nonzero squad word."""
        country = self._country(c)
        country["tactics"] = value & 0xFF
        for w in country["squad"]:
            if w:
                self.set_player_tactics(w)

    def squad_strength(self, t):
        """0791:BD03's sums (seg_0791_19.asm:BD09-BD67): 377E over the first 11 squad words."""
        total = 0
        for w in self._squad(t)[:11]:
            total = (total + self.player_strength(w)) & 0xFFFF
        return total

    def team_stronger(self, t):
        """BD03 as BD83 calls it: t's sum above the other's, unsigned (BD69-BD77)."""
        return self.squad_strength(t) > self.squad_strength(1 - t)

    # --- the line sums: 1771:0BC4 (seg_1771_02.asm:124-378) --------------------------

    def manager_bonus(self, c):
        """1771:0AA7 (seg_1771_02.asm:7-35): (manager[3*(+0x2E)+1]) idiv 8 + 0x10. The quality
        byte is ZERO-extended (`xor ah,ah` at 0AD9) before the `idiv`, so it is read unsigned
        (0..255) and the idiv never sees a negative dividend."""
        country = self._country(c)
        b = self.managers[3 * country["managed"] + 1]
        return (idiv(b, 8) + 0x10) & 0xFFFF

    def line_sums(self, flag, side, c):
        """The four word sums at DS:9B45 + 2*side + 4*k (k = 0 keeper, 1 defence, 2 midfield, 3 attack)."""
        country = self._country(c)
        m = self.manager_bonus(c)
        m8 = (m & 0xFFFF) // 8                      # xor dx,dx; div 8 (unsigned, 0CF7-0D01)
        sums = [0, 0, 0, 0]
        for slot in range(1, 12):                   # squad slots 1..11 (0C0D-0DD1)
            w = country["squad"][slot - 1]
            if w == 0:
                continue
            v = self.player_strength(w)
            if v != 0:
                v = (v + m) & 0xFFFF                # 0C5F-0C68
            p = self._player(w)
            if p[6] != 0:                           # keepers take no share (0C6B-0C75)
                for e in (1, 5, 6):                 # the set at CS:0BA4 = 62 -> elements {1,5,6}
                    if e < 5:                       # 0C95-0CCC
                        if bit_elem(e + 4, p[0xF]):             # +0xF element (e+4) = 5
                            eff = bit_elem(e, p[0xF])
                        else:
                            eff = bit_elem(e, country["tactics"])
                    else:                           # 0CCC-0CEE
                        eff = bit_elem(e, country["tactics"])
                    if eff:
                        sums[3] = (sums[3] + m8) & 0xFFFF       # attack (0D0B)
                    else:
                        sums[1] = (sums[1] + m8) & 0xFFFF       # defence (0D25)
            k = self.t_posline[p[6]]
            if k < 4:
                sums[k] = (sums[k] + v) & 0xFFFF                 # 0D44-0D68
            else:
                v = v // 2                                       # unsigned (0D6E-0D78)
                sums[k - 3] = (sums[k - 3] + v) & 0xFFFF
                sums[k - 2] = (sums[k - 2] + v) & 0xFFFF
        if flag:
            for k in range(4):
                sums[k] = (sums[k] + idiv(s16(sums[k]), 8)) & 0xFFFF   # 0DDA-0E1C (signed)
        return sums

    # --- the contests: 0791:B19D (seg_0791_18.asm:417-523) ---------------------------

    def roll_quick_goals(self, attempts):
        """Per contest the OPPONENT's draw comes first (B1C5-B1D4: al = 1 - t), the own side's
        second (B1E0-B1E8: al = t): c1 rand(mid[1-t]) vs rand(mid[t]); c2 rand(2*def[1-t]) vs
        rand(atk[t]) (B207-B220); c3 rand(gk[1-t]) vs rand(atk[t]) (B23B-B24D); each `jle`
        (signed) stops the attempt; all three won -> a goal (`inc 9B3C+t`, B261).
        Returns fresh goal counts [t0, t1]."""
        sums = [self.line_sums(0, 0, self.teams[0]), self.line_sums(self.flag80fc, 1, self.teams[1])]
        fresh = [0, 0]
        for t in (0, 1):
            gk_o, de_o, mi_o, at_o = sums[1 - t]
            _, _, mi, at = sums[t]
            for _ in range(attempts):
                a = self.rng.rand(mi_o)
                b = self.rng.rand(mi)
                if b <= a:                          # cmp ax,dx; jle (signed)
                    continue
                a = self.rng.rand((2 * de_o) & 0xFFFF)
                b = self.rng.rand(at)
                if b <= a:
                    continue
                a = self.rng.rand(gk_o)
                b = self.rng.rand(at)
                if b <= a:
                    continue
                fresh[t] += 1
        return fresh

    # --- computer tactics after a goal: 0791:C173 and its tree -----------------------

    def include_elem(self, c, r):
        self._country(c)["tactics"] |= 1 << (r - 1)

    def exclude_elem(self, c, r):
        self._country(c)["tactics"] &= ~(1 << (r - 1)) & 0xFF

    def bd83(self, t):
        """seg_0791_19.asm:585-708."""
        c = self.teams[t]
        self.bbff(self.t_r008[c], c)
        if t == 1 and self.flag80fc and self.team_stronger(t):
            self.include_elem(c, 1)                 # 0C79(1) (BE01-BE08)
            self.bbff(self._country(c)["tactics"], c)
        if self.team_stronger(t):
            for _ in range(2):
                self.include_elem(c, self.rng.rand(6))   # the rand result is the element (BE56-BE69)
            self.bbff(self._country(c)["tactics"], c)
        self.once_8332[t] = 0                       # BE8B/BE9C
        self.once_8334[t] = 0

    def bf6b(self, flag2, t):
        """seg_0791_19.asm:784-843."""
        c = self.teams[t]
        self.bd83(t)
        for _ in range(3):
            r = self.rng.rand(6)
            if flag2:
                self.include_elem(c, r)
            else:
                self.exclude_elem(c, r)
        self.bbff(self._country(c)["tactics"], c)

    def two_fad(self, w):
        """1771:2FAD (seg_1771_04.asm:2FC7-2FF2): E54[w % 12] + E46[+7]."""
        p = self._player(w)
        return (self.t_2fad_a[w % 12] + self.t_2fad_b[p[7]]) & 0xFFFF

    def bec7(self, c):
        """seg_0791_19.asm:BEC7-BF68: re-place the back four when C01A pushes up."""
        country = self._country(c)
        for slot in range(1, 12):
            w = country["squad"][slot - 1]
            if w == 0:
                continue
            p = self._player(w)
            if p[6] not in {9, 10, 11}:             # the set at CS:0xBEA7 = bytes 00 0E (08DF: bit e)
                continue
            if self.unavailable(w):
                continue
            p[6] = self.t_newpos[1 if self.two_fad(w) >= 0x48 else 0]
            break                                   # BF5A: after the write, jump to the return
            # path (BF65) — only the FIRST qualifying player is re-placed (BF56 is the only write)

    def c01a(self, t):
        """seg_0791_19.asm:849-930."""
        if self.once_8332[t]:
            return
        c = self.teams[t]
        for _ in range(5):
            self.include_elem(c, self.rng.rand(5))
        self.include_elem(c, 6)
        self.bbff(self._country(c)["tactics"], c)
        self.once_8332[t] = 1
        w = self._country(c)["squad"][8]            # the word at +0x10 (C0A9-C0BB)
        if self._player(w)[6] not in {12, 13}:      # the set at CS:0xBFFA = 00 30 -> elements
            self.bec7(c)                            # {12,13}; C0CA `je` calls BEC7/230C when the
            self.apply_230c()                       # position is NOT a member (membership zero)

    def c0df(self, t):
        """seg_0791_19.asm:932-994."""
        if self.once_8334[t]:
            return
        c = self.teams[t]
        for _ in range(5):
            self.exclude_elem(c, self.rng.rand(5))
        self.exclude_elem(c, 6)
        self.bbff(self._country(c)["tactics"], c)
        self.once_8334[t] = 1

    def c173(self):
        """seg_0791_19.asm:997-1110. 65FE's flag argument selects BF6B's include side only through
        the score comparison C173 itself makes (C1D0-C206); 7C39 is 0 in a quick match, so the
        flag BF6B receives is 0 for the team ahead and 1 for the team behind."""
        d = s8((self.score[0] - self.score[1]) & 0xFF)
        ad = -d if d < 0 else d
        for t in (0, 1):
            if self._country(self.teams[t])["managed"] > 0x80:   # 1771:0B77 (unsigned)
                continue
            if ad < 2:
                self.bd83(t)
            elif ad == 2:
                self.bf6b(0 if self.score[t] > self.score[1 - t] else 1, t)
            elif self.score[t] > self.score[1 - t]:
                self.c0df(t)
            else:
                self.c01a(t)

    def apply_230c(self):
        """0791:230C (seg_0791_04.asm:357-2619): per team, three parts.
        1. The pitch sort: swap pitch records until the position keys (0xE for unavailable
           players, else +6) no longer rise towards the lower slot: the inner-outer compare is
           `jb` (23B2-23C0), so a record with a smaller key swaps up. Each pitch swap also calls
           `0791:2218` (23C4), which swaps the SAME two squad words of the team's country record
           (2242-226B; the squad slots are the loop indices themselves, 1..11), so the squad
           array follows the sort — scorer selection and later substitutions read it.
        2. `a260` per slot base+1..base+11 (2541-258A) re-derives pitch+6 (:= the address slot)
            and pitch+0xD from the squad: 254D sets the bound to base+11 (`add ax, 0xb`), 255F
            starts the counter at base+1, and 2581 calls a260 BEFORE 2587/258A compare, so all
            eleven slots are covered.
        3. The bench sort (258C-25F3): squad slots 12..20 are ordered by the players' +6
           (`jb` at 25E3), each swap again a bare `2218` (25E6) on the squad words.
        The 830B/830C/830D bytes are re-pointed at the swapped slots (2432-252C); only 830B
        matters here (6337's keeper gate)."""
        for t in (0, 1):
            base = self.side_base[t]
            slots = [base + i for i in range(1, 12)]
            squad = self._country(self.teams[t])["squad"]

            def key(slot):
                w = self.pitch[slot]["player"]
                return 0xE if self.unavailable(w) else self._player(w)[6]

            for outer in range(0, 10):
                for inner in range(outer + 1, 11):
                    if key(slots[inner]) >= key(slots[outer]):
                        continue
                    a, b = slots[outer], slots[inner]
                    self.pitch[a], self.pitch[b] = self.pitch[b], self.pitch[a]
                    squad[outer], squad[inner] = squad[inner], squad[outer]   # 2218 (23C4)
                    if self.eight30b == a:
                        self.eight30b = b
                    elif self.eight30b == b:
                        self.eight30b = a
            for g in slots:                        # a260 (2541-258A): base+1..base+11 (254D/255F)
                self.pitch[g]["slot_no"] = g
            for outer in range(11, 19):              # the bench sort (258C-25F3)
                for inner in range(outer + 1, 20):
                    if self._player(squad[inner])[6] < self._player(squad[outer])[6]:
                        squad[outer], squad[inner] = squad[inner], squad[outer]   # 2218 (25E6)

    # --- after a goal: 0791:65FE/65A4/6337 -------------------------------------------

    def after_goal(self):
        """0791:65FE (seg_0791_11.asm:317-6754) with 65A4 and 6337; only 6337 and C173 can draw.
        65FE's order: 0441(4) whistle -> pitch+7 word copies (display) -> 65A4 (pitch+0x12
        resets + 6337) -> C173 -> the per-slot form update -> 832A/9B55 (not engine-read)."""
        if self.eight30b in (1, 12):                # 0791:045D
            r = self.rng.rand(10)                   # 6337's single draw (seg_0791_11.asm:6384-638D)
            base = self.side_base[1 if self.eight30b < 12 else 0]   # 2996: (830B < 12) ? 1 : 0
            self.eight30b = (r + 1 + base) & 0xFF
        self.c173()                                 # the flag is (7C39 == 0) = 1 (664C-665C)
        self.after_goal_form_swing()                # 65FE's per-slot form update (6666-66DD)

    def after_goal_form_swing(self):
        """65FE's per-slot loop (seg_0791_11.asm:6666-66DD, the 7C39 == 0 path at 668A-66AF):
        every AVAILABLE pitch player's form (+0xC) moves by s8(DS:0x7920[2b51(pitch)]) with
        7CC5's 214B:2000 clamp (1..0xFF); 2b51 (seg_0791_05.asm:2B51) = the slot's side
        (2974: pitch+6 < 12) equals 830B's side (2996: 830B < 12), and DS:0x7920 =
        [0xFF, 0x01] — so the side holding DS:830B (after a goal: the SCORING side, unless
        6337 re-pointed it, which stays on that side) gains +1 form on every available
        player, the other side loses 1. +0xC is read by 377E (`v += s8(+0xC)` while
        < 0x20), so the goal shifts both line sums from the next minute on — E010-r0010's
        divergence (minute 63's first B19D draw: midfield sum 589 vs the original's 595)."""
        ball_side_is_1 = self.eight30b < 12                     # 2996
        for slot in range(1, 23):
            w = self.pitch[slot]["player"]
            if self.unavailable(w):                             # 2956 gate (6683)
                continue
            slot_side_is_1 = self.pitch[slot]["slot_no"] < 12   # 2974: (pitch + 6 < 12)
            idx = 1 if slot_side_is_1 == ball_side_is_1 else 0  # 2B51: (2996 == 2974)
            p = self._player(w)
            c = s8(p[0xC]) + s8(self.t_formdelta[idx])
            p[0xC] = max(1, min(0xFF, c)) & 0xFF                # 7CC5's clamp (7CF1-7D09)

    # --- substitutions: 0791:8062 -> C88D -> c7eb/aae8/a9b8/c5dc ----------------------

    def _pos_string_index(self, pos):
        """Pos(char, DS:08CE) via 23E4:06E3: the 1-based index of pos in the string, 0 if absent."""
        s = self.t_posstring
        body = bytes(s[1:1 + s[0]])
        return body.index(pos) + 1 if pos in body else 0

    def c7eb(self, t, slot):
        """seg_0791_20.asm:C7EB-C88A: +7 -> bench squad slot; later slots overwrite earlier ones
        (the store at C87A is unconditional), so the last match wins."""
        country = self._country(self.teams[t])
        outgoing = self.pitch[slot]["player"]
        table = {}
        for k in range(12, 21):
            w = country["squad"][k - 1]
            if w == outgoing or self.unavailable(w):
                continue
            table[self._player(w)[7]] = k
        return table

    def aae8(self, t, slot):
        """seg_0791_17.asm:AAE8-AC64: pick the bench squad slot for the outgoing player's position."""
        country = self._country(self.teams[t])
        pos = self._player(self.pitch[slot]["player"])[6]
        table = self.t_formation[8 * pos:8 * pos + 8]
        count = self._pos_string_index(pos)
        expect = 1 if count > 3 else 0
        n = table[0]
        best = 0
        if count > 0:                               # AB43: count <= 0 -> the AC07 fallback
            for i in range(1, n + 1):
                cand = self._c7eb_lookup.get(table[i])
                if not cand:
                    continue
                w = country["squad"][cand - 1]
                if not self.two_footed(w) and self.foot_index(w) != expect:
                    continue                        # ABB4-ABE0
                best = cand                         # ABE2-ABF7: the store is overwritten, so the
            return best                             # LAST passing entry wins
        for i in range(1, n + 1):                   # AC07-AC56: same, without the foot check
            cand = self._c7eb_lookup.get(table[i])
            if cand:
                best = cand
        return best

    def a9b8(self, t, pos):
        """seg_0791_17.asm:A9B8-AAE5: best bench slot 12..20 by BENCH_VALUE[14*pos + (+7)], where
        pos is the POSITION ARGUMENT ([bp+6], AA56: the outgoing keeper's position), not the
        candidate's own +6; that argument also gives the foot expectation."""
        country = self._country(self.teams[t])
        count = self._pos_string_index(pos)
        expect = 1 if count > 3 else 0
        best, best_v = 0, 0
        for k in range(12, 21):
            w = country["squad"][k - 1]
            if self.unavailable(w):
                continue
            p = self._player(w)
            v = self.t_benchvalue[14 * pos + p[7]]          # AA4E (+7) then AA56 (14*[bp+6])
            if count > 0 and not self.two_footed(w) and self.foot_index(w) != expect:
                v //= 2                             # AAAD-AAB7
            if v > best_v:                          # AABA-AACB
                best, best_v = k, v
        return best

    def c5dc(self, chosen, slot, t, incoming):
        """seg_0791_20.asm:C5DC-C7E8 (quick mode: the display paths C50C/1E8D are skipped).
        a2e6 (C6E5) re-derives pitch+0xD from the already-swapped squad BEFORE the C6FA-C724
        block, so the 0x2747 word, the +0xF clear and 3431 hit the INCOMING player (and only for
        an unmanaged team, C700); the 0C79(3) mark at C612 hits the OUTGOING one. After the
        DS:9978 marking games, 230C runs unconditionally (C7A7, re-sorting pitch records and
        squad words), then the budget is decremented (C7DC)."""
        outgoing = self.pitch[slot]["player"]
        self._player(outgoing)[0x10] |= 1 << 2         # 0C79(3): mark element 3 (unavailable via 3216)
        # a2e6 (C6E5): the pitch record's +6 := the address slot, then +0xD := the squad word at
        # 2bb1 of that — the incoming player — BEFORE the 0x2747/+0xF block and the 230C sort
        self.pitch[slot]["slot_no"] = slot
        self.pitch[slot]["player"] = self._squad(t)[self._pitch_squad_index(slot) - 1]
        if not self._country(self.teams[t])["managed"] > 0x80:
            p = self._player(incoming)
            p[0x12:0x14] = (0x2747).to_bytes(2, "little")   # C6FA
            p[0xF] = 0                                      # C718
            self.set_player_tactics(incoming)                # 3431 (C724)
        # the DS:9978 marking games (C733-C7D4) touch only managed teams' display records
        self.apply_230c()                                    # C7A7: 230C re-sorts pitch AND squad
        self.sub_budget[t] = (self.sub_budget[t] - 1) & 0xFF                     # C7DC

    def c88d(self, t, slot):
        """seg_0791_20.asm:C88D-CAAA. Returns True when a substitution was made."""
        country = self._country(self.teams[t])
        s = slot - self.side_base[t]                   # C8AE: s = slot - 0668[t] (address-based)
        outgoing = self.pitch[slot]["player"]
        if self.sub_budget[t] == 0:                 # C899
            # only a forced C48D swap on an exhausted player; not reached by E010's runs
            if s8(self._player(outgoing)[0xE]) < 1:
                raise FoulPathNotModelled("C48D forced substitution not modelled (9B3A exhausted)")
            return False
        self._c7eb_lookup = self.c7eb(t, slot)
        chosen = self.aae8(t, slot)
        if chosen == 0 and self._player(outgoing)[6] == 0:     # the keeper fallback (C912-C96B)
            chosen = self.a9b8(t, self._player(outgoing)[6])
        if chosen == 0:
            return False
        squad = country["squad"]
        self._player(squad[chosen - 1])[6] = self._player(outgoing)[6]    # position copy (C9AD-C9CA)
        squad[s - 1], squad[chosen - 1] = squad[chosen - 1], squad[s - 1]  # 214B:007B swaps 2 bytes
        # (the shadow words at 9A3E+0x28*t and the byte at 9B07+0x14*t swap the same way; nothing
        # the quick engine reads looks at them)
        # c5dc runs while pitch+0xD still names the OUTGOING player (the C612 mark comes first);
        # a2e6 inside c5dc (C6E5) then re-points the record at the incoming before the 230C sort
        self.c5dc(chosen, slot, t, incoming=squad[s - 1])
        return True

    def check_substitutions(self, minute_831b):
        """0791:8062 (seg_0791_13.asm:905-8205), the unmanaged branch: the managed branch is dead
        in a quick match (DS:9B40 is 0 from A4A1 on, 80A9-80AE)."""
        for t in (0, 1):
            if self._country(self.teams[t])["managed"] > 0x80:
                continue
            if self.sub_budget[t] <= 0:
                continue
            s = 11
            while s >= 2:
                slot = self.side_base[t] + s
                p = self._player(self.pitch[slot]["player"])
                sub = (bit_elem(6, p[0x10]) == 0     # 0C57(6, +0x10) clear (815D-8172)
                       and s8(p[0xE]) > 0            # 8174-817C
                       and minute_831b > 1           # 817E-8183 (signed)
                       and s > 1
                       and minute_831b < 0x23        # 818B-8190 (signed)
                       and s16(int.from_bytes(p[0x12:0x14], "little")) < 0x5A - minute_831b)  # 8192-81AF
                if sub:
                    self.c88d(t, slot)
                    if self.sub_budget[t] == 0:
                        break                        # 81E4-81EB: the scan stops at slot 1
                s -= 1

    # --- the minute: 0791:D733 (seg_0791_21.asm:794-DAF7) ----------------------------

    def record_goal_scorer_effects(self, w):
        """The scorer-side writes of the goal path, all engine-relevant state:
        1. `inc word +0x0A` — the goals counter (6484, seg_0791_11.asm).
        2. `+0xC := clamp(s8(+0xC) + s8(DS:0x7920[1]))` — 6443's 7cc5 call (64CC-64DE pushes
           DS:0x7920[7C39 != 0 ? 0 : 1] — the quick match has 7C39 = 0, so byte 1, value +1 —
           then 7CC5-7D09 adds it with a 214B:2000 clamp). +0xC is READ BY 377E
           (player_strength: `v += s8(+0xC)` while +0xC < 0x20), so this shifts the scorer's
           strength from the next minute on (E010-r0010: the original's Durnin had +0xC 28 vs
           the model's 27 at the goal pause).
        3. `+0x12 += s8(DS:0x720[0x26])` — 2aa3's commentary ring write (1E53 tail, 1E9C-1EAB:
           `add word es:[di+0x12], ax` with ax = DS:0x720[ring id]; the quick goal id is 0x26,
           value +40 — 0x2747 + 0x28 = 0x276F in E010-r0010). Inert for draws (the sub gate's
           0x5A bound is far below either value) but kept for state faithfulness."""
        p = self._player(w)
        p[0xA:0xC] = ((int.from_bytes(p[0xA:0xC], "little") + 1) & 0xFFFF).to_bytes(2, "little")
        c = s8(p[0xC]) + s8(self.t_formdelta[1 if self.sevenc39 == 0 else 0])
        c = max(1, min(0xFF, c))                    # the 214B:2000 clamp (7CF1, bounds 1..0xFF)
        p[0xC] = c & 0xFF
        fit = int.from_bytes(p[0x12:0x14], "little")
        fit = (fit + s8(self.t_fitness[self.t_goal_id])) & 0xFFFF
        p[0x12:0x14] = fit.to_bytes(2, "little")

    def d733(self, minute_831f, minute_831b):
        idx = 1 if self.eight319 == 0x0F else 0
        saved = self.score[:]
        fresh = self.roll_quick_goals(self.t_attempts[idx])
        # the four statistics draws (D7C0-D86A): counters only, but each chance is a draw
        for t in (0, 1):
            self.rng.chance(self.t_stats5[bit_elem(5, self._tactics(t))])
            self.rng.chance(self.t_stats1[bit_elem(1, self._tactics(t))])
        # the minute fill (D873-DA4C): per team t, only when its fresh count exceeds its saved score
        # (D88F `ja`; otherwise the code jumps straight to the DA4C loop test, no fill and no goal
        # phase), 9B3C[t] is reduced by the saved score (D8A5 `sub`) and minutes are then drawn for
        # BOTH teams — j = 0 and 1 — from the CURRENT 9B3C[j] counts (D8B2-D8FC), so the other
        # team's raw, unsubtracted count is drawn for too; the goal phase (D911-DA43) is the j loop
        # the fill's own j loop falls into, so it runs only after a fill
        counts = fresh[:]
        minutes = [[], []]
        scored = False
        for t in (0, 1):
            if counts[t] > saved[t]:
                counts[t] -= saved[t]
                for j in (0, 1):
                    minutes[j] = [self.rng.rand(self.t_minutes[idx])
                                  for _ in range(counts[j])]
                # the buffer still holds the first fill's minutes when team 1's turn refills them,
                # so a minute equal to 831F in the first fill scores before the second fill can
                # overwrite it
                for j in (0, 1):
                    for k in range(counts[j]):
                        if scored:                   # D93C-D944: one goal per D733 call
                            break
                        m = minutes[j][k] if k < len(minutes[j]) else 0    # cleared buffer (D767-D76E)
                        if m != minute_831f:         # D945-D961
                            continue
                        if saved[j] >= 0xF:          # D964-D970
                            continue
                        while True:
                            slotv = self.t_scorer[self.rng.rand(30)]    # D973-D984: byte at 0xA6B + r, r in 1..30
                            w = self._squad(j)[slotv - 1]
                            if not self.unavailable(w):                   # D9A7-D9B2
                                break
                        saved[j] += 1                # D9B4-D9BA
                        squad_slot = 1
                        while (self._squad(j)[squad_slot - 1] != w and squad_slot < 20):
                            squad_slot += 1          # 3A82 (seg_1771_05.asm:3A9C-3ACA)
                        self.eight30b = (self.side_base[j] + squad_slot) & 0xFF              # D9FB-DA09
                        self.goals.append({"team": j, "minute": m, "player": w,
                                           "squad_slot": squad_slot,
                                           "stored_byte": m | self.minute_mark})  # 6443 (DA16-DA2C)
                        self.record_goal_scorer_effects(w)                       # 6443's scorer writes
                        scored = True
            if scored:
                # DA34: a scored goal sets the outer team byte to 1, so the DA4C loop test ends the
                # fill after this team — team 1's fill (and its minute draws) never runs
                break
        self.score = saved
        # the energy loop (DA6F-DAC9): every fifth minute, pitch players above 1 lose one
        if minute_831b % 5 == 0:
            for slot in range(1, 23):
                p = self._player(self.pitch[slot]["player"])
                if s8(p[0xE]) > 1:                   # cmp 1; jle skips (signed)
                    p[0xE] = (p[0xE] - 1) & 0xFF
        if self.ninea3d and not scored:              # DACB-DAD9
            self.d5c1()
        if scored:
            self.after_goal()                        # 0106(0) + 65FE (DAE7-DAEE)
        else:
            self.check_substitutions(minute_831b)    # 8062 (DAE2)
        # 9372, the key poll, draws nothing (seg_0791_15.asm:727-950: no 214B:06xx call)

    def d5c1(self):
        """0791:D5C1 (seg_0791_21.asm:621-792): the foul rolls, as far as the model goes."""
        r = self.rng.rand(10) + 1                   # D5CB rand(10), D5D0 `inc ax` -> r in 2..11
        slot1 = (r + self.side_base[1]) & 0xFF      # D5E9-D5FF: slot[side] += 0668[side] ([bp-3])
        slot0 = (self.t_slotmap[r] + self.side_base[0]) & 0xFF   # D5D7: DS:0xA90[r] (= 13-r; [bp-5])
        if self.unavailable(self.pitch[slot1]["player"]):        # D618 (the r slot first)
            return
        if self.unavailable(self.pitch[slot0]["player"]):        # D634
            return
        _ = 1 if self.rng.rand(2) == 1 else 0       # D63E: the coin is drawn only after both checks
        raise FoulPathNotModelled("D5C1 reached the 278A/7EEF branch with 9A3D set")

    # --- the half ---------------------------------------------------------------------

    def run(self):
        """The 46 second-half minutes: 831F = 46..91, 831B = 45..0 (970C advances after D733)."""
        for minute in range(46, 92):
            self.d733(minute, 91 - minute)
        return {
            "score": tuple(self.score),
            "goals": self.goals,
            "seed_DS7B62": self.rng.seed,
            "seed_DS8336": self.seed2,              # untouched: 94E8 is the only stepper (F004)
            "draws": self.rng.draws,
        }


def simulate(state):
    return QuickMatch(state).run()
