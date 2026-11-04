"""[designed: T182, #585] Competitive scenarios, each match setup played once."""
import unittest
from goal2.tests.watch_qualifiers_t176_cases import *
from goal2.tests import watch_qualifiers_t176_cases as _cases


class WatchQualifiers(_cases.WatchQualifiers):
    COMPETITIVE = True
    FRIENDLY = False


def load_tests(loader, tests, pattern):
    return unittest.TestSuite([
        WatchQualifiers('test_a_watched_qualifier_is_the_competitive_match_on_the_owner_s_bridge'),
        WatchQualifiers('test_played_with_default_answers_it_equals_drive_match_on_prepare_competitive'),
        WatchQualifiers('test_its_published_campaign_state_equals_drive_match_s_and_competitive_play_s'),
        WatchQualifiers('test_one_substitution_at_half_time_equals_the_same_answer_through_drive'),
        WatchQualifiers('test_the_bench_offers_the_competition_budget_and_refuses_one_more'),
        loader.loadTestsFromTestCase(Boundary),
    ])


if __name__ == "__main__":
    unittest.main()
