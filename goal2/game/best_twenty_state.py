"""[designed: T183b] Transient assistant projection for legacy opening careers.

[derived: F023/F031; T63, T183a] GameState's current metadata is authoritative;
its backing halftime flags/calendar are not a native season. Only the supported
opening qualifying phase is projected here. This is not a route bootstrap.
"""
from copy import deepcopy
from dataclasses import dataclass

from goal2.engine.original_match import Image
from goal2.engine.original_match.image import MEM_BASE
from goal2.engine.original_match.machine import MEM_SIZE
from goal2.game import campaign_pool, engine_tables
from goal2.game.campaign import opening_calendar
from goal2.game.campaign_rounds import validate_state
from goal2.game.season import canonical_hash
from goal2.game.watched_match import engine_year


@dataclass(frozen=True)
class PreparedAssistant:
    """Private snapshot and sealed request. Publication belongs to the owner."""
    source: object
    native: dict
    input_hash: str


def _span(image, address, size):
    if address < 0 or address + size > MEM_SIZE:
        raise ValueError('assistant data lies outside the supported guest allocation')
    return address


def _put_words(memory, address, words):
    memory[address:address + 2*len(words)] = b''.join(w.to_bytes(2, 'little') for w in words)


def prepare(state):
    """Snapshot a current opening career; never regenerate players or use a tour guess."""
    source = deepcopy(state)
    campaign = source.campaign
    if campaign is None or campaign.world is None:
        raise ValueError('The assistant needs a career with its complete current calendar')
    if campaign.cycle != 1 or campaign.stage != opening_calendar(campaign.start_year)[1]:
        raise ValueError('This career needs its native season calendar before asking the assistant')
    if len(source.players) != 3061 or any(len(p) != 20 for p in source.players):
        raise ValueError('Invalid player records')
    if len(source.countries) != 129 or any(len(c) != 191 for c in source.countries):
        raise ValueError('Invalid country records')
    campaign.__post_init__()
    validate_state(source)
    pool = campaign_pool.validate(source)
    rows = campaign.world.fixtures
    low = 1 if campaign.stage == 2 else 1361
    expected = 768 if campaign.stage == 2 else 640
    if len(rows) != expected or [r.fixture_id for r in rows] != [f'original:{n}' for n in range(low, low + expected)]:
        raise ValueError('The assistant needs the complete supported opening calendar')
    for row in rows:
        if row.kind not in (1, campaign.stage):
            raise ValueError('Unsupported opening fixture kind')
        if row.kind == 1 and source.countries[row.side_a][0x2C] != source.countries[row.side_b][0x2C]:
            raise ValueError('A rearranged overseas calendar needs its native season context')
    if any(any(score >= 0xFE for score in row['score']) for row in campaign.world.results):
        raise ValueError('A played score cannot use an unplayed fixture marker')
    country = source.managed_country
    if source.countries[country][0x2E] != 129 or any(c[0x2E] > 128 for n,c in enumerate(source.countries) if n not in (0,country)):
        raise ValueError('The assistant projection supports one active manager')

    image = Image.from_memory_component(source.mem)
    # [derived: T63] Preserve immutable DS:0E6C and opaque country+2F; neither
    # the legacy UI clock nor its separate captain is an engine record write.
    players = _span(image, image.far(0xA91B), 3061*20)
    countries = _span(image, image.far(0xA917), 129*191)
    image.memory[players:players + 3061*20] = b''.join(source.players)
    image.memory[countries:countries + 129*191] = b''.join(source.countries)
    squad = list(source.starting_eleven) + [w for w in source.managed_squad if w not in source.starting_eleven]
    _put_words(image.memory, countries + country*191, squad)
    image.memory[countries + country*191 + 0x2D] = source.country_tactics
    game = _span(image, image.far(0xA923), 0x10E)
    managers = _span(image, image.far(0xA91F), 135*3)
    image.memory[managers + 129*3] = country
    image.memory[game + 1] = 1
    # [confirmed: 1771:6730/6755] The opening qualifying build clears finals.
    image.memory[game + 0x14:game + 0x1A] = bytes(6)
    image.memory[game + 0x48] = 0
    image.memory[image.DS*16 + 0xC1E:image.DS*16 + 0xC20] = bytes(2)
    base = image.rd(0x6D1A)
    if image.rd(0xA927) + 2*(base + 80) > 65536:
        raise ValueError('Unsupported wrapped pool allocation')
    pool_at = _span(image, image.far(0xA927) + 2*base, 160)
    _put_words(image.memory, pool_at, pool)
    fixtures = _span(image, image.far(0xA92B), 0x4B48)
    lists = _span(image, image.far(0xA92F), 129*72)
    country_lists = [[] for _ in range(129)]
    completed = {row['fixture_id']:row for row in campaign.world.results}
    for n,row in enumerate(rows, low):
        address = fixtures + 8*(n - 1)
        result = completed.get(row.fixture_id)
        image.memory[address] = result['score'][0] if result else (0xFE if country in (row.side_a,row.side_b) else 0xFF)
        if result:
            image.memory[address + 1] = result['score'][1]
        # +1's unplayed group and +3 are opaque to the assistant; do not invent
        # them or publish this projection as a full native calendar.
        image.memory[address + 2] = row.kind
        _put_words(image.memory, address + 4, [row.side_a,row.side_b])
        country_lists[row.side_a].append(n)
        country_lists[row.side_b].append(n)
    for n,words in enumerate(country_lists):
        # [confirmed: 1771:5D02] New entries are appended after a left shift.
        words = words[-36:]
        _put_words(image.memory, lists + 72*n, [0]*(36 - len(words)) + words)
    _put_words(image.memory, game + 0x26, [low + len(completed),low + len(rows)])
    _put_words(image.memory, game + 0x38, [engine_year(campaign),campaign.start_year])
    image.memory[game + 0x3C] = campaign.stage
    image.memory[game + 0x40] = int(campaign.stage >= 5)
    image.memory[image.DS*16 + 0x7B62:image.DS*16 + 0x7B64] = source.rng_seed_7b62.to_bytes(2,'little')
    image.memory[image.DS*16 + 0x8336:image.DS*16 + 0x8338] = source.rng_seed_8336.to_bytes(2,'little')
    image.memory = image.memory[:MEM_SIZE]
    value = image.state(engine_tables.load())
    return PreparedAssistant(source, value, canonical_hash(value))


def candidate(prepared, answer):
    """Validate a completed private reply; return a candidate without publishing it."""
    if canonical_hash(prepared.native) != prepared.input_hash:
        raise ValueError('Assistant input changed')
    if not isinstance(answer, dict) or answer.get('allowed') is not True or answer.get('refusal') is not None:
        raise ValueError('The assistant did not complete an allowed selection')
    tables = engine_tables.load()
    before = Image.from_state(prepared.native, tables)
    after = Image.from_state(answer['state'], tables)
    if after.load != before.load or after.header != before.header or any(
            after.far(ptr) != before.far(ptr) for ptr in
            (0xA91B,0xA917,0xA91F,0xA923,0xA927,0xA92B,0xA92F)) or after.rd(0x6D1A) != before.rd(0x6D1A):
        raise ValueError('Assistant changed its storage identity')
    state = deepcopy(prepared.source)
    country = state.managed_country
    if answer.get('country') != country or answer.get('manager') != 1:
        raise ValueError('Assistant replied for another manager')
    squad = after.squad(country)
    pool_at = after.far(0xA927) + 2*after.rd(0x6D1A)
    pool = [int.from_bytes(after.memory[pool_at + 2*i:pool_at + 2*i + 2], 'little') for i in range(80)]
    if answer.get('squad') != squad or answer.get('pool') != pool:
        raise ValueError('Assistant selection differs from its records')
    original = state.managed_squad + campaign_pool.validate(state)
    if len(set(squad + pool)) != 100 or set(squad + pool) != set(original):
        raise ValueError('Assistant changed the squad/pool identities')
    players = [bytes(after.memory[after.far(0xA91B) + 20*i:after.far(0xA91B) + 20*(i+1)]) for i in range(3061)]
    countries = [bytes(after.memory[after.far(0xA917) + 191*i:after.far(0xA917) + 191*(i+1)]) for i in range(129)]
    if players != state.players or any(c != old for n,(c,old) in enumerate(zip(countries,state.countries)) if n != country):
        raise ValueError('Assistant changed unrelated player/country records')
    if countries[country][40:] != before.countries()[country][40:]:
        raise ValueError('Assistant changed unrelated managed-country data')
    for ptr,size in ((0xA91F,135*3),(0xA923,0x10E)):
        a,b=before.far(ptr),after.far(ptr)
        if before.memory[a:a+size] != after.memory[b:b+size]:
            raise ValueError('Assistant changed unrelated manager/game records')
    if any(before.rd(off) != after.rd(off) for off in (0x7B62,0x8336)):
        raise ValueError('Assistant changed RNG')
    # Preserve backing code/opaque context, installing every original call's
    # actual memory delta rather than the transient calendar projection.
    memory = bytearray(state.mem)
    for start in range(0, MEM_SIZE, 4096):
        left,right=before.memory[start:start+4096],after.memory[start:start+4096]
        if left != right:
            for i,(a,b) in enumerate(zip(left,right)):
                if a != b:memory[MEM_BASE + start + i]=b
    for ptr,data in ((0xA91B,b''.join(players)),(0xA917,b''.join(countries))):
        address=before.far(ptr);memory[MEM_BASE + address:MEM_BASE + address + len(data)]=data
    raw_pool=b''.join(w.to_bytes(2,'little') for w in pool)
    memory[MEM_BASE + pool_at:MEM_BASE + pool_at + 160]=raw_pool
    state.mem=bytes(memory)
    state.players,state.countries=players,countries
    state.managed_squad=list(squad)
    state.starting_eleven=list(squad[:11])
    if state.captain not in state.starting_eleven:
        state.captain=0
    state.campaign.reserve_ids=list(pool)
    campaign_pool.validate(state)
    validate_state(state)
    return state
