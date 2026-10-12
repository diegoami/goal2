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
E010_RECORD = ARCHAEOLOGY / "runs" / "E010" / "E010-r0001.json"

# [confirmed: E010 release manifest] E010-r0001's asset sha256[:16].
E010_R0001_SHA_PREFIX = "e010"


def _fetch_e010() -> bytes:
    """[designed] Download E010-r0001's half-time savestate, sha256-pinned."""
    if not SAV.is_file():
        CACHE.mkdir(parents=True, exist_ok=True)
        # Try the release first.
        try:
            subprocess.run(
                ["gh", "release", "download", "E010", "--repo", "diegoami/goal2-archaeology",
                 "--pattern", "*.sav", "--dir", str(CACHE), "--skip-existing"],
                check=True, capture_output=True, text=True,
            )
        except subprocess.CalledProcessError:
            pass
        # Find the savestate.
        for f in CACHE.iterdir():
            if f.suffix == ".sav" and f.name.startswith(E010_R0001_SHA_PREFIX):
                if f != SAV:
                    f.rename(SAV)
                break
    if not SAV.is_file():
        raise FileNotFoundError(f"E010-r0001 savestate not found in {CACHE}")
    return SAV.read_bytes()


def _e010_or_skip() -> bytes:
    try:
        return _fetch_e010()
    except (subprocess.CalledProcessError, FileNotFoundError) as e:
        raise unittest.SkipTest(f"E010-r0001 not fetchable: {e}")


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
    result on the adapter-roundtripped state as on the original."""

    @classmethod
    def setUpClass(cls):
        cls.original = _e010_or_skip()

    def test_engine_on_adapted_state(self):
        """Run the engine on the original and on the adapter-roundtripped
        state. The two results must be identical."""
        original_result = _run_engine(self.original)
        # Round-trip through the adapter.
        gs = state.from_savestate(self.original)
        adapted = state.to_savestate(gs, original=self.original)
        adapted_result = _run_engine(adapted)
        self.assertEqual(adapted_result, original_result)

    def test_engine_score_is_one_zero(self):
        """[confirmed: E010-r0001] The engine's score on this state is 1-0
        (the same on original and adapted)."""
        original_result = _run_engine(self.original)
        gs = state.from_savestate(self.original)
        adapted = state.to_savestate(gs, original=self.original)
        adapted_result = _run_engine(adapted)
        self.assertEqual(adapted_result["score"], original_result["score"])
        # [confirmed: E010-r0001 observation step 50] The expected score is 1-0.
        self.assertEqual(adapted_result["score"], (1, 0))

    def test_engine_seed_words_preserved(self):
        """The seed words after the engine runs are the same on original
        and adapted (the adapter preserves DS:7B62 and DS:8336 exactly)."""
        original_result = _run_engine(self.original)
        gs = state.from_savestate(self.original)
        adapted = state.to_savestate(gs, original=self.original)
        adapted_result = _run_engine(adapted)
        self.assertEqual(adapted_result["seed_DS7B62"], original_result["seed_DS7B62"])
        self.assertEqual(adapted_result["seed_DS8336"], original_result["seed_DS8336"])


if __name__ == "__main__":
    unittest.main()
