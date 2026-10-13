"""The P1 fidelity test: an end-to-end check that goal2's new game produces
the same player array and skills as E006 and E007.

This ties together T02 (GOAL.DAT loader), T03 (new-game players) and T04
(12 skills). It downloads three fixtures: GOAL.DAT, E006-r0001 (the
main-screen savestate) and E007-r0009..r0012 (the 80 player screens).
Each fetch can fail; the test skips with the reason when any fixture is
absent.

[confirmed: E006, E007, F007, F008] The oracle is the archaeology's
published records; the model's output is checked against them field by
field.
"""
import hashlib
import json
import os
import subprocess
import sys
import unittest
from pathlib import Path

from goal2.data import goaldat
from goal2.engine import new_game, skills
from goal2.engine.savestate import Savestate


ROOT = Path(__file__).resolve().parents[2]
CACHE = ROOT / ".cache"
DAT = CACHE / "GOAL.DAT"
SAV = CACHE / "e006-r0001-main.sav"
ARCHAEOLOGY = Path(os.environ.get("GOAL2_ARCHAEOLOGY", str(ROOT.parent.parent / "goal2-archaeology")))
E007_RUNS = ARCHAEOLOGY / "runs" / "E007"

# [confirmed: T02] GOAL.DAT's expected sha256.
GOAL_DAT_SHA = goaldat.SHA256
# [confirmed: E006 release manifest] E006-r0001's asset sha256.
E006_R0001_SHA = "e0afff6751747233f6ab8b9ba73dab0790b7509f15257ed7ae24f528b935657d"
# [confirmed: F007] E006-r0001's managed country is country 7 (Denmark).
MANAGED_COUNTRY = 7

PLAYER = 0x14
N_PLAYERS = 3061
# [confirmed: F007, F008] Structural fields that don't depend on the LCG draws.
# +0x00 country, +0x03 potential (squad players only), +0x06/+0x07 position,
# +0x12/+0x13 fitness word.
STRUCTURAL_FIELDS = (0, 3, 6, 7, 0x12, 0x13)
# [confirmed: F007] LCG-driven fields (the former gap, issue #11, closed by T20).
# +0x01 age, +0x02 peak, +0x05, +0x0C.
LCG_FIELDS = (1, 2, 5, 0x0C)


def _fetch_dat() -> bytes:
    """[designed] Download GOAL.DAT from archaeology's goal2-original release, sha256-pinned."""
    if not DAT.is_file():
        CACHE.mkdir(parents=True, exist_ok=True)
        subprocess.run(
            ["gh", "release", "download", "goal2-original", "--repo", "diegoami/goal2-archaeology",
             "--pattern", "GOAL.DAT", "--dir", str(CACHE)],
            check=True, capture_output=True, text=True,
        )
    data = DAT.read_bytes()
    if hashlib.sha256(data).hexdigest() != GOAL_DAT_SHA:
        raise ValueError(f"GOAL.DAT sha256 differs from {GOAL_DAT_SHA}")
    return data


def _fetch_e006_state() -> bytes:
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


def _dat_or_skip() -> bytes:
    try:
        return _fetch_dat()
    except (subprocess.CalledProcessError, FileNotFoundError, ValueError) as e:
        raise unittest.SkipTest(f"GOAL.DAT not fetchable: {e}")


def _e006_bytes_or_skip() -> bytes:
    try:
        return _fetch_e006_state()
    except (subprocess.CalledProcessError, FileNotFoundError, ValueError) as e:
        raise unittest.SkipTest(f"E006-r0001 not fetchable: {e}")


def _e006_or_skip() -> "Savestate":
    try:
        return Savestate(_fetch_e006_state())
    except (subprocess.CalledProcessError, FileNotFoundError, ValueError) as e:
        raise unittest.SkipTest(f"E006-r0001 not fetchable: {e}")


def _e007_or_skip() -> list[Path]:
    """[confirmed: E007] Return the 4 E007 run files (r0009..r0012), or skip."""
    if not E007_RUNS.is_dir():
        raise unittest.SkipTest(f"E007 runs not found at {E007_RUNS}")
    paths = [E007_RUNS / f"E007-r{n:04d}.json" for n in (9, 10, 11, 12)]
    for p in paths:
        if not p.is_file():
            raise unittest.SkipTest(f"E007 run not found at {p}")
    return paths


def _e006_player_array(state_bytes: bytes) -> bytes:
    """[confirmed: F007, E006] Read the 0xEF24-byte player array from E006-r0001.
    Uses the vendored `Savestate` and `players` readers (T01)."""
    state = Savestate(state_bytes)
    # The vendored `players` module reads from the data segment; import it
    # with the engine directory on sys.path.
    engine_dir = ROOT / "goal2" / "engine"
    if str(engine_dir) not in sys.path:
        sys.path.insert(0, str(engine_dir))
    import players  # noqa: E402
    return bytes(players.players(state))


class StructuralFidelity(unittest.TestCase):
    """[confirmed: F007, E006] The structural fields of the player array match
    E006-r0001 for all 3061 records."""

    @classmethod
    def setUpClass(cls):
        cls.d = goaldat.load(_dat_or_skip())
        cls.expected = _e006_player_array(_e006_bytes_or_skip())

    def test_player_array_length(self):
        self.assertEqual(len(self.expected), N_PLAYERS * PLAYER)

    def test_structural_fields_match_e006(self):
        """All 3061 records have the right country byte, +0x03 potential,
        +0x06/+0x07 position, +0x12/+0x13 fitness word. This catches a
        no-op model (all-zero records would fail the country check)."""
        actual = new_game.make_all_players(self.d, managed_country=MANAGED_COUNTRY)
        mismatches = []
        for i in range(N_PLAYERS):
            actual_rec = actual[i]
            expected_rec = self.expected[i * PLAYER:(i + 1) * PLAYER]
            for off in STRUCTURAL_FIELDS:
                if off == 3 and (i < 1 or i > 2560):
                    # +0x03 for managed-country players (2561..2640) is LCG-dependent
                    continue
                if actual_rec[off] != expected_rec[off]:
                    mismatches.append((i, off, actual_rec[off], expected_rec[off]))
        self.assertEqual(
            mismatches, [],
            f"{len(mismatches)} structural mismatches: {mismatches[:5]}",
        )


class SkillFidelity(unittest.TestCase):
    """[confirmed: F008, E007] All 960 skill bars match E007-r0009..r0012."""

    @classmethod
    def setUpClass(cls):
        cls.d = goaldat.load(_dat_or_skip())
        state = _e006_or_skip()
        cls.class_table = skills.load_class_table(state)
        cls.profile_table = skills.load_profile_table(state)
        cls.expected_bars = _e007_skill_bars(_e007_or_skip())

    def test_skill_bars_match_e007(self):
        """For each of the 80 players, the model's 12 skill bars must match
        the E007 screen's parsed bars. 0 mismatches across 960 bars."""
        from goal2.tests.test_skills import _get_observation  # reuse the helper
        expected_bars = self.expected_bars
        all_records = []
        for run_path in _e007_or_skip():
            d = json.loads(run_path.read_text())
            obs = d["observations"]
            for n in range(1, 21):
                rec_hex = _get_observation(obs, f"player screen {n} of the list: the 20 bytes of player")
                all_records.append(bytes.fromhex(rec_hex))
        self.assertEqual(len(all_records), 80)
        mismatches = []
        for i, rec in enumerate(all_records):
            model_bars = skills.skills(rec, self.class_table, self.profile_table)
            if model_bars != expected_bars[i]:
                mismatches.append((i, expected_bars[i], model_bars))
        self.assertEqual(
            mismatches, [],
            f"{len(mismatches)} of 80 players have mismatched bars: {mismatches[:5]}",
        )


class LCGGapMeasurement(unittest.TestCase):
    """[confirmed: F007, E006; T20] The LCG-driven fields were a known gap
    (issue #11, ~7,500 of 12,244 bytes before T20). Since T20's reconciliation
    they match E006 byte-for-byte; this test pins that closed gap."""

    @classmethod
    def setUpClass(cls):
        cls.d = goaldat.load(_dat_or_skip())
        cls.expected = _e006_player_array(_e006_bytes_or_skip())

    def test_lcg_gap_measurement(self):
        """Count byte mismatches in the LCG-driven fields across all 3061
        records. 0 mismatches since T20 (issue #11's byte-exact
        reconciliation)."""
        actual = new_game.make_all_players(self.d, managed_country=MANAGED_COUNTRY)
        mismatches = 0
        for i in range(N_PLAYERS):
            actual_rec = actual[i]
            expected_rec = self.expected[i * PLAYER:(i + 1) * PLAYER]
            for off in LCG_FIELDS:
                if actual_rec[off] != expected_rec[off]:
                    mismatches += 1
        print(f"\nLCG-driven byte mismatches: {mismatches} of {N_PLAYERS * len(LCG_FIELDS)}")
        # [confirmed: T19 report §4.5] The reconciled model matches E006 on
        # every modelled byte; anything above 0 — a degenerate LCG included —
        # fails. Before T20 this count was 7,510 (T19 report §1), inside the
        # old 6,000-9,000 "working LCG" bounds.
        self.assertEqual(
            mismatches, 0,
            f"LCG-driven mismatches {mismatches} of {N_PLAYERS * len(LCG_FIELDS)}; "
            "expected 0 since T20 (issue #11)",
        )


def _e007_skill_bars(run_paths: list[Path]) -> list[list[int]]:
    """[confirmed: E007] Parse the 12 skill bars from each of the 80 player
    screens in E007-r0009..r0012. Reuses the parser from test_skills."""
    from goal2.tests.test_skills import (
        SKILL_BAR_COL_START, SKILL_BAR_COL_END, SKILL_ROW_START, SKILL_ROW_END,
        BAR_ATTRIBUTE, _parse_text_screen, _get_observation,
    )
    all_bars = []
    for run_path in run_paths:
        d = json.loads(run_path.read_text())
        obs = d["observations"]
        for n in range(1, 21):
            text_hex = _get_observation(
                obs,
                f"player screen {n} of the list: text screen 80x25 as the 4000 bytes B800:0000",
            )
            text_rows = _parse_text_screen(text_hex)
            bars = []
            for r in range(SKILL_ROW_START, SKILL_ROW_END):
                count = sum(
                    1 for c in range(SKILL_BAR_COL_START, SKILL_BAR_COL_END)
                    if text_rows[r][c][1] == BAR_ATTRIBUTE
                )
                bars.append(count)
            all_bars.append(bars)
    return all_bars


if __name__ == "__main__":
    unittest.main()
