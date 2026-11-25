"""[designed: T170am] Retained timed opportunity controls."""

import unittest
from types import SimpleNamespace
from unittest.mock import Mock

from goal2.game.season_worker import SeasonRequestError, SeasonWorker
from goal2.tests import pypy_engine, requires
from goal2.tests.test_prematch_preview_t170s import reference_raw


def timing(keeper):
    return dict(context='substitution_opportunity', keeper_unavailable=keeper,
                timeout_polls=1000 if keeper else 400, poll_ms=10, substitutions_now=True)


class Protocol(unittest.TestCase):
    def test_worker_checks_exact_opportunity_answers_before_consuming_the_stop(self):
        worker = SeasonWorker()
        match = Mock(waiting=timing(False))
        worker.session = SimpleNamespace(pending_match=match)
        worker.decision = 7
        request = dict(op='season', action='answer', request=1, decision=7, choice_answer=True)
        for answer in ({}, {'opportunity': True}, {'opportunity': 'dismiss'},
                       {'opportunity': 'accept', 'substitutions': []}):
            with self.subTest(answer=answer), self.assertRaises(SeasonRequestError):
                worker.dispatch(dict(request, answer=answer))
            self.assertEqual(worker.decision, 7)
        for fields in ({'keeper_unavailable': 0}, {'timeout_polls': 1000}, {'poll_ms': '10'},
                       {'substitutions_now': 1}):
            match.waiting = dict(timing(False), **fields)
            with self.subTest(fields=fields), self.assertRaises(SeasonRequestError):
                worker.dispatch(dict(request, answer={'opportunity': 'accept'}))
            self.assertEqual(worker.decision, 7)
        match.answer.assert_not_called()
        match.waiting = timing(False)
        worker.dispatch(dict(request, answer={'opportunity': 'accept'}))
        self.assertIsNone(worker.decision)
        match.answer.assert_called_once_with(opportunity='accept')


def sample(keeper):
    from goal2.engine.original_match.image import Image
    from goal2.engine.original_match.screens import SUBS_ALLOWED, SUBS_LEFT
    from goal2.game import engine_tables
    from goal2.game.season import canonical_hash

    tables = engine_tables.load()
    image = Image.from_bytes(reference_raw())
    ds = image.DS * 16
    image.memory[ds + 0x9B34:ds + 0x9B38] = b'\x07\0\x13\0'
    image.memory[ds + SUBS_ALLOWED] = 1
    managed, players = image.squad(7), image.players()
    data = dict(timing(keeper), eleven=managed[:11], bench=managed[11:], injured=[],
                substitutions_left=image.rd(SUBS_LEFT, 1), tactics=image.countries()[7][0x2D],
                positions=[[word, players[word][6]] for word in managed if word],
                player_records=[[word, players[word].hex()] for word in managed if word],
                team_context=dict(match_set_up=image.rd(0xC1E, 1),
                                  in_match_menu_used=image.rd(0xC1F, 1), sides=[7, 19]))
    state = image.state(tables)
    return dict(action='stopped_preview', state=state, data=data,
                preview=dict(schema='goal2/stopped-preview/1', decision=3, managed_country=7,
                             state_hash=canonical_hash(state), data_hash=canonical_hash(data)))


@requires.need(modules=('PySide6',), files=('GOAL.DAT',))
class Window(unittest.TestCase):
    def setUp(self):
        from goal2.data.goaldat import load
        from goal2.tests.test_native_pitch_t170ad import WindowControls

        WindowControls.setUpClass()
        self.case = WindowControls('test_quick_never_answers_decisions_and_delivers_once')
        self.case.opportunity_controls = True
        self.addCleanup(self.case.doCleanups)
        self.case.setUp()
        self.case.model.goaldat = load((requires.CACHE / 'GOAL.DAT').read_bytes())
        self.case.owner.managed_country = 7

    def show(self, keeper, quick=False):
        from PySide6.QtCore import Qt
        from goal2.tests.test_native_driver_t170ac import event
        from goal2.tests.test_stopped_view_t170af import respond

        case = self.case
        if quick:
            case.key(Qt.Key.Key_R)
        self.packet = sample(keeper)
        case.tick()
        case.owner.batch(events=[event('decision', self.packet['data'])], decision=3, total=4)
        case.tick()
        self.assertEqual(case.owner.sent[-1], ('stopped_preview', {'decision': 3}))
        self.assertFalse(case.screen.stop_box.open)
        respond(case.owner, self.packet)
        case.tick()
        self.assertEqual(case.failures, [])
        self.assertEqual(case.decisions, [])
        self.assertTrue(case.screen.stop_box.open)
        return case.screen.stop_box

    def test_ordinary_escape_accepts_once_refusal_allows_explicit_retry_and_next_bench(self):
        from PySide6.QtCore import Qt
        from goal2.tests.test_native_driver_t170ac import event
        from goal2.tests.test_stopped_view_t170af import respond
        from goal2.ui.s18_stop import SUBSTITUTION_OPPORTUNITY

        case = self.case
        box = self.show(False, quick=True)
        self.assertEqual(box.opportunity_timer.interval(), 4000)
        self.assertEqual(box.headline.text(), SUBSTITUTION_OPPORTUNITY)
        with self.assertRaises(ValueError):
            case.screen.controller.driver.answer_choice(2, {'opportunity': 'accept'})

        case.key(Qt.Key.Key_Escape)
        case.key(Qt.Key.Key_Return)
        case.tick()
        accept = ('answer', {'decision': 3, 'choice_answer': True, 'answer': {'opportunity': 'accept'}})
        self.assertEqual(case.owner.sent[-1], accept)
        self.assertEqual(case.owner.sent.count(accept), 1)
        self.assertEqual(case.screen.controller.driver.pause_requests, 0)
        case.owner.number += 1
        case.owner.queue.put(('season_error', dict(request=case.owner.number, error='Retry the prompt.', lost=False)))
        case.tick()
        self.assertIn('Retry', case.screen.enter_action[0])
        self.assertEqual(case.screen.controller.note, 'Retry the prompt.')
        self.assertFalse(box.open)
        self.assertEqual(case.owner.sent.count(accept), 1)

        case.key(Qt.Key.Key_Return)
        self.assertEqual(case.owner.sent[-1], ('stopped_preview', {'decision': 3}))
        respond(case.owner, self.packet)
        case.tick()
        self.assertEqual(case.screen.controller.note, '')
        case.key(Qt.Key.Key_Return)
        self.assertEqual(case.owner.sent.count(accept), 2)
        case.owner.reply('answer')
        case.tick()
        self.assertIsNone(case.screen.opportunity)
        self.assertEqual(case.owner.sent[-1], accept)
        self.assertEqual(case.decisions, [])
        case.tick()
        self.assertEqual(case.owner.sent[-1][0], 'next')
        legal = dict(self.packet['data'], context='substitution')
        case.owner.batch(events=[event('decision', legal)], decision=4, total=5)
        case.tick()
        self.assertEqual(case.decisions, [dict(decision=4, event=event('decision', legal))])

    def test_keeper_times_out_under_help_and_waits_for_acknowledgement(self):
        from PySide6.QtCore import Qt
        from PySide6.QtTest import QSignalSpy
        from goal2.ui.s18_stop import NO_GOALKEEPER
        from goal2.ui.s22_help import HelpScreen

        case = self.case
        box = self.show(True)
        self.assertEqual(box.opportunity_timer.interval(), 10000)
        self.assertEqual(box.headline.text(), NO_GOALKEEPER)
        case.key(Qt.Key.Key_F1)
        self.assertIsInstance(case.win.current(), HelpScreen)
        timeout = QSignalSpy(box.opportunity_timer.timeout)
        box.opportunity_timer.start(20)
        self.assertTrue(timeout.wait(2000))
        self.assertEqual(case.owner.sent[-1], ('answer', {'decision': 3, 'choice_answer': True,
                                                         'answer': {'opportunity': 'timeout'}}))
        case.owner.reply('answer')
        case.tick()
        self.assertIsNone(case.screen.opportunity)
        self.assertIsInstance(case.win.current(), HelpScreen)
        self.assertEqual(case.owner.sent[-1][0], 'answer')
        case.key(Qt.Key.Key_Escape)
        case.tick()
        self.assertEqual(case.owner.sent[-1][0], 'next')

    def test_close_stops_both_timers_and_disposes_without_answer(self):
        case = self.case
        box = self.show(False)
        case.win.leaving = True
        case.win.close()
        self.assertTrue(case.owner.closed)
        self.assertFalse(box.opportunity_timer.isActive())
        self.assertFalse(box.blink_timer.isActive())
        self.assertFalse(box.open)
        self.assertFalse(any(name == 'answer' for name, _ in case.owner.sent))


def actual_opportunity(raw, response):
    from dataclasses import asdict
    import sys

    from goal2.engine.original_match import Image, Match
    from goal2.engine.original_match.machine import MEM_SIZE, REGS, Uc
    from goal2.game import engine_tables
    from goal2.game.stopped_snapshot import StoppedMatchSnapshot
    from goal2.game.watched_pitch import snapshot

    assert sys.implementation.name == 'pypy' and sys.version_info[:2] == (3, 11) and Uc is None
    worker = SeasonWorker()
    request = 0

    def ask(action, **fields):
        nonlocal request
        request += 1
        return worker.dispatch(dict(op='season', action=action, request=request, **fields))

    ask('open', state=Image.from_bytes(raw).state(engine_tables.load()))
    ask('advance')
    match = worker.session.pending_match
    ask('configure', frames=True)
    paused = armed = False
    for _ in range(300):
        batch = ask('next', count=1 if not armed else 32)
        number = batch['decision']
        if number is None:
            if not paused and batch['frames']:
                assert ask('pause')['paused']
                paused = True
            continue
        data = batch['events'][-1]['data']
        context = data['context']
        if context == 'substitution_opportunity':
            break
        if context == 'pause' and not armed:
            answer = {'edit_only': True, 'request_substitution': True}
            ask('answer', decision=number, answer=answer, pause_edit=True)
            armed = True
        else:
            if context == 'pause':
                assert data['request_substitution'] is True
            ask('answer', decision=number, answer={})
    else:
        raise AssertionError('The requested substitution did not reach a timed opportunity')

    saved = match.save()
    packet = ask('stopped_preview', decision=number)
    preview = StoppedMatchSnapshot.from_packet(packet, request=request, decision=number,
                                               managed_country=match.opts['managed'], data=data)
    assert preview.data['keeper_unavailable'] is False and preview.data['timeout_polls'] == 400
    assert match.save() == saved
    for decision, answer in ((number - 1, {'opportunity': 'accept'}),
                             (number, {'opportunity': 'dismiss'}),
                             (number, {'opportunity': 'timeout', 'substitutions': []})):
        try:
            ask('answer', decision=decision, answer=answer, choice_answer=True)
        except SeasonRequestError:
            assert match.save() == saved and worker.decision == number
        else:
            raise AssertionError('Invalid opportunity input consumed the decision')

    answer = {'opportunity': response}
    baseline = Match.load(saved)
    baseline.answer(**answer)
    seq, watermark = worker.frame_sequence, worker.event_count
    ask('answer', decision=number, answer=answer, choice_answer=True)
    result = ask('next', count=32)
    expected_events, expected_frames = [], []
    for index, event in enumerate(baseline.events(), 1):
        if event.kind == 'tick':
            expected_frames.append(snapshot(baseline, event, seq + len(expected_frames),
                                            watermark + len(expected_events)))
        else:
            expected_events.append(asdict(event))
        if event.kind == 'decision' or index == 32:
            break
    assert result['events'] == expected_events and result['frames'] == expected_frames
    assert worker.session.pending_match is match
    assert match.m.read(0, MEM_SIZE) == baseline.m.read(0, MEM_SIZE)
    assert [match.m.reg(reg) for reg in REGS] == [baseline.m.reg(reg) for reg in REGS]
    return result['events'][-1]['data']['context'] if result['decision'] is not None else None


class Actual(unittest.TestCase):
    def test_accept_and_timeout_match_direct_sdk_at_the_same_genuine_opportunity(self):
        raw = reference_raw()
        for action, expected in (('accept', 'substitution'), ('timeout', None)):
            with self.subTest(action=action):
                result = pypy_engine.call(__name__ + ':actual_opportunity', raw, action)
                self.assertEqual(result, expected)
