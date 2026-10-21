"""[designed: T88] The complete player card against the original's own screens.

[confirmed: E007-r0009..r0012, F008] Each run holds the original's text screen (CP437 rows and
the 4000 character/attribute bytes) for the twenty players of one country, taken from the
E006-r0001 state. The expected values are parsed from those screens, never from the decoder.
"""
import json
from pathlib import Path
import unittest

from goal2.tests import requires

ROOT = Path(__file__).resolve().parents[2]
RUNS = (9, 10, 11, 12)
BAR = 0x70  # [confirmed: F008] a painted bar cell's attribute


def observation(obs, text):
    return next(o['value'] for o in obs if text in o['field'])


def screens(run):
    """Per player: (record bytes, decoded rows, character/attribute cells) as the original drew them."""
    data = json.loads((requires.archaeology() / 'runs/E007' / f'E007-r{run:04d}.json').read_text())
    obs = data['observations']
    for n in range(1, 21):
        record = bytes.fromhex(observation(obs, f'player screen {n} of the list: the 20 bytes of player'))
        rows = observation(obs, f'player screen {n} of the list: text screen rows 0-24, CP437 decoded').split('\n')
        raw = bytes.fromhex(observation(obs, f'player screen {n} of the list: text screen 80x25 as the 4000 bytes'))
        cells = [[(raw[2 * (80 * r + c)], raw[2 * (80 * r + c) + 1]) for c in range(80)] for r in range(25)]
        yield n, record, rows, cells


def cells_of(rows, row):
    return [cell.strip() for cell in rows[row][:62].split('│')[1:-1]]


def right_panel(rows, row, label):
    """The text after a label in the card's right panel, without frame lines or bar cells."""
    card = rows[row][:62]
    text = card.split('┼' if '┼' in card else '├')[-1].rstrip('┤').strip()
    assert text.startswith(label), (label, text)
    return text[len(label):].lstrip('─').rstrip('■').strip()


def painted(cells, row, first, last):
    return sum(1 for c in range(first, last + 1) if cells[row][c][1] == BAR)


@requires.need(archaeology=True, files=('e006-r0001-main.sav', 'GOAL.DAT'))
class OriginalScreens(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from goal2.data.goaldat import load
        from goal2.game.state import from_savestate
        cls.state = from_savestate((ROOT / '.cache/e006-r0001-main.sav').read_bytes())
        cls.goaldat = load((ROOT / '.cache/GOAL.DAT').read_bytes())

    def word(self, record, n):
        country = self.state.countries[record[0]]
        return int.from_bytes(country[2 * (n - 1):2 * n], 'little')

    def test_eighty_cards_print_what_the_original_printed(self):
        from goal2.game.player_card import card
        checked = 0
        for run in RUNS:
            for n, record, rows, cells in screens(run):
                word = self.word(record, n)
                self.assertEqual(self.state.players[word], record, f'run {run} player {n}: record differs')
                c = card(self.state, word, self.goaldat)
                top = cells_of(rows, 7)
                self.assertEqual([int(top[1]), int(top[2]), int(top[3])], [c['age'], c['caps'], c['goals']])
                self.assertEqual(top[4], c['height'])
                self.assertEqual(' '.join(top[5].split()), c['foot'])
                middle = cells_of(rows, 9)
                self.assertEqual(middle[:2], [c['position'], c['club_position']])
                self.assertEqual(middle[-1], c['readiness'])
                for row, (name, word_text, personal) in zip(range(11, 15), c['tactics']):
                    self.assertEqual(right_panel(rows, row, name), word_text + (' P' if personal else ''))
                self.assertEqual(right_panel(rows, 15, 'mark'), c['mark'])
                for row, (name, word_text, bar, _) in zip(range(18, 23), c["characteristics"]):
                    self.assertEqual(right_panel(rows, row, name), word_text, (run, n, name))
                    self.assertEqual(painted(cells, row, 47, 60), bar or 0, (run, n, name))
                for row, (name, value) in zip(range(11, 23), c['skills']):
                    self.assertEqual(painted(cells, row, 10, 35), value, (run, n, name))
                    self.assertTrue(rows[row].startswith('├' + name[:9]))
                # The list beside the card prints the original's code at column 77 (F008);
                # the rebuild shows the left-hand values in lower case (owner, 2026-10-21).
                glyph = bytes([cells[n + 1 if n < 12 else n + 2][77][0]]).decode('cp437')
                self.assertEqual(c['role'], glyph.lower() if record[6] in (3, 7, 10) else glyph)
                self.assertNotIn('ability', c)
                checked += 1
        self.assertEqual(checked, 80)

    def test_leadership_halves_below_twenty_one(self):
        # [confirmed: F008 1771:30D9, static: E007's players are all 22..34] v = (+3 - +5) mod 8,
        # halved when the age byte +1 < 0x15.
        import copy
        from goal2.game.player_card import card
        state = copy.deepcopy(self.state)
        word = self.word(state.players[1], 1)
        found = {}
        for age in (0x14, 0x15):
            record = bytearray(state.players[word]);record[1] = age;record[5] = 2;record[3] = 2 + 6
            state.players[word] = bytes(record)
            found[age] = next((bar, raw) for name, _, bar, raw in card(state, word, self.goaldat)['characteristics'] if name == 'leadership')
        self.assertEqual(found, {0x14: (3 * 14 // 7, 3), 0x15: (6 * 14 // 7, 6)})

    def test_out_of_domain_bytes_are_unavailable_not_invented(self):
        import copy
        from goal2.game.player_card import card, UNAVAILABLE
        state = copy.deepcopy(self.state)
        word = self.word(state.players[1], 1)
        record = bytearray(state.players[word])
        record[7] = 14;record[0x0E] = 200;record[3], record[5] = 0, 5
        state.players[word] = bytes(record)
        c = card(state, word, self.goaldat)
        self.assertEqual((c['height'], c['foot'], c['club_position'], c['club_role']), (UNAVAILABLE, UNAVAILABLE, UNAVAILABLE, '?'))
        self.assertEqual(c['skills'][0][1], None)
        found = {name: (word_text, bar) for name, word_text, bar, _ in c['characteristics']}
        self.assertEqual(found['energy'], (UNAVAILABLE, None))
        self.assertEqual(found['leadership'], (UNAVAILABLE, None))


if __name__ == '__main__':
    unittest.main()
