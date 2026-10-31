"""Guest calls (T59): a port calls a routine that is still the original's.

    @PORTS.port("0791:6E11", ret="ret")
    def dead_ball_throw_in(mem, variant):
        yield mem.call("0791:8062", ret_to="0791:6E23", far=False)          # 6E20 call 0x8062
        ax = yield mem.call("0791:6BF1", side, 7, ret_to="0791:6E40", far=False)

A port that calls the original is a generator: it yields `mem.call(target, *args, ret_to=..., far=...)` and gets the
callee's AX back (DX and the rest through mem.reg). The call is the listing's: the argument words are pushed in the
order given (the last nearest the return address), then the return address `ret_to` (the instruction after the
listing's call; with far=True its segment first, as `call far` or `push cs; call near` does), and the guest runs the
callee as any guest code: the kit's hooks fire in it, its writes and draws reach the kit, another port runs in its
place if the callee is ported, and the kit may stop in it (an event, a decision). The port's Python frame is not on the
host stack meanwhile: it is this module's PortFrame, which the machine resumes when the guest reaches `ret_to` with SS:SP
back where the call left it (the callee popped its arguments, Turbo Pascal's convention; caller_pops=True for a
routine that does not, the port's frame then dropping them as the listing's `add sp, n` would). So a decision reached
inside the call stops the match as anywhere else and the match goes on exactly when it is answered; the port goes on
only from the callee's return, never from a stop (the hazard of a nested emulation, which this design does not use).

While a port frame waits, Match.save records an origin checkpoint and public actions; Match.load replays them to
reconstruct the Python generators and checks the entire resulting guest and kit state against the saved checkpoint.
A port that makes no call is a plain function, as in T58."""
import inspect

from .mem import PortError

_PARSED = {}    # T117: 'SSSS:OOOO' -> (segment, offset), each address parsed once


def _parsed(address):
    value = _PARSED.get(address)
    if value is None:
        value = _PARSED[address] = tuple(int(x, 16) for x in address.split(":"))
    return value


class Call:
    """A call of the guest a port yields (mem.call)."""
    __slots__ = ("target", "args", "ret_to", "far", "caller_pops")

    def __init__(self, target, args, ret_to, far, caller_pops=False):
        if not isinstance(far, bool):
            raise PortError(f"call of {target}: far=True or far=False, as the listing's call is")
        self.target, self.args, self.ret_to, self.far, self.caller_pops = target, tuple(args), ret_to, far, caller_pops


def call(target, *args, ret_to, far, caller_pops=False):
    return Call(target, args, ret_to, far, caller_pops)


class PortFrame:
    """One running call of a port: its entry state, its generator (if it calls the guest) and the call it waits on."""

    def __init__(self, machine, mem, entry, variant, done=None):
        self.m, self.mem, self.entry, self.variant, self.done = machine, mem, entry, variant, done
        self.ss, self.sp, self.bp = machine.reg("ss"), machine.reg("sp"), machine.reg("bp")
        self.gen = None
        self.waiting = None         # the Call the frame waits on
        self.ret_lin = None
        self.expect_sp = None
        self.after_sp = None

    def describe(self):
        if self.waiting is None:
            return self.entry.address
        return f"{self.entry.address} waiting on its call of {self.waiting.target} (returning to {self.waiting.ret_to})"

    def _in_frame(self, fn):
        mem = self.mem
        mem._entries.append((self.sp, self.entry.far))
        try:
            return fn()
        finally:
            mem._entries.pop()

    def start(self):
        value = self._in_frame(lambda: self.entry.fn(self.mem, self.variant))
        if inspect.isgenerator(value):
            self.gen = value
            self._step(None)
        else:
            self._finish(value)

    def _step(self, sent):
        try:
            request = self._in_frame(lambda: self.gen.send(sent))
        except StopIteration as stop:
            self._finish(stop.value)
            return
        if not isinstance(request, Call):
            raise PortError(f"port {self.entry.address} yielded {request!r}: a port yields mem.call(...) only")
        self._issue(request)

    def _issue(self, c):
        m, mem = self.m, self.mem
        rseg, roff = _parsed(c.ret_to)
        tseg, toff = _parsed(c.target)
        if not c.far and (m.seg(tseg) != m.reg("cs") or m.seg(rseg) != m.reg("cs")):
            raise PortError(f"port {self.entry.address}: a near call of {c.target} returning to {c.ret_to} from CS "
                            f"{m.where(m.reg('cs'), 0)[:4]}: a near call stays in its segment")
        sp = m.reg("sp")
        self.after_sp = sp
        words = [w & 0xFFFF for w in c.args] + ([m.seg(rseg)] if c.far else []) + [roff]
        for w in words:             # the pushes, named as the call's (no watch of the kit reads the stack)
            sp = (sp - 2) & 0xFFFF
            mem.w16(mem.ss_lin(sp), w, c.ret_to)
        m.set_reg("sp", sp)
        self.expect_sp = self.after_sp if not c.caller_pops else (self.after_sp - 2 * len(c.args)) & 0xFFFF
        self.waiting, self.ret_lin = c, m.seg(rseg) * 16 + roff  # m.lin(c.ret_to), parsed once
        m.set_reg("cs", m.seg(tseg))
        m.set_reg("eip", toff)
        m.expect_return(self)

    def returned(self, machine):
        """At ret_lin: whether this is the return of the call the frame waits on (and not a deeper or a recursive
        reach of the same address)."""
        return machine.reg("ss") == self.ss and machine.reg("sp") == self.expect_sp

    def resume(self, machine):
        ax = machine.reg("ax")
        machine.set_reg("sp", self.after_sp)     # caller_pops: the listing's `add sp, n`
        self.waiting = self.ret_lin = None
        self._step(ax)

    def _finish(self, value):
        m, entry = self.m, self.entry
        self.value = value          # None: a procedure's port (the proof then counts AX, DX as scratch, prove.py)
        m.set_reg("sp", (self.sp + entry.return_stack_delta) & 0xFFFF)
        # Usually the entry stack again. DOS.MsDos235C:0000 shifts its real
        # return frame down one word before falling through Intr's retf6.
        m.set_reg("bp", self.bp)
        if value is not None:
            value = int(value)
            m.set_reg("ax", value & 0xFFFF)
            if entry.long:
                m.set_reg("dx", (value >> 16) & 0xFFFF)
        m.return_from(entry.far, entry.pop)
        if self.done is not None:
            self.done(self)
