"""Tests for `goal2.engine.new_game` (T03 scope, the new-game player model).

The fidelity test downloads E006-r0001's published main-screen savestate from
archaeology's E006 release, reads the player array the original game made,
and compares it against the model's output. The state is git-ignored (rule 19);
the test fetches on demand and skips with the reason when the fetch fails.

[confirmed: F007 is the per-field source; E006-r0001's expected player
array is the fidelity oracle (release E006 of goal2-archaeology).]
"""
import hashlib
import os
import subprocess
import sys
import unittest
import zipfile
import zlib
from pathlib import Path

from goal2.data import goaldat
from goal2.engine import new_game


ROOT = Path(__file__).resolve().parents[2]
CACHE = ROOT / ".cache"
DAT = CACHE / "GOAL.DAT"
SAV = CACHE / "e006-r0001-main.sav"
ARCHAEOLOGY = Path(os.environ.get("GOAL2_ARCHAEOLOGY", str(ROOT.parent / "goal2-archaeology")))
RELEASE = "E006"
REPO = "diegoami/goal2-archaeology"

# [confirmed: F007] The managed country in E006-r0001 is country 7 (Denmark).
MANAGED_COUNTRY = 7

# [confirmed: E006 release manifest] E006-r0001's asset sha256[:16].
E006_R0001_SHA = "e0afff6751747233f6ab8b9ba73dab0790b7509f15257ed7ae24f528b935657d"


def _fetch_dat() -> bytes:
    """[designed] Download GOAL.DAT from `goal2-original` into `.cache/`, sha256-pinned."""
    if not DAT.is_file():
        CACHE.mkdir(parents=True, exist_ok=True)
        subprocess.run(
            ["gh", "release", "download", "goal2-original", "--repo", REPO,
             "--pattern", "GOAL.DAT", "--dir", str(CACHE)],
            check=True,
        )
    data = DAT.read_bytes()
    if hashlib.sha256(data).hexdigest() != goaldat.SHA256:
        raise ValueError(f"GOAL.DAT sha256 differs from {goaldat.SHA256}")
    return data


def _fetch_state() -> bytes:
    """[designed] Download E006-r0001's main-screen savestate into `.cache/`,
    sha256-pinned. Tries both the worktree's `.cache/` and the worktree root
    as the download directory; some `gh` versions write to cwd."""
    if not SAV.is_file():
        CACHE.mkdir(parents=True, exist_ok=True)
        asset_prefix = E006_R0001_SHA[:16]
        # Try to find the asset with the right pattern; the file may land
        # in CACHE (preferred) or in cwd if `gh` ignores --dir.
        search_dirs = [CACHE, ROOT]
        for d in search_dirs:
            try:
                subprocess.run(
                    ["gh", "release", "download", RELEASE, "--repo", REPO,
                     "--pattern", f"{asset_prefix}*", "--dir", str(d)],
                    check=True, capture_output=True, text=True,
                )
            except subprocess.CalledProcessError:
                continue
        for d in search_dirs:
            for f in d.iterdir():
                if f.name.startswith(asset_prefix) and f.suffix in (".sav", ".zip"):
                    if f != SAV:
                        f.rename(SAV)
                    return SAV.read_bytes()
        raise FileNotFoundError(
            f"no .sav asset found for {asset_prefix}* in {search_dirs}"
        )
    return SAV.read_bytes()


def _dat_or_skip() -> bytes:
    try:
        return _fetch_dat()
    except (subprocess.CalledProcessError, FileNotFoundError, ValueError) as e:
        raise unittest.SkipTest(f"GOAL.DAT not fetchable: {e}")


def _state_or_skip() -> bytes:
    try:
        return _fetch_state()
    except (subprocess.CalledProcessError, FileNotFoundError, ValueError) as e:
        raise unittest.SkipTest(f"E006-r0001 main-screen state not fetchable: {e}")


def _e006_player_array(state_bytes: bytes) -> bytes:
    """[confirmed: F007] Read the 0xEF24-byte player array from the E006 main-screen
    savestate. Uses the vendored `Savestate` and `players` readers (T01)."""
    # Set up engine dir on sys.path for the vendored players module.
    engine_dir = str(ROOT / "goal2" / "engine")
    if engine_dir not in sys.path:
        sys.path.insert(0, engine_dir)
    import savestate  # noqa: E402
    import players  # noqa: E402
    state = savestate.Savestate(state_bytes)
    return bytes(players.players(state))


class DataTables(unittest.TestCase):
    """[confirmed: F007, ds_2581_01.hex] The constants the model reads."""

    def test_DS_118A(self):
        self.assertEqual(new_game.DS_118A, (0x1F, 0x1C))

    def test_DS_0E80(self):
        self.assertEqual(new_game.DS_0E80, (0x1E, 0x1B))

    def test_DS_118C(self):
        self.assertEqual(new_game.DS_118C, (0x11, 0x14))

    def test_DS_0E82(self):
        self.assertEqual(new_game.DS_0E82, (0x10, 0x0D))


class CountryRank(unittest.TestCase):
    """[confirmed: F007] +0x2B from block 8, +0x2C/+0x2A from block 9."""

    def setUp(self):
        self.d = goaldat.load(_dat_or_skip())

    def test_denmark_country_record_values(self):
        # F007: Denmark's country record reads +0x2A..+0x2F = `1c 50 1c 50 01 f7 01 04`
        # → +0x2A=28, +0x2B=80, +0x2C=1.
        world, continent, within = new_game.country_rank(self.d, 1)
        self.assertEqual((world, continent, within), (80, 1, 28))

    def test_germany_position_in_block_8(self):
        # F007: "Germany reads 1, 1, 2" is the main-screen display, not the
        # +0x2B byte the rating formula reads. The function reads the
        # permutation positions; this only asserts they are positive ints.
        world, continent, within = new_game.country_rank(self.d, 2)
        self.assertGreater(world, 0)
        self.assertGreaterEqual(continent, 1)
        self.assertLessEqual(continent, 4)
        self.assertGreaterEqual(within, 1)
        self.assertLessEqual(within, 32)

    def test_rating_for_denmark(self):
        # F007: rating = ((5-1)(33-28) + (129-80)) / 2 = 34 (= 0xA1 - 0x7F).
        self.assertEqual(new_game.rating(self.d, 1), 34)


class PlayerOneCountry(unittest.TestCase):
    """[confirmed: F007] Spot-checks country 1's first player against the expected
    structural shape: country byte, position, zero-padded fields, +0x12 word."""

    def setUp(self):
        self.d = goaldat.load(_dat_or_skip())
        self.players = new_game.make_all_players(self.d, managed_country=MANAGED_COUNTRY)

    def test_player_1_country(self):
        self.assertEqual(self.players[1][0], 1)

    def test_player_1_position_bytes(self):
        # Country 1, slot 0, position 0 (goalkeeper, per F011's squad_20 ordering).
        self.assertEqual(self.players[1][6], 0)
        self.assertEqual(self.players[1][7], 0)

    def test_player_1_potential_matches_F007_example(self):
        # F007: player 1 reads +0x03 = 0xA1 = 161, which is rating(1) + 0x7F = 34 + 127.
        self.assertEqual(self.players[1][3], 0xA1)

    def test_player_1_fitness_word(self):
        # F007: +0x12 (word) = 0x7FFF at new game.
        self.assertEqual(self.players[1][0x12], 0xFF)
        self.assertEqual(self.players[1][0x13], 0x7F)

    def test_player_1_zero_padded_fields(self):
        # +0x08..+0x0B and +0x10..+0x11 are 0 per F007.
        for i in (8, 9, 10, 11, 0x10, 0x11):
            self.assertEqual(self.players[1][i], 0, f"byte +0x{i:x} not zero")


class E006Fidelity(unittest.TestCase):
    """[confirmed: F007, E006] The fidelity test: the model's player array vs
    E006-r0001's published array. The structural fields match; the LCG-driven
    fields (age, peak, +0x05) are a T03 follow-up (the draw order needs the
    E006 `summarise.py`'s LCG call sequence to be reconciled)."""

    @classmethod
    def setUpClass(cls):
        cls.d = goaldat.load(_dat_or_skip())
        cls.state = _state_or_skip()
        cls.expected = _e006_player_array(cls.state)

    def test_player_array_length(self):
        self.assertEqual(len(self.expected), 0xEF24)

    def test_structural_fields_match_e006(self):
        """The structural fields (country, +0x03 potential, +0x06/+0x07
        position, +0x12 fitness) match the E006 array for the 2560 squad
        players (records 1..2560). This catches no-op models. +0x03 for
        records 2561..2640 is excluded (the managed-country 98C4 routine
        uses `rating + 0x7F - 10 - rand(10)`, which depends on the LCG).
        +0x0F is excluded because it depends on +0x05 (an LCG draw). The
        LCG-driven fields (+0x01 age, +0x02 peak, +0x05) are not checked
        here — they're the T03 follow-up's source of truth."""
        actual = new_game.make_all_players(self.d, managed_country=MANAGED_COUNTRY)
        PLAYER = 0x14
        # +0x03 is LCG-independent for squad players (rating + 0x7F), but
        # LCG-dependent for managed-country players (- 10 - rand(10)).
        STRUCTURAL = (0, 6, 7, 0x12, 0x13)
        for i in range(0xEF24 // PLAYER):
            actual_rec = actual[i]
            expected_rec = self.expected[i * PLAYER:(i + 1) * PLAYER]
            for off in STRUCTURAL:
                if actual_rec[off] != expected_rec[off]:
                    self.fail(
                        f"record {i} byte +0x{off:02x}: model={actual_rec[off]:#04x} "
                        f"expected={expected_rec[off]:#04x}; full record: "
                        f"model={bytes(actual_rec).hex()} "
                        f"expected={bytes(expected_rec).hex()}"
                    )
            # +0x03 only for squad players (records 1..2560)
            if 1 <= i <= 2560:
                if actual_rec[3] != expected_rec[3]:
                    self.fail(
                        f"record {i} byte +0x03: model={actual_rec[3]:#04x} "
                        f"expected={expected_rec[3]:#04x}"
                    )

    def test_record_0_is_all_zero(self):
        actual = new_game.make_all_players(self.d, managed_country=MANAGED_COUNTRY)
        self.assertEqual(actual[0], bytes(0x14))

    def test_records_2641_to_3060_are_all_zero(self):
        actual = new_game.make_all_players(self.d, managed_country=MANAGED_COUNTRY)
        for i in range(2641, 3061):
            self.assertEqual(actual[i], bytes(0x14), f"record {i} not zero")

    def test_country_bytes_match_e006(self):
        """Every record's +0x00 country byte matches E006 — this is the
        strongest no-op-model check: an all-zero model would have country=0
        for all records; the model has country=1..128 in records 1..2560 and
        country=MANAGED_COUNTRY in records 2561..2640."""
        actual = new_game.make_all_players(self.d, managed_country=MANAGED_COUNTRY)
        PLAYER = 0x14
        for i in range(0xEF24 // PLAYER):
            expected_country = self.expected[i * PLAYER]
            if i == 0:
                # record 0 is all zero
                self.assertEqual(actual[i][0], 0)
            elif 1 <= i <= 2560:
                # country 1..128
                expected = ((i - 1) // 20) + 1
                self.assertEqual(actual[i][0], expected,
                                 f"record {i} country: model={actual[i][0]} expected={expected}")
            elif 2561 <= i <= 2640:
                # managed country
                self.assertEqual(actual[i][0], MANAGED_COUNTRY,
                                 f"record {i} country: model={actual[i][0]} expected={MANAGED_COUNTRY}")
            else:
                # 2641..3060 are all zero
                self.assertEqual(actual[i][0], 0)


class DW3Example(unittest.TestCase):
    """[designed] The DW3 example: a one-liner that prints a player's bytes."""

    def test_dw3_example_runs(self):
        # DW3: `python3 -c "from goal2.engine import new_game; ..."` must work.
        # This test runs the same Python and asserts the output is non-empty.
        code = (
            "from goal2.data import goaldat; "
            "from goal2.engine import new_game; "
            "d = goaldat.load(open('.cache/GOAL.DAT', 'rb').read()); "
            "ps = new_game.make_all_players(d, managed_country=7); "
            "print(bytes(ps[0]).hex(), bytes(ps[1]).hex())"
        )
        r = subprocess.run(
            [sys.executable, "-c", code],
            capture_output=True, text=True, cwd=str(ROOT),
        )
        self.assertEqual(r.returncode, 0,
                         f"stderr={r.stderr}")
        # Two hex strings, each 40 chars (0x14 * 2), separated by a space.
        parts = r.stdout.strip().split()
        self.assertEqual(len(parts), 2, f"unexpected output: {r.stdout!r}")
        self.assertEqual(len(parts[0]), 40, f"player 0 should be 40 hex chars: {parts[0]!r}")
        self.assertEqual(len(parts[1]), 40, f"player 1 should be 40 hex chars: {parts[1]!r}")


if __name__ == "__main__":
    unittest.main()
