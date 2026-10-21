"""[designed: T89] The original country card against the original's own screen.

[confirmed: E015-r0007 state 3, docs/original-game/images/country-select.png] A fresh new game's
Denmark card prints: manager R Nielsen; ranking World 29, Europe 1; formation 5-4-1; team
tactics half pitch, sag back to box, play safe; player defaults push forward, quick pass, short
passes, go in hard, man to man. Those values are typed here from that screenshot.
"""
from pathlib import Path
import unittest

from goal2.tests import requires

ROOT = Path(__file__).resolve().parents[2]
DENMARK = 7
SCREEN = {
    'manager': 'R Nielsen', 'world': 29, 'continent': 'Europe', 'continental': 1, 'formation': '5-4-1',
    'team_tactics': [('defence system', 'half pitch'), ('protection', 'sag back to box'), ('offside', 'play safe')],
    'player_defaults': [('positioning', 'push forward'), ('possession', 'quick pass'), ('passing', 'short passes'),
                        ('tackling', 'go in hard'), ('marking', 'man to man')],
}


@requires.need(**requires.HALFTIME)
class CountryCard(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from goal2.desktop.model import DesktopModel
        cls.model = DesktopModel.open(ROOT / '.cache/e010-r0008-halftime.sav', ROOT / '.cache/GOAL.DAT',
                                      ROOT / '.cache/never-written.g2save', country=1)

    def test_denmark_prints_what_the_original_card_printed(self):
        from goal2.game.country_card import card
        c = card(self.model.state, DENMARK, self.model.goaldat)
        self.assertEqual({k: c[k] for k in SCREEN}, SCREEN)
        self.assertEqual(c['name'], 'Denmark')
        self.assertEqual(len(c['players']), 20)

    def test_the_managed_countrys_live_tactics_are_shown(self):
        import copy
        from goal2.game.country_card import card
        model = copy.deepcopy(self.model);model.new_campaign(DENMARK)
        model.state.country_tactics ^= 0x10  # defence system: half pitch -> full pitch
        self.assertEqual(card(model.state, DENMARK, model.goaldat)['team_tactics'][0], ('defence system', 'full pitch'))

    def test_every_country_has_a_card_and_undecoded_fields_are_named(self):
        from goal2.game.country_card import card, NOT_DECODED
        for country in range(1, 129):
            c = card(self.model.state, country, self.model.goaldat)
            self.assertEqual(sum(int(n) for n in c['formation'].split('-')), 10, c['name'])
            self.assertEqual(len(c['eleven']), 11)
            self.assertTrue(c['manager'].strip())
        self.assertEqual(set(c['not_decoded']), {'status', 'skill', 'ranking top', 'strips', 'team skills',
                                                 'performance', 'characteristics'})
        self.assertEqual(NOT_DECODED, 'not decoded yet (G05)')
        with self.assertRaises(ValueError):
            card(self.model.state, 0, self.model.goaldat)

    @requires.need(modules=('PySide6',))
    def test_the_card_draws_every_value_and_names_what_is_not_decoded(self):
        from PySide6.QtWidgets import QApplication
        from goal2.desktop.country_card import CountryCardView
        from goal2.game.country_card import card
        app = QApplication.instance() or QApplication([])
        for width in (820, 320):
            view = CountryCardView();view.resize(width, 600);view.set_card(card(self.model.state, DENMARK, self.model.goaldat), 'X: Y')
            drawn = []
            view.text = lambda painter, x, y, value, *a, drawn=drawn, **k: drawn.append((x, str(value)))
            view.grab();app.processEvents()
            texts = ' '.join(t for _, t in drawn)
            for value in ('DENMARK', 'R Nielsen', '5-4-1', 'half pitch', 'man to man', 'not decoded yet (G05)', 'SPACE: PLAYERS'):
                self.assertIn(value, texts, (width, value))
            self.assertNotIn('ability', texts.lower())
            self.assertEqual(view.narrow, width < 740)


if __name__ == '__main__':
    unittest.main()
