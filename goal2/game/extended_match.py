"""[designed: owner #777/T235] Prepare the current pool for a selected-bench match."""
from goal2.engine.original_match.machine import MEM_SIZE
from goal2.game import campaign_pool, extended_squad
from goal2.game.watched_match import _prepare_match


def _span(image, address, size):
    if address <= 0 or address + size > min(len(image.memory), MEM_SIZE):
        raise ValueError('extended match allocation lies outside guest memory')
    return address, address + size


def prepare_extended_watched(state, original, fixture, *, competitive=False):
    """Return a private prepared Image and ordered filled additional words.

    [confirmed: F011; SDK Match._pool] Current manager at A923+1, manager1
    base at DS6D1A, eighty words in A927. Keep the original twenty/eighty
    record format and every unrelated flag/calendar byte.
    """
    slots = extended_squad.validate(state)
    image = _prepare_match(state, original, fixture, competitive=competitive)
    if state.squad_capacity == 20:
        return image, ()
    pool = campaign_pool.validate(state)
    country = state.managed_country
    if (state.countries[country][0x2E] != 129
            or any(row[0x2E] > 128 for n, row in enumerate(state.countries)
                   if n not in (0, country))):
        raise ValueError('extended match requires the declared sole manager1')
    base = image.rd(0x6D1A)
    if (base < 1 or image.far(0xA927) == 0 or image.rd(0xA927) + 2*(base + 80) > 65536
            or image.rd(0xA91F) + 135*3 > 65536
            or image.rd(0xA923) + 0x10E > 65536):
        raise ValueError('extended match has an invalid or wrapped manager/pool allocation')
    spans = [
        _span(image, image.far(0xA927) + 2*base, 160),
        _span(image, image.far(0xA91F), 135*3),
        _span(image, image.far(0xA923), 0x10E),
        _span(image, image.far(0xA91B), 3061*20),
        _span(image, image.far(0xA917), 129*191),
        _span(image, image.far(0xA92B), 0x4B48),
    ]
    for i, (lo, hi) in enumerate(spans):
        if any(lo < other_hi and other_lo < hi for other_lo, other_hi in spans[i+1:]):
            raise ValueError('extended match manager/pool allocations overlap')
    pool_at, managers, game = (spans[i][0] for i in range(3))
    image.memory[pool_at:pool_at + 160] = b''.join(w.to_bytes(2, 'little') for w in pool)
    image.memory[game + 1] = 1
    image.memory[managers + 129*3] = country
    if image.build_problems():
        raise ValueError('extended match projection changed immutable engine bytes')
    return image, tuple(w for w in slots if w is not None)
