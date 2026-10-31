"""Ball, passing and shooting routines from the segment0791 listing (T64).

Calls, including calls between routines in this module, remain guest calls.
Only routines whose complete assembly has been read are registered here.
"""
from . import Registry
from .guest import call
from .mem import s8, s16
from .runtime import Regs
from .geometry import cbw, cwd, mul, imul

PORTS = Registry("ball", "ball, passing and shooting (T64)")
PORTS.variant("launch-reverse-x", "3528/35E6: reverse the chosen horizontal launch velocity")
PORTS.variant("pass-always-replace", "3273: accept a replacement receiver even when its coin is zero")
PORTS.variant("shot-skip-jitter", "3C4D–3C5F: omit the two jitter coins and ball-x adjustment")
M16 = 0xFFFF


def local8(mem, r, offset):
    r.flush()
    return mem.u8(mem.ss_lin((r.bp + offset) & M16))


def local16(mem, r, offset):
    r.flush()
    return mem.u16(mem.ss_lin((r.bp + offset) & M16))


def load_local_pitch(mem, r):
    r.di = local16(mem, r, -0xD)
    r.es = local16(mem, r, -0xB)


def pop_word(mem, r):
    value = mem.u16(mem.ss_lin(r.sp))
    r.sp = r.sp + 2
    return value


@PORTS.port("0791:2FB1", ret="ret")
def find_nearest_to_ball(mem, variant):
    """2FB1–30E9: nearest available slot and nearest goal-side slot per side."""
    r = Regs(mem)
    r.enter(0xE)                                               # 2FB1–2FB4
    r.local8(-1, 0)                                            # 2FB7
    while True:
        r.al = local8(mem, r, -1)
        cbw(r)
        r.di = r.ax
        mem.wds8((0x8311 + r.di) & M16, 0, "0791:2FC6")
        r.al = local8(mem, r, -1)
        cbw(r)
        r.di = r.ax
        mem.wds8((0x830F + r.di) & M16, 0, "0791:2FD1")
        r.local16(-5, 100)                                     # 2FD6
        r.local16(-7, 100)                                     # 2FDB
        r.local16(-3, 2)                                       # 2FE0
        while True:
            r.al = local8(mem, r, -1)
            cbw(r)
            r.di = r.ax
            r.al = mem.ds8((0x668 + r.di) & M16)
            r.ah = 0
            r.ax = r.ax + local16(mem, r, -3)
            r.dx = 0x16
            mul(r, r.dx)
            r.di = r.ax + 0x80E8
            r.local16(-0xD, r.di)                              # 3004
            r.local16(-0xB, mem.DS)                             # 3007
            load_local_pitch(mem, r)
            r.store(stack=True)
            yield call("0791:2956", r.es, r.di, ret_to="0791:3013", far=True)
            r = Regs(mem, resumed=True)
            if r.al == 0:
                r.al = mem.ds8(0x830B)
                load_local_pitch(mem, r)
                if r.al != mem.u8(mem.addr(r.es, r.di + 6)):
                    load_local_pitch(mem, r)
                    if mem.u8(mem.addr(r.es, r.di + 0x12)) != 0xD:
                        r.al = mem.ds8(0x82F6)
                        cbw(r)
                        r.dx = r.ax
                        load_local_pitch(mem, r)
                        r.al = mem.u8(mem.addr(r.es, r.di))
                        cbw(r)
                        r.ax = r.ax - r.dx
                        if s16(r.ax) < 0:
                            r.ax = -r.ax
                        r.cx = r.ax
                        r.al = mem.ds8(0x82F7)
                        cbw(r)
                        r.dx = r.ax
                        load_local_pitch(mem, r)
                        r.al = mem.u8(mem.addr(r.es, r.di + 1))
                        cbw(r)
                        r.ax = r.ax - r.dx
                        if s16(r.ax) < 0:
                            r.ax = -r.ax
                        r.ax = r.ax + r.cx
                        r.local16(-9, r.ax)                    # 3065
                        if r.ax < local16(mem, r, -5):
                            load_local_pitch(mem, r)
                            r.dx = (r.dx & 0xFF00) | mem.u8(mem.addr(r.es, r.di + 6))
                            r.al = local8(mem, r, -1)
                            cbw(r)
                            r.di = r.ax
                            mem.wds8((0x8311 + r.di) & M16, r.dx & 0xFF, "0791:307D")
                            r.ax = local16(mem, r, -9)
                            r.local16(-5, r.ax)                 # 3084
                        load_local_pitch(mem, r)
                        r.store(stack=True)
                        yield call("0791:2BE5", r.es, r.di, ret_to="0791:3090", far=True)
                        r = Regs(mem, resumed=True)
                        cbw(r)
                        r.dx = r.ax
                        r.al = mem.ds8(0x82F7)
                        cbw(r)
                        imul(r, r.dx)
                        r.push(r.ax)                           # 3099: live across the next call
                        load_local_pitch(mem, r)
                        r.store(stack=True)
                        yield call("0791:2BE5", r.es, r.di, ret_to="0791:30A3", far=True)
                        r = Regs(mem, resumed=True)
                        cbw(r)
                        r.dx = r.ax
                        load_local_pitch(mem, r)
                        r.al = mem.u8(mem.addr(r.es, r.di + 1))
                        cbw(r)
                        imul(r, r.dx)
                        r.dx = mem.u16(mem.ss_lin(r.sp))        # 30B0 pop dx
                        r.sp = r.sp + 2
                        if s16(r.ax) < s16(r.dx):
                            r.ax = local16(mem, r, -9)
                            if r.ax < local16(mem, r, -7):
                                load_local_pitch(mem, r)
                                r.dx = (r.dx & 0xFF00) | mem.u8(mem.addr(r.es, r.di + 6))
                                r.al = local8(mem, r, -1)
                                cbw(r)
                                r.di = r.ax
                                mem.wds8((0x830F + r.di) & M16, r.dx & 0xFF, "0791:30CA")
                                r.ax = local16(mem, r, -9)
                                r.local16(-7, r.ax)             # 30D1
            if local16(mem, r, -3) == 0xB:
                break
            r.local16(-3, local16(mem, r, -3) + 1)               # 2FE7
        if local8(mem, r, -1) == 1:
            break
        r.local8(-1, local8(mem, r, -1) + 1)                    # 2FBD
    r.leave()
    r.store()


@PORTS.port("0791:30EA", ret="retf 6")
def slot_in_record_side(mem, variant):
    """30EA–310E: side base selected by2974 plus the caller's relative slot."""
    off, seg, index = mem.arg(0), mem.arg(1), mem.arg(2)
    r = Regs(mem)
    r.enter(2)
    r.es, r.di = seg, off
    r.store(stack=True)
    yield call("0791:2974", r.es, r.di, ret_to="0791:30F9", far=True)
    r = Regs(mem, resumed=True)
    cbw(r)
    r.di = r.ax
    r.al = mem.ds8((0x668 + r.di) & M16)
    r.ah = 0
    r.ax = r.ax + index
    r.local16(-2, r.ax)
    r.leave()
    r.store()


@PORTS.port("0791:3323", ret="retf 4")
def pass_to_selected_receiver(mem, variant):
    """3323–333C: select a receiver, then pass with the full returned AX."""
    off, seg = mem.arg(0), mem.arg(1)
    r = Regs(mem)
    r.enter()
    r.es, r.di = seg, off
    r.store(stack=True)
    yield call("0791:3111", seg, off, ret_to="0791:332F", far=True)
    r = Regs(mem, resumed=True)
    receiver = r.ax
    r.es, r.di = seg, off
    r.store(stack=True)
    yield call("0791:384C", receiver, seg, off, ret_to="0791:3339", far=True)
    r = Regs(mem, resumed=True)
    r.leave()
    r.store()


@PORTS.port("0791:3BEE", ret="retf 4")
def choose_pass_or_long_ball(mem, variant):
    """3BEE–3C1D: existing offside goes to82EB without drawing."""
    off, seg = mem.arg(0), mem.arg(1)
    r = Regs(mem)
    r.enter()
    if mem.ds8(0x830E) != 0:
        r.store(stack=True)
        yield call("0791:82EB", ret_to="0791:3BFB", far=False)
    else:
        r.store(stack=True)
        yield call("214B:06FA", ret_to="0791:3C02", far=True)
        r = Regs(mem, resumed=True)
        target, ret = ("0791:3B15", "0791:3C0F") if r.al else ("0791:3323", "0791:3C1A")
        r.es, r.di = seg, off
        r.store(stack=True)
        yield call(target, seg, off, ret_to=ret, far=True)
    r = Regs(mem, resumed=True)
    r.leave()
    r.store()


@PORTS.port("0791:3C20", ret="ret 2")
def count_on_target(mem, variant):
    """3C20–3C3C: increment the side's statistic only outside8326 mode."""
    side = mem.arg(0)
    r = Regs(mem)
    r.enter()
    if mem.ds8(0x8326) == 0:
        r.al = side
        cbw(r)
        r.dx = 10
        mul(r, r.dx)
        r.di = r.ax
        off = (r.di + 0x7B82) & M16
        mem.wds8(off, mem.ds8(off) + 1, "0791:3C35")
    r.leave()
    r.store()


@PORTS.port("0791:3EC5", ret="retf 6")
def take_shot(mem, variant):
    """3EC5–3EDC: event1 with the caller's low-byte commentary template."""
    off, seg, template = mem.arg(0), mem.arg(1), mem.arg(2)
    r = Regs(mem)
    r.enter()
    r.al = template                                          # 3EC8 mov al; preserve incoming AH
    template_word = r.ax
    r.ax = 1
    r.es, r.di = seg, off
    r.store(stack=True)
    yield call("0791:3C3F", template_word, 1, seg, off, ret_to="0791:3ED9", far=True)
    r = Regs(mem, resumed=True)
    r.leave()
    r.store()


@PORTS.port("0791:3EDF", ret="retf 4")
def take_header(mem, variant):
    """3EDF–3EF5: event2, commentary14h, with incoming AH preserved."""
    off, seg = mem.arg(0), mem.arg(1)
    r = Regs(mem)
    r.enter()
    r.al = 0x14
    template_word = r.ax
    r.ax = 2
    r.es, r.di = seg, off
    r.store(stack=True)
    yield call("0791:3C3F", template_word, 2, seg, off, ret_to="0791:3EF2", far=True)
    r = Regs(mem, resumed=True)
    r.leave()
    r.store()


@PORTS.port("0791:408E", ret="retf 4")
def choose_clearance(mem, variant):
    """408E–40B9: coin chooses either long clearance with event11."""
    off, seg = mem.arg(0), mem.arg(1)
    r = Regs(mem)
    r.enter()
    r.store(stack=True)
    yield call("214B:06FA", ret_to="0791:4096", far=True)
    r = Regs(mem, resumed=True)
    target, ret = ("0791:3FAD", "0791:40A7") if r.al else ("0791:3EF8", "0791:40B6")
    r.ax = 11
    r.es, r.di = seg, off
    r.store(stack=True)
    yield call(target, 11, seg, off, ret_to=ret, far=True)
    r = Regs(mem, resumed=True)
    r.leave()
    r.store()


@PORTS.port("0791:4151", ret="ret")
def keeper_clearance_if_in_strip(mem, variant):
    """4151–419B: test the ball holder's strip, optionally clear with event9."""
    r = Regs(mem)
    r.enter(6)
    r.al = mem.ds8(0x830B)
    r.ah = 0
    r.dx = 0x16
    mul(r, r.dx)
    r.di = r.ax + 0x80E8
    r.local16(-5, r.di)
    r.local16(-3, mem.DS)
    r.local8(-1, 0)
    off, seg = r.di, mem.DS
    point = mem.u16(mem.addr(seg, off))
    r.es, r.di = seg, off
    r.store(stack=True)
    yield call("0791:2EB8", point, seg, off, ret_to="0791:4180", far=True)
    r = Regs(mem, resumed=True)
    if r.al != 0:
        r.ax = 9
        r.es, r.di = seg, off
        r.store(stack=True)
        yield call("0791:3FAD", 9, seg, off, ret_to="0791:4191", far=True)
        r = Regs(mem, resumed=True)
        r.local8(-1, 1)
    r.al = local8(mem, r, -1)                                  # 4195: preserve returned AH
    r.leave()
    r.store()


@PORTS.port("0791:3B15", ret="retf 4")
def long_ball_target(mem, variant):
    """3B15–3B9B: kicking draw with floor30, signed by attack direction."""
    off, seg = mem.arg(0), mem.arg(1)
    r = Regs(mem)
    r.enter(2)
    r.ax = mem.ds16(0x82F6)
    r.local16(-2, r.ax)
    r.ax, r.dx = 30, 0
    r.push(r.dx)                                              # 3B26–3B27: floor held under skill/RNG calls
    r.push(r.ax)
    r.ax = 2
    r.es, r.di = seg, off
    r.store(stack=True)
    yield call("0791:278A", 2, seg, off, ret_to="0791:3B35", far=True)
    r = Regs(mem, resumed=True)
    r.dx, r.cx = 0, 4
    r.ax, r.dx = r.ax // r.cx, r.ax % r.cx
    r.store(stack=True)
    yield call("214B:06B1", r.ax, ret_to="0791:3B42", far=True)
    r = Regs(mem, resumed=True)
    cwd(r)
    # The floor was live across both calls. Re-present all four words to Call
    # at the same addresses, so its Pascal-return accounting includes them.
    floor_lo, floor_hi = pop_word(mem, r), pop_word(mem, r)
    r.store(stack=True)
    yield call("214B:0D56", floor_hi, floor_lo, r.dx, r.ax, ret_to="0791:3B4A", far=True)
    r = Regs(mem, resumed=True)
    r.push(r.dx)                                              # 3B4A–3B4B: full long held under direction call
    r.push(r.ax)
    r.es, r.di = seg, off
    r.store(stack=True)
    yield call("0791:2BE5", seg, off, ret_to="0791:3B55", far=True)
    r = Regs(mem, resumed=True)
    cbw(r)
    cwd(r)
    r.cx, r.bx = pop_word(mem, r), pop_word(mem, r)
    r.store(stack=True)
    yield call("23E4:0279", ret_to="0791:3B5E", far=True)
    r = Regs(mem, resumed=True)
    r.local8(-1, local8(mem, r, -1) + r.al)
    mem.wds8(0x830C, 0xFF, "0791:3B61")
    point = local16(mem, r, -2)
    r.ax = 10
    r.es, r.di = seg, off
    r.store(stack=True)
    yield call("0791:34C1", point, 10, seg, off, ret_to="0791:3B76", far=True)
    r = Regs(mem, resumed=True)
    mem.wds8(0x8303, 1, "0791:3B76")
    r.al = int(mem.ds8(0x830C) == 0)
    cbw(r)
    r.di = r.ax
    r.al = mem.ds8((0x78A + r.di) & M16)
    r.store(stack=True)
    yield call("0791:2AA3", r.ax, ret_to="0791:3B93", far=False)
    r = Regs(mem, resumed=True)
    mem.wds8(0x830C, 0, "0791:3B93")
    r.leave()
    r.store()


@PORTS.port("0791:3B9E", ret="retf 6")
def launch_to_slot_with_half_event(mem, variant):
    """3B9E–3BEB: target slot point, event selected by the passer's half."""
    off, seg, slot = mem.arg(0), mem.arg(1), mem.arg(2)
    r = Regs(mem)
    r.enter()
    r.al = slot
    mem.wds8(0x830C, r.al, "0791:3BA4")
    r.ax, r.dx = slot, 0x16
    mul(r, r.dx)
    r.di = r.ax
    r.push(mem.ds16((0x80E8 + r.di) & M16))                   # 3BB1: target point survives2C54
    r.es, r.di = seg, off
    r.store(stack=True)
    yield call("0791:2C54", seg, off, ret_to="0791:3BBE", far=True)
    r = Regs(mem, resumed=True)
    cbw(r)
    r.di = r.ax
    r.al = mem.ds8((0x78C + r.di) & M16)
    r.ah = 0
    event = r.ax
    point = pop_word(mem, r)
    r.es, r.di = seg, off
    r.store(stack=True)
    yield call("0791:34C1", point, event, seg, off, ret_to="0791:3BD1", far=True)
    r = Regs(mem, resumed=True)
    r.al = 3
    r.store(stack=True)
    yield call("0791:2AA3", r.ax, ret_to="0791:3BD7", far=False)
    r = Regs(mem, resumed=True)
    r.store(stack=True)
    yield call("214B:06FA", ret_to="0791:3BDC", far=True)
    r = Regs(mem, resumed=True)
    mem.wds8(0x8303, r.al, "0791:3BDC")
    r.es, r.di = seg, off
    r.store(stack=True)
    yield call("0791:4D3F", seg, off, ret_to="0791:3BE8", far=True)
    r = Regs(mem, resumed=True)
    r.leave()
    r.store()


@PORTS.port("0791:3EF8", ret="retf 6")
def long_kick_target(mem, variant):
    """3EF8–3FAA: mode9 selects the parallel skill/divisor/floor/event rows."""
    off, seg, event = mem.arg(0), mem.arg(1), mem.arg(2)
    r = Regs(mem)
    r.enter(4)
    mem.wds8(0x830C, 0, "0791:3EFE")
    r.ax = mem.ds16(0x82F6)
    r.local16(-2, r.ax)
    r.al = int(event == 9)
    r.local8(-3, r.al)
    cbw(r)
    r.di = r.ax
    r.al = mem.ds8((0x79C + r.di) & M16)
    r.ah, r.dx = 0, 0
    r.push(r.dx)
    r.push(r.ax)
    r.al = local8(mem, r, -3)
    cbw(r)
    r.di = r.ax
    r.al = mem.ds8((0x798 + r.di) & M16)
    r.ah = 0
    r.push(r.ax)                                              # 3F34: divisor survives skill call
    r.al = local8(mem, r, -3)
    cbw(r)
    r.di = r.ax
    r.al = mem.ds8((0x796 + r.di) & M16)
    r.ah = 0
    r.es, r.di = seg, off
    r.store(stack=True)
    yield call("0791:278A", r.ax, seg, off, ret_to="0791:3F4B", far=True)
    r = Regs(mem, resumed=True)
    r.cx = pop_word(mem, r)
    r.dx = 0
    r.ax, r.dx = r.ax // r.cx, r.ax % r.cx
    r.store(stack=True)
    yield call("214B:06B1", r.ax, ret_to="0791:3F56", far=True)
    r = Regs(mem, resumed=True)
    cwd(r)
    floor_lo, floor_hi = pop_word(mem, r), pop_word(mem, r)
    r.store(stack=True)
    yield call("214B:0D56", floor_hi, floor_lo, r.dx, r.ax, ret_to="0791:3F5E", far=True)
    r = Regs(mem, resumed=True)
    r.push(r.dx)
    r.push(r.ax)
    r.es, r.di = seg, off
    r.store(stack=True)
    yield call("0791:2BE5", seg, off, ret_to="0791:3F69", far=True)
    r = Regs(mem, resumed=True)
    cbw(r)
    cwd(r)
    r.cx, r.bx = pop_word(mem, r), pop_word(mem, r)
    r.store(stack=True)
    yield call("23E4:0279", ret_to="0791:3F72", far=True)
    r = Regs(mem, resumed=True)
    r.local8(-1, local8(mem, r, -1) + r.al)
    point = local16(mem, r, -2)
    r.al = local8(mem, r, -3)
    cbw(r)
    r.di = r.ax
    r.al = mem.ds8((0x79A + r.di) & M16)
    r.ah = 0
    chosen_event = r.ax
    r.es, r.di = seg, off
    r.store(stack=True)
    yield call("0791:34C1", point, chosen_event, seg, off, ret_to="0791:3F8E", far=True)
    r = Regs(mem, resumed=True)
    mem.wds8(0x8303, 1, "0791:3F8E")
    mode = local8(mem, r, -3)
    r.al = 0x17 if mode else 0x18
    r.store(stack=True)
    yield call("0791:2AA3", r.ax, ret_to="0791:3F9F" if mode else "0791:3FA7", far=False)
    r = Regs(mem, resumed=True)
    r.leave()
    r.store()


@PORTS.port("0791:40BC", ret="ret")
def holder_in_advanced_central_strip(mem, variant):
    """40BC–4150: ahead of opposing marker, |y|<35 and |x|<4, outside own half."""
    r = Regs(mem)
    r.enter(6)
    r.al = mem.ds8(0x830B)
    r.ah = 0
    r.dx = 0x16
    mul(r, r.dx)
    r.di = r.ax + 0x80E8
    r.local16(-5, r.di)
    r.local16(-3, mem.DS)
    off, seg = r.di, mem.DS
    r.es, r.di = seg, off
    r.store(stack=True)
    yield call("0791:2C54", seg, off, ret_to="0791:40E1", far=True)
    r = Regs(mem, resumed=True)
    result = False
    if r.al == 0:
        r.store(stack=True)
        yield call("0791:2996", ret_to="0791:40E8", far=False)
        r = Regs(mem, resumed=True)
        r.al = int(r.al == 0)
        cbw(r)
        r.di = r.ax
        r.di = r.di << 1
        r.si = r.di
        r.di = (r.di << 1) + r.si
        r.al = mem.ds8((0x82E3 + r.di) & M16)
        cbw(r)
        if s16(r.ax) < 0:
            r.ax = -r.ax
        r.dx = r.ax
        r.es, r.di = seg, off
        r.al = mem.u8(mem.addr(seg, off + 1))
        cbw(r)
        if s16(r.ax) < 0:
            r.ax = -r.ax
        if s16(r.ax) > s16(r.dx):
            r.es, r.di = seg, off
            r.al = mem.u8(mem.addr(seg, off + 1))
            cbw(r)
            if s16(r.ax) < 0:
                r.ax = -r.ax
            if s16(r.ax) < 35:
                r.es, r.di = seg, off
                r.al = mem.u8(mem.addr(seg, off))
                cbw(r)
                if s16(r.ax) < 0:
                    r.ax = -r.ax
                result = s16(r.ax) < 4
    r.al = int(result)
    r.local8(-1, r.al)
    r.al = local8(mem, r, -1)
    r.leave()
    r.store()


@PORTS.port("0791:3FAD", ret="retf 6")
def clear_to_random_target(mem, variant):
    """3FAD–408B: narrow long clearance or wide random target, preserving draws."""
    off, seg, event = mem.arg(0), mem.arg(1), mem.arg(2)
    r = Regs(mem)
    r.enter(2)
    r.store(stack=True)
    yield call("214B:06FA", ret_to="0791:3FB8", far=True)
    r = Regs(mem, resumed=True)
    wide = r.al != 0
    if not wide:
        r.es, r.di = seg, off
        r.al = mem.u8(mem.addr(seg, off + 6))
        r.ah = 0
        r.store(stack=True)
        yield call("0791:045D", r.ax, ret_to="0791:3FC9", far=False)
        r = Regs(mem, resumed=True)
        wide = r.al != 0
    if wide:
        r.es, r.di = seg, off
        r.al = int(s8(mem.u8(mem.addr(seg, off))) > 0)
        cbw(r)
        r.di = r.ax
        r.al = mem.ds8((0x7920 + r.di) & M16)
        cbw(r)
        r.cx = 12
        imul(r, r.cx)
        r.local8(-2, r.al)
        r.ax = 40
        r.store(stack=True)
        yield call("214B:06B1", 40, ret_to="0791:3FF5", far=True)
        r = Regs(mem, resumed=True)
        r.dx = r.ax
        r.es, r.di = seg, off
        r.al = int(s8(mem.u8(mem.addr(seg, off + 1))) > 0)
        cbw(r)
        r.di = r.ax
        r.al = mem.ds8((0x7920 + r.di) & M16)
        cbw(r)
        imul(r, r.dx)
        r.local8(-1, r.al)
    else:
        r.ax = 8
        r.store(stack=True)
        yield call("214B:06B1", 8, ret_to="0791:401F", far=True)
        r = Regs(mem, resumed=True)
        r.ax = r.ax + 2
        r.dx = r.ax
        r.es, r.di = seg, off
        r.al = int(s8(mem.u8(mem.addr(seg, off))) > 0)
        cbw(r)
        r.di = r.ax
        r.al = mem.ds8((0x7920 + r.di) & M16)
        cbw(r)
        imul(r, r.dx)
        r.local8(-2, r.al)
        r.es, r.di = seg, off
        r.al = int(s8(mem.u8(mem.addr(seg, off + 1))) > 0)
        cbw(r)
        r.di = r.ax
        r.al = mem.ds8((0x7920 + r.di) & M16)
        cbw(r)
        r.cx = 50
        imul(r, r.cx)
        r.local8(-1, r.al)
    point = local16(mem, r, -2)
    r.es, r.di = seg, off
    r.store(stack=True)
    yield call("0791:34C1", point, event, seg, off, ret_to="0791:406F", far=True)
    r = Regs(mem, resumed=True)
    mem.wds8(0x8303, 1, "0791:406F")
    r.al = 0x16 if event == 11 else 0x15
    r.store(stack=True)
    yield call("0791:2AA3", r.ax, ret_to="0791:4080" if event == 11 else "0791:4088", far=False)
    r = Regs(mem, resumed=True)
    r.leave()
    r.store()


@PORTS.port("0791:3DF6", ret="retf 4")
def cross_to_candidate_or_random_point(mem, variant):
    """3DF6–3EC2: use3D38's output point, drawing a target only if zero."""
    off, seg = mem.arg(0), mem.arg(1)
    r = Regs(mem)
    r.enter(2)
    r.ax = 0
    r.local16(-2, r.ax)
    outoff = (r.bp - 2) & M16
    r.di = outoff
    r.es, r.di = seg, off
    r.al = mem.u8(mem.addr(seg, off + 6))
    r.ah = 0
    r.store(stack=True)
    yield call("0791:3D38", r.ss, outoff, r.ax, ret_to="0791:3E13", far=False)
    r = Regs(mem, resumed=True)
    if local16(mem, r, -2) == 0:
        r.store(stack=True)
        yield call("0791:261A", ret_to="0791:3E1C", far=False)
        r = Regs(mem, resumed=True)
        cwd(r)
        r.cx = 4
        dividend = s16(r.ax)
        quotient = abs(dividend) // 4
        if dividend < 0:
            quotient = -quotient
        r.ax, r.dx = quotient, dividend - quotient * 4
        r.ax = r.ax + 4
        r.dx = r.ax
        r.es, r.di = seg, off
        r.al = int(s8(mem.u8(mem.addr(seg, off))) < 0)
        cbw(r)
        r.di = r.ax
        r.al = mem.ds8((0x7920 + r.di) & M16)
        cbw(r)
        imul(r, r.dx)
        r.local8(-2, r.al)
        r.ax = 10
        r.store(stack=True)
        yield call("214B:06B1", 10, ret_to="0791:3E4C", far=True)
        r = Regs(mem, resumed=True)
        r.ax = r.ax + 24
        r.dx = r.ax
        r.es, r.di = seg, off
        r.al = int(s8(mem.u8(mem.addr(seg, off + 1))) > 0)
        cbw(r)
        r.di = r.ax
        r.al = mem.ds8((0x7920 + r.di) & M16)
        cbw(r)
        imul(r, r.dx)
        r.local8(-1, r.al)
    mem.wds8(0x830C, 0xFF, "0791:3E6E")
    point = local16(mem, r, -2)
    r.ax = 5
    r.es, r.di = seg, off
    r.store(stack=True)
    yield call("0791:34C1", point, 5, seg, off, ret_to="0791:3E83", far=True)
    r = Regs(mem, resumed=True)
    r.al = int(mem.ds8(0x830C) == 0)
    cbw(r)
    r.di = r.ax
    r.al = mem.ds8((0x794 + r.di) & M16)
    r.store(stack=True)
    yield call("0791:2AA3", r.ax, ret_to="0791:3E9B", far=False)
    r = Regs(mem, resumed=True)
    mem.wds8(0x830C, 0, "0791:3E9B")
    r.ax = 8
    r.store(stack=True)
    yield call("214B:06D0", 8, ret_to="0791:3EA9", far=True)
    r = Regs(mem, resumed=True)
    r.al = int(r.al == 0)
    mem.wds8(0x8303, r.al, "0791:3EB3")
    r.es, r.di = seg, off
    r.store(stack=True)
    yield call("0791:4D3F", seg, off, ret_to="0791:3EBF", far=True)
    r = Regs(mem, resumed=True)
    r.leave()
    r.store()


@PORTS.port("0791:3C3F", ret="retf 8")
def shot_or_header(mem, variant):
    """3C3F–3D17: shot jitter, skill gates, launch and short-circuited draws."""
    off, seg, event, template = (mem.arg(i) for i in range(4))
    r = Regs(mem)
    r.enter()
    mem.wds8(0x830C, 0, "0791:3C42")
    if event != 2 and variant != "shot-skip-jitter":
        r.store(stack=True)
        yield call("214B:06FA", ret_to="0791:3C52", far=True)
        r = Regs(mem, resumed=True)
        r.ah = 0
        r.push(r.ax)                                           # 3C54: live during second coin
        r.store(stack=True)
        yield call("214B:06FA", ret_to="0791:3C5A", far=True)
        r = Regs(mem, resumed=True)
        r.ah = 0
        r.dx = pop_word(mem, r)
        r.ax = r.ax - r.dx
        mem.wds8(0x82F6, mem.ds8(0x82F6) + r.al, "0791:3C5F")
    passed = False
    if mem.ds8(0x8324) == 0:
        r.al = int(event == 2)
        cbw(r)
        r.di = r.ax
        r.al = mem.ds8((0x78E + r.di) & M16)
        r.ah = 0
        skill = r.ax
        r.es, r.di = seg, off
        r.store(stack=True)
        yield call("0791:287C", skill, seg, off, ret_to="0791:3C89", far=True)
        r = Regs(mem, resumed=True)
        passed = r.al != 0
        if not passed:
            r.ax = 4
            r.store(stack=True)
            yield call("214B:06D0", 4, ret_to="0791:3C96", far=True)
            r = Regs(mem, resumed=True)
            passed = r.al != 0
            if not passed:
                r.store(stack=True)
                yield call("0791:29B3", ret_to="0791:3C9D", far=False)
                r = Regs(mem, resumed=True)
                passed = r.al != 0
    r.al = int(passed)
    mem.wds8(0x80FB, r.al, "0791:3CA7")
    r.es, r.di = seg, off
    r.store(stack=True)
    yield call("0791:2C86", mem.ds16(0x646), seg, off, ret_to="0791:3CB7", far=True)
    r = Regs(mem, resumed=True)
    point = r.ax
    r.es, r.di = seg, off
    r.store(stack=True)
    yield call("0791:34C1", point, event, seg, off, ret_to="0791:3CC4", far=True)
    r = Regs(mem, resumed=True)
    r.al = template                                           # 3CC4 leaves AH from launch
    r.store(stack=True)
    yield call("0791:2AA3", r.ax, ret_to="0791:3CCB", far=False)
    r = Regs(mem, resumed=True)
    if mem.ds8(0x8326) == 0:
        r.es, r.di = seg, off
        r.store(stack=True)
        yield call("0791:2974", seg, off, ret_to="0791:3CDB", far=True)
        r = Regs(mem, resumed=True)
        cbw(r)
        r.dx = 10
        mul(r, r.dx)
        r.di = r.ax
        stat = (r.di + 0x7B81) & M16
        mem.wds8(stat, mem.ds8(stat) + 1, "0791:3CE3")
    passed = event == 2
    if not passed:
        r.store(stack=True)
        yield call("214B:06FA", ret_to="0791:3CF2", far=True)
        r = Regs(mem, resumed=True)
        passed = r.al != 0 and event == 4
        if not passed:
            r.ax = 3
            r.store(stack=True)
            yield call("214B:06D0", 3, ret_to="0791:3D05", far=True)
            r = Regs(mem, resumed=True)
            passed = r.al != 0
    r.al = int(passed)
    mem.wds8(0x8303, r.al, "0791:3D0F")
    r.leave()
    r.store()


@PORTS.port("0791:3D38", ret="ret 6")
def find_cross_target(mem, variant):
    """3D38–3DF5: scan the holder's side; membership is returned in ZF."""
    skip, out_off, out_seg = (mem.arg(i) for i in range(3))
    r = Regs(mem)
    r.enter(8)
    r.store(stack=True)
    yield call("0791:2996", ret_to="0791:3D41", far=False)
    r = Regs(mem, resumed=True)
    cbw(r)
    r.di = r.ax
    r.al = mem.ds8((0x668 + r.di) & M16)
    r.ah = 0
    r.ax = r.ax + 11
    r.local16(-4, r.ax)
    r.store(stack=True)
    yield call("0791:2996", ret_to="0791:3D53", far=False)
    r = Regs(mem, resumed=True)
    cbw(r)
    r.di = r.ax
    r.al = mem.ds8((0x668 + r.di) & M16)
    r.ah = 0
    r.ax = r.ax + 2
    if r.ax <= local16(mem, r, -4):
        r.local16(-2, r.ax)
        while True:
            r.ax = local16(mem, r, -2)
            r.dx = 0x16
            mul(r, r.dx)
            r.di = r.ax + 0x80E8
            r.local16(-8, r.di)
            r.local16(-6, mem.DS)
            r.es, r.di = local16(mem, r, -6), local16(mem, r, -8)
            r.al = mem.u8(mem.addr(r.es, r.di + 6))
            r.ah = 0
            if r.ax != skip:
                r.es, r.di = local16(mem, r, -6), local16(mem, r, -8)
                r.ax = mem.u16(mem.addr(r.es, r.di + 0xD))
                r.dx = 20
                mul(r, r.dx)
                r.di, r.es = mem.ds16(0xA91B), mem.ds16(0xA91D)
                r.di = r.di + r.ax
                r.al = mem.u8(mem.addr(r.es, r.di + 6))           # AH remains product's high byte
                element = r.ax
                r.di = 0x3D18
                r.store(stack=True)
                yield call("23E4:08DF", element, mem.seg(0x0791), r.di,
                           ret_to="0791:3DB2", far=True)
                r = Regs(mem, resumed=True)
                if not (mem.reg("eflags") & 0x40):             # 3DB2 JE consumes guest helper's ZF
                    r.es, r.di = local16(mem, r, -6), local16(mem, r, -8)
                    player = mem.u16(mem.addr(r.es, r.di + 0xD))
                    r.store(stack=True)
                    yield call("1771:3216", player, ret_to="0791:3DC0", far=True)
                    r = Regs(mem, resumed=True)
                    if r.al == 0:
                        r.es, r.di = local16(mem, r, -6), local16(mem, r, -8)
                        point = mem.u16(mem.addr(r.es, r.di))
                        r.store(stack=True)
                        yield call("0791:2EF0", point, r.es, r.di, ret_to="0791:3DD3", far=True)
                        r = Regs(mem, resumed=True)
                        if r.al != 0:
                            r.es, r.di = local16(mem, r, -6), local16(mem, r, -8)
                            r.ax = mem.u16(mem.addr(r.es, r.di))
                            r.es, r.di = out_seg, out_off
                            mem.w16(mem.addr(r.es, r.di), r.ax, "0791:3DE0")
                            break
            r.ax = local16(mem, r, -2)
            if r.ax == local16(mem, r, -4):
                break
            r.local16(-2, local16(mem, r, -2) + 1)
    r.leave()
    r.store()


@PORTS.port("0791:333F", ret="ret 2")
def mark_offside_candidate(mem, variant):
    """333F–3480: nested launch procedure; its pointer lives in the parent frame."""
    parent = mem.arg(0)
    r = Regs(mem)
    r.enter(4)
    if mem.ds8(0x8325) == 0:
        mem.wds8(0x8325, 1, "0791:334C")
    else:
        r.ax = 11
        r.di = parent
        off = mem.u16(mem.ss_lin((r.di + 6) & M16))
        seg = mem.u16(mem.ss_lin((r.di + 8) & M16))
        r.es, r.di = seg, off
        r.store(stack=True)
        yield call("0791:30EA", 11, seg, off, ret_to="0791:3365", far=True)
        r = Regs(mem, resumed=True)
        r.local16(-4, r.ax)
        r.ax = 1
        r.di = parent
        off = mem.u16(mem.ss_lin((r.di + 6) & M16))
        seg = mem.u16(mem.ss_lin((r.di + 8) & M16))
        r.es, r.di = seg, off
        r.store(stack=True)
        yield call("0791:30EA", 1, seg, off, ret_to="0791:3379", far=True)
        r = Regs(mem, resumed=True)
        if r.ax <= local16(mem, r, -4):
            r.local16(-2, r.ax)
            while True:
                r.ax = local16(mem, r, -2)
                r.dx = 0x16
                mul(r, r.dx)
                r.di = r.ax
                r.al = mem.ds8((r.di + 0x80EE) & M16)
                r.di = parent
                off = mem.u16(mem.ss_lin((r.di + 6) & M16))
                seg = mem.u16(mem.ss_lin((r.di + 8) & M16))
                r.es, r.di = seg, off
                eligible = r.al != mem.u8(mem.addr(seg, off + 6)) and mem.ds8(0x830E) == 0
                if eligible:
                    r.ax = local16(mem, r, -2)
                    r.dx = 0x16
                    mul(r, r.dx)
                    r.di = r.ax
                    r.al = mem.ds8((r.di + 0x80EE) & M16)
                    eligible = r.al != mem.ds8(0x830A)
                if eligible:
                    r.store(stack=True)
                    yield call("0791:2996", ret_to="0791:33CB", far=False)
                    r = Regs(mem, resumed=True)
                    r.al = int(r.al == 0)
                    cbw(r)
                    r.di = r.ax
                    r.di = r.di << 1
                    r.si = r.di
                    r.di = (r.di << 1) + r.si
                    r.al = mem.ds8((r.di + 0x82E3) & M16)
                    cbw(r)
                    if s16(r.ax) < 0:
                        r.ax = -r.ax
                    r.cx = r.ax
                    r.ax = local16(mem, r, -2)
                    r.dx = 0x16
                    mul(r, r.dx)
                    r.di = r.ax
                    r.al = mem.ds8((r.di + 0x80E9) & M16)
                    cbw(r)
                    if s16(r.ax) < 0:
                        r.ax = -r.ax
                    eligible = s16(r.ax) > s16(r.cx)
                if eligible:
                    r.ax = local16(mem, r, -2)
                    r.dx = 0x16
                    mul(r, r.dx)
                    r.di = r.ax + 0x80E8
                    r.store(stack=True)
                    yield call("0791:2BE5", mem.DS, r.di, ret_to="0791:341A", far=True)
                    r = Regs(mem, resumed=True)
                    r.al = int(s8(r.al) > 0)
                    r.cx = (r.cx & 0xFF00) | r.al
                    r.ax = local16(mem, r, -2)
                    r.dx = 0x16
                    mul(r, r.dx)
                    r.di = r.ax
                    r.al = int(s8(mem.ds8((r.di + 0x80E9) & M16)) > 0)
                    if r.al == (r.cx & 0xFF):
                        r.ax = local16(mem, r, -2)
                        r.dx = 0x16
                        mul(r, r.dx)
                        r.di = r.ax
                        if mem.ds8((r.di + 0x80F8) & M16) == 0:
                            r.al = local8(mem, r, -2)
                            mem.wds8(0x830E, r.al, "0791:3455")
                            r.ax = local16(mem, r, -2)
                            r.dx = 0x16
                            mul(r, r.dx)
                            r.di = r.ax
                            r.ax = mem.ds16((r.di + 0x80E8) & M16)
                            mem.wds16(0x8317, r.ax, "0791:3466")
                            mem.wds8(0x8329, 0, "0791:3469")
                            break
                r.ax = local16(mem, r, -2)
                if r.ax == local16(mem, r, -4):
                    break
                r.local16(-2, local16(mem, r, -2) + 1)
    r.leave()
    r.store()


@PORTS.port("0791:3111", ret="retf 4")
def pick_pass_target(mem, variant):
    """3111–3322: descending distance preference, then ascending available fallback."""
    off, seg = mem.arg(0), mem.arg(1)
    r = Regs(mem)
    r.enter(0xE)
    r.ax = 3
    r.es, r.di = seg, off
    r.store(stack=True)
    yield call("0791:26D7", 3, seg, off, ret_to="0791:3124", far=True)
    r = Regs(mem, resumed=True)
    long_mode = r.al != 0
    if not long_mode:
        r.es, r.di = seg, off
        r.store(stack=True)
        yield call("0791:2C54", seg, off, ret_to="0791:3131", far=True)
        r = Regs(mem, resumed=True)
        if r.al != 0:
            r.es, r.di = seg, off
            r.al = mem.u8(mem.addr(seg, off + 6))
            r.ah = 0
            r.store(stack=True)
            yield call("0791:045D", r.ax, ret_to="0791:3142", far=False)
            r = Regs(mem, resumed=True)
            long_mode = r.al == 0
    r.al = int(long_mode)
    r.local8(-0xB, r.al)
    r.store(stack=True)
    yield call("0791:261A", ret_to="0791:3152", far=False)
    r = Regs(mem, resumed=True)
    r.dx = r.ax
    r.al = local8(mem, r, -0xB)
    cbw(r)
    r.di = r.ax
    r.al = mem.ds8((0x778 + r.di) & M16)
    r.ah = 0
    r.ax = r.ax + r.dx
    r.local16(-0xA, r.ax)
    r.es, r.di = seg, off
    r.al = mem.u8(mem.addr(seg, off + 6))
    r.ah = 0
    r.local16(-6, r.ax)
    r.ax = 2
    r.es, r.di = seg, off
    r.store(stack=True)
    yield call("0791:30EA", 2, seg, off, ret_to="0791:317E", far=True)
    r = Regs(mem, resumed=True)
    r.local16(-0xD, r.ax)
    r.ax = 11
    r.es, r.di = seg, off
    r.store(stack=True)
    yield call("0791:30EA", 11, seg, off, ret_to="0791:318E", far=True)
    r = Regs(mem, resumed=True)
    if r.ax >= local16(mem, r, -0xD):
        r.local16(-4, r.ax)
        while True:
            r.es, r.di = seg, off
            r.al = mem.u8(mem.addr(seg, off + 6))
            r.ah = 0
            eligible = r.ax != local16(mem, r, -4)
            if eligible:
                r.ax = local16(mem, r, -4)
                r.dx = 0x16
                mul(r, r.dx)
                r.di = r.ax + 0x80E8
                r.store(stack=True)
                yield call("0791:2956", mem.DS, r.di, ret_to="0791:31C3", far=True)
                r = Regs(mem, resumed=True)
                eligible = r.al == 0
            if eligible:
                r.ax = local16(mem, r, -4)
                r.dx = 0x16
                mul(r, r.dx)
                r.di = r.ax + 0x80E8
                r.store(stack=True)
                yield call("0791:2D10", 10, mem.DS, r.di, ret_to="0791:31E2", far=True)
                r = Regs(mem, resumed=True)
                eligible = r.al == 0
            if eligible:
                r.ax = local16(mem, r, -4)
                r.dx = 0x16
                mul(r, r.dx)
                r.di = r.ax
                eligible = mem.ds8((r.di + 0x80FA) & M16) != 13
            if eligible:
                r.ax = local16(mem, r, -0xA)
                r.local16(-8, r.ax)
                r.es, r.di = seg, off
                r.al = mem.u8(mem.addr(seg, off))
                cbw(r)
                r.cx = r.ax
                r.ax = local16(mem, r, -4)
                r.dx = 0x16
                mul(r, r.dx)
                r.di = r.ax
                r.al = mem.ds8((r.di + 0x80E8) & M16)
                cbw(r)
                r.ax = r.ax - r.cx
                if s16(r.ax) < 0:
                    r.ax = -r.ax
                r.bx = r.ax
                r.es, r.di = seg, off
                r.al = mem.u8(mem.addr(seg, off + 1))
                cbw(r)
                r.cx = r.ax
                r.ax = local16(mem, r, -4)
                r.dx = 0x16
                mul(r, r.dx)
                r.di = r.ax
                r.al = mem.ds8((r.di + 0x80E9) & M16)
                cbw(r)
                r.ax = r.ax - r.cx
                if s16(r.ax) < 0:
                    r.ax = -r.ax
                r.ax = r.ax + r.bx
                r.local16(-0xA, r.ax)
                r.al = int(r.ax > local16(mem, r, -8))
                accept = r.al == local8(mem, r, -0xB)
                if accept:
                    r.es, r.di = seg, off
                    r.al = mem.u8(mem.addr(seg, off + 6))
                    r.ah = 0
                    if r.ax != local16(mem, r, -6):
                        r.store(stack=True)
                        yield call("214B:06FA", ret_to="0791:3271", far=True)
                        r = Regs(mem, resumed=True)
                        accept = r.al != 0 or variant == "pass-always-replace"
                if accept:
                    r.ax = local16(mem, r, -4)
                    r.dx = 0x16
                    mul(r, r.dx)
                    r.di = r.ax
                    r.al = mem.ds8((r.di + 0x80EE) & M16)
                    r.ah = 0
                    r.local16(-6, r.ax)
                else:
                    r.ax = local16(mem, r, -8)
                    r.local16(-0xA, r.ax)
            r.ax = local16(mem, r, -4)
            if r.ax == local16(mem, r, -0xD):
                break
            r.local16(-4, local16(mem, r, -4) - 1)
    r.es, r.di = seg, off
    r.al = mem.u8(mem.addr(seg, off + 6))
    r.ah = 0
    if r.ax == local16(mem, r, -6):
        r.ax = 11
        r.es, r.di = seg, off
        r.store(stack=True)
        yield call("0791:30EA", 11, seg, off, ret_to="0791:32B6", far=True)
        r = Regs(mem, resumed=True)
        r.local16(-0xD, r.ax)
        r.ax = 2
        r.es, r.di = seg, off
        r.store(stack=True)
        yield call("0791:30EA", 2, seg, off, ret_to="0791:32C6", far=True)
        r = Regs(mem, resumed=True)
        if r.ax <= local16(mem, r, -0xD):
            r.local16(-4, r.ax)
            while True:
                r.es, r.di = seg, off
                r.al = mem.u8(mem.addr(seg, off + 6))
                r.ah = 0
                if r.ax != local16(mem, r, -4):
                    r.ax = local16(mem, r, -4)
                    r.dx = 0x16
                    mul(r, r.dx)
                    r.di = r.ax + 0x80E8
                    r.store(stack=True)
                    yield call("0791:2956", mem.DS, r.di, ret_to="0791:32F5", far=True)
                    r = Regs(mem, resumed=True)
                    if r.al == 0:
                        r.ax = local16(mem, r, -4)
                        r.dx = 0x16
                        mul(r, r.dx)
                        r.di = r.ax
                        r.al = mem.ds8((r.di + 0x80EE) & M16)
                        r.ah = 0
                        r.local16(-6, r.ax)
                r.ax = local16(mem, r, -4)
                if r.ax == local16(mem, r, -0xD):
                    break
                r.local16(-4, local16(mem, r, -4) + 1)
    r.ax = local16(mem, r, -6)
    r.local16(-2, r.ax)
    r.ax = local16(mem, r, -2)
    r.leave()
    r.store()


@PORTS.port("0791:384C", ret="retf 6")
def move_ball_to_slot(mem, variant):
    """384C–3B14: pass/dribble launch, signed adjustments and literal guest helpers."""
    off, seg, slot = mem.arg(0), mem.arg(1), mem.arg(2)
    r = Regs(mem)
    r.enter(4)
    if mem.ds8(0x830E) > 0:
        r.store(stack=True)
        yield call("0791:82EB", ret_to="0791:385C", far=False)
        r = Regs(mem, resumed=True)
        r.leave()
        r.store()
        return
    r.ax, r.dx = slot, 0x16
    mul(r, r.dx)
    r.di = r.ax
    r.ax = mem.ds16((r.di + 0x80E8) & M16)
    r.local16(-2, r.ax)
    point = r.ax
    r.ax, r.dx = slot, 0x16
    mul(r, r.dx)
    r.di = r.ax + 0x80E8
    r.store(stack=True)
    yield call("0791:2EB8", point, mem.DS, r.di, ret_to="0791:3887", far=True)
    r = Regs(mem, resumed=True)
    if r.al:
        r.leave()
        r.store()
        return
    r.es, r.di = seg, off
    r.al = mem.u8(mem.addr(seg, off + 6))
    r.ah = 0
    if r.ax == slot:
        r.store(stack=True)
        yield call("0791:261A", ret_to="0791:389F", far=False)
        r = Regs(mem, resumed=True)
        r.ax = r.ax + 1
        r.push(r.ax)                                           # 38A0: draw+1 survives direction call
        r.es, r.di = seg, off
        r.store(stack=True)
        yield call("0791:2BE5", seg, off, ret_to="0791:38AA", far=True)
        r = Regs(mem, resumed=True)
        cbw(r)
        r.dx = pop_word(mem, r)
        imul(r, r.dx)
        cwd(r)
        r.cx = 2
        value = s16(r.ax)
        quotient = abs(value) // 2 * (-1 if value < 0 else 1)
        r.ax, r.dx = quotient, value - quotient * 2
        r.local8(-1, local8(mem, r, -1) + r.al)
        mem.wds8(0x8303, 0, "0791:38B7")
    else:
        r.al = local8(mem, r, -1)
        cbw(r)
        if s16(r.ax) < 0:
            r.ax = -r.ax
        if s16(r.ax) < 25:
            r.ax, r.dx = slot, 0x16
            mul(r, r.dx)
            r.di = r.ax
            r.ax = mem.ds16((r.di + 0x80F5) & M16)
            r.dx = 20
            mul(r, r.dx)
            r.di, r.es = mem.ds16(0xA91B), mem.ds16(0xA91D)
            r.di = r.di + r.ax
            r.al = mem.u8(mem.addr(r.es, r.di + 6))
            r.ah = 0
            r.store(stack=True)
            yield call("214B:06B1", r.ax, ret_to="0791:38F2", far=True)
            r = Regs(mem, resumed=True)
            r.push(r.ax)                                       # 38F2: random distance survives direction call
            r.es, r.di = seg, off
            r.store(stack=True)
            yield call("0791:2BE5", seg, off, ret_to="0791:38FC", far=True)
            r = Regs(mem, resumed=True)
            cbw(r)
            r.dx = pop_word(mem, r)
            imul(r, r.dx)
            cwd(r)
            r.cx = 4
            value = s16(r.ax)
            quotient = abs(value) // 4 * (-1 if value < 0 else 1)
            r.ax, r.dx = quotient, value - quotient * 4
            r.local8(-1, local8(mem, r, -1) + r.al)
    r.ax, r.dx = slot, 0x16
    mul(r, r.dx)
    r.di = r.ax
    mem.wds8((r.di + 0x80FA) & M16, 5, "0791:3913")
    r.al = slot
    mem.wds8(0x830C, r.al, "0791:391B")
    point = local16(mem, r, -2)
    special = mem.ds8(0x80FA) != 0
    r.ax = 11 if special else 6
    r.es, r.di = seg, off
    r.store(stack=True)
    yield call("0791:34C1", point, r.ax, seg, off,
               ret_to="0791:3935" if special else "0791:3947", far=True)
    r = Regs(mem, resumed=True)
    r.ax = mem.ds16(0x8313)
    r.local16(-2, r.ax)
    r.es, r.di = seg, off
    r.al = mem.u8(mem.addr(seg, off + 6))
    r.ah = 0
    adjust = False
    if r.ax == slot and mem.ds16(0x82FE) != 0:
        r.ax = 3
        r.store(stack=True)
        yield call("214B:06D0", 3, ret_to="0791:3971", far=True)
        r = Regs(mem, resumed=True)
        adjust = r.al != 0
    if adjust:
        if mem.ds16(0x8300) > 2:
            r.ax = mem.ds16(0x8300)
            r.dx, r.cx = 0, 3
            r.ax, r.dx = r.ax // 3, r.ax % 3
            mem.wds16(0x8300, r.ax, "0791:3989")
        r.ax = mem.ds16(0x82F6)
        r.local16(-2, r.ax)
        r.store(stack=True)
        yield call("214B:06FA", ret_to="0791:3997", far=True)
        r = Regs(mem, resumed=True)
        cbw(r)
        r.di = r.ax
        r.al = mem.ds8((0x7920 + r.di) & M16)
        cbw(r)
        mem.wds16(0x82FC, r.ax, "0791:399F")
        r.al = int(s16(mem.ds16(0x82FE)) > 0)
        cbw(r)
        r.di = r.ax
        r.al = mem.ds8((0x7920 + r.di) & M16)
        cbw(r)
        mem.wds16(0x82FE, mem.ds16(0x82FE) + r.ax, "0791:39B7")
        r.ax = mem.ds16(0x8300)
        r.dx = 0
        r.cx, r.bx = r.ax, r.dx
        r.ax = mem.ds16(0x82FE)
        cwd(r)
        r.store(stack=True)
        yield call("23E4:0279", ret_to="0791:39CD", far=True)
        r = Regs(mem, resumed=True)
        r.local8(-1, local8(mem, r, -1) + r.al)
        r.ax = mem.ds16(0x8300)
        r.dx = 0
        r.cx, r.bx = r.ax, r.dx
        r.ax = mem.ds16(0x82FC)
        cwd(r)
        r.store(stack=True)
        yield call("23E4:0279", ret_to="0791:39E2", far=True)
        r = Regs(mem, resumed=True)
        r.local8(-2, local8(mem, r, -2) + r.al)
        point = local16(mem, r, -2)
        r.store(stack=True)
        yield call("0791:2DCA", point, ret_to="0791:39EB", far=False)
        r = Regs(mem, resumed=True)
        skill = False
        if r.al == 0:
            r.ax = 10
            r.es, r.di = seg, off
            r.store(stack=True)
            yield call("0791:287C", 10, seg, off, ret_to="0791:39FC", far=True)
            r = Regs(mem, resumed=True)
            skill = r.al != 0
        if skill:
            r.al = local8(mem, r, -2)
            cbw(r)
            if s16(r.ax) < 0:
                r.ax = -r.ax
            if s16(r.ax) > 8:
                r.ax = 0
                mem.wds16(0x82FC, 0, "0791:3A11")
            else:
                r.al = int(s16(mem.ds16(0x82FE)) < 0)
                cbw(r)
                r.di = r.ax
                r.al = mem.ds8((0x7920 + r.di) & M16)
                cbw(r)
                mem.wds16(0x82FE, mem.ds16(0x82FE) + r.ax, "0791:3A2B")
        r.ax = mem.ds16(0x82F6)
        r.local16(-2, r.ax)
        r.ax = mem.ds16(0x8300)
        r.dx = 0
        r.cx, r.bx = r.ax, r.dx
        r.ax = mem.ds16(0x82FE)
        cwd(r)
        r.store(stack=True)
        yield call("23E4:0279", ret_to="0791:3A47", far=True)
        r = Regs(mem, resumed=True)
        r.local8(-1, local8(mem, r, -1) + r.al)
        r.ax = mem.ds16(0x8300)
        r.dx = 0
        r.cx, r.bx = r.ax, r.dx
        r.ax = mem.ds16(0x82FC)
        cwd(r)
        r.store(stack=True)
        yield call("23E4:0279", ret_to="0791:3A5C", far=True)
        r = Regs(mem, resumed=True)
        r.local8(-2, local8(mem, r, -2) + r.al)
    r.di = 0x82F6
    r.store(stack=True)
    yield call("0791:835F", mem.DS, r.di, ret_to="0791:3A68", far=True)
    r = Regs(mem, resumed=True)
    high = r.ax > 20
    if not high:
        r.al = mem.ds8(0x830C)
        if r.al != mem.ds8(0x830B):
            r.di = 0x82F6
            r.store(stack=True)
            yield call("0791:835F", mem.DS, r.di, ret_to="0791:3A7F", far=True)
            r = Regs(mem, resumed=True)
            if r.ax > 10:
                r.store(stack=True)
                yield call("214B:06FA", ret_to="0791:3A89", far=True)
                r = Regs(mem, resumed=True)
                high = r.al != 0
    r.al = int(high)
    mem.wds8(0x8303, r.al, "0791:3A93")
    if mem.ds8(0x80FA) == 0:
        clear_slot = False
        if mem.ds8(0x830C) == 0:
            r.store(stack=True)
            yield call("214B:06FA", ret_to="0791:3AA9", far=True)
            r = Regs(mem, resumed=True)
            cbw(r)
            r.di = r.ax
            r.al = mem.ds8((0x786 + r.di) & M16)
            ret_to = "0791:3AB4"
        else:
            r.al = mem.ds8(0x830C)
            if r.al == mem.ds8(0x830B):
                point = local16(mem, r, -2)
                r.store(stack=True)
                yield call("0791:2DCA", point, ret_to="0791:3AC5", far=False)
                r = Regs(mem, resumed=True)
                cbw(r)
                r.di = r.ax
                r.al = mem.ds8((0x788 + r.di) & M16)
                ret_to = "0791:3AD0"
            elif mem.ds8(0x8327) == 8:
                r.al, ret_to = 3, "0791:3ADF"
            elif mem.ds8(0x8303) != 0:
                r.al, ret_to, clear_slot = 10, "0791:3AEE", True
            elif mem.ds8(0x8327) == 7:
                r.al, ret_to, clear_slot = 9, "0791:3B02", True
            else:
                r.al, ret_to = 8, "0791:3B0F"
        r.store(stack=True)
        yield call("0791:2AA3", r.ax, ret_to=ret_to, far=False)
        r = Regs(mem, resumed=True)
        if clear_slot:
            mem.wds8(0x830C, 0, "0791:3AEE" if ret_to == "0791:3AEE" else "0791:3B02")
    r.leave()
    r.store()


@PORTS.port("0791:34C1", ret="retf 8")
def launch_ball(mem, variant):
    """34C1–384B: launch vectors, event membership, skill/miscue, long arithmetic."""
    off, seg, event, target = (mem.arg(i) for i in range(4))
    r = Regs(mem)
    r.enter(6)
    r.es, r.di = seg, off
    mem.w8(mem.addr(seg, off + 0xF), 5, "0791:34CA")
    r.ax = target
    r.local16(-2, r.ax)
    mem.wds8(0x8302, 1, "0791:34D5")
    r.es, r.di = seg, off
    r.al = mem.u8(mem.addr(seg, off + 6))
    mem.wds8(0x830B, r.al, "0791:34E1")
    r.al = mem.ds8(0x82F6)
    r.local8(-2, local8(mem, r, -2) - r.al)
    r.al = mem.ds8(0x82F7)
    r.local8(-1, local8(mem, r, -1) - r.al)
    r.ax = 0
    mem.wds16(0x82FC, 0, "0791:34F2")
    r.ax = 0
    mem.wds16(0x82FE, 0, "0791:34F7")
    r.al = local8(mem, r, -1)
    cbw(r)
    if s16(r.ax) < 0:
        r.ax = -r.ax
    r.dx = r.ax
    r.al = local8(mem, r, -2)
    cbw(r)
    if s16(r.ax) < 0:
        r.ax = -r.ax
    if s16(r.ax) > s16(r.dx):
        r.al = int(s8(local8(mem, r, -2)) > 0)
        cbw(r)
        r.di = r.ax
        r.al = mem.ds8((0x7920 + r.di) & M16)
        cbw(r)
        if variant == "launch-reverse-x":
            r.ax = -r.ax
        mem.wds16(0x82FC, r.ax, "0791:3528")
        r.al = local8(mem, r, -2)
        cbw(r)
        if s16(r.ax) < 0:
            r.ax = -r.ax
        mem.wds16(0x8300, r.ax, "0791:3535")
        r.al = local8(mem, r, -2)
        cbw(r)
        if s16(r.ax) < 0:
            r.ax = -r.ax
        cwd(r)
        r.cx = 2
        value = s16(r.ax)
        r.ax, r.dx = value // 2, value % 2
        r.dx = r.ax
        r.al = local8(mem, r, -1)
        cbw(r)
        if s16(r.ax) < 0:
            r.ax = -r.ax
        if s16(r.ax) >= s16(r.dx):
            r.al = int(s8(local8(mem, r, -1)) > 0)
            cbw(r)
            r.di = r.ax
            r.al = mem.ds8((0x7920 + r.di) & M16)
            cbw(r)
            mem.wds16(0x82FE, r.ax, "0791:356C")
            r.al = local8(mem, r, -1)
            cbw(r)
            if s16(r.ax) < 0:
                r.ax = -r.ax
            mem.wds16(0x8300, mem.ds16(0x8300) + r.ax, "0791:3579")
    else:
        r.al = int(s8(local8(mem, r, -1)) > 0)
        cbw(r)
        r.di = r.ax
        r.al = mem.ds8((0x7920 + r.di) & M16)
        cbw(r)
        mem.wds16(0x82FE, r.ax, "0791:3594")
        r.al = local8(mem, r, -1)
        cbw(r)
        if s16(r.ax) < 0:
            r.ax = -r.ax
        mem.wds16(0x8300, r.ax, "0791:35A1")
        r.al = local8(mem, r, -2)
        cbw(r)
        if s16(r.ax) < 0:
            r.ax = -r.ax
        if s16(r.ax) > 0:
            r.al = local8(mem, r, -1)
            cbw(r)
            if s16(r.ax) < 0:
                r.ax = -r.ax
            cwd(r)
            r.cx = 2
            value = s16(r.ax)
            r.ax, r.dx = value // 2, value % 2
            r.dx = r.ax
            r.al = local8(mem, r, -2)
            cbw(r)
            if s16(r.ax) < 0:
                r.ax = -r.ax
            if s16(r.ax) >= s16(r.dx):
                r.al = int(s8(local8(mem, r, -2)) > 0)
                cbw(r)
                r.di = r.ax
                r.al = mem.ds8((0x7920 + r.di) & M16)
                cbw(r)
                if variant == "launch-reverse-x":
                    r.ax = -r.ax
                mem.wds16(0x82FC, r.ax, "0791:35E6")
                r.al = local8(mem, r, -2)
                cbw(r)
                if s16(r.ax) < 0:
                    r.ax = -r.ax
                mem.wds16(0x8300, mem.ds16(0x8300) + r.ax, "0791:35F3")
                r.al = local8(mem, r, -2)
                cbw(r)
                if s16(r.ax) < 0:
                    r.ax = -r.ax
                cwd(r)
                r.cx = 2
                value = s16(r.ax)
                r.ax, r.dx = value // 2, value % 2
                r.dx = r.ax
                r.al = local8(mem, r, -1)
                cbw(r)
                if s16(r.ax) < 0:
                    r.ax = -r.ax
                if s16(r.ax) >= s16(r.dx):
                    r.ax = mem.ds16(0x82FE) << 1
                    mem.wds16(0x82FE, r.ax, "0791:361C")
    if event == 6:
        if mem.ds16(0x8300) > 20:
            event = 7
            r.local16(0xA, event)                               # 362C writes the caller's event argument
        else:
            r.es, r.di = seg, off
            r.al = mem.u8(mem.addr(seg, off + 6))
            r.ah = 0
            r.store(stack=True)
            yield call("0791:045D", r.ax, ret_to="0791:3640", far=False)
            r = Regs(mem, resumed=True)
            if r.al:
                r.es, r.di = seg, off
                r.store(stack=True)
                yield call("0791:2EB8", mem.ds16(0x82F6), seg, off, ret_to="0791:3651", far=True)
                r = Regs(mem, resumed=True)
                if r.al:
                    event = 8
                    r.local16(0xA, event)                       # 3655
    r.al = event
    mem.wds8(0x8327, r.al, "0791:365D")
    r.al = event
    element = r.ax
    r.di = 0x3481
    r.store(stack=True)
    yield call("23E4:08DF", element, mem.seg(0x0791), r.di, ret_to="0791:366E", far=True)
    r = Regs(mem, resumed=True)
    kind = 1 if not (mem.reg("eflags") & 0x40) else 0
    if not kind:
        r.al = event
        element = r.ax
        r.di = 0x34A1
        r.store(stack=True)
        yield call("23E4:08DF", element, mem.seg(0x0791), r.di, ret_to="0791:36BE", far=True)
        r = Regs(mem, resumed=True)
        kind = 2 if not (mem.reg("eflags") & 0x40) else 0
    if kind:
        r.ax = mem.ds16(0x8300) + 5
        r.dx = 0
        bound = r.ax
        r.push(r.dx)
        r.push(r.ax)                                           # 3678/3679 or36C8/36C9 held across skill
        r.di = event
        r.al = mem.ds8((0x779 + r.di) & M16)
        r.ah = 0
        skill = r.ax
        r.es, r.di = seg, off
        r.store(stack=True)
        yield call("0791:278A", skill, seg, off,
                   ret_to="0791:368D" if kind == 1 else "0791:36DD", far=True)
        r = Regs(mem, resumed=True)
        if kind == 1:
            r.dx = r.ax
            r.es, r.di = seg, off
            r.al = mem.u8(mem.addr(seg, off + 0x11))
            r.ah = 0
            r.ax = r.ax + r.dx
        r.dx, r.cx = 0, 3
        value = r.ax
        r.ax, r.dx = value // 3, value % 3
        r.dx = 0
        value = r.ax
        r.sp = r.sp + 4                                       # full Call re-pushes the held bound
        r.store(stack=True)
        yield call("214B:0D56", 0, bound, 0, value,
                   ret_to="0791:36AA" if kind == 1 else "0791:36ED", far=True)
        r = Regs(mem, resumed=True)
        mem.wds16(0x8300, r.ax, "0791:36AA" if kind == 1 else "0791:36ED")
    elif event != 8 and mem.ds16(0x8300) > 1:
        r.al = mem.ds8(0x830B)
        if r.al != mem.ds8(0x830C):
            r.di = event
            r.al = mem.ds8((0x779 + r.di) & M16)
            r.ah = 0
            skill = r.ax
            r.es, r.di = seg, off
            r.store(stack=True)
            yield call("0791:287C", skill, seg, off, ret_to="0791:3725", far=True)
            r = Regs(mem, resumed=True)
            if r.al == 0:
                mem.wds8(0x830C, 0, "0791:372C")
                r.es, r.di = seg, off
                r.al = mem.u8(mem.addr(seg, off + 6))
                r.ah = 0
                r.store(stack=True)
                yield call("0791:045D", r.ax, ret_to="0791:373E", far=False)
                r = Regs(mem, resumed=True)
                if r.al == 0:
                    r.store(stack=True)
                    yield call("214B:06FA", ret_to="0791:374A", far=True)
                    r = Regs(mem, resumed=True)
                    if r.al != 0 or mem.ds8(0x8323) != 0:
                        r.ax = mem.ds16(0x8300)
                        r.dx, r.cx = 0, 2
                        value = r.ax
                        r.ax, r.dx = value // 2, value % 2
                        r.store(stack=True)
                        yield call("214B:06B1", r.ax, ret_to="0791:3765", far=True)
                        r = Regs(mem, resumed=True)
                        mem.wds16(0x8300, mem.ds16(0x8300) - r.ax, "0791:3765")
                    elif mem.ds16(0x82FC) == 0:
                        r.store(stack=True)
                        yield call("214B:06FA", ret_to="0791:3777", far=True)
                        r = Regs(mem, resumed=True)
                        cbw(r)
                        r.di = r.ax
                        r.al = mem.ds8((0x7920 + r.di) & M16)
                        cbw(r)
                        mem.wds16(0x82FC, r.ax, "0791:377F")
                        r.al = int(s16(mem.ds16(0x82FE)) > 0)
                        cbw(r)
                        r.di = r.ax
                        r.al = mem.ds8((0x7920 + r.di) & M16)
                        cbw(r)
                        mem.wds16(0x82FE, mem.ds16(0x82FE) + r.ax, "0791:3797")
                    else:
                        r.ax = mem.ds16(0x82FE)
                        if s16(r.ax) < 0:
                            r.ax = -r.ax
                        if r.ax == 1:
                            r.ax = 0
                            mem.wds16(0x82FE, 0, "0791:37AD")
                        else:
                            r.store(stack=True)
                            yield call("214B:06FA", ret_to="0791:37B7", far=True)
                            r = Regs(mem, resumed=True)
                            cbw(r)
                            r.di = r.ax
                            r.al = mem.ds8((0x7920 + r.di) & M16)
                            cbw(r)
                            mem.wds16(0x82FE, r.ax, "0791:37BF")
    mem.wds8(0x8323, 0, "0791:37C2")
    r.ax, r.dx = 2, 0
    r.push(r.dx)
    r.push(r.ax)                                               # 37CC/37CD held across long division
    r.ax = mem.ds16(0x82FE)
    if s16(r.ax) < 0:
        r.ax = -r.ax
    r.dx = r.ax
    r.ax = mem.ds16(0x82FC)
    if s16(r.ax) < 0:
        r.ax = -r.ax
    r.ax = r.ax + r.dx
    cwd(r)
    r.cx, r.bx = r.ax, r.dx
    r.ax, r.dx = mem.ds16(0x8300), 0
    r.store(stack=True)
    yield call("23E4:0294", ret_to="0791:37F3", far=True)
    r = Regs(mem, resumed=True)
    high, low = r.dx, r.ax
    r.sp = r.sp + 4
    r.store(stack=True)
    yield call("214B:0D56", 0, 2, high, low, ret_to="0791:37FA", far=True)
    r = Regs(mem, resumed=True)
    mem.wds16(0x8300, r.ax, "0791:37FA")
    r.ax = mem.ds16(0x82F6)
    mem.wds16(0x8313, r.ax, "0791:3800")
    r.ax, r.dx = mem.ds16(0x8300), 0
    r.cx, r.bx = r.ax, r.dx
    r.ax = mem.ds16(0x82FE)
    cwd(r)
    r.store(stack=True)
    yield call("23E4:0279", ret_to="0791:3815", far=True)
    r = Regs(mem, resumed=True)
    mem.wds8(0x8314, mem.ds8(0x8314) + r.al, "0791:3815")
    r.ax, r.dx = mem.ds16(0x8300), 0
    r.cx, r.bx = r.ax, r.dx
    r.ax = mem.ds16(0x82FC)
    cwd(r)
    r.store(stack=True)
    yield call("23E4:0279", ret_to="0791:382B", far=True)
    r = Regs(mem, resumed=True)
    mem.wds8(0x8313, mem.ds8(0x8313) + r.al, "0791:382B")
    r.ax = 1
    r.store(stack=True)
    yield call("214B:1EA1", 10, 1, ret_to="0791:383C", far=True)
    r = Regs(mem, resumed=True)
    parent = r.bp
    r.store(stack=True)
    yield call("0791:333F", parent, ret_to="0791:3840", far=False)
    r = Regs(mem, resumed=True)
    r.al = mem.ds8(0x830C)
    mem.wds8(0x830D, r.al, "0791:3843")
    r.leave()
    r.store()
