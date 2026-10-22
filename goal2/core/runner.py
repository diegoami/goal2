"""goal2's core: the original's whole game, run under Unicorn from a main-screen savestate (stage 3, G8).

[designed: owner, 2026-10-22, #308] The original's own code runs as goal2's headless core; goal2 is the interface and
the bot over it. [derived: docs/estimates/99-original-engine-plugged-in.md, Stage 3 G8] Each key the original
reads is a yield point: `Core.start(savestate)` runs to the first read and returns a `KeyWait`; `core.press(key)`
answers it and runs to the next. See docs/core.md.

Evidence (goal2-archaeology at 53d7ef5 unless a commit is named):
- [confirmed: the vendored kit goal2/engine/original_match, match.py; seg_214B_02.asm 08DD-0982 (aefd8d3)] Every key
  the original reads goes through 214B:0723 ("key pressed?") and 214B:08DD (read a key). 08DD stores the key code
  at DS:A976 (0947), copies it to DS:A977 (097C) and returns it in AL (0979); with the pushed-back flag DS:79AE set
  it reads nothing (08E3-08EF). The return address of an 08DD call is the read's site.
- [confirmed: E021 notes.md section 1 (e2a46a4), runtime/emul/watched_match.py cpu_state] A DOSBox-X 2024.03.01
  savestate's `CPU` component holds the registers: EAX ECX EDX EBX ESP EBP ESI EDI at 0, EIP at 0x20, the flags at
  0x28, ES CS SS DS FS GS as words 8 bytes apart from 0xEB. A state saved at a key wait is inside the BIOS's
  INT 16h (CS:IP F000:CFA9 in E021's half-time states; F000:CFAA in E006-r0001).
- [confirmed: seg_214B_02.asm 08DD-08FF] 08DD's frame: `push bp; mov bp, sp; sub sp, 0x14`, then it pushes AX
  (AL = 0x16), SS and DI = BP-0x14 and calls 235C:000B (Intr) at 08FF, whose far return is 214B:0904.
- [confirmed: F001 (8c9622b), runtime/driver/savestate.py (ea4dba8)] The text page is in the savestate's `Vga`
  component at stream offset 0x86024, 8 bytes per cell (character, attribute, ...), not in `Memory`; the record's
  text is CP437 with 0 shown as a space and 1..31 as their glyphs, trailing blanks trimmed.
- [confirmed: F004] The DOS time seeds the game: 23E4:11D7 stores CX at DS:7B62 (the main RNG word) and DX at
  DS:7B64.
- [confirmed: F030] A timed prompt is a count of "key pressed?" polls with a calibrated delay between them
  (wait_or_key 0791:CC2E: up to n polls, 214B:1E09(10) after each); it reads no clock.

R1, how the loop is entered [derived: the four claims above]: the template's CPU is inside the BIOS's INT 16h, called
by 08DD through Intr. The core finds Intr's far return 214B:0904 on the template's own stack, checks the three
argument words 08DD pushed before it, and rebuilds 08DD's entry from its prologue: SP = 08DD's BP + 2, BP = the
saved BP, CS:IP = 214B:08DD, DS = ES = the program's data segment (DS:A923's segment, load + 0x2581). Every return
address above is the guest's own; no byte of guest memory is written but the text page (below). E006-r0001's chain:
08DD <- 1771:28F0 (the country browser 1771:26B9, "team info") <- 000E:767D (main_menu_loop 000E:7439,
annotations/routines.tsv) <- 0000:00C6.
"""
from __future__ import annotations

import hashlib
import io
import json
import struct
import zipfile
import zlib
from dataclasses import dataclass, field

from goal2.engine.original_match import machine as _machine
from goal2.engine.original_match.image import Image, MEM_BASE
from goal2.engine.original_match.machine import Machine, MEM_SIZE, REGS
from goal2.engine.original_match.match import KEYPRESSED, READKEY, PUSHED_BACK, KEY, SCREEN_PTR, SEED

VERSION = 1
MAGIC = b"G2C1"
KEY_AHEAD = 0xA977            # 08DD 097C: the last key read
SEEDS = (SEED, 0x7B64)        # F004: DS:7B62 (CX of INT 21h AH=2Ch, the main RNG word), DS:7B64 (DX)
F5_PRINT = 0xA3               # 08DD 095C-0964: F5 (scan 0x3F + 0x64) prints the screen and reads another key
INTR_RETURN = ("214B", 0x0904)   # 08DD's call far 235C:000B (Intr) at 08FF returns here
READKEY_LOCALS, INTR_ARGS, INT16 = 0x14, 6, 0x16
STACK_SEARCH = 0x200          # bytes above SS:SP searched for Intr's return
END = 1 << 21                 # an address no 16-bit CS:IP reaches: runs stop only at a read, the budget or an error
DEFAULT_BUDGET = 10_000_000_000   # [designed] instructions between two reads (a watched first half: 3e9..4e9, T100)
# The CPU component (E021 notes section 1)
CPU_GPR, CPU_EIP, CPU_FLAGS, CPU_SEGS, CPU_SEG_STRIDE = 0x00, 0x20, 0x28, 0xEB, 8
GPR_NAMES = ("EAX", "ECX", "EDX", "EBX", "ESP", "EBP", "ESI", "EDI")
SEG_NAMES = ("ES", "CS", "SS", "DS", "FS", "GS")
# The text page (F001; runtime/driver/savestate.py)
VGA_TEXT_BASE, CELL_BYTES, ROWS, COLS = 0x86024, 8, 25, 80
TEXT_PAGE = 0xB8000           # where the guest writes it: the far pointer DS:A96A (B800:0000 in E006-r0001)
CP437_LOW = ("☺☻♥♦♣♠•◘○◙♂♀♪♫☼"
             "►◄↕‼¶§▬↨↑↓→←∟↔▲▼")


class CoreError(RuntimeError):
    """The core stopped rather than guess: the template is not at a key read, the original did something the core
    does not serve, or the core was asked for something the original is not doing."""


class BudgetExceeded(CoreError):
    """The original ran more instructions than the budget without reading a key."""

    def __init__(self, budget, pc, text):
        self.budget, self.pc, self.text = budget, pc, text
        super().__init__(f"the original ran {budget} instructions without reading a key; PC {pc}\n{text}")


class InterruptError(CoreError):
    """The original called an interrupt (BIOS or DOS): the core serves none and stops at the first."""

    def __init__(self, number, ax, pc, text):
        self.number, self.ax, self.pc, self.text = number, ax, pc, text
        super().__init__(f"the original called INT {number:02X}h (AX {ax:04X}) at {pc}; the core serves no "
                         f"interrupt\n{text}")


def decode_text(raw):
    """The 80x25 text page (4000 bytes, character and attribute per cell) as F001's records decode it."""
    def ch(c):
        return " " if c == 0 else (CP437_LOW[c - 1] if c < 32 else bytes([c]).decode("cp437"))
    chars = raw[0::2]
    return "\n".join("".join(ch(c) for c in chars[r * COLS:(r + 1) * COLS]).rstrip() for r in range(ROWS))


def cpu_state(savestate):
    """The registers a DOSBox-X 2024.03.01 savestate holds (E021 notes section 1)."""
    with zipfile.ZipFile(io.BytesIO(savestate)) as z:
        d = zlib.decompressobj().decompress(z.read("CPU"))
    regs = dict(zip(GPR_NAMES, struct.unpack_from("<8I", d, CPU_GPR)))
    regs["EIP"] = struct.unpack_from("<I", d, CPU_EIP)[0]
    regs["EFLAGS"] = struct.unpack_from("<Q", d, CPU_FLAGS)[0] & 0xFFFFFFFF
    for i, name in enumerate(SEG_NAMES):
        regs[name] = struct.unpack_from("<H", d, CPU_SEGS + CPU_SEG_STRIDE * i)[0]
    return regs


def text_page(savestate):
    """The 4000 bytes of the text page from the savestate's Vga component (F001)."""
    with zipfile.ZipFile(io.BytesIO(savestate)) as z:
        v = zlib.decompressobj().decompress(z.read("Vga"))
    n = ROWS * COLS
    if len(v) < VGA_TEXT_BASE + CELL_BYTES * n:
        raise CoreError(f"the savestate's Vga component is too short for the text page ({len(v)} bytes)")
    cells = v[VGA_TEXT_BASE:VGA_TEXT_BASE + CELL_BYTES * n]
    return bytes(b for i in range(n) for b in (cells[CELL_BYTES * i], cells[CELL_BYTES * i + 1]))


def read_entry(memory, load, regs):
    """08DD's entry rebuilt from the savestate's own stack (R1, module docstring): {'ss', 'sp', 'bp', 'site'}."""
    ss, sp = regs["SS"], regs["ESP"] & 0xFFFF
    seg = (load + int(INTR_RETURN[0], 16)) & 0xFFFF

    def word(off):
        a = ss * 16 + (off & 0xFFFF)
        return int.from_bytes(memory[a:a + 2], "little")
    hits = []
    for off in range(sp, sp + STACK_SEARCH, 2):
        if word(off) != INTR_RETURN[1] or word(off + 2) != seg:
            continue
        bp = (off + 4 + INTR_ARGS + READKEY_LOCALS) & 0xFFFF
        if word(off + 4) == (bp - READKEY_LOCALS) & 0xFFFF and word(off + 6) == ss and word(off + 8) & 0xFF == INT16:
            hits.append(bp)
    if len(hits) != 1:
        raise CoreError(f"the savestate is not stopped in the original's key read: {len(hits)} frames of 214B:08DD's "
                        f"INT 16h call (Intr, returning to 214B:0904) above SS:SP {ss:04X}:{sp:04X}, one is needed "
                        f"(CPU at {regs['CS']:04X}:{regs['EIP'] & 0xFFFF:04X})")
    bp = hits[0]
    return {"ss": ss, "sp": (bp + 2) & 0xFFFF, "bp": word(bp), "site": (word(bp + 4), word(bp + 2))}


class StateView:
    """A read-only view of the original's memory at a wait, through the kit's `Image` (its record readers)."""

    _READERS = ("rd", "far", "rd_far", "players", "countries", "squad", "managed_countries", "fixture_index",
                "year", "name", "sha256", "memory_component")

    def __init__(self, memory_component):
        self._component = memory_component      # immutable bytes: the memory at the wait
        self._cached = None

    @property
    def _image(self):
        if self._cached is None:
            self._cached = Image.from_memory_component(self._component)
        return self._cached

    def __getattr__(self, name):
        if name in StateView._READERS:
            return getattr(self._image, name)
        raise AttributeError(name)

    @property
    def managed(self):
        return tuple(self._image.managed_countries())

    def __repr__(self):
        return f"StateView(managed={self.managed}, year={self._image.year()})"


@dataclass(frozen=True)
class KeyWait:
    """The original waits for a key: `site` the return address of its 214B:08DD call ('SSSS:OOOO' as the listing
    writes it), `text` the text page (25 lines, CP437, trailing blanks trimmed), `screen` its 4000 raw bytes, `state`
    the memory through the kit's Image, `polls` the "key pressed?" polls answered since the last wait, per site."""
    site: str
    text: str
    screen: bytes = field(repr=False)
    state: StateView = field(repr=False, compare=False)
    polls: tuple = ()
    core: "Core" = field(default=None, repr=False, compare=False)


class Core:
    """The original's game running from a main-screen savestate. `Core.start(savestate)` gives the first KeyWait
    (its `.core` is the Core); `press(key)` answers the wait; `save()` and `Core.load(blob)` stop and resume it."""

    def __init__(self, m, header, tail, budget, keys, template_sha256):
        self.m, self.header, self.tail = m, header, tail
        self.budget, self.keys, self.template_sha256 = budget, keys, template_sha256
        self.stopped = None           # why the core can run no further (an error it raised)
        self._polls = {}
        self.wait = None
        self._hooks()

    # -- starting and resuming -----------------------------------------------------------------------------
    @classmethod
    def start(cls, savestate, *, budget=DEFAULT_BUDGET):
        """Run the original from a savestate stopped at one of its key reads (E006-r0001, the main screen of a new
        game) to its first key read; returns that KeyWait."""
        _need_unicorn()
        savestate = bytes(savestate)
        image = Image.from_savestate(savestate)
        problems = image.build_problems()
        if problems:
            raise ValueError("the image does not hold the GOAL.EXE the kit was made on; it differs in: "
                             + "; ".join(problems))
        regs = cpu_state(savestate)
        entry = read_entry(image.memory, image.load, regs)
        m = Machine(image.memory, image.load)
        m.write(TEXT_PAGE, text_page(savestate))
        for name in REGS:
            if name in regs:
                m.set_reg(name, regs[name])
        for name, value in (("ss", entry["ss"]), ("sp", entry["sp"]), ("bp", entry["bp"]), ("ds", m.DS),
                            ("es", m.DS), ("cs", m.seg(0x214B)), ("eip", 0x08DD)):
            m.set_reg(name, value)
        core = cls(m, image.header, bytes(image.memory[MEM_SIZE:]), budget, [], hashlib.sha256(savestate).hexdigest())
        core._run()
        return core.wait

    def save(self):
        """Bytes holding the compressed image (the memory component now), the CPU, the seeds and the key log."""
        self._check_waiting()
        snap = self.m.snapshot()
        state = {"version": VERSION, "load": snap["load"], "regs": snap["regs"], "header": self.header.hex(),
                 "seeds": {f"{a:04X}": self.m.rd(a) for a in SEEDS}, "keys": list(self.keys),
                 "budget": self.budget, "template_sha256": self.template_sha256, "polls": self.wait.polls}
        blob = json.dumps(state).encode()
        return MAGIC + len(blob).to_bytes(4, "little") + blob + zlib.compress(snap["memory"] + self.tail, 6)

    @classmethod
    def load(cls, data):
        """A Core resumed from `save()`'s bytes, at the same wait (its `.wait`)."""
        _need_unicorn()
        if bytes(data[:4]) != MAGIC:
            raise ValueError("not a saved core")
        n = int.from_bytes(data[4:8], "little")
        state = json.loads(data[8:8 + n])
        if state["version"] != VERSION:
            raise ValueError(f"a saved core of version {state['version']}, this is {VERSION}")
        memory = zlib.decompress(data[8 + n:])
        m = Machine(memory, state["load"])
        m.restore({"memory": memory[:MEM_SIZE], "regs": state["regs"]})
        core = cls(m, bytes.fromhex(state["header"]), memory[MEM_SIZE:], state["budget"], list(state["keys"]),
                   state["template_sha256"])
        for off, value in state["seeds"].items():
            if m.rd(int(off, 16)) != value:
                raise ValueError(f"the saved seed DS:{off} does not match the saved memory")
        core.wait = core._make_wait(tuple(tuple(p) for p in state["polls"]))
        return core

    # -- playing ---------------------------------------------------------------------------------------------
    def press(self, key):
        """Answer the wait with `key`, the code 214B:08DD stores at DS:A976 (the character; an extended key's scan
        code adjusted, plus 0x64: kit screens.py), as 08DD returns it; run to the next wait and return it."""
        self._check_waiting()
        key = ord(key) if isinstance(key, str) else int(key)
        if not 0 < key <= 0xFF:
            raise ValueError(f"a key code is 1..255, not {key}")
        if key == F5_PRINT:
            raise ValueError("F5 (0xA3) prints the screen and makes 08DD read another key: not served by the core")
        m = self.m
        m.wr(KEY, key | (key << 8))                        # 0947 A976, 097C A977
        m.set_reg("eax", (m.reg("eax") & ~0xFF) | key)    # 0979: AL
        m.return_from(True, 0)                             # 0982 retf
        self.keys.append(key)
        self._run()
        return self.wait

    def memory(self):
        """The guest memory now (1 MiB and the HMA)."""
        return self.m.read(0, MEM_SIZE)

    def memory_sha256(self):
        return hashlib.sha256(self.memory()).hexdigest()

    def memory_component(self):
        """The memory now in the form the kit's Image reads (the savestate's Memory component)."""
        return self.header + self.memory() + self.tail

    # -- the run ------------------------------------------------------------------------------------------------
    def _check_waiting(self):
        if self.stopped is not None:
            raise CoreError(f"the core stopped and runs no further: {self.stopped}")
        if self.wait is None:
            raise CoreError("the original is not waiting for a key")

    def _hooks(self):
        from unicorn import UC_HOOK_INTR
        self.m.at(KEYPRESSED, self._on_keypressed)
        self.m.at(READKEY, self._on_readkey)
        self.m.uc.hook_add(UC_HOOK_INTR, self._on_interrupt)

    def _on_keypressed(self, replay):
        """214B:0723, "key pressed?": no key (the core gives a key only at a read), as 0723 returns it (AL 0)."""
        m = self.m
        site = m.where(m.stack_word(2), m.stack_word(0))
        self._polls[site] = self._polls.get(site, 0) + 1
        m.set_reg("ax", m.reg("ax") & 0xFF00)
        m.return_from(True, 0)

    def _on_readkey(self, replay):
        if self.m.rd(PUSHED_BACK, 1):
            return                    # 08E3: a pushed-back key is read without waiting: the guest's code runs
        self.m.stop("read")

    def _on_interrupt(self, uc, number, data):
        m = self.m
        cs, ip = m.reg("cs"), m.reg("ip")
        at = ip - 2 if m.read(cs * 16 + ((ip - 2) & 0xFFFF), 2) == bytes([0xCD, number]) else ip
        if m.error is None:
            m.error = InterruptError(number, m.reg("ax"), self._pc(cs, at & 0xFFFF), self._text())
        uc.emu_stop()

    def _pc(self, cs, ip):
        return f"{self.m.where(cs, ip)} (CS:IP {cs:04X}:{ip:04X})"

    def _text(self):
        return decode_text(self._screen())

    def _screen(self):
        return self.m.read(self.m.far(SCREEN_PTR), ROWS * COLS * 2)

    def _run(self):
        m = self.m
        self.wait, self._polls = None, {}
        m.stop_reason, m.error = None, None
        m._resume_lin = None          # the kit's replay marker: the core never resumes at a hooked instruction
        try:
            m.uc.emu_start(m.pc(), END, count=self.budget)
        except _machine.UcError as e:
            self.stopped = CoreError(f"the emulator stopped at {self._pc(m.reg('cs'), m.reg('ip'))}: {e}\n"
                                     f"{self._text()}")
            raise self.stopped from e
        if m.error is not None:
            err, m.error = m.error, None
            self.stopped = err
            raise err
        if m.stop_reason != "read":
            self.stopped = BudgetExceeded(self.budget, self._pc(m.reg("cs"), m.reg("ip")), self._text())
            raise self.stopped
        self.wait = self._make_wait(tuple(sorted(self._polls.items())))

    def _make_wait(self, polls):
        m = self.m
        site = m.where(m.stack_word(2), m.stack_word(0))
        screen = self._screen()
        return KeyWait(site=site, text=decode_text(screen), screen=screen, state=StateView(self.memory_component()),
                       polls=polls,
                       core=self)


def _need_unicorn():
    if _machine.Uc is None:
        raise ModuleNotFoundError("goal2.core runs the original under the unicorn package, which is not installed: "
                                  "pip install -e '.[watched]' (unicorn 2.1.4)")
