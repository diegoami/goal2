"""Synthetic transport controls; no original-game or port execution is claimed."""
import unittest
from measurements.T199.completion_probe import probe

class CompletionBoundary(unittest.TestCase):
    def test_valid_completion_waits_for_confirmation(self):
        self.assertEqual(probe('good')['public_completions'],1)

    def test_delayed_duplicate_is_rejected_before_any_completion(self):
        self.assertEqual(probe('duplicate')['public_completions'],0)

    def test_cancellation_discards_a_held_completion(self):
        self.assertEqual(probe('cancel')['cancelled'],1)

    def test_missing_confirmation_never_exposes_a_result(self):
        self.assertEqual(probe('missing')['public_completions'],0)

    def test_truncated_trailer_never_exposes_a_result(self):
        self.assertEqual(probe('trailing')['public_completions'],0)

    def test_nonzero_exit_retains_its_failure_before_publication(self):
        self.assertEqual(probe('nonzero')['public_completions'],0)

    def test_unconfirmed_live_worker_is_bounded_by_existing_deadline(self):
        self.assertEqual(probe('unconfirmed')['public_completions'],0)

    def test_malformed_confirmation_never_exposes_a_result(self):
        self.assertEqual(probe('bad_confirmation')['public_completions'],0)

    def test_duplicate_after_confirmation_cannot_complete_again(self):
        self.assertEqual(probe('late_duplicate')['public_completions'],1)

    def test_server_closes_its_result_transaction_without_extra_game_events(self):
        import io
        from dataclasses import asdict
        from types import SimpleNamespace
        from unittest.mock import patch
        from goal2.engine.original_match import Fixture
        from goal2.game.engine_server import Server, read_packet
        from goal2.game.watched_match import WatchedOutcome
        output = io.BytesIO()
        server = Server(io.BytesIO(), output)
        server.game = (SimpleNamespace(), b'synthetic-wire-placeholder')
        outcome = WatchedOutcome({}, b'synthetic-not-game-memory', (), (1, 2), 1)
        with patch('goal2.game.watched_match.prepare_watched', return_value=None), \
             patch('goal2.game.watched_match._drive_match', return_value=outcome):
            server._match(dict(kind='watched', fixture=asdict(Fixture(7, 19, index=21, kind=1))))
        output.seek(0)
        packets = []
        while (packet := read_packet(output)) is not None:
            packets.append(packet)
        self.assertEqual([h['kind'] for h, payload in packets], ['complete', 'settled'])
        self.assertEqual(packets[0][1], outcome.memory)
        self.assertIsNone(packets[1][0]['value'])
        self.assertEqual(packets[1][1], b'')
