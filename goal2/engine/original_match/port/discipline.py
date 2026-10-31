"""Fouls, cards, injuries and form; substitutions and the computer manager in play (T68, route C step P5a): the 20
routines of row T68.

Translated instruction by instruction from static/goal-exe/code/seg_0791_13.asm (7CC5-8205), seg_0791_14.asm
(82EB-835E), seg_0791_17.asm (A260-A374, A920-AC66), seg_0791_19.asm (BBFF-BC5C, BD03-BEC6, BF6B-C019, C173-C24C) and
seg_0791_20.asm (C5DC-CAAF), after the named view (named/seg_0791_07.c to _11.c) and the annotation rows; the line
comments are the listing's offsets. As T65's contests.py, T66's duels.py and T67's restarts.py, the routines are written
in the registers the listing uses (runtime.Regs), so the words they push for their callees (a byte pushed with `mov al, n;
push ax` keeps the AH of the instruction before), the words held on the guest stack across a call and the locals of the
frames are the original's (notes.md rule 2a).

Every call of the listing stays a guest call with its target, arguments, return address and near/far form, between these
routines too and to the callees of other rows: T73's notice 7FCF and its waits, the whistle 0441, the delay 0425, the
referee 9119 and 26C2; T74's team menu ED8A (8062 opens it for a managed side at a stoppage, so a decision there stops
the match under this port's frame, T59's mechanism, as anywhere else); T77's sending off 7B77, the penalty 6ECF, the
forced swap C48D and the computer's tactic routines C01A and C0DF; the commentary 1EB5, 230C, 2AA3, 2AD4, 2B28 and the
notice C50C; the 214B and 23E4 runtime and the 1771 player routines. A word pushed for a callee before an inner call
(7D56's C88D arguments around 2974; A9B8's and AAE8's string temporary around 23E4:075A, which leaves its pointer for
23E4:06E3) is pushed here too and handed to the outer call, which writes the same words at the same place.

The kit's events: 7D56's `inc byte ptr [di + 0x7b87]` is written as 7DD9 (match.py WRITERS["injury"]) and C5DC's `dec
byte ptr [di + 0x9b3a]` as C7DC (WRITERS["substitution"]); 8206's fouls count DS:7B84 + 10 side (8274) is outside the
kit's watch (STATS + 7 to + 9). The booking's 7A01 and the sending off's 7B6D are T67's and T77's.

The nested routines read their parent's frame through its BP, as the listing does: C7EB reads C88D's slot, side and
squad pointer (`mov di, [bp + 4]; ... ss:[di + k]`); BF6B gets C173's BP and reads nothing of it."""
from . import Registry
from .contests import guest, ss16, ss8, pop, own, rb, rw, player_record
from .geometry import cbw, cwd, mul, imul
from .restarts import wb, ww, arg8, arg16, _end
from .runtime import Regs
from .mem import s8, s16

PORTS = Registry("discipline", "fouls, cards, injuries and form; substitutions and the computer manager in play: "
                               "7CC5-835E, A260-A374, A920-AC66, BBFF-C24C, C5DC-CAAF, row T68's 20 routines (T68)")
PORTS.variant("form-delta-doubled", "7CC5 at 7CEB: the delta [bp+0xC] is added twice to the player's form +0xC")
PORTS.variant("offside-same-side", "82EB at 8350: DS:830B := DS:830C, the offender's own slot, not the other side's player")
PORTS.variant("run-direction-4", "A2E6 at A36A: the bound record's +0xF := 4, not 5")
PORTS.variant("tactics-gap-1", "C173 at C1B3: |DS:9B3C - DS:9B3D| is compared with 1, not 2 (a one-goal gap goes to C0DF / C01A)")
M16 = 0xFFFF


# -- the listing's idioms ------------------------------------------------------------------------------------------
def slot_of_byte(mem, r, byte):
    """`mov al, [byte]; xor ah, ah; mov dx, 0x16; mul dx; mov di, ax; add di, 0x80e8`: the pitch record of DS:byte's
    slot."""
    r.al = mem.ds8(byte)
    r.ah = 0
    r.dx = 0x16
    mul(r, r.dx)
    r.di = r.ax + 0x80E8
    return r.di


def slot_word(mem, r, byte):
    """`mov al, [byte]; xor ah, ah; mov dx, 0x16; mul dx; mov di, ax`; the word [di + 0x80f5]: the player word of DS:byte's
    pitch record."""
    r.al = mem.ds8(byte)
    r.ah = 0
    r.dx = 0x16
    mul(r, r.dx)
    r.di = r.ax
    return mem.ds16((r.di + 0x80F5) & M16)


def side_index(r, side):
    """`mov al, side; cbw; mov di, ax`."""
    r.al = side
    cbw(r)
    r.di = r.ax


def squad_of_side(mem, r, side):
    """`mov al, side; cbw; mov di, ax; shl di, 1`; the word [di + 0x9b34]: the side's country."""
    side_index(r, side)
    r.di = r.di << 1
    return mem.ds16((r.di + 0x9B34) & M16)


def country_record(mem, r):
    """`mov dx, 0xbf; mul dx; les di, [0xa917]; add di, ax`: the country record of AX."""
    r.dx = 0xBF
    mul(r, r.dx)
    r.di, r.es = mem.ds16(0xA917), mem.ds16(0xA919)
    r.di = r.di + r.ax


def player_of_ax(mem, r):
    """`mov dx, 0x14; mul dx; les di, [0xa91b]; add di, ax`: the player record of the word AX."""
    r.dx = 0x14
    mul(r, r.dx)
    r.di, r.es = mem.ds16(0xA91B), mem.ds16(0xA91D)
    r.di = r.di + r.ax


def word_at(mem, r, seg, off, k):
    """`mov ax, k; shl ax, 1; les di, [far]; add di, ax`; the word es:[di - 2]: word k of a 1-based word array."""
    r.ax = k << 1
    r.es, r.di = seg, off
    r.di = r.di + r.ax
    return mem.u16(mem.addr(r.es, r.di - 2))


def first_slot(mem, r, side):
    """`mov al, side; cbw; mov di, ax; mov al, [di + 0x668]; xor ah, ah`: the side's slot before its first."""
    side_index(r, side)
    r.al = mem.ds8((r.di + 0x668) & M16)
    r.ah = 0


def flip_side(r, side):
    """`cmp side, 0; je +4; mov al, 0; jmp +2; mov al, 1`: the other side (AL)."""
    r.al = 0 if side else 1


def set_dl(r, value):
    r.dx = (r.dx & 0xFF00) | (value & 0xFF)


def set_cl(r, value):
    r.cx = (r.cx & 0xFF00) | (value & 0xFF)


# -- 7CC5 ----------------------------------------------------------------------------------------------------------
@PORTS.port("0791:7CC5", ret="retf 8")
def adjust_player_form(mem, variant):
    """7CC5-7D53 (the record [bp+6], flag [bp+0xA], delta [bp+0xC]): the player's form +0xC := clamp(s8(+0xC) + delta,
    1, 0xFF) (214B:2000 on the argument word); with the flag set, DS:9B07 + 20 side + slot-in-side := min(the new form,
    0x20) (214B:0D1C on the sign-extended long)."""
    r = Regs(mem)
    r.enter(4)                                                   # 7CC5-7CC8
    own(mem, r)                                                  # 7CCB
    player_record(mem, r)                                        # 7CCE-7CDB
    pseg, poff = r.es, r.di
    r.local16(-4, poff)                                          # 7CDD
    r.local16(-2, pseg)                                          # 7CE0
    r.al = rb(mem, r, 0xC)                                       # 7CE6
    cbw(r)
    r.ax = r.ax + arg16(mem, r, 0xC)                             # 7CEB
    if variant == "form-delta-doubled":
        r.ax = r.ax + arg16(mem, r, 0xC)
    r.local16(0xC, r.ax)                                         # 7CEE
    r.di = r.bp + 0xC                                            # 7CF1 lea di, [bp + 0xc]
    r.ax = 1                                                     # 7CF6
    r.ax = 0xFF                                                  # 7CFA
    r = yield from guest(mem, r, "214B:2000", r.ss, r.di, 1, 0xFF, ret="7D03")
    r.al = ss8(mem, r, r.bp + 0xC)                               # 7D03
    r.es, r.di = pseg, poff                                      # 7D06
    wb(mem, r, 0xC, r.al, "7D09")
    if arg8(mem, r, 0xA) == 0:                                   # 7D0D cmp byte ptr [bp + 0xa], 0; je 7D50
        return _end(r)
    r.es, r.di = pseg, poff                                      # 7D13
    r.al = rb(mem, r, 0xC)                                       # 7D16
    cbw(r)
    cwd(r)                                                       # 7D1B
    high, low = r.dx, r.ax
    r.ax = 0x20                                                  # 7D1E
    r.dx = 0                                                     # 7D21
    r = yield from guest(mem, r, "214B:0D1C", high, low, 0, 0x20, ret="7D2A")
    r.push(r.ax)                                                 # 7D2A: the minimum, live across two calls
    seg, off = own(mem, r)                                       # 7D2B
    r = yield from guest(mem, r, "2BB1", seg, off, ret="7D34")
    r.ah = 0                                                     # 7D34
    r.push(r.ax)                                                 # 7D36: the slot in its side, live across 2974
    seg, off = own(mem, r)                                       # 7D37
    r = yield from guest(mem, r, "2974", seg, off, ret="7D40")
    cbw(r)                                                       # 7D40-7D46
    r.dx = 0x14
    mul(r, r.dx)
    r.di = r.ax
    r.ax = pop(mem, r)                                           # 7D48
    r.di = r.di + r.ax
    r.ax = pop(mem, r)                                           # 7D4B
    mem.wds8(r.di + 0x9B07, r.al, "0791:7D4C")                   # [di - 0x64f9]
    return _end(r)


# -- 7D56 ----------------------------------------------------------------------------------------------------------
@PORTS.port("0791:7D56", ret="retf 4")
def injure(mem, variant):
    """7D56-7E5D (the record [bp+6]): unless the record is unavailable (2956) or its side may lose no more players
    (7A43): line 0x34 (2B28), the player's +0xE := 0, the walk off (7881), the form -2 with the shadow (7CC5(-2, 1)),
    DS:8321 +1 up to 5, the side's injuries DS:7B87 + 10 side +1 (7DD9, the kit's injury event); an unmanaged side
    substitutes him (C88D(1)); a managed side gets DS:9B40 := 1 (8062's notice) unless he is not a keeper and it has no
    substitution left (DS:9B3A + side)."""
    r = Regs(mem)
    r.enter(4)                                                   # 7D56-7D59
    seg, off = own(mem, r)                                       # 7D5C
    r = yield from guest(mem, r, "2956", seg, off, ret="7D65")
    go = False
    if r.al == 0:                                                # 7D65 or al, al; jne 7D7A
        seg, off = own(mem, r)                                   # 7D69
        r = yield from guest(mem, r, "2974", seg, off, ret="7D72")
        r = yield from guest(mem, r, "7A43", r.ax, ret="7D76", far=False)
        go = r.al != 0                                           # 7D76 or al, al; jne 7D7D
    if not go:
        return _end(r)                                           # 7D7A jmp 7E5A
    r.al = 0x34                                                  # 7D7D
    line = r.ax
    seg, off = own(mem, r)                                       # 7D80
    r = yield from guest(mem, r, "2B28", line, seg, off, ret="7D89")
    own(mem, r)                                                  # 7D89
    player_record(mem, r)                                        # 7D8C-7D99
    wb(mem, r, 0xE, 0, "7D9B")
    own(mem, r)                                                  # 7DA0
    r.al = rb(mem, r, 6)
    r.ah = 0
    r = yield from guest(mem, r, "7881", r.ax, ret="7DAD", far=False)
    r.ax = 0xFFFE                                                # 7DAD
    delta = r.ax
    r.al = 1                                                     # 7DB1
    flag = r.ax
    seg, off = own(mem, r)                                       # 7DB4
    r = yield from guest(mem, r, "7CC5", delta, flag, seg, off, ret="7DBD")
    if mem.ds16(0x8321) < 5:                                     # 7DBD cmp word ptr [0x8321], 5; jae 7DC8
        mem.wds16(0x8321, mem.ds16(0x8321) + 1, "0791:7DC4")
    seg, off = own(mem, r)                                       # 7DC8
    r = yield from guest(mem, r, "2974", seg, off, ret="7DD1")
    cbw(r)                                                       # 7DD1-7DD7
    r.dx = 0xA
    mul(r, r.dx)
    r.di = r.ax
    mem.wds8(r.di + 0x7B87, mem.ds8((r.di + 0x7B87) & M16) + 1, "0791:7DD9")   # the injury
    own(mem, r)                                                  # 7DDD
    player_record(mem, r)                                        # 7DE0-7DED
    pseg, poff = r.es, r.di
    r.local16(-4, poff)                                          # 7DEF
    r.local16(-2, pseg)                                          # 7DF2
    r.al = rb(mem, r, 0)                                         # 7DF8
    r.ah = 0
    r = yield from guest(mem, r, "1771:0B77", r.ax, ret="7E03")
    if r.al == 0:                                                # 7E03 or al, al; jne 7E38
        r.es, r.di = pseg, poff                                  # 7E07
        r.al = rb(mem, r, 0)
        r.ah = 0
        country_record(mem, r)                                   # 7E0F-7E18
        squad_seg, squad_off = r.es, r.di
        r.push(squad_seg)                                        # 7E1A
        r.push(squad_off)                                        # 7E1B
        own(mem, r)                                              # 7E1C
        r.al = rb(mem, r, 6)
        r.ah = 0
        slot = r.ax
        r.push(slot)                                             # 7E25
        seg, off = own(mem, r)                                   # 7E26
        r = yield from guest(mem, r, "2974", seg, off, ret="7E2F")
        side = r.ax                                              # 7E2F push ax
        r.al = 1                                                 # 7E30
        r.sp = r.sp + 6                                          # the words of 7E1A-7E25 are C88D's first three
        r = yield from guest(mem, r, "C88D", squad_seg, squad_off, slot, side, r.ax, ret="7E36", far=False)
        return _end(r)                                           # 7E36 jmp 7E5A
    r.es, r.di = pseg, poff                                      # 7E38
    notice = True
    if rb(mem, r, 6) != 0:                                       # 7E3B cmp byte ptr es:[di + 6], 0; je 7E55
        seg, off = own(mem, r)                                   # 7E42
        r = yield from guest(mem, r, "2974", seg, off, ret="7E4B")
        cbw(r)                                                   # 7E4B
        r.di = r.ax
        notice = mem.ds8((r.di + 0x9B3A) & M16) > 0              # 7E4E cmp byte ptr [di - 0x64c6], 0; jbe 7E5A
    if notice:
        mem.wds8(0x9B40, 1, "0791:7E55")
    return _end(r)


# -- 7E60 ----------------------------------------------------------------------------------------------------------
@PORTS.port("0791:7E60", ret="ret 2")
def foul_whistle(mem, variant):
    """7E60-7EEC (flag [bp+4]): DS:8325 := 0 (the clock stops), the whistle 0441(4), ten passes of DS:830B's and
    DS:830C's pictures (8537), each with the delay 0425(4 * the speed setting), and the referee 9119(flag, DS:82EE); then
    26C2 and DS:830A := 0."""
    r = Regs(mem)
    r.enter(2)                                                   # 7E60-7E63
    mem.wds8(0x8325, 0, "0791:7E66")
    r.ax = 4                                                     # 7E6B
    r = yield from guest(mem, r, "0441", 4, ret="7E72", far=False)
    k = 1
    r.local16(-2, k)                                             # 7E72
    while True:
        for byte, after_picture, after_delay in ((0x830B, "7E92", "7EA5"), (0x830C, "7EBB", "7ECE")):
            rec = slot_of_byte(mem, r, byte)                     # 7E7C-7E88 / 7EA5-7EB1
            r = yield from guest(mem, r, "8537", mem.DS, rec, ret=after_picture)
            r.di, r.es = mem.ds16(0xA923), mem.ds16(0xA925)      # 7E92 / 7EBB
            r.al = rb(mem, r, 0x3F)
            r.ah = 0
            r.cx = 2
            r.ax = r.ax << 2                                     # shl ax, cl
            r = yield from guest(mem, r, "0425", r.ax, ret=after_delay, far=False)
        r.al = arg8(mem, r, 4)                                   # 7ECE
        r.di = 0x82EE                                            # 7ED2
        r = yield from guest(mem, r, "9119", r.ax, mem.DS, 0x82EE, ret="7EDB")
        if k == 0xA:                                             # 7EDB cmp word ptr [bp - 2], 0xa; jne 7E79
            break
        k += 1
        r.local16(-2, k)                                         # 7E79
    r = yield from guest(mem, r, "26C2", ret="7EE4", far=False)
    mem.wds8(0x830A, 0, "0791:7EE4")
    return _end(r)


# -- 7EEF ----------------------------------------------------------------------------------------------------------
@PORTS.port("0791:7EEF", ret="ret")
def foul_dispatch(mem, variant):
    """7EEF-7FCE: the fouler DS:830C: a table byte (261A) below 4 books him (798D), or sends him off (7B77) when his
    status +0x10 has element 5 (a booking already); else a chance 1/0x20 (214B:06D0) sends him off. Then a table byte of
    1 injures (7D56) the one of DS:830C and DS:830B of lower hardness (1771:2FFB), DS:830B on a tie."""
    r = Regs(mem)
    r.enter(4)                                                   # 7EEF-7EF2
    rec = slot_of_byte(mem, r, 0x830C)                           # 7EF5-7F01
    r.local16(-4, rec)                                           # 7F05
    r.local16(-2, mem.DS)                                        # 7F08
    r = yield from guest(mem, r, "261A", ret="7F0E", far=False)
    if s16(r.ax) < 4:                                            # 7F0E cmp ax, 4; jge 7F4F
        r.ax = 5                                                 # 7F13 (push ax)
        r.es, r.di = mem.DS, rec                                 # 7F17
        player_record(mem, r)                                    # 7F1A-7F27
        r.al = rb(mem, r, 0x10)                                  # 7F29
        r.ah = 0
        r = yield from guest(mem, r, "214B:0C57", 5, r.ax, ret="7F35")
        r.es, r.di = mem.DS, rec                                 # 7F39 / 7F44
        if r.al:                                                 # 7F35 or al, al; je 7F44
            r = yield from guest(mem, r, "7B77", mem.DS, rec, ret="7F42")
        else:
            r = yield from guest(mem, r, "798D", mem.DS, rec, ret="7F4D")
    else:
        r.ax = 0x20                                              # 7F4F
        r = yield from guest(mem, r, "214B:06D0", 0x20, ret="7F58")
        if r.al:                                                 # 7F58 or al, al; je 7F65
            r.es, r.di = mem.DS, rec                             # 7F5C
            r = yield from guest(mem, r, "7B77", mem.DS, rec, ret="7F65")
    r = yield from guest(mem, r, "261A", ret="7F68", far=False)
    if r.ax == 1:                                                # 7F68 cmp ax, 1; jne 7FCB
        word = slot_word(mem, r, 0x830C)                         # 7F6D-7F79
        r = yield from guest(mem, r, "1771:2FFB", word, ret="7F82")
        r.push(r.ax)                                             # 7F82: the fouler's hardness, live across 2FFB
        word = slot_word(mem, r, 0x830B)                         # 7F83-7F8F
        r = yield from guest(mem, r, "1771:2FFB", word, ret="7F98")
        r.dx = pop(mem, r)                                       # 7F98
        if r.al > (r.dx & 0xFF):                                 # 7F99 cmp al, dl; jbe 7FB5
            rec = slot_of_byte(mem, r, 0x830C)                   # 7F9D-7FA9
            r = yield from guest(mem, r, "7D56", mem.DS, rec, ret="7FB3")
        else:
            rec = slot_of_byte(mem, r, 0x830B)                   # 7FB5-7FC1
            r = yield from guest(mem, r, "7D56", mem.DS, rec, ret="7FCB")
    return _end(r)


# -- 8062 ----------------------------------------------------------------------------------------------------------
@PORTS.port("0791:8062", ret="ret")
def check_substitutions(mem, variant):
    """8062-8205: for side 0 then 1. A managed side (1771:0B77), with DS:9B40 set: when its keeper is unavailable
    (1771:3216 of slot DS:0668[side] + 1), or when the clock runs (DS:831B + DS:8321) and it has substitutions left
    (DS:9B3A + side), DS:9B41 := 1 if it has some, 214B:1E8D, the notice 7FCF(side, keeper) and, unless the notice was
    left with Esc for an available keeper, the team menu ED8A(1); then DS:9B41 := 0. A computer side with substitutions
    left: squad slots k = 11 down to 1; a player whose status has no element 6, with +0xE > 0, when 1 < DS:831B < 0x23,
    k > 1 and his signed +0x12 < 0x5A - DS:831B, is substituted (C88D(0)); the scan ends when none is left."""
    r = Regs(mem)
    r.enter(0xC)                                                 # 8062-8065
    side = 0
    r.local8(-1, side)                                           # 8068
    while True:
        squad = squad_of_side(mem, r, side)                      # 8071-8079
        r = yield from guest(mem, r, "1771:0B77", squad, ret="8082")
        if r.al:                                                 # 8082 or al, al; jne 8089
            first_slot(mem, r, side)                             # 8089-8093
            r.ax = r.ax + 1                                      # 8095 inc ax
            r.dx = 0x16
            mul(r, r.dx)
            r.di = r.ax
            word = mem.ds16((r.di + 0x80F5) & M16)               # 809D push word ptr [di - 0x7f0b]
            r = yield from guest(mem, r, "1771:3216", word, ret="80A6")
            keeper = r.al
            r.local8(-4, keeper)                                 # 80A6
            notice = False
            if mem.ds8(0x9B40) != 0:                             # 80A9 cmp byte ptr [0x9b40], 0; je 8108
                if keeper != 0:                                  # 80B0 jne 80CE
                    notice = True
                else:
                    r.ax = mem.ds16(0x831B)                      # 80B6
                    r.ax = r.ax + mem.ds16(0x8321)
                    if r.ax != 0:                                # 80BD or ax, ax; jbe 8108
                        side_index(r, side)                      # 80C1-80C5
                        notice = mem.ds8((r.di + 0x9B3A) & M16) > 0     # 80C7 jbe 8108
            if notice:
                side_index(r, side)                              # 80CE-80D2
                if mem.ds8((r.di + 0x9B3A) & M16) > 0:           # 80D4 jbe 80E0
                    mem.wds8(0x9B41, 1, "0791:80DB")
                r = yield from guest(mem, r, "214B:1E8D", ret="80E5")
                r.al = keeper                                    # 80E5
                first = r.ax
                r.al = side                                      # 80E9
                r = yield from guest(mem, r, "7FCF", first, r.ax, ret="80F0", far=False)
                if mem.ds8(0xA977) != 0x1B or keeper != 0:       # 80F0 cmp [0xa977], 0x1b; jne 80FD; cmp; je 8103
                    r.al = 1                                     # 80FD
                    r = yield from guest(mem, r, "ED8A", r.ax, ret="8103", far=False)
                mem.wds8(0x9B41, 0, "0791:8103")
        else:
            side_index(r, side)                                  # 810B-810F
            if mem.ds8((r.di + 0x9B3A) & M16) > 0:               # 8111 cmp byte ptr [di - 0x64c6], 0; ja 811B
                k = 0xB
                r.local16(-3, k)                                 # 811B
                while True:
                    first_slot(mem, r, side)                     # 8125-812F
                    r.ax = r.ax + k                              # 8131
                    r.dx = 0x16
                    mul(r, r.dx)
                    r.di = r.ax + 0x80E8                         # 8139-813B
                    rec = r.di
                    r.local16(-8, rec)                           # 813F
                    r.local16(-6, mem.DS)                        # 8142
                    r.es = mem.DS                                # 8145 les di, [bp - 8]
                    player_record(mem, r)                        # 8148-8155
                    pseg, poff = r.es, r.di
                    r.local16(-0xC, poff)                        # 8157
                    r.local16(-0xA, pseg)                        # 815A
                    r.ax = 6                                     # 815D (push ax)
                    r.al = rb(mem, r, 0x10)                      # 8164
                    r.ah = 0
                    r = yield from guest(mem, r, "214B:0C57", 6, r.ax, ret="8170")
                    if r.al == 0:                                # 8170 or al, al; jne 81F0
                        r.es, r.di = pseg, poff                  # 8174
                        take = (s8(rb(mem, r, 0xE)) > 0          # 8177 cmp byte ptr es:[di + 0xe], 0; jle 81F0
                                and mem.ds16(0x831B) > 1         # 817E cmp word ptr [0x831b], 1; jbe 81F0
                                and k > 1                        # 8185 cmp word ptr [bp - 3], 1; jbe 81F0
                                and mem.ds16(0x831B) < 0x23)     # 818B cmp word ptr [0x831b], 0x23; jae 81F0
                        if take:
                            r.ax = 0x5A - mem.ds16(0x831B)       # 8192-8195
                            r.dx = 0                             # 8199
                            r.cx = r.ax
                            r.bx = r.dx
                            r.es, r.di = pseg, poff              # 819F
                            r.ax = rw(mem, r, 0x12)              # 81A2
                            cwd(r)                               # 81A6
                            take = (s16(r.dx) < s16(r.bx)        # 81A7 cmp dx, bx; jl 81B1; jg 81F0
                                    or (r.dx == r.bx and r.ax < r.cx))     # 81AD cmp ax, cx; jae 81F0
                        if take:
                            r.ax = squad_of_side(mem, r, side)   # 81B1-81B9
                            country_record(mem, r)               # 81BD-81C6
                            squad_seg, squad_off = r.es, r.di
                            r.es, r.di = mem.DS, rec             # 81CA
                            r.al = rb(mem, r, 6)
                            r.ah = 0
                            slot = r.ax
                            r.al = side                          # 81D4
                            side_word = r.ax
                            r.al = 0                             # 81D8
                            r = yield from guest(mem, r, "C88D", squad_seg, squad_off, slot, side_word, r.ax,
                                                 ret="81DE", far=False)
                            side_index(r, side)                  # 81DE-81E2
                            if mem.ds8((r.di + 0x9B3A) & M16) == 0:     # 81E4 jne 81F0
                                k = 1
                                r.local16(-3, k)                 # 81EB
                    if k == 1:                                   # 81F0 cmp word ptr [bp - 3], 1; je 81F9
                        break
                    k -= 1
                    r.local16(-3, k)                             # 8122 dec word ptr [bp - 3]
        if side == 1:                                            # 81F9 cmp byte ptr [bp - 1], 1; je 8202
            break
        side += 1
        r.local8(-1, side)                                       # 806E inc byte ptr [bp - 1]
    return _end(r)


# -- 8206 ----------------------------------------------------------------------------------------------------------
@PORTS.port("0791:8206", ret="ret 2")
def watched_foul_sequence(mem, variant):
    """8206-82E8 (the fouler's slot [bp+4]): DS:830C := DS:830D := the slot; no foul when his record is at his own
    position (2EB8) and a coin (214B:06FA) holds; else lines 0x37 (2AA3) and 0x35 (2AD4), the whistle 7E60(1), the
    fouling side's fouls DS:7B84 + 10 side +1 (8274), the cards and injuries 7EEF; then, with the ball in his own
    penalty area (2EB8 of DS:82F6), an unmanaged fouler's own tactic off (1771:33CD) and the penalty 6ECF; else the free
    kick 6FB6."""
    r = Regs(mem)
    r.enter(6)                                                   # 8206-8209
    r.al = arg8(mem, r, 4)                                       # 820C
    mem.wds8(0x830C, r.al, "0791:820F")
    mem.wds8(0x830D, r.al, "0791:8215")                          # 8212-8215
    rec = slot_of_byte(mem, r, 0x830C)                           # 8218-8224
    r.local16(-5, rec)                                           # 8228
    r.local16(-3, mem.DS)                                        # 822B
    r.es = mem.DS                                                # 822E les di, [bp - 5]
    word = rw(mem, r, 0)                                         # 8231 push word ptr es:[di]
    r = yield from guest(mem, r, "2EB8", word, mem.DS, rec, ret="823D")
    if r.al:                                                     # 823D or al, al; je 824D
        r = yield from guest(mem, r, "214B:06FA", ret="8246")
        if r.al:                                                 # 8246 or al, al; je 824D
            return _end(r)                                       # 824A jmp 82E5
    r.al = 0x37                                                  # 824D
    r = yield from guest(mem, r, "2AA3", r.ax, ret="8253", far=False)
    r.al = 0x35                                                  # 8253
    r = yield from guest(mem, r, "2AD4", r.ax, ret="8259", far=False)
    r.al = 1                                                     # 8259
    r = yield from guest(mem, r, "7E60", r.ax, ret="825F", far=False)
    r.al = 1 if mem.ds8(0x830C) < 0xC else 0                     # 825F cmp byte ptr [0x830c], 0xc; jb 826A
    cbw(r)                                                       # 826C-8272
    r.dx = 0xA
    mul(r, r.dx)
    r.di = r.ax
    mem.wds8(r.di + 0x7B84, mem.ds8((r.di + 0x7B84) & M16) + 1, "0791:8274")    # the fouls count
    ball = mem.ds16(0x82F6)                                      # 8278 push word ptr [0x82f6]
    rec = slot_of_byte(mem, r, 0x830C)                           # 827C-8288
    r = yield from guest(mem, r, "2EB8", ball, mem.DS, rec, ret="8292")
    in_area = r.al
    r.local8(-1, in_area)                                        # 8292
    r = yield from guest(mem, r, "7EEF", ret="8298", far=False)
    if in_area:                                                  # 8298 cmp byte ptr [bp - 1], 0; je 82E2
        word = slot_word(mem, r, 0x830C)                         # 829E-82AA mov ax, word ptr [di - 0x7f0b]
        r.ax = word
        player_of_ax(mem, r)                                     # 82AE-82B7
        r.al = rb(mem, r, 0)                                     # 82B9
        r.ah = 0
        r = yield from guest(mem, r, "1771:0B77", r.ax, ret="82C4")
        if r.al == 0:                                            # 82C4 or al, al; jne 82DD
            word = slot_word(mem, r, 0x830C)                     # 82C8-82D4
            r = yield from guest(mem, r, "1771:33CD", word, ret="82DD")
        r = yield from guest(mem, r, "6ECF", ret="82E0", far=False)
    else:
        r = yield from guest(mem, r, "6FB6", ret="82E5", far=False)
    return _end(r)


# -- 82EB ----------------------------------------------------------------------------------------------------------
@PORTS.port("0791:82EB", ret="ret")
def offside(mem, variant):
    """82EB-835E: offside of DS:830E: DS:830C := DS:830E, DS:830D := 0, line 0x36 (2AD4), 26A0(2BE5 < 0), the whistle
    7E60(0), the ball DS:82F6 := DS:8317, DS:830B := DS:830C + 0xB * DS:7920[DS:830C < 0xC] (the other side's player of
    the same place), 2FB1 and the free kick 6FB6."""
    r = Regs(mem)
    r.enter(0)                                                   # 82EB-82EC
    r.al = mem.ds8(0x830E)                                       # 82EE
    mem.wds8(0x830C, r.al, "0791:82F1")
    mem.wds8(0x830D, 0, "0791:82F4")
    r.al = 0x36                                                  # 82F9
    r = yield from guest(mem, r, "2AD4", r.ax, ret="82FF", far=False)
    rec = slot_of_byte(mem, r, 0x830C)                           # 82FF-830B
    r = yield from guest(mem, r, "2BE5", mem.DS, rec, ret="8315")
    r.al = 1 if s8(r.al) < 0 else 0                              # 8315 or al, al; jl 831D
    r = yield from guest(mem, r, "26A0", r.ax, ret="8323", far=False)
    r.al = 0                                                     # 8323
    r = yield from guest(mem, r, "7E60", r.ax, ret="8329", far=False)
    r.ax = mem.ds16(0x8317)                                      # 8329
    mem.wds16(0x82F6, r.ax, "0791:832C")
    r.al = 1 if mem.ds8(0x830C) < 0xC else 0                     # 832F cmp byte ptr [0x830c], 0xc; jb 833A
    cbw(r)                                                       # 833C-833F
    r.di = r.ax
    r.al = mem.ds8((r.di + 0x7920) & M16)
    cbw(r)                                                       # 8343
    r.cx = 0xB
    imul(r, r.cx)                                                # 8347
    r.dx = r.ax                                                  # 8349
    r.al = mem.ds8(0x830C)                                       # 834B
    r.ah = 0
    if variant != "offside-same-side":
        r.ax = r.ax + r.dx                                       # 8350
    mem.wds8(0x830B, r.al, "0791:8352")
    r = yield from guest(mem, r, "2FB1", ret="8358", far=False)
    r = yield from guest(mem, r, "6FB6", ret="835B", far=False)
    return _end(r)


# -- A260 ----------------------------------------------------------------------------------------------------------
@PORTS.port("0791:A260", ret="retf 6")
def bind_pitch_player(mem, variant):
    """A260-A2E3 (the record [bp+6], slot [bp+0xA]): +6 := the slot, the player word +0xD := the side's squad word of the
    slot in its side (2BB1, 2974), the keeping extra +0x11 := 1771:0AA7(his country) + 0x20, +0x13 := 1771:3179(him)."""
    r = Regs(mem)
    r.enter(0)                                                   # A260-A261
    r.al = arg8(mem, r, 0xA)                                     # A263
    own(mem, r)                                                  # A266
    wb(mem, r, 6, r.al, "A269")
    seg, off = own(mem, r)                                       # A26D
    r = yield from guest(mem, r, "2BB1", seg, off, ret="A276")
    r.ah = 0                                                     # A276
    r.ax = r.ax << 1                                             # A278
    r.push(r.ax)                                                 # A27A: the doubled index, live across 2974
    seg, off = own(mem, r)                                       # A27B
    r = yield from guest(mem, r, "2974", seg, off, ret="A284")
    r.ax = squad_of_side(mem, r, r.al)                           # A284-A289 (cbw on AL: 2974's answer)
    country_record(mem, r)                                       # A28D-A296
    r.ax = pop(mem, r)                                           # A298
    r.di = r.di + r.ax
    r.ax = mem.u16(mem.addr(r.es, r.di - 2))                     # A29B
    own(mem, r)                                                  # A29F
    ww(mem, r, 0xD, r.ax, "A2A2")
    own(mem, r)                                                  # A2A6
    r.ax = rw(mem, r, 0xD)
    player_of_ax(mem, r)                                         # A2AD-A2B6
    r.al = rb(mem, r, 0)                                         # A2B8
    r.ah = 0
    r = yield from guest(mem, r, "1771:0AA7", r.ax, ret="A2C3")
    r.ax = r.ax + 0x20                                           # A2C3
    own(mem, r)                                                  # A2C6
    wb(mem, r, 0x11, r.al, "A2C9")
    own(mem, r)                                                  # A2CD
    r = yield from guest(mem, r, "1771:3179", rw(mem, r, 0xD), ret="A2D9")
    own(mem, r)                                                  # A2D9
    wb(mem, r, 0x13, r.al, "A2DC")
    return _end(r)


# -- A2E6 ----------------------------------------------------------------------------------------------------------
@PORTS.port("0791:A2E6", ret="retf 6")
def initialize_pitch_player(mem, variant):
    """A2E6-A372 (the record [bp+6], slot [bp+0xA]): A260; the point +0 and +2 := DS:0644; +5 := DS:8330[side] when the
    slot is a goalkeeper's (045D: 1 or 12), else DS:832E[side]; +0xB := DS:063E, +0x10 := 0, +0x14 := 0, +0xF := 5."""
    r = Regs(mem)
    r.enter(0)                                                   # A2E6-A2E7
    slot = arg16(mem, r, 0xA)                                    # A2E9 push word ptr [bp + 0xa]
    seg, off = own(mem, r)                                       # A2EC
    r = yield from guest(mem, r, "A260", slot, seg, off, ret="A2F5")
    r.ax = mem.ds16(0x644)                                       # A2F5
    own(mem, r)
    ww(mem, r, 0, r.ax, "A2FB")
    own(mem, r)                                                  # A2FE
    r.ax = rw(mem, r, 0)
    own(mem, r)                                                  # A304
    ww(mem, r, 2, r.ax, "A307")
    own(mem, r)                                                  # A30B
    r.al = rb(mem, r, 6)
    r.ah = 0
    r = yield from guest(mem, r, "045D", r.ax, ret="A318", far=False)
    table = 0x8330 if r.al else 0x832E                           # A318 or al, al; je A335 ([di - 0x7cd0] / [di - 0x7cd2])
    seg, off = own(mem, r)                                       # A31C / A335
    r = yield from guest(mem, r, "2974", seg, off, ret="A325" if table == 0x8330 else "A33E")
    cbw(r)
    r.di = r.ax
    r.al = mem.ds8((r.di + table) & M16)                         # A328 / A341
    own(mem, r)
    wb(mem, r, 5, r.al, "A32F" if table == 0x8330 else "A348")
    r.ax = mem.ds16(0x63E)                                       # A34C
    own(mem, r)
    ww(mem, r, 0xB, r.ax, "A352")
    own(mem, r)                                                  # A356
    wb(mem, r, 0x10, 0, "A359")
    own(mem, r)                                                  # A35E
    r.ax = 0                                                     # A361
    ww(mem, r, 0x14, 0, "A363")
    own(mem, r)                                                  # A367
    wb(mem, r, 0xF, 4 if variant == "run-direction-4" else 5, "A36A")
    return _end(r)


# -- A920 ----------------------------------------------------------------------------------------------------------
@PORTS.port("0791:A920", ret="ret 2")
def pitch_slot_of_player(mem, variant):
    """A920-A9B5 (the player word [bp+4]): his index k in 1..11 of his country's squad words (the last that is his; 0
    when none), plus the first-slot byte DS:0668[his country is DS:9B36] when he is among them: his pitch slot."""
    r = Regs(mem)
    r.enter(0xA)                                                 # A920-A923
    word = arg16(mem, r, 4)
    r.ax = word                                                  # A926
    player_of_ax(mem, r)                                         # A929-A932
    r.al = rb(mem, r, 0)                                         # A934
    r.ah = 0
    country_record(mem, r)                                       # A939-A942
    sq_seg, sq_off = r.es, r.di
    r.local16(-0xA, sq_off)                                      # A944
    r.local16(-8, sq_seg)                                        # A947
    r.ax = 0                                                     # A94A
    found = 0
    r.local16(-6, found)
    k = 1
    r.local16(-4, k)                                             # A94F
    while True:
        r.ax = word_at(mem, r, sq_seg, sq_off, k)                # A959-A963
        if r.ax == word:                                         # A967 cmp ax, [bp + 4]; jne A972
            r.ax = k                                             # A96C
            found = k
            r.local16(-6, found)
        if k == 0xB:                                             # A972 cmp word ptr [bp - 4], 0xb; jne A956
            break
        k += 1
        r.local16(-4, k)                                         # A956
    if found != 0:                                               # A978 cmp word ptr [bp - 6], 0; je A9A9
        r.ax = word                                              # A97E
        player_of_ax(mem, r)                                     # A981-A98A
        r.al = rb(mem, r, 0)                                     # A98C
        r.ah = 0
        r.al = 1 if r.ax == mem.ds16(0x9B36) else 0              # A991 cmp ax, [0x9b36]; je A99B
        cbw(r)                                                   # A99D
        r.di = r.ax
        r.al = mem.ds8((r.di + 0x668) & M16)                     # A9A0
        r.ah = 0
        found = (found + r.ax) & M16                             # A9A6 add word ptr [bp - 6], ax
        r.local16(-6, found)
    r.ax = found                                                 # A9A9
    r.local16(-2, found)                                         # A9AC
    r.ax = found                                                 # A9AF
    return _end(r, value=True)


# -- A9B8 ----------------------------------------------------------------------------------------------------------
@PORTS.port("0791:A9B8", ret="ret 6")
def pick_best_bench_keeper(mem, variant):
    """A9B8-AAE5 (country [bp+8], position [bp+6], last [bp+4]): over squad slots k = 12..last of the country, the
    available one (1771:3216) with the highest DS:08D5[14 * position + his role +7], halved when the position's foot
    (Pos(the position's character, DS:08CE) > 3; no foot for Pos 0) is not his (1771:3041 not two-footed, 1771:3088
    his foot); the first of equals; 0 when none."""
    r = Regs(mem)
    r.enter(0x110)                                               # A9B8-A9BB
    last, position, country = arg16(mem, r, 4), arg16(mem, r, 6), arg16(mem, r, 8)
    r.ax = country                                               # A9BF
    country_record(mem, r)                                       # A9C2-A9CB
    sq_seg, sq_off = r.es, r.di
    r.local16(-0x10, sq_off)                                     # A9CD
    r.local16(-0xE, sq_seg)                                      # A9D0
    r.ax = 0                                                     # A9D3
    best = 0
    r.local16(-4, best)
    best_value = 0                                               # A9D8
    r.local16(-8, best_value)
    temp = (r.bp - 0x110) & M16                                  # A9DD lea di, [bp - 0x110]
    r.di = temp
    r.push(r.ss)                                                 # A9E1
    r.push(temp)                                                 # A9E2
    r.al = position                                              # A9E3
    r = yield from guest(mem, r, "23E4:075A", r.ax, ret="A9EC")
    r.di = 0x8CE                                                 # A9EC
    r.sp = r.sp + 4                                              # the string 075A left (A9E1-A9E2): 06E3's first
    r = yield from guest(mem, r, "23E4:06E3", r.ss, temp, mem.DS, 0x8CE, ret="A9F6")
    pos = r.ax
    r.local16(-0xC, pos)                                         # A9F6
    r.ax = last                                                  # A9F9
    r.local16(-0x12, last)                                       # A9FC
    r.ax = 0xC                                                   # A9FF
    if 0xC <= last:                                              # AA02 cmp ax, [bp - 0x12]; jbe AA0A
        k = 0xC
        r.local16(-6, k)                                         # AA0A
        while True:
            word = word_at(mem, r, sq_seg, sq_off, k)            # AA12-AA1C
            r = yield from guest(mem, r, "1771:3216", word, ret="AA25")
            if r.al == 0:                                        # AA25 or al, al; je AA2C
                r.ax = word_at(mem, r, sq_seg, sq_off, k)        # AA2C-AA36
                player_of_ax(mem, r)                             # AA3A-AA43
                r.local16(-0x16, r.di)                           # AA45
                r.local16(-0x14, r.es)                           # AA48
                r.al = rb(mem, r, 7)                             # AA4E
                r.ah = 0
                r.cx = r.ax                                      # AA54
                r.ax = position                                  # AA56
                r.dx = 0xE
                mul(r, r.dx)
                r.di = r.ax + r.cx                               # AA5E-AA60
                r.al = mem.ds8((r.di + 0x8D5) & M16)             # AA62
                r.ah = 0
                value = r.ax
                r.local16(-0xA, value)                           # AA68
                if pos != 0:                                     # AA6B cmp word ptr [bp - 0xc], 0; jbe AABA
                    word = word_at(mem, r, sq_seg, sq_off, k)    # AA71-AA7B
                    r = yield from guest(mem, r, "1771:3041", word, ret="AA84")
                    if r.al == 0:                                # AA84 or al, al; jne AABA
                        word = word_at(mem, r, sq_seg, sq_off, k)            # AA88-AA92
                        r = yield from guest(mem, r, "1771:3088", word, ret="AA9B")
                        set_dl(r, r.al)                          # AA9B mov dl, al
                        r.al = 1 if pos > 3 else 0               # AA9D cmp word ptr [bp - 0xc], 3; ja AAA7
                        if r.al != (r.dx & 0xFF):                # AAA9 cmp al, dl; je AABA
                            r.ax = value                         # AAAD
                            r.dx = 0
                            r.cx = 2
                            r.ax, r.dx = r.ax // 2, r.ax % 2     # AAB5 div cx
                            value = r.ax
                            r.local16(-0xA, value)               # AAB7
                r.ax = value                                     # AABA
                if r.ax > best_value:                            # AABD cmp ax, [bp - 8]; jbe AACE
                    r.ax = k                                     # AAC2
                    best = k
                    r.local16(-4, best)
                    r.ax = value                                 # AAC8
                    best_value = value
                    r.local16(-8, best_value)
            r.ax = k                                             # AACE
            if k == last:                                        # AAD1 cmp ax, [bp - 0x12]; je AAD9
                break
            k += 1
            r.local16(-6, k)                                     # AA0F
    r.ax = best                                                  # AAD9
    r.local16(-2, best)                                          # AADC
    r.ax = best                                                  # AADF
    return _end(r, value=True)


# -- AAE8 ----------------------------------------------------------------------------------------------------------
@PORTS.port("0791:AAE8", ret="ret 6")
def pick_bench_by_formation(mem, variant):
    """AAE8-AC64 (the outgoing player word [bp+8], the squad [bp+4]): over the entries 1..count of the formation row
    DS:099A + 8 * his position +6 (byte 0 the count), the role's bench slot DS:99A2[role] (C7EB's map) when it is set
    and, with a foot for the position (Pos(the position's character, DS:08CE) > 0), the bench player is two-footed
    (1771:3041) or his foot (1771:3088) is the position's (Pos > 3); the last such entry; 0 when none."""
    r = Regs(mem)
    r.enter(0x112)                                               # AAE8-AAEB
    squad_off, squad_seg, word = arg16(mem, r, 4), arg16(mem, r, 6), arg16(mem, r, 8)
    r.ax = word                                                  # AAEF
    player_of_ax(mem, r)                                         # AAF2-AAFB
    p_seg, p_off = r.es, r.di
    r.local16(-0x11, p_off)                                      # AAFD
    r.local16(-0xF, p_seg)                                       # AB00
    r.al = rb(mem, r, 6)                                         # AB06
    r.ah = 0
    r.di = r.ax                                                  # AB0C
    set_cl(r, 3)                                                 # AB0E
    r.di = r.di << 3                                             # AB10 shl di, cl
    r.ax = r.di + 0x99A                                          # AB12 lea ax, [di + 0x99a]
    r.dx = mem.DS                                                # AB16
    row = r.ax
    r.local16(-6, row)                                           # AB18
    r.local16(-4, mem.DS)                                        # AB1B
    r.ax = 0                                                     # AB1E
    found = 0
    r.local16(-0xA, found)
    temp = (r.bp - 0x111) & M16                                  # AB23 lea di, [bp - 0x111]
    r.di = temp
    r.push(r.ss)                                                 # AB27
    r.push(temp)                                                 # AB28
    r.es, r.di = p_seg, p_off                                    # AB29
    r.al = rb(mem, r, 6)                                         # AB2C
    r = yield from guest(mem, r, "23E4:075A", r.ax, ret="AB36")
    r.di = 0x8CE                                                 # AB36
    r.sp = r.sp + 4                                              # the string 075A left (AB27-AB28): 06E3's first
    r = yield from guest(mem, r, "23E4:06E3", r.ss, temp, mem.DS, 0x8CE, ret="AB40")
    pos = r.ax
    r.local16(-0xC, pos)                                         # AB40

    def entry_role(i):
        """`mov ax, [bp - 8]; les di, [bp - 6]; add di, ax; mov al, es:[di]; xor ah, ah; mov di, ax`: the role of entry i."""
        r.ax = i
        r.es, r.di = mem.DS, row
        r.di = r.di + r.ax
        r.al = rb(mem, r, 0)
        r.ah = 0
        r.di = r.ax

    def bench_slot(i):
        """... `mov al, [di - 0x665e]; xor ah, ah`: the role's bench slot in C7EB's map DS:99A2."""
        entry_role(i)
        r.al = mem.ds8((r.di + 0x99A2) & M16)
        r.ah = 0

    def bench_word(i):
        """... `shl ax, 1; les di, [bp + 4]; add di, ax`; the word es:[di - 2]: the bench player of entry i."""
        bench_slot(i)
        r.ax = r.ax << 1
        r.es, r.di = squad_seg, squad_off
        r.di = r.di + r.ax
        return mem.u16(mem.addr(r.es, r.di - 2))

    if pos > 0:                                                  # AB43 cmp word ptr [bp - 0xc], 0; ja AB4C
        r.al = 1 if pos > 3 else 0                               # AB4C cmp word ptr [bp - 0xc], 3; ja AB56
        foot = r.al
        r.local8(-0xD, foot)                                     # AB58
        r.es, r.di = mem.DS, row                                 # AB5B
        r.al = rb(mem, r, 0)
        r.ah = 0
        count = r.ax
        r.local16(-0x13, count)                                  # AB63
        r.ax = 1                                                 # AB66
        if 1 <= count:                                           # AB69 cmp ax, [bp - 0x13]; jbe AB71
            i = 1
            r.local16(-8, i)                                     # AB71
            while True:
                entry_role(i)                                    # AB79-AB86
                if mem.ds8((r.di + 0x99A2) & M16) != 0:          # AB88 cmp byte ptr [di - 0x665e], 0; je ABFA
                    word = bench_word(i)                         # AB8F-ABAB
                    r = yield from guest(mem, r, "1771:3041", word, ret="ABB4")
                    take = r.al != 0                             # ABB4 or al, al; jne ABE2
                    if not take:
                        word = bench_word(i)                     # ABB8-ABD4
                        r = yield from guest(mem, r, "1771:3088", word, ret="ABDD")
                        take = r.al == foot                      # ABDD cmp al, [bp - 0xd]; jne ABFA
                    if take:
                        bench_slot(i)                            # ABE2-ABF5
                        found = r.ax
                        r.local16(-0xA, found)                   # ABF7
                r.ax = i                                         # ABFA
                if i == count:                                   # ABFD cmp ax, [bp - 0x13]; je AC05
                    break
                i += 1
                r.local16(-8, i)                                 # AB76
    else:
        r.es, r.di = mem.DS, row                                 # AC07
        r.al = rb(mem, r, 0)
        r.ah = 0
        count = r.ax
        r.local16(-0x13, count)                                  # AC0F
        r.ax = 1                                                 # AC12
        if 1 <= count:                                           # AC15 cmp ax, [bp - 0x13]; ja AC58
            i = 1
            r.local16(-8, i)                                     # AC1A
            while True:
                entry_role(i)                                    # AC22-AC2F
                if mem.ds8((r.di + 0x99A2) & M16) != 0:          # AC31 je AC50
                    bench_slot(i)                                # AC38-AC4B
                    found = r.ax
                    r.local16(-0xA, found)                       # AC4D
                r.ax = i                                         # AC50
                if i == count:                                   # AC53 cmp ax, [bp - 0x13]; jne AC1F
                    break
                i += 1
                r.local16(-8, i)                                 # AC1F
    r.ax = found                                                 # AC58
    r.local16(-2, found)                                         # AC5B
    r.ax = found                                                 # AC5E
    return _end(r, value=True)


# -- BBFF ----------------------------------------------------------------------------------------------------------
@PORTS.port("0791:BBFF", ret="ret 4")
def set_team_tactics(mem, variant):
    """BBFF-BC5A (country [bp+6], tactics [bp+4]): the country's tactic set +0x2D := the byte; 1771:3431 for each of its
    20 squad words that is not 0."""
    r = Regs(mem)
    r.enter(6)                                                   # BBFF-BC02
    r.ax = arg16(mem, r, 6)                                      # BC05
    country_record(mem, r)                                       # BC08-BC11
    sq_seg, sq_off = r.es, r.di
    r.local16(-6, sq_off)                                        # BC13
    r.local16(-4, sq_seg)                                        # BC16
    r.al = arg8(mem, r, 4)                                       # BC19
    r.es, r.di = sq_seg, sq_off                                  # BC1C
    wb(mem, r, 0x2D, r.al, "BC1F")
    k = 1
    r.local16(-2, k)                                             # BC23
    while True:
        word = word_at(mem, r, sq_seg, sq_off, k)                # BC2D-BC35
        if word != 0:                                            # BC37 cmp word ptr es:[di - 2], 0; je BC51
            word = word_at(mem, r, sq_seg, sq_off, k)            # BC3E-BC46
            r = yield from guest(mem, r, "1771:3431", word, ret="BC51")
        if k == 0x14:                                            # BC51 cmp word ptr [bp - 2], 0x14; jne BC2A
            break
        k += 1
        r.local16(-2, k)                                         # BC2A
    return _end(r)


# -- BD03 ----------------------------------------------------------------------------------------------------------
@PORTS.port("0791:BD03", ret="ret 4")
def team_strength_greater(mem, variant):
    """BD03-BD80 (country a [bp+6], country b [bp+4]): 1 when the sum of 1771:377E over a's eleven squad words exceeds
    b's (unsigned words), else 0."""
    r = Regs(mem)
    r.enter(8)                                                   # BD03-BD06
    a, b = arg16(mem, r, 6), arg16(mem, r, 4)
    r.ax = 0                                                     # BD09
    sum_a = 0
    r.local16(-5, sum_a)
    sum_b = 0                                                    # BD0E
    r.local16(-7, sum_b)
    k = 1
    r.local16(-3, k)                                             # BD13
    while True:
        for country, ret in ((a, "BD3D"), (b, "BD60")):
            r.ax = k << 1                                        # BD1D-BD22 / BD40-BD45
            r.cx = r.ax
            r.ax = country
            country_record(mem, r)                               # BD27-BD30 / BD4A-BD53
            r.di = r.di + r.cx                                   # BD32 / BD55
            word = mem.u16(mem.addr(r.es, r.di - 2))
            r = yield from guest(mem, r, "1771:377E", word, ret=ret)
            if ret == "BD3D":
                sum_a = (sum_a + r.ax) & M16                     # BD3D add word ptr [bp - 5], ax
                r.local16(-5, sum_a)
            else:
                sum_b = (sum_b + r.ax) & M16                     # BD60 add word ptr [bp - 7], ax
                r.local16(-7, sum_b)
        if k == 0xB:                                             # BD63 cmp word ptr [bp - 3], 0xb; jne BD1A
            break
        k += 1
        r.local16(-3, k)                                         # BD1A
    r.ax = sum_a                                                 # BD69
    r.al = 1 if sum_a > sum_b else 0                             # BD6C cmp ax, [bp - 7]; ja BD75
    r.local8(-1, r.al)                                           # BD77
    return _end(r, value=True)                                   # BD7A mov al, [bp - 1]


# -- BD83 ----------------------------------------------------------------------------------------------------------
@PORTS.port("0791:BD83", ret="ret 2")
def computer_tactic_change(mem, variant):
    """BD83-BEA4 (side [bp+4]): the country's tactics back to its default DS:9B7C[country] (BBFF); for side 1 with
    DS:80FC set and side 1's eleven the stronger (BD03), element 1 added (214B:0C79) and set again; when the side's
    eleven are the stronger, two elements rand(6) added and set again; DS:8332 + side and DS:8334 + side := 0."""
    r = Regs(mem)
    r.enter(6)                                                   # BD83-BD86
    side = arg8(mem, r, 4)
    r.ax = squad_of_side(mem, r, side)                           # BD89-BD91
    country_record(mem, r)                                       # BD95-BD9E
    c_seg, c_off = r.es, r.di
    r.local16(-6, c_off)                                         # BDA0
    r.local16(-4, c_seg)                                         # BDA3

    def default_tactics(at_ret):
        nonlocal r
        country = squad_of_side(mem, r, side)                    # BDA6-BDAE push word ptr [di - 0x64cc]
        r.di = squad_of_side(mem, r, side)                       # BDB2-BDBA mov di, word ptr [di - 0x64cc]
        r.al = mem.ds8((r.di + 0x9B7C) & M16)                    # BDBE
        r = yield from guest(mem, r, "BBFF", country, r.ax, ret=at_ret, far=False)

    def set_again(at_ret):
        nonlocal r
        country = squad_of_side(mem, r, side)                    # push word ptr [di - 0x64cc]
        r.es, r.di = c_seg, c_off                                # les di, [bp - 6]
        r.al = rb(mem, r, 0x2D)
        r = yield from guest(mem, r, "BBFF", country, r.ax, ret=at_ret, far=False)

    def stronger(at_ret):
        nonlocal r
        mine = squad_of_side(mem, r, side)                       # push word ptr [di - 0x64cc]
        flip_side(r, side)                                       # cmp byte ptr [bp + 4], 0; je; mov al, 0 / 1
        theirs = squad_of_side(mem, r, r.al)                     # cbw; mov di, ax; shl di, 1; push word ptr [di - 0x64cc]
        r = yield from guest(mem, r, "BD03", mine, theirs, ret=at_ret, far=False)
        return r.al != 0                                         # or al, al; je

    yield from default_tactics("BDC6")
    if side == 1 and mem.ds8(0x80FC) != 0:                       # BDC6 cmp byte ptr [bp + 4], 1; BDCC cmp [0x80fc], 0
        if (yield from stronger("BDF7")):                        # BDD3-BDF9
            r.ax = 1                                             # BDFB
            r.es, r.di = c_seg, c_off                            # BDFF
            r.di = r.di + 0x2D
            r = yield from guest(mem, r, "214B:0C79", 1, r.es, r.di, ret="BE0D")
            yield from set_again("BE24")                         # BE0D-BE21
    if (yield from stronger("BE48")):                            # BE24-BE4A
        k = 1
        r.local16(-2, k)                                         # BE4C
        while True:
            r.ax = 6                                             # BE56
            r = yield from guest(mem, r, "214B:06B1", 6, ret="BE5F")
            element = r.ax                                       # BE5F push ax
            r.es, r.di = c_seg, c_off                            # BE60
            r.di = r.di + 0x2D
            r = yield from guest(mem, r, "214B:0C79", element, r.es, r.di, ret="BE6E")
            if k == 2:                                           # BE6E cmp word ptr [bp - 2], 2; jne BE53
                break
            k += 1
            r.local16(-2, k)                                     # BE53
        yield from set_again("BE8B")                             # BE74-BE88
    side_index(r, side)                                          # BE8B-BE8F
    mem.wds8(r.di + 0x8332, 0, "0791:BE91")                      # [di - 0x7cce]
    side_index(r, side)                                          # BE96-BE9A
    mem.wds8(r.di + 0x8334, 0, "0791:BE9C")                      # [di - 0x7ccc]
    return _end(r)


# -- BF6B ----------------------------------------------------------------------------------------------------------
@PORTS.port("0791:BF6B", ret="ret 6")
def computer_tactic_shift(mem, variant):
    """BF6B-BFF7 (direction [bp+8], side [bp+6]; C173's BP [bp+4]): BD83(side), then three elements rand(6) added to the
    country's tactics (214B:0C79) when the direction is set (the side behind), else taken out (214B:0CA1); set again
    (BBFF)."""
    r = Regs(mem)
    r.enter(6)                                                   # BF6B-BF6E
    direction, side = arg8(mem, r, 8), arg8(mem, r, 6)
    r.ax = squad_of_side(mem, r, side)                           # BF71-BF79
    country_record(mem, r)                                       # BF7D-BF86
    c_seg, c_off = r.es, r.di
    r.local16(-6, c_off)                                         # BF88
    r.local16(-4, c_seg)                                         # BF8B
    r.al = side                                                  # BF8E
    r = yield from guest(mem, r, "BD83", r.ax, ret="BF95", far=False)
    k = 1
    r.local16(-2, k)                                             # BF95
    while True:
        r.ax = 6                                                 # BFA5 / BFBF
        r = yield from guest(mem, r, "214B:06B1", 6, ret="BFAE" if direction else "BFC8")
        element = r.ax                                           # push ax
        r.es, r.di = c_seg, c_off
        r.di = r.di + 0x2D
        if direction:                                            # BF9F cmp byte ptr [bp + 8], 0; je BFBF
            r = yield from guest(mem, r, "214B:0C79", element, r.es, r.di, ret="BFBD")
        else:
            r = yield from guest(mem, r, "214B:0CA1", element, r.es, r.di, ret="BFD7")
        if k == 3:                                               # BFD7 cmp word ptr [bp - 2], 3; jne BF9C
            break
        k += 1
        r.local16(-2, k)                                         # BF9C
    country = squad_of_side(mem, r, side)                        # BFDD-BFE5
    r.es, r.di = c_seg, c_off                                    # BFE9
    r.al = rb(mem, r, 0x2D)
    r = yield from guest(mem, r, "BBFF", country, r.ax, ret="BFF4", far=False)
    return _end(r)


# -- C173 ----------------------------------------------------------------------------------------------------------
@PORTS.port("0791:C173", ret="ret 2")
def update_computer_tactics(mem, variant):
    """C173-C24A: d := DS:9B3C - DS:9B3D (the score, signed bytes); for each side the computer manages (1771:0B77 0):
    |d| < 2 BD83(side); |d| = 2 BF6B(1 when the side is behind, else 0); |d| > 2 C0DF (ahead) or C01A."""
    r = Regs(mem)
    r.enter(2)                                                   # C173-C176
    r.al = mem.ds8(0x9B3D)                                       # C179
    cbw(r)
    r.dx = r.ax
    r.al = mem.ds8(0x9B3C)                                       # C17F
    cbw(r)
    r.ax = r.ax - r.dx                                           # C183
    d = r.al
    r.local8(-1, d)                                              # C185
    side = 0
    r.local8(-2, side)                                           # C188

    def gap():
        """`mov al, [bp - 1]; cbw; or ax, ax; jns; neg ax`."""
        r.al = d
        cbw(r)
        if r.ax & 0x8000:
            r.ax = -r.ax
        return s16(r.ax)

    def ahead():
        """`cmp [bp - 2], 0; je; mov al, 0 / 1; cbw; mov di, ax; mov dl, [di - 0x64c4]; mov al, [bp - 2]; cbw; mov di, ax;
        mov al, [di - 0x64c4]; cmp al, dl; jbe`: the side's goals above the other's."""
        flip_side(r, side)
        cbw(r)
        r.di = r.ax
        set_dl(r, mem.ds8((r.di + 0x9B3C) & M16))
        side_index(r, side)
        r.al = mem.ds8((r.di + 0x9B3C) & M16)
        return r.al > (r.dx & 0xFF)

    while True:
        squad = squad_of_side(mem, r, side)                      # C191-C199
        r = yield from guest(mem, r, "1771:0B77", squad, ret="C1A2")
        if r.al == 0:                                            # C1A2 or al, al; je C1A9
            if gap() < (1 if variant == "tactics-gap-1" else 2):     # C1A9-C1B6 cmp ax, 2; jge C1C1
                r.al = side                                      # C1B8
                r = yield from guest(mem, r, "BD83", r.ax, ret="C1BF", far=False)
            elif gap() == 2:                                     # C1C1-C1CE cmp ax, 2; jne C20B
                r.al = 0 if ahead() else 1                       # C1D0-C1EF jbe C1FE; C1F1 mov al, 0 / C1FE mov al, 1
                direction = r.ax
                r.al = side                                      # C1F4 / C201
                r = yield from guest(mem, r, "BF6B", direction, r.ax, r.bp,
                                     ret="C1FC" if (direction & 0xFF) == 0 else "C209", far=False)
            elif ahead():                                        # C20B-C22A jbe C236
                r.al = side                                      # C22C
                r = yield from guest(mem, r, "C0DF", r.ax, r.bp, ret="C234", far=False)
            else:
                r.al = side                                      # C236
                r = yield from guest(mem, r, "C01A", r.ax, r.bp, ret="C23E", far=False)
        if side == 1:                                            # C23E cmp byte ptr [bp - 2], 1; je C247
            break
        side += 1
        r.local8(-2, side)                                       # C18E
    return _end(r)


# -- C5DC ----------------------------------------------------------------------------------------------------------
@PORTS.port("0791:C5DC", ret="ret 6")
def refresh_pitch_slot(mem, variant):
    """C5DC-C7E8 (side [bp+8], slot [bp+6], the incoming squad index [bp+4]): the outgoing player's status +0x10 element
    3 (substituted off, 214B:0C79); an unmanaged side: 214B:1E8D, the notice C50C(him, the incoming) when the other
    side is managed and the match is watched, the line 1EB5(0, index, slot in side, side); the record rebound (A2E6) at
    its point (DS:0644 when it was off the pitch DS:0640), the incoming player's +0x12 := 0x2747 and, for an unmanaged
    side, his own tactics cleared and derived (1771:3431); each managed side's DS:9978 + 10 side word set to its
    captain's first squad word while unavailable, 230C, then cleared again; DS:9B3A + side -1 (C7DC, the kit's
    substitution event); DS:9B55 := 1."""
    r = Regs(mem)
    r.enter(0xA)                                                 # C5DC-C5DF
    side, slot, index = arg8(mem, r, 8), arg16(mem, r, 6), arg16(mem, r, 4)
    r.ax = slot                                                  # C5E2-C5EC
    r.dx = 0x16
    mul(r, r.dx)
    r.di = r.ax + 0x80E8
    rec = r.di
    r.local16(-0xA, rec)                                         # C5F0
    r.local16(-8, mem.DS)                                        # C5F3
    r.ax = 3                                                     # C5F6 (push ax)
    r.es = mem.DS                                                # C5FA
    player_record(mem, r)                                        # C5FD-C60A
    r.di = r.di + 0x10                                           # C60C
    r = yield from guest(mem, r, "214B:0C79", 3, r.es, r.di, ret="C617")
    squad = squad_of_side(mem, r, side)                          # C617-C61F
    r = yield from guest(mem, r, "1771:0B77", squad, ret="C628")
    managed = r.al
    r.local8(-3, managed)                                        # C628
    if managed == 0:                                             # C62B cmp byte ptr [bp - 3], 0; je C634
        r = yield from guest(mem, r, "214B:1E8D", ret="C639")
        flip_side(r, side)                                       # C639-C643
        squad = squad_of_side(mem, r, r.al)                      # C645-C64A
        r = yield from guest(mem, r, "1771:0B77", squad, ret="C653")
        if r.al != 0 and mem.ds8(0x9A3E) == 0:                   # C653 je C69C; C657 cmp [0x9a3e], 0; jne C69C
            first_slot(mem, r, side)                             # C65E-C668
            r.dx = r.ax
            r.ax = (slot - r.dx) << 1                            # C66C-C671
            r.cx = r.ax
            r.ax = squad_of_side(mem, r, side)                   # C675-C67D
            country_record(mem, r)                               # C681-C68A
            r.di = r.di + r.cx                                   # C68C
            outgoing = mem.u16(mem.addr(r.es, r.di - 2))         # C68E push word ptr es:[di - 2]
            r.es, r.di = mem.DS, rec                             # C692
            r = yield from guest(mem, r, "C50C", outgoing, rw(mem, r, 0xD), ret="C69C", far=False)
        r.al = side                                              # C69C
        side_word = r.ax
        first_slot(mem, r, side)                                 # C6A0-C6AA
        r.dx = r.ax
        r.ax = slot - r.dx                                       # C6AE-C6B1
        in_side = r.ax
        r.al = 0                                                 # C6B7
        r = yield from guest(mem, r, "1EB5", side_word, in_side, index, r.ax, ret="C6BD", far=False)
    r.es, r.di = mem.DS, rec                                     # C6BD
    r.ax = rw(mem, r, 2)
    if r.ax == mem.ds16(0x640):                                  # C6C4 cmp ax, [0x640]; jne C6D2
        r.ax = mem.ds16(0x644)                                   # C6CA
    else:
        r.ax = rw(mem, r, 2)                                     # C6D5
    point = r.ax
    r.local16(-2, point)                                         # C6CD / C6D9
    r = yield from guest(mem, r, "A2E6", slot, mem.DS, rec, ret="C6E8")
    r.es, r.di = mem.DS, rec                                     # C6E8
    player_record(mem, r)                                        # C6EB-C6F8
    ww(mem, r, 0x12, 0x2747, "C6FA")
    if managed == 0:                                             # C700 cmp byte ptr [bp - 3], 0; jne C729
        r.es, r.di = mem.DS, rec                                 # C706
        player_record(mem, r)                                    # C709-C716
        wb(mem, r, 0xF, 0, "C718")
        r.es, r.di = mem.DS, rec                                 # C71D
        r = yield from guest(mem, r, "1771:3431", rw(mem, r, 0xD), ret="C729")
    r.ax = point                                                 # C729
    r.es, r.di = mem.DS, rec                                     # C72C
    ww(mem, r, 2, r.ax, "C72F")
    r.ax = 0                                                     # C733
    r.local16(-6, 0)
    flags = [0, 0]
    t = 0
    r.local8(-4, t)                                              # C738
    while True:
        squad = squad_of_side(mem, r, t)                         # C741-C749
        r = yield from guest(mem, r, "1771:0B77", squad, ret="C752")
        if r.al:                                                 # C752 or al, al; je C7A1
            r.al = t                                             # C756-C75F
            cbw(r)
            r.dx = 0xA
            mul(r, r.dx)
            r.di = r.ax
            word = mem.ds16((r.di + 0x9978) & M16)               # C761 push word ptr [di - 0x6688]
            r = yield from guest(mem, r, "1771:3216", word, ret="C76A")
            if r.al:                                             # C76A or al, al; je C7A1
                side_index(r, t)                                 # C76E-C772
                flags[t] = 1
                r.local8(-6 + t, 1)                              # C774 mov byte ptr [bp + di - 6], 1
                r.ax = squad_of_side(mem, r, t)                  # C778-C780
                country_record(mem, r)                           # C784-C78D
                r.cx = mem.u16(mem.addr(r.es, r.di))             # C78F
                r.al = t                                         # C792-C79B
                cbw(r)
                r.dx = 0xA
                mul(r, r.dx)
                r.di = r.ax
                mem.wds16(r.di + 0x9978, r.cx, "0791:C79D")
        if t == 1:                                               # C7A1 cmp byte ptr [bp - 4], 1; jne C73E
            break
        t += 1
        r.local8(-4, t)                                          # C73E
    r = yield from guest(mem, r, "230C", ret="C7AA", far=False)
    t = 0
    r.local8(-4, t)                                              # C7AA
    while True:
        side_index(r, t)                                         # C7B3-C7B7
        if flags[t]:                                             # C7B9 cmp byte ptr [bp + di - 6], 0; je C7D0
            r.al = t                                             # C7BF-C7C8
            cbw(r)
            r.dx = 0xA
            mul(r, r.dx)
            r.di = r.ax
            r.ax = 0                                             # C7CA
            mem.wds16(r.di + 0x9978, 0, "0791:C7CC")
        if t == 1:                                               # C7D0 cmp byte ptr [bp - 4], 1; jne C7B0
            break
        t += 1
        r.local8(-4, t)                                          # C7B0
    side_index(r, side)                                          # C7D6-C7DA
    mem.wds8(r.di + 0x9B3A, mem.ds8((r.di + 0x9B3A) & M16) - 1, "0791:C7DC")   # the substitution
    mem.wds8(0x9B55, 1, "0791:C7E0")
    return _end(r)


# -- C7EB ----------------------------------------------------------------------------------------------------------
@PORTS.port("0791:C7EB", ret="ret 2")
def map_bench_roles(mem, variant):
    """C7EB-C88A (C88D's BP [bp+4]): over squad slots k = 12..20 of C88D's squad, each player that is not the outgoing
    one (DS:80F5 of C88D's slot - DS:0668[side]) and is available (1771:3216) is written as k at DS:99A2[his role +7]."""
    r = Regs(mem)
    r.enter(2)                                                   # C7EB-C7EE
    parent = arg16(mem, r, 4)
    k = 0xC
    r.local16(-2, k)                                             # C7F1

    def squad_word():
        """`mov ax, [bp - 2]; shl ax, 1; mov di, [bp + 4]; les di, ss:[di + 0xa]; add di, ax`; es:[di - 2]."""
        r.ax = k << 1
        r.di = parent
        r.es, r.di = ss16(mem, r, parent + 0xC), ss16(mem, r, parent + 0xA)
        r.di = r.di + r.ax
        return mem.u16(mem.addr(r.es, r.di - 2))

    while True:
        r.di = parent                                            # C7FB
        r.al = ss8(mem, r, parent + 6)                           # C7FE
        cbw(r)
        r.di = r.ax
        r.al = mem.ds8((r.di + 0x668) & M16)                     # C805
        r.ah = 0
        r.dx = r.ax                                              # C80B
        r.di = parent                                            # C80D
        r.ax = ss16(mem, r, parent + 8) - r.dx                   # C810-C814
        r.dx = 0x16
        mul(r, r.dx)
        r.di = r.ax
        r.dx = mem.ds16((r.di + 0x80F5) & M16)                   # C81D
        r.ax = squad_word()                                      # C821-C82F
        if r.ax != r.dx:                                         # C833 cmp ax, dx; je C87E
            word = squad_word()                                  # C837-C845
            r = yield from guest(mem, r, "1771:3216", word, ret="C84E")
            if r.al == 0:                                        # C84E or al, al; jne C87E
                set_cl(r, k)                                     # C852
                r.ax = squad_word()                              # C855-C863
                player_of_ax(mem, r)                             # C867-C870
                r.al = rb(mem, r, 7)                             # C872
                r.ah = 0
                r.di = r.ax
                mem.wds8(r.di + 0x99A2, k, "0791:C87A")          # [di - 0x665e]
        if k == 0x14:                                            # C87E cmp word ptr [bp - 2], 0x14; je C887
            break
        k += 1
        r.local16(-2, k)                                         # C7F8
    return _end(r)


# -- C88D ----------------------------------------------------------------------------------------------------------
@PORTS.port("0791:C88D", ret="ret 0xa")
def substitute_player(mem, variant):
    """C88D-CAAD (the squad [bp+0xA], slot [bp+8], side [bp+6], flag [bp+4]): with no substitution left (DS:9B3A + side)
    and the outgoing player injured (+0xE < 1) only the forced swap C48D; otherwise C7EB's map (DS:99A2 cleared, 14
    bytes), the bench pick AAE8 or, with none, for a keeper (+6 = 0) or with the flag, A9B8(country, position, 0x14);
    with a pick: the incoming player takes the outgoing's position +6, their squad words swap (214B:007B), and so do
    their words of DS:9A3E + 0x28 side and bytes of DS:9B07 + 0x14 side; then C5DC(side, slot, pick)."""
    r = Regs(mem)
    r.enter(6)                                                   # C88D-C890
    flag, side, slot = arg8(mem, r, 4), arg8(mem, r, 6), arg16(mem, r, 8)
    squad_off, squad_seg = arg16(mem, r, 0xA), arg16(mem, r, 0xC)

    def outgoing_record():
        """`mov ax, [bp + 8]; mov dx, 0x16; mul dx; mov di, ax; mov ax, [di - 0x7f0b]; mov dx, 0x14; mul dx; les di,
        [0xa91b]; add di, ax`: the outgoing player's record."""
        r.ax = slot
        r.dx = 0x16
        mul(r, r.dx)
        r.di = r.ax
        r.ax = mem.ds16((r.di + 0x80F5) & M16)
        player_of_ax(mem, r)

    def in_side_doubled():
        """`mov al, [bp + 6]; cbw; mov di, ax; mov al, [di + 0x668]; xor ah, ah; mov dx, ax; mov ax, [bp + 8]; sub ax,
        dx; shl ax, 1`."""
        first_slot(mem, r, side)
        r.dx = r.ax
        r.ax = (slot - r.dx) << 1

    side_index(r, side)                                          # C893-C897
    if mem.ds8((r.di + 0x9B3A) & M16) == 0:                      # C899 cmp byte ptr [di - 0x64c6], 0; jne C8DE
        in_side_doubled()                                        # C8A0-C8B3
        r.es, r.di = squad_seg, squad_off                        # C8B5
        r.di = r.di + r.ax
        r.ax = mem.u16(mem.addr(r.es, r.di - 2))                 # C8BA
        player_of_ax(mem, r)                                     # C8BE-C8C7
        if s8(rb(mem, r, 0xE)) < 1:                              # C8C9 cmp byte ptr es:[di + 0xe], 1; jge C8DE
            r.es, r.di = squad_seg, squad_off                    # C8D0
            r = yield from guest(mem, r, "C48D", squad_seg, squad_off, slot, ret="C8DB", far=False)
            return _end(r)                                       # C8DB jmp CAAA
    r.di = 0x99A2                                                # C8DE
    r.ax = 0xE                                                   # C8E3
    r.ax = 0                                                     # C8E7
    r = yield from guest(mem, r, "214B:0018", mem.DS, 0x99A2, 0xE, 0, ret="C8EF")
    r = yield from guest(mem, r, "C7EB", r.bp, ret="C8F3", far=False)
    r.ax = slot                                                  # C8F3-C8FB
    r.dx = 0x16
    mul(r, r.dx)
    r.di = r.ax
    word = mem.ds16((r.di + 0x80F5) & M16)                       # C8FD push word ptr [di - 0x7f0b]
    r.es, r.di = squad_seg, squad_off                            # C901
    r = yield from guest(mem, r, "AAE8", word, squad_seg, squad_off, ret="C909", far=False)
    pick = r.ax
    r.local16(-2, pick)                                          # C909
    if pick == 0:                                                # C90C cmp word ptr [bp - 2], 0; jne C96E
        keeper_rule = True
        if flag == 0:                                            # C912 cmp byte ptr [bp + 4], 0; jne C938
            outgoing_record()                                    # C918-C92F
            keeper_rule = rb(mem, r, 6) == 0                     # C931 cmp byte ptr es:[di + 6], 0; jne C96E
        if keeper_rule:
            country = squad_of_side(mem, r, side)                # C938-C940 push word ptr [di - 0x64cc]
            outgoing_record()                                    # C944-C95B
            r.al = rb(mem, r, 6)                                 # C95D
            r.ah = 0
            position = r.ax
            r.ax = 0x14                                          # C964
            r = yield from guest(mem, r, "A9B8", country, position, 0x14, ret="C96B", far=False)
            pick = r.ax
            r.local16(-2, pick)                                  # C96B
    if pick == 0:                                                # C96E cmp word ptr [bp - 2], 0; jne C977
        return _end(r)                                           # C974 jmp CAAA
    r.ax = squad_of_side(mem, r, side)                           # C977-C97F
    country_record(mem, r)                                       # C983-C98C
    c_seg, c_off = r.es, r.di
    r.local16(-6, c_off)                                         # C98E
    r.local16(-4, c_seg)                                         # C991
    outgoing_record()                                            # C994-C9AB
    set_cl(r, rb(mem, r, 6))                                     # C9AD mov cl, byte ptr es:[di + 6]
    r.ax = word_at(mem, r, c_seg, c_off, pick)                   # C9B1-C9BB
    player_of_ax(mem, r)                                         # C9BF-C9C8
    wb(mem, r, 6, r.cx & 0xFF, "C9CA")
    r.ax = pick << 1                                             # C9CE-C9D8
    r.es, r.di = c_seg, c_off
    r.di = r.di + r.ax + 0xFFFE
    a_seg, a_off = r.es, r.di                                    # C9DC-C9DD push es; push di
    in_side_doubled()                                            # C9DE-C9F1
    r.es, r.di = c_seg, c_off                                    # C9F3
    r.di = r.di + r.ax + 0xFFFE
    r.ax = 2                                                     # C9FE
    r = yield from guest(mem, r, "214B:007B", a_seg, a_off, r.es, r.di, 2, ret="CA07")
    r.ax = pick << 1                                             # CA07-CA0A
    r.cx = r.ax
    r.al = side                                                  # CA0E-CA15
    cbw(r)
    r.dx = 0x28
    mul(r, r.dx)
    r.di = r.ax + r.cx + 0x9A3E                                  # CA17-CA1B
    first = r.di                                                 # CA1F-CA20 push ds; push di
    in_side_doubled()                                            # CA21-CA34
    r.cx = r.ax                                                  # CA36
    r.al = side                                                  # CA38-CA3F
    cbw(r)
    r.dx = 0x28
    mul(r, r.dx)
    r.di = r.ax + r.cx + 0x9A3E                                  # CA41-CA45
    r.ax = 2                                                     # CA4B
    r = yield from guest(mem, r, "214B:007B", mem.DS, first, mem.DS, r.di, 2, ret="CA54")
    r.ax = pick                                                  # CA54
    r.cx = r.ax
    r.al = side                                                  # CA59-CA60
    cbw(r)
    r.dx = 0x14
    mul(r, r.dx)
    r.di = r.ax + r.cx + 0x9B07                                  # CA62-CA66
    first = r.di                                                 # CA6A-CA6B push ds; push di
    first_slot(mem, r, side)                                     # CA6C-CA76
    r.dx = r.ax                                                  # CA78
    r.ax = slot - r.dx                                           # CA7A-CA7D
    r.cx = r.ax                                                  # CA7F
    r.al = side                                                  # CA81-CA88
    cbw(r)
    r.dx = 0x14
    mul(r, r.dx)
    r.di = r.ax + r.cx + 0x9B07                                  # CA8A-CA8E
    r.ax = 1                                                     # CA94
    r = yield from guest(mem, r, "214B:007B", mem.DS, first, mem.DS, r.di, 1, ret="CA9D")
    r.al = side                                                  # CA9D
    r = yield from guest(mem, r, "C5DC", r.ax, slot, pick, ret="CAAA", far=False)
    return _end(r)
