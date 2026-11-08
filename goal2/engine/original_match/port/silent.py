"""T120 (#427, U2): the silent path, the fixtures no human plays: simulate_fixture 000E:6970, quick_result_silent
0791:D47E, credit_silent_match_scorers 0791:B602 and prepare_unplayed_match 0791:BB2F.

Translated instruction by instruction from the listing (static/goal-exe/code/seg_000E_08.asm 6970-6C1E,
seg_0791_21.asm D47E-D5BE, seg_0791_18.asm B602-B6C9, seg_0791_19.asm BB2F-BBFC), after the named view
(named/seg_000E_05.c, named/seg_0791_10.c, named/seg_0791_12.c) and the annotation rows (F010, F039). The line comments
are the listing's offsets. As T70's and T72's modules, the routines are written in the registers the listing uses
(runtime.Regs), so the words they push for their callees (a byte pushed with `mov al, n; push ax` keeps the AH of the
instruction before), the words held on the guest stack across a call and the locals of the frames are the original's.

Every call of the listing stays a guest call with its target, arguments, return address and near/far form: D47E's
prepare_computer_sides A3DE (which reaches the set-up reseed 2648 on every call: A3DE's `call 0x2648` at A43E has no
branch around it, seg_0791_17.asm), the quick goals B19D, the side's attributes 1771:0BC4, result_needs_winner B15F and
the coin 214B:06FA; B602's 1771:5A03, the scorer draw 214B:06B1, B3B7 and B364; BB2F's match_setup A4A1, 1771:3558,
214B:06B1, B364, 1771:0B77, BA4E and BC5D; 6970's D47E, B7FA, B602, D050, BC5D, the screens (0791:0712, 214B:0329,
23E4:025D, 214B:02C8, 1771:5BF6, 1771:7812, 214B:04F8, the group tables 0791:E929), 214B:0D56 and the delay 214B:1E09.
The key reads (214B:08DD at 6A84 and 6B8D) and polls (214B:0723 at 6B84 and 6BF2) are guest calls too, which the kit
answers at their entry from its policy (route.py), so a proof replays the same answer to the original.

simulate_fixture is a nested procedure of route_fixture 000E:6CA7 (`push bp; call 0x6970` at 7013, `ret 2`): it reads
route_fixture's word [bp - 6] (the cursor the call started at) and writes its byte [bp - 2] (1 after the results list,
0 after a 0xFE fixture's score page) through the parent BP it is given."""
from . import Registry
from .contests import ss16, pop
from .geometry import cbw, mul
from .restarts import _end
from .runtime import Regs
from .setup import guest, farg, w8, w16, rb, rw

PORTS = Registry("silent", "the silent path: simulate_fixture 000E:6970, quick_result_silent D47E, "
                           "credit_silent_match_scorers B602, prepare_unplayed_match BB2F (T120)")
PORTS.variant("goal-plus-one", "D4C7: the quick result's first goals byte stored plus one (a goal)")
PORTS.variant("credit-twice", "B694: a silent scorer's goals word incremented by two (a scorer credit)")
PORTS.variant("scorer-draw-29", "B65E: the scorer drawn by 214B:06B1(29), not (30) (a draw)")
M16 = 0xFFFF
SEG = "000E"


def save_ptr(r, off):
    """`mov word ptr [bp + off], di; mov word ptr [bp + off + 2], es`."""
    r.local16(off, r.di)
    r.local16(off + 2, r.es)


def frame_ptr(mem, r, off):
    """`les di, ptr [bp + off]`."""
    r.es, r.di = ss16(mem, r, r.bp + off + 2), ss16(mem, r, r.bp + off)
    return r.es, r.di


def country_of(mem, r, word):
    """`mov dx, 0xbf; mul dx; les di, ptr [0xa917]; add di, ax` with AX = word: the country record."""
    r.ax = word
    r.dx = 0xBF
    mul(r, r.dx)
    r.di, r.es = mem.ds16(0xA917), mem.ds16(0xA919)
    r.di = r.di + r.ax
    return r.es, r.di


def player_of(mem, r, word):
    """`mov dx, 0x14; mul dx; les di, ptr [0xa91b]; add di, ax` with AX = word: the player record."""
    r.ax = word
    r.dx = 0x14
    mul(r, r.dx)
    r.di, r.es = mem.ds16(0xA91B), mem.ds16(0xA91D)
    r.di = r.di + r.ax
    return r.es, r.di


# -- D47E ----------------------------------------------------------------------------------------------------------
def _winner_byte(mem, r, fx, at):
    """D4E3-D4FB / D538-D550: `mov al, es:[di + 1]; cmp al, es:[di]; ja; mov al, 0 | mov al, 1`, +3 := AL."""
    r.es, r.di = fx
    second = rb(mem, r, 1)
    r.al = second
    r.al = 1 if second > rb(mem, r, 0) else 0
    w8(mem, r, 3, r.al, at)


@PORTS.port("0791:D47E", ret="retf 4")
def quick_result_silent(mem, variant):
    """D47E-D5BE (the fixture [bp+6]): the computer sides A3DE; each side's attributes 1771:0BC4 (the second with 1
    and DS:80FC, the first with 0, 0); the quick goals B19D(0xC) into +0, +1 (DS:9B3C); +3 := 2 for a level score,
    else 1 when the second side scored more, else 0; when B15F asks for a winner, B19D(4) again into +0, +1 and, for a
    level score, +3 := the coin 214B:06FA, else as before; then the 11 first squad players of both sides get +0x12 :=
    0x7FFF."""
    r = Regs(mem)
    r.enter(0x10)                                                # D47E-D481
    fseg, foff = farg(mem, r, 6)                                 # D484 les di, ptr [bp + 6]
    save_ptr(r, -7)                                              # D487, D48A
    fx = (fseg, foff)
    farg(mem, r, 6)                                              # D48D
    r = yield from guest(mem, r, "A3DE", fseg, foff, ret="D495", far=False)
    r.es, r.di = fx                                              # D495 les di, ptr [bp - 7]
    second = rw(mem, r, 6)                                       # D498 push word ptr es:[di + 6]
    r.al = 1                                                     # D49C
    one = r.ax
    r.al = mem.ds8(0x80FC)                                       # D49F mov al, byte ptr [0x80fc]
    r = yield from guest(mem, r, "1771:0BC4", second, one, r.ax, ret="D4A8")
    r.es, r.di = fx                                              # D4A8
    first = rw(mem, r, 4)                                        # D4AB
    r.al = 0                                                     # D4AF
    zero = r.ax
    r = yield from guest(mem, r, "1771:0BC4", first, zero, zero, ret="D4BA")
    r.ax = 0xC                                                   # D4BA
    r = yield from guest(mem, r, "B19D", r.ax, ret="D4C1", far=False)
    r.ax = mem.ds16(0x9B3C)                                      # D4C1
    r.es, r.di = fx
    w16(mem, r, 0, r.ax + (1 if variant == "goal-plus-one" else 0), "D4C7")
    r.al = rb(mem, r, 0)                                         # D4CD
    if r.al == rb(mem, r, 1):                                    # D4D3 cmp al, es:[di + 1]; jne D4E3
        w8(mem, r, 3, 2, "D4DC")
    else:
        _winner_byte(mem, r, fx, "D4FB")
    farg(mem, r, 6)                                              # D4FF
    r = yield from guest(mem, r, "B15F", fseg, foff, ret="D507", far=False)
    if r.al:                                                     # D507 or al, al; je D554
        r.ax = 4                                                 # D50B
        r = yield from guest(mem, r, "B19D", r.ax, ret="D512", far=False)
        r.ax = mem.ds16(0x9B3C)                                  # D512
        r.es, r.di = fx
        w16(mem, r, 0, r.ax, "D518")
        r.al = rb(mem, r, 0)                                     # D51E
        if r.al == rb(mem, r, 1):                                # D524; jne D538
            r = yield from guest(mem, r, "214B:06FA", ret="D52F")
            r.es, r.di = fx                                      # D52F
            w8(mem, r, 3, r.al, "D532")
        else:
            _winner_byte(mem, r, fx, "D550")
    side = 0
    r.local8(-1, side)                                           # D554
    while True:
        r.al = side                                              # D55D
        cbw(r)
        r.ax = r.ax << 1
        r.es, r.di = fx                                          # D563
        r.di = r.di + r.ax
        cseg, coff = country_of(mem, r, rw(mem, r, 4))           # D568-D575
        save_ptr(r, -0xB)                                        # D577, D57A
        k = 1
        r.local16(-3, k)                                         # D57D
        while True:
            r.ax = k << 1                                        # D587, D58A
            r.es, r.di = cseg, coff                              # D58C
            r.di = r.di + r.ax
            player_of(mem, r, rw(mem, r, -2))                    # D591-D59E
            save_ptr(r, -0xF)                                    # D5A0, D5A3
            w16(mem, r, 0x12, 0x7FFF, "D5A9")
            if k == 0xB:                                         # D5AF cmp word ptr [bp - 3], 0xb; jne D584
                break
            k += 1
            r.local16(-3, k)                                     # D584
        if side == 1:                                            # D5B5 cmp byte ptr [bp - 1], 1; jne D55A
            break
        side += 1
        r.local8(-1, side)                                       # D55A
    return _end(r)


# -- B602 ----------------------------------------------------------------------------------------------------------
@PORTS.port("0791:B602", ret="retf 4")
def credit_silent_match_scorers(mem, variant):
    """B602-B6C9 (the fixture [bp+6]): F := 1771:5A03 (the kind counts for the scorers' table); per side, per goal in
    its byte +side: a squad slot from DS:0A09[214B:06B1(0x1E)], its player's goals word +0xA incremented, B3B7(player,
    country +0x2C) when F, and B364(player, 1)."""
    r = Regs(mem)
    r.enter(0x12)                                                # B602-B605
    fseg, foff = farg(mem, r, 6)                                 # B608
    save_ptr(r, -0xA)                                            # B60B, B60E
    fx = (fseg, foff)
    farg(mem, r, 6)                                              # B611
    r = yield from guest(mem, r, "1771:5A03", fseg, foff, ret="B61B")
    tables = r.al
    r.local8(-2, tables)                                         # B61B
    side = 0
    r.local8(-1, side)                                           # B61E
    while True:
        r.al = side                                              # B627
        cbw(r)
        r.ax = r.ax << 1
        r.es, r.di = fx                                          # B62D
        r.di = r.di + r.ax
        cseg, coff = country_of(mem, r, rw(mem, r, 4))           # B632-B63F
        save_ptr(r, -0xE)                                        # B641, B644
        r.al = side                                              # B647
        cbw(r)
        r.es, r.di = fx                                          # B64B
        r.di = r.di + r.ax
        r.al = rb(mem, r, 0)                                     # B650
        r.ah = 0                                                 # B653
        goals = r.ax
        r.local16(-6, goals)                                     # B655
        while goals != 0:                                        # B658 cmp word ptr [bp - 6], 0; jbe B6BD
            r.ax = 0x1D if variant == "scorer-draw-29" else 0x1E  # B65E
            r = yield from guest(mem, r, "214B:06B1", r.ax, ret="B667")
            r.di = r.ax                                          # B667
            r.al = mem.ds8(r.di + 0xA09)                         # B669
            r.ah = 0                                             # B66D
            r.ax = r.ax << 1                                     # B66F
            r.es, r.di = cseg, coff                              # B671
            r.di = r.di + r.ax
            word = rw(mem, r, -2)                                # B676
            r.ax = word
            r.local16(-4, word)                                  # B67A
            pseg, poff = player_of(mem, r, word)                 # B67D-B689
            save_ptr(r, -0x12)                                   # B68B, B68E
            w16(mem, r, 0xA, rw(mem, r, 0xA) + (2 if variant == "credit-twice" else 1), "B694")
            if tables:                                           # B698 cmp byte ptr [bp - 2], 0; je B6AE
                r.es, r.di = cseg, coff                          # B6A1
                r.al = rb(mem, r, 0x2C)
                r.ah = 0                                         # B6A8
                r = yield from guest(mem, r, "B3B7", word, r.ax, ret="B6AE", far=False)
            r.ax = 1                                             # B6B1
            r = yield from guest(mem, r, "B364", word, r.ax, ret="B6B8", far=False)
            goals = (goals - 1) & M16
            r.local16(-6, goals)                                 # B6B8 dec word ptr [bp - 6]
        if side == 1:                                            # B6BD cmp byte ptr [bp - 1], 1; je B6C6
            break
        side += 1
        r.local8(-1, side)                                       # B624
    return _end(r)


# -- BB2F ----------------------------------------------------------------------------------------------------------
@PORTS.port("0791:BB2F", ret="retf 4")
def prepare_unplayed_match(mem, variant):
    """BB2F-BBFC (the fixture [bp+6]): match_setup A4A1; per side (its country DS:9B34 + 2 side): for its 20 squad
    words 1771:3558 and B364(word, 214B:06B1(2) - 214B:06B1(4), the second draw minus the first); then BA4E when 1771:0B77 calls it managed, else
    BC5D; the fixture's first byte := 0 and DS:0C1E := 0."""
    r = Regs(mem)
    r.enter(8)                                                   # BB2F-BB32
    fseg, foff = farg(mem, r, 6)                                 # BB35
    r = yield from guest(mem, r, "A4A1", fseg, foff, ret="BB3D", far=False)

    def country():
        """`mov al, [bp - 1]; cwde; mov di, ax; shl di, 1; ... word ptr [di - 0x64cc]` (DS:9B34 + 2 side)."""
        r.al = side
        cbw(r)
        r.di = r.ax
        r.di = r.di << 1
        return mem.ds16(r.di + 0x9B34)

    side = 0
    r.local8(-1, side)                                           # BB3D
    while True:
        cseg, coff = country_of(mem, r, country())               # BB46-BB5B
        save_ptr(r, -7)                                          # BB5D, BB60
        k = 1
        r.local16(-3, k)                                         # BB63
        while True:
            def squad_word():
                """`mov ax, [bp - 3]; shl ax, 1; les di, ptr [bp - 7]; add di, ax; push word ptr es:[di - 2]`."""
                r.ax = k << 1
                r.es, r.di = cseg, coff
                r.di = r.di + r.ax
                return rw(mem, r, -2)
            r = yield from guest(mem, r, "1771:3558", squad_word(), ret="BB80")
            r.push(squad_word())                                 # BB8A
            r.ax = 4                                             # BB8E
            r = yield from guest(mem, r, "214B:06B1", r.ax, ret="BB97")
            r.push(r.ax)                                         # BB97
            r.ax = 2                                             # BB98
            r = yield from guest(mem, r, "214B:06B1", r.ax, ret="BBA1")
            r.dx = pop(mem, r)                                   # BBA1
            r.ax = r.ax - r.dx                                   # BBA2
            word = pop(mem, r)                                   # the word BB8A pushed, B364's first argument
            r = yield from guest(mem, r, "B364", word, r.ax, ret="BBA8", far=False)
            if k == 0x14:                                        # BBA8 cmp word ptr [bp - 3], 0x14; jne BB6A
                break
            k += 1
            r.local16(-3, k)                                     # BB6A
        r = yield from guest(mem, r, "1771:0B77", country(), ret="BBBF")
        if r.al:                                                 # BBBF or al, al; je BBD4
            r = yield from guest(mem, r, "BA4E", country(), ret="BBD2", far=False)
        else:
            r = yield from guest(mem, r, "BC5D", country(), ret="BBE4")    # BBE0 push cs; call 0xbc5d
        if side == 1:                                            # BBE4 cmp byte ptr [bp - 1], 1; je BBED
            break
        side += 1
        r.local8(-1, side)                                       # BB43
    farg(mem, r, 6)                                              # BBED
    w8(mem, r, 0, 0, "BBF0")
    mem.wds8(0x0C1E, 0, "0791:BBF4")
    return _end(r)


# -- 000E:6970 -----------------------------------------------------------------------------------------------------
def _at(off):
    return f"{SEG}:{off:04X}"


def _fixture_at_cursor(mem, r, game):
    """`les di, ptr [bp - 0xe]` (or [0xa923]); `mov ax, es:[di + 0x26]; mov cl, 3; shl ax, cl; les di, ptr [0xa92b];
    add di, ax; add di, 0xfff8`: the fixture at the cursor."""
    r.es, r.di = game
    r.ax = rw(mem, r, 0x26)
    r.cx = (r.cx & 0xFF00) | 3
    r.ax = r.ax << 3
    r.di, r.es = mem.ds16(0xA92B), mem.ds16(0xA92D)
    r.di = r.di + r.ax
    r.di = r.di + 0xFFF8
    return r.es, r.di


def _ds_far(mem, r, off):
    """`les di, ptr [off]`."""
    r.di, r.es = mem.ds16(off), mem.ds16(off + 2)
    return r.es, r.di


@PORTS.port("000E:6970", ret="ret 2")
def simulate_fixture(mem, variant):
    """6970-6C1E (route_fixture's BP [bp+4]): the fixture at the cursor goes through D47E, B7FA, B602 and D050, then
    BC5D for both its countries; a fixture whose first byte was 0xFE shows its score page (0791:0712, the screens
    DS:25CC and DS:14A6, a key at 6A84) and the group tables E929(its second country, 0), the cursor +0x26 moves on and
    route_fixture's [bp - 2] := 0; any other shows the results list (DS:5C0C, DS:26F2, 1771:5BF6, DS:142A, 1771:7812
    for the fixtures from max(the cursor - 15, route_fixture's start [bp - 6]) to the cursor, the speed 5 - game +0x3E
    at DS:00AA), takes a waiting key (0xAE: +0x3E up to 5, 0xAF: down to 0, space: the pause message CS:696A) and
    waits +0x3E times 50 ms unless a key waits; route_fixture's [bp - 2] := 1 and the cursor moves on."""
    r = Regs(mem)
    r.enter(0x10)                                                # 6970-6973
    game = _ds_far(mem, r, 0xA923)                               # 6976
    fx = _fixture_at_cursor(mem, r, game)                        # 697A-6988
    save_ptr(r, -0xA)                                            # 698C, 698F
    game = _ds_far(mem, r, 0xA923)                               # 6992
    save_ptr(r, -0xE)                                            # 6996, 6999
    r.es, r.di = fx                                              # 699C
    page = rb(mem, r, 0) == 0xFE                                 # 699F cmp byte ptr es:[di], 0xfe; je 69A9
    r.al = int(page)
    r.local8(-2, r.al)                                           # 69AB
    for target, ret in (("0791:D47E", 0x69CA), ("0791:B7FA", 0x69E6), ("0791:B602", 0x6A02),
                        ("0791:D050", 0x6A1E)):
        seg, off = _fixture_at_cursor(mem, r, game)              # 69AE-69BF and the same before each call
        r = yield from guest(mem, r, target, seg, off, ret=_at(ret))
    side = 0
    r.local8(-1, side)                                           # 6A1E
    while True:
        r.al = side                                              # 6A27
        cbw(r)
        r.ax = r.ax << 1
        r.es, r.di = fx                                          # 6A2D
        r.di = r.di + r.ax
        r = yield from guest(mem, r, "0791:BC5D", rw(mem, r, 4), ret=_at(0x6A3B))
        if side == 1:                                            # 6A3B cmp byte ptr [bp - 1], 1; jne 6A24
            break
        side += 1
        r.local8(-1, side)                                       # 6A24
    parent = None
    ds = mem.DS
    if page:                                                     # 6A41 cmp byte ptr [bp - 2], 0; je 6AAA
        r.di = 0xA96E                                            # 6A47
        r = yield from guest(mem, r, "0791:0712", ds, 0xA96E, ret=_at(0x6A51))
        for screen, ret in ((0x25CC, 0x6A60), (0x14A6, 0x6A6F)):
            r.di = 0xA96E                                        # 6A51-6A59, 6A60-6A68
            r = yield from guest(mem, r, "214B:0329", ds, screen, ds, 0xA96E, ret=_at(ret))
        back = _ds_far(mem, r, 0xA96E)                           # 6A6F
        video = _ds_far(mem, r, 0xA96A)                          # 6A75
        r.ax = 0xFA0                                             # 6A7B
        r = yield from guest(mem, r, "23E4:025D", *back, *video, r.ax, ret=_at(0x6A84))
        r = yield from guest(mem, r, "214B:08DD", ret=_at(0x6A89))
        r.es, r.di = fx                                          # 6A89
        country = rw(mem, r, 6)                                  # 6A8C push word ptr es:[di + 6]
        r.al = 0                                                 # 6A90
        r = yield from guest(mem, r, "0791:E929", country, r.ax, ret=_at(0x6A98))
        r.es, r.di = game                                        # 6A98
        w16(mem, r, 0x26, rw(mem, r, 0x26) + 1, _at(0x6A9B))
        parent = ss16(mem, r, r.bp + 4)                          # 6A9F mov di, word ptr [bp + 4]
        r.di = parent
        r._put(parent - 2, b"\x00")                              # 6AA2 mov byte ptr ss:[di - 2], 0
        r.flush()
        return _end(r)
    for screen, ret in ((0x5C0C, 0x6AB9), (0x26F2, 0x6AC8)):
        r.di = 0xA96E                                            # 6AAA-6AB2, 6AB9-6AC1
        r = yield from guest(mem, r, "214B:0329", ds, screen, ds, 0xA96E, ret=_at(ret))
    r = yield from guest(mem, r, "1771:5BF6", ret=_at(0x6ACD))
    r.di = 0xA96E                                                # 6ACD-6AD5
    r = yield from guest(mem, r, "214B:0329", ds, 0x142A, ds, 0xA96E, ret=_at(0x6ADC))
    row = 7
    r.local16(-6, row)                                           # 6ADC
    r.es, r.di = game                                            # 6AE1
    r.ax = rw(mem, r, 0x26)                                      # 6AE4
    last = r.ax
    r.local16(-0x10, last)                                       # 6AE8
    parent = ss16(mem, r, r.bp + 4)                              # 6AEB
    r.di = parent
    start = ss16(mem, r, parent - 6)                             # 6AEE mov ax, word ptr ss:[di - 6]
    r.ax = start
    r.dx = 0                                                     # 6AF2 xor dx, dx
    r.es, r.di = game                                            # 6AF6
    low = rw(mem, r, 0x26) + 0xFFF1                              # 6AF9-6AFF add ax, 0xfff1
    r.ax = low
    r.dx = 0 + (low >> 16) + 0xFFFF                              # 6B02 adc dx, -1
    r = yield from guest(mem, r, "214B:0D56", 0, start, r.dx, r.ax, ret=_at(0x6B0C))
    if r.ax <= last:                                             # 6B0C cmp ax, word ptr [bp - 0x10]; ja 6B43
        k = r.ax
        r.local16(-4, k)                                         # 6B11
        while True:
            row = (row + 1) & M16
            r.local16(-6, row)                                   # 6B19 inc word ptr [bp - 6]
            r.ax = k << 3                                        # 6B1C-6B21
            r.cx = (r.cx & 0xFF00) | 3
            r.di, r.es = mem.ds16(0xA92B), mem.ds16(0xA92D)      # 6B23
            r.di = r.di + r.ax
            r.di = r.di + 0xFFF8                                 # 6B29
            r.ax = 0x21                                          # 6B32
            r = yield from guest(mem, r, "1771:7812", r.es, r.di, row, r.ax, ret=_at(0x6B3B))
            r.ax = k                                             # 6B3B
            if k == last:                                        # 6B3E cmp ax, word ptr [bp - 0x10]; jne 6B16
                break
            k = (k + 1) & M16
            r.local16(-4, k)                                     # 6B16
    r.es, r.di = _ds_far(mem, r, 0xA923)                         # 6B43
    r.al = rb(mem, r, 0x3E)                                      # 6B47
    r.ah = 0                                                     # 6B4B
    r.dx = r.ax                                                  # 6B4D
    r.ax = 5                                                     # 6B4F
    r.ax = r.ax - r.dx                                           # 6B52
    mem.wds8(0xAA, r.al, _at(0x6B54))
    r.al = 0xE                                                   # 6B57
    attr = r.ax
    r.di = 0xAA                                                  # 6B5A
    r.al = 0x19                                                  # 6B5F
    y = r.ax
    r.al = 0x34                                                  # 6B62
    x = r.ax
    r.di = 0xA96E                                                # 6B65
    r = yield from guest(mem, r, "214B:02C8", attr, ds, 0xAA, y, x, ds, 0xA96E, ret=_at(0x6B6F))
    back = _ds_far(mem, r, 0xA96E)                               # 6B6F
    video = _ds_far(mem, r, 0xA96A)                              # 6B75
    r.ax = 0xFA0                                                 # 6B7B
    r = yield from guest(mem, r, "23E4:025D", *back, *video, r.ax, ret=_at(0x6B84))
    r = yield from guest(mem, r, "214B:0723", ret=_at(0x6B89))
    if r.al:                                                     # 6B89 or al, al; je 6BD5
        r = yield from guest(mem, r, "214B:08DD", ret=_at(0x6B92))
        r.al = mem.ds8(0xA976)                                   # 6B92
        if r.al == 0xAE:                                         # 6B95 cmp al, 0xae; jne 6BAE
            r.es, r.di = _ds_far(mem, r, 0xA923)                 # 6B99
            if rb(mem, r, 0x3E) < 5:                             # 6B9D cmp byte ptr es:[di + 0x3e], 5; jae 6BAC
                r.es, r.di = _ds_far(mem, r, 0xA923)             # 6BA4
                w8(mem, r, 0x3E, rb(mem, r, 0x3E) + 1, _at(0x6BA8))
        elif r.al == 0xAF:                                       # 6BAE cmp al, 0xaf; jne 6BC7
            r.es, r.di = _ds_far(mem, r, 0xA923)                 # 6BB2
            if rb(mem, r, 0x3E) != 0:                            # 6BB6 cmp byte ptr es:[di + 0x3e], 0; jbe 6BC5
                r.es, r.di = _ds_far(mem, r, 0xA923)             # 6BBD
                w8(mem, r, 0x3E, rb(mem, r, 0x3E) - 1, _at(0x6BC1))
        elif r.al == 0x20:                                       # 6BC7 cmp al, 0x20; jne 6BD5
            r.di = 0x696A                                        # 6BCB
            r = yield from guest(mem, r, "214B:04F8", mem.seg(0x000E), 0x696A, ret=_at(0x6BD5))  # push cs; push di
    r.es, r.di = _ds_far(mem, r, 0xA923)                         # 6BD5
    r.al = rb(mem, r, 0x3E)                                      # 6BD9
    r.ah = 0                                                     # 6BDD
    waits = r.ax
    r.local16(-0x10, waits)                                      # 6BDF
    r.ax = 1                                                     # 6BE2
    if waits >= 1:                                               # 6BE5 cmp ax, word ptr [bp - 0x10]; ja 6C0C
        k = 1
        r.local16(-4, k)                                         # 6BEA
        while True:
            r = yield from guest(mem, r, "214B:0723", ret=_at(0x6BF7))
            if not r.al:                                         # 6BF7 or al, al; jne 6C04
                r.ax = 0x32                                      # 6BFB
                r = yield from guest(mem, r, "214B:1E09", r.ax, ret=_at(0x6C04))
            r.ax = k                                             # 6C04
            if k == waits:                                       # 6C07 cmp ax, word ptr [bp - 0x10]; jne 6BEF
                break
            k = (k + 1) & M16
            r.local16(-4, k)                                     # 6BEF
    parent = ss16(mem, r, r.bp + 4)                              # 6C0C mov di, word ptr [bp + 4]
    r.di = parent
    r._put(parent - 2, b"\x01")                                  # 6C0F mov byte ptr ss:[di - 2], 1
    r.flush()
    r.es, r.di = game                                            # 6C14
    w16(mem, r, 0x26, rw(mem, r, 0x26) + 1, _at(0x6C17))
    return _end(r)


@PORTS.port('0791:B15F',ret='ret 4')
def result_needs_winner(mem,variant):
    """T123 reached closure: named0791_10, raw0791_18 B15F..B19A."""
    from .setup import member
    from .runtime import sub_flags
    r=Regs(mem);r.enter(6);farg(mem,r,4);save_ptr(r,-5)
    r.di=ss16(mem,r,r.bp-5);r.es=ss16(mem,r,r.bp-3);r.al=rb(mem,r,2)
    r.di=0x693A
    r=yield from guest(mem,r,'23E4:08DF',r.ax,mem.DS,r.di,ret='B180')
    yes=False
    if member(mem):
        r.al=mem.ds8(0x9B3C);other=mem.ds8(0x9B3D);r.arith(sub_flags(r.al,other,8));yes=r.al==other
    r.al=int(yes);r.local8(-1,r.al);r.flush();r.al=mem.u8(mem.ss_lin(r.bp-1))
    return _end(r)
