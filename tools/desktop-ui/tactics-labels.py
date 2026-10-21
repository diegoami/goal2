#!/usr/bin/env python3
"""[confirmed: F010] Verify Qt tactic labels and their existing bit positions."""
from navigation import reveal
import argparse
import gc
from pathlib import Path
import sys
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from PySide6.QtCore import QCoreApplication, QEvent, Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

from goal2.desktop.model import DesktopModel
from goal2.desktop.window import ManagementWindow, TACTICS


def destroy_window(app, window):
    """[designed] Stop and delete the owned Qt tree before the application exits."""
    destroyed = []
    window.destroyed.connect(lambda *_: destroyed.append(True))
    window.timer.start()
    window.close()
    assert not window.timer.isActive(), "window close did not stop its owned timer"
    window.deleteLater()
    QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
    app.processEvents()
    assert destroyed, "management window deferred deletion did not complete"
    assert not app.topLevelWidgets(), "top-level Qt widgets remain after window cleanup"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--template", required=True)
    parser.add_argument("--data", required=True)
    args = parser.parse_args()
    app = QApplication.instance() or QApplication([])
    folder = tempfile.TemporaryDirectory()
    window = None
    boxes = {}
    try:
        model = DesktopModel.open(args.template, args.data, Path(folder.name) / "unused.g2save", country=4)
        window = ManagementWindow(model)
        window.show()
        app.processEvents()
        assert tuple(element for element, _ in TACTICS) == (5, 6, 7, 1, 2, 3, 4, 8)
        boxes = dict(window.tactics)
        # [designed: T99] A tactic row carries the TACTICS label as its alternatives.
        labels = {element: box.property("alternatives") for element, box in boxes.items()}
        assert labels[6] == "Sag back to box / stand ground", labels
        assert labels[7] == "Play safe / offside trap", labels
        assert labels[1] == "Stay back / push forward", labels

        for element in (6, 7, 1):
            for box in boxes.values():
                box.setChecked(False)
            reveal(boxes[element]);QTest.mouseClick(boxes[element], Qt.MouseButton.LeftButton)
            assert boxes[element].isChecked(), f"element {element} checkbox did not toggle"
            assert boxes[element].accessibleName().lower().endswith(labels[element].split(" / ")[1]), boxes[element].accessibleName()
            reveal(window.confirm);QTest.mouseClick(window.confirm, Qt.MouseButton.LeftButton)
            expected = 1 << (element - 1)
            assert model.state.country_tactics == expected, (
                f"element {element} must retain mask 0x{expected:02X}; "
                f"got 0x{model.state.country_tactics:02X}"
            )
    finally:
        boxes.clear()
        try:
            if window is not None:
                destroy_window(app, window)
        finally:
            window = None
            gc.collect()
            folder.cleanup()
            app.quit()
            QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
            app.processEvents()
            gc.collect()
            assert not app.topLevelWidgets(), "top-level Qt widgets remain at application shutdown"

    print("PASS Qt tactics labels: elements 1, 6, 7; each checkbox retains its existing bit")


if __name__ == "__main__":
    main()
