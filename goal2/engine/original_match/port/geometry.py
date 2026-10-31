"""The geometry queries (T60, P1a): 32 routines of 0791:261A-2F28 that ask where a pitch record (22 bytes at DS:80E8 +
0x16 * slot) stands: its side, its slot within the side, its attack direction, whether it is ahead of or behind the ball
or in the penalty strip; the contest value of a skill (278A) and its pass/fail draw (287C); the draw table byte (261A);
the commentary wrappers that call the emitter 0791:1EB5 (T69, still the original's: guest calls, port/guest.py).

From the listing (static/goal-exe/code/seg_0791_04.asm from 261A, seg_0791_05.asm to 2F28); the line comments are its
offsets. Each routine is written as the original's instructions in the registers it works in (`Regs`, port/runtime.py), a
routine it calls near being the same function on the same registers, so that what is left in AX and DX (compared by the
proof, port/prove.py) and the pushed words a guest call receives are the original's too: the high byte of a word the
listing builds with `mov al, ..` is whatever AH held. The routines that are not in this task's row but are called here
(2974 the side of a slot, 2BE5 the attack direction: T58's pilot has them as values only) are written the same way, as
private helpers, not as ports.

The stack is the original's too (see port/runtime.py): each routine writes the frame the listing's code writes below the
entry SP (the saved BP, its locals, the arguments and return addresses it pushes for the routines it calls, and theirs),
because the memory digests of a match include the stack segment. A guest call is made from the frame the listing has, so
the stack the callee sees is the original's.

DS offsets used (each from the listing line cited where it is used): the pitch records DS:80E8 (+0 x, +1 y, +6 slot,
+0xD player, +0x11, +0x12 state, +0x13 flag), the ball slot DS:830B and the second slot DS:830C, the ball DS:82F6/82F7, the
attack direction table DS:7920, the side bases DS:0668, the players array far pointer DS:A91B (20 bytes each), the
countries array DS:A917 (0xBF each)."""
from .guest import call
from .mem import s8, s16
from .runtime import Regs, M16, args, draw_is_one, entry_sp, invoke, set_test, wrap_add_byte
from . import Registry

PORTS = Registry("geometry", "the geometry queries 0791:261A-2F28: side, slot, direction, ahead/behind, penalty strip, "
                             "the skill contest value and its draw (T60)")
PORTS.variant("ahead-inclusive", "2D10's compare of the ball with the player's line reads `jb` for `ja` (2D59): equal is ahead")
PORTS.variant("own-half-zero", "2C54 counts y * direction = 0 as the own half (2C72 jl -> jle)")
PORTS.variant("slot-side-12", "2BB1 counts slot 12 as the first slot of its side (2BBA jbe 0xB -> jbe 0xC)")
PORTS.variant("skill-no-halving", "278A never halves the skill (27F1 cmp byte [di+0x13] ignored)")
PORTS.variant("energy-gate-32", "2B7B draws against 0x20 - energy, not 0x21 (2B9A)")
PORTS.variant("penalty-strip-4", "2E82's x limit is 4, not 5 (2EA1 cmp ax, 5 -> 4)")
PORTS.variant("keeper-gate-off", "278A's element-1 gate never adds the keeper term (282D-2841)")

CS = 0x791                  # the code segment of every routine here (`push cs`, `call far` from inside it)
PITCH = 0x80E8              # the pitch records, 0x16 bytes each, slot 1..22
BALL_SLOT, SECOND_SLOT = 0x830B, 0x830C
DIRECTIONS = 0x7920         # 2C19: the attack direction by side
SIDE_BASES = 0x668          # 29C9: the first slot - 1 of side 0 and 1
PLAYERS_PTR, COUNTRIES_PTR = 0xA91B, 0xA917
CS_KEEPER_EVENTS = 0x276A   # 283A: the 32-byte set {3, 4} in the code segment 0791 (08DF tests membership)
BALL_X_Y = 0x82F6


# -- the instructions the listing repeats ----------------------------------------------------------------------------
def sx8(b):
    """cbw: AL sign-extended to AX."""
    return (b - 0x100 if b & 0x80 else b) & M16


def cbw(R):
    R.ax = sx8(R.al)


def cwd(R):
    R.dx = 0xFFFF if R.ax & 0x8000 else 0


def mul(R, src):
    """mul src (word): DX:AX := AX * src."""
    p = R.ax * (src & M16)
    R.ax, R.dx = p & M16, p >> 16


def imul(R, src):
    """imul src (word): DX:AX := AX * src, signed."""
    p = s16(R.ax) * s16(src)
    R.ax, R.dx = p & M16, (p >> 16) & M16


def neg_if_negative(R):
    """or ax, ax; jns +2; neg ax."""
    if R.ax & 0x8000:
        R.ax = -R.ax


def rec8(mem, seg, off, k):
    return mem.u8(seg * 16 + ((off + k) & M16))


def rec16(mem, seg, off, k):
    return mem.u16(seg * 16 + ((off + k) & M16))


def player_byte(mem, R, seg, off, field):
    """`les di, [rec]; ax := word at +0xD; mul 0x14; les di, [A91B]; add di, ax; al := byte [di + field]; xor ah, ah`
    (26ED-26FC and the same lines of 2712-2725, 2B84-2B93, 2F3E-2F53): the player record of a pitch record."""
    R.es, R.di = seg, off
    R.ax = rec16(mem, seg, off, 0xD)
    R.dx = 0x14
    mul(R, 0x14)
    poff, pseg = mem.farptr(mem.DS * 16 + PLAYERS_PTR)
    R.es, R.di = pseg, (poff + R.ax) & M16
    R.al = rec8(mem, pseg, R.di, field)
    R.ah = 0


# -- the helpers that are not in the row (private): 2974, 2996, 2BB1, 2BE5, 2A6D, 2C54, 2E82 ----------------------------
# Each is the routine from its `push bp` to its return; the caller has pushed the arguments and the return address.
def c2974(mem, R, seg, off):
    """2974 pitch_slot_side(rec): 1 when the record's slot (+6) is below 0xC."""
    R.enter(2)                                                 # 2974-2979
    R.es, R.di = seg, off                                      # 297A
    R.al = 1 if rec8(mem, seg, off, 6) < 0xC else 0
    R.local8(-1, R.al)                                         # 298A
    R.leave()


def c2996(mem, R):
    """2996: 1 when the ball slot DS:830B is below 0xC."""
    R.enter(2)                                                 # 2996-299B
    R.al = 1 if mem.ds8(BALL_SLOT) < 0xC else 0
    R.local8(-1, R.al)                                         # 29A9
    R.leave()


def c2bb1(mem, R, seg, off, variant=None):
    """2BB1 slot_in_side(rec): +6 - 0xB for slots above 0xB, else +6."""
    R.enter(2)                                                 # 2BB1-2BB6
    R.es, R.di = seg, off
    slot = rec8(mem, seg, off, 6)
    if slot > (0xC if variant == "slot-side-12" else 0xB):    # 2BBA cmp [di+6], 0xb; jbe 2BD2
        R.ax = (slot - 0xB) & M16                              # 2BC4-2BCA: al := slot; xor ah, ah; sub ax, 0xb
    else:
        R.al = slot                                            # 2BD5
    R.local8(-1, R.al)                                         # 2BCD / 2BD9
    R.leave()


def c2be5(mem, R, seg, off):
    """2BE5 attack_direction(rec): DS:7920[(DS:831B > sign-extended DS:8319) xor side]; AX = the byte (AH 0), DX the word
    pushed at 2C09 (AH = high byte of DS:831B, AL the flag), CX, BX the sign-extended DS:8319, DI the index."""
    R.enter(2)                                                 # 2BE5-2BEA
    R.al = mem.ds8(0x8319)                                     # 2BEB
    cbw(R)                                                     # 2BEE cwde
    cwd(R)                                                     # 2BEF cdq
    R.cx, R.bx = R.ax, R.dx                                    # 2BF0-2BF2
    R.ax = mem.ds16(0x831B)                                    # 2BF4
    R.dx = 0                                                   # 2BF7
    if s16(R.dx) > s16(R.bx):                                  # 2BF9 cmp dx, bx; jg 2C07
        flag = 1
    elif s16(R.dx) < s16(R.bx):                                # 2BFB jl 2C03
        flag = 0
    else:
        flag = 1 if R.ax > R.cx else 0                         # 2BFF cmp ax, cx; ja 2C07
    R.al = flag
    pushed = R.ax
    R.push(pushed)                                             # 2C09 push ax
    R.es, R.di = seg, off                                      # 2C0A
    invoke(mem, R, CS, 0x2C13, c2974, seg, off, pushes=(seg, off))      # 2C0D-2C10
    R.dx = pushed                                              # 2C13 pop dx
    R.sp = R.sp + 2
    R.al = R.al ^ (R.dx & 0xFF)                                # 2C14 xor al, dl
    cbw(R)                                                     # 2C16 cwde
    R.di = R.ax
    R.al = mem.ds8(DIRECTIONS + R.di)                          # 2C19
    R.local8(-1, R.al)                                         # 2C1D
    R.leave()


def direction_in_dx(mem, R, seg, off, ret_ip):
    """`les di, [rec]; push es; push di; push cs; call 2BE5; cwde; mov dx, ax` (2C5A-2C64 and its repeats)."""
    R.es, R.di = seg, off
    invoke(mem, R, CS, ret_ip, c2be5, seg, off, pushes=(seg, off))
    cbw(R)
    R.dx = R.ax


def c2a6d(mem, R, variant=None):
    """2A6D: slot_in_side (2BB1) of the record of slot DS:830C, or 0 when DS:830C is 0."""
    R.enter(2)                                                 # 2A6D-2A72
    slot = mem.ds8(SECOND_SLOT)
    if slot == 0:                                              # 2A73 cmp [830c], 0; jbe 2A97
        R.ax = 0
    else:
        R.ax = slot                                            # 2A7A-2A7D
        R.dx = 0x16
        mul(R, 0x16)                                           # 2A7F-2A82
        R.di = (R.ax + PITCH) & M16                            # 2A84-2A86
        ds = mem.DS
        invoke(mem, R, CS, 0x2A90, c2bb1, ds, R.di, variant, pushes=(ds, R.di))      # 2A8A-2A8D
        R.ah = 0                                               # 2A90 xor ah, ah
    R.local16(-2, R.ax)                                        # 2A92 / 2A99
    R.leave()


def c2e82(mem, R, word, variant=None):
    """2E82 (word: x low byte, y high byte): |y| >= 0x19 and |x| <= 5."""
    R.enter(2)                                                 # 2E82-2E87
    R.al = word >> 8                                           # 2E88
    cbw(R)
    neg_if_negative(R)                                         # 2E8C-2E90
    if s16(R.ax) < 0x19:                                       # 2E92 cmp ax, 0x19; jl 2EA6
        R.al = 0
    else:
        R.al = word & 0xFF                                     # 2E97
        cbw(R)
        neg_if_negative(R)
        limit = 4 if variant == "penalty-strip-4" else 5
        R.al = 1 if s16(R.ax) <= limit else 0                  # 2EA1 cmp ax, 5; jle 2EAA
    R.local8(-1, R.al)                                         # 2EAC
    R.leave()


def c2c54(mem, R, seg, off, variant=None):
    """2C54 in_own_half(rec) (called from 2F28 too): y * direction < 0."""
    R.enter(2)                                                 # 2C54-2C59
    direction_in_dx(mem, R, seg, off, 0x2C63)                  # 2C5A-2C64
    R.es, R.di = seg, off                                      # 2C66
    R.al = rec8(mem, seg, off, 1)                              # 2C69
    cbw(R)
    imul(R, R.dx)                                              # 2C6E
    if variant == "own-half-zero":
        R.al = 1 if s16(R.ax) <= 0 else 0
    else:
        R.al = 1 if R.ax & 0x8000 else 0                       # 2C70-2C7A or al, al; jl
    R.local8(-1, R.al)                                         # 2C7A
    R.leave()


# -- the draw table byte, the message words ---------------------------------------------------------------------------
@PORTS.port("0791:261A", ret="ret")
def draw_table_byte(mem, variant):
    """261A: the next byte of the 255-entry draw table at DS:8337, the index DS:8437 wrapping from 0xFF to 1."""
    R = Regs(mem)
    R.enter(2)                                                 # 261A-261D
    di = mem.ds16(0x8437)                                      # 2620
    R.di = di
    R.ax = mem.ds8((0x8337 + di) & M16)                        # 2624-2628
    R.local16(-2, R.ax)                                        # 262A
    if di == 0xFF:                                             # 262D
        mem.wds16(0x8437, 1, "0791:2635")
    else:
        mem.wds16(0x8437, di + 1, "0791:263D")                 # inc word ptr [0x8437]
    R.leave()
    R.store()


@PORTS.port("0791:26A0", ret="ret 2")
def set_message_word(mem, variant):
    """26A0(flag): DS:8308 := 0xEAF (flag) or 0xEAE; DS:8328 := 1. Registers untouched."""
    R = Regs(mem)
    R.enter()                                                  # 26A0
    if args(mem, 1)[0] & 0xFF:                                 # 26A3
        mem.wds16(0x8308, 0x0EAF, "0791:26A9")
    else:
        mem.wds16(0x8308, 0x0EAE, "0791:26B1")
    mem.wds8(0x8328, 1, "0791:26B7")
    R.leave()
    R.store()


@PORTS.port("0791:26C2", ret="ret")
def show_message_8304(mem, variant):
    """26C2: 9079(DS:8304) (still the original's), then DS:8328 := 0."""
    R = Regs(mem)
    R.enter()                                                  # 26C2
    R.di = 0x8304                                              # 26C5
    R.store(stack=True)
    yield call("0791:9079", mem.DS, 0x8304, ret_to="0791:26CE", far=True)       # 26C8-26CB
    mem.wds8(0x8328, 0, "0791:26CE")


# -- tactics and skills ----------------------------------------------------------------------------------------------
@PORTS.port("0791:26D7", ret="retf 6")
def player_effective_tactic(mem, variant):
    """26D7(rec, k): the player's own setting of element k when k < 5 and element k + 4 of his +0xF is set, else element k
    of the country's +0x2D (side of the slot); each is 214B:0C57's bit k - 1."""
    off, seg, k = args(mem, 3)
    R = Regs(mem)
    R.enter(2)                                                 # 26D7-26DC
    sp_frame = R.sp
    if k < 5:                                                  # 26DD cmp [bp+0xa], 5; jae 2732
        player_byte(mem, R, seg, off, 0xF)                     # 26E3-26FF
        own = R.ax
        invoke(mem, R, CS, 0x2708, set_test, own, (k + 4) & M16, pushes=((k + 4) & M16, own))        # 26E6-2703
        if R.al != 0:                                          # 2708 or al, al; je 2732
            player_byte(mem, R, seg, off, 0xF)                 # 270F-2725
            own = R.ax
            invoke(mem, R, CS, 0x272D, set_test, own, k, pushes=(k, own))      # 270C-2728
            R.local8(-1, R.al)                                 # 2730
            R.leave()
            R.store()
            return
    R.push(k)                                                  # 2732 push [bp+0xa]
    R.es, R.di = seg, off                                      # 2735
    invoke(mem, R, CS, 0x273E, c2974, seg, off, pushes=(seg, off))      # 2738-273B
    cbw(R)                                                     # 273E
    R.di = (R.ax << 1) & M16                                   # 273F-2741
    R.ax = mem.ds16(0x9B34 + R.di)                             # 2743: [di - 0x64cc]
    R.dx = 0xBF
    mul(R, 0xBF)                                               # 2747-274A
    coff, cseg = mem.farptr(mem.DS * 16 + COUNTRIES_PTR)       # 274C
    R.es, R.di = cseg, (coff + R.ax) & M16
    R.al = rec8(mem, cseg, R.di, 0x2D)                         # 2752
    R.ah = 0
    value = R.ax
    R.push(value)                                              # 2758
    R.push(mem.seg(CS))                                        # 2759 call far 0C57
    R.push(0x275E)
    set_test(mem, R, value, k)
    R.sp = sp_frame
    R.local8(-1, R.al)                                         # 275E
    R.leave()
    R.store()


@PORTS.port("0791:278A", ret="retf 6")
def skill_of_pitch_record(mem, variant):
    """278A(rec, element): the engines' only skill reader (runtime/model/keeping.py contest_value, T42, T40): form and
    energy blended, times 1771:3A06's skill (a guest call: T61), div 256, plus skill div 4, the table-controlled keeper
    extra (DS:769[element] or element 1 with DS:8327 in the set {3, 4}), a share of the manager at slot < 0xC."""
    off, seg, e = args(mem, 3)
    R = Regs(mem)
    R.enter(0xA)                                               # 278A-278F
    idx = rec16(mem, seg, off, 0xD)
    R.ax = idx
    R.dx = 0x14
    mul(R, 0x14)                                               # 2797-279A
    poff, pseg = mem.farptr(mem.DS * 16 + PLAYERS_PTR)
    pdi = (poff + R.ax) & M16                                  # 279C-27A0
    R.es, R.di = pseg, pdi
    R.local16(-0xA, pdi)                                       # 27A2
    R.local16(-8, pseg)                                        # 27A5
    form = rec8(mem, pseg, pdi, 0xC)
    if s8(form) >= 0x20:                                       # 27AB cmp byte [di+0xc], 0x20; jge 27C0
        R.ax = 0
        base = 0
    else:
        R.al = form                                            # 27B5
        cbw(R)
        R.ax = R.ax + 1                                        # 27BA inc ax
        base = R.ax
    R.local16(-4, base)                                        # 27BB / 27C2
    if e >= 0xC:                                               # 27C5 cmp [bp+0xa], 0xc; jb 27D1
        base = (base + 0x20) & M16                             # 27CB
    else:
        R.al = rec8(mem, pseg, pdi, 0xE)                       # 27D4
        cbw(R)
        base = (base + R.ax) & M16                             # 27D9
    R.local16(-4, base)
    R.es, R.di = seg, off                                      # 27DC
    R.store(stack=True)
    skill = yield call("1771:3A06", idx, e, ret_to="0791:27EB", far=True)      # 27DF-27E6 (T61's)
    R = Regs(mem, resumed=True)
    R.local16(-6, skill)                                       # 27EB
    R.es, R.di = seg, off                                      # 27EE
    if rec8(mem, seg, off, 0x13) != 0 and variant != "skill-no-halving":      # 27F1
        R.cx = 2
        R.dx = skill % 2                                       # 27FB-2800 div cx
        skill = skill // 2
        R.ax = skill
        R.local16(-6, skill)                                   # 2802
    R.cx = 4
    R.bx = skill // 4                                          # 2805-280F
    R.dx = skill % 4
    R.ax = base
    mul(R, skill)                                              # 2814
    R.dx = 0
    R.cx = 0x100                                               # 2817-2819
    lo = R.ax
    R.ax, R.dx = lo // 0x100, lo % 0x100                       # 281C
    R.ax = R.ax + R.bx                                         # 281E
    base = R.ax
    R.local16(-4, base)                                        # 2820
    R.di = e                                                   # 2823
    extra = mem.ds8((0x769 + e) & M16) != 0                    # 2826 cmp byte [di+0x769], 0; jne 2843
    if not extra and e == 1 and variant != "keeper-gate-off":  # 282D
        R.al = mem.ds8(0x8327)                                 # 2833
        el = R.al
        sp_frame = R.sp
        R.push(R.ax)                                           # 2836 push ax
        R.push(mem.seg(CS))                                    # 283A push cs
        R.push(CS_KEEPER_EVENTS)                               # 283B push di
        R.push(mem.seg(CS))                                    # 283C call far 08DF
        R.push(0x2841)
        R.sp = sp_frame
        member = (mem.u8(mem.addr(mem.seg(0x791), CS_KEEPER_EVENTS + (el >> 3))) >> (el & 7)) & 1     # -> 23E4:08DF
        R.bx = el >> 3
        R.cx = (R.cx & 0xFF00) | (el & 7)
        R.al = (1 << (el & 7)) & 0xFF
        R.es, R.di = mem.seg(0x791), CS_KEEPER_EVENTS
        extra = bool(member)                                   # 2841 je 284F
    if extra:                                                  # 2843
        R.es, R.di = seg, off
        R.al = rec8(mem, seg, off, 0x11)
        R.ah = 0
        base = (base + R.ax) & M16                             # 284C
        R.local16(-4, base)
    R.es, R.di = seg, off                                      # 284F
    if rec8(mem, seg, off, 6) < 0xC and mem.ds8(0x80FC) != 0:  # 2852-285E
        R.ax = base
        R.dx = 0
        R.cx = 0x10
        R.ax, R.dx = base // 0x10, base % 0x10                 # 2868
        base = (base + R.ax) & M16                             # 286A
        R.local16(-4, base)
    R.ax = base                                                # 286D
    R.local16(-2, base)                                        # 2870
    R.leave()
    R.store()


@PORTS.port("0791:287C", ret="retf 6")
def skill_draw_passes(mem, variant):
    """287C(rec, element): 1 with probability (n - 1) / n, n = 278A / 32 + 1 (214B:06D0 draws; 0 when it is 1)."""
    off, seg, e = args(mem, 3)
    R = Regs(mem)
    R.enter(2)                                                 # 287C-2881
    R.es, R.di = seg, off                                      # 2885
    R.store(stack=True)
    skill = yield call("0791:278A", e, seg, off, ret_to="0791:288E", far=True)     # 2882-288B
    R = Regs(mem, resumed=True)
    R.dx = skill % 0x20                                        # 288E-2893 div cx
    R.cx = 0x20
    n = (skill // 0x20 + 1) & M16                              # 2895
    R.ax = n
    invoke(mem, R, CS, 0x289C, draw_is_one, n, pushes=(n,))    # 2896-2897 -> 214B:06D0
    R.al = 0 if R.al != 0 else 1                               # 289C-28A6
    R.local8(-1, R.al)                                         # 28A6
    R.leave()
    R.store()


# -- the pitch records: whole-field loops ------------------------------------------------------------------------
@PORTS.port("0791:28B2", ret="ret 2")
def all_players_in_state(mem, variant):
    """28B2(state): 1 when each of the 22 pitch records has +0x12 = state, or is the ball slot or the second slot, or is a
    player 2956 reports unavailable."""
    state = args(mem, 1)[0] & 0xFF
    ds = mem.DS
    R = Regs(mem)
    R.enter(0xA)                                               # 28B2-28B7
    R.ax = 0                                                   # 28B8
    count = 0
    R.local16(-5, 0)                                           # 28BA
    R.local16(-3, 1)                                           # 28BD
    for i in range(1, 0x17):                                   # 28BD-290F
        if i > 1:
            R.local16(-3, i)                                   # 28C4 inc word ptr [bp-3]
        R.ax = i
        R.dx = 0x16
        mul(R, 0x16)                                           # 28C7-28CD
        rec = (R.ax + PITCH) & M16                             # 28CF-28D1
        R.di = rec
        R.local16(-9, rec)                                     # 28D5
        R.local16(-7, ds)                                      # 28D8
        R.es, R.di = ds, rec                                   # 28DB
        R.al = rec8(mem, ds, rec, 0x12)                        # 28DE
        counted = False
        if R.al == state:                                      # 28E2
            counted = True
        else:
            R.ax = mem.ds8(BALL_SLOT)                          # 28E7-28EA
            if R.ax == i:
                counted = True
            else:
                R.ax = mem.ds8(SECOND_SLOT)                    # 28F1-28F4
                if R.ax == i:
                    counted = True
                else:
                    R.es, R.di = ds, rec                       # 28FB
                    R.store(stack=True)
                    yield call("0791:2956", ds, rec, ret_to="0791:2904", far=True)       # 28FE-2901
                    R = Regs(mem, resumed=True)
                    counted = R.al != 0                        # 2904 or al, al; je 290B
        if counted:
            count += 1
            R.local16(-5, count)                               # 2908
    R.al = 1 if count == 0x16 else 0                           # 2911-291B
    R.local8(-1, R.al)                                         # 291D
    R.leave()
    R.store()


@PORTS.port("0791:2929", ret="ret 2")
def fill_pitch_state(mem, variant):
    """2929(value): +0x12 of each of the 22 pitch records := value."""
    value = args(mem, 1)[0] & 0xFF
    R = Regs(mem)
    R.enter(2)                                                 # 2929-292C
    R.local16(-2, 1)                                           # 292F
    R.cx = (R.cx & 0xFF00) | value                             # 2939
    for i in range(1, 0x17):                                   # 292F-294E
        R.ax = i
        R.dx = 0x16
        mul(R, 0x16)
        R.di = R.ax
        mem.wds8((0x80FA + i * 0x16) & M16, value, "0791:2946")
    R.local16(-2, 0x16)                                        # 2936 inc word ptr [bp-2] (22 times)
    R.leave()
    R.store()


@PORTS.port("0791:2956", ret="retf 4")
def player_unavailable_on_pitch(mem, variant):
    """2956(rec): 1771:3216 of the record's player (+0xD): 1 when he cannot play (T61's, a guest call)."""
    off, seg = args(mem, 2)
    R = Regs(mem)
    R.enter(2)                                                 # 2956-295B
    R.es, R.di = seg, off                                      # 295C
    R.store(stack=True)
    yield call("1771:3216", rec16(mem, seg, off, 0xD), ret_to="0791:2968", far=True)      # 295F-2963
    R = Regs(mem, resumed=True)
    R.local8(-1, R.al)                                         # 2968: AL as the callee left it
    R.leave()
    R.store()


@PORTS.port("0791:2996", ret="ret")
def ball_holder_is_side0(mem, variant):
    """2996: 1 when the ball slot DS:830B is below 0xC."""
    R = Regs(mem)
    c2996(mem, R)
    R.store()


@PORTS.port("0791:29B3", ret="ret")
def ball_holder_farther_flag(mem, variant):
    """29B3: DS:80FB := 1 when |y| of the ball-holder's record is at least |y| of the record at slot DS:668[2996 flag] + 1
    (the other side's first slot), else 0."""
    R = Regs(mem)
    R.enter(2)                                                 # 29B3-29B8
    invoke(mem, R, None, 0x29BC, c2996)                        # 29B9
    R.al = 0 if R.al != 0 else 1                               # 29BC-29C6
    cbw(R)
    R.di = R.ax
    R.al = mem.ds8(SIDE_BASES + R.di)                          # 29C9
    R.ah = 0
    R.ax = R.ax + 1                                            # 29CF
    R.dx = 0x16
    mul(R, 0x16)                                               # 29D0-29D3
    R.di = R.ax
    R.al = mem.ds8((0x80E9 + R.di) & M16)                      # 29D7: [di - 0x7f17]
    cbw(R)
    neg_if_negative(R)                                         # 29DC-29E0
    R.cx = R.ax
    R.al = mem.ds8(BALL_SLOT)                                  # 29E4
    R.ah = 0
    R.dx = 0x16
    mul(R, 0x16)                                               # 29E9-29EC
    R.di = R.ax
    R.al = mem.ds8((0x80E9 + R.di) & M16)                      # 29F0
    cbw(R)
    neg_if_negative(R)
    R.al = 1 if s16(R.ax) >= s16(R.cx) else 0                  # 29FB-2A03
    mem.wds8(0x80FB, R.al, "0791:2A05")
    R.local8(-1, R.al)                                         # 2A0B
    R.leave()
    R.store()


@PORTS.port("0791:2A15", ret="ret")
def advance_unavailable_ball_slot(mem, variant):
    """2A15: while the ball slot DS:830B is not 0 and its player is unavailable (2956), advance it by 1 inside its side's
    slots (214B:1D6F wraps it between DS:668[side] + 2 and + 0xB)."""
    ds = mem.DS
    R = Regs(mem)
    R.enter()                                                  # 2A15
    if mem.ds8(BALL_SLOT) == 0:                                # 2A18-2A1D
        R.leave()
        R.store()
        return
    while True:
        R.ax = mem.ds8(BALL_SLOT)                              # 2A1F-2A22
        R.dx = 0x16
        mul(R, 0x16)                                           # 2A24-2A27
        R.di = (R.ax + PITCH) & M16                            # 2A29-2A2B
        R.store(stack=True)
        yield call("0791:2956", ds, R.di, ret_to="0791:2A35", far=True)       # 2A2F-2A32
        R = Regs(mem, resumed=True)
        if R.al == 0:                                          # 2A35 or al, al; je 2A69
            return
        sp_frame = R.sp
        R.di = BALL_SLOT                                       # 2A39
        R.push(ds)                                             # 2A3C push ds
        R.push(BALL_SLOT)                                      # 2A3D push di
        invoke(mem, R, None, 0x2A41, c2996)                    # 2A3E
        cbw(R)
        R.di = R.ax
        R.al = mem.ds8(SIDE_BASES + R.di)
        R.ah = 0
        R.ax = R.ax + 2                                        # 2A4A
        lo = R.ax
        R.push(lo)                                             # 2A4D
        invoke(mem, R, None, 0x2A51, c2996)                    # 2A4E
        cbw(R)
        R.di = R.ax
        R.al = mem.ds8(SIDE_BASES + R.di)
        R.ah = 0
        R.ax = R.ax + 0xB                                      # 2A5A
        hi = R.ax
        R.push(hi)                                             # 2A5D
        R.ax = 1                                               # 2A5E
        R.push(1)                                              # 2A61
        R.push(mem.seg(CS))                                    # 2A62 call far 1D6F
        R.push(0x2A67)
        wrap_add_byte(mem, R, BALL_SLOT, ds, lo, hi, 1)
        R.sp = sp_frame
        R.store()


@PORTS.port("0791:2A6D", ret="ret")
def second_slot_in_side(mem, variant):
    """2A6D: slot_in_side (2BB1) of the record at slot DS:830C, or 0 when that is 0."""
    R = Regs(mem)
    c2a6d(mem, R, variant)
    R.store()


# -- the commentary wrappers: the emitter 1EB5 is still the original's (T69) -------------------------------------------
@PORTS.port("0791:2AA3", ret="ret 2")
def commentary_with_ball_slot(mem, variant):
    """2AA3(code): 1EB5(ball slot's side, its slot in side, 2A6D, code)."""
    code, = args(mem, 1)
    ds = mem.DS
    R = Regs(mem)
    R.enter()                                                  # 2AA3-2AA5
    sp_frame = R.sp
    invoke(mem, R, None, 0x2AA9, c2996)                        # 2AA6
    a1 = R.ax
    R.push(a1)                                                 # 2AA9
    R.ax = mem.ds8(BALL_SLOT)                                  # 2AAA-2AAD
    R.dx = 0x16
    mul(R, 0x16)                                               # 2AAF
    R.di = (R.ax + PITCH) & M16
    invoke(mem, R, CS, 0x2AC0, c2bb1, ds, R.di, variant, pushes=(ds, R.di))        # 2ABA-2ABD
    R.ah = 0                                                   # 2AC0
    a2 = R.ax
    R.push(a2)                                                 # 2AC2
    invoke(mem, R, None, 0x2AC6, c2a6d, variant)               # 2AC3
    a3 = R.ax
    R.push(a3)                                                 # 2AC6
    R.al = code & 0xFF                                         # 2AC7
    a4 = R.ax
    R.push(a4)                                                 # 2ACA
    R.sp = sp_frame                                            # the guest call pushes them again, at the same places
    R.store(stack=True)
    yield call("0791:1EB5", a1, a2, a3, a4, ret_to="0791:2ACE", far=False)       # 2ACB


@PORTS.port("0791:2AD4", ret="ret 2")
def commentary_with_both_slots(mem, variant):
    """2AD4(code): 1EB5(DS:830C below 0xC, 2A6D, ball slot's slot in side, code)."""
    code, = args(mem, 1)
    ds = mem.DS
    R = Regs(mem)
    R.enter()                                                  # 2AD4-2AD6
    sp_frame = R.sp
    R.al = 1 if mem.ds8(SECOND_SLOT) < 0xC else 0              # 2AD7-2AE2
    b1 = R.ax
    R.push(b1)                                                 # 2AE4
    invoke(mem, R, None, 0x2AE8, c2a6d, variant)               # 2AE5
    b2 = R.ax
    R.push(b2)                                                 # 2AE8
    R.ax = mem.ds8(BALL_SLOT)                                  # 2AE9
    R.dx = 0x16
    mul(R, 0x16)
    R.di = (R.ax + PITCH) & M16
    invoke(mem, R, CS, 0x2AFF, c2bb1, ds, R.di, variant, pushes=(ds, R.di))        # 2AF9-2AFC
    R.ah = 0                                                   # 2AFF
    b3 = R.ax
    R.push(b3)                                                 # 2B01
    R.al = code & 0xFF                                         # 2B02
    b4 = R.ax
    R.push(b4)                                                 # 2B05
    R.sp = sp_frame
    R.store(stack=True)
    yield call("0791:1EB5", b1, b2, b3, b4, ret_to="0791:2B09", far=False)       # 2B06


@PORTS.port("0791:2B0F", ret="ret 2")
def commentary_plain(mem, variant):
    """2B0F(code): 1EB5(1, 0, 0, code)."""
    code, = args(mem, 1)
    R = Regs(mem)
    R.enter()                                                  # 2B0F-2B11
    R.al = 1                                                   # 2B12
    w1 = R.ax
    R.ax = 0                                                   # 2B15-2B1A
    R.al = code & 0xFF                                         # 2B1B
    w4 = R.ax
    R.store(stack=True)
    yield call("0791:1EB5", w1, 0, 0, w4, ret_to="0791:2B22", far=False)       # 2B1F


@PORTS.port("0791:2B28", ret="retf 6")
def commentary_for_record(mem, variant):
    """2B28(rec, code): 1EB5(2974(rec), 2BB1(rec), 0, code)."""
    off, seg, code = args(mem, 3)
    R = Regs(mem)
    R.enter()                                                  # 2B28-2B2A
    sp_frame = R.sp
    R.es, R.di = seg, off                                      # 2B2B
    invoke(mem, R, CS, 0x2B34, c2974, seg, off, pushes=(seg, off))      # 2B2E-2B31
    c1 = R.ax
    R.push(c1)                                                 # 2B34
    R.es, R.di = seg, off
    invoke(mem, R, CS, 0x2B3E, c2bb1, seg, off, variant, pushes=(seg, off))        # 2B38-2B3B
    R.ah = 0                                                   # 2B3E
    c2 = R.ax
    R.push(c2)                                                 # 2B40
    R.ax = 0                                                   # 2B41
    R.push(0)                                                  # 2B43
    R.al = code & 0xFF                                         # 2B44
    R.push(R.ax)                                               # 2B47
    w4 = R.ax
    R.sp = sp_frame
    R.store(stack=True)
    yield call("0791:1EB5", c1, c2, 0, w4, ret_to="0791:2B4B", far=False)       # 2B48


# -- the queries on one record -----------------------------------------------------------------------------------
@PORTS.port("0791:2B51", ret="retf 4")
def slot_is_on_ball_side(mem, variant):
    """2B51(rec): 2996 = 2974(rec)."""
    off, seg = args(mem, 2)
    R = Regs(mem)
    R.enter(2)                                                 # 2B51-2B56
    invoke(mem, R, None, 0x2B5A, c2996)                        # 2B57
    side = R.ax
    R.push(side)                                               # 2B5A push ax
    R.es, R.di = seg, off                                      # 2B5B
    invoke(mem, R, CS, 0x2B64, c2974, seg, off, pushes=(seg, off))      # 2B5E-2B61
    R.dx = side                                                # 2B64 pop dx
    R.sp = R.sp + 2
    R.al = 1 if R.al == (R.dx & 0xFF) else 0                   # 2B65-2B6D
    R.local8(-1, R.al)                                         # 2B6F
    R.leave()
    R.store()


@PORTS.port("0791:2B7B", ret="retf 4")
def energy_gate_chance(mem, variant):
    """2B7B(rec): 214B:06D0(0x21 - signed energy +0xE of the record's player)."""
    off, seg = args(mem, 2)
    R = Regs(mem)
    R.enter(2)                                                 # 2B7B-2B80
    player_byte(mem, R, seg, off, 0xE)                         # 2B81-2B93
    cbw(R)                                                     # 2B97
    R.dx = R.ax                                                # 2B98
    R.ax = 0x20 if variant == "energy-gate-32" else 0x21       # 2B9A
    R.ax = R.ax - R.dx                                         # 2B9D
    n = R.ax
    invoke(mem, R, CS, 0x2BA5, draw_is_one, n, pushes=(n,))    # 2B9F-2BA0 -> 214B:06D0
    R.local8(-1, R.al)                                         # 2BA5
    R.leave()
    R.store()


@PORTS.port("0791:2BB1", ret="retf 4")
def slot_in_side(mem, variant):
    """2BB1(rec): +6 - 0xB for slots above 0xB, else +6."""
    off, seg = args(mem, 2)
    R = Regs(mem)
    c2bb1(mem, R, seg, off, variant)
    R.store()


@PORTS.port("0791:2C29", ret="retf 4")
def slot_is_idle_ball_slot(mem, variant):
    """2C29(rec): 1 when the record's slot is the ball slot DS:830B and DS:8302 is 0."""
    off, seg = args(mem, 2)
    R = Regs(mem)
    R.enter(2)                                                 # 2C29-2C2E
    R.al = mem.ds8(BALL_SLOT)                                  # 2C2F
    R.es, R.di = seg, off                                      # 2C32
    R.al = 1 if R.al == rec8(mem, seg, off, 6) and mem.ds8(0x8302) == 0 else 0     # 2C35-2C46
    R.local8(-1, R.al)                                         # 2C48
    R.leave()
    R.store()


@PORTS.port("0791:2C54", ret="retf 4")
def in_own_half(mem, variant):
    """2C54(rec): 1 when y * attack_direction < 0."""
    off, seg = args(mem, 2)
    R = Regs(mem)
    c2c54(mem, R, seg, off, variant)
    R.store()


@PORTS.port("0791:2C86", ret="retf 6")
def mirror_to_team_frame(mem, variant):
    """2C86(rec, word): both bytes of the word (x low, y high, in the argument itself) times the attack direction."""
    off, seg, word = args(mem, 3)
    sp = entry_sp(mem)
    R = Regs(mem)
    R.enter(2)                                                 # 2C86-2C8B
    direction_in_dx(mem, R, seg, off, 0x2C95)                  # 2C8C-2C96
    R.al = word >> 8                                           # 2C98
    cbw(R)
    imul(R, R.dx)                                              # 2C9C
    y = R.al
    mem.w8(mem.ss_lin(sp + 9), y, "0791:2C9E")                 # 2C9E mov [bp+0xb], al
    direction_in_dx(mem, R, seg, off, 0x2CAA)                  # 2CA1-2CAB
    R.al = word & 0xFF                                         # 2CAD
    cbw(R)
    imul(R, R.dx)                                              # 2CB1
    x = R.al
    mem.w8(mem.ss_lin(sp + 8), x, "0791:2CB3")                 # 2CB3 mov [bp+0xa], al
    R.ax = (y << 8) | x                                        # 2CB6
    R.local16(-2, R.ax)                                        # 2CB9
    R.leave()
    R.store()


@PORTS.port("0791:2CEC", ret="retf 4")
def player_at_ball(mem, variant):
    """2CEC(rec): the record's position word equals the ball word DS:82F6."""
    off, seg = args(mem, 2)
    R = Regs(mem)
    R.enter(2)                                                 # 2CEC-2CF1
    R.es, R.di = seg, off                                      # 2CF2
    R.ax = rec16(mem, seg, off, 0)                             # 2CF5
    R.al = 1 if R.ax == mem.ds16(BALL_X_Y) else 0              # 2CF8-2D02
    R.local8(-1, R.al)                                         # 2D04
    R.leave()
    R.store()


@PORTS.port("0791:2D10", ret="retf 6")
def ball_ahead_of_by(mem, variant):
    """2D10(rec, n): the ball's y * direction (from the low word, signed) > the record's y * direction + n (n unsigned),
    as a 32-bit compare: the high words signed, then the low words unsigned."""
    off, seg, n = args(mem, 3)
    R = Regs(mem)
    R.enter(2)                                                 # 2D10-2D15
    direction_in_dx(mem, R, seg, off, 0x2D1F)                  # 2D16-2D20
    R.es, R.di = seg, off                                      # 2D22
    R.al = rec8(mem, seg, off, 1)                              # 2D25
    cbw(R)
    imul(R, R.dx)                                              # 2D2A
    cwd(R)                                                     # 2D2C cdq
    R.cx, R.bx = R.ax, R.dx                                    # 2D2D-2D2F
    R.ax = n                                                   # 2D31
    R.dx = 0
    total = R.ax + R.cx + ((R.dx + R.bx) << 16)                # 2D36-2D38 add ax, cx; adc dx, bx
    R.ax, R.dx = total & M16, (total >> 16) & M16
    hi_t, lo_t = R.dx, R.ax
    R.push(hi_t)                                               # 2D3A push dx
    R.push(lo_t)                                               # 2D3B push ax
    direction_in_dx(mem, R, seg, off, 0x2D45)                  # 2D3C-2D46
    R.al = mem.ds8(0x82F7)                                     # 2D48
    cbw(R)
    imul(R, R.dx)                                              # 2D4C
    cwd(R)                                                     # 2D4E
    R.cx, R.bx = lo_t, hi_t                                    # 2D4F-2D50 pop cx; pop bx
    R.sp = R.sp + 4
    if s16(R.dx) > s16(R.bx):                                  # 2D51 cmp dx, bx; jg 2D5F
        ahead = True
    elif s16(R.dx) < s16(R.bx):                                # 2D55 jl 2D5B
        ahead = False
    elif variant == "ahead-inclusive":
        ahead = R.ax >= R.cx
    else:
        ahead = R.ax > R.cx                                    # 2D57 cmp ax, cx; ja 2D5F
    R.al = 1 if ahead else 0
    R.local8(-1, R.al)                                         # 2D61
    R.leave()
    R.store()


@PORTS.port("0791:2D6D", ret="retf 6")
def ahead_of_ball_by(mem, variant):
    """2D6D(rec, n): the record's y * direction > the ball's y * direction + n (n unsigned), the same 32-bit compare."""
    off, seg, n = args(mem, 3)
    R = Regs(mem)
    R.enter(2)                                                 # 2D6D-2D72
    direction_in_dx(mem, R, seg, off, 0x2D7C)                  # 2D73-2D7D
    R.es, R.di = seg, off                                      # 2D7F
    R.al = rec8(mem, seg, off, 1)                              # 2D82
    cbw(R)
    imul(R, R.dx)                                              # 2D87
    cwd(R)                                                     # 2D89
    a_lo, a_hi = R.ax, R.dx
    R.push(a_hi)                                               # 2D8A push dx
    R.push(a_lo)                                               # 2D8B push ax
    direction_in_dx(mem, R, seg, off, 0x2D95)                  # 2D8C-2D96
    R.al = mem.ds8(0x82F7)                                     # 2D98
    cbw(R)
    imul(R, R.dx)                                              # 2D9C
    cwd(R)                                                     # 2D9E
    R.cx, R.bx = R.ax, R.dx                                    # 2D9F-2DA1
    R.ax = n                                                   # 2DA3
    R.dx = 0
    total = R.ax + R.cx + ((R.dx + R.bx) << 16)                # 2DA8-2DAA
    R.ax, R.dx = total & M16, (total >> 16) & M16
    R.cx, R.bx = a_lo, a_hi                                    # 2DAC-2DAD pop cx; pop bx
    R.sp = R.sp + 4
    if s16(R.dx) < s16(R.bx):                                  # 2DAE cmp dx, bx; jl 2DBC
        before = True
    elif s16(R.dx) > s16(R.bx):                                # 2DB2 jg 2DB8
        before = False
    else:
        before = R.ax < R.cx                                   # 2DB4 cmp ax, cx; jb 2DBC
    R.al = 1 if before else 0
    R.local8(-1, R.al)                                         # 2DBE
    R.leave()
    R.store()


@PORTS.port("0791:2E00", ret="ret 2")
def on_pitch_wide(mem, variant):
    """2E00(word): |x| <= 9 and |y| <= 0x27 (x the low byte, y the high byte)."""
    word, = args(mem, 1)
    R = Regs(mem)
    R.enter(2)                                                 # 2E00-2E05
    R.al = word & 0xFF                                         # 2E06
    cbw(R)
    neg_if_negative(R)
    if s16(R.ax) > 9:                                          # 2E10 cmp ax, 9; jg 2E24
        R.al = 0
    else:
        R.al = word >> 8                                       # 2E15
        cbw(R)
        neg_if_negative(R)
        R.al = 1 if s16(R.ax) <= 0x27 else 0                   # 2E1F cmp ax, 0x27; jle 2E28
    R.local8(-1, R.al)                                         # 2E2A
    R.leave()
    R.store()


@PORTS.port("0791:2E36", ret="retf 6")
def in_own_goal_area(mem, variant):
    """2E36(rec, word): y * direction < 0, |y| >= 0x21 and |x| <= 2 (the word: x low byte, y high byte)."""
    off, seg, word = args(mem, 3)
    R = Regs(mem)
    R.enter(2)                                                 # 2E36-2E3B
    direction_in_dx(mem, R, seg, off, 0x2E45)                  # 2E3C-2E46
    R.al = word >> 8                                           # 2E48
    cbw(R)
    imul(R, R.dx)                                              # 2E4C
    if not R.ax & 0x8000:                                      # 2E4E or ax, ax; jge 2E70
        R.al = 0
    else:
        R.al = word >> 8                                       # 2E52
        cbw(R)
        neg_if_negative(R)
        if s16(R.ax) < 0x21:                                   # 2E5C cmp ax, 0x21; jl 2E70
            R.al = 0
        else:
            R.al = word & 0xFF                                 # 2E61
            cbw(R)
            neg_if_negative(R)
            R.al = 1 if s16(R.ax) <= 2 else 0                  # 2E6B cmp ax, 2; jle 2E74
    R.local8(-1, R.al)                                         # 2E76
    R.leave()
    R.store()


@PORTS.port("0791:2E82", ret="ret 2")
def in_penalty_strip(mem, variant):
    """2E82(word): |y| >= 0x19 and |x| <= 5."""
    R = Regs(mem)
    c2e82(mem, R, args(mem, 1)[0], variant)
    R.store()


@PORTS.port("0791:2EB8", ret="retf 6")
def in_own_goal_strip(mem, variant):
    """2EB8(rec, word): y * direction < 0 and 2E82(word)."""
    off, seg, word = args(mem, 3)
    R = Regs(mem)
    R.enter(2)                                                 # 2EB8-2EBD
    direction_in_dx(mem, R, seg, off, 0x2EC7)                  # 2EBE-2EC8
    R.al = word >> 8                                           # 2ECA
    cbw(R)
    imul(R, R.dx)                                              # 2ECE
    if not R.ax & 0x8000:                                      # 2ED0 or ax, ax; jge 2EDE
        R.al = 0
    else:
        invoke(mem, R, None, 0x2EDA, c2e82, word, variant, pushes=(word,))      # 2ED4-2ED7
        R.al = 1 if R.al != 0 else 0                           # 2EDA-2EE2
    R.local8(-1, R.al)                                         # 2EE4
    R.leave()
    R.store()


@PORTS.port("0791:2EF0", ret="retf 6")
def in_opposing_goal_strip(mem, variant):
    """2EF0(rec, word): y * direction > 0 and 2E82(word)."""
    off, seg, word = args(mem, 3)
    R = Regs(mem)
    R.enter(2)                                                 # 2EF0-2EF5
    direction_in_dx(mem, R, seg, off, 0x2EFF)                  # 2EF6-2F00
    R.al = word >> 8                                           # 2F02
    cbw(R)
    imul(R, R.dx)                                              # 2F06
    if s16(R.ax) <= 0:                                         # 2F08 or ax, ax; jle 2F16
        R.al = 0
    else:
        invoke(mem, R, None, 0x2F12, c2e82, word, variant, pushes=(word,))      # 2F0C-2F0F
        R.al = 1 if R.al != 0 else 0                           # 2F12-2F1A
    R.local8(-1, R.al)                                         # 2F1C
    R.leave()
    R.store()


@PORTS.port("0791:2F28", ret="retf 4")
def in_attack_zone(mem, variant):
    """2F28(rec): not in the own half (2C54), |y| >= the player's +6 + 0xC, and |x| <= DS:776[|y| > 0x1C]."""
    off, seg = args(mem, 2)
    R = Regs(mem)
    R.enter(2)                                                 # 2F28-2F2D
    R.es, R.di = seg, off                                      # 2F2E
    invoke(mem, R, CS, 0x2F37, c2c54, seg, off, variant, pushes=(seg, off))      # 2F31-2F34
    if R.al != 0:                                              # 2F37-2F39
        R.al = 0
    else:
        player_byte(mem, R, seg, off, 6)                       # 2F3B-2F4D
        R.ax = R.ax + 0xC                                      # 2F53
        R.dx = R.ax
        R.es, R.di = seg, off                                  # 2F58
        R.al = rec8(mem, seg, off, 1)                          # 2F5B
        cbw(R)
        neg_if_negative(R)
        if s16(R.ax) < s16(R.dx):                              # 2F66 cmp ax, dx; jl 2F9F
            R.al = 0
        else:
            R.es, R.di = seg, off                              # 2F6A
            R.al = rec8(mem, seg, off, 1)                      # 2F6D
            cbw(R)
            neg_if_negative(R)
            R.al = 1 if s16(R.ax) > 0x1C else 0                # 2F78-2F81
            cbw(R)                                             # 2F83
            R.di = R.ax
            R.al = mem.ds8((0x776 + R.di) & M16)               # 2F86
            R.ah = 0
            R.dx = R.ax
            R.es, R.di = seg, off                              # 2F8E
            R.al = rec8(mem, seg, off, 0)                      # 2F91
            cbw(R)
            neg_if_negative(R)
            R.al = 1 if s16(R.ax) <= s16(R.dx) else 0          # 2F9B-2FA3
    R.local8(-1, R.al)                                         # 2FA5
    R.leave()
    R.store()
