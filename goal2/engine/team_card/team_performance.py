"""T115: the TEAM performance bars, 1771:157D 1892-18AF -> 1289(side) -> 11E1(20).

157D draws them only while DS:0C1E (a fixture set up) and DS:0C1F (the in-match
menu already left once) are both nonzero, for match side 1 when the panel's
country is DS:9B36, else side 0, whatever country that is. Reads are explicit
immutable byte callbacks over the original's current memory, as team_skills.py.
"""
from .team_bars import idiv, line_bars, s16

PERFORMANCE_ROW = 20


def shown(match_set_up, in_match_menu_used):
    """157D 1892-189E: both bytes nonzero."""
    return bool(match_set_up) and bool(in_match_menu_used)


def match_side(country, sides):
    """157D 18A0-18AE: 1 when DS:9B36 equals the panel's country, else 0."""
    return 1 if sides[1] == country else 0


def player_value(word):
    """1289 1301-1317: +0x12 - 0x37, minus 10000 when signed above 5000, + 100 (16-bit)."""
    value = s16(word-0x37)
    if value > 5000:
        value = s16(value-10000)
    return s16(value+100)


def role_sums(team_record, read_player, read_ds):
    """1289: the four signed words DS:9B47+4k after its loop over squad slots 1..11.

    Every slot is read, a zero word or an unavailable player included. Role
    DS:0D7C[+6] k < 4 takes the value; k of 4 or 5 adds a signed half (idiv 2)
    to k-3 and k-2.
    """
    if len(team_record) != 191:
        raise ValueError('country record must be 191 bytes')
    sums = [0, 0, 0, 0]
    for slot in range(1, 12):
        word = int.from_bytes(team_record[2*slot-2:2*slot], 'little')
        player = read_player(word)
        if len(player) != 20:
            raise ValueError('player record must be 20 bytes')
        value = player_value(int.from_bytes(player[0x12:0x14], 'little'))
        role = read_ds(0xD7C+player[6], 1)
        if len(role) != 1:
            raise ValueError('truncated role table')
        role = role[0]
        if role > 5:
            raise ValueError(f'position {player[6]} selects role {role} outside 0..5')
        if role < 4:
            sums[role] += value
        else:
            sums[role-3] += idiv(value, 2)
            sums[role-2] += idiv(value, 2)
    return [s16(v) for v in sums]


def team_performance(country, match_set_up, in_match_menu_used, sides, read_country, read_player, read_ds):
    """TEAM rows 20..23 (keeper, defence, midfield, attack), or None when 157D draws none.

    match_set_up is DS:0C1E, in_match_menu_used DS:0C1F, sides the words
    DS:9B34 and DS:9B36. The bars belong to sides[side], which is not the panel's
    country when that country is not in the match.
    """
    if len(sides) != 2:
        raise ValueError('two match sides required')
    if not shown(match_set_up, in_match_menu_used):
        return None
    side = match_side(country, sides)
    sums = role_sums(read_country(sides[side]), read_player, read_ds)
    return dict(side=side, team=sides[side], bars=line_bars(sums, PERFORMANCE_ROW), role_sums=sums)
