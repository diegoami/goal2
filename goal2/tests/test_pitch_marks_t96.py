"""[designed: T96; confirmed: static 0791:9372, 0791:05C6, 0791:0691, 0791:8537, 0791:A3B6] The
original's pitch marks, officials and draw order."""
import copy
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from goal2.desktop.match_view import Display
from goal2.game.watched_pitch import validate
from goal2.tests import requires
from goal2.tests.test_pygame_pitch_view import sample

ROOT = Path(__file__).resolve().parents[2]
MAGENTA = (255, 85, 255)


def v2(sequence=0, holder=0, referee=(2, 5, False), linesmen=((8, -3), (-8, 4))):
    frame = sample(sequence);frame['version'] = 2
    frame['officials'] = {'referee': list(referee), 'linesmen': [list(l) for l in linesmen], 'holder': holder}
    return frame


class Glyphs(unittest.TestCase):
    def test_the_five_styles_keepers_and_the_player_on_the_ball(self):
        from goal2.desktop.pygame_viewer import glyph, MARKS, DEFAULT_MARKS
        self.assertEqual((len(MARKS), DEFAULT_MARKS), (5, 1), 'five styles; the original starts at 1 (DS:066A)')
        for marks in range(5):
            self.assertEqual(glyph(marks, 1, 'G', 0, 0), '☺', 'keepers are ☺ in every style')
            self.assertEqual(glyph(marks, 12, 'G', 0, 12), '☻', 'a keeper on the ball is ☻')
        self.assertEqual([glyph(0, 5, 'B', 0, h) for h in (0, 5)], ['☺', '☻'])
        self.assertEqual(glyph(1, 5, 'B', 0, 5), 'B', 'role codes; ☻ only replaces ☺')
        # DS:06D4[(slot < 12) xor selector]: 0x11 ◄ at index 0, 0x10 ► at index 1.
        self.assertEqual([glyph(2, s, '', sel, 0) for s in (5, 15) for sel in (0, 1)], ['►', '◄', '◄', '►'])
        self.assertEqual([glyph(3, s, '', 0, 0) for s in (2, 11, 13, 22)], ['H', 'H', 'A', 'A'])
        self.assertEqual([glyph(4, s, '', 0, 0) for s in (2, 6, 11, 13, 22)], ['0', '4', '9', '0', '9'])

    def test_a_glyph_fits_its_cell(self):
        from goal2.desktop.pygame_viewer import layout, marker_size
        for size in ((900, 640), (1440, 900), (2880, 1800)):
            _, (sx, sy) = layout(*size);font = marker_size(sx, sy)
            self.assertLessEqual(font * 0.6, sx + 1e-9);self.assertLessEqual(font, round(sy))


class Frames(unittest.TestCase):
    def test_version_2_carries_strict_officials_and_version_1_stays_valid(self):
        validate(sample(), 0, 0)
        validate(v2(), 0, 0)
        for bad in ({'referee': [1, 1]}, {'referee': [1, 1, 'x']}, {'holder': 256}, {'holder': -1},
                    {'linesmen': [[1, 2]]}, {'linesmen': [[1, 200], [0, 0]]}, {'extra': 1}):
            frame = v2();frame['officials'].update(bad)
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                validate(frame, 0, 0)
        frame = v2();del frame['officials']
        with self.assertRaises(ValueError):
            validate(frame, 0, 0)

    @requires.need(**requires.HALFTIME)
    def test_on_a_real_match_the_holder_is_at_the_ball_and_the_linesmen_on_the_touchlines(self):
        from goal2.desktop.model import DesktopModel
        from goal2.engine.original_match.match import Fixture
        from goal2.game.watched_match import _drive_match, prepare_watched
        m = DesktopModel.open(ROOT / '.cache/e010-r0008-halftime.sav', ROOT / '.cache/GOAL.DAT', Path(tempfile.mkdtemp()) / 'x', country=13)
        state = m.state;pending = state.campaign.next_fixture
        fixture = Fixture(pending.side_a, pending.side_b, int(pending.fixture_id.split(':')[1]))
        frames = []

        class Enough(Exception):
            pass

        def observe(frame):
            frames.append(frame)
            if frame['minute'] >= 20:
                raise Enough
        try:
            _drive_match(state, prepare_watched(state, m.template_bytes, fixture), fixture, delay_byte=0, _observe_pitch=observe)
        except Enough:
            pass
        near = sides = 0;played = [f for f in frames if f['minute'] >= 2]
        for i, frame in enumerate(frames):
            validate(frame, i, frames[i - 1]['watermark'] if i else 0)
        for frame in played:
            o = frame['officials'];bx, by, _ = frame['ball']
            self.assertTrue(1 <= o['holder'] <= 22, 'during play DS:830B is a pitch slot')
            ranked = [p[0] for p in sorted((p for p in frame['players'] if not p[7]), key=lambda p: abs(p[4] - bx) + abs(p[5] - by))]
            near += o['holder'] in ranked[:3]
            sides += sorted(l[0] for l in o['linesmen']) == [-8, 8]
        # The ball travels in passes, so the holder is not always beside it; by chance he would be
        # among the three nearest in 3 of 22 frames (14 %), measured 78 %.
        self.assertGreater(near / len(played), .5, 'the player on the ball (DS:830B) is near the ball')
        self.assertEqual(sides, len(played), 'linesmen run the touchlines, x = ±8 [confirmed: 0791:8C67]')


@requires.need(modules=('pygame',))
class Drawing(unittest.TestCase):
    SIZE = (1440, 900)

    def setUp(self):
        import pygame
        pygame.init();self.screen = pygame.display.set_mode(self.SIZE)
        self.addCleanup(pygame.quit)

    def display(self):
        d = Display('owned')
        d.accept(['owned', 0, 'start', {'countries': ['A', 'B'], 'roles': {'102': 'B', '113': 'C'}, 'managed': 0, 'kind': 'Friendly'}])
        d.accept(['owned', 1, 'pitch', {'rate': 60}])
        return d

    def count(self, colour, point, radius=12):
        x0, y0 = point
        return sum(tuple(self.screen.get_at((x, y)))[:3] == colour for x in range(x0 - radius, x0 + radius) for y in range(y0 - radius, y0 + radius))

    def test_one_glyph_per_cell_last_drawn_wins_ball_hides_and_officials_on_top(self):
        from goal2.desktop import pygame_viewer as viewer
        d = self.display();f = v2(holder=0)
        for p in f['players']:
            p[7] = True
        # Slots 2 (team 1) and 13 (team 0) share a cell; 13 comes after 2 in DS:0883's order.
        f['players'][1][4:8] = [0, 10, 0, False];f['players'][12][4:8] = [0, 10, 0, False]
        f['ball'] = [0, 10, False]
        d.accept(['owned', d.sequence, 'frame', f]);d.advance(0)
        order = viewer.DRAW_ORDER;self.assertLess(order.index(2), order.index(13))
        viewer.render_pitch(self.screen, None, d)
        point = viewer.project(0, 10, self.SIZE)
        self.assertGreater(self.count(viewer.TEAM_COLORS[0], point), 0, 'slot 13 (team 0, drawn later) shows')
        self.assertEqual(self.count(viewer.TEAM_COLORS[1], point), 0, 'slot 2 under it does not')
        self.assertEqual(self.count(viewer.YELLOW, point, 6), 0, 'the ball hides under a player [0791:8F10]')
        for official in ((2, 5), (8, -3), (-8, 4)):
            self.assertGreater(self.count(MAGENTA, viewer.project(*official, self.SIZE)), 0, 'referee and linesmen in magenta')

    def test_a_hidden_referee_is_not_drawn(self):
        from goal2.desktop import pygame_viewer as viewer
        d = self.display();f = v2(referee=(11, 0, True))
        d.accept(['owned', d.sequence, 'frame', f]);d.advance(0)
        viewer.render_pitch(self.screen, None, d)
        # The sentinel (11, 0) lies beyond the margin; the pitch would draw it at the edge, x = 9.5.
        self.assertEqual(self.count(MAGENTA, viewer.project(9.5, 0, self.SIZE)), 0)

    def test_up_down_step_the_marks_in_the_viewer_loop_and_scroll_with_the_commentary_open(self):
        import json, sys
        import pygame
        from goal2.desktop import pygame_viewer as viewer
        def run(keys):
            with tempfile.TemporaryDirectory() as folder:
                packets = [['owned', 0, 'start', ['A', 'B']], ['owned', 1, 'pitch', {'rate': 60}], ['owned', 2, 'frame', v2()]]
                (Path(folder) / 'display').write_text(''.join(json.dumps(p) + '\n' for p in packets))
                seen = [];calls = [0];real = viewer.render_pitch
                def render(*args):
                    seen.append(args[5]);return real(*args)
                def events():
                    calls[0] += 1
                    if calls[0] <= len(keys):
                        return [pygame.event.Event(pygame.KEYDOWN, key=keys[calls[0] - 1])]
                    return [pygame.event.Event(pygame.QUIT)] if calls[0] == len(keys) + 2 else []
                with patch.object(sys, 'argv', ['viewer', folder, 'owned']), patch.object(viewer, 'render_pitch', render), patch('pygame.event.get', events):
                    self.assertEqual(viewer.main(), 0)
                return seen
        self.assertEqual(run([pygame.K_DOWN, pygame.K_DOWN])[-1], 3, 'Down steps forward from the default 1')
        self.assertEqual(run([pygame.K_UP, pygame.K_UP])[-1], 4, 'Up steps back and wraps over 0..4')
        self.assertEqual(run([pygame.K_c, pygame.K_DOWN])[-1], 1, 'with the commentary open, Down scrolls')


if __name__ == '__main__':
    unittest.main()
