"""[designed: T170at] One explicit, real native match-day owner."""

from copy import deepcopy
from dataclasses import asdict
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import time
import unittest

from goal2.tests import pypy_engine, requires
from goal2.tests.test_prematch_preview_t170s import reference_raw
from goal2.tests.test_season_news_wire_t170t import digest


def direct_match_day(raw):
    from goal2.engine.original_match.image import Image
    from goal2.game import engine_tables
    from goal2.game.prematch_seam import PrematchSeam
    from goal2.game.season import SeasonSession
    from goal2.game.watched_pitch import snapshot

    session = SeasonSession(Image.from_bytes(raw).state(engine_tables.load()))
    entry = asdict(session.advance())
    match = session.pending_match
    PrematchSeam(match, frames=True, post_match_review=True)
    events, frames, visited = [], [], []
    for event in match.events():
        if event.kind == 'tick':
            frames.append(snapshot(match, event, len(frames), len(events)))
            if len(frames) == 1:
                match.pause()
        else:
            events.append(asdict(event))
        if event.kind != 'decision':
            continue
        data = event.data
        context = data['context']
        first = context not in visited
        visited.append(context)
        answer = {}
        if context == 'pre_match':
            answer = {'captain': None}
        elif context == 'pause' and first:
            answer = {'edit_only': True, 'tactics': {5: not bool(data['tactics'] & 16)}}
        elif context == 'half_time' and first:
            answer = {'edit_only': True, 'tactics': {1: not bool(data['tactics'] & 1)}}
        elif context == 'set_piece':
            answer = {'taker': None}
        elif context == 'substitution_opportunity':
            answer = {'opportunity': 'accept'}
        elif context == 'post_match':
            answer = {'post_match_exit': True}
        match.answer(**answer)
    observation = asdict(session.resume(match))
    return dict(events=events, frames=digest(frames), state=session.state, observation=observation, entry=entry)


@requires.need(modules=('PySide6',), files=('GOAL.DAT',))
class Window(unittest.TestCase):
    def setUp(self):
        from PySide6.QtWidgets import QApplication
        from goal2.data.goaldat import load
        from goal2.desktop import data_setup
        from goal2.desktop.model import DesktopModel
        from goal2.engine.original_match.image import Image
        from goal2.game import engine_tables
        from goal2.ui import theme
        from goal2.ui.screen import Screen
        from goal2.ui.window import Window

        self.app = QApplication.instance() or QApplication([])
        theme.install(self.app)
        folder = TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        root = Path(folder.name)
        self.raw = reference_raw()
        data = load((requires.CACHE / 'GOAL.DAT').read_bytes())
        self.model = DesktopModel(data, self.raw, root / 'unused')
        image = Image.from_bytes(self.raw)
        country, = image.managed_countries()
        self.model.state = SimpleNamespace(managed_country=country, player_renames={}, manager_name='')
        self.before = deepcopy(self.model.state)
        self.window = Window(data_setup.paths(root / 'data'))
        self.window.resize(1440, 1080)
        self.home = self.window.push(Screen(self.window))
        self.window.show()
        self.addCleanup(self.close_window)
        self.boundaries, self.failures = [], []
        self.state = image.state(engine_tables.load())

    def open_match_day(self, watch, *, show_bulletins=False):
        from goal2.ui.native_match_day import NativeMatchDay

        self.day = NativeMatchDay(
            self.window, self.model, self.state, watch=watch, show_bulletins=show_bulletins,
            on_boundary=lambda day, packet: self.boundaries.append((day.native.pid, packet)),
            on_failure=lambda _, message: self.failures.append(message),
            on_goal=lambda screen, _: screen.release_goal(),
            on_tournament=lambda _: self.fail('Unexpected tournament request'),
            on_stats=lambda *_: self.fail('Unexpected statistics request'),
        )
        self.addCleanup(self.dispose)

    def close_window(self):
        self.window.leaving = True
        self.window.close()
        self.window.deleteLater()
        self.app.processEvents()

    def dispose(self):
        self.day.close()
        self.until(lambda: self.day.native.disposed, limit=15, check_failures=False)

    def until(self, predicate, *, step=None, limit=120, check_failures=True):
        from PySide6.QtTest import QTest

        deadline = time.monotonic() + limit
        while not predicate():
            if check_failures:
                self.assertEqual(self.failures, [])
            if time.monotonic() >= deadline:
                current = self.window.current()
                pitch = self.day.pitch
                driver = pitch.controller.driver if pitch is not None else None
                self.fail(f'Did not settle in {self.day.phase}, screen {type(current).__name__}, '
                          f'driver {driver.status if driver else None}, '
                          f'frames {len(driver.frames) if driver else 0}')
            if step is not None:
                step()
            QTest.qWait(2)

    def key(self, key):
        from PySide6.QtTest import QTest

        QTest.keyClick(self.window, key)

    def kickoff(self, *, watch=True, show_bulletins=False):
        from PySide6.QtCore import Qt
        from goal2.ui.s16_choose import ChooseScreen

        self.open_match_day(watch, show_bulletins=show_bulletins)
        self.until(lambda: self.day.phase == 'prematch')
        pid = self.day.native.pid
        self.key(Qt.Key.Key_Return)
        self.assertIsInstance(self.window.current(), ChooseScreen)
        self.key(Qt.Key.Key_C)
        self.until(lambda: self.day.phase == 'playing')
        self.assertIs(self.window.current(), self.day.pitch)
        self.assertEqual(self.window.stack, [self.home, self.day.opening, self.day.pitch])
        self.assertEqual(self.day.native.pid, pid)
        return pid

    def test_covered_close_and_unexpected_context_do_not_answer(self):
        from PySide6.QtCore import Qt
        from goal2.ui.s17_pitch import HANG_ON
        from goal2.ui.s22_help import HelpScreen

        self.kickoff(watch=False)
        pitch = self.day.pitch
        self.assertTrue(pitch.controller.driver.quick)
        self.assertEqual(pitch.controller.note, HANG_ON)
        self.key(Qt.Key.Key_F1)
        self.assertIsInstance(self.window.current(), HelpScreen)
        choices = pitch.controller.driver.choices.copy()
        with self.assertRaisesRegex(ValueError, 'Unexpected native stopped context'):
            self.day.unexpected_stop(pitch, {'event': {'data': {'context': 'future_context'}}})
        self.window.leaving = True
        self.window.close()
        self.until(lambda: self.day.native.disposed)
        self.assertEqual(self.day.phase, 'closed')
        self.assertEqual(pitch.controller.driver.choices, choices)
        self.assertEqual(self.boundaries, [])
        self.assertEqual(self.model.state, self.before)

    @requires.need(slow=True)
    def test_explicit_qt_match_day_matches_sdk_and_resumes_on_one_worker(self):
        from PySide6.QtCore import Qt
        from goal2.game.bulletin_view import native_bulletins
        from goal2.ui.native_half_time import NativeHalfTimeScreen
        from goal2.ui.native_pause import NativePauseScreen
        from goal2.ui.native_review import NativeReviewScreen
        from goal2.ui.s16_choose import ChooseScreen
        from goal2.ui.s05_bulletin import BulletinScreen

        reference = pypy_engine.start(__name__ + ':direct_match_day', self.raw)
        pid = self.kickoff(show_bulletins=True)
        pitch = self.day.pitch
        driver = pitch.controller.driver
        original_painted = pitch.pitch.on_drawn
        requested = False

        def request_at_first_frame(sequence):
            nonlocal requested
            original_painted(sequence)
            if not requested:
                requested = True
                pitch.request_bench()

        pitch.pitch.on_drawn = request_at_first_frame
        self.until(lambda: isinstance(pitch.review, NativePauseScreen) and pitch.review.phase == 'ready')
        pause = pitch.review
        if not pause.tactics_button.isEnabled():
            self.key(Qt.Key.Key_Right)
        self.key(Qt.Key.Key_T)
        editor = self.window.current()
        self.key(Qt.Key.Key_Return)
        self.until(lambda: not editor.pending and pause.phase == 'ready')
        self.assertEqual(driver.pause_requests, 1)
        self.key(Qt.Key.Key_Escape)
        self.key(Qt.Key.Key_Return)
        self.until(lambda: self.window.current() is pitch)
        self.key(Qt.Key.Key_R)
        self.assertTrue(driver.quick)
        pitch.timer.stop()

        edited_half = False
        visited_review = False

        def advance_visible_stop():
            nonlocal edited_half, visited_review
            if not driver.pending or not driver.connection.replies.empty():
                pitch.tick()
            current = self.window.current()
            if current is pitch and pitch.stop_box.open:
                self.key(Qt.Key.Key_Return)
            elif isinstance(current, ChooseScreen):
                self.key(Qt.Key.Key_C)
            elif isinstance(current, NativeHalfTimeScreen) and current.phase == 'ready':
                if not edited_half:
                    if not current.toggle_button.isEnabled():
                        self.key(Qt.Key.Key_Right)
                    self.key(Qt.Key.Key_G)
                    edited_half = True
                else:
                    self.key(Qt.Key.Key_Return)
            elif isinstance(current, NativeReviewScreen) and current.phase == 'ready':
                if current.title == 'Post-match review':
                    visited_review = True
                    self.assertEqual(self.boundaries, [])
                    self.assertEqual(self.day.phase, 'playing')
                self.key(Qt.Key.Key_Return)

        self.until(lambda: self.day.phase == 'complete', step=advance_visible_stop)
        self.assertTrue(edited_half and visited_review)
        self.assertEqual(self.boundaries, [])
        self.assertEqual(pitch.enter_hint_text(), 'Resume round')
        self.key(Qt.Key.Key_Return)
        self.day.resume()
        self.until(lambda: self.day.phase == 'bulletin', step=pitch.tick)
        bulletin = self.window.current()
        self.assertIsInstance(bulletin, BulletinScreen)
        self.assertEqual(self.boundaries, [])
        expected = reference.result(timeout=120)
        pages = native_bulletins(expected['entry'], expected['observation'])
        self.assertTrue(pages)
        self.assertEqual(bulletin.pages, pages)
        for page in pages:
            for name, story in page.items():
                self.assertEqual(bulletin.panels[name][2].text(), story['masthead'])
                self.assertEqual(bulletin.panels[name][3].text(), '\n'.join(story['lines']))
            self.key(Qt.Key.Key_Return)
        self.assertEqual(self.day.phase, 'finished')
        self.assertEqual(len(self.boundaries), 1)
        actual_pid, packet = self.boundaries[0]
        self.assertEqual(actual_pid, pid)
        self.assertFalse(self.day.native.disposed)
        self.assertEqual(self.model.state, self.before)

        self.assertEqual(digest(driver.events), digest(expected['events'][driver.event_base:]))
        self.assertEqual(digest(driver.frames), expected['frames'])
        self.assertEqual(digest(packet['state']), digest(expected['state']))
        self.assertEqual(digest(packet['observation']), digest(expected['observation']))
        self.assertEqual(digest(self.day.entry_observation['observation']), digest(expected['entry']))
