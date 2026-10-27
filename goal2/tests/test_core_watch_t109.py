"""[designed: T109] Watched play through the core, with no guest-memory writes by the tests."""
import unittest
import os
from pathlib import Path
import sys
import tempfile
import time

from goal2.tests import requires

NEEDS = dict(modules=('unicorn',), files=('e006-r0001-main.sav', 'GOAL.DAT'))


def live():
    from goal2.core import Core
    from goal2.core.driver import Driver
    d = Driver(Core.start((requires.CACHE / 'e006-r0001-main.sav').read_bytes()).core)
    d.to_menu()
    d.round_start(watch=True)
    d.kick_off()
    return d


@requires.need(**NEEDS)
class Poll(unittest.TestCase):
    def test_one_poll_and_resume(self):
        from goal2.core import Core, views
        d = live()
        self.assertEqual(d.wait.kind, 'match-live')
        self.assertTrue(d.wait.poll)
        first = views.pitch(d.wait.state, 0, 0)
        self.assertEqual(len(first['players']), 22)
        _, lines = views.commentary(d.wait.state)
        self.assertIn(lines[-1]['text'], ' '.join(d.wait.text.split()))
        saved = d.core.save()
        d.live_step()
        self.assertEqual(d.wait.kind, 'match-live')
        self.assertEqual(d.wait.view['slot'], 2)
        other = Core.load(saved)
        other.advance()
        self.assertEqual(other.memory_sha256(), d.core.memory_sha256())
        self.assertEqual(other.keys, d.core.keys)


@requires.need(**NEEDS, slow=True)
class Match(unittest.TestCase):
    @requires.need(files=('e010-r0001-halftime.sav',))
    def test_no_substitutions_left_returns_from_the_pause_screen(self):
        """Use the kept quick half-time state to reach the same original pause routine cheaply; all five
        substitutions are the original's keys, then Enter in play. No memory counter is written by this test."""
        from goal2.core import Core, views
        from goal2.core.driver import Driver
        from goal2.desktop.core_model import CoreModel
        from goal2.tests.test_core_round_t108 import same_line_pairs
        d = Driver(Core.start((requires.CACHE / 'e010-r0001-halftime.sav').read_bytes()).core)
        d.press(13, expect=('match-menu-halftime',))
        pairs = same_line_pairs(views.bench(d.wait.state), 5)
        self.assertEqual(len(pairs), 5)
        for pair in pairs:
            self.assertTrue(d.substitute(*pair)['made'])
        self.assertEqual(views.bench(d.wait.state)['left'], 0)
        d.core.stop_at('match-live', 'substitution-notice', 'match-summary-save-prompt')
        d.play_on()
        self.assertEqual(d.wait.kind, 'match-live')
        d.live_step(13)
        self.assertEqual(d.wait.view['context'], 'pause')
        result = d.request_substitution()
        self.assertIn('no more substitutes', result['refused'])
        self.assertEqual(d.wait.kind, 'match-menu')
        self.assertEqual(d.wait.view['context'], 'pause')
        self.assertTrue(CoreModel(d.core, requires.CACHE / 'GOAL.DAT', '/tmp/zero.g2core').in_round)

    def test_watched_round_request_bench_and_summary(self):
        from goal2.core import Core, views
        from goal2.desktop.core_model import CoreModel
        from goal2.game.watched_pitch import validate
        d = live()
        with tempfile.TemporaryDirectory() as folder:
            model = CoreModel(d.core, requires.CACHE / 'GOAL.DAT', Path(folder) / 'game.g2core')
            state = model.round_step('live_step', 13)
            self.assertEqual(state['stop'], 'pause')
            self.assertFalse(state['bench']['now'])
            model.driver._open_bench()
            self.assertIn('request substitution', d.core.wait.text)
            model.driver.press(27, expect=('match-menu',))
            state = model.round_step('request_substitution')
            self.assertTrue(state['bench']['requested'])
            model.driver._open_bench()
            self.assertIn('cancel substitution request', d.core.wait.text.lower())
            model.driver.press(27, expect=('match-menu',))
            # Same keys after saving and loading give the same next complete pose.
            saved = model.core.save()
            state = model.round_step('play_on')
            copy = CoreModel(Core.load(saved), requires.CACHE / 'GOAL.DAT', Path(folder) / 'copy.g2core')
            other = copy.round_step('play_on')
            self.assertEqual(state['pitch'], other['pitch'])
            self.assertEqual(model.memory_sha256(), copy.memory_sha256())
            poses = 0
            removed = None
            half = notice = summary = False
            commentary = []
            for _ in range(12000):
                stop = state['stop']
                if stop == 'live':
                    frame = dict(state['pitch'], sequence=poses)
                    validate(frame, poses, 0)
                    # Independent raw memory oracle for every signed position and identity.
                    mem = views.Memory(model.state)
                    for slot, _, _, word, x, y, _, hidden in frame['players']:
                        a = mem.ds * 16 + 0x80E8 + 22 * slot
                        self.assertEqual(word, mem.word(a + 13))
                        self.assertEqual([x, y], [int.from_bytes(bytes([mem.byte(a + k)]), 'little', signed=True)
                                                 for k in (0, 1)])
                        self.assertEqual(hidden, mem.word(a) == frame['sentinel'])
                    commentary.extend(state['commentary'])
                    poses += 1
                    state = model.round_step('live_step')
                elif stop == 'replay':
                    # [designed: T140] This match-flow regression explicitly declines replay.
                    state = model.round_step('replay',False)
                elif stop == 'notice':
                    notice = True
                    state = model.round_step('notice', True)
                elif stop in ('half-time', 'stoppage'):
                    half |= stop == 'half-time'
                    bench = state['bench']
                    line = {r['player']: r['line'] for r in bench['squad']}
                    if stop == 'half-time' and removed in bench['bench']:
                        off = next(a for a in bench['eleven'] if line[a] == line[removed])
                        refusal = model.round_step('substitute', off, removed)['substitution']
                        self.assertFalse(refusal['made'])
                        self.assertIn('cannot play', refusal['refused'])
                        self.assertEqual(refusal['left'], bench['left'])
                    off, on = next((a, b) for a in bench['eleven'] for b in bench['bench']
                                   if line[a] == line[b] and line[a] != 'goalkeeper'
                                   and views.player_card(model.state,b)['readiness'] == views.Memory(model.state).code_str(0x1771,0x42AF))
                    before = bench['left']
                    state = model.round_step('substitute', off, on)
                    self.assertTrue(state['substitution']['made'])
                    self.assertEqual(state['substitution']['left'], before - 1)
                    removed = off
                    state = model.round_step('play_on')
                elif stop == 'full-time':
                    state = model.round_step('finish')
                elif stop == 'summary-save':
                    summary = True
                    self.assertIn('save the match summary', model.core.wait.text)
                    path = Path(folder) / 'summary.txt'
                    model.export_summary(path)
                    self.assertIn(state['board']['names'][0], path.read_text())
                    state = model.round_step('summary_done')
                elif stop == 'menu':
                    break
                else:
                    self.fail(f'Unserved stop {stop}')
            else:
                self.fail('Watched round did not end')
            self.assertTrue(half and notice and summary)
            self.assertGreater(poses, 100)
            self.assertGreater(len(commentary), 10)
            self.assertEqual(model.core.wait.kind, 'manager-menu')
            self.assertFalse(model.in_round)
            self.assertNotIn(('match-live', ord('r')), model.driver.log)


@requires.need(**(NEEDS | {'modules': ('unicorn', 'pygame', 'PySide6')}), slow=True)
class Desktop(unittest.TestCase):
    def test_watch_button_starts_the_pitch_from_the_captain_page(self):
        os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
        os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
        os.environ.setdefault('SDL_AUDIODRIVER', 'dummy')
        from PySide6.QtWidgets import QApplication
        from goal2.desktop.core_model import CoreModel
        from goal2.desktop.core_window import CoreWindow
        app = QApplication.instance() or QApplication([])
        with tempfile.TemporaryDirectory() as folder:
            model = CoreModel.open(requires.CACHE / 'e006-r0001-main.sav', requires.CACHE / 'GOAL.DAT',
                                   Path(folder) / 'game.g2core')
            window = CoreWindow(model);window.show();app.processEvents()
            try:
                window.core_routes['play next game'].click()
                self.assertEqual(window.finish_core(60)[0], 'done')
                r = window.core_round
                self.assertEqual(r.views.currentIndex(), 0)
                # [designed: owner, T116] Watch is selected without an extra click.
                self.assertTrue(r.watch.isChecked())
                r.computer.click()
                self.assertFalse(window.save.isEnabled())
                self.assertEqual(window.finish_core(60)[0], 'done')
                self.assertEqual(model.core.wait.kind, 'match-live')
                self.assertEqual(r.views.currentIndex(), 4)
                self.assertIsNotNone(r.viewer)
                self.assertNotIn(('match-live', ord('r')), model.driver.log)
            finally:
                window.close();app.processEvents()

    def test_pitch_enter_close_resume_and_fixed_pages(self):
        os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
        os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
        os.environ.setdefault('SDL_AUDIODRIVER', 'dummy')
        from PySide6.QtWidgets import QApplication
        from goal2.desktop.core_model import CoreModel
        from goal2.desktop.core_window import CoreWindow
        from goal2.desktop.core_viewer import CoreViewer
        from goal2.desktop.fixed_page import problems
        from goal2.desktop.style import load_fonts
        app = QApplication.instance() or QApplication([])
        load_fonts()
        d = live()
        with tempfile.TemporaryDirectory() as folder:
            model = CoreModel(d.core, requires.CACHE / 'GOAL.DAT', Path(folder) / 'core.g2core')
            window = CoreWindow(model)
            # Prevent the automatic resume from launching the viewer until the scripted SDL command is installed.
            r = window.core_round;r.watch_suspended = True
            window.show();app.processEvents()
            state = model.round_step('live_step')
            script = ("import pygame,sys;from goal2.desktop import pygame_viewer as v;"
                      "original=v.status;sent=[False];"
                      "exec(\"def write(p,x):\\n original(p,x)\\n if x.get('frame_sequence',-1)>=0 and not sent[0]:"
                      "\\n  sent[0]=True;pygame.event.post(pygame.event.Event(pygame.KEYDOWN,key=pygame.K_RETURN))\");"
                      "v.status=write;sys.exit(v.main())")
            r.viewer = CoreViewer(state['identity'], command=[sys.executable, '-c', script])
            r.watch_suspended = False
            r.finished('live_step', ('done', state))
            end = time.monotonic() + 20
            while time.monotonic() < end:
                app.processEvents()
                if model.core.wait is not None and model.core.wait.view.get('context') == 'pause' and not window.core_jobs.busy:
                    break
                time.sleep(.005)
            self.assertEqual(model.core.wait.view.get('context'), 'pause', window.status.text())
            self.assertEqual(r.bench.mode, 'pause')
            for width, height in ((1440,900),(1050,780),(900,640),(2560,1600)):
                window.resize(round(.9*width), round(.9*height));app.processEvents();app.processEvents()
                self.assertEqual(problems(window), [], (width, height, problems(window)))
            # Compose the summary view with the same original board reader; this is presentation only,
            # with no change to the paused guest. The complete-match test reaches the actual summary prompt.
            from goal2.desktop.fixtures_page import _board_lines
            from goal2.core import views
            r.summary_board.set_lines(_board_lines(views.board(model.state), 'FULL TIME'))
            r.show(5)
            for width, height in ((1440,900),(1050,780),(900,640),(2560,1600)):
                window.resize(round(.9*width), round(.9*height));app.processEvents();app.processEvents()
                self.assertEqual(problems(window), [], (width, height, problems(window)))
            # Closing the viewer never presses through the pause or runs a hidden match.
            before = model.memory_sha256()
            r.stop_viewer('Closed for test')
            app.processEvents()
            self.assertEqual(model.memory_sha256(), before)
            self.assertIsNone(r.viewer)
            window.close();app.processEvents()

    def test_viewer_failure_and_close_hold_a_resumable_live_wait(self):
        os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
        os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
        os.environ.setdefault('SDL_AUDIODRIVER', 'dummy')
        from PySide6.QtWidgets import QApplication
        from goal2.desktop.core_model import CoreModel
        from goal2.desktop.core_window import CoreWindow
        from goal2.desktop.core_viewer import CoreViewer
        app = QApplication.instance() or QApplication([])
        d = live()
        with tempfile.TemporaryDirectory() as folder:
            model = CoreModel(d.core, requires.CACHE / 'GOAL.DAT', Path(folder) / 'live.g2core')
            window = CoreWindow(model);r = window.core_round;r.watch_suspended = True
            window.show();app.processEvents()
            state = model.round_step('live_step')
            for command in ([sys.executable, '-c', 'raise SystemExit(1)'],
                            [sys.executable, '-c',
                             "import pygame,sys;from goal2.desktop import pygame_viewer as v;"
                             "original=v.status;"
                             "exec(\"def write(p,x):\\n original(p,x)\\n if x.get('frame_sequence',-1)>=0:"
                             "\\n  pygame.event.post(pygame.event.Event(pygame.QUIT))\");"
                             "v.status=write;sys.exit(v.main())"]):
                r.state = state
                r.viewer = CoreViewer(state['identity'], command=command)
                process = r.viewer.process
                r.watch_suspended = False
                r.finished('resume', ('done', state))
                end = time.monotonic() + 10
                while r.viewer is not None and time.monotonic() < end:
                    app.processEvents();time.sleep(.005)
                self.assertIsNone(r.viewer)
                self.assertIsNotNone(process.poll())
                if window.core_jobs.busy:window.finish_core(60)
                self.assertEqual(model.core.wait.kind, 'match-live')
                before = model.memory_sha256()
                for _ in range(5):app.processEvents();time.sleep(.01)
                self.assertEqual(before, model.memory_sha256())
                model.save()
                resumed = CoreModel.from_save(model.save_path, requires.CACHE / 'GOAL.DAT')
                self.assertEqual(resumed.memory_sha256(), before)
                state = model.round_state()
            # Actual restart after a viewer loss, with no new match or kick-off.
            r.state = state
            r.resume_viewer()
            process = r.viewer.process
            end = time.monotonic() + 10
            while not r.viewer.drained and time.monotonic() < end:
                r.viewer.poll();time.sleep(.01)
            self.assertTrue(r.viewer.drained)
            r.stop_viewer('Finished')
            self.assertIsNotNone(process.poll())
            window.close();app.processEvents()


if __name__ == '__main__':
    unittest.main()
