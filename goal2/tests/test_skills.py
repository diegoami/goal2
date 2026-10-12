"""Tests for `goal2.engine.skills` (T04 scope, the 12 skills derivation).

The fidelity test reads E007-r0009..r0012's player screens from the
archaeology repo, parses the 12 skill bars from each screen, and
compares them against the model's output. The data is read from the
archaeology repo's `runs/E007/` directory (not a GitHub release; the
E007 data is in the archaeology repo's git history).

[confirmed: F008 is the per-field source; E007-r0009..r0012's expected
bars are the fidelity oracle (experiments/E007-q009-player-screen).]
"""
import json
import os
import sys
import unittest
from pathlib import Path

from goal2.engine import skills


ROOT = Path(__file__).resolve().parents[2]
# [designed] The archaeology repo is a sibling of the goal2 repo
# (`~/projects/goal2-archaeology`); the default walks up from the worktree
# to find it. Set GOAL2_ARCHAEOLOGY to override.
ARCHAEOLOGY = Path(os.environ.get("GOAL2_ARCHAEOLOGY", str(ROOT.parent.parent / "goal2-archaeology")))
E007_RUNS = ARCHAEOLOGY / "runs" / "E007"

# [confirmed: F008] The skill bar field starts at column 10 (after the skill
# name + separator) and is 26 cells wide (columns 10..35). Rows 11..22 hold
# the 12 skills.
SKILL_BAR_COL_START = 10
SKILL_BAR_COL_END = 36  # exclusive
SKILL_ROW_START = 11
SKILL_ROW_END = 23  # exclusive
BAR_ATTRIBUTE = 0x70


def _parse_text_screen(hex_str: str) -> list[tuple[int, int]]:
    """Parse a text screen hex string (4000 bytes = 25 rows × 80 cols × 2)
    into a list of (char, attr) tuples per row. Returns 25 rows."""
    raw = bytes.fromhex(hex_str)
    assert len(raw) == 4000, f"expected 4000 bytes, got {len(raw)}"
    rows = []
    for r in range(25):
        row = []
        for c in range(80):
            off = (r * 80 + c) * 2
            row.append((raw[off], raw[off + 1]))
        rows.append(row)
    return rows


def _parse_skill_bars(text_rows: list[list[tuple[int, int]]]) -> list[int]:
    """Parse the 12 skill bars from a parsed text screen.
    For each row 11..22, count the 0x70 attribute cells in columns 11..36."""
    bars = []
    for r in range(SKILL_ROW_START, SKILL_ROW_END):
        count = 0
        for c in range(SKILL_BAR_COL_START, SKILL_BAR_COL_END):
            if text_rows[r][c][1] == BAR_ATTRIBUTE:
                count += 1
        bars.append(count)
    return bars


def _get_observation(obs: list[dict], field_substr: str) -> str:
    """Find the first observation whose field contains `field_substr`."""
    for o in obs:
        if field_substr in str(o.get("field", "")):
            return o["value"]
    raise KeyError(f"no observation with field containing {field_substr!r}")


def _load_e007_record(record_path: Path) -> list[dict]:
    """Load an E007 JSON record and return a list of per-player dicts with
    the 20-byte record, the data tables, and the parsed 12 skill bars."""
    d = json.loads(record_path.read_text())
    obs = d["observations"]
    # Load the data tables (one per record, shared across all 20 players)
    tables_hex = _get_observation(obs, "DS:6D20..6EB3")
    # Extract the class table (DS:6D25, 14*12 bytes = 168 bytes, offset 5 in the 404-byte block)
    # and the profile table (DS:6DCD, 16*12 bytes = 192 bytes, offset 0xD5 = 213 in the block)
    tables_bytes = bytes.fromhex(tables_hex)
    class_table = tables_bytes[5:5 + 14 * 12 + 1]  # DS:6D25 - DS:6D20 = 5, +1 for the 1-indexed last entry
    profile_table = tables_bytes[0xAD:0xAD + 17 * 12 + 1]  # DS:6DCD - DS:6D20 = 0xAD, covers profiles 0..16
    players = []
    for n in range(1, 21):
        rec_hex = _get_observation(obs, f"player screen {n} of the list: the 20 bytes of player")
        rec = bytes.fromhex(rec_hex)
        text_hex = _get_observation(
            obs,
            f"player screen {n} of the list: text screen 80x25 as the 4000 bytes B800:0000",
        )
        text_rows = _parse_text_screen(text_hex)
        bars = _parse_skill_bars(text_rows)
        players.append({"record": rec, "bars": bars})
    return players, class_table, profile_table


class DataTables(unittest.TestCase):
    """[confirmed: F008] The data tables the model reads."""

    def test_skill_names(self):
        self.assertEqual(skills.SKILL_NAMES, (
            "keeping", "kicking", "tackling", "heading", "marking", "passing",
            "crossing", "feinting", "control", "dribbling", "shooting", "penalties",
        ))

    def test_class_table_dimensions(self):
        self.assertEqual(skills.CLASS_TABLE_POSITIONS, 14)
        self.assertEqual(skills.CLASS_TABLE_ROWS, 12)

    def test_profile_table_dimensions(self):
        self.assertEqual(skills.PROFILE_TABLE_PROFILES, 16)
        self.assertEqual(skills.PROFILE_TABLE_CLASSES, 12)

    def test_class_table_offset(self):
        self.assertEqual(skills.CLASS_TABLE_OFFSET, 0x6D25)

    def test_profile_table_offset(self):
        self.assertEqual(skills.PROFILE_TABLE_OFFSET, 0x6DCD)


class AllZeroRecord(unittest.TestCase):
    """[designed] The all-zero record with dummy all-zero tables gives 12 zeros
    (the brief's DW3: the function works on the simplest input)."""

    def test_all_zero_record_skills(self):
        rec = bytes(20)
        # Dummy all-zero tables: class[1] = 0, profile[0] = 0, so each bar is 0.
        class_table = bytes(14 * 12 + 1)
        profile_table = bytes(17 * 12 + 1)
        self.assertEqual(skills.skills(rec, class_table, profile_table), [0] * 12)


class E007Fidelity(unittest.TestCase):
    """[confirmed: F008, E007] The fidelity test: the model's 12 skill bars vs
    E007-r0009..r0012's published bars. 80 players × 12 bars = 960 bars."""

    @classmethod
    def setUpClass(cls):
        if not E007_RUNS.is_dir():
            raise unittest.SkipTest(f"E007 runs not found at {E007_RUNS}")
        cls.all_players = []
        for rec_num in range(9, 13):  # r0009..r0012
            rec_path = E007_RUNS / f"E007-r{rec_num:04d}.json"
            players, class_table, profile_table = _load_e007_record(rec_path)
            for p in players:
                p["class_table"] = class_table
                p["profile_table"] = profile_table
            cls.all_players.extend(players)

    def test_80_players_loaded(self):
        self.assertEqual(len(self.all_players), 80)

    def test_skill_bars_match_e007(self):
        """For each of the 80 players, the model's 12 skill bars must match
        the E007 screen's parsed bars. 0 mismatches across 960 bars."""
        mismatches = []
        for i, p in enumerate(self.all_players):
            model_bars = skills.skills(p["record"], p["class_table"], p["profile_table"])
            if model_bars != p["bars"]:
                mismatches.append((i, p["bars"], model_bars))
        if mismatches:
            details = "\n".join(
                f"  player {i}: expected={exp} got={got}"
                for i, exp, got in mismatches[:5]
            )
            self.fail(
                f"{len(mismatches)} of 80 players have mismatched bars:\n{details}"
            )


if __name__ == "__main__":
    unittest.main()
