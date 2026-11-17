"""[designed: owner, 2026-11-08, #667, #668; T210] The grid check: which widgets are off the 16 x 32 cell, and which are cards.

[designed: owner, 2026-11-08; docs/design/ui-2026-11/fidelity-review.md §3] Every edge of a panel is a whole number of cells
and a panel has no card (a bordered box with an uppercase cyan heading): its frame is a rule with a label (goal2/ui/frame.py).
`off_grid(window)` walks the visible widgets the page composes and reports each rectangle whose x, y, width or height is not a
multiple of the cell, and `cards(window)` each card the theme's `#box` and `#boxHeading` still draw; `violations` is both.

What a multiple is, on a page that is pixels and not cells [designed: T210]:
- The cell is `theme.CELL_W` x `theme.CELL_H`, at the page's horizontal scale and at its vertical one (scale x the 1.2
  stretch): 16 x 38.4 pixels at scale 1. A page length is rounded to pixels (`fixed_page.px`) and so is a line of text (a 38 px
  font at scale 1), so a row is 38 pixels in a layout and 38.4 in the grid. A value is on the grid when it is within a pixel of
  a multiple of the exact cell, of the cell rounded down or of the cell rounded up (a platform's font may add a hinted pixel to
  a line).
- The page is 4:3 (1440 x 1080 at scale 1) and the grid 28 rows (1075.2): the few pixels left over are taken up by the widget
  that stretches, never by the cell. So a vertical (or horizontal) value is also on the grid when it is on it after taking
  off that slack: the foot of a page sits on the grid counted from the bottom.
- A widget with no size is not drawn and is not checked, and Qt's internal parts (`qt_` names, and what is inside them) are
  not the page's own.

The check is meant at a scale where a cell is whole pixels (1440 x 1080, scale 1) and is exact there; at other scales it is
true to a pixel per cell of drift. It reports; it never moves anything.
"""
from __future__ import annotations

import math

from PySide6.QtCore import QPoint
from PySide6.QtWidgets import QWidget

from goal2.desktop import fixed_page
from goal2.ui import theme

# The theme's card and its heading [confirmed: goal2/ui/theme.py `#box`, `#boxHeading`]: what the frame replaces.
CARD_NAMES = ("box", "boxHeading")
TOLERANCE = 1.0   # pixels


def page_of(window) -> tuple[QWidget, float, float]:
    """The page a window shows and its cell in pixels (horizontal, vertical). A widget that is not a window with a fixed page
    is its own page, at scale 1 and without the stretch."""
    host = fixed_page.host(window) if hasattr(window, "centralWidget") else None
    if host is None:
        return window, float(theme.CELL_W), float(theme.CELL_H)
    scale = host.scale
    return host.page, theme.CELL_W * scale, theme.CELL_H * host.stretch * scale


def on_grid(value: float, cell: float, slack: float = 0.0, size: bool = False) -> bool:
    """Whether `value` (pixels) is a whole number of cells of `cell` pixels, within `TOLERANCE`: as the exact cell, as the cell
    rounded down or up, each with or without the page's `slack` taken off. A size is at least one cell (0 is not a size)."""
    pitches = {cell, float(math.floor(cell)), float(math.ceil(cell))}
    for pitch in pitches:
        for offset in {0.0, slack}:
            count = (value - offset) / pitch
            low = 1 if size else 0
            near = max(low, round(count))
            if abs(value - offset - near * pitch) <= TOLERANCE:
                return True
    return False


def _inside_qt(widget: QWidget, page: QWidget) -> bool:
    """Whether `widget` is a Qt internal part or inside one (a combo's list, a scroll area's corner)."""
    while widget is not None and widget is not page:
        if widget.objectName().startswith("qt_") or widget.isWindow():
            return True
        widget = widget.parentWidget()
    return False


def widgets(window) -> list[QWidget]:
    """The visible widgets the page composes, in the order Qt lists them."""
    page, _, _ = page_of(window)
    # `isVisibleTo(page)`: drawn when the page is shown, so a page that was laid out and never shown (a test's) is checked too.
    return [w for w in page.findChildren(QWidget) if w.isVisibleTo(page) and not _inside_qt(w, page)]


def off_grid(window) -> list[str]:
    """Every visible widget whose x, y, width or height is not a multiple of the cell, one line each: its name, its rectangle in
    the page's pixels and what is off. [] when the page is on the grid."""
    page, cell_w, cell_h = page_of(window)
    slack_x = page.width() - theme.COLS * cell_w
    slack_y = page.height() - theme.ROWS * cell_h
    found = []
    for widget in widgets(window):
        if widget.width() <= 0 or widget.height() <= 0:
            continue
        origin = widget.mapTo(page, QPoint(0, 0))
        x, y, w, h = origin.x(), origin.y(), widget.width(), widget.height()
        off = [name for name, ok in (("x", on_grid(x, cell_w, slack_x)), ("y", on_grid(y, cell_h, slack_y)),
                                     ("width", on_grid(w, cell_w, slack_x, size=True)),
                                     ("height", on_grid(h, cell_h, slack_y, size=True))) if not ok]
        if off:
            name = widget.objectName() or type(widget).__name__
            found.append(f"{name} ({x}, {y}, {w}, {h}) off the {cell_w:g} x {cell_h:g} cell in {', '.join(off)}")
    return found


def cards(window) -> list[str]:
    """Every card still on the page: a visible `#box` or `#boxHeading` (the bordered box and its uppercase cyan heading)."""
    return [f"card {w.objectName()} {type(w).__name__}" for w in widgets(window) if w.objectName() in CARD_NAMES]


def violations(window) -> list[str]:
    """What keeps a screen off the grid: its off-grid widgets, then its cards. [] when it is on the grid with no card."""
    return off_grid(window) + cards(window)
