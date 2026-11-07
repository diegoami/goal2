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


    def test_real_bridge_admits_only_tactical_edits_at_non_substitution_stops(self):
        from goal2.game.watched_jobs import WatchedJobs
        def prepared(context, allowed):
            jobs = object.__new__(WatchedJobs)
            jobs.waiting = SimpleNamespace(data={'context': context, 'substitutions_now': allowed})
            jobs._decisions = 7
            jobs._check_token = lambda token: None
            calls = []
            engine = SimpleNamespace(answer=lambda number, pairs, changes=None: calls.append((number, pairs, changes)))
            jobs._command = lambda token, send: send(engine)
            return jobs, calls
        for context, allowed in [('pause', False), ('extra_time', False), ('half_time', True)]:
            jobs, calls = prepared(context, allowed)
            changes = {'tactics': {5: False, 8: True}, 'edit_only': True}
            jobs.answer('token', [], changes)
            self.assertEqual(calls, [(7, [], changes)])
            self.assertIsNone(jobs.waiting)
            self.assertEqual(jobs._decisions, 8)
            with self.assertRaises(ValueError): jobs.answer('token', [], changes)
        for context in ('pause', 'extra_time'):
            for pairs, extra in [([(11, 12)], {}), ([], {'positions': {11: 2}}),
                                  ([], {'own_tactics': {11: {1: True}}}), ([], {'marking': {11: 12}})]:
                jobs, calls = prepared(context, False)
                waiting = jobs.waiting
                with self.assertRaises(ValueError):
                    jobs.answer('token', pairs, dict(tactics={5: True}, edit_only=True, **extra))
                self.assertIs(jobs.waiting, waiting)
                self.assertEqual(jobs._decisions, 7)
                self.assertEqual(calls, [])


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
        self.assertIn("Applying", screen.enter_hint_text())
        from goal2.desktop import fixed_page
        self.assertEqual(fixed_page.problems(self.window), [])
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
            from goal2.desktop import fixed_page
            self.assertEqual(fixed_page.problems(self.window), [])
            self.assertEqual(len(self.sent), row+1)
        self.key(Qt.Key.Key_Escape)
        reopened = self.open_tactics()
        self.assertEqual(reopened.answer.team_tactics, byte)
        self.assertEqual(self.model.state.country_tactics, self.original_tactics)
        self.key(Qt.Key.Key_Escape)
        self.key(Qt.Key.Key_Escape)
        self.assertIs(self.window.current(), self.pitch)
        self.assertEqual(self.sent[-1], ([], None))

    def test_managed_tactics_work_from_both_home_and_away_menu_columns(self):
        from dataclasses import replace
        from PySide6.QtCore import Qt
        from goal2.ui.s15_match_menu import MenuScreen
        self.prepare('half_time')
        fixture = self.day.fixture
        seen = set()
        byte = self.original_tactics
        for current in (fixture, replace(fixture, home_country=fixture.away_country, away_country=fixture.home_country)):
            self.window.pop()
            self.day.fixture = current
            self.menu = self.window.push(MenuScreen(self.window, self.day, 'half'))
            seen.add(self.model.state.managed_country == self.menu.away_country)
            screen = self.open_tactics()
            self.key(Qt.Key.Key_Return)
            byte ^= 16
            self.deliver(byte)
            self.assertEqual(screen.answer.team_tactics, byte)
            self.key(Qt.Key.Key_Escape)
            self.assertIs(self.window.current(), self.menu)
        self.assertEqual(seen, {False, True})

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

    def test_pending_mouse_back_obeys_the_same_wait_as_keyboard(self):
        from PySide6.QtCore import Qt
        from PySide6.QtTest import QTest
        from PySide6.QtWidgets import QLabel
        self.prepare('half_time')
        screen = self.open_tactics()
        self.key(Qt.Key.Key_Return)
        esc = next(screen.key_layout.itemAt(i).widget() for i in range(screen.key_layout.count())
                   if any(label.text() == 'Esc' for label in screen.key_layout.itemAt(i).widget().findChildren(QLabel)))
        QTest.mouseClick(esc, Qt.MouseButton.LeftButton)
        self.app.processEvents()
        self.assertIs(self.window.current(), screen)
        self.assertTrue(screen.pending)
        self.deliver(self.original_tactics ^ 16)
        QTest.mouseClick(esc, Qt.MouseButton.LeftButton)
        self.app.processEvents()
        self.assertIs(self.window.current(), self.menu)

    def test_worker_failure_while_pending_returns_to_the_desk_without_publishing(self):
        from PySide6.QtCore import Qt
        self.prepare()
        screen = self.open_tactics()
        count = self.model.state.match_count
        self.key(Qt.Key.Key_Return)
        self.assertTrue(screen.pending)
        def fail(token): raise RuntimeError('authored worker failure')
        self.bridge.poll = fail
        self.pitch.tick()
        self.app.processEvents()
        self.assertEqual(type(self.window.current()).__name__, 'DeskScreen')
        self.assertEqual(self.model.state.match_count, count)
        self.assertIn('authored worker failure', self.controller.error)

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




@requires.need(modules=('PySide6', 'pygame', 'unicorn'), slow=True, **requires.HALFTIME)
class ActualLiveTeamTactics(unittest.TestCase):
    """Real window/worker journey; packet tests above make no original-outcome claim."""

    def run_journey(self, target):
        import json
        import os
        import tempfile
        from pathlib import Path
        from PySide6.QtCore import Qt
        from goal2.desktop import data_setup, fixed_page
        from goal2.ui.window import Window
        from goal2.ui.s17_pitch import engine_fixture, REQUESTED
        from goal2.ui.s10_team_tactics import LINES
        from goal2.tests.test_ui_bench_t180 import Walk, app, career, key, enter_on, play_on, PLAY_NEXT, pump
        from goal2.tests.match_day_policy import play_through_bridge
        from goal2.tests.test_pypy_worker_t152 import pypy
        pypy()
        application = app()
        test = self
        evidence = os.environ.get('GOAL2_TACTICS_EVIDENCE')
        def shot(window, name):
            if evidence:
                folder = Path(evidence)
                folder.mkdir(parents=True, exist_ok=True)
                path = folder / (target + '-' + name + '.png')
                if path.exists(): raise AssertionError('refuse to overwrite prior screenshot')
                window.grab().save(str(path))

        class TacticsWalk(Walk):
            def playing(self, pitch):
                super().playing(pitch)
                frame = pitch.controller.display.frame
                if (target == 'pause' and frame is not None and frame['minute'] >= 5
                        and not self.out.get('requested')):
                    before_requests = pitch.controller.requests
                    key(self.window, Qt.Key.Key_Escape)
                    self.out['requested'] = pitch.controller.requests > before_requests

            def on_menu(self, screen):
                wanted = 'pause' if target == 'pause' else 'half'
                if screen.phase == wanted and not self.out.get('tactics_done'):
                    controller = self.out['controller']
                    test.assertNotEqual(controller.note, REQUESTED)
                    before = self.day_state()
                    shot(self.window, 'menu')
                    key(self.window, Qt.Key.Key_T)
                    editor = self.window.current()
                    test.assertEqual(type(editor).__name__, 'TeamTacticsScreen')
                    original = editor.answer.team_tactics
                    byte = original
                    choices = len(controller.choices)
                    for row, (_, element) in enumerate(LINES):
                        test.assertEqual(editor.line, row)
                        key(self.window, Qt.Key.Key_Return)
                        if row == 0 and editor.pending: shot(self.window, 'pending')
                        pump(lambda: not editor.pending or controller.error, 60, 'original did not confirm team tactic')
                        test.assertIsNone(controller.error)
                        test.assertEqual(len(controller.choices), choices + row + 1, editor.message)
                        test.assertEqual(editor.message, '')
                        byte ^= 1 << (element - 1)
                        test.assertEqual(editor.answer.team_tactics, byte)
                        test.assertEqual(controller.stop.data['tactics'], byte)
                        test.assertTrue(controller.stop.data['edited'])
                        test.assertEqual(before, self.day_state())
                        test.assertEqual(len(controller.choices), choices + row + 1)
                        test.assertEqual(fixed_page.problems(self.window), [])
                        if row != len(LINES)-1: key(self.window, Qt.Key.Key_Down)
                    shot(self.window, 'confirmed')
                    key(self.window, Qt.Key.Key_Escape)
                    test.assertIs(self.window.current(), screen)
                    key(self.window, Qt.Key.Key_T)
                    test.assertEqual(self.window.current().answer.team_tactics, byte)
                    key(self.window, Qt.Key.Key_Escape)
                    self.out['tactics_done'] = True
                    self.out['actual'] = dict(initial=original, confirmed=byte, edits=8, stop=target, unchanged=before)
                    key(self.window, Qt.Key.Key_Escape)
                    test.assertEqual(type(self.window.current()).__name__, 'PitchScreen')
                    test.assertIsNone(controller.stop)
                    test.assertNotEqual(controller.note, REQUESTED)
                    test.assertEqual(len(controller.choices), choices + 9)
                    return
                if screen.phase == 'stop' and any(w in self.window.match_day.bench.injured for w in self.window.match_day.bench.eleven):
                    key(self.window, Qt.Key.Key_Space)
                else:
                    play_on(self.window, screen)

            def day_state(self):
                controller = self.out['controller']
                answer = self.window.match_day.bench
                return dict(minute=answer.minute, score=answer.score, eleven=answer.eleven,
                            bench=answer.bench, left=answer.left, frames=controller.bridge._frame_sequence)

            def on_bench(self, screen):
                answer = screen.answer
                injured = [w for w in answer.eleven if w in answer.injured]
                if answer.takes_substitutions and answer.left and injured:
                    off = injured[0]
                    used = set(self.out.get('taken_off', []))
                    on = next(w for w in answer.bench if w not in used and
                              (answer.position(w) == 0) == (answer.position(off) == 0))
                    enter_on(self.window, screen, off)
                    enter_on(self.window, screen, on)
                    test.assertIn(on, screen.answer.eleven)
                    self.out.setdefault('taken_off', []).append(off)
                key(self.window, Qt.Key.Key_Escape)

        with tempfile.TemporaryDirectory() as folder:
            owner = career()
            count = owner.state.match_count
            window = Window(data_setup.paths(Path(folder)))
            window.resize(1440, 900)
            window.show()
            desk = window.open_career(owner)
            walk = TacticsWalk('live-team-tactics-' + target, window, owner)
            fixture = owner.state.campaign.next_fixture
            try:
                desk.highlight(PLAY_NEXT)
                key(window, Qt.Key.Key_Return)
                walk.run()
                controller = walk.out['controller']
                test.assertTrue(walk.out.get('tactics_done'))
                test.assertIsNone(controller.error)
                test.assertEqual(owner.state.match_count, count + 1)
                test.assertTrue(all(not r['requested'] for r in controller.reports))
                if target == 'half_time':
                    other = career()
                    other.state = copy.deepcopy(controller.given._snapshot)
                    result = play_through_bridge(other, controller.choices, fixture=engine_fixture(fixture), wait=1500)
                    test.assertEqual(controller.outcome.result, result.result)
                    test.assertEqual(controller.outcome.memory, result.memory)
                    test.assertEqual(controller.outcome.events, result.events)
                    test.assertEqual(owner.state, other.state)
                print('ACTUAL_UI_TACTICS ' + json.dumps(dict(target=target, edits=8, published_once=True,
                    commands=controller.choices, actual=walk.out['actual'],
                    headless_full_memory_events_result_state_equal=target == 'half_time')), flush=True)
            finally:
                window.close()
                window.deleteLater()
                application.processEvents()

    def test_half_time_all_flags_confirm_before_play_and_match_headless_publication(self):
        self.run_journey('half_time')

    def test_requested_pause_all_flags_confirm_and_esc_returns_to_the_pitch(self):
        self.run_journey('pause')


if __name__ == '__main__': unittest.main()
