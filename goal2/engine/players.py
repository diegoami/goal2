"""The player array at the far pointer DS:A91B and the country array at DS:A917 of GOAL.EXE, read from a
savestate (T15, Q004).

Every constant comes from F002 / static/goal-exe-map.md:
- `2139:0000` allocates `[A917]` 0x603F bytes and `[A91B]` 0xEF24 bytes;
- the player record is 0x14 bytes (`mul 0x14` in `1771:96D3`, `97CC`, `3291` ...): 0xEF24 / 0x14 = 3061
  records, numbers 0..3060;
- the country record is 0xBF bytes (`mul 0xBF` in `1771:9A40`, `10E7`, `97CC`): 0x603F / 0xBF = 129
  records, numbers 0..128;
- `1771:9A40` fills the first 20 words of country record c with the player numbers (c-1)*20+1 .. c*20
  (seg_1771_14.asm:9B41-9B65), and `1771:96D3` writes the country into byte 0 of each of those players'
  records (seg_1771_13.asm:96ED-96F3). `check` tests both, so a pointer read wrong, or a record size off by
  one, fails before any field is used.
A far pointer is the dword offset:segment (little-endian, offset first) that `les di, ptr [..]` loads.
"""
PLAYERS_PTR = 0xA91B      # DS offset of the far pointer to the player array
COUNTRIES_PTR = 0xA917    # DS offset of the far pointer to the country array
PLAYER_SIZE = 0x14
PLAYERS_BYTES = 0xEF24    # 2139:0000's allocation
COUNTRY_SIZE = 0xBF
COUNTRIES_BYTES = 0x603F  # 2139:0000's allocation
N_PLAYERS = PLAYERS_BYTES // PLAYER_SIZE      # 3061
N_COUNTRIES = COUNTRIES_BYTES // COUNTRY_SIZE  # 129
SQUAD = 20                # players named by a country record (its first 20 words)
SQUAD_COUNTRIES = 128     # countries 1..128 own squads (1771:9A40 loops to 0x80)


def far_pointer(state, off):
    """(segment, offset, linear address) of the far pointer at DS:off."""
    raw = state.ds_bytes(off, 4)
    o, s = int.from_bytes(raw[0:2], "little"), int.from_bytes(raw[2:4], "little")
    return s, o, s * 16 + o


def players(state):
    """The 0xEF24 bytes of the player array."""
    return state.memory(far_pointer(state, PLAYERS_PTR)[2], PLAYERS_BYTES)


def countries(state):
    """The 0x603F bytes of the country array."""
    return state.memory(far_pointer(state, COUNTRIES_PTR)[2], COUNTRIES_BYTES)


def record(array, size, n):
    return array[n * size:(n + 1) * size]


def squad(country_array, c):
    """The 20 player numbers in the first 20 words of country record c."""
    r = record(country_array, COUNTRY_SIZE, c)
    return [int.from_bytes(r[2 * i:2 * i + 2], "little") for i in range(SQUAD)]


def check(player_array, country_array):
    """Problems found (empty when the arrays sit where the code puts them): the lengths are the
    allocations; country c (1..128) names players (c-1)*20+1 .. c*20; each of them has c in byte 0."""
    problems = []
    if len(player_array) != PLAYERS_BYTES:
        problems.append(f"player array {len(player_array)} bytes, not 0x{PLAYERS_BYTES:X}")
    if len(country_array) != COUNTRIES_BYTES:
        problems.append(f"country array {len(country_array)} bytes, not 0x{COUNTRIES_BYTES:X}")
    if problems:
        return problems
    for c in range(1, SQUAD_COUNTRIES + 1):
        want = list(range((c - 1) * SQUAD + 1, c * SQUAD + 1))
        got = squad(country_array, c)
        if got != want:
            problems.append(f"country {c}: squad words {got[:3]}... not {want[:3]}...")
            continue
        bad = [p for p in want if record(player_array, PLAYER_SIZE, p)[0] != c]
        if bad:
            problems.append(f"country {c}: players {bad[:3]} do not hold {c} in byte 0")
    return problems


# The names (T16, Q009). `2139:0000` allocates [9B6C] 0x8387 bytes and [9B70] 0xBF5 bytes
# (`seg_2139_01.asm:0014`-`002B`): 0x8387 = 3061 * 11 and 0xBF5 = 3061 * 1. `1771:2E93` (the routine that
# builds the name the screens print) prints `[9B70] + n` (one character), a space, then the Pascal string
# of 11 bytes at `[9B6C] + 11 n` (`seg_1771_04.asm:2E9A`-`2ECC`: `mul 0xb`).
NAMES_PTR = 0x9B6C        # DS offset of the far pointer to the surnames (11-byte Pascal strings)
INITIALS_PTR = 0x9B70     # DS offset of the far pointer to the initials (1 byte each)
NAME_SIZE = 11
NAMES_BYTES = 0x8387
INITIALS_BYTES = 0xBF5


def surnames(state):
    """The 0x8387 bytes of the surname array."""
    return state.memory(far_pointer(state, NAMES_PTR)[2], NAMES_BYTES)


def initials(state):
    """The 0xBF5 bytes of the initials array."""
    return state.memory(far_pointer(state, INITIALS_PTR)[2], INITIALS_BYTES)


def full_name(surname_array, initial_array, n):
    """The name `1771:2E93` builds for player n: the initial, a space, the Pascal string of 11 bytes."""
    rec = surname_array[n * NAME_SIZE:(n + 1) * NAME_SIZE]
    return chr(initial_array[n]) + " " + rec[1:1 + rec[0]].decode("cp437")
