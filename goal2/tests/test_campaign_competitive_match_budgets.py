"""[designed: T182, #585] Independent test group; bodies and shared helpers live in campaign_competitive_match_cases."""
import unittest
from goal2.tests import test_campaign_competitive_match as _original  # [designed: T182] retain the original change-to-test reach
from goal2.tests.campaign_competitive_match_cases import *


def load_tests(loader, tests, pattern):
    return unittest.TestSuite([
        CompetitiveAdapterTests('test_owner_budget_cases_match_independent_execution_and_guest_stamps'),
    ])


if __name__ == "__main__":
    unittest.main()
