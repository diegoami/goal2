"""T22: regression pins of the vendored quick engine's change-tactics-when-behind
behaviour (A-CPU-2's change side), driving ``QuickMatch.c173()`` on a synthetic stub state.

[confirmed: F028 (E028)] C01A, behind by more than 2: include ``rand(5)`` five times, then
element 6, write ``+0x2D`` through BBFF, at most once per stretch (the ``DS:8332`` flag);
then the slot-9 position test and the BEC7 conversion (the FIRST available code-9/10/11
squad member becomes 12 at height >= 0x48, else 13; height = ``DS:0E46[+7] +
DS:0E54[n mod 12]`` via 1771:2FAD), then the 230C re-sort.
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


def _player_record(position=5, byte_overrides=None):
    """[designed] A synthetic available outfield player record (0x14 bytes): two-footed
    (1771:3041: (+5) + (+2) == 0x1E), hardness >= 4 (1771:2FFB: (+5) - ((+3) & 1), so
    BBFF's 3431 call writes nothing), position 5 (no special set membership), +7 = 1 so
    wrong-foot (1771:3179) is False. Identical records on both sides keep the BD03
    strength sums equal, so team_stronger is false and BD83 adds no conditional draws.

    ``byte_overrides`` is an optional {byte_offset: value} map applied after the defaults,
    so a test can mark a player as unavailable (+0xE == 0x00) without disturbing the rest
    of the synthetic shape."""
    p = bytearray(0x14)
    p[2] = 0x0A
    p[4] = 0x40
    p[5] = 0x14
    p[6] = position
    p[7] = 1
    p[0xC] = 0x10
    p[0xE] = 0x20                                # energy >= 1: available (1771:3216)
    if byte_overrides:
        for off, val in byte_overrides.items():
            p[off] = val & 0xFF
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
                positions=None, two_fad_a=None, two_fad_b=None,
                player_byte_overrides=None):
    """[designed] A stub state for a quick match between C0 and C1 at 0-0 (tests set
    ``qm.score`` themselves after construction), both unmanaged, no extra time, the foul
    gate clear, five substitution points each, and the pitch slots pointing at the first
    eleven squad words of each side (team 1 at slots 1..11, team 0 at slots 12..22, per
    the DS:0668 bytes [11, 0]).

    ``positions`` maps a player word to its +6 byte (default 5); ``two_fad_a`` overrides
    the 12 bytes at DS:0E54 (1771:2FAD's per-(word mod 12) height table); ``two_fad_b``
    overrides the 16 bytes at DS:0E46 (1771:2FAD's per-(+7) height table);
    ``player_byte_overrides`` is {player_word: {byte_offset: value}} for further
    tweaking (e.g., marking a player as unavailable)."""
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
    if two_fad_b is not None:
        st.put(QuickMatch.F2FAD_B, bytes(two_fad_b))
    # the country records: squad words, the +0x2D tactics byte, the +0x2E managed byte
    for c, tac, man in ((C0, tactics[0], managed[0]), (C1, tactics[1], managed[1])):
        base = COUNTRIES_ADDR + players.COUNTRY_SIZE * c
        for i, w in enumerate(squad_words(c)):
            st.put_word(base + 2 * i, w)
        st.put(base + 0x2D, bytes([tac]))
        st.put(base + 0x2E, bytes([man]))
    # the player records
    positions = positions or {}
    player_byte_overrides = player_byte_overrides or {}
    for c in (C0, C1):
        for w in squad_words(c):
            st.put(PLAYERS_ADDR + players.PLAYER_SIZE * w,
                   _player_record(positions.get(w, 5),
                                  byte_overrides=player_byte_overrides.get(w)))
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


# [designed] Squad layout for country C0: slot 3 (word 23) is the first qualifying
# player (code 9), slot 7 (word 27) the second (code 10), slot 9 (word 29) is the
# squad[8] C01A reads (C0A9-C0BB). 23 % 12 = 11 and 27 % 12 = 3 index the 2FAD height
# table. The BEC7 matrix below exercises each control of the conversion flow:
# the slot-9 gate in c01a (BEC7Slot9PositionGate), the unavailable-skip in bec7
# (BEC7FirstAvailable), the height calculation in two_fad with both tables contributing
# (BEC7HeightBothContributions), and the 230C re-sort after the conversion
# (BEC7ReSortAfterConversion). Each class is the parameterised equivalent of the single
# case DW8 had pinned: an R<n> mutation that removes the control fails at least one test
# in the corresponding class.
_SLOT3, _SLOT7, _SLOT9 = 23, 27, 29


class BEC7Slot9PositionGate(unittest.TestCase):
    """[confirmed: F028 (E028)] C01A's slot-9 gate: BEC7/230C run only when the slot-9
    player's position is outside {12, 13}. Each test sets slot 9 to a member of {12, 13}
    and provides an eligible code-9/10/11 candidate further down the squad; the
    candidate must NOT be converted, proving the gate is enforced.

    [designed] The R1 mutation — replacing the gate with `if True` — would call BEC7
    unconditionally, converting SLOT3 in both cases. The assertions below catch that.
    """

    def _match(self, slot9_position, slot3_height=0x48):
        two_fad_a = [0] * 12
        two_fad_a[_SLOT3 % 12] = slot3_height
        return new_match(positions={_SLOT3: 9, _SLOT7: 10, _SLOT9: slot9_position},
                         two_fad_a=two_fad_a)

    def test_slot9_pos_12_blocks_bec7(self):
        """Slot 9 already at code 12: the gate suppresses BEC7, SLOT3 stays at 9.

        [designed] SLOT9 itself is at 12 by setup, so the "converted" check counts
        only SLOT3 and SLOT7 (the BEC7 candidates) — none of those flipped to 12/13."""
        qm = self._match(slot9_position=12)
        qm.score = [0, 3]
        qm.c173()
        self.assertEqual(qm.playerrec[_SLOT3][6], 9)    # untouched (gate held)
        self.assertEqual(qm.playerrec[_SLOT7][6], 10)
        for w in (_SLOT3, _SLOT7):
            self.assertNotIn(qm.playerrec[w][6], {12, 13})

    def test_slot9_pos_13_blocks_bec7(self):
        """Slot 9 already at code 13: the gate suppresses BEC7, SLOT3 stays at 9."""
        qm = self._match(slot9_position=13)
        qm.score = [0, 3]
        qm.c173()
        self.assertEqual(qm.playerrec[_SLOT3][6], 9)    # untouched (gate held)
        self.assertEqual(qm.playerrec[_SLOT7][6], 10)
        for w in (_SLOT3, _SLOT7):
            self.assertNotIn(qm.playerrec[w][6], {12, 13})


class BEC7FirstAvailable(unittest.TestCase):
    """[confirmed: vendored quick_engine.py at 8760df9] BEC7's `if self.unavailable(w):
    continue` skip: when an unavailable code-9/10/11 squad member sits BEFORE an available
    candidate, BEC7 MUST skip the unavailable player and convert the first AVAILABLE
    candidate, not the first matching code (BF56 is the only write, BF5A the only break).

    [designed] The R2 mutation — removing the `unavailable` skip — would convert the
    unavailable SLOT3 (first matching), leaving SLOT7 untouched. The assertions below
    catch that.
    """

    def _match(self, height_slot3=0x48, height_slot7=0x48,
               slot3_unavailable=False):
        two_fad_a = [0] * 12
        two_fad_a[_SLOT3 % 12] = height_slot3
        two_fad_a[_SLOT7 % 12] = height_slot7
        overrides = {_SLOT3: {0xE: 0}} if slot3_unavailable else None
        return new_match(positions={_SLOT3: 9, _SLOT7: 10, _SLOT9: 5},
                         two_fad_a=two_fad_a,
                         player_byte_overrides=overrides)

    def test_unavailable_first_skipped_available_second_converted(self):
        """SLOT3 (first qualifying code-9) is unavailable; SLOT7 (second qualifying
        code-10) is available. BEC7 must convert SLOT7, not SLOT3."""
        qm = self._match(slot3_unavailable=True)
        qm.score = [0, 3]
        qm.c173()
        self.assertEqual(qm.playerrec[_SLOT3][6], 9)    # untouched (unavailable, skipped)
        self.assertEqual(qm.playerrec[_SLOT7][6], 12)   # FIRST AVAILABLE: converted
        converted = [w for w in squad_words(C0) if qm.playerrec[w][6] in {12, 13}]
        self.assertEqual(converted, [_SLOT7])


class BEC7HeightBothContributions(unittest.TestCase):
    """[confirmed: vendored quick_engine.py at 8760df9] 1771:2FAD's
    `E54[w % 12] + E46[+7]` uses BOTH the per-(word mod 12) table and the per-(+7)
    table. The class doc-tests variants in two dimensions: which table contributes and
    whether the total is at or just below 0x48. The +0x54 table contributes non-zero in
    one boundary case, the +0x46 table contributes non-zero in the other.

    [designed] The R3 mutation — replacing the body with only `self.t_2fad_a[w % 12]`
    — would make the total depend solely on the +0x54 table. The "two_fad_a below,
    two_fad_b picks up to 0x48" case below catches that (with the mutation the total
    stays at 0x40, so the assertion `qm.playerrec[SLOT3][6] == 12` fails)."""

    def _match(self, two_fad_a, two_fad_b=None):
        if two_fad_b is None:
            two_fad_b = [0] * 16
        return new_match(positions={_SLOT3: 9, _SLOT7: 10, _SLOT9: 5},
                         two_fad_a=two_fad_a,
                         two_fad_b=two_fad_b)

    def test_two_fad_a_alone_at_0x48_becomes_12(self):
        """Height exactly 0x48 (the boundary the BEC7 docstring asserts) -> code 12.
        +0x54 contributes 0x48 alone; +0x46 contributes 0."""
        two_fad_a = [0] * 12
        two_fad_a[_SLOT3 % 12] = 0x48
        qm = self._match(two_fad_a)
        qm.score = [0, 3]
        qm.c173()
        self.assertEqual(qm.playerrec[_SLOT3][6], 12)
        self.assertEqual(qm.playerrec[_SLOT7][6], 10)  # untouched
        converted = [w for w in squad_words(C0) if qm.playerrec[w][6] in {12, 13}]
        self.assertEqual(converted, [_SLOT3])

    def test_two_fad_a_alone_below_0x48_becomes_13(self):
        """Height 0x47, one below the boundary, -> code 13; the second player
        untouched. +0x54 alone reaches 0x47."""
        two_fad_a = [0] * 12
        two_fad_a[_SLOT3 % 12] = 0x47
        qm = self._match(two_fad_a)
        qm.score = [0, 3]
        qm.c173()
        self.assertEqual(qm.playerrec[_SLOT3][6], 13)
        self.assertEqual(qm.playerrec[_SLOT7][6], 10)  # untouched
        converted = [w for w in squad_words(C0) if qm.playerrec[w][6] in {12, 13}]
        self.assertEqual(converted, [_SLOT3])

    def test_two_fad_a_and_two_fad_b_both_contribute_to_cross_0x48(self):
        """+0x54 alone is 0x40 (below the boundary); +0x46 contributes 0x08; the sum
        crosses to 0x48 -> code 12. With the R3 mutation (drop +0x46) the total stays
        at 0x40 -> code 13, failing the assertion."""
        two_fad_a = [0] * 12
        two_fad_a[_SLOT3 % 12] = 0x40
        two_fad_b = [0] * 16
        two_fad_b[1] = 0x08                                # +7 = 1 for stub players
        qm = self._match(two_fad_a, two_fad_b)
        qm.score = [0, 3]
        qm.c173()
        self.assertEqual(qm.playerrec[_SLOT3][6], 12)
        self.assertEqual(qm.playerrec[_SLOT7][6], 10)
        converted = [w for w in squad_words(C0) if qm.playerrec[w][6] in {12, 13}]
        self.assertEqual(converted, [_SLOT3])

    def test_two_fad_a_and_two_fad_b_both_contribute_stay_below_0x48(self):
        """+0x54 alone is 0x40; +0x46 contributes 0x07; the sum is 0x47 (just below
        the boundary) -> code 13. Confirms the +0x46 contribution is added, not ORed
        in: removing it makes the total 0x40 (also below 0x48) but for a different
        reason — the boundary visit is what the prior assertion needs."""
        two_fad_a = [0] * 12
        two_fad_a[_SLOT3 % 12] = 0x40
        two_fad_b = [0] * 16
        two_fad_b[1] = 0x07
        qm = self._match(two_fad_a, two_fad_b)
        qm.score = [0, 3]
        qm.c173()
        self.assertEqual(qm.playerrec[_SLOT3][6], 13)
        self.assertEqual(qm.playerrec[_SLOT7][6], 10)
        converted = [w for w in squad_words(C0) if qm.playerrec[w][6] in {12, 13}]
        self.assertEqual(converted, [_SLOT3])

    def test_overlapping_bits_at_0x40_plus_0x40_crosses_0x48(self):
        """[designed] Both tables contribute 0x40 to the same slot — `0x40 + 0x40 = 0x80`,
        which crosses the 0x48 boundary, so the player converts to 12. The
        `two_fad -> two_fad_a | two_fad_b` mutation ORs the overlapping bits,
        yielding 0x40 (< 0x48), leaving the player at code 9 (no conversion). The
        prior height cases used disjoint set bits (0x40 vs 0x07 / 0x08), so the
        `+` vs `|` mutations gave the same total — this case with overlapping bits
        is what pins the docstring's "added, not ORed" claim."""
        two_fad_a = [0] * 12
        two_fad_a[_SLOT3 % 12] = 0x40
        two_fad_b = [0] * 16
        two_fad_b[1] = 0x40                                # +7 = 1 for stub players
        qm = self._match(two_fad_a, two_fad_b)
        qm.score = [0, 3]
        qm.c173()
        self.assertEqual(qm.playerrec[_SLOT3][6], 12)
        self.assertEqual(qm.playerrec[_SLOT7][6], 10)  # untouched
        converted = [w for w in squad_words(C0) if qm.playerrec[w][6] in {12, 13}]
        self.assertEqual(converted, [_SLOT3])


class BEC7ReSortAfterConversion(unittest.TestCase):
    """[confirmed: vendored quick_engine.py at 8760df9] C01A calls BEC7 then
    `apply_230c()`: the 230C re-sort moves the BEC7-converted player up the pitch order
    so its squad slot reflects the new position. Without apply_230c the squad/pitch
    order stays in its pre-conversion layout (SLOT3 still at squad[2] / pitch[14]).

    [designed] The R4 mutation — removing `self.apply_230c()` after BEC7 — leaves
    the pitch and squad order untouched. The assertions below catch that: the
    converted player (position 12, the highest) must be at squad[10] (the back of the
    trailing side's pitch) and at pitch[22] (the highest pitch slot for the trailing
    side), and the original slot for SLOT3 must hold a different player.
    """

    def _match(self, slot3_height=0x48):
        two_fad_a = [0] * 12
        two_fad_a[_SLOT3 % 12] = slot3_height
        return new_match(positions={_SLOT3: 9, _SLOT7: 10, _SLOT9: 5},
                         two_fad_a=two_fad_a)

    def test_apply_230c_moves_converted_player_to_back_of_pitch(self):
        """SLOT3 becomes code 12 (the highest position key); apply_230c's pitch sort
        (jb at 23B2) bubbles it to the back of the trailing side's pitch slots
        (12..22)."""
        qm = self._match()
        qm.score = [0, 3]
        qm.c173()
        # The trailing side is teams[0] = C0; its pitch slots are side_base[0] + 1..+11
        # = 12..22.
        self.assertEqual(qm._country(C0)["squad"][10], _SLOT3)  # squad slot = position
        self.assertEqual(qm.pitch[22]["player"], _SLOT3)         # pitch slot 22 holds it
        self.assertNotEqual(qm.pitch[14]["player"], _SLOT3)      # original slot vacated
        # SLOT7 (position 10, the second-highest) is now at the slot just before 22.
        self.assertEqual(qm._country(C0)["squad"][9], _SLOT7)
        self.assertEqual(qm.pitch[21]["player"], _SLOT7)

    def test_apply_230c_keeps_pitch_aligned_with_squad(self):
        """[designed] For every pitch slot on the trailing side, the pitch's player
        equals the squad word at the corresponding index — AND the sort moved at
        least one player on the trailing side. Without `apply_230c` the alignment
        holds but no swap happens, so the pre/post arrays match; the companion
        `test_apply_230c_moves_converted_player_to_back_of_pitch` covers specific
        slot positions, this one is the corresponding claim about the array as a
        whole."""
        qm = self._match()
        base = qm.side_base[0]
        pre_pitch = [qm.pitch[base + 1 + i]["player"] for i in range(11)]
        qm.score = [0, 3]
        qm.c173()
        # Alignment after the 2218 swap at 23C4.
        squad = qm._country(C0)["squad"]
        for i, slot in enumerate(range(base + 1, base + 12)):
            self.assertEqual(qm.pitch[slot]["player"], squad[i])
        # The 230C re-sort MUST have moved at least one player; without
        # apply_230c the post-state array equals the pre-state array.
        post_pitch = [qm.pitch[base + 1 + i]["player"] for i in range(11)]
        self.assertNotEqual(pre_pitch, post_pitch)


if __name__ == "__main__":
    unittest.main()