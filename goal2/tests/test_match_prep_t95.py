"""[designed: T95; accepted vision #266 screen 05; #243 folded] Match preparation."""
from pathlib import Path
import unittest
from unittest.mock import patch

from goal2.tests import requires

requires.require(modules=('PySide6',), **requires.HALFTIME)

from PySide6.QtCore import Qt  # noqa: E402
from PySide6.QtTest import QTest  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402
from goal2.desktop.model import DesktopModel  # noqa: E402
from goal2.desktop.window import ManagementWindow  # noqa: E402
from goal2.game import roles  # noqa: E402
from goal2.game.session_save import encode  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]


class Preparation(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.model = DesktopModel.open(ROOT / '.cache/e010-r0008-halftime.sav', ROOT / '.cache/GOAL.DAT',
                                       ROOT / '.cache/never-written.g2save', country=13)
        self.window = ManagementWindow(self.model);self.window.resize(1440, 900);self.window.show()
        QTest.qWaitForWindowActive(self.window)
        self.addCleanup(lambda: (self.window.close(), self.window.deleteLater(), self.app.processEvents()))

    def formation(self, words):
        state = self.model.state;_, lines = roles.tables(state)
        return '-'.join(str(sum(1 for w in words if lines[state.players[w][6]] == line)) for line in (1, 2, 3))

    def test_both_elevens_with_formations_and_the_fixture(self):
        w = self.window;state = self.model.state;names = self.model.goaldat.country_names
        fixture = state.campaign.next_fixture;before = encode(state, self.model.template_bytes)
        self.assertEqual(w.prep_title.text(), f'{names[fixture.side_a].upper()} v {names[fixture.side_b].upper()} / FRIENDLY')
        selected = w.selected_ids()
        self.assertEqual([r[0] for r in w.lineup_own.rows], selected)
        self.assertEqual(w.lineup_own.caption, f'GREECE / {self.formation(selected)}')
        other = fixture.side_b if fixture.side_a == 13 else fixture.side_a
        record = state.countries[other];stored = [int.from_bytes(record[2 * i:2 * i + 2], 'little') for i in range(11)]
        self.assertEqual([r[0] for r in w.lineup_other.rows], stored, "the opponent's stored eleven")
        self.assertEqual(w.lineup_other.caption, f'{names[other].upper()} / {self.formation(stored)}')
        codes = roles.tables(state)[0]
        self.assertEqual([r[2] for r in w.lineup_other.rows], [codes[state.players[x][6]] for x in stored])
        # A draft change shows at once and is named as unconfirmed.
        row = state.managed_squad.index(selected[3]);w.table.item(row, 0).setCheckState(Qt.CheckState.Unchecked)
        self.assertEqual(len(w.lineup_own.rows), 10);self.assertIn('Unconfirmed', w.prep_note.text())
        self.assertEqual(encode(self.model.state, self.model.template_bytes), before, 'preparation never changes the game')

    def test_the_chosen_speed_reaches_the_watched_controller(self):
        w = self.window;w.confirm_draft()
        self.assertEqual(w.speed_group.checkedId(), 60, 'Normal keeps the default 60')
        # [confirmed: 0791:9372, speed byte 0..5; owner, 2026-10-21 "Six, as the code"]
        self.assertEqual([(b.text(), w.speed_group.id(b)) for b in w.speed_buttons],
                         [('Slowest', 10), ('Slower', 15), ('Slow', 30), ('Normal', 60), ('Fast', 120), ('Fastest', 240)])
        for name, rate in (('Slowest', 10), ('Slower', 15), ('Slow', 30), ('Fast', 120), ('Fastest', 240), ('Normal', 60)):
            next(b for b in w.speed_buttons if b.text() == name).click()
            w.navigate(0);w.refresh();w.navigate(3)
            self.assertEqual(w.speed_group.checkedId(), rate, 'the choice survives navigation and refresh')
            with patch.object(w.watched, 'start') as start, patch.object(w.watch_timer, 'start'), patch.object(w, 'set_busy'):
                w.start_watched()
            start.assert_called_once_with(playback_rate=rate)
        w.set_busy(True)
        self.assertFalse(any(b.isEnabled() for b in w.speed_buttons), 'the speed is locked while a match runs')
        w.set_busy(False);self.assertTrue(all(b.isEnabled() for b in w.speed_buttons))

    def test_the_country_desk_leads_to_preparation(self):
        w = self.window;w.navigate(0)
        prepare = next(b for b in w.desk_routes if b.text() == 'Prepare match')
        self.assertIs(w.desk_routes[0], prepare);prepare.click()
        self.assertEqual(w.page_stack.currentIndex(), 3)
        self.assertTrue(w.pages[3].isAncestorOf(w.play) and w.pages[3].isAncestorOf(w.watch))


class InMatchSpeed(unittest.TestCase):
    """[confirmed: E031 C39] Left slows the match by one step, Right speeds it up."""
    def display(self, rate=60):
        from goal2.desktop.match_view import Display
        d = Display('owned');d.accept(['owned', 0, 'start', ['A', 'B']]);d.accept(['owned', 1, 'pitch', {'rate': rate}])
        return d

    def test_steps_clamp_and_change_only_pacing(self):
        d = self.display();digest = d.digest()
        self.assertEqual([d.step_rate(-1) for _ in range(4)], [30, 15, 10, 10])
        self.assertEqual([d.step_rate(1) for _ in range(6)], [15, 30, 60, 120, 240, 240])
        self.assertEqual((d.speed_name(), d.digest(), d.sequence), ('Fastest', digest, 2), 'no packet, digest or ACK changes')
        from goal2.desktop.match_view import Display
        self.assertIsNone(Display('x').step_rate(1), 'text-only watching has no pitch pacing')

    def test_a_slower_step_paces_samples_further_apart(self):
        from goal2.tests.test_pygame_pitch_view import sample
        d = self.display()
        for n in range(3):d.accept(['owned', d.sequence, 'frame', sample(n)])
        # A step applies from the next interval: the sample already due at 1/60 s stays due.
        self.assertTrue(d.advance(0));d.step_rate(-1)
        self.assertTrue(d.advance(1 / 60 + .001))
        self.assertFalse(d.advance(2 / 60 + .002), 'at 30/s the next sample is not due 1/60 s later')
        self.assertTrue(d.advance(1 / 60 + 1 / 30 + .002))

    @requires.need(modules=('pygame',))
    def test_the_viewer_loop_applies_left(self):
        import json, sys, tempfile
        import pygame
        from goal2.desktop import pygame_viewer as viewer
        from goal2.tests.test_pygame_pitch_view import sample
        with tempfile.TemporaryDirectory() as folder:
            packets = [['owned', 0, 'start', ['A', 'B']], ['owned', 1, 'pitch', {'rate': 60}], ['owned', 2, 'frame', sample(0)]]
            (Path(folder) / 'display').write_text(''.join(json.dumps(p) + '\n' for p in packets))
            seen = [];calls = [0]
            real = viewer.render_pitch
            def render(*args):
                seen.append(args[2].pitch_rate);return real(*args)
            def events():
                calls[0] += 1
                return [pygame.event.Event(pygame.KEYDOWN, key=pygame.K_LEFT)] if calls[0] == 2 else (
                    [pygame.event.Event(pygame.QUIT)] if calls[0] == 4 else [])
            with patch.object(sys, 'argv', ['viewer', folder, 'owned']), patch.object(viewer, 'render_pitch', render), patch('pygame.event.get', events):
                self.assertEqual(viewer.main(), 0)
        self.assertEqual((seen[0], seen[-1]), (60, 30))


if __name__ == '__main__':
    unittest.main()
