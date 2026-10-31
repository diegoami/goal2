"""The proof mode (T59): every call of a ported routine run side by side with the original's (E021's rule, moved in
from runtime/emul/watched_match.py Guest.hook(prove=True)), the calls that cross the kit's sites and decisions
included.

Once the proof is armed (Match(prove=...)), at a ported routine's entry:

1. The port runs first, live: it is the match (the kit's hooks fire, decisions stop the match and are answered, the
   guest code it calls runs, port/guest.py). Every byte written meanwhile is recorded in order with the byte it
   replaced: the guest's (Unicorn's write hook), the port's (write_as) and the kit's own (Machine.write, e.g. the key
   a key read answers). So is every visit of a kit site (an address where the kit has a handler, or a site a port
   fires): its address, the guest's CS:IP and SS:SP there, and, in the order the kit's handlers made them, what they
   read (memory bytes, registers with the flags and segments, stack words: Machine.io_tap), the registers they set and
   the bytes they wrote; the kit's reads made between two runs while the match stands stopped at the site (a
   decision's answer) belong to it (a site that stopped the match, for a decision or for events, and was replayed on
   resume is one visit). Every call of a kit write listener (Machine.on_write, watch; Machine.listen_tap) is kept the
   same way: the listener, the write it was given, and what it read (pc() included), set and wrote. So are the
   registers each ported routine called inside the port's run returns (a nested call: it runs as its port). The
   prover's own reads and register changes bypass the taps.
2. At the port's return, its writes are undone and the CPU is put back to the entry; the ORIGINAL routine then runs
   as plain guest code, muted (machine.py: no handler, port or write listener of the kit runs in it; another ported
   routine it calls runs as the original's), its writes recorded the same way. At each kit site it reaches, the
   port's run's visit there is replayed instead of the kit: the same address in the same order, reached with the same
   CS:IP and SS:SP (a site a port fired from Python: the address only). The visit's events are taken in order: each
   read is compared with the original's byte or register BEFORE anything of the answer is applied (a difference
   raises ProofError naming the site, the byte or register, the port's run's value and the original's), each register
   set and write applied (the writes counted as the original's), so a read after a write of theirs sees it as it did.
   The kit therefore answers the original exactly as it answered the port, only where the original gave it the same
   inputs, and is never asked twice: one decision, one event stream. At each of the original's writes, the kit's
   listeners it reaches (muted, they do not run) are taken the same way, in Machine's order: paired with the port's
   run's next listener call (the same listener and write, else a difference named after the bytes in step 3), its
   reads compared and its answer applied. At the return of each ported routine the original calls, its registers
   (REGS_RETURNED, but a declared dead result) are compared with the port's run's call of the same rank to return
   (the same routine and caller), so an outer port cannot hide a nested port's result.
3. At the original's return the two must be identical: the registers of REGS_RETURNED, the kit sites (the same
   visits, none left over), and the written bytes and their order outside the routine's own dead frame (from the
   lowest the original's stack reached while it wrote up to the caller's SP after the return), and each site's place
   among those bytes (the same number of them written before it in both runs), then the listener calls (none
   unpaired, none left over) and the nested calls (none left over). The first difference
   raises ProofError naming the routine, the call, where the match is and the site, byte or register. Otherwise the
   original's writes are undone, the port's put back with its registers, and the match goes on from the port's state.

A difference in REGS_SCRATCH is counted per register, not an error (Turbo Pascal's convention: they are scratch
across a call). AX and DX are always compared, as E021 does, but for a (routine, return address) declared in
RESULT_DEAD with the static evidence that the caller never reads them there (out/T59/liveness.py over the listing);
a difference there is counted as `dead`, per register. A call made while another proof runs (a ported routine the
port calls) runs as its port, its writes and sites compared as part of the outer call and its result at its own
return (counted `nested`); a call before the proof is armed is counted `before`. No call ends otherwise: every armed
call is proved or raises ProofError. Refused under a proof (PortError), as nothing could replay them: a port that
answers a key read itself (mem.read_key, mem.keypressed; match.py), a kit write outside a site or a listener, a
register a fired site sets, and a stop made by a write listener or by a site a port fires (it takes effect at the
port's return, where the port's run is already undone).

The hooks are added once, when the proof is installed (Unicorn keeps a deleted hook listed until emu_start returns,
E021); a write hook over all memory costs every guest write a Python call, so a proved match is slower (locate.py)."""
from .mem import PortError

# Compared at a proved call's return (E021 notes.md section 5): AX, DX (the result), and what the caller relies on.
REGS_RETURNED = ("AX", "DX", "SP", "BP", "SS", "DS", "CS", "IP")
# Not compared; a difference is counted per register (E021: the owner, 2026-10-11).
REGS_SCRATCH = ("BX", "CX", "SI", "DI", "ES", "FLAGS")
REGS_ALL = ("EAX", "EBX", "ECX", "EDX", "ESI", "EDI", "EBP", "ESP", "EFLAGS", "CS", "DS", "ES", "SS", "FS", "GS", "EIP")
AT_SITE = ("CS", "IP", "SS", "SP")          # where the guest is at a kit site, compared between the two runs
# Returned registers the caller never reads, per (ported routine, return address): each with its evidence. Only these
# calls have the registers exempted; the same routine returning elsewhere is compared in full.
RESULT_DEAD = {
    ("0791:8889", "0791:8BB7"): (("AX", "DX"), (
        "8889's one call (calls.tsv: 8AE9 only) is 8BB4, returning to 8BB7. AX: 8BC1/8BC5 write AL and 8BC7 AH before "
        "8BCC reads AX (seg_0791_14.asm). DX: written before it is read on every path from 8BB7, through 8AE9's "
        "callees and back to its two callers 7881 and 9564 (calls.tsv; no data reference to 8AE9 in datarefs.tsv), by "
        "experiments/E036-match-port/out/T59/liveness.py over the listing (liveness-8BB7-b.txt; its controls "
        "liveness-controls.txt). The pilot's port leaves neither as the original's last 86D0 call does.")),
}
# The instructions that write below SP (push, call, pushf, pusha, enter, int): during such a write Unicorn's SP is the
# value before it (E021, probed 2026-10-12), so the slot written is where the stack reaches. Opcodes after any prefix;
# FF only with /2, /3 (call) or /6 (push). From watched_match.py.
PUSH_OPCODES = {0x06, 0x0E, 0x16, 0x1E, *range(0x50, 0x58), 0x60, 0x68, 0x6A, 0x9A, 0x9C, 0xC8, 0xCC, 0xCD, 0xCE, 0xE8}
PUSH_0F = {0xA0, 0xA8}
PREFIXES = {0x26, 0x2E, 0x36, 0x3E, 0x64, 0x65, 0x66, 0x67, 0xF0, 0xF2, 0xF3}


class ProofError(RuntimeError):
    """A port differs from the original routine at one call (the message names the routine, the call, the site, byte
    or register)."""


def pushes(code):
    """Does the instruction whose bytes start `code` write below SP (a push or a call)?"""
    i = 0
    while i < len(code) - 1 and code[i] in PREFIXES:
        i += 1
    op = code[i]
    if op == 0x0F:
        return code[i + 1] in PUSH_0F
    if op == 0xFF:
        return (code[i + 1] >> 3) & 7 in (2, 3, 6)
    return op in PUSH_OPCODES


class _Visit:
    """A kit site the port's run reached."""

    def __init__(self, lin, at, regs, fired):
        self.lin, self.at, self.regs, self.fired = lin, at, regs, fired
        # What the kit did with the guest there, in order: ("r", linear, bytes) it read, ("g", register, value) it
        # read, ("p", None, linear) pc() it read, ("s", register, value) it set, ("w", linear, bytes) it wrote; the
        # reads made between the runs while the match stood at this site (a decision's answer) included.
        self.events = []
        self.open = False           # stopped (a decision, events): the replay on resume belongs to it


class _Listen:
    """A call of a kit write listener (Machine.on_write, watch) the port's run made: the listener's index in
    Machine._writes, the write it was given (before it landed) and what it did, as a _Visit's events."""

    def __init__(self, index, address, size, value, label):
        self.index, self.address, self.size, self.value, self.label = index, address, size, value, label
        self.events = []


class _Call:
    """The proof of one call in progress."""

    def __init__(self, address, number, runner, done, regs, ss, sp, entry_lin, ret_lin, ret_sp, caller, where):
        self.address, self.number, self.runner, self.done = address, number, runner, done
        self.regs, self.ss, self.sp, self.entry_lin = regs, ss, sp, entry_lin
        self.ret_lin, self.ret_sp, self.caller, self.where = ret_lin, ret_sp, caller, where
        self.phase = "port"
        self.port_writes = []       # (linear, old bytes, new bytes) in order
        self.visits = []
        self.writes = []            # the original's, the same way
        self.low = ss * 16 + sp
        self.next_visit = 0
        self.started = False
        self.frame = None
        self.port_regs = None
        self.listens = []           # the kit's write listeners called in the port's run, in order (_Listen)
        self.next_listen = 0
        self.listen_diff = None     # the first listener call that does not pair up (named after the bytes, step 3)
        self.nested_returns = []    # the ported calls made inside the port's run: (address, caller, registers) at
        self.next_nested = 0        # each return, in the order they returned
        self.orig_nested = []       # the same routines' calls the original is inside: (address, caller, ret_lin, ret_sp)
        # ONE ordered transcript of everything the kit observes in the port's run (round 4): each site visit, each
        # write listener call, each nested ported call's entry and return, as (key, label) in the order they came;
        # the original's must come in the same order (checked as they come, named at the return: step 3).
        self.transcript = []
        self.next_event = 0
        self.order_diff = None


class Prover:
    """The proof of every installed port's calls (port.install's Installed). armed() says whether a call is proved
    (Match: from a given draw on); where() describes the match's point for a message (the minute, the draw)."""

    def __init__(self, machine, installed, armed=lambda: True, where=lambda: ""):
        if machine.muted_hook is not None:
            raise PortError("one proof per machine")
        taken = [n for n in ("site_tap", "write_tap", "io_tap", "listen_tap") if getattr(machine, n) is not None]
        if taken:                              # the taps are the proof's alone: another observer would be unordered
            raise PortError(f"the machine's {', '.join(taken)} is set already: a proof's taps are its own (round 5)")
        if machine.foreign_hooks:              # callbacks installed before would run in the muted original too
            raise PortError(f"{machine.foreign_hooks} use(s) of Machine.uc (the raw engine: a hook, an MMIO range, a "
                            "shared buffer, a bound read kept for later, ...) were made on this machine: a proof "
                            "cannot order or replay them; prove a machine on which Machine.uc was never used")
        machine.proving = True                # from here on (construction included) Machine.uc denies by default
        self.m, self.armed, self.where = machine, armed, where
        self.state = None
        self._visit = None          # the kit site whose handlers run now, during a proved call's port run
        self.proved, self.nested, self.before, self.scratch, self.dead = {}, {}, {}, {}, {}
        self.listened = {}          # per routine: the kit's write listener calls compared in its proved calls
        names = {}
        for reg, _ in installed.loaded:
            for address in reg.entries:
                names[address] = reg.name
        self.names = names
        for address in names:
            lin = machine.lin(address)
            machine._ports[lin] = self._wrap(address, machine._ports[lin], installed.calls)
            self.proved[address] = self.nested[address] = self.before[address] = self.listened[address] = 0
            self.scratch[address] = {r: 0 for r in REGS_SCRATCH}
            self.dead[address] = {}
        self._own_index = len(machine._writes)  # the kit's listeners before it run before it at a write, the rest after
        machine.set_recorder(self._record)    # once, before the run; the one listener called while muted
        machine.write_tap = self._host_write
        machine.io_tap = self._io
        machine.listen_tap = self
        machine.muted_hook = self._muted_at

    # The prover's own reads and register changes bypass the machine's taps (they are not the kit's).
    def _raw(self, linear, n):
        return bytes(self.m._uc.mem_read(linear, n))

    def _rreg(self, name):
        from unicorn import x86_const as X
        return self.m._uc.reg_read(getattr(X, f"UC_X86_REG_{name.upper()}"))

    def _sreg(self, name, value):
        from unicorn import x86_const as X
        self.m._uc.reg_write(getattr(X, f"UC_X86_REG_{name.upper()}"), value)

    def _io(self, kind, a, b):
        """Machine.io_tap: the kit's reads and register changes during a proved call's port run go to the site whose
        handlers run now, or, between two runs, to the site the match stands at (it stopped there)."""
        st = self.state
        if st is None or st.phase != "port":
            return
        v = self._visit
        if v is None and not self.m.running and st.visits and st.visits[-1].open:
            v = st.visits[-1]
        if v is not None:
            v.events.append((kind, a, b))

    def _observed(self, key, label):
        """The port's run: an event the kit observes, in the transcript."""
        self.state.transcript.append((key, label))

    def _expect(self, key, label):
        """The original: its next event the kit would observe must be the transcript's next; the first that is not is
        kept and named at the return, after the written bytes (a write that differs is named as such first)."""
        st = self.state
        if st.order_diff is not None:
            return
        i = st.next_event
        if i < len(st.transcript) and st.transcript[i][0] == key:
            st.next_event = i + 1
            return
        theirs = st.transcript[i][1] if i < len(st.transcript) else f"nothing ({len(st.transcript)} events)"
        st.order_diff = (f"the kit's observed event #{i + 1} differs in order: the original's is {label}, the port's "
                         f"run's {theirs}")

    def in_port_run(self):
        """Whether a proved call's port is running now (match.py refuses a port's own key reads then)."""
        return self.state is not None and self.state.phase == "port"

    def _caller_cs(self, runner):
        """At a routine's entry: the caller's CS (on the stack for a far routine)."""
        if runner.entry.far:
            ss, sp = self._rreg("ss"), self._rreg("sp")
            return int.from_bytes(self._raw(ss * 16 + ((sp + 2) & 0xFFFF), 2), "little")
        return self._rreg("cs")

    # A kit write listener's call (Machine.listen_tap): in a proved call's port run its inputs and answer are kept
    # (a _Listen), and compared and replayed at the same write of the original's (_record).
    def listen_enter(self, index, address, size, value):
        st = self.state
        if st is None or st.phase != "port":
            return None
        value &= (1 << (8 * size)) - 1
        lv = _Listen(index, address, size, value, f"write listener #{index} at the write of {size} bytes "
                                                  f"0x{value:0{2 * size}X} at {self.describe(address)}")
        st.listens.append(lv)
        self._observed(("listen", index, address, size, value), f"the kit's {lv.label}")
        token = (self._visit, self.m.stop_reason)
        self._visit = lv
        return token

    def listen_leave(self, token):
        if token is None:
            return
        lv = self._visit
        self._visit, stop_before = token
        if self.m.stop_reason is not None and self.m.stop_reason != stop_before:
            raise PortError(f"the kit's {lv.label} stopped the match ({self.m.stop_reason}) during a proved call: "
                            "its answer between runs is not replayable")

    # -- 1. the port, live, recorded ---------------------------------------------------------------------------
    def _wrap(self, address, runner, calls):
        def run(machine, done=None):
            st = self.state
            if st is not None:
                # Inside a proved call's port run: its writes and sites are the outer call's; its returned registers
                # are kept and compared with the original's same call (the n-th ported call to return, step 2).
                self.nested[address] += 1
                ip = int.from_bytes(self._raw(self._rreg("ss") * 16 + self._rreg("sp"), 2), "little")
                caller = self.m.where(self._caller_cs(runner), ip)
                self._observed(("enter", address, caller), f"the entry of {address} called from {caller}")

                def nested_done(frame):
                    st.nested_returns.append((address, caller, {r: self._rreg(r) for r in REGS_RETURNED}))
                    if self.state is st and st.phase == "port":
                        self._observed(("return", address, caller), f"the return of {address} to {caller}")
                    if done is not None:
                        done(frame)
                return runner(machine, nested_done)
            if not self.armed():
                self.before[address] += 1
                return runner(machine, done)
            m = machine
            far, pop = runner.entry.far, runner.entry.pop
            sp, ss = m.reg("sp"), m.reg("ss")
            ip = m.stack_word(0)
            cs = m.stack_word(2) if far else m.reg("cs")
            st = _Call(address, calls.get(address, 0) + 1, runner, done, {r: m.reg(r) for r in REGS_ALL}, ss, sp,
                       m.pc(), cs * 16 + ip, (sp + (4 if far else 2) + pop) & 0xFFFF, m.where(cs, ip), self.where())
            self.state = st
            if st.ret_lin not in m._handlers:     # the return address: where the original's run ends
                from ..machine import NOOP
                m.at_linear(st.ret_lin, NOOP)
            m.site_tap = self
            runner(m, self._port_done)
        run.entry = runner.entry
        return run

    def _record(self, address, size, value):
        st = self.state
        if st is None:
            return
        m = self.m
        value &= (1 << (8 * size)) - 1
        new = value.to_bytes(size, "little")
        if st.phase == "port":
            st.port_writes.append((address, self._raw(address, size), new))
            return
        st.started = True
        self._listeners_at(address, size, value, before=True)
        st.writes.append((address, self._raw(address, size), new))
        if self._rreg("ss") == st.ss:           # how far the original's stack reached
            sp = st.ss * 16 + self._rreg("sp")
            if pushes(self._raw(self._rreg("cs") * 16 + self._rreg("ip"), 6)) and sp - 16 <= address < sp:
                sp = address
            st.low = min(st.low, sp)
        self._listeners_at(address, size, value, before=False)

    def _listeners_at(self, address, size, value, before):
        """At the original's write, before it lands: the kit's write listeners it reaches (but muted), in the order
        Machine calls them (those added before the proof's own listener first: `before`), each matched with the port's
        run's next listener call, its inputs compared and its answer applied (as at a site)."""
        st = self.state
        for index, (begin, end, _, recorder) in enumerate(list(self.m._writes)):
            if recorder or not begin <= address <= end or (index < self._own_index) != before:
                continue
            if st.listen_diff is not None:      # the listener calls no longer pair up: the proof fails at the return
                return
            i = st.next_listen
            here = f"listener #{index} at the write of {size} bytes 0x{value:0{2 * size}X} at {self.describe(address)}"
            # A write that differs (another listener, address, size or value, or one the port's run did not make)
            # is a written byte that differs: named at the return by the bytes' comparison, which comes first; this
            # is named only if that comparison finds nothing (step 3).
            if i >= len(st.listens):
                st.listen_diff = (f"the original's write reached the kit's write {here} (listener call #{i + 1}), "
                                  f"which the port's run did not ({len(st.listens)} listener calls)")
                return
            self._expect(("listen", index, address, size, value), f"the kit's {here}")
            lv = st.listens[i]
            if (lv.index, lv.address, lv.size, lv.value) != (index, address, size, value):
                st.listen_diff = (f"the kit's write listener call #{i + 1}: the port's run gave the {lv.label}, the "
                                  f"original the {here}")
                return
            self._apply(lv.events, f"the kit's {lv.label} (listener call #{i + 1})")
            st.next_listen = i + 1

    def _host_write(self, linear, data):
        """The kit's own write (Machine.write) during the port's run: recorded, and kept for the visit's replay."""
        st = self.state
        if st is None or st.phase != "port":
            return
        st.port_writes.append((linear, self._raw(linear, len(data)), bytes(data)))
        if self._visit is not None:
            self._visit.events.append(("w", linear, bytes(data)))
        else:                                   # a write of the kit's outside its handlers: nothing could replay it
            raise PortError(f"the kit wrote {len(data)} bytes at {self.describe(linear)} outside a site of its own "
                            "during a proved call: not replayable")

    def _here(self, lin):
        """`lin` as the listing writes it, by the guest's CS now."""
        cs = self._rreg("cs")
        return self.m.where(cs, lin - cs * 16) if 0 <= lin - cs * 16 < 0x10000 else f"linear 0x{lin:05X}"

    def site_enter(self, lin, replay, fired=False):
        """Machine: the kit's handlers at `lin` are about to run (a dispatch, or a site a port fires)."""
        st = self.state
        last = st.visits[-1] if st.visits else None
        if replay and last is not None and last.open and last.lin == lin:
            self._visit = last                  # the resumed half of a visit that stopped
            return
        v = _Visit(lin, {r: self._rreg(r) for r in AT_SITE}, None, fired)
        v.stop_before = self.m.stop_reason
        v.label = self._here(lin)
        v.port_at = len(st.port_writes)     # the writes made before it: the original's must be the same (step 3)
        st.visits.append(v)
        self._observed(("site", lin), f"the kit's site {v.label}")
        self._visit = v

    def site_leave(self, lin, stopped, fired=False):
        v = self._visit
        self._visit = None
        if v is None:
            return
        v.open = stopped and not fired
        if fired and self.m.stop_reason is not None and self.m.stop_reason != v.stop_before:
            # its stop takes effect at the port's return, where the proof has already undone the port's run: what the
            # match reads there is not the port's state, and nothing could replay it
            raise PortError(f"the kit's site {v.label} fired by a port stopped the match ({self.m.stop_reason}) during "
                            "a proved call: not replayable in a proof")
        if fired and any(e[0] == "s" for e in v.events):
            raise PortError(f"the kit's site {v.label} fired by a port set registers "
                            f"{sorted({e[1] for e in v.events if e[0] == 's'})}: not replayable in a proof")

    def _port_done(self, frame):
        """The port returned: undo it, put the CPU back to the entry, and let the original run, muted."""
        st, m = self.state, self.m
        st.frame, st.port_regs = frame, {r: m.reg(r) for r in REGS_ALL}
        st.port_returned = {r: m.reg(r) for r in REGS_RETURNED + REGS_SCRATCH}
        m.site_tap = None
        st.phase = "original"
        for address, old, _ in reversed(st.port_writes):
            m._uc.mem_write(address, old)
        for r, v in st.regs.items():
            m.set_reg(r, v)
        m.muted = True                          # CS:IP is the entry: the guest runs the original next

    # -- 2. the original, muted, with the port's visits replayed ---------------------------------------------------
    def _muted_at(self, lin):
        st, m = self.state, self.m
        if not st.started and lin == st.entry_lin:
            st.started = True                   # the original's first instruction (its entry's hooks ran already)
            return
        st.started = True
        ss, sp = self._rreg("ss"), self._rreg("sp")
        if lin == st.ret_lin and ss == st.ss and sp == st.ret_sp:
            self._original_returned()
            return
        # In the order the port's run met them: a ported call's return (its port returned in Python, before the
        # guest reached the return address), the kit's site, then a ported routine's entry (its port ran after the
        # kit's handlers there).
        if st.orig_nested and st.orig_nested[-1][2:] == (lin, ss, sp):
            self._nested_returned()
        if m.hooked(lin):
            self._replay(lin)
        if lin in m._ports and self.state is not None:
            runner = m._ports[lin]
            ip = int.from_bytes(self._raw(ss * 16 + sp, 2), "little")
            ret_sp = (sp + (4 if runner.entry.far else 2) + runner.entry.pop) & 0xFFFF
            ret_lin = self._caller_cs(runner) * 16 + ip
            address = next(a for a in self.names if m.lin(a) == lin)
            caller = m.where(self._caller_cs(runner), ip)
            self._expect(("enter", address, caller), f"the entry of {address} called from {caller}")
            st.orig_nested.append((address, caller, ret_lin, ss, ret_sp))
            if ret_lin not in m._handlers:
                from ..machine import NOOP
                m.at_linear(ret_lin, NOOP)

    def _nested_returned(self):
        """The original returned from a call of a ported routine it made: compared with the port's run's call of the
        same rank to return (the routine, the caller, REGS_RETURNED but a declared dead result)."""
        st = self.state
        address, caller, _, _, _ = st.orig_nested.pop()
        self._expect(("return", address, caller), f"the return of {address} to {caller}")
        i = st.next_nested
        if i >= len(st.nested_returns):
            self._fail(f"the original's call of {address} ({self.names[address]}) from {caller} returned (ported call "
                       f"#{i + 1} inside), which the port's run did not make ({len(st.nested_returns)} ported calls)")
        p_address, p_caller, p_regs = st.nested_returns[i]
        if (p_address, p_caller) != (address, caller):
            self._fail(f"ported call #{i + 1} inside: the original's call of {address} from {caller} returned, the "
                       f"port's run's of {p_address} from {p_caller}")
        dead = RESULT_DEAD.get((address, caller), ((), ""))[0]
        for r in REGS_RETURNED:
            now = self._rreg(r)
            if now != p_regs[r]:
                if r in dead:
                    self.dead[address][r] = self.dead[address].get(r, 0) + 1
                    continue
                self._fail(f"ported call #{i + 1} inside, {address} ({self.names[address]}) from {caller}: register "
                           f"{r} at its return: the original 0x{now:04X}, the port 0x{p_regs[r]:04X}")
        st.next_nested = i + 1

    def _head(self, st):
        return (f"{st.address} ({self.names[st.address]}), call #{st.number} from {st.caller}"
                + (f", {st.where}" if st.where else ""))

    def _fail(self, text):
        st, m = self.state, self.m
        m.muted = False
        m.site_tap = None
        self.state = None
        raise ProofError(f"{self._head(st)}: {text}")

    def _replay(self, lin):
        st, m = self.state, self.m
        self._expect(("site", lin), f"the kit's site {self._here(lin)}")
        i = st.next_visit
        if i >= len(st.visits):
            self._fail(f"the original reached the kit's site {self._here(lin)} (site #{i + 1}), which the port's run "
                       f"did not ({len(st.visits)} sites)")
        v = st.visits[i]
        if v.lin != lin:
            self._fail(f"at the kit's site #{i + 1} the original reached {self._here(lin)}, the port's run {v.label}")
        if not v.fired:
            here = {r: m.reg(r) for r in AT_SITE}
            if here != v.at:
                self._fail(f"the original reached the kit's site {self._here(lin)} (#{i + 1}) at "
                           f"{here['CS']:04X}:{here['IP']:04X} SS:SP {here['SS']:04X}:{here['SP']:04X}, the port's run "
                           f"at {v.at['CS']:04X}:{v.at['IP']:04X} SS:SP {v.at['SS']:04X}:{v.at['SP']:04X}")
        # The kit's handlers, again, against the original: every input they read must be the original's (else the
        # answer recorded is not the one the kit would give it), and their answer (writes, registers) is applied in
        # the order they made it, so a read after a write of theirs sees it as it did.
        v.orig_at = len(st.writes)
        self._apply(v.events, f"the kit's site {v.label} (#{i + 1})")
        st.next_visit = i + 1

    def _apply(self, events, site):
        """A site's or a write listener's events against the original: each read compared, each set and write made."""
        st, m = self.state, self.m
        for kind, a, b in events:
            if kind == "r":
                now = self._raw(a, len(b))
                if now != b:
                    k = next(j for j in range(len(b)) if now[j] != b[j])
                    self._fail(f"at {site} the kit read the byte at {self.describe(a + k)}: the port's run gave it "
                               f"0x{b[k]:02X}, the original has 0x{now[k]:02X}")
            elif kind == "g":
                now = self._rreg(a)
                if now != b:
                    self._fail(f"at {site} the kit read register {a.upper()}: the port's run gave it 0x{b:04X}, the "
                               f"original has 0x{now:04X}")
            elif kind == "p":
                now = self._rreg("cs") * 16 + self._rreg("ip")
                if now != b:
                    self._fail(f"at {site} the kit read the instruction's address (pc): the port's run gave it "
                               f"{self._here(b)}, the original is at {self._here(now)}")
            elif kind == "s":
                self._sreg(a, b)
            else:                               # "w": the kit's write, counted as the original's
                st.writes.append((a, self._raw(a, len(b)), b))
                m._uc.mem_write(a, b)

    # -- 3. the comparison, then the port's state back ---------------------------------------------------------------
    def _original_returned(self):
        st, m = self.state, self.m
        if st.next_visit < len(st.visits):
            v = st.visits[st.next_visit]
            self._fail(f"the port's run reached the kit's site {v.label} (site #{st.next_visit + 1}), which "
                       "the original did not")
        if st.next_nested < len(st.nested_returns):
            address, caller, _ = st.nested_returns[st.next_nested]
            self._fail(f"the port's run made a call of {address} ({self.names[address]}) from {caller} (ported call "
                       f"#{st.next_nested + 1} inside), which the original did not return from")
        original_regs = {r: m.reg(r) for r in REGS_RETURNED + REGS_SCRATCH}
        port_regs = st.port_returned
        frame = (st.low, st.ss * 16 + m.reg("sp"))

        def live(ws):
            return [(a + i, n[i]) for a, _, n in ws for i in range(len(n)) if not frame[0] <= a + i < frame[1]]
        original, port = live(st.writes), live(st.port_writes)
        for i, (o, p) in enumerate(zip(original, port)):
            if o != p:
                self._fail(f"written byte #{i} differs: the original wrote 0x{o[1]:02X} at {self.describe(o[0])}, "
                           f"the port wrote 0x{p[1]:02X} at {self.describe(p[0])}")
        if len(original) != len(port):
            i = min(len(original), len(port))
            who, extra = ("original", original[i]) if len(original) > i else ("port", port[i])
            self._fail(f"the {who} writes more: byte #{i}, 0x{extra[1]:02X} at {self.describe(extra[0])} "
                       f"({len(original)} bytes by the original, {len(port)} by the port)")
        if st.listen_diff is not None:
            self._fail(st.listen_diff)
        if st.next_listen < len(st.listens):
            lv = st.listens[st.next_listen]
            self._fail(f"the port's run called the kit's {lv.label} (listener call #{st.next_listen + 1}), which the "
                       "original's writes did not reach")
        for i, v in enumerate(st.visits):      # each site between the same writes in both runs
            before_o, before_p = len(live(st.writes[:v.orig_at])), len(live(st.port_writes[:v.port_at]))
            if before_o != before_p:
                self._fail(f"the kit's site {v.label} (#{i + 1}) came after {before_o} written bytes in the original, "
                           f"after {before_p} in the port's run")
        if st.order_diff is not None:          # every event the kit observed, in one order (round 4)
            self._fail(st.order_diff)
        if st.next_event < len(st.transcript):
            self._fail(f"the port's run's kit event #{st.next_event + 1}, {st.transcript[st.next_event][1]}, has none "
                       "in the original")
        dead = RESULT_DEAD.get((st.address, st.caller), ((), ""))[0]
        for r in REGS_RETURNED:
            if original_regs[r] != port_regs[r]:
                if r in dead:
                    self.dead[st.address][r] = self.dead[st.address].get(r, 0) + 1
                    continue
                self._fail(f"register {r} at the return: the original 0x{original_regs[r]:04X}, "
                           f"the port 0x{port_regs[r]:04X}")
        for r in REGS_SCRATCH:
            if original_regs[r] != port_regs[r]:
                self.scratch[st.address][r] += 1
        for address, old, _ in reversed(st.writes):     # the port's state back: the match goes on from it
            m._uc.mem_write(address, old)
        for address, _, new in st.port_writes:
            m._uc.mem_write(address, new)
        for r, v in st.port_regs.items():
            m.set_reg(r, v)
        m.muted = False
        self.state = None
        self.proved[st.address] += 1
        self.listened[st.address] += st.next_listen     # the kit's write listener calls compared in it
        if st.done is not None:
            st.done(st.frame)

    def describe(self, linear):
        ds = self.m.DS * 16
        where = f" (DS:{linear - ds:04X})" if ds <= linear < ds + 0x10000 else ""
        return f"linear 0x{linear:05X}{where}"

    def summary(self):
        """{address: {"proved", "nested", "before": n, "dead": {register: n}, "scratch": {register: n}}}."""
        return {a: {"proved": self.proved[a], "nested": self.nested[a], "before": self.before[a],
                    "dead": dict(self.dead[a]), "scratch": {r: n for r, n in self.scratch[a].items() if n}}
                for a in self.names}
