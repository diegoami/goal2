"""T170aj guard controls for the native half-time transaction."""

from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import Mock

from goal2.game.half_time_edit import validate_edit
from goal2.game.native_driver import NativeMatchDriver
from goal2.game.season_worker import SeasonRequestError, SeasonWorker
from goal2.tests.test_native_driver_t170ac import Owner, event


def decision():
    available = bytearray(20)
    available[14] = 10
    return {'context': 'half_time', 'eleven': [11] * 11, 'bench': [12, 13],
            'substitutions_now': True, 'substitutions_left': 1,
            'player_records': [[12, available.hex()], [13, bytes(20).hex()]]}


class HalfTime(TestCase):
    def test_worker_guard_applies_only_to_the_opted_in_ui_request(self):
        worker = SeasonWorker()
        match = Mock(waiting=decision())
        worker.session = SimpleNamespace(pending_match=match)
        worker.decision = 7
        prior = dict(edit_only=True, substitutions=[[11, 12], [11, 12]])
        request = dict(op='season', request=1, action='answer', decision=7, answer=prior)
        with self.assertRaises(SeasonRequestError):
            worker.dispatch(dict(request, half_time_edit=True))
        match.answer.assert_not_called()
        self.assertEqual(worker.decision, 7)
        worker.dispatch(request)
        match.answer.assert_called_once_with(**prior)

    def test_single_available_pair_and_typed_tactic_domains(self):
        data = decision()
        validate_edit(data, {'edit_only': True, 'substitutions': [[11, 12]]})
        validate_edit(data, {'edit_only': True, 'tactics': {'8': False}})
        for edit in ({'substitutions': [[11, 13]]}, {'substitutions': [[12, 11]]},
                     {'substitutions': [[True, 12]]}, {'substitutions': [[11, 12], [11, 12]]},
                     {'tactics': {True: False}}, {'tactics': {'1': 1}},
                     {'tactics': {'1': True}, 'quick': False}):
            with self.subTest(edit=edit), self.assertRaises(ValueError):
                validate_edit(data, {'edit_only': True, **edit})
        for change in ({'substitutions_left': 0}, {'substitutions_now': False},
                       {'context': 'pause'}):
            with self.subTest(change=change), self.assertRaises(ValueError):
                validate_edit({**data, **change}, {'edit_only': True, 'substitutions': [[11, 12]]})

    def test_held_edit_reads_exactly_one_continuation_and_rejects_wrong_stop(self):
        owner = Owner()
        driver = NativeMatchDriver(owner)
        initial = driver.event_base + len(driver.events)
        driver.tick(0)
        first = decision()
        stop = event('decision', first)
        owner.batch(events=[stop], decision=7, total=initial + 1)
        driver.tick(0)
        with self.assertRaises(ValueError):
            driver.answer_half_time({'edit_only': True, 'tactics': {1: False}})
        driver._stopped_view = SimpleNamespace(snapshot=SimpleNamespace(data=first))
        driver.set_held(True)
        driver.answer_half_time({'edit_only': True, 'tactics': {1: False}})
        with self.assertRaises(ValueError):
            driver.answer_half_time({})
        owner.reply('answer')
        driver.tick(0)
        self.assertEqual(owner.sent[-1], ('next', {'count': 32}))
        received = len(owner.sent)
        owner.batch(events=[event('decision', {'context': 'pause', 'edited': True})],
                    decision=8, total=initial + 2)
        driver.tick(0)
        self.assertEqual(driver.status, 'lost')
        self.assertEqual(len(owner.sent), received)
