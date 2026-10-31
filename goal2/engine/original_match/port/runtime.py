"""The runtime primitives (T60, P1a): GOAL.EXE's own library `214B` (fills, moves, swaps, the set bits, long min and max,
the wrap-add, the clamps, the run-length screen unpackers, number to string, the draw `06D0`) and Turbo Pascal 5.5's System
unit `23E4` (Move, the long multiply and divide, the Pascal string routines, Str, UpCase), 38 routines.

From the listing (static/goal-exe/code/seg_214B_01.asm, _02, _03, _04 and seg_23E4_01.asm, _02, _03); the line comments
are the listing's offsets. Each routine is written as the original's instructions, in the registers it works in (`Regs`),
so that what it leaves in AX, DX (the proof compares them, port/prove.py) and in the scratch registers is the original's
too; the memory it writes is written in the original's order, each write naming the instruction that makes it (`at`).

The stack. The memory digests of a match (records.py) cover the 64 KiB from DS, which includes the stack segment, so the
bytes a routine's frame leaves below SP (the saved BP, the locals, the arguments and return addresses it pushes for the
routines it calls, and those routines' frames) are part of what a ported match must equal at its end. `Regs` therefore
carries the stack the listing's code would have: `enter`/`leave` are `push bp; mov bp, sp; sub sp, n` / `mov sp, bp; pop
bp`, `push` writes a word, `local8`/`local16` a local, and `invoke` the pushes and the return address of a call to a
routine that is itself written here (its frame is then written by that routine). A routine entered from the original's
code finds SP at its return address; the port's SP and BP are put back at its return (port/guest.py). The proof ignores
the dead frame (port/prove.py); the fuzz against the original compares it (out/T60/fuzz.py). The frames of 23E4:0787 and 07DB (two 256-byte temporaries each, which no match of ALL reaches) are written
as they end, not instruction by instruction.

Conventions of the listing, used throughout:
- a far routine's stack arguments: `arg(0)` is the word nearest the return address ([bp + 6] after `push bp; mov bp, sp`,
  ss:[bx + 4] after `mov bx, sp`), a far pointer is two words (offset, then segment);
- `ES:DI`, `DS:SI` are loaded as the listing loads them; the programs's DS is put back by `mov ds, dx` / `pop ds`, so a
  port never changes it; `DX` is left holding the DS value where the listing's `mov dx, ds` stays (the Pascal strings);
- the direction flag: `cld` clears it, and `214B:003C`'s backward copy leaves it SET (no `cld` follows its `std`).

The registers the proof does not compare (BX, CX, SI, DI, ES, the flags) are set where the listing's values are cheap to
give; the flags only where a caller reads them (the string comparison `23E4:072F`, the direction flag). Every other
flag is left as it came: a difference there is counted as scratch by the proof, never an error (port/prove.py)."""
import struct

from . import Registry
from .mem import PortError, s16
from .pilot import rand

PORTS = Registry("runtime", "214B's fills, moves, set bits, long min/max, wrap-add, clamps, screen unpackers and "
                            "23E4's Move, long multiply/divide, Pascal strings, Str, UpCase (T60)")
PORTS.variant("wrap-high-inclusive", "1C86's upper-bound test `jb` read as `jbe` (1CB4): a sum equal to the bound wraps")
PORTS.variant("clamp-high-uses-lo", "2000's upper clamp stores the lower bound ([bp+8]) for the upper ([bp+6]) at 2022")
PORTS.variant("max-unsigned-high", "0D56 compares the high words unsigned (0D64 jg -> ja, 0D66 jl -> jb)")
PORTS.variant("min-unsigned-high", "0D1C compares the high words unsigned (0D2A jg -> ja, 0D2C jl -> jb)")
PORTS.variant("bit-shift-1", "0C57 tests bit k, not bit k-1 (0C60 dec ax removed)")

M16 = 0xFFFF
CF, PF, AF, ZF, SF, OF, DF = 0x0001, 0x0004, 0x0010, 0x0040, 0x0080, 0x0800, 0x0400
ARITH = CF | PF | AF | ZF | SF | OF
STACK_AT = "214B:0000"          # the instruction a stack write names: nothing of the kit watches the stack


# -- the registers and the stack -------------------------------------------------------------------------------------
def entry_sp(mem):
    """SP at the entry of the port running: the word at it is the return address."""
    return mem._entries[-1][0]


def args(mem, n):
    """The first n words of the stack arguments of the routine running (arg 0 nearest the return address): one read."""
    sp, far = mem._entries[-1]
    return struct.unpack("<%dH" % n, mem.read(mem.ss_lin(sp + (4 if far else 2)), 2 * n))


class Regs:
    """A routine's registers: read from the machine when first used, written back by store() (only those it set). The
    16-bit registers are masked at every assignment; `al` and `ah` are the halves of AX. SP and BP are the stack the
    listing's code would have at this point (see the module doc); `push`, `enter`, `leave`, `local8`, `local16` write it,
    collected and written to memory by flush()/store() in runs (one write for a frame's contiguous words): a direct write of
    the port to its own frame's locals is preceded by flush()."""
    _NAMES = ("ax", "bx", "cx", "dx", "si", "di", "es", "sp", "bp")
    _NAME_SET = frozenset(_NAMES)       # T117: the same names, for the membership tests on every access
    __slots__ = ("_mem", "_v", "_dirty", "_flags_on", "_flags_off", "_ss", "_pending", "_bps", "_fresh")

    def __init__(self, mem, resumed=False):
        """resumed: after a guest call the machine's SP is where the port left it (stored before the call); else it is
        the entry's, which the port frame has (no read)."""
        # Plain slot assignments: Regs has no __setattr__ of its own since T117.
        self._fresh = not resumed
        self._mem = mem
        self._v = {}
        self._dirty = set()
        self._flags_on = 0
        self._flags_off = 0
        self._ss = None
        self._pending = []
        self._bps = []

    def __getattr__(self, name):
        # T117: the registers are properties (below); this is reached for any other missing name only.
        raise AttributeError(name)

    @property
    def al(self):
        return self.ax & 0xFF

    @al.setter
    def al(self, v):
        self.ax = (self.ax & 0xFF00) | (v & 0xFF)

    @property
    def ah(self):
        return self.ax >> 8

    @ah.setter
    def ah(self, v):
        self.ax = (self.ax & 0xFF) | ((v & 0xFF) << 8)

    @property
    def ss(self):
        v = self._ss
        if v is None:
            v = self._mem.reg("ss")
            object.__setattr__(self, "_ss", v)
        return v

    # -- the stack ---------------------------------------------------------------------------------------------------
    def _put(self, off, data):
        self._pending.append((self.ss * 16 + (off & M16), data))

    def push(self, value):
        sp = (self.sp - 2) & M16
        self._pending.append((self.ss * 16 + sp, (value & M16).to_bytes(2, "little")))
        self.sp = sp

    def enter(self, size=0):
        """push bp; mov bp, sp; sub sp, size."""
        bp = self.bp
        self._bps.append(bp)
        self.push(bp)
        self.bp = self.sp
        self.sp = self.sp - size

    def leave(self):
        """mov sp, bp; pop bp."""
        self.sp = self.bp
        if self._bps:
            self.bp = self._bps.pop()
        else:                                          # after a guest call: the frame was written to memory
            self.flush()
            self.bp = self._mem.u16(self._mem.ss_lin(self.sp))
        self.sp = self.sp + 2

    def local8(self, off, value):
        self._pending.append((self.ss * 16 + ((self.bp + off) & M16), bytes((value & 0xFF,))))

    def local16(self, off, value):
        self._pending.append((self.ss * 16 + ((self.bp + off) & M16), (value & M16).to_bytes(2, "little")))

    def flush(self):
        """The stack words collected so far, written to memory in order (later writes win), one write per run of bytes."""
        pend = self._pending
        if not pend:
            return
        mem = self._mem
        at = mem._at(STACK_AT)
        if len(pend) == 1:
            addr, data = pend[0]
            mem._write(addr, len(data), int.from_bytes(data, "little"), at)
        else:
            lo = min(a for a, _ in pend)
            hi = max(a + len(d) for a, d in pend)
            buf = bytearray(hi - lo)
            seen = bytearray(hi - lo)
            for a, d in pend:
                buf[a - lo:a - lo + len(d)] = d
                seen[a - lo:a - lo + len(d)] = b"\x01" * len(d)
            i, n = 0, hi - lo
            while i < n:
                if seen[i]:
                    j = i
                    while j < n and seen[j]:
                        j += 1
                    mem._write(lo + i, j - i, int.from_bytes(buf[i:j], "little"), at)
                    i = j
                else:
                    i += 1
        del pend[:]

    # -- flags -------------------------------------------------------------------------------------------------------
    def cld(self):
        object.__setattr__(self, "_flags_off", self._flags_off | DF)
        object.__setattr__(self, "_flags_on", self._flags_on & ~DF)

    def std(self):
        object.__setattr__(self, "_flags_on", self._flags_on | DF)
        object.__setattr__(self, "_flags_off", self._flags_off & ~DF)

    def arith(self, bits):
        """The six arithmetic flags as the listing's last flag-setting instruction leaves them."""
        object.__setattr__(self, "_flags_on", (self._flags_on & ~ARITH) | bits)
        object.__setattr__(self, "_flags_off", self._flags_off | (ARITH & ~bits))

    def reload(self):
        """After a call of the original's code: its registers are what the callee left."""
        self._v.clear()
        self._dirty.clear()

    def store(self, stack=False):
        """The stack words and the registers set, written to the machine. SP and BP only with stack=True (before a guest
        call: PortFrame puts them back at the port's return)."""
        self.flush()
        for name in self._dirty:
            if stack or (name != "sp" and name != "bp"):
                self._mem.set_reg(name, self._v[name])
        self._dirty.clear()
        if self._flags_on or self._flags_off:
            f = self._mem.reg("eflags")
            self._mem.set_reg("eflags", (f & ~self._flags_off) | self._flags_on)
            object.__setattr__(self, "_flags_on", 0)
            object.__setattr__(self, "_flags_off", 0)



def _register_property(name):
    """[T117] A Regs register as a property, doing what Regs.__getattr__/__setattr__ did: read from the
    machine when first used (SP of a fresh frame from the entry), masked to 16 bits at every assignment."""
    def get(self):
        v = self._v.get(name)
        if v is None:
            if name == "sp" and self._fresh:
                v = self._mem._entries[-1][0]
            else:
                v = self._mem.reg(name) & M16
            self._v[name] = v
        return v

    def put(self, value):
        self._v[name] = value & M16
        self._dirty.add(name)
    return property(get, put)


for _name in Regs._NAMES:
    setattr(Regs, _name, _register_property(_name))
del _name

def invoke(mem, R, cs_paragraph, ret_ip, core, *args, pushes=()):
    """`push w1; ... push wn; push cs; call core` (or `call far core`): the words, the segment (None for a near call) and
    the return address are written, then the callee `core(mem, R, *args)` writes its frame; it pops them all (Pascal), so
    the stack pointer comes back to where it was."""
    sp0 = R.sp
    for w in pushes:
        R.push(w)
    if cs_paragraph is not None:
        R.push(mem.seg(cs_paragraph))
    R.push(ret_ip)
    core(mem, R, *args)
    R.sp = sp0


def sub_flags(a, b, bits):
    """CF PF AF ZF SF OF of `cmp a, b` on bits-wide operands."""
    mask = (1 << bits) - 1
    a &= mask
    b &= mask
    r = (a - b) & mask
    sign = 1 << (bits - 1)
    f = 0
    if a < b:
        f |= CF
    if bin(r & 0xFF).count("1") % 2 == 0:
        f |= PF
    if (a ^ b ^ r) & 0x10:
        f |= AF
    if r == 0:
        f |= ZF
    if r & sign:
        f |= SF
    if (a ^ b) & (a ^ r) & sign:
        f |= OF
    return f


def add_flags(a, b, bits=16):
    """CF PF AF ZF SF OF of `add a, b`."""
    mask = (1 << bits) - 1
    a &= mask
    b &= mask
    r = (a + b) & mask
    sign = 1 << (bits - 1)
    f = 0
    if a + b > mask:
        f |= CF
    if bin(r & 0xFF).count("1") % 2 == 0:
        f |= PF
    if (a ^ b ^ r) & 0x10:
        f |= AF
    if r == 0:
        f |= ZF
    if r & sign:
        f |= SF
    if ~(a ^ b) & (a ^ r) & sign:
        f |= OF
    return f


def or_flags(value, eflags):
    """The 16-bit flags word after `or r, r` of the word `value`: SF, ZF, PF from it, CF, OF, AF clear, the rest as before
    (what `pushf` writes at 029D and 02AC)."""
    f = (eflags & 0xFFFF & ~ARITH) | 0x0002
    if bin(value & 0xFF).count("1") % 2 == 0:
        f |= PF
    if value & M16 == 0:
        f |= ZF
    if value & 0x8000:
        f |= SF
    return f


def shift_count(cl):
    """An x86 shift by CL uses its low five bits."""
    return cl & 0x1F


# -- the string and block moves ------------------------------------------------------------------------------------
def _copy_forward(mem, sseg, soff, dseg, doff, n, at):
    """`rep movsb` with DF clear: n bytes, one write each, each byte read just before it is written (so an overlap is
    the CPU's). Returns the offsets after."""
    if n <= 0:
        return soff & M16, doff & M16
    sl, dl = sseg * 16 + (soff & M16), dseg * 16 + (doff & M16)
    if n > 8 and soff + n <= 0x10000 and doff + n <= 0x10000 and (sl + n <= dl or dl + n <= sl):
        data = mem.read(sl, n)                                  # no overlap and no wrap: reading first is the same
        for k in range(n):
            mem.w8(dl + k, data[k], at)
    else:
        for k in range(n):
            mem.w8(dseg * 16 + ((doff + k) & M16), mem.u8(sseg * 16 + ((soff + k) & M16)), at)
    return (soff + n) & M16, (doff + n) & M16


def _write_pstring(mem, seg, off, data, at_len, at_move):
    """A Pascal string written as 0644/0676 do: the length byte, then the characters."""
    mem.w8(seg * 16 + (off & M16), data[0], at_len)
    for k in range(data[0]):
        mem.w8(seg * 16 + ((off + 1 + k) & M16), data[1 + k], at_move)


# -- 214B: fills, moves, swaps ------------------------------------------------------------------------------------
@PORTS.port("214B:0000", ret="retf 8")
def fill_words(mem, variant):
    """u214b_fill_words(var dest; count; value): `rep stosw` of the value (0003-0010)."""
    value, count, off, seg = args(mem, 4)
    R = Regs(mem)
    R.enter()                                                 # 0000
    R.cx, R.es = count, seg                                   # 0003, 0007
    R.cld()                                                   # 000B
    R.ax = value                                              # 000C
    base = seg * 16
    for k in range(count):                                    # 0010 rep stosw
        mem.w16(base + ((off + 2 * k) & M16), value, "214B:0010")
    R.di, R.cx = (off + 2 * count) & M16, 0
    R.leave()
    R.store()


@PORTS.port("214B:0018", ret="retf 8")
def fill_bytes(mem, variant):
    """u214b_fill_bytes(dest; count; value): words of the byte twice, then the odd byte (001B-0034)."""
    value, count, off, seg = args(mem, 4)
    R = Regs(mem)
    R.enter()
    R.push(count)                                             # 001F push cx
    R.cld()                                                   # 0022
    R.es = seg                                                # 0023
    R.ax = value                                              # 0027
    R.ah = R.al                                               # 002B mov ah, al
    word = R.ax
    base = seg * 16
    for k in range(count >> 1):                               # 002D rep stosw
        mem.w16(base + ((off + 2 * k) & M16), word, "214B:002D")
    di = (off + 2 * (count >> 1)) & M16
    if count & 1:                                             # 0034 rep stosb with cx = count & 1
        mem.w8(base + di, word & 0xFF, "214B:0034")
        di = (di + 1) & M16
    R.di, R.cx = di, 0
    R.sp = R.sp + 2                                           # 002F pop cx
    R.leave()
    R.store()


@PORTS.port("214B:003C", ret="retf 0xa")
def move_bytes(mem, variant):
    """u214b_move_bytes(src; dest; count): words, forward when SI > DI (offsets only, 0057), else backward (005B-0072);
    the odd byte first (the top one backward, the bottom one forward). The backward copy leaves DF set."""
    n, doff, dseg, soff, sseg = args(mem, 5)
    R = Regs(mem)
    R.enter()
    R.push(mem.DS)                                     # 003F push ds
    R.dx = n & 1                                              # 004C-004E
    R.ax = n                                                  # 0052
    words = n >> 1                                            # 0054
    si, di = soff, doff
    R.es = dseg
    if si > di:                                               # 0057 cmp si, di; 0059 ja 006C
        R.cld()                                               # 0056
        if n & 1:                                             # 006C-0071
            mem.w8(dseg * 16 + di, mem.u8(sseg * 16 + si), "214B:0071")
            si, di = (si + 1) & M16, (di + 1) & M16
        step = 2
    else:
        R.std()                                               # 005B
        si = (si + n - 1) & M16                               # 005C-005E
        di = (di + n - 1) & M16                               # 005F-0061
        if n & 1:                                             # 0062-0067
            mem.w8(dseg * 16 + di, mem.u8(sseg * 16 + si), "214B:0067")
            si, di = (si - 1) & M16, (di - 1) & M16
        si, di = (si - 1) & M16, (di - 1) & M16               # 0068-0069
        step = -2
    for _ in range(words):                                    # 0072 rep movsw
        mem.w16(dseg * 16 + di, mem.u16(sseg * 16 + si), "214B:0072")
        si, di = (si + step) & M16, (di + step) & M16
    R.si, R.di, R.cx = si, di, 0
    R.sp = R.sp + 2                                           # 0074 pop ds
    R.leave()
    R.store()


@PORTS.port("214B:007B", ret="retf 0xa")
def swap_bytes(mem, variant):
    """u214b_swap_bytes(a; b; count): exchanges count bytes between the two buffers; a count of 0 is 65536 (`loop`)."""
    n, boff, bseg, aoff, aseg = args(mem, 5)
    R = Regs(mem)
    R.enter()
    R.push(mem.DS)                                     # 007E push ds
    R.cld()                                                   # 008B
    si, di = aoff, boff
    R.es = bseg
    al = R.al
    for _ in range(n or 0x10000):                             # 008C-0093 (loop decrements first)
        mine = mem.u8(bseg * 16 + di)                         # 008C mov al, es:[di]
        theirs = mem.u8(aseg * 16 + si)                       # 008F xchg [si], al
        mem.w8(aseg * 16 + si, mine, "214B:008F")
        al = theirs
        si = (si + 1) & M16                                   # 0091
        mem.w8(bseg * 16 + di, al, "214B:0092")               # 0092 stosb
        di = (di + 1) & M16
    R.al = al
    R.si, R.di, R.cx = si, di, 0
    R.sp = R.sp + 2                                           # 0095 pop ds
    R.leave()
    R.store()


@PORTS.port("214B:009C", ret="retf 4")
def upcase_string(mem, variant):
    """u214b_upcase_string(src; var dest): the length byte as it is, then at most min(length, 0x50) characters upper-cased
    (a-z minus 0x20); 0644 first clips the length to 0x50 into a local (009F-00B0), the copy reads the source again."""
    soff, sseg, doff, dseg = args(mem, 4)
    R = Regs(mem)
    R.enter(0x52)                                             # 009C-009F
    ss = R.ss
    local = (R.bp - 0x51) & M16
    sp0 = R.sp
    for w in (sseg, soff, ss, local, 0x50):                   # 00A2-00AF push es; push di; push ss; push di; push ax
        R.push(w)
    R.ax = 0x50                                               # 00AC
    R.push(mem.seg(0x214B))                                   # 00B0 call far 0644: the return address
    R.push(0x00B5)
    length = mem.u8(sseg * 16 + soff)                         # 0644 lodsb ... clipped to the maximum 0x50
    clipped = min(length, 0x50)
    R.flush()
    _write_pstring(mem, ss, local, bytes([clipped]) + mem.read(sseg * 16 + ((soff + 1) & M16), clipped),
                   "23E4:065C", "23E4:0661")                  # the copy into the local
    R.bx = (R.sp) & M16                                       # 0645: SP at the call of 0644
    R.sp = sp0
    R.al = clipped                                            # 0656-065A
    R.dx = mem.DS                                      # 0647
    R.cld()
    R.push(mem.DS)                                     # 00B5 push ds
    mem.w8(dseg * 16 + doff, length, "214B:00BF")             # 00BF movsb: the unclipped length byte
    count = R.al                                              # 00C0-00C2
    si, di = (soff + 1) & M16, (doff + 1) & M16
    for _ in range(count):                                    # 00C6-00D2
        al = mem.u8(sseg * 16 + si)
        si = (si + 1) & M16
        if 0x61 <= al <= 0x7A:
            al -= 0x20
        R.al = al
        mem.w8(dseg * 16 + di, al, "214B:00D1")
        di = (di + 1) & M16
    R.cx, R.si, R.di, R.es = 0, si, di, dseg
    R.sp = R.sp + 2                                           # 00D4 pop ds
    R.leave()
    R.store()


# -- 214B: the screen unpackers -----------------------------------------------------------------------------------
def unpack_screen(mem, R, soff, sseg, doff, dseg):
    """214B:0147 (0147-01A0): the run-length packed screen at SSEG:SOFF into the text buffer at DSEG:DOFF, rows of
    0xA0 bytes. Header word = the 1-based first cell, then the rows and the columns as bytes; a byte 0xFF sets the
    attribute (AH) of the next characters, 0 repeats the last cell written (DX) a counted number of times."""
    R.enter()                                                 # 0147
    R.push(mem.DS)                                     # 014A push ds
    sbase = sseg * 16
    si = soff
    di = doff
    R.cld()                                                   # 014B
    R.es = dseg
    header = mem.u16(sbase + si)                              # 0152 lodsw
    si = (si + 2) & M16
    di = (di + (((header - 1) & M16) << 1)) & M16             # 0153-0156
    dx = 0                                                    # 0158
    ax = 0                                                    # 015A
    ax = (ax & 0xFF00) | mem.u8(sbase + si)                   # 015C lodsb
    si = (si + 1) & M16
    rows = ax                                                 # 015D mov bx, ax
    ax = (ax & 0xFF00) | mem.u8(sbase + si)                   # 015F lodsb
    si = (si + 1) & M16
    cx = (ax << 1) & M16                                      # 0160-0162
    R.push(R.bp)                                              # 0164 push bp (the frame's, before it is used as a scratch)
    dbase = dseg * 16
    while True:
        end = (di + cx) & M16                                 # 0165-0167
        while di != end:                                      # 0169 cmp di, bp; je 017B
            while True:                                       # 016D
                ax = (ax & 0xFF00) | mem.u8(sbase + si)       # lodsb
                si = (si + 1) & M16
                if (ax & 0xFF) != 0xFF:                       # 016E cmp al, 0xff
                    break
                ax = (ax & 0xFF00) | mem.u8(sbase + si)       # 0189 lodsb
                si = (si + 1) & M16
                ax = ((ax & 0xFF) << 8) | (ax & 0xFF)         # 018A mov ah, al: the attribute is the byte, AL too
            if (ax & 0xFF) == 0:                              # 0172 cmp al, 0; je 018E
                R.push(cx)                                    # 018E push cx (popped at 0198)
                R.sp = R.sp + 2
                run = mem.u8(sbase + si)                      # 018F lodsb (cl)
                si = (si + 1) & M16
                ax = dx                                       # 0194
                for _ in range(run):                          # 0196 rep stosw
                    mem.w16(dbase + di, ax, "214B:0196")
                    di = (di + 2) & M16
            else:
                mem.w16(dbase + di, ax, "214B:0176")          # 0176 stosw
                di = (di + 2) & M16
                dx = ax                                       # 0177
        rows = (rows - 1) & M16                               # 017B dec bx
        if rows == 0:                                         # 017C cmp bx, 0; je 019B
            break
        di = (di - cx + 0xA0) & M16                           # 0181-0183
    R.sp = R.sp + 4                                           # 019B pop bp; 019C pop ds
    R.leave()
    R.ax, R.dx, R.bx, R.cx, R.si, R.di = ax, dx, rows, cx, si, di
    return R


@PORTS.port("214B:0147", ret="retf 8")
def unpack_screen_rle(mem, variant):
    soff, sseg, doff, dseg = args(mem, 4)
    R = Regs(mem)
    unpack_screen(mem, R, soff, sseg, doff, dseg)
    R.store()


def unpack_to_buffer(mem, R, voff, vseg, soff, sseg):
    """214B:0329 (032C-0340): the destination is the far pointer stored at VSEG:VOFF, the source the pointer SSEG:SOFF."""
    R.enter()
    doff, dseg = mem.farptr(vseg * 16 + voff)                  # 032F les di, es:[di]
    invoke(mem, R, 0x214B, 0x033D, lambda m, r: unpack_screen(m, r, soff, sseg, doff, dseg),
           pushes=(dseg, doff, sseg, soff))                    # 0332-033A
    R.leave()


@PORTS.port("214B:0329", ret="retf 8")
def unpack_screen_to_buffer(mem, variant):
    voff, vseg, soff, sseg = args(mem, 4)
    R = Regs(mem)
    unpack_to_buffer(mem, R, voff, vseg, soff, sseg)
    R.store()


@PORTS.port("214B:05DB", ret="retf")
def unpack_screen_796a_to_back(mem, variant):
    """05DB: the packed screen at DS:796A into the buffer DS:A96E points at (05DE-05E9)."""
    ds = mem.DS
    R = Regs(mem)
    R.enter()
    invoke(mem, R, 0x214B, 0x05EC, unpack_to_buffer, 0xA96E, ds, 0x796A, ds, pushes=(ds, 0x796A, ds, 0xA96E))
    R.leave()
    R.store()


@PORTS.port("214B:05F0", ret="retf 2")
def unpack_screen_row_record(mem, variant):
    """05F0(row): DS:79A4 := (row - 1) * 0x50 + 1, then 05DB's unpack with that record as the source (05F6-061C)."""
    row, = args(mem, 1)
    ds = mem.DS
    R = Regs(mem)
    R.enter(4)                                                 # 05F0-05F3
    R.local16(-4, 0x79A4)                                      # 05FB
    R.local16(-2, ds)                                          # 05FE
    product = ((row - 1) & M16) * 0x50                         # 0601-0608
    R.dx = product >> 16
    R.ax = (product & M16) + 1                                 # 060A inc ax
    mem.w16(ds * 16 + 0x79A4, R.ax, "214B:060E")
    invoke(mem, R, 0x214B, 0x061F, unpack_to_buffer, 0xA96E, ds, 0x79A4, ds, pushes=(ds, 0x79A4, ds, 0xA96E))
    R.leave()
    R.store()


# -- 214B: the draw ----------------------------------------------------------------------------------------------
def rng_0688(mem, R, seed_off, seed_seg, n):
    """214B:0688(var seed; n) (0688-06AE): the seed word stepped and stored (069F), the draw 1..n in AX = DX."""
    R.enter(2)                                                 # 0688-068B
    sp0 = R.sp
    R.push(mem.DS)                                      # 068E
    R.push(seed_seg)                                           # 0692 push ds (the seed's segment)
    R.push(seed_off)                                           # 0693 push si
    draw = rand(mem, n)                                        # 0694-06A5: the seed's far pointer is DS:A978 (06D6)
    R.sp = sp0
    R.local16(-2, draw)                                        # 06A5
    R.ax, R.dx = draw, draw
    R.leave()
    return draw


def draw_is_one(mem, R, n):
    """214B:06D0 as a call from a port, from its `call far` on: the draw 1..n through 0688, AX = DX = the draw, then AL = 1
    when it is 1 (06E3-06EC). The caller has pushed n and the return address (the frames are written here)."""
    R.enter(2)                                                 # 06D0-06D3
    seed_off, seed_seg = mem.farptr(mem.DS * 16 + 0xA978)      # 06D6
    sp0 = R.sp
    R.push(seed_seg)                                           # 06DA
    R.push(seed_off)                                           # 06DB
    R.push(n)                                                  # 06DC
    R.push(mem.seg(0x214B))                                    # 06DF push cs
    R.push(0x06E3)                                             # 06E0 call 0688
    rng_0688(mem, R, seed_off, seed_seg, n)
    R.sp = sp0
    R.al = 1 if R.ax == 1 else 0                               # 06E3-06EC
    R.local8(-1, R.al)                                         # 06EE
    R.leave()


@PORTS.port("214B:06D0", ret="retf 2")
def random_is_one(mem, variant):
    """u214b_random_is_one(n): 0688's draw 1..n; AL is 1 when it is 1 (06E3-06EC), AH and DX the draw's."""
    R = Regs(mem)
    draw_is_one(mem, R, args(mem, 1)[0])
    R.store()


# -- 214B: number to string -------------------------------------------------------------------------------------
POWERS_OF_TEN = (1000000000, 100000000, 10000000, 1000000, 100000, 10000, 1000, 100, 10, 1)    # 23E4:1236, 4 bytes each


def long_to_digits(value):
    """23E4:11E4: a signed 32-bit integer as ASCII digits, '-' first when negative (11E4-1235)."""
    value &= 0xFFFFFFFF
    out = b""
    if value & 0x80000000:                                    # 11E8 or dx, dx; jge
        value = (-value) & 0xFFFFFFFF                          # 11EC-11F3: not, not, add 1, adc 0
        out = b"-"
    return out + str(value).encode()


def str_of_long(value, width, maxlen):
    """23E4:12F6 `Str(value:width, s)` into string[maxlen]: the digits, clipped to maxlen, padded to width on the left.
    Returns (pascal bytes, pad count)."""
    digits = long_to_digits(value)
    cx = len(digits)
    ax, dx = s16(width & M16), s16(maxlen & M16)
    if ax > dx:                                               # 1318-131C
        ax = dx
    if cx > dx:                                               # 131E-1322 (cx is signed here)
        cx = dx
    if ax < cx:                                               # 1324-1328
        ax = cx
    pad = ax - cx                                             # 132C
    return bytes([ax & 0xFF]) + b" " * pad + digits[:cx], pad


def digits_to_es_di(mem, R, es, di, value):
    """23E4:11E4 (near, registers; 11E4-1235): the digits of DX:AX at ES:DI, CX their number. The caller's `call` has
    pushed the return address."""
    R.push(di)                                                 # 11E4 push di
    R.flush()
    digits = long_to_digits(value)
    R.cld()
    for k, ch in enumerate(digits):
        at = "23E4:11F8" if ch == 0x2D else "23E4:122B"
        mem.w8(es * 16 + ((di + k) & M16), ch, at)
    R.sp = R.sp + 2                                            # 1232 pop di
    R.al = digits[-1]
    R.bx, R.dx, R.si, R.cx = 0, 0, 0x125E, len(digits)
    return digits


@PORTS.port("23E4:11E4", ret="ret")
def sys_long_to_digits(mem, variant):
    """The signed 32-bit integer in DX:AX as ASCII at ES:DI; CX the number of characters (11E4-1235). Near, registers."""
    R = Regs(mem)
    digits_to_es_di(mem, R, R.es, R.di, (R.dx << 16) | R.ax)
    R.store()


def str_of_long_core(mem, R, mx, doff, dseg, width, low, high):
    """23E4:12F6 Str(value:width, s) into string[max] (12F6-133E)."""
    R.enter(0x20)                                              # 12F6-12F9
    R.flush()
    local = (R.bp - 0x20) & M16
    ss = R.ss
    sp_frame = R.sp
    R.push(ss)                                                 # 1305 push ss; 1306 pop es
    R.sp = sp_frame
    R.push(0x130A)                                             # 1307 call 11E4
    digits = digits_to_es_di(mem, R, ss, local, (high << 16) | low)
    R.sp = sp_frame
    R.push(mem.DS)                                      # 130A push ds
    R.push(ss)                                                 # 130D push ss
    R.sp = R.sp + 2                                            # 130E pop ds
    text, pad = str_of_long(((high << 16) | low), width, mx)
    keep = text[1 + pad:]
    R.cld()
    if pad:                                                    # 1330 push cx (the digits kept), popped at 1337
        R.push(len(keep))
        R.sp = R.sp + 2
    mem.w8(dseg * 16 + doff, text[0], "23E4:132B")             # 132B stosb: the length
    for k in range(pad):                                       # 1335 rep stosb
        mem.w8(dseg * 16 + ((doff + 1 + k) & M16), 0x20, "23E4:1335")
    for k, ch in enumerate(keep):                              # 1338 rep movsb
        mem.w8(dseg * 16 + ((doff + 1 + pad + k) & M16), ch, "23E4:1338")
    R.ax = (((pad >> 8) & 0xFF) << 8 | 0x20) if pad else 0
    R.dx = mx
    R.cx, R.es, R.bx = 0, dseg, 0
    R.di = (doff + 1 + pad + len(keep)) & M16
    R.sp = sp_frame
    R.leave()
    return text


@PORTS.port("23E4:12F6", ret="retf 0xc")
def sys_str_of_long(mem, variant):
    """Str(value:width, s) into string[max] (12F6-133E)."""
    mx, doff, dseg, width, low, high = args(mem, 6)
    R = Regs(mem)
    str_of_long_core(mem, R, mx, doff, dseg, width, low, high)
    R.store()


@PORTS.port("214B:09DA", ret="retf 4")
def number_to_string(mem, variant):
    """u214b_number_to_string(value; var s: string[20]): Str(value:0, local), then s := local clipped to 20 (09DD-0A05)."""
    low, high, doff, dseg = args(mem, 4)
    R = Regs(mem)
    R.enter(0x16)                                              # 09DA-09DD
    local = (R.bp - 0x15) & M16
    ss = R.ss
    sp0 = R.sp
    R.ax = 0                                                   # 09E6
    for w in (high, low, 0, ss, local, 0x14):                  # 09E0-09F1
        R.push(w)
    R.push(mem.seg(0x214B))                                    # 09F2 call far 12F6
    R.push(0x09F7)
    text, _ = str_of_long(((high << 16) | low), 0, 0x14)
    str_of_long_core(mem, R, 0x14, local, ss, 0, low, high)    # writes the string into the local
    R.sp = sp0
    for w in (ss, local, dseg, doff, 0x14):                    # 09F7-0A04
        R.push(w)
    R.ax = 0x14                                                # 0A01
    R.push(mem.seg(0x214B))                                    # 0A05 call far 0644
    R.push(0x0A0A)
    store_max_bytes(mem, R, text, dseg, doff, 0x14, R.sp)
    R.sp = sp0
    R.leave()
    R.store()


def store_max_bytes(mem, R, data, dseg, doff, maxlen, sp_at_call):
    """23E4:0644 with the source a Pascal string held in Python (a local of the caller): the registers it leaves."""
    length = min(data[0], maxlen & 0xFF)
    R.al = length
    R.dx = mem.DS
    R.bx = sp_at_call & M16
    R.cld()
    mem.w8(dseg * 16 + doff, length, "23E4:065C")
    for k in range(length):
        mem.w8(dseg * 16 + ((doff + 1 + k) & M16), data[1 + k], "23E4:0661")
    R.cx, R.di, R.es = 0, (doff + 1 + length) & M16, dseg


# -- 214B: the set bits (Pascal sets of at most 16 elements in a byte or word) ------------------------------------------
def set_test(mem, R, value, k, variant=None):
    """214B:0C57 from its `push bp` (the caller pushed the arguments and the return address): bit k - 1 of the word value
    (0C5D-0C6A); a shift of 16 or more gives 0."""
    R.enter(2)                                                  # 0C57-0C5A
    dx = (k - (0 if variant == "bit-shift-1" else 1)) & M16     # 0C5D-0C61
    R.dx, R.cx = dx, dx
    R.ax = (value >> shift_count(dx & 0xFF)) & 1               # 0C68-0C6A shr ax, cl; and ax, 1
    R.local8(-1, R.al)                                          # 0C6D
    R.leave()


@PORTS.port("214B:0C57", ret="retf 4")
def set_test_bit(mem, variant):
    """u214b_set_test_bit(value; k): bit k - 1 of value."""
    R = Regs(mem)
    value, k = args(mem, 2)
    set_test(mem, R, value, k, variant)
    R.store()


def _mask_of(k):
    """1 << (k - 1) as `shl ax, cl` makes it in 16 bits (0C7F-0C87)."""
    dx = (k - 1) & M16
    return dx, (1 << shift_count(dx & 0xFF)) & M16


def set_include(mem, R, off, seg, k):
    R.enter()                                                   # 0C79
    dx, mask = _mask_of(k)
    ax = mem.u8(seg * 16 + off) | mask                         # 0C8E-0C93 mov al, es:[di]; xor ah, ah; or ax, dx
    R.dx, R.cx, R.es, R.di = mask, dx, seg, off
    mem.w8(seg * 16 + off, ax & 0xFF, "214B:0C98")
    R.ax = ax & M16
    R.leave()


def set_exclude(mem, R, off, seg, k):
    R.enter()                                                   # 0CA1
    dx, mask = _mask_of(k)
    keep = ~mask & M16                                         # 0CB1 not ax
    ax = mem.u8(seg * 16 + off) & keep                         # 0CB8-0CBD
    R.dx, R.cx, R.es, R.di = keep, dx, seg, off
    mem.w8(seg * 16 + off, ax & 0xFF, "214B:0CC2")
    R.ax = ax & M16
    R.leave()


@PORTS.port("214B:0C79", ret="retf 6")
def set_include_bit(mem, variant):
    """u214b_set_include_bit(var set; k): Include."""
    off, seg, k = args(mem, 3)
    R = Regs(mem)
    set_include(mem, R, off, seg, k)
    R.store()


@PORTS.port("214B:0CA1", ret="retf 6")
def set_exclude_bit(mem, variant):
    """u214b_set_exclude_bit(var set; k): Exclude."""
    off, seg, k = args(mem, 3)
    R = Regs(mem)
    set_exclude(mem, R, off, seg, k)
    R.store()


@PORTS.port("214B:0CCB", ret="retf 8")
def set_assign_bit(mem, variant):
    """u214b_set_assign_bit(var set; k; include): Include when the byte [bp+6] is not 0, else Exclude (0CCE-0CEB)."""
    flag, off, seg, k = args(mem, 4)
    R = Regs(mem)
    R.enter()                                                   # 0CCB
    if flag & 0xFF:
        invoke(mem, R, 0x214B, 0x0CE0, set_include, off, seg, k, pushes=(k, seg, off))        # 0CD4-0CDD
    else:
        invoke(mem, R, 0x214B, 0x0CEE, set_exclude, off, seg, k, pushes=(k, seg, off))        # 0CE2-0CEB
    R.leave()
    R.store()


@PORTS.port("214B:0CF4", ret="retf 6")
def set_toggle_bit(mem, variant):
    """u214b_set_toggle_bit(var set; k): xor the element's bit (0CF7-0D13)."""
    off, seg, k = args(mem, 3)
    R = Regs(mem)
    R.enter()
    dx, mask = _mask_of(k)
    ax = mem.u8(seg * 16 + off) ^ mask                         # 0D09-0D0E
    R.dx, R.cx, R.es, R.di = mask, dx, seg, off
    mem.w8(seg * 16 + off, ax & 0xFF, "214B:0D13")
    R.ax = ax & M16
    R.leave()
    R.store()


# -- 214B: long min and max ---------------------------------------------------------------------------------------
@PORTS.port("214B:0D1C", ret="retf 8", long=True)
def min_longint(mem, variant):
    """u214b_min_longint(a, b): the signed 32-bit minimum, a when equal... (0D22-0D4E): the high words compare signed, equal
    high words compare the low words unsigned; a wins when its high word is below, or equal with a low word not above."""
    b_lo, b_hi, a_lo, a_hi = args(mem, 4)
    R = Regs(mem)
    R.enter(4)                                                 # 0D1C-0D1F
    ha, hb = (a_hi, b_hi) if variant == "min-unsigned-high" else (s16(a_hi), s16(b_hi))
    if ha > hb:                                                # 0D27 jg -> b (0D33)
        pick_a = False
    elif ha < hb:                                              # 0D2C jl -> a (0D40)
        pick_a = True
    else:
        pick_a = a_lo <= b_lo                                  # 0D2E-0D31 jbe -> a
    lo, hi = (a_lo, a_hi) if pick_a else (b_lo, b_hi)
    R.local16(-4, lo)                                          # 0D38 / 0D45
    R.local16(-2, hi)                                          # 0D3B / 0D48
    R.ax, R.dx, R.es = lo, hi, hi                              # 0D4B-0D4E les ax, [bp-4]; mov dx, es
    R.leave()
    R.store()


@PORTS.port("214B:0D56", ret="retf 8", long=True)
def max_longint(mem, variant):
    """u214b_max_longint(a, b): a wins when its high word is above (signed), or equal with its low word above (unsigned);
    a tie returns b (0D5C-0D88; T48's value model, runtime/model/longs.py)."""
    b_lo, b_hi, a_lo, a_hi = args(mem, 4)
    R = Regs(mem)
    R.enter(4)                                                 # 0D56-0D59
    ha, hb = (a_hi, b_hi) if variant == "max-unsigned-high" else (s16(a_hi), s16(b_hi))
    if ha > hb:                                                # 0D64 jg -> a
        pick_a = True
    elif ha < hb:                                              # 0D66 jl -> b
        pick_a = False
    else:
        pick_a = a_lo > b_lo                                   # 0D68-0D6B jbe -> b
    lo, hi = (a_lo, a_hi) if pick_a else (b_lo, b_hi)
    R.local16(-4, lo)                                          # 0D72 / 0D7F
    R.local16(-2, hi)                                          # 0D75 / 0D82
    R.ax, R.dx, R.es = lo, hi, hi                              # 0D85-0D88
    R.leave()
    flags = sub_flags(a_lo, b_lo, 16) if s16(a_hi) == s16(b_hi) else sub_flags(a_hi, b_hi, 16)    # the last cmp
    R.arith(flags)
    R.store()


# -- 214B: the wrap-add and the clamps ----------------------------------------------------------------------------
def wrap_add(mem, v, lo, hi, delta, variant=None):
    """214B:1C86's arithmetic (1C89-1D66) on the word v: returns (the word to store, AX, DX, the write's instruction, the
    two words a wrapping branch pushes). delta > 0: v + delta past `hi` (unsigned compare of hi with the 32-bit sum) wraps
    to v + delta - hi + lo - 1; delta <= 0: v + delta below `lo` wraps to v + delta + hi - lo + 1. Else v + delta."""
    d32 = s16(delta) & 0xFFFFFFFF                              # 1C8F cdq / 1CFD cdq
    total = (v + d32) & 0xFFFFFFFF                             # add ax, cx; adc dx, bx
    t_lo, t_hi = total & M16, total >> 16
    if s16(delta) > 0:                                         # 1C89 cmp [bp+6], 0; jle 1CFD
        if s16(0) > s16(t_hi):                                 # 1CAE jg -> no wrap
            wrap = False
        elif s16(0) < s16(t_hi):                               # 1CB0 jl -> wrap
            wrap = True
        elif variant == "wrap-high-inclusive":
            wrap = hi <= t_lo
        else:
            wrap = hi < t_lo                                   # 1CB2-1CB4 cmp ax, cx; jb 1CC1
        if not wrap:                                           # 1CB6-1CBC add [di], delta
            return (v + delta) & M16, delta & M16, 0, "214B:1CBC", ()
        result = (v + d32 - hi + lo - 1) & 0xFFFFFFFF          # 1CC1-1CF2
        return result & M16, result & M16, result >> 16, "214B:1CF8", (0, hi)       # 1CC6 push dx; 1CC7 push ax
    if s16(0) < s16(t_hi):                                     # 1D1A cmp dx, bx; jl 1D24 -> no wrap
        wrap = False
    elif s16(0) > s16(t_hi):                                   # 1D1E jg 1D2F -> wrap
        wrap = True
    else:
        wrap = lo > t_lo                                       # 1D20-1D22 cmp ax, cx; ja 1D2F
    if not wrap:                                               # 1D24-1D2A
        return (v + delta) & M16, delta & M16, 0, "214B:1D2A", ()
    result = (v + d32 + hi - lo + 1) & 0xFFFFFFFF              # 1D2F-1D60
    return result & M16, result & M16, result >> 16, "214B:1D66", (0, lo)       # 1D34 push dx; 1D35 push ax


def wrap_add_core(mem, R, off, seg, lo, hi, delta, variant=None):
    """214B:1C86 from its `push bp` (the caller pushed the arguments and the return address)."""
    R.enter()                                                   # 1C86
    R.flush()
    v = mem.u16(seg * 16 + off)
    new, ax, dx, at, pushes = wrap_add(mem, v, lo, hi, delta, variant)
    sp0 = R.sp
    for w in pushes:
        R.push(w)
    R.sp = sp0
    R.es, R.di = seg, off
    mem.w16(seg * 16 + off, new, at)
    R.ax, R.dx = ax, dx
    R.leave()


@PORTS.port("214B:1C86", ret="retf 0xa", long=True)
def wrap_add_in_range(mem, variant):
    """u214b_wrap_add_in_range(var v: word; lo, hi, delta): v := v + delta, wrapped inside [lo, hi]. The commentary ring's
    counter DS:80EE is written by its 1CBC and 1CF8 (match.py WRITERS)."""
    delta, hi, lo, off, seg = args(mem, 5)
    R = Regs(mem)
    wrap_add_core(mem, R, off, seg, lo, hi, delta, variant)
    R.store()


def wrap_add_byte(mem, R, off, seg, lo, hi, delta, variant=None):
    """214B:1D6F from its `push bp` (the caller pushed the arguments and the return address): the byte through a word local
    and 1C86 (1D75-1DA1)."""
    R.enter(2)                                                  # 1D6F-1D72
    v = mem.u8(seg * 16 + off)
    R.es, R.di = seg, off                                       # 1D75
    R.ax = v                                                    # 1D78-1D7B
    R.local16(-2, v)                                            # 1D7D
    ss = R.ss
    local = (R.bp - 2) & M16
    invoke(mem, R, 0x214B, 0x1D98, wrap_add_core, local, ss, lo & 0xFF, hi & 0xFF, delta, variant,
           pushes=(ss, local, lo & 0xFF, hi & 0xFF, delta))    # 1D80-1D95
    new = mem.u16(mem.ss_lin(local))
    R.ax = (R.ax & 0xFF00) | (new & 0xFF)                       # 1D98 mov al, [bp-2]
    R.es, R.di = seg, off                                       # 1D9B
    mem.w8(seg * 16 + off, new & 0xFF, "214B:1D9E")
    R.leave()


@PORTS.port("214B:1D6F", ret="retf 0xa")
def wrap_add_in_range_byte(mem, variant):
    """u214b_wrap_add_in_range_byte(var v: byte; lo, hi, delta): the byte through a word local and 1C86."""
    delta, hi, lo, off, seg = args(mem, 5)
    R = Regs(mem)
    wrap_add_byte(mem, R, off, seg, lo, hi, delta, variant)
    R.store()


@PORTS.port("214B:2000", ret="retf 8")
def clamp_int(mem, variant):
    """u214b_clamp_int(var v: integer; lo, hi): signed, the lower bound first (2003-202B)."""
    hi, lo, off, seg = args(mem, 4)
    R = Regs(mem)
    R.enter()                                                  # 2000
    R.es, R.di = seg, off
    ax = mem.u16(seg * 16 + off)                               # 2006
    if s16(ax) < s16(lo):                                      # 2009 cmp ax, [bp+8]; jge 2017
        ax = lo
        mem.w16(seg * 16 + off, ax, "214B:2014")
    ax = mem.u16(seg * 16 + off)                               # 201A
    if s16(ax) > s16(hi):                                      # 201D-201F cmp ax, [bp+6]; jle 202B
        ax = lo if variant == "clamp-high-uses-lo" else hi
        mem.w16(seg * 16 + off, ax, "214B:2028")
    R.ax = ax
    R.leave()
    R.store()


@PORTS.port("214B:2031", ret="retf 8")
def clamp_byte(mem, variant):
    """u214b_clamp_byte(var v: byte; lo, hi): the signed byte compare (2034-205C)."""
    hi, lo, off, seg = args(mem, 4)
    R = Regs(mem)
    R.enter()                                                  # 2031
    R.es, R.di = seg, off
    al = mem.u8(seg * 16 + off)                                # 2037
    s8_ = lambda b: b - 0x100 if b & 0x80 else b
    if s8_(al) < s8_(lo & 0xFF):                               # 203A cmp al, [bp+8]; jge 2048
        al = lo & 0xFF
        mem.w8(seg * 16 + off, al, "214B:2045")
    al = mem.u8(seg * 16 + off)                                # 204B
    if s8_(al) > s8_(hi & 0xFF):                               # 204E cmp al, [bp+6]; jle 205C
        al = hi & 0xFF
        mem.w8(seg * 16 + off, al, "214B:2059")
    R.al = al
    R.leave()
    R.store()


# -- 23E4: Move, the long multiply and divide ---------------------------------------------------------------------
@PORTS.port("23E4:025D", ret="retf 0xa")
def sys_move(mem, variant):
    """Move(src, dest, count): `rep movsb` forward (025D-0272); DX holds the DS value, BX the SP at the entry."""
    n, doff, dseg, soff, sseg = args(mem, 5)
    sp = entry_sp(mem)
    R = Regs(mem)
    R.bx, R.dx = sp, mem.DS
    R.cld()
    R.si, R.di = _copy_forward(mem, sseg, soff, dseg, doff, n, "23E4:026E")
    R.cx, R.es = 0, dseg
    R.store()


@PORTS.port("23E4:0279", ret="retf")
def sys_long_mul(mem, variant):
    """DX:AX times BX:CX (CX the low word), low 32 bits (0279-0293; runtime/model/longs.py mul_0279, T48): the registers
    are the listing's, SI and DI copies of AX and DX, BX and CX the cross terms."""
    R = Regs(mem)
    ax, dx, bx, cx = R.ax, R.dx, R.bx, R.cx
    si, di = ax, dx                                            # 0279, 027B
    low = ax * cx                                              # 027D mul cx
    R.push(low & M16)                                          # 027F push ax
    R.push(low >> 16)                                          # 0280 push dx
    R.sp = R.sp + 4                                            # 028D pop dx; 028E pop ax
    bx_out = (si * bx) & M16                                   # 0281-0285
    cx_out = (di * cx) & M16                                   # 0287-028B
    partial = ((low >> 16) + bx_out) & M16                     # 028F add dx, bx
    dx_out = (partial + cx_out) & M16                          # 0291 add dx, cx
    R.ax, R.dx, R.bx, R.cx, R.si, R.di = low & M16, dx_out, bx_out, cx_out, si, di
    R.arith(add_flags(partial, cx_out))
    R.store()


@PORTS.port("23E4:0294", ret="retf", long=True)
def sys_long_div(mem, variant):
    """DX:AX divided by BX:CX, signed, truncating towards zero: quotient in DX:AX, remainder (the dividend's sign) in
    BX:CX, SI:DI the divisor's magnitude (0294-02FA); the shift-subtract loop of 33 steps, bit by bit as the listing does.
    A zero divisor ends the program with runtime error 200 (02FB-02FF): a port cannot, and refuses."""
    R = Regs(mem)
    ax, dx, bx, cx = R.ax, R.dx, R.bx, R.cx
    eflags = mem.reg("eflags")
    R.push(R.bp)                                               # 0294 push bp (a scratch from 0295 on)
    if (cx | bx) == 0:                                         # 0295-0299
        raise PortError("23E4:0294: division by zero, where the original ends with runtime error 200 (02FB-02FF)")
    R.push(or_flags(bx, eflags))                               # 029D pushf (after or bx, bx)
    divisor_negative = bool(bx & 0x8000)                       # 029B-029E
    if divisor_negative:
        cx, bx = (~cx) & M16, (~bx) & M16                      # 02A0-02A7
        cx += 1
        bx = (bx + (cx >> 16)) & M16
        cx &= M16
    R.push(or_flags(dx, eflags))                               # 02AC pushf (after or dx, dx)
    dividend_negative = bool(dx & 0x8000)                      # 02AA-02AD
    if dividend_negative:
        ax, dx = (~ax) & M16, (~dx) & M16                      # 02AF-02B6
        ax += 1
        dx = (dx + (ax >> 16)) & M16
        ax &= M16
    si, di = cx, bx                                            # 02B9, 02BB
    cx = bx = 0                                                # 02BD, 02BF: xor clears CF
    carry = 0
    for _ in range(0x21):                                      # 02C1 mov bp, 0x21 ... 02D8
        carry, cx = cx >> 15, ((cx << 1) | carry) & M16        # 02C4 rcl cx, 1
        carry, bx = bx >> 15, ((bx << 1) | carry) & M16        # 02C6 rcl bx, 1
        t = cx - si                                            # 02C8 sub cx, si
        borrow = 1 if t < 0 else 0
        cx = t & M16
        t = bx - di - borrow                                   # 02CA sbb bx, di
        carry = 1 if t < 0 else 0
        bx = t & M16
        if carry:                                              # 02CC jae 02D2 not taken: restore
            t = cx + si                                        # 02CE add cx, si
            cx, c = t & M16, t >> 16
            t = bx + di + c                                    # 02D0 adc bx, di
            carry, bx = t >> 16, t & M16
        carry ^= 1                                             # 02D2 cmc
        carry, ax = ax >> 15, ((ax << 1) | carry) & M16        # 02D3 rcl ax, 1
        carry, dx = dx >> 15, ((dx << 1) | carry) & M16        # 02D5 rcl dx, 1
    if dividend_negative:                                      # 02DA popf; 02DB jns 02EC
        cx, bx = (~cx) & M16, (~bx) & M16                      # 02DD-02E4
        cx += 1
        bx = (bx + (cx >> 16)) & M16
        cx &= M16
    if dividend_negative != divisor_negative:                  # 02E8-02F6
        ax, dx = (~ax) & M16, (~dx) & M16
        ax += 1
        dx = (dx + (ax >> 16)) & M16
        ax &= M16
    R.sp = R.sp + 6                                            # the pops: 02DA popf, 02E7 / 02EC popf, 02F9 pop bp
    R.ax, R.dx, R.bx, R.cx, R.si, R.di = ax, dx, bx, cx, si, di
    R.store()


# -- 23E4: Pascal strings ---------------------------------------------------------------------------------------
@PORTS.port("23E4:062A", ret="retf 4")
def sys_str_store(mem, variant):
    """String assignment, no length limit (062A-0641): the length byte and that many characters."""
    soff, sseg, doff, dseg = args(mem, 4)
    sp = entry_sp(mem)
    R = Regs(mem)
    R.bx, R.dx = sp, mem.DS
    R.cld()
    length = mem.u8(sseg * 16 + soff)                          # 0637 lodsb
    R.al = length
    mem.w8(dseg * 16 + doff, length, "23E4:0638")              # 0638 stosb
    R.si, R.di = _copy_forward(mem, sseg, soff + 1, dseg, doff + 1, length, "23E4:063D")
    R.cx, R.es = 0, dseg
    R.store()


@PORTS.port("23E4:0644", ret="retf 0xa")
def sys_str_store_max(mem, variant):
    """String assignment to a string[max] (0644-0665): the length clipped to the low byte of max."""
    mx, doff, dseg, soff, sseg = args(mem, 5)
    sp = entry_sp(mem)
    R = Regs(mem)
    R.bx, R.dx = sp, mem.DS
    R.cld()
    length = mem.u8(sseg * 16 + soff)                          # 0655 lodsb
    if length > (mx & 0xFF):                                   # 0656 cmp al, cl; 0658 jbe 065C
        length = mx & 0xFF
    R.al = length
    mem.w8(dseg * 16 + doff, length, "23E4:065C")              # 065C stosb
    R.si, R.di = _copy_forward(mem, sseg, soff + 1, dseg, doff + 1, length, "23E4:0661")
    R.cx, R.es = 0, dseg
    R.store()


def str_copy(mem, R, sseg, soff, dseg, doff, index, count, at_len="23E4:06AD", at_move="23E4:06B0"):
    """23E4:0676 Copy(s, index, count) into the string at DSEG:DOFF (0676-06B4)."""
    R.cld()
    ax = mem.u8(sseg * 16 + soff)                              # 0683-0685
    cx = index                                                 # 0687
    if s16(cx) <= 0:                                           # 068B-068F
        cx = 1
    si = (soff + cx) & M16                                     # 0692
    if ax < cx:                                                # 0694-0696 sub ax, cx; jb 06AB
        ax = 0                                                 # 06AB
    else:
        ax = (ax - cx + 1) & M16                               # 0698
        cx = count                                             # 0699
        if s16(cx) < 0:                                        # 069D-06A1
            cx = 0
        if ax > cx:                                            # 06A3-06A5 cmp ax, cx; jbe 06AD
            ax = cx                                            # 06A7
    R.ax = ax
    mem.w8(dseg * 16 + doff, ax & 0xFF, at_len)                # 06AD stosb
    R.si, R.di = _copy_forward(mem, sseg, si, dseg, doff + 1, ax, at_move)    # 06AE-06B0
    R.cx, R.es = 0, dseg


@PORTS.port("23E4:0676", ret="retf 8")
def sys_str_copy(mem, variant):
    """Copy(s, index, count): the index raised to 1, the count limited to what remains (0676-06B4)."""
    count, index, soff, sseg, doff, dseg = args(mem, 6)
    sp = entry_sp(mem)
    R = Regs(mem)
    R.bx, R.dx = sp, mem.DS
    str_copy(mem, R, sseg, soff, dseg, doff, index, count)
    R.store()


def str_concat(mem, R, sseg, soff, dseg, doff):
    """23E4:06B7: append the string at SSEG:SOFF to the one at DSEG:DOFF, the length saturating at 255 (06B7-06E0)."""
    R.cld()
    cl = mem.u8(dseg * 16 + doff)                              # 06C4
    al = mem.u8(sseg * 16 + soff)                              # 06C9 lodsb
    total = cl + al
    mem.w8(dseg * 16 + doff, total & 0xFF, "23E4:06CA")        # 06CA add byte ptr es:[di], al
    if total > 0xFF:                                           # 06CD jae 06D7 not taken
        mem.w8(dseg * 16 + doff, 0xFF, "23E4:06CF")
        al = (~cl) & 0xFF                                      # 06D3-06D5
    R.al = al
    R.si, R.di = _copy_forward(mem, sseg, soff + 1, dseg, doff + cl + 1, al, "23E4:06DC")
    R.cx, R.es = 0, dseg


@PORTS.port("23E4:06B7", ret="retf 4")
def sys_str_concat(mem, variant):
    """Concatenation: the second string appended to the first, which saturates at 255 characters."""
    soff, sseg, doff, dseg = args(mem, 4)
    sp = entry_sp(mem)
    R = Regs(mem)
    R.bx, R.dx = sp, mem.DS
    str_concat(mem, R, sseg, soff, dseg, doff)
    R.store()


@PORTS.port("23E4:06E3", ret="retf 8")
def sys_str_pos(mem, variant):
    """Pos(sub, s) (06E3-072C): the 1-based index of the first match, 0 when there is none; an empty sub gives 1 for a
    non-empty s and 0 for an empty one; the scan reads s from its second byte on."""
    s_off, s_seg, sub_off, sub_seg = args(mem, 4)
    sp = entry_sp(mem)
    R = Regs(mem)
    R.push(mem.DS)                                      # 06E6 push ds
    R.sp = R.sp + 2                                            # 072B pop ds
    R.bx = sp
    R.cld()
    R.es = s_seg
    cx = mem.u8(s_seg * 16 + s_off)                            # 06EF
    di = s_off
    si = sub_off
    ax = R.ax
    if cx == 0:                                                # 06F4 jcxz 071F
        R.ax = 0
        R.cx, R.si, R.di = 0, si, di
        R.store()
        return
    di = (di + 1) & M16                                        # 06F6
    sublen = mem.u8(sub_seg * 16 + si)                         # 06F7 lodsb
    si = (si + 1) & M16
    ax = (ax & 0xFF00) | sublen
    found = None
    if sublen == 0:                                            # 06F8 cmp al, 1; 06FA jb 0725
        found = di
    elif sublen == 1:                                          # 06FC ja 0706 not taken
        ch = mem.u8(sub_seg * 16 + si)                         # 06FE lodsb
        si = (si + 1) & M16
        ax = (ax & 0xFF00) | ch
        while cx:                                              # 06FF repne scasb
            hit = mem.u8(s_seg * 16 + di) == ch
            di = (di + 1) & M16
            cx -= 1
            if hit:
                found = (di - 1) & M16                         # 0703 dec di
                break
    else:
        ax = sublen                                            # 0706 xor ah, ah
        dx = (cx - ax) & M16                                   # 0708-070A
        if cx < ax:                                            # 070C jb 071F
            R.dx = dx
        else:
            dx = (dx + 1) & M16                                # 070E
            while True:                                        # 070F
                cx = ax
                equal = True
                compared = 0
                while cx:                                      # 0711 repe cmpsb
                    a = mem.u8(sub_seg * 16 + si)
                    b = mem.u8(s_seg * 16 + di)
                    si, di = (si + 1) & M16, (di + 1) & M16
                    cx -= 1
                    compared += 1
                    if a != b:
                        equal = False
                        break
                if equal:                                      # 0713 je 0723
                    found = (di - ax) & M16
                    break
                cx = (cx - ax) & M16                           # 0715
                si = (si + cx) & M16
                di = (di + cx + 1) & M16                       # 0717-071B
                dx = (dx - 1) & M16                            # 071C
                if dx == 0:                                    # 071D jne 070F
                    break
            R.dx = dx
    R.ax = (found - s_off) & M16 if found is not None else 0   # 0725-0728 / 071F
    R.cx, R.si, R.di = cx, si, di
    R.store()


@PORTS.port("23E4:072F", ret="retf 8")
def sys_str_compare(mem, variant):
    """String comparison (072F-0758): the flags of `cmp` of the first against the second over the shorter length, then of
    the lengths. AL and AH are the two lengths."""
    b_off, b_seg, a_off, a_seg = args(mem, 4)
    sp = entry_sp(mem)
    R = Regs(mem)
    R.bx, R.dx = sp, mem.DS
    R.cld()
    la = mem.u8(a_seg * 16 + a_off)                            # 073C lodsb
    lb = mem.u8(b_seg * 16 + b_off)                            # 073D
    R.ax = (lb << 8) | la
    cl = la if la <= lb else lb                                # 0743-0747
    si, di = (a_off + 1) & M16, (b_off + 1) & M16
    R.es = b_seg
    flags = None
    if cl:                                                     # 0749-074B
        cx = cl
        while cx:                                              # 074F repe cmpsb
            a, b = mem.u8(a_seg * 16 + si), mem.u8(b_seg * 16 + di)
            si, di = (si + 1) & M16, (di + 1) & M16
            cx -= 1
            flags = sub_flags(a, b, 8)
            if a != b:
                break
        R.cx = cx
        if flags is not None and not flags & ZF:               # 0751 jne 0755
            R.si, R.di = si, di
            R.arith(flags)
            R.store()
            return
        R.si, R.di = si, di
    else:
        R.cx = 0
    R.arith(sub_flags(la, lb, 8))                              # 0753 cmp al, ah
    R.store()


@PORTS.port("23E4:075A", ret="retf 2")
def sys_char_to_str(mem, variant):
    """Char to string (075A-0769): length 1, then the character."""
    ch, doff, dseg = args(mem, 3)
    sp = entry_sp(mem)
    R = Regs(mem)
    R.bx = sp
    R.cld()
    mem.w8(dseg * 16 + doff, 1, "23E4:0763")
    mem.w8(dseg * 16 + ((doff + 1) & M16), ch & 0xFF, "23E4:0769")
    R.al = ch & 0xFF
    R.es, R.di = dseg, (doff + 2) & M16
    R.store()


def _pstr(mem, seg, off):
    """The Pascal string at seg:off as Python bytes (the length byte, then the characters)."""
    n = mem.u8(seg * 16 + off)
    return bytes([n]) + (mem.read(seg * 16 + ((off + 1) & M16), n) if n else b"")


def _py_copy(s, index, count):
    """0676 on a Python string: Copy(s, index, count) as a Pascal string (the index raised to 1 when it is not above 0,
    the count to 0 when negative, both signed; no characters when the index is past the length)."""
    ax = s[0]
    cx = index & M16
    if s16(cx) <= 0:
        cx = 1
    if ax < cx:
        return b"\x00"
    ax = ax - cx + 1
    count &= M16
    count = 0 if s16(count) < 0 else count
    if ax > count:
        ax = count
    return bytes([ax]) + s[cx:cx + ax]


def _py_concat(a, b):
    """06B7 on Python strings: b appended to a, the length saturating at 255."""
    total = a[0] + b[0]
    if total > 0xFF:
        return bytes([0xFF]) + a[1:] + b[1:1 + 0xFF - a[0]]
    return bytes([total]) + a[1:] + b[1:]


def _insert_delete_frame(mem, R, temp1, temp2, words):
    """The bytes the frame of 0787 / 07DB leaves: the two 256-byte temporaries as they end (the first, the result of
    the concatenations, the second, a Copy) and the words the calls pushed, the last write to each address (the
    sequences are in the listing: 07A3-07D2, 07FD-0828), as offsets from the stack pointer after `sub sp, 0x200`."""
    ss = R.ss
    R.flush()
    sp = R.sp
    if temp2 is not None:
        _write_pstring(mem, ss, (R.bp - 0x200) & M16, temp2, "23E4:06AD", "23E4:06B0")
    _write_pstring(mem, ss, (R.bp - 0x100) & M16, temp1, "23E4:06CA", "23E4:06DC")
    for off, value in words:
        mem.w16(mem.ss_lin((sp + off) & M16), value & M16, STACK_AT)


@PORTS.port("23E4:0787", ret="retf 0xc")
def sys_str_insert(mem, variant):
    """Insert(src, s, index) into a string[max] (0787-07D8): s := Copy(s, 1, index - 1) + src + Copy(s, index, 255),
    clipped to max by 0644. The two 256-byte temporaries are the routine's locals."""
    index, mx, soff, sseg, rsoff, rsseg = args(mem, 6)
    R = Regs(mem)
    R.enter(0x200)                                             # 0787-078D
    ss, cs = R.ss, mem.seg(0x23E4)
    s = _pstr(mem, sseg, soff)
    src = _pstr(mem, rsseg, rsoff)
    first = _py_copy(s, 1, (index - 1) & M16)                  # 07A3 -> 0676 (s, 1, index - 1)
    first = _py_concat(first, src)                             # 07AC -> 06B7
    rest = _py_copy(s, index, 0xFF)                            # 07C2 -> 0676 (s, index, 255)
    first = _py_concat(first, rest)                            # 07C6 -> 06B7
    T1 = (R.bp - 0x100) & M16
    _insert_delete_frame(mem, R, first, rest, ((-2, ss), (-4, T1), (-6, sseg), (-8, soff), (-10, mx), (-12, cs),
                                               (-14, 0x07D5), (-16, 0x00FF), (-18, cs), (-20, 0x07C5)))
    R.ax = 0xFF                                                # 07BD mov ax, 0xff: AH is 0 for the whole chain
    store_max_bytes(mem, R, first, sseg, soff, mx, R.sp - 14)
    R.leave()
    R.store()


@PORTS.port("23E4:07DB", ret="retf 8")
def sys_str_delete(mem, variant):
    """Delete(s, index, count) (07DB-082E): nothing when count <= 0, else s := Copy(s, 1, index - 1) + Copy(s, index +
    count, 255) (the sum in 16 bits)."""
    count, index, soff, sseg = args(mem, 4)
    R = Regs(mem)
    R.enter(0x200)                                             # 07DB-07E1
    if s16(count) <= 0:                                        # 07E2-07E6 jle 082B
        R.leave()
        R.store()
        return
    ss, cs = R.ss, mem.seg(0x23E4)
    s = _pstr(mem, sseg, soff)
    first = _py_copy(s, 1, (index - 1) & M16)                  # 07FD -> 0676
    rest = _py_copy(s, (index + count) & M16, 0xFF)            # 0817 -> 0676 (s, index + count, 255)
    first = _py_concat(first, rest)                            # 081B -> 06B7
    T1 = (R.bp - 0x100) & M16
    _insert_delete_frame(mem, R, first, rest, ((-2, ss), (-4, T1), (-6, sseg), (-8, soff), (-10, 0x00FF), (-12, cs),
                                               (-14, 0x082B), (-16, 0x00FF), (-18, cs), (-20, 0x081A)))
    R.ax = 0xFF                                                # 0812
    store_max_bytes(mem, R, first, sseg, soff, 0xFF, R.sp - 14)
    R.leave()
    R.store()


@PORTS.port("23E4:08BF", ret="retf 0xa")
def sys_set_compact(mem, variant):
    """Copies bl bytes of a set from byte bh on (08BF-08DC)."""
    word, doff, dseg, soff, sseg = args(mem, 5)
    R = Regs(mem)
    R.dx = mem.DS
    R.bx = word
    R.cld()
    R.si, R.di = _copy_forward(mem, sseg, soff + (word >> 8), dseg, doff, word & 0xFF, "23E4:08D8")
    R.cx, R.es = 0, dseg
    R.store()


# -- 23E4: UpCase ------------------------------------------------------------------------------------------------
@PORTS.port("23E4:19B2", ret="retf 2")
def sys_upcase(mem, variant):
    """UpCase(c) (19B2-19C2): a-z minus 0x20."""
    ch = args(mem, 1)[0] & 0xFF
    sp = entry_sp(mem)
    R = Regs(mem)
    R.bx = sp
    if 0x61 <= ch <= 0x7A:
        ch -= 0x20
    R.al = ch
    R.store()
