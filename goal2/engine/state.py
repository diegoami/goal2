"""The state adapter: round-trip the original's savestate through goal2's state.

The original game's state lives in guest memory (the DOS program's data
segment). Vendored models (T01) read that memory directly from a DOSBox-X
savestate. The state adapter wraps that: it extracts goal2's state
(player array, country records, RNG words) from a savestate, and writes
it back. The round-trip test loads an archaeology savestate, calls
`from_savestate` then `to_savestate`, and asserts every byte matches.

[confirmed: E006, T01, F007, F008] The layout is the original's memory
image: player array at [DS:A91B], country records at [DS:A917], RNG
words at DS:7B62 and DS:8336. The vendored `Savestate` and `players`
readers parse the layout.
"""
from __future__ import annotations

import io
import zipfile
import zlib
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from goal2.engine.savestate import Savestate


PLAYER_SIZE = 0x14
N_PLAYERS = 3061
COUNTRY_SIZE = 0xBF
N_COUNTRIES = 129

# [confirmed: T01] The vendored Savestate.memory() adds this offset to the
# guest address before indexing into the raw Memory component.
MEM_BASE = 0x78

# [confirmed: E006 savestate layout] The two zip entries whose bytes the
# adapter decompresses, modifies, and recompresses.
_VGA_ENTRY = "Vga"
_MEMORY_ENTRY = "Memory"


@dataclass
class GameState:
    """[designed] goal2's state representation. Holds the parsed fields
    plus the raw decompressed VGA and Memory components so the adapter
    can write them back without losing unknown bytes."""
    # [confirmed: T01, F002] The full 0xEF24-byte player array (3061 records).
    players: bytes
    # [confirmed: T01, F002] The full 0x603F-byte country array (129 records).
    countries: bytes
    # [confirmed: F004] The two RNG seed words (DS:7B62 and DS:8336).
    rng_seed_7b62: int
    rng_seed_8336: int
    # [designed] The raw decompressed VGA component (text screen).
    vga: bytes = field(repr=False)
    # [designed] The raw decompressed Memory component (guest memory).
    # The adapter modifies known fields in this buffer, then recompresses.
    mem: bytes = field(repr=False)


def from_savestate(state_bytes: bytes) -> GameState:
    """[confirmed: T01, F002, F007] Read a savestate and return a GameState.
    Decompresses the VGA and Memory zip entries, then extracts the known
    fields (player array, country records, RNG words) from Memory."""
    with zipfile.ZipFile(io.BytesIO(state_bytes)) as z:
        vga = zlib.decompressobj().decompress(z.read(_VGA_ENTRY))
        mem = zlib.decompressobj().decompress(z.read(_MEMORY_ENTRY))
    # Build a temporary Savestate to use its ds_bytes() / memory() helpers.
    state = _wrap_raw(vga, mem)
    # [confirmed: T01] The player array is at [DS:A91B] (far pointer).
    players = bytes(_players_bytes(state))
    # [confirmed: T01] The country array is at [DS:A917] (far pointer).
    countries = bytes(_countries_bytes(state))
    # [confirmed: F004] The RNG seeds are little-endian words at DS:7B62
    # and DS:8336.
    rng_7b62 = int.from_bytes(state.ds_bytes(0x7B62, 2), "little")
    rng_8336 = int.from_bytes(state.ds_bytes(0x8336, 2), "little")
    return GameState(
        players=players,
        countries=countries,
        rng_seed_7b62=rng_7b62,
        rng_seed_8336=rng_8336,
        vga=vga,
        mem=mem,
    )


def to_savestate(game_state: GameState, original: bytes | None = None) -> bytes:
    """[confirmed: T01, F002] Write a GameState back to savestate bytes.
    Modifies the known fields in Memory, recompresses VGA and Memory, and
    re-zips them. If `original` is provided, the output preserves the
    original zip's metadata (timestamps, compression settings, extra
    fields) so a no-op round-trip is byte-for-byte.
    """
    mem = bytearray(game_state.mem)
    state = _wrap_raw(game_state.vga, mem)
    # [confirmed: T01] Write the player array.
    _write_players(state, game_state.players)
    # [confirmed: T01] Write the country array.
    _write_countries(state, game_state.countries)
    # [confirmed: F004] Write the RNG seeds (DS-relative offsets).
    state.ds_write(0x7B62, game_state.rng_seed_7b62.to_bytes(2, "little"))
    state.ds_write(0x8336, game_state.rng_seed_8336.to_bytes(2, "little"))
    # Recompress and re-zip, preserving the original's zip structure when
    # available (so a no-op round-trip is byte-for-byte).
    new_vga = zlib.compress(game_state.vga)
    new_mem = zlib.compress(bytes(state.mem))
    if original is not None:
        return _rewrite_zip(original, {_VGA_ENTRY: new_vga, _MEMORY_ENTRY: new_mem})
    out = io.BytesIO()
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr(_VGA_ENTRY, new_vga)
        z.writestr(_MEMORY_ENTRY, new_mem)
    return out.getvalue()


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
                # Preserve all metadata; only change the data and CRC.
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
                # Copy the entry unchanged.
                zout.writestr(item, zin.read(item.filename))
    return dst.getvalue()


# ---- helpers ----------------------------------------------------------------


class _RawSavestate:
    """[designed] A minimal Savestate-like wrapper that reads from raw
    decompressed components. Avoids recomputing the program location
    (find_program) for every read."""

    def __init__(self, vga: bytes, mem: "bytearray | bytes"):
        self.vga = vga
        self.mem = mem
        # [confirmed: T01] find_program scans conventional memory for the
        # MCB of the GOAL program. We can use the vendored helper or
        # re-implement it; for simplicity, use the vendored Savestate's
        # find_program by constructing a memory reader.
        from goal2.engine.savestate import find_program
        self._prog = find_program(self.memory)

    def memory(self, addr: int, n: int) -> bytes:
        # [confirmed: T01] Add MEM_BASE to the guest address, matching the
        # vendored Savestate.memory() implementation.
        o = MEM_BASE + addr
        if o + n > len(self.mem):
            raise ValueError(f"guest memory 0x{addr:x}+{n} outside the Memory component ({len(self.mem)} bytes)")
        return bytes(self.mem[o:o + n])

    def ds_bytes(self, off: int, n: int) -> bytes:
        return self.memory(self._prog.ds_base + off, n)

    def mem_write(self, addr: int, data: bytes) -> None:
        """[designed] Write bytes to the Memory component at a guest address.
        Matches the vendored Savestate.memory() layout (MEM_BASE offset).
        The addr is a full guest address (e.g. DS:7B62 = ds_base + 0x7B62),
        NOT a DS-relative offset; callers that have a DS offset must add
        ds_base first."""
        o = MEM_BASE + addr
        if o + len(data) > len(self.mem):
            raise ValueError(f"guest memory 0x{addr:x}+{len(data)} outside the Memory component ({len(self.mem)} bytes)")
        self.mem[o:o + len(data)] = data

    def ds_write(self, off: int, data: bytes) -> None:
        """[designed] Write bytes at a DS-relative offset. Mirrors ds_bytes()."""
        self.mem_write(self._prog.ds_base + off, data)


def _wrap_raw(vga: bytes, mem: bytes) -> _RawSavestate:
    return _RawSavestate(vga, mem)


def _players_bytes(state) -> bytes:
    """[confirmed: T01] Read the 0xEF24-byte player array."""
    from goal2.engine.players import players as read_players
    return read_players(state)


def _countries_bytes(state) -> bytes:
    """[confirmed: T01] Read the 0x603F-byte country array."""
    from goal2.engine.players import countries as read_countries
    return read_countries(state)


def _write_players(state, players_bytes: bytes) -> None:
    """[confirmed: T01] Write the player array to Memory at the far pointer
    address (resolved from DS:A91B)."""
    from goal2.engine.players import far_pointer
    addr = far_pointer(state, 0xA91B)[2]
    state.mem_write(addr, players_bytes)


def _write_countries(state, countries_bytes: bytes) -> None:
    """[confirmed: T01] Write the country array to Memory at the far pointer
    address (resolved from DS:A917)."""
    from goal2.engine.players import far_pointer
    addr = far_pointer(state, 0xA917)[2]
    state.mem_write(addr, countries_bytes)
