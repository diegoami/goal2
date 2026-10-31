"""T78b1: callable ABIs for pilot's inline helpers.
Source: named/ and code/seg_{0791_01,0791_04,0791_05,214B_01,23E4_01}.
The original listings define the frame writes, partial registers and final flags.
"""
from . import Registry
from .mem import s8
from .pilot import is_keeper_slot, on_pitch, pitch_slot_side
from .runtime import Regs, args, invoke, sub_flags, add_flags, CF, PF, ZF, SF

PORTS = Registry('entrypoints', 'Residual pilot helper calling conventions (T78b1)')


def test_flags(value):
    """TEST byte: Unicorn's defined arithmetic flags, with AF cleared."""
    return (PF if (value & 255).bit_count() % 2 == 0 else 0) | (ZF if not value else 0) | (SF if value & 128 else 0)


def finish_bool(R, value):
    R.al = int(value)
    R.local8(-1, R.al)
    R.leave()
    R.store()


@PORTS.port('0791:045D', ret='ret 2')
def keeper(mem, variant):
    slot, = args(mem, 1)
    R = Regs(mem); R.enter(2)
    R.arith(sub_flags(slot, 1 if slot == 1 else 12, 16))
    finish_bool(R, is_keeper_slot(slot))


def side_core(mem, R, off, seg):
    R.enter(2)
    R.di, R.es = off, seg
    slot = mem.u8(seg * 16 + ((off + 6) & 0xFFFF))
    R.arith(sub_flags(slot, 12, 8))
    R.al = pitch_slot_side(mem, seg * 16 + off)
    R.local8(-1, R.al)
    R.leave()


@PORTS.port('0791:2974', ret='retf 4')
def side(mem, variant):
    off, seg = args(mem, 2)
    R = Regs(mem)
    side_core(mem, R, off, seg)
    R.store()


@PORTS.port('0791:2BE5', ret='retf 4')
def direction(mem, variant):
    off, seg = args(mem, 2)
    R = Regs(mem); R.enter(2)
    half = s8(mem.ds8(0x8319))
    left = mem.ds16(0x831B)
    R.cx, R.bx, R.dx = half, -1 if half < 0 else 0, 0
    R.ax = left
    R.al = int(half < 0 or left > half)
    saved = R.ax
    R.push(saved)
    R.di, R.es = off, seg
    invoke(mem, R, 0x0791, 0x2C13, side_core, off, seg, pushes=(seg, off))
    R.dx = saved
    R.sp += 2
    value = R.al ^ (R.dx & 255)
    R.arith(test_flags(value))
    R.ax = s8(value)
    R.di = R.ax
    R.al = mem.ds8((R.di + 0x7920) & 0xFFFF)
    R.local8(-1, R.al)
    R.leave(); R.store()


@PORTS.port('0791:2DCA', ret='ret 2')
def pitch(mem, variant):
    word, = args(mem, 1)
    R = Regs(mem); R.enter(2)
    x, y = abs(s8(word & 255)), abs(s8(word >> 8))
    R.ax = x if x > 8 else y
    R.arith(sub_flags(R.ax, 8 if x > 8 else 37, 16))
    finish_bool(R, on_pitch(word, None))


@PORTS.port('23E4:08DF', ret='retf 6')
def membership(mem, variant):
    off, seg, element = args(mem, 3)
    element &= 255
    R = Regs(mem)
    R.di, R.es, R.bx = off, seg, element >> 3
    R.cx = (R.cx & 0xFF00) | (element & 7)
    R.al = 1 << (element & 7)
    value = mem.u8(seg * 16 + ((R.bx + off) & 0xFFFF)) & R.al
    R.arith(test_flags(value)); R.store()


def rng_core(mem, R, off, seg, n):
    """214B:0688–06AE inlined, including its dead frame and final INC flags."""
    R.enter(2)
    sp0 = R.sp
    R.push(mem.DS); R.push(seg); R.push(off)
    # 068F LDS uses the explicit pointer, not necessarily DS:A978 (94C9 uses 8336).
    linear = seg * 16 + off
    new = (mem.u16(linear) * 0x7ABD + 0x1B0F) & 0xFFFF
    mem.w16(linear, new, '214B:069F')
    draw = (((new * n) >> 16) + 1) & 0xFFFF
    high = (new * n) >> 16
    step = -2 if mem.reg("eflags") & 0x400 else 2
    R.bx, R.si, R.di, R.es = 0x7ABD, off + step, off + step, seg
    R.ax = R.dx = draw
    R.arith((add_flags(high, 1) & ~CF) | (CF if high else 0))
    R.sp = sp0
    R.local16(-2, draw)
    R.leave()


def random_core(mem, n, coin):
    R = Regs(mem); R.enter(2)
    off, seg = mem.farptr(mem.DS * 16 + 0xA978)
    R.di, R.es = off, seg
    if coin: R.ax = 2
    invoke(mem, R, 0x214B, 0x070E if coin else 0x06C4, rng_core, off, seg, n, pushes=(seg, off, n))
    if coin:
        R.arith(sub_flags(R.ax, 1, 16))
        R.al = int(R.ax == 1)
        R.local8(-1, R.al)
    else:
        R.local16(-2, R.ax)
    R.leave(); R.store()


@PORTS.port('214B:06B1', ret='retf 2')
def random_n(mem, variant):
    random_core(mem, args(mem, 1)[0], False)


@PORTS.port('214B:06FA', ret='retf')
def coin(mem, variant):
    random_core(mem, 2, True)


@PORTS.port('0791:2CC5', ret='retf 4')
def destination(mem, variant):
    off, seg = args(mem, 2)
    R = Regs(mem); R.enter(2)
    R.di, R.es = off, seg
    R.ax = mem.u16(seg * 16 + off)
    target = mem.u16(seg * 16 + ((off + 7) & 0xFFFF))
    R.arith(sub_flags(R.ax, target, 16))
    finish_bool(R, R.ax == target)


@PORTS.port('214B:0688', ret='retf 6')
def explicit_seed_draw(mem, variant):
    n, off, seg = args(mem, 3)
    R = Regs(mem)
    rng_core(mem, R, off, seg, n)
    R.store()
