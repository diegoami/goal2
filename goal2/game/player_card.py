"""The complete original player card, as data. [designed: T88; field contract T84-preflight]

[confirmed: goal2-archaeology F008 at 8a804db (unchanged at 0ef880e), E007-r0009..r0012] Every
field below is what the original's player screen (1771:42BC) prints for a record, read from the
game's own memory tables. No attribute total is shown (#286): record +4 only scales the skill
bars. Roles are one-letter codes (#283). A value outside a supported domain is unavailable,
never invented.
"""
from goal2.game import roles
from goal2.game.skills import load_class_table, load_profile_table, skills
from goal2.game.state import _wrap_raw

SKILLS = ('keeping', 'kicking', 'tackling', 'heading', 'marking', 'passing', 'crossing',
          'feinting', 'control', 'dribbling', 'shooting', 'penalties')
TACTICS = ('position', 'possession', 'passing', 'tackling')
UNAVAILABLE = 'unavailable'


class _Memory:
    """Bounded reads of the original's tables from one state's memory."""
    def __init__(self, state):
        self.raw = _wrap_raw(state.vga, state.mem)

    def byte(self, address):
        return self.raw.ds_bytes(address, 1)[0]

    def pascal(self, address, slot):
        data = self.raw.ds_bytes(address, slot)
        if not data[0] < slot:
            raise ValueError(f'string at DS:{address:04X} exceeds its {slot}-byte slot')
        return data[1:1 + data[0]].decode('cp437')


def _word(memory, index_table, value):
    """[confirmed: F008] A characteristic word: DS:6EB4 + 16 * DS:<index_table>[value]."""
    return memory.pascal(0x6EB4 + 16 * memory.byte(index_table + value), 16)


def characteristics(memory, record):
    """[confirmed: F008 right panel] (name, word, bar of 14, raw value) for the five
    characteristics; the raw value is the byte the word and bar come from."""
    out = []
    hardness = (record[5] - (record[3] & 1)) & 255
    out.append(('hardness',) + ((_word(memory, 0x78C4, hardness), hardness * 14 // 16) if hardness <= 16 else (UNAVAILABLE, None)) + (hardness,))
    fitness, energy, morale = record[0x0D], record[0x0E], record[0x0C]
    out.append(('fitness',) + ((_word(memory, 0x78D5, fitness), fitness * 14 // 32) if fitness <= 32 else (UNAVAILABLE, None)) + (fitness,))
    out.append(('energy',) + ((_word(memory, 0x78F6, energy), energy * 14 // 32) if energy <= 32 else (UNAVAILABLE, None)) + (energy,))
    out.append(('morale', _word(memory, 0x78A3, min(morale, 0x20)), morale * 14 // 32 if morale < 0x20 else 0, morale))
    difference = record[3] - record[5]
    if difference < 0:
        # [designed: T84] The original's signed remainder of a negative difference is unresolved.
        out.append(('leadership', UNAVAILABLE, None, None))
    else:
        value = difference % 8
        if record[1] < 0x15:
            value //= 2
        out.append(('leadership', memory.pascal(0x6EB4 + 16 * memory.byte(0x7917 + value), 16), value * 14 // 7, value))
    return out


def tactics(memory, record, team_tactics):
    """[confirmed: F008 tactics panel] Four (row, word, personal) and the mark line."""
    rows = []
    for i, name in enumerate(TACTICS, 1):
        personal = bool(record[0x0F] & (1 << (i + 3)))
        bit = (record[0x0F] if personal else team_tactics) >> (i - 1) & 1
        if record[6] == 0 and i in (1, 3):
            word = memory.pascal((0x0EA6 if i == 1 else 0x0EC6) + 16 * bit, 16)
        else:
            word = memory.pascal(0x6AA0 + 32 * i + 16 * bit, 16)
        rows.append((name, word, personal))
    if record[6] < 2:
        mark = ''
    elif record[0x10] & 0x80:
        mark = 'Protect zone P'
    else:
        mark = memory.pascal(0x0E90 + 11 * (team_tactics >> 7 & 1), 11)
    return rows, mark


def readiness(record):
    """[confirmed: F008 status; T84 contract priority] The status line before a match."""
    status = record[0x10]
    if status & 0x80:return 'suspended'
    if record[0x0E] == 0:return 'injured'
    if status & 0x10:return 'booked'
    if status & 0x20:return 'sent off'
    if status & 0x04:return 'substituted'
    return 'ready to play'


def card(state, word, goaldat, *, team_tactics=None):
    """The complete card of player `word` in this state. `team_tactics` defaults to his country's
    stored byte +0x2D (the managed country's live tactics are state.country_tactics)."""
    record = state.players[word]
    if len(record) != 20:
        raise ValueError('invalid player record')
    memory = _Memory(state)
    country = record[0]
    if team_tactics is None:
        team_tactics = (state.country_tactics if country == state.managed_country
                        else state.countries[country][0x2D])
    table = roles.tables(state);names = roles.names(state)
    club = record[7]
    position = names[record[6]] if record[6] < 14 else UNAVAILABLE
    club_position = names[club] if club < 14 else UNAVAILABLE
    if club < 14:
        inches = memory.byte(0x0E46 + club) + memory.byte(0x0E54 + word % 12)
        height = f"{inches // 12}'{inches % 12:2}\""  # the original pads the inches: 6' 0"
        if record[5] + record[2] == 30:
            foot = 'two footed'
        else:
            side = memory.byte(0x0E60 + 14 * memory.byte(0x0E7C + word % 3) + club)
            foot = memory.pascal(0x0F2C + 6 * side, 6) + ' foot'
        bars = skills(record, load_class_table(_wrap_raw(state.vga, state.mem)),
                      load_profile_table(_wrap_raw(state.vga, state.mem)))
    else:
        height = foot = UNAVAILABLE;bars = [None] * 12
    performance = record[0x12] | record[0x13] << 8
    flags = record[0x10]
    cards = [label for bit, label in ((0x08, 'carried booking'), (0x10, 'booked'), (0x20, 'sent off')) if flags & bit]
    tactic_rows, mark = tactics(memory, record, team_tactics)
    code, line = roles.role(state, record[6], cache=table)
    return {
        # [confirmed: F008] the card's name is the initial and the surname.
        'id': word, 'name': goaldat.player_names[word], 'country': country,
        'full_name': (goaldat.player_initials[word] + ' ' if word < len(goaldat.player_initials) else '') + goaldat.player_names[word],
        'role': code, 'line': line, 'club_role': roles.role(state, club, cache=table)[0],
        'age': record[1], 'caps': record[8] | record[9] << 8, 'goals': record[0x0A] | record[0x0B] << 8,
        'height': height, 'foot': foot, 'position': position, 'club_position': club_position,
        'cards': cards, 'readiness': readiness(record),
        # [designed: T84] The original's bucket glyphs are unresolved (archaeology #346): raw word only.
        'performance': None if performance == 0x7FFF else performance,
        'skills': list(zip(SKILLS, bars)), 'characteristics': characteristics(memory, record),
        'tactics': tactic_rows, 'mark': mark,
    }
