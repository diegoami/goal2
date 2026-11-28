"""[derived: T170bf/T170bi] Shared manager context and private calls for original squad edits."""

from dataclasses import dataclass
from struct import unpack

from goal2.engine.original_match import port
from goal2.engine.original_match.image import COUNTRIES_PTR, COUNTRY_SIZE, GAME_PTR
from goal2.engine.original_match.machine import MEM_SIZE


PREPARE = '1771:52CC'
EXIT = '1771:5532'
STACK_SEGMENT = 0x3052
STACK_POINTER = 0x3000


@dataclass(frozen=True)
class ManagerRoster:
    country: int
    manager: int
    game: int
    squad_at: int
    pool_at: int
    pool_base: int

    def words(self, read):
        return unpack('<20H', read(self.squad_at, 40)), unpack('<80H', read(self.pool_at, 160))


def manager_roster(image):
    if image.rd(0xC1E, 1) or image.rd(0xC1F, 1):
        raise ValueError('A standalone squad edit needs a manager boundary.')
    game = image.far(GAME_PTR)
    # [confirmed: F031, 1771:027B] The saved game block spans 0x10E bytes.
    if game + 0x10E > MEM_SIZE:
        raise ValueError('The current game block is outside guest memory.')
    manager = image.memory[game + 1]
    managed = image.managed_countries()
    if not 1 <= manager <= 6 or len(managed) != 1:
        raise ValueError('A standalone squad edit needs one active native manager.')
    country, = managed
    squad_at = image.far(COUNTRIES_PTR) + COUNTRY_SIZE * country
    manager_at = image.far(0xA91F) + 3 * (manager + 0x80)
    if (manager_at >= MEM_SIZE or squad_at + COUNTRY_SIZE > MEM_SIZE
            or image.memory[manager_at] != country or image.memory[squad_at + 0x2E] != manager + 0x80
            or image.memory[game + 0x47 + manager]):
        raise ValueError('A standalone squad edit needs one active native manager.')

    # [confirmed: F011, E44F pool reader] The native manager's actual A927 list.
    base = image.rd(0x6D18 + 2 * manager)
    pool_at = image.far(0xA927) + 2 * base
    if image.rd(0xA927) + 2 * (base + 80) > 65536 or pool_at + 160 > MEM_SIZE:
        raise ValueError('The current manager pool is outside its supported span.')
    return ManagerRoster(country, manager, game, squad_at, pool_at, base)


def install_menu_ports(machine, *, keys=None):
    specs = []
    for registry, variant in port.load(['all']):
        real = port.Registry(registry.name, registry.doc)
        for entry in registry.entries.values():
            if entry.stub is None:
                real._add(entry)
        specs.append((real, variant))
    return port.install(machine, specs, keys=keys)


def far_menu_call(machine, target, args, return_to):
    # [derived: T183a] Use a private far-call frame outside any retained Match.
    ss, sp = machine.seg(STACK_SEGMENT), STACK_POINTER
    stop = machine.far_call(target, args, return_to, ss, sp)
    machine.set_reg('bp', 0x3456)
    machine.run(stop, fresh=True)
    if machine.frames or machine.pc() != stop or machine.reg('sp') != sp + 4 + 2 * len(args):
        raise RuntimeError(f'{target} did not return with its original ABI')
