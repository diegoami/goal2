"""[designed: T170bf] One original standalone R/C operation on a private state."""

from goal2.engine.original_match import Image, port
from goal2.engine.original_match.image import COUNTRY_SIZE, GAME_PTR, PLAYERS_PTR, PLAYER_SIZE, N_PLAYERS
from goal2.engine.original_match.machine import MEM_SIZE
from goal2.engine.original_match.port.engine import PortMachine
from goal2.game import engine_tables
from goal2.game.season import canonical_hash


_PREPARE = '1771:52CC'
_EDIT = '1771:4952'
_EXIT = '1771:5532'


def _call(machine, target, args, return_to):
    # [derived: T183a] Use a private far-call frame, outside any retained Match.
    ss, sp = machine.seg(0x3052), 0x3000
    stop = machine.far_call(target, args, return_to, ss, sp)
    machine.set_reg('bp', 0x3456)
    machine.run(stop, fresh=True)
    if machine.frames or machine.pc() != stop or machine.reg('sp') != sp + 4 + 2 * len(args):
        raise RuntimeError(f'{target} did not return with its original ABI')


def _context(image):
    if image.rd(0xC1E, 1) or image.rd(0xC1F, 1):
        raise ValueError('A standalone position edit needs a manager boundary.')
    game = image.far(GAME_PTR)
    manager = image.memory[game + 1]
    managed = image.managed_countries()
    if not 1 <= manager <= 6 or len(managed) != 1:
        raise ValueError('A standalone position edit needs one active native manager.')
    country, = managed
    record = image.countries()[country]
    if (image.memory[image.far(0xA91F) + 3 * (manager + 0x80)] != country
            or len(record) != COUNTRY_SIZE or record[0x2E] != manager + 0x80
            or image.memory[game + 0x47 + manager]):
        raise ValueError('A standalone position edit needs one active native manager.')

    # [confirmed: F011, E44F pool reader] Reference the current manager's actual A927 list.
    base = image.rd(0x6D18 + 2 * manager)
    pool_at = image.far(0xA927) + 2 * base
    if image.rd(0xA927) + 2 * (base + 80) > 65536 or pool_at + 160 > MEM_SIZE:
        raise ValueError('The current manager pool is outside its supported span.')
    words = tuple(int.from_bytes(image.memory[at:at + 2], 'little')
                  for at in range(pool_at, pool_at + 160, 2))
    return country, image.squad(country), words


def validate_selection(player, key):
    if type(key) is not str or key not in ('R', 'C'):
        raise ValueError('A standalone position edit needs the original R or C key.')
    if type(player) is not int or not 1 <= player < N_PLAYERS:
        raise ValueError('A standalone position edit needs a valid player word.')


def _position_record(image, player):
    at = image.far(PLAYERS_PTR) + PLAYER_SIZE * player
    if at + PLAYER_SIZE > MEM_SIZE:
        raise ValueError('The selected native player record is outside guest memory.')
    position, club = image.memory[at + 6:at + 8]
    if position >= 14 or club >= 14:
        raise ValueError('The player has an unsupported position code.')
    return at, position, club


def position_codes(state, player):
    """[derived: T170bf] Read the saved position and club position for an admitted word."""
    image = Image.from_state(state, engine_tables.load())
    _, position, club = _position_record(image, player)
    return position, club


def position_goal(position, club, key):
    return club if key == 'C' else (position + 1) % 14


def edit_position(state, player, key):
    """[designed: T170bf] Produce a detached candidate for one original R or C."""
    validate_selection(player, key)
    tables = engine_tables.load()
    image = Image.from_state(state, tables)
    country, squad, pool = _context(image)
    if squad.count(player) + pool.count(player) != 1:
        raise ValueError('Select a player in the current native squad or pool.')
    player_at, position, club = _position_record(image, player)

    machine = PortMachine(image.memory, image.load)
    specs = []
    for registry, variant in port.load(['all']):
        real = port.Registry(registry.name, registry.doc)
        for entry in registry.entries.values():
            if entry.stub is None:
                real._add(entry)
        specs.append((real, variant))
    port.install(machine, specs)
    visits = []

    def observe(replay):
        if not replay:
            visits.append((machine.stack_word(4), machine.rd(0xA976, 1)))

    machine.at(_EDIT, observe)
    # [confirmed: E44F E484/E491/E72A/E7E7] Run the original preparation, position and exit routines.
    machine.wr(0xC20, 0, 1)
    _call(machine, _PREPARE, (country,), '0791:E491')
    byte = ord(key)
    machine.wr(0xA976, byte | (byte << 8))
    _call(machine, _EDIT, (player,), '0791:E72A')
    _call(machine, _EXIT, (), '0791:E7E7')
    new_position = machine.read(player_at + 6, 1)[0]
    expected = position_goal(position, club, key)
    if visits != [(player, byte)] or new_position != expected:
        raise RuntimeError('The original position edit did not complete for the selected player.')
    image.memory[:MEM_SIZE] = machine.read(0, MEM_SIZE)
    value = image.state(tables)
    return dict(state=value, input_hash=canonical_hash(state), output_hash=canonical_hash(value),
                player=player, position=new_position, club_position=club)
