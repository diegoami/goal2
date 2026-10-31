"""The guest machine: Unicorn running the original's code on a memory image (no original bytes here).

A 16-bit real-mode x86 with 1 MiB + the HMA mapped, holding the memory of a DOSBox-X savestate of goal (version 2).
Addresses are written as the listing writes them ('SSSS:OOOO', a paragraph of the load module and an offset) and
relocated by the load segment. Interrupts are swallowed: the BIOS and DOS calls the match makes are display,
speaker and keyboard, and the keyboard is answered by the kit's own hooks (match.py).

Stopping: a hook calls `stop(reason)`; Unicorn then leaves the instruction at the hooked address unexecuted, and
every hook at that address fires again when the run resumes there (probed: E033 notes, section 3). Handlers are
told so (`replay=True` on that first call after a resume) and those that count things skip it."""
try:                     # the kit imports without unicorn (a checkout that lacks it; the CI code tier installs it, #304); a match needs it
    from unicorn import Uc, UcError, UC_ARCH_X86, UC_MODE_16, UC_HOOK_CODE, UC_HOOK_INTR, UC_HOOK_MEM_WRITE
    from unicorn import x86_const as X
except ImportError:
    Uc = None

    class UcError(Exception):
        pass

MEM_SIZE = 0x110000          # 1 MiB and the high memory area
DS_PARAGRAPH = 0x2581        # GOAL.EXE's data segment, a paragraph of the load module (static/goal-exe/README.md)
REGS = ("EAX", "EBX", "ECX", "EDX", "ESI", "EDI", "EBP", "ESP", "EFLAGS", "EIP", "CS", "DS", "ES", "SS", "FS", "GS")


def NOOP(replay):
    """The placeholder handler at a port's entry or a guest call's return address where the kit has none."""


class GuestError(RuntimeError):
    """The original did something the kit does not declare (an unknown key read, a stray routine)."""


# Machine.uc under a proof (round 6, deny by default): the only engine attributes forwarded, constants and queries of
# the engine's configuration that neither call back into the host nor observe the guest. Everything else, every new
# Unicorn API included, is refused (PortError); tests.test_port_guest inventories dir() of the engine against this.
UC_WHITELIST = frozenset(("REG_RANGE_FP", "REG_RANGE_MMR", "REG_RANGE_MSR", "REG_RANGE_XMM", "REG_RANGE_YMM",
                          "REG_RANGE_ZMM", "ctl_get_arch", "ctl_get_mode", "ctl_get_page_size", "ctl_get_cpu_model"))
# Outside a proof everything is forwarded, and every use is counted (Machine.foreign_hooks): a proof refuses to start
# on a machine whose Machine.uc was used at all (not only the uses that install a host callback or share guest memory,
# UC_FOREIGN: a raw hook, an MMIO range, a host buffer mapped as guest memory, a remap; also a bound method taken
# before the proof, e.g. a raw reg_read kept by an observer, which no check at call time would see). Unproved runs keep
# them (family.py --count).
UC_FOREIGN = frozenset(("hook_add", "hook_del", "mmio_map", "mem_map_ptr", "mem_map", "mem_unmap", "mem_protect"))


class _HookGuard:
    """Machine.uc: the Unicorn engine as the kit's users see it. Under a proof (installed, or being constructed) only
    UC_WHITELIST is forwarded and any other attribute raises PortError naming it; outside one everything is
    forwarded and every use is counted (Machine.foreign_hooks: a proof refuses such a machine). The kit reaches the guest through Machine's
    methods (the taps a proof records); the machine, the proof and the port's view use the engine itself
    (Machine._uc), never this. Nothing is cached, so the check is made at every access."""

    def __init__(self, uc, machine):
        object.__setattr__(self, "_engine", uc)
        object.__setattr__(self, "_machine", machine)

    def __getattr__(self, name):
        m = self._machine
        if m.proving:
            if name not in UC_WHITELIST:
                from .port.mem import PortError
                raise PortError(f"Machine.uc.{name} while a proof is installed: refused (deny by default; the kit "
                                "reads and writes the guest through Machine's methods, which the proof records)")
        else:
            m.foreign_hooks += 1
        return getattr(self._engine, name)

    def __setattr__(self, name, value):
        from .port.mem import PortError
        raise PortError(f"Machine.uc.{name} cannot be set")


class Machine:
    def __init__(self, memory, load):
        if Uc is None:
            raise ModuleNotFoundError("original_match needs the unicorn package to run a match: pip install unicorn")
        if len(memory) < MEM_SIZE:
            raise ValueError(f"the image holds {len(memory)} bytes of guest memory, {MEM_SIZE} are needed")
        self._uc = Uc(UC_ARCH_X86, UC_MODE_16)
        self.proving = False       # a proof is installed (port/prove.py): no raw hook, no second recorder
        self.foreign_hooks = 0     # uses of `uc` by users of the kit outside a proof (a proof refuses to start then)
        self._recorder = None      # the proof's write recorder: the one listener that runs in the muted original too
        self.uc = _HookGuard(self._uc, self)
        self._uc.mem_map(0, MEM_SIZE)
        self._uc.mem_write(0, bytes(memory[:MEM_SIZE]))
        self.load = load
        self.DS = load + DS_PARAGRAPH
        self.stop_reason = None
        self.error = None
        self._handlers = {}        # linear address -> [handler]
        self._resume_lin = None
        # The port mode (port/; inert without ports): the write listeners a port's write reaches as a guest write
        # would, the port at a routine's entry, the instruction a port's write or site stands for (pc()), and the
        # address a port returned to before a stop made inside it (not a replay when the run resumes there).
        self._writes = []          # (begin, end, fn(address, size, value), the proof's recorder)
        self._ports = {}           # linear address -> runner(machine)
        self._pc_override = None
        self.no_replay_at = None
        # Guest calls (T59, port/guest.py): the port frames waiting on a call of the original's code, innermost last;
        # each resumes when the guest reaches its return address with the stack as the call left it.
        self.frames = []
        # The proof mode (T59, port/prove.py): while `muted`, the original runs as plain guest code: no handler, port
        # or write listener of the kit runs (only the proof's recorder, set_recorder); every hooked address goes to
        # muted_hook(linear) instead.
        self.muted = False
        self.muted_hook = None
        # ... and while a proved call's port runs, the kit's sites it reaches (site_enter, site_leave around the
        # handlers) and the kit's own writes (write_tap(linear, data), before they land) are told to the proof.
        self.site_tap = None
        self.write_tap = None
        # ... and the reads and register changes of the kit (io_tap(kind, a, b): "r" linear, bytes; "g" register, value
        # read; "s" register, value set; "p" None, pc() returned), so a proof can check a site's inputs and replay its
        # answer (port/prove.py). `running`: inside emu_start (the guest or a hook), not between two runs of the match.
        # listen_tap: told around each call of a kit write listener (not the recorder): listen_enter(index in _writes,
        # address, size, value) returns a token, listen_leave(token) after it (round 3: a listener's inputs are proved).
        self.io_tap = None
        self.listen_tap = None
        self.running = False
        self._uc.hook_add(UC_HOOK_INTR, lambda uc, intno, data: None)

    # -- addresses ---------------------------------------------------------------------------------
    def seg(self, paragraph):
        return (self.load + paragraph) & 0xFFFF

    def lin(self, address):
        seg, off = address.split(":")
        return self.seg(int(seg, 16)) * 16 + int(off, 16)

    def where(self, seg, off):
        """A runtime segment:offset as the listing writes it."""
        return "%04X:%04X" % ((seg - self.load) & 0xFFFF, off)

    # -- memory --------------------------------------------------------------------------------------
    def read(self, linear, n):
        """The kit's read of guest memory (every read of the kit's goes through here; a proof records it: io_tap)."""
        data = bytes(self._uc.mem_read(linear, n))
        if self.io_tap is not None:
            self.io_tap("r", linear, data)
        return data

    def write(self, linear, data):
        """The kit's write of guest memory (a proof records it: write_tap)."""
        if self.write_tap is not None:
            self.write_tap(linear, bytes(data))
        self._uc.mem_write(linear, bytes(data))

    def word_at(self, linear):
        return int.from_bytes(self.read(linear, 2), "little")

    def rd(self, off, n=2):
        """The little-endian value of n bytes at DS:off."""
        return int.from_bytes(self.read(self.DS * 16 + off, n), "little")

    def wr(self, off, value, n=2):
        self.write(self.DS * 16 + off, int(value).to_bytes(n, "little"))

    def far(self, off):
        """The linear address a far pointer at DS:off holds."""
        return self.rd(off + 2) * 16 + self.rd(off)

    def rd_far(self, ptr, off, n=2):
        """The value of n bytes at offset `off` of the record the far pointer DS:ptr points to."""
        return int.from_bytes(self.read(self.far(ptr) + off, n), "little")

    # -- registers and the stack ---------------------------------------------------------------------
    def reg(self, name):
        value = self._uc.reg_read(getattr(X, f"UC_X86_REG_{name.upper()}"))
        if self.io_tap is not None:
            self.io_tap("g", name.lower(), value)
        return value

    def set_reg(self, name, value):
        self._uc.reg_write(getattr(X, f"UC_X86_REG_{name.upper()}"), value)
        if self.io_tap is not None:
            self.io_tap("s", name.lower(), value)

    def stack_word(self, offset):
        return self.word_at(self.reg("ss") * 16 + ((self.reg("sp") + offset) & 0xFFFF))

    def frame_word(self, bp, offset):
        return self.word_at(self.reg("ss") * 16 + ((bp + offset) & 0xFFFF))

    def return_from(self, far, pop=0):
        """Return to the caller as `retf pop` / `ret pop` would, from a routine's first instruction."""
        sp = self.reg("sp")
        ip = self.stack_word(0)
        if far:
            cs = self.stack_word(2)
            self.set_reg("sp", (sp + 4 + pop) & 0xFFFF)
            self.set_reg("cs", cs)
        else:
            self.set_reg("sp", (sp + 2 + pop) & 0xFFFF)
        self.set_reg("eip", ip)

    def far_call(self, target, args, return_to, ss, sp):
        """Set up the registers and stack of a far call of `target` ('SSSS:OOOO') with the argument words `args`
        (pushed in order, so the last is nearest the return address) returning to `return_to`, so that SP is `sp`
        at the routine's first instruction. Returns the linear address of the return."""
        rseg, roff = return_to.split(":")
        words = [int(roff, 16), self.seg(int(rseg, 16))] + list(reversed(args))
        for i, w in enumerate(words):
            self.write(ss * 16 + ((sp + 2 * i) & 0xFFFF), (w & 0xFFFF).to_bytes(2, "little"))
        tseg, toff = target.split(":")
        for name, value in (("ss", ss), ("sp", sp), ("ds", self.DS), ("es", self.DS),
                            ("cs", self.seg(int(tseg, 16))), ("eip", int(toff, 16))):
            self.set_reg(name, value)
        return self.lin(return_to)

    # -- hooks and running -------------------------------------------------------------------------------
    def at(self, address, handler):
        """Call handler(replay) when the guest reaches `address` ('SSSS:OOOO'), before its instruction runs."""
        self.at_linear(self.lin(address), handler)

    def at_linear(self, lin, handler):
        """`at` by linear address. Safe while the guest runs (a guest call's return address, T59): Unicorn applies a
        code hook added mid-run only to code it has not translated yet (probed, Unicorn 2.1.4: notes/T59.md), so the
        address's translation is dropped and the hook reaches it next time."""
        if lin not in self._handlers:
            self._handlers[lin] = []

            def dispatch(uc, addr, size, data, lin=lin):
                replay = lin == self._resume_lin
                self._resume_lin = None
                try:
                    if self.muted:              # a proof's original runs (port/prove.py): it decides what this is
                        self.muted_hook(lin)
                        if self.muted or self.pc() != lin:
                            return              # still the original, or the port it gave way to went elsewhere
                    handlers = list(self._handlers[lin])
                    tap = self.site_tap if any(h is not NOOP for h in handlers) else None
                    if tap is not None:
                        tap.site_enter(lin, replay)
                    stopped = False
                    for h in handlers:
                        h(replay)
                        if self.stop_reason is not None or self.error is not None:
                            stopped = True
                            break
                    if tap is not None:
                        tap.site_leave(lin, stopped)
                    if stopped:
                        return
                    # a port runs after the kit's handlers, only when none stopped: it never ran before a replay,
                    # and once it ran CS:IP is its caller's, so it never runs twice; so does a port frame's return
                    runner = self._ports.get(lin)
                    frame = self.frames[-1] if self.frames else None
                    if runner is not None:
                        runner(self)
                    elif frame is not None and frame.ret_lin == lin and frame.returned(self):
                        self.frames.pop()
                        frame.resume(self)
                    else:
                        return
                    if self.stop_reason is not None:   # a site inside the port stopped: the run resumes where
                        self.no_replay_at = self.pc()  # the port went (its return, a call), where no hook fired yet
                except Exception as e:          # stop the emulation; run() re-raises it
                    self.error = e
                    uc.emu_stop()
            self._uc.hook_add(UC_HOOK_CODE, dispatch, begin=lin, end=lin)
            self._uc.ctl_remove_cache(lin, lin + 1)
        self._handlers[lin].append(handler)

    def hooked(self, lin):
        """Whether a handler of the kit (not only a port's or a guest call's placeholder) is at `lin`."""
        return any(h is not NOOP for h in self._handlers.get(lin, ()))

    def port(self, address, runner):
        """Run runner(machine) in place of the routine at `address` (the port mode, port/): it runs from the entry,
        after every handler `at` the entry, and returns to the caller itself."""
        lin = self.lin(address)
        if lin in self._ports:
            raise ValueError(f"two ports of {address}")
        self._ports[lin] = runner
        if lin not in self._handlers:
            self.at_linear(lin, NOOP)

    def expect_return(self, frame):
        """A port frame (port/guest.py) waits on a call of the guest: frame.resume(machine) runs when the guest
        reaches frame.ret_lin and frame.returned(machine), after the kit's handlers there (as a port at an entry)."""
        if frame.ret_lin not in self._handlers:
            self.at_linear(frame.ret_lin, NOOP)
        self.frames.append(frame)

    def on_write(self, begin, end, fn):
        """Call fn(address, size, value) at every write starting in [begin, end], before it lands: a guest
        instruction's (Unicorn's write hook) or a port's (write_as), told to listen_tap around each call (a proof's
        transcript). Not while `muted` (a proof's original runs): there the proof replays it. No listener of the kit's
        runs while muted (round 5: the old always=True flag is gone; only the proof's recorder, set_recorder, does)."""
        self._add_write(begin, end, fn, False)

    def set_recorder(self, fn):
        """The proof's write recorder (port/prove.py), reserved: the one write listener called also while `muted`,
        at every write of all memory, in its place among the listeners. One per machine."""
        if self._recorder is not None:
            from .port.mem import PortError
            raise PortError("the machine has its write recorder already (one proof per machine)")
        self._recorder = fn
        self._add_write(0, MEM_SIZE - 1, fn, True)

    def _add_write(self, begin, end, fn, recorder):
        index = len(self._writes)

        def hook(uc, access, address, size, value, data):
            try:
                if recorder:
                    fn(address, size, value)
                elif not self.muted:
                    self._listen(index, fn, address, size, value)
            except Exception as e:      # stop the emulation; run() re-raises it
                self.error = e
                uc.emu_stop()
        self._writes.append((begin, end, fn, recorder))
        self._uc.hook_add(UC_HOOK_MEM_WRITE, hook, begin=begin, end=end)

    def write_as(self, linear, size, value, at):
        """A port's write of `size` bytes at `linear`, as the original's instruction at the linear address `at`
        makes it: every write listener sees it (with pc() = at) before it lands, as a guest write's hooks would."""
        value &= (1 << (8 * size)) - 1
        saved, self._pc_override = self._pc_override, at
        try:
            for index, (begin, end, fn, recorder) in enumerate(list(self._writes)):
                if begin <= linear <= end and (recorder or not self.muted):
                    if recorder:
                        fn(linear, size, value)
                    else:
                        self._listen(index, fn, linear, size, value)
                    if self.error is not None:       # a watch's handler refused the write
                        err, self.error = self.error, None
                        raise err
        finally:
            self._pc_override = saved
        self._uc.mem_write(linear, value.to_bytes(size, "little"))

    def _listen(self, index, fn, address, size, value):
        """A kit write listener's call, told to listen_tap around it (a proof records its inputs and answer)."""
        tap = self.listen_tap
        if tap is None:
            fn(address, size, value)
            return
        token = tap.listen_enter(index, address, size, value)
        try:
            fn(address, size, value)
        finally:
            tap.listen_leave(token)

    def fire(self, address):
        """A port reaching `address` inside the routine it replaces: the handlers `at` it run as the original's
        reaching it would (replay False, pc() = the address). A stop they make takes effect at the port's return."""
        lin = self.lin(address)
        saved, self._pc_override = self._pc_override, lin
        handlers = list(self._handlers.get(lin, ()))
        tap = self.site_tap if any(h is not NOOP for h in handlers) else None
        if tap is not None:
            tap.site_enter(lin, False, fired=True)
        try:
            for h in handlers:
                h(False)
                if self.error is not None:
                    err, self.error = self.error, None
                    raise err
        finally:
            self._pc_override = saved
            if tap is not None:
                tap.site_leave(lin, False, fired=True)

    def watch(self, linear, size, handler):
        """Call handler(old, new), the watched `size` bytes at `linear` before and after, at every guest write that
        touches them, before the write lands (Unicorn calls write hooks first: the old bytes are still in memory).
        A write that starts up to 3 bytes below the range is caught too. A port's write (write_as) is seen the same."""
        def hook(address, wsize, value):
            if address + wsize <= linear or address >= linear + size:
                return
            old = self.read(linear, size)           # the kit's read: a proof compares it (io_tap)
            new = bytearray(old)
            for i in range(wsize):
                j = address + i - linear
                if 0 <= j < size:
                    new[j] = (value >> (8 * i)) & 0xFF
            try:
                handler(old, bytes(new))
            except Exception as e:
                self.error = e
                self._uc.emu_stop()
        self.on_write(max(0, linear - 3), linear + size - 1, hook)

    def stop(self, reason):
        self.stop_reason = reason
        self._uc.emu_stop()

    def pc(self):
        """The linear address of the instruction running: during a port's write or site, the listing's."""
        pc = self._pc_override if self._pc_override is not None else self.reg("cs") * 16 + self.reg("ip")
        if self.io_tap is not None:
            self.io_tap("p", None, pc)
        return pc

    def run(self, until, timeout_s=600, fresh=False):
        """Run from CS:IP until the linear address `until` or a stop; returns the stop reason (None at `until`).
        `fresh`: CS:IP is a new start (a call set up by far_call), not the instruction a stop left unexecuted; so is
        the return a port stopped at (no_replay_at)."""
        self.stop_reason = None
        start = self.pc()
        self._resume_lin = None if fresh or start == self.no_replay_at else start
        self.no_replay_at = None
        self.running = True
        try:
            self._uc.emu_start(start, until, timeout=int(timeout_s * 1_000_000))
        except UcError as e:
            self.running = False
            raise GuestError(f"the emulator stopped at {self.where(self.reg('cs'), self.reg('ip'))}: {e}") from e
        self.running = False
        if self.error is not None:
            err, self.error = self.error, None
            raise err
        if self.stop_reason is None and self.pc() != until:
            raise GuestError(f"the run ended at {self.where(self.reg('cs'), self.reg('ip'))} without reaching its end "
                             f"(time limit {timeout_s} s)")
        return self.stop_reason

    # -- snapshots ---------------------------------------------------------------------------------------
    def snapshot(self):
        return {"memory": self.read(0, MEM_SIZE), "regs": {r: self.reg(r) for r in REGS}, "load": self.load}

    def restore(self, snap):
        self.write(0, snap["memory"])
        for r, v in snap["regs"].items():
            self.set_reg(r, v)
