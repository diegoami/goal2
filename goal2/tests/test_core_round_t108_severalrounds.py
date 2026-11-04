"""[designed: T182, #585] Independent test group; bodies and shared helpers stay in test_core_round_t108."""
import unittest
from goal2.tests import test_core_round_t108 as _original  # [designed: T182] retain the original change-to-test reach
from goal2.tests.test_core_round_t108 import *


def load_tests(loader, tests, pattern):
    return unittest.TestSuite([
        loader.loadTestsFromTestCase(SeveralRounds),
    ])


if __name__ == "__main__":
    unittest.main()
