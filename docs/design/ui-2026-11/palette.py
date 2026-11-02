#!/usr/bin/env python3
"""[designed: owner, 2026-11-03, #526] Read the original's colours from its captures.

The mockups use the original's own palette. This script decodes the captured screens in docs/original-game/images
(640x400 RGB PNGs, read with zlib only) and prints the README's palette table: for each role, its colour, the image and area it is read from, and what the area
shows. With --all it also lists every colour of each
image with its pixel count.

    python3 docs/design/ui-2026-11/palette.py [--all]
"""
import struct
import sys
import zlib
from collections import Counter
from pathlib import Path

IMAGES = Path(__file__).resolve().parents[2] / "original-game" / "images"

# (role, image, (x0, y0, x1, y1), what the area shows). The colour of a role is the commonest colour of that area of the
# 640x400 capture other than the black ground (the ground itself is the commonest colour of the whole screen).
SAMPLES = [
    ("ground", "t156-013-hub.png", (0, 0, 640, 400), "the whole hub screen"),
    ("text, bright", "t156-013-hub.png", (20, 110, 100, 128), "the manager's name 'K Ees'"),
    ("text, normal", "t156-224-fixture-list.png", (430, 146, 520, 161), "'qualifying' in the fixture list"),
    ("frame lines", "t156-013-hub.png", (505, 20, 509, 390), "the frame of the hub's squad strip"),
    ("frame lines, dark grey", "t156-013-hub.png", (0, 95, 10, 400), "the frames on the hub's left"),
    ("headings, cyan", "t156-224-fixture-list.png", (140, 80, 240, 95), "'and results' under the fixtures title"),
    ("card headings, red", "t156-014-squad.png", (8, 160, 60, 174), "'skills' on the squad card"),
    ("card labels, brown", "t156-014-squad.png", (8, 177, 70, 190), "'keeping' on the squad card"),
    ("key hints, magenta", "t156-013-hub.png", (205, 270, 300, 305), "'Use ↑↓ to find option' on the hub"),
    ("highlight bar", "t156-013-hub.png", (362, 103, 442, 127), "the highlighted 'team info' option"),
    ("values, yellow", "t156-224-fixture-list.png", (104, 130, 530, 370), "the team names of the fixture list"),
    ("title banner, light red", "t156-013-hub.png", (100, 5, 440, 90), "the 'European Championship' banner"),
    ("goalkeeper", "t156-013-hub.png", (510, 32, 520, 46), "V Breuklen's initial in the squad strip"),
    ("defence", "t156-013-hub.png", (510, 48, 520, 62), "Koeman's initial"),
    ("midfield", "t156-013-hub.png", (510, 96, 520, 110), "Wouters's initial"),
    ("attack", "t156-013-hub.png", (510, 192, 520, 206), "Van Basten's initial"),
    ("bar, filled", "t156-014-squad.png", (80, 177, 270, 190), "the keeping bar"),
    ("bar, empty", "t156-014-squad.png", (120, 241, 270, 254), "the marking bar's empty part"),
    ("pitch lines", "t156-045-kick-off.png", (18, 100, 22, 350), "the left touchline"),
    ("pitch surround", "t156-045-kick-off.png", (0, 80, 640, 100), "the band above the pitch"),
    ("home side", "t156-045-kick-off.png", (362, 222, 380, 240), "a Norway player's letter at kick-off"),
    ("away side", "t156-045-kick-off.png", (170, 222, 188, 240), "a Holland player's letter at kick-off"),
]


def decode(path):
    data = path.read_bytes()
    assert data[:8] == b"\x89PNG\r\n\x1a\n", path
    pos, idat, width = 8, b"", 0
    while pos < len(data):
        length, kind = struct.unpack(">I4s", data[pos:pos + 8])
        chunk = data[pos + 8:pos + 8 + length]
        if kind == b"IHDR":
            width, height, depth, colour = struct.unpack(">IIBB", chunk[:10])
            assert (depth, colour) == (8, 2), f"{path}: not 8-bit RGB"
        elif kind == b"IDAT":
            idat += chunk
        pos += 12 + length
    raw, stride, rows, prev = zlib.decompress(idat), width * 3, [], bytearray(width * 3)
    for y in range(height):
        f, line = raw[y * (stride + 1)], bytearray(raw[y * (stride + 1) + 1:(y + 1) * (stride + 1)])
        for i in range(stride):
            a = line[i - 3] if i >= 3 else 0
            b, c = prev[i], prev[i - 3] if i >= 3 else 0
            if f == 1:
                line[i] = (line[i] + a) & 255
            elif f == 2:
                line[i] = (line[i] + b) & 255
            elif f == 3:
                line[i] = (line[i] + (a + b) // 2) & 255
            elif f == 4:
                p = a + b - c
                pa, pb, pc = abs(p - a), abs(p - b), abs(p - c)
                line[i] = (line[i] + (a if pa <= pb and pa <= pc else b if pb <= pc else c)) & 255
        rows.append(line)
        prev = line
    return rows


def colour(rows, box, ground=False):
    x0, y0, x1, y1 = box
    counts = Counter(pixel(rows, x, y) for y in range(y0, y1) for x in range(x0, x1))
    for c, _ in counts.most_common():
        if ground or c != "#000000":
            return c
    return "#000000"


def pixel(rows, x, y):
    r, g, b = rows[y][3 * x:3 * x + 3]
    return f"#{r:02x}{g:02x}{b:02x}"


def main(argv):
    cache = {}
    for role, image, box, what in SAMPLES:
        rows = cache.setdefault(image, decode(IMAGES / image))
        print(f"| {role} | `{colour(rows, box, role == 'ground')}` | {image} {box} | {what} |")
    if "--all" in argv:
        for image, rows in cache.items():
            counts = Counter(pixel(rows, x, y) for y in range(len(rows)) for x in range(len(rows[0]) // 3))
            print(image, ", ".join(f"{c} {n}" for c, n in counts.most_common()))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
