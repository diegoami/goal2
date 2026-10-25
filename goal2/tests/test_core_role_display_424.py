"""[designed: owner #424] Preserve the accepted side-sensitive role letters at the UI boundary."""
import unittest
from goal2.tests import requires

CODES = ('G', 'S', 'C', 'b', 'B', 'D', 'Ç', 'm', 'M', 'F', 'w', 'W', '¢', '$')
RAW = ('G', 'S', 'C', 'B', 'B', 'D', 'Ç', 'M', 'M', 'F', 'W', 'W', '¢', '$')


class DisplayCodes(unittest.TestCase):
    def test_every_position_and_club_role_uses_the_accepted_mapping_without_mutating_input(self):
        from goal2.desktop.core_roles import role_code
        for position, expected in enumerate(CODES):
            row = dict(position=position, code=RAW[position], club_position=position, club_code=RAW[position])
            before = dict(row)
            self.assertEqual(role_code(row), expected)
            self.assertEqual(role_code(row, club=True), expected)
            self.assertEqual(row, before)
        self.assertEqual(role_code(dict(code='?', position=255)), '?')
        self.assertEqual(role_code(dict(code='M')), 'M')


@requires.need(modules=('unicorn', 'PySide6'), files=('e006-r0001-main.sav', 'GOAL.DAT'))
class GenuinePresentation(unittest.TestCase):
    def test_squad_pool_cards_and_country_use_case_sensitive_codes_without_changing_core(self):
        from PySide6.QtWidgets import QApplication
        from goal2.tests.test_core_team_t107 import model
        from goal2.desktop.core_window import CoreWindow
        from goal2.desktop.player_card import core_card
        from goal2.desktop.country_card import CountryCardView
        from goal2.core import views
        app = QApplication.instance() or QApplication([])
        m = model();w = CoreWindow(m)
        try:
            before = m.core.save()
            raw = m.team()['squad']
            self.assertEqual([r[2] for r in w.team_roster.rows], [CODES[p['position']] for p in raw])
            pool = m.pool()['rows'][:len(w.pool_strip.rows)]
            self.assertEqual([r[2] for r in w.pool_strip.rows], [CODES[p['position']] for p in pool])
            seen = set()
            for p in raw + m.pool()['rows']:
                card = m.card(p['player']);shown = core_card(card);seen.add(card['position'])
                self.assertEqual(shown['role'], CODES[card['position']])
                self.assertEqual(shown['club_role'], CODES[card['club_position']])
                self.assertEqual(card['code'], RAW[card['position']])
            self.assertTrue({3,4,7,8,10,11}.issubset(seen))
            country = views.country_card(m.state, m.team()['country'])
            original = list(country['eleven']);widget = CountryCardView();widget.set_card(country)
            self.assertEqual(widget.card['eleven'], [CODES[p['position']] for p in country['squad'][:11]])
            self.assertEqual(country['eleven'], original)
            self.assertEqual(m.core.save(), before)
        finally:
            w.close();app.processEvents()

    def test_viewer_identity_uses_actual_player_positions_without_changing_raw_identity(self):
        import copy
        from goal2.tests.test_core_team_t107 import model
        from goal2.desktop.core_roles import pitch_identity
        m = model();rows = m.team()['squad'] + m.pool()['rows']
        # The viewer wire dictionary has codes but no position fields: resolve the actual full IDs.
        identity = dict(countries=['one','two'], managed=0, kind='Match',
                        roles={str(p['player']):p['code'] for p in rows})
        before = copy.deepcopy(identity);machine = m.core.save()
        shown = pitch_identity(m.state, identity)
        self.assertEqual(shown['roles'], {str(p['player']):CODES[p['position']] for p in rows})
        self.assertEqual(identity, before)
        self.assertEqual(m.core.save(), machine)
