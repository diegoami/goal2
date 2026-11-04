"""[designed: T182, #585] Independent test group; bodies and shared helpers live in watched_publication_cases."""
import unittest
from goal2.tests import test_watched_publication as _original  # [designed: T182] retain the original change-to-test reach
from goal2.tests.watched_publication_cases import *


def load_tests(loader, tests, pattern):
    return unittest.TestSuite([
        WatchedPublicationTests('test_changed_job_and_malformed_completions_cannot_publish'),
    ])


if __name__ == "__main__":
    unittest.main()
