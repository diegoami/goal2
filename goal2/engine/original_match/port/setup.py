"""The per-match set-up (T70, route C step P5c): match_setup 0791:A4A1 and what it reaches, the 16 routines of row T70.

Translated instruction by instruction from static/goal-exe/code/seg_0791_02.asm (1073-112B), seg_0791_04.asm
(2648-269F), seg_0791_17.asm (A375-A698, A6E4-A75C, A841-A91F, AC67-AD0E), seg_0791_18.asm (AD8F-B15E),
seg_0791_21.asm (D44C-D47D), seg_1771_07.asm (517A-52CB) and seg_1771_08.asm (52CC-53E7, 580B-59B7), after the named
view (named/seg_0791_*.c, named/seg_1771_*.c) and the annotation rows (F005, F010, F012, F020, F024, F027); the line
comments are the listing's offsets. As T65's to T68's modules, the routines are written in the registers the listing
uses (runtime.Regs), so the words they push for their callees (a byte pushed with `mov al, n; push ax` keeps the AH of
the instruction before), the words held on the guest stack across a call and the locals of the frames are the
original's (notes.md rule 2a).

Every call of the listing stays a guest call with its target, arguments, return address and near/far form, between these
routines too (so each is counted and run as its own port) and to the callees of other rows: T68's initialize_pitch_player
A2E6, the bench pickers A9B8 and AAE8 and computer_tactic_change BD83; T69's resort_pitch_and_bench 230C; T64's
find_nearest_to_ball 2FB1; T73's screen work (the draw_score 0712, the screen unpacker 214B:0329 and the string writer
214B:02C8); T61's 1771 player routines (0B77, 3179, 3216, 34E7, 377E, 5A03); the runtime of 214B and 23E4 (the fills
214B:0018, the move 214B:003C, the swap 214B:007B, the upcase 214B:009C, the draws 214B:06B1 and 06FA, the set test
23E4:08DF, the string store 23E4:0644).

What the set-up writes into the pitch picture (A841's 214B:003C into [DS:7C1E]) is engine state and stays; what it
draws is the callees' (T73). The kit's two inputs around the set-up stay where they are: the seed it writes at the
captain prompt comes after 2648's reseed, and goal2's substitution budget is written when play_match starts, after
A4A1's (A605).

The nested routines read their parent's frame through its BP, as the listing does: AC67, AD8F and AFA3 read B11F's
country word (`mov di, [bp + 4]; ss:[di + 6]`) and its bench slot local (`ss:[di - 2]`, which AFA3 writes); 517A reads
52CC's country word and swaps 52CC's saved position bytes ([bp + i - 0x15] of 52CC's frame) along with the squad words.

The Pascal string functions leave their result pointer on the stack (580B `retf 2`, 214B:009C `retf 4`), which a guest
call cannot express: the port pushes those words itself, and the next call takes them as its first arguments, writing
the same words at the same place (T61's and T68's way)."""
from . import Registry
from .contests import ss16, ss8, pop
from .geometry import cbw, mul
from .guest import call
from .restarts import _end
from .runtime import Regs

PORTS = Registry("setup", "the per-match set-up: A4A1 and what it reaches, 1073, 2648, A375-A4A1, A6E4, A841, "
                          "AC67-B11F, D44C, 1771:517A, 52CC, 580B, row T70's 16 routines (T70)")
PORTS.variant("seed-year-not-incremented", "2648 at 2669: the seed is index * year, the `inc ax` dropped")
PORTS.variant("budget-kind-inverted", "A4A1 at A54C: DS:9A3D := 1 for a friendly (kind 1) and 0 for the others")
PORTS.variant("sort-bytes-unswapped", "517A at 5288: the saved position bytes are not swapped with the words (no "
                                      "214B:007B)")
PORTS.variant("bench-tie-replaces", "AC67 at ACF5: a bench player of equal strength replaces the earlier one (`jbe` "
                                    "read as `jb`)")
M16 = 0xFFFF
ZF = 0x40                       # EFLAGS' zero flag: 23E4:08DF's answer (`test byte ptr es:[bx + di], al`)


# -- the listing's idioms ------------------------------------------------------------------------------------------
def guest(mem, r, target, *args, ret, far=True):
    """The call of the listing: registers and stack stored, the guest runs the callee; the registers it leaves. `ret`
    is the return address, in 0791 unless it names its segment (1771's routines)."""
    r.store(stack=True)
    yield call(target if ":" in target else f"0791:{target}", *args,
               ret_to=ret if ":" in ret else f"0791:{ret}", far=far)
    return Regs(mem, resumed=True)


def member(mem):
    """After 23E4:08DF: the element is in the set (ZF clear, the listing's `jne`)."""
    return not (mem.reg("eflags") & ZF)


def farg(mem, r, k):
    """`les di, ptr [bp + k]`: a far pointer argument."""
    r.es, r.di = ss16(mem, r, r.bp + k + 2), ss16(mem, r, r.bp + k)
    return r.es, r.di


def ss_w16(r, off, value):
    """`mov word ptr ss:[off], value`: a word of another frame (the parent's), written in order with the stack."""
    r._put(off, (value & M16).to_bytes(2, "little"))


def wd8(mem, off, value, at):
    mem.wds8(off & M16, value & 0xFF, f"0791:{at}")


def wd16(mem, off, value, at):
    mem.wds16(off & M16, value & M16, f"0791:{at}")


def w8(mem, r, k, value, at):
    """`mov byte ptr es:[di + k], value`, as the listing's instruction `at` ('SSSS:OOOO' or a 0791 offset)."""
    mem.w8(mem.addr(r.es, r.di + k), value & 0xFF, at if ":" in at else f"0791:{at}")


def w16(mem, r, k, value, at):
    mem.w16(mem.addr(r.es, r.di + k), value & M16, at if ":" in at else f"0791:{at}")


def rb(mem, r, k):
    return mem.u8(mem.addr(r.es, r.di + k))


def rw(mem, r, k):
    return mem.u16(mem.addr(r.es, r.di + k))


def squad_of(mem, r, country):
    """`mov ax, country; mov dx, 0xbf; mul dx; les di, [0xa917]; add di, ax`: the country record (its squad words)."""
    r.ax = country
    r.dx = 0xBF
    mul(r, r.dx)
    r.di, r.es = mem.ds16(0xA917), mem.ds16(0xA919)
    r.di = r.di + r.ax
    return r.es, r.di


def player_of(mem, r, word):
    """`mov ax, word; mov dx, 0x14; mul dx; les di, [0xa91b]; add di, ax`: the player record of the word."""
    r.ax = word
    r.dx = 0x14
    mul(r, r.dx)
    r.di, r.es = mem.ds16(0xA91B), mem.ds16(0xA91D)
    r.di = r.di + r.ax
    return r.es, r.di


def squad_word(mem, r, seg, off, k):
    """`mov ax, k; shl ax, 1; les di, [squad]; add di, ax; mov ax, es:[di - 2]`: squad word k (1-based)."""
    r.ax = k << 1
    r.es, r.di = seg, off
    r.di = r.di + r.ax
    r.ax = rw(mem, r, -2)
    return r.ax


def player_at(mem, r, seg, off, k):
    """Squad word k's player record (`... mov ax, es:[di - 2]; mov dx, 0x14; mul dx; les di, [0xa91b]; add di, ax`)."""
    word = squad_word(mem, r, seg, off, k)
    return player_of(mem, r, word)


def fill(mem, r, off, n, value, ret):
    """`mov di, off; push ds; push di; mov ax, n; push ax; (xor ax, ax | mov ax, value); push ax; call far 214B:0018`."""
    r.di = off
    r.ax = n
    r.ax = value
    return (yield from guest(mem, r, "214B:0018", mem.DS, off, n, value, ret=ret))


# -- 1073 ----------------------------------------------------------------------------------------------------------
@PORTS.port("0791:1073", ret="ret")
def kit_colours(mem, variant):
    """1073-112B: the two sides' kit colours DS:832E (team 0's shirt), 832F (team 1's), 8330, 8331 (their second
    colours): with DS:A964 set the fixed 4, 1, 0xC, 9; else from each country's three bytes DS:9D80 + 3 country (+0,
    +2), and team 0 takes its third byte (+1) for a colour equal to team 1's shirt (832E first, else 8330), then team
    1 its third byte for its second colour 8331 equal to team 0's shirt."""
    r = Regs(mem)
    r.enter()                                                    # 1073-1074
    if mem.ds8(0xA964) != 0:                                     # 1076 cmp byte ptr [0xa964], 0; je 1094
        wd8(mem, 0x832F, 1, "107D")
        wd8(mem, 0x832E, 4, "1082")
        wd8(mem, 0x8331, 9, "1087")
        wd8(mem, 0x8330, 0xC, "108C")
        return _end(r)                                           # 1091 jmp 1128

    def kit(word, k):
        """`mov ax, [word]; mov dx, 3; mul dx; mov di, ax; mov al, [di + 0x9d80 + k]`."""
        r.ax = mem.ds16(word)
        r.dx = 3
        mul(r, r.dx)
        r.di = r.ax
        r.al = mem.ds8((r.di + 0x9D80 + k) & M16)
        return r.al
    wd8(mem, 0x832F, kit(0x9B36, 0), "10A2")                     # 1094-10A2
    wd8(mem, 0x8331, kit(0x9B36, 2), "10B3")                     # 10A5-10B3
    wd8(mem, 0x832E, kit(0x9B34, 0), "10C4")                     # 10B6-10C4
    wd8(mem, 0x8330, kit(0x9B34, 2), "10D5")                     # 10C7-10D5
    r.al = mem.ds8(0x832F)                                       # 10D8
    if r.al == mem.ds8(0x832E):                                  # 10DB cmp al, [0x832e]; jne 10F4
        wd8(mem, 0x832E, kit(0x9B34, 1), "10EF")                 # 10E1-10EF
    else:
        r.al = mem.ds8(0x832F)                                   # 10F4
        if r.al == mem.ds8(0x8330):                              # 10F7 cmp al, [0x8330]; jne 110E
            wd8(mem, 0x8330, kit(0x9B34, 1), "110B")             # 10FD-110B
    r.al = mem.ds8(0x832E)                                       # 110E
    if r.al == mem.ds8(0x8331):                                  # 1111 cmp al, [0x8331]; jne 1128
        wd8(mem, 0x8331, kit(0x9B36, 1), "1125")                 # 1117-1125
    return _end(r)


# -- 2648 ----------------------------------------------------------------------------------------------------------
@PORTS.port("0791:2648", ret="ret")
def reseed(mem, variant):
    """2648-269F: the main RNG word [DS:A978] := (index [A923]+0x26) * (year [A923]+0x38 + 1); the foul draw table
    DS:8337 + k := rand(0x10) - 1 (214B:06B1) for k = 1..0xFF; its index DS:8437 := DS:9B36."""
    r = Regs(mem)
    r.enter(8)                                                   # 2648-264B
    r.di, r.es = mem.ds16(0xA923), mem.ds16(0xA925)              # 264E les di, ptr [0xa923]
    r.local16(-8, r.di)                                          # 2652
    r.local16(-6, r.es)                                          # 2655
    r.ax = rw(mem, r, 0x26)                                      # 265B
    index = r.ax
    r.local16(-4, index)                                         # 265F
    r.ax = rw(mem, r, 0x38)                                      # 2665
    if variant != "seed-year-not-incremented":
        r.ax = r.ax + 1                                          # 2669 inc ax
    mul(r, index)                                                # 266A mul word ptr [bp - 4]
    r.di, r.es = mem.ds16(0xA978), mem.ds16(0xA97A)              # 266D les di, ptr [0xa978]
    w16(mem, r, 0, r.ax, "2671")
    k = 1
    r.local16(-2, k)                                             # 2674
    while True:
        r.ax = 0x10                                              # 267E
        r = yield from guest(mem, r, "214B:06B1", 0x10, ret="2687")
        r.ax = r.ax - 1                                          # 2687 dec ax
        r.di = k                                                 # 2688
        wd8(mem, r.di + 0x8337, r.al, "268B")                    # [di - 0x7cc9]
        if k == 0xFF:                                            # 268F cmp word ptr [bp - 2], 0xff; jne 267B
            break
        k += 1
        r.local16(-2, k)                                         # 267B inc word ptr [bp - 2]
    r.ax = mem.ds16(0x9B36)                                      # 2696
    wd16(mem, 0x8437, r.ax, "2699")
    return _end(r)


# -- A375, A3B6 ----------------------------------------------------------------------------------------------------
@PORTS.port("0791:A375", ret="retf 4")
def init_ball_record(mem, variant):
    """A375-A3B3 (the record [bp+6]): +0xA := 0, +4 := 0x0F07, +0xC := 0, +0xD := 0, +0 := DS:0640, +2 := +0."""
    r = Regs(mem)
    r.enter()                                                    # A375-A376
    farg(mem, r, 6)                                              # A378
    r.ax = 0                                                     # A37B
    w16(mem, r, 0xA, r.ax, "A37D")
    w16(mem, r, 4, 0xF07, "A384")
    w8(mem, r, 0xC, 0, "A38D")
    w8(mem, r, 0xD, 0, "A395")
    r.ax = mem.ds16(0x640)                                       # A39A
    w16(mem, r, 0, r.ax, "A3A0")
    r.ax = rw(mem, r, 0)                                         # A3A6
    w16(mem, r, 2, r.ax, "A3AC")
    return _end(r)


@PORTS.port("0791:A3B6", ret="retf 4")
def init_point_record(mem, variant):
    """A3B6-A3DB (the record [bp+6]): +4 := 0x0D01, +0 := DS:0644, +2 := +0."""
    r = Regs(mem)
    r.enter()                                                    # A3B6-A3B7
    farg(mem, r, 6)                                              # A3B9
    w16(mem, r, 4, 0xD01, "A3BC")
    r.ax = mem.ds16(0x644)                                       # A3C2
    w16(mem, r, 0, r.ax, "A3C8")
    r.ax = rw(mem, r, 0)                                         # A3CE
    w16(mem, r, 2, r.ax, "A3D4")
    return _end(r)


# -- A3DE ----------------------------------------------------------------------------------------------------------
@PORTS.port("0791:A3DE", ret="ret 4")
def prepare_computer_sides(mem, variant):
    """A3DE-A49E (the fixture [bp+4]): DS:9B34, 9B36 := its countries (+4, +6); DS:7C36 := its kind (+2) in the
    decider set DS:693A (23E4:08DF); DS:80FC := D44C (the second team is the host); DS:9976 := +1; DS:7C2A := the
    fixture's far pointer; the reseed 2648; DS:9B3C := 0 (the score); then for side 0 and 1, a side 1771:0B77 calls
    unmanaged gets its eleven (B11F), its own tactics re-derived (1771:34E7) and its tactic change (BD83)."""
    r = Regs(mem)
    r.enter(6)                                                   # A3DE-A3E1
    seg, off = farg(mem, r, 4)                                   # A3E4
    r.local16(-5, off)                                           # A3E7
    r.local16(-3, seg)                                           # A3EA
    r.ax, r.es = rw(mem, r, 4), rw(mem, r, 6)                    # A3F0 les ax, ptr es:[di + 4]
    r.dx = r.es                                                  # A3F4
    wd16(mem, 0x9B34, r.ax, "A3F6")
    wd16(mem, 0x9B36, r.dx, "A3F9")
    r.es, r.di = seg, off                                        # A3FD
    r.al = rb(mem, r, 2)                                         # A400
    r.di = 0x693A                                                # A405
    r = yield from guest(mem, r, "23E4:08DF", r.ax, mem.DS, 0x693A, ret="A40F")
    r.al = 1 if member(mem) else 0                               # A40F jne A415; mov al, 0 / mov al, 1
    wd8(mem, 0x7C36, r.al, "A417")
    farg(mem, r, 4)                                              # A41A
    r = yield from guest(mem, r, "D44C", seg, off, ret="A423")
    wd8(mem, 0x80FC, r.al, "A423")
    r.es, r.di = seg, off                                        # A426
    r.al = rb(mem, r, 1)                                         # A429
    wd8(mem, 0x9976, r.al, "A42D")
    farg(mem, r, 4)                                              # A430
    r.ax = r.di                                                  # A433
    r.dx = r.es                                                  # A435
    wd16(mem, 0x7C2A, r.ax, "A437")
    wd16(mem, 0x7C2C, r.dx, "A43A")
    r = yield from guest(mem, r, "2648", ret="A441", far=False)
    r.ax = 0                                                     # A441
    wd16(mem, 0x9B3C, r.ax, "A443")
    side = 0
    r.local8(-1, side)                                           # A446
    while True:
        def country():
            """`mov al, [bp - 1]; cwde; shl ax, 1; les di, [bp - 5]; add di, ax`; the word es:[di + 4]."""
            r.al = side
            cbw(r)
            r.ax = r.ax << 1
            r.es, r.di = seg, off
            r.di = r.di + r.ax
            return rw(mem, r, 4)
        r = yield from guest(mem, r, "1771:0B77", country(), ret="A463")
        if r.al == 0:                                            # A463 or al, al; jne A495
            r = yield from guest(mem, r, "B11F", country(), ret="A47A")
            r = yield from guest(mem, r, "1771:34E7", country(), ret="A48E")
            r.al = side                                          # A48E
            r = yield from guest(mem, r, "BD83", r.ax, ret="A495", far=False)
        if side == 1:                                            # A495 cmp byte ptr [bp - 1], 1; jne A44C
            break
        side += 1
        r.local8(-1, side)                                       # A44C inc byte ptr [bp - 1]
    return _end(r)


# -- A4A1 ----------------------------------------------------------------------------------------------------------
@PORTS.port("0791:A4A1", ret="ret 4")
def match_setup(mem, variant):
    """A4A1-A696 (the fixture [bp+4]): the computer sides (A3DE); DS:832C := 0xFFFF; the kit colours (1073); the
    per-match state cleared (214B:0018: DS:9B08 0x28 bytes, 7C3E 0x4B0 bytes of 0xFF, the statistics 7B7E 0x14,
    7BD4 0x42, 80F2 4, 80F6 4, 9A40 0x50; the words 7C3A, 8332, 8334 and the ring counter 80EE); DS:9A3D := the kind
    (+2) is not 1; DS:831A := the coin (214B:06FA); the ball (A375 on DS:82F6) and the points DS:82EE, 8304 (A3B6); the
    22 pitch records (A2E6(slot) on DS:80E8 + 0x16 slot); for each side DS:80F0 + side := 0, the point DS:82E2 + 6
    side (A3B6) and the budget DS:9B3A + side := DS:066B[DS:9A3D] (A605); 230C and 2FB1; the clock and the play state
    cleared; DS:80FD := either side managed (1771:0B77); DS:9978 0x14 bytes cleared; the screen (A841)."""
    r = Regs(mem)
    r.enter(4)                                                   # A4A1-A4A4
    seg, off = farg(mem, r, 4)                                   # A4A7
    r = yield from guest(mem, r, "A3DE", seg, off, ret="A4AF", far=False)
    wd16(mem, 0x832C, 0xFFFF, "A4AF")
    r = yield from guest(mem, r, "1073", ret="A4B8", far=False)
    r = yield from fill(mem, r, 0x9B08, 0x28, 0, "A4C9")
    r.ax = 0
    for word, at in ((0x7C3A, "A4CB"), (0x8332, "A4D0"), (0x8334, "A4D5"), (0x80EE, "A4DA")):
        wd16(mem, word, 0, at)                                   # xor ax, ax; mov word ptr [word], ax
    r = yield from fill(mem, r, 0x7C3E, 0x4B0, 0xFF, "A4EF")
    r = yield from fill(mem, r, 0x7B7E, 0x14, 0, "A500")
    r = yield from fill(mem, r, 0x7BD4, 0x42, 0, "A511")
    r = yield from fill(mem, r, 0x80F2, 4, 0, "A522")
    r = yield from fill(mem, r, 0x80F6, 4, 0, "A533")
    r = yield from fill(mem, r, 0x9A40, 0x50, 0, "A544")
    farg(mem, r, 4)                                              # A544
    friendly = rb(mem, r, 2) == 1                                # A547 cmp byte ptr es:[di + 2], 1; jne A552
    if variant == "budget-kind-inverted":
        friendly = not friendly
    r.al = 0 if friendly else 1                                  # A54E / A552
    wd8(mem, 0x9A3D, r.al, "A554")
    r = yield from guest(mem, r, "214B:06FA", ret="A55C")
    wd8(mem, 0x831A, r.al, "A55C")
    for byte, at in ((0x830C, "A55F"), (0x830E, "A564"), (0x830D, "A569"), (0x80FA, "A56E"), (0x7C39, "A573")):
        wd8(mem, byte, 0, at)
    r.di = 0x82F6                                                # A578
    r = yield from guest(mem, r, "A375", mem.DS, 0x82F6, ret="A581")
    r.di = 0x82EE                                                # A581
    r = yield from guest(mem, r, "A3B6", mem.DS, 0x82EE, ret="A58A")
    r.di = 0x8304                                                # A58A
    r = yield from guest(mem, r, "A3B6", mem.DS, 0x8304, ret="A593")
    k = 1
    r.local16(-2, k)                                             # A593
    while True:
        r.ax = k                                                 # A5A0
        r.dx = 0x16
        mul(r, r.dx)
        r.di = r.ax + 0x80E8                                     # A5A8-A5AA
        r = yield from guest(mem, r, "A2E6", k, mem.DS, r.di, ret="A5B4")
        if k == 0x16:                                            # A5B4 cmp word ptr [bp - 2], 0x16; jne A59A
            break
        k += 1
        r.local16(-2, k)                                         # A59A inc word ptr [bp - 2]
    wd8(mem, 0x0C1F, 0, "A5BA")
    wd8(mem, 0x8326, 0, "A5BF")
    wd8(mem, 0x9B41, 1, "A5C4")
    side = 0
    r.local8(-3, side)                                           # A5C9
    while True:
        r.al = side                                              # A5D2
        cbw(r)
        r.di = r.ax
        wd8(mem, r.di + 0x80F0, 0, "A5D8")                       # [di - 0x7f10]
        r.al = side                                              # A5DD
        cbw(r)
        r.di = r.ax
        r.di = r.di << 1                                         # A5E3
        r.si = r.di
        r.di = r.di << 1
        r.di = r.di + r.si
        r.di = r.di + 0x82E2                                     # A5EB
        r = yield from guest(mem, r, "A3B6", mem.DS, r.di, ret="A5F5")
        r.al = mem.ds8(0x9A3D)                                   # A5F5
        cbw(r)
        r.di = r.ax
        r.dx = (r.dx & 0xFF00) | mem.ds8((r.di + 0x66B) & M16)   # A5FB mov dl, byte ptr [di + 0x66b]
        r.al = side                                              # A5FF
        cbw(r)
        r.di = r.ax
        wd8(mem, r.di + 0x9B3A, r.dx, "A605")                    # [di - 0x64c6]: the budget
        if side == 1:                                            # A609 cmp byte ptr [bp - 3], 1; jne A5CF
            break
        side += 1
        r.local8(-3, side)                                       # A5CF inc byte ptr [bp - 3]
    r = yield from guest(mem, r, "230C", ret="A612", far=False)
    r = yield from guest(mem, r, "2FB1", ret="A615", far=False)
    wd8(mem, 0x9B40, 0, "A615")
    r.ax = 0
    wd16(mem, 0x831D, 0, "A61C")
    wd16(mem, 0x831F, 0, "A621")
    wd16(mem, 0x8321, 0, "A626")
    for byte, at in ((0x8325, "A629"), (0x8324, "A62E"), (0x8327, "A633"), (0x8328, "A638")):
        wd8(mem, byte, 0, at)
    wd16(mem, 0x832A, 0x64, "A63D")
    r = yield from guest(mem, r, "1771:0B77", mem.ds16(0x9B36), ret="A64C")
    managed = r.al != 0                                          # A64C or al, al; jne A661
    if not managed:
        r = yield from guest(mem, r, "1771:0B77", mem.ds16(0x9B34), ret="A659")
        managed = r.al != 0                                      # A659 or al, al; jne A661
    r.al = 1 if managed else 0                                   # A65D / A661
    wd8(mem, 0x80FD, r.al, "A663")
    wd8(mem, 0x0C1E, 1, "A666")
    r = yield from fill(mem, r, 0x9978, 0x14, 0, "A67C")
    wd8(mem, 0x9A3E, 0, "A67C")
    wd8(mem, 0x9A3F, 0, "A681")
    r = yield from guest(mem, r, "A841", ret="A689", far=False)
    wd8(mem, 0x7C37, 0, "A689")
    wd8(mem, 0x7C38, 0, "A68E")
    return _end(r)


# -- A6E4, D44C ----------------------------------------------------------------------------------------------------
@PORTS.port("0791:A6E4", ret="ret 4")
def host_country(mem, variant):
    """A6E4-A75A (the fixture [bp+4]): when 1771:5A03 holds for the fixture, the word [A923] + 0x2C + 2 c, c = 5 when
    [A923]+0x40 is set, else the continent byte +0x2C of the fixture's second country; otherwise the second country
    (+6)."""
    r = Regs(mem)
    r.enter(0xC)                                                 # A6E4-A6E7
    seg, off = farg(mem, r, 4)                                   # A6EA
    r.local16(-8, off)                                           # A6ED
    r.local16(-6, seg)                                           # A6F0
    gseg, goff = mem.ds16(0xA925), mem.ds16(0xA923)              # A6F3 les di, ptr [0xa923]
    r.es, r.di = gseg, goff
    r.local16(-0xC, goff)                                        # A6F7
    r.local16(-0xA, gseg)                                        # A6FA
    farg(mem, r, 4)                                              # A6FD
    r = yield from guest(mem, r, "1771:5A03", seg, off, ret="A707")
    if r.al != 0:                                                # A707 or al, al; je A74A
        r.es, r.di = gseg, goff                                  # A70B
        if rb(mem, r, 0x40) != 0:                                # A70E cmp byte ptr es:[di + 0x40], 0; je A71C
            c = 5
            r.local16(-4, c)                                     # A715
        else:
            r.es, r.di = seg, off                                # A71C
            squad_of(mem, r, rw(mem, r, 6))                      # A71F-A72C
            r.al = rb(mem, r, 0x2C)                              # A72E
            r.ah = 0
            c = r.ax
            r.local16(-4, c)                                     # A734
        r.ax = c << 1                                            # A737-A73A
        r.es, r.di = gseg, goff                                  # A73C
        r.di = r.di + r.ax
        r.ax = rw(mem, r, 0x2C)                                  # A741
    else:
        r.es, r.di = seg, off                                    # A74A
        r.ax = rw(mem, r, 6)                                     # A74D
    r.local16(-2, r.ax)                                          # A745 / A751
    return _end(r, value=True)                                   # A754 mov ax, word ptr [bp - 2]


@PORTS.port("0791:D44C", ret="retf 4")
def second_team_is_host(mem, variant):
    """D44C-D47B (the fixture [bp+6]): 1 when A6E4 gives the fixture's second country (+6), else 0."""
    r = Regs(mem)
    r.enter(6)                                                   # D44C-D44F
    seg, off = farg(mem, r, 6)                                   # D452
    r.local16(-5, off)                                           # D455
    r.local16(-3, seg)                                           # D458
    farg(mem, r, 6)                                              # D45B
    r = yield from guest(mem, r, "A6E4", seg, off, ret="D463", far=False)
    r.es, r.di = seg, off                                        # D463
    r.al = 1 if r.ax == rw(mem, r, 6) else 0                     # D466 cmp ax, word ptr es:[di + 6]; je D470
    r.local8(-1, r.al)                                           # D472
    return _end(r, value=True)                                   # D475 mov al, byte ptr [bp - 1]


# -- A841 ----------------------------------------------------------------------------------------------------------
@PORTS.port("0791:A841", ret="ret")
def setup_screen(mem, variant):
    """A841-A91F: the match screen into the back buffer [DS:A96E] (214B:0329 of DS:6192, 613E, 5796), each side's
    country name upper-cased (214B:009C of [DS:9B68] + 0x10 country) in its kit colour DS:832E + side at row 0xE,
    column DS:08CC + side (214B:02C8), the fixture kind's title (1771:580B, upper-cased) in colour 5 at row 0x21,
    column 1, the score (0712); then the buffer copied to the pitch picture [DS:7C1E] (214B:003C, 0xFA0 bytes)."""
    r = Regs(mem)
    r.enter(0x202)                                               # A841-A844
    for src, ret in ((0x6192, "A857"), (0x613E, "A866"), (0x5796, "A875")):
        r.di = src
        r.di = 0xA96E
        r = yield from guest(mem, r, "214B:0329", mem.DS, src, mem.DS, 0xA96E, ret=ret)
    side = 0
    r.local8(-1, side)                                           # A875
    while True:
        r.al = side                                              # A87E
        cbw(r)
        r.di = r.ax
        r.al = mem.ds8((r.di + 0x832E) & M16)                    # A884 [di - 0x7cd2]
        colour = r.ax
        r.push(colour)                                           # A888: 02C8's first argument
        r.di = (r.bp - 0x101) & M16                              # A889 lea di, [bp - 0x101]
        name = r.di
        r.push(r.ss)                                             # A88D: 009C's result, 02C8's string
        r.push(name)
        r.al = side                                              # A88F
        cbw(r)
        r.di = r.ax
        r.di = r.di << 1
        r.ax = mem.ds16((r.di + 0x9B34) & M16)                   # A897
        r.cx = (r.cx & 0xFF00) | 4                               # A89B mov cl, 4
        r.ax = r.ax << 4
        r.di, r.es = mem.ds16(0x9B68), mem.ds16(0x9B6A)          # A89F les di, ptr [0x9b68]
        r.di = r.di + r.ax
        r = yield from guest(mem, r, "214B:009C", r.es, r.di, ret="A8AC")
        r.al = side                                              # A8AC
        cbw(r)
        r.di = r.ax
        r.al = mem.ds8((r.di + 0x8CC) & M16)                     # A8B2
        column = r.ax
        r.al = 0xE                                               # A8B7
        row = r.ax
        r.di = 0xA96E                                            # A8BA
        r.sp = r.sp + 6                                          # the words of A888-A88E are 02C8's first three
        r = yield from guest(mem, r, "214B:02C8", colour, r.ss, name, column, row, mem.DS, 0xA96E, ret="A8C4")
        if side == 1:                                            # A8C4 cmp byte ptr [bp - 1], 1; jne A87B
            break
        side += 1
        r.local8(-1, side)                                       # A87B inc byte ptr [bp - 1]
    r.al = 5                                                     # A8CA
    colour = r.ax
    r.push(colour)                                               # A8CC: 02C8's first argument
    title = (r.bp - 0x201) & M16                                 # A8CD lea di, [bp - 0x201]
    r.push(r.ss)                                                 # A8D1: 009C's result, 02C8's string
    r.push(title)
    kind = (r.bp - 0x101) & M16                                  # A8D3 lea di, [bp - 0x101]
    r.push(r.ss)                                                 # A8D7: 580B's result, 009C's source
    r.push(kind)
    r.di, r.es = mem.ds16(0x7C2A), mem.ds16(0x7C2C)              # A8D9 les di, ptr [0x7c2a]
    r.al = rb(mem, r, 2)                                         # A8DD
    r.ah = 0
    r = yield from guest(mem, r, "1771:580B", r.ax, ret="A8E9")
    r.sp = r.sp + 4                                              # 580B's result is 009C's source
    r = yield from guest(mem, r, "214B:009C", r.ss, kind, ret="A8EE")
    r.al = 1                                                     # A8EE
    column = r.ax
    r.al = 0x21                                                  # A8F1
    row = r.ax
    r.di = 0xA96E                                                # A8F4
    r.sp = r.sp + 6                                              # the words of A8CC-A8D2 are 02C8's first three
    r = yield from guest(mem, r, "214B:02C8", colour, r.ss, title, column, row, mem.DS, 0xA96E, ret="A8FE")
    r.di = 0xA96E                                                # A8FE
    r = yield from guest(mem, r, "0712", mem.DS, 0xA96E, ret="A907")
    bseg, boff = mem.ds16(0xA970), mem.ds16(0xA96E)              # A907 les di, ptr [0xa96e]
    pseg, poff = mem.ds16(0x7C20), mem.ds16(0x7C1E)              # A90D les di, ptr [0x7c1e]
    r.es, r.di = pseg, poff
    r.ax = 0xFA0                                                 # A913
    r = yield from guest(mem, r, "214B:003C", bseg, boff, pseg, poff, 0xFA0, ret="A91C")
    return _end(r)


# -- AC67, AD8F, AFA3, B11F: the computer's eleven ---------------------------------------------------------------
def parent_squad(mem, r):
    """`mov di, [bp + 4]; mov ax, ss:[di + 6]; mov dx, 0xbf; mul dx; les di, [0xa917]; add di, ax`: the squad of the
    parent's (B11F's) country word."""
    r.di = ss16(mem, r, r.bp + 4)
    return squad_of(mem, r, ss16(mem, r, r.di + 6))


def bench_slot(mem, r):
    """`mov di, [bp + 4]; mov ax, ss:[di - 2]`: B11F's local [bp - 2], the bench slot."""
    r.di = ss16(mem, r, r.bp + 4)
    r.ax = ss16(mem, r, r.di - 2)
    return r.ax


@PORTS.port("0791:AC67", ret="ret 4")
def bench_best_for_position(mem, variant):
    """AC67-AD0C (B11F's BP [bp+4], bench slot k [bp+6]): when k's player is available (1771:3216 = 0), DS:99A2 +
    (his +7) := k if that entry is 0 or his strength (1771:377E) is above the stored slot's player's."""
    r = Regs(mem)
    r.enter(0xA)                                                 # AC67-AC6A
    sseg, soff = parent_squad(mem, r)                            # AC6D-AC7D
    r.local16(-6, soff)                                          # AC7F
    r.local16(-4, sseg)                                          # AC82
    k = ss16(mem, r, r.bp + 6)                                   # AC85
    word = squad_word(mem, r, sseg, soff, k)                     # AC88-AC8F
    r.local16(-2, word)                                          # AC93
    pseg, poff = player_of(mem, r, word)                         # AC96-ACA2
    r.local16(-0xA, poff)                                        # ACA4
    r.local16(-8, pseg)                                          # ACA7
    r = yield from guest(mem, r, "1771:3216", word, ret="ACB2")
    if r.al != 0:                                                # ACB2 or al, al; jne AD09
        return _end(r)

    def entry():
        """`les di, [bp - 0xa]; mov al, es:[di + 7]; xor ah, ah; mov di, ax`; the byte [di + 0x99a2]."""
        r.es, r.di = pseg, poff
        r.al = rb(mem, r, 7)
        r.ah = 0
        r.di = r.ax
        return mem.ds8((r.di + 0x99A2) & M16)
    store = True
    if entry() != 0:                                             # ACB6-ACC1 cmp byte ptr [di - 0x665e], 0; je ACF7
        r.al = entry()                                           # ACC8-ACD3
        r.ah = 0
        held = squad_word(mem, r, sseg, soff, r.ax)              # ACD9-ACE0
        r = yield from guest(mem, r, "1771:377E", held, ret="ACE9")
        r.push(r.ax)                                             # ACE9: the held player's strength
        r = yield from guest(mem, r, "1771:377E", word, ret="ACF2")
        r.dx = pop(mem, r)                                       # ACF2
        if variant == "bench-tie-replaces":
            store = not r.ax < r.dx
        else:
            store = not r.ax <= r.dx                             # ACF3 cmp ax, dx; jbe AD09
    if store:
        r.dx = (r.dx & 0xFF00) | (k & 0xFF)                      # ACF7 mov dl, byte ptr [bp + 6]
        entry()                                                  # ACFA-AD03
        wd8(mem, r.di + 0x99A2, r.dx, "AD05")
    return _end(r)


@PORTS.port("0791:AD8F", ret="ret 4")
def swap_bench_into_slot(mem, variant):
    """AD8F-AFA0 (B11F's BP [bp+4], starter slot s [bp+6]; B11F's [bp-2] the bench slot b): DS:99A2 + (b's +7) := 0;
    squad words s and b swapped (214B:007B); the player now at s gets +6 := his +7 when the outgoing player's +6 and
    the incomer's +7 are both in one of the sets CS:AD0F, AD2F, AD4F, AD6F (23E4:08DF), else the outgoing player's +6;
    the outgoing player +6 := his +7; then AC67(b)."""
    r = Regs(mem)
    r.enter(8)                                                   # AD8F-AD92
    sseg, soff = parent_squad(mem, r)                            # AD95-ADA5
    r.local16(-4, soff)                                          # ADA7
    r.local16(-2, sseg)                                          # ADAA
    s = ss16(mem, r, r.bp + 6)
    b = bench_slot(mem, r)                                       # ADAD-ADB0
    player_at(mem, r, sseg, soff, b)                             # ADB4-ADC8
    r.al = rb(mem, r, 7)                                         # ADCA
    r.ah = 0
    r.di = r.ax
    wd8(mem, r.di + 0x99A2, 0, "ADD2")
    b = bench_slot(mem, r)                                       # ADD7-ADDA
    r.ax = b << 1
    r.es, r.di = sseg, soff
    r.di = r.di + r.ax + 0xFFFE                                  # ADE3-ADE5
    bword = (r.es, r.di)
    r.ax = s << 1                                                # ADEB
    r.es, r.di = sseg, soff
    r.di = r.di + r.ax + 0xFFFE                                  # ADF3-ADF5
    sword = (r.es, r.di)
    r.ax = 2                                                     # ADFB
    r = yield from guest(mem, r, "214B:007B", bword[0], bword[1], sword[0], sword[1], 2, ret="AE04")
    b = bench_slot(mem, r)                                       # AE04-AE07
    oseg, ooff = player_at(mem, r, sseg, soff, b)                # AE0B-AE1F: the outgoing player, now at b
    r.local16(-8, ooff)                                          # AE21
    r.local16(-6, oseg)                                          # AE24
    own_role = False
    for cs_set, rets in ((0xAD0F, ("AE39", "AE63")), (0xAD2F, ("AE7A", "AEA4")), (0xAD4F, ("AEB8", "AEE2")),
                         (0xAD6F, ("AEF6", "AF20"))):
        r.es, r.di = oseg, ooff                                  # les di, [bp - 8]
        r.al = rb(mem, r, 6)                                     # the outgoing player's +6
        r.di = cs_set
        r = yield from guest(mem, r, "23E4:08DF", r.ax, mem.seg(0x0791), cs_set, ret=rets[0])
        if not member(mem):                                      # je: the next set
            continue
        player_at(mem, r, sseg, soff, s)                         # the incomer, now at s
        r.al = rb(mem, r, 7)                                     # his +7
        r.di = cs_set
        r = yield from guest(mem, r, "23E4:08DF", r.ax, mem.seg(0x0791), cs_set, ret=rets[1])
        if member(mem):                                          # AE65 jmp AF22 / jne AF22 / AF20 je AF5E
            own_role = True
            break
    if own_role:
        player_at(mem, r, sseg, soff, s)                         # AF22-AF39
        r.cx = (r.cx & 0xFF00) | rb(mem, r, 7)                   # AF3B mov cl, byte ptr es:[di + 7]
        player_at(mem, r, sseg, soff, s)                         # AF3F-AF56
        w8(mem, r, 6, r.cx, "AF58")
    else:
        r.es, r.di = oseg, ooff                                  # AF5E
        r.cx = (r.cx & 0xFF00) | rb(mem, r, 6)                   # AF61 mov cl, byte ptr es:[di + 6]
        player_at(mem, r, sseg, soff, s)                         # AF65-AF7C
        w8(mem, r, 6, r.cx, "AF7E")
    r.es, r.di = oseg, ooff                                      # AF82
    r.al = rb(mem, r, 7)                                         # AF85
    w8(mem, r, 6, r.al, "AF8C")
    r.di = ss16(mem, r, r.bp + 4)                                # AF90
    b = ss16(mem, r, r.di - 2)                                   # AF93 push word ptr ss:[di - 2]
    r = yield from guest(mem, r, "AC67", b, ss16(mem, r, r.bp + 4), ret="AF9D", far=False)
    return _end(r)


@PORTS.port("0791:AFA3", ret="ret 2")
def fill_starters_from_bench(mem, variant):
    """AFA3-B11C (B11F's BP [bp+4]): for starter slots s = 1..11, b := AAE8(s's player) into B11F's [bp-2]; a bench
    player b stronger (1771:377E) than the starter, or the starter away from his +7 while b's +7 is the starter's +6,
    comes in (AD8F(s)); else when the starter is unavailable (1771:3216), out of place (1771:3179) or a non-keeper in
    slot 1, b comes in, or with no b the choice A9B8(country, +6, 0x14) when there is one."""
    r = Regs(mem)
    r.enter(8)                                                   # AFA3-AFA6
    sseg, soff = parent_squad(mem, r)                            # AFA9-AFB9
    r.local16(-8, soff)                                          # AFBB
    r.local16(-6, sseg)                                          # AFBE
    s = 1
    r.local16(-2, s)                                             # AFC1
    while True:
        word = squad_word(mem, r, sseg, soff, s)                 # AFCB-AFD5
        r.local16(-4, word)                                      # AFD9
        r.es, r.di = sseg, soff                                  # AFDF
        r = yield from guest(mem, r, "AAE8", word, sseg, soff, ret="AFE7", far=False)
        parent = ss16(mem, r, r.bp + 4)                          # AFE7 mov di, word ptr [bp + 4]
        r.di = parent
        ss_w16(r, parent - 2, r.ax)                              # AFEA mov word ptr ss:[di - 2], ax
        b = r.ax
        swap = False
        if b != 0:                                               # AFF1 cmp word ptr ss:[di - 2], 0; jne AFFB
            r = yield from guest(mem, r, "1771:377E", word, ret="B003")
            r.push(r.ax)                                         # B003: the starter's strength
            b = bench_slot(mem, r)                               # B004-B007
            bench = squad_word(mem, r, sseg, soff, b)            # B00B-B012
            r = yield from guest(mem, r, "1771:377E", bench, ret="B01B")
            r.dx = pop(mem, r)                                   # B01B
            if r.ax > r.dx:                                      # B01C cmp ax, dx; ja B07F
                swap = True
            else:
                player_of(mem, r, word)                          # B020-B02C
                r.cx = (r.cx & 0xFF00) | rb(mem, r, 6)           # B02E mov cl, es:[di + 6]
                player_of(mem, r, word)                          # B032-B03E
                r.al = rb(mem, r, 7)                             # B040
                if r.al != (r.cx & 0xFF):                        # B044 cmp al, cl; je B08B
                    player_of(mem, r, word)                      # B048-B054
                    r.cx = (r.cx & 0xFF00) | rb(mem, r, 6)       # B056
                    b = bench_slot(mem, r)                       # B05A-B05D
                    player_at(mem, r, sseg, soff, b)             # B061-B075
                    r.al = rb(mem, r, 7)                         # B077
                    swap = r.al == (r.cx & 0xFF)                 # B07B cmp al, cl; jne B08B
        if swap:
            r = yield from guest(mem, r, "AD8F", s, ss16(mem, r, r.bp + 4), ret="B088", far=False)   # B07F
        else:
            r = yield from guest(mem, r, "1771:3216", word, ret="B093")                # B08B
            replace = r.al != 0                                  # B093 or al, al; jne B0BE
            if not replace:
                r = yield from guest(mem, r, "1771:3179", word, ret="B09F")
                replace = r.al != 0                              # B09F or al, al; jne B0BE
            if not replace and s == 1:                           # B0A3 cmp word ptr [bp - 2], 1; jne B110
                player_of(mem, r, word)                          # B0A9-B0B5
                replace = rb(mem, r, 7) != 0                     # B0B7 cmp byte ptr es:[di + 7], 0; je B110
            if replace:
                r.di = ss16(mem, r, r.bp + 4)                    # B0BE
                if ss16(mem, r, r.di - 2) != 0:                  # B0C1 cmp word ptr ss:[di - 2], 0; je B0D3
                    r = yield from guest(mem, r, "AD8F", s, ss16(mem, r, r.bp + 4), ret="B0D1", far=False)
                else:
                    country = ss16(mem, r, r.di + 6)             # B0D6 push word ptr ss:[di + 6]
                    player_of(mem, r, word)                      # B0DA-B0E6
                    r.al = rb(mem, r, 6)                         # B0E8
                    r.ah = 0
                    role = r.ax
                    r.ax = 0x14                                  # B0EF
                    r = yield from guest(mem, r, "A9B8", country, role, 0x14, ret="B0F6", far=False)
                    parent = ss16(mem, r, r.bp + 4)              # B0F6
                    r.di = parent
                    ss_w16(r, parent - 2, r.ax)                  # B0F9 mov word ptr ss:[di - 2], ax
                    if r.ax != 0:                                # B100 cmp word ptr ss:[di - 2], 0; je B110
                        r = yield from guest(mem, r, "AD8F", s, parent, ret="B110", far=False)
        if s == 0xB:                                             # B110 cmp word ptr [bp - 2], 0xb; je B119
            break
        s += 1
        r.local16(-2, s)                                         # AFC8 inc word ptr [bp - 2]
    return _end(r)


@PORTS.port("0791:B11F", ret="retf 2")
def choose_computer_lineup(mem, variant):
    """B11F-B15C (the country [bp+6]): DS:99A2 0xE bytes cleared; AC67(k) for the bench slots k = 0xC..0x14; AFA3; the
    squad sorted by position (1771:52CC)."""
    r = Regs(mem)
    r.enter(6)                                                   # B11F-B122
    r = yield from fill(mem, r, 0x99A2, 0xE, 0, "B136")
    k = 0xC
    r.local16(-4, k)                                             # B136
    while True:
        r = yield from guest(mem, r, "AC67", k, r.bp, ret="B147", far=False)
        if k == 0x14:                                            # B147 cmp word ptr [bp - 4], 0x14; jne B13D
            break
        k += 1
        r.local16(-4, k)                                         # B13D inc word ptr [bp - 4]
    r = yield from guest(mem, r, "AFA3", r.bp, ret="B151", far=False)
    r = yield from guest(mem, r, "1771:52CC", ss16(mem, r, r.bp + 6), ret="B159")
    return _end(r)


# -- 1771:517A, 52CC: the squad sort -------------------------------------------------------------------------------
@PORTS.port("1771:517A", ret="ret 6")
def quicksort_words(mem, variant):
    """517A-52C9 (52CC's BP [bp+4], hi [bp+6], lo [bp+8]): Hoare's quicksort of the squad words lo..hi of 52CC's
    country by the players' +6, the pivot the middle word's (unsigned (lo + hi) / 2); each swap of two words swaps
    52CC's saved bytes [parent bp + i - 0x15] too (214B:007B); then the two parts, the left first."""
    r = Regs(mem)
    r.enter(0xC)                                                 # 517A-517D
    sseg, soff = parent_squad(mem, r)                            # 5180-5190
    r.local16(-0xC, soff)                                        # 5192
    r.local16(-0xA, sseg)                                        # 5195
    hi, lo = ss16(mem, r, r.bp + 6), ss16(mem, r, r.bp + 8)
    i, j = lo, hi
    r.local16(-2, i)                                             # 519B
    r.local16(-4, j)                                             # 51A1
    r.ax = lo + hi                                               # 51A4-51A7
    r.dx = 0                                                     # 51AA
    r.cx = 2                                                     # 51AC
    r.ax, r.dx = r.ax // 2, r.ax % 2                             # 51AF div cx
    player_at(mem, r, sseg, soff, r.ax)                          # 51B1-51C5
    r.al = rb(mem, r, 6)                                         # 51C7
    r.ah = 0
    pivot = r.ax
    r.local16(-8, pivot)                                         # 51CD

    def key(k):
        player_at(mem, r, sseg, soff, k)
        r.al = rb(mem, r, 6)
        r.ah = 0
        return r.ax
    while True:
        while key(i) < pivot:                                    # 51D0-51F2 cmp ax, word ptr [bp - 8]; jae 51F9
            i = (i + 1) & M16
            r.local16(-2, i)                                     # 51F4 inc word ptr [bp - 2]
        while key(j) > pivot:                                    # 51F9-521B jbe 5222
            j = (j - 1) & M16
            r.local16(-4, j)                                     # 521D dec word ptr [bp - 4]
        if i <= j:                                               # 5222 cmp ax, word ptr [bp - 4]; ja 5293
            wi = squad_word(mem, r, sseg, soff, i)               # 522A-5234
            r.local16(-6, wi)                                    # 5238
            r.ax = j << 1                                        # 523B-5245
            r.es, r.di = sseg, soff
            r.di = r.di + r.ax
            r.dx = rw(mem, r, -2)
            r.ax = i << 1                                        # 5249-5253
            r.es, r.di = sseg, soff
            r.di = r.di + r.ax
            w16(mem, r, -2, r.dx, "1771:5253")
            r.dx = wi                                            # 5257
            r.ax = j << 1                                        # 525A-5264
            r.es, r.di = sseg, soff
            r.di = r.di + r.ax
            w16(mem, r, -2, r.dx, "1771:5264")
            parent = ss16(mem, r, r.bp + 4)
            r.ax = i                                             # 5268
            a = (parent + i + 0xFFEB) & M16                      # 526B-5270
            b = (parent + j + 0xFFEB) & M16                      # 5276-527E
            r.ax = j
            r.di = b
            r.ax = 1                                             # 5284
            if variant != "sort-bytes-unswapped":
                r = yield from guest(mem, r, "214B:007B", r.ss, a, r.ss, b, 1, ret="1771:528D")
            i = (i + 1) & M16
            r.local16(-2, i)                                     # 528D inc word ptr [bp - 2]
            j = (j - 1) & M16
            r.local16(-4, j)                                     # 5290 dec word ptr [bp - 4]
        r.ax = i                                                 # 5293
        if i > j:                                                # 5296 cmp ax, word ptr [bp - 4]; ja 529E
            break
    parent = ss16(mem, r, r.bp + 4)
    r.ax = lo                                                    # 529E
    if lo < j:                                                   # 52A1 cmp ax, word ptr [bp - 4]; jae 52B2
        r = yield from guest(mem, r, "1771:517A", lo, j, parent, ret="1771:52B2", far=False)
    r.ax = i                                                     # 52B2
    if i < hi:                                                   # 52B5 cmp ax, word ptr [bp + 6]; jae 52C6
        r = yield from guest(mem, r, "1771:517A", i, hi, parent, ret="1771:52C6", far=False)
    return _end(r)


@PORTS.port("1771:52CC", ret="retf 2")
def sort_squad_by_position(mem, variant):
    """52CC-53E5 (the country [bp+6]): for the starters and the bench (slots DS:0F3A + g to DS:0F3C + g, g = 0, 1):
    each player's +6 saved in [bp + i - 0x15], 0xE written for an unavailable one (1771:3216) of a managed country
    (1771:0B77); the words sorted by +6 (517A, the saved bytes along); then each player's +6 put back from them."""
    r = Regs(mem)
    r.enter(0x26)                                                # 52CC-52CF
    country = ss16(mem, r, r.bp + 6)
    sseg, soff = squad_of(mem, r, country)                       # 52D2-52DE
    r.local16(-0x20, soff)                                       # 52E0
    r.local16(-0x1E, sseg)                                       # 52E3
    r = yield from guest(mem, r, "1771:0B77", country, ret="1771:52ED")
    managed = r.al
    r.local8(-0x1B, managed)                                     # 52ED
    g = 0
    r.local8(-0x1C, g)                                           # 52F0
    while True:
        r.al = g                                                 # 52F9
        cbw(r)
        r.di = r.ax
        r.al = mem.ds8((r.di + 0xF3A) & M16)                     # 52FF
        r.ah = 0
        lo = r.ax
        r.local16(-0x18, lo)                                     # 5305
        r.al = g                                                 # 5308
        cbw(r)
        r.di = r.ax
        r.al = mem.ds8((r.di + 0xF3C) & M16)                     # 530E
        r.ah = 0
        hi = r.ax
        r.local16(-0x1A, hi)                                     # 5314
        r.ax = hi                                                # 5317
        r.local16(-0x22, hi)                                     # 531A
        r.ax = lo                                                # 531D
        if lo <= hi:                                             # 5320 cmp ax, word ptr [bp - 0x22]; ja 5385
            i = lo
            r.local16(-0x16, i)                                  # 5325
            while True:
                pseg, poff = player_at(mem, r, sseg, soff, i)    # 532D-5344
                r.local16(-0x26, poff)                           # 5346
                r.local16(-0x24, pseg)                           # 5349
                r.al = rb(mem, r, 6)                             # 534F
                r.di = i                                         # 5353
                r.local8(i - 0x15, r.al)                         # 5356 mov byte ptr [bp + di - 0x15], al
                if managed != 0:                                 # 5359 cmp byte ptr [bp - 0x1b], 0; je 537D
                    word = squad_word(mem, r, sseg, soff, i)     # 535F-5369
                    r = yield from guest(mem, r, "1771:3216", word, ret="1771:5371")
                    if r.al != 0:                                # 5371 or al, al; je 537D
                        r.es, r.di = pseg, poff                  # 5375
                        w8(mem, r, 6, 0xE, "1771:5378")
                r.ax = i                                         # 537D
                if i == hi:                                      # 5380 cmp ax, word ptr [bp - 0x22]; jne 532A
                    break
                i += 1
                r.local16(-0x16, i)                              # 532A inc word ptr [bp - 0x16]
        r = yield from guest(mem, r, "1771:517A", lo, hi, r.bp, ret="1771:538F", far=False)
        r.ax = hi                                                # 538F
        r.local16(-0x22, hi)                                     # 5392
        r.ax = lo                                                # 5395
        if lo <= hi:                                             # 5398 cmp ax, word ptr [bp - 0x22]; ja 53D9
            i = lo
            r.local16(-0x16, i)                                  # 539D
            while True:
                pseg, poff = player_at(mem, r, sseg, soff, i)    # 53A5-53BC
                r.local16(-0x26, poff)                           # 53BE
                r.local16(-0x24, pseg)                           # 53C1
                r.di = i                                         # 53C4
                r.al = ss8(mem, r, r.bp + i - 0x15)              # 53C7 mov al, byte ptr [bp + di - 0x15]
                r.es, r.di = pseg, poff                          # 53CA
                w8(mem, r, 6, r.al, "1771:53CD")
                r.ax = i                                         # 53D1
                if i == hi:                                      # 53D4 cmp ax, word ptr [bp - 0x22]; jne 53A2
                    break
                i += 1
                r.local16(-0x16, i)                              # 53A2 inc word ptr [bp - 0x16]
        if g == 1:                                               # 53D9 cmp byte ptr [bp - 0x1c], 1; je 53E2
            break
        g += 1
        r.local8(-0x1C, g)                                       # 52F6 inc byte ptr [bp - 0x1c]
    return _end(r)


# -- 1771:580B: the fixture kind's title ---------------------------------------------------------------------------
# kind -> (the string in segment 1771, the return address after its 23E4:0644): 5816-59AD; any other kind takes 57FF.
KIND_TITLES = {0: (0x577F, "5829"), 1: (0x5789, "5844"), 2: (0x5792, "5864"), 5: (0x5792, "5864"),
               6: (0x579D, "587F"), 3: (0x57A6, "589F"), 7: (0x57A6, "589F"), 0xC8: (0x57B2, "58BA"),
               0x65: (0x57BC, "58DA"), 0xC9: (0x57BC, "58DA"), 0x67: (0x57C7, "58FA"), 0xCB: (0x57C7, "58FA"),
               0x66: (0x57CD, "591A"), 0xCA: (0x57CD, "591A"), 8: (0x57D7, "5935"), 0xFC: (0x57DF, "594F"),
               0xFD: (0x57E6, "5969"), 0xFE: (0x57EC, "5983"), 0xFF: (0x57F7, "599D")}
OTHER_KIND = (0x57FF, "59B2")


@PORTS.port("1771:580B", ret="retf 2")
def kind_title(mem, variant):
    """580B-59B5 (the kind word [bp+6]; the result string [bp+8]): the title of the fixture kind, a string constant of
    segment 1771 stored with 23E4:0644 (at most 0xC characters) into the result."""
    r = Regs(mem)
    r.enter()                                                    # 580B-580C
    r.ax = ss16(mem, r, r.bp + 6)                                # 580E
    src, ret = KIND_TITLES.get(r.ax, OTHER_KIND)                 # 5811-5988 the cmp ax, n chain
    r.di = src
    dseg, doff = farg(mem, r, 8)                                 # les di, ptr [bp + 8]
    r.ax = 0xC
    r = yield from guest(mem, r, "23E4:0644", mem.seg(0x1771), src, dseg, doff, 0xC, ret=f"1771:{ret}")
    return _end(r)
