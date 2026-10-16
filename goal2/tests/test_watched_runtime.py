"""[designed: T62] Optional runtime, exact vendoring, verified resources and build boundaries."""
import copy
import hashlib
import importlib.util
from pathlib import Path
import subprocess
import sys
import shutil
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))
import watched_evidence
from watched_evidence import IMAGES, verify_vendor
from goal2.engine.original_match import Image, Match, Fixture
from goal2.engine.original_match.assets import reference_image, AssetError
from goal2.game.state import from_savestate, to_savestate


class RuntimeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.raw = reference_image(ROOT / ".cache")
        cls.image = Image.from_savestate(cls.raw)

    def test_all_ten_files_are_exact_accepted_source(self):
        self.assertEqual(verify_vendor(), 10)

    def test_changed_vendor_bytes_and_added_files_are_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / "tools").mkdir()
            shutil.copyfile(ROOT / "tools/watched-kit-hashes.json",root / "tools/watched-kit-hashes.json")
            shutil.copytree(ROOT / "goal2/engine/original_match",root / "goal2/engine/original_match",
                            ignore=shutil.ignore_patterns("__pycache__"))
            with patch.object(watched_evidence,"ROOT",root):
                self.assertEqual(verify_vendor(),10)
                readme = root / "goal2/engine/original_match/README.md"
                original = readme.read_bytes()
                readme.write_bytes(original+b"changed")
                with self.assertRaisesRegex(ValueError,"differs from accepted source"):
                    verify_vendor()
                readme.write_bytes(original)
                (readme.parent / "extra.py").write_text("pass")
                with self.assertRaisesRegex(ValueError,"file set differs"):
                    verify_vendor()

    def test_missing_asset_and_wrong_hash_are_actionable(self):
        with tempfile.TemporaryDirectory() as folder:
            with patch("goal2.engine.original_match.assets.subprocess.run", side_effect=FileNotFoundError("gh missing")):
                with self.assertRaisesRegex(AssetError, "cannot download.*gh release download"):
                    reference_image(folder)
            path = Path(folder) / next(iter(IMAGES))
            path.write_bytes(b"wrong image")
            with patch("goal2.engine.original_match.assets.subprocess.run", side_effect=AssertionError("no network on cache hit")):
                with self.assertRaisesRegex(AssetError, "SHA-256"):
                    reference_image(folder)
        self.assertEqual(hashlib.sha256(self.raw).hexdigest(), next(iter(IMAGES.values())))

    def test_optional_dependency_failure_and_actual_quick_play(self):
        # [designed] A fresh interpreter with Unicorn imports refused, and no watched image in cwd.
        child = r'''
import importlib.abc,sys
from pathlib import Path
class NoUnicorn(importlib.abc.MetaPathFinder):
 def find_spec(self,fullname,path=None,target=None):
  if fullname == "unicorn" or fullname.startswith("unicorn."):raise ImportError("deliberately absent")
sys.meta_path.insert(0,NoUnicorn())
root=Path(sys.argv[1]);sys.path.insert(0,str(root))
from goal2.engine.original_match import Image,Match,Fixture
from goal2.engine.original_match.machine import Machine
try:Machine(bytearray(0x110000),0)
except ModuleNotFoundError as exc:assert "pip install unicorn" in str(exc),exc
else:raise AssertionError("missing Unicorn accepted")
from goal2.engine.savestate import Savestate
from goal2.game.state import from_savestate
from goal2.game.quick_match import run_full_match
raw=(root/".cache/e010-r0008-halftime.sav").read_bytes()
state=from_savestate(raw)
result=run_full_match(Savestate(raw),state)
assert len(result["score"])==2,result
assert not any(name=="unicorn" or name.startswith("unicorn.") for name in sys.modules)
print("quick-only PASS")
'''
        with tempfile.TemporaryDirectory() as folder:
            result = subprocess.run([sys.executable,"-B","-c",child,str(ROOT)],cwd=folder,capture_output=True,text=True)
        self.assertEqual(result.returncode,0,result.stdout+result.stderr)
        self.assertIn("quick-only PASS",result.stdout)

    def test_build_refuses_meaningful_code_and_data_changes(self):
        mutations = ((self.image.load+0x214B)*16+0x0696, self.image.DS*16+0x07CB)
        for address in mutations:
            image = Image(self.image.memory_component())
            image.memory[address] ^= 2
            with self.assertRaisesRegex(ValueError,"registered version.*differs"):
                Match(image,Fixture(7,19,index=21),managed=7)

    def test_supported_adapted_records_pass_guard_without_mutating_original(self):
        state = from_savestate(self.raw)
        before = copy.deepcopy(state)
        player = bytearray(state.players[121]); player[0x0C] = (player[0x0C]+1) % 16
        state.players[121] = bytes(player)
        country = bytearray(state.countries[7]); country[0x2D] ^= 4
        state.countries[7] = bytes(country)
        state.rng_seed_7b62 = 1234
        # [derived: merged README] Keep immutable foot-table bytes; clock was read from the same template.
        image = Image.from_savestate(to_savestate(state,original=self.raw))
        self.assertEqual(image.build_problems(),[])
        Match(image,Fixture(7,19,index=21),managed=7)
        self.assertNotEqual(state,before)
        self.assertEqual(Image.from_savestate(self.raw).build_problems(),[])

    def test_unsupported_fixtures_refuse_without_changing_image(self):
        before = self.image.memory_component()
        for kind in (0,2,4,16):
            with self.assertRaisesRegex(ValueError,"only friendlies"):
                Match(self.image,Fixture(7,19,index=21,kind=kind),managed=7)
        self.assertEqual(self.image.memory_component(),before)


if __name__ == "__main__":
    unittest.main()
