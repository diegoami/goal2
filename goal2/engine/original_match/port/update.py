"""T72: fixture and manager-pool player updates, from the named view then the listing.

0791 B27F/B364/B6CC/B71C/B7FA/BA4E (code/seg_0791_18.asm and _19.asm),
1771 10E7 (seg_1771_02.asm), 3558/3651 (seg_1771_05.asm), and
5A38/5A8F/5C60 (seg_1771_08.asm). Comments and writes name instruction offsets.
Calls remain guest calls, with exact argument words, return sites and dead frames.
The model modules are comparison references only: no model arithmetic replaces
the listing's register operations or its ordered RNG calls.
"""
from . import Registry
from .contests import ss16, pop
from .geometry import cbw, imul, mul
from .mem import s16, s8
from .postmatch import half
from .restarts import _end, idiv_by
from .runtime import Regs
from .setup import guest, farg, w8, w16, rb, rw, squad_of, player_of, squad_word, player_at

PORTS = Registry("update", "fixture and manager-pool player state: confidence, bans, fitness and energy (T72)")
PORTS.variant("confidence-plus-one", "B3AD: store clipped confidence plus one")
PORTS.variant("rolled-energy-plus-one", "3635: store rolled fitness plus one into energy")
PORTS.variant("recovered-energy-plus-one", "3774: store recovered fitness plus one into energy")
M16 = 0xFFFF


def save_ptr(r, off):
    r.local16(off, r.di)
    r.local16(off + 2, r.es)


@PORTS.port("0791:B27F", ret="ret 2")
def post_fixture_status_update(mem, variant):
    r = Regs(mem)
    r.enter(4)
    pseg, poff = player_of(mem, r, ss16(mem, r, r.bp + 4))
    save_ptr(r, -4)

    def status_ptr(bit):
        r.ax = bit
        r.es, r.di = pseg, poff + 0x10
        return bit, r.es, r.di

    def status_word(bit):
        r.ax = bit
        r.es, r.di = pseg, poff
        r.al = rb(mem, r, 0x10)
        r.ah = 0
        return bit, r.ax

    r = yield from guest(mem, r, "214B:0CA1", *status_ptr(8), ret="B2AB")
    r = yield from guest(mem, r, "214B:0C57", *status_word(6), ret="B2BE")
    if r.al:
        r = yield from guest(mem, r, "214B:0C79", *status_ptr(8), ret="B2D4")
    r = yield from guest(mem, r, "214B:0CA1", *status_ptr(6), ret="B2E6")
    r = yield from guest(mem, r, "214B:0C57", *status_word(5), ret="B2F9")
    if r.al:
        r = yield from guest(mem, r, "214B:0C57", *status_word(4), ret="B310")
        if not r.al:
            r = yield from guest(mem, r, "214B:0C79", *status_ptr(4), ret="B326")
        else:
            r = yield from guest(mem, r, "214B:0C79", *status_ptr(8), ret="B33A")
            r = yield from guest(mem, r, "214B:0CA1", *status_ptr(4), ret="B34C")
    r = yield from guest(mem, r, "214B:0CA1", *status_ptr(5), ret="B35E")
    return _end(r)


@PORTS.port("0791:B364", ret="ret 4")
def adjust_player_confidence(mem, variant):
    r = Regs(mem)
    r.enter(6)
    player_of(mem, r, ss16(mem, r, r.bp + 6))
    save_ptr(r, -6)
    r.al = rb(mem, r, 0xC)
    cbw(r)
    value = r.ax
    r.local16(-2, value)
    r.ax = ss16(mem, r, r.bp + 4)
    value = (value + r.ax) & M16                              # B38C word wrapping before signed clamp
    r.local16(-2, value)
    if s16(value) < 1:
        value = 1
        r.local16(-2, value)
    elif s16(value) > 32:
        value = 32
        r.local16(-2, value)
    r.al = value & 0xFF
    w8(mem, r, 0xC, r.al + (1 if variant == "confidence-plus-one" else 0), "B3AD")
    return _end(r)


@PORTS.port("0791:B6CC", ret="retf 4")
def add_manager_delta(mem, variant):
    r = Regs(mem)
    r.enter(6)
    r.ax, r.dx = ss16(mem, r, r.bp + 8), 3
    mul(r, r.dx)
    r.di, r.es = mem.ds16(0xA91F), mem.ds16(0xA921)
    r.di = r.di + r.ax
    save_ptr(r, -6)
    r.al = rb(mem, r, 2)
    cbw(r)
    r.ax = r.ax + ss16(mem, r, r.bp + 6)
    value = r.ax
    r.local16(-2, value)
    if s16(value) < -127:
        value = (-127) & M16
        r.local16(-2, value)
    elif s16(value) > 127:
        value = 127
        r.local16(-2, value)
    r.al = value & 0xFF
    w8(mem, r, 2, r.al, "B712")
    return _end(r)


@PORTS.port("0791:B71C", ret="retf 6")
def fixture_confidence_delta(mem, variant):
    r = Regs(mem)
    r.enter(8)
    fxseg, fxoff = farg(mem, r, 8)
    save_ptr(r, -8)
    side = ss16(mem, r, r.bp + 6) & 0xFF
    r.al = side
    cbw(r)
    r.ax = r.ax << 1
    r.di = fxoff + r.ax
    r = yield from guest(mem, r, "1771:10E7", rw(mem, r, 4), ret="B73F")
    r.push(r.ax)
    r.al = int(side == 0)
    cbw(r)
    r.ax = r.ax << 1
    r.es, r.di = fxseg, fxoff + r.ax
    r = yield from guest(mem, r, "1771:10E7", rw(mem, r, 4), ret="B75D")
    r.dx = pop(mem, r)
    r.ax = r.ax - r.dx
    idiv_by(r, 32)
    value = r.ax
    r.local16(-4, value)
    r.es, r.di = fxseg, fxoff
    if rb(mem, r, 3) != 2:
        r.al = rb(mem, r, 3)
        won = r.al == side
        r.es, r.di = fxseg, fxoff
        r = yield from guest(mem, r, "1771:5C60", fxseg, fxoff, ret="B789" if won else "B798")
        if not won:
            old = r.ax
            r.dx = 0
            r.ax = (~r.ax) & M16
            r.dx = (~r.dx) & M16
            r.ax = r.ax + 1
            r.dx = r.dx + int(old == 0)                       # B79E/B7A1 not/add/adc long negate
        value = (value + r.ax) & M16
        r.local16(-4, value)
    r.es, r.di = fxseg, fxoff
    if rb(mem, r, 3) != 2:
        special = side == 0
        if not special:
            r.es, r.di = fxseg, fxoff
            r = yield from guest(mem, r, "1771:5A03", fxseg, fxoff, ret="B7C1")
            special = bool(r.al)
        r.al = int(special)
        half(r, "dx", r.al)
        r.es, r.di = fxseg, fxoff
        r.al = int(rb(mem, r, 3) == side)
        if r.al == (r.dx & 0xFF):
            r.ax = value
            r.ax = r.ax << 1
            value = r.ax
            r.local16(-4, value)
    r.ax = value
    r.local16(-2, r.ax)
    return _end(r, value=True)


@PORTS.port("1771:10E7", ret="retf 2")
def country_rating(mem, variant):
    r = Regs(mem)
    r.enter(6)
    squad_of(mem, r, ss16(mem, r, r.bp + 6))
    save_ptr(r, -6)
    r.al = rb(mem, r, 0x2C)
    r.ah = 0
    r.dx = r.ax
    r.ax = 5 - r.dx
    r.cx = r.ax
    r.al = rb(mem, r, 0x2A)
    r.ah = 0
    r.dx = r.ax
    r.ax = 33 - r.dx
    imul(r, r.cx)
    r.cx = r.ax
    r.al = rb(mem, r, 0x2B)
    r.ah = 0
    r.dx = r.ax
    r.ax = 129 - r.dx
    r.ax = r.ax + r.cx
    idiv_by(r, 2)
    r.local16(-2, r.ax)
    return _end(r, value=True)


@PORTS.port("1771:5A38", ret="retf 6")
def friendly_continents_differ(mem, variant):
    r = Regs(mem)
    r.enter(6)
    fxseg, fxoff = farg(mem, r, 6)
    save_ptr(r, -5)
    different = False
    if rb(mem, r, 2) == 1:
        squad_of(mem, r, ss16(mem, r, r.bp + 0xA))
        half(r, "cx", rb(mem, r, 0x2C))
        r.es, r.di = fxseg, fxoff
        squad_of(mem, r, rw(mem, r, 6))
        r.al = rb(mem, r, 0x2C)
        different = r.al != (r.cx & 0xFF)
    r.al = int(different)
    r.local8(-1, r.al)
    return _end(r, value=True)


@PORTS.port("1771:5A8F", ret="retf 6")
def recovery_route_gradual(mem, variant):
    r = Regs(mem)
    r.enter(2)
    country = ss16(mem, r, r.bp + 0xA)
    seg, off = farg(mem, r, 6)
    r = yield from guest(mem, r, "1771:5A38", country, seg, off, ret="1771:5AA1")
    gradual = bool(r.al)
    if not gradual:
        seg, off = farg(mem, r, 6)
        r = yield from guest(mem, r, "1771:5A03", seg, off, ret="1771:5AAE")
        gradual = bool(r.al)
    r.al = int(gradual)
    r.local8(-1, r.al)
    return _end(r, value=True)


@PORTS.port("1771:5C60", ret="retf 4")
def fixture_absolute_margin(mem, variant):
    r = Regs(mem)
    r.enter(6)
    farg(mem, r, 6)
    save_ptr(r, -6)
    r.al = rb(mem, r, 0)
    cbw(r)
    r.dx = r.ax
    r.al = rb(mem, r, 1)
    cbw(r)
    r.ax = r.ax - r.dx
    if s16(r.ax) < 0:
        r.ax = -r.ax
    r.local16(-2, r.ax)
    return _end(r, value=True)


@PORTS.port("1771:3558", ret="retf 2")
def roll_fitness_energy(mem, variant):
    r = Regs(mem)
    r.enter(6)
    pseg, poff = player_of(mem, r, ss16(mem, r, r.bp + 6))
    save_ptr(r, -5)
    r.al = rb(mem, r, 2)
    r.ah = 0
    r.ax = r.ax + 4
    r.dx = r.ax
    r.al = rb(mem, r, 1)
    r.ah = 0
    older = s16(r.ax) > s16(r.dx)
    r.al = int(older)
    r.local8(-1, r.al)
    r.al = rb(mem, r, 0)
    r.ah = 0
    r = yield from guest(mem, r, "1771:0B77", r.ax, ret="1771:35A3")

    def base():
        r.al = int(older)
        cbw(r)
        r.di = r.ax
        r.al = mem.ds8((r.di + 0xE82) & M16)
        r.ah = 0

    if r.al:
        base()
        r.ax = r.ax + 1
        r = yield from guest(mem, r, "214B:06B1", r.ax, ret="1771:35BA")
        r.push(r.ax)
        base()
        r.cx = 3
        imul(r, r.cx)
        r = yield from guest(mem, r, "214B:06B1", r.ax, ret="1771:35D2")
        r.dx = r.ax
        base()
        r.ax = r.ax + r.dx
        r.dx = pop(mem, r)
        r.ax = r.ax - r.dx
        r.es, r.di = pseg, poff
        w8(mem, r, 0xD, r.al, "1771:35E8")
    else:
        base()
        r.ax = r.ax << 1
        r = yield from guest(mem, r, "214B:06B1", r.ax, ret="1771:3602")
        r.dx = r.ax
        base()
        r.ax = r.ax + r.dx
        r.es, r.di = pseg, poff
        w8(mem, r, 0xD, r.al, "1771:3615")
    r.es, r.di = pseg, poff
    if s8(rb(mem, r, 0xD)) > 32:
        w8(mem, r, 0xD, 32, "1771:3626")
    r.al = rb(mem, r, 0xD)
    w8(mem, r, 0xE, r.al + (1 if variant == "rolled-energy-plus-one" else 0), "1771:3635")
    if s8(rb(mem, r, 0xD)) < 1:
        w8(mem, r, 0xD, 1, "1771:3646")
    return _end(r)


@PORTS.port("1771:3651", ret="retf 4")
def recover_fitness_energy(mem, variant):
    r = Regs(mem)
    r.enter(6)
    pseg, poff = player_of(mem, r, ss16(mem, r, r.bp + 8))
    save_ptr(r, -6)
    r.al = rb(mem, r, 0xD)
    cbw(r)
    value = r.ax
    r.local16(-2, value)
    if rb(mem, r, 0xE) == 0:
        r.ax = 2
        r = yield from guest(mem, r, "214B:06B1", r.ax, ret="1771:3689")
        r.push(r.ax)
        r.ax = 8
        r = yield from guest(mem, r, "214B:06B1", r.ax, ret="1771:3693")
        r.ax = -r.ax
        r.dx = pop(mem, r)
        r.ax = r.ax + r.dx
        value = (value + r.ax) & M16
        r.local16(-2, value)
    elif ss16(mem, r, r.bp + 6) & 0xFF:
        r.ax = 2
        r = yield from guest(mem, r, "214B:06B1", r.ax, ret="1771:36AC")
        r.push(r.ax)
        r.ax = 8
        r = yield from guest(mem, r, "214B:06B1", r.ax, ret="1771:36B6")
        r.dx = pop(mem, r)
        r.ax = r.ax - r.dx
        value = (value + r.ax) & M16
        r.local16(-2, value)
    else:
        r.ax = 3
        r = yield from guest(mem, r, "214B:06B1", r.ax, ret="1771:36C7")
        r.push(r.ax)
        r.ax = 2
        r = yield from guest(mem, r, "214B:06B1", r.ax, ret="1771:36D1")
        r.dx = pop(mem, r)
        r.ax = r.ax - r.dx
        value = (value + r.ax) & M16
        r.local16(-2, value)
        if s16(value) < 16:
            value = (value + 1) & M16
            r.local16(-2, value)
    if s16(value) < 1:
        value = 1
        r.local16(-2, value)                                  # 36E6 bypasses the age cap
    else:
        def cap():
            r.es, r.di = pseg, poff
            r.al = rb(mem, r, 2)
            r.ah = 0
            r.ax = r.ax + 3
            r.dx = r.ax
            r.al = rb(mem, r, 1)
            r.ah = 0
            r.al = int(s16(r.ax) > s16(r.dx))
            cbw(r)
            r.di = r.ax
            r.al = mem.ds8((r.di + 0xE84) & M16)
            r.ah = 0
        cap()
        if s16(r.ax) < s16(value):
            cap()
            value = r.ax
            r.local16(-2, value)
    r.al = value & 0xFF
    r.es, r.di = pseg, poff
    w8(mem, r, 0xD, r.al, "1771:374F")
    heal = s8(rb(mem, r, 0xE)) > 0
    if not heal:
        r.ax = 3
        r = yield from guest(mem, r, "214B:06D0", r.ax, ret="1771:3766")
        heal = bool(r.al)
    if heal:
        r.es, r.di = pseg, poff
        r.al = rb(mem, r, 0xD)
        w8(mem, r, 0xE, r.al + (1 if variant == "recovered-energy-plus-one" else 0), "1771:3774")
    return _end(r)


@PORTS.port("0791:B7FA", ret="retf 4")
def update_fixture_player_state(mem, variant):
    r = Regs(mem)
    r.enter(0x1A)
    fxseg, fxoff = farg(mem, r, 6)
    save_ptr(r, -0xD)
    r = yield from guest(mem, r, "1771:0B77", rw(mem, r, 4), ret="B815")
    managed = bool(r.al)
    if not managed:
        r.es, r.di = fxseg, fxoff
        r = yield from guest(mem, r, "1771:0B77", rw(mem, r, 6), ret="B825")
        managed = bool(r.al)
    r.al = int(managed)
    r.local8(-5, r.al)
    def squad_arg(k):
        # A pushed memory word leaves AX at 2*k; its AH is part of a following byte flag.
        r.ax = k << 1
        r.es, r.di = sqseg, sqoff + r.ax
        return rw(mem, r, -2)

    for side in range(2):
        r.local8(-7, side)
        r.al = side
        cbw(r)
        r.ax = r.ax << 1
        r.es, r.di = fxseg, fxoff + r.ax
        sqseg, sqoff = squad_of(mem, r, rw(mem, r, 4))
        save_ptr(r, -0x11)
        r.es, r.di = fxseg, fxoff
        r.al = side                                         # B860 preserves country-product AH
        r = yield from guest(mem, r, "B71C", fxseg, fxoff, r.ax, ret="B868")
        delta = r.ax
        r.local16(-9, delta)
        if not managed:
            r.es, r.di = fxseg, fxoff
            if rb(mem, r, 2) != 1:
                r.es, r.di = sqseg, sqoff
                r.al = rb(mem, r, 0x2E)
                r.ah = 0
                r = yield from guest(mem, r, "B6CC", r.ax, delta, ret="B88C")
        r.al = side
        cbw(r)
        r.ax = r.ax << 1
        r.es, r.di = fxseg, fxoff + r.ax
        country = rw(mem, r, 4)
        r.es, r.di = fxseg, fxoff
        r = yield from guest(mem, r, "1771:5A8F", country, fxseg, fxoff, ret="B8A5")
        gradual = r.al
        r.local8(-6, gradual)
        for k in range(1, 21):
            r.local16(-2, k)
            r.ax = k << 1
            r.es, r.di = sqseg, sqoff + r.ax
            if rw(mem, r, -2) == 0:
                continue
            pseg, poff = player_at(mem, r, sqseg, sqoff, k)
            save_ptr(r, -0x15)
            participant = k < 12
            if not participant:
                r.ax = 3
                r.al = rb(mem, r, 0x10)
                r.ah = 0
                r = yield from guest(mem, r, "214B:0C57", 3, r.ax, ret="B8FE")
                participant = bool(r.al)
            if participant:
                r.es, r.di = pseg, poff
                w16(mem, r, 8, rw(mem, r, 8) + 1, "B908")
                word = squad_arg(k)
                if gradual:
                    r.al = 1
                    r = yield from guest(mem, r, "1771:3651", word, r.ax, ret="B928")
                else:
                    r = yield from guest(mem, r, "1771:3558", word, ret="B93D")
                word = squad_arg(k)
                r = yield from guest(mem, r, "B364", word, delta, ret="B951", far=False)
                if k > 11:
                    r.ax = 3
                    r.es, r.di = pseg, poff + 0x10
                    r = yield from guest(mem, r, "214B:0CA1", 3, r.es, r.di, ret="B969")
                    word = squad_arg(k)
                    r.push(word)
                    r.ax = 2
                    r = yield from guest(mem, r, "214B:06B1", r.ax, ret="B980")
                    r.push(r.ax)
                    r.ax = 2
                    r = yield from guest(mem, r, "214B:06B1", r.ax, ret="B98A")
                    r.dx = pop(mem, r)
                    r.ax = r.ax - r.dx
                    word = pop(mem, r)
                    r = yield from guest(mem, r, "B364", word, r.ax, ret="B991", far=False)
            else:
                word = squad_arg(k)
                r.push(word)
                r.ax = 4
                r = yield from guest(mem, r, "214B:06B1", r.ax, ret="B9AA")
                r.push(r.ax)
                r.ax = 2
                r = yield from guest(mem, r, "214B:06B1", r.ax, ret="B9B4")
                r.dx = pop(mem, r)
                r.ax = r.ax - r.dx
                word = pop(mem, r)
                r = yield from guest(mem, r, "B364", word, r.ax, ret="B9BB", far=False)
                word = squad_arg(k)
                if gradual:
                    r.al = 0
                    r = yield from guest(mem, r, "1771:3651", word, r.ax, ret="B9D7")
                else:
                    r = yield from guest(mem, r, "1771:3558", word, ret="B9EC")
            word = squad_arg(k)
            r = yield from guest(mem, r, "B27F", word, ret="B9FD", far=False)
            if k > 11 and not managed:
                player_at(mem, r, sqseg, sqoff, k)
                save_ptr(r, -0x19)
                r.al = rb(mem, r, 7)
                w8(mem, r, 6, r.al, "BA32")
    return _end(r)


@PORTS.port("0791:BA4E", ret="ret 2")
def update_pool_player_state(mem, variant):
    r = Regs(mem)
    r.enter(0xC)
    country = ss16(mem, r, r.bp + 4)
    squad_of(mem, r, country)
    save_ptr(r, -9)
    r.al = rb(mem, r, 0x2E)
    r.ah = 0
    r.ax = r.ax - 0x80
    r.di = r.ax << 1
    r.ax = mem.ds16((r.di + 0x6D18) & M16)
    first = r.ax
    r.local16(-4, first)
    r.di, r.es = mem.ds16(0x7C2A), mem.ds16(0x7C2C)
    r = yield from guest(mem, r, "1771:5A8F", country, r.es, r.di, ret="BA8D")
    gradual = r.al
    r.local8(-5, gradual)
    r.ax = first + 0x4F
    last = r.ax
    r.local16(-0xB, last)
    r.ax = first

    def pool_word(k):
        r.ax = k << 1
        r.di, r.es = mem.ds16(0xA927), mem.ds16(0xA929)
        r.di = r.di + r.ax
        return rw(mem, r, 0)

    if first <= last:
        for k in range(first, last + 1):
            r.local16(-2, k)
            word = pool_word(k)
            if gradual:
                r.al = 0
                r = yield from guest(mem, r, "1771:3651", word, r.ax, ret="BAC8")
            else:
                r = yield from guest(mem, r, "1771:3558", word, ret="BADD")
            word = pool_word(k)
            r.push(word)
            r.ax = 4
            r = yield from guest(mem, r, "214B:06B1", r.ax, ret="BAF4")
            r.push(r.ax)
            r.ax = 4
            r = yield from guest(mem, r, "214B:06B1", r.ax, ret="BAFE")
            r.dx = pop(mem, r)
            r.ax = r.ax - r.dx
            word = pop(mem, r)
            r = yield from guest(mem, r, "B364", word, r.ax, ret="BB05", far=False)
            r.di, r.es = mem.ds16(0x7C2A), mem.ds16(0x7C2C)
            if rb(mem, r, 2) != 0:
                word = pool_word(k)
                r = yield from guest(mem, r, "B27F", word, ret="BB21", far=False)
            r.ax = k
    return _end(r)
