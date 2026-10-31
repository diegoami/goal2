"""Ball and player motion, the offside line and the referee (T62, match-engine-plan step P2a): row T62's eleven
routines, memory-faithful, from the listing static/goal-exe/code/seg_0791_14.asm (835F-8CC7) and seg_0791_15.asm
(8CCA-92F9); the line comments are its offsets.

    0791:835F ball_travel        retf 4   (|+6| + |+8|) * +0xA, a long through 23E4:0279
    0791:83A2 move_ball          retf 4   the ball's step, its flight flag, and the dead-ball dispatch off the pitch
    0791:8537                    retf 4   a player's sprite moved in the picture, and the ball with its holder
    0791:869F                    retf 4   possession taken: DS:830B := the record's slot, the play bytes cleared
    0791:8AE9 update_player      retf 4   a player's tick: its state's handler, the run step 8889, possession, 8537
    0791:8C67                    ret 4    a nested procedure of 8CCA (its BP, a side byte): an offside line reset
    0791:8CCA                    ret      both lines reset and the four bytes DS:82EE..82F5
    0791:8CF5 track_offside_line ret      each side's line at its deepest outfield player, and its marker moved
    0791:8E24                    retf 4   a sprite moved in the picture: the old cell restored from the background
    0791:90C5                    retf 8   an offside marker placed (DS:8304) and drawn
    0791:9119 move_referee       retf 6   the referee's step towards the ball, blocked by the set DS:0648

The pitch picture's characters and attributes (the far pointer DS:7C16; its background DS:7C1E) are the occupancy grid
the move test 86D0 reads (E032 notes, "Why 8537 and 8E24 stay"): every write to it is kept, named as the listing's.

Every callee outside the row stays the original's and is called as the listing calls it, with its return address
(port/guest.py): 23E4:0279 (registers DX:AX * BX:CX), 2E00 (ret 2), 8F10 draw_ball (retf 4), 2DCA (ret 2), 0441 the
whistle (ret 2), 2BE5 (retf 4, by `push cs; call near`), 82EB, 690C, 698E, 6E11, 6E6E, 2996 (ret), 6F01 (ret 4), 2C29
(retf 4), 045D (ret 2), 2EB8 (retf 6), the state handlers of 8AE9 (57AC, 58E1, 69BD, 6AAD, 6AF7, 6240, 7069, 7287,
715A, 73BA, 7621: retf 4), 8889 (ret 2, 8AE9's BP), 2CEC (retf 4), 2AD4 (ret 2), 214B:06B1 (retf 2), 214B:0D1C and
0D56 (retf 8), 214B:2031 (retf 8) and 23E4:08DF (retf 6; the answer in ZF). A routine of the row calls another of the
row the same way, so its port runs there and is counted. Guest-call inputs follow the listing; BX, CX, SI, DI and ES
are scratch. On three referee paths the incoming AX of the nested port 8E24 differs from the listing; 8E24 never
reads that incoming value and sets AX and DX before returning. No claim of identical unused entry registers is made.
The locals of a frame are not written (the dead frame); each port that calls builds the listing's frame (mem.enter) so
every callee runs at the original's SP. The module holds no byte of the original."""
from .guest import call
from .mem import s8, s16
from . import Registry

PORTS = Registry("motion", "ball and player motion, the offside line and the referee (row T62)")
PORTS.variant("no-draw", "8537's draw of the player's sprite at its new cell (85BB-8602) skipped: the picture")
PORTS.variant("offside-max", "8CF5's jge at 8D92 read as jle: the line taken at the most advanced player")
PORTS.variant("referee-still", "9119's step towards its target and its blocking test (9249-92EA) skipped")

PICTURE, BACKGROUND = 0x7C16, 0x7C1E   # far pointers: the pitch picture and its background copy (E032 notes)
CELL = 0x90E                           # es:[di + 0x90e] of every cell access (8577, 859D, 8602, 8E57, 92CE ...)
NO_POSITION = 0x640                    # the word 8537 tests a position against (8541, 85B5)
DIRECTIONS = 0x7920                    # the two signed steps -1 and +1 by a 0/1 index (90E6, 9154, 9177 ...)
LINES = 0x82E2                         # the two offside lines, 6 bytes each from DS:82E2 (8C7B, 8D12)
SIDE_BASE = 0x668                      # the first slot - 1 of each side (8C8B, 8D2A)
RECORDS, RECORD = 0x80E8, 0x16         # the pitch record of slot s at DS:80E8 + 0x16 s (8C99, 8D38)
BLOCKERS = 0x648                       # the set of characters that block a step (92D4; 86D0's too)
HANDLERS = {                           # 8AE9's dispatch on the state byte +0x12 (8B0E-8BB0): callee, return address
    0x05: ("0791:57AC", "0791:8B1B"), 0x0D: ("0791:58E1", "0791:8B2B"), 0x01: ("0791:69BD", "0791:8B3B"),
    0x02: ("0791:6AAD", "0791:8B4A"), 0x03: ("0791:6AF7", "0791:8B59"), 0x06: ("0791:6240", "0791:8B68"),
    0x07: ("0791:7069", "0791:8B77"), 0x08: ("0791:7287", "0791:8B86"), 0x09: ("0791:715A", "0791:8B95"),
    0x0A: ("0791:73BA", "0791:8BA4"), 0x0B: ("0791:7621", "0791:8BB3")}


# -- the arithmetic the listing does on AX and DX -------------------------------------------------------------------
def cbw(al):
    """98 (cbw in 16-bit code; the listing writes `cwde`)."""
    al &= 0xFF
    return al | 0xFF00 if al & 0x80 else al


def cwd(ax):
    """99 (cwd; the listing writes `cdq`): DX."""
    return 0xFFFF if ax & 0x8000 else 0


def absw(ax):
    """`or ax, ax; jns; neg ax`."""
    ax &= 0xFFFF
    return (-ax) & 0xFFFF if ax & 0x8000 else ax


def mul(a, b):
    """`mul` (unsigned 16 x 16): (AX, DX)."""
    p = (a & 0xFFFF) * (b & 0xFFFF)
    return p & 0xFFFF, p >> 16


def imul(a, b):
    """`imul` (signed 16 x 16): (AX, DX)."""
    p = s16(a & 0xFFFF) * s16(b & 0xFFFF)
    return p & 0xFFFF, (p >> 16) & 0xFFFF


def lo(ax, al):
    """`mov al, ...`: AH kept."""
    return (ax & 0xFF00) | (al & 0xFF)


def regs(mem, ax, dx=None):
    mem.set_reg("ax", ax & 0xFFFF)
    if dx is not None:
        mem.set_reg("dx", dx & 0xFFFF)


def record(mem, frame, off=6):
    """`les di, ptr [bp + off]`: (offset, segment, linear) of the far pointer argument."""
    o, s = mem.farptr(frame.lin(off))
    return o, s, mem.addr(s, o)


def cell(mem, ptr, row, col):
    """The linear address of the cell (row, col) of the picture DS:ptr points to: `mov al, row; cbw; mov dx, 0xa0;
    mul dx; les di, ptr [ptr]; add di, ax; add di, (cbw col) * 2`, then es:[di + 0x90e]."""
    boff, bseg = mem.farptr(mem.DS * 16 + ptr)
    di = (boff + mul(cbw(row), 0xA0)[0] + ((cbw(col) << 1) & 0xFFFF)) & 0xFFFF
    return mem.addr(bseg, di + CELL)


def cell_mul(row):
    """AX and DX the cell address computation leaves (the `mul dx`)."""
    return mul(cbw(row), 0xA0)


def slot_record(slot):
    """`xor ah, ah; mov dx, 0x16; mul dx; mov di, ax; add di, 0x80e8`: (DI, AX, DX)."""
    ax, dx = mul(slot, RECORD)
    return (ax + RECORDS) & 0xFFFF, ax, dx


def push(mem, at, *words):
    """The listing's pushes made ahead of a call that leaves them on the stack (91C6-91C7, 91EB-91EC)."""
    sp = mem.reg("sp")
    for w in words:
        sp = (sp - 2) & 0xFFFF
        mem.w16(mem.ss_lin(sp), w, at)
    mem.set_reg("sp", sp)


def pop(mem, n):
    mem.set_reg("sp", (mem.reg("sp") + 2 * n) & 0xFFFF)


# -- 835F --------------------------------------------------------------------------------------------------------
@PORTS.port("0791:835F", ret="retf 4")                     # 839F retf 4
def ball_travel(mem, variant):
    f = mem.enter(2, "0791:835F")                         # 835F-8362
    _, _, rec = record(mem, f)
    a = absw(mem.u16(rec + 6))                            # 8365-8370
    b = absw(mem.u16(rec + 8))                            # 8374-837F
    s = (a + b) & 0xFFFF                                  # 8381 add ax, dx
    mem.set_reg("cx", s)                                  # 8383-8386 cwd; mov cx, ax; mov bx, dx
    mem.set_reg("bx", cwd(s))
    regs(mem, mem.u16(rec + 0xA), 0)                      # 8388-838F mov ax, es:[di + 0xa]; xor dx, dx
    ax = yield call("23E4:0279", ret_to="0791:8396", far=True)      # 8391 call far: DX:AX * BX:CX
    return ax                                             # 8396-8399 via [bp - 2]; DX the product's high word


# -- 83A2 --------------------------------------------------------------------------------------------------------
def _toward_own_half(mem, rec, ret_to):
    """845A/84AD/84F6: the side of the holder's slot DS:830B by 2BE5, times the ball's row +1, signed: (AX, DX)."""
    di, ax, dx = slot_record(mem.ds8(0x830B))
    regs(mem, ax, dx)
    mem.set_reg("di", di)
    ax = yield call("0791:2BE5", mem.reg("ds"), di, ret_to=ret_to, far=True)   # push ds; push di; push cs
    return imul(cbw(mem.u8(rec + 1)), cbw(ax))            # cbw; mov dx, ax; mov al, es:[di + 1]; cbw; imul dx


@PORTS.port("0791:83A2", ret="retf 4")                     # 8534 retf 4
def move_ball(mem, variant):
    f = mem.enter(4, "0791:83A2")                         # 83A2-83A5
    off, seg, rec = record(mem, f)
    pos = mem.u16(rec)                                    # 83AB-83AE [bp - 2]
    pos = (pos & 0xFF00) | ((pos + mem.u8(rec + 6)) & 0xFF)                  # 83B4-83B8 add byte [bp - 2]
    pos = (pos & 0x00FF) | ((((pos >> 8) + mem.u8(rec + 8)) & 0xFF) << 8)    # 83BE-83C2 add byte [bp - 1]
    ax = lo(mem.u16(rec), mem.u8(rec + 8))
    if mem.u16(rec + 0xA) != 0:                           # 83C8 cmp word, 0; jbe
        mem.w16(rec + 0xA, mem.u16(rec + 0xA) - 1, "0791:83D2")
    flag = 0
    if mem.u8(rec + 0xD) != 0:                            # 83D9 cmp byte +0xd, 0; je 83EE
        regs(mem, ax)
        ax = yield call("0791:835F", seg, off, ret_to="0791:83E9", far=True)
        flag = 1 if ax > 2 else 0                         # 83E9 cmp ax, 2; ja 83F2
    ax = lo(ax, flag)
    mem.w8(rec + 0xD, flag, "0791:83F7")                  # 83F4-83F7 the ball in flight
    regs(mem, ax)
    ax = yield call("0791:2E00", pos, ret_to="0791:8401", far=False)        # 83FB-83FE
    if ax & 0xFF:                                         # 8401 or al, al; je 840E
        ax = pos
        mem.w16(rec, pos, "0791:840B")                    # 8405-840B the ball's new position
    regs(mem, ax)
    yield call("0791:8F10", seg, off, ret_to="0791:8417", far=True)         # 840E-8414 draw_ball
    ax = yield call("0791:2DCA", mem.u16(rec), ret_to="0791:8420", far=False)  # 8417-841D
    if ax & 0xFF:                                         # 8420-8424: on the pitch, done
        return None                                       # AX, DX as 2DCA left them
    regs(mem, 2)
    yield call("0791:0441", 2, ret_to="0791:842E", far=False)              # 8427-842B the whistle
    if mem.ds8(0x830E) != 0:                              # 842E cmp byte [0x830e], 0; jbe 8474
        ax = absw(cbw(mem.u8(rec)))                       # 8435-8440
        stop = s16(ax) > 1                                # 8442 cmp ax, 1; jg 846E
        if not stop:
            ax, dx = yield from _toward_own_half(mem, rec, "0791:845D")
            stop = s16(ax) < 0                            # 846A or ax, ax; jge 8474
            regs(mem, ax, dx)
        else:
            regs(mem, ax)
        if stop:
            yield call("0791:82EB", ret_to="0791:8471", far=False)          # 846E
            return None                                   # 8471 jmp 8531
    mem.wds8(0x830C, 0, "0791:8474")
    mem.wds8(0x830A, 0, "0791:8479")
    mem.wds8(0x830D, 0, "0791:847E")
    mem.wds8(0x8325, 0, "0791:8483")
    ax = absw(cbw(mem.u8(rec)))                           # 8488-8493
    if s16(ax) <= 1:                                      # 8495 cmp ax, 1; jg 84CB
        ax, dx = yield from _toward_own_half(mem, rec, "0791:84B0")
        regs(mem, ax, dx)
        if s16(ax) < 0:                                   # 84BD or ax, ax; jge 84C6
            yield call("0791:698E", ret_to="0791:84C4", far=False)
        else:
            yield call("0791:690C", ret_to="0791:84C9", far=False)
    else:
        ax = absw(cbw(mem.u8(rec + 1)))                   # 84CB-84D7
        if s16(ax) < 0x26:                                # 84D9 cmp ax, 0x26; jge 84E3
            regs(mem, ax)
            yield call("0791:6E11", ret_to="0791:84E1", far=False)          # the throw-in
        else:
            ax, dx = yield from _toward_own_half(mem, rec, "0791:84F9")
            regs(mem, ax, dx)
            if s16(ax) < 0:                               # 8506 or ax, ax; jge 850F
                yield call("0791:6E6E", ret_to="0791:850D", far=False)      # the corner
            else:
                ax = yield call("0791:2996", ret_to="0791:8512", far=False)
                side = 0 if ax & 0xFF else 1              # 8512-851A
                first = lo(ax, side)                      # 851C push ax
                second = lo(ax, 0)                        # 851D-851F mov al, 0; push ax
                regs(mem, second)
                yield call("0791:6F01", first, second, ret_to="0791:8523", far=False)
    mem.w16(rec + 0xA, 0, "0791:8528")                    # 8523-8528 xor ax, ax; mov es:[di + 0xa], ax
    mem.wds8(0x8327, 0, "0791:852C")
    return 0                                              # AX 0; DX as the restart left it


# -- 8537 --------------------------------------------------------------------------------------------------------
@PORTS.port("0791:8537", ret="retf 4")                     # 869C retf 4
def move_player_sprite(mem, variant):
    f = mem.enter(0, "0791:8537")
    off, seg, rec = record(mem, f)
    no_position = mem.ds16(NO_POSITION)
    old = mem.u16(rec + 2)
    ax = old
    if old != no_position and old != mem.u16(rec):        # 853D-8554
        row, col = mem.u8(rec + 2), mem.u8(rec + 3)
        bx = mem.u16(cell(mem, BACKGROUND, row, col))                        # 8556-8577
        mem.w16(cell(mem, PICTURE, row, col), bx, "0791:859D")               # 857C-859D
        ax, dx = cell_mul(row)
        mem.set_reg("dx", dx)
    pos = mem.u16(rec)
    mem.w16(rec + 2, pos, "0791:85AB")                    # 85A2-85AB the old position := the position
    ax = pos
    if pos != no_position:                                # 85AF-85B9
        held = 1 if (mem.u8(rec + 4) == 1 and mem.ds8(0x830B) == mem.u8(rec + 6)) else 0     # 85BB-85D5
        bx = (held + mem.u16(rec + 4)) & 0xFFFF           # 85D7-85E0 xor ah, ah; add ax, es:[di + 4]
        row, col = mem.u8(rec), mem.u8(rec + 1)
        if variant != "no-draw":
            mem.w16(cell(mem, PICTURE, row, col), bx, "0791:8602")           # 85E2-8602 the sprite drawn
        ax, dx = cell_mul(row)
        mem.set_reg("dx", dx)
    regs(mem, ax)
    ax = yield call("0791:2C29", seg, off, ret_to="0791:8610", far=True)    # 8607-860D
    if not ax & 0xFF:                                     # 8610 or al, al; jne 8617
        return None                                       # 8614 jmp 8699: AX, DX as 2C29 left them
    pos = mem.u16(rec)
    mem.wds16(0x82F6, pos, "0791:861D")                   # 8617-861D the ball at the holder
    slot = mem.u8(rec + 6)                                # 8620-8627
    regs(mem, slot)
    ax = yield call("0791:045D", slot, ret_to="0791:862D", far=False)
    draw = False
    if ax & 0xFF:                                         # 862D or al, al; je 8644
        ax = yield call("0791:2EB8", mem.u16(rec), seg, off, ret_to="0791:8640", far=True)   # 8631-863D
        draw = bool(ax & 0xFF)                            # 8640 or al, al; jne 8690
    if not draw:
        state = mem.u8(rec + 0xF)                         # 8644-8647
        ax = lo(ax, state)
        if state in (1, 2, 5):                            # 864B-8655
            regs(mem, ax)
            ax = yield call("0791:2BE5", seg, off, ret_to="0791:8660", far=True)
            mem.wds8(0x82F7, mem.ds8(0x82F7) + (ax & 0xFF), "0791:8660")
        elif state == 3:
            mem.wds8(0x82F7, mem.ds8(0x82F7) - 1, "0791:866A")
        elif state == 4:
            mem.wds8(0x82F7, mem.ds8(0x82F7) + 1, "0791:8674")
        if mem.ds8(0x82F7) == 0x26:                       # 8678-867F
            mem.wds8(0x82F7, 0x24, "0791:867F")
        if mem.ds8(0x82F7) == 0xDA:                       # 8684-868B
            mem.wds8(0x82F7, 0xDC, "0791:868B")
    regs(mem, ax)
    mem.set_reg("di", 0x82F6)
    yield call("0791:8F10", mem.reg("ds"), 0x82F6, ret_to="0791:8699", far=True)   # 8690-8696 draw_ball
    return None


# -- 869F --------------------------------------------------------------------------------------------------------
@PORTS.port("0791:869F", ret="retf 4")                     # 86CD retf 4
def take_possession(mem, variant):
    f = mem.enter(0, "0791:869F")
    _, _, rec = record(mem, f)
    mem.wds8(0x830B, mem.u8(rec + 6), "0791:86A9")        # 86A2-86A9
    mem.wds16(0x8300, 0, "0791:86AE")
    mem.wds8(0x830C, 0, "0791:86B1")
    mem.wds8(0x830D, 0, "0791:86B6")
    mem.wds8(0x8302, 0, "0791:86BB")
    mem.wds8(0x8303, 0, "0791:86C0")
    mem.wds8(0x8327, 0, "0791:86C5")
    return 0                                              # 86AC xor ax, ax


# -- 8AE9 --------------------------------------------------------------------------------------------------------
@PORTS.port("0791:8AE9", ret="retf 4")                     # 8C64 retf 4
def update_player(mem, variant):
    f = mem.enter(6, "0791:8AE9")                         # 8AE9-8AEC
    off, seg, rec = record(mem, f)
    ax, dx = mul(mem.u16(rec + 0xD), 0x14)                # 8AEF-8AF9
    poff, pseg = mem.farptr(mem.DS * 16 + 0xA91B)         # 8AFB-8B04 [bp - 6]: the player's position code
    code = mem.addr(pseg, poff + ax)
    state = mem.u8(rec + 0x12)                            # 8B07-8B0A
    regs(mem, lo(ax, state), dx)
    if state in HANDLERS:
        target, ret_to = HANDLERS[state]
        yield call(target, seg, off, ret_to=ret_to, far=True)
    yield call("0791:8889", f.bp, ret_to="0791:8BB7", far=False)           # 8BB3-8BB4 push bp
    ax = 1 if mem.u8(rec + 0xF) < 5 else 0                # 8BB7-8BC7 cmp byte +0xf, 5; jb
    mem.w16(rec + 0x14, mem.u16(rec + 0x14) + ax, "0791:8BCC")
    if mem.ds8(0x8302) != 0:                              # 8BD0 cmp byte [0x8302], 0; je 8C2C
        ax = mem.u8(rec + 6)                              # 8BDA mov al (AH 0 since 8BC7)
    if mem.ds8(0x8302) != 0 and mem.u8(rec + 6) == mem.ds8(0x830D):        # 8BD0-8BE2
        regs(mem, ax)
        ax = yield call("0791:2CEC", seg, off, ret_to="0791:8BED", far=True)
        if ax & 0xFF and mem.u8(rec + 0x12) != 0x0C:      # 8BED-8BF9
            kept = mem.ds8(0x8303)                        # 8BFB-8BFE [bp - 2]
            mem.wds8(0x830C, mem.ds8(0x830D), "0791:8C04")
            ax = lo(ax, mem.ds8(0x830B))
            if mem.ds8(0x830B) != mem.ds8(0x830D) and mem.ds8(0x8303) == 0:     # 8C07-8C15
                ax = lo(ax, 0x19)
                regs(mem, ax)
                ax = yield call("0791:2AD4", ax, ret_to="0791:8C1D", far=False)
            regs(mem, ax)
            ax = yield call("0791:869F", seg, off, ret_to="0791:8C26", far=True)
            mem.wds8(0x8303, kept, "0791:8C29")           # 8C26-8C29
            ax = lo(ax, kept)
    regs(mem, ax)
    yield call("0791:8537", seg, off, ret_to="0791:8C35", far=True)        # 8C2C-8C32
    if mem.ds8(0x8325) != 0 and mem.u16(rec + 0x14) > 0xB4:                # 8C35-8C45
        if s8(mem.u8(code + 0xE)) > 1:                    # 8C47-8C4F cmp byte +0xe, 1; jle
            mem.w8(code + 0xE, mem.u8(code + 0xE) - 1, "0791:8C54")
        mem.w16(rec + 0x14, 0, "0791:8C5D")               # 8C58-8C5D
        return 0
    return None                                           # AX, DX as 8537 left them


# -- 8C67, 8CCA ----------------------------------------------------------------------------------------------------
@PORTS.port("0791:8C67", ret="ret 4")                      # 8CC7 ret 4
def reset_offside_line(mem, variant):
    f = mem.enter(4, "0791:8C67")                         # [bp + 4] 8CCA's BP, [bp + 6] the side byte
    side = cbw(f.u8(6))                                   # 8C6D-8C70
    line = mem.DS * 16 + ((side * 6 + LINES) & 0xFFFF)    # 8C71-8C82 [bp - 4]
    first = mem.ds8(SIDE_BASE + side)                     # 8C85-8C8B
    di, ax, dx = slot_record(first + 1)                   # 8C8F-8C99
    regs(mem, ax, dx)
    mem.set_reg("di", di)
    ax = yield call("0791:2BE5", mem.reg("ds"), di, ret_to="0791:8CA3", far=True)
    ax = (cbw(ax) << 3) & 0xFFFF                          # 8CA3-8CA7 cbw; mov cx, 3; shl ax, cl
    mem.w8(line, ax, "0791:8CAC")
    mem.w8(line + 1, 0, "0791:8CB2")
    ax = mem.u16(line)                                    # 8CB7-8CC0
    mem.w16(line + 2, ax, "0791:8CC0")
    return ax


@PORTS.port("0791:8CCA", ret="ret")                        # 8CF4 ret
def reset_offside_lines(mem, variant):
    f = mem.enter(0, "0791:8CCA")
    ax = lo(mem.reg("ax"), 1)                             # 8CCD-8CD0 mov al, 1; push ax; push bp
    regs(mem, ax)
    ax = yield call("0791:8C67", ax, f.bp, ret_to="0791:8CD4", far=False)
    ax = lo(ax, 0)                                        # 8CD4-8CD7
    regs(mem, ax)
    yield call("0791:8C67", ax, f.bp, ret_to="0791:8CDB", far=False)
    mem.wds8(0x82EF, 0, "0791:8CDB")
    mem.wds8(0x82EE, 1, "0791:8CE0")
    mem.wds16(0x82F0, mem.ds16(0x82EE), "0791:8CE8")      # 8CE5-8CE8
    ax = mem.ds16(0x82EE)
    mem.wds16(0x82F4, ax, "0791:8CEE")                    # 8CEB-8CEE
    return ax


# -- 8CF5 --------------------------------------------------------------------------------------------------------
@PORTS.port("0791:8CF5", ret="ret")                        # 8E23 ret
def track_offside_line(mem, variant):
    mem.enter(0xC, "0791:8CF5")                           # 8CF5-8CF8
    for side in (0, 1):                                   # 8CFB [bp - 1] := 0 .. 8E17 cmp [bp - 1], 1
        line_off = (side * 6 + LINES) & 0xFFFF            # 8D04-8D19 [bp - 9]
        line = mem.DS * 16 + line_off
        mem.w8(line + 1, 0, "0791:8D1F")
        first = mem.ds8(SIDE_BASE + side)                 # 8D24-8D2A
        di, ax, dx = slot_record(first + 1)               # 8D2E-8D38
        regs(mem, ax, dx)
        mem.set_reg("di", di)
        ax = yield call("0791:2BE5", mem.reg("ds"), di, ret_to="0791:8D42", far=True)
        d = cbw(ax)                                       # 8D42-8D43 [bp - 5]
        last = first + 0xB                                # 8D46-8D55 [bp - 0xb]
        k = first + 2                                     # 8D58-8D6C [bp - 3]; jg 8DB5 never (k < last)
        while True:                                       # 8D74-8DB3
            cx = cbw(mem.u8(line + 1))
            di = mul(k, RECORD)[0]
            y = mem.ds8(di + RECORDS + 1)                 # 8D88 [di - 0x7f17]: slot k's row byte +1
            ax, dx = imul(cbw(y), d)
            if variant == "offside-max":
                take = s16(ax) > s16(cx)
            else:
                take = s16(ax) < s16(cx)                  # 8D90 cmp ax, cx; jge 8DAD
            if take:
                mem.w8(line + 1, ax, "0791:8DA9")         # 8D94-8DA9
            if k == last:
                break
            k += 1
        ax, dx = imul(cbw(mem.u8(line + 1)), d)           # 8DB5-8DBD
        mem.w8(line + 1, ax, "0791:8DC3")
        regs(mem, ax, dx)
        mem.set_reg("di", line_off)
        ax = yield call("0791:8E24", mem.reg("ds"), line_off, ret_to="0791:8DD0", far=True)
        dl = 1 if s8(mem.u8(line + 1)) > 0 else 0         # 8DD0-8DE0
        ax = lo(ax, dl)
        dx = lo(mem.reg("dx"), dl)
        al = 1 if s8(mem.ds8(0x82F7)) > 0 else 0          # 8DE2-8DEF
        ax = lo(ax, al)
        regs(mem, ax, dx)
        if al == dl and mem.ds8(0x8328) != 0 and mem.u8(line + 1) != 0:     # 8DEF-8E02
            mem.set_reg("di", 0x8304)
            yield call("0791:90C5", mem.ds16(0x8308), mem.u16(line), mem.reg("ds"), 0x8304,
                       ret_to="0791:8E17", far=True)      # 8E04-8E14 the marker
    return None                                           # AX, DX as left


# -- 8E24 --------------------------------------------------------------------------------------------------------
@PORTS.port("0791:8E24", ret="retf 4")                     # 8EED retf 4
def move_sprite(mem, variant):
    f = mem.enter(0, "0791:8E24")
    _, _, rec = record(mem, f)
    if mem.u16(rec + 2) != mem.u16(rec):                  # 8E27-8E34
        row, col = mem.u8(rec + 2), mem.u8(rec + 3)
        if mem.u16(cell(mem, PICTURE, row, col)) == mem.u16(rec + 4):       # 8E36-8E63 still the sprite there
            bx = mem.u16(cell(mem, BACKGROUND, row, col))                    # 8E65-8E86
            mem.w16(cell(mem, PICTURE, row, col), bx, "0791:8EAC")           # 8E8B-8EAC restored
    mem.w16(rec + 2, mem.u16(rec), "0791:8EBA")           # 8EB1-8EBA
    bx = mem.u16(rec + 4)
    row, col = mem.u8(rec), mem.u8(rec + 1)
    mem.w16(cell(mem, PICTURE, row, col), bx, "0791:8EE5")                   # 8EBE-8EE5 drawn at the new one
    ax, dx = cell_mul(row)
    mem.set_reg("dx", dx)
    return ax


# -- 90C5 --------------------------------------------------------------------------------------------------------
@PORTS.port("0791:90C5", ret="retf 8")                     # 9116 retf 8
def place_marker(mem, variant):
    f = mem.enter(0, "0791:90C5")                         # [bp + 6] the record, [bp + 0xa] a position, [bp + 0xc] a sprite
    off, seg, rec = record(mem, f)
    mem.w16(rec + 4, f.u16(0xC), "0791:90CE")             # 90C8-90CE
    index = 0 if mem.u16(rec + 4) == 0x0EAE else 1        # 90D2-90E1
    dx = cbw(mem.ds8(DIRECTIONS + index))                 # 90E3-90EB
    ax = (cbw(f.u8(0xB)) + dx) & 0xFFFF                   # 90ED-90F1
    mem.w8(rec + 1, ax, "0791:90F6")
    ax = lo(ax, f.u8(0xA))                                # 90FA-9100
    mem.w8(rec, ax, "0791:9100")
    regs(mem, ax, dx)
    if mem.ds8(0x9A3E) == 0:                              # 9103-9108
        yield call("0791:8E24", seg, off, ret_to="0791:9113", far=True)
    return None


# -- 9119 --------------------------------------------------------------------------------------------------------
def _step(mem, rec, target, here, at):
    """9145-915B, 9166-917E, 9257-9279, 9287-92AB: the byte `here` one step (DS:7920 by target > here) closer."""
    al = 1 if s8(mem.u8(rec + target)) > s8(mem.u8(rec + here)) else 0
    mem.w8(rec + here, mem.u8(rec + here) + mem.ds8(DIRECTIONS + al), at)


@PORTS.port("0791:9119", ret="retf 6")                     # 92F9 retf 6
def move_referee(mem, variant):
    f = mem.enter(0, "0791:9119")                         # [bp + 6] the referee's record, [bp + 0xa] a byte
    off, seg, rec = record(mem, f)
    if f.u8(0xA) != 0:                                    # 911C-9122
        mem.w8(rec + 7, mem.ds8(0x82F7), "0791:912B")     # 9125-912B
        mem.w8(rec + 6, cbw(mem.ds8(0x82F6)) + 1, "0791:9137")              # 912F-9137
        _step(mem, rec, 7, 1, "0791:915B")
        _step(mem, rec, 6, 0, "0791:917E")
        yield call("0791:8E24", seg, off, ret_to="0791:918A", far=True)
        bx = mem.u16(rec + 4)                             # 918A-91B1
        row, col = mem.u8(rec), mem.u8(rec + 1)
        mem.w16(cell(mem, PICTURE, row, col), bx, "0791:91B1")
        ax, dx = cell_mul(row)
        mem.set_reg("dx", dx)
        return ax
    ball = cbw(mem.ds8(0x82F7))                           # 91B9-91BE cmp byte [0x82f7], 0; jle 91E5
    if s16(ball) > 0:
        a = (ball + 1) & 0xFFFF                           # 91C0-91C7 inc; cwd; push dx; push ax
        push(mem, "0791:91C6", cwd(a))
        push(mem, "0791:91C7", a)
        regs(mem, 2, cwd(a))
        r = yield call("214B:06B1", 2, ret_to="0791:91D1", far=True)        # 91C8-91CC rand(2)
        pop(mem, 2)                                       # the long stays: 0D1C's call pushes it again in place
        b = (r + 0x1E) & 0xFFFF                           # 91D1-91D6
        regs(mem, b, cwd(b))
        ax = yield call("214B:0D1C", cwd(a), a, cwd(b), b, ret_to="0791:91DC", far=True)
        mem.w8(rec + 7, ax, "0791:91DF")
    else:
        a = (ball - 1) & 0xFFFF                           # 91E5-91EC dec; cwd; push dx; push ax
        push(mem, "0791:91EB", cwd(a))
        push(mem, "0791:91EC", a)
        regs(mem, 2, cwd(a))
        r = yield call("214B:06B1", 2, ret_to="0791:91F6", far=True)        # 91ED-91F1 rand(2)
        pop(mem, 2)
        b = (0xFFE2 - r) & 0xFFFF                         # 91F6-91FF mov dx, ax; mov ax, -0x1e; sub ax, dx
        regs(mem, b, cwd(b))
        ax = yield call("214B:0D56", cwd(a), a, cwd(b), b, ret_to="0791:9205", far=True)
        mem.w8(rec + 7, ax, "0791:9208")
    v = s16(cbw(mem.u8(rec + 7)))                         # 920C-9218 cbw; cwd; mov cx, 4; idiv cx
    q = abs(v) // 4 * (1 if v >= 0 else -1)
    r = v - 4 * q
    ax = (q + 1) & 0xFFFF                                 # 921A inc ax
    mem.w8(rec + 6, ax, "0791:921E")
    lo_word, hi_word = lo(ax, 0xFB), lo(ax, 5)            # 922B-9230 mov al, -5; push ax; mov al, 5; push ax
    regs(mem, hi_word, r)
    mem.set_reg("cx", 4)
    mem.set_reg("di", (off + 6) & 0xFFFF)
    yield call("214B:2031", seg, (off + 6) & 0xFFFF, lo_word, hi_word, ret_to="0791:9236", far=True)
    if mem.u16(rec + 6) != mem.u16(rec + 2) and variant != "referee-still":  # 9236-9246
        if mem.u8(rec + 7) != mem.u8(rec + 1):            # 9249-9257
            _step(mem, rec, 7, 1, "0791:9279")
        if mem.u8(rec + 6) != mem.u8(rec):                # 927D-928A
            _step(mem, rec, 6, 0, "0791:92AB")
        row, col = mem.u8(rec), mem.u8(rec + 1)           # 92AE-92CE the background's character there
        ax, dx = cell_mul(row)
        ax = lo(ax, mem.u8(cell(mem, BACKGROUND, row, col)))
        regs(mem, ax, dx)
        mem.set_reg("di", BLOCKERS)
        yield call("23E4:08DF", ax, mem.reg("ds"), BLOCKERS, ret_to="0791:92DE", far=True)
        if not mem.reg("eflags") & 0x40:                  # 92DE je 92ED: ZF set when not in the set
            mem.w16(rec, mem.u16(rec + 2), "0791:92EA")   # 92E0-92EA blocked: back to the old position
    yield call("0791:8E24", seg, off, ret_to="0791:92F6", far=True)        # 92ED-92F3
    return None
