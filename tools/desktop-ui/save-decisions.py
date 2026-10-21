#!/usr/bin/env python3
"""[designed: T87] Save, Save as and the replacement/quit decisions through real dialogs.

Run offscreen (the default) and under `xvfb-run` with QT_QPA_PLATFORM=xcb and
QT_SCALE_FACTOR 1 or 2. Each modal question is answered by real key or mouse input on the
real dialog, at 1440×900 and 900×640. Original resources stay in the ignored .cache/.
"""
import argparse
import copy
import os
from pathlib import Path
import sys
import tempfile
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
ROOT = Path(__file__).resolve().parents[2];sys.path.insert(0, str(ROOT))
from PySide6.QtCore import Qt, QTimer, QRect  # noqa: E402
from PySide6.QtTest import QTest  # noqa: E402
from PySide6.QtWidgets import QApplication, QMessageBox, QPushButton  # noqa: E402
from goal2.desktop.model import DesktopModel  # noqa: E402
from goal2.desktop.window import ManagementWindow  # noqa: E402
from goal2.game import session_save  # noqa: E402

SIZES = ((1440, 900), (900, 640))


def main():
    p = argparse.ArgumentParser();p.add_argument('--template', required=True, type=Path)
    p.add_argument('--data', required=True, type=Path);args = p.parse_args()
    app = QApplication.instance() or QApplication([])
    seen = []

    def answer(respond):
        """Answer the next modal dialog with real input, recording its text and buttons."""
        def act():
            box = app.activeModalWidget()
            if box is None:QTimer.singleShot(20, act);return
            buttons = [b for b in box.findChildren(QPushButton) if b.isVisible()]
            screen = QRect(0, 0, box.width(), box.height())
            for b in buttons:
                assert screen.contains(QRect(b.mapTo(box, b.rect().topLeft()), b.size())), f'{b.text()} outside its dialog'
            text = box.text() if isinstance(box, QMessageBox) else box.labelText()
            seen.append((type(box).__name__, text, [b.text() for b in buttons]))
            respond(box, {b.text(): b for b in buttons})
        QTimer.singleShot(20, act)

    def key(widget, k, mod=Qt.KeyboardModifier.NoModifier):
        QTest.keyClick(widget, k, mod);app.processEvents()

    def shortcut(window, k):
        """A real Ctrl+key to the active window, as after any dialog has closed."""
        window.activateWindow();QTest.qWaitForWindowActive(window);window.table.setFocus()
        key(window.table, k, Qt.KeyboardModifier.ControlModifier)

    def press(name):
        """Focus a button by Tab, then Space: keyboard only."""
        def respond(box, buttons):
            for _ in range(10):
                if box.focusWidget() is buttons[name]:break
                key(box.focusWidget() or box, Qt.Key.Key_Tab)
            assert box.focusWidget() is buttons[name], f'{name} not reachable by Tab'
            key(buttons[name], Qt.Key.Key_Space)
        return respond

    def click(name):
        return lambda box, buttons: QTest.mouseClick(buttons[name], Qt.MouseButton.LeftButton)

    def escape(box, buttons):
        key(box.focusWidget() or box, Qt.Key.Key_Escape)

    receipts = []
    for width, height in SIZES:
        with tempfile.TemporaryDirectory() as folder:
            folder = Path(folder);save = folder / 'game.g2save'
            model = DesktopModel.open(args.template, args.data, save, country=4)
            w = ManagementWindow(model);w.resize(width, height);w.show();QTest.qWaitForWindowExposed(w)
            w.activateWindow();QTest.qWaitForWindowActive(w);w.table.setFocus()
            assert (w.width(), w.height()) == (width, height), w.size()
            # Clean game: Ctrl+S saves without a question.
            shortcut(w, Qt.Key.Key_S);assert save.is_file() and not model.unsaved and not seen
            # Unsaved progress: Ctrl+Q asks; Esc cancels and nothing changes.
            state = model.state;model.confirm(list(state.starting_eleven), state.starting_eleven[0], state.country_tactics ^ 1)
            w.refresh();before = copy.deepcopy(model.state);prior = save.read_bytes()
            answer(escape);shortcut(w, Qt.Key.Key_Q)
            assert 'progress confirmed since the last save' in seen[-1][1] and w.isVisible() and model.state == before
            assert seen[-1][2] == ['Save and continue', 'Continue without saving', 'Cancel'], seen[-1]
            # New campaign → Save and continue by mouse: the confirmed state is written, then replaced.
            w.country.setCurrentIndex(w.country.findData(9))
            answer(click('Save and continue'));QTest.mouseClick(w.new, Qt.MouseButton.LeftButton);app.processEvents()
            assert session_save.load(save)[0] == before and model.state.managed_country == 9 and not model.unsaved
            # An unconfirmed draft alone: no Save offered; Continue without saving by keyboard.
            w.tactics[0][1].setChecked(not w.tactics[0][1].isChecked())
            saved_now = save.read_bytes()
            answer(press('Continue without saving'));QTest.mouseClick(w.resume, Qt.MouseButton.LeftButton);app.processEvents()
            assert seen[-1][2] == ['Continue without saving', 'Cancel'] and 'unconfirmed' in seen[-1][1]
            assert model.state.managed_country == 4 and save.read_bytes() == saved_now
            # Save as… from the Game menu onto another existing file: Esc keeps it, Overwrite replaces it.
            other = folder / 'other.g2save';other.write_bytes(b'keep me')
            def type_path_then(respond):
                def typed(box, buttons):
                    line = box.findChild(type(w.path));line.selectAll();QTest.keyClicks(line, str(other))
                    answer(respond);key(line, Qt.Key.Key_Return)  # Enter opens the overwrite question
                return typed
            menu = w.menuBar().actions()[0].menu()
            for respond, expected in ((escape, b'keep me'), (click('Overwrite'), None)):
                answer(type_path_then(respond))
                next(a for a in menu.actions() if a.objectName() == 'menuSaveAs').trigger();app.processEvents()
                assert seen[-1][0] == 'QMessageBox' and 'already exists' in seen[-1][1], seen[-2:]
                if expected:assert other.read_bytes() == expected
                else:assert session_save.load(other)[0] == model.state and model.save_path == other
            # A failing save keeps the quit decision pending: the window stays, the file is unchanged.
            model.confirm(list(model.state.starting_eleven), model.state.starting_eleven[0], model.state.country_tactics ^ 2)
            w.refresh();blocked = folder / 'not-a-directory';blocked.write_text('file')
            model.save_path = blocked / 'game.g2save';prior = other.read_bytes();before = copy.deepcopy(model.state)
            answer(press('Save and continue'));shortcut(w, Qt.Key.Key_Q)
            assert w.isVisible() and model.state == before and other.read_bytes() == prior
            assert 'Cannot save' in w.status.text(), w.status.text()
            # Continue without saving quits.
            answer(press('Continue without saving'));shortcut(w, Qt.Key.Key_Q)
            assert not w.isVisible() and not blocked.is_dir()
            w.deleteLater();app.processEvents()
            receipts.append(f'{width}×{height}: {len(seen)} questions answered')
            seen.clear()
    print(f"PASS save decisions ({app.platformName()}, ratio {app.primaryScreen().devicePixelRatio():g}): Ctrl+S, "
          "Ctrl+Q/Esc cancel, Save and continue by mouse, draft-only Continue by keyboard, Save as overwrite Esc/Overwrite, "
          "failed save keeps the window, Continue without saving quits; " + '; '.join(receipts))


if __name__ == '__main__':
    main()
