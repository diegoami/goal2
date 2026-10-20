"""[designed: T51a] Run accepted E034 regressions against the consumer package itself."""
import ast
import importlib.util
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))
from watched_evidence import IMAGES, SOURCE, stage, verify_vendor
from run_watched_scenario import selected_source
import goal2.engine.original_match as consumer
from goal2.engine.original_match.assets import reference_image
from goal2.tests import requires

requires.require(modules=("unicorn",), files=tuple(IMAGES), archaeology=True)
FOLDER = stage()
spec = importlib.util.spec_from_file_location("accepted_competitive_tests", FOLDER / "tests/test_original_match.py")
accepted = importlib.util.module_from_spec(spec)
spec.loader.exec_module(accepted)
import original_match as independent


def consumer_modules():
    # [designed] Exact upstream assertions execute against goal2's imported package.
    return {name.removeprefix("goal2.engine."): module for name, module in list(sys.modules.items())
            if name == "goal2.engine.original_match" or name.startswith("goal2.engine.original_match.")}


class CompetitiveTests(accepted.CompetitiveTests):
    @classmethod
    def setUpClass(cls):
        cls.image = consumer.Image.from_savestate(reference_image(ROOT / ".cache"))

    def run(self, result=None):
        with patch.dict(sys.modules, consumer_modules()):
            return super().run(result)


class ConsumerAcceptanceTests(unittest.TestCase):
    def test_exact_source_and_scenario_selector(self):
        self.assertEqual(SOURCE, "424d5998076da1e4efc399c2715689ddb44d3e1a")
        self.assertEqual(verify_vendor(), 10)
        for index in range(3):
            tree = selected_source("def main():\n scenarios = [1,2,3]\n assert True\n", index)
            assignment = next(n for n in ast.walk(tree) if isinstance(n, ast.Assign))
            self.assertEqual([n.value for n in assignment.value.elts], [index+1])
            self.assertEqual(sum(isinstance(n, ast.Assert) for n in ast.walk(tree)), 1)
        for raw, index in (("scenarios=[1]", 1), ("scenarios=[]", 0), ("value=[1]", 0)):
            with self.assertRaises(ValueError):
                selected_source(raw, index)

    def test_all_builder_kinds_accept_and_impossible_kinds_refuse(self):
        image = consumer.Image.from_savestate(reference_image(ROOT / ".cache"))
        before = image.memory_component()
        for kind in (1,2,3,5,6,7,8,101,102,103,200,201,202,203):
            match = consumer.Match(image, consumer.Fixture(7,19,index=21,kind=kind), managed=7)
            self.assertEqual(match.opts["kind"], kind)
        for kind in (0,4,9,100,104,199,204,255):
            with self.assertRaises(ValueError):
                consumer.Match(image, consumer.Fixture(7,19,index=21,kind=kind), managed=7)
        self.assertEqual(image.memory_component(), before)

    def test_result_shape_matches_independent_guest_execution(self):
        # [confirmed: accepted E034 stamps index42] Sudden death, independent guest-write hooks.
        spec = importlib.util.spec_from_file_location("consumer_e034", FOLDER / "experiments/E034-kit-competitive/stamps_competitive.py")
        probe = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(probe)
        image = consumer.Image.from_savestate(reference_image(ROOT / ".cache"))
        want, got, result = probe.run(consumer,image,index=42,kind=200,policy=probe.play_on)
        self.assertEqual(got,want)
        self.assertTrue({"winner","kind","score_90","extra_time","substitution_budget","shootout","players"} <= result.keys())
        self.assertEqual((result["score_90"],result["score"],result["extra_time"]),([0,0],[0,0],True))
        self.assertEqual(result["shootout"]["score"],[3,2])
        self.assertEqual(result["winner"],0)
        self.assertEqual(len(result["shootout"]["kicks"]),12)
        self.assertEqual(result["board"]["final_score"],[3,2])
        self.assertEqual(result["substitution_budget"],[2,2])
        # [designed] A separately exported package executes again with the same declared inputs.
        expected_want, expected_got, expected = probe.run(independent,
            image,index=42,kind=200,policy=probe.play_on)
        self.assertEqual(expected_want,expected_got)
        self.assertEqual(result,expected)


if __name__ == "__main__":
    unittest.main()
