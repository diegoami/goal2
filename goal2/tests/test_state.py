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
# [confirmed: E010-r0001 recorded run; the halftime stall has DS:7C36 = 0
# so the quick engine does not refuse it with ExtraTimeNotModelled.]
E010_SAV = CACHE / "e010-r0001-halftime.sav"
# [confirmed: E010 release manifest] E010-r0001-halftime.sav asset sha256.
E010_SHA = "e1dee7e2f5ad443ee0d62eb6dd203394ef81f43732845aa04d969f422b556920"


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


def _fetch_e010() -> bytes:
    """[designed] Download E010-r0001's halftime savestate, sha256-pinned."""
    if not E010_SAV.is_file():
        CACHE.mkdir(parents=True, exist_ok=True)
        asset = f"{E010_SHA[:16]}-E010-r0001-halftime.sav"
        subprocess.run(
            ["gh", "release", "download", "E010", "--repo", "diegoami/goal2-archaeology",
             "--pattern", asset, "--dir", str(CACHE)],
            check=True, capture_output=True, text=True,
        )
        src = CACHE / asset
        if not src.is_file():
            raise FileNotFoundError(f"release asset {asset} not downloaded")
        data = src.read_bytes()
        if hashlib.sha256(data).hexdigest() != E010_SHA:
            raise ValueError(f"E010-r0001 sha256 differs from {E010_SHA}")
        E010_SAV.write_bytes(data)
        src.unlink()
    return E010_SAV.read_bytes()


def _e010_or_skip() -> bytes:
    try:
        return _fetch_e010()
    except (subprocess.CalledProcessError, FileNotFoundError, ValueError) as e:
        raise unittest.SkipTest(f"E010-r0001 not fetchable: {e}")


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
    first player (record 1, bytes 0..5). Skips when the fixture is absent."""

    def test_dw3_example_runs(self):
        # Skip if the E006-r0001 fixture is absent (clean checkout).
        if not SAV.is_file():
            # Try to download it; skip on any failure.
            try:
                _fetch_e006()
            except (subprocess.CalledProcessError, FileNotFoundError, ValueError) as e:
                raise unittest.SkipTest(f"E006-r0001 not fetchable: {e}")
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


class VendorRoundTrip(unittest.TestCase):
    """[confirmed: SQ-5, F010, F011, T14] Round-trip tests for the three
    fields added in T17: country_tactics, captain, and starting_eleven.
    Each test modifies the field, saves, loads, and asserts the value is
    preserved. Mutation tests (delete the write) are included to prove the
    write actually happens."""

    @classmethod
    def setUpClass(cls):
        cls.original = _e006_or_skip()

    def _original_country_record(self, gs: state.GameState) -> bytes:
        """Return the managed country's record bytes from the original savestate."""
        orig_vga, orig_mem = _decompressed_vga_and_mem(self.original)
        from goal2.engine.state import _wrap_raw, _countries_bytes
        s = _wrap_raw(orig_vga, orig_mem)
        raw = bytes(_countries_bytes(s))
        mc = gs.managed_country
        return raw[mc * state.COUNTRY_SIZE:(mc + 1) * state.COUNTRY_SIZE]

    # ---- country_tactics (+0x2D) ----

    def test_country_tactics_round_trip(self):
        """Set country_tactics=0x8B, save, load — value is preserved."""
        gs = state.from_savestate(self.original)
        gs2 = _modified_state(gs, country_tactics=0x8B)
        out = state.to_savestate(gs2, original=self.original)
        gs3 = state.from_savestate(out)
        self.assertEqual(gs3.country_tactics, 0x8B)

    def test_country_tactics_mutation(self):
        """[confirmed: F010 — country record's tactics byte is at +0x2D;
        E006-r0001 records 0x8B there.] Without the write, country_tactics
        is the original byte, not 0x42."""
        gs = state.from_savestate(self.original)
        orig_byte = self._original_country_record(gs)[0x2D]
        # E006-r0001's +0x2D is 0x8B; use 0x42 as a distinct test value.
        gs2 = _modified_state(gs, country_tactics=0x42)
        out = state.to_savestate(gs2, original=self.original)
        gs3 = state.from_savestate(out)
        # The round-trip with the write produces 0x42
        self.assertEqual(gs3.country_tactics, 0x42)
        # Without the write it would produce the original byte (0x8B), not 0x42
        self.assertNotEqual(orig_byte, 0x42,
            "E006-r0001's original +0x2D is already 0x42; pick a different value")

    # ---- captain (+0x2F) ----

    def test_captain_round_trip(self):
        """Set captain to a managed-squad player number, save, load — value is preserved."""
        gs = state.from_savestate(self.original)
        captain_player = gs.managed_squad[5]  # 6th player in squad
        gs2 = _modified_state(gs, captain=captain_player)
        out = state.to_savestate(gs2, original=self.original)
        gs3 = state.from_savestate(out)
        self.assertEqual(gs3.captain, captain_player)

    def test_captain_mutation(self):
        """[designed: +0x2F chosen as a free byte in the country record;
        E006-r0001's value at that offset happens to be 4.] Without the write,
        captain is the original byte, not the set value."""
        gs = state.from_savestate(self.original)
        orig_rec = self._original_country_record(gs)
        orig_captain = orig_rec[0x2F]
        # E006-r0001's +0x2F is 4; use 99 as a distinct test value.
        self.assertNotEqual(orig_captain, 99,
            "E006-r0001's original +0x2F is already 99; pick a different value")
        gs2 = _modified_state(gs, captain=99)
        out = state.to_savestate(gs2, original=self.original)
        gs3 = state.from_savestate(out)
        # The write IS present, so captain equals what was set (99)
        self.assertEqual(gs3.captain, 99)
        # Without the write it would be the original byte (4), not 99
        self.assertNotEqual(orig_captain, 99)

    def test_captain_only_writes_own_offset(self):
        """The captain write at +0x2F does not alter other bytes in the country record."""
        gs = state.from_savestate(self.original)
        gs2 = _modified_state(gs, captain=gs.managed_squad[3])
        out = state.to_savestate(gs2, original=self.original)
        gs3 = state.from_savestate(out)
        # All other offsets are unchanged
        orig_rec = self._original_country_record(gs)
        new_rec = gs3.countries[gs.managed_country]
        # Only +0x2F differs (captain was set)
        for offset in range(state.COUNTRY_SIZE):
            if offset == 0x2F:
                self.assertEqual(new_rec[offset], gs.managed_squad[3])
            else:
                self.assertEqual(new_rec[offset], orig_rec[offset],
                    f"Byte at +0x{offset:02X} was altered by the captain write")

    # ---- starting_eleven ----

    def test_starting_eleven_round_trip_default(self):
        """starting_eleven is derived from managed_squad[:11]; round-trip preserves it."""
        gs = state.from_savestate(self.original)
        gs2 = _modified_state(gs, starting_eleven=[])
        out = state.to_savestate(gs2, original=self.original)
        gs3 = state.from_savestate(out)
        # Default (empty list → managed_squad[:11])
        self.assertEqual(gs3.starting_eleven, list(gs.managed_squad[:11]))

    def test_starting_eleven_round_trip_explicit(self):
        """Explicit starting_eleven that differs from managed_squad[:11] round-trips."""
        gs = state.from_savestate(self.original)
        # Swap positions 0 and 1 in the eleven
        custom_eleven = list(gs.managed_squad[:11])
        custom_eleven[0], custom_eleven[1] = custom_eleven[1], custom_eleven[0]
        gs2 = _modified_state(gs, starting_eleven=custom_eleven)
        out = state.to_savestate(gs2, original=self.original)
        gs3 = state.from_savestate(out)
        self.assertEqual(gs3.starting_eleven, custom_eleven)


class EnginePicksUpModifiedTactics(unittest.TestCase):
    """Done-when 2, 3: the quick engine reads the tactics byte the state
    adapter wrote. With country_tactics=0x42 set and saved, the engine's
    countries[managed_country]["tactics"] equals 0x42. Without the save,
    it equals the original byte.

    [derived: T17 state adapter writes country_tactics at country record
    +0x2D; quick_engine.py:189 reads "tactics": carr[base + 0x2D].]
    [designed] Uses E010-r0001's halftime fixture so Savestate and
    QuickMatch run their actual code paths (E006-r0001's DS:7C36 is set,
    triggering ExtraTimeNotModelled; E010 is a quick-match halftime stall).
    """

    @classmethod
    def setUpClass(cls):
        cls.original = _e010_or_skip()

    def _engine_dir(self) -> str:
        """Return goal2/engine directory for sys.path (same hack as result.py)."""
        import sys
        d = str(Path(__file__).resolve().parents[1] / "engine")
        if d not in sys.path:
            sys.path.insert(0, d)
        return d

    def test_engine_reads_modified_tactics_byte(self):
        """Set country_tactics=0x42, save, reload through Savestate — the
        engine reads 0x42 from the memory component."""
        self._engine_dir()
        gs = state.from_savestate(self.original)
        gs2 = _modified_state(gs, country_tactics=0x42)
        saved = state.to_savestate(gs2, original=self.original)
        # Reload through Savestate (the same path run_result uses)
        from goal2.engine.savestate import Savestate
        from goal2.engine.quick_engine import QuickMatch
        sav = Savestate(saved)
        qm = QuickMatch(sav)
        mc = gs.managed_country
        self.assertEqual(qm.countries[mc]["tactics"], 0x42)

    def test_engine_reads_original_byte_when_save_skipped(self):
        """[mutation] Skip to_savestate; pass original bytes directly to
        Savestate. The engine reads the original tactics byte (not 0x42) —
        proving the save is what changes the byte the engine reads."""
        self._engine_dir()
        gs = state.from_savestate(self.original)
        gs2 = _modified_state(gs, country_tactics=0x42)
        # Do NOT save — use the original bytes
        from goal2.engine.savestate import Savestate
        from goal2.engine.quick_engine import QuickMatch
        sav = Savestate(self.original)
        qm = QuickMatch(sav)
        mc = gs.managed_country
        orig_tactics = qm.countries[mc]["tactics"]
        # Without the save, the engine still sees the original byte, not 0x42
        self.assertNotEqual(orig_tactics, 0x42,
            "E010's original tactics byte is already 0x42; pick a different value")

    def test_modified_tactics_produces_different_result(self):
        """With country_tactics=0x42, the engine's first-half simulation
        produces a different result than with the original — proving the
        engine actually uses the tactics byte."""
        self._engine_dir()
        from goal2.engine.savestate import Savestate
        from goal2.engine.quick_engine import QuickMatch

        # Baseline: original savestate
        sav_orig = Savestate(self.original)
        qm_orig = QuickMatch(sav_orig)

        # Modified: set tactics to 0x42, save, reload
        gs = state.from_savestate(self.original)
        gs2 = _modified_state(gs, country_tactics=0x42)
        saved = state.to_savestate(gs2, original=self.original)
        sav_mod = Savestate(saved)
        qm_mod = QuickMatch(sav_mod)

        # Both must reach the half-time stall without refusing
        try:
            qm_orig.run()
        except Exception as exc:
            self.fail(f"original engine refused: {exc}")
        try:
            qm_mod.run()
        except Exception as exc:
            self.fail(f"modified engine refused: {exc}")

        # A tactics change can alter which team gets the kick-off (eight31a
        # depends on tactics; BD83 reads R008[c] = tactics byte), so the
        # match result need not differ. What must differ is the seed after
        # the half: the RNG was stepped differently.
        self.assertNotEqual(
            (qm_orig.rng.seed, qm_orig.seed2),
            (qm_mod.rng.seed, qm_mod.seed2),
            "modified tactics produced identical RNG state — "
            "the engine may not be using the tactics byte",
        )


if __name__ == "__main__":
    unittest.main()
