"""[designed: T182, #585] Independent test group; bodies and shared helpers stay in test_watched_adapter."""
import unittest
from goal2.tests import test_watched_adapter as _original  # [designed: T182] retain the original change-to-test reach
from goal2.tests.test_watched_adapter import *


def load_tests(loader, tests, pattern):
    return unittest.TestSuite([
        WatchedAdapter('test_ten_strict_t62_inputs'),
    ])


if __name__ == "__main__":
    unittest.main()
