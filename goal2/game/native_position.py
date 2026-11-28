"""[designed: T170bf] One original standalone R/C operation on a private state."""

from goal2.engine.original_match import Image
from goal2.engine.original_match.image import PLAYERS_PTR, PLAYER_SIZE, N_PLAYERS
from goal2.engine.original_match.machine import MEM_SIZE
from goal2.engine.original_match.port.engine import PortMachine
from goal2.game import engine_tables
from goal2.game.native_squad_menu import EXIT, PREPARE, far_menu_call, install_menu_ports, manager_roster
from goal2.game.season import canonical_hash


_EDIT = '1771:4952'


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
    roster = manager_roster(image)
    squad, pool = roster.words(lambda at, size: image.memory[at:at + size])
    if squad.count(player) + pool.count(player) != 1:
        raise ValueError('Select a player in the current native squad or pool.')
    player_at, position, club = _position_record(image, player)

    machine = PortMachine(image.memory, image.load)
    install_menu_ports(machine)
    visits = []

    def observe(replay):
        if not replay:
            visits.append((machine.stack_word(4), machine.rd(0xA976, 1)))

    machine.at(_EDIT, observe)
    # [confirmed: E44F E484/E491/E72A/E7E7] Run the original preparation, position and exit routines.
    machine.wr(0xC20, 0, 1)
    far_menu_call(machine, PREPARE, (roster.country,), '0791:E491')
    byte = ord(key)
    machine.wr(0xA976, byte | (byte << 8))
    far_menu_call(machine, _EDIT, (player,), '0791:E72A')
    far_menu_call(machine, EXIT, (), '0791:E7E7')
    new_position = machine.read(player_at + 6, 1)[0]
    expected = position_goal(position, club, key)
    if visits != [(player, byte)] or new_position != expected:
        raise RuntimeError('The original position edit did not complete for the selected player.')
    image.memory[:MEM_SIZE] = machine.read(0, MEM_SIZE)
    value = image.state(tables)
    return dict(state=value, input_hash=canonical_hash(state), output_hash=canonical_hash(value),
                player=player, position=new_position, club_position=club)
