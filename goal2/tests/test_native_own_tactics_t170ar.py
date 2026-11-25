"""[designed: T170ar] Live own tactics through verified bench decisions."""

import unittest
from types import SimpleNamespace
from unittest.mock import Mock

from goal2.game.season_worker import SeasonRequestError, SeasonWorker
from goal2.tests import pypy_engine, requires
from goal2.tests.test_prematch_preview_t170s import reference_raw


class Protocol(unittest.TestCase):
    def test_single_exact_own_tactic(self):
        for context, flag in (('half_time', 'half_time_edit'), ('substitution', 'substitution_edit')):
            worker = SeasonWorker()
            match = Mock(waiting=dict(context=context, substitutions_now=True, eleven=[11], bench=[12, 0]))
            worker.session = SimpleNamespace(pending_match=match)
            worker.decision = 7
            request = dict(op='season', action='answer', request=1, decision=7, **{flag: True})
            for malformed in ({12: {1: 0}}, {12: {5: True}}, {0: {1: None}},
                              {True: {1: False}}, {12: {True: False}}, {12: {1: False, 2: True}},
                              {13: {1: False}}, {12: {'01': True}}):
                with self.assertRaises(SeasonRequestError):
                    worker.dispatch(dict(request, answer={'edit_only': True, 'own_tactics': malformed}))
                self.assertEqual(worker.decision, 7)
            match.answer.assert_not_called()
            worker.dispatch(dict(request, answer={'edit_only': True, 'own_tactics': {'12': {'1': None}}}))
            self.assertIsNone(worker.decision)


@requires.need(modules=('PySide6',), files=('GOAL.DAT',))
class Window(unittest.TestCase):
    def test_existing_editor_awaits_confirmed_data_under_help_at_both_stops(self):
        for context, flag in (('half_time', 'half_time_edit'), ('substitution', 'substitution_edit')):
            with self.subTest(context=context):
                self.exercise(context, flag)

    def exercise(self, context, flag):
        from PySide6.QtCore import Qt
        from PySide6.QtTest import QTest
        from goal2.data.goaldat import load
        from goal2.engine.original_match.image import COUNTRIES_PTR, COUNTRY_SIZE, Image, PLAYERS_PTR, PLAYER_SIZE
        from goal2.game import engine_tables
        from goal2.game.season import canonical_hash
        from goal2.tests.test_native_driver_t170ac import event
        from goal2.tests.test_native_opportunity_t170am import sample
        from goal2.tests.test_native_pitch_t170ad import WindowControls
        from goal2.tests.test_stopped_view_t170af import respond
        from goal2.tests.ui_assertions import assert_fits
        from goal2.ui.s09_player_tactics import PlayerTacticsScreen
        from goal2.ui.s22_help import HelpScreen

        WindowControls.setUpClass()
        case = WindowControls('test_quick_never_answers_decisions_and_delivers_once')
        case.half_time_controls = context == 'half_time'
        case.substitution_controls = context == 'substitution'
        self.addCleanup(case.doCleanups)
        case.setUp()
        case.model.goaldat = load((requires.CACHE / 'GOAL.DAT').read_bytes())
        case.owner.managed_country = 7

        packet = sample(False)
        tables = engine_tables.load()
        image = Image.from_state(packet['state'], tables)
        word = packet['data']['eleven'][1]
        record = image.far(PLAYERS_PTR) + PLAYER_SIZE * word
        data = packet['data']
        vacant = image.far(COUNTRIES_PTR) + COUNTRY_SIZE * 7 + 38
        image.memory[vacant:vacant + 2] = b'\0\0'
        removed = data['bench'][-1]
        data['bench'][-1] = 0
        data['positions'] = [pair for pair in data['positions'] if pair[0] != removed]

        def stage(number, own):
            image.memory[record + 15] = own
            players = image.players()
            data.update(context=context, edited=number > 3,
                        player_records=[[w, players[w].hex()] for w in data['eleven'] + data['bench'] if w])
            packet['state'] = image.state(tables)
            packet['preview'].update(decision=number, state_hash=canonical_hash(packet['state']),
                                      data_hash=canonical_hash(data))
            case.owner.batch(events=[event('decision', data)], decision=number, total=number + 1)
            case.tick()
            respond(case.owner, packet)
            case.tick()

        case.tick()
        stage(3, 0)
        bench = case.win.current()
        case.key(Qt.Key.Key_Right)
        self.assertFalse(bench.own_tactics.isEnabled())
        case.key(Qt.Key.Key_T)
        self.assertIs(case.win.current(), bench)
        case.key(Qt.Key.Key_Left)
        QTest.mouseClick(bench.roster.rows[-1], Qt.MouseButton.LeftButton)
        self.assertFalse(bench.own_tactics.isEnabled())
        QTest.mouseClick(bench.roster.rows[1], Qt.MouseButton.LeftButton)
        case.key(Qt.Key.Key_T)
        editor = case.win.current()
        self.assertIsInstance(editor, PlayerTacticsScreen)
        self.assertEqual(editor.word, word)
        self.assertEqual(len(editor.rows), 4)
        assert_fits(self, case.win)

        old = editor.lines()
        case.key(Qt.Key.Key_Return)
        QTest.mouseClick(editor.rows[0], Qt.MouseButton.LeftButton)
        self.assertEqual(editor.lines(), old)
        self.assertEqual(case.owner.sent[-1], ('answer', {
            'decision': 3, flag: True, 'answer': {'edit_only': True, 'own_tactics': {word: {1: False}}}}))
        self.assertEqual(sum(action == 'answer' for action, _ in case.owner.sent), 1)
        case.key(Qt.Key.Key_F1)
        case.owner.reply('answer')
        case.tick()
        stage(4, 16)
        self.assertIsInstance(case.win.current(), HelpScreen)
        self.assertFalse(editor.pending)
        self.assertTrue(editor.lines()[0][1].endswith(' P'))
        case.key(Qt.Key.Key_Escape)

        QTest.mouseClick(editor.rows[0], Qt.MouseButton.LeftButton)
        self.assertEqual(case.owner.sent[-1][1]['answer']['own_tactics'], {word: {1: True}})
        case.owner.number += 1
        case.owner.queue.put(('season_error', dict(request=case.owner.number, error='Refused.', lost=False)))
        case.tick()
        self.assertEqual(case.owner.sent[-1], ('stopped_preview', {'decision': 4}))
        respond(case.owner, packet)
        case.tick()
        self.assertFalse(editor.pending)
        self.assertEqual(editor.message, 'Refused.')
        case.key(Qt.Key.Key_Escape)
        self.assertIs(case.win.current(), bench)
        self.assertEqual(bench.players[bench.row], word)
        case.key(Qt.Key.Key_Return)
        self.assertEqual(case.owner.sent[-1], ('answer', {'decision': 4, 'answer': {}}))
        case.owner.reply('answer')
        case.tick()
        self.assertIs(case.win.current(), case.screen)
        self.assertEqual(case.failures, [])


def actual_own_tactics(raw):
    from dataclasses import asdict
    import sys

    from goal2.engine.original_match import Match
    from goal2.engine.original_match.machine import MEM_SIZE, REGS, Uc
    from goal2.tests.test_native_opportunity_t170am import reach_requested_opportunity

    assert sys.implementation.name == 'pypy' and Uc is None
    worker, ask, opportunity, _ = reach_requested_opportunity(raw)
    match = worker.session.pending_match
    ask('answer', decision=opportunity, answer={'opportunity': 'accept'}, choice_answer=True)
    batch = ask('next', count=32)
    data = batch['events'][-1]['data']
    assert data['context'] == 'substitution' and data['substitutions_now']
    word = data['bench'][1]
    assert word
    baseline = Match.load(match.save())
    direct = iter(baseline.events())
    for desired in (False, True, None):
        number = batch['decision']
        saved = match.save()
        answer = {'edit_only': True, 'own_tactics': {word: {1: desired}}}
        for stale, bad in ((number - 1, answer), (number, dict(answer, own_tactics={word: {1: 0}}))):
            try:
                ask('answer', decision=stale, answer=bad, substitution_edit=True)
            except SeasonRequestError:
                assert worker.decision == number and match.save() == saved
            else:
                raise AssertionError('Invalid live tactic consumed the stop')
        baseline.answer(**answer)
        ask('answer', decision=number, answer=answer, substitution_edit=True)
        batch = ask('next', count=32)
        events = []
        for event in direct:
            events.append(asdict(event))
            if event.kind == 'decision':
                break
        assert batch['events'] == events and not batch['frames'] and batch['decision'] > number
        assert match.m.read(0, MEM_SIZE) == baseline.m.read(0, MEM_SIZE)
        assert [match.m.reg(reg) for reg in REGS] == [baseline.m.reg(reg) for reg in REGS]
        data = batch['events'][-1]['data']
        assert data['context'] == 'substitution' and data['edited'] is True
        packet = ask('stopped_preview', decision=batch['decision'])
        byte = bytes.fromhex(dict(packet['data']['player_records'])[word])[15]
        assert (bool(byte & 1) if byte & 16 else None) is desired
    return True


class Actual(unittest.TestCase):
    def test_false_true_and_inherit_match_direct_sdk(self):
        self.assertTrue(pypy_engine.call(__name__ + ':actual_own_tactics', reference_raw()))
