"""Tests for `goal2.engine.skills` (T04 scope, the 12 skills derivation).

The fidelity test reads E007-r0009..r0012's player screens from the
archaeology repo, parses the 12 skill bars from each screen, and
compares them against the model's output. The data is read from the
archaeology repo's `runs/E007/` directory (not a GitHub release; the
E007 data is in the archaeology repo's git history).

[confirmed: F008 is the per-field source; E007-r0009..r0012's expected
bars are the fidelity oracle (experiments/E007-q009-player-screen).]
"""
import hashlib
import json
import os
import subprocess
import sys
import unittest
from pathlib import Path

from goal2.engine import skills
from goal2.engine.savestate import Savestate


ROOT = Path(__file__).resolve().parents[2]
# [designed] The archaeology repo is a sibling of the goal2 repo
# (`~/projects/goal2-archaeology`); the default walks up from the worktree
# to find it. Set GOAL2_ARCHAEOLOGY to override.
ARCHAEOLOGY = Path(os.environ.get("GOAL2_ARCHAEOLOGY", str(ROOT.parent.parent / "goal2-archaeology")))
E007_RUNS = ARCHAEOLOGY / "runs" / "E007"
CACHE = ROOT / ".cache"

# [confirmed: E006 release manifest] E006-r0001's asset sha256.
E006_R0001_SHA = "e0afff6751747233f6ab8b9ba73dab0790b7509f15257ed7ae24f528b935657d"

# [confirmed: F008] The skill bar field starts at column 10 (after the skill
# name + separator) and is 26 cells wide (columns 10..35). Rows 11..22 hold
# the 12 skills.
SKILL_BAR_COL_START = 10
SKILL_BAR_COL_END = 36  # exclusive
SKILL_ROW_START = 11
SKILL_ROW_END = 23  # exclusive
BAR_ATTRIBUTE = 0x70


def _parse_text_screen(hex_str: str) -> list[tuple[int, int]]:
    """[designed] Parse a text screen hex string (4000 bytes = 25 rows × 80 cols × 2)
    into a list of (char, attr) tuples per row. Returns 25 rows. The format
    (4000 bytes, interleaved char/attr) is the savestate's text page layout
    (vendored `Savestate.screen()`)."""
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
    """[designed] Find the first observation whose field contains `field_substr`.
    The E007 JSON observations are a list of dicts with `field` and `value` keys."""
    for o in obs:
        if field_substr in str(o.get("field", "")):
            return o["value"]
    raise KeyError(f"no observation with field containing {field_substr!r}")


def _load_e007_record(record_path: Path) -> list[dict]:
    """[designed] Load an E007 JSON record and return a list of per-player dicts
    with the 20-byte record and the parsed 12 skill bars. The data tables are
    also extracted (for the TableLoaders comparison test) but the E007Fidelity
    test uses the tables loaded from the E006-r0001 savestate, not these."""
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


def _fetch_e006_state() -> bytes:
    """[designed] Find E006-r0001's main-screen savestate in `.cache/`,
    sha256-pinned. Downloads from archaeology's E006 release on first use;
    also accepts a file already present under its release asset name."""
    sav_path = CACHE / "e006-r0001-main.sav"
    if not sav_path.is_file():
        CACHE.mkdir(parents=True, exist_ok=True)
        # Look for an existing file with the release asset name first.
        for f in CACHE.iterdir():
            if f.name.startswith(E006_R0001_SHA[:16]) and f.suffix == ".sav":
                f.rename(sav_path)
                break
        if not sav_path.is_file():
            subprocess.run(
                ["gh", "release", "download", "E006", "--repo", "diegoami/goal2-archaeology",
                 "--pattern", f"{E006_R0001_SHA[:16]}*", "--dir", str(CACHE),
                 "--skip-existing"],
                check=True, capture_output=True, text=True,
            )
            for f in CACHE.iterdir():
                if f.name.startswith(E006_R0001_SHA[:16]) and f.suffix == ".sav":
                    if f != sav_path:
                        f.rename(sav_path)
                    break
    data = sav_path.read_bytes()
    if hashlib.sha256(data).hexdigest() != E006_R0001_SHA:
        raise ValueError(f"E006-r0001 sha256 differs from {E006_R0001_SHA}")
    return data


def _e006_or_skip() -> "Savestate":
    try:
        return Savestate(_fetch_e006_state())
    except (subprocess.CalledProcessError, FileNotFoundError, ValueError) as e:
        raise unittest.SkipTest(f"E006-r0001 not fetchable: {e}")


class TableLoaders(unittest.TestCase):
    """[confirmed: F008] The loaders read the data tables from the savestate's
    data segment. The tables must match the ones the E007 player screens used
    (the same DOS session)."""

    @classmethod
    def setUpClass(cls):
        cls.state = _e006_or_skip()
        cls.class_loaded = skills.load_class_table(cls.state)
        cls.profile_loaded = skills.load_profile_table(cls.state)

    def test_class_table_size_covers_all_positions(self):
        # 14 positions × 12 classes (1-indexed) = 169 bytes (offset 0..168).
        self.assertEqual(len(self.class_loaded), 169)

    def test_profile_table_size_covers_all_profiles(self):
        # 17 profiles (0..16) × 12 classes (1-indexed) = 205 bytes.
        self.assertEqual(len(self.profile_loaded), 205)

    def test_loaded_tables_match_e007(self):
        """[confirmed: F008, E007] The tables loaded from the E006-r0001
        savestate must match the tables recorded in E007-r0009's observations
        (same DOS session). Skips when the E007 run file is absent."""
        run_path = E007_RUNS / "E007-r0009.json"
        if not run_path.is_file():
            raise unittest.SkipTest(f"E007 run not found at {run_path}")
        d = json.loads(run_path.read_text())
        tables_bytes = bytes.fromhex(_get_observation(d["observations"], "DS:6D20..6EB3"))
        class_expected = tables_bytes[5:5 + 169]
        profile_expected = tables_bytes[0xAD:0xAD + 205]
        self.assertEqual(self.class_loaded, class_expected)
        self.assertEqual(self.profile_loaded, profile_expected)

    def test_loaders_handle_max_position_and_profile(self):
        """Position 13, profile 16 are the max valid inputs; the loaded tables
        must have entries at those indices (no IndexError)."""
        # Class table: position 13, skill 12 → offset 12*13+12 = 168
        self.assertIn(self.class_loaded[168], range(0, 13))
        # Profile table: profile 16, class 12 → offset 12*16+12 = 204
        self.assertIn(self.profile_loaded[204], range(0, 27))


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
    E007-r0009..r0012's published bars. 80 players × 12 bars = 960 bars.
    The data tables are loaded from the E006-r0001 savestate (the same DOS
    session the E007 screens were taken from)."""

    @classmethod
    def setUpClass(cls):
        # [confirmed: F008, E007] Skip if any of the 4 required E007 run files
        # are absent; a partial directory is not enough.
        for rec_num in range(9, 13):  # r0009..r0012
            rec_path = E007_RUNS / f"E007-r{rec_num:04d}.json"
            if not rec_path.is_file():
                raise unittest.SkipTest(f"E007 run not found at {rec_path}")
        state = _e006_or_skip()
        cls.class_table = skills.load_class_table(state)
        cls.profile_table = skills.load_profile_table(state)
        cls.all_players = []
        for rec_num in range(9, 13):  # r0009..r0012
            rec_path = E007_RUNS / f"E007-r{rec_num:04d}.json"
            players, _json_class, _json_profile = _load_e007_record(rec_path)
            cls.all_players.extend(players)

    def test_80_players_loaded(self):
        self.assertEqual(len(self.all_players), 80)

    def test_skill_bars_match_e007(self):
        """For each of the 80 players, the model's 12 skill bars must match
        the E007 screen's parsed bars. 0 mismatches across 960 bars.
        The tables come from the E006-r0001 savestate, not the JSON."""
        mismatches = []
        for i, p in enumerate(self.all_players):
            model_bars = skills.skills(p["record"], self.class_table, self.profile_table)
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
