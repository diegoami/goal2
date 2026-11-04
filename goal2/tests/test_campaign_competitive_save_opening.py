"""[designed: T182, #585] Independent test group; bodies and shared helpers live in campaign_competitive_save_cases."""
import unittest
from goal2.tests import test_campaign_competitive_save as _original  # [designed: T182] retain the original change-to-test reach
from goal2.tests.campaign_competitive_save_cases import *


def load_tests(loader, tests, pattern):
    return unittest.TestSuite([
        CompetitiveSaveTests('test_actual_country4_qualifier_after_two_original_friendlies_roundtrips_and_continues'),
    ])


if __name__ == "__main__":
    unittest.main()
