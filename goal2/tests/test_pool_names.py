"""[designed: owner, 2026-10-21; #295] Localized names for the national pool."""
from dataclasses import replace
import json
from pathlib import Path
import re
import tempfile
import unittest

from goal2.tests import requires

requires.require(**requires.HALFTIME)

from goal2.data.goaldat import load  # noqa: E402
from goal2.desktop.model import DesktopModel  # noqa: E402
from goal2.game import pool_names  # noqa: E402
from goal2.game.new_game import country_rank  # noqa: E402
from goal2.game.session_save import encode  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
GREECE = 13
POOL = range(pool_names.FIRST, pool_names.FIRST + pool_names.COUNT)


class Data(unittest.TestCase):
    def test_33_nations_of_80_valid_distinct_names(self):
        goaldat = load((ROOT / '.cache/GOAL.DAT').read_bytes())
        table = pool_names.table()
        top = sorted(range(1, 129), key=lambda n: country_rank(goaldat, n)[0])[:32]
        self.assertEqual(set(table), set(top) | {GREECE})
        for number, (name, surnames, initials) in table.items():
            self.assertEqual(goaldat.country_names[number], name)
            self.assertEqual((len(surnames), len(initials)), (80, 80), name)
            self.assertEqual(len({s.lower() for s in surnames}), 80, name)
            for surname in surnames:
                self.assertTrue(1 <= len(surname) <= 10, surname)
                self.assertTrue(all(b >= 0x20 and b != 0x7F for b in surname.encode('cp437')), surname)
            self.assertTrue(all(re.fullmatch('[A-Z]', i) for i in initials), name)
        self.assertIn('not real players', json.loads(pool_names.PATH.read_text(encoding='utf-8'))['_note'])


class InTheGame(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory();self.addCleanup(self.folder.cleanup)
        self.save = Path(self.folder.name) / 'game.g2save'

    def model(self, country):
        return DesktopModel.open(ROOT / '.cache/e010-r0008-halftime.sav', ROOT / '.cache/GOAL.DAT', self.save, country=country)

    def test_greece_pool_is_greek_everywhere(self):
        model = self.model(GREECE);_, surnames, initials = pool_names.table()[GREECE]
        reserves = model.pool_view()['reserves']
        self.assertEqual({r['id']: r['name'] for r in reserves}, {w: surnames[w - pool_names.FIRST] for w in POOL})
        from goal2.game.player_card import card
        c = card(model.state, 2561, model.goaldat)
        self.assertEqual((c['name'], c['full_name']), (surnames[0], f'{initials[0]} {surnames[0]}'))
        outgoing = model.state.managed_squad[19]
        model.exchange(outgoing, 2561)
        self.assertIn(surnames[0], [p['name'] for p in model.view()['players']])

    def test_an_unlisted_country_keeps_the_original_names(self):
        goaldat = load((ROOT / '.cache/GOAL.DAT').read_bytes())
        unlisted = next(n for n in range(1, 129) if n not in pool_names.table())
        model = self.model(unlisted)
        self.assertEqual({r['id']: r['name'] for r in model.pool_view()['reserves']}, {w: goaldat.player_names[w] for w in POOL})

    def test_nothing_is_saved_and_an_old_save_shows_the_names(self):
        model = self.model(GREECE);encoded = encode(model.state, model.template_bytes)
        self.assertNotIn(b'Georgiou', encoded);self.assertNotIn(b'identities', encoded)
        self.assertEqual(model.state.player_renames, {})
        model.save(self.save)
        resumed = DesktopModel.from_save(self.save, ROOT / '.cache/GOAL.DAT')
        self.assertEqual(resumed.goaldat.player_names[2561], pool_names.table()[GREECE][1][0])

    def test_a_rename_wins_and_the_localized_name_removes_it(self):
        model = self.model(GREECE);localized = pool_names.table()[GREECE][1][0]
        model.rename_player(2561, 'Zagorakis')
        self.assertEqual(model.goaldat.player_names[2561], 'Zagorakis')
        model.rename_player(2561, localized)
        self.assertEqual((model.state.player_renames, model.goaldat.player_names[2561]), ({}, localized))

    def test_search_ignores_accents(self):
        model = self.model(14)
        self.assertIn('Kovács', pool_names.table()[14][1])
        for query in ('kovacs', 'KOVÁCS', 'Kovács'):
            self.assertIn('Kovács', [r['name'] for r in model.pool_view(query=query)['reserves']], query)

    def test_an_altered_country_name_keeps_its_own_names(self):
        goaldat = load((ROOT / '.cache/GOAL.DAT').read_bytes())
        names = list(goaldat.country_names);names[GREECE] = 'Hellas'
        altered = replace(goaldat, country_names=names)
        self.assertIs(pool_names.localize(altered, GREECE), altered)


if __name__ == '__main__':
    unittest.main()
