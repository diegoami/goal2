"""The player attributes (segment 1771), ported (T61, step P1 part b): the routines that read a player's or a country's
record and answer a small number, plus the player's own tactics and the marking words.

From the listing static/goal-exe/code/seg_1771_02.asm (0AA7-0E6C), seg_1771_04.asm (2E20-2FFB), seg_1771_05.asm
(3041-3A82), seg_1771_06.asm (3E2F, 3EF8) and seg_1771_08.asm (5A03); the line comments are the listing's offsets. The
records are the ones image.py names: the player array, 3061 records of 0x14 bytes at the far pointer DS:A91B, the
country array, 129 of 0xBF at DS:A917, the manager array at DS:A91F. Every routine is `retf n` (1771 is a far segment,
Turbo Pascal's convention: the callee pops its arguments) but 0E24, called near (`ret 2`) and 3E2F, a nested procedure
(`ret 6`, its parent's BP is its first argument).

Registers. The proof (port/prove.py) compares AX and DX at every return, so each port returns the AX and DX the
original leaves, not only its value: the high byte of AX and DX are what the last instruction of the listing left
(`mul` leaves the high word in DX; `xor ah, ah` makes AH 0; a `mov al, ..` keeps AH). Each routine below tracks AX and DX
through the listing as the plain variables `ax`, `dx`; the tiny runtime helpers it calls inline are the helpers
below, each with the registers it leaves (`bit_test` is 214B:0C57, `bit_set` 214B:0C79, `bit_clear` 214B:0CA1; the
set test 23E4:08DF is inlined where its set is a constant of the code segment, `cs_set_has`).

A routine it calls that is still the original's (the Pascal string helpers of 23E4, `Str` 214B:09DA, `FillChar`
214B:0018) is a guest call (port/guest.py) with the registers the listing hands it; a routine of this module it
calls is a guest call too (the guest then runs its port), so every call is counted and proved on its own. The Turbo
Pascal string helpers leave the destination pointer on the stack for the next call (`retf 2` / `retf 4`), which a
guest call cannot express, so the pointer words are pushed by the port (`push`) and dropped with `drop` and pushed again
as the next call's arguments (the same bytes at the same stack addresses)."""
from .guest import call
from .mem import s8, s16
from . import Registry

PORTS = Registry("attributes", "the player attributes of segment 1771: the records' readers, tactics and marking (T61)")
PORTS.variant("foot-sets-swapped", "3179 tests the right-foot set CS:3139 where it tests CS:3159 and the reverse (31B6, 31D0)")
PORTS.variant("unavailable-bit-6", "3216 tests element 5 where it tests element 6 (3251-3264)")
PORTS.variant("skill-divisor-31", "3A06's divisor 0x20 read as 0x1F (3A71)")
PORTS.variant("tactic-element-2-for-1", "3431 sets element 2 where it sets element 1 for positions 0, 1, 3, 4 (3483)")
PORTS.variant("mark-hi-excl", "3E2F's upper bound 'oc > hi' read as 'oc >= hi' (3E6E-3E71)")

PLAYERS, COUNTRIES, MANAGERS = 0xA91B, 0xA917, 0xA91F      # far pointers at DS:xxxx (0AB5, 0ACF, 3F18...)
TEAM_COUNTRY = 0x9B34       # the two teams' countries, words (3F0F: [di - 0x64cc])
MARK_BASE = 0x9A3E          # the marking word of slot s of team t: DS:9A3E + 0x28 t + 2 s (3F31: [di - 0x65c0])

# The sets of the code segment 23E4:08DF reads (bit e of byte e >> 3 of a 32-byte set) are the original's data, passed as
# pointers: CS:3139 = 88 04 (elements 3, 7, 10: positions a right foot plays badly), CS:3159 = 10 09 (4, 8, 11: left),
# CS:3411 = 1B 00 (0, 1, 3, 4: the positions that take elements 5 and 1), each row 32 bytes with the rest zero.


# -- the view of a record ------------------------------------------------------------------------------------------
class Rec:
    """`les di, ptr [DS:ptr]; add di, ax`: record bytes at seg:(off + ax + k), the offset wrapping in 16 bits."""
    __slots__ = ("mem", "seg", "off")

    def __init__(self, mem, ptr, ax):
        off, seg = mem.farptr(mem.DS * 16 + ptr)
        self.mem, self.seg, self.off = mem, seg, (off + ax) & 0xFFFF

    def lin(self, k):
        return (self.seg << 4) + ((self.off + k) & 0xFFFF)

    def u8(self, k):
        return self.mem.u8(self.lin(k))

    def u16(self, k):
        return self.mem.u16(self.lin(k))

    def w8(self, k, value, at):
        self.mem.w8(self.lin(k), value, at)


def mul(a, b):
    """`mov dx, b; mul dx` (or `mov ax, a; mov dx, b; mul dx`): (AX, DX) the low and high word of a * b."""
    p = (a & 0xFFFF) * b
    return p & 0xFFFF, p >> 16


def idiv(a, b):
    """x86 `idiv` of the signed word a by b (cwd first): (quotient, remainder) truncated toward zero."""
    q = abs(a) // abs(b)
    if (a < 0) != (b < 0):
        q = -q
    return q & 0xFFFF, (a - q * b) & 0xFFFF


# -- the runtime helpers the routines call (still the original's, T60): guest calls with the listing's arguments --------
def bit_test(mem, dx, setbyte, elem, ret_to):
    """214B:0C57(elem, set) as the listing calls it (`mov ax, elem; push ax; mov al, [set]; xor ah, ah; push ax; call far`):
    (AX, DX) it leaves; AL is the element's bit, AH 0."""
    return (yield from gcall(mem, setbyte, dx, "214B:0C57", elem, setbyte, ret_to=ret_to))


def bit_op(mem, target, dx, rec, k, elem, ret_to):
    """214B:0C79 (set) or 0CA1 (clear) of element `elem` of the byte at record offset k (`mov ax, elem; push ax; les di,
    [bp - n]; add di, k; push es; push di; call far`)."""
    return (yield from gcall(mem, elem, dx, target, elem, rec.seg, (rec.off + k) & 0xFFFF, ret_to=ret_to))


def set_test(mem, ax, dx, set_seg, set_off, ret_to):
    """23E4:08DF(ax, set far pointer): (AX, DX, member); `ax` is the word the listing pushes (its low byte is the element).
    The result is the zero flag (`test byte es:[bx + di], al`): a member when it is clear."""
    ax, dx = yield from gcall(mem, ax, dx, "23E4:08DF", ax, set_seg, set_off, ret_to=ret_to)
    return ax, dx, not (mem.reg("eflags") & 0x40)


def regs(mem, ax, dx):
    mem.set_reg("ax", ax & 0xFFFF)
    mem.set_reg("dx", dx & 0xFFFF)


def ret(mem, ax, dx):
    """The end of a function: AX is the value the port returns, DX set here."""
    mem.set_reg("dx", dx & 0xFFFF)
    return ax & 0xFFFF


def end(mem, ax, dx):
    """The end of a procedure: AX and DX as the listing leaves them (the port returns no value)."""
    regs(mem, ax, dx)
    return None


def gcall(mem, ax, dx, target, *args, ret_to, far=True):
    """A guest call (yield from): the registers the listing hands the callee, and (AX, DX) it returns."""
    regs(mem, ax, dx)
    result = yield call(target, *args, ret_to=ret_to, far=far)
    return result & 0xFFFF, mem.reg("dx")


def push(mem, word, at):
    """`push word`: the word written at the new SP, as the original's instruction `at` writes it."""
    sp = (mem.reg("sp") - 2) & 0xFFFF
    mem.w16(mem.ss_lin(sp), word, at)
    mem.set_reg("sp", sp)


def drop(mem, words):
    """The stack pointer back over words the callee of a string helper would have popped: they are pushed again as the
    arguments of the next call (same words, same addresses)."""
    mem.set_reg("sp", (mem.reg("sp") + 2 * words) & 0xFFFF)


def put(mem, linear, data, at):
    """`data` stored at `linear` as one write by the original's instruction `at` (a block of dead stack: no watch of the
    kit covers the stack, and the view's write takes any size)."""
    mem._write(linear, len(data), int.from_bytes(data, "little"), mem._at(at))


# -- the small readers -------------------------------------------------------------------------------------------
def ptr_local(f, off, rec, at_off, at_seg):
    """The two stores `mov [bp + off], di` and `mov [bp + off + 2], es` that keep a record's far pointer in the frame."""
    f.w16(off, rec.off, at_off)
    f.w16(off + 2, rec.seg, at_seg)


@PORTS.port("1771:0AA7", ret="retf 2")
def manager_bonus(mem, variant):
    """0AA7: the manager's match bonus: idiv 8 of the manager byte at [DS:A91F] + 3 * (country +0x2E), plus 0x10."""
    f = mem.enter(6, "1771:0AA7")                           # 0AA7-0AAA
    ax, dx = mul(mem.arg(0), 0xBF)                          # 0AAD-0AB3
    c = Rec(mem, COUNTRIES, ax)
    ptr_local(f, -6, c, "1771:0ABB", "1771:0ABE")           # 0ABB, 0ABE
    ax, dx = mul(c.u8(0x2E), 3)                             # 0AC1-0ACD (xor ah, ah)
    m = Rec(mem, MANAGERS, ax).u8(1)                        # 0ACF-0AD9 (xor ah, ah)
    f.w16(-2, m // 8 + 0x10, "1771:0AE4")                   # 0ADB-0AE4: cdq, idiv 8 (DX the remainder), add ax, 0x10
    return ret(mem, m // 8 + 0x10, m % 8)


@PORTS.port("1771:0B77", ret="retf 2")
def is_managed(mem, variant):
    """0B77: the country's +0x2E above 0x80 (ja)."""
    f = mem.enter(2, "1771:0B77")                           # 0B77-0B7A
    ax, dx = mul(mem.arg(0), 0xBF)                          # 0B7D-0B83
    managed = Rec(mem, COUNTRIES, ax).u8(0x2E) > 0x80       # 0B85-0B90
    f.w8(-1, managed, "1771:0B98")                          # 0B92/0B96, 0B98
    return ret(mem, (ax & 0xFF00) | managed, dx)


@PORTS.port("1771:0E24", ret="ret 2")
def country_colour(mem, variant):
    """0E24 (near): 0x0F when the country is managed (0B77), else the byte DS:6905[country +0x2C]."""
    country = mem.arg(0)
    f = mem.enter(6, "1771:0E24")                           # 0E24-0E27
    ax, dx = mul(country, 0xBF)                             # 0E2A-0E30
    c = Rec(mem, COUNTRIES, ax)
    ptr_local(f, -5, c, "1771:0E38", "1771:0E3B")
    ax, dx = yield from gcall(mem, ax, dx, "1771:0B77", country, ret_to="1771:0E45")   # 0E3E-0E42 push; push cs; call
    if ax & 0xFF:                                           # 0E45-0E47
        f.w8(-1, 0x0F, "1771:0E49")
        return ret(mem, (ax & 0xFF00) | 0x0F, dx)           # 0E61 mov al, [bp - 1]
    colour = mem.ds8(0x6905 + c.u8(0x2C))                   # 0E4F-0E5A (xor ah, ah)
    f.w8(-1, colour, "1771:0E5E")
    return ret(mem, colour, dx)


@PORTS.port("1771:2E20", ret="retf 4")
def player_name_colour(mem, variant):
    """2E20: 6 when +0x0E is 0, 5 when element 8 or 6 of +0x10 is set, else DS:699A[position]."""
    pos, n = mem.arg(0), mem.arg(1)                         # [bp + 6], [bp + 8]
    f = mem.enter(6, "1771:2E20")                           # 2E20-2E23
    ax, dx = mul(n, 0x14)                                   # 2E26-2E2C
    p = Rec(mem, PLAYERS, ax)
    ptr_local(f, -5, p, "1771:2E34", "1771:2E37")
    if p.u8(0xE) == 0:                                      # 2E3A-2E42
        f.w8(-1, 6, "1771:2E44")
        return ret(mem, (ax & 0xFF00) | 6, dx)
    ax, dx = yield from bit_test(mem, dx, p.u8(0x10), 8, "1771:2E5D")           # 2E4A-2E58
    if not (ax & 0xFF):
        ax, dx = yield from bit_test(mem, dx, p.u8(0x10), 6, "1771:2E74")       # 2E61-2E6F
    if ax & 0xFF:
        f.w8(-1, 5, "1771:2E78")                            # 2E78
        return ret(mem, (ax & 0xFF00) | 5, dx)
    colour = mem.ds8(0x699A + pos)                          # 2E7E-2E85: AL from the table, AH the callee's
    f.w8(-1, colour, "1771:2E85")
    return ret(mem, (ax & 0xFF00) | colour, dx)


@PORTS.port("1771:2FAD", ret="retf 2")
def player_height(mem, variant):
    """2FAD: DS:0E46[+7] + DS:0E54[n mod 12]."""
    n = mem.arg(0)
    f = mem.enter(6, "1771:2FAD")                           # 2FAD-2FB0
    ax, dx = mul(n, 0x14)                                   # 2FB3-2FB9
    p = Rec(mem, PLAYERS, ax)
    ptr_local(f, -6, p, "1771:2FC1", "1771:2FC4")
    dx = mem.ds8(0xE54 + n % 12)                            # 2FC7-2FDA: div 12, xchg dx, ax; mov dx, ax
    ax = mem.ds8(0xE46 + p.u8(7)) + dx                      # 2FDC-2FED
    f.w16(-2, ax, "1771:2FEF")
    return ret(mem, ax, dx)


@PORTS.port("1771:2FFB", ret="retf 2")
def player_hardness(mem, variant):
    """2FFB: +5 minus bit 0 of +3."""
    f = mem.enter(6, "1771:2FFB")                           # 2FFB-2FFE
    ax, dx = mul(mem.arg(0), 0x14)                          # 3001-3007
    p = Rec(mem, PLAYERS, ax)
    ptr_local(f, -5, p, "1771:300F", "1771:3012")
    dx = p.u8(3) & 1                                        # 3015-3028 (shr al, 1; jb; mov dx, ax)
    ax = (p.u8(5) - dx) & 0xFFFF                            # 302A-3033: sub ax, dx (16 bits)
    f.w8(-1, ax, "1771:3035")                               # 3035: AL stored and reloaded
    return ret(mem, ax, dx)


@PORTS.port("1771:3041", ret="retf 2")
def is_two_footed(mem, variant):
    """3041: +5 + +2 == 30."""
    f = mem.enter(6, "1771:3041")                           # 3041-3044
    ax, dx = mul(mem.arg(0), 0x14)                          # 3047-304D
    p = Rec(mem, PLAYERS, ax)
    ptr_local(f, -5, p, "1771:3055", "1771:3058")
    dx = p.u8(5)                                            # 305B-3064: mov dx, ax
    total = p.u8(2) + dx                                    # 3066-306F
    flag = total == 0x1E                                    # 3071-307C: mov al, 0/1, AH of the sum
    f.w8(-1, flag, "1771:307C")
    return ret(mem, (total & 0xFF00) | flag, dx)


@PORTS.port("1771:3088", ret="retf 2")
def foot_index(mem, variant):
    """3088: DS:0E60[14 * DS:0E7C[n mod 3] + +7]."""
    n = mem.arg(0)
    f = mem.enter(6, "1771:3088")                           # 3088-308B
    ax, dx = mul(n, 0x14)                                   # 308E-3094
    p = Rec(mem, PLAYERS, ax)
    ptr_local(f, -5, p, "1771:309C", "1771:309F")
    bx = p.u8(7)                                            # 30A2-30AB
    row = mem.ds8(0xE7C + n % 3)                            # 30AD-30BE: div 3, xchg, xor ah, ah
    ax, dx = mul(row, 0xE)                                  # 30C0-30C3
    value = mem.ds8(0xE60 + ((ax + bx) & 0xFFFF))           # 30C5-30C9
    f.w8(-1, value, "1771:30CD")
    return ret(mem, (ax & 0xFF00) | value, dx)              # 30D0: AH of the mul


@PORTS.port("1771:30D9", ret="retf 2")
def player_leadership(mem, variant):
    """30D9: ((+3) - (+5)) mod 8 (idiv: the remainder keeps the dividend's sign), halved (div 2) when +1 < 0x15."""
    f = mem.enter(8, "1771:30D9")                           # 30D9-30DC
    ax, dx = mul(mem.arg(0), 0x14)                          # 30DF-30E5
    p = Rec(mem, PLAYERS, ax)
    ptr_local(f, -8, p, "1771:30ED", "1771:30F0")
    dx = p.u8(5)                                            # 30F6-30FC: mov dx, ax
    quotient, remainder = idiv(p.u8(3) - dx, 8)             # 30FE-310D: sub ax, dx; cdq; idiv 8
    f.w16(-4, remainder, "1771:3110")                       # 310F-3110: xchg dx, ax; mov [bp - 4], ax
    if p.u8(1) >= 0x15:                                     # 3113-311B: jae 312A
        f.w16(-2, remainder, "1771:312D")
        return ret(mem, remainder, quotient)
    f.w16(-4, remainder // 2, "1771:3127")                  # 311D-3127: xor dx, dx; div 2
    f.w16(-2, remainder // 2, "1771:312D")
    return ret(mem, remainder // 2, remainder % 2)


@PORTS.port("1771:3216", ret="retf 2")
def player_unavailable(mem, variant):
    """3216: 1 when +0xE is below 1 (signed) or element 8, 6 or 3 of +0x10 is set, else 0. The hot routine (about 345,000
    calls a match): the three tests of 214B:0C57 are inline, and the bytes the original leaves on the stack (its frame, and
    the last test's two pushes, far return and 0C57's frame) are written as one block: the 20 bytes below the return
    address, laid out as the listing's pushes and stores lay them."""
    e = mem.reg("sp")                                       # SP at the entry: [e] the return address
    bp = mem.reg("bp")
    n = mem.u16(mem.ss_lin(e + 4))                          # [bp + 6] as the callee sees it: the argument
    ax, dx = mul(n, 0x14)                                   # 321C-3222
    ptr = mem.u32(mem.DS * 16 + PLAYERS)                    # 3224: les di, [0xa91b]
    off, seg = (ptr + ax) & 0xFFFF, ptr >> 16               # 3228: add di, ax
    energy = s8(mem.u8((seg << 4) + ((off + 0xE) & 0xFFFF)))
    base = mem.ss_lin(e - 20)
    block = bytearray(mem.read(base, 20))                   # the bytes the original leaves unwritten stay as they are
    block[18:20] = bp.to_bytes(2, "little")                 # 3216: push bp at e - 2
    block[13:15] = off.to_bytes(2, "little")                # 322A: [bp - 5] = di
    block[15:17] = seg.to_bytes(2, "little")                # 322D: [bp - 3] = es
    if energy < 1:                                          # 3230-3238: jl
        block[17] = 1                                       # 3285: [bp - 1] = al
        put(mem, base + 12, block[12:], "1771:3285")
        return ret(mem, (ax & 0xFF00) | 1, dx)              # 3283: mov al, 1 (AH of the mul)
    s = mem.u8((seg << 4) + ((off + 0x10) & 0xFFFF))
    elem6 = 5 if variant == "unavailable-bit-6" else 6
    cs, result, dx = mem.seg(0x1771), 0, 2
    for elem, shift, after in ((8, 7, 0x324D), (6, elem6 - 1, 0x3264), (3, 2, 0x327B)):
        bit = (s >> shift) & 1                              # 214B:0C57: ((word s) >> (elem - 1)) & 1, AH 0, DX = elem - 1
        if bit or elem == 3:                                # the last of the calls made: its pushes, far return, 0C57's frame
            block[10:12] = elem.to_bytes(2, "little")       # push ax (the element) at e - 10
            block[8:10] = s.to_bytes(2, "little")           # push ax (the set, zero-extended) at e - 12
            block[6:8] = cs.to_bytes(2, "little")           # call far: the return segment at e - 14
            block[4:6] = after.to_bytes(2, "little")        # the return offset at e - 16
            block[2:4] = ((e - 2) & 0xFFFF).to_bytes(2, "little")     # 0C57: push bp (3216's frame, bp = e - 2) at e - 18
            block[1] = bit                                  # 0C6D: [bp - 1] = al at e - 19
            result, dx = bit, shift
            break
    block[17] = result                                      # 3285: [bp - 1] = al
    put(mem, base, block, "1771:3285")
    return ret(mem, result, dx)                             # 327F: mov al, 0 (AH 0 from 0C57)


@PORTS.port("1771:3A06", ret="retf 4")
def derived_skill(mem, variant):
    """3A06: DS:6DCD[12 * (+5) + DS:6D25[12 * (+7) + element]] * ((+4) + 1) div 32."""
    element, n = mem.arg(0), mem.arg(1)                     # [bp + 6], [bp + 8]
    f = mem.enter(0xA, "1771:3A06")                         # 3A06-3A09
    ax, dx = mul(n, 0x14)                                   # 3A0C-3A12
    p = Rec(mem, PLAYERS, ax)
    ptr_local(f, -0xA, p, "1771:3A1A", "1771:3A1D")
    scale = p.u8(4) + 1                                     # 3A20-3A2C
    f.w16(-6, scale, "1771:3A2C")
    cx = mem.ds8(0x6D25 + ((p.u8(7) * 12 + element) & 0xFFFF))      # 3A2F-3A4C (mul 12: DX 0, no overflow)
    t = mem.ds8(0x6DCD + ((p.u8(5) * 12 + cx) & 0xFFFF))    # 3A4E-3A64
    f.w16(-4, t, "1771:3A66")
    product = (t * scale) & 0xFFFF                          # 3A69-3A6C: mul; xor dx, dx drops the high word
    divisor = 0x1F if variant == "skill-divisor-31" else 0x20
    f.w16(-2, product // divisor, "1771:3A76")              # 3A6F-3A76: div 0x20
    return ret(mem, product // divisor, product % divisor)


@PORTS.port("1771:3A82", ret="retf 4")
def squad_slot_of_player(mem, variant):
    """3A82: the slot 1..20 of a player word in the country's word list, or 0."""
    country, player = mem.arg(0), mem.arg(1)                # [bp + 6], [bp + 8]
    f = mem.enter(8, "1771:3A82")                           # 3A82-3A85
    ax, dx = mul(country, 0xBF)                             # 3A88-3A8E
    c = Rec(mem, COUNTRIES, ax)
    ptr_local(f, -8, c, "1771:3A96", "1771:3A99")
    f.w16(-2, 0, "1771:3A9E")
    found, slot = 0, 0
    for slot in range(1, 0x15):                             # 3AA1-3AC6
        if c.u16(2 * slot - 2) == player:
            found = slot
            f.w16(-2, found, "1771:3AC1")
            break
    f.w16(-4, slot, "1771:3AA8")                            # the loop variable stays where the loop ended
    return ret(mem, found, dx)


@PORTS.port("1771:5A03", ret="retf 4")
def fixture_kind_in_result_set(mem, variant):
    """5A03: whether the fixture's +2 is in the set DS:0F3E (through 23E4:08DF)."""
    ax, dx = mem.reg("ax"), mem.reg("dx")                   # the caller's (the listing never writes AX's high byte or DX)
    off, seg = mem.arg(0), mem.arg(1)                       # 5A09: les di, [bp + 6]
    f = mem.enter(6, "1771:5A03")                           # 5A03-5A06
    f.w16(-5, off, "1771:5A0C")
    f.w16(-3, seg, "1771:5A0F")
    ax = (ax & 0xFF00) | mem.u8((seg << 4) + ((off + 2) & 0xFFFF))      # 5A12-5A15: mov al, es:[di + 2]; push ax
    ax, dx, member = yield from set_test(mem, ax, dx, mem.reg("ds"), 0xF3E, "1771:5A24")     # 5A19-5A1F
    f.w8(-1, 1 if member else 0, "1771:5A2C")               # 5A24-5A2C
    return ret(mem, (ax & 0xFF00) | (1 if member else 0), dx)


# -- the two routines that build Pascal strings (the helpers of 23E4 and 214B stay the original's: T60) ------------------
@PORTS.port("1771:2E93", ret="retf 2")
def player_name(mem, variant):
    """2E93: the player's name into the string at the far pointer [bp + 8]: the initial DS:[9B70] + n, a space (CS:2E91)
    and the surname, 11 bytes at [DS:9B6C] + 11 n, assigned with a maximum of 12 (23E4:075A, 06B7 twice, 0644)."""
    n = mem.arg(0)
    dest_off, dest_seg = mem.arg(1), mem.arg(2)             # les di, [bp + 8]
    dx = mem.reg("dx")
    mem.enter(0x100, "1771:2E93")                           # 2E93-2E96
    ss, cs, local = mem.reg("ss"), mem.seg(0x1771), (mem.reg("bp") - 0x100) & 0xFFFF
    push(mem, ss, "1771:2E9E")                              # 2E9A-2E9F: lea di, [bp - 0x100]; push ss; push di
    push(mem, local, "1771:2E9F")
    off, seg = mem.farptr(mem.DS * 16 + 0x9B70)             # 2EA3
    ax = (n & 0xFF00) | mem.u8((seg << 4) + ((off + n) & 0xFFFF))      # 2EA0-2EA9: mov ax, [bp + 6]; mov al, es:[di]
    ax, dx = yield from gcall(mem, ax, dx, "23E4:075A", ax, ret_to="1771:2EB2")                  # 2EAC-2EAD
    ax, dx = yield from gcall(mem, ax, dx, "23E4:06B7", cs, 0x2E91, ret_to="1771:2EBC")          # 2EB2-2EB7
    ax, dx = mul(n, 11)                                     # 2EBC-2EC2
    off, seg = mem.farptr(mem.DS * 16 + 0x9B6C)             # 2EC4
    ax, dx = yield from gcall(mem, ax, dx, "23E4:06B7", seg, (off + ax) & 0xFFFF, ret_to="1771:2ED1")   # 2ECA-2ECC
    drop(mem, 2)                                            # 0644 pops the pointer 06B7 left (retf 0xA)
    yield from gcall(mem, 0xC, dx, "23E4:0644", ss, local, dest_seg, dest_off, 0xC, ret_to="1771:2EDF")   # 2ED1-2EDA


@PORTS.port("1771:0E6C", ret="retf 2")
def formation_label(mem, variant):
    """0E6C: 'defence-midfield-attack' of the country's available players of squad slots 1..11 by DS:0D5C[position]
    (3216 per slot), built with 214B:09DA (Str) and 23E4:06B7 (concatenate) and assigned with a maximum of 10 (0644)
    into the string at the far pointer [bp + 8]."""
    country = mem.arg(0)
    dest_off, dest_seg = mem.arg(1), mem.arg(2)
    f = mem.enter(0x30A, "1771:0E6C")                       # 0E6C-0E6F
    bp, ss, cs = mem.reg("bp"), mem.reg("ss"), mem.seg(0x1771)
    ax, dx = mul(country, 0xBF)                             # 0E73-0E79
    c = Rec(mem, COUNTRIES, ax)
    ptr_local(f, -0xA, c, "1771:0E81", "1771:0E84")
    ax = 0                                                  # 0E87-0E8F: the four counts [bp - 4 .. bp - 1] := 0, i := 1
    f.w16(-4, 0, "1771:0E89")
    f.w16(-2, 0, "1771:0E8C")
    for i in range(1, 12):                                  # 0E8F-0EE8
        f.w16(-6, i, "1771:0E96" if i > 1 else "1771:0E8F")
        ax = 2 * i
        w = c.u16(2 * i - 2)                                # 0E99-0EA3
        ax, dx = yield from gcall(mem, ax, dx, "1771:3216", w, ret_to="1771:0EAB")          # 0EA3-0EA8
        if ax & 0xFF:                                       # 0EAB-0EAD: unavailable
            continue
        ax, dx = mul(w, 0x14)                               # 0EAF-0EC0
        q = Rec(mem, PLAYERS, ax)
        ptr_local(f, -0xE, q, "1771:0EC8", "1771:0ECB")
        code = mem.ds8(0xD5C + q.u8(6))                     # 0ECE-0EDD (xor ah, ah)
        ax = code
        f.w8(code - 4, f.u8(code - 4) + 1, "1771:0EE1")     # 0EDF-0EE1: inc byte [bp + di - 4]
    counts = [f.u8(-4), f.u8(-3), f.u8(-2), f.u8(-1)]
    buffers = [(bp - 0x10A) & 0xFFFF, (bp - 0x20A) & 0xFFFF, (bp - 0x30A) & 0xFFFF]
    # defence: Str(count) onto the stack, then the separator CS:0E6A (a string of one byte, '-')
    push(mem, ss, "1771:0EEE")                              # 0EEA-0EEF: lea di, [bp - 0x10a]; push ss; push di
    push(mem, buffers[0], "1771:0EEF")
    ax, dx = yield from gcall(mem, counts[1], 0, "214B:09DA", 0, counts[1], ret_to="1771:0EFE")   # 0EF0-0EF9
    ax, dx = yield from gcall(mem, ax, dx, "23E4:06B7", cs, 0x0E6A, ret_to="1771:0F08")          # 0EFE-0F03
    push(mem, ss, "1771:0F0C")                              # 0F08-0F0D
    push(mem, buffers[1], "1771:0F0D")
    ax, dx = yield from gcall(mem, counts[2], 0, "214B:09DA", 0, counts[2], ret_to="1771:0F1C")   # 0F0E-0F17
    drop(mem, 2)
    ax, dx = yield from gcall(mem, ax, dx, "23E4:06B7", ss, buffers[1], ret_to="1771:0F21")      # 0F1C
    ax, dx = yield from gcall(mem, ax, dx, "23E4:06B7", cs, 0x0E6A, ret_to="1771:0F2B")          # 0F21-0F26
    push(mem, ss, "1771:0F2F")                              # 0F2B-0F30
    push(mem, buffers[2], "1771:0F30")
    ax, dx = yield from gcall(mem, counts[3], 0, "214B:09DA", 0, counts[3], ret_to="1771:0F3F")   # 0F31-0F3A
    drop(mem, 2)
    ax, dx = yield from gcall(mem, ax, dx, "23E4:06B7", ss, buffers[2], ret_to="1771:0F44")      # 0F3F
    drop(mem, 2)                                            # 0644 pops the first pointer too (retf 0xA)
    yield from gcall(mem, 0xA, dx, "23E4:0644", ss, buffers[0], dest_seg, dest_off, 0xA, ret_to="1771:0F52")   # 0F44-0F4D


# -- the player's own tactics ------------------------------------------------------------------------------------
@PORTS.port("1771:33CD", ret="retf 2")
def force_tactic4_off(mem, variant):
    """33CD: set element 8 and clear element 4 of the player's +0xF (214B:0C79, 0CA1)."""
    f = mem.enter(4, "1771:33CD")                           # 33CD-33D0
    ax, dx = mul(mem.arg(0), 0x14)                          # 33D3-33D9
    p = Rec(mem, PLAYERS, ax)
    ptr_local(f, -4, p, "1771:33E1", "1771:33E4")
    ax, dx = yield from bit_op(mem, "214B:0C79", dx, p, 0xF, 8, "1771:33F9")    # 33E7-33F4
    ax, dx = yield from bit_op(mem, "214B:0CA1", dx, p, 0xF, 4, "1771:340B")    # 33F9-3406
    return end(mem, ax, dx)


@PORTS.port("1771:3431", ret="retf 2")
def set_player_tactics(mem, variant):
    """3431: from the player's own fields: element 8 on and 4 off when the hardness is below 4 (33CD), then by the
    position code (the set CS:3411): elements 5 and 1, or for position 2 elements 5 (when +5 < 0xE), 6 and 2."""
    n = mem.arg(0)
    f = mem.enter(4, "1771:3431")                           # 3431-3434
    ax, dx = mul(n, 0x14)                                   # 3437-343D
    p = Rec(mem, PLAYERS, ax)
    ptr_local(f, -4, p, "1771:3445", "1771:3448")
    ax, dx = yield from gcall(mem, ax, dx, "1771:2FFB", n, ret_to="1771:3452")      # 344B-344F
    if (ax & 0xFF) < 4:                                     # 3452: cmp al, 4; jae
        ax, dx = yield from gcall(mem, ax, dx, "1771:33CD", n, ret_to="1771:345D")  # 3456-345A
    pos = p.u8(6)                                           # 345D-3464: mov al, [di + 6]
    ax = (ax & 0xFF00) | pos
    cs = mem.reg("cs")
    ax, dx, member = yield from set_test(mem, ax, dx, cs, 0x3411, "1771:346F")      # 3465-346A (the set CS:3411)
    if member:                                              # 346F: je 3497 (not in the set)
        ax, dx = yield from bit_op(mem, "214B:0C79", dx, p, 0xF, 5, "1771:3483")    # 3471-347E
        ax, dx = yield from bit_op(mem, "214B:0C79", dx, p, 0xF, 2 if variant == "tactic-element-2-for-1" else 1, "1771:3495")    # 3483-3490
        return end(mem, ax, dx)
    if pos == 2:                                            # 3497-349F
        if p.u8(5) < 0xE:                                   # 34A4-34A9: jae 34BD
            ax, dx = yield from bit_op(mem, "214B:0C79", dx, p, 0xF, 5, "1771:34BD")    # 34AB-34B8
        ax, dx = yield from bit_op(mem, "214B:0C79", dx, p, 0xF, 6, "1771:34CF")        # 34BD-34CA
        ax, dx = yield from bit_op(mem, "214B:0C79", dx, p, 0xF, 2, "1771:34E1")        # 34CF-34DC
    return end(mem, ax, dx)


@PORTS.port("1771:34E7", ret="retf 2")
def reset_own_tactics(mem, variant):
    """34E7: the +0xF of each of a country's players (squad slots 1..20, a word 0 is empty) cleared, then 3431."""
    country = mem.arg(0)
    f = mem.enter(6, "1771:34E7")                           # 34E7-34EA
    ax, dx = mul(country, 0xBF)                             # 34ED-34F3
    c = Rec(mem, COUNTRIES, ax)
    ptr_local(f, -6, c, "1771:34FB", "1771:34FE")
    for slot in range(1, 0x15):                             # 3501-3550
        f.w16(-2, slot, "1771:3501" if slot == 1 else "1771:3508")
        ax = (2 * slot) & 0xFFFF                            # 350B-350E: shl ax, 1
        word = c.u16(2 * slot - 2)                          # 3510-3515
        if word == 0:                                       # 351A: je 354C
            continue
        ax, dx = mul(word, 0x14)                            # 3526-352D
        Rec(mem, PLAYERS, ax).w8(0xF, 0, "1771:3535")       # 352F-3535
        ax = (2 * slot) & 0xFFFF                            # 353A-353D
        ax, dx = yield from gcall(mem, ax, dx, "1771:3431", word, ret_to="1771:354C")   # 3544-3549
    return end(mem, ax, dx)


# -- a player's strength -------------------------------------------------------------------------------------------
@PORTS.port("1771:3179", ret="retf 2")
def out_of_place_flag(mem, variant):
    """3179: 1 when the player plays on the wrong foot for the position (3088, 3041, the sets CS:3139 and CS:3159) or
    when exactly one of +6 and +7 is 0."""
    n = mem.arg(0)
    f = mem.enter(6, "1771:3179")                           # 3179-317C
    ax, dx = mul(n, 0x14)                                   # 317F-3185
    p = Rec(mem, PLAYERS, ax)
    ptr_local(f, -6, p, "1771:318D", "1771:3190")
    ax, dx = yield from gcall(mem, ax, dx, "1771:3088", n, ret_to="1771:319A")      # 3193-3197
    foot = ax & 0xFF                                        # 319A: [bp - 2] = al
    f.w8(-2, foot, "1771:319A")
    ax, dx = yield from gcall(mem, ax, dx, "1771:3041", n, ret_to="1771:31A4")      # 319D-31A1
    cs = mem.reg("cs")
    flag = None
    if not (ax & 0xFF) and foot != 0:                       # 31A4-31AC: not two-footed, a foot
        ax = (ax & 0xFF00) | p.u8(6)                        # 31AE-31B5
        right = 0x3159 if variant == "foot-sets-swapped" else 0x3139
        ax, dx, member = yield from set_test(mem, ax, dx, cs, right, "1771:31C0")       # 31B6-31BB: the set CS:3139
        if member:                                          # 31C0: jne 3208
            flag = 1
    if flag is None and foot == 0:                          # 31C2-31DA
        ax = (ax & 0xFF00) | p.u8(6)                        # 31C8-31CF
        left = 0x3139 if variant == "foot-sets-swapped" else 0x3159
        ax, dx, member = yield from set_test(mem, ax, dx, cs, left, "1771:31DA")        # 31D0-31D5: the set CS:3159
        if member:                                          # 31DA: jne 3208
            flag = 1
    if flag is None:
        p6, p7 = p.u8(6), p.u8(7)                           # 31DC-3202
        flag = 1 if (p6 == 0) != (p7 == 0) else 0
    f.w8(-1, flag, "1771:320A")
    return ret(mem, (ax & 0xFF00) | flag, dx)               # 3204/3208, 320A-3210


@PORTS.port("1771:377E", ret="retf 2")
def player_strength(mem, variant):
    """377E: (+4 - 0x3E) + s8(+0xE), then plus s8(+0xC) when that is below 0x20 else minus a sixteenth, clamped 0..0x100,
    halved when 3179 says so; 0 when 3216 says unavailable. (T43's model: runtime/model/quick_engine.py.)"""
    n = mem.arg(0)
    f = mem.enter(8, "1771:377E")                           # 377E-3781
    ax, dx = mul(n, 0x14)                                   # 3784-378A
    p = Rec(mem, PLAYERS, ax)
    ptr_local(f, -8, p, "1771:3792", "1771:3795")
    ax, dx = yield from gcall(mem, ax, dx, "1771:3216", n, ret_to="1771:379F")      # 3798-379C
    if ax & 0xFF:                                           # 379F-37A1
        f.w16(-2, 0, "1771:37A5")                           # 37A3-37A8
        return ret(mem, 0, dx)
    dx = s8(p.u8(0xE)) & 0xFFFF                             # 37AA-37B2: cwde; mov dx, ax
    v = (p.u8(4) - 0x3E + dx) & 0xFFFF                      # 37B4-37C2
    ax = v
    c = s8(p.u8(0xC))
    if c >= 0x20:                                           # 37C8-37CD: jl 37DD
        q, dx = idiv(s16(v), 0x10)                          # 37CF-37D6: cdq; idiv 0x10
        v = (v - q) & 0xFFFF                                # 37D8
        ax = q
    else:
        ax = c & 0xFFFF                                     # 37DD-37E5: cwde; add [bp - 4], ax
        v = (v + c) & 0xFFFF
    if s16(v) < 0:                                          # 37E8-37F3
        v, ax = 0, 0
    elif s16(v) > 0x100:                                    # 37F5-37FC
        v = 0x100
    f.w16(-4, v, "1771:3801")                               # the clamped value, as [bp - 4] holds it at 3801
    ax, dx = yield from gcall(mem, ax, dx, "1771:3179", n, ret_to="1771:3808")      # 3801-3805
    if ax & 0xFF:                                           # 3808-380A
        q, dx = idiv(s16(v), 2)                             # 380C-3813: cdq; idiv 2
        v = q
        ax = q
        f.w16(-4, v, "1771:3815")
    else:
        ax = v
    f.w16(-2, v, "1771:381B")
    return ret(mem, v, dx)                                  # 3818-3821 (AX = v in both cases)


# -- the marking words ---------------------------------------------------------------------------------------------
@PORTS.port("1771:3E2F", ret="ret 6")
def pick_mark_target(mem, variant):
    """3E2F (a nested procedure of 3EF8; its parent's BP, hi, lo): for the opposing slots 11 down to 2 whose position
    byte (the opponents' string at BP - 0x1C + slot) is in [lo, hi], and the rows r = 1..4 of the table DS:0EE6 + 14 r
    (the own position that marks it), the first own slot (the own string at BP - 0x10) holding that position is taken: its
    entry is cleared, the opponent's is cleared and the opponent's slot is noted at BP - 0x27 + own slot."""
    parent = mem.frame(mem.arg(0))
    hi, lo = mem.arg(1), mem.arg(2)                         # [bp + 6], [bp + 8]
    ax, dx = mem.reg("ax"), mem.reg("dx")                   # the caller's, which the loop carries when it does not write them
    f = mem.enter(0x106, "1771:3E2F")                       # 3E2F-3E32
    bp = mem.reg("bp")
    pattern = (bp - 0x106) & 0xFFFF                         # 3E73: lea di, [bp - 0x106]
    target = (mem.arg(0) - 0x10) & 0xFFFF                   # 3E9F-3EA2: [bp + 4] + 0xFFF0
    ss = mem.reg("ss")
    for r in range(1, 5):                                   # 3E36-3EEF
        f.w16(-4, r, "1771:3E36" if r == 1 else "1771:3E3D")
        for j in range(11, 1, -1):                          # 3E40-3EE6
            f.w16(-2, j, "1771:3E40" if j == 11 else "1771:3E47")
            oc = parent.u8(j - 0x1C)                        # 3E4D-3E56 (xor ah, ah)
            ax = oc
            if oc < lo:                                     # 3E58-3E5D
                continue
            if oc > hi or (variant == "mark-hi-excl" and oc == hi):    # 3E6E-3E71
                continue
            push(mem, ss, "1771:3E77")                      # 3E73-3E78
            push(mem, pattern, "1771:3E78")
            ax, dx = mul(r, 14)                             # 3E89-3E8C
            ax = (ax & 0xFF00) | mem.ds8(0xEE6 + ((ax + oc) & 0xFFFF))      # 3E8F-3E95
            ax, dx = yield from gcall(mem, ax, dx, "23E4:075A", ax, ret_to="1771:3E9F")     # 3E99-3E9A (leaves the pointer)
            drop(mem, 2)
            ax, dx = yield from gcall(mem, ax, dx, "23E4:06E3", ss, pattern, ss, target, ret_to="1771:3EAD")  # 3EA5-3EA8
            pos = (ax + 1) & 0xFFFF                         # 3EAD: inc ax
            ax = pos
            f.w16(-6, pos, "1771:3EAE")
            if pos <= 1:                                    # 3EB1-3EB5: jbe
                continue
            parent.w8(pos - 0x11, 0, "1771:3EBF")           # 3EB7-3EBF
            parent.w8(j - 0x1C, 0, "1771:3ECC")             # 3EC4-3ECC
            dx = (dx & 0xFF00) | j                          # 3ED1: mov dl, [bp - 2]
            parent.w8(pos - 0x27, j, "1771:3EDC")           # 3ED4-3EDC
    return end(mem, ax, dx)


@PORTS.port("1771:3EF8", ret="retf")
def set_marking_words(mem, variant):
    """3EF8: per team t the marking words (DS:9A3E + 0x28 t + 2 slot): the own positions string (slots 2..11; 0 for a
    sweeper, a protect-zone player or an unavailable one) and the opponents', the protect-zone men cleared from the
    opponents', the five calls of 3E2F, then each marking word set from the match (3E2F's marks) or cleared."""
    f = mem.enter(0x32, "1771:3EF8")
    ss = mem.reg("ss")
    bp = mem.reg("bp")
    DS = mem.DS * 16
    ax = dx = 0
    for t in (0, 1):                                        # 3EFE-3F04, 4250-4256
        other = 1 - t
        f.w8(-5, t, "1771:3EFE" if t == 0 else "1771:3F04")
        ax, dx = mul(mem.ds16(TEAM_COUNTRY + 2 * t), 0xBF)                  # 3F0F-3F16
        mine = Rec(mem, COUNTRIES, ax)
        ptr_local(f, -0x2A, mine, "1771:3F1E", "1771:3F21")
        ax = dx = 0
        mem.w16(DS + ((MARK_BASE + 0x28 * t + 2) & 0xFFFF), 0, "1771:3F31")  # 3F24-3F31: slot 1's word := 0
        ax, dx = mul(mine.u16(2), 0x14)                     # 3F35-3F3F: slot 2's player
        if Rec(mem, PLAYERS, ax).u8(6) == 1:                # 3F41-3F47
            ax = dx = 0
            mem.w16(DS + ((MARK_BASE + 0x28 * t + 4) & 0xFFFF), 0, "1771:3F5B")   # 3F4E-3F5B: slot 2's word := 0
        f.w8(-0x10, 10, "1771:3F5F")                        # 3F5F, 3F63: the two strings' lengths
        f.w8(-0x1B, 10, "1771:3F63")
        for j in range(2, 12):                              # 3F67-4054
            w = mine.u16(2 * j - 2)
            f.w16(-2, j, "1771:3F67" if j == 2 else "1771:3F6E")
            ax, dx = mul(w, 0x14)                           # 3F71-3F82
            q = Rec(mem, PLAYERS, ax)
            ptr_local(f, -0x2E, q, "1771:3F8A", "1771:3F8D")
            unusable = q.u8(6) == 1                         # 3F93: je 3FC7
            if not unusable:
                ax, dx = yield from bit_test(mem, dx, q.u8(0x10), 7, "1771:3FAD")      # 3F9A-3FA8
                unusable = bool(ax & 0xFF)
            if not unusable:
                ax, dx = yield from gcall(mem, ax, dx, "1771:3216", w, ret_to="1771:3FC3")      # 3FB1-3FC0
                unusable = bool(ax & 0xFF)
            if unusable:
                f.w8(j - 0x11, 0, "1771:3FCA")              # 3FC7-3FCA
            else:
                ax = (ax & 0xFF00) | q.u8(6)                # 3FD0-3FD3
                f.w8(j - 0x11, ax & 0xFF, "1771:3FDA")
            ax, dx = mul(mem.ds16(TEAM_COUNTRY + 2 * other), 0xBF)          # 3FDD-3FF5 (cmp [bp - 5], 0; mov al, 0/1; cwde)
            opponents = Rec(mem, COUNTRIES, ax)
            ptr_local(f, -0x2E, opponents, "1771:3FFD", "1771:4000")
            ow = opponents.u16(2 * j - 2)                   # 4003-400D
            ax, dx = mul(ow, 0x14)                          # 400D-4014
            oq = Rec(mem, PLAYERS, ax)
            ptr_local(f, -0x32, oq, "1771:401C", "1771:401F")
            ax, dx = yield from gcall(mem, ax, dx, "1771:3216", ow, ret_to="1771:4034")     # 4022-4031
            if ax & 0xFF:                                   # 4034-4036
                f.w8(j - 0x1C, 0, "1771:403B")              # 4038-403B
            else:
                ax = (ax & 0xFF00) | oq.u8(6)               # 4041-4044
                f.w8(j - 0x1C, ax & 0xFF, "1771:404B")
        for j in range(2, 12):                              # 4057-40FD: the protect-zone men take their own marker's man
            f.w16(-2, j, "1771:4057" if j == 2 else "1771:405E")
            ax, dx = mul(mine.u16(2 * j - 2), 0x14)         # 4061-4072
            q = Rec(mem, PLAYERS, ax)
            ptr_local(f, -0x2E, q, "1771:407A", "1771:407D")
            ax, dx = yield from bit_test(mem, dx, q.u8(0x10), 7, "1771:4093")      # 4080-408E
            if not (ax & 0xFF):                             # 4093: je 40F7
                continue
            for k in range(2, 12):                          # 4097-40F5
                f.w16(-4, k, "1771:4097" if k == 2 else "1771:409E")
                ax, dx = mul(t, 0x28)                       # 40A8-40B3
                bx = mem.ds16(MARK_BASE + 0x28 * t + 2 * j)           # 40B5
                ax, dx = mul(mem.ds16(TEAM_COUNTRY + 2 * other), 0xBF)  # 40C0-40D8
                ax = Rec(mem, COUNTRIES, ax).u16(2 * k - 2)  # 40DA-40E2
                if ax == bx:                                # 40E6-40E8
                    f.w8(k - 0x1C, 0, "1771:40ED")          # 40EA-40ED
        ax, dx = yield from gcall(mem, 0, dx, "214B:0018", ss, (bp - 0x26) & 0xFFFF, 0xB, 0, ret_to="1771:4111")   # 4100-410C
        for hi, lo, ret_to in ((0xD, 0xC, "411D"), (0xB, 9, "4129"), (8, 5, "4135"), (1, 1, "4141"), (4, 2, "414D")):
            ax, dx = yield from gcall(mem, hi, dx, "1771:3E2F", lo, hi, bp, ret_to="1771:" + ret_to, far=False)  # 4111-414A
        for j in range(2, 12):                              # 414D-424D
            f.w16(-2, j, "1771:414D" if j == 2 else "1771:4154")
            ax, dx = mul(mine.u16(2 * j - 2), 0x14)         # 4157-416A
            q = Rec(mem, PLAYERS, ax)
            ptr_local(f, -0x2E, q, "1771:4170", "1771:4173")
            ax, dx = yield from bit_test(mem, dx, q.u8(0x10), 7, "1771:4189")      # 4176-4184
            if not (ax & 0xFF):                             # 418B: jne 41A7
                ax, dx = (0, 0)                             # 418D-41A3: AX := 0 (cwde; mul 0x28; xor ax, ax)
                mem.w16(DS + ((MARK_BASE + 0x28 * t + 2 * j) & 0xFFFF), 0, "1771:41A3")
            ax, dx = yield from bit_test(mem, dx, q.u8(0x10), 7, "1771:41BA")      # 41A7-41B5
            if ax & 0xFF:                                   # 41BA: je 41C1; jmp 4247
                continue
            ax, dx = yield from bit_test(mem, dx, mine.u8(0x2D), 8, "1771:41D4")   # 41C1-41CF: team tactics, element 8
            if not (ax & 0xFF):                             # 41D4
                continue
            mark = f.u8(j - 0x27)                           # 41D8-41DF: jbe 422D
            if mark > 0:                                    # 41E1-4227
                ax, dx = mul(mem.ds16(TEAM_COUNTRY + 2 * other), 0xBF)      # 41FE-4205
                bx = Rec(mem, COUNTRIES, ax).u16(2 * mark - 2)             # 4207-420F
                ax, dx = mul(t, 0x28)                       # 421A-4223
                mem.w16(DS + ((MARK_BASE + 0x28 * t + 2 * j) & 0xFFFF), bx, "1771:4227")
            else:
                ax, dx = mul(t, 0x28)                       # 422D-423D
                ax = 0                                      # 4241
                mem.w16(DS + ((MARK_BASE + 0x28 * t + 2 * j) & 0xFFFF), 0, "1771:4243")
    return end(mem, ax, dx)
