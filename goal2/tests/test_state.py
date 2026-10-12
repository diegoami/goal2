"""Tests for `goal2.engine.state` (T06 scope, the state adapter).

The round-trip test loads E006-r0001, calls `from_savestate` then
`to_savestate`, and asserts the decompressed content matches the
original. It also verifies that a modification to a known field is
reflected in the output (the adapter actually writes the fields, not
just the raw bytes).

[confirmed: E006, T01, F002, F007, F008] The layout is the original's
memory image; the vendored `Savestate` and `players` readers parse it.
"""
import hashlib
import os
import subprocess
import sys
import unittest
import zipfile
import zlib
import io
from pathlib import Path

from goal2.engine import state


ROOT = Path(__file__).resolve().parents[2]
CACHE = ROOT / ".cache"
SAV = CACHE / "e006-r0001-main.sav"
# [confirmed: E006 release manifest] E006-r0001's asset sha256.
E006_R0001_SHA = "e0afff6751747233f6ab8b9ba73dab0790b7509f15257ed7ae24f528b935657d"


def _fetch_e006() -> bytes:
    """[designed] Download E006-r0001's main-screen savestate, sha256-pinned."""
    if not SAV.is_file():
        CACHE.mkdir(parents=True, exist_ok=True)
        subprocess.run(
            ["gh", "release", "download", "E006", "--repo", "diegoami/goal2-archaeology",
             "--pattern", f"{E006_R0001_SHA[:16]}*", "--dir", str(CACHE), "--skip-existing"],
            check=True, capture_output=True, text=True,
        )
        for f in CACHE.iterdir():
            if f.name.startswith(E006_R0001_SHA[:16]) and f.suffix == ".sav":
                if f != SAV:
                    f.rename(SAV)
                break
    data = SAV.read_bytes()
    if hashlib.sha256(data).hexdigest() != E006_R0001_SHA:
        raise ValueError(f"E006-r0001 sha256 differs from {E006_R0001_SHA}")
    return data


def _e006_or_skip() -> bytes:
    try:
        return _fetch_e006()
    except (subprocess.CalledProcessError, FileNotFoundError, ValueError) as e:
        raise unittest.SkipTest(f"E006-r0001 not fetchable: {e}")


def _decompressed_vga_and_mem(sav_bytes: bytes) -> tuple[bytes, bytes]:
    """[designed] Decompress the VGA and Memory components of a savestate."""
    with zipfile.ZipFile(io.BytesIO(sav_bytes)) as z:
        vga = zlib.decompressobj().decompress(z.read("Vga"))
        mem = zlib.decompressobj().decompress(z.read("Memory"))
    return vga, mem


def _zip_entries(sav_bytes: bytes) -> set[str]:
    """[designed] The set of entry names in a savestate zip."""
    with zipfile.ZipFile(io.BytesIO(sav_bytes)) as z:
        return {info.filename for info in z.infolist()}


def _modified_state(gs: state.GameState, **changes) -> state.GameState:
    """[designed] Return a copy of gs with the given fields replaced."""
    from dataclasses import replace
    return replace(gs, **changes)


class RoundTrip(unittest.TestCase):
    """[confirmed: E006, T01, F007, F008] The adapter must round-trip
    E006-r0001's decompressed content exactly, preserve all 25 zip
    entries, and write known fields (a modification to a player byte,
    country byte, or RNG word is reflected in the output)."""

    @classmethod
    def setUpClass(cls):
        cls.original = _e006_or_skip()

    def test_round_trip_decompressed_match(self):
        """from_savestate → to_savestate reproduces the original's
        decompressed VGA and Memory components exactly."""
        gs = state.from_savestate(self.original)
        out = state.to_savestate(gs, original=self.original)
        orig_vga, orig_mem = _decompressed_vga_and_mem(self.original)
        out_vga, out_mem = _decompressed_vga_and_mem(out)
        self.assertEqual(out_vga, orig_vga, "VGA component differs after round-trip")
        self.assertEqual(out_mem, orig_mem, "Memory component differs after round-trip")

    def test_round_trip_preserves_all_zip_entries(self):
        """The output zip has the same 25 entries as the original
        (CMOS, CPU, DMA, Vga, Memory, etc.)."""
        gs = state.from_savestate(self.original)
        out = state.to_savestate(gs, original=self.original)
        self.assertEqual(_zip_entries(out), _zip_entries(self.original))

    def test_to_savestate_requires_original(self):
        """to_savestate raises when original is None (it can't preserve
        the zip structure without the original bytes)."""
        gs = state.from_savestate(self.original)
        with self.assertRaises(ValueError):
            state.to_savestate(gs, original=None)

    def test_modify_player_byte_round_trip(self):
        """Modify player 1's +0x01 age and verify the change is in the output."""
        gs = state.from_savestate(self.original)
        modified_players = list(gs.players)
        modified_players[1] = bytes([1, 0x42]) + gs.players[1][2:]
        gs2 = _modified_state(gs, players=modified_players)
        out = state.to_savestate(gs2, original=self.original)
        gs3 = state.from_savestate(out)
        self.assertEqual(gs3.players[1][1], 0x42)

    def test_modify_country_byte_round_trip(self):
        """Modify country 1's +0x2B byte and verify the change is in the output."""
        gs = state.from_savestate(self.original)
        modified_countries = list(gs.countries)
        rec = bytearray(modified_countries[1])
        rec[0x2B] = 0x42
        modified_countries[1] = bytes(rec)
        gs2 = _modified_state(gs, countries=modified_countries)
        out = state.to_savestate(gs2, original=self.original)
        gs3 = state.from_savestate(out)
        self.assertEqual(gs3.countries[1][0x2B], 0x42)

    def test_modify_rng_word_round_trip(self):
        """Modify an RNG word and verify the change is reflected."""
        gs = state.from_savestate(self.original)
        gs2 = _modified_state(gs, rng_seed_7b62=0xBEEF)
        out = state.to_savestate(gs2, original=self.original)
        gs3 = state.from_savestate(out)
        self.assertEqual(gs3.rng_seed_7b62, 0xBEEF)

    def test_managed_country_squad(self):
        """The managed country's 20-player squad is country 7's first
        20 players: records 121..140 in the player array."""
        gs = state.from_savestate(self.original)
        self.assertEqual(gs.managed_country, 7)
        self.assertEqual(len(gs.managed_squad), 20)
        self.assertEqual(gs.managed_squad, list(range(121, 141)))

    def test_player_array_record_count(self):
        """The player array has 3061 records of 20 bytes each."""
        gs = state.from_savestate(self.original)
        self.assertEqual(len(gs.players), 3061)
        for rec in gs.players:
            self.assertEqual(len(rec), 0x14)

    def test_country_array_record_count(self):
        """The country array has 129 records of 0xBF bytes each."""
        gs = state.from_savestate(self.original)
        self.assertEqual(len(gs.countries), 129)
        for rec in gs.countries:
            self.assertEqual(len(rec), 0xBF)

    def test_player_1_first_byte_is_country(self):
        """Player 1's +0x00 byte is 1 (country 1)."""
        gs = state.from_savestate(self.original)
        self.assertEqual(gs.players[1][0], 1)


class DW3Example(unittest.TestCase):
    """[designed] The DW3 example: print the first 6 bytes of country 1's
    first player (record 1, bytes 0..5)."""

    def test_dw3_example_runs(self):
        code = (
            "from goal2.engine import state; "
            "s = state.from_savestate(open('.cache/e006-r0001-main.sav','rb').read()); "
            "print(s.players[1][:6].hex())"
        )
        r = subprocess.run(
            [sys.executable, "-c", code],
            capture_output=True, text=True, cwd=str(ROOT),
        )
        self.assertEqual(r.returncode, 0, f"stderr={r.stderr}")
        parts = r.stdout.strip().split()
        self.assertEqual(len(parts), 1, f"unexpected output: {r.stdout!r}")
        self.assertEqual(len(parts[0]), 12, f"expected 12 hex chars (6 bytes): {parts[0]!r}")


if __name__ == "__main__":
    unittest.main()
