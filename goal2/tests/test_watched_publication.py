"""[designed: T182, #585] Independent test group; bodies and shared helpers live in watched_publication_cases."""
import unittest
from goal2.tests.watched_publication_cases import *


def load_tests(loader, tests, pattern):
    return unittest.TestSuite([
        WatchedPublicationTests('test_cancel_and_wrong_tokens_preserve_active_state'),
    ])


if __name__ == "__main__":
    unittest.main()
