"""Unit tests for the vendored savestate reader (T01 scope).

The reader is the `Savestate` class from `runtime/driver/savestate.py`, vendored at
`goal2/engine/savestate.py`. The reader parses a DOSBox-X savestate (a zip of two
zlib streams: `Vga` and `Memory`). The unit tests cover the format's contract:
- a savestate must have both streams;
- the `Vga` stream's text page lives at offset 0x86024, 8 bytes per cell, 25x80 cells;
- the `Memory` stream's guest memory lives at offset 0x78;
- an out-of-range memory read raises ValueError.
[confirmed: the layout constants (VGA_TEXT_BASE, MEM_BASE, CELL_BYTES) and the BIOS data area
offsets (BDA_VIDEO_MODE = 0x449, BDA_TICKS = 0x46C) come from F001, calibrated on DOSBox-X
2024.03.01 (svga_s3, memsize 16).]
"""
import io
import unittest
import zipfile
import zlib

from goal2 import cli


def _zip_sav(vga: bytes, mem: bytes) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr("Vga", zlib.compress(vga))
        z.writestr("Memory", zlib.compress(mem))
    return buf.getvalue()


class SavestateLoad(unittest.TestCase):
    def test_loads_a_zip_with_vga_and_memory(self):
        vga = b"\x00" * (0x86024 + 8 * 25 * 80)
        mem = b"\x00" * (0x78 + 0x1000)
        s = cli.savestate.Savestate(_zip_sav(vga, mem))
        self.assertGreater(len(s.vga), 0)
        self.assertGreater(len(s.mem), 0)

    def test_video_mode_and_ticks(self):
        """The BDA fields are read at well-known offsets."""
        vga = b"\x00" * (0x86024 + 8 * 25 * 80)
        mem = bytearray(0x78 + 0x1000)
        # BDA video mode = 0x449: 0x03 (text mode)
        mem[0x78 + 0x449] = 0x03
        # BDA ticks = 0x46C: 0x12345678 little-endian
        mem[0x78 + 0x46C:0x78 + 0x46C + 4] = b"\x78\x56\x34\x12"
        s = cli.savestate.Savestate(_zip_sav(vga, bytes(mem)))
        self.assertEqual(s.video_mode(), 0x03)
        self.assertEqual(s.ticks()[0], 0x12345678)

    def test_out_of_range_memory_read_raises(self):
        vga = b"\x00" * (0x86024 + 8 * 25 * 80)
        mem = b"\x00" * (0x78 + 16)
        s = cli.savestate.Savestate(_zip_sav(vga, mem))
        with self.assertRaises(ValueError):
            s.memory(0x1000, 1)

    def test_missing_zip_member_raises(self):
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as z:
            z.writestr("Vga", zlib.compress(b"\x00" * 100))
        with self.assertRaises(KeyError):
            cli.savestate.Savestate(buf.getvalue())
