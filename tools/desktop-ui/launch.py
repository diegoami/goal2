#!/usr/bin/env python3
"""[designed: T86] Launch window through real input at 1440×900 and 900×640.

Run offscreen (the default) and under `xvfb-run` with QT_QPA_PLATFORM=xcb and
QT_SCALE_FACTOR 1 or 2. Checks that each page's controls are reachable by keyboard and lie
inside the window, then drives Resume, a failed load with Retry and Load another, and New
career → Review → Start with keys only. Original resources stay in the ignored .cache/.
"""
import argparse
import os
from pathlib import Path
import sys
import tempfile
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
ROOT = Path(__file__).resolve().parents[2];sys.path.insert(0, str(ROOT))
from PySide6.QtCore import Qt, QRect  # noqa: E402
from PySide6.QtTest import QTest  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402
from goal2.desktop.launch import LaunchWindow  # noqa: E402
from goal2.desktop.model import DesktopModel  # noqa: E402

SIZES = ((1440, 900), (900, 640))


def main():
    p = argparse.ArgumentParser();p.add_argument('--template', required=True, type=Path)
    p.add_argument('--data', required=True, type=Path);args = p.parse_args()
    app = QApplication.instance() or QApplication([])
    receipts = []
    with tempfile.TemporaryDirectory() as folder:
        save = Path(folder) / 'career.g2save'
        model = DesktopModel.open(args.template, args.data, save, country=4)
        model.new_campaign(4, 1992);model.save(save);saved = save.read_bytes()
        broken = Path(folder) / 'broken.g2save';broken.write_bytes(b'broken')
        for width, height in SIZES:
            opened = []
            w = LaunchWindow(args.data, args.template, save, opened.append)
            w.resize(width, height);w.show();QTest.qWaitForWindowExposed(w);app.processEvents()
            assert (w.width(), w.height()) == (width, height), f'window refused {width}×{height}: {w.size()}'

            def key(k):
                QTest.keyClick(w.focusWidget() or w, k);app.processEvents()

            def reachable(page):
                """Tab from the page's first control visits every enabled control, each inside the window."""
                controls = w.focusables();seen = []
                for _ in range(3 * len(controls)):
                    focus = w.focusWidget()
                    if focus in controls and focus not in seen:seen.append(focus)
                    key(Qt.Key.Key_Tab)
                missing = [c.objectName() for c in controls if c not in seen]
                assert not missing, f'{page} {width}×{height}: not reachable by Tab: {missing}'
                client = QRect(0, 0, w.width(), w.height())
                for c in controls:
                    box = QRect(c.mapTo(w, c.rect().topLeft()), c.size())
                    assert client.contains(box), f'{page} {width}×{height}: {c.objectName()} {box} outside {client}'
                    assert c.height() >= 24, f'{page} {width}×{height}: {c.objectName()} squeezed to {c.height()} px'
                return len(controls)

            counts = [reachable('launch')]
            # Failure keeps everything and offers Retry / Load another, by keys only.
            w.other_path.setFocus();w.other_path.selectAll();QTest.keyClicks(w.other_path, str(broken));key(Qt.Key.Key_Return)
            assert 'invalid session save JSON' in w.error.text() and not w.resume.isEnabled() and w.retry.isVisible()
            assert save.read_bytes() == saved and not opened
            w.other_path.setFocus();w.other_path.selectAll();QTest.keyClicks(w.other_path, str(save));key(Qt.Key.Key_Return)
            assert w.focusWidget() is w.resume and w.error.text() == ''
            # New career → Review → back → Start, keys only.
            w.new_career.setFocus();key(Qt.Key.Key_Return)
            assert w.pages.currentIndex() == 1;counts.append(reachable('browse'))
            w.country_list.setFocus();key(Qt.Key.Key_Home)
            for _ in range(6):key(Qt.Key.Key_Down)
            w.start_year.setFocus();key(Qt.Key.Key_Down);assert w.start_year.currentData() == 1992
            w.country_list.setFocus();key(Qt.Key.Key_Return)
            assert w.pages.currentIndex() == 2 and w.review_fields['country'].text() == 'Denmark'
            counts.append(reachable('review'))
            w.start.setFocus();key(Qt.Key.Key_Escape);assert w.pages.currentIndex() == 1
            w.country_list.setFocus();key(Qt.Key.Key_Return);w.start.setFocus();key(Qt.Key.Key_Return)
            assert len(opened) == 1 and opened[0].state.managed_country == 7 and opened[0].state.campaign.stage == 2
            assert save.read_bytes() == saved, 'starting a career wrote the save'
            # Resume through Enter in a fresh window.
            again = []
            r = LaunchWindow(args.data, args.template, save, again.append);r.resize(width, height);r.show()
            QTest.qWaitForWindowExposed(r);QTest.keyClick(r.focusWidget(), Qt.Key.Key_Return);app.processEvents()
            assert len(again) == 1 and again[0].state == DesktopModel.from_save(save, args.data).state
            for window in (w, r):window.close();window.deleteLater()
            app.processEvents()
            receipts.append(f'{width}×{height}: {"/".join(map(str, counts))} controls')
        platform, ratio = app.platformName(), app.primaryScreen().devicePixelRatio()
        # The real entry (last: it shuts the application down): no --resume/--country opens
        # Launch; Enter resumes into management.
        from PySide6.QtCore import QTimer
        from goal2.desktop.__main__ import main as desktop_main
        from goal2.desktop.window import ManagementWindow
        seen = []
        def drive():
            launch = [x for x in app.topLevelWidgets() if isinstance(x, LaunchWindow) and x.isVisible()]
            seen.append(len(launch))
            if launch:QTest.keyClick(launch[0].focusWidget(), Qt.Key.Key_Return)
            QTimer.singleShot(300, finish)
        def finish():
            managed = [x for x in app.topLevelWidgets() if isinstance(x, ManagementWindow) and x.isVisible()]
            seen.append([x.model.state.managed_country for x in managed])
            app.closeAllWindows();app.quit()
        QTimer.singleShot(300, drive)
        code = desktop_main(['--template', str(args.template), '--data', str(args.data), '--save', str(save)])
        assert code == 0 and seen == [1, [4]], (code, seen)
        assert save.read_bytes() == saved
    print(f"PASS launch window ({platform}, ratio {ratio:g}): keyboard reach and in-window geometry on every page, "
          f"failed load kept the save, Retry/Load another, New career → Review → Start, Resume by Enter, real entry Launch → management; "
          + '; '.join(receipts))


if __name__ == '__main__':
    main()
