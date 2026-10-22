"""[designed: owner, 2026-10-22, #312; T101] Screens fit without scrolling: one fixed page of
1440x900, scaled to the window.

Each Qt scale runs in a child process (QT_SCALE_FACTOR is read once, when Qt starts), offscreen so
that a window larger than the screen is not clamped by the platform (the Windows runner's screen is
1024x768). The child opens the management window and the launch window, shows every page and view
at each window size and runs the shared no-scroll check (goal2.desktop.fixed_page.problems); it
also records the page's scale and geometry at each size, and sends a click and a key at 900x640
through the window itself (the platform's hit test, not a widget-targeted event).
"""
import json
import os
from pathlib import Path
import subprocess
import sys
import unittest

from goal2.tests import requires

requires.require(modules=('PySide6',), **requires.HALFTIME)

ROOT = Path(__file__).resolve().parents[2]
SIZES = ((1440, 900), (1050, 780), (900, 640), (2560, 1600))
SCALES = ('1', '2')
# (screen name, page index or 'launch', the window attribute holding the page's views, view index)
SCREENS = (('Country desk', 0, 'country_views', 0), ('Country card', 0, 'country_views', 1),
           ('Country other games', 0, 'country_views', 2),
           ('Team card view', 1, 'team_views', 0), ('Team tactics view', 1, 'team_views', 1),
           ('Pool browser', 2, 'pool_views', 0), ('Pool cards', 2, 'pool_views', 1),
           ('Fixtures preparation', 3, 'fixture_views', 0), ('Fixtures result', 3, 'fixture_views', 1),
           ('Fixtures half time', 3, 'fixture_views', 2), ('Fixtures list', 3, 'fixture_views', 3),
           ('Save', 4, None, 0), ('Country desk, bars retracted', 0, 'bars', 0),
           ('Launch', 'launch', None, 0), ('Launch countries', 'launch', None, 1),
           ('Launch review', 'launch', None, 2), ('Launch players', 'launch', None, 3))


def child():
    """Run in a fresh process; prints one JSON report."""
    from PySide6.QtCore import QPoint, Qt
    from PySide6.QtTest import QTest
    from PySide6.QtWidgets import QApplication
    from goal2.desktop.model import DesktopModel
    from goal2.desktop.window import ManagementWindow
    from goal2.desktop.launch import LaunchWindow
    from goal2.desktop.worker import play
    from goal2.desktop import fixed_page
    app = QApplication([])
    report = {'ratio': None, 'screens': {}, 'scales': [], 'input': {}}
    model = DesktopModel.open(ROOT / '.cache/e010-r0008-halftime.sav', ROOT / '.cache/GOAL.DAT',
                              ROOT / '.cache/never-written.g2save', country=8)
    # A completed quick result, so the desk's last result and the result view hold real text.
    model.confirm(list(model.state.starting_eleven), model.state.starting_eleven[0], model.state.country_tactics)
    model.state = play(model.state, model.template_bytes)
    w = ManagementWindow(model);w.show();w.activateWindow();QTest.qWaitForWindowActive(w)
    report['ratio'] = w.devicePixelRatioF()
    launch = LaunchWindow(ROOT / '.cache/GOAL.DAT', ROOT / '.cache/e010-r0008-halftime.sav',
                          ROOT / '.cache/never-written.g2save', lambda m: None)

    def settle():
        app.processEvents();QTest.qWait(20);app.processEvents()

    def show(name, page, views, view):
        if page == 'launch':
            launch.show_page(view) if view in (0, 1) else (launch.review() if view == 2 else launch.show_players())
            if view == 1:launch.preview()
            return launch
        w.set_bars(top=True, side=True);w.navigate(page)
        if views == 'bars':
            w.set_bars(top=False, side=False)
        elif views is not None:
            stack = getattr(w, views)
            stack.show_view(view)
            if views == 'fixture_views' and view == 1:
                from goal2.desktop.fixtures_page import open_result
                open_result(w)
        return w

    for width, height in SIZES:
        for window in (w, launch):
            window.show();window.resize(width, height)
        settle()
        for name, page, views, view in SCREENS:
            try:
                window = show(name, page, views, view);settle()
                found = fixed_page.problems(window)
                if (window.width(), window.height()) != (width, height):
                    found.append(f'window is {window.width()}x{window.height()}, not {width}x{height}')
            except Exception as exc:  # an absent page or view is a failure of the check, not of the run
                found = [f'{type(exc).__name__}: {exc}']
            report['screens'].setdefault(name, []).append({'size': [width, height], 'problems': found})
        for label, window in (('management', w), ('launch', launch)):
            frame = window.centralWidget();page = getattr(frame, 'page', frame)
            report['scales'].append({'window': label, 'size': [width, height],
                                     'area': [frame.width(), frame.height()],
                                     'page': list(page.geometry().getRect()),
                                     'scale': getattr(frame, 'scale', None)})
    # A click and a key at 900x640, through the window: the platform finds the widget at the point.
    w.set_bars(top=True, side=True);w.resize(900, 640);w.navigate(1);w.team_view(0)
    w.activateWindow();QTest.qWaitForWindowActive(w);settle()
    strip = w.team_roster;row = 5
    rect = strip.row_rect(row);point = strip.mapTo(w, rect.center())
    target = w.childAt(point)
    QTest.mouseClick(w.windowHandle(), Qt.MouseButton.LeftButton, pos=point);settle()
    clicked = {'target': target.objectName() if target else None, 'current': strip.current,
               'table_row': w.table.currentRow(), 'focus': w.focusWidget().objectName() if w.focusWidget() else None}
    before = strip.current
    QTest.keyClick(w.windowHandle(), Qt.Key.Key_Down);settle()
    keyed = {'before': before, 'after': strip.current, 'focus': w.focusWidget().objectName() if w.focusWidget() else None}
    route = w.team_tactics_route;point = route.mapTo(w, route.rect().center())
    QTest.mouseClick(w.windowHandle(), Qt.MouseButton.LeftButton, pos=point);settle()
    routed = {'view': w.team_views.currentIndex(), 'focus': w.focusWidget().objectName() if w.focusWidget() else None}
    first = w.tactics[0][1];was = first.isChecked()
    QTest.keyClick(w.windowHandle(), Qt.Key.Key_Space);settle()
    toggled = {'element': first.element, 'changed': first.isChecked() != was}
    # A drop-down opens at its scaled place: the captain list's popup touches its combo box.
    combo = w.captain;combo.showPopup();settle()
    popup = combo.view().window().geometry();box = combo.rect().translated(combo.mapToGlobal(QPoint(0, 0)))
    dropped = {'visible': combo.view().isVisible(), 'popup': list(popup.getRect()), 'combo': list(box.getRect())}
    combo.hidePopup();settle()
    report['input'] = {'scale': w.centralWidget().scale, 'click': clicked, 'key': keyed, 'route': routed,
                       'space': toggled, 'dropdown': dropped}
    launch.close();w.close();app.processEvents()
    print('REPORT ' + json.dumps(report))


def run_child(scale):
    env = {**os.environ, 'QT_QPA_PLATFORM': 'offscreen', 'QT_SCALE_FACTOR': scale, 'PYTHONDONTWRITEBYTECODE': '1'}
    result = subprocess.run([sys.executable, '-c', 'from goal2.tests.test_fixed_page_t101 import child; child()'],
                            cwd=ROOT, env=env, capture_output=True, text=True, timeout=900)
    lines = [line for line in result.stdout.splitlines() if line.startswith('REPORT ')]
    if result.returncode or not lines:
        raise AssertionError(f'child at scale {scale} failed ({result.returncode}): {result.stderr[-3000:]}')
    return json.loads(lines[-1][len('REPORT '):])


class FixedPage(unittest.TestCase):
    reports = {}

    @classmethod
    def report(cls, scale):
        if scale not in cls.reports:cls.reports[scale] = run_child(scale)
        return cls.reports[scale]

    def no_scroll(self, scale, screen):
        report = self.report(scale)
        self.assertEqual(report['ratio'], float(scale), 'the child did not run at the requested Qt scale')
        checks = report['screens'][screen]
        self.assertEqual([tuple(c['size']) for c in checks], list(SIZES))
        failed = {f"{c['size'][0]}x{c['size'][1]}": c['problems'] for c in checks if c['problems']}
        self.assertFalse(failed, f'{screen} at Qt scale {scale}: {json.dumps(failed, indent=1)}')

    def test_the_page_scale_follows_the_window_with_the_aspect_kept(self):
        for scale in SCALES:
            for entry in self.report(scale)['scales']:
                with self.subTest(scale=scale, **{k: str(v) for k, v in entry.items() if k in ('window', 'size')}):
                    area_w, area_h = entry['area'];x, y, page_w, page_h = entry['page']
                    expected = min(area_w / 1440, area_h / 900)
                    self.assertIsNotNone(entry['scale'], 'no fixed page')
                    self.assertAlmostEqual(entry['scale'], expected, places=6)
                    # Uniform: 1440x900 times the scale, centred, never cut.
                    self.assertLessEqual(abs(page_w - 1440 * expected), 1);self.assertLessEqual(abs(page_h - 900 * expected), 1)
                    self.assertTrue(abs(page_w / page_h - 1.6) < 0.01, (page_w, page_h))
                    self.assertTrue(0 <= x and 0 <= y and x + page_w <= area_w and y + page_h <= area_h)
                    self.assertLessEqual(abs(x - (area_w - page_w) // 2), 1);self.assertLessEqual(abs(y - (area_h - page_h) // 2), 1)
                    # One side fills the window: the page is as large as it can be.
                    self.assertTrue(abs(page_w - area_w) <= 1 or abs(page_h - area_h) <= 1)
            sizes = {tuple(e['size']): e['scale'] for e in self.report(scale)['scales'] if e['window'] == 'management'}
            self.assertLess(sizes[(900, 640)], sizes[(1050, 780)]);self.assertLess(sizes[(1050, 780)], sizes[(1440, 900)])
            self.assertLess(sizes[(1440, 900)], sizes[(2560, 1600)]);self.assertGreater(sizes[(2560, 1600)], 1.5)

    def test_a_click_and_a_key_reach_the_intended_widget_at_900x640(self):
        for scale in SCALES:
            with self.subTest(scale=scale):
                given = self.report(scale)['input']
                self.assertLess(given['scale'], 0.7)
                click = given['click'];key = given['key']
                self.assertEqual(click['target'], 'roster', 'the point is not on the strip')
                self.assertEqual((click['current'], click['table_row'], click['focus']), (5, 5, 'roster'))
                self.assertEqual(key['focus'], 'roster')
                self.assertNotEqual(key['after'], key['before'], 'Down did not reach the strip')
                self.assertEqual(given['route'], {'view': 1, 'focus': 'tactic5'})
                self.assertTrue(given['space']['changed'], 'Space did not reach the focused tactic')
                popup, combo = given['dropdown']['popup'], given['dropdown']['combo']
                self.assertTrue(given['dropdown']['visible'])
                # The popup overlaps or touches its combo box horizontally and vertically.
                self.assertTrue(popup[0] <= combo[0] + combo[2] and combo[0] <= popup[0] + popup[2], (popup, combo))
                self.assertTrue(popup[1] <= combo[1] + combo[3] + 2 and combo[1] <= popup[1] + popup[3] + 2, (popup, combo))


def _no_scroll_test(scale, screen):
    def test(self):
        self.no_scroll(scale, screen)
    test.__doc__ = f'No scroll, nothing outside the page or clipped: {screen}, Qt scale {scale}, ' + \
        ', '.join(f'{w}x{h}' for w, h in SIZES)
    return test


for _scale in SCALES:
    for _index, (_screen, *_rest) in enumerate(SCREENS):
        _slug = ''.join(ch if ch.isalnum() else '_' for ch in _screen.lower()).strip('_')
        setattr(FixedPage, f'test_no_scroll_qt_scale_{_scale}_{_index:02}_{_slug}', _no_scroll_test(_scale, _screen))


if __name__ == '__main__':
    unittest.main()
