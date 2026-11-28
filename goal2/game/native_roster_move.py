"""[designed: T170bi] Original two-Enter roster edit on a detached native state."""

from goal2.engine.original_match import Image
from goal2.engine.original_match.image import N_PLAYERS
from goal2.engine.original_match.machine import MEM_SIZE
from goal2.engine.original_match.port.engine import PortMachine
from goal2.game import engine_tables
from goal2.game.native_squad_menu import (
    EXIT, PREPARE, STACK_POINTER, STACK_SEGMENT, far_menu_call, install_menu_ports, manager_roster,
)
from goal2.game.season import canonical_hash


_PARENT_BP = 0x3200
_REFUSALS = {'0791:DC3D': 'finals', '0791:DC68': 'tour'}


class _Acknowledgement:
    """[confirmed: F031 DBFA] Acknowledge the guest's native refusal box."""

    def __init__(self, machine):
        self.machine = machine

    def key(self, site):
        self.machine.wr(0xA976, 0x0D0D)
        return 13

    def keypressed(self, site):
        return True


def _write_word(machine, at, word):
    machine.write(at, word.to_bytes(2, 'little'))


def _enter(machine, parent, roster, side, index):
    # [confirmed: E44F E667, DEA6/DDCB] Supply the actual parent frame and cursor
    # for the current pane. The previous Enter's mark remains in that frame.
    _write_word(machine, parent - 5, side + 1)
    if side == 0:
        machine.wr(0xC1B, index + 1)
    else:
        # [confirmed: E7D9] Keep top and row inside the original 21-row pane.
        top = min(index + 1, 80 - 21 + 1)
        _write_word(machine, roster.game + 0x52 + 2 * roster.manager, top)
        _write_word(machine, roster.game + 0x5E + 2 * roster.manager, index + 2 - top)
    ss, sp = machine.seg(STACK_SEGMENT), STACK_POINTER
    stop = machine.far_call('0791:DEA6', (), '0791:E672', ss, sp)
    # [confirmed: E667/E672] This is a near call. The second stack word is the parent BP.
    _write_word(machine, ss * 16 + sp + 2, _PARENT_BP)
    machine.set_reg('bp', _PARENT_BP)
    machine.run(stop, fresh=True)
    if (machine.frames or machine.pc() != stop or machine.reg('sp') != sp + 4
            or machine.reg('bp') != _PARENT_BP):
        raise RuntimeError('The squad Enter did not return with its original near ABI.')


def _locate(rosters, word):
    side = int(word not in rosters[0])
    return side, rosters[side].index(word)


def move_player(state, first, second):
    """Run both original Enter operations, returning a private candidate or refusal."""
    players = [first, second]
    if any(type(word) is not int or not 1 <= word < N_PLAYERS for word in players) or first == second:
        raise ValueError('Select two distinct native player words.')

    tables = engine_tables.load()
    image = Image.from_state(state, tables)
    roster = manager_roster(image)
    source_words = roster.words(lambda at, size: image.memory[at:at + size])
    squad, pool = source_words
    if (any(squad.count(word) + pool.count(word) != 1 for word in players)
            or all(word in pool for word in players)):
        raise ValueError('Select two squad players or one squad and one pool player.')

    machine = PortMachine(image.memory, image.load)
    installed = install_menu_ports(machine, keys=_Acknowledgement(machine))
    swaps, refusals = [], []

    def witness(replay):
        if not replay:
            swaps.append(roster.words(machine.read))

    def refusal(replay):
        if not replay and machine.stack_word(8) & 255:
            caller = machine.where(machine.stack_word(2), machine.stack_word(0))
            refusals.append(_REFUSALS[caller])

    machine.at('0791:DF29', witness)
    machine.at('214B:1765', refusal)

    machine.wr(0xC20, 0, 1)
    far_menu_call(machine, PREPARE, (roster.country,), '0791:E491')
    prepared = roster.words(machine.read)
    side_a, index_a = _locate(prepared, first)
    side_b, index_b = _locate(prepared, second)
    expected = [list(pane) for pane in prepared]
    expected[side_a][index_a] = second
    expected[side_b][index_b] = first

    parent = machine.seg(STACK_SEGMENT) * 16 + _PARENT_BP
    machine.write(parent - 18, bytes(18))
    _write_word(machine, parent + 6, roster.country)
    _enter(machine, parent, roster, side_a, index_a)
    if not refusals:
        marked_index = index_a + 1 if side_a == 0 else roster.pool_base + index_a
        if (machine.read(parent - 1, 1) != b'\x01' or machine.word_at(parent - 7) != side_a + 1
                or machine.word_at(parent - 9) != marked_index):
            raise RuntimeError('The original first Enter did not mark the selected word.')
        _enter(machine, parent, roster, side_b, index_b)
    if installed.calls.get('0791:DBFA', 0) != int(side_a != side_b):
        raise RuntimeError('The original pool gate was not reached exactly once.')

    input_hash = canonical_hash(state)
    if refusals:
        if len(refusals) != 1 or swaps or roster.words(machine.read) != prepared:
            raise RuntimeError('The original pool refusal changed the roster.')
        return dict(state=None, players=players, refusal=refusals[0], input_hash=input_hash, output_hash=None)
    if swaps != [tuple(tuple(pane) for pane in expected)] or machine.read(parent - 1, 1) != b'\x00':
        raise RuntimeError('The original word swap differs from the requested pair.')

    far_menu_call(machine, EXIT, (), '0791:E7E7')
    after_squad, after_pool = roster.words(machine.read)
    for after, wanted in ((after_squad[:11], expected[0][:11]), (after_squad[11:], expected[0][11:]),
                          (after_pool, expected[1])):
        if sorted(after) != sorted(wanted):
            raise RuntimeError('The original sort changed roster membership.')
    # [designed: T170bi] Restore the host-owned cursors used to address the picks.
    cursors = (image.DS * 16 + 0xC1B, roster.game + 0x52 + 2 * roster.manager,
               roster.game + 0x5E + 2 * roster.manager)
    for at in cursors:
        machine.write(at, image.memory[at:at + 2])
    image.memory[:MEM_SIZE] = machine.read(0, MEM_SIZE)
    candidate = image.state(tables)
    return dict(state=candidate, players=players, refusal=None, input_hash=input_hash,
                output_hash=canonical_hash(candidate))
