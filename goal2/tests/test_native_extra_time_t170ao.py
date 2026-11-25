"""[designed: T170ao] Retained extra-time phase, tactic and Play boundaries."""

import unittest
from types import SimpleNamespace
from unittest.mock import Mock

from goal2.game.season_worker import SeasonRequestError, SeasonWorker
from goal2.tests import pypy_engine, requires
from goal2.tests.test_prematch_preview_t170s import reference_raw


class Protocol(unittest.TestCase):
    def test_only_one_typed_tactic_at_the_current_extra_time_half(self):
        worker = SeasonWorker()
        match = Mock(waiting={'context': 'extra_time', 'half': 1, 'substitutions_now': False})
        worker.session = SimpleNamespace(pending_match=match)
        worker.decision = 7
        request = dict(op='season', action='answer', request=1, decision=7, extra_time_edit=True)
        tactic = {'edit_only': True, 'tactics': {'8': False}}
        for fields in ({'decision': 6}, {'extra_time_edit': 1}, {'substitution_edit': True},
                       {'answer': dict(tactic, tactics={1: 1})},
                       {'answer': dict(tactic, tactics={'1': True, '8': False})},
                       {'answer': dict(tactic, substitutions=[[11, 12]])}):
            with self.subTest(fields=fields), self.assertRaises(SeasonRequestError):
                worker.dispatch(dict(request, answer=tactic) | fields)
            self.assertEqual(worker.decision, 7)
        for half in (None, True, 0, 3, '1'):
            match.waiting['half'] = half
            with self.subTest(half=half), self.assertRaises(SeasonRequestError):
                worker.dispatch(dict(request, answer=tactic))
        match.answer.assert_not_called()
        match.waiting['half'] = 2
        worker.dispatch(dict(request, answer=tactic))
        match.answer.assert_called_once_with(edit_only=True, tactics={8: False})
        self.assertIsNone(worker.decision)


def actual_extra_time(raw):
    from dataclasses import asdict
    import sys

    from goal2.engine.original_match import Fixture, Image, Match
    from goal2.engine.original_match.machine import MEM_SIZE, REGS, Uc
    from goal2.game import engine_tables
    from goal2.game.stopped_snapshot import StoppedMatchSnapshot

    assert sys.implementation.name == 'pypy' and sys.version_info[:2] == (3, 11) and Uc is None
    tables = engine_tables.load()
    image = Image.from_state(Image.from_bytes(raw).state(tables), tables)
    # [confirmed: upstream test_penalties_after_extra_time] This knockout reaches both halves.
    match = Match(image, Fixture(7, 19, 42, 200), managed=7, live_players=True, engine='port')
    worker = SeasonWorker()
    worker.session = SimpleNamespace(pending_match=match)
    worker.seam = object()
    worker.stream = iter(match.events())
    serial = 0

    def ask(action, **fields):
        nonlocal serial
        serial += 1
        return worker.dispatch(dict(op='season', action=action, request=serial, **fields))

    def seek(batch, half, advance, answer):
        for _ in range(500):
            number = batch['decision']
            if number is not None:
                data = batch['events'][-1]['data']
                if data['context'] == 'extra_time':
                    assert data['half'] == half
                    return batch
                answer(number)
            if batch['exhausted']:
                break
            batch = advance()
        raise AssertionError(f'The knockout did not reach extra-time half {half}')

    advance = lambda: ask('next', count=32)
    batch = seek(advance(), 1, advance, lambda number: ask('answer', decision=number, answer={}))
    baseline = Match.load(match.save())
    direct = iter(baseline.events())

    def compare():
        batch = advance()
        expected = []
        for index, event in enumerate(direct, 1):
            expected.append(asdict(event))
            if event.kind == 'decision' or index == 32:
                break
        assert batch['events'] == expected
        assert match.m.read(0, MEM_SIZE) == baseline.m.read(0, MEM_SIZE)
        assert [match.m.reg(reg) for reg in REGS] == [baseline.m.reg(reg) for reg in REGS]
        return batch

    def read(batch):
        number = batch['decision']
        data = batch['events'][-1]['data']
        packet = ask('stopped_preview', decision=number)
        return StoppedMatchSnapshot.from_packet(packet, request=packet['request'], decision=number,
                                                managed_country=7, data=data)

    def play(number):
        baseline.answer()
        ask('answer', decision=number, answer={})

    seen = []
    for half in (1, 2):
        before = read(batch)
        number = batch['decision']
        assert before.data['half'] == half
        saved = match.save()
        action = {'edit_only': True, 'tactics': {8: not bool(before.data['tactics'] & 128)}}
        for decision, invalid in ((number - 1, action), (number, dict(action, substitutions=[[1, 2]])),
                                  (number, dict(action, tactics={8: 1}))):
            try:
                ask('answer', decision=decision, answer=invalid, extra_time_edit=True)
            except SeasonRequestError:
                assert worker.decision == number and match.save() == saved
            else:
                raise AssertionError('Invalid extra-time input consumed the stop')
        baseline.answer(**action)
        ask('answer', decision=number, answer=action, extra_time_edit=True)
        edited = compare()
        view = read(edited)
        assert edited['decision'] > number and view.data['edited'] is True and view.data['half'] == half
        assert view.data['tactics'] == before.data['tactics'] ^ 128
        assert edited['events'][-1]['score'] == batch['events'][-1]['score']
        assert edited['events'][-1]['minute'] == batch['events'][-1]['minute']
        play(edited['decision'])
        batch = compare()
        if half == 1:
            batch = seek(batch, 2, compare, play)
        else:
            assert batch['events'] and not any(
                event['kind'] == 'decision' and event['data'].get('context') == 'extra_time'
                for event in batch['events'])
        seen.append(half)
    return seen


class Actual(unittest.TestCase):
    @requires.need(slow=True)
    def test_both_genuine_extra_time_stops_match_direct_sdk(self):
        self.assertEqual(pypy_engine.call(__name__ + ':actual_extra_time', reference_raw()), [1, 2])


@requires.need(modules=('PySide6',), files=('GOAL.DAT',))
class Window(unittest.TestCase):
    def setUp(self):
        from goal2.data.goaldat import load
        from goal2.engine.original_match.image import COUNTRIES_PTR, COUNTRY_SIZE, Image
        from goal2.engine.original_match.screens import SUBS_ALLOWED
        from goal2.game import engine_tables
        from goal2.tests.test_native_opportunity_t170am import sample
        from goal2.tests.test_native_pitch_t170ad import WindowControls

        WindowControls.setUpClass()
        self.case = WindowControls('test_quick_never_answers_decisions_and_delivers_once')
        self.case.extra_time_controls = True
        self.addCleanup(self.case.doCleanups)
        self.case.setUp()
        self.case.model.goaldat = load((requires.CACHE / 'GOAL.DAT').read_bytes())
        self.case.owner.managed_country = 7

        self.packet = sample(False)
        self.tables = engine_tables.load()
        self.image = Image.from_state(self.packet['state'], self.tables)
        self.image.memory[self.image.DS * 16 + SUBS_ALLOWED] = 0
        self.tactics_at = self.image.far(COUNTRIES_PTR) + 7 * COUNTRY_SIZE + 0x2D
        self.data = self.packet['data']
        self.data.update(context='extra_time', substitutions_now=False)
        self.total = 3
        self.case.tick()

    def decision(self, number, half, *, edited=False, bit=0):
        from goal2.game.season import canonical_hash
        from goal2.tests.test_native_driver_t170ac import event

        self.image.memory[self.tactics_at] ^= bit
        self.data.update(half=half, edited=edited, tactics=self.image.memory[self.tactics_at])
        state = self.image.state(self.tables)
        self.packet['state'] = state
        self.packet['preview'].update(decision=number, state_hash=canonical_hash(state),
                                      data_hash=canonical_hash(self.data))
        self.total += 1
        notice = event('decision', self.data)
        notice['minute'] = 90 if half == 1 else 105
        self.case.owner.batch(events=[notice], decision=number, total=self.total)
        self.case.tick()

    def read(self):
        from goal2.tests.test_stopped_view_t170af import respond
        respond(self.case.owner, self.packet)
        self.case.tick()

    def test_both_phases_keep_edits_and_play_separate_under_help(self):
        from PySide6.QtCore import Qt
        from goal2.tests.ui_assertions import assert_fits
        from goal2.ui.native_half_time import NativeExtraTimeScreen
        from goal2.ui.s22_help import HelpScreen

        case = self.case
        for number, half, label in ((3, 1, 'Play extra time'), (5, 2, 'Play second half of extra time')):
            self.decision(number, half)
            page = case.win.current()
            self.assertIsInstance(page, NativeExtraTimeScreen)
            self.assertFalse(page.toggle_button.isEnabled())
            self.read()
            self.assertEqual(case.failures, [])
            self.assertEqual(page.enter_hint_text(), label)
            self.assertEqual(page.snapshot.snapshot.data['half'], half)
            self.assertEqual(page.players, tuple(self.data['eleven'] + self.data['bench']))
            self.assertFalse(hasattr(page, 'substitute'))
            assert_fits(self, case.win)
            self.assertTrue(page.toggle_button.isEnabled())
            desired = not bool(self.data['tactics'] & 1)
            change = {'edit_only': True, 'tactics': {1: desired}}
            with self.assertRaises(ValueError):
                page.driver.answer_extra_time(number - 1, change)
            case.key(Qt.Key.Key_G)
            case.key(Qt.Key.Key_G)
            case.key(Qt.Key.Key_Return)
            expected = ('answer', {'decision': number, 'extra_time_edit': True, 'answer': change})
            self.assertEqual(case.owner.sent[-1], expected)
            self.assertEqual(case.owner.sent.count(expected), 1)
            case.key(Qt.Key.Key_F1)
            self.assertIsInstance(case.win.current(), HelpScreen)
            case.owner.reply('answer')
            case.tick()
            self.assertEqual(case.owner.sent[-1], ('next', {'count': 32}))
            self.decision(number + 1, half, edited=True, bit=1)
            self.read()
            self.assertIsInstance(case.win.current(), HelpScreen)
            self.assertEqual(bool(page.snapshot.snapshot.data['tactics'] & 1), desired)
            case.key(Qt.Key.Key_Escape)
            self.assertIs(case.win.current(), page)
            case.key(Qt.Key.Key_Return)
            self.assertEqual(case.owner.sent[-1], ('answer', {'decision': number + 1, 'answer': {}}))
            case.owner.reply('answer')
            case.tick()
            self.assertIs(case.win.current(), case.screen)
            case.tick()
            self.assertEqual(case.owner.sent[-1][0], 'next')
        self.assertEqual(case.decisions, [])
        self.assertEqual(case.failures, [])

    def test_an_edit_cannot_acknowledge_the_other_half(self):
        from PySide6.QtCore import Qt
        from goal2.tests.test_native_driver_t170ac import event

        case = self.case
        self.decision(3, 1)
        self.read()
        case.key(Qt.Key.Key_G)
        case.owner.reply('answer')
        case.tick()
        self.assertEqual(case.owner.sent[-1], ('next', {'count': 32}))
        wrong_stop = event('decision', dict(self.data, half=2, edited=True))
        wrong_stop['minute'] = 90
        case.owner.batch(events=[wrong_stop], decision=4, total=5)
        case.tick()
        self.assertEqual(len(case.failures), 1)
        self.assertIn('different half', case.failures[0])
        self.assertTrue(case.owner.closed)
