"""Owner610/612: real Qt journeys, with packet-only engine replies isolated here."""
import copy
from types import SimpleNamespace
import unittest
from goal2.tests import requires


class TacticTransport(unittest.TestCase):
    def test_all_eight_flag_changes_retain_false_and_reject_invalid_shapes(self):
        from goal2.game.watched_jobs import _changes
        self.assertEqual(_changes({'tactics': {'1': True, '8': False}}), {'tactics': {1: True, 8: False}})
        for value in ({'0': True}, {'9': True}, {'1': 1}, {'1': None}, {'x': False}):
            with self.subTest(value=value), self.assertRaises(ValueError):
                _changes({'tactics': value})


@requires.need(modules=('PySide6', 'pygame'), **requires.HALFTIME)
class LiveTeamTactics(unittest.TestCase):
    def setUp(self):
        from goal2.tests.test_ui_replay_t181 import ReplayScreens
        ReplayScreens.setUp(self)
        self.sent = []
        self.bridge.reports = []
        self.bridge.answer = lambda token, pairs, changes=None: self.sent.append((copy.deepcopy(pairs), copy.deepcopy(changes)))

    def key(self, key):
        from PySide6.QtTest import QTest
        QTest.keyClick(self.app.focusWidget() or self.window, key)
        self.app.processEvents()

    def prepare(self, context='pause'):
        from goal2.ui.s19_bench import BenchAnswer
        from goal2.ui.s15_match_menu import MenuScreen
        words = self.model.state.managed_squad
        self.original_tactics = self.model.state.country_tactics
        self.decision = SimpleNamespace(minute=30 if context == 'pause' else 45, score=[0,0], data=dict(
            context=context, eleven=words[:11], bench=words[11:], substitutions_now=context == 'half_time',
            substitutions_left=5, tactics=self.original_tactics, positions=[[w,self.model.state.players[w][6]] for w in words]))
        self.controller.stop = self.decision
        self.pitch.held = self.decision
        if context == 'pause':
            self.day.stop(self.pitch, self.decision)
        else:
            self.day.bench = BenchAnswer(self.model, self.decision)
            self.window.push(MenuScreen(self.window, self.day, 'half' if context == 'half_time' else 'extra'))
        self.assertIsInstance(self.window.current(), MenuScreen)
        self.menu = self.window.current()

    def open_tactics(self):
        from PySide6.QtCore import Qt
        from goal2.ui.s10_team_tactics import TeamTacticsScreen
        self.key(Qt.Key.Key_T)
        self.assertIsInstance(self.window.current(), TeamTacticsScreen)
        return self.window.current()

    def deliver(self, byte):
        data = copy.deepcopy(self.decision.data)
        data.update(edited=True, tactics=byte)
        self.decision = SimpleNamespace(data=data, minute=self.decision.minute, score=[0,0])
        self.bridge.waiting = self.decision
        self.pitch.tick()
        self.app.processEvents()

    def test_pause_edits_are_confirmed_before_esc_resumes_without_resubmission(self):
        from PySide6.QtCore import Qt
        self.prepare()
        screen = self.open_tactics()
        self.key(Qt.Key.Key_Return)  # first row is team element5
        expected = not bool(self.original_tactics & 16)
        self.assertEqual(self.sent, [([], {'tactics': {5: expected}, 'edit_only': True})])
        self.assertTrue(screen.pending)
        self.assertEqual(self.model.state.country_tactics, self.original_tactics)
        self.key(Qt.Key.Key_Return)
        self.key(Qt.Key.Key_Escape)
        self.assertIs(self.window.current(), screen)
        self.assertEqual(len(self.sent), 1)
        self.deliver(self.original_tactics ^ 16)
        self.assertFalse(screen.pending)
        self.assertEqual(self.day.bench.team_tactics, self.original_tactics ^ 16)
        self.assertEqual(self.model.state.country_tactics, self.original_tactics)
        self.key(Qt.Key.Key_Escape)
        self.assertIs(self.window.current(), self.menu)
        self.key(Qt.Key.Key_Escape)
        self.assertIs(self.window.current(), self.pitch)
        self.assertEqual(self.sent[-1], ([], None))
        self.assertEqual(len(self.sent), 2)

    def test_half_time_all_eight_flags_apply_and_reopen_from_actual_reply(self):
        from PySide6.QtCore import Qt
        from goal2.ui.s10_team_tactics import LINES
        self.prepare('half_time')
        screen = self.open_tactics()
        byte = self.original_tactics
        for row, (_, element) in enumerate(LINES):
            screen.choose(row)
            self.key(Qt.Key.Key_Return)
            byte ^= 1 << (element-1)
            self.assertTrue(screen.pending)
            self.deliver(byte)
            self.assertEqual(screen.answer.team_tactics, byte)
            self.assertEqual(len(self.sent), row+1)
        self.key(Qt.Key.Key_Escape)
        reopened = self.open_tactics()
        self.assertEqual(reopened.answer.team_tactics, byte)
        self.assertEqual(self.model.state.country_tactics, self.original_tactics)
        self.key(Qt.Key.Key_Escape)
        self.key(Qt.Key.Key_Escape)
        self.assertIs(self.window.current(), self.pitch)
        self.assertEqual(self.sent[-1], ([], None))

    def test_extra_time_tactics_are_editable_without_creating_substitution_pairs(self):
        from PySide6.QtCore import Qt
        self.prepare('extra_time')
        screen = self.open_tactics()
        self.key(Qt.Key.Key_Return)
        self.assertEqual(self.sent, [([], {'tactics': {5: not bool(self.original_tactics & 16)}, 'edit_only': True})])
        self.deliver(self.original_tactics ^ 16)
        self.assertFalse(screen.pending)

    def test_team_reply_preserves_pending_personal_changes_and_live_roster(self):
        from PySide6.QtCore import Qt
        self.prepare('half_time')
        player = self.day.bench.eleven[3]
        self.day.bench.own[player] = self.model.state.players[player][15] ^ 17
        self.day.bench.positions[player] = (self.day.bench.position(player) + 1) % 14
        own, positions = dict(self.day.bench.own), dict(self.day.bench.positions)
        screen = self.open_tactics()
        self.key(Qt.Key.Key_Return)
        self.deliver(self.original_tactics ^ 16)
        self.assertEqual(self.day.bench.own, own)
        self.assertEqual(self.day.bench.positions, positions)
        self.assertEqual(self.day.bench.eleven, self.decision.data['eleven'])
        self.assertNotIn('own_tactics', self.sent[0][1], 'team edit must not silently consume personal drafts')
        self.assertIn('own_tactics', self.day.bench.value())

    def test_failed_submission_and_unaccepted_reply_never_claim_a_change(self):
        from PySide6.QtCore import Qt
        self.prepare('half_time')
        screen = self.open_tactics()
        original = self.bridge.answer
        def fail(*args, **kwargs): raise ValueError('authored send failure')
        self.bridge.answer = fail
        self.key(Qt.Key.Key_Return)
        self.assertFalse(screen.pending)
        self.assertIn('not submitted', screen.note.text())
        self.assertIsNotNone(self.controller.stop)
        self.assertEqual(self.day.bench.team_tactics, self.original_tactics)
        self.bridge.answer = original
        self.key(Qt.Key.Key_Return)
        self.deliver(self.original_tactics)  # actual original kept its old flag
        self.assertIsNone(screen.changed)
        self.assertIn('did not accept', screen.note.text())
        self.assertEqual(screen.answer.team_tactics, self.original_tactics)

    def test_held_escape_cannot_fall_through_screens_and_request_another_pause(self):
        from PySide6.QtCore import Qt, QEvent
        from PySide6.QtGui import QKeyEvent
        self.prepare()
        self.open_tactics()
        self.key(Qt.Key.Key_Escape)
        repeat = QKeyEvent(QEvent.Type.KeyPress, Qt.Key.Key_Escape, Qt.KeyboardModifier.NoModifier, '', True)
        self.app.sendEvent(self.window, repeat)
        self.assertIs(self.window.current(), self.menu)
        self.assertEqual(self.sent, [])
        self.key(Qt.Key.Key_Escape)
        self.assertIs(self.window.current(), self.pitch)
        self.app.sendEvent(self.window, repeat)
        self.assertEqual(self.bridge.pauses, 0)
        self.key(Qt.Key.Key_Escape)
        self.assertEqual(self.bridge.pauses, 1)
        self.key(Qt.Key.Key_Escape)
        self.assertEqual(self.bridge.pauses, 1, 'coalesce while the original has not acknowledged the stop')

    def test_request_note_clears_when_the_engine_stop_arrives(self):
        from goal2.ui.s17_pitch import REQUESTED
        self.prepare()
        self.window.pop()  # back to pitch, still held in this isolated packet fixture
        self.controller.stop = None
        self.pitch.held = None
        self.controller.request_bench()
        self.assertEqual(self.controller.note, REQUESTED)
        self.bridge.waiting = self.decision
        self.pitch.tick()
        self.assertNotEqual(self.controller.note, REQUESTED)


if __name__ == '__main__': unittest.main()
