"""[designed: T182, #585] Independent test group; bodies and shared helpers live in campaign_competitive_match_cases."""
import unittest
from goal2.tests.campaign_competitive_match_cases import *


def load_tests(loader, tests, pattern):
    return unittest.TestSuite([
        CompetitiveAdapterTests('test_competitive_preparation_preserves_public_friendly_gate'),
        CompetitiveAdapterTests('test_source_context_is_explicit_and_invalid_changes_are_atomic'),
    ])


if __name__ == "__main__":
    unittest.main()
