"""[designed: T182, #585] Independent test group; bodies and shared helpers stay in test_campaign_competitive_match."""
import unittest
from goal2.tests import test_campaign_competitive_match as _original  # [designed: T182] retain the original change-to-test reach
from goal2.tests.test_campaign_competitive_match import *


def load_tests(loader, tests, pattern):
    return unittest.TestSuite([
        CompetitiveAdapterTests('test_owner_budget_cases_match_independent_execution_and_guest_stamps'),
    ])


if __name__ == "__main__":
    unittest.main()
