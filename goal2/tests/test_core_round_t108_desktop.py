"""[designed: T182, #585] Independent test group; bodies and shared helpers live in core_round_t108_cases."""
import unittest
from goal2.tests import test_core_round_t108 as _original  # [designed: T182] retain the original change-to-test reach
from goal2.tests.core_round_t108_cases import *


def load_tests(loader, tests, pattern):
    return unittest.TestSuite([
        loader.loadTestsFromTestCase(Desktop),
    ])


if __name__ == "__main__":
    unittest.main()
