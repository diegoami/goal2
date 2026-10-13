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
    """[confirmed: F007, ds_2581_01.hex; T19 report §3.1] The constants the model
    reads, indexed by `gk` (1 = goalkeeper, position 0; 0 = outfield)."""

    def test_DS_118A(self):
        # [confirmed: T19 report §3.1; ds_2581_01.hex row 1180: 118A=0x1C,
        # 118B=0x1F] The age base: outfield (gk=0) reads DS:118A = 0x1C,
        # goalkeeper (gk=1) reads DS:118B = 0x1F.
        self.assertEqual(new_game.DS_118A, (0x1C, 0x1F))

    def test_DS_0E80(self):
        # [confirmed: T19 report §3.1; ds_2581_01.hex row 0E80: 0E80=0x1B,
        # 0E81=0x1E] The peak base: outfield (gk=0) reads DS:0E80 = 0x1B,
        # goalkeeper (gk=1) reads DS:0E81 = 0x1E.
        self.assertEqual(new_game.DS_0E80, (0x1B, 0x1E))

    def test_DS_118C(self):
        self.assertEqual(new_game.DS_118C, (0x11, 0x14))

    def test_DS_0E82(self):
        self.assertEqual(new_game.DS_0E82, (0x10, 0x0D))


class CountryRank(unittest.TestCase):
    """[confirmed: F007] +0x2B from block 8, +0x2C/+0x2A from block 9."""

    def setUp(self):
        self.d = goaldat.load(_dat_or_skip())

    def test_country_1_country_record_values(self):
        # F007: country 1's record reads +0x2A..+0x2F = `1c 50 1c 50 01 f7 01 04`
        # → +0x2A=28, +0x2B=80, +0x2C=1. (Country 7 is Denmark; country 1 is
        # the first country in the data tables.)
        world, continent, within = new_game.country_rank(self.d, 1)
        self.assertEqual((world, continent, within), (80, 1, 28))

    def test_country_2_rank_is_in_range(self):
        # The function reads the permutation positions for any country;
        # this only asserts they are positive ints within their domains.
        world, continent, within = new_game.country_rank(self.d, 2)
        self.assertGreater(world, 0)
        self.assertGreaterEqual(continent, 1)
        self.assertLessEqual(continent, 4)
        self.assertGreaterEqual(within, 1)
        self.assertLessEqual(within, 32)

    def test_rating_for_country_1(self):
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
    """[confirmed: F007, E006; T19 report §2] The fidelity test: the model's
    player array vs E006-r0001's published array. Since T20 the comparison is
    byte-exact over all 3061 records x 20 bytes; the structural no-op-model
    checks below still stand on their own."""

    @classmethod
    def setUpClass(cls):
        cls.d = goaldat.load(_dat_or_skip())
        cls.state = _state_or_skip()
        cls.expected = _e006_player_array(cls.state)

    def test_player_array_length(self):
        self.assertEqual(len(self.expected), 0xEF24)

    def test_structural_fields_match_e006(self):
        """[confirmed: E006-r0001; T19 report §2's replication] Byte-exact
        fidelity: `make_all_players` equals the E006-r0001 expected array on
        ALL 3061 records x 20 bytes (0 differing; `matching_players == 3061`
        is the pass condition, issue #11 step 3). Before T20's fix the same
        comparison had 11,002 differing bytes of 61,220 (T19 report §1) —
        that is the case this test fails without the fix (rule 20/21)."""
        actual = new_game.make_all_players(self.d, managed_country=MANAGED_COUNTRY)
        PLAYER = 0x14
        matching_players = 0
        for i in range(0xEF24 // PLAYER):
            actual_rec = bytes(actual[i])
            expected_rec = self.expected[i * PLAYER:(i + 1) * PLAYER]
            if actual_rec == expected_rec:
                matching_players += 1
                continue
            for off in range(PLAYER):
                if actual_rec[off] != expected_rec[off]:
                    self.fail(
                        f"record {i} byte +0x{off:02x}: model={actual_rec[off]:#04x} "
                        f"expected={expected_rec[off]:#04x}; full record: "
                        f"model={actual_rec.hex()} expected={expected_rec.hex()}"
                    )
        self.assertEqual(
            matching_players, 3061,
            f"only {matching_players} of 3061 records match E006 byte-for-byte",
        )

    def test_issue11_fields_zero_differing_bytes(self):
        """[derived: T19 report §4.5] The four issue-#11 LCG fields
        (+0x01 age, +0x02 peak, +0x05, +0x0C) and the fields that depend on
        them (+0x03 managed potential, +0x04, +0x0D/+0x0E, +0x0F) show 0
        differing bytes in this test's own accounting over all 3061 records.
        On the pre-T20 model these were the 11,002 differing bytes (T19
        report §1); this names them field by field."""
        FIELDS = (0x01, 0x02, 0x03, 0x04, 0x05, 0x0C, 0x0D, 0x0E, 0x0F)
        actual = new_game.make_all_players(self.d, managed_country=MANAGED_COUNTRY)
        PLAYER = 0x14
        differing = {f: [] for f in FIELDS}
        for i in range(0xEF24 // PLAYER):
            actual_rec = actual[i]
            expected_rec = self.expected[i * PLAYER:(i + 1) * PLAYER]
            for f in FIELDS:
                if actual_rec[f] != expected_rec[f]:
                    differing[f].append(
                        f"record {i}: model={actual_rec[f]:#04x} "
                        f"expected={expected_rec[f]:#04x}"
                    )
        for f in FIELDS:
            self.assertEqual(
                len(differing[f]), 0,
                f"+0x{f:02x}: {len(differing[f])} differing bytes; "
                f"first: {differing[f][0] if differing[f] else '-'}",
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

    def test_lcg_produces_varied_values(self):
        """The LCG drives +0x01, +0x02, +0x05, +0x0C, +0x0D/+0x0E. A
        degenerate LCG (always returns 0 or 1) would produce a model with
        zero variance in these fields. This test catches that: across the
        2560 squad players, the +0x0C values (one LCG draw per player)
        must include at least 30 distinct values out of 32 possible. An
        all-1 or all-0 LCG would fail; a working LCG passes."""
        actual = new_game.make_all_players(self.d, managed_country=MANAGED_COUNTRY)
        c_values = set()
        for i in range(1, 2561):
            c_values.add(actual[i][0x0C])
        self.assertGreaterEqual(
            len(c_values), 30,
            f"only {len(c_values)} distinct +0x0C values; LCG appears degenerate"
        )


class LCGDrawOrderRegression(unittest.TestCase):
    """[confirmed: E006-r0001; T19 report §3.2] Regression guard: pin the
    LCG-driven fields of country 1's first 10 players to the reconciled
    draw order's output, and assert the pins against BOTH the model's output
    and the E006 expected bytes (T20 Done-when 5). Catches a draw-order swap
    (e.g. moving the +0x05 `rand(16)` back after the age's `rand(7)` pair
    changes player 1's +0x05 and fails this test on both assertions).
    """

    @classmethod
    def setUpClass(cls):
        cls.d = goaldat.load(_dat_or_skip())
        cls.players = new_game.make_all_players(cls.d, managed_country=MANAGED_COUNTRY)
        cls.expected = _e006_player_array(_state_or_skip())

    # Pinned: (record_index, +0x01 age, +0x02 peak, +0x05, +0x0C, +0x0D, +0x0E)
    PINNED = (
        (1,  0x1a, 0x1b, 0x0e, 0x08, 0x20, 0x20),
        (2,  0x22, 0x1f, 0x03, 0x05, 0x12, 0x12),
        (3,  0x23, 0x1d, 0x0f, 0x1e, 0x11, 0x11),
        (4,  0x1d, 0x1d, 0x02, 0x18, 0x17, 0x17),
        (5,  0x21, 0x20, 0x01, 0x13, 0x20, 0x20),
        (6,  0x1c, 0x1d, 0x0e, 0x04, 0x20, 0x20),
        (7,  0x1b, 0x1e, 0x0b, 0x11, 0x20, 0x20),
        (8,  0x21, 0x1e, 0x03, 0x1e, 0x14, 0x14),
        (9,  0x1f, 0x20, 0x0c, 0x10, 0x20, 0x20),
        (10, 0x24, 0x1d, 0x05, 0x1a, 0x16, 0x16),
    )

    def test_lcg_driven_fields_match_pinned_values(self):
        PLAYER = 0x14
        FIELDS = ((0x01, "+0x01 age"), (0x02, "+0x02 peak"), (0x05, "+0x05"),
                  (0x0C, "+0x0C"), (0x0D, "+0x0D"), (0x0E, "+0x0E"))
        for row in self.PINNED:
            idx, pinned = row[0], row[1:]
            rec = self.players[idx]
            exp = self.expected[idx * PLAYER:(idx + 1) * PLAYER]
            for (off, name), want in zip(FIELDS, pinned):
                self.assertEqual(
                    rec[off], want,
                    f"player {idx} {name}: model=0x{rec[off]:02x} pinned=0x{want:02x}",
                )
                # The pins are the E006 bytes, not just the model's: a pin
                # that matches the model but not the expected array fails.
                self.assertEqual(
                    exp[off], want,
                    f"player {idx} {name}: e006=0x{exp[off]:02x} pinned=0x{want:02x}",
                )


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
