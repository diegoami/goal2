"""[designed: T182, #585] Independent test group; bodies and shared helpers live in core_round_t108_cases."""
import unittest
from goal2.tests.core_round_t108_cases import *


def load_tests(loader, tests, pattern):
    return unittest.TestSuite([
        loader.loadTestsFromTestCase(Runner327),
    ])


if __name__ == "__main__":
    unittest.main()
