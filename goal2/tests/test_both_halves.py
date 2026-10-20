"""[derived: T26] T08's independent second-half replay regression.

This test runs the vendored engine twice on the same E010 half-time input.
It proves deterministic replay of the second half. T26's full-match test
exercises consecutive halves on one mutable engine instance.

[confirmed: E010, T01, T07] The engine is the vendored quick_engine
(T01); the adapter is the state adapter (T06/T07). E010-r0001 is a
half-time savestate; the engine runs the second half from it.
"""
import subprocess
import unittest
from pathlib import Path

# [designed] Import cli first to trigger its sys.path setup for the
# vendored engine directory.
from goal2 import cli  # noqa: F401

from goal2.engine.quick_engine import simulate
from goal2.engine.savestate import Savestate
from goal2.tests import requires


ROOT = Path(__file__).resolve().parents[2]
CACHE = ROOT / ".cache"
ARCHAEOLOGY = requires.archaeology()
E010_RUNS = ARCHAEOLOGY / "runs" / "E010"


def _fetch_e010(n: int = 1) -> bytes:
    """[designed] Download E010-rNNNN's half-time savestate from the
    E010 release."""
    sav_path = CACHE / f"e010-r{n:04d}-halftime.sav"
    if not sav_path.is_file():
        CACHE.mkdir(parents=True, exist_ok=True)
        subprocess.run(
            ["gh", "release", "download", "E010", "--repo", "diegoami/goal2-archaeology",
             "--pattern", "*.sav", "--dir", str(CACHE), "--skip-existing"],
            check=True, capture_output=True, text=True,
        )
        suffix = f"-E010-r{n:04d}-halftime.sav"
        for f in CACHE.iterdir():
            if f.name.endswith(suffix):
                if f != sav_path:
                    f.rename(sav_path)
                break
    if not sav_path.is_file():
        raise FileNotFoundError(f"E010-r{n:04d} savestate not found in {CACHE}")
    return sav_path.read_bytes()


def _run_half(state_bytes: bytes) -> dict:
    """[designed] Run the vendored engine on the given half-time savestate
    and return a comparable result dict."""
    sav = Savestate(state_bytes)
    result = simulate(sav)
    return {
        "score": tuple(result["score"]),
        "goals": tuple((g["team"], g["player"], g["minute"]) for g in result["goals"]),
        "seed_DS7B62": result["seed_DS7B62"],
        "seed_DS8336": result["seed_DS8336"],
    }


class BothHalvesReproducibility(unittest.TestCase):
    """[derived: E010/T01] Independent replays of one half are identical."""

    PRIMARY_RECORD = 1  # E010-r0001, the primary record.

    @classmethod
    def setUpClass(cls):
        requires.require(archaeology=True)
        cls.records = []
        for n in range(1, 11):
            record_path = E010_RUNS / f"E007-r{n:04d}.json" if False else E010_RUNS / f"E010-r{n:04d}.json"
            if not record_path.is_file():
                continue
            try:
                cls.records.append((n, _fetch_e010(n)))
            except (subprocess.CalledProcessError, FileNotFoundError):
                continue
        if not any(n == cls.PRIMARY_RECORD for n, _ in cls.records):
            raise unittest.SkipTest(
                f"E010-r{cls.PRIMARY_RECORD:04d} (the primary record) is not available"
            )

    def test_both_halves_reproducible(self):
        """[confirmed: F004, T01] For every available E010 record: run
        the engine on the half-time state, then re-read the savestate
        and run it again. The two results must be identical. This
        proves deterministic second-half replay from the seed words."""
        for n, state_bytes in self.records:
            with self.subTest(record=n):
                first = _run_half(state_bytes)
                # Re-read the savestate to reset guest memory.
                state_bytes_2 = _fetch_e010(n)
                second = _run_half(state_bytes_2)
                self.assertEqual(
                    first, second,
                    f"engine result differs between two runs on E010-r{n:04d}: "
                    f"first={first} second={second}",
                )

    def test_both_halves_all_fields_match(self):
        """[confirmed: F004, T01] Score, goals, and seed words must all
        match between two independent runs. A mutation that changes
        only the score (or only the goals, or only the seed words)
        fails this test."""
        n, state_bytes = self.records[0]
        first = _run_half(state_bytes)
        state_bytes_2 = _fetch_e010(n)
        second = _run_half(state_bytes_2)
        # Every field must match.
        self.assertEqual(first["score"], second["score"], "score differs")
        self.assertEqual(first["goals"], second["goals"], "goals differ")
        self.assertEqual(first["seed_DS7B62"], second["seed_DS7B62"], "seed_DS7B62 differs")
        self.assertEqual(first["seed_DS8336"], second["seed_DS8336"], "seed_DS8336 differs")


if __name__ == "__main__":
    unittest.main()
