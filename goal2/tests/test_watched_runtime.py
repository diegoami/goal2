"""[designed: T62] Optional runtime, exact vendoring, verified resources and build boundaries."""
import copy
import hashlib
import json
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
from goal2.engine.original_match.assets import reference_image, AssetError, REFERENCE
from goal2.game.state import from_savestate, to_savestate
from goal2.tests import requires


class RuntimeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        requires.require(**requires.WATCHED)
        cls.raw = reference_image(ROOT / ".cache")
        cls.image = Image.from_savestate(cls.raw)

    @requires.need(archaeology=True)
    def test_all_files_are_exact_accepted_source(self):
        # [designed: T150] the re-vendored kit: ten top-level files, fileopts.py and the port's 30
        self.assertEqual(verify_vendor(), 41)

    @requires.need(archaeology=True)
    def test_changed_vendor_bytes_and_added_files_are_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / "tools").mkdir()
            shutil.copyfile(ROOT / "tools/watched-kit-hashes.json",root / "tools/watched-kit-hashes.json")
            shutil.copytree(ROOT / "goal2/engine/original_match",root / "goal2/engine/original_match",
                            ignore=shutil.ignore_patterns("__pycache__"))
            with patch.object(watched_evidence,"ROOT",root):
                self.assertEqual(verify_vendor(),41)
                for name in ('README.md','build.py'):
                    source = root / "goal2/engine/original_match" / name
                    original = source.read_bytes()
                    source.write_bytes(original+b"changed")
                    with self.assertRaisesRegex(ValueError,"differs from accepted source"):
                        verify_vendor()
                    source.write_bytes(original)
                manifest_path = root / 'tools/watched-kit-hashes.json'
                original = manifest_path.read_bytes();manifest = json.loads(original)
                manifest['source_overrides'] = {'runtime/original_match/build.py': 'a1067ba0df7ba9c7644f36e648d897b76c7697f8'}
                manifest_path.write_text(json.dumps(manifest))
                with self.assertRaisesRegex(ValueError,'source overrides differ'):
                    verify_vendor()
                manifest_path.write_bytes(original)
                (source.parent / "extra.py").write_text("pass")
                with self.assertRaisesRegex(ValueError,"file set differs"):
                    verify_vendor()

    @requires.need(archaeology=True,files=tuple(IMAGES))
    def test_staged_guard_uses_its_declared_source_and_other_runtime_remains_pinned(self):
        with tempfile.TemporaryDirectory() as folder:
            for name in IMAGES:shutil.copyfile(ROOT/'.cache'/name,Path(folder)/name)
            staged=watched_evidence.stage(folder)
            for name in ('build.py','match.py'):
                relative='runtime/original_match/'+name
                self.assertEqual((staged/relative).read_bytes(),watched_evidence.source_bytes(relative))
            manifest=json.loads((ROOT/'tools/watched-kit-hashes.json').read_text())
            self.assertEqual(hashlib.sha256((staged/'runtime/original_match/build.py').read_bytes()).hexdigest(),
                             manifest['files']['goal2/engine/original_match/build.py'])

    def test_entry_probe_false_or_incomplete_evidence_is_rejected(self):
        from check_watched_upstream import validate_entry
        from watched_evidence import source_bytes
        rows = [json.loads(line) for line in source_bytes(
            "experiments/E033-original-match-kit/out/entry-probe-20261016.jsonl").decode().splitlines()]
        validate_entry(rows)
        for mode in ("comparison","duplicate","boundary","missing"):
            changed = copy.deepcopy(rows)
            if mode == "comparison":changed[2]["checks"]["score"] = False
            if mode == "duplicate":changed[4] = copy.deepcopy(changed[3])
            if mode == "boundary":changed[1]["captain_wait"]["seed"] += 1
            if mode == "missing":changed.pop(3)
            with self.assertRaisesRegex(ValueError,"entry evidence failed"):
                validate_entry(changed)

    def test_missing_asset_and_wrong_hash_are_actionable(self):
        with tempfile.TemporaryDirectory() as folder:
            with patch("goal2.engine.original_match.assets.subprocess.run", side_effect=FileNotFoundError("gh missing")):
                with self.assertRaisesRegex(AssetError, "cannot download.*gh release download"):
                    reference_image(folder)
            path = Path(folder) / REFERENCE["asset"]
            path.write_bytes(b"wrong image")
            with patch("goal2.engine.original_match.assets.subprocess.run", side_effect=AssertionError("no network on cache hit")):
                with self.assertRaisesRegex(AssetError, "SHA-256"):
                    reference_image(folder)
        self.assertEqual(hashlib.sha256(self.raw).hexdigest(), REFERENCE["sha256"])

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

    def test_disallowed_goal_save_preserves_complete_match_and_closes_coverage(self):
        # [derived: accepted check.goals seed70 policy and README public-event list at3656a2d]
        report = json.loads((ROOT / "docs/evidence/T62-watched-kit.json").read_text())
        kinds = set().union(*(set(row["kinds"]) for row in report["save_scenarios"]))
        control = report.get("disallowed_goal_save", {})
        if control:
            kinds.add(control["boundary"])
        expected = {"minute", "commentary", "goal", "goal_disallowed", "booking", "sending_off",
                    "injury", "substitution", "half_time", "full_time", "decision", "tactics",
                    "position", "player_tactics", "substitution_requested", "refused", "end", "tick"}
        self.assertEqual(kinds, expected, "recorded save coverage must include every claimed public kind")
        self.assertEqual(control["checks"], {"events_equal": True, "full_result_equal": True,
                                            "complete_memory_equal": True})
        from goal2.engine.original_match.check import take_back_answers
        def play(resume):
            match = Match(self.image, Fixture(7,19,index=21), managed=7, seed=70)
            events, paused, saved, seen = [], set(), False, False
            while True:
                for event in match.events():
                    events.append((event.kind,event.minute,event.score,event.data))
                    if event.kind == "minute" and event.minute in (20,60) and event.minute not in paused:
                        paused.add(event.minute)
                        match.pause()
                    if event.kind == "decision":
                        take_back_answers(match,event.data)
                    if event.kind == "goal_disallowed":
                        seen = True
                        if resume and not saved:
                            try:
                                blob = match.save()
                                loaded = Match.load(blob)
                            except Exception as exc:
                                self.fail(f"goal_disallowed must be a usable save boundary: {exc}")
                            self.assertIsNot(loaded,match)
                            match, saved = loaded, True
                            break
                else:
                    break
            self.assertTrue(seen, "the regression must actually visit a disallowed goal")
            if resume:
                self.assertTrue(saved)
            # [confirmed: Match.answer/save/load at accepted3656 and424 pins] Snapshot
            # JSON turns sorted answer-item tuples into lists. Compare the COMPLETE
            # serialized result, including all seven new fields, rather than native
            # container identity. The historical kit1 digest remains an additional
            # friendly semantics control; no field/value is omitted from the full JSON.
            result = match.result()
            self.assertEqual(result["kit"],"4")      # [designed: T150] the re-vendored kit's label
            legacy = {key:value for key,value in result.items() if key not in
                      {"kind","winner","score_90","extra_time","substitution_budget","shootout","players"}}
            legacy["kit"] = "1"
            return {"event_sha256": hashlib.sha256(json.dumps(events,sort_keys=True).encode()).hexdigest(),
                    "result_sha256": hashlib.sha256(json.dumps(legacy,sort_keys=True).encode()).hexdigest(),
                    "memory_sha256": hashlib.sha256(match.memory_component()).hexdigest(),
                    "current_result_json": json.dumps(result,sort_keys=True)}
        straight, resumed = play(False), play(True)
        self.assertEqual(straight,resumed)
        self.assertEqual({key:value for key,value in straight.items() if key != "current_result_json"},
                         {key:control[key] for key in straight if key != "current_result_json"})

    def test_unsupported_fixtures_refuse_without_changing_image(self):
        before = self.image.memory_component()
        for kind in (0,4,9,16,204):
            with self.assertRaisesRegex(ValueError,"kind"):
                Match(self.image,Fixture(7,19,index=21,kind=kind),managed=7)
        self.assertEqual(self.image.memory_component(),before)


if __name__ == "__main__":
    unittest.main()
