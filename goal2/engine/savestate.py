"""Read a DOSBox-X 2024.03.01 savestate (the zip Host+S writes): the 80x25 text screen and guest memory.

Standard library only; no DOSBox-X needed, so the tests build a synthetic savestate and run in CI.
Every constant here comes from F001 ("Method", "Screen read"); copied from runtime/spike/dbx.py.
The layout is specific to DOSBox-X 2024.03.01 (F001): another version needs a new calibration.
"""
import hashlib
import zipfile
import zlib

ROWS, COLS = 25, 80
# F001: component `Vga` is one zlib stream; the text page is at stream offset 0x86024, 8 bytes per
# cell (character, attribute, 6 bytes of other planes). Calibrated on svga_s3, memsize 16, by matching
# a DOSBox-X PNG capture (F001, M:layout `base`).
VGA_TEXT_BASE = 0x86024
CELL_BYTES = 8
# F001: component `Memory` is one zlib stream holding guest physical memory from stream offset 0x78
# (M:layout `mem_header`).
MEM_BASE = 0x78

# BIOS data area (guest physical addresses): video mode byte 0040:0049, timer tick count dword 0040:006C.
BDA_VIDEO_MODE = 0x449
BDA_TICKS = 0x46C

CP437_LOW = ("☺☻♥♦♣♠•◘○◙♂♀♪♫☼"
             "►◄↕‼¶§▬↨↑↓→←∟↔▲▼")


def sha256(b):
    return hashlib.sha256(b).hexdigest()


class Screen:
    """The text page: 2000 characters and 2000 attributes."""

    def __init__(self, chars, attrs):
        self.chars, self.attrs = bytes(chars), bytes(attrs)

    def raw(self):
        """chars and attributes interleaved: the 4000 bytes B800:0000 would hold."""
        return bytes(b for c, a in zip(self.chars, self.attrs) for b in (c, a))

    def digest(self):
        return sha256(self.raw())

    def lines(self):
        def ch(c):
            return " " if c == 0 else (CP437_LOW[c - 1] if c < 32 else bytes([c]).decode("cp437"))
        return ["".join(ch(c) for c in self.chars[r * COLS:(r + 1) * COLS]) for r in range(ROWS)]

    def text(self):
        return "\n".join(line.rstrip() for line in self.lines())


class Savestate:
    """The two components the driver reads, inflated once."""

    def __init__(self, path_or_bytes):
        src = path_or_bytes
        if isinstance(src, (bytes, bytearray)):
            import io
            src = io.BytesIO(src)
        with zipfile.ZipFile(src) as z:
            self.vga = zlib.decompressobj().decompress(z.read("Vga"))
            self.mem = zlib.decompressobj().decompress(z.read("Memory"))

    def screen(self):
        b = VGA_TEXT_BASE
        n = ROWS * COLS
        if len(self.vga) < b + CELL_BYTES * n:
            raise ValueError(f"Vga component too short for the text page: {len(self.vga)} bytes")
        return Screen(self.vga[b:b + CELL_BYTES * n:CELL_BYTES], self.vga[b + 1:b + 1 + CELL_BYTES * n:CELL_BYTES])

    def memory(self, addr, n):
        """n bytes of guest physical memory from address addr."""
        o = MEM_BASE + addr
        if addr < 0 or n < 0 or o + n > len(self.mem):
            raise ValueError(f"guest memory 0x{addr:x}+{n} outside the Memory component ({len(self.mem)} bytes)")
        return bytes(self.mem[o:o + n])

    def video_mode(self):
        return self.memory(BDA_VIDEO_MODE, 1)[0]

    def ticks(self):
        """The BIOS timer tick count dword at 0040:006C, little-endian, with its raw bytes."""
        b = self.memory(BDA_TICKS, 4)
        return int.from_bytes(b, "little"), b

    def program(self):
        """Where GOAL.EXE was loaded (find_program, below), found once per savestate."""
        if not hasattr(self, "_prog"):
            self._prog = find_program(self.memory)
        return self._prog

    def ds_bytes(self, off, n):
        """n bytes at DS:off of GOAL.EXE (its data segment, located by find_program)."""
        return self.memory(self.program().ds_base + off, n)

    def ds_word(self, off):
        """The little-endian word at DS:off of GOAL.EXE."""
        return int.from_bytes(self.ds_bytes(off, 2), "little")


# ---- GOAL.EXE's data segment (T08) --------------------------------------------------------------
# DOS memory control block (MCB), one paragraph before the block it describes: byte 0 'M' or 'Z',
# word 1 the owner's PSP segment, word 3 the size in paragraphs, bytes 8..15 the program name
# (DOS 4 and later; DOSBox-X fills it). An EXE's load module starts 0x10 paragraphs (256 bytes)
# after its PSP, and a PSP starts with INT 20h (CD 20).
MCB_OWNER, MCB_NAME = 1, 8
PSP_PARAGRAPHS = 0x10
# static/goal-exe/README.md: "Data segment 2581", the paragraph of DS in the load module before
# relocation (the value GOAL.EXE's startup loads into DS, relocated by the load segment).
GOAL_DS_PARAGRAPH = 0x2581
CONVENTIONAL_TOP = 0xA0000


class Program:
    """Where DOS loaded a program, found in guest memory by its MCB: psp, load segment, and the
    linear base of its data segment (load segment + GOAL_DS_PARAGRAPH, times 16)."""

    def __init__(self, mcb, psp, ds_paragraph=GOAL_DS_PARAGRAPH):
        self.mcb, self.psp = mcb, psp
        self.load = psp + PSP_PARAGRAPHS
        self.ds = self.load + ds_paragraph
        self.ds_base = self.ds * 16

    def describe(self):
        return (f"MCB at segment {self.mcb:04X} (owner {self.psp:04X}, name GOAL), PSP {self.psp:04X}, "
                f"load segment {self.load:04X} = PSP + {PSP_PARAGRAPHS:X}h, DS {self.ds:04X} = load + "
                f"{self.ds - self.load:04X}h, linear base 0x{self.ds_base:05X}")


def find_program(mem_reader, name=b"GOAL", ds_paragraph=GOAL_DS_PARAGRAPH):
    """Scan conventional memory for the MCB of the block a program runs in: an 'M'/'Z' MCB whose
    owner is the segment right after it, whose name starts with `name`, followed by a PSP (CD 20).
    mem_reader(addr, n) returns guest bytes. Returns a Program, or raises when none or several match."""
    found = []
    for seg in range(0x50, CONVENTIONAL_TOP // 16 - 1):
        a = seg * 16
        head = mem_reader(a, 16)
        if head[0] not in (0x4D, 0x5A):
            continue
        owner = int.from_bytes(head[MCB_OWNER:MCB_OWNER + 2], "little")
        if owner != seg + 1 or not head[MCB_NAME:MCB_NAME + 8].startswith(name):
            continue
        if mem_reader(owner * 16, 2) != b"\xcd\x20":
            continue
        found.append(Program(seg, owner, ds_paragraph))
    if len(found) != 1:
        raise ValueError(f"{len(found)} MCBs of {name!r} with a PSP behind them in conventional memory")
    return found[0]



# ---- an edited copy (T19, E008) -----------------------------------------------------------------
def with_memory(data, addr, new):
    """The savestate zip `data` with guest memory at addr replaced by the bytes `new`: an I3 edit,
    to be declared in the record that loads it. Only the `Memory` component changes: its zlib stream
    is inflated, edited and deflated again, and the bytes DOSBox-X writes after the stream are kept;
    every other component, and the order and compression of the zip entries, are copied unchanged."""
    import io
    src = zipfile.ZipFile(io.BytesIO(data))
    out = io.BytesIO()
    with zipfile.ZipFile(out, "w") as dst:
        for info in src.infolist():
            body = src.read(info.filename)
            if info.filename == "Memory":
                d = zlib.decompressobj()
                mem = bytearray(d.decompress(body))
                o = MEM_BASE + addr
                if addr < 0 or o + len(new) > len(mem):
                    raise ValueError(f"guest memory 0x{addr:x}+{len(new)} outside the Memory component ({len(mem)} bytes)")
                mem[o:o + len(new)] = new
                body = zlib.compress(bytes(mem), 1) + d.unused_data
            dst.writestr(info, body, compress_type=info.compress_type)
    return out.getvalue()
