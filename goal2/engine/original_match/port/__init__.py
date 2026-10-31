"""The port mode (T58): Python translations of the original's routines run in place of them, inside the kit's match.

    Match(image, fixture, ports=["pilot"])                   # every port of port/pilot.py
    Match(image, fixture, ports=["pilot.coin-swapped"])      # the same with one of its variants (a falsifier)

A port module registers its own ports (no shared table, so tasks running at the same time own different files):

    PORTS = Registry("pilot", "what the module ports")
    PORTS.variant("coin-swapped", "the coin's two axis orders swapped (8A33)")

    @PORTS.port("0791:8889", ret="ret 2")                     # the listing's return, as it writes it
    def player_run_step(mem, variant):                       # mem: port.mem.Mem; variant: a name or None
        ...                                                  # a returned int is AX (and DX with long=True)

    PORTS.stub("0791:XXXX", ret="retf 4", value=0, why="...")  # a routine replaced by a declared return value (T73)

A port runs from its routine's entry, after every hook the kit has there (Machine.port), reads and writes only through
`mem` (port/mem.py), fires the kit's sites inside the routine with mem.site(), answers its key reads with
mem.read_key() and mem.keypressed(), and returns as the listing's `ret n` / `retf n`. A port that calls a routine
still the original's is a generator yielding guest.call(...) (port/guest.py, T59); prove.py runs a port side by side
with the original (T59). The module holds no byte of the original: only addresses, offsets and constants, each citing
its listing line."""
import importlib
import pkgutil
import re

from .mem import MachineMem, PortError

__all__ = ["Registry", "PortError", "load", "install", "available"]


class Entry:
    def __init__(self, address, ret, fn, name, long=False, stub=None, return_stack_delta=0):
        m = re.fullmatch(r"(retf|ret)(?: (0x[0-9a-fA-F]+|\d+))?", ret.strip())
        if not m:
            raise ValueError(f"{address}: ret {ret!r} is not the listing's `ret n` or `retf n`")
        self.address, self.ret, self.fn, self.name, self.long, self.stub = address, ret, fn, name, long, stub
        self.return_stack_delta = return_stack_delta
        self.far, self.pop = m.group(1) == "retf", int(m.group(2), 0) if m.group(2) else 0


class Registry:
    """A module's ports, stubs and variants."""

    def __init__(self, name, doc=""):
        self.name, self.doc = name, doc
        self.entries = {}           # address -> Entry
        self.variants = {}          # name -> what it changes

    def _add(self, entry):
        if entry.address in self.entries:
            raise ValueError(f"{self.name}: two ports of {entry.address}")
        self.entries[entry.address] = entry

    def port(self, address, ret, long=False, return_stack_delta=0):
        def deco(fn):
            self._add(Entry(address, ret, fn, fn.__name__, long, return_stack_delta=return_stack_delta))
            return fn
        return deco

    def stub(self, address, ret, value, why, long=False):
        """The routine at `address` replaced by a declared return value (None: nothing returned)."""
        self._add(Entry(address, ret, lambda mem, variant: value, f"stub {address}", long, stub=why))

    def variant(self, name, what):
        if not re.fullmatch(r"[a-z0-9][a-z0-9-]*", name):
            raise ValueError(f"variant name {name!r}: lower case, digits and '-'")
        self.variants[name] = what


NOT_PORT_MODULES = ("mem", "guest", "prove", "engine", "tables")   # the view, the guest calls, the proof (T59) and
#                                                                     the tables' loader (T80): machinery, no ports


def available():
    """The port modules of this package (each a file of its own, the machinery excluded)."""
    return sorted(m.name for m in pkgutil.iter_modules(__path__)
                  if m.name not in NOT_PORT_MODULES and not m.name.startswith("_"))


def _module_registry(name):
    if name not in available():
        raise ValueError(f"no port module {name!r} (there are: {', '.join(available()) or 'none'})")
    reg = getattr(importlib.import_module(f"{__name__}.{name}"), "PORTS", None)
    if not isinstance(reg, Registry) or reg.name != name:
        raise ValueError(f"port module {name} has no PORTS = Registry({name!r}, ...)")
    return reg


def load(specs):
    """[(Registry, variant or None)] for specs: 'module', 'module.variant', 'all', or (Registry, variant) as is."""
    out = []
    for spec in specs or ():
        if isinstance(spec, tuple):
            out.append(spec)
            continue
        if spec == "all":
            out.extend((_module_registry(n), None) for n in available())
            continue
        name, _, variant = spec.partition(".")
        reg = _module_registry(name)
        if variant and variant not in reg.variants:
            raise ValueError(f"port module {name} has no variant {variant!r} (it has: {', '.join(reg.variants) or 'none'})")
        out.append((reg, variant or None))
    seen = {}
    merged = []
    for reg, variant in out:            # a module named twice: once, with its variant if one was named
        if reg.name in seen:
            i = seen[reg.name]
            if variant is not None and merged[i][1] not in (None, variant):
                raise ValueError(f"two variants of {reg.name}: {merged[i][1]}, {variant}")
            merged[i] = (reg, variant or merged[i][1])
        else:
            seen[reg.name] = len(merged)
            merged.append((reg, variant))
    return merged


def spec_names(loaded):
    """The names a saved match keeps ('module' or 'module.variant')."""
    return [reg.name + (f".{v}" if v else "") for reg, v in loaded]


class Installed:
    """The ports running in a machine: their names and their calls per address."""

    def __init__(self, loaded, mem):
        self.loaded, self.mem = loaded, mem
        self.names = spec_names(loaded)
        self.calls = {}


def runner(entry, variant, mem, calls):
    """The port at its entry: a PortFrame (port/guest.py, T59) runs it and returns to the caller, at once for a plain
    function, after its last guest call for a generator; done(frame) is called at that return (the proof, prove.py)."""
    from .guest import PortFrame

    def run(machine, done=None):
        calls[entry.address] = calls.get(entry.address, 0) + 1
        PortFrame(machine, mem, entry, variant, done).start()
    run.entry = entry
    return run


def install(machine, specs, keys=None):
    """Put the ports of `specs` (load()) in place of their routines in `machine` (after the kit's own hooks, so
    they run after them). keys: the kit's key services (Match). Returns Installed."""
    loaded = load(specs)
    factory = getattr(machine, "port_memory", None)
    mem = factory(keys) if factory is not None else MachineMem(machine, keys)
    inst = Installed(loaded, mem)
    owner = {}
    for reg, variant in loaded:
        for address, entry in reg.entries.items():
            if address in owner:
                raise ValueError(f"{address} is ported by both {owner[address]} and {reg.name}")
            owner[address] = reg.name
            machine.port(address, runner(entry, variant, mem, inst.calls))
            inst.calls[address] = 0
    return inst
