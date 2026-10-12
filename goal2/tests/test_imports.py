"""Smoke test: the vendored engine imports and exposes what T01's CLI uses."""
import unittest


class EngineImports(unittest.TestCase):
    def test_cli_imports(self):
        from goal2 import cli  # noqa: F401
        self.assertTrue(hasattr(cli, "main"))
        self.assertTrue(hasattr(cli, "quick_engine"))
        self.assertTrue(hasattr(cli, "savestate"))

    def test_quick_engine_exposes_simulate_and_exceptions(self):
        from goal2 import cli
        self.assertTrue(callable(cli.quick_engine.simulate))
        self.assertTrue(issubclass(cli.quick_engine.FoulPathNotModelled, Exception))
        self.assertTrue(issubclass(cli.quick_engine.ExtraTimeNotModelled, Exception))

    def test_savestate_class_loadable(self):
        from goal2 import cli
        self.assertTrue(callable(cli.savestate.Savestate))
