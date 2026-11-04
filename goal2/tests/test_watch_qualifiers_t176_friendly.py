"""[designed: T182, #585] Friendly scenarios, each match setup played once."""
import unittest
from goal2.tests import test_watch_qualifiers_t176 as _original  # [designed: T182] retain the original change-to-test reach
from goal2.tests.watch_qualifiers_t176_cases import *
from goal2.tests import watch_qualifiers_t176_cases as _cases


class WatchQualifiers(_cases.WatchQualifiers):
    COMPETITIVE = False
    FRIENDLY = True


def load_tests(loader, tests, pattern):
    return unittest.TestSuite([
        WatchQualifiers('test_a_watched_friendly_still_plays_and_publishes_as_before'),
    ])


if __name__ == "__main__":
    unittest.main()
