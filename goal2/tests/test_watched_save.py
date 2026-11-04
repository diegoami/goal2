"""[designed: T182, #585] Independent test group; bodies and shared helpers live in watched_save_cases."""
import unittest
from goal2.tests.watched_save_cases import *


def load_tests(loader, tests, pattern):
    return unittest.TestSuite([
        WatchedSaveTests('test_legacy_friendly_and_campaign_history_retain_v1_v2_meaning'),
    ])


if __name__ == "__main__":
    unittest.main()
