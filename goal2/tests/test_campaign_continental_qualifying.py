"""[designed: T50] Stage-2 continental qualifying: draw coverage, legs, persistence and qualifiers.

[derived: F023 §§3-4, 8 at goal2-archaeology 3656a2d26e0f57a410d648edeaa6cd9eb7d1f607]
Synthetic results are bounded fixture inputs: each country gets a strength and the stronger
side of a fixture wins by the strength gap, so the group winner is known independently of the
table sort. The real played stage is covered by tools/desktop-ui/acceptance.py
--scenario continental-qualifying.
"""
import copy
from collections import Counter
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from goal2.tests import requires

ROOT = Path(__file__).resolve().parents[2]
SEEDS = dict(seed_7b62=4660, seed_8336=33590)


def resources():
    from goal2.data.goaldat import load
    return (load((ROOT / '.cache/GOAL.DAT').read_bytes()),
            (ROOT / '.cache/e010-r0008-halftime.sav').read_bytes())


def started(country=4, start_year=1992, **seeds):
    from goal2.game.campaign_schedule import start_opening_campaign
    goaldat, template = resources()
    state, opening = start_opening_campaign(goaldat, template, managed_country=country,
                                            start_year=start_year, **(seeds or SEEDS))
    return state, opening, template


def played(campaign, strength, *, missing=0):
    """A copy of the campaign whose world has a result for every fixture but the last `missing`."""
    candidate = copy.deepcopy(campaign)
    fixtures = candidate.world.fixtures
    results = []
    for f in fixtures[:len(fixtures) - missing]:
        gap = strength[f.side_a] - strength[f.side_b]
        margin = min(abs(gap), 9)
        results.append({'fixture_id': f.fixture_id, 'teams': [f.side_a, f.side_b],
                        'score': [margin, 0] if gap > 0 else [0, margin]})
    candidate.world.results = results
    return candidate


@requires.need(**requires.HALFTIME)
class Draw(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from goal2.game.campaign_schedule import _validated_orders
        cls.state, cls.opening, cls.template = started()
        _, _, cls.continent_for = _validated_orders(resources()[0])

    def test_participant_coverage(self):
        groups = self.opening.groups
        self.assertEqual(self.opening.stage, 2)
        self.assertEqual(len(groups), 32)
        self.assertEqual(Counter(g.continent for g in groups), {1: 8, 2: 8, 3: 8, 4: 8})
        members = [c for g in groups for c in g.countries_by_slot]
        self.assertEqual(sorted(members), list(range(1, 129)))
        for g in groups:
            self.assertEqual({self.continent_for[c] for c in g.countries_by_slot}, {g.continent})
        per_country = Counter()
        for f in self.opening.fixtures:
            per_country[(f.country_a, f.kind)] += 1;per_country[(f.country_b, f.kind)] += 1
        self.assertEqual({per_country[(c, 2)] for c in range(1, 129)}, {6})
        self.assertEqual({per_country[(c, 1)] for c in range(1, 129)}, {6})

    def test_double_round_robin_legs_in_both_orders(self):
        for g in self.opening.groups:
            rows = [(f.country_a, f.country_b) for f in self.opening.fixtures
                    if f.kind == 2 and (f.continent, f.group) == (g.continent, g.group)]
            self.assertEqual(len(rows), 12)
            pairs = Counter(frozenset(r) for r in rows)
            self.assertEqual(len(pairs), 6);self.assertEqual(set(pairs.values()), {2})
            self.assertEqual(len(set(rows)), 12, 'each pair once in each A/B order')
            self.assertEqual(Counter(a for a, _ in rows), Counter({c: 3 for c in g.countries_by_slot}))
            self.assertTrue(all(set(r) <= set(g.countries_by_slot) for r in rows))
        rounds = Counter(f.round for f in self.opening.fixtures if f.kind == 2)
        self.assertEqual(rounds, Counter({r: 32 for r in range(1, 13)}))

    def test_draw_is_deterministic_and_seeded(self):
        from goal2.game.campaign_schedule import build_opening_campaign
        goaldat, template = resources()
        again = build_opening_campaign(goaldat, template, start_year=1992, **SEEDS)
        self.assertEqual(again, self.opening)
        other = build_opening_campaign(goaldat, template, start_year=1992, seed_7b62=4661, seed_8336=33590)
        self.assertNotEqual(other.groups, self.opening.groups)

    def test_saved_schedule_resumes_the_same_groups_without_drawing_again(self):
        from goal2.game import session_save
        from goal2.game.standings import opening_groups
        drawn = tuple((g.continent, g.group, g.countries_by_slot) for g in self.opening.groups)
        self.assertEqual(opening_groups(self.state.campaign, self.template), drawn)
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'qualifying.g2save'
            session_save.save(path, self.state, self.template)
            with patch('goal2.game.campaign_schedule.build_opening_campaign',
                       side_effect=AssertionError('load drew the groups again')):
                loaded, raw = session_save.load(path)
        self.assertEqual(loaded.campaign.world.fixtures, self.state.campaign.world.fixtures)
        self.assertEqual(opening_groups(loaded.campaign, raw), drawn)


@requires.need(**requires.HALFTIME)
class Qualifiers(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.state, cls.opening, cls.template = started()

    def strongest(self, strength):
        return {c: tuple(max(g.countries_by_slot, key=strength.get) for g in self.opening.groups if g.continent == c)
                for c in range(1, 5)}

    def test_exact_qualifier_counts_for_all_continents(self):
        from goal2.game.continental_qualifying import outcome
        for strength in ({c: c for c in range(1, 129)}, {c: 129 - c for c in range(1, 129)},
                         {c: (c * 37) % 128 for c in range(1, 129)}):
            result = outcome(played(self.state.campaign, strength), self.template, 4)
            self.assertTrue(result['complete'])
            self.assertEqual(result['qualifiers'], self.strongest(strength))
            self.assertEqual([len(w) for w in result['qualifiers'].values()], [8, 8, 8, 8])
            self.assertEqual(len({c for w in result['qualifiers'].values() for c in w}), 32)
            for g in result['groups']:
                self.assertEqual(g['rows'][0].country, result['qualifiers'][g['continent']][g['group'] - 1])
                self.assertEqual(sum(r.played for r in g['rows']), 24)

    def test_no_qualifiers_until_every_fixture_has_a_result(self):
        from goal2.game.continental_qualifying import outcome
        strength = {c: c for c in range(1, 129)}
        for missing in (1, len(self.state.campaign.world.fixtures)):
            result = outcome(played(self.state.campaign, strength, missing=missing), self.template, 4)
            self.assertFalse(result['complete'])
            self.assertIsNone(result['qualifiers'])
            self.assertEqual(result['managed']['status'], 'in progress')

    def test_managed_country_qualifies_or_is_eliminated(self):
        from goal2.game.continental_qualifying import outcome
        group = next(g for g in self.opening.groups if 4 in g.countries_by_slot)
        strength = {c: 1 for c in range(1, 129)}
        strength.update({c: 10 * (n + 1) for n, c in enumerate(c for c in group.countries_by_slot if c != 4)})
        for managed, rank, status in ((99, 1, 'qualified'), (25, 2, 'eliminated'), (0, 4, 'eliminated')):
            strength[4] = managed
            result = outcome(played(self.state.campaign, strength), self.template, 4)['managed']
            self.assertEqual((result['continent'], result['group'], result['rank'], result['status']),
                             (group.continent, group.group, rank, status))

    def test_outcome_reads_without_changing_the_campaign(self):
        from goal2.game.continental_qualifying import outcome
        campaign = played(self.state.campaign, {c: c for c in range(1, 129)})
        before = copy.deepcopy(campaign)
        outcome(campaign, self.template, 4)
        self.assertEqual(campaign.to_data(), before.to_data())

    def test_only_a_stage_two_schedule_has_a_qualifying_outcome(self):
        from goal2.game.continental_qualifying import outcome
        world_cup, _, template = started(start_year=1990)
        self.assertEqual(world_cup.campaign.stage, 5)
        self.assertIsNone(outcome(world_cup.campaign, template, 4))
        self.assertIsNone(outcome(None, template, 4))


@requires.need(**requires.HALFTIME)
class Desktop(unittest.TestCase):
    def model(self):
        from goal2.desktop.model import DesktopModel
        return DesktopModel.open(ROOT / '.cache/e010-r0008-halftime.sav', ROOT / '.cache/GOAL.DAT',
                                 ROOT / '.cache/never-written.g2save', country=4)

    def test_new_campaign_offers_both_start_calendars(self):
        m = self.model()
        self.assertEqual(m.state.campaign.stage, 5, '1990 stays the default')
        self.assertIsNone(m.qualifying())
        m.new_campaign(4, 1992)
        self.assertEqual((m.state.campaign.start_year, m.state.campaign.stage), (1992, 2))
        view = m.qualifying()
        self.assertEqual((view['status'], view['complete'], view['qualifiers']), ('in progress', False, None))
        self.assertIn('only the group winner qualifies', view['text'])
        before = copy.deepcopy(m.state)
        with self.assertRaisesRegex(ValueError, 'Start year must be one of 1990, 1992'):
            m.new_campaign(4, 1994)
        self.assertEqual(m.state, before)

    def test_finished_stage_names_finalists(self):
        m = self.model();m.new_campaign(4, 1992)
        m.state.campaign = played(m.state.campaign, {c: c for c in range(1, 129)})
        view = m.qualifying()
        self.assertTrue(view['complete'])
        self.assertEqual([len(names) for names in view['qualifiers'].values()], [8, 8, 8, 8])
        self.assertEqual(view['status'], 'eliminated' if view['rank'] > 1 else 'qualified')

    @requires.need(modules=('PySide6',))
    def test_start_year_selector_creates_a_continental_qualifying_campaign(self):
        from PySide6.QtWidgets import QApplication
        from goal2.desktop.window import ManagementWindow
        app = QApplication.instance() or QApplication([])
        m = self.model();window = ManagementWindow(m)
        try:
            self.assertEqual(window.start_year.currentData(), 1990)
            before = copy.deepcopy(m.state)
            window.start_year.setCurrentIndex(window.start_year.findData(1992))
            self.assertEqual(m.state, before, 'choosing a start year is a draft')
            window.new.click();app.processEvents()
            self.assertEqual((m.state.campaign.start_year, m.state.campaign.stage), (1992, 2))
            self.assertIn('only the group winner qualifies', window.qualifying.text())
            m.state.campaign = played(m.state.campaign, {c: c for c in range(1, 129)})
            m.state.campaign.completed_fixture_ids = [f.fixture_id for f in m.state.campaign.fixtures]
            from goal2.desktop.fixtures_page import enabled
            enabled(window, True)
            self.assertFalse(window.play.isEnabled())
            self.assertIn('this stage is complete', window.fixture_routes.text())
        finally:
            window.close();window.deleteLater();app.processEvents()


if __name__ == '__main__':
    unittest.main()
