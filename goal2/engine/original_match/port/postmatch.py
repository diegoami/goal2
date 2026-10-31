"""T71: run_match and its tail, translated from the named view and the instruction listing.

The instruction offsets in comments and write sites refer to code/seg_0791_19.asm (BC5D),
seg_0791_20.asm (CAB0-CB7D), seg_0791_21.asm (D016-D050), seg_0791_23.asm
(E929 and F1F6), and seg_1771_08/12.asm (59D8, 82BD-8757).
Guest calls preserve the listing's arguments, return addresses, registers and dead stack frames.
"""
from . import Registry
from .contests import ss16, pop
from .geometry import cbw, mul
from .mem import s16
from .restarts import _end
from .runtime import Regs
from .setup import guest, member, farg, wd8, wd16, w8, w16, rb, rw, squad_of, player_of, squad_word, player_at

PORTS = Registry("postmatch", "run_match, man of the match, restored players, tactics, country records and group tables (T71)")
PORTS.variant("man-best-reversed", "CB4E: reverse the signed comparison of performance with best (greater to less)")
PORTS.variant("winner-count-two", "D0AE: increment a winning country's season wins by two instead of one")
PORTS.variant("man-tie-replaces", "CB4E: replace the man of the match on equal performance")
PORTS.variant("restore-energy-omitted", "CC14: omit the restoration of positive energy from fitness")
PORTS.variant("group-points-bonus", "8401: add one to the computed group points, including a draw")
PORTS.variant("group-points-one", "83FF: a win earns one point rather than two")
M16 = 0xFFFF


def half(r, name, value):
    """Set BL/CL/DL as the listing does, preserving the high byte."""
    setattr(r, name, (getattr(r, name) & 0xFF00) | (value & 0xFF))


@PORTS.port("0791:F1F6", ret="retf 4")
def run_match(mem, variant):
    r = Regs(mem)
    r.enter(0xA)
    seg, off = farg(mem, r, 6)
    r = yield from guest(mem, r, "A4A1", seg, off, ret="F204", far=False)
    r.al = 1
    r = yield from guest(mem, r, "ED8A", r.ax, ret="F20A", far=False)
    for src, dst, ret in ((0x7C1E, 0x7C16, "F21F"), (0x7C1E, 0x7C22, "F234")):
        r.di, r.es = mem.ds16(src), mem.ds16(src + 2)
        s = (r.es, r.di)
        r.di, r.es = mem.ds16(dst), mem.ds16(dst + 2)
        r.ax = 0xFA0
        r = yield from guest(mem, r, "23E4:025D", *s, r.es, r.di, r.ax, ret=ret)
    for side in range(2):
        r.local8(-1, side)                                       # F234/F23A
        for k in range(1, 21):
            r.local16(-3, k)                                    # F23D/F244
            r.al = side
            cbw(r)
            r.di = r.ax << 1
            squad_of(mem, r, mem.ds16((0x9B34 + r.di) & M16))
            sqseg, sqoff = r.es, r.di
            r.local16(-9, r.di)
            r.local16(-7, r.es)
            r.ax = k << 1
            r.di = sqoff + r.ax
            if rw(mem, r, -2) != 0:                             # F273
                player_at(mem, r, sqseg, sqoff, k)
                half(r, "bx", rb(mem, r, 0xC))
                r.ax, r.cx = k, k
                r.al = side
                cbw(r)
                r.dx = 0x14
                mul(r, r.dx)
                r.di = r.ax + r.cx
                wd8(mem, r.di + 0x9B07, r.bx & 0xFF, "F2A4")
                if k < 12:
                    player_at(mem, r, sqseg, sqoff, k)
                    w16(mem, r, 0x12, 0x37, "F2C7")
    r = yield from guest(mem, r, "F098", r.bp, ret="F2E3", far=False)
    r.store(stack=True)
    mem.site("0791:F2E3")                                       # MATCH_PLAYED at the original's point
    r = Regs(mem, resumed=True)
    r.di, r.es = mem.ds16(0x7C16), mem.ds16(0x7C18)
    src = r.es, r.di
    r.di, r.es = mem.ds16(0x7C22), mem.ds16(0x7C24)
    r.ax = 0xFA0
    r = yield from guest(mem, r, "23E4:025D", *src, r.es, r.di, r.ax, ret="F2F8")
    r = yield from guest(mem, r, "CAB0", ret="F2FB", far=False)
    if mem.ds8(0x9A3E) == 0:
        r = yield from guest(mem, r, "15B9", ret="F305", far=False)
    r.al = 1
    r = yield from guest(mem, r, "0106", r.ax, ret="F30C")
    r = yield from guest(mem, r, "1771:8757", ret="F311")
    wd8(mem, 0x66D, 1, "F311")
    wd8(mem, 0xC20, 1, "F316")
    r.al, r.di = mem.ds8(0xA977), 0xF1B4
    r = yield from guest(mem, r, "23E4:08DF", r.ax, mem.seg(0x0791), r.di, ret="F329")
    if member(mem):
        r.al = 1
        r = yield from guest(mem, r, "ED8A", r.ax, ret="F331", far=False)
    if mem.ds8(0x9A3E) == 0:
        r.di = 0xF1D4
        r = yield from guest(mem, r, "0B7C", mem.seg(0x0791), r.di, ret="F340", far=False)
        if r.al:
            r = yield from guest(mem, r, "0A6B", ret="F347", far=False)
    r = yield from guest(mem, r, "CB7D", ret="F34A", far=False)
    wd8(mem, 0x66D, 0, "F34A")
    farg(mem, r, 6)
    if rb(mem, r, 2) != 1:
        r.al = 0
        r = yield from guest(mem, r, "E929", mem.ds16(0x9B36), r.ax, ret="F364")
    for side in range(2):
        r.local8(-1, side)
        r.al = side
        cbw(r)
        r.di = r.ax << 1
        r = yield from guest(mem, r, "1771:0B77", mem.ds16((0x9B34 + r.di) & M16), ret="F37E")
        if not r.al:
            r.al = side
            cbw(r)
            r.di = r.ax << 1
            r = yield from guest(mem, r, "BC5D", mem.ds16((0x9B34 + r.di) & M16), ret="F392")
    for word, at in ((0xC1F, "F398"), (0xC1E, "F39D"), (0xC20, "F3A2")):
        wd8(mem, word, 0, at)
    seg, off = farg(mem, r, 6)
    r = yield from guest(mem, r, "D050", seg, off, ret="F3B0")
    for side in range(2):
        r.local8(-1, side)
        r.al = side
        cbw(r)
        r.di = r.ax << 1
        r = yield from guest(mem, r, "1771:0B77", mem.ds16((0x9B34 + r.di) & M16), ret="F3CA")
        if r.al:
            r.al = side
            cbw(r)
            r.di = r.ax << 1
            r = yield from guest(mem, r, "BA4E", mem.ds16((0x9B34 + r.di) & M16), ret="F3DD", far=False)
    r.di, r.es = mem.ds16(0xA923), mem.ds16(0xA925)
    w8(mem, r, 1, 1, "F3E7")
    return _end(r)


@PORTS.port("0791:CAB0", ret="ret")
def select_man_of_the_match(mem, variant):
    r = Regs(mem)
    r.enter(0x10)
    best = 1
    r.local16(-5, best)
    for side in range(2):
        r.local8(-1, side)
        r.al = side
        cbw(r)
        r.di = r.ax << 1
        sqseg, sqoff = squad_of(mem, r, mem.ds16((0x9B34 + r.di) & M16))
        r.local16(-0xB, sqoff)
        r.local16(-9, sqseg)
        for k in range(1, 21):
            r.local16(-3, k)
            pseg, poff = player_at(mem, r, sqseg, sqoff, k)
            r.local16(-0xF, poff)
            r.local16(-0xD, pseg)
            if k >= 12:
                r.ax = 3
                r.al = rb(mem, r, 0x10)
                r.ah = 0
                r = yield from guest(mem, r, "214B:0C57", 3, r.ax, ret="CB23")
                if not r.al:
                    continue
            r.es, r.di = pseg, poff
            if rw(mem, r, 0x12) == 0x7FFF:
                continue
            r.ax = rw(mem, r, 0x12)
            perf = r.ax
            r.local16(-7, perf)
            if s16(perf) > 5000:
                perf = (perf - 10000) & M16
                r.local16(-7, perf)
            r.ax = perf
            better = s16(perf) > s16(best)
            if variant == "man-best-reversed":
                better = s16(perf) < s16(best)
            if better or (variant == "man-tie-replaces" and perf == best):
                squad_word(mem, r, sqseg, sqoff, k)
                wd16(mem, 0x7C3A, r.ax, "CB5E")
                r.ax, best = perf, perf
                r.local16(-5, best)
    return _end(r)


@PORTS.port("0791:CB7D", ret="ret")
def restore_match_player_state(mem, variant):
    r = Regs(mem)
    r.enter(0xC)
    for side in range(2):
        r.local8(-1, side)
        for k in range(1, 21):
            r.local16(-3, k)
            r.al = side
            cbw(r)
            r.di = r.ax << 1
            sqseg, sqoff = squad_of(mem, r, mem.ds16((0x9B34 + r.di) & M16))
            r.local16(-7, sqoff)
            r.local16(-5, sqseg)
            r.ax = k << 1
            r.di = sqoff + r.ax
            if rw(mem, r, -2) == 0:
                continue
            pseg, poff = player_at(mem, r, sqseg, sqoff, k)
            r.local16(-0xB, poff)
            r.local16(-9, pseg)
            r.ax, r.cx = k, k
            r.al = side
            cbw(r)
            r.dx = 0x14
            mul(r, r.dx)
            r.di = r.ax + r.cx
            r.al = mem.ds8((r.di + 0x9B07) & M16)
            r.es, r.di = pseg, poff
            w8(mem, r, 0xC, r.al, "CBFC")
            if rb(mem, r, 0xE) < 0x80 and rb(mem, r, 0xE) > 0:
                r.al = rb(mem, r, 0xD)
                if variant != "restore-energy-omitted":
                    w8(mem, r, 0xE, r.al, "CC14")
    return _end(r)


@PORTS.port("0791:BC5D", ret="retf 2")
def reset_team_tactics(mem, variant):
    r = Regs(mem)
    r.enter(6)
    country = ss16(mem, r, r.bp + 6)
    sqseg, sqoff = squad_of(mem, r, country)
    r.local16(-6, sqoff)
    r.local16(-4, sqseg)
    for k in range(1, 21):
        r.local16(-2, k)
        player_at(mem, r, sqseg, sqoff, k)
        w8(mem, r, 0xF, 0, "BC9A")
    r.di = country
    r.al = mem.ds8((r.di + 0x9B7C) & M16)
    r = yield from guest(mem, r, "BBFF", country, r.ax, ret="BCB3", far=False)
    r = yield from guest(mem, r, "1771:52CC", country, ret="BCBB")
    for k in range(1, 12):
        r.local16(-2, k)
        r.ax, r.cx = k, k
        r.ax, r.dx = country, 0x14
        mul(r, r.dx)
        r.di = r.ax + r.cx
        half(r, "cx", mem.ds8((r.di + 0x9F02) & M16))
        player_at(mem, r, sqseg, sqoff, k)
        w8(mem, r, 6, r.cx & 0xFF, "BCF3")
    return _end(r)


@PORTS.port("0791:E929", ret="retf 4")
def show_updated_group_tables(mem, variant):
    r = Regs(mem)
    r.enter()
    r = yield from guest(mem, r, "1771:8757", ret="E931")
    r.al = ss16(mem, r, r.bp + 6) & 0xFF
    mode = r.ax
    r.al = mem.ds8(0x9976)
    r.ah = 0
    r = yield from guest(mem, r, "1771:958D", mode, r.ax, ss16(mem, r, r.bp + 8), ret="E943")
    return _end(r)


@PORTS.port("0791:D016", ret="ret 8")
def increment_streak(mem, variant):
    r = Regs(mem)
    r.enter()
    r.ax = ss16(mem, r, r.bp + 6)
    seg, off = farg(mem, r, 8)
    r.di = off + r.ax
    w8(mem, r, 3, rb(mem, r, 3) + 1, "D021")
    r.es, r.di = seg, off
    w8(mem, r, 5, rb(mem, r, 5) + 1, "D028")
    return _end(r)


@PORTS.port("0791:D032", ret="ret 8")
def clear_streak(mem, variant):
    r = Regs(mem)
    r.enter()
    r.ax = ss16(mem, r, r.bp + 6)
    seg, off = farg(mem, r, 8)
    r.di = off + r.ax
    w8(mem, r, 3, 0, "D03D")
    r.es, r.di = seg, off
    w8(mem, r, 5, 0, "D045")
    return _end(r)


@PORTS.port("0791:D050", ret="retf 4")
def update_country_match_records(mem, variant):
    """D050-D449: season totals, unbeaten/win/loss streaks and largest win/loss fixtures."""
    r = Regs(mem)
    r.enter(0xE)
    fxseg, fxoff = farg(mem, r, 6)
    r.local16(-9, fxoff)
    r.local16(-7, fxseg)

    def fixture(k=0):
        r.es, r.di = fxseg, fxoff + k

    def country(side):
        r.al = side
        cbw(r)
        r.ax = r.ax << 1
        fixture(r.ax)
        return squad_of(mem, r, rw(mem, r, 4))

    for side in range(2):
        r.local8(-1, side)
        cseg, coff = country(side)
        r.di = coff + 0x3B
        rec = r.di
        r.local16(-0xD, rec)
        r.local16(-0xB, cseg)
        fixture()
        if rb(mem, r, 3) == 2:
            r.es, r.di = cseg, rec
            w8(mem, r, 2, rb(mem, r, 2) + 1, "D099")
        else:
            r.al = rb(mem, r, 3)
            r.es, r.di = cseg, rec
            k, at = (1, "D0AE") if r.al == side else (3, "D0B7")
            w8(mem, r, k, rb(mem, r, k) + (2 if variant == "winner-count-two" and k == 1 else 1), at)
        r.al = side
        cbw(r)
        fixture(r.ax)
        r.al = rb(mem, r, 0)
        r.es, r.di = cseg, rec
        w8(mem, r, 4, rb(mem, r, 4) + r.al, "D0CA")
        r.al = 1 if side == 0 else 0
        cbw(r)
        fixture(r.ax)
        r.al = rb(mem, r, 0)
        r.es, r.di = cseg, rec
        w8(mem, r, 5, rb(mem, r, 5) + r.al, "D0E6")

    for side in range(2):
        r.local8(-1, side)
        cseg, coff = country(side)
        r.local16(-0xD, coff)
        r.local16(-0xB, cseg)
        host = False
        if side == 1:
            fixture()
            r = yield from guest(mem, r, "D44C", r.es, r.di, ret="D12B")
            host = bool(r.al)
        r.al = int(host)
        r.ah = 0
        place = r.ax
        r.local16(-5, place)
        fixture()
        outcome = rb(mem, r, 3)
        if outcome != 2:
            r.al = outcome
        if outcome == 2 or outcome == side:
            r.es, r.di = cseg, coff + 0xB9
            r = yield from guest(mem, r, "D016", r.es, r.di, place, r.bp, ret="D160", far=False)
            r.es, r.di = cseg, coff + 0xAD
            r = yield from guest(mem, r, "D032", r.es, r.di, place, r.bp, ret="D170", far=False)
        fixture()
        outcome = rb(mem, r, 3)
        if outcome != 2:
            r.al = outcome
        if outcome == 2 or outcome != side:
            r.es, r.di = cseg, coff + 0xB3
            r = yield from guest(mem, r, "D016", r.es, r.di, place, r.bp, ret="D196", far=False)
            r.es, r.di = cseg, coff + 0xA7
            r = yield from guest(mem, r, "D032", r.es, r.di, place, r.bp, ret="D1A6", far=False)
        fixture()
        r.al = rb(mem, r, 3)
        if r.al == side:
            r.es, r.di = cseg, coff + 0xA7
            r = yield from guest(mem, r, "D016", r.es, r.di, place, r.bp, ret="D1C2", far=False)
            r.es, r.di = cseg, coff + 0xB3
            r = yield from guest(mem, r, "D032", r.es, r.di, place, r.bp, ret="D1D2", far=False)
        else:
            fixture()
            if rb(mem, r, 3) != 2:
                r.es, r.di = cseg, coff + 0xAD
                r = yield from guest(mem, r, "D016", r.es, r.di, place, r.bp, ret="D1EE", far=False)
                r.es, r.di = cseg, coff + 0xB9
                r = yield from guest(mem, r, "D032", r.es, r.di, place, r.bp, ret="D1FE", far=False)
            else:
                r.es, r.di = cseg, coff + 0xAD
                r = yield from guest(mem, r, "D032", r.es, r.di, place, r.bp, ret="D210", far=False)
                r.es, r.di = cseg, coff + 0xA7
                r = yield from guest(mem, r, "D032", r.es, r.di, place, r.bp, ret="D220", far=False)

    fixture()
    if rb(mem, r, 3) != 2:
        for side in range(2):
            r.local8(-1, side)
            cseg, coff = country(side)
            r.local16(-0xD, coff)
            r.local16(-0xB, cseg)
            fixture()
            r = yield from guest(mem, r, "1771:5A03", r.es, r.di, ret="D269")
            neutral = False
            if r.al:
                fixture()
                r = yield from guest(mem, r, "A6E4", r.es, r.di, ret="D275", far=False)
                r.dx = r.ax
                r.al = side
                cbw(r)
                r.ax = r.ax << 1
                fixture(r.ax)
                r.ax = rw(mem, r, 4)
                neutral = r.ax != r.dx
            if neutral:
                place = 2
            else:
                r.al = side
                r.ah = 0
                place = r.ax
            r.local16(-3, place)

            def record():
                r.ax = place
                half(r, "cx", 3)
                r.ax = r.ax << 3
                r.bx = r.ax
                fixture()
                r.al = rb(mem, r, 3)
                r.al = int(r.al == side)
                cbw(r)
                r.dx = 0x18
                mul(r, r.dx)
                r.es, r.di = cseg, coff + r.ax + r.bx + 0x77
            record()
            r = yield from guest(mem, r, "1771:5C60", r.es, r.di, ret="D2CC")
            r.push(r.ax)
            fixture()
            r = yield from guest(mem, r, "1771:5C60", r.es, r.di, ret="D2D7")
            r.dx = pop(mem, r)
            if r.ax >= r.dx:
                fixture()
                src = r.es, r.di
                record()
                dst = r.es, r.di
                r.ax = 8
                r = yield from guest(mem, r, "23E4:025D", *src, *dst, r.ax, ret="D318")

    for side in range(2):
        r.local8(-1, side)
        r.ax = 0
        for k in range(3):
            r.local16(-3, k)
            cseg, coff = country(side)
            r.local16(-0xD, coff)
            r.local16(-0xB, cseg)
            for base, at in ((0xA7, "D387"), (0xAD, "D3BF"), (0xB3, "D3F7"), (0xB9, "D42F")):
                r.ax = k
                r.es, r.di = cseg, coff + k
                half(r, "dx", rb(mem, r, base))
                r.ax = k
                r.al = rb(mem, r, base + 3)
                if r.al > (r.dx & 0xFF):
                    r.ax = k
                    half(r, "dx", rb(mem, r, base + 3))
                    r.ax = k
                    w8(mem, r, base, r.dx & 0xFF, at)
    return _end(r)


@PORTS.port("1771:59D8", ret="retf")
def stage_uses_finals_table(mem, variant):
    r = Regs(mem)
    r.enter(2)
    r.di, r.es = mem.ds16(0xA923), mem.ds16(0xA925)
    r.al = rb(mem, r, 0x3C)
    r.di = 0x59B8
    r = yield from guest(mem, r, "23E4:08DF", r.ax, mem.seg(0x1771), r.di, ret="1771:59F1")
    r.al = int(member(mem))
    r.local8(-1, r.al)
    return _end(r, value=True)


@PORTS.port("1771:8757", ret="retf")
def update_group_tables(mem, variant):
    r = Regs(mem)
    r.enter(0xC)
    gseg, goff = mem.ds16(0xA925), mem.ds16(0xA923)
    r.es, r.di = gseg, goff
    r.local16(-8, goff)
    r.local16(-6, gseg)
    r.al = rb(mem, r, 0x3C)
    r.di = 0x8737
    r = yield from guest(mem, r, "23E4:08DF", r.ax, mem.seg(0x1771), r.di, ret="1771:8779")
    if member(mem):
        r.es, r.di = gseg, goff
        r.al = int(rb(mem, r, 0x3C) == 7)
        cbw(r)
        r.di = r.ax
        r.al = mem.ds8((r.di + 0x1110) & M16)
        r.ah = 0
        continents = r.ax
        r.local16(-0xA, continents)
        r.ax = 1
        for continent in range(1, continents + 1):
            r.local16(-2, continent)
            r.es, r.di = gseg, goff
            r.al = int(rb(mem, r, 0x3C) == 3)
            cbw(r)
            r.di = r.ax
            r.al = mem.ds8((r.di + 0x1112) & M16)
            r.ah = 0
            groups = r.ax
            r.local16(-0xC, groups)
            r.ax = 1
            for group in range(1, groups + 1):
                r.local16(-4, group)
                r.ax, r.dx = group, 0x38
                mul(r, r.dx)
                r.push(r.ax)
                r.ax, r.dx = continent, 0x1C0
                mul(r, r.dx)
                r.push(r.ax)
                r = yield from guest(mem, r, "1771:59D8", ret="1771:87EF")
                cbw(r)
                r.dx = 0x700
                mul(r, r.dx)
                r.cx = r.ax
                r.es, r.di = gseg, goff
                r.al = rb(mem, r, 0x40)
                cbw(r)
                r.dx = 0xE00
                mul(r, r.dx)
                r.di, r.es = mem.ds16(0xA933), mem.ds16(0xA935)
                r.di = r.di + r.ax + r.cx
                r.ax = pop(mem, r)
                r.di = r.di + r.ax
                r.ax = pop(mem, r)
                r.di = r.di + r.ax - 0x1F8
                r = yield from guest(mem, r, "1771:82BD", r.es, r.di, ret="1771:881B", far=False)
                r.ax = group
            r.ax = continent
    r.es, r.di = gseg, goff
    if rb(mem, r, 0x3C) == 6:
        r = yield from guest(mem, r, "1771:85F7", ret="1771:883B", far=False)
    return _end(r)


@PORTS.port("1771:82BD", ret="ret 4")
def sort_group_table(mem, variant):
    r = Regs(mem)
    r.enter(0x1C)
    gseg, goff = mem.ds16(0xA925), mem.ds16(0xA923)
    r.es, r.di = gseg, goff
    r.local16(-0xB, goff)
    r.local16(-9, gseg)
    tseg, toff = farg(mem, r, 4)
    r.local16(-0xF, toff)
    r.local16(-0xD, tseg)
    for slot in range(1, 5):
        r.local16(-2, slot)
        r.ax = slot
        half(r, "cx", 3)
        r.ax = r.ax << 3
        r.es, r.di = tseg, toff + r.ax - 8
        eseg, eoff = r.es, r.di
        r.local16(-0x13, eoff)
        r.local16(-0x11, eseg)
        country = rw(mem, r, 0)
        squad_of(mem, r, country)
        r.local16(-0x17, r.di)
        r.local16(-0x15, r.es)
        r.es, r.di = eseg, eoff + 2
        r.ax = 0
        r = yield from guest(mem, r, "214B:0018", r.es, r.di, 6, 0, ret="1771:8322")
        for k in range(0x19, 0x25):
            r.local16(-4, k)
            def fixture_word():
                r.ax = k << 1
                r.cx = r.ax
                r.es, r.di = eseg, eoff
                r.ax, r.dx = rw(mem, r, 0), 0x48
                mul(r, r.dx)
                r.di, r.es = mem.ds16(0xA92F), mem.ds16(0xA931)
                r.di = r.di + r.ax + r.cx
                return rw(mem, r, -2)
            if fixture_word() == 0:
                continue
            r.ax = fixture_word()
            half(r, "cx", 3)
            r.ax = r.ax << 3
            r.di, r.es = mem.ds16(0xA92B), mem.ds16(0xA92D)
            r.di = r.di + r.ax - 8
            fxseg, fxoff = r.es, r.di
            r.local16(-0x1B, fxoff)
            r.local16(-0x19, fxseg)
            r.al = rb(mem, r, 2)
            r.es, r.di = gseg, goff
            if r.al != rb(mem, r, 0x3C):
                continue
            r.es, r.di = fxseg, fxoff
            if rb(mem, r, 0) >= 0xFE:
                continue
            r.ax = rw(mem, r, 6)
            r.es, r.di = eseg, eoff
            r.al = int(r.ax == rw(mem, r, 0))
            side = r.al
            r.local8(-7, side)
            r.es, r.di = fxseg, fxoff
            r.al = rb(mem, r, 1)
            r.al = int(r.al == rb(mem, r, 0))
            r.ah = 0
            r.cx = r.ax
            r.al = int(side == 0)
            cbw(r)
            r.es, r.di = fxseg, fxoff + r.ax
            half(r, "dx", rb(mem, r, 0))
            r.al = side
            cbw(r)
            r.es, r.di = fxseg, fxoff + r.ax
            r.al = int(rb(mem, r, 0) > (r.dx & 0xFF))
            r.ah = 0
            r.ax = r.ax << (0 if variant == "group-points-one" else 1)
            r.ax = r.ax + r.cx + (1 if variant == "group-points-bonus" else 0)
            points = r.ax
            r.local16(-6, points)
            r.es, r.di = eseg, eoff
            field, at = (2, "1771:840F") if points == 2 else ((3, "1771:841E") if points == 1 else (4, "1771:8427"))
            w8(mem, r, field, rb(mem, r, field) + 1, at)
            r.al = side
            cbw(r)
            r.es, r.di = fxseg, fxoff + r.ax
            r.al = rb(mem, r, 0)
            r.es, r.di = eseg, eoff
            w8(mem, r, 5, rb(mem, r, 5) + r.al, "1771:843A")
            r.al = int(side == 0)
            cbw(r)
            r.es, r.di = fxseg, fxoff + r.ax
            r.al = rb(mem, r, 0)
            r.es, r.di = eseg, eoff
            w8(mem, r, 6, rb(mem, r, 6) + r.al, "1771:8456")
            r.al = points & 0xFF
            w8(mem, r, 7, rb(mem, r, 7) + r.al, "1771:8460")

    def item(k, field):
        r.ax = k
        half(r, "cx", 3)
        r.ax = r.ax << 3
        r.es, r.di = tseg, toff + r.ax
        return rb(mem, r, field)

    def difference(k):
        r.al = item(k, -2)
        r.ah = 0
        r.dx = r.ax
        r.al = item(k, -3)
        r.ah = 0
        r.ax = r.ax - r.dx
        return r.ax

    for first in range(1, 4):
        r.local16(-4, first)
        r.ax = first + 1
        for second in range(first + 1, 5):
            r.local16(-2, second)
            half(r, "dx", item(first, -1))
            r.al = item(second, -1)
            swap = r.al > (r.dx & 0xFF)
            if not swap:
                half(r, "dx", item(first, -1))
                r.al = item(second, -1)
                if r.al == (r.dx & 0xFF):
                    r.bx = difference(first)
                    difference(second)
                    swap = s16(r.ax) > s16(r.bx)
                    if not swap:
                        r.bx = difference(first)
                        difference(second)
                        if r.ax == r.bx:
                            half(r, "dx", item(first, -3))
                            r.al = item(second, -3)
                            swap = r.al > (r.dx & 0xFF)
            if swap:
                item(second, 0)
                r.di = r.di - 8
                second_ptr = r.es, r.di
                item(first, 0)
                r.di = r.di - 8
                r.ax = 8
                r = yield from guest(mem, r, "214B:007B", *second_ptr, r.es, r.di, r.ax, ret="1771:85DF")
    return _end(r)


@PORTS.port("1771:85F7", ret="ret")
def decide_playoff_aggregates(mem, variant):
    r = Regs(mem)
    r.enter(0xE)
    gseg, goff = mem.ds16(0xA925), mem.ds16(0xA923)
    r.es, r.di = gseg, goff
    r.local16(-0xA, goff)
    r.local16(-8, gseg)
    r.ax = 0
    k = 0
    r.local16(-2, k)

    def state():
        r.es, r.di = gseg, goff

    def fixture(number):
        r.ax = number
        half(r, "cx", 3)
        r.ax = r.ax << 3
        r.di, r.es = mem.ds16(0xA92B), mem.ds16(0xA92D)
        r.di = r.di + r.ax

    while True:
        state()
        r.ax = rw(mem, r, 0x2C) + k + 1
        index = r.ax
        if index > rw(mem, r, 0x26):
            break
        state()
        r.ax = rw(mem, r, 0x2C) + k + 1
        fixture(r.ax)
        if rb(mem, r, -8) >= 0xFE:
            break
        r.ax, r.dx, r.cx = k, 0, 2
        r.ax = r.ax // r.cx
        r.ax = r.ax + 0x961
        fixture(r.ax)
        r.di = r.di - 8
        aseg, aoff = r.es, r.di
        r.local16(-0xE, aoff)
        r.local16(-0xC, aseg)
        state()
        r.ax = rw(mem, r, 0x2C) + k + 1
        fixture(r.ax)
        r.al = rb(mem, r, -8)
        r.ah = 0
        second_home = r.ax
        r.local16(-4, second_home)
        state()
        r.ax = rw(mem, r, 0x2C) + k
        fixture(r.ax)
        r.al = rb(mem, r, -7)
        r.ah = 0
        r.ax = r.ax + second_home
        r.es, r.di = aseg, aoff
        w8(mem, r, 1, r.al, "1771:86A1")
        state()
        r.ax = rw(mem, r, 0x2C) + k
        fixture(r.ax)
        r.al = rb(mem, r, -8)
        r.ah = 0
        first_home = r.ax
        r.local16(-6, first_home)
        state()
        r.ax = rw(mem, r, 0x2C) + k + 1
        fixture(r.ax)
        r.al = rb(mem, r, -7)
        r.ah = 0
        r.ax = r.ax + first_home
        r.es, r.di = aseg, aoff
        w8(mem, r, 0, r.al, "1771:86E3")
        r.al = rb(mem, r, 1)
        win = r.al > rb(mem, r, 0)
        if not win:
            r.al = rb(mem, r, 1)
            if r.al == rb(mem, r, 0):
                r.ax = second_home
                win = r.ax >= first_home
                if not win:
                    r.ax = second_home
                    if r.ax == first_home:
                        r.al = rb(mem, r, 6)
                        carry = r.al & 1
                        r.al = r.al >> 1
                        win = bool(carry)
        r.al = int(win)
        r.es, r.di = aseg, aoff
        w8(mem, r, 3, r.al, "1771:8728")
        k = (k + 2) & M16
        r.local16(-2, k)
    return _end(r)
