"""Focused protocol controls for the retained review decision."""
from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import Mock

from goal2.game.native_driver import NativeMatchDriver
from goal2.game.season_worker import SeasonRequestError, SeasonWorker, validate_request
from goal2.tests.test_native_driver_t170ac import Owner, event


class ReviewProtocol(TestCase):
    def test_configure_rejects_non_boolean_review(self):
        for value in (None, 0, 1, 'true'):
            with self.subTest(value=value), self.assertRaises(SeasonRequestError):
                validate_request(dict(op='season', request=1, action='configure', post_match_review=value))

    def test_exit_is_the_only_valid_review_answer_and_belongs_to_that_phase(self):
        worker = SeasonWorker()
        match = Mock()
        worker.session = SimpleNamespace(pending_match=match)
        worker.decision = 8
        match.waiting = {'context': 'post_match'}
        for answer in ({}, {'post_match_exit': False}, {'post_match_exit': 1},
                       {'post_match_exit': True, 'quick': False}):
            with self.subTest(answer=answer), self.assertRaises(SeasonRequestError):
                worker.dispatch(dict(op='season', request=9, action='answer', decision=8, answer=answer))
        match.waiting = {'context': 'half_time'}
        packet = dict(op='season', request=10, action='answer', decision=8, answer={'post_match_exit': True})
        with self.assertRaises(SeasonRequestError):
            worker.dispatch(packet)
        match.answer.assert_not_called()
        self.assertEqual(worker.decision, 8)
        match.waiting = {'context': 'post_match'}
        worker.dispatch(packet)
        match.answer.assert_called_once_with(post_match_exit=True)
        self.assertIsNone(worker.decision)

    def test_review_rejects_a_board_different_from_the_canonical_event(self):
        owner = Owner()
        driver = NativeMatchDriver(owner)
        initial = driver.event_base + len(driver.events)
        driver.tick(0)
        owner.batch(events=[event('full_time', {'seed': 5})], total=initial + 1)
        driver.tick(0)
        self.assertFalse(owner.closed)
        owner.batch(events=[event('decision', {'context': 'post_match', 'board': {'seed': 6}})],
                    decision=8, total=initial + 2)
        driver.tick(0)
        self.assertEqual(driver.status, 'lost')
        self.assertTrue(owner.closed)
