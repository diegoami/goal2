"""T78a: run registered Python ports on plain memory, never original instructions.

The control protocol is machine.py with guest.PortFrame: entry handlers precede
ports, near/far returns retain their declared stack ABI, and a stop inside a
ported body is deferred until it yields/returns. This is assembly machinery,
not an x86 interpreter. Unregistered execution addresses are refused.
"""
import time

from ..machine import Machine, MEM_SIZE, DS_PARAGRAPH, REGS, NOOP
from .mem import MachineMem, PortError


def _alias_of(name):
    """The (base register, shift, bits) a plain register name addresses."""
    name = name.lower()
    if name in ('eax','ebx','ecx','edx','esi','edi','ebp','esp','eip','eflags'):
        return name, 0, 32
    if name in ('cs','ds','es','ss','fs','gs'):
        return name, 0, 16
    if name in ('ax','bx','cx','dx','si','di','bp','sp','ip','flags'):
        return 'e'+name, 0, 16
    if len(name)==2 and name[0] in 'abcd' and name[1] in 'lh':
        return 'e'+name[0]+'x', 8 if name[1]=='h' else 0, 8
    raise PortError(f'unsupported plain register {name!r}')


# T117: every supported lower-case name, resolved once: (base, shift, bits, the name an io_tap is
# told, whether a write clears the base first). Any other name, upper case included, takes
# _alias_of's path each time, with its errors unchanged.
_REGISTERS = {}
for _name in ('eax','ebx','ecx','edx','esi','edi','ebp','esp','eip','eflags','cs','ds','es','ss','fs','gs',
              'ax','bx','cx','dx','si','di','bp','sp','ip','flags','al','ah','bl','bh','cl','ch','dl','dh'):
    _REGISTERS[_name] = _alias_of(_name) + (_name, _name in ('ip','flags'))
del _name
# The same table for a read with no io_tap: (base, shift, mask).
_READ = {name: (base, shift, (1 << bits)-1) for name, (base, shift, bits, _, _) in _REGISTERS.items()}
# ... and for a write: (base, the mask in place, shift, whether the base clears first).
_WRITE = {name: (base, ((1 << bits)-1) << shift, shift, clears)
          for name, (base, shift, bits, _, clears) in _REGISTERS.items()}


def _set_plain(registers, name, value):
    """PortMachine.set_reg with no io_tap, for a supported lower-case name; False for any other."""
    entry = _WRITE.get(name) if name.__class__ is str else None
    if entry is None:
        return False
    base, mask, shift, clears = entry
    if clears:registers[base] = 0
    registers[base] = ((registers[base] & ~mask) | ((value << shift) & mask)) & 0xFFFFFFFF
    if base=='eflags':registers[base] |= 2
    return True


def _register(name):
    try:
        return _REGISTERS[name]
    except (KeyError, TypeError):
        lowered = name.lower()
        return _alias_of(name) + (lowered, lowered in ('ip','flags'))


class _PortMemory(MachineMem):
    def read(self, linear, n):
        # As MachineMem's native read, a port's own read is not a kit IO-tap read.
        self.m._bounds(linear, n)
        return bytes(self.m._memory[linear:linear+n])

    # T117: the view's hottest reads, one call each. A read of the port's own is never tapped (above),
    # so u8/u16 need no tap check; a register read takes the machine's path whenever an io_tap listens.
    def u8(self, linear):
        self.m._bounds(linear, 1)
        return self.m._memory[linear]

    def u16(self, linear):
        self.m._bounds(linear, 2)
        return int.from_bytes(self.m._memory[linear:linear+2], "little")

    def reg(self, name):
        m = self.m
        if m.io_tap is None:
            fast = _READ.get(name) if name.__class__ is str else None
            if fast is not None:
                base, shift, mask = fast
                return m._registers[base] >> shift & mask
        return m.reg(name)

    # T117: Mem's write path in one layer (Mem.w8/w16 -> _write -> Machine.write_as), the
    # instruction's address from the same cache.
    def _at(self, at):
        cache = self.__dict__.get("_at_cache")
        if cache is not None:
            lin = cache.get(at)
            if lin is not None:
                return lin
        return MachineMem._at(self, at)

    def w8(self, linear, value, at):
        self.m.write_as(linear, 1, value & 0xFF, self._at(at))

    def w16(self, linear, value, at):
        self.m.write_as(linear, 2, value & 0xFFFF, self._at(at))

    def set_reg(self, name, value):
        m = self.m
        if m.io_tap is None and _set_plain(m._registers, name, value):
            return
        m.set_reg(name, value)

    def ss_lin(self, off):
        m = self.m
        if m.io_tap is None:
            return (m._registers['ss'] & 0xFFFF) * 16 + (off & 0xFFFF)
        return m.reg("ss") * 16 + (off & 0xFFFF)


class PortMachine(Machine):
    """The existing port/call/listener interface with no Unicorn object or opcode runner."""
    def __init__(self, memory, load):
        if len(memory) < MEM_SIZE:
            raise ValueError(f'the image holds {len(memory)} bytes; {MEM_SIZE} are needed')
        self._memory = bytearray(memory[:MEM_SIZE])
        self._registers = {name.lower(): 0 for name in REGS}
        # x86 reserved flag bit1, independently checked against the reference API
        # by out/T78a/register-controls-v1.json; other supplied bits are retained.
        self._registers['eflags'] = 2
        self.load, self.DS = load, load + DS_PARAGRAPH
        self.proving = False
        self.foreign_hooks = 0
        self._recorder = None
        self.stop_reason = self.error = None
        self._handlers, self._ports = {}, {}
        self._resume_lin = self._pc_override = self.no_replay_at = None
        self._writes, self.frames = [], []
        self._writes_now = ()       # T117: _writes as a tuple, replaced (never changed) by _add_write,
        self._writes_span = (1, 0)  # and the lowest begin/highest end of all of them (none: empty)
        self.muted = False
        self.muted_hook = self.site_tap = self.write_tap = None
        self.io_tap = self.listen_tap = None
        self.running = False

    def port_memory(self, keys=None):
        return _PortMemory(self, keys)

    @staticmethod
    def _bounds(linear, n):
        # T117: plain ints in range pass at once; anything else (bool included) takes the full check.
        if linear.__class__ is int and n.__class__ is int and 0 <= linear and 0 <= n and linear+n <= MEM_SIZE:
            return
        if (not isinstance(linear, int) or not isinstance(n, int)
                or linear < 0 or n < 0 or linear+n > MEM_SIZE):
            raise PortError(f'plain-memory read/write outside mapped range: {linear}+{n}')

    def read(self, linear, n):
        self._bounds(linear, n)
        data = bytes(self._memory[linear:linear+n])
        if self.io_tap is not None:self.io_tap('r', linear, data)
        return data

    def write(self, linear, data):
        data = bytes(data);self._bounds(linear, len(data))
        if self.write_tap is not None:self.write_tap(linear, data)
        self._memory[linear:linear+len(data)] = data

    @staticmethod
    def _alias(name):
        return _register(name)[:3]

    def reg(self, name):
        base, shift, bits, told, _ = _register(name)
        value = self._registers[base] >> shift & ((1 << bits)-1)
        if self.io_tap is not None:self.io_tap('g', told, value)
        return value

    def set_reg(self, name, value):
        if self.io_tap is None and _set_plain(self._registers, name, value):
            return
        base, shift, bits, told, clears = _register(name)
        # Reference register API: IP/FLAGS writes clear their upper half;
        # general-purpose low-word aliases retain it (review563 R1 controls).
        if clears:self._registers[base] = 0
        mask = ((1 << bits)-1) << shift
        self._registers[base] = ((self._registers[base] & ~mask) | ((value << shift) & mask)) & 0xFFFFFFFF
        if base=='eflags':self._registers[base] |= 2
        if self.io_tap is not None:self.io_tap('s', told, value)

    def at_linear(self, linear, handler):
        self._handlers.setdefault(linear, []).append(handler)

    def _add_write(self, begin, end, fn, recorder):
        self._writes.append((begin, end, fn, recorder))
        self._writes_now = tuple(self._writes)
        self._writes_span = (min(w[0] for w in self._writes), max(w[1] for w in self._writes))

    def write_as(self, linear, size, value, at):
        self._bounds(linear, size)
        value &= (1 << (8*size))-1
        lo, hi = self._writes_span
        if not lo <= linear <= hi:  # no listener's range holds it: the loop below would call none
            self._memory[linear:linear+size] = value.to_bytes(size, 'little')
            return
        saved, self._pc_override = self._pc_override, at
        try:
            # The listeners as at this write's start, as the list copy was: one added meanwhile waits.
            for index, (begin, end, fn, recorder) in enumerate(self._writes_now):
                if begin <= linear <= end and (recorder or not self.muted):
                    if recorder:fn(linear, size, value)
                    else:self._listen(index, fn, linear, size, value)
                    if self.error is not None:
                        error, self.error = self.error, None
                        raise error
        finally:self._pc_override = saved
        self._memory[linear:linear+size] = value.to_bytes(size, 'little')

    def watch(self, linear, size, handler):
        def hook(address, wsize, value):
            if address+wsize <= linear or address >= linear+size:return
            old = self.read(linear, size);new = bytearray(old)
            for i in range(wsize):
                j = address+i-linear
                if 0 <= j < size:new[j] = value >> (8*i) & 255
            try:handler(old, bytes(new))
            except Exception as error:self.error = error
        self.on_write(max(0, linear-3), linear+size-1, hook)

    def stop(self, reason):
        self.stop_reason = reason

    def pc(self):
        # T117: Machine.pc without its two register calls, unless an io_tap listens to them.
        if self.io_tap is not None:
            return Machine.pc(self)
        if self._pc_override is not None:
            return self._pc_override
        registers = self._registers
        return (registers['cs'] & 0xFFFF) * 16 + (registers['eip'] & 0xFFFF)

    def _dispatch(self, linear):
        replay = linear == self._resume_lin
        self._resume_lin = None
        handlers = self._handlers.get(linear)
        if handlers:  # T117: an address with no handler skips the copy, the tap test and the loop
            handlers = list(handlers)
            tap = self.site_tap if any(h is not NOOP for h in handlers) else None
            if tap is not None:tap.site_enter(linear, replay)
            stopped = False
            for handler in handlers:
                handler(replay)
                if self.stop_reason is not None or self.error is not None:
                    stopped = True;break
            if tap is not None:tap.site_leave(linear, stopped)
            if stopped:return
        runner = self._ports.get(linear)
        frame = self.frames[-1] if self.frames else None
        if runner is not None:runner(self)
        elif frame is not None and frame.ret_lin==linear and frame.returned(self):
            self.frames.pop();frame.resume(self)
        elif self.pc()!=linear:
            return  # a registered kit service explicitly returned/redirected
        else:
            raise PortError('no registered port/return at '+self.where(self.reg('cs'), self.reg('ip')))
        if self.stop_reason is not None:self.no_replay_at = self.pc()

    def run(self, until, timeout_s=600, fresh=False):
        if self.muted:raise PortError('plain engine cannot execute a muted original proof')
        self.stop_reason = None
        start = self.pc()
        self._resume_lin = None if fresh or start==self.no_replay_at else start
        self.no_replay_at = None
        deadline = time.monotonic()+timeout_s
        self.running = True
        try:
            while True:
                # T117: pc() once a step; an io_tap is told of both calls, as before.
                pc = self.pc()
                if pc==until:break
                if time.monotonic() > deadline:raise PortError('plain dispatch time limit exceeded')
                self._dispatch(self.pc() if self.io_tap is not None else pc)
                if self.error is not None:
                    error, self.error = self.error, None
                    raise error
                if self.stop_reason is not None:break
        finally:self.running = False
        return self.stop_reason
