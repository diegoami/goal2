"""T114: the TEAM skills bars, 1771:157D -> 0BC4(country, side 1, flag 0) -> 11E1(15).

Reads are explicit immutable byte callbacks over the original's current memory:
read_player(word) -> the 20 bytes at far(DS:A91B)+20*word, read_country(n) ->
the 191 bytes at far(DS:A917)+191*n, read_manager(m) -> the 3 bytes at
far(DS:A91F)+3*m, read_ds(offset, size) and read_code(image_segment, offset,
size). No binary bytes or tables are bundled. Host validation below rejects
inputs the original would follow outside its tables; it is not original behaviour.
"""
from .team_bars import line_bars, s16

SKILLS_ROW = 15


def _read(read, key, size, what):
    raw = read(*key) if isinstance(key, tuple) else read(key)
    if len(raw) != size:
        raise ValueError(f'{what} must be {size} bytes')
    return raw


def _s8(value):
    return value-0x100 if value >= 0x80 else value


def _idiv(a, b):
    q = abs(a)//abs(b)
    return -q if (a < 0) != (b < 0) else q


def _element(byte, n):
    """214B:0C57: element n of a one-byte Pascal set is bit n-1."""
    return (byte >> (n-1)) & 1


def _in_set(read_code, offset, value):
    """23E4:08DF: membership of a byte in a 32-byte Pascal set in segment 1771."""
    return (_read(read_code, (0x1771, offset+(value >> 3), 1), 1, 'set byte')[0] >> (value & 7)) & 1


def unavailable(player):
    """1771:3216: energy +0xE below 1 (signed) or element 8, 6 or 3 of +0x10 set."""
    return _s8(player[0xE]) < 1 or any(_element(player[0x10], n) for n in (8, 6, 3))


def halved(word, player, read_ds, read_code):
    """1771:3179, the out-of-position halving flag (F028), with 3088 and 3041."""
    position, side = player[6], player[7]
    row = _read(read_ds, (0xE7C+word % 3, 1), 1, 'foot index')[0]
    foot = _read(read_ds, (0xE60+14*row+side, 1), 1, 'foot table')[0]
    exact = (player[5]+player[2]) == 0x1E
    if not exact and foot and _in_set(read_code, 0x3139, position):
        return True
    if not foot and _in_set(read_code, 0x3159, position):
        return True
    return (position == 0) != (side == 0)


def strength(word, player, read_ds, read_code):
    """1771:377E: (+4 - 0x3E) + s8(+0xE), form +0xC added below 32 else minus a
    sixteenth, clamped 0..0x100, halved by 3179; 0 when 3216 says unavailable."""
    if unavailable(player):
        return 0
    value = player[4]-0x3E+_s8(player[0xE])
    form = _s8(player[0xC])
    value = value-_idiv(value, 16) if form >= 0x20 else value+form
    value = 0 if value < 0 else 0x100 if value > 0x100 else value
    return _idiv(value, 2) if halved(word, player, read_ds, read_code) else value


def manager_bonus(manager_record):
    """1771:0AA7: manager byte +1 zero-extended, idiv 8, +0x10."""
    return manager_record[1]//8+0x10


def line_sums(country_record, read_player, read_country, read_manager, read_ds, read_code):
    """0BC4(country, side 1, flag 0): the four signed words DS:9B47+4k it leaves.

    Squad slots 1..11 with a nonzero word: strength plus the manager bonus M when
    the strength is nonzero, into line DS:0D4E[+6] (k >= 4: an unsigned half to
    k-3 and k-2). An outfield player (+6 nonzero) adds M div 8 to attack or to
    defence per effective tactic element 1, 5, 6 (the set at CS:0BA4): element e
    of +0xF when e < 5 and element e+4 of +0xF is set, else element e of +0x2D of
    the country in the player's byte 0. The panel's flag is 0: no eighth is added.
    """
    if len(country_record) != 191:
        raise ValueError('country record must be 191 bytes')
    bonus = manager_bonus(_read(read_manager, country_record[0x2E], 3, 'manager record'))
    sums = [0, 0, 0, 0]
    for slot in range(1, 12):
        word = int.from_bytes(country_record[2*slot-2:2*slot], 'little')
        if word == 0:
            continue
        player = _read(read_player, word, 20, 'player record')
        value = strength(word, player, read_ds, read_code)
        if value:
            value = (value+bonus) & 0xFFFF
        if player[6]:
            for e in range(1, 7):
                if not _in_set(read_code, 0x0BA4, e):
                    continue
                if e < 5 and _element(player[0xF], e+4):
                    bit = _element(player[0xF], e)
                else:
                    bit = _element(_read(read_country, player[0], 191, 'country record')[0x2D], e)
                sums[3 if bit else 1] += bonus//8
        line = _read(read_ds, (0xD4E+player[6], 1), 1, 'line table')[0]
        if line > 5:
            raise ValueError(f'position {player[6]} selects line {line} outside 0..5')
        if line < 4:
            sums[line] += value
        else:
            sums[line-3] += value//2
            sums[line-2] += value//2
    return [s16(v) for v in sums]


def team_skills(country_record, read_player, read_country, read_manager, read_ds, read_code):
    """TEAM rows 15..18 (keeper, defence, midfield, attack): the cells 11E1 highlights."""
    sums = line_sums(country_record, read_player, read_country, read_manager, read_ds, read_code)
    return dict(bars=line_bars(sums, SKILLS_ROW), line_sums=sums)
