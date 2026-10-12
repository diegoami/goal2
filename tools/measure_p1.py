#!/usr/bin/env python3
"""The P1 measurement: print the §9 numbers for the new-game fidelity.

Downloads GOAL.DAT and E006-r0001 from archaeology's releases, loads
them, runs the model, and prints the player array length, the structural
match count, the skill match count, and the LCG-driven mismatch count.

The output is the §9 measurement comment for the P1 milestone: it shows
what works (structural fields, 12 skills) and what's still a gap (the
LCG-driven fields, tracked in issue #11).

[confirmed: T02, T03, T04, E006, E007, F007, F008] The measurement uses
the same fixtures and formulas as the fidelity test.
"""
import hashlib
import json
import os
import subprocess
import sys
import zipfile
import zlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "goal2" / "engine"))

from goal2.data import goaldat
from goal2.engine import new_game, skills
from goal2.engine.savestate import Savestate

CACHE = ROOT / ".cache"
DAT = CACHE / "GOAL.DAT"
SAV = CACHE / "e006-r0001-main.sav"
E006_R0001_SHA = "e0afff6751747233f6ab8b9ba73dab0790b7509f15257ed7ae24f528b935657d"
MANAGED_COUNTRY = 7

PLAYER = 0x14
N_PLAYERS = 3061
# [confirmed: F007, F008] Structural fields that don't depend on the LCG draws.
STRUCTURAL_FIELDS = (0, 3, 6, 7, 0x12, 0x13)
# [confirmed: F007] LCG-driven fields (the known gap, issue #11).
LCG_FIELDS = (1, 2, 5, 0x0C)
# [derived from F007, E006] The current LCG gap is ~7,500 of 12,244 bytes.
LCG_GAP_LOW = 6_000
LCG_GAP_HIGH = 9_000


def _ensure_dat() -> bytes:
    if not DAT.is_file():
        CACHE.mkdir(parents=True, exist_ok=True)
        subprocess.run(
            ["gh", "release", "download", "goal2-original", "--repo", "diegoami/goal2-archaeology",
             "--pattern", "GOAL.DAT", "--dir", str(CACHE)],
            check=True,
        )
    data = DAT.read_bytes()
    if hashlib.sha256(data).hexdigest() != goaldat.SHA256:
        raise SystemExit(f"GOAL.DAT sha256 mismatch")
    return data


def _ensure_e006() -> bytes:
    if not SAV.is_file():
        CACHE.mkdir(parents=True, exist_ok=True)
        subprocess.run(
            ["gh", "release", "download", "E006", "--repo", "diegoami/goal2-archaeology",
             "--pattern", f"{E006_R0001_SHA[:16]}*", "--dir", str(CACHE), "--skip-existing"],
            check=True,
        )
        for f in CACHE.iterdir():
            if f.name.startswith(E006_R0001_SHA[:16]) and f.suffix == ".sav":
                if f != SAV:
                    f.rename(SAV)
                break
    data = SAV.read_bytes()
    if hashlib.sha256(data).hexdigest() != E006_R0001_SHA:
        raise SystemExit(f"E006-r0001 sha256 mismatch")
    return data


def _e006_player_array(state: "Savestate") -> bytes:
    import players  # noqa: E402
    return bytes(players.players(state))


def main() -> int:
    print("=== P1 fidelity measurement ===")
    dat = _ensure_dat()
    sav = _ensure_e006()
    print(f"GOAL.DAT: {len(dat)} bytes")
    print(f"E006-r0001: {len(sav)} bytes")

    d = goaldat.load(dat)
    state = Savestate(sav)
    expected = _e006_player_array(state)
    actual = new_game.make_all_players(d, managed_country=MANAGED_COUNTRY)

    # Structural match count
    structural_matches = 0
    structural_total = 0
    for i in range(N_PLAYERS):
        actual_rec = actual[i]
        expected_rec = expected[i * PLAYER:(i + 1) * PLAYER]
        for off in STRUCTURAL_FIELDS:
            if off == 3 and (i < 1 or i > 2560):
                continue
            structural_total += 1
            if actual_rec[off] == expected_rec[off]:
                structural_matches += 1

    # LCG-driven mismatch count
    lcg_mismatches = 0
    for i in range(N_PLAYERS):
        actual_rec = actual[i]
        expected_rec = expected[i * PLAYER:(i + 1) * PLAYER]
        for off in LCG_FIELDS:
            if actual_rec[off] != expected_rec[off]:
                lcg_mismatches += 1

    # Skill match count (needs E007; skip if not available)
    skill_matches = 0
    skill_total = 0
    archaeology = Path(os.environ.get("GOAL2_ARCHAEOLOGY", str(ROOT.parent.parent / "goal2-archaeology")))
    e007 = archaeology / "runs" / "E007"
    if e007.is_dir():
        class_table = skills.load_class_table(state)
        profile_table = skills.load_profile_table(state)
        from goal2.tests.test_skills import (
            SKILL_BAR_COL_START, SKILL_BAR_COL_END, SKILL_ROW_START, SKILL_ROW_END,
            BAR_ATTRIBUTE, _parse_text_screen, _get_observation,
        )
        for rec_num in range(9, 13):
            run_path = e007 / f"E007-r{rec_num:04d}.json"
            if not run_path.is_file():
                continue
            d_json = json.loads(run_path.read_text())
            obs = d_json["observations"]
            for n in range(1, 21):
                rec = bytes.fromhex(_get_observation(obs, f"player screen {n} of the list: the 20 bytes of player"))
                text_hex = _get_observation(obs, f"player screen {n} of the list: text screen 80x25 as the 4000 bytes B800:0000")
                text_rows = _parse_text_screen(text_hex)
                expected_bars = []
                for r in range(SKILL_ROW_START, SKILL_ROW_END):
                    count = sum(1 for c in range(SKILL_BAR_COL_START, SKILL_BAR_COL_END) if text_rows[r][c][1] == BAR_ATTRIBUTE)
                    expected_bars.append(count)
                model_bars = skills.skills(rec, class_table, profile_table)
                skill_total += 12
                if model_bars == expected_bars:
                    skill_matches += 12

    print()
    print(f"Player array: {N_PLAYERS} records ({N_PLAYERS * PLAYER} bytes)")
    # [confirmed: F007] 2560 squad players (128 countries x 20) + 80 managed-country
    # players + 1 record 0 + 420 trailing zero records = 3061.
    print(f"Squad players: 2560 (128 countries x 20)")
    print(f"Managed-country players: 80 (records 2561..2640)")
    print(f"Zero records: 421 (record 0 + 2641..3060)")
    print(f"Structural fields: {structural_matches} of {structural_total} match")
    # LCG gap bounds: a degenerate LCG would push the count to ~12,000+ or ~0.
    lcg_status = "OK" if LCG_GAP_LOW <= lcg_mismatches <= LCG_GAP_HIGH else "OUT OF BOUNDS"
    print(f"LCG-driven fields: {lcg_mismatches} of {N_PLAYERS * len(LCG_FIELDS)} differ "
          f"({lcg_status}; expected range {LCG_GAP_LOW}..{LCG_GAP_HIGH}, known gap #11)")
    if skill_total > 0:
        print(f"Skill bars: {skill_matches} of {skill_total} match ({skill_matches // 12} of {skill_total // 12} players)")
    else:
        print(f"Skill bars: E007 not available, skipped")

    # [designed] Country/player sanity check: print the 4 countries' first
    # player bytes (record 1, 21, 41, 61) for a visual check.
    print()
    print("Sanity check — first player of each country (record 1, 21, 41, 61):")
    country_names = {1: "country 1", 2: "country 2", 3: "country 3", 4: "country 4"}
    for c in range(1, 5):
        rec = actual[(c - 1) * 20 + 1]  # +1 because record 0 is the placeholder
        print(f"  {country_names[c]}: {bytes(rec).hex()}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
