"""[designed: T182, #585] Friendly scenarios, each match setup played once."""
import unittest
from goal2.tests import test_watch_qualifiers_t176 as _original  # [designed: T182] retain the original change-to-test reach
from goal2.tests.test_watch_qualifiers_t176 import *


class WatchQualifiers(_original.WatchQualifiers):
    COMPETITIVE = False
    FRIENDLY = True


def load_tests(loader, tests, pattern):
    return unittest.TestSuite([
        WatchQualifiers('test_a_watched_friendly_still_plays_and_publishes_as_before'),
    ])


if __name__ == "__main__":
    unittest.main()
