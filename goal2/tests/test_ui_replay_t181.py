"""[designed: T181, #575] Replay only recorded samples; named records survive changes to the career."""
import copy
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from goal2.tests import requires

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')


def frames(count=3):
    from goal2.tests.test_watched_pitch_jobs import sample
    rows = []
    for sequence in range(count):
        row = sample(sequence, 0)
        row['minute'] = sequence + 1
        rows.append(row)
    return rows


class RecordedSamples(unittest.TestCase):
    def test_keeps_a_bounded_independent_copy_of_only_painted_samples(self):
        from goal2.ui.replays import GoalWindow, WINDOW_FRAMES
        kept = GoalWindow()
        rows = frames(WINDOW_FRAMES + 2)
        for row in rows:
            kept.painted(row)
            kept.painted(row)  # a resize paints the same frame again
        self.assertEqual(kept.samples(), rows[-WINDOW_FRAMES:])
        rows[-1]['score'][0] = 123
        self.assertNotEqual(kept.samples()[-1]['score'][0], 123)

    def test_playback_waits_for_each_paint_and_preserves_every_sample(self):
        from goal2.ui.replays import Playback
        source = frames()
        replay = Playback(source)
        drawn = []
        self.assertTrue(replay.advance(0, 240))
        self.assertFalse(replay.advance(10, 240))  # stalled paint: never skip a sample
        while not replay.finished:
            drawn.append(copy.deepcopy(replay.frame))
            replay.painted(replay.frame['sequence'])
            replay.advance(10 + len(drawn), 240)
        self.assertEqual(drawn, source)
        self.assertEqual(source, frames())

    def test_records_are_named_atomic_and_read_without_current_career(self):
        from goal2.ui import replays
        goal = {'frames': frames(), 'countries': ['One', 'Two'], 'score': [0, 1], 'minute': 3,
                'scorer': 'A Player', 'kits': {'shirt': [1, 2], 'keeper': [3, 4]}, 'kind': 'FRIENDLY'}
        with tempfile.TemporaryDirectory() as folder:
            path = replays.write(folder, 'goal', 'The winner', goal)
            self.assertEqual(replays.read(path)['data'], goal)
            self.assertEqual(replays.entries(folder, 'goal')[0]['name'], 'The winner')
            before = path.read_bytes()
            with patch.object(replays.os, 'replace', side_effect=OSError('disk unavailable')):
                with self.assertRaises(replays.RecordError):
                    replays.write(folder, 'goal', 'The winner', goal)
            self.assertEqual(path.read_bytes(), before)
            self.assertEqual(replays.entries(folder, 'summary'), [])

    def test_read_refuses_damaged_frames_and_never_reads_original_goal_files(self):
        from goal2.ui import replays
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'bad.g2goal'
            path.write_text(json.dumps({'format': replays.FORMAT, 'version': 1, 'kind': 'goal', 'name': 'Bad',
                                        'data': {'frames': [{}]}}))
            with self.assertRaises(replays.RecordError):
                replays.read(path)
            original = Path(folder) / 'old.GL'
            original.write_bytes(b'not a goal2 record')
            self.assertEqual(replays.entries(folder, 'goal'), [])


@requires.need(modules=('PySide6', 'pygame'), **requires.HALFTIME)
class ReplayScreens(unittest.TestCase):
    """[designed: T181] Synthetic packets isolate the UI's questions/painting; no real match is played here."""
    def setUp(self):
        from goal2.tests.test_ui_match_day_t167 import app, career
        from goal2.ui.window import Window
        from goal2.desktop import data_setup
        from goal2.ui.match_day import for_window
        from goal2.ui.s17_pitch import MatchController, PitchScreen
        self.app = app()
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.window = Window(data_setup.paths(Path(self.temporary.name)))
        self.model = career()
        self.window.open_career(self.model)
        self.window.show()
        self.day = for_window(self.window, self.model)
        self.day.fixture = self.model.state.campaign.next_fixture
        self.day.watch = True
        class Bridge:
            busy = True
            closed = False
            waiting = None
            reports = []
            token = 'synthetic'
            def __init__(self):
                self.acks = []
                self.polls = 0
                self.pauses = 0
            def start(self, *args, **kwargs): return self.token
            def poll(self, token):
                self.polls += 1
                return []
            def poll_frames(self, token): return []
            def ack_frames(self, token, sequence): self.acks.append(sequence)
            def pause(self, token):
                self.pauses += 1
                return True
            def frames_drained(self): return True
            def cancel_and_reap(self, token): self.busy = False
            def close(self): self.busy = False; self.closed = True
        self.bridge = Bridge()
        self.controller = MatchController(self.model, self.day.fixture, self.bridge)
        self.controller.start()
        self.day.controller = self.controller
        self.pitch = self.window.push(PitchScreen(self.window, self.model, self.controller, self.day))
        self.pitch.timer.stop()
        self.day.pitch = self.pitch
        self.addCleanup(self.window.leave)
        self.addCleanup(self.pitch.timer.stop)

    def goal(self, *, automatic=False, quick=False):
        self.day.replay_auto = automatic
        self.controller.quick = quick
        event = {'kind': 'goal', 'minute': 3, 'score': [0, 1],
                 'data': {'team': 1, 'player': self.model.state.managed_squad[1]}}
        rows = frames()
        for i, row in enumerate(rows):
            if i == len(rows) - 1:
                self.controller._send('event', event)
                self.controller.events.append(event)
                row['watermark'] = 1
                row['score'] = [0, 1]
            self.controller.display.frame = copy.deepcopy(row)
            self.pitch.painted(row['sequence'])
        self.pitch.tick()
        return rows

    def play_replay(self):
        import time
        drawn = []
        now = time.monotonic() + 10
        while self.pitch.replay is not None:
            frame = self.pitch.replay.frame
            drawn.append(copy.deepcopy(frame))
            self.pitch.painted(frame['sequence'])
            now += 1
            self.pitch.replay_tick(now)
        return drawn

    def test_goal_questions_replay_exact_painted_samples_without_live_acknowledgements(self):
        from PySide6.QtCore import Qt
        rows = self.goal()
        self.assertEqual(self.pitch.stop_box.kind, 'replay')
        self.assertIn('action replay?', self.pitch.stop_box.headline.text())
        self.pitch.answer_stop_box(Qt.Key.Key_Return)
        self.assertTrue(self.pitch.stop_box.open, 'only Y/N answers')
        self.pitch.answer_stop_box(Qt.Key.Key_Y)
        self.assertEqual(self.pitch.result_binding.text, 'REPLAY')
        acks = list(self.bridge.acks)
        self.assertEqual(self.play_replay(), rows)
        self.assertEqual(self.bridge.acks, acks, 'replayed paints never acknowledge live samples')
        self.assertEqual(self.pitch.stop_box.kind, 'save-goal')
        self.pitch.answer_stop_box(Qt.Key.Key_N)
        self.assertIsNone(self.controller.goal)
        self.assertFalse(self.pitch.stop_box.open)

    def click_live_controls(self):
        from PySide6.QtCore import Qt
        from goal2.ui.screen import Clickable
        for item in self.pitch.key_bar.findChildren(Clickable, 'keyItem'):
            binding = getattr(item, 'binding', None)
            if binding is self.pitch.result_binding or (binding is not None and Qt.Key.Key_Escape in binding.keys):
                item.clicked.emit()  # the mouse callback bypasses handle_key
        self.pitch.enter_hint.clicked.emit()

    def test_keybar_mouse_callbacks_cannot_change_live_match_during_goal_questions(self):
        self.goal()
        held = self.controller.goal
        self.click_live_controls()
        self.assertEqual((self.controller.quick, self.bridge.pauses, self.controller.requests), (False, 0, 0))
        self.assertIs(self.controller.goal, held)
        self.assertEqual(self.bridge.acks, [])
        self.assertEqual(self.pitch.stop_box.kind, 'replay')
        from PySide6.QtCore import Qt
        self.pitch.answer_stop_box(Qt.Key.Key_N)
        self.assertEqual(self.pitch.stop_box.kind, 'save-goal')
        self.click_live_controls()
        self.assertEqual((self.controller.quick, self.bridge.pauses, self.controller.requests), (False, 0, 0))
        self.assertIs(self.controller.goal, held)
        self.assertEqual(self.bridge.acks, [])
        self.assertEqual(self.pitch.stop_box.kind, 'save-goal')

    def test_keybar_mouse_callbacks_cannot_change_live_match_during_replay(self):
        from PySide6.QtCore import Qt
        self.goal()
        held = self.controller.goal
        self.pitch.answer_stop_box(Qt.Key.Key_Y)
        self.assertIsNotNone(self.pitch.replay)
        self.click_live_controls()
        self.assertEqual((self.controller.quick, self.bridge.pauses, self.controller.requests), (False, 0, 0))
        self.assertIs(self.controller.goal, held)
        self.assertEqual(self.bridge.acks, [])
        self.assertIsNotNone(self.pitch.replay)
        self.assertEqual(self.pitch.result_binding.text, 'REPLAY')

    def test_final_sample_goal_questions_finish_before_live_ack_and_publication(self):
        from PySide6.QtCore import Qt
        from types import SimpleNamespace
        self.bridge.outcome = SimpleNamespace()
        final = {'acknowledged': False}
        def acknowledge(token, sequence):
            self.bridge.acks.append(sequence)
            final['acknowledged'] = True
        def poll(token):
            self.bridge.polls += 1
            if final['acknowledged']:
                self.bridge.busy = False
            return []
        with patch.object(self.bridge, 'ack_frames', side_effect=acknowledge), \
                patch.object(self.bridge, 'poll', side_effect=poll):
            rows = self.goal()
            self.assertFalse(self.controller.finished, 'publication cannot overtake the painted goal')
            self.assertEqual(self.pitch.stop_box.kind, 'replay')
            self.assertEqual(self.bridge.acks, [], 'goal question holds the live acknowledgement')
            self.assertEqual(self.bridge.polls, 0)
            self.pitch.tick()
            self.assertEqual(self.bridge.acks, [], 'the pending question stays held on later ticks')
            self.pitch.answer_stop_box(Qt.Key.Key_Y)
            self.assertEqual(self.play_replay(), rows)
            self.assertEqual(self.pitch.stop_box.kind, 'save-goal')
            self.pitch.tick()
            self.assertFalse(self.controller.finished)
            self.assertEqual(self.bridge.acks, [])
            self.pitch.answer_stop_box(Qt.Key.Key_N)
            self.pitch.tick()
            self.assertTrue(self.controller.finished)
            self.assertEqual(self.bridge.acks, [rows[-1]['sequence']])
            self.assertIs(self.controller.outcome, self.bridge.outcome)
            self.assertEqual(type(self.window.current()).__name__, 'BoardScreen')

    def test_automatic_replay_has_no_replay_question_and_quick_result_has_neither_question(self):
        from PySide6.QtCore import Qt
        rows = self.goal(automatic=True)
        self.assertFalse(self.pitch.stop_box.open)
        self.assertIsNotNone(self.pitch.replay)
        self.assertEqual(self.play_replay(), rows)
        self.pitch.answer_stop_box(Qt.Key.Key_N)
        self.controller.quick_result()
        self.goal(quick=True)
        self.assertIsNone(self.pitch.replay)
        self.assertFalse(self.pitch.stop_box.open)

    def test_r_after_paint_before_the_next_tick_discards_pending_goal(self):
        event = {'kind': 'goal', 'minute': 3, 'score': [0, 1],
                 'data': {'team': 1, 'player': self.model.state.managed_squad[1]}}
        self.controller.events.append(event)
        row = frames(1)[0]
        row['watermark'] = 1
        self.controller.display.frame = row
        self.pitch.painted(row['sequence'])
        self.assertIsNotNone(self.controller.goal)
        self.pitch.quick_result()
        self.pitch.tick()
        self.assertIsNone(self.controller.goal)
        self.assertFalse(self.controller.held)
        self.assertFalse(self.pitch.stop_box.open)
        self.assertIsNone(self.pitch.replay)

    def test_future_and_recalled_goal_events_do_not_open_a_question(self):
        from PySide6.QtCore import Qt
        event = {'kind': 'goal', 'minute': 3, 'score': [0, 1], 'data': {'team': 1, 'player': 0}}
        self.controller.events.append(event)
        row = frames(1)[0]
        row['watermark'] = 1
        self.controller.display.frame = row
        self.pitch.painted(row['sequence'])
        self.assertIsNone(self.controller.goal, 'a recalled goal is not a scored goal')
        event = {'kind': 'goal', 'minute': 4, 'score': [0, 1],
                 'data': {'team': 1, 'player': self.model.state.managed_squad[1]}}
        self.controller.events.append(event)
        self.pitch.painted(row['sequence'])
        self.assertIsNone(self.controller.goal, 'the future goal is ahead of this sample watermark')
        self.assertFalse(self.pitch.stop_box.open)

    def test_saved_goal_f3_name_menu_play_and_escape_keep_the_career_unchanged(self):
        from PySide6.QtCore import Qt
        from goal2.ui import replays
        rows = self.goal()
        before = copy.deepcopy(self.model.state)
        self.pitch.answer_stop_box(Qt.Key.Key_Y)
        self.assertEqual(self.play_replay(), rows)
        self.pitch.answer_stop_box(Qt.Key.Key_Y)
        name_box = self.window.current()
        name_box.field.set_text('The winning goal')
        name_box.save()
        saved = replays.entries(self.window.target.root / 'recordings', 'goal')
        self.assertEqual(saved[0]['name'], 'The winning goal')
        self.assertEqual(replays.read(saved[0]['path'])['data']['frames'], rows)
        self.window.pop()  # synthetic live pitch, back to desk
        desk = self.window.current()
        desk.handle_key(Qt.Key.Key_F3)
        listing = self.window.current()
        self.assertEqual(listing.entries[0]['name'], 'The winning goal')
        listing.press_enter()
        self.assertEqual(type(self.window.current()).__name__, 'SavedGoalMenu')
        self.window.current().press_enter()
        playback = self.window.current()
        playback.timer.stop()
        self.assertEqual(playback.replay.frames, rows)
        self.assertEqual(playback.kits, self.pitch.kits)
        playback.handle_key(Qt.Key.Key_Escape)
        self.assertEqual(type(self.window.current()).__name__, 'SavedGoalMenu')
        self.window.current().escape()
        self.assertIs(self.window.current(), listing)
        listing.escape()
        self.assertIs(self.window.current(), desk)
        self.assertEqual(self.model.state, before)

    def test_duplicate_name_needs_yes_and_long_saved_list_scrolls(self):
        from PySide6.QtCore import Qt
        from goal2.ui import replays
        self.goal()
        self.pitch.answer_stop_box(Qt.Key.Key_N)
        self.pitch.answer_stop_box(Qt.Key.Key_Y)
        name_box = self.window.current()
        name_box.field.set_text('Goal 00')
        name_box.save()
        record = replays.read(replays.entries(self.window.target.root / 'recordings', 'goal')[0]['path'])
        for n in range(1, 12):
            replays.write(self.window.target.root / 'recordings', 'goal', f'Goal {n:02}', record['data'])
        replays.name_recording(self.window, self.pitch, 'goal', record['data'], lambda: None)
        name_box = self.window.current()
        name_box.field.set_text('Goal 00')
        name_box.save()
        self.assertIsNotNone(name_box.replacing)
        name_box.keep()
        self.assertIsNone(name_box.replacing)
        name_box.escape()
        listing = replays.open_list(self.window, self.model, 'goal')
        for _ in range(10):
            listing.handle_key(Qt.Key.Key_Down)
        self.assertEqual(listing.entries[listing.position]['name'], 'Goal 10')
        self.assertGreater(listing.top, 0)
        listing.press_enter()
        self.assertEqual(self.window.current().record['name'], 'Goal 10')

    def test_saved_summary_f4_preserves_counts_and_names_after_the_career_changes(self):
        from PySide6.QtCore import Qt
        from goal2.ui.s20_board import BoardScreen, board, COUNTERS
        from goal2.ui import replays
        event = {'kind': 'full_time', 'minute': 90, 'score': [0, 1], 'data': {
            'final_score': [0, 1], 'statistics': {k: [i, i + 1] for i, (k, _) in enumerate(COUNTERS)},
            'bars': [[3, 4], [5, 6]], 'man_of_the_match': self.model.state.managed_squad[1]}}
        goal = {'kind': 'goal', 'minute': 83, 'score': [0, 1],
                'data': {'team': 1, 'player': self.model.state.managed_squad[1]}}
        screen = BoardScreen(self.window, self.model, ['One', 'Two'], 'FRIENDLY', 'full',
                             board([goal, event], 'full', False), lambda note: self.window.pop(),
                             self.pitch.kits, save_summary=True)
        self.window.push(screen)
        screen.handle_key(Qt.Key.Key_Y)
        self.window.current().field.set_text('A match to remember')
        self.window.current().save()
        self.window.pop()  # pitch -> desk
        record = replays.read(replays.entries(self.window.target.root / 'recordings', 'summary')[0]['path'])
        counts = list(screen.stat_rows)
        scorers = list(screen.scorer_texts)
        with patch('goal2.ui.s20_board.full_name', side_effect=KeyError('old player absent from this career')):
            self.window.current().handle_key(Qt.Key.Key_F4)
            self.window.current().press_enter()
        opened = self.window.current()
        self.assertEqual(opened.stat_rows, counts)
        self.assertEqual(opened.scorer_texts, scorers)
        self.assertEqual(opened.motm.text(), screen.motm.text())
        self.assertEqual(opened.data, record['data']['board'])



@requires.need(modules=('PySide6', 'pygame'), **requires.HALFTIME, slow=True)
class WatchedReplay(unittest.TestCase):
    def test_replayed_engine_samples_and_published_state_equal_the_same_match_through_bridge(self):
        """[designed: T181] Actual PyPy match, not synthetic: a replay is presentation only."""
        from PySide6.QtCore import Qt
        from goal2.tests.test_pypy_worker_t152 import pypy
        from goal2.tests.test_ui_match_day_t167 import app, career, key, pump
        from goal2.desktop import data_setup
        from goal2.ui.window import Window
        from goal2.ui.match_day import for_window
        from goal2.ui.s17_pitch import suggested_captain, engine_fixture
        from goal2.tests.match_day_policy import play_through_bridge
        pypy()
        application = app()
        with tempfile.TemporaryDirectory() as folder:
            model = career()
            reference = copy.deepcopy(model)
            window = Window(data_setup.paths(Path(folder)))
            window.open_career(model)
            window.show()
            self.addCleanup(window.leave)
            day = for_window(window, model)
            day.fixture = model.state.campaign.next_fixture
            day.watch = True
            pitch = day.kick_off(suggested_captain(model.state))
            controller = pitch.controller
            for _ in range(4):
                controller.step_speed(1)
            expected, drawn = [], []
            original_painted = pitch.painted
            def painted(sequence):
                if pitch.replay is not None:
                    row = copy.deepcopy(pitch.replay.frame)
                    if not drawn or not drawn[-1] or drawn[-1][-1]['sequence'] != sequence:
                        drawn[-1].append(row)
                original_painted(sequence)
            pitch.pitch.on_drawn = painted
            def step():
                screen = window.current()
                if screen is pitch:
                    if pitch.stop_box.open:
                        box = pitch.stop_box
                        if box.kind == 'replay':
                            expected.append(copy.deepcopy(pitch.goal_record['frames']))
                            drawn.append([])
                            key(window, Qt.Key.Key_Y)
                        else:
                            key(window, Qt.Key.Key_N if box.answers else Qt.Key.Key_Space)
                elif type(screen).__name__ == 'ChooseScreen':
                    key(window, Qt.Key.Key_Return)
                elif type(screen).__name__ == 'BoardScreen':
                    if screen.phase != 'full':
                        key(window, Qt.Key.Key_Return)
                elif type(screen).__name__ == 'MenuScreen':
                    screen.highlight(screen.options.index(screen.play))
                    key(window, Qt.Key.Key_Return)
            pump(lambda: controller.finished, 1500, 'watched replay match did not finish', step)
            self.assertIsNone(controller.error)
            self.assertTrue(expected, 'the actual match must score a goal and replay it')
            self.assertEqual(drawn, expected)
            self.assertIsNotNone(controller.outcome)
            reference.state = copy.deepcopy(controller.given._snapshot)
            outcome = play_through_bridge(reference, controller.choices, fixture=engine_fixture(day.fixture), wait=1500)
            self.assertEqual(controller.outcome.result, outcome.result)
            self.assertEqual(model.state, reference.state)
            self.assertEqual(controller.outcome.events, outcome.events)
            window.leave()
            application.processEvents()



if __name__ == '__main__':
    unittest.main()
