"""[designed: T182, #585] Independent test group; bodies and shared helpers live in watched_pitch_jobs_cases."""
import unittest
from goal2.tests import test_watched_pitch_jobs as _original  # [designed: T182] retain the original change-to-test reach
from goal2.tests.watched_pitch_jobs_cases import *


def load_tests(loader, tests, pattern):
    return unittest.TestSuite([
        OriginalPitchJobsTests('test_actual_finished_cancel_and_close_preserve_prior_save'),
    ])


if __name__ == "__main__":
    unittest.main()
