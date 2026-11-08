"""T121 (#427): route_fixture, its gate/watch prompt and competition news.

[confirmed: F010/F030/F039, ab6ade71; named/seg_000E_01.c, _04.c, _05.c,
named/seg_0791_13.c, then code/seg_000E_01.asm 038E-0838,
seg_000E_07.asm 5978-5A1C, seg_000E_08.asm 6685-6866,
seg_000E_09.asm 6C21-7071 and seg_0791_23.asm E80D-E926].
The comments name listing offsets. Calls retain their arguments, return addresses
and near/far forms. In particular 6C21 and silent.6970 see the real parent BP;
strings leave their result pointers on the stack until the consuming call.
"""
from . import Registry
from .contests import ss8, ss16, pop
from .geometry import cbw, mul
from .restarts import _end
from .runtime import Regs, add_flags
from .setup import guest, farg, member, rb, rw, w8, w16
from .silent import save_ptr, country_of, _ds_far, _fixture_at_cursor

PORTS = Registry("route", "route_fixture 6CA7, gate 6C21, watch E80D, competition news 6685 and helpers (T121)")
PORTS.variant("finals-mark-dropped", "6E75: the kinds 3/7 finals mark stored as zero")
PORTS.variant("confidence-managed-only", "6F44: wrongly omit confidence for the unmanaged side")
PORTS.variant("news-second-draw-dropped", "6809: omit the second mandatory news draw")
M16 = 0xFFFF


def at(off):
    return f"000E:{off:04X}"


def near(mem, r, target, *args, ret):
    return (yield from guest(mem, r, at(target), *args, ret=at(ret), far=False))


def far(mem, r, target, *args, ret):
    return (yield from guest(mem, r, target, *args, ret=at(ret)))


def side_country(mem, r, fx, side):
    r.al = side
    cbw(r)
    r.ax = r.ax << 1
    r.es, r.di = fx
    r.di += r.ax
    return rw(mem, r, 4)


def continent(mem, r, word):
    country_of(mem, r, word)
    r.al = rb(mem, r, 0x2C)
    r.ah = 0
    r.di = r.ax
    return r.ax


@PORTS.port("000E:6C21", ret="ret 4")
def maybe_ask_watch_match(mem, variant):
    r = Regs(mem)
    r.enter(6)                                                   # 6C21
    game = _ds_far(mem, r, 0xA923)
    save_ptr(r, -5)
    parent = ss16(mem, r, r.bp + 4)
    r.di = parent
    if ss8(mem, r, parent - 2):                                  # 6C34
        r.di = 0xA96A
        r = yield from far(mem, r, "214B:0329", mem.DS, 0x14A6, mem.DS, r.di, ret=0x6C4A)
        r = yield from far(mem, r, "214B:08DD", ret=0x6C4F)
    if ss8(mem, r, r.bp + 6):                                    # 6C4F
        fx = _fixture_at_cursor(mem, r, game)
        r = yield from far(mem, r, "0791:E80D", *fx, ret=0x6C71)
        if not r.al:
            r.al = 0
            r.local8(-1, r.al)
            return _end(r, value=True)
    r.al = 1
    r.local8(-1, r.al)
    return _end(r, value=True)


@PORTS.port("000E:6CA7", ret="ret")
def route_fixture(mem, variant):
    r = Regs(mem)
    r.enter(0x16)                                                # 6CA7
    game = _ds_far(mem, r, 0xA923)
    save_ptr(r, -0x10)
    r.ax = rw(mem, r, 0x26)
    r.local16(-6, r.ax)
    r.local8(-2, 0)
    r.es, r.di = game
    r.di += 0x4E
    dest = r.es, r.di
    r.ax = 0
    r = yield from far(mem, r, "214B:0018", *dest, 6, r.ax, ret=0x6CDA)
    r.di = r.bp - 0xC
    r.ax = 0
    r = yield from far(mem, r, "214B:0018", r.ss, r.di, 4, r.ax, ret=0x6CEB)
    r.es, r.di = game
    r.al = rb(mem, r, 0)
    r.ah = 0
    count = r.ax
    r.local16(-0x12, count)
    r.ax = 1
    for k in range(1, count + 1):                                 # 6CFE-6D42
        r.local16(-8, k)
        r.ax = k + 0x80
        r.dx = 3
        mul(r, r.dx)
        _ds_far(mem, r, 0xA91F)
        r.di += r.ax
        r.al = rb(mem, r, 0)
        r.ah = 0
        country_of(mem, r, r.ax)
        save_ptr(r, -0x16)
        r.al = rb(mem, r, 0x2C)
        r.ah = 0
        r.di = r.ax
        r.local8(r.di - 0xD, 1)
        r.ax = k
    while True:
        r.es, r.di = game
        r.ax = rw(mem, r, 0x26)
        if r.ax >= rw(mem, r, 0x28):                             # 6D44-6D54
            r = yield from far(mem, r, "1771:8757", ret=0x706E)
            return _end(r)
        fx = _fixture_at_cursor(mem, r, game)
        save_ptr(r, -0x14)
        managed = False
        r.local8(-4, 0)
        play = False
        r.es, r.di = fx
        if rb(mem, r, 0) == 0xFE:                                # 6D79
            r = yield from far(mem, r, "1771:0B77", rw(mem, r, 6), ret=0x6D8B)
            if not r.al:
                r.es, r.di = fx
                r = yield from far(mem, r, "1771:0B77", rw(mem, r, 4), ret=0x6D9B)
            r.al = int(not r.al)
            r = yield from near(mem, r, 0x6C21, r.ax, r.bp, ret=0x6DAA)
            play = bool(r.al)
        if not play:
            r.es, r.di = fx
            r.al = rb(mem, r, 2)
            kind = r.ax
            r.di = 0x695A
            r = yield from far(mem, r, "23E4:08DF", kind, mem.DS, r.di, ret=0x6DC0)
            if member(mem):
                r.al = 1
                r = yield from near(mem, r, 0x6C21, r.ax, r.bp, ret=0x6DC9)
                play = bool(r.al)
            if not play:
                r.es, r.di = fx
                cont = continent(mem, r, rw(mem, r, 6))
                if ss8(mem, r, r.bp + cont - 0xD):
                    r.es, r.di = fx
                    r.al = rb(mem, r, 2)
                    kind = r.ax
                    r.di = 0x697A
                    r = yield from far(mem, r, "23E4:08DF", kind, mem.DS, r.di, ret=0x6E02)
                    if member(mem):
                        r.al = 1
                        r = yield from near(mem, r, 0x6C21, r.ax, r.bp, ret=0x6E0E)
                        play = bool(r.al)
        if play:
            r.es, r.di = fx
            r.al = rb(mem, r, 2)
            kind = r.ax
            r.di = 0x6C87
            r = yield from far(mem, r, "23E4:08DF", kind, mem.seg(0xE), r.di, ret=0x6E27)
            if member(mem):                                     # 6E2C-6EAB
                for side in (0, 1):
                    r.local8(-3, side)
                    country = side_country(mem, r, fx, side)
                    r = yield from far(mem, r, "1771:0B77", country, ret=0x6E49)
                    if r.al:
                        for off, value, site in ((0x13, int(variant != "finals-mark-dropped"), 0x6E75),
                                                 (0x41, 0, 0x6EA2)):
                            country_of(mem, r, side_country(mem, r, fx, side))
                            r.al = rb(mem, r, 0x2E)
                            r.ah = 0
                            r.ax -= 0x80
                            r.es, r.di = game
                            r.di += r.ax
                            w8(mem, r, off, value, at(site))
            for side in (0, 1):                                  # 6EAD-6ED6
                r.local8(-3, side)
                country = side_country(mem, r, fx, side)
                r = yield from far(mem, r, "1771:0B77", country, ret=0x6ECA)
                if r.al:
                    managed = True
                    r.local8(-4, 1)
            r.es, r.di = fx
            if rb(mem, r, 2) == 0:
                now = _fixture_at_cursor(mem, r, game)
                r = yield from far(mem, r, "0791:BB2F", *now, ret=0x6EFE)
            else:
                now = _fixture_at_cursor(mem, r, game)
                # 6F12 add di,0xFFF8 is the last flag-setting instruction
                # before the real F1F6 entry, whose handoff snapshots EFLAGS.
                r.arith(add_flags((r.di + 8) & M16, 0xFFF8))
                r = yield from far(mem, r, "0791:F1F6", *now, ret=0x6F1D)
                if managed:
                    now = _fixture_at_cursor(mem, r, game)
                    r.di += 8
                    if rb(mem, r, -6) != 1:
                        for side in (0, 1):                      # applies to BOTH sides, including unmanaged
                            r.local8(-3, side)
                            country = side_country(mem, r, fx, side)
                            country_of(mem, r, country)
                            r.al = rb(mem, r, 0x2E)
                            r.ah = 0
                            manager = r.ax
                            if variant == "confidence-managed-only" and manager < 0x80:
                                continue
                            r.push(manager)
                            now = _fixture_at_cursor(mem, r, game)
                            r.al = side
                            r = yield from far(mem, r, "0791:B71C", *now, r.ax, ret=0x6F85)
                            delta = r.ax
                            manager = pop(mem, r)
                            r = yield from far(mem, r, "0791:B6CC", manager, delta, ret=0x6F8B)
                for side in (0, 1):
                    r.local8(-3, side)
                    country = side_country(mem, r, fx, side)
                    r = yield from far(mem, r, "1771:0B77", country, ret=0x6FAE)
                    if r.al:
                        country = side_country(mem, r, fx, side)
                        now = _fixture_at_cursor(mem, r, game)
                        r = yield from near(mem, r, 0x4E0E, country, *now, ret=0x6FDB)
                now = _fixture_at_cursor(mem, r, game)
                r = yield from far(mem, r, "0791:B7FA", *now, ret=0x6FFD)
            r.es, r.di = game
            w16(mem, r, 0x26, rw(mem, r, 0x26) + 1, at(0x7000))
            r = yield from far(mem, r, "1771:8757", ret=0x7009)
            if managed:
                return _end(r)
        else:
            r = yield from near(mem, r, 0x6970, r.bp, ret=0x7017)
        r.es, r.di = fx
        kind = rb(mem, r, 2)
        show = kind == 0xCB
        if kind == 0x67:
            r.es, r.di = fx
            cont = continent(mem, r, rw(mem, r, 6))
            show = bool(ss8(mem, r, r.bp + cont - 0xD))
        if show:
            r.es, r.di = game
            r.ax = rw(mem, r, 0x26) - 1
            r.cx = (r.cx & 0xFF00) | 3
            r.ax <<= 3
            _ds_far(mem, r, 0xA92B)
            r.di += r.ax + 0xFFF8
            r = yield from near(mem, r, 0x6685, r.es, r.di, ret=0x7066)


@PORTS.port("0791:E80D", ret="retf 4")
def ask_watch_match(mem, variant):
    r = Regs(mem)
    r.enter(0x22)
    fx = farg(mem, r, 6)
    r = yield from guest(mem, r, "A4A1", *fx, ret="E81B", far=False)
    while True:
        r = yield from guest(mem, r, "A75D", ret="E81E", far=False)
        r.di = 0xA96E
        r = yield from guest(mem, r, "214B:0329", mem.DS, 0x3A36, mem.DS, r.di, ret="E82D")
        r.ax = 0x10
        colour = r.ax
        r.al = int(mem.ds16(0xABE) == 1)
        cbw(r)
        r.di = r.ax
        r.al = mem.ds8(r.di + 0xAC0)
        r.ah = 0
        column = r.ax
        r.al = int(mem.ds16(0xABE) == 1)
        r.ah = 0
        r.ax += 4
        r = yield from guest(mem, r, "214B:13C5", colour, column, r.ax, ret="E860")
        r.di = 0xABE
        r.ax = 2
        r = yield from guest(mem, r, "214B:1560", mem.DS, r.di, r.ax, ret="E86E")
        r.al = mem.ds8(0xA976)
        r = yield from guest(mem, r, "23E4:19B2", r.ax, ret="E877")
        if r.al in (0x4E, 0x1B):
            mem.wds16(0xABE, 2, "0791:E87F")
        elif r.al == 0x59:
            mem.wds16(0xABE, 1, "0791:E88B")
        elif r.al in (0xAE, 0xAF):
            r.di = 0xABE
            r.ax = 1
            r = yield from guest(mem, r, "214B:1C86", mem.DS, r.di, 1, 2, 1, ret="E8B1")
        r.al = mem.ds8(0xA976)
        key = r.ax
        r.push(key)
        tmp = (r.bp - 0x22) & M16
        r.push(r.ss)
        r.push(tmp)
        r.di = 0x7946
        r.ax = 0x20
        r = yield from guest(mem, r, "23E4:0831", mem.DS, r.di, r.ax, ret="E8C8")
        r.di = 0xE7ED
        r = yield from guest(mem, r, "23E4:0900", mem.seg(0x791), r.di, ret="E8D2")
        off, seg, key = pop(mem, r), pop(mem, r), pop(mem, r)
        r = yield from guest(mem, r, "23E4:08DF", key, seg, off, ret="E8D7")
        if member(mem):
            break
    r.al = int(mem.ds16(0xABE) == 1)
    result = r.al
    r.local8(-1, result)
    for side in (0, 1):
        r.local8(-2, side)
        r.al = side
        cbw(r)
        r.di = r.ax << 1
        country = mem.ds16(r.di + 0x9B34)
        r = yield from guest(mem, r, "BC5D", country, ret="E905")
    if mem.ds16(0xABE) != 1:
        farg(mem, r, 6)
        w8(mem, r, 0, 0xFE, "E917")
        mem.wds8(0xC1E, 0, "0791:E91B")
    r.al = result
    return _end(r, value=True)


@PORTS.port("000E:038E", ret="ret")
def news_background(mem, variant):
    r = Regs(mem)
    r.enter()
    for src, ret in ((0x4ED8, 0x03A0), (0x5796, 0x03AF), (0x14A6, 0x03BE)):
        r.di = 0xA96E
        r = yield from far(mem, r, "214B:0329", mem.DS, src, mem.DS, r.di, ret=ret)
    return _end(r)


@PORTS.port("000E:05F6", ret="ret 6")
def news_key_wait(mem, variant):
    r = Regs(mem)
    r.enter()
    back = _ds_far(mem, r, 0xA96E)
    screen = _ds_far(mem, r, 0xA96A)
    r.ax = 0xFA0
    r = yield from far(mem, r, "23E4:025D", *back, *screen, r.ax, ret=0x060E)
    if any(ss8(mem, r, r.bp + k) for k in (8, 6, 4)):
        r = yield from near(mem, r, 0x0572, r.bp, ret=0x0624)
    r = yield from far(mem, r, "214B:08DD", ret=0x0629)
    return _end(r)


@PORTS.port("000E:070B", ret="ret 6")
def news_heading(mem, variant):
    r = Regs(mem)
    r.enter(0x216)
    src = farg(mem, r, 4)
    text = (r.bp - 0x15) & M16
    r.di = text
    r.ax = 0x14
    r = yield from far(mem, r, "23E4:0644", *src, r.ss, text, r.ax, ret=0x0725)
    r.al = 0x17
    colour = r.ax
    r.push(colour)
    result = (r.bp - 0x215) & M16
    r.push(r.ss)
    r.push(result)
    tmp = (r.bp - 0x115) & M16
    r.push(r.ss)
    r.push(tmp)
    r.di = text
    r.ax = 0x14
    r = yield from near(mem, r, 0x03C4, r.ss, text, r.ax, ret=0x0740)
    off, seg = pop(mem, r), pop(mem, r)
    r = yield from far(mem, r, "214B:009C", seg, off, ret=0x0745)
    r.ax = ss16(mem, r, r.bp + 8) + 8
    row = r.ax
    r.al = 0x1F
    column = r.ax
    r.di = 0xA96E
    off, seg, colour = pop(mem, r), pop(mem, r), pop(mem, r)
    r = yield from far(mem, r, "214B:02C8", colour, seg, off, row, column, mem.DS, r.di, ret=0x0759)
    return _end(r)


def news_columns(mem, variant, right):
    r = Regs(mem)
    r.enter(0x240)
    delta = 0x130 if right else 0
    for arg, local, ret in ((0xC, -0x15, 0x0649), (8, -0x2A, 0x065C), (4, -0x3F, 0x066F)):
        src = farg(mem, r, arg)
        dest = (r.bp + local) & M16
        r.di = dest
        r.ax = 0x14
        r = yield from far(mem, r, "23E4:0644", *src, r.ss, dest, r.ax, ret=ret + delta)
    r.al = 0x20 if right else 0x70
    colour = r.ax
    r.push(colour)
    for k, (local, fmtret, upperret, drawret) in enumerate((
        (-0x15, 0x068A, 0x068F, 0x069F), (-0x2A, 0x06BD, 0x06C2, 0x06D2),
        (-0x3F, 0x06F0, 0x06F5, 0x0705))):
        if k and not ss8(mem, r, r.bp + local):
            continue
        tmp, result = (r.bp - 0x13F) & M16, (r.bp - 0x23F) & M16
        r.push(r.ss)
        r.push(result)
        r.push(r.ss)
        r.push(tmp)
        text = (r.bp + local) & M16
        r.di = text
        r.ax = 0x12
        r = yield from near(mem, r, 0x03C4, r.ss, text, r.ax, ret=fmtret + delta)
        off, seg = pop(mem, r), pop(mem, r)
        r = yield from far(mem, r, "214B:009C", seg, off, ret=upperret + delta)
        r.al = 0xB + k
        row = r.ax
        r.al = 0x3B if right else 5
        column = r.ax
        r.di = 0xA96E
        off, seg = pop(mem, r), pop(mem, r)
        args = (seg, off, row, column, mem.DS, r.di)
        if not k:
            colour = pop(mem, r)
            args = (colour,) + args
        r = yield from far(mem, r, "214B:02C8" if not k else "214B:026D", *args, ret=drawret + delta)
    return _end(r)


@PORTS.port("000E:062F", ret="ret 0xc")
def news_left(mem, variant):
    return (yield from news_columns(mem, variant, False))


@PORTS.port("000E:075F", ret="ret 0xc")
def news_right(mem, variant):
    return (yield from news_columns(mem, variant, True))


@PORTS.port("000E:5978", ret="ret 4")
def news_championship(mem, variant):
    r = Regs(mem)
    r.enter(0x204)
    game = _ds_far(mem, r, 0xA923)
    save_ptr(r, -4)
    line = ss16(mem, r, r.bp + 6)
    if rb(mem, r, 0x40):
        r.di = 0x5955
        r = yield from near(mem, r, 0x070B, line, mem.seg(0xE), r.di, ret=0x599E)
        return _end(r)
    # 59A0: line, result of the concatenations, and result of number-to-string
    # remain below SP until their consuming calls (062A/06B7 leave the result).
    r.push(line)
    result = (r.bp - 0x204) & M16
    r.push(r.ss)
    r.push(result)
    r.di = 0x5963
    r = yield from far(mem, r, "23E4:062A", mem.seg(0xE), r.di, ret=0x59B3)
    tmp = (r.bp - 0x104) & M16
    r.push(r.ss)
    r.push(tmp)
    r.es, r.di = game
    r.ax = rw(mem, r, 0x38) << 1
    r.ax += rw(mem, r, 0x3A)
    r.dx = 0
    r = yield from far(mem, r, "214B:09DA", r.dx, r.ax, ret=0x59D2)
    off, seg = pop(mem, r), pop(mem, r)
    r = yield from far(mem, r, "23E4:06B7", seg, off, ret=0x59D7)
    r.di = 0x5968
    r = yield from far(mem, r, "23E4:06B7", mem.seg(0xE), r.di, ret=0x59E1)
    country = ss16(mem, r, r.bp + 4)
    country_of(mem, r, country)
    r.al = rb(mem, r, 0x2C)
    r.ah = 0
    r.dx = 0xB
    mul(r, r.dx)
    r.di = r.ax + 0x68FF
    r = yield from far(mem, r, "23E4:06B7", mem.DS, r.di, ret=0x5A07)
    off, seg, line = pop(mem, r), pop(mem, r), pop(mem, r)
    r = yield from near(mem, r, 0x070B, line, seg, off, ret=0x5A0A)
    r.ax = ss16(mem, r, r.bp + 6) + 1
    r.di = 0x596A
    r = yield from near(mem, r, 0x070B, r.ax, mem.seg(0xE), r.di, ret=0x5A17)
    return _end(r)


@PORTS.port("000E:6685", ret="ret 4")
def news_competition_result(mem, variant):
    r = Regs(mem)
    r.enter(0x12E)
    game = _ds_far(mem, r, 0xA923)
    save_ptr(r, -0x26)
    fx = farg(mem, r, 4)
    save_ptr(r, -0x2A)
    r = yield from near(mem, r, 0x038E, ret=0x66A2)
    r.es, r.di = game
    if rb(mem, r, 0x40):
        cont = 5
    else:
        r.es, r.di = fx
        cont = continent(mem, r, rw(mem, r, 6))
    r.local16(-0x22, cont)
    r.ax = cont
    r.dx = 0x60
    mul(r, r.dx)
    _ds_far(mem, r, 0xA93F)
    r.di += r.ax + 0xFFA0
    table = r.es, r.di
    save_ptr(r, -0x2E)
    if rw(mem, r, 0xE) and rw(mem, r, 0xC) > 1:
        r.ax = 4
        r.push(r.ax)
        tmp = (r.bp - 0x12E) & M16
        r.push(r.ss)
        r.push(tmp)
        r.es, r.di = table
        r.al = rb(mem, r, 0)
        r = yield from far(mem, r, "23E4:075A", r.ax, ret=0x6710)
        r.di = 0x6635
        r = yield from far(mem, r, "23E4:06B7", mem.seg(0xE), r.di, ret=0x671A)
        r.es, r.di = table
        r.di += 1
        r = yield from far(mem, r, "23E4:06B7", r.es, r.di, ret=0x6728)
        r.di = 0x6637
        r = yield from far(mem, r, "23E4:06B7", mem.seg(0xE), r.di, ret=0x6732)
        off, seg, line = pop(mem, r), pop(mem, r), pop(mem, r)
        r = yield from near(mem, r, 0x070B, line, seg, off, ret=0x6735)
        r.ax = 5
        r.di = 0x663B
        r = yield from near(mem, r, 0x070B, r.ax, mem.seg(0xE), r.di, ret=0x6741)
        r.ax = 6
        r.push(r.ax)
        r.push(r.ss)
        r.push(tmp)
        r.es, r.di = table
        r.ax = rw(mem, r, 0xC)
        r.dx = 0
        r = yield from far(mem, r, "214B:09DA", r.dx, r.ax, ret=0x675B)
        r.di = 0x664B
        r = yield from far(mem, r, "23E4:06B7", mem.seg(0xE), r.di, ret=0x6765)
        off, seg, line = pop(mem, r), pop(mem, r), pop(mem, r)
        r = yield from near(mem, r, 0x070B, line, seg, off, ret=0x6768)
    for target, ret, dest, copyret in (("1771:5C94", 0x6772, -0x10, 0x678C),
                                       ("1771:5CCB", 0x6796, -0x20, 0x67B0)):
        farg(mem, r, 4)
        r = yield from far(mem, r, target, *fx, ret=ret)
        r.cx = (r.cx & 0xFF00) | 4
        r.ax <<= 4
        _ds_far(mem, r, 0x9B68)
        r.di += r.ax
        name = r.es, r.di
        r.di = r.bp + dest
        r.ax = 0xF
        r = yield from far(mem, r, "23E4:0644", *name, r.ss, r.di, r.ax, ret=copyret)
    winner, loser = (r.bp - 0x10) & M16, (r.bp - 0x20) & M16
    r.ax = 1
    r.push(r.ax)
    result = (r.bp - 0x12A) & M16
    r.push(r.ss)
    r.push(result)
    r.di = winner
    r = yield from far(mem, r, "23E4:062A", r.ss, r.di, ret=0x67C4)
    r.di = 0x6652
    r = yield from far(mem, r, "23E4:06B7", mem.seg(0xE), r.di, ret=0x67CE)
    off, seg, line = pop(mem, r), pop(mem, r), pop(mem, r)
    r = yield from near(mem, r, 0x070B, line, seg, off, ret=0x67D1)
    r.ax = 2
    r.push(r.ax)
    farg(mem, r, 4)
    r = yield from far(mem, r, "1771:5C94", *fx, ret=0x67DF)
    winning = r.ax
    line = pop(mem, r)
    r = yield from near(mem, r, 0x5978, line, winning, ret=0x67E3)
    r.ax = 3
    r = yield from far(mem, r, "214B:06B1", r.ax, ret=0x67EC)
    r.di = r.ax
    r.cx = (r.cx & 0xFF00) | 4
    r.di = (r.di << 4) + 0x6A
    phrase = r.di
    r.di = 0x6658
    r = yield from near(mem, r, 0x062F, mem.DS, phrase, r.ss, winner, mem.seg(0xE), r.di, ret=0x6805)
    r.ax = 3
    if variant != "news-second-draw-dropped":
        r = yield from far(mem, r, "214B:06B1", r.ax, ret=0x680E)
    if r.ax == 1:
        r.di = 0x6663
        r = yield from near(mem, r, 0x075F, r.ss, loser, mem.seg(0xE), 0x6659, mem.seg(0xE), r.di, ret=0x6825)
    elif r.ax == 2:
        r.di = winner
        r = yield from near(mem, r, 0x075F, r.ss, loser, mem.seg(0xE), 0x666C, r.ss, r.di, ret=0x683E)
    elif r.ax == 3:
        r.di = loser
        r = yield from near(mem, r, 0x075F, r.ss, winner, mem.seg(0xE), 0x6678, r.ss, r.di, ret=0x6857)
    r.al = 0
    zero = r.ax
    r = yield from near(mem, r, 0x05F6, zero, zero, zero, ret=0x6863)
    return _end(r)


# T123: named000E_05 then raw000E_09 7072..715D. Annual deferral is an
# explicit bounded-consumer contract; it precedes stage_end's first mutation.
@PORTS.port('000E:7072',ret='ret')
def shareware_limit_reached(mem,variant):
    from .runtime import PF,ZF
    r=Regs(mem);r.enter(2)
    r.al=0;r.arith(PF|ZF)                                       # 7078/707A registered build
    r.al=0;r.local8(-1,r.al);r.al=ss8(mem,r,r.bp-1)               # 7089/708F/7092
    return _end(r)


@PORTS.port('000E:70B9',ret='ret')
def play_round_body(mem,variant):
    from .runtime import sub_flags
    r=Regs(mem);r.enter(8)
    _ds_far(mem,r,0xA923);save_ptr(r,-6)
    farg(mem,r,-6);w8(mem,r,1,1,'000E:70CC')
    r=yield from near(mem,r,0x6CA7,ret=0x70D4)
    farg(mem,r,-6);r.ax=rw(mem,r,0x26)
    farg(mem,r,-6);count=rw(mem,r,0x28);r.arith(sub_flags(r.ax,count,16))
    if r.ax!=count:return _end(r)                              # 70E2/70E4: equality only
    terminal=rb(mem,r,0x3D)==1 and rb(mem,r,0x3C) in (4,8)
    r.store(stack=True)
    mem.site('000E:70E6')                                      # explicit Python-body observation
    if terminal:return _end(r)                                # BEFORE yielding8208
    r=yield from far(mem,r,'1771:8208',ret=0x70EB)
    r=yield from near(mem,r,0x7072,ret=0x70EE)
    r.arith(sub_flags(r.al,0,8))
    if r.al:return _end(r)
    r=yield from far(mem,r,'1771:76B1',ret=0x70F9)
    farg(mem,r,-6);r.al=rb(mem,r,0x3C);r.di=0x7099
    r=yield from far(mem,r,'23E4:08DF',r.ax,mem.seg(0xE),r.di,ret=0x710B)
    if not member(mem):return _end(r)
    farg(mem,r,-6);r.al=rb(mem,r,0);r.ah=0;r.local16(-8,r.ax)
    r.ax=1;r.arith(sub_flags(r.ax,ss16(mem,r,r.bp-8),16))
    if r.ax>ss16(mem,r,r.bp-8):return _end(r)
    r.local16(-2,r.ax)
    while True:
        r.ax=ss16(mem,r,r.bp-2);farg(mem,r,-6);r.di+=r.ax
        if rb(mem,r,0x47)==0:
            r.ax=ss16(mem,r,r.bp-2);r.ax+=0x80;r.dx=3;mul(r,r.dx)
            _ds_far(mem,r,0xA91F);r.di+=r.ax;r.al=rb(mem,r,0);r.ah=0
            r=yield from far(mem,r,'000E:60CB',r.ax,ret=0x7152)    # pushCS+near, FAR return
        r.ax=ss16(mem,r,r.bp-2);limit=ss16(mem,r,r.bp-8);r.arith(sub_flags(r.ax,limit,16))
        if r.ax==limit:break
        r.local16(-2,ss16(mem,r,r.bp-2)+1)
    return _end(r)
