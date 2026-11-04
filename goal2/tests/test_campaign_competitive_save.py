"""[designed: T182, #585] Independent test group; bodies and shared helpers live in campaign_competitive_save_cases."""
import unittest
from goal2.tests.campaign_competitive_save_cases import *


def load_tests(loader, tests, pattern):
    return unittest.TestSuite([
        CompetitiveSaveTests('test_no_world_compact_resolution_survives_later_friendly_and_rejects_damage'),
        CompetitiveSaveTests('test_quick_setup_is_private_and_preserves_strict_template_refusals'),
    ])


if __name__ == "__main__":
    unittest.main()
