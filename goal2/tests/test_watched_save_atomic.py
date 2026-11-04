"""[designed: T182, #585] Independent test group; bodies and shared helpers live in watched_save_cases."""
import unittest
from goal2.tests import test_watched_save as _original  # [designed: T182] retain the original change-to-test reach
from goal2.tests.watched_save_cases import *


def load_tests(loader, tests, pattern):
    return unittest.TestSuite([
        WatchedSaveTests('test_injected_failure_before_swap_preserves_complete_state'),
    ])


if __name__ == "__main__":
    unittest.main()
