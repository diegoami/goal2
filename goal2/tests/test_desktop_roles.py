"""[designed: owner, 2026-10-21; #283, #286] One-letter role codes everywhere, and never an
overall ability. [confirmed: F002 R011 DS:69A8/69B6, F028 DS:0D5C] the original's tables."""
from pathlib import Path
import unittest

from goal2.tests import requires

ROOT = Path(__file__).resolve().parents[2]
CODES = ('G', 'S', 'C', 'b', 'B', 'D', 'Ç', 'm', 'M', 'F', 'w', 'W', '¢', '$')
LINES = ('goalkeeper',) + ('defence',) * 4 + ('midfield',) * 7 + ('attack',) * 2
NAMES = ('goalkeeper', 'sweeper', 'centre back', 'left back', 'right back', 'defensive midfield',
         'central midfield', 'left midfield', 'right midfield', 'forward midfield', 'left winger',
         'right winger', 'centre forward', 'striker')


@requires.need(**requires.HALFTIME)
class Roles(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from goal2.desktop.model import DesktopModel
        cls.model = DesktopModel.open(ROOT / '.cache/e010-r0008-halftime.sav', ROOT / '.cache/GOAL.DAT',
                                      ROOT / '.cache/never-written.g2save', country=4)
        cls.model.new_campaign(4, 1992)

    def test_the_original_tables_with_lower_case_for_the_left_side(self):
        from goal2.game import roles
        codes, lines = roles.tables(self.model.state)
        self.assertEqual(codes, CODES)
        self.assertEqual(tuple(roles.LINES[x] for x in lines), LINES)
        self.assertEqual(roles.names(self.model.state), NAMES)
        self.assertEqual([roles.role(self.model.state, v) for v in range(14)], list(zip(CODES, LINES)))
        for invalid in (-1, 14, 255, True, None):
            self.assertEqual(roles.role(self.model.state, invalid), ('?', 'unknown'))

    def test_squad_and_pool_views_carry_roles_and_no_ability(self):
        state = self.model.state
        rows = self.model.view()['players'] + self.model.pool_view()['reserves']
        self.assertEqual(len(rows), 100)
        for row in rows:
            record = state.players[row['id']]
            self.assertNotIn('ability', row)
            self.assertEqual((row['role'], row['line'], row['club_role'], row['position_name']),
                             (CODES[record[6]], LINES[record[6]], CODES[record[7]], NAMES[record[6]]))
        self.assertGreater(len({row['role'] for row in rows}), 5, 'the 100 players cover many roles')

    @requires.need(modules=('PySide6',))
    def test_tables_and_details_show_roles_and_never_ability(self):
        from PySide6.QtWidgets import QApplication
        from goal2.desktop.window import ManagementWindow
        app = QApplication.instance() or QApplication([])
        window = ManagementWindow(self.model)
        try:
            for table in (window.table, window.reserves):
                headers = [table.horizontalHeaderItem(c).text() for c in range(table.columnCount())]
                self.assertNotIn('Ability', headers);self.assertEqual(headers[2], 'Role')
            for row, player in enumerate(self.model.view()['players']):
                self.assertEqual([window.table.item(row, c).text() for c in (2, 3)], [player['role'], player['position_name']])
            for row, player in enumerate(self.model.pool_view()['reserves']):
                self.assertEqual([window.reserves.item(row, c).text() for c in (2, 3)], [player['role'], player['position_name']])
            window.reserves.setCurrentCell(0, 1);app.processEvents()
            from goal2.desktop.pool_page import refresh as refresh_pool
            refresh_pool(window)
            for label in (window.player_detail, window.pool_detail, window.exchange_summary):
                self.assertNotIn('Ability', label.text())
            self.assertIn('Role ', window.player_detail.text())
            self.assertEqual([window.position.itemText(i) for i in range(1, 15)],
                             [f'{c} · {n}' for c, n in zip(CODES, NAMES)])
        finally:
            window.close();window.deleteLater();app.processEvents()


if __name__ == '__main__':
    unittest.main()
