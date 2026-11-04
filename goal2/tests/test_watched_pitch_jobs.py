"""[designed: T182, #585] Independent test group; bodies and shared helpers live in watched_pitch_jobs_cases."""
import unittest
from goal2.tests.watched_pitch_jobs_cases import *


def load_tests(loader, tests, pattern):
    return unittest.TestSuite([
        loader.loadTestsFromTestCase(PitchTransportTests),
        loader.loadTestsFromTestCase(PitchSetupCleanupTests),
        loader.loadTestsFromTestCase(PitchObservationTests),
    ])


if __name__ == "__main__":
    unittest.main()
