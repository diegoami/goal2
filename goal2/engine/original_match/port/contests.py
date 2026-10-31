"""The holder's decisions and the contests in GOAL.EXE segment 0791 (T65, route C step P3b).

Translated instruction by instruction from static/goal-exe/code/seg_0791_08.asm (4DA9-4E25), seg_0791_09.asm
(4E28-5A8B) and seg_0791_10.asm (5A8E-5AF3), after the named view (named/seg_0791_04.c and _05.c). The line comments
are the listing's offsets. The routines are written in the registers the listing uses (runtime.Regs), so the words they
push for their callees (a template byte pushed with `mov al, n; push ax` keeps the AH of the instruction before) and the
locals of their frames are the original's: the family digests cover the stack (notes.md rule 2a).

Every call of the listing stays a guest call (port/guest.py), including calls between the routines of this module and
the callees of other rows (T60's 261A, T63's 4D3F, T64's 3323, T66's 5B36 and 5E41, T68's 8206 and 82EB, T73's beep
214B:1EA1). The nested routines (`ret 2` / `ret 4` taking the parent's BP) read their parent's far pointer through it,
as the listing does: `mov di, [bp + 4]; les di, ss:[di + 6]` (one level) or with `mov di, ss:[di + 4]` between (two).
"""
from . import Registry
from .guest import call
from .mem import s16
from .runtime import Regs
from .geometry import cbw, cwd, mul, imul

PORTS = Registry("contests", "the holder's decisions and the contests: 4DA9-5A8E (T65)")
PORTS.variant("receiver-to-target", "533B at 5372: the pass receiver runs to DS:8313, not to the ball DS:82F6")
PORTS.variant("countdown-double", "58E1 at 591A: the chase countdown +0x10 runs down by 2, not 1")
PORTS.variant("nearest-not-chasing", "57AC at 5876: the side's nearest player (DS:8311) no longer goes to the ball")
M16 = 0xFFFF


# -- the listing's idioms ------------------------------------------------------------------------------------------
def guest(mem, r, target, *args, ret, far=True):
    """The call of the listing: registers and stack stored, the guest runs the callee; the registers it leaves."""
    r.store(stack=True)
    yield call(target if ":" in target else f"0791:{target}", *args, ret_to=f"0791:{ret}", far=far)
    return Regs(mem, resumed=True)


def ss16(mem, r, off):
    r.flush()
    return mem.u16(mem.ss_lin(off & M16))


def ss8(mem, r, off):
    r.flush()
    return mem.u8(mem.ss_lin(off & M16))


def pop(mem, r):
    value = ss16(mem, r, r.sp)
    r.sp = r.sp + 2
    return value


def nested(mem, r, levels=1):
    """`mov di, [bp + 4]` (`mov di, ss:[di + 4]` for each further level) `les di, ss:[di + 6]`: the far pointer
    argument of the routine `levels` frames up."""
    r.di = ss16(mem, r, r.bp + 4)
    for _ in range(levels - 1):
        r.di = ss16(mem, r, r.di + 4)
    di = r.di
    r.es, r.di = ss16(mem, r, di + 8), ss16(mem, r, di + 6)
    return r.es, r.di


def own(mem, r):
    """`les di, ptr [bp + 6]`: the routine's own far pointer argument."""
    r.es, r.di = ss16(mem, r, r.bp + 8), ss16(mem, r, r.bp + 6)
    return r.es, r.di


def rb(mem, r, k):
    return mem.u8(mem.addr(r.es, r.di + k))


def rw(mem, r, k):
    return mem.u16(mem.addr(r.es, r.di + k))


def slot_offset(r, slot):
    """`mov al, slot; xor ah, ah; mov dx, 0x16; mul dx`: AX = slot * 0x16."""
    r.al = slot
    r.ah = 0
    r.dx = 0x16
    mul(r, r.dx)


def player_record(mem, r):
    """`mov ax, es:[di + 0xd]; mov dx, 0x14; mul dx; les di, [0xa91b]; add di, ax`: the pitch record's player."""
    r.ax = rw(mem, r, 0xD)
    r.dx = 0x14
    mul(r, r.dx)
    r.di, r.es = mem.ds16(0xA91B), mem.ds16(0xA91D)
    r.di = r.di + r.ax


def byte_abs(r, value):
    """`mov al, b; cbw; or ax, ax; jns; neg ax`."""
    r.al = value
    cbw(r)
    if r.ax & 0x8000:
        r.ax = -r.ax
    return s16(r.ax)


# -- 4DA9 ----------------------------------------------------------------------------------------------------------
@PORTS.port("0791:4DA9", ret="retf 4")
def challenger_would_foul(mem, variant):
    """4DA9-4E25: (random_is_one(0x12 - hardness) or effective element 4) and rand(hardness of DS:830B's player) <
    rand(hardness of the record's player)."""
    r = Regs(mem)
    r.enter(2)                                                   # 4DA9-4DAC
    seg, off = own(mem, r)                                       # 4DAF
    r = yield from guest(mem, r, "1771:2FFB", rw(mem, r, 0xD), ret="4DBB")
    r.ah = 0
    r.dx = r.ax
    r.ax = 0x12 - r.dx                                           # 4DBF-4DC2
    r = yield from guest(mem, r, "214B:06D0", r.ax, ret="4DCA")
    go = True
    if r.al == 0:
        r.ax = 4
        r.es, r.di = seg, off
        r = yield from guest(mem, r, "26D7", 4, seg, off, ret="4DDB")
        go = r.al != 0
    if go:
        slot_offset(r, mem.ds8(0x830B))                          # 4DDF-4DE7
        r.di = r.ax
        r = yield from guest(mem, r, "1771:2FFB", mem.ds16((r.di + 0x80F5) & M16), ret="4DF4")
        r.ah = 0
        r = yield from guest(mem, r, "214B:06B1", r.ax, ret="4DFC")
        r.push(r.ax)                                             # 4DFC: the holder's roll, live across two calls
        r.es, r.di = seg, off
        r = yield from guest(mem, r, "1771:2FFB", rw(mem, r, 0xD), ret="4E09")
        r.ah = 0
        r = yield from guest(mem, r, "214B:06B1", r.ax, ret="4E11")
        r.dx = pop(mem, r)                                       # 4E11
        go = s16(r.ax) > s16(r.dx)                               # 4E12-4E14 jg
    r.al = 1 if go else 0                                        # 4E16 / 4E1A
    r.local8(-1, r.al)                                           # 4E1C
    r.leave()
    r.store()
    return r.ax


# -- 4E28 ----------------------------------------------------------------------------------------------------------
@PORTS.port("0791:4E28", ret="ret 2")
def holder_action_choice(mem, variant):
    """4E28-5009: shoot (3DF6), pass (3323) or dribble (384C) by the holder's row and position."""
    r = Regs(mem)
    r.enter(4)                                                   # 4E28-4E2B
    nested(mem, r)                                               # 4E2E-4E31
    player_record(mem, r)                                        # 4E35-4E42
    r.local16(-4, r.di)                                          # 4E44
    r.local16(-2, r.es)                                          # 4E47
    r = yield from guest(mem, r, "261A", ret="4E4D", far=False)
    r.ax = r.ax + 0x18                                           # 4E4D
    r.push(r.ax)                                                 # 4E50: the floor, live across 2BE5
    seg, off = nested(mem, r)
    r = yield from guest(mem, r, "2BE5", seg, off, ret="4E5E")
    cbw(r)
    r.dx = r.ax
    nested(mem, r)
    r.al = rb(mem, r, 1)
    cbw(r)
    imul(r, r.dx)                                                # 4E6D
    r.dx = pop(mem, r)                                           # 4E6F
    far_forward = s16(r.ax) > s16(r.dx)                          # 4E70-4E72 jle 4E9A
    if far_forward:
        nested(mem, r)                                           # 4E74
        far_forward = byte_abs(r, rb(mem, r, 0)) > 3             # 4E85-4E88 jle 4E9A
    if far_forward:
        seg, off = nested(mem, r)                                # 4E8A
        r = yield from guest(mem, r, "3DF6", seg, off, ret="4E97")
        r.leave()
        r.store()
        return None
    seg, off = nested(mem, r)                                    # 4E9A
    r = yield from guest(mem, r, "2BE5", seg, off, ret="4EA7")
    cbw(r)
    r.dx = r.ax
    nested(mem, r)
    r.al = rb(mem, r, 1)
    cbw(r)
    imul(r, r.dx)                                                # 4EB6
    to_pass = s16(r.ax) < -8                                     # 4EB8 cmp ax, 0xfff8; jl
    if not to_pass:
        r = yield from guest(mem, r, "261A", ret="4EC0", far=False)
        to_pass = r.ax == 1                                      # 4EC0
    if to_pass:
        seg, off = nested(mem, r)                                # 4EC5
        r = yield from guest(mem, r, "3323", seg, off, ret="4ED2")
        r.leave()
        r.store()
        return None
    r.di, r.es = ss16(mem, r, r.bp - 4), ss16(mem, r, r.bp - 2)   # 4ED5
    r.al = rb(mem, r, 6)
    position = r.al

    def dribble(ret):
        nonlocal r
        nested(mem, r)
        r.al = rb(mem, r, 6)
        r.ah = 0
        slot = r.ax
        seg, off = nested(mem, r)
        r = yield from guest(mem, r, "384C", slot, seg, off, ret=ret)

    def pass_(ret):
        nonlocal r
        seg, off = nested(mem, r)
        r = yield from guest(mem, r, "3323", seg, off, ret=ret)

    if position in (3, 4):                                       # 4EDC-4EE2
        r.ax = 1
        seg, off = nested(mem, r)
        r = yield from guest(mem, r, "26D7", 1, seg, off, ret="4EF5")
        if r.al:
            yield from dribble("4F14")
        else:
            yield from pass_("4F23")
    elif position in (7, 8):                                     # 4F26-4F2C
        r.ax = 1
        seg, off = nested(mem, r)
        r = yield from guest(mem, r, "26D7", 1, seg, off, ret="4F3F")
        drib = False
        if r.al:
            r.ax = 3
            r = yield from guest(mem, r, "214B:06D0", 3, ret="4F4C")
            drib = r.al == 0
        if drib:
            yield from dribble("4F6B")
        else:
            yield from pass_("4F7A")
    elif position in (10, 11):                                   # 4F7D-4F83
        yield from dribble("4FA0")
    elif position in (13, 12):                                   # 4FA2-4FA8
        r.di, r.es = ss16(mem, r, r.bp - 4), ss16(mem, r, r.bp - 2)   # 4FAA
        r.al = 1 if rb(mem, r, 6) == 0xC else 0
        cbw(r)
        r.di = r.ax
        r.al = mem.ds8((r.di + 0x7E4) & M16)                     # 4FBD
        r.ah = 0
        r = yield from guest(mem, r, "214B:06D0", r.ax, ret="4FC9")
        if r.al:
            yield from pass_("4FDA")
        else:
            yield from dribble("4FF7")
    else:
        yield from pass_("5006")                                 # 4FF9
    r.leave()                                                    # 5006
    r.store()
    return None


# -- 500C ----------------------------------------------------------------------------------------------------------
@PORTS.port("0791:500C", ret="ret 2")
def defending_keeper_in_state13(mem, variant):
    """500C-5046: whether the first pitch slot of the side not holding the ball (its keeper) is in state 0x0D."""
    r = Regs(mem)
    r.enter(2)
    r = yield from guest(mem, r, "2996", ret="5015", far=False)
    r.al = 0 if r.al else 1                                      # 5017-501D
    cbw(r)
    r.di = r.ax
    r.al = mem.ds8((r.di + 0x668) & M16)                         # 5022
    r.ah = 0
    r.ax = r.ax + 1
    r.dx = 0x16
    mul(r, r.dx)
    r.di = r.ax
    r.al = 1 if mem.ds8((r.di + 0x80FA) & M16) == 0xD else 0     # 5030 cmp [di - 0x7f06], 0xd
    r.local8(-1, r.al)                                           # 503D
    r.leave()
    r.store()
    return r.ax


# -- 5049 ----------------------------------------------------------------------------------------------------------
@PORTS.port("0791:5049", ret="ret 2")
def energy_chance_branch(mem, variant):
    """5049-5338: the holder's turn (2C29): the keeper's distribution, or a shot, header or 4E28's choice."""
    r = Regs(mem)
    r.enter(4)                                                   # 5049-504C
    seg, off = nested(mem, r)
    r = yield from guest(mem, r, "2C29", seg, off, ret="505C")
    if r.al == 0:
        r.local8(-1, 0)                                          # 532E
        r.al = ss8(mem, r, r.bp - 1)
        r.leave()
        r.store()
        return r.ax
    r.local8(-1, 1)                                              # 5063
    seg, off = nested(mem, r)
    r = yield from guest(mem, r, "474D", seg, off, ret="5074")
    nested(mem, r)
    r.al = rb(mem, r, 6)
    r.ah = 0
    r = yield from guest(mem, r, "045D", r.ax, ret="5085", far=False)
    if r.al:                                                     # the keeper holds the ball
        nested(mem, r)
        if byte_abs(r, rb(mem, r, 1)) == 0x1A:                   # 509B
            seg, off = nested(mem, r)
            r = yield from guest(mem, r, "3BEE", seg, off, ret="50AD")
        else:
            nested(mem, r)
            if byte_abs(r, rb(mem, r, 8)) != 0x1A:               # 50C1
                seg, off = nested(mem, r)
                r = yield from guest(mem, r, "2BE5", seg, off, ret="50D3")
                cbw(r)
                r.cx = 0xFFE6
                imul(r, r.cx)                                    # 50D7
                nested(mem, r)
                mem.w8(mem.addr(r.es, r.di + 8), r.al, "0791:50E0")
                r.ax = 9
                r = yield from guest(mem, r, "214B:06B1", 9, ret="50ED")
                r.ax = r.ax + 0xFFFB
                nested(mem, r)
                mem.w8(mem.addr(r.es, r.di + 7), r.al, "0791:50F7")
        return (yield from _5049_end(mem, r))
    seg, off = nested(mem, r)                                    # 50FE
    r = yield from guest(mem, r, "4354", seg, off, ret="510B")
    r = yield from guest(mem, r, "40BC", ret="510E", far=False)
    if r.al:                                                     # 5115
        point = mem.ds16(0x646)
        seg, off = nested(mem, r)
        r = yield from guest(mem, r, "2C86", point, seg, off, ret="5126")
        nested(mem, r)
        mem.w16(mem.addr(r.es, r.di + 7), r.ax, "0791:512D")
        r = yield from guest(mem, r, "500C", r.bp, ret="5135", far=False)
        attempt = r.al != 0
        if not attempt:
            nested(mem, r)
            if byte_abs(r, rb(mem, r, 0)) < 2:                   # 514A jge 519F
                r = yield from guest(mem, r, "261A", ret="5152", far=False)
                r.ax = r.ax + 0x14
                r.push(r.ax)                                     # 5155: live across 2BE5
                seg, off = nested(mem, r)
                r = yield from guest(mem, r, "2BE5", seg, off, ret="5163")
                cbw(r)
                r.dx = r.ax
                nested(mem, r)
                r.al = rb(mem, r, 1)
                cbw(r)
                imul(r, r.dx)
                r.dx = pop(mem, r)                               # 5174
                attempt = s16(r.ax) > s16(r.dx)                  # 5175-5177 jle 519F
        if attempt:                                              # 5179
            if mem.ds8(0x8303):
                seg, off = nested(mem, r)
                r = yield from guest(mem, r, "3EDF", seg, off, ret="518D")
            else:
                r.al = 0x11                                      # 518F
                template = r.ax
                seg, off = nested(mem, r)
                r = yield from guest(mem, r, "3EC5", template, seg, off, ret="519F")
        if mem.ds8(0x8303):                                      # 519F
            mem.wds8(0x8303, 0, "0791:51A6")
        return (yield from _5049_end(mem, r))
    seg, off = nested(mem, r)                                    # 51AE
    r = yield from guest(mem, r, "2F28", seg, off, ret="51BB")
    near_goal = r.al != 0
    if near_goal and not mem.ds8(0x8303):                        # 51C2
        r = yield from guest(mem, r, "500C", r.bp, ret="51CD", far=False)
        if r.al == 0:
            nested(mem, r)
            player_record(mem, r)                                # 51D8-51E5
            r.al = rb(mem, r, 6)
            r.ah = 0
            r.di = r.ax
            r.al = mem.ds8((r.di + 0x7E5) & M16)                 # 51EF
            r.ah = 0
            r = yield from guest(mem, r, "214B:06D0", r.ax, ret="51FB")
            near_goal = r.al != 0
    if near_goal:                                                # 5202
        if mem.ds8(0x8303):
            nested(mem, r)
            point = rw(mem, r, 0)
            seg, off = nested(mem, r)
            r = yield from guest(mem, r, "2EF0", point, seg, off, ret="5220")
            if r.al:
                seg, off = nested(mem, r)
                r = yield from guest(mem, r, "3EDF", seg, off, ret="5231")
            else:
                nested(mem, r)                                   # 5233
                player_record(mem, r)
                r.al = rb(mem, r, 6)
                r.ah = 0
                r.di = r.ax
                r.al = mem.ds8((r.di + 0x7E5) & M16)             # 5251
                r.ah = 0
                r = yield from guest(mem, r, "214B:06D0", r.ax, ret="525D")
                if r.al:
                    r.al = 0x12                                  # 5261
                    template = r.ax
                    seg, off = nested(mem, r)
                    r = yield from guest(mem, r, "3EC5", template, seg, off, ret="5271")
        else:
            r.al = 0x11                                          # 5273
            template = r.ax
            seg, off = nested(mem, r)
            r = yield from guest(mem, r, "3EC5", template, seg, off, ret="5283")
        if mem.ds8(0x8303):                                      # 5283
            mem.wds8(0x8303, 0, "0791:528A")
        return (yield from _5049_end(mem, r))
    seg, off = nested(mem, r)                                    # 5292
    r = yield from guest(mem, r, "2BE5", seg, off, ret="529F")
    cbw(r)
    r.dx = r.ax
    nested(mem, r)
    r.al = rb(mem, r, 1)
    cbw(r)
    imul(r, r.dx)
    if s16(r.ax) < -0x14:                                        # 52B0 cmp ax, 0xffec; jge 52DD
        r.ax = 4
        r = yield from guest(mem, r, "214B:06D0", 4, ret="52BE")
        if r.al:
            r.ax = 9
            seg, off = nested(mem, r)
            r = yield from guest(mem, r, "3EF8", 9, seg, off, ret="52D3")
        else:
            r = yield from guest(mem, r, "4E28", ss16(mem, r, r.bp + 4), ret="52DB", far=False)
        return (yield from _5049_end(mem, r))
    r.ax = 2                                                     # 52DD
    seg, off = nested(mem, r)
    r = yield from guest(mem, r, "26D7", 2, seg, off, ret="52EE")
    choose = False
    if r.al:
        r = yield from guest(mem, r, "214B:06FA", ret="52F7")
        choose = r.al != 0
    if not choose:                                               # 52FB
        nested(mem, r)
        player_record(mem, r)
        r.al = rb(mem, r, 0xE)
        cbw(r)
        cwd(r)
        r.cx = 2
        q = int(s16(r.ax) / 2)                                   # 531A idiv cx: toward zero
        r.ax, r.dx = q, s16(r.ax) - 2 * q
        r = yield from guest(mem, r, "214B:06D0", r.ax, ret="5322")
        choose = r.al != 0
    if choose:                                                   # 5326
        r = yield from guest(mem, r, "4E28", ss16(mem, r, r.bp + 4), ret="532C", far=False)
    return (yield from _5049_end(mem, r))


def _5049_end(mem, r):
    """5332-5338: `mov al, [bp - 1]` and the epilogue (a generator only to be called with `yield from`)."""
    r.al = ss8(mem, r, r.bp - 1)
    r.leave()
    r.store()
    return r.ax
    yield                                                        # pragma: no cover


# -- 533B ----------------------------------------------------------------------------------------------------------
@PORTS.port("0791:533B", ret="ret 2")
def pass_receiver_destination(mem, variant):
    """533B-539C: the record whose slot is the pass target DS:830C runs to the ball (keeper or DS:8300 < 10) or to
    DS:8313."""
    r = Regs(mem)
    r.enter(2)
    nested(mem, r)
    r.al = rb(mem, r, 6)
    if r.al != mem.ds8(0x830C):                                  # 534C
        r.local8(-1, 0)                                          # 5392
    else:
        r.local8(-1, 1)                                          # 5352
        nested(mem, r)
        r.al = rb(mem, r, 6)
        r.ah = 0
        r = yield from guest(mem, r, "045D", r.ax, ret="5367", far=False)
        if r.al or mem.ds16(0x8300) < 0xA:                       # 5369-5370 jae 5382
            r.ax = mem.ds16(0x8313 if variant == "receiver-to-target" else 0x82F6)   # 5372
            nested(mem, r)
            mem.w16(mem.addr(r.es, r.di + 7), r.ax, "0791:537C")
        else:
            r.ax = mem.ds16(0x8313)                              # 5382
            nested(mem, r)
            mem.w16(mem.addr(r.es, r.di + 7), r.ax, "0791:538C")
    r.al = ss8(mem, r, r.bp - 1)                                 # 5396
    r.leave()
    r.store()
    return r.ax


# -- 539F ----------------------------------------------------------------------------------------------------------
@PORTS.port("0791:539F", ret="ret 2")
def foul_outcome_line(mem, variant):
    """539F-5471: the challenger wins the ball (5474, 5513): 4D3F on the holder's record, then by DS:8303 a clearance
    (408E), a beep and 869F with commentary 0x0E, or 5E41 with 0x0E and 0x21."""
    r = Regs(mem)
    r.enter(0)
    r.al = mem.ds8(0x830B)
    r.ah = 0
    r = yield from guest(mem, r, "045D", r.ax, ret="53AB", far=False)
    if r.al:
        r.leave()                                                # 546E
        r.store()
        return None
    slot_offset(r, mem.ds8(0x830B))                              # 53B2-53BA
    r.di = r.ax + 0x80E8
    r = yield from guest(mem, r, "4D3F", mem.DS, r.di, ret="53C8")
    if mem.ds8(0x8303) == 0:
        r.ax = 0x64
        r.ax = 5
        r = yield from guest(mem, r, "214B:1EA1", 0x64, 5, ret="53DC")
    if mem.ds8(0x8303) == 0:                                     # 53DC
        r = yield from guest(mem, r, "214B:06FA", ret="53E8")
        win = r.al != 0
        if not win:
            r.ax = 3
            seg, off = nested(mem, r, 2)
            r = yield from guest(mem, r, "287C", 3, seg, off, ret="5401")
            win = r.al != 0
        if win:                                                  # 5405
            seg, off = nested(mem, r, 2)
            r = yield from guest(mem, r, "869F", seg, off, ret="5416")
            r.al = 0xE
            r = yield from guest(mem, r, "2AA3", r.ax, ret="541C", far=False)
            r.leave()
            r.store()
            return None
    if mem.ds8(0x8303):                                          # 541E
        point = mem.ds16(0x82F6)
        seg, off = nested(mem, r, 2)
        r = yield from guest(mem, r, "2EB8", point, seg, off, ret="543A")
        if r.al:
            seg, off = nested(mem, r, 2)
            r = yield from guest(mem, r, "408E", seg, off, ret="544F")
            r.leave()
            r.store()
            return None
    seg, off = nested(mem, r, 2)                                 # 5451
    r = yield from guest(mem, r, "5E41", seg, off, ret="5462")
    r.al = 0xE
    r = yield from guest(mem, r, "2AA3", r.ax, ret="5468", far=False)
    r.al = 0x21
    r = yield from guest(mem, r, "2AA3", r.ax, ret="546E", far=False)
    r.leave()
    r.store()
    return None


# -- 5474 ----------------------------------------------------------------------------------------------------------
@PORTS.port("0791:5474", ret="ret 2")
def tackle_roll(mem, variant):
    """5474-5510: rand(skill of the holder) against rand(skill of the challenger * factor); the challenger wins
    (539F, returns 1) on the larger roll."""
    r = Regs(mem)
    r.enter(2)
    r.local8(-1, 0)                                              # 547A
    r.al = mem.ds8(0x8303)
    cbw(r)
    r.di = r.ax
    r.al = mem.ds8((r.di + 0x7F6) & M16)                         # 5484
    r.ah = 0
    element = r.ax
    slot_offset(r, mem.ds8(0x830B))                              # 548B-5493
    r.di = r.ax + 0x80E8
    r = yield from guest(mem, r, "278A", element, mem.DS, r.di, ret="54A1")
    r = yield from guest(mem, r, "214B:06B1", r.ax, ret="54A7")
    r.push(r.ax)                                                 # 54A7: the holder's roll
    close = False
    if mem.ds8(0x8303) == 0:
        seg, off = nested(mem, r, 2)
        r = yield from guest(mem, r, "2C54", seg, off, ret="54C0")
        close = r.al != 0
    r.al = 0 if close else 1                                     # 54C4 / 54C8
    cbw(r)
    r.di = r.ax
    r.al = mem.ds8((r.di + 0x7F8) & M16)                         # 54CD
    r.ah = 0
    r.push(r.ax)                                                 # 54D3: the factor, live across 278A
    r.al = mem.ds8(0x8303)
    cbw(r)
    r.di = r.ax
    r.al = mem.ds8((r.di + 0x7F4) & M16)                         # 54DA
    r.ah = 0
    element = r.ax
    seg, off = nested(mem, r, 2)
    r = yield from guest(mem, r, "278A", element, seg, off, ret="54F2")
    r.dx = pop(mem, r)                                           # 54F2
    mul(r, r.dx)
    r = yield from guest(mem, r, "214B:06B1", r.ax, ret="54FB")
    r.dx = pop(mem, r)                                           # 54FB
    if s16(r.ax) > s16(r.dx):                                    # 54FC-54FE jle 550A
        r = yield from guest(mem, r, "539F", ss16(mem, r, r.bp + 4), ret="5506", far=False)
        r.local8(-1, 1)                                          # 5506
    r.al = ss8(mem, r, r.bp - 1)                                 # 550A
    r.leave()
    r.store()
    return r.ax


# -- 5513 ----------------------------------------------------------------------------------------------------------
@PORTS.port("0791:5513", ret="ret 2")
def challenge_foul_gate(mem, variant):
    """5513-5562: when 4DA9 says the challenger fouls: a coin between the watched foul sequence 8206 and 539F."""
    r = Regs(mem)
    r.enter(2)
    r.local8(-1, 0)                                              # 5519
    seg, off = nested(mem, r, 2)
    r = yield from guest(mem, r, "4DA9", seg, off, ret="552E")
    if r.al:
        r = yield from guest(mem, r, "214B:06FA", ret="5537")
        if r.al:
            nested(mem, r, 2)                                    # 553B
            r.al = rb(mem, r, 6)
            r.ah = 0
            r = yield from guest(mem, r, "8206", r.ax, ret="5550", far=False)
        else:
            r = yield from guest(mem, r, "539F", ss16(mem, r, r.bp + 4), ret="5558", far=False)
        r.local8(-1, 1)                                          # 5558
    r.al = ss8(mem, r, r.bp - 1)                                 # 555C
    r.leave()
    r.store()
    return r.ax


# -- 5565 ----------------------------------------------------------------------------------------------------------
@PORTS.port("0791:5565", ret="ret 2")
def challenge_duel(mem, variant):
    """5565-56D6: the challenge of a record at the ball on the holder (offside 82EB, the keeper's duel 5B36, else the
    'challenge by' line, the tackle 5474, the foul gate 5513, 4151 and 4D3F)."""
    r = Regs(mem)
    r.enter(2)
    r.local8(-1, 0)                                              # 556B
    result = yield from _5565_body(mem, r)
    r = result
    r.al = ss8(mem, r, r.bp - 1)                                 # 56D0
    r.leave()
    r.store()
    return r.ax


def _5565_body(mem, r):
    if mem.ds8(0x8325) == 0:                                     # 556F
        return r
    seg, off = nested(mem, r)
    r = yield from guest(mem, r, "2CEC", seg, off, ret="5586")
    if r.al == 0:
        slot_offset(r, mem.ds8(0x830B))                          # 558A-5592
        r.di = r.ax
        r.ax = mem.ds16((r.di + 0x80E8) & M16)                   # 5596
        nested(mem, r)
        if r.ax != rw(mem, r, 0):                                # 55A1
            return r
    seg, off = nested(mem, r)                                    # 55A6
    r = yield from guest(mem, r, "2B51", seg, off, ret="55B3")
    if r.al or mem.ds8(0x8302):
        return r
    r.al = mem.ds8(0x830B)                                       # 55BE
    r.ah = 0
    r = yield from guest(mem, r, "045D", r.ax, ret="55C7", far=False)
    if r.al:
        return r
    seg, off = nested(mem, r)
    r = yield from guest(mem, r, "2F28", seg, off, ret="55D8")
    if r.al:
        return r
    seg, off = nested(mem, r)
    r = yield from guest(mem, r, "2BE5", seg, off, ret="55E9")
    cbw(r)
    r.dx = r.ax
    nested(mem, r)
    r.al = rb(mem, r, 1)
    cbw(r)
    imul(r, r.dx)
    if s16(r.ax) > 0:                                            # 55FA-55FC jle 5616
        r.ax = 3
        seg, off = nested(mem, r)
        r = yield from guest(mem, r, "287C", 3, seg, off, ret="560F")
        if r.al == 0:
            return r
    r.local8(-1, 1)                                              # 5616
    if mem.ds8(0x830E):                                          # 561A jbe 5627
        r = yield from guest(mem, r, "82EB", ret="5624", far=False)
        return r
    nested(mem, r)                                               # 5627
    r.al = rb(mem, r, 6)
    r.ah = 0
    r = yield from guest(mem, r, "045D", r.ax, ret="5638", far=False)
    if r.al:
        seg, off = nested(mem, r)
        r = yield from guest(mem, r, "5B36", seg, off, ret="5649")
        return r
    moving = mem.ds8(0x8303) != 0                                # 564C
    r.al = 0x41 if moving else 0xB                               # 5653 / 5665
    template = r.ax
    seg, off = nested(mem, r)
    r = yield from guest(mem, r, "2B28", template, seg, off, ret="5663" if moving else "5675")
    r = yield from guest(mem, r, "5474", r.bp, ret="5679", far=False)
    if r.al:
        return r
    r = yield from guest(mem, r, "5513", r.bp, ret="5681", far=False)
    if r.al:
        return r
    r = yield from guest(mem, r, "4151", ret="5688", far=False)
    if r.al:
        return r
    r.al = mem.ds8(0x830B)                                       # 568C
    r.ah = 0
    r = yield from guest(mem, r, "045D", r.ax, ret="5695", far=False)
    if r.al:
        return r
    seg, off = nested(mem, r)
    r = yield from guest(mem, r, "4D3F", seg, off, ret="56A6")
    if mem.ds8(0x8303) == 0:
        r.al = 0xC                                               # 56AD
        r = yield from guest(mem, r, "2AA3", r.ax, ret="56B3", far=False)
        return r
    nested(mem, r)                                               # 56B5
    player_record(mem, r)
    lin = mem.addr(r.es, r.di + 0x12)
    mem.w16(lin, mem.u16(lin) + 0xA, "0791:56CB")
    return r


# -- 56D9 ----------------------------------------------------------------------------------------------------------
@PORTS.port("0791:56D9", ret="ret 2")
def offside_call(mem, variant):
    """56D9-5726: with an offside player (DS:830E) the free kick goes to the other side (26A0) and the 'offside' line
    0x42 is said once (DS:8329); always returns 0."""
    r = Regs(mem)
    r.enter(2)
    r.local8(-1, 0)                                              # 56DF
    if mem.ds8(0x830E):                                          # 56E3 jbe 5720
        slot_offset(r, mem.ds8(0x830E))
        r.di = r.ax + 0x80E8
        r = yield from guest(mem, r, "2BE5", mem.DS, r.di, ret="5700")
        r.al = 1 if r.al & 0x80 else 0                           # 5700-5708 jl
        r = yield from guest(mem, r, "26A0", r.ax, ret="570E", far=False)
        if mem.ds8(0x8329) == 0:
            r.al = 0x42                                          # 5715
            r = yield from guest(mem, r, "2B0F", r.ax, ret="571B", far=False)
        mem.wds8(0x8329, 1, "0791:571B")
    r.al = ss8(mem, r, r.bp - 1)                                 # 5720
    r.leave()
    r.store()
    return r.ax


# -- 5729 ----------------------------------------------------------------------------------------------------------
@PORTS.port("0791:5729", ret="ret 2")
def chase_ball_gate(mem, variant):
    """5729-57A9: a defender off the ball's side and not a keeper goes for the ball when 2EB8 holds and (2EF0 holds or
    effective element 6 is clear)."""
    r = Regs(mem)
    r.enter(2)
    go = False
    nested(mem, r)
    r.al = rb(mem, r, 6)
    r.ah = 0
    r = yield from guest(mem, r, "045D", r.ax, ret="5740", far=False)
    if r.al == 0:
        seg, off = nested(mem, r)
        r = yield from guest(mem, r, "2B51", seg, off, ret="5751")
        if r.al == 0:
            point = mem.ds16(0x82F6)
            seg, off = nested(mem, r)
            r = yield from guest(mem, r, "2EB8", point, seg, off, ret="5766")
            if r.al:
                nested(mem, r)
                point = rw(mem, r, 0)
                seg, off = nested(mem, r)
                r = yield from guest(mem, r, "2EF0", point, seg, off, ret="5781")
                go = True
                if r.al == 0:
                    r.ax = 6
                    seg, off = nested(mem, r)
                    r = yield from guest(mem, r, "26D7", 6, seg, off, ret="5796")
                    go = r.al == 0                               # 5798 je 579E
    r.al = 1 if go else 0                                        # 579A / 579E
    r.local8(-1, r.al)                                           # 57A0
    r.leave()
    r.store()
    return r.ax


# -- 57AC ----------------------------------------------------------------------------------------------------------
@PORTS.port("0791:57AC", ret="retf 4")
def play_state_update(mem, variant):
    """57AC-58DE: the per-update decision of a pitch record in state 5 (play)."""
    r = Regs(mem)
    r.enter(2)
    for target, ret in (("56D9", "57B6"), ("5049", "57BE"), ("533B", "57C6"), ("5565", "57CE")):
        r = yield from guest(mem, r, target, r.bp, ret=ret, far=False)
        if r.al:
            r.leave()                                            # 57D2
            r.store()
            return None
    r.al = mem.ds8(0x830B)                                       # 57D5
    r.ah = 0
    r = yield from guest(mem, r, "045D", r.ax, ret="57DE", far=False)
    if r.al and mem.ds8(0x8302) == 0:
        seg, off = own(mem, r)                                   # 57E9
        r = yield from guest(mem, r, "4B64", seg, off, ret="57F2")
        r.leave()
        r.store()
        return None
    to_ball = None                                               # None: 4A28's destination; True: the ball's
    if mem.ds8(0x8327) == 5 and mem.ds16(0x8300) > 0:            # 57F5-5801
        r.ax = mem.ds16(0x82F6)
        own(mem, r)
        mem.w16(mem.addr(r.es, r.di + 7), r.ax, "0791:5809")
        to_ball = False                                          # 580D jmp 58C2
    elif mem.ds8(0x8325):                                        # 5810
        candidate = True
        if mem.ds8(0x830C):                                      # 581A
            seg, off = own(mem, r)
            r = yield from guest(mem, r, "2BB1", seg, off, ret="582A")
            if r.al != 2:
                own(mem, r)                                      # 582E
                player_record(mem, r)
                candidate = rb(mem, r, 6) == 1
        if candidate and mem.ds8(0x8302) == 0:                   # 5847
            seg, off = own(mem, r)
            r = yield from guest(mem, r, "2B51", seg, off, ret="5857")
            candidate = r.al == 0
        if candidate:                                            # 585B
            r = yield from guest(mem, r, "5729", r.bp, ret="585F", far=False)
            if r.al:
                to_ball = True
            else:
                for table, ret in ((0x8311, "586C"), (0x830F, "5885")):
                    seg, off = own(mem, r)
                    r = yield from guest(mem, r, "2974", seg, off, ret=ret)
                    cbw(r)
                    r.di = r.ax
                    r.al = mem.ds8((r.di + table) & M16)         # 586F / 5888
                    own(mem, r)
                    if r.al == rb(mem, r, 6) and not (table == 0x8311 and variant == "nearest-not-chasing"):
                        to_ball = True                           # 5876 / 588F je 58AD
                        break
                if to_ball is None and mem.ds8(0x830C) == 0:     # 5895
                    point = mem.ds16(0x82F6)
                    seg, off = own(mem, r)
                    r = yield from guest(mem, r, "44C1", point, seg, off, ret="58A9")
                    if r.al:
                        to_ball = True
    if to_ball:                                                  # 58AD
        r.ax = mem.ds16(0x82F6)
        own(mem, r)
        mem.w16(mem.addr(r.es, r.di + 7), r.ax, "0791:58B3")
    elif to_ball is None:                                        # 58B9
        seg, off = own(mem, r)
        r = yield from guest(mem, r, "4A28", seg, off, ret="58C2")
    seg, off = own(mem, r)                                       # 58C2
    r = yield from guest(mem, r, "474D", seg, off, ret="58CB")
    if mem.ds8(0x8302):
        seg, off = own(mem, r)
        r = yield from guest(mem, r, "6188", seg, off, ret="58DB")
    r.leave()                                                    # 58DB
    r.store()
    return None


# -- 58E1 ----------------------------------------------------------------------------------------------------------
@PORTS.port("0791:58E1", ret="retf 4")
def chase_countdown(mem, variant):
    """58E1-5938: a record chasing: its countdown +0x10 runs down, then state 5 (at once for a keeper with the ball
    dead, DS:8302 set and DS:8300 = 0); the destination becomes its own point."""
    r = Regs(mem)
    r.enter(0)
    own(mem, r)
    r.al = rb(mem, r, 6)
    r.ah = 0
    r = yield from guest(mem, r, "045D", r.ax, ret="58F1", far=False)
    if r.al and mem.ds8(0x8302) and mem.ds16(0x8300) == 0:
        own(mem, r)
        mem.w8(mem.addr(r.es, r.di + 0x12), 5, "0791:5906")
    else:
        own(mem, r)                                              # 590D
        if rb(mem, r, 0x10) > 0:
            own(mem, r)
            mem.w8(mem.addr(r.es, r.di + 0x10), rb(mem, r, 0x10) - (2 if variant == "countdown-double" else 1),
                   "0791:591A")
        else:
            own(mem, r)
            mem.w8(mem.addr(r.es, r.di + 0x12), 5, "0791:5923")
    own(mem, r)                                                  # 5928
    r.ax = rw(mem, r, 0)
    own(mem, r)
    mem.w16(mem.addr(r.es, r.di + 7), r.ax, "0791:5931")
    r.leave()
    r.store()
    return None


# -- 593B ----------------------------------------------------------------------------------------------------------
@PORTS.port("0791:593B", ret="ret 4")
def woodwork_bounce(mem, variant):
    """593B-59B0 (nested in 59B3; args: the parent's BP, the template): the ball hits the woodwork: velocities
    negated, speed max(1, speed / 4), the template said, the parent's result set."""
    r = Regs(mem)
    r.enter(0)
    r.al = mem.ds8(0x8324)
    cbw(r)
    r.di = r.ax
    r.al = mem.ds8((r.di + 0x7FC) & M16)                         # 5944
    r.ah = 0
    r = yield from guest(mem, r, "214B:06D0", r.ax, ret="5950")
    if r.al == 0 or mem.ds8(0x8327) == 5:                        # 5952 / 5954-5959
        r.leave()
        r.store()
        return None
    if ss8(mem, r, r.bp + 6) == 0x1B:                            # 595B
        r = yield from guest(mem, r, "214B:06FA", ret="5966")
        if r.al:
            r.leave()
            r.store()
            return None
    r.ax = -mem.ds16(0x82FE)                                     # 596C-5971
    mem.wds16(0x82FE, r.ax, "0791:5971")
    r.ax = -mem.ds16(0x82FC)
    mem.wds16(0x82FC, r.ax, "0791:5979")
    r.ax, r.dx = 1, 0                                            # 597C-5982: push dx; push ax
    r.ax = mem.ds16(0x8300)
    r.cx = 4
    r.ax, r.dx = r.ax // 4, r.ax % 4                             # 598B div cx
    r.dx = 0
    r = yield from guest(mem, r, "214B:0D56", 0, 1, 0, r.ax, ret="5996")
    mem.wds16(0x8300, r.ax, "0791:5996")
    r.al = ss8(mem, r, r.bp + 6)                                 # 5999
    r = yield from guest(mem, r, "2AA3", r.ax, ret="59A0", far=False)
    r.di = ss16(mem, r, r.bp + 4)
    mem.w8(mem.ss_lin(r.di - 1), 1, "0791:59A3")
    mem.wds8(0x8324, 0, "0791:59A8")
    r.leave()
    r.store()
    return None


# -- 59B3 ----------------------------------------------------------------------------------------------------------
@PORTS.port("0791:59B3", ret="ret")
def check_woodwork(mem, variant):
    """59B3-5A32: with the ball moving to the goal line (|y| = 0x25, |x| <= 1) and no keeper holding it, 593B may
    bounce it off the woodwork; returns 1 when it does. With DS:8325 and DS:8324 both clear it returns its local
    byte unwritten, as the listing does (59C5 je 5A2C)."""
    r = Regs(mem)
    r.enter(2)
    if mem.ds8(0x8325) or mem.ds8(0x8324):                       # 59B9-59C5
        r.local8(-1, 0)                                          # 59C7
        r.al = mem.ds8(0x830B)
        r.ah = 0
        r = yield from guest(mem, r, "045D", r.ax, ret="59D4", far=False)
        if r.al == 0 and mem.ds16(0x8300) != 0:                  # 59D6-59DD
            if byte_abs(r, mem.ds8(0x82F7)) == 0x25 and byte_abs(r, mem.ds8(0x82F6)) <= 1:   # 59E1-59FD
                if byte_abs(r, mem.ds8(0x82F6)) == 0:            # 5A09 je 5A1E
                    r.al = 1
                else:
                    r.ax = 4
                    r = yield from guest(mem, r, "214B:06D0", 4, ret="5A16")
                    r.al = 1 if r.al else 0                      # 5A18-5A1E
                cbw(r)                                           # 5A20
                r.di = r.ax
                r.al = mem.ds8((r.di + 0x7FA) & M16)             # 5A23
                r = yield from guest(mem, r, "593B", r.ax, r.bp, ret="5A2C", far=False)
    r.al = ss8(mem, r, r.bp - 1)                                 # 5A2C
    r.leave()
    r.store()
    return r.ax


# -- 5A33 ----------------------------------------------------------------------------------------------------------
@PORTS.port("0791:5A33", ret="ret 4")
def saved_line(mem, variant):
    """5A33-5A8B (args: the parent's BP, the template): the keeper takes the ball (DS:830B), the template is said and,
    in play, the side's saves counter DS:7B83 + 10 * side grows; outside play DS:830B is the byte at the parent's
    BP-2."""
    r = Regs(mem)
    r.enter(0)
    nested(mem, r)
    r.al = rb(mem, r, 6)
    mem.wds8(0x830B, r.al, "0791:5A41")
    r.al = ss8(mem, r, r.bp + 6)                                 # 5A44
    r = yield from guest(mem, r, "2AA3", r.ax, ret="5A4B", far=False)
    if mem.ds8(0x8326) == 0:
        seg, off = nested(mem, r)
        r = yield from guest(mem, r, "2974", seg, off, ret="5A5F")
        cbw(r)
        r.dx = 0xA
        mul(r, r.dx)
        r.di = r.ax
        mem.wds8(r.di + 0x7B83, mem.ds8((r.di + 0x7B83) & M16) + 1, "0791:5A67")
    else:
        r.di = ss16(mem, r, r.bp + 4)                            # 5A6D
        r.al = ss8(mem, r, r.di - 2)
        mem.wds8(0x830B, r.al, "0791:5A74")
    mem.wds8(0x8324, 0, "0791:5A77")
    if mem.ds8(0x8326) == 0:
        mem.wds8(0x8327, 0, "0791:5A83")
    r.leave()
    r.store()
    return None


# -- 5A8E ----------------------------------------------------------------------------------------------------------
@PORTS.port("0791:5A8E", ret="ret 2")
def write_save_line(mem, variant):
    """5A8E-5AF3: the keeper's save: the ball stops (869F, or DS:8300 = 0 outside play), 'saved by' (5A33, 0x1D),
    then 4D3F inside the keeper's area (2EB8) or the clearance 3FAD with event 9."""
    r = Regs(mem)
    r.enter(0)
    if mem.ds8(0x8326):
        r.ax = 0
        mem.wds16(0x8300, 0, "0791:5A9A")
    else:
        seg, off = nested(mem, r)
        r = yield from guest(mem, r, "869F", seg, off, ret="5AAC")
    r.al = 0x1D                                                  # 5AAC
    r = yield from guest(mem, r, "5A33", r.ax, ss16(mem, r, r.bp + 4), ret="5AB5", far=False)
    nested(mem, r)
    point = rw(mem, r, 0)
    seg, off = nested(mem, r)
    r = yield from guest(mem, r, "2EB8", point, seg, off, ret="5ACC")
    if r.al:
        seg, off = nested(mem, r)
        r = yield from guest(mem, r, "4D3F", seg, off, ret="5ADD")
    else:
        r.ax = 9
        seg, off = nested(mem, r)
        r = yield from guest(mem, r, "3FAD", 9, seg, off, ret="5AF0")
    r.leave()
    r.store()
    return None
