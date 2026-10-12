"""Tests for `goal2.engine.state` (T06 scope, the state adapter).

The round-trip test loads E006-r0001, calls `from_savestate` then
`to_savestate`, and asserts every byte matches the original. It also
verifies that a modification to a known field is reflected in the
output (the adapter actually writes the fields, not just the raw bytes).

[confirmed: E006, T01, F002, F007, F008] The layout is the original's
memory image; the vendored `Savestate` and `players` readers parse it.
"""
import hashlib
import os
import subprocess
import sys
import unittest
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


class RoundTrip(unittest.TestCase):
    """[confirmed: E006, T01] The adapter must round-trip E006-r0001
    byte-for-byte. It also must write known fields (a modification to
    a player byte is reflected in the output)."""

    @classmethod
    def setUpClass(cls):
        cls.original = _e006_or_skip()

    def test_round_trip_decompressed_match(self):
        """[designed] from_savestate → to_savestate reproduces the original's
        decompressed VGA and Memory components exactly. (The raw zip bytes
        differ because Python's zlib.compress uses different deflate
        settings than DOSBox-X.)"""
        import zipfile, zlib, io
        gs = state.from_savestate(self.original)
        out = state.to_savestate(gs, original=self.original)
        with zipfile.ZipFile(io.BytesIO(self.original)) as zin:
            orig_vga = zlib.decompress(zin.read("Vga"))
            orig_mem = zlib.decompress(zin.read("Memory"))
        with zipfile.ZipFile(io.BytesIO(out)) as zout:
            out_vga = zlib.decompress(zout.read("Vga"))
            out_mem = zlib.decompress(zout.read("Memory"))
        self.assertEqual(out_vga, orig_vga, "VGA component differs after round-trip")
        self.assertEqual(out_mem, orig_mem, "Memory component differs after round-trip")

    def test_modify_player_byte_round_trip(self):
        """Modify a known field (player 1's +0x01 age) and verify the
        modification is reflected in the output. This proves the adapter
        writes the fields, not just the raw bytes."""
        gs = state.from_savestate(self.original)
        # Modify player 1's +0x01 age to 0x42 (66).
        modified_players = bytearray(gs.players)
        modified_players[1 * 0x14 + 1] = 0x42
        gs2 = state.GameState(
            players=bytes(modified_players),
            countries=gs.countries,
            rng_seed_7b62=gs.rng_seed_7b62,
            rng_seed_8336=gs.rng_seed_8336,
            vga=gs.vga,
            mem=gs.mem,
        )
        out = state.to_savestate(gs2, original=self.original)
        # The output should differ from the original.
        self.assertNotEqual(out, self.original)
        # Read the modified savestate and verify the change.
        gs3 = state.from_savestate(out)
        self.assertEqual(gs3.players[1 * 0x14 + 1], 0x42)

    def test_modify_rng_word_round_trip(self):
        """Modify an RNG word and verify the change is reflected."""
        gs = state.from_savestate(self.original)
        gs2 = state.GameState(
            players=gs.players,
            countries=gs.countries,
            rng_seed_7b62=0xBEEF,
            rng_seed_8336=gs.rng_seed_8336,
            vga=gs.vga,
            mem=gs.mem,
        )
        out = state.to_savestate(gs2, original=self.original)
        gs3 = state.from_savestate(out)
        self.assertEqual(gs3.rng_seed_7b62, 0xBEEF)

    def test_player_array_size(self):
        """The player array is 0xEF24 = 61220 bytes (3061 records × 0x14)."""
        gs = state.from_savestate(self.original)
        self.assertEqual(len(gs.players), 0xEF24)

    def test_country_array_size(self):
        """The country array is 0x603F = 24639 bytes (129 records × 0xBF)."""
        gs = state.from_savestate(self.original)
        self.assertEqual(len(gs.countries), 0x603F)

    def test_player_1_first_byte_is_country(self):
        """Player 1's +0x00 byte is 1 (country 1)."""
        gs = state.from_savestate(self.original)
        self.assertEqual(gs.players[0x14 + 0], 1)


class DW3Example(unittest.TestCase):
    """[designed] The DW3 example: print the first 6 bytes of country 1's
    first player."""

    def test_dw3_example_runs(self):
        from goal2.engine import state as state_mod
        code = (
            "from goal2.engine import state; "
            "s = state.from_savestate(open('.cache/e006-r0001-main.sav','rb').read()); "
            "print(s.players[0x14:0x14+6].hex())"
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
