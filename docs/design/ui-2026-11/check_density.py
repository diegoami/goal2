#!/usr/bin/env python3
"""[designed: owner, 2026-11-08; T208, #672] Fail a screen that has a region with no ink.

fidelity-review.md section 2.2 measures how evenly a screen's ink is spread: cut the screen into a 4x4
tiling and take each tile's mean luminance as a percentage. The original's hub and squad screens have no
tile under 1.83 %; the built desk has a tile at 0.00 %. This is that measure as a command:

    python3 docs/design/ui-2026-11/check_density.py <png-or-folder>... [--floor 1.5]

A folder is searched for *.png (recursively, in name order). Exit 0 when every tile of every screen is at or
above the floor; otherwise exit 1 and print the 4x4 table of each failing screen, so the message says which
region is empty. A file that cannot be decoded is reported by name and counts as a failure: it is never
passed in silence. Nothing but the standard library is needed (the runners have no image library and may
have no ImageMagick), so the PNG is decoded here.

The decoder handles what the committed screens are: 8-bit grey, grey+alpha, RGB or RGBA, not interlaced,
all five scanline filters. Anything else (palette, 16-bit, Adam7) is refused by name.
"""
import argparse
import struct
import sys
import zlib
from pathlib import Path

# [designed: T208] The tiling and the floor. The floor sits just under the original's own minimum tile
# (1.83 %, manager-menu.png; m244-squad.png is 1.97 %) so those two originals pass with room and a tile of 1 % or
# less fails. It is not every original's floor: 57 of the 135 original screens have a tile under it (section 2.2).
TILES = 4
DEFAULT_FLOOR = 1.5

# [confirmed: ImageMagick 7.1, `-colorspace Gray`, the command of fidelity-review.md section 7] Rec.709
# coefficients applied to the stored (gamma-encoded) sRGB values, not to linear light. The same weights as
# `magick ... -colorspace Gray`, so the two agree by construction and the cross-check in the test is the proof.
WEIGHTS = (0.2126, 0.7152, 0.0722)

SIGNATURE = b"\x89PNG\r\n\x1a\n"
# colour type -> channels. Colour type 3 (palette) is not here: the screens are never palettised.
CHANNELS = {0: 1, 2: 3, 4: 2, 6: 4}


class PngError(Exception):
    """The file is not a PNG this checker decodes; the message says why."""


def read_png(data):
    """(width, height, channels, rows) of an 8-bit non-interlaced PNG; each row is a bytes of width*channels."""
    if not data.startswith(SIGNATURE):
        raise PngError("not a PNG (bad signature)")
    pos, header, idat = len(SIGNATURE), None, []
    while pos + 8 <= len(data):
        length, kind = struct.unpack(">I4s", data[pos:pos + 8])
        body = data[pos + 8:pos + 8 + length]
        if len(body) != length:
            raise PngError("truncated chunk " + kind.decode("latin-1"))
        if kind == b"IHDR":
            header = struct.unpack(">IIBBBBB", body)
        elif kind == b"IDAT":
            idat.append(body)
        elif kind == b"IEND":
            break
        pos += 12 + length
    if header is None:
        raise PngError("no IHDR chunk")
    width, height, depth, colour, _, _, interlace = header
    if depth != 8:
        raise PngError(f"{depth}-bit samples (only 8-bit is decoded)")
    if colour not in CHANNELS:
        raise PngError(f"colour type {colour} (only grey, grey+alpha, RGB and RGBA are decoded)")
    if interlace:
        raise PngError("interlaced (only non-interlaced is decoded)")
    if width == 0 or height == 0:
        raise PngError("empty image")
    channels = CHANNELS[colour]
    try:
        raw = zlib.decompress(b"".join(idat))
    except zlib.error as error:
        raise PngError(f"bad image data: {error}") from None
    stride = width * channels
    if len(raw) != height * (stride + 1):
        raise PngError(f"image data is {len(raw)} bytes, expected {height * (stride + 1)}")
    return width, height, channels, unfilter(raw, height, stride, channels)


def unfilter(raw, height, stride, bpp):
    """Undo the five scanline filters (PNG spec 9.2). `bpp` is bytes per pixel, as 8-bit samples make it."""
    rows, prior = [], bytes(stride)
    for y in range(height):
        start = y * (stride + 1)
        kind, line = raw[start], bytearray(raw[start + 1:start + 1 + stride])
        if kind == 0:                                   # None
            pass
        elif kind == 1:                                 # Sub: add the byte one pixel to the left
            for i in range(bpp, stride):
                line[i] = (line[i] + line[i - bpp]) & 255
        elif kind == 2:                                 # Up: add the byte above
            line = bytearray((a + b) & 255 for a, b in zip(line, prior))
        elif kind == 3:                                 # Average of left and above, rounded down
            for i in range(stride):
                left = line[i - bpp] if i >= bpp else 0
                line[i] = (line[i] + ((left + prior[i]) >> 1)) & 255
        elif kind == 4:                                 # Paeth: the neighbour nearest left+above-upperleft
            for i in range(stride):
                a = line[i - bpp] if i >= bpp else 0
                b = prior[i]
                c = prior[i - bpp] if i >= bpp else 0
                p = a + b - c
                pa, pb, pc = abs(p - a), abs(p - b), abs(p - c)
                near = a if pa <= pb and pa <= pc else b if pb <= pc else c
                line[i] = (line[i] + near) & 255
        else:
            raise PngError(f"scanline {y} has filter type {kind}")
        prior = bytes(line)
        rows.append(prior)
    return rows


def tile_means(width, height, channels, rows, tiles=TILES):
    """The mean luminance, as a percentage of white, of each tile: `tiles` lists of `tiles` numbers, top row
    first. Tile edges are i*size//tiles, so every pixel is in exactly one tile (ImageMagick's
    `-crop 25x25%` cuts the same way on sizes that divide, which the screens' do)."""
    xs = [i * width // tiles for i in range(tiles + 1)]
    ys = [i * height // tiles for i in range(tiles + 1)]
    if channels <= 2:
        weights, offsets = (1.0,), (0,)
    else:
        weights, offsets = WEIGHTS, (0, 1, 2)
    means = []
    for ty in range(tiles):
        sums = [0.0] * tiles
        for y in range(ys[ty], ys[ty + 1]):
            row = rows[y]
            for tx in range(tiles):
                lo, hi = xs[tx] * channels, xs[tx + 1] * channels
                sums[tx] += sum(w * sum(row[lo + o:hi:channels]) for w, o in zip(weights, offsets))
        band = ys[ty + 1] - ys[ty]
        means.append([100.0 * s / (255.0 * band * (xs[tx + 1] - xs[tx])) for tx, s in enumerate(sums)])
    return means


def measure(path):
    """The 4x4 table of one PNG, or raise PngError / OSError."""
    return tile_means(*read_png(Path(path).read_bytes()))


def table(means):
    return "\n".join("    " + "  ".join(f"{m:6.2f}" for m in row) for row in means)


def collect(paths):
    """The PNG files named by the arguments: a file as given, a folder searched for *.png."""
    found = []
    for arg in paths:
        p = Path(arg)
        found.extend(sorted(p.rglob("*.png")) if p.is_dir() else [p])
    return found


def main(argv=None):
    parser = argparse.ArgumentParser(description="Fail a screen with a region of no ink (4x4 tiling).")
    parser.add_argument("paths", nargs="+", help="PNG files or folders of them")
    parser.add_argument("--floor", type=float, default=DEFAULT_FLOOR,
                        help=f"lowest tile mean luminance in percent (default {DEFAULT_FLOOR}); "
                             "lower it only for a deliberate exception")
    args = parser.parse_args(argv)
    files = collect(args.paths)
    if not files:
        print("no PNG files found")
        return 1
    failed = 0
    for path in files:
        try:
            means = measure(path)
        except (PngError, OSError) as error:
            print(f"{path}: cannot be checked: {error}")
            failed += 1
            continue
        low = [(ty, tx) for ty, row in enumerate(means) for tx, m in enumerate(row) if m < args.floor]
        if low:
            failed += 1
            cells = ", ".join(f"row {ty + 1} col {tx + 1}" for ty, tx in low)
            print(f"{path}: {len(low)} of {TILES * TILES} tiles under {args.floor:g} % ({cells}); "
                  f"mean luminance % per tile:")
            print(table(means))
    print(f"{len(files)} screens, {failed} failing (floor {args.floor:g} %)")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
