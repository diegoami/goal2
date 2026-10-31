"""Positioning, marking and leaders in GOAL.EXE segment 0791 (T63).

Translated from static/goal-exe/code/seg_0791_{03,04,07,08}.asm.  The
tables and the squad live in the match image; all calls across a listing call
instruction go through guest.call, including calls to another port here.
"""

from . import Registry
from .guest import call
from .mem import s8, s16

PORTS = Registry("positioning", "positioning, marking, and leaders (T63)")
PORTS.variant("depth-plus-one", "4532 permits an extra depth step")
PORTS.variant("marking-no-copy", "4B34 does not copy the selected marking target")
PORTS.variant("keeper-no-state", "4D6B leaves the keeper's chase state unchanged")


def rec(mem, pointer, stride, index):
    off = mem.ds16(pointer)
    seg = mem.ds16(pointer + 2)
    return mem.addr(seg, off + (stride * index & 0xffff))


def player(mem, index):
    return rec(mem, 0xA91B, 0x14, index)


def country(mem, index):
    return rec(mem, 0xA917, 0xBF, index)


def pitch(mem, slot):
    return mem.addr(mem.DS, 0x80E8 + 0x16 * slot)


def ptr(mem, address):
    return address & 0xffff, (address >> 4) & 0xffff


def argptr(mem):
    return mem.addr(mem.arg(1), mem.arg(0)), mem.arg(1), mem.arg(0)


def r8(mem, address, k):
    return mem.u8(address + k)


def r16(mem, address, k):
    return mem.u16(address + k)


def w8(mem, address, k, value, site):
    mem.w8(address + k, value, f"0791:{site}")


def w16(mem, address, k, value, site):
    mem.w16(address + k, value, f"0791:{site}")


def dsrec(mem, off):
    return mem.addr(mem.DS, off)


def push_word(mem, value, at):
    """Keep a listing push live across the next guest call, including its stack word."""
    sp = (mem.reg("sp") - 2) & 0xffff
    mem.w16(mem.ss_lin(sp), value, f"0791:{at}")
    mem.set_reg("sp", sp)


def pop_dx(mem):
    sp = mem.reg("sp")
    value = mem.u16(mem.ss_lin(sp))
    mem.set_reg("sp", (sp + 2) & 0xffff)
    mem.set_reg("dx", value)
    return value


def pop_ax(mem):
    sp = mem.reg("sp")
    value = mem.u16(mem.ss_lin(sp))
    mem.set_reg("sp", (sp + 2) & 0xffff)
    mem.set_reg("ax", value)
    return value


def drop_words(mem, count):
    """Hand pre-pushed arguments to a Call, which writes those same words at this SP."""
    mem.set_reg("sp", (mem.reg("sp") + 2 * count) & 0xffff)


def guest(mem, target, *args, at, far=True, ax=None, dx=None):
    if ax is not None:
        mem.set_reg("ax", ax & 0xffff)
    if dx is not None:
        mem.set_reg("dx", dx & 0xffff)
    result = yield call(target, *args, ret_to=f"0791:{at}", far=far)
    return result & 0xffff


def near(mem, target, *args, at, ax=None, dx=None):
    return (yield from guest(mem, f"0791:{target}", *args, at=at, far=False, ax=ax, dx=dx))


def same(mem, target, *args, at, ax=None, dx=None):
    """Listing's push cs; call near, a far-returning procedure in this segment."""
    return (yield from guest(mem, f"0791:{target}", *args, at=at, far=True, ax=ax, dx=dx))


def far(mem, target, *args, at, ax=None, dx=None):
    return (yield from guest(mem, target, *args, at=at, ax=ax, dx=dx))


def local_far(frame, off):
    return frame.u16(off + 2), frame.u16(off)


@PORTS.port("0791:4532", ret="ret 2")
def depth_step_attack(mem, variant):
    f = mem.enter(2, "0791:4532")
    f.w8(-1, 0, "0791:4538")
    parent = mem.frame(mem.arg(0))
    seg, off = local_far(parent, 6)
    p = mem.addr(seg, off)
    group = yield from same(mem, "42CB", seg, off, at="4549")
    push_word(mem, group, "4549")
    tactic = yield from same(mem, "26D7", 7, seg, off, at="455B", ax=7)
    group = pop_ax(mem)
    limit = mem.ds8(0x07DB + ((s8(tactic & 0xff) * 4 + group) & 0xffff))
    if s8(r8(mem, p, 0xc)) < limit + (variant == "depth-plus-one"):
        group = yield from same(mem, "42CB", seg, off, at="458D")
        if group == 1:
            yes = yield from same(mem, "2D10", 0, seg, off, at="45A2", ax=0)
            if not (yes & 0xff):
                yes = yield from same(mem, "26D7", 1, seg, off, at="45B7", ax=1)
                if not (yes & 0xff):
                    yes = yield from far(mem, "214B:06FA", at="45C0")
            f.w8(-1, bool(yes & 0xff), "0791:45CA")
        elif group == 2:
            yes = yield from same(mem, "2D10", 0, seg, off, at="45E4", ax=0)
            if not (yes & 0xff):
                yes = yield from same(mem, "26D7", 1, seg, off, at="45F9", ax=1)
            f.w8(-1, bool(yes & 0xff), "0791:4603")
        elif group == 3:
            yes = yield from same(mem, "2D10", 0x1e, seg, off, at="461E", ax=0x1e)
            if not (yes & 0xff):
                yes = yield from same(mem, "26D7", 7, seg, off, at="4633", ax=7)
            f.w8(-1, bool(yes & 0xff), "0791:463D")
    return (mem.reg("ax") & 0xff00) | f.u8(-1)


@PORTS.port("0791:4649", ret="ret 2")
def depth_step_defend(mem, variant):
    f = mem.enter(2, "0791:4649")
    f.w8(-1, 0, "0791:464F")
    parent = mem.frame(mem.arg(0))
    seg, off = local_far(parent, 6)
    p = mem.addr(seg, off)
    group = yield from same(mem, "42CB", seg, off, at="4660")
    push_word(mem, group, "4660")
    t6 = yield from same(mem, "26D7", 6, seg, off, at="4672", ax=6)
    push_word(mem, s8(t6 & 0xff) * 4, "4677")
    t5 = yield from same(mem, "26D7", 5, seg, off, at="4689", ax=5)
    pop_ax(mem)
    group = pop_ax(mem)
    limit = mem.ds8(0x07CB + ((s8(t5 & 0xff) * 8 + s8(t6 & 0xff) * 4 + group) & 0xffff))
    if s8(r8(mem, p, 0xc)) > limit:
        group = yield from same(mem, "42CB", seg, off, at="46BE")
        if group == 1:
            yes = yield from same(mem, "2D6D", 0xf, seg, off, at="46D4", ax=0xf)
            f.w8(-1, yes, "0791:46D4")
        elif group == 2:
            yes = yield from same(mem, "2D6D", 0, seg, off, at="46EE", ax=0)
            f.w8(-1, yes, "0791:46EE")
        elif group == 3:
            yes = yield from same(mem, "2D10", 10, seg, off, at="4709", ax=10)
            if yes & 0xff:
                slot = yield from same(mem, "2BB1", seg, off, at="471A")
                if slot & 0xff != 2:
                    yes = r8(mem, player(mem, r16(mem, p, 0xd)), 6) == 1
                else:
                    yes = True
            else:
                yes = True
            f.w8(-1, bool(yes), "0791:4741")
    return (mem.reg("ax") & 0xff00) | f.u8(-1)


@PORTS.port("0791:474D", ret="retf 4")
def adjust_depth_offset(mem, variant):
    p, seg, off = argptr(mem)
    f = mem.enter(2, "0791:474D")
    own = yield from same(mem, "2B51", seg, off, at="475C")
    attack = bool(own & 0xff)
    if attack:
        position = r8(mem, player(mem, r16(mem, p, 0xd)), 6)
        if position <= 4:
            ahead = yield from same(mem, "2D10", 0, seg, off, at="4785", ax=0)
            attack = bool(ahead & 0xff)
    if attack:
        step = yield from near(mem, "4532", f.bp, at="478D")
        w8(mem, p, 0xc, r8(mem, p, 0xc) + (step & 0xff), "4790")
    else:
        step = yield from near(mem, "4649", f.bp, at="479A")
        w8(mem, p, 0xc, r8(mem, p, 0xc) - (step & 0xff), "479D")
        slot = yield from same(mem, "2BB1", seg, off, at="47AA")
        if slot & 0xff == 2:
            w8(mem, p, 0xb, -s8(r8(mem, p, 9)), "47BB")
    return None


@PORTS.port("0791:4D3F", ret="retf 4")
def begin_chase(mem, variant):
    p, seg, off = argptr(mem)
    mem.enter(0, "0791:4D3F")
    keeper = yield from near(mem, "045D", r8(mem, p, 6), at="4D4F", ax=r8(mem, p, 6))
    if keeper & 0xff:
        goal = yield from same(mem, "2EB8", r16(mem, p, 0), seg, off, at="4D62")
        if not goal & 0xff:
            return None
    if variant != "keeper-no-state":
        w8(mem, p, 0x12, 0xd, "4D6B")
    w16(mem, p, 7, r16(mem, p, 0), "4D79")
    draw = yield from near(mem, "261A", at="4D80")
    w8(mem, p, 0x10, draw + 4, "4D86")
    keeper = yield from near(mem, "045D", r8(mem, p, 6), at="4D97", ax=r8(mem, p, 6))
    if keeper & 0xff:
        w8(mem, p, 0x10, r8(mem, p, 0x10) + 10, "4D9E")
    return None


@PORTS.port("0791:42CB", ret="retf 4")
def position_group(mem, variant):
    p, seg, off = argptr(mem)
    f = mem.enter(6, "0791:42CB")
    idx = r16(mem, p, 0xd)
    r = player(mem, idx)
    f.w16(-6, (mem.ds16(0xA91B) + idx * 0x14) & 0xffff, "0791:42E3")
    f.w16(-4, mem.ds16(0xA91D), "0791:42E6")
    pos = r8(mem, r, 6)
    if pos == 0:
        group = 4
        f.w16(-2, group, "0791:42F3")
    else:
        flag = 1
        if pos <= 11:
            tactic = yield from same(mem, "26D7", 1, seg, off, at="4311", ax=1)
            if not tactic & 0xff:
                flag = 0
            else:
                own = yield from same(mem, "2B51", seg, off, at="431E")
                flag = bool(own & 0xff)
        group = mem.ds8(0x07BA + (2 if pos > 4 else 0) + flag)
        f.w16(-2, group, "0791:4348")
    return group


@PORTS.port("0791:4354", ret="retf 4")
def set_destination_from_post(mem, variant):
    p, seg, off = argptr(mem)
    mem.enter(0, "0791:4354")
    pos = r8(mem, player(mem, r16(mem, p, 0xd)), 6)
    if pos == 0:
        w8(mem, p, 0xb, 0, "4374")
    else:
        if pos == 13 and r8(mem, p, 0x12) != 9:
            draw = yield from far(mem, "214B:06B1", 15, at="43A7", ax=15)
            w8(mem, p, 0xb, draw - 8, "43AD")
        else:
            site = "4392" if pos == 13 else "43BC"
            write = "4398" if pos == 13 else "43C2"
            draw = yield from far(mem, "214B:06B1", 5, at=site, ax=5)
            w8(mem, p, 0xb, draw - 3, write)
    if s8(r8(mem, p, 0xc)) < 2:
        half = int(s8(r8(mem, p, 9)) / 2)
        w8(mem, p, 0xb, r8(mem, p, 0xb) - half, "43E1")
    w8(mem, p, 8, s8(r8(mem, p, 10)) + s8(r8(mem, p, 0xc)), "43FC")
    w8(mem, p, 7, s8(r8(mem, p, 9)) + s8(r8(mem, p, 0xb)), "4417")
    mirrored = yield from same(mem, "2C86", r16(mem, p, 7), seg, off, at="442B")
    w16(mem, p, 7, mirrored, "442E")
    return None


@PORTS.port("0791:4438", ret="retf 6")
def near_post_zone(mem, variant):
    p, seg, off = argptr(mem)
    point = mem.arg(2)
    f = mem.enter(4, "0791:4438")
    f.w16(-3, r16(mem, p, 9), "0791:4445")
    if r8(mem, p, 0x12) != 9:
        position = r8(mem, player(mem, r16(mem, p, 0xd)), 6)
        f.w8(-2, f.u8(-2) + mem.ds8(0x07BE + position), "0791:4470")
    close = abs(s8(point & 0xff) - s8(f.u8(-3))) < 4
    if close:
        direction = yield from same(mem, "2BE5", seg, off, at="4493")
        close = abs(s8((point >> 8) & 0xff) - s8(f.u8(-2)) * s8(direction & 0xff)) < 9
    f.w8(-1, close, "0791:44B5")
    return (mem.reg("ax") & 0xff00) | f.u8(-1)


@PORTS.port("0791:44C1", ret="retf 6")
def near_player_zone(mem, variant):
    p, seg, off = argptr(mem)
    point = mem.arg(2)
    f = mem.enter(2, "0791:44C1")
    close = False
    if r8(mem, p, 0x12) != 13 and r8(mem, p, 6) != mem.ds8(0x830B):
        close = abs(s8(point & 0xff) - s8(r8(mem, p, 0))) < 4
        if close:
            direction = yield from same(mem, "2BE5", seg, off, at="4500")
            close = abs(s8((point >> 8) & 0xff) - s8(r8(mem, p, 1)) * s8(direction & 0xff)) < 6
    f.w8(-1, close, "0791:4526")
    return (mem.reg("ax") & 0xff00) | f.u8(-1)


@PORTS.port("0791:47C5", ret="ret 2")
def choose_marking_target(mem, variant):
    f = mem.enter(12, "0791:47C5")
    parent = mem.frame(mem.arg(0))
    seg, off = local_far(parent, 6)
    p = mem.addr(seg, off)
    side = yield from near(mem, "2996", at="47CE")
    country_id = mem.ds16(0x9B34 + 2 * s8(side & 0xff))
    c = country(mem, country_id)
    f.w16(-12, (mem.ds16(0xA917) + 0xBF * country_id) & 0xffff, "0791:47E2")
    f.w16(-10, mem.ds16(0xA919), "0791:47E5")
    f.w8(-1, 0, "0791:47E8")
    side = yield from near(mem, "2996", at="47EF")
    side &= 0xff
    f.w8(-8, side, "0791:47EF")
    base = mem.ds8(0x0668 + (side == 0))
    mark_off = 0x9A3E + (side == 0) * 0x28 + 2 * ((r8(mem, p, 6) - base) & 0xffff)
    mark = mem.ds16(mark_off)
    f.w16(-7, mark, "0791:4836")
    if mark == 0:
        f.w16(-3, 2, "0791:483F")
        for slot in range(2, 12):
            player_id = r16(mem, c, (slot - 1) * 2)
            unavailable = yield from far(mem, "1771:3216", player_id, at="485D")
            if not unavailable & 0xff:
                opponent = pitch(mem, mem.ds8(0x0668 + side) + slot)
                point = r16(mem, opponent, 0)
                within = yield from same(mem, "4438", point, seg, off, at="4888")
                if within & 0xff:
                    mark = player_id
                    f.w16(-7, mark, "0791:489A")
            f.w16(-3, slot + 1, "0791:489D")
    if mark:
        f.w16(-3, 2, "0791:48AB")
        for slot in range(2, 12):
            player_id = r16(mem, c, (slot - 1) * 2)
            if player_id != mark:
                f.w16(-3, slot + 1, "0791:49D3")
                continue
            unavailable = yield from far(mem, "1771:3216", player_id, at="48E2")
            if unavailable & 0xff:
                f.w16(-3, slot + 1, "0791:49D3")
                continue
            opp_slot = mem.ds8(0x0668 + side) + slot
            parent.w16(-4, opp_slot, "0791:48FB")
            opponent = pitch(mem, opp_slot)
            parent.w16(-2, r16(mem, opponent, 0), "0791:4914")
            keeper_area = yield from same(mem, "2C54", mem.DS, (0x80E8 + 0x16 * opp_slot) & 0xffff,
                                          at="4930")
            if keeper_area & 0xff:
                return (mem.reg("ax") & 0xff00)
            f.w16(-5, 1, "0791:4937")
            ours = yield from same(mem, "278A", 5, seg, off, at="494D")
            push_word(mem, ours, "494D")
            theirs = yield from same(mem, "278A", 8, mem.DS, (0x80E8 + 0x16 * opp_slot) & 0xffff,
                                     at="496A")
            ours = pop_dx(mem)
            if theirs > ours:
                ours = yield from same(mem, "278A", 5, seg, off, at="4980")
                push_word(mem, ours, "4980")
                theirs = yield from same(mem, "278A", 8, mem.DS, (0x80E8 + 0x16 * opp_slot) & 0xffff,
                                         at="499D")
                ours = pop_dx(mem)
                f.w16(-5, ((theirs - ours) & 0xffff) // 16 + 1, "0791:49A7")
            draw = yield from far(mem, "214B:06B1", f.u16(-5), at="49B2")
            push_word(mem, draw, "49B2")
            direction = yield from same(mem, "2BE5", seg, off, at="49C0")
            draw = pop_dx(mem)
            parent.w8(-1, parent.u8(-1) - s8(direction & 0xff) * s8(draw & 0xff), "0791:49C7")
            f.w8(-1, 1, "0791:49CB")
            return (mem.reg("ax") & 0xff00) | 1
        mem.wds16(mark_off, 0, "0791:4A1B")
    return (mem.reg("ax") & 0xff00) | f.u8(-1)


@PORTS.port("0791:4A28", ret="retf 4")
def update_marking_destination(mem, variant):
    p, seg, off = argptr(mem)
    f = mem.enter(8, "0791:4A28")
    player_id = r16(mem, p, 0xd)
    r = player(mem, player_id)
    f.w16(-8, (mem.ds16(0xA91B) + player_id * 0x14) & 0xffff, "0791:4A40")
    f.w16(-6, mem.ds16(0xA91D), "0791:4A43")
    own = yield from same(mem, "2B51", seg, off, at="4A4F")
    if own & 0xff:
        gate = yield from same(mem, "2B7B", seg, off, at="4A5C")
        set_post = bool(gate & 0xff)
        if not set_post and r8(mem, r, 6) == 1:
            ahead = yield from same(mem, "2D10", 10, seg, off, at="4A77")
            set_post = not bool(ahead & 0xff)
        if set_post:
            yield from same(mem, "4354", seg, off, at="4A84")
        return None
    yield from same(mem, "4354", seg, off, at="4A90")
    keeper = yield from near(mem, "045D", r8(mem, p, 6), at="4A9D")
    if keeper & 0xff:
        if mem.ds8(0x8325):
            area = yield from same(mem, "2E36", mem.ds16(0x82F6), seg, off, at="4AB5")
            if not area & 0xff:
                tactic = yield from same(mem, "26D7", 1, seg, off, at="4AC6")
                if tactic & 0xff:
                    area = yield from near(mem, "40BC", at="4ACD")
            if area & 0xff:
                w16(mem, p, 7, mem.ds16(0x82F6), "4AD7")
        return None
    target = yield from near(mem, "47C5", f.bp, at="4AE1")
    if not target & 0xff:
        return None
    if not mem.ds8(0x8325) and mem.ds8(0x830B) == f.u16(-4):
        return None
    draw = yield from far(mem, "214B:06B1", 6, at="4AFF")
    if s8(r8(mem, r, 0xe)) <= s16(draw):
        return None
    tactic = yield from same(mem, "26D7", 5, seg, off, at="4B1A")
    if not tactic & 0xff:
        direction = yield from same(mem, "2BE5", seg, off, at="4B27")
        if s8(f.u8(-1)) * s8(direction & 0xff) >= 0:
            return None
    if variant != "marking-no-copy":
        w16(mem, p, 7, f.u16(-2), "4B3A")
    return None


@PORTS.port("0791:4B64", ret="retf 4")
def update_player_destination(mem, variant):
    p, seg, off = argptr(mem)
    mem.enter(0, "0791:4B64")
    keeper = yield from near(mem, "045D", r8(mem, p, 6), at="4B74", ax=r8(mem, p, 6))
    if keeper & 0xff:
        dest = yield from same(mem, "2C86", r16(mem, p, 9), seg, off, at="4B88")
        w16(mem, p, 7, dest, "4B8B")
        return None
    state = r8(mem, p, 0x12)
    special = state == 9
    if state == 11:
        direction = yield from same(mem, "2BE5", seg, off, at="4BB2")
        special = s16(s8(mem.ds8(0x82F7)) * s8(direction & 0xff)) > 20
    if special:
        own = yield from same(mem, "2B51", seg, off, at="4BCC")
        if own & 0xff:
            player_id = r16(mem, p, 0xd)
            position = r8(mem, player(mem, player_id), 6)
            ax = ((player_id * 0x14) & 0xff00) | position
            yield from far(mem, "23E4:08DF", ax, mem.seg(0x0791), 0x4B44, at="4BF1", ax=ax)
            absent = bool(mem.reg("eflags") & 0x40)
            if absent:
                draw = yield from near(mem, "261A", at="4C14")
                w8(mem, p, 0xc, 0x26 - s8(r8(mem, p, 10)) - draw, "4C2A")
            else:
                draw = yield from near(mem, "261A", at="4BF6")
                w8(mem, p, 0xc, abs(s8(r8(mem, p, 10))) + draw, "4C0B")
        else:
            draw = yield from near(mem, "261A", at="4C33")
            w8(mem, p, 0xc, -0x26 - s8(r8(mem, p, 10)) + draw, "4C49")
    else:
        own = yield from same(mem, "2B51", seg, off, at="4C59")
        if own & 0xff:
            push_word(mem, 0, "4C62")
            push_word(mem, 20, "4C63")
        group = yield from same(mem, "42CB", seg, off, at="4C6D" if own & 0xff else "4CCA")
        if own & 0xff:
            push_word(mem, group, "4C6D")
            t7 = yield from same(mem, "26D7", 7, seg, off, at="4C7B", ax=7)
            group = pop_ax(mem)
            limit = mem.ds8(0x07DB + ((s8(t7 & 0xff) * 4 + group) & 0xffff))
            # 0D56 pops all four long-argument words; Call writes the two already
            # pushed at 4C62/4C63 again at their original addresses.
            drop_words(mem, 2)
            maximum = yield from far(mem, "214B:0D56", 0, 20, 0, limit, at="4C94", ax=limit, dx=0)
            w8(mem, p, 0xc, maximum, "4C97")
            ahead = yield from same(mem, "2D6D", 0x28, seg, off, at="4CA8", ax=0x28)
            if ahead & 0xff:
                direction = yield from same(mem, "2BE5", seg, off, at="4CB5")
                w8(mem, p, 0xc, -s8(direction & 0xff), "4CBB")
        else:
            push_word(mem, group, "4CCA")
            t6 = yield from same(mem, "26D7", 6, seg, off, at="4CD8", ax=6)
            push_word(mem, s8(t6 & 0xff) * 4, "4CDD")
            t5 = yield from same(mem, "26D7", 5, seg, off, at="4CEB", ax=5)
            pop_ax(mem)
            group = pop_ax(mem)
            limit = mem.ds8(0x07CB + ((s8(t5 & 0xff) * 8 + s8(t6 & 0xff) * 4 + group) & 0xffff))
            w8(mem, p, 0xc, limit, "4CFF")
            # The destination pointer and zero lower bound are pushed before
            # 0D1C computes the upper bound, and stay live under that guest call.
            push_word(mem, seg, "4D0A")
            push_word(mem, (off + 0xc) & 0xffff, "4D0B")
            push_word(mem, 0, "4D0E")
            ball_limit = abs(s8(mem.ds8(0x82F7))) * 2
            upper = yield from far(mem, "214B:0D1C", 0, 42, (ball_limit >> 16) & 0xffff,
                                   ball_limit & 0xffff, at="4D2A", ax=ball_limit & 0xffff,
                                   dx=(ball_limit >> 16) & 0xffff)
            drop_words(mem, 3)
            yield from far(mem, "214B:2031", seg, (off + 0xc) & 0xffff, 0, upper,
                           at="4D30", ax=upper)
    yield from same(mem, "4A28", seg, off, at="4D39")
    return None


@PORTS.port("0791:1F3C", ret="ret 2")
def best_leader_available(mem, variant):
    f = mem.enter(12, "0791:1F3C")
    side = s8(mem.arg(0) & 0xff)
    c = country(mem, mem.ds16(0x9B34 + 2 * side))
    f.w16(-12, (mem.ds16(0xA917) + mem.ds16(0x9B34 + 2 * side) * 0xBF) & 0xffff, "0791:1F59")
    f.w16(-10, mem.ds16(0xA919), "0791:1F5C")
    f.w16(-8, 0xffff, "0791:1F5F")
    f.w16(-4, 1, "0791:1F64")
    for slot in range(1, 12):
        f.w16(-4, slot, "0791:1F6B")
        player_id = r16(mem, c, 2 * (slot - 1))
        unavailable = yield from far(mem, "1771:3216", player_id, at="1F81")
        if unavailable & 0xff:
            continue
        score = yield from far(mem, "1771:30D9", player_id, at="1F98")
        best = f.u16(-8)
        if s16(best) < 0 or best < score:
            f.w16(-6, player_id, "0791:1FBA")
            score = yield from far(mem, "1771:30D9", f.u16(-6), at="1FC5")
            f.w16(-8, score, "0791:1FC5")
    # The listing reads BP-6 even if all eleven were unavailable (1FCE).
    f.w16(-2, f.u16(-6), "0791:1FD1")
    return f.u16(-2)


@PORTS.port("0791:1FDD", ret="ret 6")
def pick_marker_by_skill(mem, variant):
    f = mem.enter(8, "0791:1FDD")
    slot, element, side = mem.arg(0), mem.arg(1), s8(mem.arg(2) & 0xff)
    mark_off = 0x9976 + side * 10 + slot * 2
    mem.wds16(mark_off, 0, "0791:1FF9")
    start = mem.ds8(0x0764 + (slot == 5)) + 1
    if start > 11:
        return None
    for candidate in range(start, 12):
        f.w16(-2, candidate, "0791:201B")
        pitch_slot = mem.ds8(0x0668 + side) + candidate
        f.w16(-4, pitch_slot, "0791:2032")
        rec = pitch(mem, pitch_slot)
        f.w16(-8, (0x80E8 + 0x16 * pitch_slot) & 0xffff, "0791:2043")
        f.w16(-6, mem.DS, "0791:2046")
        player_id = r16(mem, rec, 0xd)
        unavailable = yield from far(mem, "1771:3216", player_id, at="2055")
        if unavailable & 0xff:
            continue
        winner = mem.ds16(mark_off)
        if winner:
            push_word(mem, element, "2074")
            winner_slot = yield from near(mem, "A920", winner, at="2092")
            drop_words(mem, 1)
            incumbent = yield from same(mem, "278A", element, mem.DS,
                                        (0x80E8 + 0x16 * winner_slot) & 0xffff, at="20A3")
            push_word(mem, incumbent, "20A3")
            challenger = yield from same(mem, "278A", element, mem.DS,
                                         (0x80E8 + 0x16 * pitch_slot) & 0xffff, at="20B0")
            incumbent = pop_dx(mem)
            if challenger <= incumbent:
                continue
        mem.wds16(mark_off, player_id, "0791:20D0")
    return None


@PORTS.port("0791:20E3", ret="ret")
def assign_marking_slots(mem, variant):
    f = mem.enter(12, "0791:20E3")
    f.w8(-1, 0, "0791:20E9")
    for side in range(2):
        f.w8(-1, side, "0791:20EF")
        country_id = mem.ds16(0x9B34 + 2 * side)
        c = country(mem, country_id)
        f.w16(-8, (mem.ds16(0xA917) + 0xBF * country_id) & 0xffff, "0791:2109")
        f.w16(-6, mem.ds16(0xA919), "0791:210C")
        managed = yield from far(mem, "1771:0B77", country_id, at="2120")
        f.w8(-2, managed & 0xff, "0791:2120")
        captain_off = 0x9978 + side * 10
        if not managed & 0xff or not mem.ds8(0x0C1F):
            if not managed & 0xff:
                captain = yield from near(mem, "1F3C", side, at="213D")
                mem.wds16(captain_off, captain, "0791:214A")
            for k in range(2, 6):
                f.w16(-4, k, "0791:214E")
                yield from near(mem, "1FDD", side, mem.ds8(0x0764 + k), k, at="216C")
        else:
            captain = mem.ds16(captain_off)
            unavailable = yield from far(mem, "1771:3216", captain, at="218F")
            prompt = bool(unavailable & 0xff)
            if not prompt:
                slot = yield from near(mem, "6B65", side, 1, at="219E")
                prompt = slot > 11
            if prompt:
                captain = yield from near(mem, "CC7B", side, 1, at="21AD", ax=1)
                mem.wds16(captain_off, captain, "0791:21BA")
        for k in range(1, 12):
            f.w16(-4, k, "0791:21BE")
            rec = pitch(mem, mem.ds8(0x0668 + side) + k)
            f.w16(-12, (0x80E8 + 0x16 * (mem.ds8(0x0668 + side) + k)) & 0xffff, "0791:21E2")
            f.w16(-10, mem.DS, "0791:21E5")
            leadership = yield from far(mem, "1771:30D9", mem.ds16(captain_off), at="21FC")
            w8(mem, rec, 0x11, r8(mem, rec, 0x11) + ((leadership << 1) & 0xff), "2201")
    return None


@PORTS.port("0791:2218", ret="ret 2")
def swap_squad_slots(mem, variant):
    f = mem.enter(4, "0791:2218")
    parent = mem.frame(mem.arg(0))
    side = s8(parent.u8(-1))
    i, j = parent.u16(-5), parent.u16(-3)
    country_id = mem.ds16(0x9B34 + 2 * side)
    c_off = (mem.ds16(0xA917) + country_id * 0xBF) & 0xffff
    c_seg = mem.ds16(0xA919)
    f.w16(-4, c_off, "0791:2239")
    f.w16(-2, c_seg, "0791:223C")
    yield from far(mem, "214B:007B", c_seg, (c_off + 2 * (j - 1)) & 0xffff,
                   c_seg, (c_off + 2 * (i - 1)) & 0xffff, 2, at="2270", ax=2)
    yield from far(mem, "214B:007B", mem.DS, (0x9B07 + side * 0x14 + j) & 0xffff,
                   mem.DS, (0x9B07 + side * 0x14 + i) & 0xffff, 1, at="22B9", ax=1)
    yield from far(mem, "214B:007B", mem.DS, (0x9A3E + side * 0x28 + 2 * j) & 0xffff,
                   mem.DS, (0x9A3E + side * 0x28 + 2 * i) & 0xffff, 2, at="2306", ax=2)
    return None


@PORTS.port("0791:419C", ret="ret")
def assign_start_posts(mem, variant):
    f = mem.enter(12, "0791:419C")
    # 41A2 reads the pre-existing local side before 41B2 initializes it.
    previous = mem.ds8(0x0668 + s8(f.u8(-1))) + 1
    f.w16(-5, previous, "0791:41AF")
    f.w8(-1, 0, "0791:41B2")
    for side in range(2):
        f.w8(-1, side, "0791:41B8")
        base = mem.ds8(0x0668 + side)
        f.w16(-7, base + 11, "0791:41CA")
        for slot in range(base + 1, base + 12):
            f.w16(-3, slot, "0791:41E2")
            r = pitch(mem, slot)
            f.w16(-11, (0x80E8 + 0x16 * slot) & 0xffff, "0791:41F8")
            f.w16(-9, mem.DS, "0791:41FB")
            position = r8(mem, player(mem, r16(mem, r, 0xd)), 6)
            w16(mem, r, 9, mem.ds16(0x079E + 2 * position), "4221")
            previous = f.u16(-5)
            if base + 1 < slot and r16(mem, pitch(mem, previous), 9) == r16(mem, r, 9):
                prev = pitch(mem, previous)
                x = s8(r8(mem, r, 9))
                if abs(x) <= 4:
                    w8(mem, r, 9, x + 3, "4299")
                    w8(mem, prev, 9, r8(mem, prev, 9) - 3, "42A8")
                else:
                    direction = s8(mem.ds8(0x7920 + (x > 0)))
                    w8(mem, r, 9, x - direction * 3, "4281")
                    w8(mem, prev, 10, r8(mem, prev, 10) - 3, "428F")
            f.w16(-5, slot, "0791:42B0")
    return None
