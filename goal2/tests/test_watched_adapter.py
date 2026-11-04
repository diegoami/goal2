"""[designed: T182, #585] Independent test group; bodies and shared helpers live in watched_adapter_cases."""
import unittest
from goal2.tests.watched_adapter_cases import *


def load_tests(loader, tests, pattern):
    return unittest.TestSuite([
        WatchedAdapter('test_year_mapping_pinned_to_f025_both_start_calendars_and_wrap'),
        WatchedAdapter('test_invalid_inputs_do_not_mutate_active_state'),
        WatchedAdapter('test_each_default_decision_is_explicitly_answered'),
        WatchedAdapter('test_distinct_same_minute_notices_are_not_a_no_progress_loop'),
        WatchedAdapter('test_default_decision_policy_and_refusal_fail_closed'),
    ])


if __name__ == "__main__":
    unittest.main()
