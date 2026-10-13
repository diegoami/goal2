"""T22: regression pins of the vendored quick engine's change-tactics-when-behind
behaviour (A-CPU-2's change side), driving ``QuickMatch.c173()`` on a synthetic stub state.

[confirmed: F028 (E028)] C01A, behind by more than 2: include ``rand(5)`` five times, then
element 6, write ``+0x2D`` through BBFF, at most once per stretch (the ``DS:8332`` flag);
then the slot-9 position test and the BEC7 conversion (the FIRST available code-9/10/11
squad member becomes 12 at height >= 0x48, else 13), then the 230C re-sort.
[confirmed: routines.tsv (0791:C0DF)] C0DF, ahead by more than 2: exclude ``rand(5)`` five
times, then element 6, through BBFF, once per stretch (the ``DS:8334`` flag).
[confirmed: vendored quick_engine.py at 8760df9] C173 after every goal: margin <2 -> BD83
(reset to the country's R008 default, once-flags cleared); margin ==2 -> BF6B (BD83, then
three ``rand(6)`` includes for the trailing side / excludes for the leading side); margin
>2 -> C0DF (leading) / C01A (trailing); a country whose managed byte ``+0x2E`` > 0x80 is
skipped (1771:0B77).

[designed] These tests are regression pins of the vendored model, not fidelity proof: F021
records that the E020 halves never reached 230C, so the model is not seed-exact on this
path and rule 20's arbiter clause does not apply. The pins exist so a future re-vendor
cannot silently lose the behaviour. Expected bit patterns are computed by drawing from a
parallel ``LCG`` seeded with the same word, never hardcoded literals copied out of a run.

The stub state is synthetic and test-local: a flat memory image exposing the
``ds_bytes`` / ``ds_word`` / ``memory`` surface the vendored engine and the vendored
``players.py`` readers use, so scores, flags and records are fully controlled. Each test
constructs ``QuickMatch``, sets ``qm.score``, then calls ``qm.c173()`` directly, so the
LCG position is honest (no match is driven and no draw is guessed).
"""
import unittest

# [designed] Import cli first to trigger its sys.path setup for the vendored engine
# directory (so `import players` inside quick_engine resolves to goal2/engine/players.py),
# the same approach the suite's other engine-adjacent tests take.
from goal2 import cli  # noqa: F401

import players  # noqa: E402  the vendored reader, goal2/engine/players.py
from goal2.engine.quick_engine import LCG, QuickMatch  # noqa: E402

# [designed] Stub memory layout: the DS area is the first 0x10000 bytes (DS base 0) and
# the arrays the far pointers name sit on paragraph boundaries above it.
COUNTRIES_ADDR = 0x10000                       # players.COUNTRIES_PTR points here
PLAYERS_ADDR = 0x17000                         # 0x603F of country records end at 0x1603F
MANAGERS_ADDR = 0x26000                        # 0xEF24 of player records end at 0x25F24
MEM_SIZE = MANAGERS_ADDR + 0x400               # + the manager rows QuickMatch reads

C0, C1 = 1, 2                                  # the two countries playing: teams[0], teams[1]

SEED = 0x1234                                  # the DS:7B62 word every test starts from


def squad_words(c):
    """[designed] Country c's twenty synthetic player words: 20*c+1 .. 20*c+20."""
    return list(range(20 * c + 1, 20 * c + 21))


def _player_record(position=5):
    """[designed] A synthetic available outfield player record (0x14 bytes): two-footed
    (1771:3041: (+5) + (+2) == 0x1E), hardness >= 4 (1771:2FFB: (+5) - ((+3) & 1), so
    BBFF's 3431 call writes nothing), position 5 (no special set membership), +7 = 1 so
    wrong-foot (1771:3179) is False. Identical records on both sides keep the BD03
    strength sums equal, so team_stronger is false and BD83 adds no conditional draws."""
    p = bytearray(0x14)
    p[2] = 0x0A
    p[4] = 0x40
    p[5] = 0x14
    p[6] = position
    p[7] = 1
    p[0xC] = 0x10
    p[0xE] = 0x20                                # energy >= 1: available (1771:3216)
    return p


class StubState:
    """[designed] A synthetic state with the ds_bytes / ds_word / memory surface of the
    vendored savestate reader, DS based at 0 in one flat image."""

    def __init__(self):
        self.mem = bytearray(MEM_SIZE)

    def memory(self, addr, n):
        return bytes(self.mem[addr:addr + n])

    def ds_bytes(self, off, n):
        return bytes(self.mem[off:off + n])

    def ds_word(self, off):
        return int.from_bytes(self.mem[off:off + 2], "little")

    # --- writers, used only while building the stub ---
    def put(self, off, data):
        self.mem[off:off + len(data)] = data

    def put_word(self, off, w):
        self.mem[off:off + 2] = (w & 0xFFFF).to_bytes(2, "little")

    def put_far(self, ptr_off, addr):
        """[confirmed: vendored players.py at 8760df9] A far pointer is the dword
        offset:segment, little-endian, offset first."""
        self.put_word(ptr_off, addr % 16)
        self.put_word(ptr_off + 2, addr // 16)


def build_state(seed=SEED, tactics=(0x00, 0x00), managed=(0x00, 0x00),
                once_8332=(0, 0), once_8334=(0, 0), r008=(0x00, 0x00),
                positions=None, two_fad_a=None):
    """[designed] A stub state for a quick match between C0 and C1 at 0-0 (tests set
    ``qm.score`` themselves after construction), both unmanaged, no extra time, the foul
    gate clear, five substitution points each, and the pitch slots pointing at the first
    eleven squad words of each side (team 1 at slots 1..11, team 0 at slots 12..22, per
    the DS:0668 bytes [11, 0]).

    ``positions`` maps a player word to its +6 byte (default 5); ``two_fad_a`` overrides
    the 12 bytes at DS:0E54 (1771:2FAD's per-(word mod 12) height table)."""
    st = StubState()
    st.put_far(players.PLAYERS_PTR, PLAYERS_ADDR)
    st.put_far(players.COUNTRIES_PTR, COUNTRIES_ADDR)
    st.put_far(QuickMatch.MANAGERS_PTR, MANAGERS_ADDR)
    # the scalar DS fields QuickMatch.__init__ reads
    st.put_word(0x7B62, seed)                    # the main stream's seed
    st.put_word(0x8336, 0)                       # the second stream (speaker only)
    st.put(0x9B3C, bytes([0, 0]))                # score bytes; tests set qm.score directly
    st.put_word(0x9B34, C0)
    st.put_word(0x9B36, C1)
    st.put(0x80FC, b"\x00")                      # 0BC4's side-1 flag
    st.put(0x831A, b"\x00")                      # the first half's kick-off side
    st.put(0x9A3D, b"\x00")                      # the foul gate: a friendly
    st.put(0x8319, b"\x2d")                      # the half length marker
    st.put(0x7C36, b"\x00")                      # no extra time
    st.put(0x8324, b"\x00")
    st.put(0x7C39, b"\x00")
    st.put(0x9B3A, bytes([5, 5]))                # the substitution budgets
    st.put(0x8332, bytes(once_8332))             # C01A's once flags
    st.put(0x8334, bytes(once_8334))             # C0DF's once flags
    st.put(0x668, bytes([11, 0]))                # side_base: team t plays 0668[t]+1..+11
    # [confirmed: vendored quick_engine.py at 8760df9] BEC7 writes t_newpos[1] at height
    # >= 0x48 and t_newpos[0] below it; the task pins 12 and 13 respectively.
    st.put(QuickMatch.BEC7_NEWPOS, bytes([13, 12]))
    st.put(QuickMatch.R008, bytes(129))          # per-country default tactics bytes...
    st.put(QuickMatch.R008 + C0, bytes([r008[0]]))
    st.put(QuickMatch.R008 + C1, bytes([r008[1]]))
    if two_fad_a is not None:
        st.put(QuickMatch.F2FAD_A, bytes(two_fad_a))
    # the country records: squad words, the +0x2D tactics byte, the +0x2E managed byte
    for c, tac, man in ((C0, tactics[0], managed[0]), (C1, tactics[1], managed[1])):
        base = COUNTRIES_ADDR + players.COUNTRY_SIZE * c
        for i, w in enumerate(squad_words(c)):
            st.put_word(base + 2 * i, w)
        st.put(base + 0x2D, bytes([tac]))
        st.put(base + 0x2E, bytes([man]))
    # the player records
    positions = positions or {}
    for c in (C0, C1):
        for w in squad_words(c):
            st.put(PLAYERS_ADDR + players.PLAYER_SIZE * w,
                   _player_record(positions.get(w, 5)))
    # the pitch records (8062: 813B-8148): slot 1..22 at 0x80E8 + 0x16*slot
    for slot in range(1, 23):
        base = 0x80E8 + 0x16 * slot
        w = squad_words(C1)[slot - 1] if slot <= 11 else squad_words(C0)[slot - 12]
        st.put(base + 6, bytes([slot]))
        st.put_word(base + 0xD, w)
    return st


def new_match(**kwargs):
    """[designed] A QuickMatch on a fresh stub state; the caller sets ``qm.score`` and
    calls ``qm.c173()`` so the LCG position is exactly where the score bytes put it."""
    return QuickMatch(build_state(**kwargs))


def draw_bits(rng, count, n):
    """[designed] The bit mask of ``count`` successive rand(n) draws from a parallel LCG:
    [confirmed: vendored quick_engine.py at 8760df9] rand(n) returns 1..n and
    include_elem/exclude_elem act on bit r-1."""
    bits = 0
    for _ in range(count):
        bits |= 1 << (rng.rand(n) - 1)
    return bits


class C01ABehindByMoreThan2(unittest.TestCase):
    """[confirmed: F028 (E028)] Behind by more than 2, C01A includes five rand(5) draws
    and element 6 into the country's +0x2D byte and sets the DS:8332 once flag."""

    def test_c01a_includes_five_draws_and_element_6(self):
        qm = new_match(tactics=(0x01, 0x00))
        qm.score = [0, 3]                        # team 0 trails by 3
        par = LCG(SEED)                          # the parallel stream, same seed word
        inc0 = draw_bits(par, 5, 5)              # t0's C01A draws first (C173 loops t 0,1)
        draw_bits(par, 5, 5)                     # then t1's C0DF draws
        qm.c173()
        # [confirmed: F028 (E028)] prior OR the five drawn bits OR element 6 (bit 5)
        self.assertEqual(qm.countries[C0]["tactics"], 0x01 | inc0 | (1 << 5))
        self.assertEqual(qm.once_8332[0], 1)
        # [designed] the draw count pins that each side's routine ran exactly once
        self.assertEqual(qm.rng.draws, 10)

    def test_c01a_once_flag_blocks_a_second_call(self):
        """[confirmed: F028 (E028)] At most once per stretch: a second C173 at the
        unchanged score leaves the byte, the once flags and the stream untouched."""
        qm = new_match(tactics=(0x01, 0x00))
        qm.score = [0, 3]
        qm.c173()
        byte0 = qm.countries[C0]["tactics"]
        flags = (qm.once_8332[:], qm.once_8334[:])
        draws = qm.rng.draws
        qm.c173()
        self.assertEqual(qm.countries[C0]["tactics"], byte0)
        self.assertEqual((qm.once_8332[:], qm.once_8334[:]), flags)
        self.assertEqual(qm.rng.draws, draws)


class C0DFAheadByMoreThan2(unittest.TestCase):
    """[confirmed: routines.tsv (0791:C0DF)] Ahead by more than 2, C0DF excludes five
    rand(5) draws and element 6 from the country's +0x2D byte and sets DS:8334."""

    def test_c0df_excludes_five_draws_and_element_6(self):
        qm = new_match(tactics=(0xFF, 0x00))
        qm.score = [3, 0]                        # team 0 leads by 3
        par = LCG(SEED)
        exc0 = draw_bits(par, 5, 5)              # t0's C0DF draws first
        draw_bits(par, 5, 5)                     # then t1's C01A draws
        qm.c173()
        # [confirmed: routines.tsv (0791:C0DF)] prior with the five drawn bits and bit 5
        # cleared
        self.assertEqual(qm.countries[C0]["tactics"], 0xFF & ~exc0 & ~(1 << 5))
        self.assertEqual(qm.once_8334[0], 1)
        self.assertEqual(qm.rng.draws, 10)


class BF6BMarginExactly2(unittest.TestCase):
    """[confirmed: vendored quick_engine.py at 8760df9] At margin exactly 2, BF6B resets
    through BD83 and then includes three rand(6) draws for the trailing side and excludes
    three for the leading side. Both squads are byte-identical, so team_stronger is false
    and BD83 adds no conditional draws (the 377E sums over the first 11 squad words are
    equal)."""

    def test_bf6b_resets_then_three_draws_each_side(self):
        qm = new_match(tactics=(0xFF, 0x00), r008=(0x00, 0xFF))
        qm.score = [0, 2]                        # team 0 trails by exactly 2
        par = LCG(SEED)
        inc0 = draw_bits(par, 3, 6)              # t0 (trailing): BF6B's includes
        exc1 = draw_bits(par, 3, 6)              # t1 (leading): BF6B's excludes
        qm.c173()
        self.assertEqual(qm.countries[C0]["tactics"], 0x00 | inc0)
        self.assertEqual(qm.countries[C1]["tactics"], 0xFF & ~exc1)
        self.assertEqual(qm.rng.draws, 6)


class BD83MarginBelow2(unittest.TestCase):
    """[confirmed: vendored quick_engine.py at 8760df9] At margin <2 after a goal, BD83
    resets +0x2D to the country's R008 default and clears both once flags. Squads are
    byte-identical (team_stronger false), so no conditional draws follow the reset."""

    def test_bd83_resets_to_r008_and_clears_once_flags(self):
        qm = new_match(tactics=(0xFF, 0xFF), r008=(0x15, 0x2A),
                       once_8332=(1, 1), once_8334=(1, 1))
        qm.score = [1, 2]                        # margin 1
        qm.c173()
        self.assertEqual(qm.countries[C0]["tactics"], 0x15)
        self.assertEqual(qm.countries[C1]["tactics"], 0x2A)
        self.assertEqual(qm.once_8332, [0, 0])
        self.assertEqual(qm.once_8334, [0, 0])
        self.assertEqual(qm.rng.draws, 0)


class ManagedByteExclusion(unittest.TestCase):
    """[confirmed: vendored quick_engine.py at 8760df9] C173 skips a country whose managed
    byte +0x2E is strictly above 0x80 (1771:0B77, an unsigned compare)."""

    def test_managed_side_untouched_at_0_5(self):
        qm = new_match(tactics=(0x00, 0x00), managed=(0x81, 0x00))
        qm.score = [0, 5]
        qm.c173()
        self.assertEqual(qm.countries[C0]["tactics"], 0x00)
        self.assertEqual(qm.once_8332[0], 0)
        self.assertEqual(qm.once_8334[0], 0)
        # [designed] five draws prove the unmanaged side's C0DF did run: the skip, not an
        # empty C173, is what left the managed side untouched
        self.assertEqual(qm.rng.draws, 5)

    def test_managed_byte_0x80_is_not_excluded(self):
        """[confirmed: vendored quick_engine.py at 8760df9] The compare is strict: 0x80
        itself does not skip, so the side's C01A runs. This test visits the boundary the
        class docstring asserts."""
        qm = new_match(tactics=(0x00, 0x00), managed=(0x80, 0x00),
                       positions={squad_words(C0)[8]: 12})
        qm.score = [0, 5]
        par = LCG(SEED)
        inc0 = draw_bits(par, 5, 5)
        qm.c173()
        self.assertEqual(qm.countries[C0]["tactics"], 0x00 | inc0 | (1 << 5))
        self.assertEqual(qm.once_8332[0], 1)


class BEC7Conversion(unittest.TestCase):
    """[confirmed: F028 (E028)] When C01A pushed the trailing side up and its slot-9
    player's position is outside {12,13}, BEC7 re-places the FIRST available code-9/10/11
    squad member (the lowest squad slot): code 12 at a 1771:2FAD height >= 0x48, else 13;
    the write is followed by a jump to the return, so exactly one conversion happens."""

    # [designed] Squad layout for country C0: slot 3 (word 23) is the first qualifying
    # player, slot 7 (word 27) the second; slot 9 (word 29) sits outside {12,13} so C01A
    # calls BEC7. 23 % 12 = 11 and 27 % 12 = 3 index the 2FAD height table.
    SLOT3, SLOT7, SLOT9 = 23, 27, 29

    def _match(self, height_slot3, height_slot7):
        two_fad_a = [0] * 12
        two_fad_a[self.SLOT3 % 12] = height_slot3
        two_fad_a[self.SLOT7 % 12] = height_slot7
        return new_match(positions={self.SLOT3: 9, self.SLOT7: 10, self.SLOT9: 5},
                         two_fad_a=two_fad_a)

    def test_first_qualifying_player_tall_becomes_12(self):
        """Height exactly 0x48 (the boundary the class docstring asserts) -> code 12."""
        qm = self._match(height_slot3=0x48, height_slot7=0x60)
        qm.score = [0, 3]
        qm.c173()
        self.assertEqual(qm.playerrec[self.SLOT3][6], 12)
        self.assertEqual(qm.playerrec[self.SLOT7][6], 10)  # untouched
        converted = [w for w in squad_words(C0) if qm.playerrec[w][6] in {12, 13}]
        self.assertEqual(converted, [self.SLOT3])

    def test_first_qualifying_player_short_becomes_13(self):
        """Height 0x47, one below the boundary, -> code 13; the second player untouched."""
        qm = self._match(height_slot3=0x47, height_slot7=0x60)
        qm.score = [0, 3]
        qm.c173()
        self.assertEqual(qm.playerrec[self.SLOT3][6], 13)
        self.assertEqual(qm.playerrec[self.SLOT7][6], 10)  # untouched
        converted = [w for w in squad_words(C0) if qm.playerrec[w][6] in {12, 13}]
        self.assertEqual(converted, [self.SLOT3])


if __name__ == "__main__":
    unittest.main()
