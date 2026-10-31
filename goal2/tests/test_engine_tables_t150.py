"""[designed: T150] The sealed engine's vendored tables.

The committed tables load and seal the reference image; a copy with one byte changed is refused; a built
wheel carries them; the vendored engine and tables are byte-equal to goal2-archaeology at the commit
PROVENANCE.md pins."""
import shutil
import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

from goal2.tests import requires

ROOT = Path(__file__).resolve().parents[2]
VENDORED = {"goal2/engine/original_match/": "runtime/original_match/",
            "goal2/engine/tables/": "static/goal-exe/tables/"}
TABLE_FILES = ("code_data.hex", "ds.hex", "manifest.json")


class Tables(unittest.TestCase):
    def setUp(self):
        from goal2.game import engine_tables
        self.et = engine_tables
        self.tmp = Path(tempfile.mkdtemp());self.addCleanup(shutil.rmtree, self.tmp)

    def test_the_vendored_tables_seal_the_reference_image(self):
        requires.require(files=(requires.REFERENCE["asset"],))
        from goal2.engine.original_match import Image
        t = self.et.load()
        image = Image.from_savestate((requires.CACHE / requires.REFERENCE["asset"]).read_bytes())
        sealed = Image.from_state(image.state(t), t)
        self.assertEqual(sealed.build_problems(), [])
        self.assertEqual(sealed.players(), image.players())

    def test_a_changed_byte_is_refused(self):
        for name in ("ds.hex", "code_data.hex"):
            with self.subTest(table=name):
                folder = self.tmp / name;shutil.copytree(self.et.FOLDER, folder, ignore=shutil.ignore_patterns("__pycache__"))
                lines = (folder / name).read_text().splitlines()
                row = next(i for i, l in enumerate(lines) if l and not l.startswith(";") and len(l.split("|")[0].split()) > 1)
                head, _, tail = lines[row].partition("|")
                cells = head.split();cells[1] = f"{int(cells[1], 16) ^ 1:02X}"
                lines[row] = f"{cells[0]}  {' '.join(cells[1:]):<95}  |{tail}"
                (folder / name).write_text("\n".join(lines) + "\n")
                with self.assertRaises(self.et.TablesError):
                    self.et.load(folder)

    def test_a_built_wheel_carries_the_tables(self):
        # a clean copy of the sources: a stale build/ in the checkout would hide missing package data
        src, out = self.tmp / "src", self.tmp / "dist"
        shutil.copytree(ROOT / "goal2", src / "goal2", ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
        shutil.copy(ROOT / "pyproject.toml", src)
        r = subprocess.run([sys.executable, "-m", "pip", "wheel", "--no-deps", "--no-build-isolation", "-q",
                            "-w", str(out), str(src)], capture_output=True, text=True)
        if r.returncode != 0 and "No module named pip" in r.stderr:
            self.skipTest("pip absent")
        self.assertEqual(r.returncode, 0, r.stderr[-2000:])
        names = zipfile.ZipFile(next(out.glob("goal2-*.whl"))).namelist()
        for name in TABLE_FILES:
            self.assertIn(f"goal2/engine/tables/{name}", names)


class Vendored(unittest.TestCase):
    """Rule 13: the vendored engine and tables are byte-copies of goal2-archaeology at the pinned commit."""

    def test_vendored_files_equal_upstream_at_their_pin(self):
        requires.require(archaeology=True)
        sys.path.insert(0, str(ROOT / "tools"))
        try:
            from check_provenance import _parse_table
        finally:
            sys.path.remove(str(ROOT / "tools"))
        rows = {r["file"]: r["commit"] for r in _parse_table((ROOT / "PROVENANCE.md").read_text())}
        upstream = requires.archaeology_path()
        checked = 0
        for path, commit in rows.items():
            source = next((src + path[len(dst):] for dst, src in VENDORED.items() if path.startswith(dst)), None)
            if source is None:
                continue
            with self.subTest(file=path):
                want = subprocess.run(["git", "show", f"{commit}:{source}"], cwd=upstream, capture_output=True, check=True).stdout
                self.assertEqual((ROOT / path).read_bytes(), want)
                checked += 1
        self.assertGreaterEqual(checked, 40 + len(TABLE_FILES))


if __name__ == "__main__":
    unittest.main()
