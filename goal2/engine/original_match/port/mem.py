"""The memory view a port is written against (T58): the original's memory, registers and the kit's sites, through
which every read and write of a port goes.

`Mem` holds what a port uses; a backend gives it six primitives. `MachineMem` is the kit's Unicorn machine (a port
running in place of the original's routine, the original's code around it); `PlainMem` is plain memory with its own
listeners (unit tests now, the engine without Unicorn later: T78). A port never touches the machine directly: a
write that bypasses the view reaches no watch, so the kit would lose an event or a draw without an error.

A write names the original's instruction that makes it (`at`, 'SSSS:OOOO' as the listing writes it): the kit's
watches see it as that instruction's (match.py checks the writer of every event counter, WRITERS)."""


class PortError(RuntimeError):
    """A port asked for something the port mode does not do (the message says what)."""


# The stops a site inside a port may make: they take effect when the port has returned (Machine.fire). match.py's
# tick (970C, `_on_tick`) stops for "events" only to hand out events already queued; a "decision" stops the
# original before a key read returns, which a port, being Python, cannot be suspended in.
DEFERRABLE_STOPS = (None, "events")


def s8(v):
    return v - 0x100 if v & 0x80 else v


def s16(v):
    return v - 0x10000 if v & 0x8000 else v


class Mem:
    """The view. Backends give: read(linear, n) -> bytes; _write(linear, size, value, at_linear); reg(name);
    set_reg(name, value); lin(address 'SSSS:OOOO') -> linear; seg(paragraph) -> runtime segment; DS; and, for the
    kit's sites, _site(address), _key(site), _keypressed(site)."""

    # -- reads ---------------------------------------------------------------------------------------------
    def u8(self, linear):
        return self.read(linear, 1)[0]

    def u16(self, linear):
        return int.from_bytes(self.read(linear, 2), "little")

    def u32(self, linear):
        return int.from_bytes(self.read(linear, 4), "little")

    def ds8(self, off):
        return self.u8(self.DS * 16 + (off & 0xFFFF))

    def ds16(self, off):
        return self.u16(self.DS * 16 + (off & 0xFFFF))

    def farptr(self, linear):
        """The (offset, segment) a far pointer at `linear` holds."""
        return self.u16(linear), self.u16(linear + 2)

    def ds_far(self, off):
        """The linear address the far pointer at DS:off points to."""
        o, s = self.farptr(self.DS * 16 + off)
        return s * 16 + o

    @staticmethod
    def addr(seg, off):
        return seg * 16 + (off & 0xFFFF)

    # -- writes (each as the original's instruction `at` makes it) -----------------------------------------
    def _at(self, at):
        cache = self.__dict__.setdefault("_at_cache", {})
        lin = cache.get(at)
        if lin is None:
            lin = cache[at] = self.lin(at)
        return lin

    def w8(self, linear, value, at):
        self._write(linear, 1, value & 0xFF, self._at(at))

    def w16(self, linear, value, at):
        self._write(linear, 2, value & 0xFFFF, self._at(at))

    def w32(self, linear, value, at):
        self._write(linear, 4, value & 0xFFFFFFFF, self._at(at))

    def wds8(self, off, value, at):
        self.w8(self.DS * 16 + (off & 0xFFFF), value, at)

    def wds16(self, off, value, at):
        self.w16(self.DS * 16 + (off & 0xFFFF), value, at)

    # -- the stack: arguments and frames ---------------------------------------------------------------------
    def ss_lin(self, off):
        return self.reg("ss") * 16 + (off & 0xFFFF)

    def arg(self, i):
        """Argument word i of the routine the port replaces, read at its entry (0: the one pushed last, nearest the
        return address; a nested procedure's parent BP is its arg(0))."""
        if not self._entries:
            raise PortError("arg() outside a port")
        sp, far = self._entries[-1]
        return self.u16(self.ss_lin(sp + (4 if far else 2) + 2 * i))

    def frame(self, bp):
        """The frame at SS:bp (a nested procedure's parent frame: frame(arg(0)))."""
        return Frame(self, bp)

    def enter(self, size, at):
        """The listing's prologue `push bp; mov bp, sp; sub sp, size`, for a port whose site logic reads its frame
        (the kit reads BP at the captain prompt's slot, the menus' items, the prompts' wait): returns its Frame. The
        port's runner puts SP and BP back at the return, as the epilogue `mov sp, bp; pop bp` would."""
        sp = (self.reg("sp") - 2) & 0xFFFF
        self.w16(self.ss_lin(sp), self.reg("bp"), at)
        self.set_reg("sp", sp)
        self.set_reg("bp", sp)
        self.set_reg("sp", (sp - size) & 0xFFFF)
        return Frame(self, sp)

    # -- the kit's sites -------------------------------------------------------------------------------------
    def site(self, address):
        """The original reaches `address` inside the ported routine: the kit's hooks there fire, at the listing's
        point (a stop they make takes effect at the port's return; a decision cannot: PortError)."""
        self._site(address)
        self._check_stop(address)

    def read_key(self, site):
        """The original's 214B:08DD called with the return address `site`: the key the kit's logic gives there (its
        writes of DS:A976 and A977 made as 08DD's), as AL."""
        key = self._key(site)
        self._check_stop(site)
        return key

    def keypressed(self, site):
        """The original's 214B:0723 called with the return address `site`: whether the kit has a key there."""
        return bool(self._keypressed(site))

    def _check_stop(self, where):
        reason = self.stop_reason()
        if reason not in DEFERRABLE_STOPS:
            raise PortError(f"a port reached {where}, where the kit stops the original ({reason}): a port cannot be "
                            "suspended there")

    def stop_reason(self):
        return None


class Frame:
    """Words and bytes at SS:(bp + offset)."""

    def __init__(self, mem, bp):
        self.mem, self.bp = mem, bp

    def lin(self, off):
        return self.mem.ss_lin(self.bp + off)

    def u8(self, off):
        return self.mem.u8(self.lin(off))

    def u16(self, off):
        return self.mem.u16(self.lin(off))

    def far(self, off):
        """The linear address of the far pointer at bp + off."""
        o, s = self.mem.farptr(self.lin(off))
        return s * 16 + o

    def w8(self, off, value, at):
        self.mem.w8(self.lin(off), value, at)

    def w16(self, off, value, at):
        self.mem.w16(self.lin(off), value, at)


class MachineMem(Mem):
    """The view over the kit's Machine (machine.py): writes through Machine.write_as (the kit's watches and the draw
    record see them as the guest's), sites through Machine.fire, key reads through the kit's services."""

    def __init__(self, machine, keys=None):
        self.m = machine
        self.keys = keys            # an object with key(site) and keypressed(site) (Match), or None
        self.DS = machine.DS
        self._entries = []          # (SP at the entry, far) of the ports running, innermost last

    def read(self, linear, n):
        return bytes(self.m._uc.mem_read(linear, n))     # the port's own read: the engine, not Machine.uc (T59)

    def _write(self, linear, size, value, at_linear):
        self.m.write_as(linear, size, value, at_linear)

    def reg(self, name):
        return self.m.reg(name)

    def set_reg(self, name, value):
        self.m.set_reg(name, value)

    def lin(self, address):
        return self.m.lin(address)

    def seg(self, paragraph):
        return self.m.seg(paragraph)

    def stop_reason(self):
        return self.m.stop_reason

    def _site(self, address):
        self.m.fire(address)

    def _key(self, site):
        if self.keys is None:
            raise PortError(f"a key read at {site} with no kit to answer it")
        return self.keys.key(site)

    def _keypressed(self, site):
        if self.keys is None:
            raise PortError(f"a key poll at {site} with no kit to answer it")
        return self.keys.keypressed(site)


class PlainMem(Mem):
    """Plain memory (a bytearray of guest memory) with the load segment, registers in a dict, write listeners
    (begin, end, fn(address, size, value, at_linear)) and site handlers {linear: [fn()]}. For unit tests on synthetic
    memory now, and the engine without Unicorn later (T78)."""

    def __init__(self, memory, load=0, ds_paragraph=0x2581, regs=None):
        self.memory = memory
        self.load = load
        self.DS = (load + ds_paragraph) & 0xFFFF
        self.regs = dict(regs or {})
        self.listeners = []
        self.sites = {}
        self._entries = []

    def read(self, linear, n):
        return bytes(self.memory[linear:linear + n])

    def _write(self, linear, size, value, at_linear):
        for begin, end, fn in list(self.listeners):
            if begin <= linear <= end:
                fn(linear, size, value, at_linear)
        self.memory[linear:linear + size] = value.to_bytes(size, "little")

    def reg(self, name):
        return self.regs.get(name.lower(), 0)

    def set_reg(self, name, value):
        self.regs[name.lower()] = value & 0xFFFF

    def seg(self, paragraph):
        return (self.load + paragraph) & 0xFFFF

    def lin(self, address):
        s, o = address.split(":")
        return self.seg(int(s, 16)) * 16 + int(o, 16)

    def _site(self, address):
        for fn in self.sites.get(self.lin(address), ()):
            fn()

    def _key(self, site):
        raise PortError(f"a key read at {site}: plain memory has no kit to answer it")

    def _keypressed(self, site):
        raise PortError(f"a key poll at {site}: plain memory has no kit to answer it")
