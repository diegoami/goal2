"""Tests for `goal2.data.goaldat` (T02 scope, the GOAL.DAT loader).

The data file `GOAL.DAT` is fetched on demand from `goal2-archaeology`'s
`goal2-original` release (sha256 pinned in the loader) into `.cache/`
(never committed, rule 19). The tests skip with the reason when the file
is absent and `gh` is not logged in.

[confirmed: the block offsets, sizes, record layouts, and check rules are
F002 R001–R011; the data file's SHA256 is F002's pinned value.]
"""
import hashlib
import io
import os
import subprocess
import sys
import unittest
import zipfile
import zlib
from pathlib import Path

from goal2.data import goaldat as gd
from goal2.data.goaldat import SHA256, SIZE


ROOT = Path(__file__).resolve().parents[2]
CACHE = ROOT / ".cache"
DAT = CACHE / "GOAL.DAT"
ARCHAEOLOGY = Path(os.environ.get("GOAL2_ARCHAEOLOGY", str(ROOT.parent / "goal2-archaeology")))
RELEASE = "goal2-original"
REPO = "diegoami/goal2-archaeology"


def _fetch_dat() -> None:
    """Download `GOAL.DAT` from the archaeology release into `.cache/`, sha256-pinned."""
    CACHE.mkdir(parents=True, exist_ok=True)
    # The release ships the file directly (44,040 bytes, not a zip).
    asset = "GOAL.DAT"
    subprocess.run(
        ["gh", "release", "download", RELEASE, "--repo", REPO,
         "--pattern", asset, "--dir", str(CACHE)],
        check=True,
    )
    src = CACHE / asset
    if not src.is_file():
        raise FileNotFoundError(f"{asset} not downloaded to {CACHE}")
    data = src.read_bytes()
    if hashlib.sha256(data).hexdigest() != SHA256:
        raise ValueError(f"{src}: sha256 differs from the pinned {SHA256}")


def _dat_path() -> Path:
    if not DAT.is_file():
        try:
            _fetch_dat()
        except (subprocess.CalledProcessError, FileNotFoundError, ValueError) as e:
            raise unittest.SkipTest(
                f"GOAL.DAT not in {DAT} and could not be downloaded ({e}); "
                f"or run `gh release download {RELEASE} --repo {REPO} "
                f"--pattern GOAL.DAT --dir {CACHE}`"
            ) from e
    return DAT


def _dat_bytes() -> bytes:
    return _dat_path().read_bytes()


class BlockShape(unittest.TestCase):
    """R001–R011: every F002 check passes against the released GOAL.DAT."""
    @classmethod
    def setUpClass(cls):
        cls.data = _dat_bytes()

    def test_R001_size_and_sha256(self):
        ok, text = gd._check_R001(self.data)
        self.assertTrue(ok, text)
        self.assertIn(SHA256, text)

    def test_R002_country_names(self):
        ok, text = gd._check_R002(self.data)
        self.assertTrue(ok, text)

    def test_R003_player_names(self):
        ok, text = gd._check_R003(self.data)
        self.assertTrue(ok, text)

    def test_R004_initials(self):
        ok, text = gd._check_R004(self.data)
        self.assertTrue(ok, text)

    def test_R005_manager_names(self):
        ok, text = gd._check_R005(self.data)
        self.assertTrue(ok, text)

    def test_R006_manager_initials(self):
        ok, text = gd._check_R006(self.data)
        self.assertTrue(ok, text)

    def test_R007_per_country_3(self):
        ok, text = gd._check_R007(self.data)
        self.assertTrue(ok, text)

    def test_R008_per_country_a(self):
        ok, text = gd._check_R008(self.data)
        self.assertTrue(ok, text)

    def test_R009_per_country_b(self):
        ok, text = gd._check_R009(self.data)
        self.assertTrue(ok, text)

    def test_R010_per_country_c(self):
        ok, text = gd._check_R010(self.data)
        self.assertTrue(ok, text)

    def test_R011_squad_20(self):
        ok, text = gd._check_R011(self.data)
        self.assertTrue(ok, text)

    def test_run_checks_all_pass(self):
        results = gd.run_checks(self.data)
        failed = [(cid, text) for cid, ok, text in results if not ok]
        self.assertEqual(failed, [], f"failed: {failed}")


class Loader(unittest.TestCase):
    """The library form: `goaldat.load(data)` returns the parsed blocks."""
    @classmethod
    def setUpClass(cls):
        cls.data = _dat_bytes()
        cls.gd = gd.load(cls.data)

    def test_country_names_index_0_is_empty(self):
        # R002: record 0 is all zero.
        self.assertEqual(self.gd.country_names[0], "")

    def test_country_names_index_1_is_nonempty(self):
        # R002: at least one country name is non-empty.
        nonempty = [n for n in self.gd.country_names if n]
        self.assertGreater(len(nonempty), 0)

    def test_player_names_count(self):
        # R003: 3061 records (0 is empty, 3060 are valid players).
        self.assertEqual(len(self.gd.player_names), 3061)

    def test_squad_20_layout(self):
        # R011: 129 records of 20 ints; record 0 is all zero; values lie in 0..13.
        self.assertEqual(len(self.gd.squad_20), 129)
        self.assertEqual(self.gd.squad_20[0], [0] * 20)
        for r in self.gd.squad_20[1:]:
            self.assertEqual(len(r), 20)
            for v in r:
                self.assertGreaterEqual(v, 0)
                self.assertLessEqual(v, 13)

    def test_per_country_b_is_a_permutation(self):
        # R009: per_country_b is a permutation of 0..128.
        self.assertEqual(sorted(self.gd.per_country_b), list(range(129)))

    def test_per_country_c_is_a_permutation(self):
        # R010: per_country_c is a permutation of 0..128.
        self.assertEqual(sorted(self.gd.per_country_c), list(range(129)))


class LoaderErrors(unittest.TestCase):
    """The loader's contract: a wrong file is rejected with a clear error."""

    def test_wrong_size_rejected(self):
        with self.assertRaises(ValueError) as cm:
            gd.load(b"\x00" * (SIZE - 1))
        self.assertIn(f"{SIZE - 1}", str(cm.exception))

    def test_wrong_sha256_rejected(self):
        # Right size, wrong content.
        with self.assertRaises(ValueError) as cm:
            gd.load(b"\x00" * SIZE)
        self.assertIn("sha256", str(cm.exception))


class Cli(unittest.TestCase):
    """`python -m goal2.data --check <path>` and `tools/check_goaldat.py <path>`."""

    def _run_module(self, path: Path) -> subprocess.CompletedProcess:
        return subprocess.run(
            [sys.executable, "-m", "goal2.data", "--check", str(path)],
            capture_output=True, text=True, cwd=str(ROOT),
        )

    def test_module_check_exits_0_on_dat(self):
        path = _dat_path()
        r = self._run_module(path)
        self.assertEqual(r.returncode, 0, f"stderr={r.stderr}\nstdout={r.stdout}")
        # The output is one line per check, R001..R011.
        cids = [line.split()[0] for line in r.stdout.splitlines() if line]
        self.assertEqual(cids, [f"R{n:03d}" for n in range(1, 12)])

    def test_module_check_exits_1_on_truncated_file(self):
        # A truncated file fails R001 (size mismatch). The CLI prints "R001 FAIL"
        # (the run_checks function reports it as a failed check, not as a raised
        # ValueError — the SHA256 mismatch is a different code path).
        truncated = _dat_bytes()[:SIZE - 1]
        truncated_path = self._write_temp(truncated)
        r = self._run_module(truncated_path)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("r001 fail", (r.stderr + r.stdout).lower())

    def _write_temp(self, data: bytes) -> Path:
        import tempfile
        fd, path = tempfile.mkstemp(suffix=".DAT")
        os.write(fd, data)
        os.close(fd)
        return Path(path)

    def test_truncated_r001_fails(self):
        # R001 directly: a wrong-size file fails the check.
        truncated = _dat_bytes()[:SIZE - 1]
        ok, text = gd._check_R001(truncated)
        self.assertFalse(ok)
        self.assertIn("bytes", text)


if __name__ == "__main__":
    unittest.main()
