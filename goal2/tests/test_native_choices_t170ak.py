"""T170ak checks the native pitch-to-chooser boundary using controlled packets."""

import unittest
from types import SimpleNamespace

from goal2.game.native_choice import validate_choice
from goal2.game.season import canonical_hash
from goal2.game.season_worker import SeasonRequestError, SeasonWorker
from goal2.tests import pypy_engine, requires
from goal2.tests.test_prematch_preview_t170s import reference_raw


class Protocol(unittest.TestCase):
    def test_choice_answer_is_typed_and_bound_to_the_current_available_domain(self):
        data = {'context': 'set_piece', 'available': [1, 2]}
        validate_choice(data, {'taker': None})
        validate_choice(data, {'taker': 2})
        for invalid in ({}, {'taker': 3}, {'taker': True}, {'taker': '2'}, {'taker': 1, 'quick': True}):
            with self.subTest(invalid=invalid), self.assertRaises(ValueError):
                validate_choice(data, invalid)
        order = {'context': 'shootout_order', 'available': [1, 2, 3], 'takers': 2}
        for answer in ([1, 2], [2], []):
            validate_choice(order, {'shootout_order': answer})
        for invalid in ([1, 1], [1, 2, 3], [True], ['1'], None):
            with self.subTest(invalid=invalid), self.assertRaises(ValueError):
                validate_choice(order, {'shootout_order': invalid})

    def test_worker_refusal_does_not_consume_the_choice(self):
        from unittest.mock import Mock
        worker = SeasonWorker()
        match = Mock(waiting={'context': 'set_piece', 'available': [1, 2]})
        worker.session = SimpleNamespace(pending_match=match)
        worker.decision = 7
        request = dict(op='season', action='answer', request=8, decision=7, choice_answer=True)
        with self.assertRaises(SeasonRequestError):
            worker.dispatch(dict(request, answer={'taker': True}))
        self.assertEqual(worker.decision, 7)
        match.answer.assert_not_called()
        worker.dispatch(dict(request, answer={'taker': 2}))
        self.assertIsNone(worker.decision)
        match.answer.assert_called_once_with(taker=2)


@requires.need(modules=('PySide6',), files=('GOAL.DAT',))
class Window(unittest.TestCase):
    def setUp(self):
        from goal2.data.goaldat import load
        from goal2.tests.test_native_pitch_t170ad import WindowControls
        WindowControls.setUpClass()
        self.case = WindowControls('test_quick_never_answers_decisions_and_delivers_once')
        self.case.choice_controls = True
        self.addCleanup(self.case.doCleanups)
        self.case.setUp()
        self.case.model.goaldat = load((requires.CACHE / 'GOAL.DAT').read_bytes())
        self.case.owner.managed_country = 7

    def show_choice(self, context, **fields):
        from goal2.engine.original_match.image import Image
        from goal2.engine.original_match.screens import SUBS_LEFT
        from goal2.game import engine_tables
        from goal2.tests.test_native_driver_t170ac import event
        case = self.case
        image = Image.from_bytes(reference_raw())
        ds = image.DS * 16
        # Controlled decision fixture on the structurally valid reference memory.
        image.memory[ds + 0x9B34:ds + 0x9B38] = b'\x07\0\x13\0'
        players = image.players()
        squad = image.squad(7)
        self.eleven = squad[:11]
        available = [word for word in self.eleven if word
                     and 0 < players[word][14] < 128 and not players[word][16] & 0xA4]
        data = dict(context=context, eleven=self.eleven, bench=squad[11:],
                    positions=[[word, players[word][6]] for word in squad if word],
                    player_records=[[word, players[word].hex()] for word in squad if word],
                    tactics=image.countries()[7][0x2D], substitutions_left=image.rd(SUBS_LEFT, 1),
                    team_context=dict(match_set_up=image.rd(0xC1E, 1),
                                      in_match_menu_used=image.rd(0xC1F, 1), sides=[7, 19]),
                    available=available, **fields)
        if context == 'set_piece':
            data['current'] = self.eleven[1]
        state = image.state(engine_tables.load())
        self.packet = dict(action='stopped_preview', state=state, data=data,
                           preview=dict(schema='goal2/stopped-preview/1', decision=7, managed_country=7,
                                        state_hash=canonical_hash(state), data_hash=canonical_hash(data)))
        case.tick()
        case.owner.batch(events=[event('decision', data)], decision=7, total=4)
        case.tick()
        self.assertEqual(case.owner.sent[-1], ('stopped_preview', {'decision': 7}))
        self.reply_read()
        self.assertEqual(case.failures, [])
        self.assertEqual(case.decisions, [])
        return case.win.current()

    def reply_read(self):
        from goal2.tests.test_stopped_view_t170af import respond
        respond(self.case.owner, self.packet)
        self.case.tick()

    def test_taker_timeout_under_help_returns_to_pitch_only_after_ack(self):
        from PySide6.QtCore import Qt
        from PySide6.QtTest import QSignalSpy
        from goal2.ui.s22_help import HelpScreen
        from goal2.tests.ui_assertions import assert_fits
        case = self.case
        chooser = self.show_choice('set_piece', role=5)
        word = self.eleven[1]
        self.assertEqual(chooser.highlighted(), word)
        self.assertEqual(chooser.model.state.players[word], bytes.fromhex(dict(self.packet['data']['player_records'])[word]))
        assert_fits(self, case.win)
        with self.assertRaises(ValueError):
            case.screen.controller.driver.answer_choice(8, {'taker': word})
        case.key(Qt.Key.Key_F1)
        help_screen = case.win.current()
        self.assertIsInstance(help_screen, HelpScreen)
        timeout = QSignalSpy(chooser.timer.timeout)
        chooser.timer.start(20)
        self.assertTrue(timeout.wait(2000))
        chooser.no_key()
        self.assertIs(case.win.current(), help_screen)
        self.assertEqual(case.owner.sent[-1], ('answer', {'decision': 7, 'answer': {'taker': None}, 'choice_answer': True}))
        self.assertEqual(sum(action == 'answer' for action, _ in case.owner.sent), 1)
        case.owner.reply('answer')
        case.tick()
        self.assertIs(case.win.current(), case.screen)
        self.assertIsNone(case.screen.choice)

    def test_order_undo_partial_remainder_and_refusal_refresh(self):
        from PySide6.QtCore import Qt
        case = self.case
        chooser = self.show_choice('shootout_order', takers=5)
        case.key(Qt.Key.Key_Return)
        case.key(Qt.Key.Key_Down)
        case.key(Qt.Key.Key_Return)
        case.key(Qt.Key.Key_Escape)
        first = self.eleven[0]
        self.assertEqual(chooser.picks, [first])
        case.key(Qt.Key.Key_C)
        self.assertEqual(case.owner.sent[-1][1]['answer'], {'shootout_order': [first]})
        case.owner.number += 1
        case.owner.queue.put(('season_error', {'request': case.owner.number,
                                               'error': 'Please choose again.', 'lost': False}))
        case.tick()
        self.assertEqual(case.owner.sent[-1], ('stopped_preview', {'decision': 7}))
        self.reply_read()
        fresh = case.win.current()
        self.assertIsNot(fresh, chooser)
        self.assertIn('Please choose again.', fresh.wait_detail.text())
        case.key(Qt.Key.Key_C)
        self.assertEqual(case.owner.sent[-1][1]['answer'], {'shootout_order': []})
        case.owner.reply('answer')
        case.tick()
        self.assertIs(case.win.current(), case.screen)
        self.assertEqual(case.failures, [])


def actual_prompt(raw, context):
    """Visit genuine SDK decisions and compare worker submission to direct continuation."""
    import sys
    from dataclasses import asdict
    from goal2.engine.original_match import Fixture, Image, Match
    from goal2.engine.original_match.machine import MEM_SIZE, REGS, Uc
    from goal2.game import engine_tables
    from goal2.game.stopped_snapshot import StoppedMatchSnapshot

    assert sys.implementation.name == 'pypy' and sys.version_info[:2] == (3, 11) and Uc is None
    tables = engine_tables.load()
    image = Image.from_state(Image.from_bytes(raw).state(tables), tables)
    fixture = Fixture(7, 19, 21) if context == 'set_piece' else Fixture(7, 19, 42, 200)
    match = Match(image, fixture, managed=7, set_piece=True, live_players=True, engine='port')
    stream = match.events()
    for event in stream:
        if event.kind == 'decision':
            if event.data['context'] == context:
                break
            match.answer()
    else:
        raise AssertionError('Reference fixture did not reach ' + context)
    worker = SeasonWorker()
    worker.session = SimpleNamespace(pending_match=match)
    worker.stream = stream
    worker.seam = object()
    worker.decision = worker._decision_number = 7
    saved = match.save()
    preview = worker.dispatch(dict(op='season', action='stopped_preview', request=1, decision=7))
    snapshot = StoppedMatchSnapshot.from_packet(preview, request=1, decision=7,
                                               managed_country=7, data=event.data)
    assert snapshot.data == event.data and match.save() == saved
    order = list(reversed(event.data['available']))[:2]
    answer = {'taker': order[0]} if context == 'set_piece' else {'shootout_order': order}
    request = dict(op='season', action='answer', request=2, decision=7, choice_answer=True)
    invalid = {'taker': True} if context == 'set_piece' else {'shootout_order': [order[0]] * 2}
    try:
        worker.dispatch(dict(request, answer=invalid))
    except SeasonRequestError:
        assert worker.decision == 7 and match.save() == saved
    else:
        raise AssertionError('Invalid choice was consumed')
    baseline = Match.load(saved)
    baseline.answer(**answer)
    worker.dispatch(dict(request, answer=answer))
    batch = worker.dispatch(dict(op='season', action='next', request=3, count=32))
    expected = []
    for row in baseline.events():
        expected.append(asdict(row))
        if row.kind == 'decision' or len(expected) == 32:
            break
    assert batch['events'] == expected
    assert match.m.read(0, MEM_SIZE) == baseline.m.read(0, MEM_SIZE)
    assert [match.m.reg(reg) for reg in REGS] == [baseline.m.reg(reg) for reg in REGS]
    return dict(context=context, event_count=len(expected))


class Actual(unittest.TestCase):
    @requires.need(slow=True)
    def test_actual_taker_and_shootout_choices_equal_direct_sdk_continuation(self):
        for context in ('set_piece', 'shootout_order'):
            with self.subTest(context=context):
                result = pypy_engine.call(__name__ + ':actual_prompt', reference_raw(), context)
                self.assertEqual(result['context'], context)
                self.assertGreater(result['event_count'], 0)
