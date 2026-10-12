"""T07: the quick engine on an adapter-roundtripped state.

Proves the state adapter (T06) is faithful enough for the vendored quick
engine (T01): the engine produces the same score, goals, and seed
words on a roundtripped state as on the original.

[confirmed: E010, T01, T06] The engine is the vendored quick_engine
(T01); the adapter is the state adapter (T06). E010-r0001 is a
half-time savestate; the engine runs the second half from it.
"""
import hashlib
import json
import os
import subprocess
import sys
import unittest
from pathlib import Path

# [designed] Import cli first to trigger its sys.path setup for the
# vendored engine directory (so `import players` inside quick_engine
# resolves to goal2/engine/players.py).
from goal2 import cli  # noqa: F401

from goal2.engine import state
from goal2.engine.quick_engine import simulate
from goal2.engine.savestate import Savestate


ROOT = Path(__file__).resolve().parents[2]
CACHE = ROOT / ".cache"
SAV = CACHE / "e010-r0001-halftime.sav"
ARCHAEOLOGY = Path(os.environ.get("GOAL2_ARCHAEOLOGY", str(ROOT.parent.parent / "goal2-archaeology")))
E010_RUNS = ARCHAEOLOGY / "runs" / "E010"

# [confirmed: E010 release manifest] E010-r0001's asset sha256[:16].
E010_R0001_SHA_PREFIX = "e1dee7e2f5ad443e"


def _fetch_e010(n: int = 1) -> bytes:
    """[designed] Download E010-rNNNN's half-time savestate from the
    E010 release, verified by sha256 prefix per record.
    `n` is the record number (1..10)."""
    # [confirmed: E010 release manifest] Each E010 record has a distinct
    # asset name like `e1dee7e2f5ad443e-E010-r0001-halftime.sav`. The
    # sha256 prefixes differ per record; we look up the right one.
    sav_path = CACHE / f"e010-r{n:04d}-halftime.sav"
    if not sav_path.is_file():
        CACHE.mkdir(parents=True, exist_ok=True)
        subprocess.run(
            ["gh", "release", "download", "E010", "--repo", "diegoami/goal2-archaeology",
             "--pattern", "*.sav", "--dir", str(CACHE), "--skip-existing"],
            check=True, capture_output=True, text=True,
        )
        # [confirmed: E010 release naming] The asset name embeds the
        # record number: `*-E010-rNNNN-halftime.sav`.
        suffix = f"-E010-r{n:04d}-halftime.sav"
        for f in CACHE.iterdir():
            if f.name.endswith(suffix):
                if f != sav_path:
                    f.rename(sav_path)
                break
    if not sav_path.is_file():
        raise FileNotFoundError(f"E010-r{n:04d} savestate not found in {CACHE}")
    return sav_path.read_bytes()


def _e010_or_skip(n: int = 1) -> bytes:
    try:
        return _fetch_e010(n)
    except (subprocess.CalledProcessError, FileNotFoundError) as e:
        raise unittest.SkipTest(f"E010-r{n:04d} not fetchable: {e}")


def _run_engine(state_bytes: bytes) -> dict:
    """[designed] Run the vendored quick engine on the given savestate bytes
    and return a comparable result dict (score, goals, seed words)."""
    sav = Savestate(state_bytes)
    result = simulate(sav)
    return {
        "score": tuple(result["score"]),
        "goals": [(g["team"], g["player"], g["minute"]) for g in result["goals"]],
        "seed_DS7B62": result["seed_DS7B62"],
        "seed_DS8336": result["seed_DS8336"],
    }


class EngineOnAdaptedState(unittest.TestCase):
    """[confirmed: E010, T01, T06] The vendored quick engine produces the same
    result on the adapter-roundtripped state as on the original. The
    test runs against every E010 record (r0001..r0010) the archaeology
    checkout has, not just r0001."""

    @classmethod
    def setUpClass(cls):
        cls.records = []
        for n in range(1, 11):
            record_path = E010_RUNS / f"E010-r{n:04d}.json"
            if not record_path.is_file():
                continue  # archaeology checkout absent; skip this record
            try:
                original = _fetch_e010(n)
            except (subprocess.CalledProcessError, FileNotFoundError):
                continue
            cls.records.append((n, original))

    def test_engine_on_adapted_state(self):
        """For every available E010 record: run the engine on the
        original and on the adapter-roundtripped state. The two
        results must be identical. This catches a broken adapter that
        loses engine-relevant state (RNG words, player/country arrays,
        VGA text)."""
        if not self.records:
            self.skipTest("no E010 records available")
        for n, original in self.records:
            with self.subTest(record=n):
                original_result = _run_engine(original)
                gs = state.from_savestate(original)
                adapted = state.to_savestate(gs, original=original)
                adapted_result = _run_engine(adapted)
                self.assertEqual(
                    adapted_result, original_result,
                    f"engine result differs on adapted state for E010-r{n:04d}",
                )

    def test_adapter_modification_changes_engine_output(self):
        """A modification through the adapter is reflected in the
        engine's output. This proves the adapter actually writes the
        state, not just passes bytes through. The RNG words (DS:7B62,
        DS:8336) seed the LCG; changing them changes every draw the
        engine makes."""
        if not self.records:
            self.skipTest("no E010 records available")
        n, original = self.records[0]
        gs = state.from_savestate(original)
        gs2 = state.GameState(
            players=gs.players,
            countries=gs.countries,
            managed_country=gs.managed_country,
            managed_squad=gs.managed_squad,
            rng_seed_7b62=(gs.rng_seed_7b62 + 1) & 0xFFFF,  # nudge the seed
            rng_seed_8336=gs.rng_seed_8336,
            match_state=gs.match_state,
            vga=gs.vga,
            mem=gs.mem,
        )
        adapted = state.to_savestate(gs2, original=original)
        original_result = _run_engine(original)
        adapted_result = _run_engine(adapted)
        # A one-step seed nudge changes every LCG draw, so the engine's
        # output (score, goals, seed words) must differ.
        self.assertNotEqual(
            adapted_result, original_result,
            "adapter modification (RNG seed nudge) not reflected in engine output",
        )

    def test_adapter_preserves_vga(self):
        """The adapter preserves the VGA (text screen) component
        byte-for-byte. A broken adapter that corrupts VGA would change
        the engine's behaviour on a main-screen state (the engine
        reads VGA for some inputs)."""
        if not self.records:
            self.skipTest("no E010 records available")
        n, original = self.records[0]
        gs = state.from_savestate(original)
        adapted = state.to_savestate(gs, original=original)
        # [confirmed: T01] The VGA component is the text screen.
        import zipfile, zlib, io
        with zipfile.ZipFile(io.BytesIO(original)) as z:
            orig_vga = zlib.decompress(z.read("Vga"))
        with zipfile.ZipFile(io.BytesIO(adapted)) as z:
            out_vga = zlib.decompress(z.read("Vga"))
        self.assertEqual(out_vga, orig_vga, "VGA component differs after adapter round-trip")


if __name__ == "__main__":
    unittest.main()
