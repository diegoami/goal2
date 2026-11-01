"""[designed: owner, 2026-11-01, #500] No test plays the sealed port engine in the CPython test process: the guard
refuses it here, and goal2/tests/pypy_engine.py plays it in a child under engine_python() (PyPy 3.11), returning its
value and raising its exception as the same type."""
import os
import pickle
import subprocess
import unittest

from goal2.game.engine_python import engine_python
from goal2.tests import pypy_engine, requires


class Unpicklable(Exception):
    """An exception pickle cannot rebuild (its constructor needs two arguments, it pickles one)."""
    def __init__(self, a, b):
        super().__init__(f"{a} {b}")


def raise_unpicklable():
    raise Unpicklable("not", "rebuilt")


class Guard(unittest.TestCase):
    def test_this_test_process_is_guarded(self):
        self.assertTrue(pypy_engine.guarded())
        self.assertNotEqual(os.environ.get(pypy_engine.CHILD), "1")
        from goal2.engine.original_match.port.engine import PortMachine
        with self.assertRaises(pypy_engine.EngineInTestProcess):
            PortMachine(b"", 0)

    def test_the_route_is_refused_here_before_it_plays(self):
        requires.require(**requires.WATCHED)
        from goal2.engine.original_match import Fixture
        from goal2.engine.original_match.assets import reference_image
        from goal2.game.state import from_savestate
        from goal2.game.watched_match import run_watched_match
        from goal2.tests.test_watched_adapter import ROOT
        raw = reference_image(ROOT / ".cache");state = from_savestate(raw);state.captain = 0
        with self.assertRaises(pypy_engine.EngineInTestProcess):
            run_watched_match(state, raw, Fixture(7, 19, 21), reference_seed=257, delay_byte=0)

    def test_installing_twice_keeps_one_guard(self):
        from goal2.engine.original_match.port.engine import PortMachine
        before = PortMachine.__init__
        pypy_engine.guard()
        self.assertIs(PortMachine.__init__, before)


class Child(unittest.TestCase):
    def test_the_child_runs_under_engine_python_unguarded(self):
        pending = pypy_engine.start("goal2.tests.pypy_engine:probe")
        self.assertEqual(pending.interpreter, engine_python())
        implementation, guarded, flag = pending.result()
        expected = subprocess.run([engine_python(), "-c", "import platform;print(platform.python_implementation())"],
                                  capture_output=True, text=True, check=True).stdout.strip()
        self.assertEqual(implementation, expected)
        self.assertFalse(guarded);self.assertEqual(flag, "1")

    def test_a_value_and_the_arguments_come_back(self):
        self.assertEqual(pypy_engine.call("goal2.tests.pypy_engine:echo", "builtins:sorted", [3, 1, 2]),
                         ([1, 2, 3], ([3, 1, 2],), {}))
        pending = pypy_engine.start("builtins:divmod", 17, 5)
        self.assertEqual(pending.result(), (3, 2))

    def test_an_exception_is_raised_again_as_its_type(self):
        with self.assertRaises(ValueError) as caught:
            pypy_engine.call("builtins:int", "x")
        self.assertIn("invalid literal", str(caught.exception))
        self.assertIsInstance(caught.exception.__cause__, pypy_engine.ChildTraceback)
        self.assertIn("Traceback", str(caught.exception.__cause__))

    def test_an_unpicklable_exception_and_a_dead_child_are_child_errors(self):
        with self.assertRaises(TypeError):
            pickle.loads(pickle.dumps(Unpicklable("a", "b")))
        with self.assertRaisesRegex(pypy_engine.ChildError, "Unpicklable: not rebuilt"):
            pypy_engine.call("goal2.tests.test_pypy_engine_500:raise_unpicklable")
        with self.assertRaisesRegex(pypy_engine.ChildError, "exited with 3 and no reply"):
            pypy_engine.call("os:_exit", 3)


if __name__ == "__main__":
    unittest.main()
