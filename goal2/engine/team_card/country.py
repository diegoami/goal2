"""T94/F035: the original TEAM Status (country) and Skill (manager) labels.

Reads are explicit immutable byte callbacks: read_ds(offset,size) and
read_code(image_segment,offset,size). No binary bytes or label tables are bundled.
Host validation below is distinct from the original's unchecked memory accesses.
"""
from .manager import screen_text


def _integer(value, low, high, name):
    if type(value) is not int or not low <= value <= high:
        raise ValueError(f'{name} must be {low}..{high}')


def _read(read, offset, size):
    raw=read(offset,size)
    if len(raw)!=size:
        raise ValueError('truncated display data')
    return raw


def _label(read_ds, table, band):
    index=_read(read_ds,table+band,1)[0]
    record=_read(read_ds,0x6EB4+16*index,16)
    if record[0]>15:
        raise ValueError('label exceeds its 16-byte Pascal slot')
    return screen_text(record[1:1+record[0]])


def country_rating(continent, continental_rank, world_rank):
    """1771:10E7 / F007: original rank-derived value in the normal rank domain."""
    _integer(continent,1,4,'continent')
    _integer(continental_rank,1,32,'continental rank')
    _integer(world_rank,1,128,'world rank')
    return ((5-continent)*(33-continental_rank)+129-world_rank)//2


def country_status(continent, continental_rank, world_rank, read_ds):
    """TEAM row8/column25, 1771:1527: country rating -> DS:7884 label band."""
    rating=country_rating(continent,continental_rank,world_rank)
    return _label(read_ds,0x7884,(rating-1)//8)


def manager_skill(manager, ability, read_ds, read_code):
    """TEAM row10/column24, 1771:0AF8: manager+1, not country/player skill.

    Manager0 draws nothing (None); ability0 draws CS:0AF0 'unknown'. The
    original accepts the full unsigned byte1..255 and reads DS:7894+(v-1)//8;
    values129..255 extend into neighboring tables, without a clamp. This
    reproduces that lookup, without assigning invented semantic levels to it.
    """
    _integer(manager,0,134,'manager')
    _integer(ability,0,255,'manager ability')
    if manager==0:
        return None
    if ability==0:
        record=read_code(0x1771,0xAF0,8)
        if len(record)!=8 or record[0]>7:
            raise ValueError('invalid unknown label')
        return screen_text(record[1:1+record[0]])
    return _label(read_ds,0x7894,(ability-1)//8)


def team_labels(country_record, manager_record, read_ds, read_code):
    """Decode one current country record and its selected manager's current record.

    Country+0x2E selects the manager. Caller reads three bytes from
    far(DS:A91F)+3*m, including human slots129..134; byte+1 is ability.
    No player, formation, current-match or aggregate field enters these labels.
    """
    if len(country_record)!=191:
        raise ValueError('country record must be 191 bytes')
    manager=country_record[46]
    _integer(manager,0,134,'manager')
    if manager and (manager_record is None or len(manager_record)!=3):
        raise ValueError('selected manager record must be 3 bytes')
    c,r,w=country_record[44],country_record[42],country_record[43]
    return dict(status=country_status(c,r,w,read_ds),
                skill=manager_skill(manager,manager_record[1] if manager else 0,read_ds,read_code),
                country_rating=country_rating(c,r,w))
