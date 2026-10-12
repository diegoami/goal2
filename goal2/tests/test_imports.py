"""Smoke test: the vendored engine imports and exposes what T01's CLI uses.

[confirmed: the vendored `quick_engine.py` exposes `simulate(state)` and the two refusal
exceptions; the vendored `savestate.py` exposes `Savestate(path)`; goal2.cli re-exports
both. The test asserts only that these names resolve and are callable — it does not pin
their behaviour, which the fidelity test and the loader tests cover.]
"""
import unittest


class EngineImports(unittest.TestCase):
    def test_cli_imports(self):
        # [designed: the CLI module's re-exports are the contract `play.py` and tests use.]
        from goal2 import cli  # noqa: F401
        self.assertTrue(hasattr(cli, "main"))
        self.assertTrue(hasattr(cli, "quick_engine"))
        self.assertTrue(hasattr(cli, "savestate"))

    def test_quick_engine_exposes_simulate_and_exceptions(self):
        # [confirmed: `simulate`, `FoulPathNotModelled`, `ExtraTimeNotModelled` come from
        # quick_engine.py at 8760df9; the import-level smoke only checks the names resolve.]
        from goal2 import cli
        self.assertTrue(callable(cli.quick_engine.simulate))
        self.assertTrue(issubclass(cli.quick_engine.FoulPathNotModelled, Exception))
        self.assertTrue(issubclass(cli.quick_engine.ExtraTimeNotModelled, Exception))

    def test_savestate_class_loadable(self):
        # [confirmed: `Savestate` is the only public class the vendored reader exposes.]
        from goal2 import cli
        self.assertTrue(callable(cli.savestate.Savestate))
