"""T116: the TEAM characteristics, 1771:157D 16BB-180C with 1771:13D0.

13D0 seeds six words with 6 and, for each squad slot 1..11 whose player 3216
reports available, adds: morale min(32, s8 +0xC); fitness s8 +0xD when s8
energy +0xE > 0; hardness (+5 - (+3 and 1)) and 0xFF (2FFB); energy s8 +0xE;
age +1; caps word +8. Every word wraps at 16 bits and is divided unsigned by
11, whatever the number of available players; morale is then at least 1.
157D draws four descriptors from their tables with bars, and caps and age as
numbers. Reads are explicit immutable byte callbacks, as team_skills.py.
"""
from .manager import screen_text
from .team_skills import unavailable

FIELDS = ('morale', 'fitness', 'hardness', 'energy', 'age', 'caps')
# (field, DS table, row, bar divisor, the table's own index range): 157D 16C1-17C8.
# The four tables are contiguous (78A3+33 = 78C4, +17 = 78D5, +33 = 78F6, +33 = 7917);
# an index outside its range reads the next table, as the original does.
DESCRIPTORS = (('hardness', 0x78C4, 20, 16, (0, 16)), ('fitness', 0x78D5, 21, 32, (0, 32)),
               ('energy', 0x78F6, 22, 32, (0, 32)), ('morale', 0x78A3, 23, 32, (1, 32)))
COLUMN = 46
NUMBERS = (('caps', 19, 49), ('age', 19, 59))


def _s8(value):
    return value-0x100 if value >= 0x80 else value


def aggregates(country_record, read_player):
    """13D0(country): the six words DS:9B5A..9B64 it leaves, by name."""
    if len(country_record) != 191:
        raise ValueError('country record must be 191 bytes')
    acc = dict.fromkeys(FIELDS, 6)
    for slot in range(1, 12):
        word = int.from_bytes(country_record[2*slot-2:2*slot], 'little')
        player = read_player(word)
        if len(player) != 20:
            raise ValueError('player record must be 20 bytes')
        if unavailable(player):
            continue
        acc['morale'] += min(32, _s8(player[0xC]))
        if _s8(player[0xE]) > 0:
            acc['fitness'] += _s8(player[0xD])
        acc['hardness'] += (player[5]-(player[3] & 1)) & 0xFF
        acc['energy'] += _s8(player[0xE])
        acc['age'] += player[1]
        acc['caps'] += int.from_bytes(player[8:10], 'little')
    out = {k: (v & 0xFFFF)//11 for k, v in acc.items()}
    out['morale'] = max(1, out['morale'])
    return out


def _label(read_ds, table, value):
    index = read_ds(table+value, 1)
    if len(index) != 1:
        raise ValueError('truncated descriptor table')
    record = read_ds(0x6EB4+16*index[0], 16)
    if len(record) != 16 or record[0] > 15:
        raise ValueError('label exceeds its 16-byte Pascal slot')
    return screen_text(record[1:1+record[0]])


def bar_cells(value, divisor):
    """157D: ((v shl 4) and 0xFFFF) div divisor, unsigned; 214B:00DB highlights that many."""
    return ((value << 4) & 0xFFFF)//divisor


def team_characteristics(country_record, read_player, read_ds):
    """The panel's rows 19..23: descriptors with bars from column 46, caps and age as text."""
    values = aggregates(country_record, read_player)
    rows = [dict(field=f, row=row, column=COLUMN, value=values[f], text=_label(read_ds, table, values[f]),
                 cells=bar_cells(values[f], divisor), in_table=lo <= values[f] <= hi)
            for f, table, row, divisor, (lo, hi) in DESCRIPTORS]
    numbers = [dict(field=f, row=row, column=column, value=values[f], text=str(values[f]))
               for f, row, column in NUMBERS]
    return dict(descriptors=rows, numbers=numbers, aggregates=values)
