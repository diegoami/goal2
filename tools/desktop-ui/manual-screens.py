#!/usr/bin/env python3
"""[designed: owner, 2026-11-08] Capture every screen of the build as it ships, for the
current-game manual (docs/current-game/README.md).

It is the rebuild's counterpart of the original's capture method
(docs/original-game/capture-method.md): the original's screens are rendered from DOSBox-X
savestates, these are grabbed from the real windows, offscreen, at the fixed page's own
1440x900. Nothing here is a claim about the original; it records what goal2 shows today.

    python3 tools/desktop-ui/manual-screens.py --data .cache/GOAL.DAT \
        --template .cache/e010-r0008-halftime.sav --core .cache/e006-r0001-main.sav \
        --out docs/current-game/images

Each screen is written as `<name>.png` with a row in `<out>/../image-provenance.tsv`:
the route that opened it, how it was reached, and the PNG's SHA-256. A screen that cannot
be reached is reported and the run goes on, so the manual says honestly what is missing.
"""
import argparse
import hashlib
import os
import sys
import tempfile
from pathlib import Path

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from PySide6.QtCore import Qt  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

PAGE = (1440, 900)


# [designed] The real pitch window, with its own post-flip surface saved now and then. It
# renders goal2's own pixels: `pygame_viewer.main` is the shipped viewer, unchanged.
PITCH_VIEWER = r"""
import pathlib, sys, pygame
out = pathlib.Path(sys.argv.pop(1)); out.mkdir(parents=True, exist_ok=True)
every = int(sys.argv.pop(1))
from goal2.desktop import pygame_viewer as viewer
flip = pygame.display.flip
seen = [0]
def saving_flip():
    flip()
    surface = pygame.display.get_surface()
    if surface is None:
        return
    seen[0] += 1
    if seen[0] == 1 or seen[0] % every == 0:
        pygame.image.save(surface, str(out / ('pitch-%05d.png' % seen[0])))
pygame.display.flip = saving_flip
sys.exit(viewer.main())
"""



class Shots:
    """Grabs a window into the output folder and keeps a provenance row for each."""

    def __init__(self, out: Path):
        self.out = out
        self.out.mkdir(parents=True, exist_ok=True)
        self.rows = []
        self.missing = []

    def take(self, widget, name, route, reached):
        app = QApplication.instance()
        for _ in range(3):
            app.processEvents()
        path = self.out / f'{name}.png'
        if not widget.grab().save(str(path)):
            self.missing.append((name, 'the grab failed'))
            return
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        self.rows.append((name, f'images/{name}.png', route, reached, digest))
        print(f'  {name:34s} {route:12s} {reached}')

    def skip(self, name, why):
        self.missing.append((name, why))
        print(f'  {name:34s} -- not captured: {why}')

    def write(self, path: Path):
        """Merge this run's rows into the table, keeping rows whose image is still there.

        A run captures one route, so the table is built over several runs; a row whose PNG has
        been deleted goes with it."""
        header = ('screen', 'image', 'route', 'reached', 'png_sha256')
        kept = {}
        if path.exists():
            for line in path.read_text().splitlines()[1:]:
                row = line.split('\t')
                if len(row) == len(header) and (path.parent / row[1]).exists():
                    kept[row[0]] = tuple(row)
        for row in self.rows:
            kept[row[0]] = row
        lines = ['\t'.join(header)] + ['\t'.join(kept[name]) for name in sorted(kept)]
        path.write_text('\n'.join(lines) + '\n')


def show(window):
    window.resize(*PAGE)
    window.show()
    app = QApplication.instance()
    for _ in range(3):
        app.processEvents()
    return window


def views_of(page):
    """The named views of a page (T101's stack), as (index, name) pairs."""
    if page.views is None:
        return []
    return [(i, page.views.widget(i).objectName()) for i in range(page.views.count())]


def capture_window(window, shots, route, prefix, pages):
    """Every destination of a main window, and every view of each destination."""
    for index, label in enumerate(pages):
        try:
            window.navigate(index)
        except Exception as exc:                                     # noqa: BLE001
            shots.skip(f'{prefix}-{label}', f'navigate({index}) raised {exc!r}')
            continue
        page = window.pages[index]
        shots.take(window, f'{prefix}-{label}', route, f'side bar {label!r} (Ctrl+{index + 1})')
        for view_index, view_name in views_of(page):
            if view_index == 0:
                continue                                             # the page's own view, already taken
            try:
                page.views.setCurrentIndex(view_index)
            except Exception as exc:                                 # noqa: BLE001
                shots.skip(f'{prefix}-{label}-{view_name}', f'the view raised {exc!r}')
                continue
            shots.take(window, f'{prefix}-{label}-{view_name}', route,
                       f'{label} -> view {view_name!r}')
        if page.views is not None:
            page.views.setCurrentIndex(0)


def select_country(launch, country):
    """Put the browse list on one country, as an arrow key does, and fill its card."""
    from PySide6.QtCore import Qt as _Qt
    launch.fill_countries()
    for row in range(launch.country_list.count()):
        item = launch.country_list.item(row)
        if item.data(_Qt.ItemDataRole.UserRole) == country:
            launch.country_list.setCurrentRow(row)
            break
    launch.preview()


def drive_launch(launch, shots, route, country, manager='K Ees'):
    """Walk Launch as a player does: the saved career, the countries, a card, the review."""
    launch.show_page(0)
    shots.take(launch, f'{route}-launch-start', route, 'the first window: Resume or New career')
    launch.show_page(1)
    try:
        select_country(launch, country)
    except Exception as exc:                                         # noqa: BLE001
        shots.skip(f'{route}-launch-country', f'selecting the country raised {exc!r}')
    else:
        shots.take(launch, f'{route}-launch-country', route, 'New career, a country chosen')
        try:
            launch.show_players()
        except Exception as exc:                                     # noqa: BLE001
            shots.skip(f'{route}-launch-players', f'show_players raised {exc!r}')
        else:
            shots.take(launch, f'{route}-launch-players', route, 'Space on the country list')
        try:
            launch.review()
            if getattr(launch, 'manager_name', None) is not None:
                launch.manager_name.setText(manager)
        except Exception as exc:                                     # noqa: BLE001
            shots.skip(f'{route}-launch-review', f'review raised {exc!r}')
        else:
            shots.take(launch, f'{route}-launch-review', route, 'Enter on the country list')


def python_route(args, shots):
    """The --template route: Launch, then the management window over a DesktopModel."""
    from goal2.desktop.launch import LaunchWindow
    from goal2.desktop.model import DesktopModel
    from goal2.desktop.window import ManagementWindow

    folder = Path(tempfile.mkdtemp())
    save = folder / 'career.g2save'
    model = DesktopModel.open(args.template, args.data, save, country=args.country)
    model.new_campaign(args.country, 1992)
    model.save(save)

    print('Launch window (the --template route)')
    launch = show(LaunchWindow(args.data, args.template, save, lambda m: None))
    drive_launch(launch, shots, 'template', args.country)
    launch.close()

    print('Management window')
    window = show(ManagementWindow(model))
    capture_window(window, shots, 'template', 'window',
                   ('country', 'team', 'pool', 'fixtures', 'save'))
    print('Retracted bars (F11)')
    try:
        window.set_bars(top=False, side=False)
        shots.take(window, 'window-bars-retracted', 'template', 'F11 on any page')
        window.set_bars(top=True, side=True)
    except Exception as exc:                                         # noqa: BLE001
        shots.skip('window-bars-retracted', f'set_bars raised {exc!r}')
    print('Small window (900x640)')
    window.resize(900, 640)
    QApplication.instance().processEvents()
    shots.take(window, 'window-small', 'template', 'the same page at 900x640')
    window.resize(*PAGE)
    window.close()


def instrument_pitch(out: Path, every=150):
    """Make the window's pitch window save its own frames into `out`."""
    import goal2.desktop.core_viewer as core_viewer
    first = core_viewer.CoreViewer.__init__
    command = [sys.executable, '-c', PITCH_VIEWER, str(out), str(every)]

    def opened(self, *args, **kwargs):
        kwargs['command'] = command
        return first(self, *args, **kwargs)

    core_viewer.CoreViewer.__init__ = opened
    os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')


def import_dialog(shots):
    """[designed: T153] The first window of a first start: the data import."""
    from goal2.desktop import data_setup
    folder = Path(tempfile.mkdtemp())
    target = data_setup.paths(folder)
    dialog = data_setup.make_dialog(target, choose=lambda: None)
    dialog.resize(760, 260)
    dialog.show()
    QApplication.instance().processEvents()
    shots.take(dialog, 'import-data-folder', 'first start',
               "the first start, with no data folder yet (data_setup.make_dialog)")
    dialog.status.setText('That folder has no GOAL.DAT.')
    shots.take(dialog, 'import-data-refused', 'first start',
               'the same dialog after a folder it cannot take')
    dialog.close()


def play_round(window, shots, route, seconds=1800, watch=False):
    """[designed: T108] Play the next game on the core and capture every stop it makes.

    The captain's stop takes Q (the original's quick result), so the round is played without
    the separate pitch window; every other stop takes the action the screen advertises, as a
    player pressing Enter does.
    """
    import time
    from PySide6.QtCore import Qt as _Qt
    from PySide6.QtTest import QTest
    app = QApplication.instance()
    window.navigate(3)
    round_ = window.core_round
    shots.take(window, f'{route}-round-before', route, 'Fixtures & match before playing')
    round_.start()
    seen, deadline, guard = set(), time.monotonic() + seconds, 0
    while time.monotonic() < deadline and guard < 400:
        app.processEvents()
        time.sleep(0.02)
        if window.core_jobs.busy:
            continue
        state = round_.state or {}
        stop = state.get('stop', 'start')
        view = round_.views.currentIndex()
        # A page view shows one original page at a time: its text tells one from the next.
        board = round_.page_board.text() if view == 2 else ''
        key = (stop, view, board.strip()[:160])
        if key not in seen:
            seen.add(key)
            shots.take(window, f'{route}-round-{len(seen):02d}-{stop}', route,
                       f'the round stopped at {stop!r} (view {view})')
        guard += 1
        if window.page_stack.currentIndex() != 3 and len(seen) > 2:
            break                                   # the round ended: the window went back
        if view == 0:                                   # the captain
            button = round_.kick_off if watch else round_.quick
            if button.isEnabled():
                button.click()
                continue
        if view == 1:                                   # the bench: play on, making no change
            play = getattr(round_.bench, 'play', None)
            if play is not None and play.isEnabled():
                play.click()
                continue
        target = window.focusWidget()
        if target is None or not target.isEnabled():
            break
        QTest.keyClick(target, _Qt.Key.Key_Return)
    shots.take(window, f'{route}-round-after', route, 'the page the round ends on')


def boot_route(args, shots):
    """[designed: T106] The route a player gets from the portable build: Launch over the
    original's own new game, its bulletins, then the main window on the core."""
    from goal2.desktop.launch import LaunchWindow
    from goal2.desktop.window import window_for

    folder = Path(tempfile.mkdtemp())
    save = folder / 'career.g2core'
    opened = []
    print('Launch window (the player\'s own route: --core-boot)')
    launch = show(LaunchWindow(args.data, None, save, opened.append, core_boot=args.core_boot))
    drive_launch(launch, shots, 'boot', args.country)
    print('Starting the original\'s new game (this runs the original; it takes a while)')
    try:
        launch.do_start()
    except Exception as exc:                                         # noqa: BLE001
        shots.skip('boot-bulletin', f'starting raised {exc!r}')
        launch.close()
        return
    for page in range(len(getattr(launch, 'bulletins', ()))):
        launch.show_bulletin(page)
        shots.take(launch, f'boot-bulletin-{page + 1}', 'boot',
                   f'bulletin {page + 1} of {len(launch.bulletins)} after starting')
    if not opened:
        launch.show_bulletin(len(getattr(launch, 'bulletins', ())))   # past the last: the window opens
    launch.close()
    if not opened:
        shots.skip('boot-window', 'the new game did not open a window')
        return
    print('The main window on the new career')
    window = show(window_for(opened[0]))
    capture_window(window, shots, 'boot', 'boot',
                   ('country', 'team', 'pool', 'fixtures', 'save'))
    if args.round:
        print('Playing the next game on the core (the original plays it; this takes minutes)')
        try:
            if args.pitch:
                instrument_pitch(args.out.parent / 'pitch-frames')
            play_round(window, shots, 'boot', watch=bool(args.pitch))
        except Exception as exc:                                     # noqa: BLE001
            shots.skip('boot-round-*', f'the round raised {exc!r}')
    window.close()


def core_route(args, shots):
    """The --core route: the same shell over the original's own game."""
    from goal2.desktop.core_model import CoreModel
    from goal2.desktop.window import window_for

    folder = Path(tempfile.mkdtemp())
    save = folder / 'career.g2core'
    model = CoreModel.open(args.core, args.data, save)
    print('Core window (the original\'s own game as goal2\'s core)')
    window = show(window_for(model))
    pages = tuple(name.lower().split()[0] for name in ('Country', 'Team', 'Pool',
                                                       'Fixtures', 'Save'))
    capture_window(window, shots, 'core', 'core', pages)
    window.close()


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--data', required=True, type=Path, help='GOAL.DAT in .cache')
    p.add_argument('--template', type=Path, help='a savestate for the --template route')
    p.add_argument('--core', type=Path, help='a savestate for the --core route')
    p.add_argument('--core-boot', type=Path, dest='core_boot',
                   help="the date-call savestate: the player's own new-game route")
    p.add_argument('--country', type=int, default=4, help='the country the capture manages')
    p.add_argument('--import-dialog', action='store_true', dest='import_dialog',
                   help='also capture the first start\'s data import dialog')
    p.add_argument('--pitch', action='store_true',
                   help='watch the match, so the pitch window saves its own frames')
    p.add_argument('--round', action='store_true',
                   help='also play the next game and capture every stop it makes')
    p.add_argument('--out', type=Path, default=ROOT / 'docs/current-game/images')
    args = p.parse_args()

    QApplication.instance() or QApplication([])
    shots = Shots(args.out)
    if args.import_dialog:
        print('The import dialog')
        import_dialog(shots)
    if args.core_boot:
        try:
            boot_route(args, shots)
        except Exception as exc:                                     # noqa: BLE001
            shots.skip('boot-*', f'the new-game route raised {exc!r}')
    if args.template:
        python_route(args, shots)
    if args.core:
        try:
            core_route(args, shots)
        except Exception as exc:                                     # noqa: BLE001
            shots.skip('core-*', f'the core route raised {exc!r}')
    shots.write(args.out.parent / 'image-provenance.tsv')
    print(f'\n{len(shots.rows)} screens in {args.out}')
    if shots.missing:
        print('not captured:')
        for name, why in shots.missing:
            print(f'  {name}: {why}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
