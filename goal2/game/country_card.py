"""The original country card, as data. [designed: T89; owner, 2026-10-21]

Choosing a country shows its card and, with Space, its players (goal2.game.player_card), as the
original's country selection does (screenshots `country-select`, `m244-team-info-2030`).
Decoded fields carry their evidence. [derived: F034–F038; T197] Both career and
Core routes consume the delivered TEAM readers. [confirmed: original157D; T200]
This career route also exposes stored top-rank bytes and raw strip attributes;
monochrome leaves the original template's neutral strip glyphs without a colour overlay.
"""
from goal2.game import roles

NOT_DECODED = 'not decoded yet (G05)'
CONTINENTS = {1: 'Europe', 2: 'America', 3: 'Africa', 4: 'Asia'}
# [confirmed: F010 elements; screenshot country-select] The card's two tactic groups.
TEAM_TACTICS = (('defence system', 5), ('protection', 6), ('offside', 7))
PLAYER_DEFAULTS = (('positioning', 1), ('possession', 2), ('passing', 3), ('tackling', 4), ('marking', 8))
UNDECODED = ('status', 'skill', 'ranking top', 'strips', 'team skills', 'performance', 'characteristics')


def tactic_word(memory, element, bit):
    """[confirmed: F008] elements 1..4 at DS:6AA0 + 32 i + 16 bit and marking at DS:0E90 + 11 bit;
    [derived: the same DS:6AA0 table continues for i = 5..7 (`half pitch` … `offside trap` in
    memory), matching the original's country card for Denmark]."""
    if element == 8:
        return memory.pascal(0x0E90 + 11 * bit, 11)
    return memory.pascal(0x6AA0 + 32 * element + 16 * bit, 16)


def card(state, country, goaldat, *, memory=None, performance_context=...):
    """The country card of `country` in this state."""
    if type(country) is not int or not 1 <= country <= 128:
        raise ValueError('country must be 1..128')
    from goal2.game.team_card import TeamMemory
    memory = TeamMemory(state) if memory is None else memory
    record = memory.country_record(country)
    panels = memory.panels(country, performance_context=performance_context)
    words = [int.from_bytes(record[2 * i:2 * i + 2], 'little') for i in range(20)]
    # [confirmed: F008 squad list] the country's 20 player numbers at +0..+0x27; slots 1..11 are
    # the stored eleven (F024). [derived: F028 DS:0D5C line classes; screenshots country-select
    # (Denmark 5-4-1) and m244-team-info-2030 (Holland 4-4-2)] the formation counts the eleven's
    # defence, midfield and attack lines.
    codes, lines = roles.tables(state)
    eleven = [state.players[w][6] for w in words[:11]]
    formation = '-'.join(str(sum(1 for p in eleven if p < 14 and lines[p] == line)) for line in (1, 2, 3))
    tactics = state.country_tactics if country == state.managed_country else record[0x2D]
    def group(rows):
        return [(name, tactic_word(memory, element, tactics >> (element - 1) & 1)) for name, element in rows]
    initial = goaldat.manager_initials[country] if country < len(goaldat.manager_initials) else ''
    return {
        'country': country, 'name': goaldat.country_names[country], **panels,
        # [confirmed: F002 R001 manager names by country; F024 computer managers' names]
        'manager': (initial + ' ' if initial else '') + goaldat.manager_names[country],
        # [confirmed: F007] world rank +0x2B, continent +0x2C, rank within it +0x2A.
        'world': record[0x2B], 'continent': CONTINENTS.get(record[0x2C], NOT_DECODED), 'continental': record[0x2A],
        # [confirmed: F008/F002, original1771:157D; T200] Stored top ranks, not new history arithmetic.
        'top_world': record[0x29], 'top_continental': record[0x28],
        # Raw attributes are full bytes. None means no coloured overlay, not missing evidence.
        'strips': None if memory.byte(0xA964) else tuple(memory.read_ds(0x9D80 + 3 * country, 3)),
        'formation': formation, 'eleven': [codes[p] if p < 14 else '?' for p in eleven],
        'team_tactics': group(TEAM_TACTICS), 'player_defaults': group(PLAYER_DEFAULTS),
        'players': words, 'not_decoded': tuple(name for name in UNDECODED
            if name not in {'status', 'skill', 'team skills', 'performance', 'characteristics', 'ranking top', 'strips'}),
    }

