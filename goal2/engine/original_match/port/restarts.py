"""The dead-ball restarts (T59 ports the throw-in; T67 adds the others): routines that stop play and call the
original's code around them (the substitution check, the commentary, the restart's set-up), the first ports with
guest calls (port/guest.py).

From the listing static/goal-exe/code/seg_0791_12.asm 6E11-6E6D (dead_ball_throw_in, routines.tsv row 0791:6E11; 93
bytes, 43 instructions); the line comments are its offsets. Its callees stay the original's and are called as the
listing calls them, each with its return address: 8062 (ret, seg_0791_13.asm 8205), 2996 (ret, seg_0791_04.asm 29B2),
6BF1 (ret 4, seg_0791_11.asm 6D4B), 2AA3 (ret 2, seg_0791_05.asm 2AD1), 2BE5 (retf 4, seg_0791_05.asm 2C26, called
by `push cs; call near`), 26A0 (ret 2, seg_0791_04.asm 26BF)."""
from .guest import call
from .mem import s8
from . import Registry

PORTS = Registry("restarts", "the dead-ball restarts: the throw-in 0791:6E11 (T59)")
PORTS.variant("side-swapped", "6E26-6E2E's test inverted: the other side's byte of DS:8311 is passed to 6BF1")


@PORTS.port("0791:6E11", ret="ret")                       # 6E6D ret
def dead_ball_throw_in(mem, variant):
    mem.enter(0, "0791:6E11")                             # 6E11-6E12 push bp; mov bp, sp
    if mem.ds8(0x8326) != 0:                              # 6E14 cmp byte ptr [0x8326], 0; jne 6E6A
        return None                                       # AX, DX as they came
    mem.wds8(0x830E, 0, "0791:6E1B")                      # 6E1B mov byte ptr [0x830e], 0
    yield call("0791:8062", ret_to="0791:6E23", far=False)            # 6E20 the substitution check
    ax = yield call("0791:2996", ret_to="0791:6E26", far=False)       # 6E23
    side = 0 if ax & 0xFF else 1                          # 6E26-6E2E: al != 0 -> 0, else 1
    if variant == "side-swapped":
        side ^= 1
    # The registers each callee is entered with are the original's too (AX, DX, DI as the listing leaves them).
    value = mem.ds8(0x8311 + side)                        # 6E30-6E37 cbw; mov di, ax; mov al, [di + 0x8311]; xor ah, ah
    mem.set_reg("di", side)
    mem.set_reg("ax", 7)                                  # 6E3A mov al, 7 (AH 0 since 6E37)
    ax = yield call("0791:6BF1", value, 7, ret_to="0791:6E40", far=False)     # 6E39-6E3D push ax; mov al, 7; push ax
    ax = (ax & 0xFF00) | 0x2B                             # 6E40 mov al, 0x2b: AH is 6BF1's
    mem.set_reg("ax", ax)
    yield call("0791:2AA3", ax, ret_to="0791:6E46", far=False)            # 6E42-6E43
    product = mem.ds8(0x830B) * 0x16                      # 6E46-6E4E mov al, [0x830b]; xor ah, ah; mov dx, 0x16; mul dx
    record = (product + 0x80E8) & 0xFFFF                  # 6E50-6E52: the pitch record of slot [0x830b]
    mem.set_reg("ax", product & 0xFFFF)
    mem.set_reg("dx", product >> 16)
    mem.set_reg("di", record)
    ax = yield call("0791:2BE5", mem.reg("ds"), record, ret_to="0791:6E5C", far=True)   # 6E56-6E59 push ds; push di; push cs
    ax = (ax & 0xFF00) | (1 if s8(ax & 0xFF) > 0 else 0)  # 6E5C-6E64 or al, al; jg; mov al, 0 or 1: AH is 2BE5's
    mem.set_reg("ax", ax)
    yield call("0791:26A0", ax, ret_to="0791:6E6A", far=False)            # 6E66-6E67
    return None                                           # 6E6A-6E6D: AX, DX as 26A0 left them


# ======================================================================================================================
# T67 (route C, P4b): kick-offs, restarts and set pieces, the walk-off and the booking: the 25 routines of row T67,
# translated from static/goal-exe/code/seg_0791_11.asm (690C-6D4B), seg_0791_12.asm (6D4E-787E) and seg_0791_13.asm
# (7881-7B21), after the named view (named/seg_0791_05.c). As T65's contests.py and T66's duels.py, these are written in
# the registers the listing uses (runtime.Regs), so the words pushed for a callee (`mov al, n; push ax` keeps the AH of
# the instruction before), the words held on the guest stack across a call and the locals of the frames are the
# original's (notes.md rule 2a).
#
# Every call of the listing stays a guest call with its target, arguments, return address and near/far form, between
# these routines too and to the callees of other rows (T66's 6755 and 67B6; T68's 8062 and 8AE9's handlers; T73's
# 0425, 0441, 94E8, 214B:1E09; T76's taker prompt CC7B), so a decision under 8062 or at the prompt stops the match as
# anywhere else (T59). The walk-off's key poll (7881: 214B:0723 returning to 78F9, then 214B:08DD to 7902) is answered by
# the kit's logic for that site (mem.keypressed, mem.read_key; match.py `_key_waiting`: a walk-off has no key), with the
# far call's return address written below SP as the call leaves it. The booking's statistics write (7A01 `inc byte ptr
# [di + 0x7b85]`) is made as that instruction, the kit's booking event (match.py WRITERS["booking"]).
#
# The nested routines (`push bp; call`, `ret 2`) read their parent's far pointer through its BP, as the listing does:
# 6FEE in 7069, 70F6 in 715A, 71E8 in 7287, 74C2 in 7621; 717F gets 7287's BP from 71E8 and reads nothing of it.
# ======================================================================================================================
from .contests import guest, ss16, ss8, pop, nested, own, rb, rw, player_record, byte_abs
from .duels import zero_flag, holder_record, flip, table_by_al
from .geometry import cbw, cwd, mul, imul
from .runtime import Regs
from .mem import s16

PORTS.doc = ("the dead-ball restarts: the throw-in 0791:6E11 (T59); kick-offs, restarts and set pieces, the walk-off and "
             "the booking: 690C-7B21, row T67's 25 routines (T67)")
PORTS.variant("kickoff-depth-dropped", "69BD at 69FD: the kick-off depth DS:0812[position] is not added to y (+8)")
PORTS.variant("restart-count-shifted", "6DEA at 6E07: the restart's statistics byte is DS:7B7F + 10 side + n, not DS:7B7E")
PORTS.variant("throw-step-3", "7069 at 70AE: the throw-in's x offset is DS:82F6 / 3, not / 2")
M16 = 0xFFFF


def wb(mem, r, k, value, at):
    """`mov byte ptr es:[di + k], value` (or an add, dec), as the listing's instruction `at`."""
    mem.w8(mem.addr(r.es, r.di + k), value, f"0791:{at}")


def ww(mem, r, k, value, at):
    mem.w16(mem.addr(r.es, r.di + k), value, f"0791:{at}")


def idiv_by(r, divisor):
    """`cdq` (cwd); `mov cx, divisor`; `idiv cx`: AX the quotient toward zero, DX the remainder (the dividend's sign)."""
    cwd(r)
    r.cx = divisor
    a = s16(r.ax)
    q = abs(a) // divisor
    q = -q if a < 0 else q
    r.ax, r.dx = q, a - q * divisor


def arg8(mem, r, k):
    """byte ptr [bp + k]: an argument of the routine running."""
    return ss8(mem, r, r.bp + k)


def arg16(mem, r, k):
    return ss16(mem, r, r.bp + k)


def _end(r, value=False):
    r.leave()
    r.store()
    return r.ax if value else None


def far_return_words(mem, r, ret_ip):
    """The words a `call far 214B:xxxx` leaves below SP (its return CS:IP) when the kit answers the call at its entry."""
    sp = r.sp
    r.push(mem.seg(0x0791))
    r.push(ret_ip)
    r.sp = sp


# -- 690C ----------------------------------------------------------------------------------------------------------
@PORTS.port("0791:690C", ret="ret")
def penalty_contest(mem, variant):
    """690C-698D: DS:8327 above 4: the ball over the goal line (6755); else unless DS:7C39 or DS:80FB, with DS:8327 in
    the set at 0791:68EC the keeper's roll 06B1(278A(holder, DS:080C[8327])) against 06B1(0x20): above it the goal
    67B6, else 6755; DS:7C39 or DS:80FB set: the goal 67B6. Then DS:8324 and DS:80FB cleared."""
    r = Regs(mem)
    r.enter(4)                                                   # 690C-690F
    if mem.ds8(0x8327) > 4:                                      # 6912 cmp; jbe 691F
        r = yield from guest(mem, r, "6755", r.bp, ret="691D", far=False)     # 6919-691A
    else:
        goal = True
        if mem.ds8(0x7C39) == 0 and mem.ds8(0x80FB) == 0:        # 691F, 6926
            r.al = mem.ds8(0x8327)                               # 692D
            r.di = 0x68EC
            r = yield from guest(mem, r, "23E4:08DF", r.ax, mem.seg(0x0791), 0x68EC, ret="693B")
            if zero_flag(mem):                                   # 693B je 697C
                goal = False
            else:
                r.ax = 0x20                                      # 693D
                r = yield from guest(mem, r, "214B:06B1", 0x20, ret="6946")
                r.push(r.ax)                                     # 6946: the roll, live across two calls
                r.al = mem.ds8(0x8327)                           # 6947-6952
                r.ah = 0
                r.di = r.ax
                r.al = mem.ds8((r.di + 0x80C) & M16)
                r.ah = 0
                element = r.ax                                   # 6954 push ax
                holder_record(r, mem)                            # 6955-6961
                r = yield from guest(mem, r, "278A", element, mem.DS, r.di, ret="696B")
                r = yield from guest(mem, r, "214B:06B1", r.ax, ret="6971")
                r.dx = pop(mem, r)                               # 6971
                goal = s16(r.ax) > s16(r.dx)                     # 6972-6974 cmp ax, dx; jle 697C
        if goal:
            r = yield from guest(mem, r, "67B6", r.bp, ret="697A", far=False)     # 6976-6977
        else:
            r = yield from guest(mem, r, "6755", r.bp, ret="6980", far=False)     # 697C-697D
    mem.wds8(0x8324, 0, "0791:6980")
    mem.wds8(0x80FB, 0, "0791:6985")
    return _end(r)                                               # 698A-698D


# -- 698E ----------------------------------------------------------------------------------------------------------
@PORTS.port("0791:698E", ret="ret")
def ball_out_at_goal_line(mem, variant):
    """698E-69BC: with DS:830B's slot a goalkeeper's (045D: 1 or 12) or a coin (06FA) the corner 6E6E; else DS:8327 := 0,
    DS:7C39 := 1 and 690C (the own goal's path)."""
    r = Regs(mem)
    r.enter(0)
    r.al = mem.ds8(0x830B)                                       # 6991-6996
    r.ah = 0
    r = yield from guest(mem, r, "045D", r.ax, ret="699A", far=False)
    corner = r.al != 0                                           # 699A jne 69A7
    if not corner:
        r = yield from guest(mem, r, "214B:06FA", ret="69A3")
        corner = r.al != 0                                       # 69A3 je 69AC
    if corner:
        r = yield from guest(mem, r, "6E6E", ret="69AA", far=False)
    else:
        mem.wds8(0x8327, 0, "0791:69AC")
        mem.wds8(0x7C39, 1, "0791:69B1")
        r = yield from guest(mem, r, "690C", ret="69B9", far=False)
    return _end(r)


# -- 69BD ----------------------------------------------------------------------------------------------------------
@PORTS.port("0791:69BD", ret="retf 4")
def kickoff_placement(mem, variant):
    """69BD-6AAC (state 1 of 8AE9): destination +7 := post +9, depth +0xC := DS:0812[player position], y +8 += depth,
    mirrored (2C86); the side's last slot (DS:0668[2996] + 0xB) to DS:0822, the holder DS:830B to DS:0820; at the
    destination (2CC5) with DS:8326 clear the holder goes to state 2 (DS:8302 := 0, line 0x31), the others to 0."""
    r = Regs(mem)
    r.enter(0)
    seg, off = own(mem, r)                                       # 69C0
    r.ax = rw(mem, r, 9)
    ww(mem, r, 7, r.ax, "69CA")
    r.ax = rw(mem, r, 0xD)                                       # 69CE-69D8
    r.dx = 0x14
    mul(r, r.dx)
    r.di, r.es = mem.ds16(0xA91B), mem.ds16(0xA91D)              # 69DA
    r.di = r.di + r.ax
    r.al = rb(mem, r, 6)                                         # 69E0
    r.ah = 0
    r.di = r.ax
    r.al = mem.ds8((r.di + 0x812) & M16)                         # 69E8
    depth = r.al
    r.es, r.di = seg, off
    wb(mem, r, 0xC, depth, "69EF")
    r.al = rb(mem, r, 0xC)                                       # 69F6
    if variant != "kickoff-depth-dropped":
        wb(mem, r, 8, rb(mem, r, 8) + r.al, "69FD")              # 69FD add byte ptr es:[di + 8], al
    word = rw(mem, r, 7)                                         # 6A04
    r = yield from guest(mem, r, "2C86", word, seg, off, ret="6A11")
    r.es, r.di = seg, off
    ww(mem, r, 7, r.ax, "6A14")
    r = yield from guest(mem, r, "2996", ret="6A1B", far=False)
    cbw(r)                                                       # 6A1B
    r.di = r.ax
    r.al = mem.ds8((r.di + 0x668) & M16)
    r.ah = 0
    r.ax = r.ax + 0xB                                            # 6A24
    r.dx = r.ax
    r.es, r.di = seg, off
    r.al = rb(mem, r, 6)                                         # 6A2C
    r.ah = 0
    if r.ax == r.dx:                                             # 6A32 jne 6A4A
        word = mem.ds16(0x822)                                   # 6A36
        r = yield from guest(mem, r, "2C86", word, seg, off, ret="6A43")
        r.es, r.di = seg, off
        ww(mem, r, 7, r.ax, "6A46")
    r.al = mem.ds8(0x830B)                                       # 6A4A
    r.es, r.di = seg, off
    if r.al == rb(mem, r, 6):                                    # 6A50 jne 6A6A
        word = mem.ds16(0x820)                                   # 6A56
        r = yield from guest(mem, r, "2C86", word, seg, off, ret="6A63")
        r.es, r.di = seg, off
        ww(mem, r, 7, r.ax, "6A66")
    if mem.ds8(0x8326) == 0:                                     # 6A6A
        r.es, r.di = seg, off
        r = yield from guest(mem, r, "2CC5", seg, off, ret="6A7A")
        if r.al:                                                 # 6A7A je 6AA7
            r.al = mem.ds8(0x830B)                               # 6A7E
            r.es, r.di = seg, off
            if r.al == rb(mem, r, 6):                            # 6A84 jne 6A9F
                wb(mem, r, 0x12, 2, "6A8D")
                mem.wds8(0x8302, 0, "0791:6A92")
                r.al = 0x31                                      # 6A97
                r = yield from guest(mem, r, "2AA3", r.ax, ret="6A9D", far=False)
            else:
                wb(mem, r, 0x12, 0, "6AA2")
    return _end(r)


# -- 6AAD ----------------------------------------------------------------------------------------------------------
@PORTS.port("0791:6AAD", ret="retf 4")
def kickoff_taken(mem, variant):
    """6AAD-6AF4 (state 2 of 8AE9, the kick-off's taker): when every slot is in state 0 (28B2(0)) DS:9B55 := 1,
    DS:830C and DS:8323 cleared, the ball launched (34C1) to DS:0824 mirrored with speed 6, every slot to state 5 (2929)
    and the whistle 0441(2)."""
    r = Regs(mem)
    r.enter(0)
    r.al = 0                                                     # 6AB0
    r = yield from guest(mem, r, "28B2", r.ax, ret="6AB6", far=False)
    if r.al:                                                     # 6AB6 je 6AF1
        mem.wds8(0x9B55, 1, "0791:6ABA")
        mem.wds8(0x830C, 0, "0791:6ABF")
        mem.wds8(0x8323, 0, "0791:6AC4")
        word = mem.ds16(0x824)                                   # 6AC9
        seg, off = own(mem, r)
        r = yield from guest(mem, r, "2C86", word, seg, off, ret="6AD6")
        target = r.ax                                            # 6AD6 push ax
        r.ax = 6
        seg, off = own(mem, r)
        r = yield from guest(mem, r, "34C1", target, 6, seg, off, ret="6AE4")
        r.al = 5                                                 # 6AE4
        r = yield from guest(mem, r, "2929", r.ax, ret="6AEA", far=False)
        r.ax = 2                                                 # 6AEA
        r = yield from guest(mem, r, "0441", 2, ret="6AF1", far=False)
    return _end(r)


# -- 6AF7 ----------------------------------------------------------------------------------------------------------
@PORTS.port("0791:6AF7", ret="retf 4")
def walk_off_state(mem, variant):
    """6AF7-6B62 (state 3 of 8AE9): destination +7 := DS:0642 unless the point +0 is DS:0644 or DS:0640 (then the
    point itself); at the destination (2CC5) state 4, the point and destination := DS:0644 and the picture moved (8537)."""
    r = Regs(mem)
    r.enter(0)
    seg, off = own(mem, r)                                       # 6AFA
    r.ax = rw(mem, r, 0)
    at_point = r.ax == mem.ds16(0x644)                           # 6B00 je 6B1E
    if not at_point:
        r.ax = rw(mem, r, 0)                                     # 6B06
        at_point = r.ax == mem.ds16(0x640)                       # 6B0C je 6B1E
    if at_point:
        r.ax = rw(mem, r, 0)                                     # 6B1E
        ww(mem, r, 7, r.ax, "6B27")
    else:
        r.ax = mem.ds16(0x642)                                   # 6B12
        ww(mem, r, 7, r.ax, "6B18")
    r = yield from guest(mem, r, "2CC5", seg, off, ret="6B34")
    if r.al:                                                     # 6B34 je 6B5F
        r.es, r.di = seg, off
        wb(mem, r, 0x12, 4, "6B3B")
        r.ax = mem.ds16(0x644)                                   # 6B40
        ww(mem, r, 0, r.ax, "6B46")
        r.ax = rw(mem, r, 0)                                     # 6B49
        ww(mem, r, 7, r.ax, "6B52")
        r = yield from guest(mem, r, "8537", seg, off, ret="6B5F")
    return _end(r)


# -- 6B65 ----------------------------------------------------------------------------------------------------------
@PORTS.port("0791:6B65", ret="ret 4")
def taker_squad_index(mem, variant):
    """6B65-6BCE (side [bp+6], role [bp+4]): the first k in 1..11 whose squad word (DS:A917 + 0xBF * DS:9B34[side],
    word k - 1) is the pick DS:9976 + 10 side + 2 role; 0xC when none is."""
    r = Regs(mem)
    r.enter(8)                                                   # 6B65-6B68
    side, role = arg8(mem, r, 6), arg16(mem, r, 4)
    r.al = side                                                  # 6B6B-6B71
    cbw(r)
    r.di = r.ax
    r.di = r.di << 1
    r.ax = mem.ds16((r.di + 0x9B34) & M16)                       # 6B73 [di - 0x64cc]
    r.dx = 0xBF
    mul(r, r.dx)
    r.di, r.es = mem.ds16(0xA917), mem.ds16(0xA919)              # 6B7C
    r.di = r.di + r.ax
    squad_seg, squad_off = r.es, r.di
    r.local16(-8, squad_off)                                     # 6B82
    r.local16(-6, squad_seg)                                     # 6B85
    k = 1
    r.local16(-4, k)                                             # 6B88
    while k < 0xC:                                               # 6B8D cmp; jae 6BC2
        r.ax = role << 1                                         # 6B93-6B98
        r.cx = r.ax
        r.al = side                                              # 6B9A-6BA5
        cbw(r)
        r.dx = 0xA
        mul(r, r.dx)
        r.di = r.ax + r.cx
        r.dx = mem.ds16((r.di + 0x9976) & M16)                   # 6BA7 [di - 0x668a]
        r.ax = k << 1                                            # 6BAB-6BB3
        r.es, r.di = squad_seg, squad_off
        r.di = r.di + r.ax
        r.ax = mem.u16(mem.addr(r.es, r.di - 2))                 # 6BB5
        if r.ax == r.dx:                                         # 6BB9 je 6BC2
            break
        k += 1
        r.local16(-4, k)                                         # 6BBD
    r.ax = k                                                     # 6BC2-6BC8
    r.local16(-2, k)
    return _end(r, value=True)


# -- 6BF1 ----------------------------------------------------------------------------------------------------------
@PORTS.port("0791:6BF1", ret="ret 4")
def restart_setup(mem, variant):
    """6BF1-6D4B (slot [bp+6], kind [bp+4]): the slot takes the ball (DS:830B, 2A15), DS:830C, 830D cleared, DS:8302
    := 1, DS:8300 := 0, every slot to state kind (2929), DS:9B55 := 1 for a kind in the set at 0791:6BD1; the ball's
    point DS:8315 by kind: 0xA the penalty spot (0, 0x1C * 2BE5), 9 a corner (+-8, +-0x24), 0xB where it is, 8 a goal
    kick (+-2, -0x21 * 2BE5), 7 a throw-in (+-8, its y), else the record's point; the record's destination and the ball
    := that point; the taker's countdown +0x10 := 10 * 2F28 + 261A + 10."""
    r = Regs(mem)
    r.enter(4)                                                   # 6BF1-6BF4
    r.al = arg8(mem, r, 6)                                       # 6BF7
    mem.wds8(0x830B, r.al, "0791:6BFA")
    r = yield from guest(mem, r, "2A15", ret="6C00", far=False)
    mem.wds8(0x830C, 0, "0791:6C00")
    mem.wds8(0x830D, 0, "0791:6C05")
    mem.wds8(0x8302, 1, "0791:6C0A")
    r.ax = 0                                                     # 6C0F
    mem.wds16(0x8300, 0, "0791:6C11")
    kind = arg8(mem, r, 4)
    r.al = kind                                                  # 6C14
    r = yield from guest(mem, r, "2929", r.ax, ret="6C1B", far=False)
    r.al = kind                                                  # 6C1B
    r.di = 0x6BD1
    r = yield from guest(mem, r, "23E4:08DF", r.ax, mem.seg(0x0791), 0x6BD1, ret="6C29")
    if not zero_flag(mem):                                       # 6C29 je 6C30
        mem.wds8(0x9B55, 1, "0791:6C2B")
    rec = holder_record(r, mem)                                  # 6C30-6C3C
    r.local16(-4, rec)                                           # 6C40
    r.local16(-2, mem.DS)                                        # 6C43
    r.al = kind                                                  # 6C46

    def sign_of(byte):
        """`cmp byte ptr [b], 0; jg; mov al, 0 / 1; cbw; mov di, ax; mov al, [di + 0x7920]; cbw`."""
        r.al = 1 if s8(mem.ds8(byte)) > 0 else 0
        table_by_al(r, mem, 0x7920)
        cbw(r)

    if kind == 0xA:                                              # 6C49 cmp al, 0xa
        mem.wds8(0x8315, 0, "0791:6C4D")
        r.es, r.di = mem.DS, rec                                 # 6C52
        r = yield from guest(mem, r, "2BE5", mem.DS, rec, ret="6C5B")
        cbw(r)
        r.cx = 0x1C
        imul(r, r.cx)                                            # 6C5F
        mem.wds8(0x8316, r.al, "0791:6C61")
    elif kind == 9:                                              # 6C67
        sign_of(0x82F6)                                          # 6C6B-6C7F
        r.cx = 3
        r.ax = r.ax << 3                                         # 6C83 shl ax, cl
        mem.wds8(0x8315, r.al, "0791:6C85")
        sign_of(0x82F7)                                          # 6C88-6C9C
        r.cx = 0x24
        imul(r, r.cx)                                            # 6CA0
        mem.wds8(0x8316, r.al, "0791:6CA2")
    elif kind == 0xB:                                            # 6CA7
        r.ax = mem.ds16(0x82F6)                                  # 6CAB
        mem.wds16(0x8315, r.ax, "0791:6CAE")
    elif kind == 8:                                              # 6CB3
        sign_of(0x82F6)                                          # 6CB7-6CCB
        r.ax = r.ax << 1                                         # 6CCC shl ax, 1
        mem.wds8(0x8315, r.al, "0791:6CCE")
        r.es, r.di = mem.DS, rec                                 # 6CD1
        r = yield from guest(mem, r, "2BE5", mem.DS, rec, ret="6CDA")
        cbw(r)
        r.cx = 0xFFDF
        imul(r, r.cx)                                            # 6CDE
        mem.wds8(0x8316, r.al, "0791:6CE0")
    elif kind == 7:                                              # 6CE5
        sign_of(0x82F6)                                          # 6CE9-6CFD
        r.cx = 3
        r.ax = r.ax << 3                                         # 6D01 shl ax, cl
        mem.wds8(0x8315, r.al, "0791:6D03")
        r.al = mem.ds8(0x82F7)                                   # 6D06
        mem.wds8(0x8316, r.al, "0791:6D09")
    else:
        r.es, r.di = mem.DS, rec                                 # 6D0E
        r.ax = rw(mem, r, 0)
        mem.wds16(0x8315, r.ax, "0791:6D14")
    r.ax = mem.ds16(0x8315)                                      # 6D17
    r.es, r.di = mem.DS, rec
    ww(mem, r, 7, r.ax, "6D1D")
    r.ax = mem.ds16(0x8315)                                      # 6D21
    mem.wds16(0x82F6, r.ax, "0791:6D24")
    r.es, r.di = mem.DS, rec                                     # 6D27
    r = yield from guest(mem, r, "2F28", mem.DS, rec, ret="6D30")
    r.ah = 0                                                     # 6D30
    r.cx = 0xA
    imul(r, r.cx)
    r.push(r.ax)                                                 # 6D37: live across 261A
    r = yield from guest(mem, r, "261A", ret="6D3B", far=False)
    r.ax = r.ax + 0xA                                            # 6D3B
    r.dx = pop(mem, r)                                           # 6D3E
    r.ax = r.ax + r.dx
    r.es, r.di = mem.DS, rec                                     # 6D41
    wb(mem, r, 0x10, r.al, "6D44")
    return _end(r)


# -- 6D4E ----------------------------------------------------------------------------------------------------------
@PORTS.port("0791:6D4E", ret="ret 6")
def pick_dead_ball_taker(mem, variant):
    """6D4E-6DE7 (side [bp+8], role [bp+6], kind [bp+4]): a managed side's taker from the prompt CC7B(side, role), kept
    at DS:9976 + 10 side + 2 role; else 1FDD(side, DS:0764[role], role); the slot: the pick's squad index (6B65) + the
    side's first slot DS:0668[side], or with none (0xC) the side's nearest DS:8311[side]; then 6BF1(slot, kind)."""
    r = Regs(mem)
    r.enter(2)                                                   # 6D4E-6D51
    side, role, kind = arg8(mem, r, 8), arg16(mem, r, 6), arg8(mem, r, 4)
    r.al = side                                                  # 6D54-6D5A
    cbw(r)
    r.di = r.ax
    r.di = r.di << 1
    squad = mem.ds16((r.di + 0x9B34) & M16)                      # 6D5C push word ptr [di - 0x64cc]
    r = yield from guest(mem, r, "1771:0B77", squad, ret="6D65")
    if r.al:                                                     # 6D65 je 6D90
        r.al = side                                              # 6D69
        first = r.ax
        r.al = role & 0xFF                                       # 6D6D
        r = yield from guest(mem, r, "CC7B", first, r.ax, ret="6D74", far=False)
        r.bx = r.ax                                              # 6D74
        r.ax = role << 1                                         # 6D76-6D79
        r.cx = r.ax
        r.al = side                                              # 6D7D-6D88
        cbw(r)
        r.dx = 0xA
        mul(r, r.dx)
        r.di = r.ax + r.cx
        mem.wds16(r.di + 0x9976, r.bx, "0791:6D8A")              # [di - 0x668a]
    else:
        r.al = side                                              # 6D90
        first = r.ax
        r.di = role                                              # 6D94
        r.al = mem.ds8((r.di + 0x764) & M16)
        r.ah = 0
        r = yield from guest(mem, r, "1FDD", first, r.ax, role, ret="6DA4", far=False)
    r.al = side                                                  # 6DA4
    r = yield from guest(mem, r, "6B65", r.ax, role, ret="6DAE", far=False)
    pick = r.ax
    r.local16(-2, pick)                                          # 6DAE
    if pick < 0xC:                                               # 6DB1 cmp; jae 6DCB
        r.al = side                                              # 6DB7
        cbw(r)
        r.di = r.ax
        r.al = mem.ds8((r.di + 0x668) & M16)
        r.ah = 0
        r.ax = r.ax + pick                                       # 6DC3
    else:
        r.al = side                                              # 6DCB
        cbw(r)
        r.di = r.ax
        r.al = mem.ds8((r.di + 0x8311) & M16)                    # [di - 0x7cef]
        r.ah = 0
    slot = r.ax
    r.local16(-2, slot)                                          # 6DC6 / 6DD7
    r.al = kind                                                  # 6DDD
    r = yield from guest(mem, r, "6BF1", slot, r.ax, ret="6DE4", far=False)
    return _end(r)


# -- 6DEA ----------------------------------------------------------------------------------------------------------
@PORTS.port("0791:6DEA", ret="ret 4")
def restart_line_and_count(mem, variant):
    """6DEA-6E0E (statistic [bp+6], line [bp+4]): the line (2AA3), then the statistics byte n of the side holding the
    ball (2996) +1: DS:7B7E + 10 side + n (n 0 corners, 1 free kicks, 2 penalties)."""
    r = Regs(mem)
    r.enter(0)
    r.al = arg8(mem, r, 4)                                       # 6DED
    r = yield from guest(mem, r, "2AA3", r.ax, ret="6DF4", far=False)
    r.al = arg8(mem, r, 6)                                       # 6DF4-6DF8
    cbw(r)
    r.push(r.ax)                                                 # 6DF8: the statistic, live across 2996
    r = yield from guest(mem, r, "2996", ret="6DFC", far=False)
    cbw(r)                                                       # 6DFC-6E00
    r.dx = 0xA
    mul(r, r.dx)
    r.di = r.ax
    r.ax = pop(mem, r)                                           # 6E04
    r.di = r.di + r.ax
    table = 0x7B7F if variant == "restart-count-shifted" else 0x7B7E
    mem.wds8(r.di + table, mem.ds8((r.di + table) & M16) + 1, "0791:6E07")
    return _end(r)


# -- 6E6E ----------------------------------------------------------------------------------------------------------
@PORTS.port("0791:6E6E", ret="ret")
def dead_ball_corner(mem, variant):
    """6E6E-6ECE: unless DS:8326, DS:830E := 0, the substitution check 8062, the corner's taker for the side not
    holding the ball (6D4E(side, 2, 9)), DS:830A := DS:830B, line 0x2D and the corners count (6DEA(0x2D, 0)), then 26A0
    with 2BE5 > 0."""
    r = Regs(mem)
    r.enter(0)
    if mem.ds8(0x8326) == 0:                                     # 6E71 jne 6ECB
        mem.wds8(0x830E, 0, "0791:6E78")
        r = yield from guest(mem, r, "8062", ret="6E80", far=False)
        r = yield from guest(mem, r, "2996", ret="6E83", far=False)
        flip(r, r.al)                                            # 6E83-6E8B
        side = r.ax                                              # 6E8D push ax
        r.ax = 2                                                 # 6E8E
        r.al = 9                                                 # 6E92
        r = yield from guest(mem, r, "6D4E", side, 2, r.ax, ret="6E98", far=False)
        r.al = mem.ds8(0x830B)                                   # 6E98
        mem.wds8(0x830A, r.al, "0791:6E9B")
        r.al = 0                                                 # 6E9E
        first = r.ax
        r.al = 0x2D                                              # 6EA1
        r = yield from guest(mem, r, "6DEA", first, r.ax, ret="6EA7", far=False)
        holder_record(r, mem)                                    # 6EA7-6EB3
        r = yield from guest(mem, r, "2BE5", mem.DS, r.di, ret="6EBD")
        r.al = 1 if s8(r.al) > 0 else 0                          # 6EBD-6EC5 or al, al; jg
        r = yield from guest(mem, r, "26A0", r.ax, ret="6ECB", far=False)
    return _end(r)


# -- 6F01 ----------------------------------------------------------------------------------------------------------
@PORTS.port("0791:6F01", ret="ret 4")
def dead_ball_goal_kick_or_free_kick(mem, variant):
    """6F01-6F3B (side [bp+6], free kick [bp+4]): unless DS:8326, DS:830E := 0, 8062, the taker 6D4E(side, 5, 8),
    then a free kick's line 0x3A and count (6DEA(0x3A, 1)) or the goal kick's line 0x38."""
    r = Regs(mem)
    r.enter(0)
    if mem.ds8(0x8326) == 0:                                     # 6F04 jne 6F38
        mem.wds8(0x830E, 0, "0791:6F0B")
        r = yield from guest(mem, r, "8062", ret="6F13", far=False)
        r.al = arg8(mem, r, 6)                                   # 6F13
        side = r.ax
        r.ax = 5                                                 # 6F17
        r.al = 8                                                 # 6F1B
        r = yield from guest(mem, r, "6D4E", side, 5, r.ax, ret="6F21", far=False)
        if arg8(mem, r, 4):                                      # 6F21 je 6F32
            r.al = 1                                             # 6F27
            first = r.ax
            r.al = 0x3A
            r = yield from guest(mem, r, "6DEA", first, r.ax, ret="6F30", far=False)
        else:
            r.al = 0x38                                          # 6F32
            r = yield from guest(mem, r, "2AA3", r.ax, ret="6F38", far=False)
    return _end(r)


# -- 6F3E ----------------------------------------------------------------------------------------------------------
@PORTS.port("0791:6F3E", ret="ret 2")
def dead_ball_free_kick(mem, variant):
    """6F3E-6FB3 (side [bp+4]): DS:830E := 0, 8062; near the goal (2BE5 of the side's first record times the ball's y
    at least 0x12 and |x| at most 4) the free-kick taker 6D4E(side, 4, 0xB), else the side's nearest DS:8311[side] takes
    it (6BF1(slot, 0xB)); then line 0x3A and the free kicks count (6DEA(0x3A, 1))."""
    r = Regs(mem)
    r.enter(0)
    mem.wds8(0x830E, 0, "0791:6F41")
    r = yield from guest(mem, r, "8062", ret="6F49", far=False)
    side = arg8(mem, r, 4)
    r.al = side                                                  # 6F49-6F5D
    cbw(r)
    r.di = r.ax
    r.al = mem.ds8((r.di + 0x668) & M16)
    r.ah = 0
    r.ax = r.ax + 1
    r.dx = 0x16
    mul(r, r.dx)
    r.di = r.ax + 0x80E8
    r = yield from guest(mem, r, "2BE5", mem.DS, r.di, ret="6F67")
    cbw(r)                                                       # 6F67
    r.dx = r.ax
    r.al = mem.ds8(0x82F7)
    cbw(r)
    imul(r, r.dx)                                                # 6F6E
    near = False
    if s16(r.ax) >= 0x12:                                        # 6F70 cmp ax, 0x12; jl 6F94
        near = byte_abs(r, mem.ds8(0x82F6)) <= 4                 # 6F75-6F82 jg 6F94
    if near:
        r.al = side                                              # 6F84
        first = r.ax
        r.ax = 4
        r.al = 0xB
        r = yield from guest(mem, r, "6D4E", first, 4, r.ax, ret="6F92", far=False)
    else:
        r.al = side                                              # 6F94-6F9E
        cbw(r)
        r.di = r.ax
        r.al = mem.ds8((r.di + 0x8311) & M16)
        r.ah = 0
        slot = r.ax
        r.al = 0xB                                               # 6FA1
        r = yield from guest(mem, r, "6BF1", slot, r.ax, ret="6FA7", far=False)
    r.al = 1                                                     # 6FA7
    first = r.ax
    r.al = 0x3A
    r = yield from guest(mem, r, "6DEA", first, r.ax, ret="6FB0", far=False)
    return _end(r)


# -- 6FB6 ----------------------------------------------------------------------------------------------------------
@PORTS.port("0791:6FB6", ret="ret")
def foul_restart(mem, variant):
    """6FB6-6FED: with the ball's point in the holder's goal area (2E36) the side holding the ball (2996) takes a goal
    kick or free kick 6F01(side, 1), else the free kick 6F3E(side)."""
    r = Regs(mem)
    r.enter(0)
    point = mem.ds16(0x82F6)                                     # 6FB9
    holder_record(r, mem)                                        # 6FBD-6FC9
    r = yield from guest(mem, r, "2E36", point, mem.DS, r.di, ret="6FD3")
    if r.al:                                                     # 6FD3 je 6FE3
        r = yield from guest(mem, r, "2996", ret="6FDA", far=False)
        side = r.ax
        r.al = 1                                                 # 6FDB
        r = yield from guest(mem, r, "6F01", side, r.ax, ret="6FE1", far=False)
    else:
        r = yield from guest(mem, r, "2996", ret="6FE6", far=False)
        r = yield from guest(mem, r, "6F3E", r.ax, ret="6FEA", far=False)
    return _end(r)


# -- 6FEE / 70F6 / 74C2: the taker's countdown -----------------------------------------------------------------------
def _taker_wait(mem, r, at):
    """The shared head of 6FEE, 70F6 and 74C2 after 2CC5: the countdown +0x10 runs down (`dec` at at['dec']); at 0 DS:8302
    := 0, the line at['line'], DS:8323 := 1 and (6FEE, 70F6) 26C2."""
    nested(mem, r)
    v = rb(mem, r, 0x10)
    if v > 0:                                                    # cmp byte ptr es:[di + 0x10], 0; jbe
        nested(mem, r)
        wb(mem, r, 0x10, v - 1, at["dec"])
        return r
    mem.wds8(0x8302, 0, f"0791:{at['clear']}")
    r.al = at["line"]
    r = yield from guest(mem, r, "2AA3", r.ax, ret=at["ret"], far=False)
    mem.wds8(0x8323, 1, f"0791:{at['ret']}")
    if at.get("26C2"):
        r = yield from guest(mem, r, "26C2", ret=at["26C2"], far=False)
    return r


@PORTS.port("0791:6FEE", ret="ret 2")
def throw_in_taker(mem, variant):
    """6FEE-7066 (nested in 7069, its record): at the destination (2CC5) with DS:8323 set the throw (3B9E to the side's
    nearest DS:8311[2974]) and every slot to state 5; else the countdown, at 0 line 0x2A, DS:8323 := 1 and 26C2."""
    r = Regs(mem)
    r.enter(0)
    seg, off = nested(mem, r)                                    # 6FF1-6FF4
    r = yield from guest(mem, r, "2CC5", seg, off, ret="6FFE")
    if r.al:                                                     # 6FFE je 7063
        if mem.ds8(0x8323):                                      # 7002 je 7035
            seg, off = nested(mem, r)                            # 7009
            r = yield from guest(mem, r, "2974", seg, off, ret="7016")
            cbw(r)                                               # 7016-701D
            r.di = r.ax
            r.al = mem.ds8((r.di + 0x8311) & M16)
            r.ah = 0
            slot = r.ax
            seg, off = nested(mem, r)                            # 7020
            r = yield from guest(mem, r, "3B9E", slot, seg, off, ret="702D")
            r.al = 5                                             # 702D
            r = yield from guest(mem, r, "2929", r.ax, ret="7033", far=False)
        else:
            r = yield from _taker_wait(mem, r, {"dec": "704A", "clear": "7050", "line": 0x2A, "ret": "705B",
                                                "26C2": "7063"})
    return _end(r)


@PORTS.port("0791:70F6", ret="ret 2")
def corner_taker(mem, variant):
    """70F6-7157 (nested in 715A, its record): at the destination with DS:8323 set the corner's kick 3DF6 and every slot to state
    5; else the countdown, at 0 line 0x2C, DS:8323 := 1 and 26C2."""
    r = Regs(mem)
    r.enter(0)
    seg, off = nested(mem, r)                                    # 70F9-70FC
    r = yield from guest(mem, r, "2CC5", seg, off, ret="7106")
    if r.al:                                                     # 7106 je 7154
        if mem.ds8(0x8323):                                      # 710A je 7126
            seg, off = nested(mem, r)                            # 7111
            r = yield from guest(mem, r, "3DF6", seg, off, ret="711E")
            r.al = 5                                             # 711E
            r = yield from guest(mem, r, "2929", r.ax, ret="7124", far=False)
        else:
            r = yield from _taker_wait(mem, r, {"dec": "713B", "clear": "7141", "line": 0x2C, "ret": "714C",
                                                "26C2": "7154"})
    return _end(r)


@PORTS.port("0791:74C2", ret="ret 2")
def free_kick_taker(mem, variant):
    """74C2-75FE (nested in 7621, its record): at the destination with DS:8323 set, when the other side's keeper (the
    slot after DS:0668[the other side]) stands at |y| 0x25: the taker's position set to 1 (a keeper) for 06FA and 2F28, then
    put back; both true the kick 3C3F(4, 0x11), else the pass 3323; every slot to state 5. DS:8323 clear: the countdown,
    at 0 line 0x30 and DS:8323 := 1."""
    r = Regs(mem)
    r.enter(2)                                                   # 74C2-74C5
    seg, off = nested(mem, r)                                    # 74C8-74CB
    r = yield from guest(mem, r, "2CC5", seg, off, ret="74D5")
    if r.al == 0:                                                # 74D7 jne 74DC; jmp 75FB
        return _end(r)
    if mem.ds8(0x8323) == 0:                                     # 74DC jne 74E6; jmp 75D0
        r = yield from _taker_wait(mem, r, {"dec": "75E5", "clear": "75EB", "line": 0x30, "ret": "75F6"})
        return _end(r)
    r = yield from guest(mem, r, "2996", ret="74E9", far=False)
    flip(r, r.al)                                                # 74E9-74F1
    cbw(r)                                                       # 74F3-7504
    r.di = r.ax
    r.al = mem.ds8((r.di + 0x668) & M16)
    r.ah = 0
    r.ax = r.ax + 1
    r.dx = 0x16
    mul(r, r.dx)
    r.di = r.ax
    if byte_abs(r, mem.ds8((r.di + 0x80E9) & M16)) != 0x25:      # 7504 [di - 0x7f17]; 750F cmp ax, 0x25; je 7517
        return _end(r)
    nested(mem, r)                                               # 7517
    player_record(mem, r)                                        # 751E-752B
    r.al = rb(mem, r, 6)                                         # 752D
    r.ah = 0
    position = r.ax
    r.local16(-2, position)                                      # 7533
    nested(mem, r)                                               # 7536
    player_record(mem, r)
    wb(mem, r, 6, 1, "754C")
    r = yield from guest(mem, r, "214B:06FA", ret="7556")
    kick = r.al != 0                                             # 7556 je 759E
    if kick:
        seg, off = nested(mem, r)                                # 755A
        r = yield from guest(mem, r, "2F28", seg, off, ret="7567")
        kick = r.al != 0                                         # 7567 je 759E
    r.cx = (r.cx & 0xFF00) | (position & 0xFF)                   # 756B / 759E mov cl, byte ptr [bp - 2]
    nested(mem, r)
    player_record(mem, r)
    if kick:
        wb(mem, r, 6, r.cx & 0xFF, "7584")
        r.al = 0x11                                              # 7588
        first = r.ax
        r.ax = 4
        seg, off = nested(mem, r)
        r = yield from guest(mem, r, "3C3F", first, 4, seg, off, ret="759C")
    else:
        wb(mem, r, 6, r.cx & 0xFF, "75B7")
        seg, off = nested(mem, r)                                # 75BB
        r = yield from guest(mem, r, "3323", seg, off, ret="75C8")
    r.al = 5                                                     # 75C8
    r = yield from guest(mem, r, "2929", r.ax, ret="75CE", far=False)
    return _end(r)


# -- 7069 ----------------------------------------------------------------------------------------------------------
@PORTS.port("0791:7069", ret="retf 4")
def throw_in_state(mem, variant):
    """7069-70F3 (state 7 of 8AE9, a throw-in): the holder 6FEE; the side's nearest to the thrower (DS:8311[2974]) gets the
    destination x := DS:82F6 / 2 + 06FA - 06FA, y := 82F7 + 2BE5 * 06B1(4); the others 4B64."""
    r = Regs(mem)
    r.enter(0)
    seg, off = own(mem, r)                                       # 706C
    r.al = rb(mem, r, 6)
    if r.al == mem.ds8(0x830B):                                  # 7073 jne 707F
        r = yield from guest(mem, r, "6FEE", r.bp, ret="707D", far=False)
        return _end(r)
    r = yield from guest(mem, r, "2974", seg, off, ret="7088")
    cbw(r)                                                       # 7088-708B
    r.di = r.ax
    r.al = mem.ds8((r.di + 0x8311) & M16)
    r.es, r.di = seg, off
    if r.al != rb(mem, r, 6):                                    # 7092 jne 70E7
        r = yield from guest(mem, r, "4B64", seg, off, ret="70F0")
        return _end(r)
    r = yield from guest(mem, r, "214B:06FA", ret="709D")
    r.ah = 0
    r.push(r.ax)                                                 # 709F: the first coin, live across the second
    r = yield from guest(mem, r, "214B:06FA", ret="70A5")
    r.ah = 0
    r.bx = r.ax                                                  # 70A7
    r.al = mem.ds8(0x82F6)                                       # 70A9-70B1
    cbw(r)
    idiv_by(r, 3 if variant == "throw-step-3" else 2)
    r.ax = r.ax + r.bx                                           # 70B3
    r.dx = pop(mem, r)                                           # 70B5
    r.ax = r.ax - r.dx
    r.es, r.di = seg, off
    wb(mem, r, 7, r.al, "70BB")
    r = yield from guest(mem, r, "2BE5", seg, off, ret="70C8")
    cbw(r)
    r.push(r.ax)                                                 # 70C9: live across 06B1
    r.ax = 4
    r = yield from guest(mem, r, "214B:06B1", 4, ret="70D3")
    r.dx = pop(mem, r)                                           # 70D3
    imul(r, r.dx)
    r.dx = r.ax
    r.al = mem.ds8(0x82F7)                                       # 70D8
    cbw(r)
    r.ax = r.ax + r.dx
    r.es, r.di = seg, off
    wb(mem, r, 8, r.al, "70E1")
    return _end(r)


# -- 715A ----------------------------------------------------------------------------------------------------------
@PORTS.port("0791:715A", ret="retf 4")
def corner_state(mem, variant):
    """715A-717C (state 9 of 8AE9, a corner): the holder 70F6, the others 4B64."""
    r = Regs(mem)
    r.enter(0)
    seg, off = own(mem, r)                                       # 715D
    r.al = rb(mem, r, 6)
    if r.al == mem.ds8(0x830B):                                  # 7164 jne 7170
        r = yield from guest(mem, r, "70F6", r.bp, ret="716E", far=False)
    else:
        r = yield from guest(mem, r, "4B64", seg, off, ret="7179")
    return _end(r)


# -- 717F ----------------------------------------------------------------------------------------------------------
@PORTS.port("0791:717F", ret="ret 2")
def goal_area_clear(mem, variant):
    """717F-71E5 (7287's BP, unused): 1 unless an outfield slot (045D false: not 1 or 12) other than DS:830B stands in the holder's
    area (2EB8 of its point)."""
    r = Regs(mem)
    r.enter(4)                                                   # 717F-7182
    flag = 1
    r.local8(-4, flag)                                           # 7185
    slot = 1
    r.local16(-3, slot)                                          # 7189
    while True:
        r = yield from guest(mem, r, "045D", slot, ret="7199", far=False)     # 7193
        if r.al == 0:                                            # 719B jne 71D3
            r.al = mem.ds8(0x830B)                               # 719D
            r.ah = 0
            if r.ax != slot:                                     # 71A2 je 71D3
                r.ax = slot                                      # 71A7-71AF
                r.dx = 0x16
                mul(r, r.dx)
                r.di = r.ax
                point = mem.ds16((r.di + 0x80E8) & M16)          # 71B1 [di - 0x7f18]
                holder_record(r, mem)                            # 71B5-71C1
                r = yield from guest(mem, r, "2EB8", point, mem.DS, r.di, ret="71CB")
                if r.al:                                         # 71CB je 71D3
                    flag = 0
                    r.local8(-4, 0)                              # 71CF
        if slot == 0x16:                                         # 71D3 cmp; jne 7190
            break
        slot += 1
        r.local16(-3, slot)                                      # 7190
    r.al = flag                                                  # 71D9-71DF
    r.local8(-1, flag)
    return _end(r, value=True)


# -- 71E8 ----------------------------------------------------------------------------------------------------------
@PORTS.port("0791:71E8", ret="ret 2")
def goal_kick_taker(mem, variant):
    """71E8-7284 (nested in 7287, its record): at the destination, on the ball's spot DS:8315: with DS:8323 set the
    kick 3B15 and every slot to state 5; else with the area clear (717F) y := -0x25 * 2BE5, line 0x2E and
    DS:8323 := 1. Off the spot: DS:830C := its slot, DS:830D := 0 and the destination := DS:8315."""
    r = Regs(mem)
    r.enter(0)
    seg, off = nested(mem, r)                                    # 71EB-71EE
    r = yield from guest(mem, r, "2CC5", seg, off, ret="71F8")
    if r.al == 0:                                                # 71FA jne 71FF; jmp 7281
        return _end(r)
    nested(mem, r)                                               # 71FF
    r.ax = rw(mem, r, 0)
    if r.ax == mem.ds16(0x8315):                                 # 7209 jne 7260
        if mem.ds8(0x8323):                                      # 720F je 722B
            seg, off = nested(mem, r)                            # 7216
            r = yield from guest(mem, r, "3B15", seg, off, ret="7223")
            r.al = 5                                             # 7223
            r = yield from guest(mem, r, "2929", r.ax, ret="7229", far=False)
        else:
            parent = arg16(mem, r, 4)                            # 722B push word ptr [bp + 4]
            r = yield from guest(mem, r, "717F", parent, ret="7231", far=False)
            if r.al:                                             # 7231 je 725E
                seg, off = nested(mem, r)                        # 7235
                r = yield from guest(mem, r, "2BE5", seg, off, ret="7242")
                cbw(r)
                r.cx = 0xFFDB
                imul(r, r.cx)                                    # 7246
                nested(mem, r)                                   # 7248
                wb(mem, r, 8, r.al, "724F")
                r.al = 0x2E                                      # 7253
                r = yield from guest(mem, r, "2AA3", r.ax, ret="7259", far=False)
                mem.wds8(0x8323, 1, "0791:7259")
    else:
        nested(mem, r)                                           # 7260
        r.al = rb(mem, r, 6)
        mem.wds8(0x830C, r.al, "0791:726B")
        mem.wds8(0x830D, 0, "0791:726E")
        r.ax = mem.ds16(0x8315)                                  # 7273
        nested(mem, r)
        ww(mem, r, 7, r.ax, "727D")
    return _end(r)


# -- 7287 ----------------------------------------------------------------------------------------------------------
@PORTS.port("0791:7287", ret="retf 4")
def goal_kick_state(mem, variant):
    """7287-72EF (state 8 of 8AE9, a goal kick): the holder 71E8; a goalkeeper's slot (045D: 1 or 12) 4354; one in the holder's area (2EB8)
    y := 0; the others 4B64."""
    r = Regs(mem)
    r.enter(0)
    seg, off = own(mem, r)                                       # 728A
    r.al = rb(mem, r, 6)
    if r.al == mem.ds8(0x830B):                                  # 7291 jne 729D
        r = yield from guest(mem, r, "71E8", r.bp, ret="729B", far=False)
        return _end(r)
    r.al = rb(mem, r, 6)                                         # 729D-72A4
    r.ah = 0
    r = yield from guest(mem, r, "045D", r.ax, ret="72AA", far=False)
    if r.al:                                                     # 72AA je 72B9
        r = yield from guest(mem, r, "4354", seg, off, ret="72B7")
        return _end(r)
    r.es, r.di = seg, off                                        # 72B9
    point = rw(mem, r, 0)
    holder_record(r, mem)                                        # 72BF-72CB
    r = yield from guest(mem, r, "2EB8", point, mem.DS, r.di, ret="72D5")
    r.es, r.di = seg, off
    if r.al:                                                     # 72D5 je 72E3
        wb(mem, r, 8, 0, "72DC")
    else:
        r = yield from guest(mem, r, "4B64", seg, off, ret="72EC")
    return _end(r)


# -- 7621 ----------------------------------------------------------------------------------------------------------
@PORTS.port("0791:7621", ret="retf 4")
def free_kick_state(mem, variant):
    """7621-787E (state 0xB of 8AE9, a free kick): the holder 74C2. A slot of the side defending (2B51 false) facing the kick (2BE5 of
    the holder times DS:8316 above 0), with |y| - |x| of DS:8315 above 10 and its position in the set at 0791:7601,
    takes a place by its position (2BB1 - 7) around a point near the ball (|y| < 0x1A) or the halfway point; the others
    4B64, a defender then kept at least 4 rows from the ball's |y| (2BE5 steps) and moved off the ball's x by a coin."""
    r = Regs(mem)
    r.enter(4)                                                   # 7621-7624
    seg, off = own(mem, r)                                       # 7627
    r.al = rb(mem, r, 6)
    if r.al == mem.ds8(0x830B):                                  # 762E jne 763B
        r = yield from guest(mem, r, "74C2", r.bp, ret="7638", far=False)
        return _end(r)
    r = yield from guest(mem, r, "2B51", seg, off, ret="7644")
    place = False
    if r.al == 0:                                                # 7644 je 764B; jmp 7805
        holder_record(r, mem)                                    # 764B-7657
        r = yield from guest(mem, r, "2BE5", mem.DS, r.di, ret="7661")
        cbw(r)                                                   # 7661-7668
        r.dx = r.ax
        r.al = mem.ds8(0x8316)
        cbw(r)
        imul(r, r.dx)
        if s16(r.ax) > 0:                                        # 766A or ax, ax; jg 7671
            byte_abs(r, mem.ds8(0x8315))                         # 7671-7679
            r.dx = r.ax
            byte_abs(r, mem.ds8(0x8316))                         # 767D-7685
            r.ax = r.ax - r.dx                                   # 7687
            if s16(r.ax) > 0xA:                                  # 7689 cmp ax, 0xa; jg 7691
                r.es, r.di = seg, off
                r = yield from guest(mem, r, "2BB1", seg, off, ret="769A")
                r.di = 0x7601                                    # 769B
                r = yield from guest(mem, r, "23E4:08DF", r.ax, mem.seg(0x0791), 0x7601, ret="76A5")
                place = not zero_flag(mem)                       # 76A5 jne 76AA
    if place:
        if byte_abs(r, mem.ds8(0x8316)) < 0x1A:                  # 76AA-76B7 cmp ax, 0x1a; jl 76BC
            xs = 1 if s8(mem.ds8(0x8315)) > 0 else 0xFF          # 76BC-76C9 jle
            r.local8(-4, xs)
            if byte_abs(r, mem.ds8(0x8315)) > 4:                 # 76CD-76DA jle 76F7
                holder_record(r, mem)                            # 76DC-76E8
                r = yield from guest(mem, r, "2BE5", mem.DS, r.di, ret="76F2")
                ys = r.al
            else:
                ys = 0
            r.local8(-3, ys)                                     # 76F2 / 76F7
            r.al = xs                                            # 76FB-7701
            cbw(r)
            r.ax = r.ax << 1
            r.bx = r.ax
            r.al = mem.ds8(0x8315)                               # 7703-770B
            cbw(r)
            idiv_by(r, 2)
            r.ax = r.ax - r.bx                                   # 770D
            x = r.al
            r.local8(-2, x)                                      # 770F
            r.al = ys                                            # 7712-7716
            cbw(r)
            r.ax = r.ax << 1
            r.push(r.ax)                                         # 7718: live across 2BE5
            holder_record(r, mem)                                # 7719-7725
            r = yield from guest(mem, r, "2BE5", mem.DS, r.di, ret="772F")
            cbw(r)
            r.cx = 5
            imul(r, r.cx)                                        # 7733
            r.dx = r.ax
            r.al = mem.ds8(0x8316)                               # 7737
            cbw(r)
            r.ax = r.ax + r.dx
            r.dx = pop(mem, r)                                   # 773D
            r.ax = r.ax - r.dx
            y = r.al
            r.local8(-1, y)                                      # 7740
        else:
            xs, ys = 0, 1
            r.local8(-4, xs)                                     # 7745
            r.local8(-3, ys)                                     # 7749
            r.al = 1 if s8(mem.ds8(0x8315)) < 0 else 0           # 774D-775A jl
            table_by_al(r, mem, 0x7920)
            cbw(r)
            r.cx = 3
            imul(r, r.cx)                                        # 7765
            r.dx = r.ax
            r.al = mem.ds8(0x8315)                               # 7769
            cbw(r)
            r.ax = r.ax + r.dx
            x = r.al
            r.local8(-2, x)                                      # 776F
            r.al = 1 if s8(mem.ds8(0x8316)) < 0 else 0           # 7772-777F jl
            table_by_al(r, mem, 0x7920)
            cbw(r)
            r.bx = r.ax                                          # 7787
            byte_abs(r, mem.ds8(0x8316))                         # 7789-7791
            r.ax = r.ax + 0xFFE6                                 # 7793
            idiv_by(r, 2)                                        # 7796-779A
            r.ax = r.ax + 0x1C                                   # 779C
            imul(r, r.bx)                                        # 779F
            y = r.al
            r.local8(-1, y)                                      # 77A1
        r.es, r.di = seg, off                                    # 77A4
        r = yield from guest(mem, r, "2BB1", seg, off, ret="77AD")
        r.ah = 0
        r.ax = r.ax - 7                                          # 77AF
        r.dx = r.ax
        r.al = ys                                                # 77B4
        cbw(r)
        imul(r, r.dx)
        r.dx = r.ax
        r.al = y                                                 # 77BC
        cbw(r)
        r.ax = r.ax + r.dx
        r.es, r.di = seg, off
        wb(mem, r, 8, r.al, "77C5")
        r = yield from guest(mem, r, "2BB1", seg, off, ret="77D2")
        r.ah = 0
        r.ax = r.ax - 7                                          # 77D4
        r.dx = r.ax
        r.al = xs                                                # 77D9
        cbw(r)
        imul(r, r.dx)
        r.dx = r.ax
        r.al = x                                                 # 77E1
        cbw(r)
        r.ax = r.ax + r.dx
        r.es, r.di = seg, off
        wb(mem, r, 7, r.al, "77EA")
        r = yield from guest(mem, r, "2CC5", seg, off, ret="77F7")
        if r.al:                                                 # 77F7 je 7803
            r.es, r.di = seg, off
            wb(mem, r, 0x12, 0, "77FE")
        return _end(r)
    r.es, r.di = seg, off                                        # 7805
    r = yield from guest(mem, r, "4B64", seg, off, ret="780E")
    r.es, r.di = seg, off                                        # 780E
    r = yield from guest(mem, r, "2B51", seg, off, ret="7817")
    if r.al:                                                     # 7817 jne 787B
        return _end(r)
    while True:
        byte_abs(r, mem.ds8(0x8316))                             # 781B-7823
        r.dx = r.ax
        r.es, r.di = seg, off                                    # 7827
        byte_abs(r, rb(mem, r, 8))
        r.ax = r.ax - r.dx                                       # 7835
        if s16(r.ax) >= 4:                                       # 7837 cmp ax, 4; jge 785B
            break
        holder_record(r, mem)                                    # 783C-7848
        r = yield from guest(mem, r, "2BE5", mem.DS, r.di, ret="7852")
        r.es, r.di = seg, off
        wb(mem, r, 8, rb(mem, r, 8) + r.al, "7855")
    r.es, r.di = seg, off                                        # 785B
    r.al = rb(mem, r, 7)
    if r.al == mem.ds8(0x8315):                                  # 7862 jne 787B
        r = yield from guest(mem, r, "214B:06FA", ret="786D")
        cbw(r)                                                   # 786D-7870
        r.di = r.ax
        r.al = mem.ds8((r.di + 0x7920) & M16)
        r.es, r.di = seg, off
        wb(mem, r, 7, rb(mem, r, 7) + r.al, "7877")
    return _end(r)


# -- 7881 ----------------------------------------------------------------------------------------------------------
@PORTS.port("0791:7881", ret="ret 2")
def walk_player_off(mem, variant):
    """7881-798A (slot [bp+4]): unless its point is DS:0640 (off the pitch): DS:8302 := 1, state 0xC, destination
    DS:0642, the clock flags DS:8325 and DS:9B41 kept and cleared; unless a quick match (DS:9A3E), passes of its tick
    (8AE9) and of the 22 slots' pictures (8537), each with the speaker 94E8, the key poll and the wait 214B:1E09 by the
    speed setting, until it is there (2CC5); the flags put back, its point := DS:0640, the picture (8537), state 0."""
    r = Regs(mem)
    r.enter(8)                                                   # 7881-7884
    slot = arg16(mem, r, 4)
    r.ax = slot                                                  # 7887-7891
    r.dx = 0x16
    mul(r, r.dx)
    r.di = r.ax + 0x80E8
    rec = r.di
    r.local16(-8, rec)                                           # 7895
    r.local16(-6, mem.DS)                                        # 7898
    r.es = mem.DS                                                # 789B
    r.ax = rw(mem, r, 0)
    if r.ax == mem.ds16(0x640):                                  # 78A1 jne 78AA; jmp 7987
        return _end(r)
    mem.wds8(0x8302, 1, "0791:78AA")
    r.es, r.di = mem.DS, rec
    wb(mem, r, 0x12, 0xC, "78B2")
    r.ax = mem.ds16(0x642)                                       # 78B7
    ww(mem, r, 7, r.ax, "78BD")
    clock = mem.ds8(0x8325)                                      # 78C1
    r.al = clock
    r.local8(-3, clock)
    mem.wds8(0x8325, 0, "0791:78C7")
    pause = mem.ds8(0x9B41)                                      # 78CC
    r.al = pause
    r.local8(-4, pause)
    mem.wds8(0x9B41, 0, "0791:78D2")
    if mem.ds8(0x9A3E) == 0:                                     # 78D7 jne 795A
        while True:
            r.es, r.di = mem.DS, rec                             # 78DE
            r = yield from guest(mem, r, "8AE9", mem.DS, rec, ret="78E7")
            k = 1
            r.local16(-2, k)                                     # 78E7
            while True:
                r = yield from guest(mem, r, "94E8", ret="78F4", far=False)    # 78F1
                far_return_words(mem, r, 0x78F9)                 # 78F4 call far 214B:0723
                r.al = 1 if mem.keypressed("0791:78F9") else 0
                if r.al:                                         # 78F9 je 7902
                    far_return_words(mem, r, 0x7902)             # 78FD call far 214B:08DD
                    r.al = mem.read_key("0791:7902")
                r.di, r.es = mem.ds16(0xA923), mem.ds16(0xA925)  # 7902
                speed = rb(mem, r, 0x3F)
                if speed == 0:                                   # 7906 jne 7918
                    r.ax = 2                                     # 790D
                    r = yield from guest(mem, r, "214B:1E09", 2, ret="7916")
                elif speed == 1:                                 # 791C jne 792C
                    r.ax = 1                                     # 7923
                    r = yield from guest(mem, r, "214B:1E09", 1, ret="792C")
                r.ax = k                                         # 792C-7936
                r.dx = 0x16
                mul(r, r.dx)
                r.di = r.ax + 0x80E8
                r = yield from guest(mem, r, "8537", mem.DS, r.di, ret="7940")
                if k == 0x16:                                    # 7940 cmp; jne 78EE
                    break
                k += 1
                r.local16(-2, k)                                 # 78EE
            if mem.ds8(0x9A3E):                                  # 7946 jne 795A
                break
            r.es, r.di = mem.DS, rec                             # 794D
            r = yield from guest(mem, r, "2CC5", mem.DS, rec, ret="7956")
            if r.al:                                             # 7956 je 78DE
                break
    r.al = pause                                                 # 795A
    mem.wds8(0x9B41, pause, "0791:795A")
    r.al = clock                                                 # 7960
    mem.wds8(0x8325, clock, "0791:7960")
    r.ax = mem.ds16(0x640)                                       # 7966
    r.es, r.di = mem.DS, rec
    ww(mem, r, 0, r.ax, "796C")
    if mem.ds8(0x9A3E) == 0:                                     # 796F jne 797F
        r = yield from guest(mem, r, "8537", mem.DS, rec, ret="797F")
    r.es, r.di = mem.DS, rec                                     # 797F
    wb(mem, r, 0x12, 0, "7982")
    return _end(r)


# -- 798D ----------------------------------------------------------------------------------------------------------
@PORTS.port("0791:798D", ret="retf 4")
def booking(mem, variant):
    """798D-7A40 (the record [bp+6]): line 0x32 (2AD4), the referee's message (90C5, the delay 0425 of 200 * the speed
    setting, 9079), the player's status +0x10 element 5 (214B:0C79), the side's bookings DS:7B85 + 10 side +1 (7A01, the
    kit's booking event), DS:8321 +1 up to 5; an unmanaged side's player loses his own tactic (1771:33CD)."""
    r = Regs(mem)
    r.enter(4)                                                   # 798D-7990
    seg, off = own(mem, r)                                       # 7993
    player_record(mem, r)                                        # 7996-79A3
    prec_seg, prec_off = r.es, r.di
    r.local16(-4, prec_off)                                      # 79A5
    r.local16(-2, prec_seg)                                      # 79A8
    r.al = 0x32                                                  # 79AB
    r = yield from guest(mem, r, "2AD4", r.ax, ret="79B1", far=False)
    r.ax = 0xEFE                                                 # 79B1
    word = mem.ds16(0x82EE)
    r.di = 0x8304
    r = yield from guest(mem, r, "90C5", 0xEFE, word, mem.DS, 0x8304, ret="79C2")
    r.di, r.es = mem.ds16(0xA923), mem.ds16(0xA925)              # 79C2
    r.al = rb(mem, r, 0x3F)
    r.ah = 0
    r.cx = 0xC8
    imul(r, r.cx)                                                # 79CF
    r = yield from guest(mem, r, "0425", r.ax, ret="79D5", far=False)
    r.di = 0x8304                                                # 79D5
    r = yield from guest(mem, r, "9079", mem.DS, 0x8304, ret="79DE")
    r.ax = 5                                                     # 79DE
    r.es, r.di = prec_seg, prec_off                              # 79E2
    r.di = r.di + 0x10
    r = yield from guest(mem, r, "214B:0C79", 5, r.es, r.di, ret="79F0")
    seg, off = own(mem, r)                                       # 79F0
    r = yield from guest(mem, r, "2974", seg, off, ret="79F9")
    cbw(r)                                                       # 79F9-79FD
    r.dx = 0xA
    mul(r, r.dx)
    r.di = r.ax
    mem.wds8(r.di + 0x7B85, mem.ds8((r.di + 0x7B85) & M16) + 1, "0791:7A01")   # the booking
    if mem.ds16(0x8321) < 5:                                     # 7A05 cmp word; jae 7A10
        mem.wds16(0x8321, mem.ds16(0x8321) + 1, "0791:7A0C")
    own(mem, r)                                                  # 7A10
    player_record(mem, r)                                        # 7A13-7A20
    r.al = rb(mem, r, 0)                                         # 7A22
    r.ah = 0
    r = yield from guest(mem, r, "1771:0B77", r.ax, ret="7A2D")
    if r.al == 0:                                                # 7A2D jne 7A3D
        own(mem, r)                                              # 7A31
        r = yield from guest(mem, r, "1771:33CD", rw(mem, r, 0xD), ret="7A3D")
    return _end(r)


# -- 7A43 ----------------------------------------------------------------------------------------------------------
@PORTS.port("0791:7A43", ret="ret 2")
def side_may_lose_a_player(mem, variant):
    """7A43-7B21 (side [bp+4]): 1 when the side's sendings off and injuries (DS:7B86, 7B87 + 10 side) are fewer than 3,
    for an unmanaged side only when more than 11 of its 20 squad words are available (1771:3216 false); else 0."""
    r = Regs(mem)
    r.enter(0xA)                                                 # 7A43-7A46
    side = arg8(mem, r, 4)
    r.al = side                                                  # 7A49-7A4F
    cbw(r)
    r.di = r.ax
    r.di = r.di << 1
    squad = mem.ds16((r.di + 0x9B34) & M16)                      # 7A51
    r = yield from guest(mem, r, "1771:0B77", squad, ret="7A5A")

    def fewer_than_3():
        """7A5E-7A87 / 7AE7-7B10: DS:7B86 + 10 side plus DS:7B87 + 10 side, below 3 (signed)."""
        r.al = side
        cbw(r)
        r.dx = 0xA
        mul(r, r.dx)
        r.di = r.ax
        r.al = mem.ds8((r.di + 0x7B86) & M16)
        r.ah = 0
        r.cx = r.ax
        r.al = side
        cbw(r)
        r.dx = 0xA
        mul(r, r.dx)
        r.di = r.ax
        r.al = mem.ds8((r.di + 0x7B87) & M16)
        r.ah = 0
        r.ax = r.ax + r.cx
        return s16(r.ax) < 3

    if r.al:                                                     # 7A5A je 7A95
        r.al = 1 if fewer_than_3() else 0                        # 7A87-7A8D
    else:
        r.ax = 0                                                 # 7A95
        available = 0
        r.local16(-5, available)
        k = 1
        r.local16(-3, k)                                         # 7A9A
        while True:
            r.al = side                                          # 7AA4-7AB3
            cbw(r)
            r.di = r.ax
            r.di = r.di << 1
            r.ax = mem.ds16((r.di + 0x9B34) & M16)
            r.dx = 0xBF
            mul(r, r.dx)
            r.di, r.es = mem.ds16(0xA917), mem.ds16(0xA919)      # 7AB5
            r.di = r.di + r.ax
            r.local16(-9, r.di)                                  # 7ABB
            r.local16(-7, r.es)                                  # 7ABE
            r.ax = k << 1                                        # 7AC1-7AC9
            r.di = r.di + r.ax
            word = mem.u16(mem.addr(r.es, r.di - 2))             # 7ACB
            r = yield from guest(mem, r, "1771:3216", word, ret="7AD4")
            if r.al == 0:                                        # 7AD6 jne 7ADB
                available += 1
                r.local16(-5, available)                         # 7AD8
            if k == 0x14:                                        # 7ADB cmp; jne 7AA1
                break
            k += 1
            r.local16(-3, k)                                     # 7AA1
        if available > 0xB:                                      # 7AE1 cmp word; jbe 7B12
            r.al = 1 if fewer_than_3() else 0                    # 7B10
        else:
            r.al = 0                                             # 7B12
    r.local8(-1, r.al)                                           # 7A8F / 7B18
    return _end(r, value=True)
