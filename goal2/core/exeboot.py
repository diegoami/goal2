"""The core's third entry kind (T222): the date-call state built from the player's own GOAL.EXE.

[designed: owner, 2026-11-13, #705] v0.1 ships the core route with the player supplying GOAL.EXE and GOAL.DAT. A new
game used to start from `e039-r0005-date-call.sav`, an emulator state recorded with GOAL.EXE in memory, which a
player cannot make and which never ships (CLAUDE.md rule 14). `date_call(exe)` makes that state from GOAL.EXE's bytes
alone: a minimal DOS in a bare 1 MiB machine, the load module at the recording's load segment, run from the MZ entry
to the program's date call `235C:0071`, where `Core.boot_exe` (runner.py) answers the date as `Core.boot` does.

Why a module of its own [designed: T222]: the boot's DOS and BIOS answers serve the boot only (docs/core.md
"Refusals"). They run on an engine of their own, which is dropped at the date call; the Core then starts a Machine
from the memory and registers this module returns, with only its own hooks. No answer of this module's survives into
the game.

Evidence (goal2-archaeology static/goal-exe at 7fbfd2e9 unless named; the listing's addresses are paragraphs of the
load module):
- [confirmed: goal2/engine/original_match/build.py:3] The registered GOAL.EXE: packed SHA-256 a6928b0b...d3664. Its MZ
  header: LZEXE 0.91 (`LZ91` at offset 28), no relocation entries, entry 000E:15F1, stack 2DE7:0080, 2 header
  paragraphs, 181 pages, maxalloc 6990h.
- [confirmed: e039-r0005-date-call.sav's DOS memory blocks, read by tests/test_core_exe_boot_t222.py] DOSBox-X loaded
  the program at segment 0823 (PSP 0813, its memory block 'M' at 0812 owned by 0813, named GOAL, of 803Eh paragraphs,
  then a free block). 803Eh = 10h (the PSP) + 169Eh (the 181 pages less the header, in paragraphs) + 6990h (maxalloc):
  DOS sizes the block by the header's page count, not by the last page's byte count. [derived] The block's top, the
  PSP's word +2 (8851h), is what 23E4:002B-0032 turns into DS:7B4A (the top less 1000h); DOS's own rule gives it.
- [confirmed: seg_23E4_01.asm 0035-0071] The system unit saves 18 vectors at DS:ACC0 (INT 21h AH=35h) and sets
  INT 00h, 23h, 24h and 3Fh (AH=25h); [confirmed: seg_2382_01.asm 0030-0098, 00E7-012E, 0608] the CRT unit asks the
  video mode (INT 10h AH=0Fh), the font (AX=1130h, BH 0: DL the rows less one, CX the points), the attribute at the
  cursor (AH=08h: DS:AAB2 and DS:AABC take it, bit 7 cleared), calibrates its delay on the BIOS tick 0040:006C
  (DS:AAB8 = (not CX) / 37h after the loop 02BE: `cmp al, es:[di]; jne; loop`, CX from FFFFh) and sets INT 1Bh.
- [derived: feasibility probe, #705] On the way to the date call it asks INT 21h AH=35h x18, 25h x5, 44h x1 and
  INT 10h AH=0Fh x2, 1130h x1, 08h x1, 02h x2; nothing else. Anything else stops the boot (InterruptError): the core
  never guesses.
"""
from __future__ import annotations

import hashlib
import struct
from dataclasses import dataclass
from pathlib import Path

from goal2.engine.original_match.machine import MEM_SIZE, REGS

# [confirmed: goal2/engine/original_match/build.py:3] the registered GOAL.EXE, packed
SHA256 = "a6928b0bb7cda0303ac8daf8690efc56ef1792dddaccb5c6f3d85af1f68d3664"
EXE_NAME = "GOAL.EXE"
BOOT_KIND = "goal-exe"          # [designed: T222] the core save's template_sha256 for a GOAL.EXE boot: kind:digest
# [designed: T222; confirmed: the load segment of every E039 state] Where the boot puts the program: the recording's
# place, so that the booted memory and the recorded one compare at the same addresses.
PSP = 0x0813
LOAD = PSP + 0x10
ENV = 0x07CA                    # [designed] the environment block, in a block of its own below the program's
ENV_TEXT = b"COMSPEC=C:\\COMMAND.COM\x00\x00\x01\x00C:\\GOAL.EXE\x00"
TOP = 0xA000                    # [designed] 640 KiB of conventional memory, no upper memory
# [confirmed: seg_235C_01.asm 006C-0071, F033] the date call: `mov ah, 2Ah; int 21h` at GetDate 235C:0071
DATE_CALL = (0x235C, 0x0071)
GET_DATE = 0x2A
STUB_SEG = 0xF000               # [designed] the BIOS's segment: vector n points to F000:4n, `int n; iret`
TEXT_SEG, TEXT_PAGE_SIZE = 0xB800, 0x1000
BLANK = b"\x20\x07"             # [designed] a cleared mode-3 screen: space, attribute 07h (light grey on black)
# [derived: goal2-archaeology experiments/E039-start-year/derive.py (4f4bf358), which made the recording from a
# DOSBox-X state caught at load+2382:0074] The BIOS tick 0040:006C advances by one every TICK instructions: the
# nominal length of a tick at the recording's fixed `cycles=30000` (30,000 instructions a millisecond x 54.925 ms).
# Its readers in the boot are the two delay calibrations: the CRT unit's (2382:006E-007C: DS:AAB8 = (not CX) / 37h,
# 04A7h when its 65,535-pass loop sees no advance, as here) and the game's (214B:1DA7: the passes of one tick / 55
# at DS:A9FF, 10B7h here as in the recording). The tick is an input, like the date; nothing else of IRQ 0 runs.
TICK = 30000 * 54925 // 1000
BDA_TICKS = 0x46C
# [confirmed: seg_0791_24.asm F43F-F447; datarefs.tsv DS:8336 (0791:94C9, 0791:F3F2)] The count itself is an input
# too: the unit start-up 0791:F3F2 keeps its low word at DS:8336, the seed of the random numbers 0791:94C9 draws
# (214B:0688) for the watched match's sounds (0791:94E8). `bios_ticks` is the count when GOAL.EXE starts; the BIOS
# counts 1,193,182 / 65,536 ticks a second from midnight, so `ticks_at(time)` gives it for a time of day.
PIT_HZ, PIT_DIVISOR = 1193182, 65536
# [derived: the recording's FLAGS 7206h at the date call carry IOPL 3 and NT, which the program never sets; DOSBox's
# EXEC enters a program by IRET with flags 7202h] The flags, and the registers as DOS's EXEC leaves them (MS-DOS's
# convention, which DOSBox follows: AX the FCB drives' validity (0), BX 0, CX 00FFh, DX the PSP, SI the entry IP,
# DI the entry SP, BP 091Ch).
ENTRY_FLAGS = 0x7202
BUDGET = 100 * TICK            # [designed] instructions to the date call (it needs about 3 ticks)
HEADER = bytes(0x78)            # [designed] the Memory component's header: no DOSBox-X state made it; nothing reads it


@dataclass(frozen=True)
class DateCall:
    """The machine at the program's date call: `memory` (MEM_SIZE bytes), `regs` (the names of machine.REGS), the
    `load` segment, the Memory component's `header`, the `requests` the boot served, in order ((vector, AX), ...),
    and `stack_top`, the program's SP at its own entry 0000:0000 (after LZEXE's unpacking): the top of its stack."""
    memory: bytes
    regs: dict
    load: int
    header: bytes
    requests: tuple
    stack_top: int


def ticks_at(time) -> int:
    """The BIOS's tick count at the time of day `time` (hours, minutes, seconds, hundredths)."""
    h, m, sec, cs = (int(x) for x in time)
    return (((h * 60 + m) * 60 + sec) * 100 + cs) * PIT_HZ // (100 * PIT_DIVISOR)


def is_exe(data) -> bool:
    """An MZ executable (GOAL.EXE), not a DOSBox-X savestate (a zip)."""
    return bytes(data[:2]) == b"MZ"


def digest_id(exe) -> str:
    """The core save's `template_sha256` of a GOAL.EXE boot: the boot kind and GOAL.EXE's digest."""
    return f"{BOOT_KIND}:{hashlib.sha256(bytes(exe)).hexdigest()}"


def read_exe(source):
    """GOAL.EXE's bytes and the name to report: `source` a path, or bytes (named GOAL.EXE). Refused (CoreError,
    naming the file) unless it is the registered GOAL.EXE, before any instruction runs."""
    from goal2.core.runner import CoreError
    if isinstance(source, (bytes, bytearray, memoryview)):
        data, name = bytes(source), EXE_NAME
    else:
        name = str(source)
        try:
            data = Path(source).read_bytes()
        except OSError as e:
            raise CoreError(f"cannot read GOAL.EXE at {name}: {e}") from e
    got = hashlib.sha256(data).hexdigest()
    if got != SHA256:
        raise CoreError(f"{name} is not the registered GOAL.EXE (sha256 {got}, {SHA256} is needed): refused before "
                        "running it")
    return data, name


def header(exe):
    """The MZ header's fields the boot uses."""
    (magic, last, pages, nrel, paras, minalloc, maxalloc, ss, sp, _, ip, cs, _, _) = struct.unpack_from("<2s13H", exe)
    return {"pages": pages, "last": last, "relocations": nrel, "paras": paras, "minalloc": minalloc,
            "maxalloc": maxalloc, "ss": ss, "sp": sp, "ip": ip, "cs": cs}


def block_paragraphs(h):
    """[confirmed: the recording's MCB 0812, 803Eh paragraphs] DOS's block for the program: the PSP, the load module
    as the header's pages give it, and maxalloc."""
    return 0x10 + (h["pages"] * 512 - h["paras"] * 16 + 15) // 16 + h["maxalloc"]


def machine_memory(exe):
    """The bare machine before the program's first instruction: IVT, BIOS data area, DOS's memory blocks, the
    environment, the PSP, the load module and a cleared screen. Every byte is GOAL.EXE's or this function's."""
    h = header(exe)
    if h["relocations"]:
        raise ValueError("the registered GOAL.EXE has no relocation entries")
    module = exe[h["paras"] * 16:]
    mem = bytearray(MEM_SIZE)
    # IVT: vector n -> F000:4n, which holds `int n; iret` (the hook serves the `int`)
    for n in range(256):
        struct.pack_into("<HH", mem, n * 4, n * 4, STUB_SEG)
        mem[STUB_SEG * 16 + n * 4:STUB_SEG * 16 + n * 4 + 3] = bytes((0xCD, n, 0xCF))
    # BIOS data area [designed: a VGA in mode 3, 80x25, page 0, cursor at 0,0, 640 KiB]
    struct.pack_into("<H", mem, 0x410, 0x0021)      # equipment: 80x25 colour, a diskette
    struct.pack_into("<H", mem, 0x413, TOP // 64)    # KiB of conventional memory
    mem[0x449] = 3                                   # video mode
    struct.pack_into("<H", mem, 0x44A, 80)           # columns
    struct.pack_into("<H", mem, 0x44C, TEXT_PAGE_SIZE)
    struct.pack_into("<H", mem, 0x463, 0x3D4)        # CRTC port
    mem[0x484] = 24                                  # rows less one
    struct.pack_into("<H", mem, 0x485, 16)           # points
    # the screen: cleared
    mem[TEXT_SEG * 16:TEXT_SEG * 16 + 0x8000] = BLANK * 0x4000
    # DOS's memory blocks: the environment's, the program's (named GOAL, as find_load_segment reads it), free memory
    env_paras = (len(ENV_TEXT) + 15) // 16
    _mcb(mem, ENV - 1, b"M", PSP, PSP - 1 - ENV, b"")
    mem[ENV * 16:ENV * 16 + len(ENV_TEXT)] = ENV_TEXT
    assert env_paras <= PSP - 1 - ENV
    size = block_paragraphs(h)
    _mcb(mem, PSP - 1, b"M", PSP, size, b"GOAL")
    free = PSP + size
    _mcb(mem, free, b"Z", 0, TOP - free - 1, b"")
    # the PSP [designed: DOS's layout; the program reads its +2, the top of its block]
    p = PSP * 16
    mem[p:p + 2] = b"\xcd\x20"
    struct.pack_into("<H", mem, p + 2, PSP + size)
    struct.pack_into("<H", mem, p + 0x16, PSP)       # parent: itself (no COMMAND.COM)
    mem[p + 0x18:p + 0x18 + 20] = bytes((1, 1, 1, 0, 2)) + b"\xff" * 15
    struct.pack_into("<H", mem, p + 0x2C, ENV)
    struct.pack_into("<HHH", mem, p + 0x32, 20, 0x18, PSP)
    mem[p + 0x50:p + 0x53] = b"\xcd\x21\xcb"
    mem[p + 0x80:p + 0x82] = b"\x00\x0d"
    # the load module
    mem[LOAD * 16:LOAD * 16 + len(module)] = module
    return mem, h


def _mcb(mem, seg, kind, owner, size, name):
    a = seg * 16
    mem[a] = kind[0]
    struct.pack_into("<HH", mem, a + 1, owner, size)
    mem[a + 8:a + 16] = name.ljust(8, b"\0")


class _Boot:
    """The run from the MZ entry to the date call, on an engine of its own."""

    def __init__(self, exe, bios_ticks):
        from unicorn import Uc, UC_ARCH_X86, UC_MODE_16, UC_HOOK_INTR, UC_HOOK_CODE
        from unicorn import x86_const as X
        self.X = X
        mem, h = machine_memory(exe)
        struct.pack_into("<I", mem, BDA_TICKS, bios_ticks & 0xFFFFFFFF)
        self.uc = uc = Uc(UC_ARCH_X86, UC_MODE_16)
        uc.mem_map(0, MEM_SIZE)
        uc.mem_write(0, bytes(mem))
        regs = {"cs": LOAD + h["cs"], "ip": h["ip"], "ss": LOAD + h["ss"], "sp": h["sp"], "ds": PSP, "es": PSP,
                "ax": 0, "bx": 0, "cx": 0x00FF, "dx": PSP, "si": h["ip"], "di": h["sp"], "bp": 0x091C,
                "eflags": ENTRY_FLAGS}
        for name, value in regs.items():
            uc.reg_write(getattr(X, f"UC_X86_REG_{name.upper()}"), value)
        self.requests, self.error, self.at_date = [], None, False
        self.ticks = 0
        uc.hook_add(UC_HOOK_INTR, self._interrupt)
        date = ((LOAD + DATE_CALL[0]) & 0xFFFF) * 16 + DATE_CALL[1]
        uc.hook_add(UC_HOOK_CODE, self._date, begin=date, end=date)
        self.stack_top = None
        uc.hook_add(UC_HOOK_CODE, self._entry, begin=LOAD * 16, end=LOAD * 16)

    def reg(self, name):
        return self.uc.reg_read(getattr(self.X, f"UC_X86_REG_{name.upper()}"))

    def set(self, name, value):
        self.uc.reg_write(getattr(self.X, f"UC_X86_REG_{name.upper()}"), value)

    def run(self):
        from unicorn import UcError
        from goal2.core.runner import CoreError
        while not self.at_date and self.error is None and self.ticks * TICK < BUDGET:
            try:
                self.uc.emu_start(self.reg("cs") * 16 + self.reg("ip"), 1 << 21, count=TICK)
            except UcError as e:
                raise CoreError(f"GOAL.EXE's boot stopped at {self._where()}: {e}") from e
            if not self.at_date and self.error is None:
                tick = struct.unpack("<I", self.uc.mem_read(BDA_TICKS, 4))[0]
                self.uc.mem_write(BDA_TICKS, struct.pack("<I", (tick + 1) & 0xFFFFFFFF))
                self.ticks += 1
        if self.error is not None:
            raise self.error
        if not self.at_date:
            raise CoreError(f"GOAL.EXE's boot ran {BUDGET} instructions without reaching the date call; at "
                            f"{self._where()}")

    def _where(self):
        cs, ip = self.reg("cs"), self.reg("ip")
        return f"{(cs - LOAD) & 0xFFFF:04X}:{ip:04X} (CS:IP {cs:04X}:{ip:04X})"

    def _date(self, uc, address, size, data):
        """235C:0071, before its `int 21h`: the boot ends here when the program asks the date (AH 2Ah)."""
        if self.reg("cs") == (LOAD + DATE_CALL[0]) & 0xFFFF and self.reg("ax") >> 8 == GET_DATE \
                and bytes(uc.mem_read(address, 2)) == b"\xcd\x21":
            self.at_date = True
            uc.emu_stop()

    def _entry(self, uc, address, size, data):
        """The program's own entry 0000:0000, reached once LZEXE has unpacked it: its SP is the stack's top."""
        if self.stack_top is None and self.reg("cs") == LOAD:
            self.stack_top = self.reg("sp")

    def _interrupt(self, uc, number, data):
        if self.error is not None:
            uc.emu_stop()
            return
        ax = self.reg("ax")
        self.requests.append((number, ax))
        try:
            if number == 0x21:
                self._dos(ax)
            elif number == 0x10:
                self._video(ax)
            else:
                self._refuse(number, ax)
        except Exception as e:          # noqa: BLE001 - reported after emu_start returns
            self.error = e
            uc.emu_stop()

    def _refuse(self, number, ax, reason=""):
        from goal2.core.runner import InterruptError
        raise InterruptError(number, ax, self._where(), "", via="int",
                             reason=reason or "GOAL.EXE's boot serves INT 21h AH=25h/35h/44h and INT 10h AH=02h/08h/"
                                              "0Fh/1130h only (T222)")

    def _dos(self, ax):
        """INT 21h as DOS answers: 35h (ES:BX the vector), 25h (the vector set to DS:DX), 44h AL 0 (a handle's
        device information: the standard handles are the console)."""
        ah, al = ax >> 8, ax & 0xFF
        if ah == 0x35:
            off, seg = struct.unpack("<HH", self.uc.mem_read(al * 4, 4))
            self.set("bx", off)
            self.set("es", seg)
        elif ah == 0x25:
            self.uc.mem_write(al * 4, struct.pack("<HH", self.reg("dx"), self.reg("ds")))
        elif ah == 0x44 and al == 0 and self.reg("bx") <= 2:
            # [designed: T222] the console device's information word as DOS gives it (device, stdin, stdout,
            # special, not end of file): 80D3h. [confirmed: the caller 23E4:14C8-14D7] the program tests DL's bit 7
            # (a device) and overwrites AX at once (14CD).
            self.set("dx", 0x80D3)
            self.set("eflags", self.reg("eflags") & ~1)
        else:
            self._refuse(0x21, ax)

    def _video(self, ax):
        """INT 10h as a VGA BIOS answers, from the BIOS data area and the screen: 0Fh, 1130h (BH 0), 08h, 02h."""
        ah = ax >> 8
        mem = self.uc
        bh = self.reg("bx") >> 8
        if ah == 0x0F:
            mode, cols, page = mem.mem_read(0x449, 1)[0], mem.mem_read(0x44A, 1)[0], mem.mem_read(0x462, 1)[0]
            self.set("ax", (cols << 8) | mode)
            self.set("bx", (page << 8) | (self.reg("bx") & 0xFF))
        elif ax == 0x1130 and bh == 0:
            # ES:BP the font of INT 1Fh's vector, CX the points, DL the rows less one
            off, seg = struct.unpack("<HH", mem.mem_read(0x1F * 4, 4))
            self.set("es", seg)
            self.set("bp", off)
            self.set("cx", struct.unpack("<H", mem.mem_read(0x485, 2))[0])
            self.set("dx", (self.reg("dx") & 0xFF00) | mem.mem_read(0x484, 1)[0])
        elif ah == 0x08 and bh < 8:
            col, row = mem.mem_read(0x450 + 2 * bh, 2)
            cols = struct.unpack("<H", mem.mem_read(0x44A, 2))[0]
            a = TEXT_SEG * 16 + bh * TEXT_PAGE_SIZE + 2 * (row * cols + col)
            ch, attr = mem.mem_read(a, 2)
            self.set("ax", (attr << 8) | ch)
        elif ah == 0x02 and bh < 8:
            dx = self.reg("dx")
            mem.mem_write(0x450 + 2 * bh, struct.pack("<H", dx))
        else:
            self._refuse(0x10, ax)


def date_call(source, bios_ticks) -> DateCall:
    """Boot GOAL.EXE (`source`: its path or bytes) to its date call, the BIOS's tick count `bios_ticks` when it
    starts; refused before any instruction runs unless it is the registered GOAL.EXE (CoreError naming the file)."""
    exe, _ = read_exe(source)
    boot = _Boot(exe, int(bios_ticks))
    boot.run()
    regs = {name: boot.reg(name) for name in REGS}
    return DateCall(memory=bytes(boot.uc.mem_read(0, MEM_SIZE)), regs=regs, load=LOAD, header=HEADER,
                    requests=tuple(boot.requests), stack_top=boot.stack_top)
