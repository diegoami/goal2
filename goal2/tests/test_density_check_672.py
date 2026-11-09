"""[designed: owner, 2026-11-08; T208, #672] docs/design/ui-2026-11/check_density.py.

The claim it protects: the check fails a screen with a region of no ink, and the numbers it prints are
the ones ImageMagick gives. The tests write their own PNGs to a temporary folder and change nothing in the
repository. `test_floor_is_applied` is the one that fails if the floor stops being applied.
"""
import contextlib
import importlib.util
import io
import random
import shutil
import struct
import subprocess
import tempfile
import unittest
import zlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CHECKER = ROOT / "docs" / "design" / "ui-2026-11" / "check_density.py"
ORIGINAL_DESK = ROOT / "docs" / "original-game" / "images" / "manager-menu.png"
ORIGINAL_SQUAD = ROOT / "docs" / "original-game" / "images" / "m244-squad.png"

_spec = importlib.util.spec_from_file_location("check_density", CHECKER)
check_density = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(check_density)


def _paeth(a, b, c):
    p = a + b - c
    pa, pb, pc = abs(p - a), abs(p - b), abs(p - c)
    return a if pa <= pb and pa <= pc else b if pb <= pc else c


def _filter(kind, line, prior, bpp):
    """The encoder side of PNG's five filters, written from the spec independently of the checker's decoder."""
    out = bytearray()
    for i, x in enumerate(line):
        a = line[i - bpp] if i >= bpp else 0
        b = prior[i]
        c = prior[i - bpp] if i >= bpp else 0
        predicted = (0, a, b, (a + b) // 2, _paeth(a, b, c))[kind]
        out.append((x - predicted) & 255)
    return bytes(out)


def png_bytes(rows, colour=2, kinds=(0,), extra=()):
    """A PNG of 8-bit `rows` (bytes each), scanline i filtered with kinds[i % len(kinds)]."""
    channels = {0: 1, 2: 3, 4: 2, 6: 4}[colour]
    width, height = len(rows[0]) // channels, len(rows)
    prior, raw = bytes(width * channels), bytearray()
    for i, line in enumerate(rows):
        kind = kinds[i % len(kinds)]
        raw.append(kind)
        raw += _filter(kind, line, prior, channels)
        prior = line

    def chunk(kind, body):
        return struct.pack(">I", len(body)) + kind + body + struct.pack(">I", zlib.crc32(kind + body))

    header = struct.pack(">IIBBBBB", width, height, 8, colour, 0, 0, 0)
    return (check_density.SIGNATURE + chunk(b"IHDR", header) + chunk(b"IDAT", zlib.compress(bytes(raw)))
            + chunk(b"IEND", b""))


def screen(width=64, height=40, channels=3, empty=None):
    """Rows of a screen with ink everywhere, except the pixels `empty(x, y)` selects, which are black."""
    rows = []
    for y in range(height):
        line = bytearray()
        for x in range(width):
            ink = not (empty and empty(x, y))
            pixel = (200, 200, 200, 255)[:channels] if ink else (0, 0, 0, 255)[:channels]
            line += bytes(pixel)
        rows.append(bytes(line))
    return rows


def run(*args):
    """check_density.main(args): (exit code, what it printed)."""
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        code = check_density.main([str(a) for a in args])
    return code, out.getvalue()


class DensityCheck(unittest.TestCase):
    def setUp(self):
        self.dir = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.dir, True)

    def write(self, name, data):
        path = self.dir / name
        path.write_bytes(data)
        return path

    def test_decoder_undoes_every_filter(self):
        rng = random.Random(672)
        for colour, channels in ((0, 1), (2, 3), (4, 2), (6, 4)):
            rows = [bytes(rng.randrange(256) for _ in range(9 * channels)) for _ in range(10)]
            for kind in range(5):
                with self.subTest(colour=colour, filter=kind):
                    width, height, got_channels, got = check_density.read_png(png_bytes(rows, colour, (kind,)))
                    self.assertEqual((width, height, got_channels), (9, 10, channels))
                    self.assertEqual(got, rows)
            with self.subTest(colour=colour, filter="mixed"):
                self.assertEqual(check_density.read_png(png_bytes(rows, colour, (0, 1, 2, 3, 4)))[3], rows)

    def test_tile_means_of_known_pixels(self):
        # A white left half and a black right half: the two left columns of tiles are 100 %, the right 0 %.
        rows = [bytes([255] * 3 * 8 + [0] * 3 * 8)] * 16
        means = check_density.tile_means(16, 16, 3, rows)
        for row in means:
            for got, want in zip(row, (100.0, 100.0, 0.0, 0.0)):
                self.assertAlmostEqual(got, want, places=9)
        # Grey 51/255 = 20 % everywhere, and the same for RGBA whatever the alpha.
        for channels, pixel in ((3, bytes([51] * 3)), (4, bytes([51, 51, 51, 7]))):
            means = check_density.tile_means(8, 8, channels, [pixel * 8] * 8)
            self.assertAlmostEqual(means[2][1], 20.0, places=6)

    def test_filled_screen_passes(self):
        path = self.write("filled.png", png_bytes(screen(), kinds=(1, 2, 3, 4)))
        code, out = run(path)
        self.assertEqual(code, 0, out)
        self.assertIn("1 screens, 0 failing", out)

    def test_the_management_originals_the_floor_is_drawn_from_pass(self):
        # [confirmed: fidelity-review.md 2.2, measured] The desk (min tile 1.83 %) and the squad (1.97 %) clear
        # the default floor. The floor is NOT the whole original set's: 57 of 135 screens, match-menu.png among
        # them (0.28 %), have a tile under it, so this test names the two screens and nothing wider.
        for path in (ORIGINAL_DESK, ORIGINAL_SQUAD):
            code, out = run(path)
            self.assertEqual(code, 0, out)
        self.assertEqual(run(ORIGINAL_DESK, "--floor", "1.9")[0], 1)

    def test_empty_quarter_fails_and_prints_the_table(self):
        # The bottom-right quarter of the screen carries no ink: tiles (row 3-4, col 3-4).
        rows = screen(empty=lambda x, y: x >= 32 and y >= 20)
        path = self.write("quarter.png", png_bytes(rows, kinds=(4,)))
        code, out = run(path)
        self.assertEqual(code, 1)
        self.assertIn("4 of 16 tiles under 1.5 %", out)
        self.assertIn("row 3 col 3", out)
        self.assertIn("row 4 col 4", out)
        self.assertEqual(out.count("0.00"), 4)
        self.assertEqual(out.count("78.43"), 12)  # the 4x4 table: the other twelve tiles, 200/255

    def test_floor_is_applied(self):
        # The bottom-right tile (25 x 10 pixels) keeps one inked column in 25, about 3 %; the others are full.
        # With the floor above that tile it fails; with the floor lowered under it, it passes.
        rows = screen(width=100, height=40, empty=lambda x, y: x >= 75 and y >= 30 and (x - 75) % 25 != 0)
        path = self.write("thin.png", png_bytes(rows))
        means = check_density.measure(path)
        thin = means[3][3]
        self.assertTrue(0.5 < thin < 5, thin)
        self.assertEqual(run(path, "--floor", thin + 0.5)[0], 1)
        self.assertEqual(run(path, "--floor", thin - 0.05)[0], 0)
        self.assertEqual(run(path, "--floor", 0)[0], 0)
        # The default floor is the task's 1.5 %, and a tile at 0 % is under any positive floor.
        self.assertEqual(check_density.DEFAULT_FLOOR, 1.5)
        black = self.write("black.png", png_bytes(screen(empty=lambda x, y: True)))
        self.assertEqual(run(black)[0], 1)
        self.assertEqual(run(black, "--floor", 0.01)[0], 1)

    def test_folders_and_files_are_both_taken(self):
        self.write("a-filled.png", png_bytes(screen()))
        self.write("b-empty.png", png_bytes(screen(empty=lambda x, y: x < 16 and y < 10)))
        sub = self.dir / "sub"
        sub.mkdir()
        (sub / "c-filled.png").write_bytes(png_bytes(screen()))
        code, out = run(self.dir)
        self.assertEqual(code, 1)
        self.assertIn("3 screens, 1 failing", out)
        self.assertIn("b-empty.png", out)
        self.assertEqual(run(self.dir / "a-filled.png", sub)[0], 0)

    def test_file_that_cannot_be_decoded_is_named_not_passed(self):
        good = png_bytes(screen())
        cases = {
            "text.png": b"not a png at all",
            "truncated.png": good[:len(good) // 2],
            "missing.png": None,
        }
        for name, data in cases.items():
            path = self.dir / name
            if data is not None:
                path.write_bytes(data)
            with self.subTest(name):
                code, out = run(path)
                self.assertEqual(code, 1)
                self.assertIn(str(path), out)
                self.assertIn("cannot be checked", out)
        # A palette image and a 16-bit image are refused by name, not guessed at.
        for name, depth, colour in (("palette.png", 8, 3), ("deep.png", 16, 2)):
            data = bytearray(good)
            struct.pack_into(">BB", data, 24, depth, colour)
            struct.pack_into(">I", data, 29, zlib.crc32(bytes(data[12:29])))
            path = self.write(name, bytes(data))
            with self.subTest(name):
                code, out = run(path)
                self.assertEqual(code, 1)
                self.assertIn(name, out)
                self.assertIn("cannot be checked", out)

    def test_no_files_is_a_failure(self):
        empty = self.dir / "empty"
        empty.mkdir()
        self.assertEqual(run(empty)[0], 1)

    @unittest.skipUnless(shutil.which("magick"), "ImageMagick (magick) absent: the cross-check needs it")
    def test_tile_means_agree_with_imagemagick(self):
        # The task's command, on a committed original screen: every tile within 0.05 percentage points.
        result = subprocess.run(
            ["magick", str(ORIGINAL_DESK), "-colorspace", "Gray", "-crop", "25x25%",
             "-format", "%[fx:mean*100]\n", "info:-"],
            capture_output=True, text=True, check=True)
        expected = [float(v) for v in result.stdout.split()]
        self.assertEqual(len(expected), 16)
        got = [m for row in check_density.measure(ORIGINAL_DESK) for m in row]
        for i, (a, b) in enumerate(zip(got, expected)):
            self.assertAlmostEqual(a, b, delta=0.05, msg=f"tile {i}")


if __name__ == "__main__":
    unittest.main()
