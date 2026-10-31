"""Duels, play at the ball, the goal and the after-goal swing in GOAL.EXE segment 0791 (T66, route C step P4a).

Translated instruction by instruction from static/goal-exe/code/seg_0791_10.asm (5B36-6334) and seg_0791_11.asm
(6337-68E9), after the named view (named/seg_0791_04.c and _05.c). The line comments are the listing's offsets. As in
T65's contests.py the routines are written in the registers the listing uses (runtime.Regs), so the words they push for
their callees (`mov al, n; push ax` keeps the AH of the instruction before), the words they hold on the guest stack
across a call and the locals of their frames are the original's: the family digests cover the stack (notes.md rule 2a).

Every call of the listing stays a guest call (port/guest.py), between the routines of this module too, and to the
callees of other rows (T65's 4DA9, 5A33, 5A8E; T68's 7CC5, 8062, 8206, 82EB, C173; T73's 0441, 0712; T77's B3B7).
The set test 23E4:08DF answers in ZF (`test byte ptr es:[bx + di], al`), which the listing's `jne`/`je` after it
reads: the port reads it from the flags the callee left.

The score: 67B6's `inc byte ptr [di - 0x64c4]` (685C) is the watched goal and its `dec` (68B3, DS:830E set) the goal
taken back; the port writes DS:9B3C + side through the memory view as those two instructions, so the kit sees each
as the write it reads (match.py GOAL_WRITE, CANCEL_WRITE) and no other.

The nested routines (`ret 2` with the parent's BP pushed) read their parent's far pointer through it: 5F8A one level
(6188's frame), 5F06 two (5F8A's, then 6188's). 5F8A writes its parent's local byte (6188's BP-1) at 5FDD."""
from . import Registry
from .contests import guest, ss16, ss8, pop, nested, own, rb, rw, byte_abs
from .mem import s8, s16
from .geometry import cbw, cwd, mul, imul
from .runtime import Regs

PORTS = Registry("duels", "duels, play at the ball, the goal and the after-goal swing: 5B36-68E9 (T66)")
PORTS.variant("deflect-step-3", "5E41 at 5E6C: each axis of a deflection moves by rand + 3, not rand + 2")
PORTS.variant("swing-reversed", "65FE at 669D: the after-goal form swing takes the other side's sign of DS:7920")
PORTS.variant("loose-line-0x23", "5F8A at 6165: the line for a loose ball off the holding side is 0x23, not 0x22")
M16 = 0xFFFF
ZF = 0x40                    # EFLAGS' zero flag: 23E4:08DF's answer


def zero_flag(mem):
    return bool(mem.reg("eflags") & ZF)


def holder_record(r, mem):
    """`mov al, [0x830b]; xor ah, ah; mov dx, 0x16; mul dx; mov di, ax; add di, 0x80e8`: DS:830B's pitch record."""
    r.al = mem.ds8(0x830B)
    r.ah = 0
    r.dx = 0x16
    mul(r, r.dx)
    r.di = r.ax + 0x80E8
    return r.di


def slot_record(r, slot):
    """`mov ax, slot; mov dx, 0x16; mul dx; mov di, ax; add di, 0x80e8`."""
    r.ax = slot
    r.dx = 0x16
    mul(r, r.dx)
    r.di = r.ax + 0x80E8
    return r.di


def flip(r, value):
    """`or al, al; je +4; mov al, 0; jmp +2; mov al, 1` (or `cmp b, 0` before it): 1 when value is 0, else 0."""
    r.al = 0 if value else 1


def table_by_al(r, mem, table):
    """`cbw; mov di, ax; mov al, byte ptr [di + table]`."""
    cbw(r)
    r.di = r.ax
    r.al = mem.ds8((r.di + table) & M16)


def div_by_4_long(r, mem):
    """`mov ax, [0x8300]; xor dx, dx; mov cx, 4; div cx; xor dx, dx`."""
    r.ax = mem.ds16(0x8300)
    r.dx = 0
    r.cx = 4
    r.ax, r.dx = r.ax // 4, r.ax % 4
    r.dx = 0


# -- 5B36 ----------------------------------------------------------------------------------------------------------
@PORTS.port("0791:5B36", ret="retf 4")
def duel_line(mem, variant):
    """5B36-5E3E: the keeper at the ball: with the ball dead (DS:8302 = 0) the duel with the holder (5BA6-5C3C: a
    win is the save 5A8E), the foul 4DA9 or the chase 4D3F; with it in flight the catch (5D69) and the parry 06B1(4):
    1 bounces it out (5A33 0x1E), 2 sends it wide (5A33 0x1F), else 5A8E; 2B51 true: the holder's own keeper takes it."""
    r = Regs(mem)
    r.enter(8)                                                   # 5B36-5B39
    if mem.ds8(0x8325) == 0 and mem.ds8(0x8324) == 0:            # 5B3C-5B4A
        return _5b36_end(r)
    seg, off = own(mem, r)                                       # 5B4D
    r = yield from guest(mem, r, "2B51", seg, off, ret="5B56")
    if r.al:                                                     # 5B58 je; 5B5A jmp 5E25
        if mem.ds8(0x8326) == 0:                                 # 5E25
            seg, off = own(mem, r)
            r = yield from guest(mem, r, "869F", seg, off, ret="5E35")
            r.al = 0x1C
            r = yield from guest(mem, r, "2AA3", r.ax, ret="5E3B", far=False)
        return _5b36_end(r)
    r.al = mem.ds8(0x830B)                                       # 5B5D
    r.ah = 0
    r.local16(-2, r.ax)                                          # 5B62
    if mem.ds8(0x8302) == 0:                                     # 5B65
        r = yield from _5b36_duel(mem, r, variant)
    else:
        r = yield from _5b36_catch(mem, r)
    return _5b36_end(r)


def _5b36_end(r):
    r.leave()                                                    # 5E3B
    r.store()
    return None


def _5b36_duel(mem, r, variant):
    """5B6F-5C85: the ball dead at the keeper's feet."""
    own(mem, r)                                                  # 5B6F
    point = rw(mem, r, 0)
    seg, off = own(mem, r)
    r = yield from guest(mem, r, "2EB8", point, seg, off, ret="5B7E")
    if r.al == 0:
        template = 0x0B                                          # 5B82
    elif mem.ds8(0x8303):
        template = 0x41                                          # 5B8F
    else:
        template = 0x0D                                          # 5B95
    r.local8(-7, template)
    r.al = template                                              # 5B99
    seg, off = own(mem, r)
    r = yield from guest(mem, r, "2B28", r.ax, seg, off, ret="5BA6")
    save = False
    if mem.ds8(0x8303):                                          # 5BA6
        r.ax = 4                                                 # 5BAD
        holder_record(r, mem)
        r = yield from guest(mem, r, "278A", 4, mem.DS, r.di, ret="5BC7")
        r = yield from guest(mem, r, "214B:06B1", r.ax, ret="5BCD")
        r.push(r.ax)                                             # 5BCD: the holder's roll, live across two calls
        r.ax = 1
        seg, off = own(mem, r)
        r = yield from guest(mem, r, "278A", 1, seg, off, ret="5BDB")
        r.ax = r.ax << 1                                         # 5BDB shl ax, 1
        r = yield from guest(mem, r, "214B:06B1", r.ax, ret="5BE3")
        r.dx = pop(mem, r)                                       # 5BE3
        save = s16(r.ax) > s16(r.dx)                             # 5BE4-5BE6 jg 5C3E
    if not save and mem.ds8(0x8303) == 0:                        # 5BE8 jne 5C44
        r.ax = 0xA                                               # 5BEF
        holder_record(r, mem)
        r = yield from guest(mem, r, "278A", 0xA, mem.DS, r.di, ret="5C09")
        r = yield from guest(mem, r, "214B:06B1", r.ax, ret="5C0F")
        r.push(r.ax)                                             # 5C0F
        r.ax = 1
        seg, off = own(mem, r)
        r = yield from guest(mem, r, "278A", 1, seg, off, ret="5C1D")
        r.cx = 0                                                 # 5C1D xor cx, cx; shl ax, cl
        r.dx = r.ax
        r.al = 0 if ss8(mem, r, r.bp - 7) == 0x0B else 1         # 5C23-5C2D
        r.ah = 0
        r.ax = r.ax + r.dx
        r = yield from guest(mem, r, "214B:06B1", r.ax, ret="5C39")
        r.dx = pop(mem, r)                                       # 5C39
        save = s16(r.ax) > s16(r.dx)                             # 5C3A-5C3C jle 5C44
    if save:                                                     # 5C3E
        r = yield from guest(mem, r, "5A8E", r.bp, ret="5C42", far=False)
        return r
    seg, off = own(mem, r)                                       # 5C44
    r = yield from guest(mem, r, "4DA9", seg, off, ret="5C4D")
    if r.al:
        r = yield from guest(mem, r, "214B:06FA", ret="5C56")
        if r.al:
            own(mem, r)                                          # 5C5A
            r.al = rb(mem, r, 6)
            r.ah = 0
            r = yield from guest(mem, r, "8206", r.ax, ret="5C67", far=False)
        else:
            r = yield from guest(mem, r, "5A8E", r.bp, ret="5C6D", far=False)
        return r
    if mem.ds8(0x8303) == 0:                                     # 5C6F
        r.al = 0x0C
        r = yield from guest(mem, r, "2AA3", r.ax, ret="5C7C", far=False)
    seg, off = own(mem, r)                                       # 5C7C
    r = yield from guest(mem, r, "4D3F", seg, off, ret="5C85")
    return r


def _5b36_catch(mem, r):
    """5C88-5E23: the ball in flight at the keeper."""
    if mem.ds8(0x8324):                                          # 5C88
        r.local16(-4, 1)                                         # 5C8F
    else:
        r.al = mem.ds8(0x8327)                                   # 5C96
        r.di = 0x5AF6
        r = yield from guest(mem, r, "23E4:08DF", r.ax, mem.seg(0x0791), 0x5AF6, ret="5CA4")
        r.al = 0 if zero_flag(mem) else 1                        # 5CA4 jne 5CAA
        table_by_al(r, mem, 0x7FE)                               # 5CAC-5CAF
        r.ah = 0
        r.local16(-4, r.ax)                                      # 5CB5
    if mem.ds8(0x8324) == 0:                                     # 5CB8
        r.ax = 0                                                 # 5CBF
        r.local16(-6, 0)
    else:
        r.ax = 3                                                 # 5CC6
        r = yield from guest(mem, r, "214B:06D0", 3, ret="5CCF")
        if r.al == 0:                                            # 5CD1; 5CD3 jmp 5E3B
            return r
        r.al = 1 if mem.ds8(0x8327) == 4 else 0                  # 5CD8-5CE3
        table_by_al(r, mem, 0x800)                               # 5CE5-5CE8
        r.ah = 0
        element = r.ax
        holder_record(r, mem)                                    # 5CEF-5CFB
        r = yield from guest(mem, r, "278A", element, mem.DS, r.di, ret="5D05")
        r.dx = 0                                                 # 5D05-5D0A div cx
        r.cx = 2
        r.ax, r.dx = r.ax // 2, r.ax % 2
        r.local16(-6, r.ax)                                      # 5D0C
    own(mem, r)                                                  # 5D0F
    point = rw(mem, r, 0)
    seg, off = own(mem, r)
    r = yield from guest(mem, r, "2EB8", point, seg, off, ret="5D1E")
    if r.al == 0:                                                # 5D20
        r.ax = 9                                                 # 5D22
        seg, off = own(mem, r)
        r = yield from guest(mem, r, "3FAD", 9, seg, off, ret="5D2F")
        return r
    caught = True
    if mem.ds16(0x8300) != 0:                                    # 5D32
        r.di = 0x82F6                                            # 5D39
        r = yield from guest(mem, r, "835F", mem.DS, 0x82F6, ret="5D42")
        r.cx = 2
        r.ax = r.ax << 2                                         # 5D45 shl ax, cl
        r = yield from guest(mem, r, "214B:06B1", r.ax, ret="5D4D")
        cwd(r)                                                   # 5D4D
        r.cx = r.ax
        r.bx = r.dx
        r.ax = ss16(mem, r, r.bp - 6)                            # 5D52
        r.dx = 0
        total = r.ax + r.cx
        r.ax = total
        r.dx = r.dx + r.bx + (total >> 16)                       # 5D59 adc dx, bx
        r.push(r.dx)                                             # 5D5B-5D5C: the ball's long, live across two calls
        r.push(r.ax)
        element = ss16(mem, r, r.bp - 4)                         # 5D5D
        seg, off = own(mem, r)
        r = yield from guest(mem, r, "278A", element, seg, off, ret="5D69")
        r = yield from guest(mem, r, "214B:06B1", r.ax, ret="5D6F")
        cwd(r)                                                   # 5D6F
        r.cx = pop(mem, r)                                       # 5D70
        r.bx = pop(mem, r)                                       # 5D71
        if s16(r.dx) != s16(r.bx):                               # 5D72-5D76
            caught = s16(r.dx) > s16(r.bx)
        else:
            caught = r.ax > r.cx                                 # 5D7B ja
    if not caught:
        return r                                                 # 5D78 / 5D7F jmp 5E23
    if mem.ds8(0x8326) == 0:                                     # 5D82
        r.al = mem.ds8(0x8327)                                   # 5D89
        r.di = 0x5B16
        r = yield from guest(mem, r, "23E4:08DF", r.ax, mem.seg(0x0791), 0x5B16, ret="5D97")
        if not zero_flag(mem):                                   # 5D97 je 5DA0
            r = yield from guest(mem, r, "2996", ret="5D9C", far=False)
            r = yield from guest(mem, r, "3C20", r.ax, ret="5DA0", far=False)
    r.ax = 4                                                     # 5DA0
    r = yield from guest(mem, r, "214B:06B1", 4, ret="5DA9")
    if r.ax == 1:                                                # 5DA9
        r.ax = -mem.ds16(0x82FE)                                 # 5DAE-5DB3
        mem.wds16(0x82FE, r.ax, "0791:5DB3")
        r.ax = -mem.ds16(0x82FC)                                 # 5DB6-5DBB
        mem.wds16(0x82FC, r.ax, "0791:5DBB")
        template, rets = 0x1E, ("5DD8", "5DE2")
    elif r.ax == 2:                                              # 5DE4
        r = yield from guest(mem, r, "214B:06FA", ret="5DEE")
        table_by_al(r, mem, 0x7920)                              # 5DEE-5DF1
        cbw(r)
        mem.wds16(0x82FC, r.ax, "0791:5DF6")
        template, rets = 0x1F, ("5E13", "5E1D")
    else:
        r = yield from guest(mem, r, "5A8E", r.bp, ret="5E23", far=False)    # 5E1F
        return r
    r.ax, r.dx = 1, 0                                            # 5DBE-5DC4 / 5DF9-5DFF
    div_by_4_long(r, mem)                                        # 5DC5-5DCF / 5E00-5E0A
    r = yield from guest(mem, r, "214B:0D56", 0, 1, 0, r.ax, ret=rets[0])
    mem.wds16(0x8300, r.ax, f"0791:{rets[0]}")                   # 5DD8 / 5E13
    r.al = template
    r = yield from guest(mem, r, "5A33", r.ax, r.bp, ret=rets[1], far=False)
    return r


# -- 5E41 ----------------------------------------------------------------------------------------------------------
@PORTS.port("0791:5E41", ret="retf 4")
def deflect_from_record(mem, variant):
    """5E41-5EA8: the ball leaves the record's point, each axis moved by (rand(DS:0802[8303]) + 2) times a coin's
    sign (DS:7920), after 869F; launched by 34C1 with speed 6."""
    r = Regs(mem)
    r.enter(4)                                                   # 5E41-5E44
    own(mem, r)                                                  # 5E47
    r.ax = rw(mem, r, 0)
    point = [r.ax & 0xFF, r.ax >> 8]
    r.local16(-2, r.ax)                                          # 5E4D
    r.local16(-4, 1)                                             # 5E50
    i = 1
    while True:
        r.al = mem.ds8(0x8303)                                   # 5E5A
        table_by_al(r, mem, 0x802)
        r.ah = 0
        r = yield from guest(mem, r, "214B:06B1", r.ax, ret="5E6C")
        r.ax = r.ax + (3 if variant == "deflect-step-3" else 2)  # 5E6C
        r.push(r.ax)                                             # 5E6F: the step, live across 06FA
        r = yield from guest(mem, r, "214B:06FA", ret="5E75")
        table_by_al(r, mem, 0x7920)                              # 5E75-5E78
        cbw(r)
        r.dx = pop(mem, r)                                       # 5E7D
        imul(r, r.dx)
        r.di = i                                                 # 5E80
        point[i - 1] = (point[i - 1] + r.al) & 0xFF
        r.local8(i - 3, point[i - 1])                            # 5E83 add byte ptr [bp + di - 3], al
        if i == 2:                                               # 5E86
            break
        i += 1
        r.local16(-4, i)                                         # 5E57
    seg, off = own(mem, r)                                       # 5E8C
    r = yield from guest(mem, r, "869F", seg, off, ret="5E95")
    moved = point[0] | (point[1] << 8)                           # 5E95 push word ptr [bp - 2]
    r.ax = 6
    seg, off = own(mem, r)
    r = yield from guest(mem, r, "34C1", moved, 6, seg, off, ret="5EA5")
    r.leave()
    r.store()
    return None


# -- 5EAB ----------------------------------------------------------------------------------------------------------
@PORTS.port("0791:5EAB", ret="retf 4")
def loose_ball_to_nearest(mem, variant):
    """5EAB-5EE3: the record takes the ball (869F), line 0x20, then with DS:80FA set the ball goes to the slot
    DS:8311[2996] (the side's nearest, 2FB1) through 384C; DS:80FA cleared."""
    r = Regs(mem)
    r.enter(0)
    seg, off = own(mem, r)                                       # 5EAE
    r = yield from guest(mem, r, "869F", seg, off, ret="5EB7")
    r.al = 0x20
    r = yield from guest(mem, r, "2AA3", r.ax, ret="5EBD", far=False)
    r = yield from guest(mem, r, "2FB1", ret="5EC0", far=False)
    mem.wds8(0x80FA, 1, "0791:5EC0")
    r = yield from guest(mem, r, "2996", ret="5EC8", far=False)
    table_by_al(r, mem, 0x8311)                                  # 5EC8-5ECB [di - 0x7cef]
    r.ah = 0
    slot = r.ax
    seg, off = own(mem, r)
    r = yield from guest(mem, r, "384C", slot, seg, off, ret="5EDB")
    mem.wds8(0x80FA, 0, "0791:5EDB")
    r.leave()
    r.store()
    return None


# -- 5F06 ----------------------------------------------------------------------------------------------------------
@PORTS.port("0791:5F06", ret="ret 2")
def deflection(mem, variant):
    """5F06-5F87 (nested in 5F8A, the record two frames up): with the ball moving and DS:8327 in the set at 0791:5EE6
    5EAB; else the deflection 5E41 with line 0x20 (ball moving) or DS:080A[2B51]; then DS:8303 := 06FA()."""
    r = Regs(mem)
    r.enter(2)
    moving = mem.ds8(0x8303)                                     # 5F0C
    r.al = moving
    r.local8(-1, moving)
    seg, off = nested(mem, r, 2)                                 # 5F12-5F19
    r = yield from guest(mem, r, "2B51", seg, off, ret="5F23")
    side = r.al
    r.local8(-2, side)                                           # 5F23
    if moving:                                                   # 5F26
        r.al = mem.ds8(0x8327)                                   # 5F2C
        r.di = 0x5EE6
        r = yield from guest(mem, r, "23E4:08DF", r.ax, mem.seg(0x0791), 0x5EE6, ret="5F3A")
        if zero_flag(mem):                                       # 5F3A jne 5F4F
            seg, off = nested(mem, r, 2)
            r = yield from guest(mem, r, "5EAB", seg, off, ret="5F4D")
            r.leave()
            r.store()
            return None
    seg, off = nested(mem, r, 2)                                 # 5F4F
    r = yield from guest(mem, r, "5E41", seg, off, ret="5F60")
    if ss8(mem, r, r.bp - 1):                                    # 5F60
        r.al = 0x20                                              # 5F66
        r = yield from guest(mem, r, "2AA3", r.ax, ret="5F6C", far=False)
    else:
        r.al = ss8(mem, r, r.bp - 2)                             # 5F6E
        table_by_al(r, mem, 0x80A)
        r = yield from guest(mem, r, "2AA3", r.ax, ret="5F7C", far=False)
    r = yield from guest(mem, r, "214B:06FA", ret="5F81")      # 5F7C
    mem.wds8(0x8303, r.al, "0791:5F81")
    r.leave()
    r.store()
    return None


# -- 5F8A ----------------------------------------------------------------------------------------------------------
@PORTS.port("0791:5F8A", ret="ret 2")
def react_off_ball(mem, variant):
    """5F8A-6185 (nested in 6188): a record at the ball not holding it: 'far' (835F > 10) kept in 6188's BP-1; with
    the ball moving a near header or clearance (287C 4), far a deflection (287C 3), near in the attack zone a shot (287C
    9 and DS:0808), else with the ball rolling 287C(DS:0804) and the commentary 0x19, 0x23 or 0x22 with 869F."""
    r = Regs(mem)
    r.enter(0)
    seg, off = nested(mem, r)                                    # 5F8D-5F90
    r = yield from guest(mem, r, "2B51", seg, off, ret="5F9A")
    if r.al == 0:                                                # 5F9C
        r.al = mem.ds8(0x830B)
        r.ah = 0
        r = yield from guest(mem, r, "045D", r.ax, ret="5FA7", far=False)
        if r.al and mem.ds16(0x8300) != 0:                       # 5FA9-5FB0 jbe 5FB5
            return _5f8a_end(r)
    if mem.ds8(0x8325) == 0 and mem.ds8(0x8324) == 0:            # 5FB5-5FC3
        return _5f8a_end(r)
    r.di = 0x82F6                                                # 5FC6
    r = yield from guest(mem, r, "835F", mem.DS, 0x82F6, ret="5FCF")
    r.al = 1 if r.ax > 0xA else 0                                # 5FCF cmp ax, 0xa; ja
    r.flush()
    r.di = ss16(mem, r, r.bp + 4)                                # 5FDA
    mem.w8(mem.ss_lin(r.di - 1), r.al, "0791:5FDD")

    def far():
        r.di = ss16(mem, r, r.bp + 4)
        return ss8(mem, r, r.di - 1)

    if mem.ds8(0x8303):                                          # 5FE1
        if far():                                                # 5FE8
            return _5f8a_end(r)
        r.ax = 4                                                 # 5FF2
        seg, off = nested(mem, r)
        r = yield from guest(mem, r, "287C", 4, seg, off, ret="6003")
        if r.al == 0:
            return _5f8a_end(r)
        point = mem.ds16(0x82F6)                                 # 6007
        seg, off = nested(mem, r)
        r = yield from guest(mem, r, "2EB8", point, seg, off, ret="6018")
        if r.al:
            seg, off = nested(mem, r)                            # 601C
            r = yield from guest(mem, r, "408E", seg, off, ret="6029")
            return _5f8a_end(r)
        point = mem.ds16(0x82F6)                                 # 602B
        seg, off = nested(mem, r)
        r = yield from guest(mem, r, "2EF0", point, seg, off, ret="603C")
        if r.al:
            seg, off = nested(mem, r)                            # 6040
            r = yield from guest(mem, r, "3EDF", seg, off, ret="604D")
        else:
            r = yield from guest(mem, r, "5F06", r.bp, ret="6053", far=False)   # 604F
        return _5f8a_end(r)
    if far():                                                    # 6056
        r.ax = 3                                                 # 6060
        seg, off = nested(mem, r)
        r = yield from guest(mem, r, "287C", 3, seg, off, ret="6071")
        if r.al:
            r = yield from guest(mem, r, "5F06", r.bp, ret="6079", far=False)   # 6075
        return _5f8a_end(r)
    shoot = False
    if not far():                                                # 607C
        seg, off = nested(mem, r)                                # 6086
        r = yield from guest(mem, r, "2F28", seg, off, ret="6093")
        if r.al:
            r.ax = 9                                             # 6097
            seg, off = nested(mem, r)
            r = yield from guest(mem, r, "287C", 9, seg, off, ret="60A8")
            if r.al:
                seg, off = nested(mem, r)                        # 60AC
                r = yield from guest(mem, r, "2B51", seg, off, ret="60B9")
                table_by_al(r, mem, 0x808)
                r.ah = 0
                r = yield from guest(mem, r, "214B:06D0", r.ax, ret="60C8")
                shoot = r.al != 0
    if shoot:
        seg, off = nested(mem, r)                                # 60CC
        r = yield from guest(mem, r, "2B51", seg, off, ret="60D9")
        table_by_al(r, mem, 0x806)
        template = r.ax
        seg, off = nested(mem, r)
        r = yield from guest(mem, r, "3EC5", template, seg, off, ret="60EE")
        return _5f8a_end(r)
    if mem.ds16(0x8300) != 0:                                    # 60F1
        seg, off = nested(mem, r)                                # 60F8
        r = yield from guest(mem, r, "2B51", seg, off, ret="6105")
        table_by_al(r, mem, 0x804)
        r.ah = 0
        element = r.ax
        seg, off = nested(mem, r)
        r = yield from guest(mem, r, "287C", element, seg, off, ret="611C")
        if r.al == 0:
            return _5f8a_end(r)
    seg, off = nested(mem, r)                                    # 6120
    r = yield from guest(mem, r, "2B51", seg, off, ret="612D")
    if r.al:
        r.al = mem.ds8(0x830B)                                   # 6131
        nested(mem, r)
        if r.al == rb(mem, r, 6):                                # 613B
            r.al, ret = 0x19, "6151"                             # 6141
        else:
            r.al, ret = 0x23, "6163"                             # 6153
    else:
        r.al, ret = (0x23 if variant == "loose-line-0x23" else 0x22), "6175"     # 6165
    template = r.ax
    seg, off = nested(mem, r)
    r = yield from guest(mem, r, "2B28", template, seg, off, ret=ret)
    seg, off = nested(mem, r)                                    # 6175
    r = yield from guest(mem, r, "869F", seg, off, ret="6182")
    return _5f8a_end(r)


def _5f8a_end(r):
    r.leave()                                                    # 6182
    r.store()
    return None


# -- 6188 ----------------------------------------------------------------------------------------------------------
@PORTS.port("0791:6188", ret="retf 4")
def handle_player_at_ball(mem, variant):
    """6188-61E9: watched match only (DS:9A3E = 0), state +0x12 not 13, the record at the ball (2CEC): a keeper
    5B36; another record, with DS:8326 and DS:830C clear and not the holder DS:830B, 5F8A."""
    r = Regs(mem)
    r.enter(2)                                                   # 6188-618B
    if mem.ds8(0x9A3E) == 0:                                     # 618E
        own(mem, r)                                              # 6195
        if rb(mem, r, 0x12) != 0xD:
            seg, off = own(mem, r)                               # 619F
            r = yield from guest(mem, r, "2CEC", seg, off, ret="61A8")
            if r.al:
                own(mem, r)                                      # 61AC
                r.al = rb(mem, r, 6)
                r.ah = 0
                r = yield from guest(mem, r, "045D", r.ax, ret="61B9", far=False)
                if r.al:
                    seg, off = own(mem, r)                       # 61BD
                    r = yield from guest(mem, r, "5B36", seg, off, ret="61C6")
                elif mem.ds8(0x8326) == 0 and mem.ds8(0x830C) == 0:      # 61C8-61D4
                    r.al = mem.ds8(0x830B)                       # 61D6
                    own(mem, r)
                    if r.al != rb(mem, r, 6):                    # 61DC
                        r = yield from guest(mem, r, "5F8A", r.bp, ret="61E6", far=False)
    r.leave()                                                    # 61E6
    r.store()
    return None


# -- 61EC ----------------------------------------------------------------------------------------------------------
@PORTS.port("0791:61EC", ret="ret")
def kick_off_to_conceding_side(mem, variant):
    """61EC-623F: DS:8325 := 0, the substitutions check 8062, the ball to slot DS:0668[side] + 10 of the side not
    holding it (of the holding side after an own goal, DS:7C39, which is then cleared), 2A15 and 2929(1)."""
    r = Regs(mem)
    r.enter(0)
    mem.wds8(0x8325, 0, "0791:61EF")
    r = yield from guest(mem, r, "8062", ret="61F7", far=False)
    if mem.ds8(0x7C39):                                          # 61F7
        r = yield from guest(mem, r, "2996", ret="6201", far=False)
        at = "0791:620D"
    else:
        r = yield from guest(mem, r, "2996", ret="6215", far=False)
        flip(r, r.al)                                            # 6215-621D
        at = "0791:622B"
    table_by_al(r, mem, 0x668)                                   # 6201-6204 / 621F-6222
    r.ah = 0
    r.ax = r.ax + 0xA
    mem.wds8(0x830B, r.al, at)
    mem.wds8(0x7C39, 0, "0791:622E")
    r = yield from guest(mem, r, "2A15", ret="6236", far=False)
    r.al = 1
    r = yield from guest(mem, r, "2929", r.ax, ret="623C", far=False)
    r.leave()
    r.store()
    return None


# -- 6240 ----------------------------------------------------------------------------------------------------------
@PORTS.port("0791:6240", ret="retf 4")
def kick_off_state(mem, variant):
    """6240-6334: a record at the kick-off: after an own goal 61EC; not the holder: to the holder's point when its
    side's score is not below the other's, else 4354; the holder: when its facing (+8) is not 5 times 2BE5 it turns,
    else with |+7| = 6 61EC, otherwise +7 := 6 * DS:7920[+7 < 0] (2CC5 or a 1-in-16 chance first)."""
    r = Regs(mem)
    r.enter(0)
    if mem.ds8(0x7C39):                                          # 6243
        r = yield from guest(mem, r, "61EC", ret="624D", far=False)
        return _6240_end(r)
    own(mem, r)                                                  # 6250
    r.al = rb(mem, r, 6)
    if r.al != mem.ds8(0x830B):                                  # 6257
        r = yield from guest(mem, r, "2996", ret="6260", far=False)
        flip(r, r.al)                                            # 6260-6268
        table_by_al(r, mem, 0x9B3C)                              # 626A-626D [di - 0x64c4]
        r.push(r.ax)                                             # 6271: the other side's score, live across 2996
        r = yield from guest(mem, r, "2996", ret="6275", far=False)
        table_by_al(r, mem, 0x9B3C)                              # 6275-6278
        r.dx = pop(mem, r)                                       # 627C
        if r.al >= (r.dx & 0xFF):                                # 627D cmp al, dl; jb 629A
            r.al = mem.ds8(0x830B)                               # 6281-628B
            r.ah = 0
            r.dx = 0x16
            mul(r, r.dx)
            r.di = r.ax
            r.ax = mem.ds16((r.di + 0x80E8) & M16)               # 628D [di - 0x7f18]
            own(mem, r)
            mem.w16(mem.addr(r.es, r.di + 7), r.ax, "0791:6294")
        else:
            seg, off = own(mem, r)                               # 629A
            r = yield from guest(mem, r, "4354", seg, off, ret="62A3")
        return _6240_end(r)
    seg, off = own(mem, r)                                       # 62A6
    r = yield from guest(mem, r, "2CC5", seg, off, ret="62AF")
    if r.al == 0:
        r.ax = 0x10                                              # 62B3
        r = yield from guest(mem, r, "214B:06D0", 0x10, ret="62BC")
        if r.al == 0:
            return _6240_end(r)
    seg, off = own(mem, r)                                       # 62C0
    r = yield from guest(mem, r, "2BE5", seg, off, ret="62C9")
    cbw(r)
    r.cx = 5
    imul(r, r.cx)
    r.dx = r.ax
    own(mem, r)                                                  # 62D1
    r.al = rb(mem, r, 8)
    cbw(r)
    if r.ax != r.dx:                                             # 62D9
        seg, off = own(mem, r)                                   # 62DD
        r = yield from guest(mem, r, "2BE5", seg, off, ret="62E6")
        cbw(r)
        r.cx = 5
        imul(r, r.cx)
        own(mem, r)
        mem.w8(mem.addr(r.es, r.di + 8), r.al, "0791:62EF")
        return _6240_end(r)
    own(mem, r)                                                  # 62F5
    if byte_abs(r, rb(mem, r, 7)) == 6:                          # 62F8-6306
        r = yield from guest(mem, r, "61EC", ret="6331", far=False)     # 632E
        return _6240_end(r)
    own(mem, r)                                                  # 6308
    r.al = 1 if s8(rb(mem, r, 7)) < 0 else 0                     # 630B-6316 jl
    table_by_al(r, mem, 0x7920)                                  # 6318-631B
    cbw(r)
    r.cx = 6
    imul(r, r.cx)
    own(mem, r)
    mem.w8(mem.addr(r.es, r.di + 7), r.al, "0791:6328")
    return _6240_end(r)


def _6240_end(r):
    r.leave()                                                    # 6331
    r.store()
    return None


# -- 6337 ----------------------------------------------------------------------------------------------------------
@PORTS.port("0791:6337", ret="ret")
def repick_kickoff_keeper(mem, variant):
    """6337-6442: a keeper holding (DS:830B, 045D) gives the ball to slot DS:0668[2996] + 1 + rand(10) after sending
    himself to his mirrored post (2C86, 2A15); the holder then faces his point (watched: DS:9A3E clear) by a coin:
    +8 := (10 + rand(25)) * 2BE5 and +7 := 7 * DS:7920[coin], or +8 := 0x24 * 2BE5 and +7 := rand(5) * DS:7920[coin]."""
    r = Regs(mem)
    r.enter(4)                                                   # 6337-633A
    r.al = mem.ds8(0x830B)                                       # 633D
    r.ah = 0
    r = yield from guest(mem, r, "045D", r.ax, ret="6346", far=False)
    if r.al:
        holder_record(r, mem)                                    # 634A-6356
        r.local16(-4, r.di)                                      # 635A
        r.local16(-2, mem.DS)                                    # 635D
        r.es = mem.DS                                            # 6360
        rec = r.di
        word = mem.ds16((rec + 9) & M16)                         # 6363
        r = yield from guest(mem, r, "2C86", word, mem.DS, rec, ret="6370")
        r.es, r.di = mem.DS, rec                                 # 6370
        mem.w16(mem.addr(r.es, r.di + 7), r.ax, "0791:6373")
        r = yield from guest(mem, r, "2996", ret="6377", far=False)
        table_by_al(r, mem, 0x668)                               # 6377-637D
        r.ah = 0
        r.push(r.ax)                                             # 6383: the side's first slot, live across 06B1
        r.ax = 0xA
        r = yield from guest(mem, r, "214B:06B1", 0xA, ret="638D")
        r.ax = r.ax + 1                                          # 638D
        r.dx = pop(mem, r)
        r.ax = r.ax + r.dx                                       # 638F
        mem.wds8(0x830B, r.al, "0791:6391")
        r = yield from guest(mem, r, "2A15", ret="6397", far=False)
    holder_record(r, mem)                                        # 6397-63A3
    rec = r.di
    r.local16(-4, rec)                                           # 63A7
    r.local16(-2, mem.DS)                                        # 63AA
    if mem.ds8(0x9A3E):                                          # 63AD
        r.es, r.di = mem.DS, rec                                 # 63B4
        r.ax = rw(mem, r, 0)
        mem.w16(mem.addr(r.es, r.di + 7), r.ax, "0791:63BD")
        r.leave()
        r.store()
        return None
    r = yield from guest(mem, r, "214B:06FA", ret="63C8")        # 63C3
    if r.al:
        r.ax = 0x19                                              # 63CC
        r = yield from guest(mem, r, "214B:06B1", 0x19, ret="63D5")
        r.ax = r.ax + 0xA                                        # 63D5
        r.push(r.ax)                                             # 63D8: the facing's factor, live across 2BE5
        r.es, r.di = mem.DS, rec                                 # 63D9
        r = yield from guest(mem, r, "2BE5", mem.DS, rec, ret="63E2")
        cbw(r)
        r.dx = pop(mem, r)                                       # 63E3
        imul(r, r.dx)
        r.es, r.di = mem.DS, rec
        mem.w8(mem.addr(r.es, r.di + 8), r.al, "0791:63E9")
        r = yield from guest(mem, r, "214B:06FA", ret="63F2")   # 63ED
        table_by_al(r, mem, 0x7920)
        cbw(r)
        r.cx = 7
        imul(r, r.cx)                                            # 63FD
        r.es, r.di = mem.DS, rec
        mem.w8(mem.addr(r.es, r.di + 7), r.al, "0791:6402")
    else:
        r.es, r.di = mem.DS, rec                                 # 6408
        r = yield from guest(mem, r, "2BE5", mem.DS, rec, ret="6411")
        cbw(r)
        r.cx = 0x24
        imul(r, r.cx)                                            # 6415
        r.es, r.di = mem.DS, rec
        mem.w8(mem.addr(r.es, r.di + 8), r.al, "0791:641A")
        r.ax = 5                                                 # 641E
        r = yield from guest(mem, r, "214B:06B1", 5, ret="6427")
        r.push(r.ax)                                             # 6427: the roll, live across 06FA
        r = yield from guest(mem, r, "214B:06FA", ret="642D")
        table_by_al(r, mem, 0x7920)
        cbw(r)
        r.dx = pop(mem, r)                                       # 6435
        imul(r, r.dx)
        r.es, r.di = mem.DS, rec
        mem.w8(mem.addr(r.es, r.di + 7), r.al, "0791:643B")
    r.leave()                                                    # 643F
    r.store()
    return None


# -- 6443 ----------------------------------------------------------------------------------------------------------
@PORTS.port("0791:6443", ret="ret 6")
def record_goal(mem, variant):
    """6443-65A1 (minute, slot, side): line 0x26 (0x27 for an own goal, DS:7C39, the side then reversed in its
    argument), the scorer's goals +0x0A and the top scorers B3B7 (when 1771:5A03 holds) for a goal of his own, his form
    7CC5(+-1), the count DS:80F0[side] + 1 up to 11 and the scorer row DS:7BD1 + 0x21 * side + 3 * count (player's
    squad word, minute, +0x80 with DS:8324 or 7C39), then the on-target count 3C20 unless an own goal."""
    r = Regs(mem)
    r.enter(0xA)                                                 # 6443-6446
    r.ax = ss16(mem, r, r.bp + 6)                                # 6449 the slot
    r.dx = 0x16
    mul(r, r.dx)
    r.di = r.ax + 0x80E8
    rec = r.di
    r.local16(-5, rec)                                           # 6457
    r.local16(-3, mem.DS)                                        # 645A
    if mem.ds8(0x7C39):                                          # 645D
        r.al = 0x27                                              # 6464
        r = yield from guest(mem, r, "2AA3", r.ax, ret="646A", far=False)
    else:
        r.al = 0x26                                              # 646C
        r = yield from guest(mem, r, "2AA3", r.ax, ret="6472", far=False)
        r.es, r.di = mem.DS, rec                                 # 6472
        r.ax = rw(mem, r, 0xD)
        r.dx = 0x14
        mul(r, r.dx)
        r.di, r.es = mem.ds16(0xA91B), mem.ds16(0xA91D)          # 647E
        r.di = r.di + r.ax
        lin = mem.addr(r.es, r.di + 0xA)
        mem.w16(lin, mem.u16(lin) + 1, "0791:6484")
        r.di, r.es = mem.ds16(0x7C2A), mem.ds16(0x7C2C)          # 6488
        r = yield from guest(mem, r, "1771:5A03", r.es, r.di, ret="6493")
        if r.al:
            r.es, r.di = mem.DS, rec                             # 6497
            player = rw(mem, r, 0xD)
            r.al = ss8(mem, r, r.bp + 8)                         # 649E
            cbw(r)
            r.di = (r.ax << 1) & M16                             # 64A2-64A4
            r.ax = mem.ds16((r.di + 0x9B34) & M16)               # 64A6 [di - 0x64cc]
            r.dx = 0xBF
            mul(r, r.dx)
            r.di, r.es = mem.ds16(0xA917), mem.ds16(0xA919)      # 64AF
            r.di = r.di + r.ax
            r.al = rb(mem, r, 0x2C)
            r.ah = 0
            r = yield from guest(mem, r, "B3B7", player, r.ax, ret="64BF", far=False)
    flip(r, mem.ds8(0x7C39))                                     # 64BF-64CA
    table_by_al(r, mem, 0x7920)                                  # 64CC-64CF
    cbw(r)
    sign = r.ax                                                  # 64D4 push ax
    r.al = 1
    r.es, r.di = mem.DS, rec                                     # 64D8
    r = yield from guest(mem, r, "7CC5", sign, r.ax, mem.DS, rec, ret="64E1")
    r.al = ss8(mem, r, r.bp + 8)                                 # 64E1
    r.local8(-1, r.al)                                           # 64E4
    if mem.ds8(0x7C39):                                          # 64E7
        flip(r, ss8(mem, r, r.bp + 8))                           # 64EE-64F8
        r.local8(8, r.al)                                        # 64FA: the side argument reversed
    side = ss8(mem, r, r.bp + 8)                                 # 64FD
    r.al = side
    cbw(r)
    r.di = r.ax
    if mem.ds8((r.di + 0x80F0) & M16) < 0xB:                     # 6503 cmp [di - 0x7f10], 0xb; jae
        r.al = side                                              # 650A
        cbw(r)
        r.di = r.ax
        mem.wds8(r.di + 0x80F0, mem.ds8((r.di + 0x80F0) & M16) + 1, "0791:6510")
    r.al = side                                                  # 6514
    cbw(r)
    r.di = r.ax
    r.al = mem.ds8((r.di + 0x80F0) & M16)                        # 651A
    r.ah = 0
    r.dx = 3
    mul(r, r.dx)
    r.cx = r.ax                                                  # 6525
    r.al = side
    cbw(r)
    r.dx = 0x21
    mul(r, r.dx)
    r.di = r.ax + r.cx + 0x7BD1                                  # 6530-6534
    row = r.di
    r.local16(-9, row)                                           # 6538
    r.local16(-7, mem.DS)                                        # 653B
    r.es, r.di = mem.DS, rec                                     # 653E
    r = yield from guest(mem, r, "2BB1", mem.DS, rec, ret="6547")
    r.ah = 0                                                     # 6547
    r.ax = r.ax << 1
    r.cx = r.ax
    r.al = ss8(mem, r, r.bp - 1)                                 # 654D
    cbw(r)
    r.di = (r.ax << 1) & M16
    r.ax = mem.ds16((r.di + 0x9B34) & M16)                       # 6555
    r.dx = 0xBF
    mul(r, r.dx)
    r.di, r.es = mem.ds16(0xA917), mem.ds16(0xA919)              # 655E
    r.di = r.di + r.ax + r.cx
    r.ax = mem.u16(mem.addr(r.es, r.di - 2))                     # 6566
    r.es, r.di = mem.DS, row                                     # 656A
    mem.w16(mem.addr(r.es, r.di), r.ax, "0791:656D")
    r.al = ss8(mem, r, r.bp + 4)                                 # 6570 the minute
    mem.w8(mem.addr(r.es, r.di + 2), r.al, "0791:6576")
    if mem.ds8(0x8324) or mem.ds8(0x7C39):                       # 657A-6586
        lin = mem.addr(r.es, r.di + 2)
        mem.w8(lin, mem.u8(lin) + 0x80, "0791:6588")
    if mem.ds8(0x7C39) == 0:                                     # 6590
        r.al = ss8(mem, r, r.bp + 8)                             # 6597
        r = yield from guest(mem, r, "3C20", r.ax, ret="659E", far=False)
    r.leave()                                                    # 659E
    r.store()
    return None


# -- 65A4 ----------------------------------------------------------------------------------------------------------
@PORTS.port("0791:65A4", ret="ret")
def reset_pitch_states(mem, variant):
    """65A4-65FD: per pitch slot 1..22, +0x12 := 6 on DS:830B's side (2B51) unless a keeper (045D), else 0; then
    6337."""
    r = Regs(mem)
    r.enter(6)                                                   # 65A4-65A7
    slot = 1
    r.local16(-2, slot)                                          # 65AA
    while True:
        slot_record(r, slot)                                     # 65B4-65BE
        rec = r.di
        r.local16(-6, rec)                                       # 65C2
        r.local16(-4, mem.DS)                                    # 65C5
        r.es = mem.DS                                            # 65C8
        r = yield from guest(mem, r, "2B51", mem.DS, rec, ret="65D1")
        state = 0
        if r.al:
            r = yield from guest(mem, r, "045D", slot, ret="65DB", far=False)    # 65D5
            if r.al == 0:
                state = 6
        r.es, r.di = mem.DS, rec                                 # 65DF / 65E9
        mem.w8(mem.addr(r.es, r.di + 0x12), state, "0791:65E2" if state else "0791:65EC")
        if slot == 0x16:                                         # 65F1
            break
        slot += 1
        r.local16(-2, slot)                                      # 65B1
    r = yield from guest(mem, r, "6337", ret="65FA", far=False)
    r.leave()
    r.store()
    return None


# -- 65FE ----------------------------------------------------------------------------------------------------------
@PORTS.port("0791:65FE", ret="ret")
def after_goal(mem, variant):
    """65FE-6754: after a goal: DS:8325 := 1, the whistle 0441(4), every slot's destination := its point; unless
    DS:8326, 65A4, the computer's tactics C173 and the form swing 7CC5(0, +-1 by side and DS:7C39) of every available
    slot (2956); then DS:832A := 50 * (a > b) + 50 * (a >= b) + 50 for the scores a, b of the sides by DS:7C39, and
    DS:9B55 := 1 in a quick match (DS:9A3E)."""
    r = Regs(mem)
    r.enter(8)                                                   # 65FE-6601
    mem.wds8(0x8325, 1, "0791:6604")
    r.ax = 4                                                     # 6609
    r = yield from guest(mem, r, "0441", 4, ret="6610", far=False)
    slot = 1
    r.local16(-2, slot)                                          # 6610
    while True:
        r.ax = slot                                              # 661A
        r.dx = 0x16
        mul(r, r.dx)
        r.di = r.ax
        r.cx = mem.ds16((r.di + 0x80E8) & M16)                   # 6624 [di - 0x7f18]
        r.ax = slot
        r.dx = 0x16
        mul(r, r.dx)
        r.di = r.ax
        mem.wds16(r.di + 0x80EF, r.cx, "0791:6632")              # 6632 [di - 0x7f11]
        if slot == 0x16:                                         # 6636
            break
        slot += 1
        r.local16(-2, slot)                                      # 6617
    own_goal = mem.ds8(0x7C39)                                   # 663C
    r.al = own_goal
    r.local8(-3, own_goal)                                       # 663F
    if mem.ds8(0x8326) == 0:                                     # 6642
        r = yield from guest(mem, r, "65A4", ret="664F", far=False)
        flip(r, own_goal)                                        # 664F-6659
        r = yield from guest(mem, r, "C173", r.ax, ret="665F", far=False)
        slot = 1
        r.local16(-2, slot)                                      # 665F
        while True:
            slot_record(r, slot)                                 # 6669-6673
            rec = r.di
            r.local16(-7, rec)                                   # 6677
            r.local16(-5, mem.DS)                                # 667A
            r.es = mem.DS                                        # 667D
            r = yield from guest(mem, r, "2956", mem.DS, rec, ret="6686")
            if r.al == 0:                                        # 6688
                r.es, r.di = mem.DS, rec
                if mem.ds8(0x7C39) == 0:                         # 668A
                    r = yield from guest(mem, r, "2B51", mem.DS, rec, ret="669A")
                    if variant == "swing-reversed":
                        flip(r, r.al)
                    ret = "66AF"
                else:
                    r = yield from guest(mem, r, "2B51", mem.DS, rec, ret="66BA")
                    flip(r, r.al)                                # 66BA-66C2
                    ret = "66D9"
                table_by_al(r, mem, 0x7920)                      # 669A-669D / 66C4-66C7
                cbw(r)
                sign = r.ax
                r.al = 0                                         # 66A3 / 66CD
                r.es, r.di = mem.DS, rec
                r = yield from guest(mem, r, "7CC5", sign, r.ax, mem.DS, rec, ret=ret)
            if slot == 0x16:                                     # 66D9
                break
            slot += 1
            r.local16(-2, slot)                                  # 6666
    score = lambda side: mem.ds8((side + 0x9B3C) & M16)          # noqa: E731
    flip(r, ss8(mem, r, r.bp - 3))                               # 66DF-66E9
    cbw(r)
    r.di = r.ax
    other = score(r.di)                                          # 66EE
    r.dx = (r.dx & 0xFF00) | other
    r.al = ss8(mem, r, r.bp - 3)                                 # 66F2
    cbw(r)
    r.di = r.ax
    mine = score(r.di)                                           # 66F8
    r.al = 1 if mine > other else 0                              # 66FC ja
    r.ah = 0
    r.cx = 0x32
    imul(r, r.cx)                                                # 670B
    r.bx = r.ax
    flip(r, ss8(mem, r, r.bp - 3))                               # 670F-6719
    cbw(r)
    r.di = r.ax
    other = score(r.di)                                          # 671E
    r.dx = (r.dx & 0xFF00) | other
    r.al = ss8(mem, r, r.bp - 3)                                 # 6722
    cbw(r)
    r.di = r.ax
    mine = score(r.di)                                           # 6728
    r.al = 1 if mine >= other else 0                             # 672C jae
    r.ah = 0
    r.cx = 0x32
    imul(r, r.cx)                                                # 673B
    r.ax = r.ax + 0x32 + r.bx                                    # 673D-6740
    mem.wds16(0x832A, r.ax, "0791:6742")
    if mem.ds8(0x9A3E):                                          # 6745
        mem.wds8(0x9B55, 1, "0791:674C")
    r.leave()                                                    # 6751
    r.store()
    return None


# -- 6755 ----------------------------------------------------------------------------------------------------------
@PORTS.port("0791:6755", ret="ret 2")
def ball_over_goal_line(mem, variant):
    """6755-67B3 (nested in 690C): the ball out over a goal line: y := 0x27 * DS:7920[y > 0], line 0x28 (x = 0) or
    0x29, DS:832A := 0x14, then the goal kick or free kick 6F01(the other side, 0), or offside 82EB with DS:830E."""
    r = Regs(mem)
    r.enter(0)
    r.al = 1 if s8(mem.ds8(0x82F7)) > 0 else 0                   # 6758-6763 jg
    table_by_al(r, mem, 0x7920)                                  # 6765-6768
    cbw(r)
    r.cx = 0x27
    imul(r, r.cx)                                                # 6770
    mem.wds8(0x82F7, r.al, "0791:6772")
    if mem.ds8(0x82F6) == 0:                                     # 6775
        r.al = 0x28                                              # 677C
        r = yield from guest(mem, r, "2AA3", r.ax, ret="6782", far=False)
    else:
        r.al = 0x29                                              # 6784
        r = yield from guest(mem, r, "2AA3", r.ax, ret="678A", far=False)
    mem.wds16(0x832A, 0x14, "0791:678A")
    if mem.ds8(0x830E) == 0:                                     # 6790
        r = yield from guest(mem, r, "2996", ret="679A", far=False)
        flip(r, r.al)                                            # 679A-67A2
        side = r.ax
        r.al = 0                                                 # 67A5
        r = yield from guest(mem, r, "6F01", side, r.ax, ret="67AB", far=False)
    else:
        r = yield from guest(mem, r, "82EB", ret="67B0", far=False)     # 67AD
    r.leave()                                                    # 67B0
    r.store()
    return None


# -- 67B6 ----------------------------------------------------------------------------------------------------------
@PORTS.port("0791:67B6", ret="ret 2")
def goal_scored(mem, variant):
    """67B6-68E9 (nested in 690C): the ball's point clamped into the goal (2031), the side credited (2996, reversed
    for an own goal DS:7C39), the line 0x24 or 0x25 on the other side's first slot, the score DS:9B3C + side + 1 (685C)
    and the board 0712; unless DS:8326, with DS:830E set (an attacker offside) the line and the goal taken back (68B3),
    82EB and the board again, else record_goal 6443; then after_goal 65FE and the replay flag DS:7C37 (or, with
    DS:0C20 set, DS:0C20 cleared and DS:7C3C kept in the fixture at DS:A923 + 0x3F)."""
    r = Regs(mem)
    r.enter(8)                                                   # 67B6-67B9
    r.di = 0x82F7                                                # 67BC
    r.al = 0xDA
    low = r.ax
    r.al = 0x26
    r = yield from guest(mem, r, "214B:2031", mem.DS, 0x82F7, low, r.ax, ret="67CC")
    r.di = 0x82F6                                                # 67CC
    r.al = 0xFF
    low = r.ax
    r.al = 1
    r = yield from guest(mem, r, "214B:2031", mem.DS, 0x82F6, low, r.ax, ret="67DC")
    if mem.ds8(0x7C39):                                          # 67DC
        r = yield from guest(mem, r, "2996", ret="67E6", far=False)
        flip(r, r.al)                                            # 67E6-67EE
    else:
        r = yield from guest(mem, r, "2996", ret="67F8", far=False)
    side = r.al
    r.local8(-3, side)                                           # 67F0 / 67F8
    template = 0x27 if mem.ds8(0x7C39) else 0x26                # 67FB-6808
    r.local8(-4, template)
    flip(r, side)                                                # 680C-6816
    table_by_al(r, mem, 0x668)                                   # 6818-681B
    r.ah = 0
    r.ax = r.ax + 1                                              # 6821
    r.dx = 0x16
    mul(r, r.dx)
    r.di = r.ax + 0x80E8                                         # 6827-6829
    rec = r.di
    r.local16(-8, rec)                                           # 682D
    r.local16(-6, mem.DS)                                        # 6830
    r = yield from guest(mem, r, "214B:06FA", ret="6838")       # 6833
    r.al = 0x24 if r.al else 0x25                                # 683C / 684A
    r.es, r.di = mem.DS, rec
    r = yield from guest(mem, r, "2B28", r.ax, mem.DS, rec, ret="6848" if r.al == 0x24 else "6856")
    r.al = side                                                  # 6856
    cbw(r)
    r.di = r.ax
    mem.wds8(r.di + 0x9B3C, mem.ds8((r.di + 0x9B3C) & M16) + 1, "0791:685C")   # the goal
    r.di = 0xA96A                                                # 6860
    r = yield from guest(mem, r, "0712", mem.DS, 0xA96A, ret="6869")
    if mem.ds8(0x8326):                                          # 6869
        r.al = template                                          # 6870
        r = yield from guest(mem, r, "2AA3", r.ax, ret="6877", far=False)
    elif mem.ds8(0x830E) == 0:                                   # 6879
        holder_record(r, mem)                                    # 6880-688C
        r = yield from guest(mem, r, "2974", mem.DS, r.di, ret="6896")
        scoring_side = r.ax                                      # 6896 push ax
        r.al = mem.ds8(0x830B)                                   # 6897
        r.ah = 0
        slot = r.ax
        r = yield from guest(mem, r, "6443", scoring_side, slot, mem.ds16(0x831F), ret="68A4", far=False)
    else:
        r.al = template                                          # 68A6
        r = yield from guest(mem, r, "2AA3", r.ax, ret="68AD", far=False)
        r.al = side                                              # 68AD
        cbw(r)
        r.di = r.ax
        mem.wds8(r.di + 0x9B3C, mem.ds8((r.di + 0x9B3C) & M16) - 1, "0791:68B3")   # the goal taken back
        r = yield from guest(mem, r, "82EB", ret="68BA", far=False)
        r.di = 0xA96A                                            # 68BA
        r = yield from guest(mem, r, "0712", mem.DS, 0xA96A, ret="68C3")
        r.leave()
        r.store()
        return None
    r = yield from guest(mem, r, "65FE", ret="68C8", far=False)  # 68C5
    if mem.ds8(0x0C20) == 0:                                     # 68C8
        mem.wds8(0x7C37, 1, "0791:68CF")
    else:
        mem.wds8(0x0C20, 0, "0791:68D6")
        r.al = mem.ds8(0x7C3C)                                   # 68DB
        r.di, r.es = mem.ds16(0xA923), mem.ds16(0xA925)          # 68DE
        mem.w8(mem.addr(r.es, r.di + 0x3F), r.al, "0791:68E2")
    r.leave()                                                    # 68E6
    r.store()
    return None
