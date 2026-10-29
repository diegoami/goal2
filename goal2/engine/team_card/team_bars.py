"""T114: TEAM line bars, 1771:11E1, and their highlight, 214B:13C5 -> 214B:00DB.

11E1(row) reads the four signed words DS:9B47+4k (k = keeper, defence,
midfield, attack) its caller filled, divides lines 1..3 by 4 (idiv), clamps all
four to 1..256 and highlights v*25 idiv 256 cells from column 10 of row row+k.
13C5(row, column, n) writes attribute 0x70 into n cells (00DB: nothing when
n <= 0); characters and the other cells keep the template's text and colours.
"""

HIGHLIGHT = 0x70
LINES = ('keeper', 'defence', 'midfield', 'attack')
BAR_COLUMN = 10


def s16(value):
    value &= 0xFFFF
    return value-0x10000 if value >= 0x8000 else value


def idiv(a, b):
    """x86 idiv: the quotient truncated toward zero."""
    q = abs(a)//abs(b)
    return -q if (a < 0) != (b < 0) else q


def line_bars(words, row):
    """11E1(row) on the four signed words; returns one bar per line, in order."""
    if len(words) != 4 or any(type(w) is not int or not -0x8000 <= w <= 0x7FFF for w in words):
        raise ValueError('four signed 16-bit line words required')
    bars = []
    for k, word in enumerate(words):
        value = word if k == 0 else idiv(word, 4)
        value = 1 if value < 1 else 0x100 if value > 0x100 else value
        bars.append(dict(line=LINES[k], row=row+k, column=BAR_COLUMN,
                         value=value, cells=value*25//256))
    return bars

