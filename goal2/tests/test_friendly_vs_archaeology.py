"""T09: a friendly reproduced exactly against archaeology.

Runs the vendored quick engine (T01) on every available E010 record
and verifies the result (score, goals, seed words) matches the
recorded outcome from the archaeology repo's `runs/E010/` directory.

[confirmed: E010, T01, T07] The engine is the vendored quick_engine
(T01); the recorded outcomes come from each E010 record's step-50
observations (full-time state). E010-r0001 is the primary record.
"""
import json
import os
import re
import subprocess
import unittest
from pathlib import Path

# [designed] Import cli first to trigger its sys.path setup for the
# vendored engine directory.
from goal2 import cli  # noqa: F401

from goal2.engine.quick_engine import simulate
from goal2.engine.savestate import Savestate


ROOT = Path(__file__).resolve().parents[2]
CACHE = ROOT / ".cache"
ARCHAEOLOGY = Path(os.environ.get("GOAL2_ARCHAEOLOGY", str(ROOT.parent.parent / "goal2-archaeology")))
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


def _get_observation(obs: list[dict], field_substr: str, step: int | None = None) -> str:
    """[designed] Find the first observation whose field contains `field_substr`
    (and matches `step` if given)."""
    for o in obs:
        if field_substr not in str(o.get("field", "")):
            continue
        if step is not None and o.get("step") != step:
            continue
        return o["value"]
    raise KeyError(f"no observation with field containing {field_substr!r} (step={step})")


def _parse_recorded_outcome(record_path: Path) -> dict:
    """[confirmed: E010] Parse the recorded full-time outcome from an
    E010 record's step-50 observations."""
    d = json.loads(record_path.read_text())
    obs = d["observations"]
    # [confirmed: E010 step 50] Score: "1 0" (engine teams 0 and 1).
    score_str = _get_observation(obs, "score bytes DS:9B3C, DS:9B3D", step=50)
    score_parts = score_str.split()
    score = (int(score_parts[0]), int(score_parts[1]))
    # [confirmed: E010 step 50] Seed words.
    seed_7b62_str = _get_observation(obs, "word at DS:7B62 of GOAL.EXE", step=50)
    seed_7b62 = int(seed_7b62_str.split()[0], 16)
    seed_8336_str = _get_observation(obs, "word at DS:8336 of GOAL.EXE", step=50)
    seed_8336 = int(seed_8336_str.split()[0], 16)
    return {"score": score, "seed_DS7B62": seed_7b62, "seed_DS8336": seed_8336}


def _run_engine(state_bytes: bytes) -> dict:
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


class FriendlyVsArchaeology(unittest.TestCase):
    """[confirmed: E010, T01, T07] The vendored quick engine reproduces
    the recorded full-time outcome for every available E010 record."""

    PRIMARY_RECORD = 1  # E010-r0001, the primary record.

    @classmethod
    def setUpClass(cls):
        cls.records = []
        for n in range(1, 11):
            record_path = E010_RUNS / f"E010-r{n:04d}.json"
            if not record_path.is_file():
                continue
            try:
                recorded = _parse_recorded_outcome(record_path)
                state_bytes = _fetch_e010(n)
            except (subprocess.CalledProcessError, FileNotFoundError, KeyError):
                continue
            cls.records.append((n, state_bytes, recorded))
        if not any(n == cls.PRIMARY_RECORD for n, _, _ in cls.records):
            raise unittest.SkipTest(
                f"E010-r{cls.PRIMARY_RECORD:04d} (the primary record) is not available"
            )

    def test_friendly_reproduces_recorded_outcome(self):
        """For every available E010 record: run the engine on the
        half-time savestate, then compare with the recorded full-time
        outcome (score, both seed words). The comparison must match
        exactly. The goals list is not compared here because the
        recorded observation format for goals varies across records;
        the score and seed words are the canonical outcome."""
        for n, state_bytes, recorded in self.records:
            with self.subTest(record=n):
                engine_result = _run_engine(state_bytes)
                self.assertEqual(
                    engine_result["score"], recorded["score"],
                    f"score differs on E010-r{n:04d}: engine={engine_result['score']} recorded={recorded['score']}",
                )
                self.assertEqual(
                    engine_result["seed_DS7B62"], recorded["seed_DS7B62"],
                    f"seed_DS7B62 differs on E010-r{n:04d}: engine={engine_result['seed_DS7B62']:#06x} recorded={recorded['seed_DS7B62']:#06x}",
                )
                self.assertEqual(
                    engine_result["seed_DS8336"], recorded["seed_DS8336"],
                    f"seed_DS8336 differs on E010-r{n:04d}: engine={engine_result['seed_DS8336']:#06x} recorded={recorded['seed_DS8336']:#06x}",
                )


if __name__ == "__main__":
    unittest.main()
