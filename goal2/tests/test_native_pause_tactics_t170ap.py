"""[designed: T170ap] Team tactics at a verified ordinary pause."""

import unittest
from types import SimpleNamespace
from unittest.mock import Mock

from goal2.game.season_worker import SeasonRequestError, SeasonWorker
from goal2.tests import pypy_engine, requires
from goal2.tests.test_prematch_preview_t170s import reference_raw


class Protocol(unittest.TestCase):
    def test_only_one_typed_tactic_can_share_the_pause_edit_mode(self):
        worker = SeasonWorker()
        match = Mock(waiting={'context': 'pause', 'substitutions_now': False,
                              'request_substitution': True})
        worker.session = SimpleNamespace(pending_match=match)
        worker.decision = 7
        request = dict(op='season', action='answer', request=1, decision=7, pause_edit=True)
        valid = {'edit_only': True, 'tactics': {'3': False}}
        for fields in ({'decision': 6}, {'answer': dict(valid, tactics={1: 1})},
                       {'answer': dict(valid, tactics={'1': True, '8': False})},
                       {'answer': dict(valid, substitutions=[[11, 12]])},
                       {'answer': dict(valid, request_substitution=False)}):
            with self.subTest(fields=fields), self.assertRaises(SeasonRequestError):
                worker.dispatch(dict(request, answer=valid) | fields)
            self.assertEqual(worker.decision, 7)
        match.answer.assert_not_called()
        worker.dispatch(dict(request, answer=valid))
        self.assertIsNone(worker.decision)
        match.answer.assert_called_once_with(edit_only=True, tactics={3: False})


@requires.need(modules=('PySide6',), files=('GOAL.DAT',))
class Window(unittest.TestCase):
    def setUp(self):
        from goal2.data.goaldat import load
        from goal2.engine.original_match.image import COUNTRIES_PTR, COUNTRY_SIZE, Image
        from goal2.engine.original_match.screens import SUBS_ALLOWED, SUBS_REQUEST
        from goal2.game import engine_tables
        from goal2.tests.test_native_opportunity_t170am import sample
        from goal2.tests.test_native_pitch_t170ad import WindowControls

        WindowControls.setUpClass()
        self.case = WindowControls('test_quick_never_answers_decisions_and_delivers_once')
        self.case.pause_controls = True
        self.addCleanup(self.case.doCleanups)
        self.case.setUp()
        self.case.model.goaldat = load((requires.CACHE / 'GOAL.DAT').read_bytes())
        self.case.owner.managed_country = 7
        self.packet = sample(False)
        self.tables = engine_tables.load()
        self.image = Image.from_state(self.packet['state'], self.tables)
        ds = self.image.DS * 16
        self.image.memory[ds + SUBS_ALLOWED] = 0
        self.image.memory[ds + SUBS_REQUEST] = 1
        self.tactics_at = self.image.far(COUNTRIES_PTR) + 7 * COUNTRY_SIZE + 0x2D
        self.data = self.packet['data']
        self.data.update(context='pause', substitutions_now=False, request_substitution=True)
        self.case.tick()
        self.decision(3)
        self.pause = self.case.win.current()
        self.read()

    def decision(self, number, bit=0):
        from goal2.game.season import canonical_hash
        from goal2.tests.test_native_driver_t170ac import event

        self.image.memory[self.tactics_at] ^= bit
        self.data.update(tactics=self.image.memory[self.tactics_at], edited=bool(bit))
        state = self.image.state(self.tables)
        self.packet['state'] = state
        self.packet['preview'].update(decision=number, state_hash=canonical_hash(state),
                                      data_hash=canonical_hash(self.data))
        self.case.owner.batch(events=[event('decision', self.data)], decision=number, total=number + 1)
        self.case.tick()

    def read(self):
        from goal2.tests.test_stopped_view_t170af import respond
        respond(self.case.owner, self.packet)
        self.case.tick()

    def test_open_edit_and_repair_from_fresh_current_records_before_play(self):
        from PySide6.QtCore import Qt
        from PySide6.QtTest import QTest
        from goal2.tests.ui_assertions import assert_fits
        from goal2.ui.s10_team_tactics import TeamTacticsScreen
        from goal2.ui.s22_help import HelpScreen

        case = self.case
        case.key(Qt.Key.Key_Right)
        self.assertFalse(self.pause.tactics_button.isEnabled())
        case.key(Qt.Key.Key_Left)
        case.key(Qt.Key.Key_T)
        editor = case.win.current()
        self.assertIsInstance(editor, TeamTacticsScreen)
        self.assertEqual(editor.answer.words(), self.data['eleven'] + self.data['bench'])
        self.assertEqual(editor.answer.team_tactics, self.data['tactics'])
        self.assertEqual(editor.answer.live_records, {
            word: bytes.fromhex(value) for word, value in self.data['player_records']})
        assert_fits(self, case.win)

        before = editor.lines()[0][1]
        desired = not bool(self.data['tactics'] & 16)
        case.key(Qt.Key.Key_Return)
        case.key(Qt.Key.Key_Return)
        sent = ('answer', {'decision': 3, 'pause_edit': True,
                           'answer': {'edit_only': True, 'tactics': {5: desired}}})
        self.assertEqual(case.owner.sent[-1], sent)
        self.assertEqual(case.owner.sent.count(sent), 1)
        case.key(Qt.Key.Key_F1)
        self.assertIsInstance(case.win.current(), HelpScreen)
        case.owner.reply('answer')
        case.tick()
        self.assertEqual(case.owner.sent[-1], ('next', {'count': 32}))
        self.decision(4, 16)
        self.read()
        self.assertIsInstance(case.win.current(), HelpScreen)
        self.assertFalse(editor.pending)
        self.assertNotEqual(editor.lines()[0][1], before)
        self.assertEqual(editor.answer.team_tactics, self.data['tactics'])
        self.assertTrue(editor.answer.substitution_requested)
        case.key(Qt.Key.Key_Escape)

        row = editor.rows[1]
        QTest.mouseClick(row, Qt.MouseButton.LeftButton)
        QTest.mouseClick(row, Qt.MouseButton.LeftButton)
        self.assertEqual(case.owner.sent[-1][1]['answer']['tactics'],
                         {6: not bool(self.data['tactics'] & 32)})
        case.owner.number += 1
        case.owner.queue.put(('season_error', dict(request=case.owner.number, error='The tactic was refused.', lost=False)))
        case.tick()
        self.assertTrue(editor.pending)
        self.assertEqual(case.owner.sent[-1], ('stopped_preview', {'decision': 4}))
        self.read()
        self.assertFalse(editor.pending)
        self.assertEqual(editor.message, 'The tactic was refused.')
        self.assertEqual(editor.answer.team_tactics, self.data['tactics'])

        case.key(Qt.Key.Key_Escape)
        self.assertIs(case.win.current(), self.pause)
        self.assertEqual(self.pause.request_button.text(), 'Cancel request')
        case.key(Qt.Key.Key_Return)
        self.assertEqual(case.owner.sent[-1], ('answer', {'decision': 4, 'answer': {}}))
        case.owner.reply('answer')
        case.tick()
        self.assertIs(case.win.current(), case.screen)
        self.assertEqual(case.decisions, [])
        self.assertEqual(case.failures, [])

    def test_window_close_during_tactic_edit_disposes_the_same_owner(self):
        from PySide6.QtCore import Qt

        case = self.case
        case.key(Qt.Key.Key_T)
        case.key(Qt.Key.Key_Return)
        self.assertTrue(self.pause.tactics_editor.pending)
        self.assertEqual(case.owner.sent[-1][0], 'answer')
        case.win.leaving = True
        case.win.close()
        self.assertTrue(case.owner.closed)
        self.assertFalse(case.screen.timer.isActive())
        self.assertEqual(sum(action == 'answer' for action, _ in case.owner.sent), 1)


def actual_pause_tactic(raw):
    from dataclasses import asdict
    import sys

    from goal2.engine.original_match import Match
    from goal2.engine.original_match.machine import MEM_SIZE, REGS, Uc
    from goal2.game.stopped_snapshot import StoppedMatchSnapshot
    from goal2.game.watched_pitch import snapshot
    from goal2.tests.test_native_pause_t170al import reach_pause

    assert sys.implementation.name == 'pypy' and sys.version_info[:2] == (3, 11) and Uc is None
    worker, ask, initial = reach_pause(raw)
    match = worker.session.pending_match
    ask('answer', decision=initial['decision'],
        answer={'edit_only': True, 'request_substitution': True}, pause_edit=True)
    armed = ask('next', count=32)
    number = armed['decision']

    def read(batch):
        current = batch['decision']
        data = batch['events'][-1]['data']
        packet = ask('stopped_preview', decision=current)
        return StoppedMatchSnapshot.from_packet(packet, request=packet['request'], decision=current,
                                                managed_country=match.opts['managed'], data=data)

    before = read(armed)
    assert before.data['request_substitution'] is True and before.data['substitutions_now'] is False
    saved = match.save()
    desired = not bool(before.data['tactics'] & 16)
    answer = {'edit_only': True, 'tactics': {5: desired}}
    for decision, invalid in ((number - 1, answer), (number, dict(answer, tactics={5: 1})),
                              (number, dict(answer, request_substitution=False))):
        try:
            ask('answer', decision=decision, answer=invalid, pause_edit=True)
        except SeasonRequestError:
            assert worker.decision == number and match.save() == saved
        else:
            raise AssertionError('Invalid paused tactic consumed the decision')

    baseline = Match.load(saved)
    direct = iter(baseline.events())

    def compare_next():
        sequence, watermark = worker.frame_sequence, worker.event_count
        batch = ask('next', count=32)
        events, frames = [], []
        for index, event in enumerate(direct, 1):
            if event.kind == 'tick':
                frames.append(snapshot(baseline, event, sequence + len(frames), watermark + len(events)))
            else:
                events.append(asdict(event))
            if event.kind == 'decision' or index == 32:
                break
        assert batch['events'] == events and batch['frames'] == frames
        assert match.m.read(0, MEM_SIZE) == baseline.m.read(0, MEM_SIZE)
        assert [match.m.reg(reg) for reg in REGS] == [baseline.m.reg(reg) for reg in REGS]
        assert worker.session.pending_match is match
        return batch

    baseline.answer(**answer)
    ask('answer', decision=number, answer=answer, pause_edit=True)
    edited = compare_next()
    after = read(edited)
    assert edited['decision'] > number and not edited['frames'] and after.data['edited'] is True
    assert after.context == 'pause' and after.data['tactics'] == before.data['tactics'] ^ 16
    assert after.data['request_substitution'] is True
    for field in ('eleven', 'bench', 'substitutions_left'):
        assert after.data[field] == before.data[field]

    baseline.answer()
    ask('answer', decision=edited['decision'], answer={})
    resumed = compare_next()
    assert resumed['frames']
    return dict(context=after.context, frames=len(resumed['frames']))


class Actual(unittest.TestCase):
    def test_actual_paused_tactic_and_play_match_direct_sdk_with_latch_on(self):
        result = pypy_engine.call(__name__ + ':actual_pause_tactic', reference_raw())
        self.assertEqual(result['context'], 'pause')
        self.assertGreater(result['frames'], 0)
