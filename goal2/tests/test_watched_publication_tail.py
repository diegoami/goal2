"""[designed: T182, #585] Independent test group; bodies and shared helpers stay in test_watched_publication."""
import unittest
from goal2.tests import test_watched_publication as _original  # [designed: T182] retain the original change-to-test reach
from goal2.tests.test_watched_publication import *


def load_tests(loader, tests, pattern):
    return unittest.TestSuite([
        WatchedPublicationTests('test_full_time_is_not_completion_and_tail_failure_is_atomic'),
    ])


if __name__ == "__main__":
    unittest.main()
