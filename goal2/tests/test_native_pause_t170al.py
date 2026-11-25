"""[designed: T170al] Retained pause request and cancel contracts."""

import unittest
from types import SimpleNamespace
from unittest.mock import Mock

from goal2.game.season_worker import SeasonRequestError, SeasonWorker
from goal2.tests import pypy_engine, requires
from goal2.tests.test_prematch_preview_t170s import reference_raw


class Protocol(unittest.TestCase):
    def test_paused_request_is_a_pure_typed_edit(self):
        worker = SeasonWorker()
        match = Mock(waiting={'context': 'pause', 'substitutions_now': False,
                              'request_substitution': False})
        worker.session = SimpleNamespace(pending_match=match)
        worker.decision = 7
        request = dict(op='season', action='answer', request=1, decision=7, pause_edit=True)
        valid = {'edit_only': True, 'request_substitution': True}
        for answer in ({'request_substitution': 1, 'edit_only': True},
                       {'request_substitution': True, 'edit_only': True, 'substitutions': [[1, 2]]},
                       {'request_substitution': True}):
            with self.subTest(answer=answer), self.assertRaises(SeasonRequestError):
                worker.dispatch(dict(request, answer=answer))
            self.assertEqual(worker.decision, 7)
        for fields in ({'pause_edit': 1}, {'choice_answer': True}, {'half_time_edit': True}, {'decision': 6}):
            with self.subTest(fields=fields), self.assertRaises(SeasonRequestError):
                worker.dispatch(dict(request, answer=valid) | fields)
        match.answer.assert_not_called()
        worker.dispatch(dict(request, answer=valid))
        self.assertIsNone(worker.decision)
        match.answer.assert_called_once_with(edit_only=True, request_substitution=True)


@requires.need(modules=('PySide6',), files=('GOAL.DAT',))
class Window(unittest.TestCase):
    def test_request_cancel_and_play_use_only_verified_current_stops(self):
        from PySide6.QtCore import Qt
        from PySide6.QtTest import QTest
        from goal2.data.goaldat import load
        from goal2.engine.original_match.image import Image
        from goal2.engine.original_match.screens import SUBS_ALLOWED, SUBS_LEFT, SUBS_REQUEST
        from goal2.game import engine_tables
        from goal2.game.season import canonical_hash
        from goal2.tests.test_native_driver_t170ac import event
        from goal2.tests.test_native_pitch_t170ad import WindowControls
        from goal2.tests.test_stopped_view_t170af import respond
        from goal2.tests.ui_assertions import assert_fits
        from goal2.ui.native_pause import NativePauseScreen
        from goal2.ui.s22_help import HelpScreen

        WindowControls.setUpClass()
        case = WindowControls('test_quick_never_answers_decisions_and_delivers_once')
        case.pause_controls = True
        self.addCleanup(case.doCleanups)
        case.setUp()
        case.model.goaldat = load((requires.CACHE / 'GOAL.DAT').read_bytes())
        case.owner.managed_country = 7

        tables = engine_tables.load()
        image = Image.from_bytes(reference_raw())
        ds = image.DS * 16
        image.memory[ds + 0x9B34:ds + 0x9B38] = b'\x07\0\x13\0'
        image.memory[ds + SUBS_ALLOWED] = image.memory[ds + SUBS_REQUEST] = 0
        image.memory[ds + SUBS_LEFT] = 3
        managed, opponents = image.squad(7), image.squad(19)
        players = image.players()
        data = dict(context='pause', eleven=managed[:11], bench=managed[11:], substitutions_now=False,
                    substitutions_left=3, request_substitution=False, tactics=image.countries()[7][0x2D],
                    positions=[[word, players[word][6]] for word in managed if word],
                    player_records=[[word, players[word].hex()] for word in managed if word],
                    team_context=dict(match_set_up=image.rd(0xC1E, 1),
                                      in_match_menu_used=image.rd(0xC1F, 1), sides=[7, 19]))
        state = image.state(tables)
        packet = dict(action='stopped_preview', state=state, data=data,
                      preview=dict(schema='goal2/stopped-preview/1', decision=3, managed_country=7,
                                   state_hash=canonical_hash(state), data_hash=canonical_hash(data)))
        case.tick()
        case.owner.batch(events=[event('decision', data)], decision=3, total=4)
        case.tick()
        page = case.win.current()
        self.assertIsInstance(page, NativePauseScreen)
        respond(case.owner, packet)
        case.tick()
        self.assertEqual(case.failures, [])
        self.assertEqual(page.players, tuple(managed))
        self.assertEqual(page.budget.text(), 'Substitutions left: 3')
        self.assertEqual(page.request_button.text(), 'Request substitution')
        assert_fits(self, case.win)
        case.key(Qt.Key.Key_Right)
        self.assertEqual(page.players, tuple(opponents))
        case.key(Qt.Key.Key_Left)
        with self.assertRaises(ValueError):
            page.driver.answer_pause(2, {'edit_only': True, 'request_substitution': True})

        for number, desired in ((3, True), (4, False)):
            QTest.mouseClick(page.request_button, Qt.MouseButton.LeftButton)
            case.key(Qt.Key.Key_X)
            case.key(Qt.Key.Key_Return)
            self.assertEqual(case.owner.sent[-1], ('answer', {'decision': number, 'pause_edit': True,
                            'answer': {'edit_only': True, 'request_substitution': desired}}))
            self.assertEqual(sum(name == 'answer' for name, _ in case.owner.sent), number - 2)
            if desired:
                case.key(Qt.Key.Key_F1)
                self.assertIsInstance(case.win.current(), HelpScreen)
            case.owner.reply('answer')
            case.tick()
            self.assertEqual(case.owner.sent[-1], ('next', {'count': 32}))
            image.memory[image.DS * 16 + SUBS_REQUEST] = int(desired)
            packet['state'] = image.state(tables)
            data.update(request_substitution=desired, edited=True)
            packet['preview'].update(decision=number + 1, state_hash=canonical_hash(packet['state']),
                                     data_hash=canonical_hash(data))
            case.owner.batch(events=[event('decision', data)], decision=number + 1, total=number + 2)
            case.tick()
            self.assertEqual(case.owner.sent[-1], ('stopped_preview', {'decision': number + 1}))
            respond(case.owner, packet)
            case.tick()
            if desired:
                self.assertIsInstance(case.win.current(), HelpScreen)
                case.key(Qt.Key.Key_Escape)
            self.assertIs(case.win.current(), page)
            self.assertEqual(page.request_button.text(), 'Cancel request' if desired else 'Request substitution')

        case.key(Qt.Key.Key_Return)
        self.assertEqual(case.owner.sent[-1], ('answer', {'decision': 5, 'answer': {}}))
        case.owner.reply('answer')
        case.tick()
        self.assertIs(case.win.current(), case.screen)
        self.assertEqual(case.decisions, [])
        self.assertEqual(case.failures, [])


def reach_pause(raw):
    from goal2.engine.original_match import Image
    from goal2.game import engine_tables

    worker = SeasonWorker()
    request = 0

    def ask(action, **fields):
        nonlocal request
        request += 1
        return worker.dispatch(dict(op='season', action=action, request=request, **fields))

    ask('open', state=Image.from_bytes(raw).state(engine_tables.load()))
    ask('advance')
    ask('configure', frames=True)
    asked_pause = False
    for _ in range(1000):
        batch = ask('next', count=1)
        number = batch['decision']
        if number is not None:
            if batch['events'][-1]['data']['context'] == 'pause':
                return worker, ask, batch
            ask('answer', decision=number, answer={})
        elif not asked_pause and batch['frames']:
            assert ask('pause')['paused']
            asked_pause = True
    raise AssertionError('The fixture did not reach its requested pause')


def actual_pause(raw):
    from dataclasses import asdict
    import sys

    from goal2.engine.original_match import Match
    from goal2.engine.original_match.machine import MEM_SIZE, REGS, Uc
    from goal2.game.stopped_snapshot import StoppedMatchSnapshot

    assert sys.implementation.name == 'pypy' and sys.version_info[:2] == (3, 11) and Uc is None
    worker, ask, batch = reach_pause(raw)
    match = worker.session.pending_match
    number = batch['decision']

    def verified(current, data):
        packet = ask('stopped_preview', decision=current)
        return StoppedMatchSnapshot.from_packet(packet, request=packet['request'], decision=current,
                                                managed_country=match.opts['managed'], data=data)

    views = []
    for desired in (True, False):
        snapshot = verified(number, batch['events'][-1]['data'])
        assert snapshot.data['request_substitution'] is not desired
        saved = match.save()
        for invalid in ({'request_substitution': int(desired), 'edit_only': True},
                        {'request_substitution': desired, 'edit_only': True, 'quick': True}):
            try:
                ask('answer', decision=number, answer=invalid, pause_edit=True)
            except SeasonRequestError:
                assert worker.decision == number and match.save() == saved
            else:
                raise AssertionError('Invalid pause input consumed the decision')
        answer = {'request_substitution': desired, 'edit_only': True}
        baseline = Match.load(saved)
        baseline.answer(**answer)
        ask('answer', decision=number, answer=answer, pause_edit=True)
        batch = ask('next', count=32)
        expected = []
        for row in baseline.events():
            expected.append(asdict(row))
            if row.kind == 'decision':
                break
        assert batch['events'] == expected and not batch['frames']
        assert batch['decision'] > number and batch['events'][-1]['data']['edited'] is True
        assert worker.session.pending_match is match
        assert match.m.read(0, MEM_SIZE) == baseline.m.read(0, MEM_SIZE)
        assert [match.m.reg(reg) for reg in REGS] == [baseline.m.reg(reg) for reg in REGS]
        number = batch['decision']
        view = verified(number, batch['events'][-1]['data'])
        views.append(view.data['request_substitution'])
    ask('answer', decision=number, answer={})
    return views


class Actual(unittest.TestCase):
    def test_retained_worker_pause_request_and_cancel_match_direct_sdk(self):
        states = pypy_engine.call(__name__ + ':actual_pause', reference_raw())
        self.assertEqual(states, [True, False])
