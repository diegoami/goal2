"""[designed: T97; accepted vision #266 screens 08/09] The result of a finished match and Continue."""
import copy
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from goal2.tests import requires

requires.require(modules=('PySide6',), **requires.HALFTIME)

from PySide6.QtTest import QTest  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402
from goal2.desktop.model import DesktopModel  # noqa: E402
from goal2.desktop.window import ManagementWindow  # noqa: E402
from goal2.game import match_report  # noqa: E402
from goal2.game.session_save import encode  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]


def played_model():
    """A Greece campaign after a real original friendly (watched engine, about 15 s)."""
    from goal2.engine.original_match.match import Fixture
    from goal2.game.campaign_rounds import prepare
    from goal2.game.watched_match import run_watched_match
    from goal2.game.watched_publication import completed_candidate
    model = DesktopModel.open(ROOT / '.cache/e010-r0008-halftime.sav', ROOT / '.cache/GOAL.DAT',
                              Path(tempfile.mkdtemp()) / 'game.g2save', country=13)
    state = prepare(model.state, model.template_bytes);pending = state.campaign.next_fixture
    fixture = Fixture(pending.side_a, pending.side_b, int(pending.fixture_id.split(':')[1]))
    outcome = run_watched_match(state, model.template_bytes, fixture, delay_byte=0, record_draws=True)
    model.state = completed_candidate(state, fixture, outcome, model.template_bytes);model.mark_saved()
    return model


class Report(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.model = played_model()

    def test_a_watched_result_reports_the_originals_board(self):
        m = self.model;last = m.state.last_match;original = last['original'];names = m.goaldat.player_names
        value = match_report.report(last, m.goaldat)
        self.assertEqual(value['teams'], [m.goaldat.country_names[t] for t in last['teams']])
        self.assertEqual(value['score'], last['score']);self.assertEqual(value['half_time'], original['half_time_score'])
        self.assertEqual(value['engine'], 'Original engine');self.assertEqual(value['kind'], 'Friendly')
        for side in (0, 1):
            self.assertEqual(value['scorers'][side], [(names[g['player']], g['minute']) for g in last['goals'] if g['team'] == side])
        self.assertEqual([label for label, _ in value['statistics']],
                         ['Corners', 'Free kicks', 'Penalties', 'Shots', 'On target', 'Saves', 'Fouls', 'Yellow cards', 'Red cards', 'Injuries'])
        self.assertEqual([v for _, v in value['statistics']],
                         [list(original['board']['statistics'][k]) for k, _ in match_report.STATISTICS])
        self.assertEqual(value['bars'], [list(b) for b in original['board']['bars']])
        self.assertEqual(value['man_of_the_match'], names[original['man_of_the_match']])
        self.assertEqual(value['substitutions'], [(r['team'], names[r['off']], names[r['on']], r['minute']) for r in original['substitutions']])

    def test_a_quick_result_reports_only_what_it_keeps(self):
        m = self.model;quick = {'teams': list(m.state.last_match['teams']), 'score': [1, 0],
                                'goals': [{'team': 0, 'minute': 12, 'player': m.state.last_match['goals'][0]['player'] if m.state.last_match['goals'] else 1}]}
        value = match_report.report(quick, m.goaldat)
        self.assertEqual((value['statistics'], value['half_time'], value['man_of_the_match'], value['bars']), (None, None, None, None))
        self.assertEqual(value['engine'], 'Quick simulation (rebuild setup)')
        self.assertIn('Half time Not recorded', match_report.lines(value))
        self.assertIsNone(match_report.report(None, m.goaldat))

    def test_renamed_scorers_carry_into_the_result(self):
        m = copy.deepcopy(self.model);last = m.state.last_match
        if not last['goals']:
            self.skipTest('this original friendly had no goals')
        word = last['goals'][0]['player'];m.rename_player(word, 'Renamed')
        value = match_report.report(m.state.last_match, m.goaldat)
        self.assertIn('Renamed', [n for side in value['scorers'] for n, _ in side])


class Window(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])
        cls.base = played_model()

    def setUp(self):
        self.model = copy.deepcopy(self.base)
        self.window = ManagementWindow(self.model);self.window.resize(1440, 900);self.window.show()
        QTest.qWaitForWindowActive(self.window)
        self.addCleanup(lambda: (self.window.close(), self.window.deleteLater(), self.app.processEvents()))

    def test_a_finished_match_opens_its_result_and_continue_leads_on(self):
        w = self.window;before = encode(self.model.state, self.model.template_bytes)
        self.assertFalse(w.result_box.isVisibleTo(w), 'no result before a match finishes')
        w.match_finished();self.app.processEvents()
        self.assertEqual(w.page_stack.currentIndex(), 3);self.assertTrue(w.result_box.isVisible())
        # [designed: #311] The window's own focus: with other GUI test windows on the Windows runner,
        # this one may not be the active window, and then the application has no focus widget.
        self.assertIs(w.focusWidget(), w.result_continue)
        a, b = [self.model.goaldat.country_names[t] for t in self.model.state.last_match['teams']];s = self.model.state.last_match['score']
        self.assertEqual(w.result_title.text(), f'FULL TIME / {a.upper()} {s[0]} - {s[1]} {b.upper()}')
        self.assertIn('Corners', w.result_panels[1][1].text());self.assertIn('MAN OF THE MATCH: ', w.result_motm.text())
        with patch.object(w, 'show_standings') as standings:
            w.result_round.click();standings.assert_called_once()
        w.result_continue.click();self.app.processEvents()
        self.assertEqual(w.page_stack.currentIndex(), 0);self.assertFalse(w.result_box.isVisibleTo(w))
        self.assertIs(w.focusWidget(), w.desk_routes[0], 'Prepare match is next')
        self.assertEqual(encode(self.model.state, self.model.template_bytes), before, 'reading a result changes nothing')

    def test_every_completion_opens_the_result(self):
        w = self.window
        with patch.object(w, 'match_finished') as finished:
            with patch.object(w.jobs, 'poll', return_value=True), patch.object(w, 'show_halftime'):
                w.poll_match()
            with patch.object(w.watched, 'poll', return_value=True):
                w.poll_watched()
        self.assertEqual(finished.call_count, 2)

    def test_a_preview_shows_no_result(self):
        w = self.window;w.match_finished()
        w.country.setCurrentIndex(w.country.findData(5));self.app.processEvents()
        self.assertIsNotNone(w.preview);self.assertFalse(w.result_box.isVisibleTo(w))


if __name__ == '__main__':
    unittest.main()
