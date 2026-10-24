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
- [confirmed: F032 (proposed), E038-r0001, goal2-archaeology #368; docs/assumptions.md NG-7, NG-8] From the title's
  key read to the first manager menu of a new game the original makes no interrupt but INT 21h AH=3Dh, ten AH=3Fh
  and AH=3Eh on GOAL.DAT, through MsDos 235C:0000 and Intr 235C:000B, and INT 21h AH=2Ch at 23E4:11D9 (the seed).
  Intr (seg_235C_01.asm 000B-0044) pushes the flags and a return to 235C:0045, loads the registers from the record
  (AX BX CX DX BP SI DI DS ES Flags) and enters the vector's handler by `retf`, with no `int` instruction; MsDos
  (0000-000A) pushes the vector 21h under its own arguments and falls through into Intr. The core serves them at
  Intr's entry: the record's far pointer and the vector are on the stack, the record is written back as 235C:0045
  would, and the call returns `retf 6` (E038's trace.py, which reached DOSBox-X's manager menu byte for byte).
- [confirmed: F033 (proposed), E039, goal2-archaeology #371; docs/assumptions.md NG-9, NG-10] The program's only DOS
  date read is the `int 21h` (AH=2Ah) at 235C:0071 in GetDate, before the title; e039-r0005-date-call.sav stops on
  it. Answered as DOS does (CX year, DH month, DL day, AL weekday, 0 Sunday) and continued at 235C:0073, it runs
  to the title's key read 1771:085F with no other interrupt: "key pressed?" polls and speaker port I/O only.

R1, how the loop is entered [derived: the four claims above]: the template's CPU is inside the BIOS's INT 16h, called
by 08DD through Intr. The core finds Intr's far return 214B:0904 on the template's own stack, checks the three
argument words 08DD pushed before it, and rebuilds 08DD's entry from its prologue: SP = 08DD's BP + 2, BP = the
saved BP, CS:IP = 214B:08DD, DS = ES = the program's data segment (DS:A923's segment, load + 0x2581). Every return
address above is the guest's own; no byte of guest memory is written but the text page (below). E006-r0001's chain:
08DD <- 1771:28F0 (the country browser 1771:26B9, "team info") <- 000E:767D (main_menu_loop 000E:7439,
annotations/routines.tsv) <- 0000:00C6.
"""
from __future__ import annotations

import datetime
import hashlib
import io
import json
import struct
import zipfile
import zlib
from contextlib import contextmanager
from dataclasses import dataclass, field
from pathlib import Path

from goal2.core import screens as _screens
from goal2.engine.original_match import machine as _machine
from goal2.engine.original_match.image import Image, MEM_BASE, GOAL_DS_PARAGRAPH
from goal2.engine.original_match.machine import Machine, MEM_SIZE, REGS
from goal2.engine.original_match.match import KEYPRESSED, READKEY, PUSHED_BACK, KEY, SCREEN_PTR, SEED

VERSION = 3                   # 2 (T106): the DOS time and date; 3 (T108): a wait at a poll and the polls that stop
#                               (a version 1 or 2 save loads with the defaults)
MAGIC = b"G2C1"
KEY_AHEAD = 0xA977            # 08DD 097C: the last key read
SEEDS = (SEED, 0x7B64)        # F004: DS:7B62 (CX of INT 21h AH=2Ch, the main RNG word), DS:7B64 (DX)
F5_PRINT = 0xA3               # 08DD 095C-0964: F5 (scan 0x3F + 0x64) prints the screen and reads another key
INTR_RETURN = ("214B", 0x0904)   # 08DD's call far 235C:000B (Intr) at 08FF returns here
READKEY_LOCALS, INTR_ARGS, INT16 = 0x14, 6, 0x16
STACK_SEARCH = 0x200          # bytes above SS:SP searched for Intr's return
END = 1 << 21                 # an address no 16-bit CS:IP reaches: runs stop only at a read, the budget or an error
DEFAULT_BUDGET = 10_000_000_000   # [designed] instructions between two reads (a watched first half: 3e9..4e9, T100)
# [confirmed: seg_235C_01.asm, F032] Turbo Pascal's MsDos and Intr, and Intr's register record
MSDOS, INTR = "235C:0000", "235C:000B"
RECORD = ("AX", "BX", "CX", "DX", "BP", "SI", "DI", "DS", "ES", "FLAGS")
CARRY = 0x0001
DOS_INT = 0x21
GET_DATE, GET_TIME, OPEN, CLOSE, READ = 0x2A, 0x2C, 0x3D, 0x3E, 0x3F
# [confirmed: F033, NG-9, NG-10] the date call of e039-r0005-date-call.sav: `int 21h` at GetDate 235C:0071, AH 2Ah
DATE_CALL, DATE_RETURN = ("235C", 0x0071), 0x0073
DOS_YEARS = (1980, 2099)      # [confirmed: NG-9] the years DOS's AH=2Ah returns; the game checks none
# [designed: T106] The DOS time a core answers when the caller declares none: 10:00:00.00, the hour E038 and E039 set.
DEFAULT_DOS_TIME = (10, 0, 0, 0)
DATA_NAME = "GOAL.DAT"        # [confirmed: F032] the only file the new game opens (1771:018A, the name at 1771:0181)
FIRST_HANDLE = 5              # [derived: F032, E038's trace] DOS's first free handle after the five standard ones
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
    """The original asked for an interrupt (BIOS or DOS) the core does not serve: it stops at the first. `number` the
    vector, `ah` the function, `via` how it came ('int', 'Intr' or 'MsDos'), `reason` why it is refused."""

    def __init__(self, number, ax, pc, text, via="int", reason=""):
        self.number, self.ax, self.pc, self.text, self.via, self.reason = number, ax, pc, text, via, reason
        self.ah = ax >> 8
        why = reason or ("the core serves INT 21h AH=2Ch by `int`, and INT 21h AH=3Dh/3Fh/3Eh on GOAL.DAT through "
                         "Intr/MsDos, only")
        super().__init__(f"the original called INT {number:02X}h AH={self.ah:02X}h (AX {ax:04X}, by {via}) at {pc}: "
                         f"{why}\n{text}")


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


def timed_taker_entry(memory, load, regs):
    """[derived:214B:1E09/CC2E/CC7B; confirmed:T88/T89] Validate a live delay, never search stale reads.

    Only instructions with the delay's eight-byte local frame still allocated are accepted. Registers,
    including scratch ES and branch flags, and every local/counter remain the saved native values.
    """
    instructions = (0x1E0F,0x1E13,0x1E15,0x1E18,0x1E1B,0x1E1E,0x1E21,0x1E23,0x1E26,
                    0x1E28,0x1E2B,0x1E2D,0x1E30,0x1E33,0x1E37,0x1E3B,0x1E3E,0x1E40,
                    0x1E44,0x1E46,0x1E4A,0x1E4C,0x1E4F,0x1E52,0x1E54)
    if regs['CS'] != ((load+0x214B)&0xFFFF) or (regs['EIP']&0xFFFF) not in instructions:return False
    ds=(load+GOAL_DS_PARAGRAPH)&0xFFFF;bp=regs['EBP']&0xFFFF
    if regs['DS'] != ds or (regs['ESP']&0xFFFF) != ((bp-8)&0xFFFF):return False
    f=_screens.Frame(lambda a,n:bytes(memory[a:a+n]),load,ds,regs['SS'],bp)
    if f.far_caller(bp)!='0791:CC65' or f.word(bp,6)!=10:return False
    waiting=f.up(bp);selector=f.up(waiting)
    if (waiting!=bp+12 or selector!=waiting+20 or selector+8>=0x10000
            or f.near_caller(waiting)!=0xCED9 or f.word(waiting,4)!=1000):return False
    return _screens._taker(f,selector)==_screens.TAKER_SELECT


class UnknownScreen(CoreError):
    """The original reads or polls a key at a site the screen table (goal2/core/screens.py) does not know, or knows
    for other screens than the one the original's frames and memory show: the core stops rather than guess."""

    def __init__(self, site, text, poll=False):
        self.site, self.text, self.poll = site, text, poll
        what = "polls for a key" if poll else "reads a key"
        super().__init__(f"the original {what} at {site}, a screen the table does not know\n{text}")


@dataclass(frozen=True)
class PassedScreen:
    """A polled screen passed between two waits: its `kind`, the `polls` it answered, the `text` page at its first
    poll, and the queued `keys` the original read there."""
    kind: str
    polls: int
    text: str = field(repr=False)
    keys: tuple = ()


class _WaitImage(Image):
    """[designed: T116] The kit's readers over an immutable kept snapshot, with the already known load segment.

    Core validated the image when it started. Reads need neither another 16 MiB copy nor a DOS MCB scan per pose.
    The full component, including high memory, remains available to the inherited memory/hash readers.
    """
    def __init__(self, component, load):
        self.header = component[:MEM_BASE]
        self.memory = memoryview(component)[MEM_BASE:]
        self.load = load
        self.DS = load + GOAL_DS_PARAGRAPH


class StateView:
    """A read-only view of the original's memory at a wait, through the kit's `Image` (its record readers)."""

    _READERS = ("rd", "far", "rd_far", "players", "countries", "squad", "managed_countries", "fixture_index",
                "year", "name", "sha256", "memory_component")

    def __init__(self, memory_component, load=None):
        self._component = memory_component      # immutable bytes: the memory at the wait
        self._load = load
        self._cached = None

    @property
    def _image(self):
        if self._cached is None:
            self._cached = (Image.from_memory_component(self._component) if self._load is None
                            else _WaitImage(self._component, self._load))
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
    the memory through the kit's Image, `polls` the "key pressed?" polls answered since the last wait, per site;
    `kind` the screen kind (goal2/core/screens.py), `view` its cursor or selection read from memory, `passed` the
    polled screens passed since the last wait (PassedScreen, in order)."""
    site: str
    text: str
    screen: bytes = field(repr=False)
    state: StateView = field(repr=False, compare=False)
    polls: tuple = ()
    core: "Core" = field(default=None, repr=False, compare=False)
    kind: str = None
    view: dict = field(default_factory=dict, hash=False)
    passed: tuple = ()
    poll: bool = False          # [T108] the original is at a poll of a kind the core stops at (Core.stop_at)


class Core:
    """The original's game running from a main-screen savestate. `Core.start(savestate)` gives the first KeyWait
    (its `.core` is the Core); `press(key)` answers the wait; `save()` and `Core.load(blob)` stop and resume it."""

    def __init__(self, m, header, tail, budget, keys, template_sha256, dos_time=DEFAULT_DOS_TIME, date=None,
                 data=None):
        self.m, self.header, self.tail = m, header, tail
        self.budget, self.keys, self.template_sha256 = budget, keys, template_sha256
        self.dos_time = _dos_time(dos_time)   # INT 21h AH=2Ch's answer, an input (never written into memory)
        self.date = None if date is None else tuple(date)   # the DOS date boot() answered, kept in the save
        self.data = None if data is None else str(data)      # the player's GOAL.DAT, read when the original opens it
        self.files = {}               # DOS handle -> [bytes, position]: GOAL.DAT while the original has it open
        self._via = None              # 'MsDos' while MsDos falls through into Intr
        self.stopped = None           # why the core can run no further (an error it raised)
        self._polls = {}
        self._passed = []             # [kind, polls, text, [keys]] since the last wait
        self.queued = []              # [(kind, key)]: keys for the next polls of their kinds (queue())
        self.pending = None           # (kind, key): a poll said it waits; the original's next read takes it
        self.stops = set()            # [T108] polled kinds whose polls are waits (stop_at)
        self._passed_at_poll = None   # [T108] a key pressed at a poll wait, until the original's read takes it
        self.released = None          # [T108] the polled kind let pass (release) until a poll of another kind
        self.wait = None
        self._live_frames = False     # [T116] temporary presentation batching; never a guest or save setting
        self._hooks()

    # -- starting and resuming -----------------------------------------------------------------------------
    @classmethod
    def start(cls, savestate, *, budget=DEFAULT_BUDGET, dos_time=DEFAULT_DOS_TIME, goal_dat=None):
        """Run the original from a savestate stopped at one of its key reads (E006-r0001, the main screen of a new
        game; E038-r0001's title) to its first key read; returns that KeyWait. `dos_time` (hours, minutes, seconds,
        hundredths) is what INT 21h AH=2Ch answers; `goal_dat` the path of the player's GOAL.DAT, opened only when the
        original opens it (a new game, F032).

        [confirmed:T88/T89; designed:T120] The observed CC7B role2/5 delay inputs are another validated entry:
        restore their actual CPU and locals, run the remaining delay and stop at the selector poll. They are not
        BIOS key reads and must never be normalized into08DD or restarted at CC7B.
        """
        _need_unicorn()
        savestate = bytes(savestate)
        image = _image(savestate)
        regs = cpu_state(savestate)
        timed = timed_taker_entry(image.memory, image.load, regs)
        entry = None if timed else read_entry(image.memory, image.load, regs)
        if not timed and regs['CS'] != 0xF000:
            raise CoreError("the savestate is not stopped in a current BIOS key read or supported CC7B delay")
        m = Machine(image.memory, image.load)
        m.write(TEXT_PAGE, text_page(savestate))
        for name in REGS:
            if name in regs:
                m.set_reg(name, regs[name])
        if not timed:
            for name, value in (("ss", entry["ss"]), ("sp", entry["sp"]), ("bp", entry["bp"]), ("ds", m.DS),
                                ("es", m.DS), ("cs", m.seg(0x214B)), ("eip", 0x08DD)):
                m.set_reg(name, value)
        core = cls(m, image.header, bytes(image.memory[MEM_SIZE:]), budget, [], hashlib.sha256(savestate).hexdigest(),
                   dos_time=dos_time, data=goal_dat)
        if timed or (entry is not None and m.where(*entry['site'])=='0791:CF3A'):
            core.stop_at(_screens.TAKER_SELECT)
        core._run()
        return core.wait

    @classmethod
    def boot(cls, state, date, *, budget=DEFAULT_BUDGET, dos_time=DEFAULT_DOS_TIME, goal_dat=None, title_key=None):
        """The second entry kind, resume at a DOS call (NG-10): from a state stopped at the program's date call
        (e039-r0005-date-call.sav: CS:IP at 235C:0071, the `int 21h` not executed, AH 2Ah), answer it with `date`
        (year, month, day) as DOS does (CX year, DH month, DL day, AL weekday, 0 Sunday), continue at 235C:0073 and
        run to the first key read, the title's (1771:085F); returns that KeyWait. The date is an input to the
        interrupt and is kept in the core save; no byte of memory is written for it. [confirmed: NG-9] the year goes
        to DS:A9FD and a new game's start year is year + 1, rounded up to even.

        `title_key`: a key the player presses while the title's tune plays (a 'title-tune' poll, screens.py): the tune
        ends at the first poll and the title's read takes the key, so boot returns the wait after the title. [designed:
        T106] The desktop boots so (the tune is about a minute under Unicorn). [derived: measured by
        goal2/tests/test_core_new_game_t106.py] Its new game then differs from one after the whole tune only in the
        tune's own counters, DS:7966 and DS:7968."""
        _need_unicorn()
        state = bytes(state)
        image = _image(state)
        regs = cpu_state(state)
        year, month, day = (int(x) for x in date)
        if not DOS_YEARS[0] <= year <= DOS_YEARS[1]:
            raise ValueError(f"DOS answers the years {DOS_YEARS[0]}..{DOS_YEARS[1]}, not {year} (NG-9)")
        seg = (image.load + int(DATE_CALL[0], 16)) & 0xFFFF
        at = seg * 16 + DATE_CALL[1]
        if (regs["CS"], regs["EIP"] & 0xFFFF) != (seg, DATE_CALL[1]) or bytes(image.memory[at:at + 2]) != b"\xcd\x21" \
                or (regs["EAX"] >> 8) & 0xFF != GET_DATE:
            raise CoreError(f"the state is not stopped at the date call {DATE_CALL[0]}:{DATE_CALL[1]:04X} (int 21h, "
                            f"AH 2Ah; NG-10): CPU at {regs['CS']:04X}:{regs['EIP'] & 0xFFFF:04X}, AX "
                            f"{regs['EAX'] & 0xFFFF:04X}")
        m = Machine(image.memory, image.load)
        m.write(TEXT_PAGE, text_page(state))
        for name in REGS:
            if name in regs:
                m.set_reg(name, regs[name])
        for name, value in date_registers(regs, (year, month, day)).items():
            m.set_reg(name, value)
        m.set_reg("eip", DATE_RETURN)
        core = cls(m, image.header, bytes(image.memory[MEM_SIZE:]), budget, [], hashlib.sha256(state).hexdigest(),
                   dos_time=dos_time, date=(year, month, day), data=goal_dat)
        if title_key is not None:
            core.queue("title-tune", title_key)
        core._run()
        return core.wait

    def save(self):
        """Bytes holding the compressed image (the memory component now), the CPU, the seeds and the key log."""
        self._check_waiting()
        if self.files:
            raise CoreError("the original has GOAL.DAT open: a core is saved only between its file reads")
        snap = self.m.snapshot()
        state = {"version": VERSION, "dos_time": list(self.dos_time),
                 "date": None if self.date is None else list(self.date), "load": snap["load"], "regs": snap["regs"], "header": self.header.hex(),
                 "seeds": {f"{a:04X}": self.m.rd(a) for a in SEEDS}, "keys": list(self.keys),
                 "budget": self.budget, "template_sha256": self.template_sha256, "polls": self.wait.polls,
                 "passed": [[p.kind, p.polls, p.text, list(p.keys)] for p in self.wait.passed],
                 "queued": [list(q) for q in self.queued], "pending": None if self.pending is None else list(self.pending),
                 "at_poll": self.wait.poll, "stops": sorted(self.stops), "released": self.released}
        blob = json.dumps(state).encode()
        return MAGIC + len(blob).to_bytes(4, "little") + blob + zlib.compress(snap["memory"] + self.tail, 6)

    @classmethod
    def load(cls, data, *, goal_dat=None):
        """A Core resumed from `save()`'s bytes, at the same wait (its `.wait`), with its DOS time and date.
        `goal_dat`: the player's GOAL.DAT, if the original is to open it again."""
        _need_unicorn()
        if bytes(data[:4]) != MAGIC:
            raise ValueError("not a saved core")
        n = int.from_bytes(data[4:8], "little")
        state = json.loads(data[8:8 + n])
        if state["version"] not in (1, 2, VERSION):
            raise ValueError(f"a saved core of version {state['version']}, this is {VERSION}")
        memory = zlib.decompress(data[8 + n:])
        m = Machine(memory, state["load"])
        m.restore({"memory": memory[:MEM_SIZE], "regs": state["regs"]})
        core = cls(m, bytes.fromhex(state["header"]), memory[MEM_SIZE:], state["budget"], list(state["keys"]),
                   state["template_sha256"], dos_time=state.get("dos_time", DEFAULT_DOS_TIME),
                   date=state.get("date"), data=goal_dat)
        for off, value in state["seeds"].items():
            if m.rd(int(off, 16)) != value:
                raise ValueError(f"the saved seed DS:{off} does not match the saved memory")
        core.queued = [tuple(q) for q in state.get("queued", [])]
        core.pending = None if state.get("pending") is None else tuple(state["pending"])
        core.stops = set(state.get("stops", ()))
        core.released = state.get("released")
        passed = tuple(PassedScreen(k, n, t, tuple(keys)) for k, n, t, keys in state.get("passed", []))
        core.wait = core._make_wait(tuple(tuple(p) for p in state["polls"]), passed, poll=state.get("at_poll", False))
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
        if self.wait.poll:
            # [T108] at a poll: 0723 says a key waits, and the original's next read takes it (as queue() gives it)
            if not _screens.KINDS[self.wait.kind].accepts(key):
                raise ValueError(f"{self.wait.kind} does not accept the key {key:#04x}")
            self.pending = (self.wait.kind, key)
            self._passed_at_poll = [self.wait.kind, 0, self.wait.text, []]
            self.m.set_reg("ax", (self.m.reg("ax") & 0xFF00) | 1)
            self.m.return_from(True, 0)
            self.keys.append(key)
            self._run()
            return self.wait
        self._answer(key)
        self.keys.append(key)
        self._run()
        return self.wait

    def queue(self, kind, key):
        """Answer the next poll of the polled screen `kind` with `key` (a code as for press()): that poll says a key
        waits and the original's next read takes it. A key the kind does not accept is refused (ValueError)."""
        if self.stopped is not None:
            raise CoreError(f"the core stopped and runs no further: {self.stopped}")
        key = ord(key) if isinstance(key, str) else int(key)
        k = _screens.KINDS.get(kind)
        if k is None or not k.polled:
            raise ValueError(f"{kind!r} is not a polled screen kind of the table")
        if not k.accepts(key):
            raise ValueError(f"{kind} does not accept the key {key:#04x}")
        self.queued.append((kind, key))

    def stop_at(self, *kinds):
        """[designed: T108] Make each poll of the polled `kinds` a wait (KeyWait.poll), so that a caller can read the
        screen's state before each key (the captain prompt's highlight): press() then answers that poll "a key
        waits" and the original's next read takes the key. A poll while a queued or announced key is in flight is
        not a wait. `stop_at()` with no kinds stops at none. Kept in the core save."""
        for kind in kinds:
            k = _screens.KINDS.get(kind)
            if k is None or not k.polled:
                raise ValueError(f"{kind!r} is not a polled screen kind of the table")
        self.stops = set(kinds)

    def release(self):
        """[designed: T108] At a poll wait (stop_at): answer "no key", as 0723 does with no key waiting, and let the
        screen pass: its next polls are not waits until a poll of another kind or a read. Returns the next wait."""
        self._check_waiting()
        if not self.wait.poll:
            raise CoreError("release() answers a poll wait (stop_at); the original is reading a key")
        self.released = self.wait.kind
        self.m.set_reg("ax", self.m.reg("ax") & 0xFF00)
        self.m.return_from(True, 0)
        self._run()
        return self.wait

    def advance(self):
        """[designed: T109] Answer this one poll with no key and run to the next wait, including another poll
        of the same kind. Unlike release(), this keeps every live poll available to the watching manager."""
        self._check_waiting()
        if not self.wait.poll:
            raise CoreError("advance() answers a poll wait; the original is reading a key")
        self.m.set_reg("ax", self.m.reg("ax") & 0xFF00)
        self.m.return_from(True, 0)
        self._run()
        return self.wait

    @contextmanager
    def live_frames(self):
        """[designed: T116; confirmed: 0791:9571–9708] Keep complete live poses, not each intermediate player poll.

        Every poll still executes and queued keys/read waits/other decisions still stop normally. The regular
        stop_at/advance API keeps its single-poll behavior outside this bounded desktop operation.
        """
        previous, self._live_frames = self._live_frames, True
        try:
            yield
        finally:
            self._live_frames = previous

    def unqueue(self, kind):
        """[designed: T108] Drop the keys queued for `kind` that no poll has taken; returns them."""
        dropped = [key for k, key in self.queued if k == kind]
        self.queued = [(k, key) for k, key in self.queued if k != kind]
        return dropped

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
        self.m.at(MSDOS, self._on_msdos)
        self.m.at(INTR, self._on_intr)
        self.m.uc.hook_add(UC_HOOK_INTR, self._on_interrupt)
        # [confirmed: NG-10] Speaker port I/O (OUT 42h/43h, IN/OUT 61h) is ignored: Unicorn drops an OUT and reads 0
        # from an IN without a port hook, as E039's trace answered them.

    def _on_keypressed(self, replay):
        """214B:0723, "key pressed?": no key (the core gives a key only at a read), as 0723 returns it (AL 0)."""
        m = self.m
        site = m.where(m.stack_word(2), m.stack_word(0))
        self._polls[site] = self._polls.get(site, 0) + 1
        kind = _screens.identify(site, self._frame())
        if kind is None:
            raise UnknownScreen(site, self._text(), poll=True)
        if self.released is not None and kind != self.released:
            self.released = None
        complete = (not self._live_frames or kind != 'match-live'
                    or _screens.view(site, self._frame()).get('slot') in (22, None))
        if (complete and kind in self.stops and self.pending is None and kind != self.released
                and not any(k == kind for k, _ in self.queued)):
            m.stop("poll")           # [T108] a wait at the poll: press() answers it
            return
        if not self._passed or self._passed[-1][0] != kind:
            self._passed.append([kind, 0, self._text(), []])
        self._passed[-1][1] += 1
        has = 0
        if self.pending is not None:
            has = int(self.pending[0] == kind)     # the key still waits for the read of the screen that saw it
        else:
            for i, (k, key) in enumerate(self.queued):
                if k == kind:
                    self.pending, has = self.queued.pop(i), 1
                    break
        m.set_reg("ax", (m.reg("ax") & 0xFF00) | has)
        m.return_from(True, 0)

    def _on_readkey(self, replay):
        if self.m.rd(PUSHED_BACK, 1):
            return                    # 08E3: a pushed-back key is read without waiting: the guest's code runs
        self.released = None
        if self.pending is not None:  # a poll said a queued key waits: the read takes it, as press() answers
            kind, key = self.pending
            self.pending = None
            self._answer(key)
            if self._passed_at_poll is not None:
                self._passed_at_poll = None      # [T108] pressed at a poll wait: logged by press, not passed
            else:
                self._passed[-1][3].append(key)
            return
        self.m.stop("read")

    def _answer(self, key):
        m = self.m
        m.wr(KEY, key | (key << 8))                        # 0947 A976, 097C A977
        m.set_reg("eax", (m.reg("eax") & ~0xFF) | key)    # 0979: AL
        m.return_from(True, 0)                             # 0982 retf

    def _frame(self):
        m = self.m
        return _screens.Frame(m.read, m.load, m.DS, m.reg("ss"), m.reg("bp"))

    def _on_interrupt(self, uc, number, data):
        """An `int` instruction. [confirmed: F032, NG-7] INT 21h AH=2Ch (Randomize 23E4:11D7, the `int` at 11D9) is
        answered with the declared DOS time, CH:CL hours and minutes, DH:DL seconds and hundredths (23E4:11D7 then
        stores CX at DS:7B62 and DX at DS:7B64, F004); every other one stops the core (InterruptError)."""
        m = self.m
        cs, ip = m.reg("cs"), m.reg("ip")
        at = ip - 2 if m.read(cs * 16 + ((ip - 2) & 0xFFFF), 2) == bytes([0xCD, number]) else ip
        ax = m.reg("ax")
        if number == DOS_INT and ax >> 8 == GET_TIME and m.error is None:
            h, mi, sec, cs100 = self.dos_time
            m.set_reg("cx", (h << 8) | mi)
            m.set_reg("dx", (sec << 8) | cs100)
            return
        if m.error is None:
            m.error = InterruptError(number, ax, self._pc(cs, at & 0xFFFF), self._text())
        uc.emu_stop()

    def _on_msdos(self, replay):
        """235C:0000 MsDos(var regs): it pushes the vector 21h and falls through into Intr, served there."""
        self._via = "MsDos"

    def _on_intr(self, replay):
        """235C:000B Intr(n, var regs), at its entry: the stack holds the far return, the record's offset and segment
        and the vector (F032). The request is served into the record, which is written back, and Intr returns
        `retf 6`; one the core does not serve stops it (InterruptError), the record untouched."""
        m = self.m
        via, self._via = self._via or "Intr", None
        number = m.stack_word(8) & 0xFF
        rec = m.stack_word(6) * 16 + m.stack_word(4)
        regs = dict(zip(RECORD, struct.unpack("<10H", m.read(rec, 20))))
        pc = self._pc(m.stack_word(2), m.stack_word(0)) + f", through {via}"
        out = self._serve_dos(number, regs, pc, via)
        m.write(rec, struct.pack("<10H", *(out[k] for k in RECORD)))
        m.return_from(True, 6)

    def _serve_dos(self, number, regs, pc, via):
        """INT 21h AH=3Dh (open GOAL.DAT), 3Fh (read) and 3Eh (close), as DOS answers them [confirmed: F032, NG-7,
        E038's trace: the handle 5, AX the count read, the carry clear]; anything else raises InterruptError. The
        record's Flags are the CPU's flags with the carry clear, as Intr's 235C:0045 stores them (#327)."""
        ah, out = regs["AX"] >> 8, dict(regs)

        def refuse(reason=""):
            raise InterruptError(number, regs["AX"], pc, self._text(), via=via, reason=reason)
        if number != DOS_INT or ah not in (OPEN, READ, CLOSE):
            refuse()
        if ah == OPEN:
            raw = self.m.read(regs["DS"] * 16 + regs["DX"], 80).split(b"\0")[0].decode("cp437")
            name = raw.replace("/", "\\").rsplit("\\", 1)[-1].rsplit(":", 1)[-1]
            if name.upper() != DATA_NAME:
                refuse(f"the core opens {DATA_NAME} only, not {raw!r}")
            if self.data is None:
                refuse(f"the original opens {DATA_NAME} and no path to it was given (goal_dat=)")
            self.files[FIRST_HANDLE] = [_goal_dat(self.data), 0]
            out["AX"] = FIRST_HANDLE
        elif regs["BX"] not in self.files:
            refuse(f"handle {regs['BX']} is not GOAL.DAT's")
        elif ah == READ:
            f = self.files[regs["BX"]]
            chunk = f[0][f[1]:f[1] + regs["CX"]]
            self.m.write(regs["DS"] * 16 + regs["DX"], chunk)
            f[1] += len(chunk)
            out["AX"] = len(chunk)
        else:
            del self.files[regs["BX"]]
        # [confirmed: seg_235C_01.asm 0045, #327] Intr's return path stores the CPU's flags (pushf) into the record:
        # the flags now, with the carry DOS clears on success.
        out["FLAGS"] = self.m.reg("eflags") & 0xFFFF & ~CARRY
        return out

    def _pc(self, cs, ip):
        return f"{self.m.where(cs, ip)} (CS:IP {cs:04X}:{ip:04X})"

    def _text(self):
        return decode_text(self._screen())

    def _screen(self):
        return self.m.read(self.m.far(SCREEN_PTR), ROWS * COLS * 2)

    def _run(self):
        m = self.m
        self.wait, self._polls, self._passed = None, {}, []
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
        if m.stop_reason not in ("read", "poll"):
            self.stopped = BudgetExceeded(self.budget, self._pc(m.reg("cs"), m.reg("ip")), self._text())
            raise self.stopped
        passed = tuple(PassedScreen(k, n, t, tuple(keys)) for k, n, t, keys in self._passed)
        self.wait = self._make_wait(tuple(sorted(self._polls.items())), passed, poll=m.stop_reason == "poll")

    def _make_wait(self, polls, passed=(), poll=False):
        m = self.m
        site = m.where(m.stack_word(2), m.stack_word(0))
        screen = self._screen()
        frame = self._frame()
        kind = _screens.identify(site, frame)
        if kind is None:
            self.stopped = UnknownScreen(site, decode_text(screen))
            raise self.stopped
        return KeyWait(site=site, text=decode_text(screen), screen=screen, state=StateView(self.memory_component(), m.load),
                       polls=polls, core=self, kind=kind, view=_screens.view(site, frame), passed=passed, poll=poll)


def _image(savestate):
    """The kit's Image of a savestate, refused (ValueError) unless it holds the GOAL.EXE the kit was made on."""
    image = Image.from_savestate(savestate)
    problems = image.build_problems()
    if problems:
        raise ValueError("the image does not hold the GOAL.EXE the kit was made on; it differs in: "
                         + "; ".join(problems))
    return image


def date_registers(regs, date):
    """The registers DOS's INT 21h AH=2Ah sets for `date` (year, month, day), from the state's `regs`: CX the year,
    DH the month, DL the day, AL the weekday (0 Sunday) [confirmed: F033, NG-9]; the upper halves of ECX, EDX and EAX
    and AH are kept, as DOS writes the 16- and 8-bit registers only (#327). F033: the program drops the weekday."""
    year, month, day = date
    weekday = datetime.date(year, month, day).isoweekday() % 7
    return {"ecx": (regs["ECX"] & ~0xFFFF) | year, "edx": (regs["EDX"] & ~0xFFFF) | (month << 8) | day,
            "eax": (regs["EAX"] & ~0xFF) | weekday}


def _dos_time(t):
    h, m, s, cs = (int(x) for x in t)
    if not (0 <= h < 24 and 0 <= m < 60 and 0 <= s < 60 and 0 <= cs < 100):
        raise ValueError(f"a DOS time is (hours 0..23, minutes 0..59, seconds 0..59, hundredths 0..99), not {t}")
    return (h, m, s, cs)


def _goal_dat(path):
    """The player's GOAL.DAT, read at run time from the path given (never from the repository), checked against
    the released file's SHA-256 (goal2/data/goaldat.py, F002 R001)."""
    from goal2.data import goaldat
    try:
        data = Path(path).read_bytes()
    except OSError as e:
        raise CoreError(f"cannot read GOAL.DAT at {path}: {e}") from e
    if hashlib.sha256(data).hexdigest() != goaldat.SHA256:
        raise CoreError(f"{path} is not the released GOAL.DAT (sha256 {hashlib.sha256(data).hexdigest()})")
    return data


def _need_unicorn():
    if _machine.Uc is None:
        raise ModuleNotFoundError("goal2.core runs the original under the unicorn package, which is not installed: "
                                  "pip install -e '.[watched]' (unicorn 2.1.4)")
