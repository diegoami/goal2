"""[designed: T170aw] Results and acknowledgement at advance-only boundaries."""

from dataclasses import asdict
from functools import cache
from pathlib import Path
from tempfile import TemporaryDirectory
import time
from types import SimpleNamespace
import unittest

from goal2.tests import pypy_engine, requires
from goal2.tests.season_oracle import component_of
from goal2.tests.test_native_round_view_t170av import result
from goal2.tests.test_season_oracle_t170d import ARTIFACTS, CASES, GOAL_DAT, checkpoint


def advance(state, count=1):
    from goal2.game.season import SeasonSession

    session = SeasonSession(state)
    for _ in range(count - 1):
        assert session.advance().status == 'complete'
        assert session.pending_match is None
    entry = session.state
    session = SeasonSession(entry)
    observed = session.advance()
    assert session.pending_match is None
    return entry, session.state, asdict(observed)


class Projection(unittest.TestCase):
    def test_boundary_rows_preserve_order_score_and_empty_delta(self):
        from goal2.engine.original_match.image import Image
        from goal2.game import engine_tables
        from goal2.game.native_round_view import completed_round_results
        from goal2.tests.test_prematch_preview_t170s import reference_raw

        state = Image.from_bytes(reference_raw()).state(engine_tables.load())
        rows = (result(10, 7, 19, (1, 2)), result(11, 22, 25, (254, 0)),
                result(12, 20, 30, (4, 3)))
        names = tuple(f'Country {i}' for i in range(129))
        for status in ('complete', 'deferred-rollover'):
            with self.subTest(status=status):
                packet = dict(state=state, observation=dict(status=status, played_fixtures=rows))
                view = completed_round_results(packet, names, 9)
                self.assertEqual(view['round'], 9)
                self.assertIsNone(view['match'])
                self.assertEqual([(row['fixture_id'], row['home'], row['away'], row['score'])
                                  for row in view['results']],
                                 [(10, 19, 7, (2, 1)), (12, 30, 20, (3, 4))])
        packet['observation']['played_fixtures'] = rows[1:2]
        self.assertEqual(completed_round_results(packet, names, None)['results'], [])
        packet['observation']['status'] = 'match'
        with self.assertRaises(ValueError):
            completed_round_results(packet, names, None)


@requires.need(modules=('PySide6', 'unicorn'), files=('GOAL.DAT', ARTIFACTS[0]['name'], ARTIFACTS[2]['name']))
class Window(unittest.TestCase):
    def open(self, state, *, number=None, bulletins=True):
        from PySide6.QtWidgets import QApplication
        from goal2.data.goaldat import load
        from goal2.desktop.data_setup import paths
        from goal2.desktop.model import DesktopModel
        from goal2.engine.original_match.image import Image
        from goal2.game import engine_tables
        from goal2.ui import theme
        from goal2.ui.native_match_day import NativeMatchDay
        from goal2.ui.screen import Screen
        from goal2.ui.window import Window as GameWindow

        self.app = QApplication.instance() or QApplication([])
        theme.install(self.app)
        folder = TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        root = Path(folder.name)
        self.window = GameWindow(paths(root / 'data'))
        self.window.push(Screen(self.window))
        self.window.show()
        self.addCleanup(self.close_window)
        image = Image.from_state(state, engine_tables.load())
        data = load(GOAL_DAT.read_bytes())
        model = DesktopModel(data, b'', root / 'unused')
        country, = image.managed_countries()
        model.state = SimpleNamespace(managed_country=country, player_renames={}, manager_name="")
        self.boundaries, self.failures = [], []
        self.day = NativeMatchDay(
            self.window, model, state, show_round_results=True, show_bulletins=bulletins, round_number=number,
            on_boundary=lambda _, value: self.boundaries.append(value),
            on_failure=lambda _, message: self.failures.append(message),
            on_goal=self.unexpected, on_tournament=self.unexpected, on_stats=self.unexpected,
        )

    def unexpected(self, *_):
        self.fail('Advance without a managed fixture opened a match action')

    def close_window(self):
        self.window.leaving = True
        self.window.close()
        self.day.close()
        self.until(lambda: self.day.native.disposed, limit=15)
        self.window.deleteLater()
        self.app.processEvents()

    def until(self, predicate, *, limit=120):
        from PySide6.QtTest import QTest

        end = time.monotonic() + limit
        while not predicate():
            self.assertEqual(self.failures, [])
            self.assertLess(time.monotonic(), end, getattr(self.day, 'phase', ''))
            QTest.qWait(2)

    def key(self, key):
        from PySide6.QtTest import QTest

        QTest.keyClick(self.window, key)

    def assert_boundary(self, state, observed):
        self.assertEqual(len(self.boundaries), 1)
        self.assertEqual(self.boundaries[0]['action'], 'advance')
        self.assertEqual(self.boundaries[0]['state'], state)
        self.assertEqual(self.boundaries[0]['observation'], observed)
        self.assertIsNone(self.day.prematch)
        self.assertIsNone(self.day.pitch)

    @staticmethod
    @cache
    def case(index, count):
        from goal2.engine.original_match.image import Image
        from goal2.game import engine_tables

        raw = component_of(checkpoint(CASES[index]), GOAL_DAT)
        state = Image.from_bytes(raw).state(engine_tables.load())
        return pypy_engine.call(__name__ + ':advance', state, count)

    def test_actual_unmanaged_round_shows_only_verified_rows_then_bulletin(self):
        from PySide6.QtCore import Qt
        from goal2.core.views import Memory
        from goal2.engine.original_match.image import Image
        from goal2.game import engine_tables
        from goal2.game.bulletin_view import native_bulletins
        from goal2.ui.s05_bulletin import BulletinScreen
        from goal2.ui.s14_round import RoundScreen
        from goal2.ui.s22_help import HelpScreen

        entry, state, observation = self.case(0, 1)
        self.assertEqual(observation['status'], 'complete')
        self.assertTrue(observation['played_fixtures'])
        self.assertTrue(observation['news_pages'])
        self.open(entry, number=13)
        self.key(Qt.Key.Key_F1)
        self.assertIsInstance(self.window.current(), HelpScreen)
        self.until(lambda: self.day.native.status == 'boundary')
        self.assertEqual(self.day.phase, 'advancing')
        self.assertFalse(self.boundaries)
        self.key(Qt.Key.Key_Escape)
        self.until(lambda: self.day.phase in ('after_results', 'bulletin', 'finished'))
        results = self.window.current()
        self.assertIsInstance(results, RoundScreen)
        results.timer.stop()
        self.assertEqual(results.title, 'round 13 · results')
        self.assertIsNone(results.mine)
        self.assertEqual(results.visible(), [])
        self.key(Qt.Key.Key_Space)
        results.arrive()
        self.assertEqual(results.visible(), [])
        self.key(Qt.Key.Key_Right)
        self.assertIn('speed 4/', results.state_label.text())
        self.key(Qt.Key.Key_Space)
        results.arrive()
        first = next(row for row in observation['played_fixtures'] if row['kind'] and row['score'][0] < 254)
        memory = Memory(Image.from_state(state, engine_tables.load()))
        names = self.day.model.goaldat.country_names
        away, home = first['score']
        self.assertEqual(results.visible(), [(names[first['second']], f'{home} - {away}',
                                              names[first['first']], memory.kind_name(first['kind']))])
        self.assertEqual(results.enter_action[0], 'Continue round')
        self.key(Qt.Key.Key_Return)
        bulletin = self.window.current()
        self.assertIsInstance(bulletin, BulletinScreen)
        self.assertEqual(bulletin.pages, native_bulletins(observation))
        self.assertFalse(self.boundaries)
        for _ in bulletin.pages:
            self.key(Qt.Key.Key_Return)
        self.assert_boundary(state, observation)
        self.day.poll()
        self.assertEqual(len(self.boundaries), 1)

    def test_actual_deferred_rollover_displays_the_fixtures_played_before_it(self):
        from PySide6.QtCore import Qt
        from goal2.ui.s05_bulletin import BulletinScreen
        from goal2.ui.s14_round import RoundScreen

        entry, state, observation = self.case(2, 2)
        self.assertEqual(observation['status'], 'deferred-rollover')
        self.assertTrue(observation['played_fixtures'])
        self.open(entry)
        self.until(lambda: self.day.phase in ('after_results', 'bulletin', 'finished'))
        results = self.window.current()
        self.assertIsInstance(results, RoundScreen)
        self.assertEqual(results.title, 'round results')
        self.assertIsNone(results.mine)
        self.assertEqual(len(results.arriving) + len(results.shown_rows), len(observation['played_fixtures']))
        self.assertFalse(self.boundaries)
        self.key(Qt.Key.Key_Return)
        bulletin = self.window.current()
        if isinstance(bulletin, BulletinScreen):
            for _ in bulletin.pages:
                self.key(Qt.Key.Key_Return)
        self.assert_boundary(state, observation)
        self.assertEqual(self.day.native.status, 'terminal')

    def test_actual_empty_rollover_guard_has_no_result_board(self):
        from PySide6.QtCore import Qt

        _, terminal, _ = self.case(2, 2)
        entry, state, observation = pypy_engine.call(__name__ + ':advance', terminal)
        self.assertEqual(observation['status'], 'deferred-rollover')
        self.assertFalse(observation['played_fixtures'])
        self.assertFalse(observation['news_pages'])
        self.assertEqual(state, entry)
        self.open(entry, bulletins=False)
        self.key(Qt.Key.Key_F1)
        self.until(lambda: self.day.native.status == 'terminal')
        self.assertFalse(self.boundaries)
        self.key(Qt.Key.Key_Escape)
        self.until(lambda: self.day.phase == 'finished')
        self.assertIs(self.window.current(), self.day.opening)
        self.assert_boundary(state, observation)

    def test_close_under_help_at_actual_unmanaged_results_releases_owner(self):
        from PySide6.QtCore import Qt
        from goal2.ui.s14_round import RoundScreen
        from goal2.ui.s22_help import HelpScreen

        entry, _, _ = self.case(0, 1)
        self.open(entry)
        self.until(lambda: self.day.phase in ('after_results', 'bulletin', 'finished'))
        results = self.window.current()
        self.assertIsInstance(results, RoundScreen)
        self.key(Qt.Key.Key_F1)
        self.assertIsInstance(self.window.current(), HelpScreen)
        self.window.leaving = True
        self.window.close()
        self.until(lambda: self.day.native.disposed, limit=15)
        self.assertFalse(results.timer.isActive())
        self.assertFalse(self.boundaries)
