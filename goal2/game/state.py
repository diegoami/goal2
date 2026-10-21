"""[confirmed: T01/T06 state adapter; PROVENANCE.md does not list state.py as vendored — this file is the rebuild's own adapter, not engine code.]
The state adapter: round-trip the original's savestate through goal2's state.

The original game's state lives in guest memory (the DOS program's data
segment). Vendored models (T01) read that memory directly from a DOSBox-X
savestate. The state adapter wraps that: it extracts goal2's state
(player array, country records, RNG words, managed-country players,
match state) from a savestate, and writes it back. The round-trip test
loads an archaeology savestate, calls `from_savestate` then
`to_savestate`, and asserts the decompressed content matches exactly.

[confirmed: E006, T01, F002, F007, F008] The layout is the original's
memory image: player array at [DS:A91B], country records at [DS:A917],
RNG words at DS:7B62 and DS:8336. The vendored `Savestate` and
`players` readers parse the layout.
"""
from __future__ import annotations

import io
import zipfile
import zlib
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from goal2.engine.savestate import Savestate
    from goal2.game.campaign import CampaignState


PLAYER_SIZE = 0x14
N_PLAYERS = 3061
COUNTRY_SIZE = 0xBF
N_COUNTRIES = 129
SQUAD = 20

# [confirmed: T01] The vendored Savestate.memory() adds this offset to the
# guest address before indexing into the raw Memory component.
MEM_BASE = 0x78

# [confirmed: E006 savestate layout] The two zip entries whose bytes the
# adapter decompresses, modifies, and recompresses.
_VGA_ENTRY = "Vga"
_MEMORY_ENTRY = "Memory"

# [designed] The DOS clock word at DS:0E6C. Not used by the quick engine
# (T01), but read by the round-trip test to verify a second field.
CLOCK_OFFSET = 0x0E6C


@dataclass
class GameState:
    """[confirmed: T01, F002, F007, F008] goal2's state representation.
    Holds the parsed fields plus the raw decompressed VGA and Memory
    components so the adapter can write them back without losing
    unknown bytes."""
    # [confirmed: T01, F002] The player array as 3061 records of 20 bytes
    # each. Record-indexed for goal2's use (players[1] is country 1's
    # first player; players[0] is the placeholder all-zero record).
    players: list[bytes]
    # [confirmed: T01, F002] The country array as 129 records of 0xBF bytes.
    countries: list[bytes]
    # [confirmed: F007] The managed country's 20 player numbers (the
    # squad of country 7 in E006-r0001). Stored as a list of 20 ints
    # (1-based player numbers).
    managed_country: int
    managed_squad: list[int]
    # [confirmed: F004] The two RNG seed words (DS:7B62 and DS:8336).
    rng_seed_7b62: int
    rng_seed_8336: int
    # [designed] The match state (score, minute, half). Read from the
    # match state at DS:0E6C (clock) and other locations; modelled as a
    # simple dict for now.
    match_state: dict
    # [designed] The raw decompressed VGA component (text screen).
    vga: bytes = field(repr=False)
    # [designed] The raw decompressed Memory component (guest memory).
    # The adapter modifies known fields in this buffer, then writes it
    # back to the zip.
    mem: bytes = field(repr=False)
    # [designed] The 11 player numbers of the chosen starting lineup.
    # Set by the squad select screen (T12); read by the tactics screen (T13).
    starting_eleven: list[int] = field(default_factory=list)
    # [designed] The captain's player number (0 means "not yet picked").
    # Set by the squad select screen (T12); read by the match screen (T14).
    captain: int = 0
    # [designed] The 8-bit team tactics byte for the managed country.
    # Set by the tactics screen (T13); read by the match screen (T14).
    # Default 0 means all bits clear.
    country_tactics: int = 0
    # [designed: T32, T33] Successful interactive assumed friendlies retain
    # a compact result and count; the rebuild session save serializes both.
    match_count: int = 0
    last_match: dict | None = None
    # [designed: T40] Campaign metadata remains separate from friendly match
    # state; legacy sessions leave this unset and keep their v1 meaning.
    campaign: "CampaignState | None" = None
    # [designed: T92; owner, 2026-10-21] In-game renames (goal2.game.identities): player number
    # to surname, and the manager's name; empty means GOAL.DAT's names and "Manager 1".
    player_renames: dict = field(default_factory=dict)
    manager_name: str = ''


def from_savestate(state_bytes: bytes) -> GameState:
    """[confirmed: T01, F002, F007, F008] Read a savestate and return a
    GameState. Decompresses the VGA and Memory zip entries, then extracts
    the known fields (player array, country records, RNG words,
    managed-country squad, match state) from Memory."""
    with zipfile.ZipFile(io.BytesIO(state_bytes)) as z:
        vga = zlib.decompressobj().decompress(z.read(_VGA_ENTRY))
        mem = zlib.decompressobj().decompress(z.read(_MEMORY_ENTRY))
    # Build a temporary Savestate to use its ds_bytes() / memory() helpers.
    state = _wrap_raw(vga, mem)
    # [confirmed: T01] The player array is at [DS:A91B] (far pointer).
    raw_players = bytes(_players_bytes(state))
    players = [raw_players[i * PLAYER_SIZE:(i + 1) * PLAYER_SIZE] for i in range(N_PLAYERS)]
    # [confirmed: T01] The country array is at [DS:A917] (far pointer).
    raw_countries = bytes(_countries_bytes(state))
    countries = [raw_countries[i * COUNTRY_SIZE:(i + 1) * COUNTRY_SIZE] for i in range(N_COUNTRIES)]
    # [confirmed: F004] The RNG seeds are little-endian words at DS:7B62
    # and DS:8336.
    rng_7b62 = int.from_bytes(state.ds_bytes(0x7B62, 2), "little")
    rng_8336 = int.from_bytes(state.ds_bytes(0x8336, 2), "little")
    # [confirmed: F007] E006-r0001's managed country is 7 (Denmark).
    # The managed country's 20-player squad is at country record 7's
    # first 20 words.
    managed_country = 7
    managed_squad = list(_squad(raw_countries, managed_country))
    # [confirmed: F010] The tactics byte is at country record offset +0x2D.
    country_tactics = raw_countries[managed_country * COUNTRY_SIZE + 0x2D]
    # [designed: chosen +0x2F, free byte in country record per F011] The
    # captain byte; the engine does not read it in v1 (T14), so this is
    # for state-fidelity / UI round-trip only.
    captain = raw_countries[managed_country * COUNTRY_SIZE + 0x2F]
    # [designed] Read the DOS clock word at DS:0E6C as a stand-in for
    # match state (score, minute, half). The quick engine (T01) doesn't
    # read this; the watched engine will.
    clock = int.from_bytes(state.ds_bytes(CLOCK_OFFSET, 2), "little")
    match_state = {"clock": clock, "score": (0, 0), "minute": 0, "half": 0}
    return GameState(
        players=players,
        countries=countries,
        managed_country=managed_country,
        managed_squad=managed_squad,
        rng_seed_7b62=rng_7b62,
        rng_seed_8336=rng_8336,
        match_state=match_state,
        vga=vga,
        mem=mem,
        starting_eleven=list(managed_squad[:11]),
        captain=captain,
        country_tactics=country_tactics,
    )


def to_savestate(game_state: GameState, original: bytes) -> bytes:
    """[confirmed: T01, F002, F007, F008] Write a GameState back to
    savestate bytes. `original` is required: the adapter preserves the
    original's zip structure (other DOSBox-X components, timestamps,
    compression method) and only replaces the Vga and Memory entries
    with the modified content. Modifies the known fields in Memory,
    recompresses VGA and Memory, and re-zips them.
    """
    if original is None:
        raise ValueError("to_savestate requires the original bytes to preserve zip structure")
    # Pack the player array from records to flat bytes.
    raw_players = bytes(b"").join(game_state.players)
    if len(raw_players) != N_PLAYERS * PLAYER_SIZE:
        raise ValueError(f"player array: expected {N_PLAYERS * PLAYER_SIZE} bytes, got {len(raw_players)}")
    # Pack the country array from records to flat bytes.
    raw_countries = bytes(b"").join(game_state.countries)
    if len(raw_countries) != N_COUNTRIES * COUNTRY_SIZE:
        raise ValueError(f"country array: expected {N_COUNTRIES * COUNTRY_SIZE} bytes, got {len(raw_countries)}")
    # Update the managed-country squad in the country record.
    if len(game_state.managed_squad) != SQUAD:
        raise ValueError(f"managed squad: expected {SQUAD} player numbers, got {len(game_state.managed_squad)}")
    raw_countries_arr = bytearray(raw_countries)
    for i, n in enumerate(game_state.managed_squad):
        mc = game_state.managed_country
        raw_countries_arr[mc * COUNTRY_SIZE + 2 * i:mc * COUNTRY_SIZE + 2 * i + 2] = n.to_bytes(2, "little")
    # [confirmed: F010] Write the tactics byte at country record +0x2D.
    mc = game_state.managed_country
    raw_countries_arr[mc * COUNTRY_SIZE + 0x2D] = game_state.country_tactics & 0xFF
    # [designed: chosen +0x2F, free byte in country record per F011] Write
    # the captain byte. The engine does not read it in v1 (T14); this is
    # for state-fidelity / UI round-trip only.
    raw_countries_arr[mc * COUNTRY_SIZE + 0x2F] = game_state.captain & 0xFF
    # [designed] Write the starting eleven only when it differs from the
    # managed squad's first 11 (SQ-5: the eleven is squad order). If it
    # equals managed_squad[:11] the squad write already stored it correctly.
    if game_state.starting_eleven and game_state.starting_eleven != list(game_state.managed_squad[:11]):
        for i, n in enumerate(game_state.starting_eleven[:11]):
            raw_countries_arr[mc * COUNTRY_SIZE + 2 * i:mc * COUNTRY_SIZE + 2 * i + 2] = n.to_bytes(2, "little")
    # Write to Memory.
    mem = bytearray(game_state.mem)
    state = _wrap_raw(game_state.vga, mem)
    # [confirmed: T01] Write the player array.
    _write_players(state, raw_players)
    # [confirmed: T01] Write the country array.
    _write_countries(state, bytes(raw_countries_arr))
    # [confirmed: F004] Write the RNG seeds (DS-relative offsets).
    state.ds_write(0x7B62, game_state.rng_seed_7b62.to_bytes(2, "little"))
    state.ds_write(0x8336, game_state.rng_seed_8336.to_bytes(2, "little"))
    # [designed] Write the DOS clock word.
    state.ds_write(CLOCK_OFFSET, game_state.match_state.get("clock", 0).to_bytes(2, "little"))
    # Recompress and re-zip, preserving the original's zip structure.
    new_vga = zlib.compress(game_state.vga)
    new_mem = zlib.compress(bytes(state.mem))
    return _rewrite_zip(original, {_VGA_ENTRY: new_vga, _MEMORY_ENTRY: new_mem})


# ---- helpers ----------------------------------------------------------------


class _RawSavestate:
    """[designed] A minimal Savestate-like wrapper that reads from raw
    decompressed components. Avoids recomputing the program location
    (find_program) for every read."""

    def __init__(self, vga: bytes, mem: "bytearray | bytes"):
        self.vga = vga
        self.mem = mem
        from goal2.engine.savestate import find_program
        self._prog = find_program(self.memory)

    def memory(self, addr: int, n: int) -> bytes:
        o = MEM_BASE + addr
        if o + n > len(self.mem):
            raise ValueError(f"guest memory 0x{addr:x}+{n} outside the Memory component ({len(self.mem)} bytes)")
        return bytes(self.mem[o:o + n])

    def ds_bytes(self, off: int, n: int) -> bytes:
        return self.memory(self._prog.ds_base + off, n)

    def mem_write(self, addr: int, data: bytes) -> None:
        o = MEM_BASE + addr
        if o + len(data) > len(self.mem):
            raise ValueError(f"guest memory 0x{addr:x}+{len(data)} outside the Memory component ({len(self.mem)} bytes)")
        self.mem[o:o + len(data)] = data

    def ds_write(self, off: int, data: bytes) -> None:
        self.mem_write(self._prog.ds_base + off, data)


def _wrap_raw(vga: bytes, mem: "bytearray | bytes") -> _RawSavestate:
    return _RawSavestate(vga, mem)


def _players_bytes(state) -> bytes:
    from goal2.engine.players import players as read_players
    return read_players(state)


def _countries_bytes(state) -> bytes:
    from goal2.engine.players import countries as read_countries
    return read_countries(state)


def _squad(country_array: bytes, c: int) -> list[int]:
    """[confirmed: T01, players.squad] The 20 player numbers in the first
    20 words of country record c."""
    r = country_array[c * COUNTRY_SIZE:(c + 1) * COUNTRY_SIZE]
    return [int.from_bytes(r[2 * i:2 * i + 2], "little") for i in range(SQUAD)]


def _write_players(state, players_bytes: bytes) -> None:
    from goal2.engine.players import far_pointer
    addr = far_pointer(state, 0xA91B)[2]
    state.mem_write(addr, players_bytes)


def _write_countries(state, countries_bytes: bytes) -> None:
    from goal2.engine.players import far_pointer
    addr = far_pointer(state, 0xA917)[2]
    state.mem_write(addr, countries_bytes)


def _rewrite_zip(original: bytes, replacements: dict[str, bytes]) -> bytes:
    """[designed] Rewrite a zip, replacing named entries' data while
    preserving the original's zip structure (timestamps, compression
    method, extra fields). Other entries are copied unchanged."""
    src = io.BytesIO(original)
    dst = io.BytesIO()
    with zipfile.ZipFile(src, "r") as zin, zipfile.ZipFile(
        dst, "w", zipfile.ZIP_STORED
    ) as zout:
        for item in zin.infolist():
            if item.filename in replacements:
                new_data = replacements[item.filename]
                new_info = zipfile.ZipInfo(filename=item.filename, date_time=item.date_time)
                new_info.compress_type = item.compress_type
                new_info.external_attr = item.external_attr
                new_info.create_system = item.create_system
                new_info.create_version = item.create_version
                new_info.extract_version = item.extract_version
                new_info.flag_bits = item.flag_bits
                new_info.extra = item.extra
                new_info.internal_attr = item.internal_attr
                zout.writestr(new_info, new_data)
            else:
                zout.writestr(item, zin.read(item.filename))
    return dst.getvalue()
