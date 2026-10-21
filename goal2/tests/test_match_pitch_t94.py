"""[designed: T94; owner, 2026-10-21 (#283 folded into #262)] The watched pitch's identity."""
import copy
from pathlib import Path
import tempfile
import unittest

from goal2.desktop.match_view import Display
from goal2.tests import requires

ROOT = Path(__file__).resolve().parents[2]
RIGHT, LEFT = set('BMW'), set('bmw')  # [designed: owner, 2026-10-21] low capital for left


class Identity(unittest.TestCase):
    def start(self, value):
        d = Display('owned');d.accept(['owned', 0, 'start', value]);return d

    def test_a_strict_identity_packet(self):
        good = {'countries': ['A', 'B'], 'roles': {'5': 'G', '6': 'Ç'}, 'managed': 1, 'kind': 'Qualifier'}
        d = self.start(copy.deepcopy(good))
        self.assertEqual((d.countries, d.roles, d.managed, d.kind), (['A', 'B'], {5: 'G', 6: 'Ç'}, 1, 'Qualifier'))
        self.assertEqual((d.code(6, 3), d.code(7, 3)), ('Ç', '3'), 'a word without a role shows its slot number')
        self.assertEqual(self.start(['A', 'B']).roles, {}, 'the two-country form still works')
        for change in ({'roles': {'x': 'G'}}, {'roles': {'5': 'GK'}}, {'roles': {'0': 'G'}}, {'roles': {'3061': 'G'}},
                       {'managed': 2}, {'managed': True}, {'kind': ''}, {'kind': 'x' * 41}, {'countries': ['A']},
                       {'extra': 1}):
            with self.subTest(change=change), self.assertRaises(ValueError):
                self.start({**good, **change})


@requires.need(**requires.HALFTIME)
class FromTheGame(unittest.TestCase):
    def model(self, country=13):
        from goal2.desktop.model import DesktopModel
        folder = tempfile.mkdtemp()
        return DesktopModel.open(ROOT / '.cache/e010-r0008-halftime.sav', ROOT / '.cache/GOAL.DAT', Path(folder) / 'x', country=country)

    def test_both_squads_codes_managed_side_and_kind(self):
        from goal2.desktop.watched import pitch_identity
        from goal2.game import roles
        m = self.model();state = m.state;fixture = state.campaign.next_fixture
        identity = pitch_identity(m, fixture)
        sides = [fixture.side_a, fixture.side_b]
        self.assertEqual(identity['countries'], [m.goaldat.country_names[c] for c in sides])
        self.assertEqual(identity['managed'], sides.index(13));self.assertEqual(identity['kind'], 'Friendly')
        codes = roles.tables(state)[0];other = fixture.side_b if fixture.side_a == 13 else fixture.side_a
        record = state.countries[other]
        expected = list(state.managed_squad) + [int.from_bytes(record[2 * i:2 * i + 2], 'little') for i in range(20)]
        self.assertEqual(identity['roles'], {str(w): codes[state.players[w][6]] for w in expected})
        Display('owned').accept(['owned', 0, 'start', identity])  # the parent's packet is valid

    def test_sides_on_the_real_pitch(self):
        """[confirmed: F013 (x down, y right)] In a real original match, a side attacking right
        (its goalkeeper at negative y) has its right-side players (B, M, W) below its left-side
        ones (b, m, w), and a side attacking left has them above."""
        from goal2.desktop.watched import pitch_identity
        from goal2.engine.original_match.match import Fixture
        from goal2.game.watched_match import _drive_match, prepare_watched
        m = self.model();state = m.state;pending = state.campaign.next_fixture
        codes = {int(w): c for w, c in pitch_identity(m, pending)['roles'].items()}
        fixture = Fixture(pending.side_a, pending.side_b, int(pending.fixture_id.split(':')[1]))
        checked = []

        class Enough(Exception):
            pass

        def observe(frame):
            if frame['minute'] < 5:
                return
            for team in (0, 1):
                rows = [(codes.get(w), x, y) for _, t, _, w, x, y, _, hidden in frame['players'] if t == team and not hidden]
                keeper = [y for c, x, y in rows if c == 'G']
                right = [x for c, x, y in rows if c in RIGHT];left = [x for c, x, y in rows if c in LEFT]
                if not keeper or not right or not left or keeper[0] == 0:
                    continue
                attacking_right = keeper[0] < 0
                mean = lambda v: sum(v) / len(v)
                checked.append(mean(right) > mean(left) if attacking_right else mean(right) < mean(left))
            if len(checked) >= 4000:
                raise Enough

        try:
            _drive_match(state, prepare_watched(state, m.template_bytes, fixture), fixture, delay_byte=0, _observe_pitch=observe)
        except Enough:
            pass
        self.assertGreaterEqual(len(checked), 4000)
        # Players roam, so not every sample agrees; a mirrored pitch would agree in few of them.
        share = sum(checked) / len(checked)
        self.assertGreater(share, .75, f'right-side players are not on the right of their side ({share:.1%})')


if __name__ == '__main__':
    unittest.main()
